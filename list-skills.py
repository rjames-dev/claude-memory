#!/usr/bin/env python3
"""
Claude Memory - Skills System: Skill Listing Tool

Lists all skills with filtering, sorting, and multiple output formats.

Usage:
    python3 list-skills.py                           # List all active skills
    python3 list-skills.py --category database       # Filter by category
    python3 list-skills.py --scope global            # Filter by scope
    python3 list-skills.py --sort success_rate       # Sort by success rate
    python3 list-skills.py --format json             # Output as JSON
    python3 list-skills.py --show-inactive           # Include inactive skills

Arguments:
    --category CATEGORY     Filter by category (git, database, scaffolding, etc.)
    --scope SCOPE           Filter by scope (global or project)
    --project-path PATH     Filter by specific project path
    --sort FIELD            Sort by field (name, success_rate, use_count, last_used)
    --format FORMAT         Output format (table, json, compact)
    --show-inactive         Include inactive skills (default: active only)
    --limit N               Limit results to N skills
"""

import sys
import os
import argparse
import json
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# Use standardized database utilities
from db_utils import get_db_connection


def build_filter_query(args):
    """
    Build SQL WHERE clause based on filter arguments.

    Returns:
        tuple: (where_clause, params)
    """
    conditions = []
    params = []

    # Active/inactive filter
    if not args.show_inactive:
        conditions.append("sa.is_active = TRUE")

    # Category filter
    if args.category:
        conditions.append("sa.category = %s")
        params.append(args.category)

    # Scope filter
    if args.scope:
        conditions.append("sa.scope = %s")
        params.append(args.scope)

    # Project path filter
    if args.project_path:
        conditions.append("sa.project_path = %s")
        params.append(args.project_path)

    where_clause = " AND ".join(conditions) if conditions else "TRUE"
    return where_clause, params


def get_sort_field(sort_arg):
    """
    Map sort argument to SQL field.

    Valid sorts: name, success_rate, use_count, last_used, created
    """
    sort_mapping = {
        'name': 'sa.agent_name',
        'success_rate': 'sa.success_rate DESC',
        'use_count': 'sa.use_count DESC',
        'last_used': 'sa.last_used DESC NULLS LAST',
        'created': 'sa.created_at DESC'
    }

    return sort_mapping.get(sort_arg, 'sa.agent_name')


def list_skills(args):
    """
    List skills with optional filtering and sorting.

    Returns:
        list: List of skill dictionaries
    """
    conn = get_db_connection()

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Build query
        where_clause, params = build_filter_query(args)
        sort_field = get_sort_field(args.sort)

        query = f"""
            SELECT
                sa.id,
                sa.agent_name,
                sa.display_name,
                sa.description,
                sa.category,
                sa.scope,
                sa.project_path,

                -- Performance metrics
                sa.use_count,
                sa.success_count,
                sa.failure_count,
                sa.success_rate,
                sa.avg_time_saved_ms,
                sa.total_time_saved_ms,
                sa.total_time_saved_ms / 1000 / 60 AS total_time_saved_minutes,

                -- Recency
                sa.last_used,
                sa.created_at,
                sa.updated_at,

                -- Metadata
                sa.version,
                sa.confidence_score,
                sa.is_active,
                sa.created_by,

                -- Trigger count
                COUNT(DISTINCT st.id) AS trigger_count,

                -- Status categorization
                CASE
                    WHEN sa.use_count >= 10 AND sa.success_rate >= 90 THEN 'stable'
                    WHEN sa.use_count < 5 THEN 'new'
                    WHEN sa.success_rate < 70 THEN 'needs_improvement'
                    ELSE 'developing'
                END AS status_category

            FROM skills_agents sa
            LEFT JOIN skills_triggers st ON st.agent_id = sa.id AND st.is_active = TRUE
            WHERE {where_clause}
            GROUP BY sa.id
            ORDER BY {sort_field}
        """

        if args.limit:
            query += f" LIMIT {int(args.limit)}"

        cur.execute(query, params)
        skills = cur.fetchall()

        cur.close()
        conn.close()

        return [dict(skill) for skill in skills]

    except psycopg2.Error as e:
        print(f"❌ Database error: {e}", file=sys.stderr)
        conn.close()
        sys.exit(1)


def format_table(skills):
    """Format skills as a table."""
    if not skills:
        print("No skills found.")
        return

    # Header
    print("\n" + "="*120)
    print(f"{'ID':<4} {'Name':<25} {'Category':<15} {'Uses':<6} {'Success':<8} {'Status':<12} {'Triggers':<8}")
    print("="*120)

    # Rows
    for skill in skills:
        print(
            f"{skill['id']:<4} "
            f"{skill['agent_name']:<25} "
            f"{skill['category'] or 'N/A':<15} "
            f"{skill['use_count']:<6} "
            f"{skill['success_rate']:.1f}%".ljust(8) + " "
            f"{skill['status_category']:<12} "
            f"{skill['trigger_count']:<8}"
        )

    print("="*120)
    print(f"Total: {len(skills)} skill(s)\n")


