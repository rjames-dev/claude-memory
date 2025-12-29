#!/usr/bin/env python3
"""
Skills Performance Analytics

Shows detailed performance statistics for the Skills System:
- Individual skill stats (uses, success rate, time saved)
- Recent performance trends (7-day, 30-day)
- Suggestion acceptance rates
- Project usage breakdown
- All skills summary by category

Usage:
    # Show stats for specific skill
    python3 skills-stats.py git-commit-protocol

    # Show all skills summary
    python3 skills-stats.py --all

    # Show skills in specific category
    python3 skills-stats.py --category git

    # Show top performers
    python3 skills-stats.py --top 10

    # Show detailed trend analysis
    python3 skills-stats.py git-commit-protocol --days 30
"""

import sys
import os
import argparse
import psycopg2
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import json

# ============================================================================
# Database Connection
# ============================================================================

def get_db_password():
    """Get database password from .env file or environment."""
    password = os.environ.get('CONTEXT_DB_PASSWORD')
    if password:
        return password

    # Try reading from .env file
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('CONTEXT_DB_PASSWORD='):
                    return line.strip().split('=', 1)[1]

    return 'memory_secure_2024'  # Fallback

def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=int(os.environ.get('DB_PORT', 5435)),
        database='claude_memory',
        user='memory_admin',
        password=get_db_password()
    )

# ============================================================================
# Formatting Utilities
# ============================================================================

def format_time_ms(ms):
    """Convert milliseconds to readable format."""
    if ms is None:
        return "N/A"

    seconds = ms / 1000

    if seconds < 1:
        return f"{ms:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"

def format_percentage(value):
    """Format a percentage value."""
    if value is None:
        return "N/A"
    return f"{value:.1f}%"

def truncate_path(path, max_length=50):
    """Truncate long paths for display."""
    if not path or len(path) <= max_length:
        return path or "(unknown)"

    # Show start and end
    half = (max_length - 3) // 2
    return f"{path[:half]}...{path[-half:]}"

# ============================================================================
# Individual Skill Statistics
# ============================================================================

