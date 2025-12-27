#!/usr/bin/env python3
"""
Claude Memory - Skills System: Skill Information Tool

Displays comprehensive information about a specific skill.

Usage:
    python3 skill-info.py <skill_name>          # By name
    python3 skill-info.py --id <skill_id>       # By ID
    python3 skill-info.py <skill_name> --json   # JSON output
    python3 skill-info.py <skill_name> --show-script  # Include full script

Arguments:
    skill_name              Skill name (e.g., "check-db-health")
    --id ID                 Skill ID instead of name
    --format FORMAT         Output format (text, json)
    --show-script          Show full script content (default: first 500 chars)
    --show-logs N          Show last N execution logs (default: 5)
"""

import sys
import os
import argparse
import json
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

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


def get_skill_triggers(conn, skill_id):
    """Fetch all triggers for a skill."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT
            id,
            trigger_phrase,
            match_type,
            confidence_threshold,
            is_active,
            created_at
        FROM skills_triggers
        WHERE agent_id = %s
        ORDER BY created_at
    """, (skill_id,))
    triggers = cur.fetchall()
    cur.close()
    return [dict(t) for t in triggers]


def get_skill_command(conn, skill_id):
    """Fetch command definition for a skill."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT
            id,
            command_type,
            script_content,
            command_definition,
            agent_config,
            parameters,
            prerequisites,
            created_at
        FROM skills_commands
        WHERE agent_id = %s
    """, (skill_id,))
    command = cur.fetchone()
    cur.close()
    return dict(command) if command else None


def get_performance_logs(conn, skill_id, limit=5):
    """Fetch recent performance logs for a skill."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT
            id,
            outcome,
            time_saved_ms,
            execution_time_ms,
            error_message,
            executed_at,
            user_request,
            matched_trigger_id,
            similarity_score,
            session_id,
            project_path,
            user_feedback,
            was_suggestion_accepted
        FROM skills_performance_log
        WHERE agent_id = %s
        ORDER BY executed_at DESC
        LIMIT %s
    """, (skill_id, limit))
    logs = cur.fetchall()
    cur.close()
    return [dict(log) for log in logs]


def format_skill_info_text(skill, triggers, command, logs, args):
    """Format skill information as text."""
    print("\n" + "="*80)
    print(f"SKILL INFORMATION: {skill['agent_name']}")
    print("="*80)

    # Basic Information
    print("\n📋 BASIC INFORMATION")
    print(f"   ID: {skill['id']}")
    print(f"   Name: {skill['agent_name']}")
    print(f"   Display Name: {skill['display_name'] or 'N/A'}")
    print(f"   Description: {skill['description'] or 'N/A'}")
    print(f"   Category: {skill['category'] or 'N/A'}")
    print(f"   Scope: {skill['scope']}")
    if skill['project_path']:
        print(f"   Project Path: {skill['project_path']}")

    # Status
    status_category = None
    if skill['use_count'] >= 10 and skill['success_rate'] >= 90:
        status_category = 'stable'
        status_icon = '✅'
    elif skill['use_count'] < 5:
        status_category = 'new'
        status_icon = '🆕'
    elif skill['success_rate'] < 70:
        status_category = 'needs_improvement'
        status_icon = '⚠️'
    else:
        status_category = 'developing'
        status_icon = '🔄'

    print(f"   Status: {status_icon} {status_category}")
    print(f"   Active: {'Yes' if skill['is_active'] else 'No'}")
    print(f"   Created By: {skill['created_by']}")
    print(f"   Version: {skill['version']}")

    # Performance Metrics
    print("\n📊 PERFORMANCE METRICS")
    print(f"   Total Uses: {skill['use_count']}")
    print(f"   Successes: {skill['success_count']}")
    print(f"   Failures: {skill['failure_count']}")
    print(f"   Success Rate: {skill['success_rate']:.1f}%")
    print(f"   Confidence Score: {skill['confidence_score']}")

    if skill['avg_time_saved_ms']:
        avg_time_sec = skill['avg_time_saved_ms'] / 1000
        print(f"   Avg Time Saved: {avg_time_sec:.2f} seconds")

    if skill['total_time_saved_ms']:
        total_time_min = skill['total_time_saved_ms'] / 1000 / 60
        print(f"   Total Time Saved: {total_time_min:.2f} minutes")

    # Timestamps
    print("\n🕐 TIMESTAMPS")
    print(f"   Created: {skill['created_at']}")
    print(f"   Updated: {skill['updated_at']}")
    print(f"   Last Used: {skill['last_used'] or 'Never'}")

    # Triggers
    print(f"\n🎯 TRIGGERS ({len(triggers)})")
    if triggers:
        for i, trigger in enumerate(triggers, 1):
            active_marker = "✓" if trigger['is_active'] else "✗"
            print(f"   {i}. [{active_marker}] \"{trigger['trigger_phrase']}\"")
            print(f"      Type: {trigger['match_type']} | Confidence: {trigger['confidence_threshold']}")
    else:
        print("   No triggers configured")

    # Command Definition
    if command:
        print(f"\n⚙️  COMMAND DEFINITION")
        print(f"   Type: {command['command_type']}")
        print(f"   Command ID: {command['id']}")

        if command['command_type'] == 'bash_script' and command['script_content']:
            script_length = len(command['script_content'])
            print(f"   Script Length: {script_length} characters")

            if args.show_script:
                print(f"\n   Script Content:")
                print("   " + "-"*76)
                for line in command['script_content'].split('\n'):
                    print(f"   {line}")
                print("   " + "-"*76)
            else:
                preview = command['script_content'][:500]
                if len(command['script_content']) > 500:
                    preview += "\n   ... (truncated, use --show-script for full content)"
                print(f"\n   Script Preview:")
                print("   " + "-"*76)
                for line in preview.split('\n'):
                    print(f"   {line}")
                print("   " + "-"*76)

        # Parameters
        if command['parameters']:
            print(f"\n   Parameters:")
            for key, value in command['parameters'].items():
                print(f"      {key}: {value}")

        # Prerequisites
        if command['prerequisites']:
            print(f"\n   Prerequisites:")
            for key, value in command['prerequisites'].items():
                print(f"      {key}: {value}")

        print(f"\n   Created: {command['created_at']}")
    else:
        print(f"\n⚙️  COMMAND DEFINITION")
        print("   No command configured")

    # Performance Logs
    if logs:
        print(f"\n📜 RECENT EXECUTION HISTORY (Last {len(logs)})")
        for i, log in enumerate(logs, 1):
            outcome_icon = "✅" if log['outcome'] == 'success' else "❌"
            print(f"\n   {i}. {outcome_icon} {log['outcome'].upper()} - {log['executed_at']}")

            if log['execution_time_ms']:
                exec_time_sec = log['execution_time_ms'] / 1000
                print(f"      Execution Time: {exec_time_sec:.2f} seconds")

            if log['time_saved_ms']:
                time_saved_sec = log['time_saved_ms'] / 1000
                print(f"      Time Saved: {time_saved_sec:.2f} seconds")

            if log['user_request']:
                request_preview = log['user_request'][:100]
                if len(log['user_request']) > 100:
                    request_preview += "..."
                print(f"      Request: {request_preview}")

            if log['similarity_score']:
                print(f"      Match Score: {log['similarity_score']:.2f}")

            if log['error_message']:
                print(f"      Error: {log['error_message']}")

            if log['user_feedback']:
                print(f"      Feedback: {log['user_feedback']}")

            if log['session_id']:
                print(f"      Session: {log['session_id']}")
    else:
        print(f"\n📜 RECENT EXECUTION HISTORY")
        print("   No execution history")

    print("\n" + "="*80 + "\n")


