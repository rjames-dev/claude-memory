#!/usr/bin/env python3
"""
Claude Memory - Agent Capture Module
Detects and captures agent work during auto-capture hooks.

This module:
1. Scans session directory for agent transcript files (agent-*.jsonl)
2. Extracts agent work and links to agent definitions
3. Links agent work to parent snapshot
4. Stores in database with full metadata
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Optional, Tuple
import psycopg2
from psycopg2.extras import Json

# Database configuration
def get_db_config():
    """Get database configuration from environment variables."""
    password = os.getenv('CONTEXT_DB_PASSWORD')
    if not password:
        raise ValueError(
            "CONTEXT_DB_PASSWORD environment variable required.\n"
            "Set in .env file and ensure it's loaded."
        )

    return {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_HOST_PORT', '5435')),
        'database': os.getenv('POSTGRES_DB', 'claude_memory'),
        'user': os.getenv('POSTGRES_USER', 'memory_admin'),
        'password': password
    }

def get_db_connection():
    """Get database connection."""
    config = get_db_config()
    return psycopg2.connect(**config)

def find_agent_transcripts(session_directory: str, min_size_bytes: int = 512) -> List[str]:
    """
    Find agent transcript files in the same session directory.

    Args:
        session_directory: Directory containing the main session transcript
        min_size_bytes: Minimum file size to consider (ignores abandoned agents)

    Returns:
        List of agent transcript paths
    """
    directory_path = Path(session_directory)

    if not directory_path.exists() or not directory_path.is_dir():
        return []

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

def parse_agent_transcript(transcript_path: str) -> List[dict]:
    """
    Parse agent transcript file (.jsonl format).

    Agent transcript format:
    {"agentId": "...", "type": "user|assistant", "message": {...}, "timestamp": "..."}

    Returns:
        List of message dictionaries
    """
    messages = []

    try:
        with open(transcript_path, 'r') as f:
            for line in f:
                try:
                    msg = json.loads(line)
                    messages.append(msg)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Error parsing agent transcript {transcript_path}: {e}", file=sys.stderr)
        return []

    return messages

def extract_agent_id(transcript_path: str) -> str:
    """Extract agent ID from filename (agent-{id}.jsonl)."""
    filename = Path(transcript_path).stem
    if filename.startswith('agent-'):
        return filename.replace('agent-', '')
    return filename

def extract_agent_request(messages: List[dict]) -> Optional[str]:
    """Extract the original agent request (first user message)."""
    for msg in messages:
        if msg.get('type') == 'user':
            message_obj = msg.get('message', {})
            if isinstance(message_obj, dict):
                content = message_obj.get('content')
                if isinstance(content, str):
                    return content
    return None

def extract_tools_used(messages: List[dict]) -> dict:
    """Extract and count tool usage from assistant messages."""
    from collections import Counter
    tools = Counter()

    for msg in messages:
        if msg.get('type') == 'assistant':
            message_obj = msg.get('message', {})
            if isinstance(message_obj, dict):
                content = message_obj.get('content', [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get('type') == 'tool_use':
                            tool_name = block.get('name')
                            if tool_name:
                                tools[tool_name] += 1

    return dict(tools)

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

    return list(set(files))

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

    return list(set(urls))

def extract_result_summary(messages: List[dict]) -> Optional[str]:
    """Extract the agent's final result (last assistant message)."""
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

def infer_agent_type(agent_request: Optional[str]) -> str:
    """Infer agent type from request (simple heuristic)."""
    if not agent_request:
        return "unknown"

    request_lower = agent_request.lower()

    # Check for common agent types
    if "explore" in request_lower or "find" in request_lower:
        return "Explore"
    elif "plan" in request_lower or "design" in request_lower:
        return "Plan"
    elif "warmup" in request_lower:
        return "Explore"  # Warmup agents are typically Explore type
    else:
        return "general-purpose"

