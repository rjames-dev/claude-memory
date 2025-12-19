#!/usr/bin/env python3
"""
Diagnostic hook to understand what SessionStart "compact" actually receives.
This will help us verify if SessionStart can access the full conversation.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

DIAGNOSTIC_LOG = Path.home() / ".claude" / "sessionstart-diagnostic.jsonl"

def main():
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    transcript_path = hook_input.get("transcript_path")
    source = hook_input.get("source", "unknown")
    session_id = hook_input.get("session_id")
    cwd = hook_input.get("cwd", "/unknown")

    # Check if transcript file exists and get info
    transcript_exists = False
    transcript_size = 0
    message_count = 0

    if transcript_path and Path(transcript_path).exists():
        transcript_exists = True
        transcript_size = Path(transcript_path).stat().st_size

        # Count messages in transcript
        try:
            with open(transcript_path, 'r') as f:
                message_count = sum(1 for line in f if line.strip())
        except Exception:
            message_count = -1

    # Log diagnostic info
    diagnostic_entry = {
        "timestamp": datetime.now().isoformat(),
        "event": "SESSIONSTART_DIAGNOSTIC",
        "source": source,
        "session_id": session_id,
        "project_path": cwd,
        "transcript_path": transcript_path,
        "transcript_exists": transcript_exists,
        "transcript_size_bytes": transcript_size,
        "message_count": message_count,
        "all_hook_input": hook_input
    }

    try:
        DIAGNOSTIC_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(DIAGNOSTIC_LOG, 'a') as f:
            f.write(json.dumps(diagnostic_entry) + "\n")
    except Exception:
        pass

    # Output to user
    output = {
        "systemMessage": f"🔍 SessionStart diagnostic: {message_count} messages in transcript (size: {transcript_size} bytes)",
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": f"Source: {source}, Session: {session_id}"
        }
    }

    print(json.dumps(output))
    sys.exit(0)

if __name__ == "__main__":
    main()
