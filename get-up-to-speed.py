#!/usr/bin/env python3
"""
Get Up to Speed - Project Onboarding Skill

Provides comprehensive onboarding for fresh Claude instances by analyzing
project history, stats, and available tools. Generates actionable guide
formatted for quick orientation.

Usage:
    python3 get-up-to-speed.py
    python3 get-up-to-speed.py --project-path /path/to/project

This skill addresses the "15-minute brute force onboarding" problem
identified in real-world testing (2025-12-27 onboarding exercise).

Author: Claude Sonnet 4.5
Created: 2025-12-28
Status: Development
"""

import sys
import json
import os
import argparse
from datetime import datetime, timedelta
from db_utils import get_db_connection


def normalize_project_path(cur, hint=None):
    """
    Normalize project path using fuzzy matching.

    Priority:
    1. Explicit hint argument
    2. Current working directory basename match
    3. Most recent project in database

    Args:
        cur: Database cursor
        hint: Optional path hint

    Returns:
        str: Normalized project path
    """
    # If explicit hint provided
    if hint:
        return hint

    # Get current directory
    cwd = os.getcwd()
    cwd_basename = os.path.basename(cwd)

    # Query database for all project paths
    cur.execute("SELECT DISTINCT project_path FROM context_snapshots WHERE project_path IS NOT NULL")
    db_paths = [row[0] for row in cur.fetchall()]

    if not db_paths:
        # No projects in database
        return cwd

    # Fuzzy match: basename appears in path
    matches = [p for p in db_paths if cwd_basename in p]

    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        # Multiple matches: use most recent
        cur.execute('''
            SELECT project_path
            FROM context_snapshots
            WHERE project_path = ANY(%s)
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (matches,))
        result = cur.fetchone()
        return result[0] if result else cwd
    else:
        # No matches: try exact match
        if cwd in db_paths:
            return cwd

        # Last resort: most recent project in database
        cur.execute('''
            SELECT project_path
            FROM context_snapshots
            ORDER BY timestamp DESC
            LIMIT 1
        ''')
        result = cur.fetchone()
        return result[0] if result else cwd


def collect_project_stats(cur, project_path):
    """
    Collect high-level project statistics.

    Args:
        cur: Database cursor
        project_path: Normalized project path

    Returns:
        dict: Project overview stats
    """
    cur.execute('''
        SELECT
            COUNT(*) as total_snapshots,
            AVG(quality_score)::numeric(3,1) as avg_quality,
            COUNT(*) FILTER (WHERE quality_score >= 8) as high_quality_count,
            MAX(pst_time) as last_activity,
            COUNT(DISTINCT session_id) FILTER (WHERE session_id IS NOT NULL) as tracked_sessions
        FROM v_snapshot_quality
        WHERE project_path = %s
    ''', (project_path,))

    row = cur.fetchone()

    if not row or row[0] == 0:
        return {
            "total_snapshots": 0,
            "avg_quality": 0.0,
            "high_quality_count": 0,
            "last_activity": None,
            "tracked_sessions": 0,
            "project_exists": False
        }

    return {
        "total_snapshots": row[0],
        "avg_quality": float(row[1]) if row[1] else 0.0,
        "high_quality_count": row[2],
        "last_activity": row[3].isoformat() if row[3] else None,
        "tracked_sessions": row[4],
        "project_exists": True
    }


def collect_timeline(cur, project_path, limit=10):
    """
    Collect recent snapshots timeline.

    Args:
        cur: Database cursor
        project_path: Project path
        limit: Number of recent snapshots

    Returns:
        list: Recent snapshot summaries
    """
    cur.execute('''
        SELECT
            cs.id,
            sq.pst_time,
            sq.message_count,
            sq.tag_count,
            sq.file_count,
            sq.quality_score,
            LEFT(cs.summary, 100) as summary_preview
        FROM v_snapshot_quality sq
        JOIN context_snapshots cs ON cs.id = sq.id
        WHERE sq.project_path = %s
        ORDER BY sq.pst_time DESC
        LIMIT %s
    ''', (project_path, limit))

    results = []
    for row in cur.fetchall():
        results.append({
            "id": row[0],
            "timestamp": row[1].isoformat() if row[1] else None,
            "message_count": row[2],
            "tag_count": row[3],
            "file_count": row[4],
            "quality_score": float(row[5]) if row[5] else 0.0,
            "summary_preview": row[6]
        })

    return results


def collect_tag_cloud(cur, project_path, limit=10):
    """
    Collect tag frequency for topic analysis.

    Args:
        cur: Database cursor
        project_path: Project path
        limit: Number of top tags

    Returns:
        list: Tag frequency tuples
    """
    cur.execute('''
        SELECT
            unnest(tags) as tag,
            COUNT(*) as frequency
        FROM context_snapshots
        WHERE project_path = %s AND tags IS NOT NULL
        GROUP BY tag
        ORDER BY frequency DESC
        LIMIT %s
    ''', (project_path, limit))

    return [(row[0], row[1]) for row in cur.fetchall()]


def collect_file_heatmap(cur, project_path, limit=10):
    """
    Collect file activity heatmap.

    Args:
        cur: Database cursor
        project_path: Project path
        limit: Number of top files

    Returns:
        list: File mention tuples
    """
    # Try v_file_heatmap view first
    try:
        cur.execute('''
            SELECT
                file_path,
                mention_count
            FROM v_file_heatmap
            WHERE %s = ANY(mentioned_in_projects)
            ORDER BY mention_count DESC
            LIMIT %s
        ''', (project_path, limit))

        results = cur.fetchall()
        if results:
            return [(row[0], row[1]) for row in results]
    except:
        # View doesn't exist, fallback
        pass

    # Fallback: aggregate from mentioned_files
    cur.execute('''
        SELECT
            unnest(mentioned_files) as file_path,
            COUNT(*) as mention_count
        FROM context_snapshots
        WHERE project_path = %s AND mentioned_files IS NOT NULL
        GROUP BY file_path
        ORDER BY mention_count DESC
        LIMIT %s
    ''', (project_path, limit))

    return [(row[0], row[1]) for row in cur.fetchall()]


def collect_enhancement_opportunities(cur, project_path):
    """
    Identify low-quality snapshots worth enhancing.

    Args:
        cur: Database cursor
        project_path: Project path

    Returns:
        list: Enhancement opportunity dicts with cost estimates
    """
    cur.execute('''
        SELECT
            id,
            message_count,
            quality_score,
            summary_length
        FROM v_snapshot_quality
        WHERE project_path = %s
          AND quality_score < 8
          AND message_count > 100
        ORDER BY message_count DESC
        LIMIT 5
    ''', (project_path,))

    results = []
    for row in cur.fetchall():
        # Cost estimate: ~$0.15-0.25 per enhancement
        # Based on 200k context window usage
        estimated_cost = 0.20  # Average

        results.append({
            "snapshot_id": row[0],
            "message_count": row[1],
            "quality_score": float(row[2]) if row[2] else 0.0,
            "summary_length": row[3],
            "estimated_cost": estimated_cost
        })

    return results


def collect_available_tools():
    """
    Collect available MCP tools and slash commands.

    Returns:
        dict: Tool inventory
    """
    tools = {
        "mcp_search_tools": [],
        "slash_commands": [],
        "skills_count": 0
    }

    # List MCP search tools (hardcoded for now - could introspect .claude config)
    tools["mcp_search_tools"] = [
        "search_memory - Semantic search of summaries",
        "search_raw_messages - Full-text search of conversations",
        "get_timeline - Chronological project history",
        "get_snapshot - Detailed snapshot retrieval",
        "search_agent_work - Agent task history"
    ]

    # Count slash commands in .claude/commands/
    commands_dir = os.path.join(os.getcwd(), '.claude', 'commands')
    if os.path.exists(commands_dir):
        slash_files = [f for f in os.listdir(commands_dir) if f.startswith('mem-') and f.endswith('.md')]
        tools["slash_commands"] = [f.replace('.md', '').replace('mem-', '/mem-') for f in slash_files]

    return tools


def format_output_for_display(data):
    """
    Format collected data as JSON for agent consumption.

    For now, just pretty-print the JSON. The agent spawn
    integration will be added in a future iteration.

    Args:
        data: Collected project data

    Returns:
        str: Formatted output
    """
    stats = data["stats"]
    project_name = os.path.basename(data["project_path"])

    output = []
    output.append("╔══════════════════════════════════════════════════════════════╗")
    output.append("║         🎯 Project Onboarding - Get Up to Speed             ║")
    output.append("╚══════════════════════════════════════════════════════════════╝")
    output.append("")

    if not stats["project_exists"]:
        output.append(f"⚠️  No data found for project: {project_name}")
        output.append("")
        output.append("This could mean:")
        output.append("  • No snapshots have been captured yet")
        output.append("  • Project path mismatch")
        output.append("")
        output.append("Try running: /mem-capture")
        return "\n".join(output)

    # Project Overview
    output.append(f"📊 Project: {project_name}")
    output.append(f"   Path: {data['project_path']}")
    output.append("")
    output.append("=== Project Statistics ===")
    output.append(f"Total Snapshots: {stats['total_snapshots']}")
    output.append(f"Average Quality: {stats['avg_quality']}/10")
    output.append(f"High Quality (≥8): {stats['high_quality_count']}")
    output.append(f"Tracked Sessions: {stats['tracked_sessions']}")
    if stats['last_activity']:
        last_date = datetime.fromisoformat(stats['last_activity']).strftime('%Y-%m-%d %H:%M')
        output.append(f"Last Activity: {last_date}")
    output.append("")

    # Timeline
    if data["timeline"]:
        output.append("=== Recent Activity (Top 5) ===")
        for snap in data["timeline"][:5]:
            snap_date = datetime.fromisoformat(snap['timestamp']).astimezone().strftime('%Y-%m-%d')
            output.append(f"Snapshot #{snap['id']} ({snap_date}) - Quality: {snap['quality_score']}/10")
            output.append(f"  Messages: {snap['message_count']}, Tags: {snap['tag_count']}, Files: {snap['file_count']}")
            if snap['summary_preview']:
                output.append(f"  Preview: {snap['summary_preview']}...")
        output.append("")

    # Tag Cloud
    if data["tags"]:
        output.append("=== Common Topics ===")
        for tag, freq in data["tags"][:10]:
            output.append(f"  🏷️  {tag} ({freq} mentions)")
        output.append("")

    # File Activity
    if data["files"]:
        output.append("=== Active Files ===")
        for file_path, mentions in data["files"][:10]:
            output.append(f"  📄 {file_path} ({mentions} mentions)")
        output.append("")

    # Enhancement Opportunities
    if data["enhancements"]:
        output.append("=== Enhancement Opportunities ===")
        output.append(f"Found {len(data['enhancements'])} low-quality snapshots worth enhancing:")
        total_cost = sum(e['estimated_cost'] for e in data['enhancements'])
        for enh in data["enhancements"]:
            output.append(f"  Snapshot #{enh['snapshot_id']}: {enh['message_count']} msgs, quality {enh['quality_score']}/10")
            output.append(f"    Cost: ~${enh['estimated_cost']:.2f}")
        output.append(f"Total enhancement cost: ~${total_cost:.2f}")
        output.append("")
        output.append("To enhance: /mem-enhance-summary <snapshot_id>")
        output.append("")

    # Available Tools
    output.append("=== Available Tools ===")
    if data["tools"]["mcp_search_tools"]:
        output.append("MCP Search Tools:")
        for tool in data["tools"]["mcp_search_tools"]:
            output.append(f"  • {tool}")
        output.append("")

    if data["tools"]["slash_commands"]:
        output.append(f"Slash Commands ({len(data['tools']['slash_commands'])}):")
        for cmd in data["tools"]["slash_commands"]:
            output.append(f"  • {cmd}")
        output.append("")

    # Next Steps
    output.append("=== 📋 Next Steps ===")
    if stats['high_quality_count'] > 0:
        output.append("1. Review high-quality snapshots for context")
        output.append("2. Search memory for specific topics")
    if data["enhancements"]:
        output.append("3. Enhance low-quality snapshots for better searchability")
    output.append("4. Use MCP search tools to explore project history")
    output.append("")

    return "\n".join(output)


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(
        description='Get comprehensive project onboarding',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-detect project from current directory
  python3 get-up-to-speed.py

  # Specify project explicitly
  python3 get-up-to-speed.py --project-path /Users/alice/Code/my-project
        """
    )
    parser.add_argument(
        '--project-path',
        help='Explicit project path (default: auto-detect from current directory)'
    )

    args = parser.parse_args()

    # Connect to database
    try:
        conn = get_db_connection()
        cur = conn.cursor()
    except SystemExit:
        return 1

    # Step 1: Normalize project path
    print("🔍 Detecting project...")
    project_path = normalize_project_path(cur, hint=args.project_path)
    print(f"✅ Analyzing: {os.path.basename(project_path)}")
    print("")

    # Step 2: Collect all data
    print("📊 Collecting project data...")
    data = {
        "project_path": project_path,
        "stats": collect_project_stats(cur, project_path),
        "timeline": collect_timeline(cur, project_path),
        "tags": collect_tag_cloud(cur, project_path),
        "files": collect_file_heatmap(cur, project_path),
        "enhancements": collect_enhancement_opportunities(cur, project_path),
        "tools": collect_available_tools()
    }
    print("✅ Data collection complete")
    print("")

    # Step 3: Format and display
    output = format_output_for_display(data)
    print(output)

    cur.close()
    conn.close()

    return 0


if __name__ == '__main__':
    sys.exit(main())
