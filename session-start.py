#!/usr/bin/env python3
"""
Session Start - Oriented Briefing Skill

Produces a structured session brief by pulling from three sources:
  1. claude-memory  — most recent snapshot summary for this project
  2. claude-vault   — Current State.md for active projects
  3. hp-feature-planning — SESSION-STATE.md quick-resume blocks

Replaces the manual 5-10 minute context-gathering at session start.

Usage:
    python3 session-start.py
    python3 session-start.py --project NLQ
    python3 session-start.py --all-projects

Author: Claude Sonnet 4.6
Created: 2026-03-22
"""

import sys
import os
import re
import argparse
from pathlib import Path
from datetime import datetime
from db_utils import get_db_connection

# ── Path config ──────────────────────────────────────────────────────────────
VAULT_ROOT      = Path(os.environ.get("VAULT_ROOT",    "/home/hp-admin/code/claude-vault"))
PLANNING_ROOT   = Path(os.environ.get("PLANNING_ROOT", "/home/hp-admin/data/code/hp-feature-planning"))
PROJECTS_DIR    = VAULT_ROOT / "Projects"

# ── Formatting helpers ────────────────────────────────────────────────────────
W = 68

def header(title):
    print(f"\n{'═' * W}")
    print(f"  {title}")
    print(f"{'═' * W}")

def section(title):
    print(f"\n── {title} {'─' * (W - len(title) - 4)}")

def rule():
    print(f"{'─' * W}")

# ── claude-memory: recent snapshots ──────────────────────────────────────────

