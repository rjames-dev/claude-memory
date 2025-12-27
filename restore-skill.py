#!/usr/bin/env python3
"""
Claude Memory - Skills System: Skill Restoration Tool

Restore soft-deleted skills (skills marked as is_active=FALSE).

Usage:
    python3 restore-skill.py <skill_name>      # Restore by name
    python3 restore-skill.py --id 5            # Restore by ID
    python3 restore-skill.py --list            # List all soft-deleted skills
    python3 restore-skill.py --all             # Restore all soft-deleted skills

Arguments:
    skill_name          Skill name (e.g., "old-skill")
    --id ID             Restore by skill ID instead of name
    --list              List all soft-deleted skills without restoring
    --all               Restore all soft-deleted skills
    --force             Skip confirmation prompt
"""

import sys
import os
import argparse
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


def get_inactive_skill_by_name(conn, skill_name):
    """Fetch inactive skill by name."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT * FROM skills_agents
        WHERE agent_name = %s AND is_active = FALSE
    """, (skill_name,))
    skill = cur.fetchone()
    cur.close()
    return dict(skill) if skill else None


def get_inactive_skill_by_id(conn, skill_id):
    """Fetch inactive skill by ID."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT * FROM skills_agents
        WHERE id = %s AND is_active = FALSE
    """, (skill_id,))
    skill = cur.fetchone()
    cur.close()
    return dict(skill) if skill else None


def list_inactive_skills(conn):
    """List all soft-deleted skills."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT
            id,
            agent_name,
            display_name,
            category,
            use_count,
            success_rate,
            updated_at
        FROM skills_agents
        WHERE is_active = FALSE
        ORDER BY updated_at DESC
    """)
    skills = cur.fetchall()
    cur.close()
    return [dict(s) for s in skills]


def restore_skill(conn, skill_id):
    """
    Restore soft-deleted skill.

    Sets is_active=TRUE for skill and all related triggers/commands.

    Args:
        conn: Database connection
        skill_id: Skill ID

    Returns:
        bool: Success
    """
    try:
        cur = conn.cursor()

        # Restore skill
        cur.execute("""
            UPDATE skills_agents
            SET is_active = TRUE,
                updated_at = NOW()
            WHERE id = %s
        """, (skill_id,))

        # Restore triggers
        cur.execute("""
            UPDATE skills_triggers
            SET is_active = TRUE
            WHERE agent_id = %s
        """, (skill_id,))

        # Restore commands
        cur.execute("""
            UPDATE skills_commands
            SET is_active = TRUE
            WHERE agent_id = %s
        """, (skill_id,))

        conn.commit()
        cur.close()

        return True

    except Exception as e:
        conn.rollback()
        print(f"❌ Database error: {e}", file=sys.stderr)
        return False


def confirm_restore(skill):
    """Prompt user for restore confirmation."""
    print(f"\n⚠️  You are about to restore:")
    print(f"   ID: {skill['id']}")
    print(f"   Name: {skill['agent_name']}")
    print(f"   Display: {skill['display_name']}")
    print(f"   Category: {skill['category']}")
    print(f"   Uses: {skill['use_count']}")
    print(f"   Success Rate: {skill['success_rate']:.1f}%")
    print(f"\n   This will mark the skill as active.")

    response = input(f"\nType 'yes' to confirm restore: ")
    return response.lower() == 'yes'


def display_inactive_skills(skills):
    """Display list of inactive skills."""
    if not skills:
        print("\n✅ No soft-deleted skills found")
        return

    print(f"\n{'='*80}")
    print(f"Soft-Deleted Skills ({len(skills)} total)")
    print(f"{'='*80}\n")

    for skill in skills:
        print(f"ID: {skill['id']}")
        print(f"  Name: {skill['agent_name']}")
        print(f"  Display: {skill['display_name']}")
        print(f"  Category: {skill['category']}")
        print(f"  Usage: {skill['use_count']} executions, {skill['success_rate']:.1f}% success")
        print(f"  Deleted: {skill['updated_at']}")
        print()


def restore_skills(args):
    """
    Main function to restore skills.

    Returns:
        int: 0 on success, 1 on failure
    """
    conn = get_db_connection()

    try:
        # List mode
        if args.list:
            skills = list_inactive_skills(conn)
            display_inactive_skills(skills)
            conn.close()
            return 0

        # Restore all mode
        if args.all:
            skills = list_inactive_skills(conn)

            if not skills:
                print("\n✅ No soft-deleted skills found")
                conn.close()
                return 0

            print(f"\nFound {len(skills)} soft-deleted skill(s):")
            for skill in skills:
                print(f"  - {skill['agent_name']} (ID: {skill['id']})")

            if not args.force:
                response = input(f"\nRestore all {len(skills)} skills? (yes/no): ")
                if response.lower() != 'yes':
                    print("Restore cancelled")
                    conn.close()
                    return 1

            # Restore all
            restored_count = 0
            failed_count = 0

            for skill in skills:
                if restore_skill(conn, skill['id']):
                    print(f"✅ Restored: {skill['agent_name']}")
                    restored_count += 1
                else:
                    print(f"❌ Failed: {skill['agent_name']}")
                    failed_count += 1

            print(f"\n{'='*80}")
            print(f"Restore Summary:")
            print(f"  Restored: {restored_count}")
            if failed_count > 0:
                print(f"  Failed: {failed_count}")
            print(f"{'='*80}")

            conn.close()
            return 0 if failed_count == 0 else 1

        # Single skill restore
        if args.id:
            skill = get_inactive_skill_by_id(conn, args.id)
            if not skill:
                print(f"❌ No inactive skill with ID {args.id}", file=sys.stderr)
                conn.close()
                return 1
        else:
            skill = get_inactive_skill_by_name(conn, args.skill_name)
            if not skill:
                print(f"❌ No inactive skill named '{args.skill_name}'", file=sys.stderr)
                print(f"   Use --list to see all soft-deleted skills", file=sys.stderr)
                conn.close()
                return 1

        # Confirm restore
        if not args.force:
            if not confirm_restore(skill):
                print("Restore cancelled")
                conn.close()
                return 1

        # Restore skill
        if restore_skill(conn, skill['id']):
            print(f"\n✅ Skill '{skill['agent_name']}' restored successfully")
            conn.close()
            return 0
        else:
            print(f"\n❌ Failed to restore skill", file=sys.stderr)
            conn.close()
            return 1

    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        conn.close()
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='Restore soft-deleted skills',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all soft-deleted skills
  python3 restore-skill.py --list

  # Restore by name
  python3 restore-skill.py old-skill

  # Restore by ID
  python3 restore-skill.py --id 5

  # Restore without confirmation
  python3 restore-skill.py old-skill --force

  # Restore all soft-deleted skills
  python3 restore-skill.py --all
        """
    )

    # Skill identifier
    parser.add_argument('skill_name', nargs='?',
                        help='Skill name (e.g., "old-skill")')
    parser.add_argument('--id', type=int,
                        help='Skill ID instead of name')

    # Options
    parser.add_argument('--list',
                        action='store_true',
                        help='List all soft-deleted skills')
    parser.add_argument('--all',
                        action='store_true',
                        help='Restore all soft-deleted skills')
    parser.add_argument('--force',
                        action='store_true',
                        help='Skip confirmation prompt')

    args = parser.parse_args()

    # Validate input
    if not args.list and not args.all and not args.skill_name and not args.id:
        parser.error("Either skill_name, --id, --list, or --all must be provided")

    # Restore skill(s)
    exit_code = restore_skills(args)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
