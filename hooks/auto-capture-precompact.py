#!/usr/bin/env python3
"""
Claude Memory - Auto-Capture PreCompact Hook

Automatically captures conversation context before Claude Code compacts.
Triggers when context usage is high (auto-compact) or manual compact requested.

Hook Event: PreCompact
Trigger: auto (context nearly full) or manual (user-initiated)
"""

import json
import sys
import requests
from pathlib import Path
from datetime import datetime
import os

# Configuration
PROCESSOR_URL = os.getenv("CLAUDE_MEMORY_PROCESSOR_URL", "http://localhost:3200")
CAPTURE_ENDPOINT = f"{PROCESSOR_URL}/capture"
LOG_FILE = Path.home() / ".claude" / "memory-captures.jsonl"

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
                # Fixed: Claude Code uses "message" not "response"
                content = ""
                message = msg.get("message", {})
                if isinstance(message, dict):
                    for block in message.get("content", []):
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

def capture_conversation(messages, project_path, trigger, session_id, transcript_path):
    """Send conversation to claude-memory processor for capture."""
    try:
        payload = {
            "project_path": project_path,
            "trigger": f"auto-compact-{trigger}-{datetime.now().strftime('%Y-%m-%d-%H-%M')}",
            "session_id": session_id,
            "transcript_path": transcript_path,
            "conversation_data": {
                "messages": messages
            },
            "metadata": {
                "tags": ["auto-capture", "pre-compact", trigger],
                "files_mentioned": []
            }
        }

        response = requests.post(
            CAPTURE_ENDPOINT,
            json=payload,
            timeout=300  # 5 minutes for large/verbose sessions (increased from 5s)
        )

        if response.status_code == 202:
            return {"status": "success", "data": response.json()}
        else:
            return {"status": "error", "message": f"HTTP {response.status_code}"}

    except requests.exceptions.ConnectionError:
        return {"status": "error", "message": "Cannot connect to processor. Is docker running?"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_snapshot_id_for_session(session_id):
    """
    Retrieve the most recent snapshot ID for a session.

    This is needed to link agent work to the parent snapshot.
    """
    try:
        import psycopg2
        import os

        # Database configuration (same as agent_capture module)
        db_password = os.getenv('CONTEXT_DB_PASSWORD')
        if not db_password:
            raise ValueError("CONTEXT_DB_PASSWORD environment variable required")

        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_HOST_PORT', '5435')),
            database=os.getenv('POSTGRES_DB', 'claude_memory'),
            user=os.getenv('POSTGRES_USER', 'memory_admin'),
            password=db_password
        )

        cur = conn.cursor()
        cur.execute("""
            SELECT id FROM context_snapshots
            WHERE session_id = %s
            ORDER BY timestamp DESC
            LIMIT 1
        """, (session_id,))

        result = cur.fetchone()
        cur.close()
        conn.close()

        return result[0] if result else None

    except Exception as e:
        print(f"Error getting snapshot ID: {e}", file=sys.stderr)
        return None

def capture_agents_for_session(transcript_path, session_id):
    """
    Capture all agent work from the same session directory.

    Args:
        transcript_path: Path to the main session transcript
        session_id: Session ID from the hook input

    Returns:
        Dict with capture statistics
    """
    try:
        # Import agent capture module
        from pathlib import Path
        import sys

        # Add hooks directory to path if not already there
        hooks_dir = Path(__file__).parent
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))

        import agent_capture

        # Get session directory (same directory as main transcript)
        session_directory = Path(transcript_path).parent

        # Get parent snapshot ID (wait briefly for processor to finish)
        import time
        time.sleep(1)  # Give processor time to create snapshot

        parent_snapshot_id = get_snapshot_id_for_session(session_id)

        if not parent_snapshot_id:
            return {"status": "error", "message": "Parent snapshot not found"}

        # Capture all agents in the session
        stats = agent_capture.capture_agents(
            session_directory=str(session_directory),
            parent_snapshot_id=parent_snapshot_id,
            parent_session_id=session_id
        )

        return {"status": "success", "stats": stats}

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
    
    transcript_path = hook_input.get("transcript_path")
    trigger = hook_input.get("trigger", "unknown")  # "auto" or "manual"
    session_id = hook_input.get("session_id")
    cwd = hook_input.get("cwd", "/unknown")
    
    if not transcript_path:
        print("Error: No transcript_path provided", file=sys.stderr)
        sys.exit(1)
    
    # Parse conversation from transcript
    messages = parse_transcript(transcript_path)
    
    if not messages or len(messages) == 0:
        print("Warning: No messages found in transcript", file=sys.stderr)
        sys.exit(0)
    
    # Capture conversation
    result = capture_conversation(messages, cwd, trigger, session_id, transcript_path)

    # If conversation capture succeeded, also capture any agent work
    agent_result = None
    if result["status"] == "success" and session_id:
        agent_result = capture_agents_for_session(transcript_path, session_id)

    # Log the event
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event": "AUTO_CAPTURE",
        "trigger": trigger,
        "session_id": session_id,
        "project_path": cwd,
        "message_count": len(messages),
        "capture_result": result,
        "agent_capture_result": agent_result
    }
    log_capture(log_entry)

    # Output hook response
    if result["status"] == "success":
        # Build message with agent capture stats
        main_msg = f"✅ Conversation captured to memory ({len(messages)} messages) before compact."

        if agent_result and agent_result.get("status") == "success":
            stats = agent_result.get("stats", {})
            agents_captured = stats.get("agents_captured", 0)
            if agents_captured > 0:
                main_msg += f" {agents_captured} agent(s) also captured."

        output = {
            "systemMessage": main_msg,
            "hookSpecificOutput": {
                "hookEventName": "PreCompact",
                "additionalContext": f"Snapshot created. Trigger: {trigger}",
                "agentsCaptured": agent_result.get("stats", {}).get("agents_captured", 0) if agent_result else 0
            }
        }
    else:
        output = {
            "systemMessage": f"⚠️ Failed to capture conversation: {result.get('message', 'Unknown error')}",
            "hookSpecificOutput": {
                "hookEventName": "PreCompact",
                "error": result.get("message")
            }
        }

    print(json.dumps(output))
    sys.exit(0)

if __name__ == "__main__":
    main()
