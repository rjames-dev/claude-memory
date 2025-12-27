#!/usr/bin/env python3
"""
Generate embeddings for skill triggers

Uses Ollama's mxbai-embed-large model (1024 dimensions)
Same model as used for existing skill embeddings in claude-memory

Usage:
    # Generate for specific trigger
    python3 generate-trigger-embeddings.py --trigger-id 5

    # Backfill all triggers missing embeddings
    python3 generate-trigger-embeddings.py --backfill

    # Regenerate all embeddings (model update)
    python3 generate-trigger-embeddings.py --regenerate

    # Test with a phrase
    python3 generate-trigger-embeddings.py --test "commit these changes"
"""

import sys
import os
import argparse
import psycopg2
import requests
import numpy as np
from typing import List, Optional, Tuple
import time

# Ollama configuration
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
EMBEDDING_MODEL = 'mxbai-embed-large'
EMBEDDING_DIM = 1024

# ============================================================================
# Database Connection
# ============================================================================

def get_db_password():
    """Get database password from .env file or environment."""
    password = os.environ.get('CONTEXT_DB_PASSWORD')
    if password:
        return password

    # Try reading from .env file
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('CONTEXT_DB_PASSWORD='):
                    return line.strip().split('=', 1)[1]

    return 'memory_secure_2024'  # Fallback

def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=int(os.environ.get('DB_PORT', 5435)),
        database='claude_memory',
        user='memory_admin',
        password=get_db_password()
    )

# ============================================================================
# Ollama Connection & Embedding Generation
# ============================================================================