def get_recent_snapshots(cur, limit=3):
    """Most recent snapshots with enhanced summaries, any project."""
    cur.execute("""
        SELECT
            id,
            project_path,
            session_id,
            timestamp,
            context_window_size,
            trigger_event,
            LEFT(summary, 600) as summary_preview,
            LENGTH(summary) as summary_len
        FROM context_snapshots
        WHERE summary IS NOT NULL AND LENGTH(summary) > 100
        ORDER BY timestamp DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    return [
        {
            "id":           r[0],
            "project":      os.path.basename(r[1]) if r[1] else "unknown",
            "project_path": r[1],
            "session_id":   r[2],
            "timestamp":    r[3],
            "messages":     r[4],
            "trigger":      r[5],
            "summary":      r[6],
            "summary_len":  r[7],
        }
        for r in rows
    ]

def get_snapshot_for_project(cur, project_keyword):
    """Most recent snapshot where project_path contains keyword."""
    cur.execute("""
        SELECT
            id, project_path, session_id, timestamp,
            context_window_size, trigger_event,
            LEFT(summary, 800) as summary_preview,
            LENGTH(summary) as summary_len
        FROM context_snapshots
        WHERE summary IS NOT NULL
          AND LENGTH(summary) > 100
          AND (project_path ILIKE %s OR project_path ILIKE %s)
        ORDER BY timestamp DESC
        LIMIT 1
    """, (f"%{project_keyword}%", f"%{project_keyword.lower()}%"))
    r = cur.fetchone()
    if not r:
        return None
    return {
        "id":           r[0],
        "project_path": r[1],
        "project":      os.path.basename(r[1]) if r[1] else "unknown",
        "session_id":   r[2],
        "timestamp":    r[3],
        "messages":     r[4],
        "trigger":      r[5],
        "summary":      r[6],
        "summary_len":  r[7],
    }

# ── claude-vault: Current State extraction ───────────────────────────────────

def find_vault_projects():
    """Return list of (project_name, current_state_path) for all vault projects."""
    if not PROJECTS_DIR.exists():
        return []
    results = []
    for p in sorted(PROJECTS_DIR.iterdir()):
        if p.is_dir():
            cs = p / "Current State.md"
            if cs.exists():
                results.append((p.name, cs))
    return results

def extract_vault_state(path: Path) -> dict:
    """
    Extract key fields from a Current State.md file.
    Returns: { phase, next_steps: [str], updated }
    """
    text = path.read_text(errors="replace")

    # Updated date from frontmatter
    updated = None
    m = re.search(r'^updated:\s*(.+)$', text, re.MULTILINE)
    if m:
        updated = m.group(1).strip()

    # Phase line — look for bold "Phase:" pattern
    phase = None
    m = re.search(r'\*\*Phase[:\s]+([^\n*]+)\*\*', text)
    if m:
        phase = m.group(1).strip()
    else:
        # Fallback: look for a "## Where We Are" section header line
        m = re.search(r'## Where We Are\s*\n+\*\*([^\n*]+)\*\*', text)
        if m:
            phase = m.group(1).strip()

    # Immediate Next Steps — numbered list items after "## Immediate Next Steps"
    next_steps = []
    m = re.search(r'## Immediate Next Steps\s*\n(.*?)(?=\n##|\Z)', text, re.DOTALL)
    if m:
        block = m.group(1)
        items = re.findall(r'^\d+\.\s+\*\*([^*]+)\*\*[^\n]*', block, re.MULTILINE)
        if not items:
            items = re.findall(r'^\d+\.\s+(.+)$', block, re.MULTILINE)
        next_steps = [i.strip() for i in items[:3]]

    return {
        "phase":      phase or "(phase not found)",
        "next_steps": next_steps,
        "updated":    updated or "unknown",
    }

# ── hp-feature-planning: SESSION-STATE quick resume ──────────────────────────

def find_planning_states():
    """Return list of (folder_name, session_state_path) for non-template folders."""
    if not PLANNING_ROOT.exists():
        return []
    results = []
    for p in sorted(PLANNING_ROOT.iterdir()):
        if p.is_dir() and p.name != "TEMPLATE":
            ss = p / "SESSION-STATE.md"
            if ss.exists():
                results.append((p.name, ss))
    return results

def extract_session_state(path: Path) -> dict:
    """
    Extract Quick Resume block from SESSION-STATE.md.
    Returns: { status, next_action, last_updated }
    """
    text = path.read_text(errors="replace")

    # Last updated
    updated = None
    m = re.search(r'\*\*Last Updated:\*\*\s*(.+)', text)
    if m:
        updated = m.group(1).strip()

    # Session status
    status = None
    m = re.search(r'\*\*Session Status:\*\*\s*(.+)', text)
    if m:
        status = m.group(1).strip()

    # Next action — line after "**Next Action:**"
    next_action = None
    m = re.search(r'\*\*Next Action:\*\*\s*\n([^\n]+)', text)
    if m:
        next_action = m.group(1).strip()
    else:
        m = re.search(r'\*\*Next Action:\*\*\s*(.+)', text)
        if m:
            next_action = m.group(1).strip()

    return {
        "status":      status or "(status not found)",
        "next_action": next_action or "(no next action specified)",
        "updated":     updated or "unknown",
    }

# ── Output renderers ──────────────────────────────────────────────────────────

def render_memory_section(snapshots):
    section("LAST SESSION  (claude-memory)")
    if not snapshots:
        print("  No enhanced snapshots found. Run: python3 enhance-summary.py <id>")
        return

    for snap in snapshots:
        ts = snap["timestamp"].strftime("%Y-%m-%d %H:%M") if snap["timestamp"] else "unknown"
        print(f"  Snapshot #{snap['id']}  |  {ts}  |  {snap['messages']} messages  |  {snap['summary_len']} char summary")
        print(f"  Project: {snap['project_path']}")
        print()
        # Print first ~500 chars of summary, word-wrapped
        preview = snap["summary"].strip()
        # Take just the first section up to the first "---" or 500 chars
        cut = preview.find("---")
        if cut > 0 and cut < 600:
            preview = preview[:cut].strip()
        else:
            preview = preview[:500]
        for line in preview.splitlines():
            print(f"  {line}")
        if len(snapshots) > 1:
            print()
            rule()

def render_vault_section(project_filter=None):
    section("VAULT STATE  (claude-vault)")
    projects = find_vault_projects()
    if not projects:
        print(f"  No vault projects found at {PROJECTS_DIR}")
        return

    shown = 0
    for name, path in projects:
        if project_filter and project_filter.lower() not in name.lower():
            continue
        state = extract_vault_state(path)
        print(f"  ▸ {name}  (updated: {state['updated']})")
        print(f"    Phase: {state['phase']}")
        if state["next_steps"]:
            print(f"    Next:")
            for i, step in enumerate(state["next_steps"], 1):
                print(f"      {i}. {step}")
        print()
        shown += 1

    if shown == 0:
        print(f"  No projects matching '{project_filter}'")

def render_planning_section(project_filter=None):
    section("EXECUTION STATE  (hp-feature-planning)")
    states = find_planning_states()
    if not states:
        print(f"  No SESSION-STATE.md files found at {PLANNING_ROOT}")
        return

    shown = 0
    for name, path in states:
        if project_filter:
            # Loose match: any word from filter appears in folder name
            words = project_filter.lower().split()
            if not any(w in name.lower() for w in words):
                continue
        state = extract_session_state(path)
        print(f"  ▸ {name}  (updated: {state['updated']})")
        print(f"    Status: {state['status']}")
        print(f"    Next:   {state['next_action'][:100]}")
        print()
        shown += 1

    if shown == 0 and project_filter:
        # Show all if filter matched nothing
        for name, path in states:
            state = extract_session_state(path)
            print(f"  ▸ {name}  (updated: {state['updated']})")
            print(f"    Status: {state['status']}")
            print(f"    Next:   {state['next_action'][:100]}")
            print()

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Session Start — oriented briefing from claude-memory + vault + planning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 session-start.py                  # Recent snapshots + all active projects
  python3 session-start.py --project NLQ   # Filter to NLQ across all three sources
  python3 session-start.py --memory-only   # Just claude-memory snapshot
        """
    )
    parser.add_argument("--project",      help="Filter output to a specific project name/keyword")
    parser.add_argument("--memory-only",  action="store_true", help="Show only claude-memory section")
    parser.add_argument("--vault-only",   action="store_true", help="Show only vault section")
    parser.add_argument("--planning-only",action="store_true", help="Show only planning section")
    args = parser.parse_args()

    # Determine which sections to show
    show_all     = not (args.memory_only or args.vault_only or args.planning_only)
    show_memory  = show_all or args.memory_only
    show_vault   = show_all or args.vault_only
    show_planning= show_all or args.planning_only

    header(f"SESSION START BRIEF  —  {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # ── 1. claude-memory ──
    if show_memory:
        try:
            conn = get_db_connection()
            cur  = conn.cursor()

            if args.project:
                snap = get_snapshot_for_project(cur, args.project)
                # Fall back to most recent snapshot if none match the project filter
                snapshots = [snap] if snap else get_recent_snapshots(cur, limit=1)
            else:
                snapshots = get_recent_snapshots(cur, limit=2)

            render_memory_section(snapshots)
            cur.close()
            conn.close()
        except SystemExit:
            section("LAST SESSION  (claude-memory)")
            print("  ⚠  Could not connect to claude-memory DB.")
            print("     Check: cd /home/hp-admin/code/claude-memory && docker compose ps")

    # ── 2. claude-vault ──
    if show_vault:
        render_vault_section(project_filter=args.project)

    # ── 3. hp-feature-planning ──
    if show_planning:
        render_planning_section(project_filter=args.project)

    # ── Footer ──
    print(f"\n{'═' * W}")
    hints = []
    if show_memory:
        hints.append("enhance snapshot: python3 enhance-summary.py <id>")
    hints.append("vault path: " + str(VAULT_ROOT))
    hints.append("planning path: " + str(PLANNING_ROOT))
    for h in hints:
        print(f"  {h}")
    print(f"{'═' * W}\n")

if __name__ == "__main__":
    main()
