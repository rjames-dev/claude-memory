#!/usr/bin/env python3
"""
Claude Memory - Skills System: Semantic Skill Search

Search for skills using natural language queries with semantic similarity matching.
Uses embeddings to find relevant skills even if query doesn't match trigger phrases exactly.

Usage:
    python3 search-skills-semantic.py "check if database is healthy"
    python3 search-skills-semantic.py "make a backup" --threshold 0.6
    python3 search-skills-semantic.py "verify db" --limit 10
    python3 search-skills-semantic.py "git status" --show-scores

Phase 2 Milestone 3: Semantic Matching - Search Implementation
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

# Database configuration
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', '5435'))

# Default similarity threshold (0.0 - 1.0)
DEFAULT_THRESHOLD = 0.7


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
    """Create database connection."""
    try:
        return psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database='claude_memory',
            user='memory_admin',
            password=get_db_password()
        )
    except Exception as e:
        print(f"❌ Database connection failed: {e}", file=sys.stderr)
        sys.exit(1)


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
            return data.get('embedding', [])
        else:
            print(f"❌ Ollama request failed: {response.status_code}", file=sys.stderr)
            return None

    except Exception as e:
        print(f"❌ Error generating embedding: {e}", file=sys.stderr)
        return None


def semantic_search(conn, query_embedding, threshold=DEFAULT_THRESHOLD, limit=5):
    """
    Search for skills using semantic similarity.

    Args:
        conn: Database connection
        query_embedding: Query vector (1024-dimensional)
        threshold: Minimum similarity score (0.0 - 1.0)
        limit: Maximum number of results

    Returns:
        list: Matching skills with similarity scores
    """
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Convert embedding to vector format
        vector_str = '[' + ','.join(str(v) for v in query_embedding) + ']'

        # Semantic search query using cosine similarity
        # Similarity = 1 - (vector1 <=> vector2)
        # <=> is the cosine distance operator in pgvector
        query = """
            SELECT DISTINCT ON (sa.id)
                sa.id AS skill_id,
                sa.agent_name,
                sa.display_name,
                sa.description,
                sa.category,
                sa.use_count,
                sa.success_rate,
                st.trigger_phrase AS matched_trigger,
                1 - (st.embedding <=> %s::vector) AS similarity
            FROM skills_agents sa
            JOIN skills_triggers st ON st.agent_id = sa.id
            WHERE sa.is_active = TRUE
              AND st.is_active = TRUE
              AND st.embedding IS NOT NULL
              AND 1 - (st.embedding <=> %s::vector) >= %s
            ORDER BY sa.id, similarity DESC
        """

        # Order by similarity and apply limit after DISTINCT ON
        final_query = f"""
            WITH ranked_results AS ({query})
            SELECT *
            FROM ranked_results
            ORDER BY similarity DESC
            LIMIT %s
        """

        cur.execute(final_query, (vector_str, vector_str, threshold, limit))
        results = cur.fetchall()
        cur.close()

        return [dict(r) for r in results]

    except Exception as e:
        print(f"❌ Search failed: {e}", file=sys.stderr)
        return []


def display_results(results, query, show_scores=False):
    """
    Display search results in user-friendly format.

    Args:
        results: List of skill matches
        query: Original query string
        show_scores: Show similarity scores
    """
    if not results:
        print(f"\n❌ No skills found matching: '{query}'")
        print(f"   Try lowering the similarity threshold with --threshold")
        return

    print(f"\n{'='*80}")
    print(f"Semantic Search Results for: '{query}'")
    print(f"Found {len(results)} matching skill(s)")
    print(f"{'='*80}\n")

    for i, skill in enumerate(results, 1):
        similarity_pct = skill['similarity'] * 100

        # Similarity indicator
        if similarity_pct >= 90:
            indicator = "🎯"  # Excellent match
        elif similarity_pct >= 80:
            indicator = "✅"  # Very good match
        elif similarity_pct >= 70:
            indicator = "👍"  # Good match
        else:
            indicator = "👌"  # Acceptable match

        print(f"{indicator} [{i}] {skill['display_name']}")
        print(f"    Name: {skill['agent_name']}")
        print(f"    Category: {skill['category']}")
        print(f"    Matched Trigger: \"{skill['matched_trigger']}\"")

        if show_scores:
            print(f"    Similarity: {similarity_pct:.1f}%")

        # Status indicator
        status = []
        if skill['use_count'] == 0:
            status.append("🆕 New")
        elif skill['use_count'] >= 10 and skill['success_rate'] >= 90:
            status.append("✅ Stable")
        elif skill['success_rate'] < 70:
            status.append("⚠️  Needs Improvement")

        if status:
            print(f"    Status: {', '.join(status)}")

        print(f"    Usage: {skill['use_count']} executions, {skill['success_rate']:.1f}% success")

        # Description (truncated)
        desc = skill['description']
        if desc:
            if len(desc) > 80:
                desc = desc[:77] + "..."
            print(f"    Description: {desc}")
        else:
            print(f"    Description: (no description)")

        print()


def search_skills(args):
    """
    Main search function.

    Returns:
        int: 0 on success, 1 on failure
    """
    query = args.query

    print(f"Searching for: '{query}'")
    print(f"Threshold: {args.threshold:.2f}")
    print(f"Limit: {args.limit}")

    # Generate query embedding
    print("\nGenerating query embedding...")
    query_embedding = generate_embedding(query)

    if not query_embedding:
        print("❌ Failed to generate query embedding", file=sys.stderr)
        return 1

    print(f"✅ Generated {len(query_embedding)}-dimensional embedding")

    # Connect to database
    conn = get_db_connection()

    # Perform semantic search
    print("Searching database...")
    results = semantic_search(
        conn,
        query_embedding,
        threshold=args.threshold,
        limit=args.limit
    )

    conn.close()

    # Display results
    display_results(results, query, show_scores=args.show_scores)

    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Search for skills using natural language semantic matching',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for database health check
  python3 search-skills-semantic.py "check if database is healthy"

  # Search for backup skills
  python3 search-skills-semantic.py "make a backup"

  # Lower threshold to find more results
  python3 search-skills-semantic.py "verify db" --threshold 0.6

  # Show more results
  python3 search-skills-semantic.py "git" --limit 10

  # Show similarity scores
  python3 search-skills-semantic.py "database" --show-scores

Similarity Thresholds:
  0.9-1.0  : Nearly identical (🎯 Excellent match)
  0.8-0.9  : Very similar (✅ Very good match)
  0.7-0.8  : Similar (👍 Good match)
  0.6-0.7  : Somewhat similar (👌 Acceptable match)
  <0.6     : Different (may not be relevant)

Default threshold: 0.7 (Good match)
        """
    )

    parser.add_argument('query',
                        help='Natural language query to search for skills')
    parser.add_argument('--threshold',
                        type=float,
                        default=DEFAULT_THRESHOLD,
                        help=f'Minimum similarity score (0.0-1.0, default: {DEFAULT_THRESHOLD})')
    parser.add_argument('--limit',
                        type=int,
                        default=5,
                        help='Maximum number of results to return (default: 5)')
    parser.add_argument('--show-scores',
                        action='store_true',
                        help='Show similarity scores in output')

    args = parser.parse_args()

    # Validate threshold
    if not 0.0 <= args.threshold <= 1.0:
        parser.error("Threshold must be between 0.0 and 1.0")

    # Search
    exit_code = search_skills(args)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