def test_ollama_connection() -> bool:
    """Test if Ollama is accessible and model is available."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [m.get('name', '') for m in models]

            if any(EMBEDDING_MODEL in name for name in model_names):
                return True
            else:
                print(f"❌ {EMBEDDING_MODEL} model not found")
                print(f"   Available: {model_names}")
                print(f"   Run: docker exec claude-ollama ollama pull {EMBEDDING_MODEL}")
                return False
        else:
            print(f"❌ Ollama returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Failed to connect to Ollama: {e}")
        print(f"   Is Ollama running? Check: docker ps | grep ollama")
        return False

def generate_embedding(text: str) -> List[float]:
    """
    Generate 1024-dim embedding for text using Ollama.

    Args:
        text: Input text to embed

    Returns:
        List of 1024 floats

    Raises:
        Exception: if embedding generation fails
    """
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={
                "model": EMBEDDING_MODEL,
                "prompt": text
            },
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            embedding = data.get('embedding')

            if embedding and len(embedding) == EMBEDDING_DIM:
                return embedding
            else:
                raise ValueError(f"Invalid embedding dimensions: {len(embedding) if embedding else 0}")
        else:
            raise Exception(f"Ollama returned status {response.status_code}: {response.text}")

    except requests.exceptions.Timeout:
        raise Exception("Ollama request timed out after 30s")
    except Exception as e:
        raise Exception(f"Failed to generate embedding: {e}")

def validate_embedding(embedding: List[float], text: str = ""):
    """
    Validate embedding format.

    Args:
        embedding: list of floats to validate
        text: optional text for error messages

    Raises:
        ValueError: if embedding is invalid
    """
    # Check dimensions
    if len(embedding) != EMBEDDING_DIM:
        raise ValueError(f"Invalid dimensions: {len(embedding)}, expected {EMBEDDING_DIM}")

    # Convert to numpy for additional checks
    embedding_array = np.array(embedding)

    # Check for NaN/Inf
    if not np.isfinite(embedding_array).all():
        raise ValueError(f"Embedding contains NaN or Inf values")

# ============================================================================
# Database Operations
# ============================================================================

def store_embedding(trigger_id: int, embedding: List[float]) -> bool:
    """
    Store embedding in database.

    Args:
        trigger_id: ID of trigger
        embedding: 384-dim embedding

    Returns:
        True if successful
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE skills_triggers
            SET embedding = %s
            WHERE id = %s
        """, (embedding, trigger_id))

        conn.commit()

        if cur.rowcount == 0:
            print(f"  ⚠️  Trigger {trigger_id} not found")
            return False

        return True

    except Exception as e:
        conn.rollback()
        print(f"  ❌ Database error: {e}")
        return False

    finally:
        cur.close()
        conn.close()

def get_trigger(trigger_id: int) -> Optional[Tuple[int, str]]:
    """
    Get trigger by ID.

    Args:
        trigger_id: Trigger ID

    Returns:
        (id, trigger_phrase) or None
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id, trigger_phrase
            FROM skills_triggers
            WHERE id = %s
        """, (trigger_id,))

        result = cur.fetchone()
        return result

    finally:
        cur.close()
        conn.close()

def get_triggers_missing_embeddings() -> List[Tuple[int, str]]:
    """
    Get all triggers missing embeddings.

    Returns:
        List of (id, trigger_phrase) tuples
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id, trigger_phrase
            FROM skills_triggers
            WHERE match_type = 'semantic'
              AND embedding IS NULL
              AND is_active = TRUE
            ORDER BY id
        """)

        results = cur.fetchall()
        return results

    finally:
        cur.close()
        conn.close()

def get_all_semantic_triggers() -> List[Tuple[int, str]]:
    """
    Get all semantic triggers (for regeneration).

    Returns:
        List of (id, trigger_phrase) tuples
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id, trigger_phrase
            FROM skills_triggers
            WHERE match_type = 'semantic'
              AND is_active = TRUE
            ORDER BY id
        """)

        results = cur.fetchall()
        return results

    finally:
        cur.close()
        conn.close()

# ============================================================================
# Operations
# ============================================================================

def generate_trigger_embedding(trigger_id: int, trigger_phrase: str, verbose: bool = True) -> bool:
    """
    Generate and store embedding for a single trigger.

    Args:
        trigger_id: Trigger ID
        trigger_phrase: Trigger text
        verbose: Print progress

    Returns:
        True if successful
    """
    if verbose:
        print(f"  Generating embedding for: '{trigger_phrase}'")

    try:
        # Generate embedding
        start = time.time()
        embedding = generate_embedding(trigger_phrase)
        elapsed = time.time() - start

        # Store in database
        success = store_embedding(trigger_id, embedding)

        if success and verbose:
            print(f"  ✅ Embedding stored ({elapsed*1000:.0f}ms, {EMBEDDING_DIM} dims)")

        return success

    except Exception as e:
        if verbose:
            print(f"  ❌ Error: {e}")
        return False

def backfill_embeddings() -> dict:
    """
    Generate embeddings for all triggers missing them.

    Returns:
        Dict with statistics
    """
    print("\n" + "="*70)
    print("Backfilling Embeddings for Semantic Triggers")
    print("="*70 + "\n")

    triggers = get_triggers_missing_embeddings()
    total = len(triggers)

    if total == 0:
        print("✅ No triggers missing embeddings")
        return {'total': 0, 'success': 0, 'failed': 0}

    print(f"Found {total} triggers needing embeddings\n")

    success_count = 0
    failed_count = 0
    start_time = time.time()

    for i, (trigger_id, phrase) in enumerate(triggers, 1):
        print(f"[{i}/{total}] ID:{trigger_id}", end=" ")

        success = generate_trigger_embedding(trigger_id, phrase)

        if success:
            success_count += 1
        else:
            failed_count += 1

        print()  # Newline

    elapsed = time.time() - start_time

    print()
    print("="*70)
    print(f"✅ Backfill complete:")
    print(f"   Total: {total}")
    print(f"   Success: {success_count}")
    print(f"   Failed: {failed_count}")
    print(f"   Time: {elapsed:.1f}s ({elapsed/total*1000:.0f}ms avg)")
    print("="*70 + "\n")

    return {
        'total': total,
        'success': success_count,
        'failed': failed_count,
        'time': elapsed
    }

def regenerate_all() -> dict:
    """
    Regenerate all embeddings (for model updates).

    Returns:
        Dict with statistics
    """
    print("\n" + "="*70)
    print("Regenerating All Embeddings")
    print("="*70 + "\n")

    triggers = get_all_semantic_triggers()
    total = len(triggers)

    if total == 0:
        print("⚠️  No semantic triggers found")
        return {'total': 0, 'success': 0, 'failed': 0}

    print(f"Regenerating {total} embeddings\n")

    success_count = 0
    failed_count = 0
    start_time = time.time()

    for i, (trigger_id, phrase) in enumerate(triggers, 1):
        print(f"[{i}/{total}] ID:{trigger_id}", end=" ")

        success = generate_trigger_embedding(trigger_id, phrase)

        if success:
            success_count += 1
        else:
            failed_count += 1

        print()  # Newline

    elapsed = time.time() - start_time

    print()
    print("="*70)
    print(f"✅ Regeneration complete:")
    print(f"   Total: {total}")
    print(f"   Success: {success_count}")
    print(f"   Failed: {failed_count}")
    print(f"   Time: {elapsed:.1f}s ({elapsed/total*1000:.0f}ms avg)")
    print("="*70 + "\n")

    return {
        'total': total,
        'success': success_count,
        'failed': failed_count,
        'time': elapsed
    }

def test_embedding(phrase: str):
    """
    Test embedding generation with a phrase.

    Args:
        phrase: Text to embed
    """
    print("\n" + "="*70)
    print("Test Embedding Generation")
    print("="*70 + "\n")

    # Test Ollama connection first
    print("Testing Ollama connection...")
    if not test_ollama_connection():
        print("\n❌ Cannot proceed without Ollama connection")
        return

    print(f"✅ Connected to Ollama at {OLLAMA_URL}\n")
    print(f"Phrase: \"{phrase}\"\n")

    start = time.time()
    try:
        embedding = generate_embedding(phrase)
        elapsed = time.time() - start

        print(f"✅ Embedding generated:")
        print(f"   Model: {EMBEDDING_MODEL}")
        print(f"   Dimensions: {len(embedding)}")
        print(f"   Time: {elapsed*1000:.0f}ms")
        print(f"   First 10 values: {[f'{v:.4f}' for v in embedding[:10]]}")
        print()

        # Show some statistics
        embedding_array = np.array(embedding)
        print(f"Statistics:")
        print(f"   Min: {embedding_array.min():.4f}")
        print(f"   Max: {embedding_array.max():.4f}")
        print(f"   Mean: {embedding_array.mean():.4f}")
        print(f"   Std: {embedding_array.std():.4f}")
        print()

    except Exception as e:
        print(f"\n❌ Failed to generate embedding: {e}")
        import traceback
        traceback.print_exc()

# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description='Generate embeddings for skill triggers',
        epilog='Examples:\n'
               '  generate-trigger-embeddings.py --backfill\n'
               '  generate-trigger-embeddings.py --trigger-id 5\n'
               '  generate-trigger-embeddings.py --test "commit changes"',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--trigger-id', type=int, metavar='ID',
                       help='Generate embedding for specific trigger ID')
    parser.add_argument('--backfill', action='store_true',
                       help='Generate embeddings for all triggers missing them')
    parser.add_argument('--regenerate', action='store_true',
                       help='Regenerate all embeddings (for model updates)')
    parser.add_argument('--test', metavar='PHRASE',
                       help='Test embedding generation with a phrase')

    args = parser.parse_args()

    try:
        if args.test:
            test_embedding(args.test)
            return 0

        elif args.trigger_id:
            trigger = get_trigger(args.trigger_id)

            if not trigger:
                print(f"❌ Trigger {args.trigger_id} not found")
                return 1

            trigger_id, phrase = trigger
            print(f"\nGenerating embedding for trigger {trigger_id}")

            success = generate_trigger_embedding(trigger_id, phrase)
            return 0 if success else 1

        elif args.backfill:
            result = backfill_embeddings()
            return 0 if result['failed'] == 0 else 1

        elif args.regenerate:
            result = regenerate_all()
            return 0 if result['failed'] == 0 else 1

        else:
            parser.print_help()
            print("\n💡 Tip: Use --backfill to generate embeddings for all triggers")
            return 1

    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
