#!/usr/bin/env python3
"""
Claude Memory - Skills System: Skill Export Tool

Export skills to JSON format for backup and sharing.

Usage:
    python3 export-skill.py <skill_name> -o skill.json
    python3 export-skill.py --all -o all-skills.json
    python3 export-skill.py --category database -o db-skills.json
    python3 export-skill.py --id 5 -o skill-5.json

Arguments:
    skill_name              Skill name (e.g., "check-db-health")
    --id ID                 Export by skill ID instead of name
    --all                   Export all active skills
    --category CATEGORY     Export all skills in category
    -o, --output FILE       Output JSON file (default: stdout)
    --pretty                Pretty-print JSON output
"""

import sys
import os
import argparse
import json
from datetime import datetime
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
    cur.execute("SELECT * FROM skills_agents WHERE agent_name = %s", (skill_name,))
    skill = cur.fetchone()
    cur.close()
    return dict(skill) if skill else None


def get_skill_by_id(conn, skill_id):
    """Fetch skill by ID."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM skills_agents WHERE id = %s", (skill_id,))
    skill = cur.fetchone()
    cur.close()
    return dict(skill) if skill else None


def get_all_skills(conn):
    """Fetch all active skills."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM skills_agents WHERE is_active = TRUE ORDER BY agent_name")
    skills = cur.fetchall()
    cur.close()
    return [dict(s) for s in skills]


def get_skills_by_category(conn, category):
    """Fetch skills by category."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT * FROM skills_agents WHERE category = %s AND is_active = TRUE ORDER BY agent_name",
        (category,)
    )
    skills = cur.fetchall()
    cur.close()
    return [dict(s) for s in skills]


def get_triggers(conn, skill_id):
    """Fetch all triggers for a skill."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT trigger_phrase, match_type, confidence_threshold
        FROM skills_triggers
        WHERE agent_id = %s AND is_active = TRUE
        ORDER BY trigger_phrase
    """, (skill_id,))
    triggers = cur.fetchall()
    cur.close()
    return [dict(t) for t in triggers]


def get_command(conn, skill_id):
    """Fetch command for a skill."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT command_type, script_content, prerequisites
        FROM skills_commands
        WHERE agent_id = %s AND is_active = TRUE
    """, (skill_id,))
    command = cur.fetchone()
    cur.close()
    return dict(command) if command else None


def export_skill_data(conn, skill):
    """
    Export complete skill data including triggers and command.

    Args:
        conn: Database connection
        skill: Skill record

    Returns:
        dict: Complete skill export data
    """
    triggers = get_triggers(conn, skill['id'])
    command = get_command(conn, skill['id'])

    # Build export object
    export_data = {
        'agent_name': skill['agent_name'],
        'display_name': skill['display_name'],
        'description': skill['description'],
        'category': skill['category'],
        'scope': skill['scope'],
        'project_path': skill['project_path'],
        'triggers': [t['trigger_phrase'] for t in triggers],
        'command': {
            'type': command['command_type'] if command else None,
            'content': command['script_content'] if command else None,
            'prerequisites': command['prerequisites'] if command else None
        },
        'metadata': {
            'use_count': skill['use_count'],
            'success_rate': skill['success_rate'],
            'created_at': skill['created_at'].isoformat() if skill['created_at'] else None,
            'updated_at': skill['updated_at'].isoformat() if skill['updated_at'] else None
        }
    }

    return export_data


def export_skills(args):
    """
    Main function to export skills.

    Returns:
        int: 0 on success, 1 on failure
    """
    conn = get_db_connection()

    try:
        # Get skills to export
        skills_to_export = []

        if args.all:
            skills = get_all_skills(conn)
            if not skills:
                print("❌ No active skills found", file=sys.stderr)
                conn.close()
                return 1
            skills_to_export = skills
            print(f"Exporting all {len(skills)} active skills...")

        elif args.category:
            skills = get_skills_by_category(conn, args.category)
            if not skills:
                print(f"❌ No active skills in category '{args.category}'", file=sys.stderr)
                conn.close()
                return 1
            skills_to_export = skills
            print(f"Exporting {len(skills)} skills in category '{args.category}'...")

        elif args.id:
            skill = get_skill_by_id(conn, args.id)
            if not skill:
                print(f"❌ Skill with ID {args.id} not found", file=sys.stderr)
                conn.close()
                return 1
            skills_to_export = [skill]
            print(f"Exporting skill: {skill['agent_name']}...")

        else:
            skill = get_skill_by_name(conn, args.skill_name)
            if not skill:
                print(f"❌ Skill '{args.skill_name}' not found", file=sys.stderr)
                conn.close()
                return 1
            skills_to_export = [skill]
            print(f"Exporting skill: {skill['agent_name']}...")

        # Export skills
        exported_skills = []
        for skill in skills_to_export:
            export_data = export_skill_data(conn, skill)
            exported_skills.append(export_data)

        # Build final export object
        export_object = {
            'version': '1.0',
            'exported_at': datetime.now().isoformat(),
            'exported_by': 'claude-memory-skills-system',
            'skill_count': len(exported_skills),
            'skills': exported_skills
        }

        # Output JSON
        if args.pretty:
            json_output = json.dumps(export_object, indent=2, ensure_ascii=False)
        else:
            json_output = json.dumps(export_object, ensure_ascii=False)

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"✅ Exported {len(exported_skills)} skill(s) to: {args.output}")
        else:
            print(json_output)

        conn.close()
        return 0

    except Exception as e:
        print(f"❌ Export failed: {e}", file=sys.stderr)
        conn.close()
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='Export skills to JSON format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export single skill
  python3 export-skill.py check-db-health -o check-db-health.json

  # Export all skills
  python3 export-skill.py --all -o all-skills.json

  # Export by category
  python3 export-skill.py --category database -o database-skills.json

  # Export by ID
  python3 export-skill.py --id 5 -o skill-5.json

  # Export to stdout with pretty formatting
  python3 export-skill.py check-db-health --pretty

  # Export all skills with pretty formatting
  python3 export-skill.py --all --pretty -o skills-backup.json
        """
    )

    # Skill identifier
    parser.add_argument('skill_name', nargs='?',
                        help='Skill name (e.g., "check-db-health")')
    parser.add_argument('--id', type=int,
                        help='Skill ID instead of name')

    # Export options
    parser.add_argument('--all',
                        action='store_true',
                        help='Export all active skills')
    parser.add_argument('--category',
                        help='Export all skills in category')

    # Output options
    parser.add_argument('-o', '--output',
                        help='Output JSON file (default: stdout)')
    parser.add_argument('--pretty',
                        action='store_true',
                        help='Pretty-print JSON output')

    args = parser.parse_args()

    # Validate input
    if not args.skill_name and not args.id and not args.all and not args.category:
        parser.error("Either skill_name, --id, --all, or --category must be provided")

    # Export skills
    exit_code = export_skills(args)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
