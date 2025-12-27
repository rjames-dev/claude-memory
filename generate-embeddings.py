#!/usr/bin/env python3
"""
Claude Memory - Skills System: Embedding Generation

Generates embeddings for skill trigger phrases using Ollama's mxbai-embed-large model.
Stores embeddings in the database for semantic similarity search.

Usage:
    python3 generate-embeddings.py              # Generate for all triggers missing embeddings
    python3 generate-embeddings.py --all        # Regenerate all embeddings (overwrite existing)
    python3 generate-embeddings.py --skill-id 5 # Generate for specific skill only
    python3 generate-embeddings.py --dry-run    # Preview what would be done

Phase 2 Milestone 3: Semantic Matching
"""

import sys
import os
import argparse
import requests
import psycopg2
from psycopg2.extras import RealDictCursor

# Ollama configuration
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
EMBEDDING_MODEL = 'mxbai-embed-large'
EMBEDDING_DIMENSIONS = 1024

# Database configuration
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', '5435'))

DB_CONFIG = {
    'host': DB_HOST,
    'port': DB_PORT,
    'database': 'claude_memory',
    'user': 'memory_admin',
    'password': os.environ.get('CONTEXT_DB_PASSWORD', 'memory_secure_2024')
}


def get_db_connection():
    """Create database connection."""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"❌ Database connection failed: {e}", file=sys.stderr)
        print(f"   Host: {DB_HOST}:{DB_PORT}", file=sys.stderr)
        sys.exit(1)