def format_skill_info_json(skill, triggers, command, logs):
    """Format skill information as JSON."""
    # Convert datetime objects to ISO format
    for key in ['created_at', 'updated_at', 'last_used']:
        if skill.get(key):
            skill[key] = skill[key].isoformat()

    for trigger in triggers:
        if trigger.get('created_at'):
            trigger['created_at'] = trigger['created_at'].isoformat()

    if command:
        for key in ['created_at', 'updated_at']:
            if command.get(key):
                command[key] = command[key].isoformat()

    for log in logs:
        if log.get('executed_at'):
            log['executed_at'] = log['executed_at'].isoformat()

    result = {
        'skill': skill,
        'triggers': triggers,
        'command': command,
        'performance_logs': logs
    }

    print(json.dumps(result, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(
        description='Display detailed information about a specific skill',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show skill by name
  python3 skill-info.py check-db-health

  # Show skill by ID
  python3 skill-info.py --id 2

  # Show full script content
  python3 skill-info.py check-db-health --show-script

  # Show last 10 execution logs
  python3 skill-info.py check-db-health --show-logs 10

  # Output as JSON
  python3 skill-info.py check-db-health --format json
        """
    )

    # Positional or named skill identifier
    parser.add_argument('skill_name', nargs='?',
                        help='Skill name (e.g., "check-db-health")')
    parser.add_argument('--id', type=int,
                        help='Skill ID instead of name')

    # Output options
    parser.add_argument('--format',
                        choices=['text', 'json'],
                        default='text',
                        help='Output format (default: text)')
    parser.add_argument('--show-script',
                        action='store_true',
                        help='Show full script content (default: preview only)')
    parser.add_argument('--show-logs',
                        type=int,
                        default=5,
                        help='Number of execution logs to show (default: 5)')

    args = parser.parse_args()

    # Validate input
    if not args.skill_name and not args.id:
        parser.error("Either skill_name or --id must be provided")

    # Connect to database
    conn = get_db_connection()

    try:
        # Fetch skill
        if args.id:
            skill = get_skill_by_id(conn, args.id)
            if not skill:
                print(f"❌ Skill with ID {args.id} not found", file=sys.stderr)
                sys.exit(1)
        else:
            skill = get_skill_by_name(conn, args.skill_name)
            if not skill:
                print(f"❌ Skill '{args.skill_name}' not found", file=sys.stderr)
                sys.exit(1)

        # Fetch related data
        triggers = get_skill_triggers(conn, skill['id'])
        command = get_skill_command(conn, skill['id'])
        logs = get_performance_logs(conn, skill['id'], args.show_logs)

        conn.close()

        # Format output
        if args.format == 'json':
            format_skill_info_json(skill, triggers, command, logs)
        else:
            format_skill_info_text(skill, triggers, command, logs, args)

    except psycopg2.Error as e:
        print(f"❌ Database error: {e}", file=sys.stderr)
        conn.close()
        sys.exit(1)


if __name__ == '__main__':
    main()
