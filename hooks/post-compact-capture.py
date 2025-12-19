#!/usr/bin/env python3
"""
Claude Memory - Post-Compact Capture Hook

Captures conversation context AFTER auto-compact or manual compact completes.
Uses intelligent previous-session detection to find the right transcript file.

Hook Event: SessionStart (matcher: "compact")
Trigger: Fires after both auto-compact and manual compact operations

Smart Session Detection:
- SessionStart receives a NEW (empty) session transcript
- We intelligently find the PREVIOUS session's transcript
- Use timestamp + file size to identify the right file
- Prevents duplicate captures via upsert logic
"""

import json
import sys
import requests
from pathlib import Path
from datetime import datetime
import os
import glob

# Configuration
PROCESSOR_URL = os.getenv("CLAUDE_MEMORY_PROCESSOR_URL", "http://localhost:3200")
CAPTURE_ENDPOINT = f"{PROCESSOR_URL}/capture"
LOG_FILE = Path.home() / ".claude" / "memory-captures.jsonl"
MIN_TRANSCRIPT_SIZE = 512  # Minimum bytes to consider a transcript file "substantive"

def find_previous_session_transcript(current_transcript_path):
    """
    Smart previous-session detection.

    When SessionStart "compact" fires, it receives the NEW session's transcript path,
    which is typically empty. We need to find the PREVIOUS session's transcript.

    Strategy:
    1. Check if current transcript is empty/minimal
    2. If yes, search the same directory for recent non-empty transcripts
    3. Return the most recent substantive transcript before current time
    """
    try:
        current_path = Path(current_transcript_path)

        # Check current file size
        if current_path.exists():
            current_size = current_path.stat().st_size
            current_mtime = current_path.stat().st_mtime

            # If current file is substantive, use it
            if current_size >= MIN_TRANSCRIPT_SIZE:
                return str(current_path), current_size
        else:
            current_mtime = datetime.now().timestamp()

        # Current file is empty/doesn't exist - find previous session
        transcript_dir = current_path.parent

        if not transcript_dir.exists():
            return None, 0

        # Find all .jsonl files in the same directory
        candidates = []
        for jsonl_file in transcript_dir.glob("*.jsonl"):
            try:
                stat = jsonl_file.stat()
                # Must be modified before current transcript AND be substantive
                if stat.st_mtime < current_mtime and stat.st_size >= MIN_TRANSCRIPT_SIZE:
                    candidates.append({
                        'path': jsonl_file,
                        'size': stat.st_size,
                        'mtime': stat.st_mtime
                    })
            except Exception:
                continue

        if not candidates:
            return None, 0

        # Sort by modification time descending (most recent first)
        candidates.sort(key=lambda x: x['mtime'], reverse=True)

        # Return the most recent substantive transcript
        best = candidates[0]
        return str(best['path']), best['size']

    except Exception as e:
        print(f"Error finding previous session: {e}", file=sys.stderr)
        return None, 0

def parse_transcript(transcript_path):
    """Parse Claude Code transcript (.jsonl format)."""
    try:
        if not Path(transcript_path).exists():
            return None

        messages = []
        with open(transcript_path, 'r') as f:
            for line in f:
                try:
                    msg = json.loads(line)
                    messages.append(msg)
                except json.JSONDecodeError:
                    continue

        # Convert to claude-memory format
        conversation_messages = []
        for msg in messages:
            msg_type = msg.get("type")

            if msg_type == "user":
                conversation_messages.append({
                    "role": "user",
                    "content": msg.get("content", "")
                })
            elif msg_type == "assistant":
                # Extract text from assistant response
                content = ""
                response = msg.get("response", {})
                if isinstance(response, dict):
                    for block in response.get("content", []):
                        if block.get("type") == "text":
                            content += block.get("text", "")
                conversation_messages.append({
                    "role": "assistant",
                    "content": content
                })

        return conversation_messages

    except Exception as e:
        print(f"Error parsing transcript: {e}", file=sys.stderr)
        return None

def capture_conversation(messages, project_path, source_type, session_id, transcript_path):
    """Send conversation to claude-memory processor for capture."""
    try:
        payload = {
            "project_path": project_path,
            "trigger": f"post-compact-{source_type}-{datetime.now().strftime('%Y-%m-%d-%H-%M')}",
            "session_id": session_id,
            "transcript_path": transcript_path,
            "conversation_data": {
                "messages": messages
            },
            "metadata": {
                "tags": ["post-compact-capture", source_type],
                "files_mentioned": []
            }
        }

        response = requests.post(
            CAPTURE_ENDPOINT,
            json=payload,
            timeout=5
        )

        if response.status_code == 202:
            return {"status": "success", "data": response.json()}
        else:
            return {"status": "error", "message": f"HTTP {response.status_code}"}

    except requests.exceptions.ConnectionError:
        return {"status": "error", "message": "Cannot connect to processor. Is docker running?"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def log_capture(event_data):
    """Log capture event to file."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(json.dumps(event_data) + "\n")
    except Exception:
        pass

def main():
    try:
        # Read hook input from stdin
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    current_transcript_path = hook_input.get("transcript_path")
    source = hook_input.get("source", "unknown")  # SessionStart source: "compact"
    current_session_id = hook_input.get("session_id")
    cwd = hook_input.get("cwd", "/unknown")

    if not current_transcript_path:
        print("Error: No transcript_path provided", file=sys.stderr)
        sys.exit(1)

    # Smart previous-session detection
    # SessionStart "compact" often receives a NEW (empty) session transcript
    # We intelligently find the PREVIOUS session's transcript to capture
    actual_transcript_path, file_size = find_previous_session_transcript(current_transcript_path)

    if not actual_transcript_path:
        print(f"Warning: Could not find previous session transcript (current: {current_transcript_path})", file=sys.stderr)
        sys.exit(0)

    # Extract session ID from transcript filename (UUID format)
    # Example: ~/.claude/projects/.../abc-def-123.jsonl -> abc-def-123
    actual_session_id = Path(actual_transcript_path).stem

    # Parse conversation from the ACTUAL (previous) transcript
    messages = parse_transcript(actual_transcript_path)

    if not messages or len(messages) == 0:
        print(f"Warning: No messages found in transcript: {actual_transcript_path}", file=sys.stderr)
        sys.exit(0)

    print(f"📂 Smart session detection:", file=sys.stderr)
    print(f"   Current (new): {current_transcript_path}", file=sys.stderr)
    print(f"   Actual (prev): {actual_transcript_path} ({file_size} bytes, {len(messages)} messages)", file=sys.stderr)

    # Capture conversation
    result = capture_conversation(messages, cwd, source, actual_session_id, actual_transcript_path)

    # Log the event
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event": "POST_COMPACT_CAPTURE",
        "source": source,  # "compact" for SessionStart compact matcher
        "session_id": actual_session_id,
        "transcript_path": actual_transcript_path,
        "current_session_id": current_session_id,
        "current_transcript_path": current_transcript_path,
        "project_path": cwd,
        "message_count": len(messages),
        "file_size_bytes": file_size,
        "capture_result": result
    }
    log_capture(log_entry)

    # Output hook response
    if result["status"] == "success":
        output = {
            "systemMessage": f"✅ Conversation captured to memory ({len(messages)} messages) after compact.",
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": f"Post-compact snapshot created. Source: {source}, Session: {actual_session_id}"
            }
        }
    else:
        output = {
            "systemMessage": f"⚠️ Failed to capture conversation: {result.get('message', 'Unknown error')}",
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "error": result.get("message")
            }
        }

    print(json.dumps(output))
    sys.exit(0)

if __name__ == "__main__":
    main()
