#!/usr/bin/env python3
"""
Claude Memory - Promote to Obsidian
Write session insights from claude-memory into the Obsidian vault.

Reads a snapshot from the DB and writes structured Obsidian notes:
  - Claude/Session-Logs/YYYY-MM-DD.md        (always)
  - Projects/<folder>/Decisions Log.md        (if key_decisions present)
  - Claude/Knowledge-Base/Learnings Log.md    (if bugs_fixed present)

vault_root is derived from CLAUDE_WORKSPACE_ROOT in .env (no separate config needed).
Project → Obsidian folder mapping is stored in the project_registry table.

Usage:
    python3 promote-to-obsidian.py <snapshot_id>

Requirements:
    - ANTHROPIC_API_KEY in environment or .env
    - Docker containers running (claude-context-db)
    - anthropic, psycopg2-binary packages

Example:
    python3 promote-to-obsidian.py 1
"""

import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from psycopg2.extras import RealDictCursor

# ---------------------------------------------------------------------------
# Resolve paths relative to this script (works from any working directory)
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent


def get_env_vars():
    """Read .env file from the claude-memory directory."""
    env_vars = {}
    env_file = SCRIPT_DIR / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
    return env_vars


def get_vault_root(env_vars):
    """
    vault_root = CLAUDE_WORKSPACE_ROOT/vault
    This is a convention — not a separate config value.
    """
    workspace = (
        os.environ.get('CLAUDE_WORKSPACE_ROOT')
        or env_vars.get('CLAUDE_WORKSPACE_ROOT')
    )
    if not workspace:
        print("❌ CLAUDE_WORKSPACE_ROOT not set in environment or .env", file=sys.stderr)
        sys.exit(1)
    vault = Path(workspace) / 'vault'
    if not vault.exists():
        print(f"❌ Vault not found at {vault}", file=sys.stderr)
        print("   Run setup-hooks.sh to create it, or set CLAUDE_WORKSPACE_ROOT correctly.",
              file=sys.stderr)
        sys.exit(1)
    return vault


def get_anthropic_api_key(env_vars):
    key = os.environ.get('ANTHROPIC_API_KEY') or env_vars.get('ANTHROPIC_API_KEY')
    if not key:
        print("❌ ANTHROPIC_API_KEY not found in environment or .env", file=sys.stderr)
        sys.exit(1)
    return key


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def get_db_connection():
    """Use db_utils if available, otherwise fall back to direct connection."""
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from db_utils import get_db_connection as _conn
        return _conn(cursor_factory=RealDictCursor)
    except ImportError:
        import psycopg2
        env_vars = get_env_vars()
        conn = psycopg2.connect(
            host='localhost',
            port=int(env_vars.get('POSTGRES_HOST_PORT', '5435')),
            database=env_vars.get('POSTGRES_DB', 'claude_memory'),
            user=env_vars.get('POSTGRES_USER', 'memory_admin'),
            password=env_vars.get('CONTEXT_DB_PASSWORD', ''),
        )
        conn.cursor_factory = RealDictCursor
        return conn


