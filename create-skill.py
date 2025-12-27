#!/usr/bin/env python3
"""
Claude Memory - Skills System: Skill Creation Tool

Creates a new skill manually with triggers and execution definition.

Usage:
    python3 create-skill.py --name "check-db-health" \
                             --display-name "Database Health Check" \
                             --category "database" \
                             --description "Checks PostgreSQL database health" \
                             --command-type "bash_script" \
                             --script-content "#!/bin/bash\necho 'Hello'" \
                             --triggers "check db,verify database" \
                             [--project-path "/path/to/project"] \
                             [--confidence 0.8]

Arguments:
    --name              Skill name (kebab-case, e.g., "git-commit-protocol")
    --display-name      Human-friendly name (e.g., "Git Commit Protocol")
    --category          Category (git, database, scaffolding, file-ops, etc.)
    --description       What this skill does (1-2 sentences)
    --command-type      bash_script, tool_sequence, or agent_spawn
    --script-content    Bash script content (for bash_script type)
    --triggers          Comma-separated trigger phrases
    --project-path      Optional: project path (NULL = global)
    --confidence        Optional: confidence score 0-1 (default: 0.8)
    --parameters        Optional: JSON parameters definition
    --prerequisites     Optional: JSON prerequisites definition
"""

import sys
import os
import argparse
import re
import json
from pathlib import Path
import psycopg2
from psycopg2.extras import Json

# Use standardized database utilities
from db_utils import get_db_connection

def validate_skill_name(name):
    """
    Validate skill name format.

    Rules:
    - kebab-case (lowercase with hyphens)
    - alphanumeric and hyphens only
    - must start with letter
    - 3-50 characters
    """
    if not name:
        return False, "Skill name is required"

    if len(name) < 3 or len(name) > 50:
        return False, "Skill name must be 3-50 characters"

    if not re.match(r'^[a-z][a-z0-9-]*$', name):
        return False, "Skill name must be kebab-case (lowercase letters, numbers, hyphens only)"

    if name.startswith('-') or name.endswith('-') or '--' in name:
        return False, "Invalid hyphen placement in skill name"

    return True, None


def check_duplicate_skill(conn, skill_name):
    """Check if skill name already exists."""
    cur = conn.cursor()
    cur.execute(
        "SELECT id, agent_name FROM skills_agents WHERE agent_name = %s",
        (skill_name,)
    )
    existing = cur.fetchone()
    cur.close()

    if existing:
        return True, existing[0]
    return False, None


def validate_confidence(confidence):
    """Validate confidence score is between 0 and 1."""
    try:
        conf = float(confidence)
        if 0 <= conf <= 1:
            return True, conf
        return False, "Confidence must be between 0 and 1"
    except ValueError:
        return False, "Confidence must be a number"