def format_compact(skills):
    """Format skills in compact view."""
    if not skills:
        print("No skills found.")
        return

    for skill in skills:
        status_icon = {
            'stable': '✅',
            'new': '🆕',
            'developing': '🔄',
            'needs_improvement': '⚠️'
        }.get(skill['status_category'], '❓')

        print(f"{status_icon} {skill['agent_name']}")
        print(f"   ID: {skill['id']} | Category: {skill['category']} | Uses: {skill['use_count']} | Success: {skill['success_rate']:.1f}%")
        if skill['description']:
            print(f"   {skill['description']}")
        print()


def format_json(skills):
    """Format skills as JSON."""
    # Convert datetime objects to ISO format strings
    for skill in skills:
        for key in ['last_used', 'created_at', 'updated_at']:
            if skill.get(key):
                skill[key] = skill[key].isoformat()

    print(json.dumps(skills, indent=2, default=str))


def format_detailed(skills):
    """Format skills with full details."""
    if not skills:
        print("No skills found.")
        return

    for i, skill in enumerate(skills):
        if i > 0:
            print("\n" + "-"*80 + "\n")

        print(f"ID: {skill['id']}")
        print(f"Name: {skill['agent_name']}")
        print(f"Display Name: {skill['display_name'] or 'N/A'}")
        print(f"Description: {skill['description'] or 'N/A'}")
        print(f"Category: {skill['category'] or 'N/A'}")
        print(f"Scope: {skill['scope']}")

        if skill['project_path']:
            print(f"Project: {skill['project_path']}")

        print(f"\nPerformance:")
        print(f"  Uses: {skill['use_count']}")
        print(f"  Successes: {skill['success_count']}")
        print(f"  Failures: {skill['failure_count']}")
        print(f"  Success Rate: {skill['success_rate']:.1f}%")
        print(f"  Status: {skill['status_category']}")

        if skill['total_time_saved_minutes']:
            print(f"  Time Saved: {skill['total_time_saved_minutes']:.1f} minutes")

        print(f"\nMetadata:")
        print(f"  Version: {skill['version']}")
        print(f"  Confidence: {skill['confidence_score']}")
        print(f"  Active: {'Yes' if skill['is_active'] else 'No'}")
        print(f"  Created By: {skill['created_by']}")
        print(f"  Created: {skill['created_at']}")
        print(f"  Last Used: {skill['last_used'] or 'Never'}")
        print(f"  Triggers: {skill['trigger_count']}")


def main():
    parser = argparse.ArgumentParser(
        description='List skills in the Skills System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all active skills (default table format)
  python3 list-skills.py

  # Filter by category
  python3 list-skills.py --category database

  # Filter by scope
  python3 list-skills.py --scope global

  # Sort by success rate
  python3 list-skills.py --sort success_rate

  # Show top 5 most used skills
  python3 list-skills.py --sort use_count --limit 5

  # Output as JSON
  python3 list-skills.py --format json

  # Show all skills including inactive
  python3 list-skills.py --show-inactive

  # Detailed view of database skills
  python3 list-skills.py --category database --format detailed
        """
    )

    # Filter arguments
    parser.add_argument('--category',
                        help='Filter by category (git, database, scaffolding, etc.)')
    parser.add_argument('--scope',
                        choices=['global', 'project'],
                        help='Filter by scope (global or project)')
    parser.add_argument('--project-path',
                        help='Filter by specific project path')
    parser.add_argument('--show-inactive',
                        action='store_true',
                        help='Include inactive skills (default: active only)')

    # Sorting arguments
    parser.add_argument('--sort',
                        choices=['name', 'success_rate', 'use_count', 'last_used', 'created'],
                        default='name',
                        help='Sort field (default: name)')

    # Output arguments
    parser.add_argument('--format',
                        choices=['table', 'json', 'compact', 'detailed'],
                        default='table',
                        help='Output format (default: table)')
    parser.add_argument('--limit',
                        type=int,
                        help='Limit results to N skills')

    args = parser.parse_args()

    # Get skills
    skills = list_skills(args)

    # Format output
    if args.format == 'table':
        format_table(skills)
    elif args.format == 'json':
        format_json(skills)
    elif args.format == 'compact':
        format_compact(skills)
    elif args.format == 'detailed':
        format_detailed(skills)


if __name__ == '__main__':
    main()