def get_or_create_agent_definition(agent_type: str, tools_used: dict) -> int:
    """
    Get or create agent definition based on configuration.

    This is a simplified version that uses agent_type + tools_available for deduplication.
    For full implementation, import from store_agent_definition module.

    Returns:
        definition_id
    """
    import hashlib

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Generate simple config hash
        tools_available = list(tools_used.keys()) if tools_used else []
        config_str = json.dumps({
            'agent_type': agent_type,
            'tools_available': sorted(tools_available)
        }, sort_keys=True)
        config_hash = hashlib.sha256(config_str.encode()).hexdigest()

        # Check if definition exists
        cur.execute("""
            SELECT id FROM agent_definitions
            WHERE config_hash = %s
        """, (config_hash,))

        result = cur.fetchone()
        if result:
            return result[0]

        # Get next version number
        cur.execute("""
            SELECT COALESCE(MAX(version), 0) as max_version
            FROM agent_definitions
            WHERE agent_type = %s
        """, (agent_type,))

        max_version = cur.fetchone()[0]
        next_version = max_version + 1

        # Insert new definition
        cur.execute("""
            INSERT INTO agent_definitions (
                agent_type, tools_available, version,
                description, created_by, config_hash
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            agent_type,
            tools_available,
            next_version,
            f"Auto-detected from hook capture",
            'hook',
            config_hash
        ))

        definition_id = cur.fetchone()[0]
        conn.commit()

        return definition_id

    finally:
        cur.close()
        conn.close()

def store_agent_work(
    agent_id: str,
    agent_type: str,
    agent_request: str,
    agent_transcript_path: str,
    work_context: List[dict],
    tools_used: dict,
    files_examined: List[str],
    urls_fetched: List[str],
    result_summary: Optional[str],
    agent_definition_id: int,
    parent_snapshot_id: int,
    parent_session_id: str
) -> int:
    """
    Store agent work in database.

    Returns:
        agent_work_id
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        request_id = f"{parent_session_id}-{agent_id}"

        cur.execute("""
            INSERT INTO agent_work (
                request_id, parent_snapshot_id, parent_session_id,
                agent_definition_id, agent_id, agent_type,
                agent_request, agent_transcript_path, work_context,
                tools_used, files_examined, urls_fetched, result_summary
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (agent_id, parent_session_id) DO NOTHING
            RETURNING id
        """, (
            request_id, parent_snapshot_id, parent_session_id,
            agent_definition_id, agent_id, agent_type,
            agent_request, agent_transcript_path, Json(work_context),
            Json(tools_used), files_examined, urls_fetched, result_summary
        ))

        result = cur.fetchone()
        if result:
            work_id = result[0]
            conn.commit()
            return work_id
        else:
            # Already exists
            cur.execute("""
                SELECT id FROM agent_work
                WHERE agent_id = %s AND parent_session_id = %s
            """, (agent_id, parent_session_id))
            return cur.fetchone()[0]

    finally:
        cur.close()
        conn.close()

def capture_agents(session_directory: str, parent_snapshot_id: int, parent_session_id: str) -> dict:
    """
    Main function to capture all agent work from a session.

    Args:
        session_directory: Directory containing agent transcripts
        parent_snapshot_id: ID of the parent context snapshot
        parent_session_id: Session ID from the parent conversation

    Returns:
        Dict with capture statistics
    """
    stats = {
        'agents_found': 0,
        'agents_captured': 0,
        'agents_skipped': 0,
        'errors': []
    }

    # Find agent transcripts
    agent_files = find_agent_transcripts(session_directory)
    stats['agents_found'] = len(agent_files)

    if not agent_files:
        return stats

    # Process each agent
    for agent_path in agent_files:
        try:
            # Parse transcript
            messages = parse_agent_transcript(agent_path)
            if not messages:
                stats['agents_skipped'] += 1
                continue

            # Extract agent work data
            agent_id = extract_agent_id(agent_path)
            agent_request = extract_agent_request(messages) or "No request captured"
            tools_used = extract_tools_used(messages)
            files_examined = extract_files_examined(messages)
            urls_fetched = extract_urls_fetched(messages)
            result_summary = extract_result_summary(messages)
            work_context = convert_messages_to_work_context(messages)
            agent_type = infer_agent_type(agent_request)

            # Get or create agent definition
            agent_definition_id = get_or_create_agent_definition(agent_type, tools_used)

            # Store agent work
            work_id = store_agent_work(
                agent_id=agent_id,
                agent_type=agent_type,
                agent_request=agent_request,
                agent_transcript_path=agent_path,
                work_context=work_context,
                tools_used=tools_used,
                files_examined=files_examined,
                urls_fetched=urls_fetched,
                result_summary=result_summary,
                agent_definition_id=agent_definition_id,
                parent_snapshot_id=parent_snapshot_id,
                parent_session_id=parent_session_id
            )

            stats['agents_captured'] += 1

        except Exception as e:
            stats['errors'].append(f"{Path(agent_path).name}: {str(e)}")
            continue

    return stats
