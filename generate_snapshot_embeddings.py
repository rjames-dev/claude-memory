#!/usr/bin/env python3
"""
Claude Memory - Context Snapshot Embedding Generator
Regenerates semantic embeddings for context snapshots, replacing mock embeddings.

Usage:
    python3 generate_snapshot_embeddings.py [--batch-size 10] [--update-all] [--mock-only]

Options:
    --batch-size N    Process N records at a time (default: 10)
    --update-all      Regenerate embeddings for all records (default: only NULL embeddings)
    --mock-only       Only regenerate mock embeddings (detects via summary pattern)
"""

import sys
import os
import argparse
from pathlib import Path
from typing import List, Tuple
import psycopg2
from psycopg2.extras import Json
from sentence_transformers import SentenceTransformer

# Database configuration (matches system config)
# Auto-detect if running in Docker or locally
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', '5435'))

DB_CONFIG = {
    'host': DB_HOST,
    'port': DB_PORT,
    'database': 'claude_memory',
    'user': 'memory_admin',
    'password': os.environ.get('CONTEXT_DB_PASSWORD', 'memory_secure_2024')
}

# Use same model as rest of system
MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'
EXPECTED_DIMENSIONS = 384

def get_db_connection():
    """Create database connection."""
    return psycopg2.connect(**DB_CONFIG)

def load_embedding_model():
    """Load the sentence transformer model."""
    try:
        print(f"📥 Loading embedding model: {MODEL_NAME}", file=sys.stderr)
        model = SentenceTransformer(MODEL_NAME)
        print(f"✅ Model loaded successfully", file=sys.stderr)
        return model
    except Exception as e:
        print(f"❌ Failed to load model: {e}", file=sys.stderr)
        sys.exit(1)