def get_skill_stats(skill_name: str, days: int = 7):
    """Get detailed stats for a single skill."""

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Overall stats
        cur.execute("""
            SELECT
                id,
                agent_name,
                display_name,
                description,
                category,
                use_count,
                success_count,
                failure_count,
                success_rate,
                avg_time_saved_ms,
                total_time_saved_ms,
                confidence_score,
                last_used,
                created_at
            FROM skills_agents
            WHERE agent_name = %s
        """, (skill_name,))

        skill = cur.fetchone()
        if not skill:
            print(f"❌ Skill not found: {skill_name}")
            return None

        (skill_id, name, display, desc, category, uses, successes, failures,
         success_rate, avg_saved_ms, total_saved_ms, confidence, last_used,
         created) = skill

        # Recent performance (configurable days)
        cur.execute("""
            SELECT
                dates.date,
                COALESCE(COUNT(spl.id), 0) as executions,
                COALESCE(COUNT(spl.id) FILTER (WHERE spl.outcome = 'success'), 0) as successes,
                COALESCE(AVG(spl.execution_time_ms), 0) as avg_time_ms
            FROM generate_series(
                CURRENT_DATE - INTERVAL '%s days',
                CURRENT_DATE,
                '1 day'::interval
            ) as dates(date)
            LEFT JOIN skills_performance_log spl
                ON DATE(spl.executed_at) = dates.date
                AND spl.agent_id = %s
            GROUP BY dates.date
            ORDER BY dates.date DESC
        """, (days, skill_id))

        recent_perf = cur.fetchall()

        # Suggestion acceptance
        cur.execute("""
            SELECT
                COUNT(*) as total_suggestions,
                COUNT(*) FILTER (WHERE was_suggestion_accepted = TRUE) as accepted,
                COUNT(*) FILTER (WHERE was_suggestion_accepted = FALSE) as rejected
            FROM skills_performance_log
            WHERE agent_id = %s
              AND was_suggestion_accepted IS NOT NULL
        """, (skill_id,))

        suggestions = cur.fetchone()

        # Project usage
        cur.execute("""
            SELECT
                COALESCE(project_path, '(unknown)') as project,
                COUNT(*) as uses,
                AVG(execution_time_ms) as avg_time_ms
            FROM skills_performance_log
            WHERE agent_id = %s
            GROUP BY COALESCE(project_path, '(unknown)')
            ORDER BY uses DESC
            LIMIT 10
        """, (skill_id,))

        projects = cur.fetchall()

        # Last 10 executions
        cur.execute("""
            SELECT
                executed_at,
                outcome,
                execution_time_ms,
                project_path
            FROM skills_performance_log
            WHERE agent_id = %s
            ORDER BY executed_at DESC
            LIMIT 10
        """, (skill_id,))

        recent_execs = cur.fetchall()

        # Format output
        print()
        print(f"{'=' * 70}")
        print(f"{display or name} - Performance Statistics")
        print(f"{'=' * 70}")

        # Overall section
        print(f"\n📊 Overall:")
        print(f"  Total Uses: {uses}")
        print(f"  Success: {successes} ({format_percentage(success_rate)})")
        print(f"  Failed: {failures}")

        if avg_saved_ms and avg_saved_ms > 0:
            print(f"  Avg Time Saved: {format_time_ms(avg_saved_ms)}")
            print(f"  Total Time Saved: {format_time_ms(total_saved_ms)}")

        # Recent performance
        print(f"\n📈 Recent Performance (Last {days} days):")

        active_days = [p for p in recent_perf if p[1] > 0]  # Days with activity

        if active_days:
            for date, execs, succs, avg_time in active_days[:10]:  # Show up to 10 recent active days
                success_pct = (succs / execs * 100) if execs > 0 else 0
                print(f"  {date}: {execs} uses, {success_pct:.0f}% success, {format_time_ms(avg_time)} avg")
        else:
            print(f"  No activity in last {days} days")

        # Suggestion acceptance
        if suggestions:
            total_sug, accepted, rejected = suggestions
            if total_sug > 0:
                acceptance = (accepted / total_sug * 100)
                print(f"\n👍 User Acceptance:")
                print(f"  Suggested: {total_sug} times")
                print(f"  Accepted: {accepted} ({acceptance:.0f}%)")
                print(f"  Rejected: {rejected}")

        # Project usage
        if projects:
            print(f"\n📁 Usage by Project:")
            for project, count, avg_time in projects:
                proj_display = truncate_path(project, 60)
                print(f"  {proj_display}: {count} uses ({format_time_ms(avg_time)} avg)")

        # Recent executions
        if recent_execs:
            print(f"\n🕐 Last {min(10, len(recent_execs))} Executions:")
            for exec_time, outcome, duration_ms, project in recent_execs:
                status = "✅" if outcome == 'success' else "❌"
                proj_short = truncate_path(project, 30)
                print(f"  {exec_time.strftime('%Y-%m-%d %H:%M')}  {status} {outcome:15}  "
                      f"{format_time_ms(duration_ms):>7}  [{proj_short}]")

        # Metadata
        print(f"\nℹ️  Metadata:")
        print(f"  Category: {category}")
        print(f"  Confidence: {confidence:.2f}")
        print(f"  Created: {created.strftime('%Y-%m-%d')}")
        if last_used:
            last_used_local = last_used.astimezone()
            days_ago = (datetime.now(last_used_local.tzinfo) - last_used_local).days
            print(f"  Last Used: {last_used_local.strftime('%Y-%m-%d %H:%M')} ({days_ago} days ago)")

        if desc:
            print(f"\n📝 Description:")
            print(f"  {desc}")

        print()

        return {
            'skill_id': skill_id,
            'name': name,
            'display': display,
            'category': category,
            'uses': uses,
            'success_rate': success_rate
        }

    finally:
        cur.close()
        conn.close()

# ============================================================================
# All Skills Summary
# ============================================================================

