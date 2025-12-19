#!/usr/bin/env python3
"""
Claude Memory - Agent Definition Storage
Extracts agent definition from transcript and stores in database with deduplication.

Usage:
    python3 store-agent-definition.py <agent-transcript.jsonl>
"""

import json
import sys
import os
from pathlib import Path
import psycopg2
from psycopg2.extras import Json

# Import the extraction function
from extract_agent_definition import extract_agent_definition

# Database configuration (Docker port mapping)
DB_CONFIG = {
    'host': 'localhost',
    'port': 5435,  # Docker mapped port for claude-context-db
    'database': 'claude_memory',
    'user': 'memory_admin',
    'password': os.getenv('CONTEXT_DB_PASSWORD', 'RvnK7z05jIlgo4FIf4dvpvWhSl4lnOtWQgH0a9gEzVE=')
}

def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(**DB_CONFIG)

def get_or_create_agent_definition(definition: dict) -> int:
    """
    Find existing agent definition or create new one.

    Uses config_hash for deduplication - if an agent definition with the
    same configuration already exists, returns that definition_id.

    Args:
        definition: Dict with agent definition fields

    Returns:
        definition_id: The ID of the agent definition (existing or new)
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Check if definition with this config_hash already exists
        cur.execute("""
            SELECT id, version
            FROM agent_definitions
            WHERE config_hash = %s
        """, (definition['config_hash'],))

        result = cur.fetchone()

        if result:
            # Existing definition found!
            definition_id, version = result
            print(f"✓ Found existing definition (ID: {definition_id}, Version: {version})", file=sys.stderr)
            return definition_id

        # No existing definition - determine version number
        # Check if there are any existing definitions of this type
        cur.execute("""
            SELECT COALESCE(MAX(version), 0) as max_version
            FROM agent_definitions
            WHERE agent_type = %s
        """, (definition['agent_type'],))

        max_version = cur.fetchone()[0]
        next_version = max_version + 1

        # Insert new definition
        cur.execute("""
            INSERT INTO agent_definitions (
                agent_type,
                agent_name,
                system_message,
                configuration_params,
                tools_available,
                model_used,
                version,
                description,
                created_by,
                config_hash
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            definition['agent_type'],
            None,  # agent_name (optional)
            definition.get('system_message'),
            Json(definition['configuration_params']),
            definition['tools_available'],
            definition['model_used'],
            next_version,
            f"Auto-detected from agent transcript",
            'system',
            definition['config_hash']
        ))

        definition_id = cur.fetchone()[0]
        conn.commit()

        print(f"✓ Created new definition (ID: {definition_id}, Version: {next_version})", file=sys.stderr)
        return definition_id

    except Exception as e:
        conn.rollback()
        raise Exception(f"Database error: {e}")

    finally:
        cur.close()
        conn.close()

def get_definition_details(definition_id: int) -> dict:
    """Retrieve full definition details from database."""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                id,
                agent_type,
                version,
                model_used,
                tools_available,
                configuration_params,
                config_hash,
                created_at
            FROM agent_definitions
            WHERE id = %s
        """, (definition_id,))

        row = cur.fetchone()
        if not row:
            return None

        return {
            'id': row[0],
            'agent_type': row[1],
            'version': row[2],
            'model_used': row[3],
            'tools_available': row[4],
            'configuration_params': row[5],
            'config_hash': row[6],
            'created_at': row[7].isoformat()
        }

    finally:
        cur.close()
        conn.close()

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 store-agent-definition.py <agent-transcript.jsonl>", file=sys.stderr)
        sys.exit(1)

    transcript_path = sys.argv[1]

    if not Path(transcript_path).exists():
        print(f"Error: File not found: {transcript_path}", file=sys.stderr)
        sys.exit(1)

    try:
        # Extract definition from transcript
        print(f"📖 Extracting agent definition from: {Path(transcript_path).name}", file=sys.stderr)
        definition = extract_agent_definition(transcript_path)

        print(f"   Agent ID: {definition['agent_id']}", file=sys.stderr)
        print(f"   Agent Type: {definition['agent_type']}", file=sys.stderr)
        print(f"   Model: {definition['model_used']}", file=sys.stderr)
        print(f"   Tools: {', '.join(definition['tools_available']) if definition['tools_available'] else 'None'}", file=sys.stderr)
        print(f"   Config Hash: {definition['config_hash'][:16]}...", file=sys.stderr)
        print(file=sys.stderr)

        # Store in database (with deduplication)
        print("💾 Storing in database...", file=sys.stderr)
        definition_id = get_or_create_agent_definition(definition)

        # Retrieve and display the stored definition
        stored_def = get_definition_details(definition_id)

        print(file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print("Stored Agent Definition", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        # Output as JSON for programmatic use
        print(json.dumps(stored_def, indent=2))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