def create_skill(args):
    """
    Create a new skill in the database.

    Returns:
        int: skill_id if successful, None if failed
    """
    # Validate skill name
    valid, error = validate_skill_name(args.name)
    if not valid:
        print(f"❌ Invalid skill name: {error}", file=sys.stderr)
        return None

    # Validate confidence if provided
    if args.confidence:
        valid, result = validate_confidence(args.confidence)
        if not valid:
            print(f"❌ Invalid confidence: {result}", file=sys.stderr)
            return None
        confidence = result
    else:
        confidence = 0.8  # Default

    # Parse parameters and prerequisites if provided
    parameters = {}
    prerequisites = {}

    if args.parameters:
        try:
            parameters = json.loads(args.parameters)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid parameters JSON: {e}", file=sys.stderr)
            return None

    if args.prerequisites:
        try:
            prerequisites = json.loads(args.prerequisites)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid prerequisites JSON: {e}", file=sys.stderr)
            return None

    # Connect to database
    conn = get_db_connection()

    try:
        # Check for duplicates
        is_duplicate, existing_id = check_duplicate_skill(conn, args.name)
        if is_duplicate:
            print(f"❌ Skill '{args.name}' already exists (ID: {existing_id})", file=sys.stderr)
            print(f"   Use a different name or delete the existing skill first", file=sys.stderr)
            conn.close()
            return None

        cur = conn.cursor()

        # Insert skill into skills_agents
        cur.execute("""
            INSERT INTO skills_agents (
                agent_name,
                display_name,
                description,
                category,
                scope,
                project_path,
                confidence_score,
                created_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, agent_name, created_at
        """, (
            args.name,
            args.display_name,
            args.description,
            args.category,
            'global' if not args.project_path else 'project',
            args.project_path,
            confidence,
            'user'
        ))

        skill_id, skill_name, created_at = cur.fetchone()
        print(f"✅ Skill created: {skill_name} (ID: {skill_id})")
        print(f"   Created: {created_at}")

        # Insert triggers
        triggers = [t.strip() for t in args.triggers.split(',') if t.strip()]
        if not triggers:
            print(f"⚠️  Warning: No triggers specified", file=sys.stderr)
        else:
            trigger_ids = []
            for trigger_phrase in triggers:
                cur.execute("""
                    INSERT INTO skills_triggers (
                        agent_id,
                        trigger_phrase,
                        match_type,
                        confidence_threshold
                    ) VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (
                    skill_id,
                    trigger_phrase,
                    'exact',  # Phase 1: exact matching only
                    1.0
                ))
                trigger_ids.append(cur.fetchone()[0])

            print(f"   Triggers: {len(triggers)} added")
            for i, phrase in enumerate(triggers):
                print(f"     - \"{phrase}\" (ID: {trigger_ids[i]})")

        # Insert command definition
        if args.command_type == 'bash_script':
            if not args.script_content:
                print(f"❌ --script-content required for bash_script type", file=sys.stderr)
                conn.rollback()
                cur.close()
                conn.close()
                return None

            cur.execute("""
                INSERT INTO skills_commands (
                    agent_id,
                    command_type,
                    script_content,
                    parameters,
                    prerequisites
                ) VALUES (%s, %s, %s, %s, %s)
                RETURNING id, length(script_content) as script_length
            """, (
                skill_id,
                'bash_script',
                args.script_content,
                Json(parameters),
                Json(prerequisites)
            ))

            cmd_id, script_length = cur.fetchone()
            print(f"   Command: bash_script (ID: {cmd_id}, {script_length} chars)")
            print(f"   Script stored in database ✅")

        elif args.command_type == 'tool_sequence':
            # Phase 2 feature - placeholder for now
            print(f"⚠️  tool_sequence not yet implemented (Phase 2)", file=sys.stderr)
            print(f"   Creating skill without command definition", file=sys.stderr)

        elif args.command_type == 'agent_spawn':
            # Phase 2 feature - placeholder for now
            print(f"⚠️  agent_spawn not yet implemented (Phase 2)", file=sys.stderr)
            print(f"   Creating skill without command definition", file=sys.stderr)

        else:
            print(f"❌ Invalid command type: {args.command_type}", file=sys.stderr)
            print(f"   Supported: bash_script (tool_sequence, agent_spawn in Phase 2)", file=sys.stderr)
            conn.rollback()
            cur.close()
            conn.close()
            return None

        # Commit transaction
        conn.commit()

        print(f"\n✅ Skill '{skill_name}' created successfully!")
        print(f"\n📋 Summary:")
        print(f"   ID: {skill_id}")
        print(f"   Name: {skill_name}")
        print(f"   Display: {args.display_name}")
        print(f"   Category: {args.category}")
        print(f"   Scope: {'Global' if not args.project_path else f'Project: {args.project_path}'}")
        print(f"   Type: {args.command_type}")
        print(f"   Triggers: {len(triggers)}")
        print(f"   Confidence: {confidence}")

        cur.close()
        conn.close()

        return skill_id

    except psycopg2.Error as e:
        conn.rollback()
        print(f"❌ Database error: {e}", file=sys.stderr)
        conn.close()
        return None
    except Exception as e:
        conn.rollback()
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        conn.close()
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Create a new skill in the Skills System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a simple bash script skill
  python3 create-skill.py \\
    --name "check-db-health" \\
    --display-name "Database Health Check" \\
    --category "database" \\
    --description "Checks PostgreSQL database health" \\
    --command-type "bash_script" \\
    --script-content "#!/bin/bash\\npsql -c 'SELECT version();'" \\
    --triggers "check db health,verify database"

  # Create a project-specific skill
  python3 create-skill.py \\
    --name "nlq-deploy" \\
    --display-name "Deploy NLQ" \\
    --category "deployment" \\
    --description "Deploy NLQ to staging" \\
    --command-type "bash_script" \\
    --script-content "#!/bin/bash\\ndocker-compose up -d" \\
    --triggers "deploy nlq,deploy to staging" \\
    --project-path "/path/to/NLQ"
        """
    )

    # Required arguments
    parser.add_argument('--name', required=True,
                        help='Skill name in kebab-case (e.g., check-db-health)')
    parser.add_argument('--display-name', required=True,
                        help='Human-friendly display name')
    parser.add_argument('--category', required=True,
                        help='Category: git, database, scaffolding, file-ops, etc.')
    parser.add_argument('--description', required=True,
                        help='What this skill does (1-2 sentences)')
    parser.add_argument('--command-type', required=True,
                        choices=['bash_script', 'tool_sequence', 'agent_spawn'],
                        help='Execution type (only bash_script in Phase 1)')
    parser.add_argument('--triggers', required=True,
                        help='Comma-separated trigger phrases')

    # Optional arguments
    parser.add_argument('--script-content',
                        help='Bash script content (required for bash_script type)')
    parser.add_argument('--project-path',
                        help='Project path for project-specific skills (default: global)')
    parser.add_argument('--confidence', type=float, default=0.8,
                        help='Confidence score 0-1 (default: 0.8)')
    parser.add_argument('--parameters',
                        help='JSON parameters definition')
    parser.add_argument('--prerequisites',
                        help='JSON prerequisites definition')

    args = parser.parse_args()

    # Create skill
    skill_id = create_skill(args)

    if skill_id:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
