#!/usr/bin/env python3
"""
Claude Memory - Skills System: Skill Editing Tool

Edit existing skills - update metadata, triggers, scripts, and configuration.

Usage:
    python3 edit-skill.py <skill_name> --description "New description"
    python3 edit-skill.py <skill_name> --add-trigger "new trigger phrase"
    python3 edit-skill.py <skill_name> --remove-trigger "old trigger"
    python3 edit-skill.py <skill_name> --script-content "new script"
    python3 edit-skill.py --id 5 --category database

Arguments:
    skill_name                  Skill name (e.g., "check-db-health")
    --id ID                     Edit by skill ID instead of name
    --display-name NAME         Update display name
    --description DESC          Update description
    --category CATEGORY         Update category
    --script-content CONTENT    Update script content
    --add-trigger TRIGGER       Add new trigger phrase
    --remove-trigger TRIGGER    Remove trigger phrase
    --dry-run                   Preview changes without applying them
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


def get_triggers(conn, skill_id):
    """Fetch all triggers for a skill."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT id, trigger_phrase, match_type
        FROM skills_triggers
        WHERE agent_id = %s
        ORDER BY trigger_phrase
    """, (skill_id,))
    triggers = cur.fetchall()
    cur.close()
    return [dict(t) for t in triggers]


def get_command(conn, skill_id):
    """Fetch command for a skill."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT * FROM skills_commands
        WHERE agent_id = %s
    """, (skill_id,))
    command = cur.fetchone()
    cur.close()
    return dict(command) if command else None


def update_skill_metadata(conn, skill_id, updates):
    """
    Update skill metadata fields.

    Args:
        conn: Database connection
        skill_id: Skill ID
        updates: Dict of field:value pairs to update

    Returns:
        bool: Success
    """
    if not updates:
        return True

    try:
        cur = conn.cursor()

        # Build UPDATE query dynamically
        set_clauses = []
        values = []

        for field, value in updates.items():
            set_clauses.append(f"{field} = %s")
            values.append(value)

        values.append(skill_id)

        query = f"""
            UPDATE skills_agents
            SET {', '.join(set_clauses)},
                updated_at = NOW()
            WHERE id = %s
        """

        cur.execute(query, values)
        conn.commit()
        cur.close()

        return True

    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to update metadata: {e}", file=sys.stderr)
        return False


def update_script_content(conn, skill_id, new_content):
    """
    Update script content in skills_commands.

    Args:
        conn: Database connection
        skill_id: Skill ID
        new_content: New script content

    Returns:
        bool: Success
    """
    try:
        cur = conn.cursor()

        cur.execute("""
            UPDATE skills_commands
            SET script_content = %s,
                updated_at = NOW()
            WHERE agent_id = %s
        """, (new_content, skill_id))

        affected = cur.rowcount
        conn.commit()
        cur.close()

        return affected > 0

    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to update script: {e}", file=sys.stderr)
        return False


def add_trigger(conn, skill_id, trigger_phrase):
    """
    Add new trigger phrase to skill.

    Args:
        conn: Database connection
        skill_id: Skill ID
        trigger_phrase: New trigger phrase

    Returns:
        bool: Success
    """
    try:
        cur = conn.cursor()

        # Check if trigger already exists
        cur.execute("""
            SELECT id FROM skills_triggers
            WHERE agent_id = %s AND trigger_phrase = %s
        """, (skill_id, trigger_phrase))

        if cur.fetchone():
            print(f"⚠️  Trigger '{trigger_phrase}' already exists")
            cur.close()
            return False

        # Insert new trigger
        cur.execute("""
            INSERT INTO skills_triggers (agent_id, trigger_phrase, match_type)
            VALUES (%s, %s, 'semantic')
        """, (skill_id, trigger_phrase))

        conn.commit()
        cur.close()

        print(f"✅ Added trigger: '{trigger_phrase}'")
        return True

    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to add trigger: {e}", file=sys.stderr)
        return False


def remove_trigger(conn, skill_id, trigger_phrase):
    """
    Remove trigger phrase from skill.

    Args:
        conn: Database connection
        skill_id: Skill ID
        trigger_phrase: Trigger phrase to remove

    Returns:
        bool: Success
    """
    try:
        cur = conn.cursor()

        # Check how many triggers exist
        cur.execute("""
            SELECT COUNT(*) FROM skills_triggers
            WHERE agent_id = %s AND is_active = TRUE
        """, (skill_id,))

        count = cur.fetchone()[0]

        if count <= 1:
            print(f"❌ Cannot remove last trigger (skill must have at least one)", file=sys.stderr)
            cur.close()
            return False

        # Delete trigger
        cur.execute("""
            DELETE FROM skills_triggers
            WHERE agent_id = %s AND trigger_phrase = %s
        """, (skill_id, trigger_phrase))

        affected = cur.rowcount
        conn.commit()
        cur.close()

        if affected > 0:
            print(f"✅ Removed trigger: '{trigger_phrase}'")
            return True
        else:
            print(f"⚠️  Trigger '{trigger_phrase}' not found")
            return False

    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to remove trigger: {e}", file=sys.stderr)
        return False


def show_changes_preview(skill, args):
    """Show what changes will be made."""
    print(f"\n{'='*80}")
    print(f"Preview of Changes to: {skill['agent_name']}")
    print(f"{'='*80}\n")

    changes_made = False

    if args.display_name:
        print(f"Display Name:")
        print(f"  Before: {skill['display_name']}")
        print(f"  After:  {args.display_name}\n")
        changes_made = True

    if args.description:
        print(f"Description:")
        print(f"  Before: {skill['description'][:80]}...")
        print(f"  After:  {args.description[:80]}...\n")
        changes_made = True

    if args.category:
        print(f"Category:")
        print(f"  Before: {skill['category']}")
        print(f"  After:  {args.category}\n")
        changes_made = True

    if args.add_trigger:
        print(f"Add Trigger:")
        print(f"  New: '{args.add_trigger}'\n")
        changes_made = True

    if args.remove_trigger:
        print(f"Remove Trigger:")
        print(f"  Delete: '{args.remove_trigger}'\n")
        changes_made = True

    if args.script_content:
        print(f"Script Content:")
        print(f"  Will be updated ({len(args.script_content)} characters)\n")
        changes_made = True

    if not changes_made:
        print("⚠️  No changes specified")
        return False

    return True


def edit_skill(args):
    """
    Main function to edit a skill.

    Returns:
        int: 0 on success, 1 on failure
    """
    conn = get_db_connection()

    try:
        # Get skill
        if args.id:
            skill = get_skill_by_id(conn, args.id)
            if not skill:
                print(f"❌ Skill with ID {args.id} not found", file=sys.stderr)
                conn.close()
                return 1
        else:
            skill = get_skill_by_name(conn, args.skill_name)
            if not skill:
                print(f"❌ Skill '{args.skill_name}' not found", file=sys.stderr)
                conn.close()
                return 1

        # Show preview
        if not show_changes_preview(skill, args):
            conn.close()
            return 1

        if args.dry_run:
            print("(--dry-run mode, no changes made)")
            conn.close()
            return 0

        # Confirm changes
        response = input("\nApply these changes? (yes/no): ")
        if response.lower() != 'yes':
            print("Changes cancelled")
            conn.close()
            return 1

        print(f"\nApplying changes...")

        # Update metadata
        metadata_updates = {}
        if args.display_name:
            metadata_updates['display_name'] = args.display_name
        if args.description:
            metadata_updates['description'] = args.description
        if args.category:
            metadata_updates['category'] = args.category

        if metadata_updates:
            if update_skill_metadata(conn, skill['id'], metadata_updates):
                print(f"✅ Metadata updated")
            else:
                print(f"❌ Failed to update metadata")

        # Update script
        if args.script_content:
            if update_script_content(conn, skill['id'], args.script_content):
                print(f"✅ Script content updated")
            else:
                print(f"❌ Failed to update script")

        # Add trigger
        if args.add_trigger:
            add_trigger(conn, skill['id'], args.add_trigger)

        # Remove trigger
        if args.remove_trigger:
            remove_trigger(conn, skill['id'], args.remove_trigger)

        print(f"\n{'='*80}")
        print(f"✅ Skill '{skill['agent_name']}' updated successfully")
        print(f"{'='*80}")

        conn.close()
        return 0

    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        conn.close()
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='Edit existing skill',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update description
  python3 edit-skill.py check-db-health --description "Comprehensive database health check"

  # Change category
  python3 edit-skill.py backup-claude-memory --category backup

  # Update script content
  python3 edit-skill.py check-db-health --script-content "#!/bin/bash\necho 'New script'"

  # Add trigger phrase
  python3 edit-skill.py check-db-health --add-trigger "is database ok"

  # Remove trigger phrase
  python3 edit-skill.py check-db-health --remove-trigger "verify database status"

  # Multiple changes at once
  python3 edit-skill.py check-db-health \
    --display-name "DB Health Monitor" \
    --add-trigger "monitor database"

  # Edit by ID
  python3 edit-skill.py --id 2 --description "Updated description"

  # Preview changes without applying
  python3 edit-skill.py check-db-health --description "New desc" --dry-run
        """
    )

    # Skill identifier
    parser.add_argument('skill_name', nargs='?',
                        help='Skill name (e.g., "check-db-health")')
    parser.add_argument('--id', type=int,
                        help='Skill ID instead of name')

    # Metadata updates
    parser.add_argument('--display-name',
                        help='Update display name')
    parser.add_argument('--description',
                        help='Update description')
    parser.add_argument('--category',
                        help='Update category')

    # Script update
    parser.add_argument('--script-content',
                        help='Update script content')

    # Trigger management
    parser.add_argument('--add-trigger',
                        help='Add new trigger phrase')
    parser.add_argument('--remove-trigger',
                        help='Remove trigger phrase')

    # Options
    parser.add_argument('--dry-run',
                        action='store_true',
                        help='Preview changes without applying them')

    args = parser.parse_args()

    # Validate input
    if not args.skill_name and not args.id:
        parser.error("Either skill_name or --id must be provided")

    # Check that at least one update is specified
    has_updates = any([
        args.display_name,
        args.description,
        args.category,
        args.script_content,
        args.add_trigger,
        args.remove_trigger
    ])

    if not has_updates:
        parser.error("At least one update must be specified")

    # Edit skill
    exit_code = edit_skill(args)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
