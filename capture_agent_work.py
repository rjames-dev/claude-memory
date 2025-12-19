#!/usr/bin/env python3
"""
Claude Memory - Agent Work Capture
Scans for agent transcripts and captures agent work with linkage to definitions.

Usage:
    python3 capture_agent_work.py <parent-session-id> <project-path>

    Or scan all agents in a directory:
    python3 capture_agent_work.py --scan ~/.claude/projects/...
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import psycopg2
from psycopg2.extras import Json

# Import our existing modules
from extract_agent_definition import (
    extract_agent_id,
    extract_model_used,
    extract_tools_used,
    get_tools_available,
    extract_agent_request,
    extract_agent_self_description,
    infer_agent_type,
    generate_config_hash,
    extract_configuration_params,
    parse_transcript
)
from store_agent_definition import get_or_create_agent_definition, get_db_connection

def scan_agent_transcripts(directory: str, min_size_bytes: int = 512) -> List[str]:
    """
    Scan directory for agent transcript files.

    Args:
        directory: Path to search for agent-*.jsonl files
        min_size_bytes: Minimum file size to consider (ignore empty/abandoned agents)

    Returns:
        List of agent transcript paths
    """
    directory_path = Path(directory)

    if not directory_path.exists():
        raise ValueError(f"Directory not found: {directory}")

    agent_files = []

    for jsonl_file in directory_path.glob("agent-*.jsonl"):
        try:
            file_size = jsonl_file.stat().st_size
            if file_size >= min_size_bytes:
                agent_files.append(str(jsonl_file))
        except Exception:
            continue

    # Sort by modification time (most recent first)
    agent_files.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)

    return agent_files

def extract_files_examined(messages: List[dict]) -> List[str]:
    """Extract all files the agent read."""
    files = []

    for msg in messages:
        if msg.get('type') == 'assistant':
            message_obj = msg.get('message', {})
            if isinstance(message_obj, dict):
                content = message_obj.get('content', [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get('type') == 'tool_use':
                            if block.get('name') == 'Read':
                                file_path = block.get('input', {}).get('file_path')
                                if file_path:
                                    files.append(file_path)

    return list(set(files))  # Deduplicate

def extract_urls_fetched(messages: List[dict]) -> List[str]:
    """Extract all URLs the agent fetched."""
    urls = []

    for msg in messages:
        if msg.get('type') == 'assistant':
            message_obj = msg.get('message', {})
            if isinstance(message_obj, dict):
                content = message_obj.get('content', [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get('type') == 'tool_use':
                            if block.get('name') == 'WebFetch':
                                url = block.get('input', {}).get('url')
                                if url:
                                    urls.append(url)

    return list(set(urls))  # Deduplicate

def extract_result_summary(messages: List[dict]) -> Optional[str]:
    """Extract the agent's final result (last assistant message)."""
    # Get last assistant message
    for msg in reversed(messages):
        if msg.get('type') == 'assistant':
            message_obj = msg.get('message', {})
            if isinstance(message_obj, dict):
                content = message_obj.get('content', [])
                if isinstance(content, list):
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get('type') == 'text':
                            text_parts.append(block.get('text', ''))

                    if text_parts:
                        result = ''.join(text_parts)
                        return result[:1000]  # First 1000 chars

    return None

def extract_timestamps(messages: List[dict]) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Extract start and end timestamps from messages."""
    timestamps = []

    for msg in messages:
        ts = msg.get('timestamp')
        if ts:
            try:
                timestamps.append(datetime.fromisoformat(ts.replace('Z', '+00:00')))
            except Exception:
                continue

    if not timestamps:
        return None, None

    return min(timestamps), max(timestamps)

def convert_messages_to_work_context(messages: List[dict]) -> List[dict]:
    """Convert agent transcript messages to work_context format (role/content)."""
    work_context = []

    for msg in messages:
        if msg.get('type') == 'user':
            message_obj = msg.get('message', {})
            if isinstance(message_obj, dict):
                content = message_obj.get('content')
                if isinstance(content, str):
                    work_context.append({
                        'role': 'user',
                        'content': content
                    })

        elif msg.get('type') == 'assistant':
            message_obj = msg.get('message', {})
            if isinstance(message_obj, dict):
                content = message_obj.get('content', [])
                if isinstance(content, list):
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get('type') == 'text':
                            text_parts.append(block.get('text', ''))

                    if text_parts:
                        work_context.append({
                            'role': 'assistant',
                            'content': ''.join(text_parts)
                        })

    return work_context

def extract_agent_work(transcript_path: str) -> Dict:
    """
    Extract complete agent work data from transcript.

    Returns dict with:
        - agent_id
        - agent_type
        - agent_request
        - work_context (messages in role/content format)
        - tools_used (counter dict)
        - files_examined
        - urls_fetched
        - result_summary
        - timestamp_start
        - timestamp_end
    """
    messages = parse_transcript(transcript_path)
    if not messages:
        raise ValueError(f"No messages found in transcript: {transcript_path}")

    # Extract all components
    agent_id = extract_agent_id(transcript_path)
    agent_request = extract_agent_request(messages)
    tools_used = extract_tools_used(messages)
    files_examined = extract_files_examined(messages)
    urls_fetched = extract_urls_fetched(messages)
    result_summary = extract_result_summary(messages)
    timestamp_start, timestamp_end = extract_timestamps(messages)
    work_context = convert_messages_to_work_context(messages)

    # Infer agent type
    self_description = extract_agent_self_description(messages)
    agent_type = infer_agent_type(agent_request, self_description)

    return {
        'agent_id': agent_id,
        'agent_type': agent_type,
        'agent_request': agent_request or "No request captured",
        'agent_transcript_path': str(transcript_path),
        'work_context': work_context,
        'tools_used': dict(tools_used),  # Convert Counter to dict
        'files_examined': files_examined,
        'urls_fetched': urls_fetched,
        'result_summary': result_summary,
        'timestamp_start': timestamp_start,
        'timestamp_end': timestamp_end
    }

def check_already_captured(agent_id: str, parent_session_id: str) -> bool:
    """Check if this agent work has already been captured."""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id FROM agent_work
            WHERE agent_id = %s AND parent_session_id = %s
        """, (agent_id, parent_session_id))

        result = cur.fetchone()
        return result is not None

    finally:
        cur.close()
        conn.close()