def fetch_snapshot(snapshot_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT id, project_path, timestamp, summary, tags,
               mentioned_files, key_decisions, bugs_fixed,
               trigger_event, context_window_size
        FROM context_snapshots
        WHERE id = %s
    """, (snapshot_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def fetch_registry(project_path):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT project_path, obsidian_folder, display_name
        FROM project_registry
        WHERE project_path = %s
    """, (project_path,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def auto_register_project(project_path):
    """
    Register a project not yet in project_registry.
    Derives display_name from the last path segment.
    """
    last_segment = project_path.rstrip('/').split('/')[-1]
    display_name = last_segment.replace('-', ' ').replace('_', ' ').title()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO project_registry (project_path, display_name)
        VALUES (%s, %s)
        ON CONFLICT (project_path) DO NOTHING
    """, (project_path, display_name))
    conn.commit()
    cur.close()
    conn.close()
    return display_name


def set_obsidian_folder(project_path, obsidian_folder):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE project_registry
        SET obsidian_folder = %s,
            obsidian_linked_at = NOW()
        WHERE project_path = %s
    """, (obsidian_folder, project_path))
    conn.commit()
    cur.close()
    conn.close()


# ---------------------------------------------------------------------------
# Resolve Obsidian project folder
# ---------------------------------------------------------------------------

def resolve_obsidian_folder(registry, project_path, vault_root):
    """
    Return the Projects/<folder> path to use, creating it if necessary.
    If registry has no obsidian_folder, auto-derive and create.
    """
    if registry and registry['obsidian_folder']:
        folder_name = registry['obsidian_folder']
        projects_path = vault_root / 'Projects' / folder_name
        projects_path.mkdir(parents=True, exist_ok=True)
        return folder_name, projects_path

    # Auto-derive from project_path
    last_segment = project_path.rstrip('/').split('/')[-1]
    folder_name = last_segment.replace('-', ' ').replace('_', ' ').title()

    print(f"   No Obsidian folder mapped — auto-creating 'Projects/{folder_name}'")
    projects_path = vault_root / 'Projects' / folder_name
    projects_path.mkdir(parents=True, exist_ok=True)

    # Create stub Current State if it doesn't exist
    current_state = projects_path / 'Current State.md'
    if not current_state.exists():
        current_state.write_text(f"""---
tags:
  - project/active
  - type/current-state
  - status/new
created: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}
---

# Current State — {folder_name}

*Auto-created by promote-to-obsidian on first promotion.*

## Where We Are

## Immediate Next Steps

## References
""")
        print(f"   Created stub: Projects/{folder_name}/Current State.md")

    # Update registry
    set_obsidian_folder(project_path, folder_name)
    print(f"   Linked project_registry: {project_path} → {folder_name}")

    return folder_name, projects_path


# ---------------------------------------------------------------------------
# Claude API — generate session log narrative
# ---------------------------------------------------------------------------

def generate_session_log_narrative(snapshot, api_key):
    """
    Ask Claude to distill the full summary into a tight 2-3 paragraph
    session log entry suitable for Obsidian.
    """
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    summary = snapshot['summary'] or '(no summary available)'
    decisions = snapshot['key_decisions'] or []
    bugs = snapshot['bugs_fixed'] or []
    tags = snapshot['tags'] or []

    prompt = f"""You are writing a concise session log entry for an Obsidian knowledge base.

Given this development session summary, write a tight 2-3 paragraph narrative
suitable for a session log. Focus on: what was accomplished, why it matters,
and what comes next. No headings — just clean prose. Plain markdown only.
Be specific and concrete, not generic.

SUMMARY:
{summary[:3000]}

TAGS: {', '.join(tags)}
DECISIONS MADE: {len(decisions)}
BUGS FIXED: {len(bugs)}

Write the 2-3 paragraph narrative now:"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()


# ---------------------------------------------------------------------------
# File writers
# ---------------------------------------------------------------------------

def write_session_log(vault_root, snapshot, folder_name, narrative):
    """Write Claude/Session-Logs/YYYY-MM-DD.md"""
    ts = snapshot['timestamp']
    if isinstance(ts, str):
        date_str = ts[:10]
    else:
        date_str = ts.strftime('%Y-%m-%d')

    log_dir = vault_root / 'Claude' / 'Session-Logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{date_str}.md"

    # Derive tag slug from folder name
    tag_slug = folder_name.lower().replace(' ', '-').replace('+', '').replace('--', '-')

    decisions = snapshot['key_decisions'] or []
    bugs = snapshot['bugs_fixed'] or []
    tags = snapshot['tags'] or []

    decisions_block = ''
    if decisions:
        items = '\n'.join(f"- {d}" for d in decisions)
        decisions_block = f"\n## Decisions\n\n{items}\n"

    bugs_block = ''
    if bugs:
        items = '\n'.join(f"- {b}" for b in bugs)
        bugs_block = f"\n## Learnings\n\n{items}\n"

    tags_yaml = '\n'.join(f"  - {t}" for t in [
        'type/session-log', f'project/{tag_slug}', *tags
    ])

    content = f"""---
tags:
{tags_yaml}
created: {date_str}
source: claude-memory
snapshot_id: {snapshot['id']}
---

# Session Log — {date_str}

**Project:** {folder_name}
**Snapshot:** claude-memory #{snapshot['id']}

## Summary

{narrative}
{decisions_block}{bugs_block}
> [!info] Source
> claude-memory snapshot #{snapshot['id']} · [[Projects/{folder_name}/Current State|{folder_name}]]
"""

    # Append if file exists (multiple sessions same day), otherwise create
    if log_file.exists():
        existing = log_file.read_text()
        log_file.write_text(existing + '\n---\n\n' + content)
        print(f"   Appended to existing: Claude/Session-Logs/{date_str}.md")
    else:
        log_file.write_text(content)
        print(f"   Created: Claude/Session-Logs/{date_str}.md")

    return date_str


def append_decisions_log(projects_path, snapshot, folder_name, date_str):
    """Append to Projects/<folder>/Decisions Log.md"""
    decisions = snapshot['key_decisions'] or []
    if not decisions:
        return

    log_file = projects_path / 'Decisions Log.md'

    # Create file with header if it doesn't exist
    if not log_file.exists():
        log_file.write_text(f"""---
tags:
  - project/active
  - type/decisions-log
created: {date_str}
---

# Decisions Log — {folder_name}

*Architecture and implementation decisions, newest first.*

""")

    items = '\n'.join(f"- {d}" for d in decisions)
    entry = f"""
## {date_str}

> Source: [[../../Claude/Session-Logs/{date_str}]] · claude-memory #{snapshot['id']}

{items}
"""
    with open(log_file, 'a') as f:
        f.write(entry)

    print(f"   Appended {len(decisions)} decision(s) to: Projects/{folder_name}/Decisions Log.md")


def append_learnings_log(vault_root, snapshot, folder_name, date_str):
    """Append to Claude/Knowledge-Base/Learnings Log.md"""
    bugs = snapshot['bugs_fixed'] or []
    if not bugs:
        return

    kb_dir = vault_root / 'Claude' / 'Knowledge-Base'
    kb_dir.mkdir(parents=True, exist_ok=True)
    log_file = kb_dir / 'Learnings Log.md'

    if not log_file.exists():
        log_file.write_text("""---
tags:
  - type/knowledge-base
  - type/learnings
created: {}
---

# Learnings Log

*Errors, fixes, and generalizable lessons captured from sessions.*

""".format(date_str))

    items = '\n'.join(f"- {b}" for b in bugs)
    entry = f"""
## {date_str} — {folder_name}

> Source: [[../Session-Logs/{date_str}]] · claude-memory #{snapshot['id']}

{items}
"""
    with open(log_file, 'a') as f:
        f.write(entry)

    print(f"   Appended {len(bugs)} learning(s) to: Claude/Knowledge-Base/Learnings Log.md")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 promote-to-obsidian.py <snapshot_id>", file=sys.stderr)
        sys.exit(1)

    try:
        snapshot_id = int(sys.argv[1])
    except ValueError:
        print(f"❌ Invalid snapshot_id '{sys.argv[1]}' (must be a number)", file=sys.stderr)
        sys.exit(1)

    env_vars = get_env_vars()
    vault_root = get_vault_root(env_vars)
    api_key = get_anthropic_api_key(env_vars)

    print("=" * 70)
    print(f"🚀 PROMOTE TO OBSIDIAN — Snapshot #{snapshot_id}")
    print("=" * 70)
    print()

    # Step 1: Fetch snapshot
    print(f"📂 [1/5] Fetching snapshot #{snapshot_id}...")
    snapshot = fetch_snapshot(snapshot_id)
    if not snapshot:
        print(f"❌ Snapshot #{snapshot_id} not found", file=sys.stderr)
        sys.exit(1)

    print(f"   Project:  {snapshot['project_path']}")
    print(f"   Date:     {str(snapshot['timestamp'])[:10]}")
    print(f"   Tags:     {', '.join(snapshot['tags'] or [])}")
    print(f"   Decisions:{len(snapshot['key_decisions'] or [])}")
    print(f"   Bugs:     {len(snapshot['bugs_fixed'] or [])}")
    print()

    # Step 2: Resolve vault project folder
    print(f"🗂️  [2/5] Resolving Obsidian project folder...")
    print(f"   Vault:    {vault_root}")

    registry = fetch_registry(snapshot['project_path'])
    if not registry:
        print(f"   Project not in registry — auto-registering...")
        auto_register_project(snapshot['project_path'])
        registry = None  # resolve_obsidian_folder handles the rest

    folder_name, projects_path = resolve_obsidian_folder(
        registry, snapshot['project_path'], vault_root
    )
    print(f"   Folder:   Projects/{folder_name}")
    print()

    # Step 3: Generate narrative
    print(f"🤖 [3/5] Generating session log narrative via Claude API...")
    narrative = generate_session_log_narrative(snapshot, api_key)
    print(f"   Generated {len(narrative)} chars")
    print()

    # Step 4: Write files
    print(f"✍️  [4/5] Writing Obsidian notes...")
    date_str = write_session_log(vault_root, snapshot, folder_name, narrative)

    if snapshot['key_decisions']:
        append_decisions_log(projects_path, snapshot, folder_name, date_str)

    if snapshot['bugs_fixed']:
        append_learnings_log(vault_root, snapshot, folder_name, date_str)

    print()

    # Step 5: Update registry timestamp
    print(f"💾 [5/5] Updating project registry...")
    set_obsidian_folder(snapshot['project_path'], folder_name)
    print(f"   obsidian_linked_at updated")
    print()

    print("=" * 70)
    print("✨ PROMOTION COMPLETE!")
    print("=" * 70)
    print()
    print("Files written:")
    print(f"  📄 Claude/Session-Logs/{date_str}.md")
    if snapshot['key_decisions']:
        print(f"  📄 Projects/{folder_name}/Decisions Log.md")
    if snapshot['bugs_fixed']:
        print(f"  📄 Claude/Knowledge-Base/Learnings Log.md")
    print()
    print(f"Open Obsidian and check Projects/{folder_name}/ to review.")
    print()


if __name__ == '__main__':
    main()