def get_all_stats():
    """Get summary stats for all skills."""

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                category,
                agent_name,
                display_name,
                use_count,
                success_rate,
                total_time_saved_ms / 1000 / 60 as minutes_saved,
                last_used_pst
            FROM v_skills_dashboard
            WHERE use_count > 0
            ORDER BY category, use_count DESC
        """)

        skills = cur.fetchall()

        if not skills:
            print("\n📊 No skills with usage data found.")
            print("   Create and use some skills to see statistics here.\n")
            return

        # Group by category
        by_category = {}
        total_uses = 0
        total_time_saved = 0

        for cat, name, display, uses, success, minutes, last_used in skills:
            if cat not in by_category:
                by_category[cat] = []

            total_uses += uses
            total_time_saved += (minutes or 0)

            display_name = display or name
            last_used_str = last_used.astimezone().strftime('%Y-%m-%d') if last_used else 'Never'

            by_category[cat].append({
                'name': name,
                'display': display_name,
                'uses': uses,
                'success': success,
                'minutes': minutes or 0,
                'last_used': last_used_str
            })

        print()
        print(f"{'=' * 70}")
        print(f"📊 All Skills Performance Summary")
        print(f"{'=' * 70}")

        print(f"\n🎯 Overall Totals:")
        print(f"  Total Skills: {len(skills)}")
        print(f"  Total Uses: {total_uses}")
        print(f"  Total Time Saved: {total_time_saved:.1f} minutes ({total_time_saved/60:.1f} hours)")
        print()

        for category in sorted(by_category.keys()):
            cat_skills = by_category[category]
            cat_total_uses = sum(s['uses'] for s in cat_skills)
            cat_time_saved = sum(s['minutes'] for s in cat_skills)

            print(f"\n{category.upper()} ({len(cat_skills)} skills, {cat_total_uses} total uses)")
            print(f"{'-' * 70}")

            # Table header
            print(f"{'Skill':<30} {'Uses':>6} {'Success':>8} {'Saved':>10} {'Last Used':<12}")
            print(f"{'-' * 70}")

            for skill in cat_skills:
                display = skill['display'][:28] if len(skill['display']) > 28 else skill['display']
                success_str = format_percentage(skill['success'])
                saved_str = f"{skill['minutes']:.1f}m"

                print(f"{display:<30} {skill['uses']:>6} {success_str:>8} {saved_str:>10} {skill['last_used']:<12}")

            print(f"{'-' * 70}")
            print(f"Category Total: {cat_total_uses} uses, {cat_time_saved:.1f} minutes saved")

        print()

    finally:
        cur.close()
        conn.close()

# ============================================================================
# Category Statistics
# ============================================================================

def get_category_stats(category: str):
    """Get stats for all skills in a specific category."""

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                agent_name,
                display_name,
                use_count,
                success_rate,
                avg_time_saved_ms,
                total_time_saved_ms,
                last_used
            FROM skills_agents
            WHERE category = %s
              AND is_active = TRUE
            ORDER BY use_count DESC
        """, (category,))

        skills = cur.fetchall()

        if not skills:
            print(f"\n❌ No skills found in category: {category}")
            return

        print()
        print(f"{'=' * 70}")
        print(f"📊 {category.upper()} Category Statistics")
        print(f"{'=' * 70}")

        print(f"\nTotal Skills: {len(skills)}")

        # Calculate category totals
        total_uses = sum(s[2] for s in skills)
        avg_success = sum(s[3] for s in skills if s[3]) / len([s for s in skills if s[3]]) if skills else 0
        total_time_saved = sum(s[5] for s in skills if s[5]) or 0

        print(f"Total Uses: {total_uses}")
        print(f"Avg Success Rate: {format_percentage(avg_success)}")
        print(f"Total Time Saved: {format_time_ms(total_time_saved)}")
        print()

        # Table header
        print(f"{'Skill':<30} {'Uses':>6} {'Success':>8} {'Avg Saved':>10} {'Last Used':<12}")
        print(f"{'-' * 70}")

        for name, display, uses, success, avg_saved, total_saved, last_used in skills:
            display_name = (display or name)[:28]
            success_str = format_percentage(success)
            saved_str = format_time_ms(avg_saved)
            last_used_str = last_used.astimezone().strftime('%Y-%m-%d') if last_used else 'Never'

            print(f"{display_name:<30} {uses:>6} {success_str:>8} {saved_str:>10} {last_used_str:<12}")

        print()

    finally:
        cur.close()
        conn.close()

# ============================================================================
# Top Performers
# ============================================================================

def get_top_performers(limit: int = 10):
    """Get top performing skills by usage."""

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                agent_name,
                display_name,
                category,
                use_count,
                success_rate,
                total_time_saved_ms
            FROM skills_agents
            WHERE use_count > 0
              AND is_active = TRUE
            ORDER BY use_count DESC
            LIMIT %s
        """, (limit,))

        skills = cur.fetchall()

        if not skills:
            print("\n📊 No skills with usage data found.\n")
            return

        print()
        print(f"{'=' * 70}")
        print(f"🏆 Top {limit} Most Used Skills")
        print(f"{'=' * 70}")
        print()

        # Table header
        print(f"{'Rank':<6} {'Skill':<25} {'Category':<12} {'Uses':>6} {'Success':>8} {'Saved':>10}")
        print(f"{'-' * 70}")

        for i, (name, display, category, uses, success, time_saved) in enumerate(skills, 1):
            display_name = (display or name)[:23]
            cat_short = category[:10]
            success_str = format_percentage(success)
            saved_str = format_time_ms(time_saved)

            # Medal for top 3
            medal = {1: '🥇', 2: '🥈', 3: '🥉'}.get(i, '  ')

            print(f"{medal} #{i:<3} {display_name:<25} {cat_short:<12} {uses:>6} {success_str:>8} {saved_str:>10}")

        print()

    finally:
        cur.close()
        conn.close()

# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description='Show performance statistics for Skills System',
        epilog='Examples:\n'
               '  skills-stats.py git-commit-protocol\n'
               '  skills-stats.py --all\n'
               '  skills-stats.py --category git\n'
               '  skills-stats.py --top 10',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('skill_name', nargs='?', help='Skill name to analyze')
    parser.add_argument('--all', action='store_true', help='Show all skills summary')
    parser.add_argument('--category', help='Show all skills in a category')
    parser.add_argument('--top', type=int, metavar='N', help='Show top N most used skills')
    parser.add_argument('--days', type=int, default=7, help='Days of history to show (default: 7)')

    args = parser.parse_args()

    try:
        if args.all:
            get_all_stats()
        elif args.category:
            get_category_stats(args.category)
        elif args.top:
            get_top_performers(args.top)
        elif args.skill_name:
            get_skill_stats(args.skill_name, args.days)
        else:
            parser.print_help()
            print("\n💡 Tip: Use --all to see a summary of all skills")
            return 1

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
        return 1
    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
