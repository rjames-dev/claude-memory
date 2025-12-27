#!/usr/bin/env python3
"""
Claude Memory - Skills System: Skill Deletion Tool

Deletes skills from the database (soft or hard delete).

Usage:
    python3 delete-skill.py <skill_name>              # Soft delete with confirmation
    python3 delete-skill.py --id <skill_id>           # Delete by ID
    python3 delete-skill.py <skill_name> --hard       # Hard delete (removes from DB)
    python3 delete-skill.py <skill_name> --force      # Skip confirmation
    python3 delete-skill.py --pattern "test-*"        # Delete multiple by pattern

Arguments:
    skill_name              Skill name (e.g., "old-skill")
    --id ID                 Skill ID instead of name
    --pattern PATTERN       Delete multiple skills matching pattern
    --hard                  Hard delete (remove from database)
    --force                 Skip confirmation prompt
    --list-only             List matching skills without deleting
"""

import sys
import os
import argparse
import psycopg2
from psycopg2.extras import RealDictCursor
import fnmatch

# Database configuration (matches existing claude-memory scripts)
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


def get_skill_by_name(conn, skill_name):
    """Fetch skill by name."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT * FROM skills_agents
        WHERE agent_name = %s
    """, (skill_name,))
    skill = cur.fetchone()
    cur.close()
    return dict(skill) if skill else None


def get_skill_by_id(conn, skill_id):
    """Fetch skill by ID."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT * FROM skills_agents
        WHERE id = %s
    """, (skill_id,))
    skill = cur.fetchone()
    cur.close()
    return dict(skill) if skill else None


def get_skills_by_pattern(conn, pattern):
    """Fetch skills matching pattern."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT * FROM skills_agents
        ORDER BY agent_name
    """)
    all_skills = cur.fetchall()
    cur.close()

    # Filter using fnmatch
    matching_skills = [
        dict(skill) for skill in all_skills
        if fnmatch.fnmatch(skill['agent_name'], pattern)
    ]

    return matching_skills


def confirm_deletion(skill, hard_delete):
    """Prompt user for deletion confirmation."""
    delete_type = "HARD DELETE" if hard_delete else "soft delete"

    print(f"\n⚠️  WARNING: You are about to {delete_type}:")
    print(f"   ID: {skill['id']}")
    print(f"   Name: {skill['agent_name']}")
    print(f"   Display: {skill['display_name']}")
    print(f"   Category: {skill['category']}")
    print(f"   Uses: {skill['use_count']}")
    print(f"   Success Rate: {skill['success_rate']:.1f}%")

    if hard_delete:
        print(f"\n   This will PERMANENTLY remove:")
        print(f"   - Skill record")
        print(f"   - All triggers")
        print(f"   - Command definitions")
        print(f"   - Performance logs")
        print(f"\n   ⚠️  THIS CANNOT BE UNDONE!")
    else:
        print(f"\n   This will mark the skill as inactive.")
        print(f"   The skill can be restored later.")

    response = input(f"\nType 'yes' to confirm {delete_type}: ")
    return response.lower() == 'yes'


def soft_delete_skill(conn, skill_id):
    """
    Soft delete: Mark skill as inactive.

    Returns:
        bool: True if successful
    """
    try:
        cur = conn.cursor()

        # Mark skill as inactive
        cur.execute("""
            UPDATE skills_agents
            SET is_active = FALSE,
                updated_at = NOW()
            WHERE id = %s
        """, (skill_id,))

        # Also mark triggers as inactive
        cur.execute("""
            UPDATE skills_triggers
            SET is_active = FALSE
            WHERE agent_id = %s
        """, (skill_id,))

        # Mark commands as inactive
        cur.execute("""
            UPDATE skills_commands
            SET is_active = FALSE
            WHERE agent_id = %s
        """, (skill_id,))

        conn.commit()
        cur.close()

        return True

    except psycopg2.Error as e:
        conn.rollback()
        print(f"❌ Database error: {e}", file=sys.stderr)
        return False


def hard_delete_skill(conn, skill_id):
    """
    Hard delete: Remove skill and all related records from database.

    Manually deletes in order:
    1. skills_performance_log (no CASCADE)
    2. skills_triggers (has CASCADE)
    3. skills_commands (has CASCADE)
    4. skills_agents (parent table)

    Returns:
        bool: True if successful
    """
    try:
        cur = conn.cursor()

        # Delete performance logs first (FK doesn't have CASCADE)
        cur.execute("""
            DELETE FROM skills_performance_log
            WHERE agent_id = %s
        """, (skill_id,))

        # Delete triggers (has CASCADE but explicit for clarity)
        cur.execute("""
            DELETE FROM skills_triggers
            WHERE agent_id = %s
        """, (skill_id,))

        # Delete commands (has CASCADE but explicit for clarity)
        cur.execute("""
            DELETE FROM skills_commands
            WHERE agent_id = %s
        """, (skill_id,))

        # Finally delete skill record
        cur.execute("""
            DELETE FROM skills_agents
            WHERE id = %s
        """, (skill_id,))

        affected_rows = cur.rowcount

        conn.commit()
        cur.close()

        return affected_rows > 0

    except psycopg2.Error as e:
        conn.rollback()
        print(f"❌ Database error: {e}", file=sys.stderr)
        return False