def store_agent_work(
    agent_work: Dict,
    agent_definition_id: int,
    parent_snapshot_id: Optional[int],
    parent_session_id: str
) -> int:
    """
    Store agent work in database.

    Args:
        agent_work: Dict with agent work data
        agent_definition_id: FK to agent_definitions
        parent_snapshot_id: FK to context_snapshots (optional)
        parent_session_id: Parent session identifier

    Returns:
        agent_work_id: ID of inserted/existing agent work record
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Generate request_id
        request_id = f"{parent_session_id}-{agent_work['agent_id']}"

        # Insert agent work
        cur.execute("""
            INSERT INTO agent_work (
                request_id,
                parent_snapshot_id,
                parent_session_id,
                agent_definition_id,
                agent_id,
                agent_type,
                agent_request,
                agent_transcript_path,
                work_context,
                tools_used,
                files_examined,
                urls_fetched,
                result_summary,
                timestamp_start,
                timestamp_end
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (agent_id, parent_session_id) DO NOTHING
            RETURNING id
        """, (
            request_id,
            parent_snapshot_id,
            parent_session_id,
            agent_definition_id,
            agent_work['agent_id'],
            agent_work['agent_type'],
            agent_work['agent_request'],
            agent_work['agent_transcript_path'],
            Json(agent_work['work_context']),
            Json(agent_work['tools_used']),
            agent_work['files_examined'],
            agent_work['urls_fetched'],
            agent_work['result_summary'],
            agent_work['timestamp_start'],
            agent_work['timestamp_end']
        ))

        result = cur.fetchone()

        if result:
            work_id = result[0]
            conn.commit()
            return work_id
        else:
            # Already exists (ON CONFLICT triggered)
            cur.execute("""
                SELECT id FROM agent_work
                WHERE agent_id = %s AND parent_session_id = %s
            """, (agent_work['agent_id'], parent_session_id))

            return cur.fetchone()[0]

    except Exception as e:
        conn.rollback()
        raise Exception(f"Database error storing agent work: {e}")

    finally:
        cur.close()
        conn.close()

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 capture_agent_work.py --scan <directory>", file=sys.stderr)
        print("   or: python3 capture_agent_work.py <parent-session-id> <project-path>", file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] == '--scan':
        if len(sys.argv) < 3:
            print("Error: --scan requires directory path", file=sys.stderr)
            sys.exit(1)

        directory = sys.argv[2]
        parent_session_id = "scan-" + datetime.now().strftime('%Y%m%d-%H%M%S')

        print(f"🔍 Scanning for agent transcripts in: {directory}", file=sys.stderr)
        agent_files = scan_agent_transcripts(directory)

        print(f"✅ Found {len(agent_files)} agent transcripts", file=sys.stderr)
        print(file=sys.stderr)

        captured_count = 0
        skipped_count = 0

        for agent_path in agent_files:
            try:
                agent_filename = Path(agent_path).name

                # Check if already captured
                agent_id = extract_agent_id(agent_path)
                if check_already_captured(agent_id, parent_session_id):
                    print(f"⏭️  Skipped (already captured): {agent_filename}", file=sys.stderr)
                    skipped_count += 1
                    continue

                print(f"📖 Processing: {agent_filename}", file=sys.stderr)

                # Extract agent work
                agent_work = extract_agent_work(agent_path)

                # Extract and store agent definition
                messages = parse_transcript(agent_path)
                model_used = extract_model_used(messages)
                tools_available = get_tools_available(extract_tools_used(messages))
                config_hash = generate_config_hash(
                    agent_work['agent_type'],
                    model_used or "unknown",
                    tools_available
                )

                definition = {
                    'agent_type': agent_work['agent_type'],
                    'model_used': model_used,
                    'tools_available': tools_available,
                    'configuration_params': extract_configuration_params(messages, extract_tools_used(messages)),
                    'system_message': extract_agent_self_description(messages),
                    'config_hash': config_hash
                }

                definition_id = get_or_create_agent_definition(definition)

                # Store agent work
                work_id = store_agent_work(
                    agent_work,
                    definition_id,
                    None,  # No parent snapshot for scan mode
                    parent_session_id
                )

                print(f"   ✅ Captured agent work (ID: {work_id}, Definition: {definition_id})", file=sys.stderr)
                print(f"      Tools: {', '.join(agent_work['tools_used'].keys()) if agent_work['tools_used'] else 'None'}", file=sys.stderr)
                print(f"      Files: {len(agent_work['files_examined'])} examined", file=sys.stderr)
                print(f"      URLs: {len(agent_work['urls_fetched'])} fetched", file=sys.stderr)
                print(file=sys.stderr)

                captured_count += 1

            except Exception as e:
                print(f"   ❌ Error: {e}", file=sys.stderr)
                print(file=sys.stderr)
                continue

        print("=" * 60, file=sys.stderr)
        print(f"Summary: {captured_count} captured, {skipped_count} skipped", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

    else:
        print("Error: Only --scan mode is implemented", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
