#!/usr/bin/env python3
"""
Claude Memory - Agent Work Embedding Generator
Generates semantic embeddings for agent work to enable vector similarity search.

Usage:
    python3 generate_agent_embeddings.py [--batch-size 10] [--update-all]

Options:
    --batch-size N    Process N records at a time (default: 10)
    --update-all      Regenerate embeddings for all records (default: only NULL embeddings)
"""

import sys
import os
import argparse
from pathlib import Path
from typing import List, Tuple
import psycopg2
from psycopg2.extras import Json
from sentence_transformers import SentenceTransformer

# Import database config from store_agent_definition
from store_agent_definition import get_db_connection

# Use same model as rest of system
MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'
EXPECTED_DIMENSIONS = 384

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

def get_agent_work_without_embeddings(update_all: bool = False) -> List[Tuple]:
    """
    Fetch agent work records that need embeddings.

    Args:
        update_all: If True, fetch all records. If False, only NULL embeddings.

    Returns:
        List of tuples: (id, agent_request, result_summary)
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        if update_all:
            query = """
                SELECT id, agent_request, result_summary
                FROM agent_work
                ORDER BY id
            """
        else:
            query = """
                SELECT id, agent_request, result_summary
                FROM agent_work
                WHERE embedding IS NULL
                ORDER BY id
            """

        cur.execute(query)
        records = cur.fetchall()
        return records

    finally:
        cur.close()
        conn.close()

def create_embedding_text(agent_request: str, result_summary: str = None) -> str:
    """
    Create combined text for embedding generation.

    Combines agent request (what was asked) with result summary (what was achieved)
    to create semantically meaningful embedding for search.

    Args:
        agent_request: The original task given to the agent
        result_summary: The agent's final result/output (optional)

    Returns:
        Combined text for embedding
    """
    parts = []

    # Always include the request (what the agent was asked to do)
    if agent_request:
        parts.append(f"Task: {agent_request}")

    # Include result if available (what the agent accomplished)
    if result_summary:
        parts.append(f"Result: {result_summary}")

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

def update_agent_work_embedding(work_id: int, embedding: List[float]) -> None:
    """
    Update agent_work record with generated embedding.

    Args:
        work_id: ID of agent_work record
        embedding: 384-dimensional embedding vector
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE agent_work
            SET embedding = %s
            WHERE id = %s
        """, (embedding, work_id))

        conn.commit()

    except Exception as e:
        conn.rollback()
        raise Exception(f"Failed to update embedding for work_id {work_id}: {e}")

    finally:
        cur.close()
        conn.close()

def main():
    parser = argparse.ArgumentParser(
        description='Generate embeddings for agent work records'
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

    args = parser.parse_args()

    # Load embedding model
    model = load_embedding_model()

    # Get records that need embeddings
    print(file=sys.stderr)
    print(f"🔍 Fetching agent work records...", file=sys.stderr)
    records = get_agent_work_without_embeddings(update_all=args.update_all)

    if not records:
        print(f"✅ No records need embedding generation", file=sys.stderr)
        return

    print(f"📊 Found {len(records)} records to process", file=sys.stderr)
    print(file=sys.stderr)

    # Process records in batches
    success_count = 0
    error_count = 0

    for i, (work_id, agent_request, result_summary) in enumerate(records, 1):
        try:
            # Create embedding text
            embedding_text = create_embedding_text(agent_request, result_summary)

            # Generate embedding
            embedding = generate_embedding(model, embedding_text)

            # Update database
            update_agent_work_embedding(work_id, embedding)

            print(f"✅ [{i}/{len(records)}] Work ID {work_id}: Embedding generated", file=sys.stderr)
            success_count += 1

            # Show progress summary every batch_size records
            if i % args.batch_size == 0:
                print(f"   Progress: {success_count} succeeded, {error_count} failed", file=sys.stderr)
                print(file=sys.stderr)

        except Exception as e:
            print(f"❌ [{i}/{len(records)}] Work ID {work_id}: Error - {e}", file=sys.stderr)
            error_count += 1
            continue

    # Final summary
    print(file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("Embedding Generation Complete", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"✅ Success: {success_count}", file=sys.stderr)
    print(f"❌ Errors: {error_count}", file=sys.stderr)
    print(f"📊 Total: {len(records)}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

if __name__ == "__main__":
    main()