def delete_skill(args):
    """
    Delete a skill (soft or hard delete).

    Returns:
        int: 0 on success, 1 on failure
    """
    conn = get_db_connection()

    try:
        # Get skills to delete
        skills_to_delete = []

        if args.pattern:
            # Pattern-based deletion
            skills_to_delete = get_skills_by_pattern(conn, args.pattern)

            if not skills_to_delete:
                print(f"❌ No skills match pattern '{args.pattern}'", file=sys.stderr)
                conn.close()
                return 1

            print(f"Found {len(skills_to_delete)} skill(s) matching pattern '{args.pattern}':")
            for skill in skills_to_delete:
                print(f"  - {skill['agent_name']} (ID: {skill['id']})")

            if args.list_only:
                print(f"\n(--list-only mode, no deletion performed)")
                conn.close()
                return 0

        elif args.id:
            # Delete by ID
            skill = get_skill_by_id(conn, args.id)
            if not skill:
                print(f"❌ Skill with ID {args.id} not found", file=sys.stderr)
                conn.close()
                return 1
            skills_to_delete = [skill]

        else:
            # Delete by name
            skill = get_skill_by_name(conn, args.skill_name)
            if not skill:
                print(f"❌ Skill '{args.skill_name}' not found", file=sys.stderr)
                conn.close()
                return 1
            skills_to_delete = [skill]

        # Confirm deletion (unless --force)
        if not args.force:
            if len(skills_to_delete) > 1:
                # Batch confirmation
                print(f"\n⚠️  WARNING: You are about to delete {len(skills_to_delete)} skills")
                delete_type = "HARD DELETE" if args.hard else "soft delete"
                response = input(f"Type 'yes' to confirm {delete_type} of all skills: ")
                if response.lower() != 'yes':
                    print("Deletion cancelled.")
                    conn.close()
                    return 1
            else:
                # Single skill confirmation
                if not confirm_deletion(skills_to_delete[0], args.hard):
                    print("Deletion cancelled.")
                    conn.close()
                    return 1

        # Perform deletion
        deleted_count = 0
        failed_count = 0

        for skill in skills_to_delete:
            if args.hard:
                success = hard_delete_skill(conn, skill['id'])
                action = "hard deleted"
            else:
                success = soft_delete_skill(conn, skill['id'])
                action = "soft deleted"

            if success:
                deleted_count += 1
                print(f"✅ {skill['agent_name']} {action}")
            else:
                failed_count += 1
                print(f"❌ Failed to delete {skill['agent_name']}")

        # Summary
        print(f"\n{'='*80}")
        print(f"Deletion Summary:")
        print(f"  Deleted: {deleted_count}")
        if failed_count > 0:
            print(f"  Failed: {failed_count}")
        print(f"{'='*80}")

        conn.close()

        return 0 if failed_count == 0 else 1

    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        conn.close()
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='Delete skills from the Skills System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Soft delete by name (mark inactive)
  python3 delete-skill.py old-skill

  # Hard delete by name (remove from database)
  python3 delete-skill.py old-skill --hard

  # Delete by ID
  python3 delete-skill.py --id 5

  # Delete without confirmation
  python3 delete-skill.py old-skill --force

  # Delete all test skills
  python3 delete-skill.py --pattern "test-*"

  # List matching skills without deleting
  python3 delete-skill.py --pattern "test-*" --list-only

  # Hard delete multiple test skills
  python3 delete-skill.py --pattern "test-integration-*" --hard --force
        """
    )

    # Positional or named skill identifier
    parser.add_argument('skill_name', nargs='?',
                        help='Skill name (e.g., "old-skill")')
    parser.add_argument('--id', type=int,
                        help='Skill ID instead of name')
    parser.add_argument('--pattern',
                        help='Delete multiple skills matching pattern (e.g., "test-*")')

    # Deletion options
    parser.add_argument('--hard',
                        action='store_true',
                        help='Hard delete (remove from database permanently)')
    parser.add_argument('--force',
                        action='store_true',
                        help='Skip confirmation prompt')
    parser.add_argument('--list-only',
                        action='store_true',
                        help='List matching skills without deleting (use with --pattern)')

    args = parser.parse_args()

    # Validate input
    if not args.skill_name and not args.id and not args.pattern:
        parser.error("Either skill_name, --id, or --pattern must be provided")

    if args.list_only and not args.pattern:
        parser.error("--list-only requires --pattern")

    # Delete skill
    exit_code = delete_skill(args)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