def get_snapshots_needing_embeddings(update_all: bool = False, mock_only: bool = False) -> List[Tuple]:
    """
    Fetch snapshot records that need embeddings.

    Args:
        update_all: If True, fetch all records. If False, only NULL embeddings.
        mock_only: If True, only fetch records with mock embeddings (summary contains mock patterns)

    Returns:
        List of tuples: (id, summary, tags, mentioned_files)
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        if mock_only:
            # Detect mock embeddings by checking if summary is very short or contains patterns
            query = """
                SELECT id, summary, tags, mentioned_files
                FROM context_snapshots
                WHERE embedding IS NOT NULL
                  AND (
                    LENGTH(summary) < 100
                    OR summary LIKE '%mock%'
                    OR summary LIKE '%fallback%'
                  )
                ORDER BY id
            """
        elif update_all:
            query = """
                SELECT id, summary, tags, mentioned_files
                FROM context_snapshots
                ORDER BY id
            """
        else:
            query = """
                SELECT id, summary, tags, mentioned_files
                FROM context_snapshots
                WHERE embedding IS NULL
                ORDER BY id
            """

        cur.execute(query)
        records = cur.fetchall()
        return records

    finally:
        cur.close()
        conn.close()

def create_embedding_text(summary: str, tags: list = None, mentioned_files: list = None) -> str:
    """
    Create combined text for embedding generation.

    Combines summary with tags and file mentions to create semantically meaningful
    embedding for search.

    Args:
        summary: The conversation summary
        tags: List of tags/topics (optional)
        mentioned_files: List of files mentioned (optional)

    Returns:
        Combined text for embedding
    """
    parts = []

    # Primary content: the summary
    if summary:
        parts.append(summary)

    # Add tags for topic context
    if tags and len(tags) > 0:
        tags_str = ", ".join(tags[:10])  # Limit to 10 tags
        parts.append(f"Topics: {tags_str}")

    # Add key files for context
    if mentioned_files and len(mentioned_files) > 0:
        files_str = ", ".join(mentioned_files[:10])  # Limit to 10 files
        parts.append(f"Files: {files_str}")

    combined = "\n\n".join(parts)

    # Limit to reasonable length (model has token limit)
    if len(combined) > 5000:
        combined = combined[:5000] + "..."

    return combined

def generate_embedding(model: SentenceTransformer, text: str) -> List[float]:
    """
    Generate embedding for given text.

    Args:
        model: Loaded SentenceTransformer model
        text: Text to embed

    Returns:
        384-dimensional embedding vector
    """
    embedding = model.encode(text)
    embedding_list = embedding.tolist()

    # Verify dimensions
    if len(embedding_list) != EXPECTED_DIMENSIONS:
        raise ValueError(f"Expected {EXPECTED_DIMENSIONS} dimensions, got {len(embedding_list)}")

    return embedding_list

def update_snapshot_embedding(snapshot_id: int, embedding: List[float]) -> None:
    """
    Update context_snapshots record with generated embedding.

    Args:
        snapshot_id: ID of context_snapshots record
        embedding: 384-dimensional embedding vector
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE context_snapshots
            SET embedding = %s
            WHERE id = %s
        """, (embedding, snapshot_id))

        conn.commit()

    except Exception as e:
        conn.rollback()
        raise Exception(f"Failed to update embedding for snapshot_id {snapshot_id}: {e}")

    finally:
        cur.close()
        conn.close()

def main():
    parser = argparse.ArgumentParser(
        description='Generate embeddings for context snapshot records'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Number of records to process at a time (default: 10)'
    )
    parser.add_argument(
        '--update-all',
        action='store_true',
        help='Regenerate embeddings for all records (default: only NULL embeddings)'
    )
    parser.add_argument(
        '--mock-only',
        action='store_true',
        help='Only regenerate mock/fallback embeddings (default: only NULL embeddings)'
    )

    args = parser.parse_args()

    # Load embedding model
    model = load_embedding_model()

    # Get records that need embeddings
    print(file=sys.stderr)
    print(f"🔍 Fetching context snapshot records...", file=sys.stderr)

    if args.mock_only:
        print(f"   Mode: Regenerating mock/fallback embeddings only", file=sys.stderr)
    elif args.update_all:
        print(f"   Mode: Regenerating ALL embeddings", file=sys.stderr)
    else:
        print(f"   Mode: Generating missing (NULL) embeddings only", file=sys.stderr)

    records = get_snapshots_needing_embeddings(update_all=args.update_all, mock_only=args.mock_only)

    if not records:
        print(f"✅ No records need embedding generation", file=sys.stderr)
        return

    print(f"📊 Found {len(records)} records to process", file=sys.stderr)
    print(file=sys.stderr)

    # Process records in batches
    success_count = 0
    error_count = 0

    for i, (snapshot_id, summary, tags, mentioned_files) in enumerate(records, 1):
        try:
            # Create embedding text
            embedding_text = create_embedding_text(summary, tags, mentioned_files)

            # Generate embedding
            embedding = generate_embedding(model, embedding_text)

            # Update database
            update_snapshot_embedding(snapshot_id, embedding)

            # Show truncated summary for context
            summary_preview = (summary[:60] + '...') if summary and len(summary) > 60 else (summary or 'N/A')
            print(f"✅ [{i}/{len(records)}] Snapshot ID {snapshot_id}: Embedding generated", file=sys.stderr)
            print(f"   Summary: {summary_preview}", file=sys.stderr)
            success_count += 1

            # Show progress summary every batch_size records
            if i % args.batch_size == 0:
                print(f"   Progress: {success_count} succeeded, {error_count} failed", file=sys.stderr)
                print(file=sys.stderr)

        except Exception as e:
            print(f"❌ [{i}/{len(records)}] Snapshot ID {snapshot_id}: Error - {e}", file=sys.stderr)
            error_count += 1
            continue

    # Final summary
    print(file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("Snapshot Embedding Generation Complete", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"✅ Success: {success_count}", file=sys.stderr)
    print(f"❌ Errors: {error_count}", file=sys.stderr)
    print(f"📊 Total: {len(records)}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

if __name__ == "__main__":
    main()
