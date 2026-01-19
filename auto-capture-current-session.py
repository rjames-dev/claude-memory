#!/usr/bin/env python3
"""
Claude Memory - Auto-Capture Current Session

Automatically detects and captures the current Claude Code session to the database.
No manual file paths required - everything is auto-detected.

Usage:
    python3 auto-capture-current-session.py
    python3 auto-capture-current-session.py --project /path/to/project

    Or from slash command:
    /context
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path
from datetime import datetime

# Configuration
PROCESSOR_URL = os.getenv("CLAUDE_MEMORY_PROCESSOR_URL", "http://localhost:3200")
CAPTURE_ENDPOINT = f"{PROCESSOR_URL}/capture"
# MESSAGE_LIMIT removed - Phase 6C intelligent sampling handles large conversations

def detect_current_session(project_path=None):
    """
    Detect current Claude Code session transcript.

    Args:
        project_path: Optional explicit project path. If not provided, uses cwd.

    Returns:
        dict: Session information including transcript_path, session_id, project_path
    """
    # Get project directory - use explicit path if provided, otherwise cwd
    cwd = project_path if project_path else os.getcwd()

    # Encode project path (replace / and spaces with -)
    # Claude Code encoding: both forward slashes and spaces become hyphens
    encoded_path = cwd.replace('/', '-').replace(' ', '-')

    # Build project directory path
    project_dir = Path.home() / '.claude' / 'projects' / encoded_path

    # Check if project directory exists
    if not project_dir.exists():
        raise FileNotFoundError(f"No Claude Code project found for: {cwd}")

    # Find all .jsonl files
    transcript_files = list(project_dir.glob('*.jsonl'))

    if not transcript_files:
        raise FileNotFoundError(f"No session transcripts found in: {project_dir}")

    # Get most recently modified transcript (current active session)
    transcript_path = max(transcript_files, key=lambda p: p.stat().st_mtime)

    # Extract session ID (filename without extension)
    session_id = transcript_path.stem

    return {
        'transcript_path': str(transcript_path),
        'session_id': session_id,
        'project_path': cwd,
        'encoded_path': encoded_path,
        'file_size': transcript_path.stat().st_size,
        'modified_time': datetime.fromtimestamp(transcript_path.stat().st_mtime).isoformat()
    }

def read_transcript(transcript_path):
    """
    Read and parse Claude Code transcript file.

    Args:
        transcript_path: Path to .jsonl transcript file

    Returns:
        list: Parsed messages from transcript
    """
    messages = []

    with open(transcript_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    msg = json.loads(line)
                    messages.append(msg)
                except json.JSONDecodeError:
                    # Skip malformed lines
                    continue

    return messages

def convert_to_openai_format(claude_messages):
    """
    Convert Claude Code .jsonl format to OpenAI format (role/content).

    Claude Code messages have a nested 'message' field with role/content.
    This function extracts and normalizes them for the AI summarizer.

    Args:
        claude_messages: Raw messages from Claude Code transcript

    Returns:
        list: Messages in OpenAI format [{"role": "user", "content": "..."}]
    """
    converted = []

    for msg in claude_messages:
        # Check if this is a conversation message (has 'message' field with 'role')
        if isinstance(msg, dict) and 'message' in msg:
            message_obj = msg['message']

            if isinstance(message_obj, dict) and 'role' in message_obj:
                role = message_obj.get('role')
                content = message_obj.get('content')

                # Handle user messages (content is a string)
                if role == 'user' and isinstance(content, str):
                    converted.append({
                        'role': 'user',
                        'content': content
                    })

                # Handle assistant messages (content is an array of blocks)
                elif role == 'assistant':
                    if isinstance(content, list):
                        # Extract text from content blocks
                        text_parts = []
                        for block in content:
                            if isinstance(block, dict):
                                if block.get('type') == 'text':
                                    text_parts.append(block.get('text', ''))
                                elif block.get('type') == 'thinking':
                                    # Optionally include thinking blocks (commented out for now)
                                    # text_parts.append(f"[Thinking: {block.get('thinking', '')}]")
                                    pass

                        if text_parts:
                            converted.append({
                                'role': 'assistant',
                                'content': '\n\n'.join(text_parts)
                            })
                    elif isinstance(content, str):
                        # Some assistant messages might have string content
                        converted.append({
                            'role': 'assistant',
                            'content': content
                        })

    return converted

def capture_session(session_info, messages):
    """
    Send session to claude-memory processor for capture.

    Args:
        session_info: Dict with session details
        messages: List of conversation messages (raw Claude Code format)

    Returns:
        dict: Processor response
    """
    # Create trigger identifier
    trigger = f"auto-capture-{session_info['session_id'][:8]}-{datetime.now().strftime('%Y-%m-%d')}"

    # Convert Claude Code format to OpenAI format for AI processing
    converted_messages = convert_to_openai_format(messages)

    # Phase 6C: No artificial limit - intelligent sampling handles large conversations
    # Prepare capture request
    request_data = {
        "project_path": session_info['project_path'],
        "trigger": trigger,
        "session_id": session_info['session_id'],
        "transcript_path": session_info['transcript_path'],
        "conversation_data": {
            "messages": converted_messages
        }
    }

    # Send to processor
    response = requests.post(
        CAPTURE_ENDPOINT,
        json=request_data,
        timeout=30
    )

    response.raise_for_status()
    return response.json()

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description='Auto-capture current Claude Code session to database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Capture current directory's session
  python3 auto-capture-current-session.py

  # Capture specific project's session
  python3 auto-capture-current-session.py --project /path/to/project
        """
    )
    parser.add_argument(
        '--project',
        type=str,
        default=None,
        help='Explicit project path (default: current working directory)'
    )

    args = parser.parse_args()

    print("🔍 Claude Memory - Auto-Capture Current Session", flush=True)
    print("=" * 60, flush=True)
    print(flush=True)

    try:
        # Step 1: Detect current session
        print("📂 Detecting current session...", flush=True)
        if args.project:
            print(f"   Using explicit project path: {args.project}", flush=True)
        session_info = detect_current_session(project_path=args.project)

        print(f"✅ Found active session:", flush=True)
        print(f"   Session ID: {session_info['session_id']}", flush=True)
        print(f"   Project: {session_info['project_path']}", flush=True)
        print(f"   Transcript: {Path(session_info['transcript_path']).name}", flush=True)
        print(f"   File size: {session_info['file_size']:,} bytes", flush=True)
        print(flush=True)

        # Step 2: Read transcript
        print("📖 Reading transcript...", flush=True)
        messages = read_transcript(session_info['transcript_path'])
        print(f"✅ Loaded {len(messages)} raw transcript entries", flush=True)

        # Step 2.5: Convert to OpenAI format
        print("🔄 Converting to conversation format...", flush=True)
        converted_messages = convert_to_openai_format(messages)
        print(f"✅ Extracted {len(converted_messages)} conversation messages", flush=True)

        if len(converted_messages) == 0:
            print("⚠️  Warning: No conversation messages found in transcript", flush=True)
            print("   This transcript may only contain system/metadata entries", flush=True)
            sys.exit(1)

        print(flush=True)

        # Step 3: Capture to database
        print("🚀 Sending to claude-memory processor...", flush=True)
        result = capture_session(session_info, messages)

        print(f"✅ {result['message']}", flush=True)
        print(flush=True)
        print("📊 Capture Summary:", flush=True)
        print(f"   Status: {result['status']}", flush=True)
        print(f"   Project: {result['project_path']}", flush=True)
        print(f"   Trigger: {result['trigger']}", flush=True)
        print(f"   Messages captured: {len(converted_messages)}", flush=True)
        print(f"   Raw transcript entries: {len(messages)}", flush=True)
        print(flush=True)
        print("⏳ Processing in background (summary + embeddings)...", flush=True)
        print("   Check dashboard: http://localhost:3200/dashboard", flush=True)
        print("   Or terminal: npm run monitor", flush=True)
        print(flush=True)
        print("✨ Done!", flush=True)

    except FileNotFoundError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        print()
        print("💡 Troubleshooting:")
        print("   • Make sure you're running this from a Claude Code project directory")
        print("   • Verify Claude Code has created a session in this project")
        print("   • Check: ls ~/.claude/projects/")
        sys.exit(1)

    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to claude-memory processor", file=sys.stderr)
        print()
        print("💡 Troubleshooting:")
        print("   • Is the processor running? docker compose ps")
        print("   • Check health: curl http://localhost:3200/health")
        print("   • Start processor: docker compose up -d")
        sys.exit(1)

    except requests.exceptions.Timeout:
        print("❌ Error: Processor request timed out", file=sys.stderr)
        print()
        print("💡 Troubleshooting:")
        print("   • Large conversation may take longer to process")
        print("   • Check processor logs: docker compose logs context-processor")
        print("   • Capture may still complete in background")
        sys.exit(1)

    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        print()
        print("💡 Check processor logs:")
        print("   docker compose logs context-processor --tail=50")
        sys.exit(1)

if __name__ == '__main__':
    main()