def test_ollama_connection():
    """Test if Ollama is accessible and model is available."""
    print("Testing Ollama connection...")
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [m.get('name', '') for m in models]

            if any(EMBEDDING_MODEL in name for name in model_names):
                print(f"✅ Connected to Ollama at {OLLAMA_URL}")
                print(f"✅ {EMBEDDING_MODEL} model available")
                return True
            else:
                print(f"❌ {EMBEDDING_MODEL} model not found", file=sys.stderr)
                print(f"   Available: {model_names}", file=sys.stderr)
                print(f"   Run: docker exec claude-ollama ollama pull {EMBEDDING_MODEL}", file=sys.stderr)
                return False
        else:
            print(f"❌ Ollama returned status {response.status_code}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"❌ Failed to connect to Ollama: {e}", file=sys.stderr)
        print(f"   Is Ollama running? Check: docker ps | grep ollama", file=sys.stderr)
        return False


def generate_embedding(text):
    """
    Generate embedding for text using Ollama.

    Args:
        text: Text to embed

    Returns:
        list: 1024-dimensional embedding vector, or None if failed
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
            embedding = data.get('embedding', [])

            if len(embedding) == EMBEDDING_DIMENSIONS:
                return embedding
            else:
                print(f"⚠️  Unexpected embedding dimensions: {len(embedding)} (expected {EMBEDDING_DIMENSIONS})")
                return None
        else:
            print(f"❌ Ollama request failed: {response.status_code} - {response.text}", file=sys.stderr)
            return None

    except Exception as e:
        print(f"❌ Error generating embedding: {e}", file=sys.stderr)
        return None


def get_triggers_needing_embeddings(conn, regenerate_all=False, skill_id=None):
    """
    Fetch triggers that need embeddings generated.

    Args:
        conn: Database connection
        regenerate_all: If True, fetch all triggers (overwrite existing)
        skill_id: If provided, only fetch triggers for this skill

    Returns:
        list: Trigger records
    """
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if regenerate_all:
        condition = "TRUE"
    else:
        condition = "st.embedding IS NULL"

    if skill_id:
        condition += f" AND st.agent_id = {skill_id}"

    query = f"""
        SELECT
            st.id,
            st.agent_id,
            st.trigger_phrase,
            st.match_type,
            sa.agent_name,
            sa.display_name,
            st.embedding IS NOT NULL AS has_embedding
        FROM skills_triggers st
        JOIN skills_agents sa ON sa.id = st.agent_id
        WHERE st.is_active = TRUE
          AND {condition}
        ORDER BY sa.agent_name, st.trigger_phrase
    """

    cur.execute(query)
    triggers = cur.fetchall()
    cur.close()

    return [dict(t) for t in triggers]


def store_embedding(conn, trigger_id, embedding):
    """
    Store embedding vector in database.

    Args:
        conn: Database connection
        trigger_id: Trigger ID to update
        embedding: 1024-dimensional vector

    Returns:
        bool: Success
    """
    try:
        cur = conn.cursor()

        # Convert Python list to PostgreSQL vector format
        vector_str = '[' + ','.join(str(v) for v in embedding) + ']'

        cur.execute("""
            UPDATE skills_triggers
            SET embedding = %s::vector
            WHERE id = %s
        """, (vector_str, trigger_id))

        affected = cur.rowcount
        conn.commit()
        cur.close()

        return affected > 0

    except Exception as e:
        conn.rollback()
        print(f"❌ Database error storing embedding: {e}", file=sys.stderr)
        return False


def generate_embeddings(args):
    """
    Main function to generate embeddings for triggers.

    Returns:
        int: 0 on success, 1 on failure
    """
    # Test Ollama connection
    if not test_ollama_connection():
        return 1

    # Connect to database
    conn = get_db_connection()

    # Get triggers needing embeddings
    print("\nFetching triggers...")
    triggers = get_triggers_needing_embeddings(
        conn,
        regenerate_all=args.all,
        skill_id=args.skill_id
    )

    if not triggers:
        print("✅ No triggers need embedding generation")
        conn.close()
        return 0

    print(f"Found {len(triggers)} trigger(s) to process:")
    for t in triggers:
        status = "has embedding" if t['has_embedding'] else "no embedding"
        print(f"  - [{t['agent_name']}] '{t['trigger_phrase']}' ({status})")

    if args.dry_run:
        print("\n(--dry-run mode, no changes made)")
        conn.close()
        return 0

    # Generate embeddings
    print(f"\n{'='*80}")
    print("Generating embeddings...")
    print(f"{'='*80}")

    success_count = 0
    fail_count = 0

    for i, trigger in enumerate(triggers, 1):
        print(f"\n[{i}/{len(triggers)}] Processing: '{trigger['trigger_phrase']}'")

        # Generate embedding
        embedding = generate_embedding(trigger['trigger_phrase'])

        if embedding is None:
            print(f"   ❌ Failed to generate embedding")
            fail_count += 1
            continue

        print(f"   ✅ Generated {len(embedding)}-dimensional vector")

        # Store in database
        if store_embedding(conn, trigger['id'], embedding):
            print(f"   ✅ Stored in database")
            success_count += 1
        else:
            print(f"   ❌ Failed to store in database")
            fail_count += 1

    # Summary
    print(f"\n{'='*80}")
    print(f"Embedding Generation Summary:")
    print(f"  Total triggers: {len(triggers)}")
    print(f"  Success: {success_count}")
    if fail_count > 0:
        print(f"  Failed: {fail_count}")
    print(f"{'='*80}")

    conn.close()

    return 0 if fail_count == 0 else 1


def main():
    parser = argparse.ArgumentParser(
        description='Generate embeddings for skill trigger phrases',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate embeddings for triggers that don't have them
  python3 generate-embeddings.py

  # Regenerate all embeddings (overwrite existing)
  python3 generate-embeddings.py --all

  # Generate for specific skill only
  python3 generate-embeddings.py --skill-id 5

  # Preview what would be done
  python3 generate-embeddings.py --dry-run

  # Regenerate all with preview first
  python3 generate-embeddings.py --all --dry-run
        """
    )

    parser.add_argument('--all',
                        action='store_true',
                        help='Regenerate all embeddings (overwrite existing)')
    parser.add_argument('--skill-id',
                        type=int,
                        help='Generate embeddings for specific skill only')
    parser.add_argument('--dry-run',
                        action='store_true',
                        help='Preview what would be done without making changes')

    args = parser.parse_args()

    # Generate embeddings
    exit_code = generate_embeddings(args)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
