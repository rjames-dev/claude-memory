#!/usr/bin/env python3
"""
Claude Memory - Skills System: Skill Import Tool

Import skills from JSON export files.

Usage:
    python3 import-skill.py skills.json
    python3 import-skill.py backup.json --skip-existing
    python3 import-skill.py all-skills.json --dry-run

Arguments:
    json_file               JSON file to import
    --skip-existing         Skip skills that already exist
    --overwrite             Overwrite existing skills
    --dry-run               Preview import without making changes
"""

import sys
import os
import argparse
import json
import psycopg2
from psycopg2.extras import RealDictCursor

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
        sys.exit(1)


def skill_exists(conn, agent_name):
    """Check if skill already exists."""
    cur = conn.cursor()
    cur.execute("SELECT id FROM skills_agents WHERE agent_name = %s", (agent_name,))
    result = cur.fetchone()
    cur.close()
    return result is not None


def import_single_skill(conn, skill_data, skip_existing=False, overwrite=False):
    """
    Import a single skill.

    Args:
        conn: Database connection
        skill_data: Skill data dict
        skip_existing: Skip if skill exists
        overwrite: Overwrite if skill exists

    Returns:
        tuple: (success, message)
    """
    agent_name = skill_data['agent_name']

    # Check if exists
    exists = skill_exists(conn, agent_name)

    if exists:
        if skip_existing:
            return (True, f"⏭️  Skipped (already exists): {agent_name}")
        elif overwrite:
            # Delete existing skill first
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM skills_agents WHERE agent_name = %s", (agent_name,))
                conn.commit()
                cur.close()
            except Exception as e:
                conn.rollback()
                return (False, f"❌ Failed to delete existing skill: {e}")
        else:
            return (False, f"❌ Skill exists (use --skip-existing or --overwrite): {agent_name}")

    # Insert skill
    try:
        cur = conn.cursor()

        # Insert into skills_agents
        cur.execute("""
            INSERT INTO skills_agents (
                agent_name,
                display_name,
                description,
                category,
                scope,
                project_path
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            skill_data['agent_name'],
            skill_data['display_name'],
            skill_data['description'],
            skill_data['category'],
            skill_data.get('scope', 'global'),
            skill_data.get('project_path')
        ))

        skill_id = cur.fetchone()[0]

        # Insert triggers
        for trigger_phrase in skill_data.get('triggers', []):
            cur.execute("""
                INSERT INTO skills_triggers (agent_id, trigger_phrase, match_type)
                VALUES (%s, %s, 'semantic')
            """, (skill_id, trigger_phrase))

        # Insert command
        command = skill_data.get('command', {})
        if command and command.get('type'):
            cur.execute("""
                INSERT INTO skills_commands (
                    agent_id,
                    command_type,
                    script_content,
                    prerequisites
                ) VALUES (%s, %s, %s, %s)
            """, (
                skill_id,
                command['type'],
                command.get('content'),
                json.dumps(command.get('prerequisites')) if command.get('prerequisites') else None
            ))

        conn.commit()
        cur.close()

        return (True, f"✅ Imported: {agent_name} (ID: {skill_id})")

    except Exception as e:
        conn.rollback()
        return (False, f"❌ Failed to import {agent_name}: {e}")


def import_skills(args):
    """
    Main function to import skills.

    Returns:
        int: 0 on success, 1 on failure
    """
    # Read JSON file
    try:
        with open(args.json_file, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {args.json_file}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}", file=sys.stderr)
        return 1

    # Validate format
    if 'skills' not in import_data:
        print(f"❌ Invalid format: missing 'skills' array", file=sys.stderr)
        return 1

    skills = import_data['skills']
    print(f"\nFound {len(skills)} skill(s) in import file")
    print(f"Export version: {import_data.get('version', 'unknown')}")
    print(f"Exported at: {import_data.get('exported_at', 'unknown')}\n")

    if args.dry_run:
        print("(--dry-run mode - previewing only)\n")
        for skill in skills:
            print(f"Would import: {skill['agent_name']}")
            print(f"  Display: {skill['display_name']}")
            print(f"  Category: {skill['category']}")
            print(f"  Triggers: {len(skill.get('triggers', []))}")
            print()
        return 0

    # Import skills
    conn = get_db_connection()

    success_count = 0
    skip_count = 0
    fail_count = 0

    print(f"{'='*80}")
    print(f"Importing Skills...")
    print(f"{'='*80}\n")

    for i, skill_data in enumerate(skills, 1):
        print(f"[{i}/{len(skills)}] ", end='')

        success, message = import_single_skill(
            conn,
            skill_data,
            skip_existing=args.skip_existing,
            overwrite=args.overwrite
        )

        print(message)

        if success:
            if '⏭️' in message:
                skip_count += 1
            else:
                success_count += 1
        else:
            fail_count += 1

    # Summary
    print(f"\n{'='*80}")
    print(f"Import Summary:")
    print(f"  Imported: {success_count}")
    if skip_count > 0:
        print(f"  Skipped: {skip_count}")
    if fail_count > 0:
        print(f"  Failed: {fail_count}")
    print(f"{'='*80}")

    conn.close()

    return 0 if fail_count == 0 else 1


def main():
    parser = argparse.ArgumentParser(
        description='Import skills from JSON export file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import skills from file
  python3 import-skill.py backup.json

  # Skip skills that already exist
  python3 import-skill.py all-skills.json --skip-existing

  # Overwrite existing skills
  python3 import-skill.py database-skills.json --overwrite

  # Preview import without making changes
  python3 import-skill.py skills.json --dry-run

Notes:
  - Default behavior fails if skill already exists
  - Use --skip-existing to skip duplicates
  - Use --overwrite to replace existing skills
  - Imported skills will have new IDs
  - Performance history is not imported
        """
    )

    parser.add_argument('json_file',
                        help='JSON file to import')

    parser.add_argument('--skip-existing',
                        action='store_true',
                        help='Skip skills that already exist')
    parser.add_argument('--overwrite',
                        action='store_true',
                        help='Overwrite existing skills')
    parser.add_argument('--dry-run',
                        action='store_true',
                        help='Preview import without making changes')

    args = parser.parse_args()

    # Validate that only one conflict resolution strategy is specified
    if args.skip_existing and args.overwrite:
        parser.error("Cannot specify both --skip-existing and --overwrite")

    # Import skills
    exit_code = import_skills(args)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
