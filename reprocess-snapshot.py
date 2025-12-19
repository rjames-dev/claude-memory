#!/usr/bin/env python3
"""
Claude Memory - Reprocess Snapshot

Retroactively reprocess a snapshot to fix AI summary and metadata extraction.
Useful for fixing snapshots that were captured with wrong message format.

Usage:
    python3 reprocess-snapshot.py <snapshot_id>
    python3 reprocess-snapshot.py 26
"""

import os
import sys
import json
import requests
import psycopg2
from pathlib import Path

# Configuration
PROCESSOR_URL = os.getenv("CLAUDE_MEMORY_PROCESSOR_URL", "http://localhost:3200")
CAPTURE_ENDPOINT = f"{PROCESSOR_URL}/capture"

# Database connection
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5435")
DB_NAME = os.getenv("DB_NAME", "claude_memory")
DB_USER = os.getenv("DB_USER", "memory_admin")
DB_PASS = os.getenv("DB_PASS", "RvnK7z05jIlgo4FIf4dvpvWhSl4lnOtWQgH0a9gEzVE=")

def get_snapshot(snapshot_id):
    """Fetch snapshot from database"""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                id, session_id, project_path, trigger_event, transcript_path,
                raw_context, summary
            FROM context_snapshots
            WHERE id = %s
        """, (snapshot_id,))

        row = cursor.fetchone()
        if not row:
            return None

        return {
            'id': row[0],
            'session_id': row[1],
            'project_path': row[2],
            'trigger_event': row[3],
            'transcript_path': row[4],
            'raw_context': row[5],
            'old_summary': row[6]
        }
    finally:
        conn.close()

def convert_to_openai_format(claude_messages):
    """
    Convert Claude Code .jsonl format to OpenAI format (role/content).

    Args:
        claude_messages: Raw messages from Claude Code transcript or database

    Returns:
        list: Messages in OpenAI format [{"role": "user", "content": "..."}]
    """
    # If messages is already a dict with 'messages' key, extract it
    if isinstance(claude_messages, dict) and 'messages' in claude_messages:
        claude_messages = claude_messages['messages']

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

def reprocess_snapshot(snapshot_id):
    """Reprocess a snapshot with correct message format"""

    print(f"🔄 Reprocessing snapshot #{snapshot_id}")
    print("=" * 60)
    print()

    # Step 1: Fetch snapshot from database
    print("📂 Fetching snapshot from database...")
    snapshot = get_snapshot(snapshot_id)

    if not snapshot:
        print(f"❌ Error: Snapshot #{snapshot_id} not found")
        sys.exit(1)

    print(f"✅ Found snapshot:")
    print(f"   ID: {snapshot['id']}")
    print(f"   Session: {snapshot['session_id']}")
    print(f"   Project: {snapshot['project_path']}")
    print(f"   Trigger: {snapshot['trigger_event']}")
    print(f"   Old summary length: {len(snapshot['old_summary'])} chars")
    print()

    # Step 2: Convert messages to OpenAI format
    print("🔄 Converting messages to OpenAI format...")
    raw_context = snapshot['raw_context']

    # raw_context is JSONB, might be dict or already parsed
    if isinstance(raw_context, str):
        raw_context = json.loads(raw_context)

    messages = raw_context.get('messages', []) if isinstance(raw_context, dict) else raw_context

    print(f"   Raw entries: {len(messages)}")

    converted_messages = convert_to_openai_format(messages)

    print(f"   Converted messages: {len(converted_messages)}")

    if len(converted_messages) == 0:
        print("⚠️  Warning: No conversation messages found")
        print("   Snapshot may only contain metadata/system entries")
        sys.exit(1)

    print()

    # Step 3: Send to processor for reprocessing
    print("🚀 Sending to processor for AI reprocessing...")

    request_data = {
        "project_path": snapshot['project_path'],
        "trigger": f"{snapshot['trigger_event']}-reprocessed",
        "session_id": snapshot['session_id'],
        "transcript_path": snapshot['transcript_path'],
        "conversation_data": {
            "messages": converted_messages
        }
    }

    try:
        response = requests.post(
            CAPTURE_ENDPOINT,
            json=request_data,
            timeout=60
        )
        response.raise_for_status()
        result = response.json()

        print(f"✅ {result['message']}")
        print()
        print("📊 Reprocessing Summary:")
        print(f"   Status: {result['status']}")
        print(f"   Messages sent: {len(converted_messages)}")
        print()
        print("⏳ Processing in background...")
        print("   The snapshot will be updated with new summary & metadata")
        print()
        print("✨ Done! Check database in ~30 seconds for updated content")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error: Failed to send to processor: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 reprocess-snapshot.py <snapshot_id>")
        print()
        print("Example:")
        print("  python3 reprocess-snapshot.py 26")
        sys.exit(1)

    try:
        snapshot_id = int(sys.argv[1])
    except ValueError:
        print("❌ Error: snapshot_id must be a number")
        sys.exit(1)

    reprocess_snapshot(snapshot_id)

if __name__ == '__main__':
    main()
