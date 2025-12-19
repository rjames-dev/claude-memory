#!/usr/bin/env python3
"""
Claude Memory - Agent Definition Extractor
Extracts agent configuration from Claude Code agent transcripts.

Usage:
    python3 extract-agent-definition.py <agent-transcript.jsonl>
"""

import json
import sys
import hashlib
from pathlib import Path
from collections import Counter
from typing import Dict, List, Optional, Set

def extract_agent_id(transcript_path: str) -> str:
    """Extract agent ID from filename (agent-{id}.jsonl)."""
    filename = Path(transcript_path).stem
    if filename.startswith('agent-'):
        return filename.replace('agent-', '')
    return filename

def extract_model_used(messages: List[dict]) -> Optional[str]:
    """Extract model name from assistant messages."""
    for msg in messages:
        if msg.get('type') == 'assistant':
            message_obj = msg.get('message', {})
            if isinstance(message_obj, dict):
                model = message_obj.get('model')
                if model:
                    return model
    return None

def extract_tools_used(messages: List[dict]) -> Counter:
    """Extract and count tool usage from assistant messages."""
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

    return tools

def get_tools_available(tools_used: Counter) -> List[str]:
    """Get list of tools that were available to the agent."""
    # Return sorted list of unique tools used
    return sorted(tools_used.keys())

def extract_agent_request(messages: List[dict]) -> Optional[str]:
    """Extract the initial task/request given to the agent (first user message)."""
    for msg in messages:
        if msg.get('type') == 'user':
            message_obj = msg.get('message', {})
            if isinstance(message_obj, dict):
                content = message_obj.get('content')
                if isinstance(content, str):
                    return content
    return None

def extract_agent_self_description(messages: List[dict]) -> Optional[str]:
    """Extract agent's self-description from first assistant message."""
    for msg in messages:
        if msg.get('type') == 'assistant':
            message_obj = msg.get('message', {})
            if isinstance(message_obj, dict):
                content = message_obj.get('content', [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get('type') == 'text':
                            text = block.get('text', '')
                            # Look for self-description indicators
                            if any(indicator in text.lower() for indicator in [
                                "i'm ready", "i understand", "i can", "my tools",
                                "read-only mode", "i have access to"
                            ]):
                                return text[:500]  # First 500 chars
    return None

def infer_agent_type(agent_request: Optional[str], self_description: Optional[str]) -> str:
    """Infer agent type from request and self-description."""
    if not agent_request and not self_description:
        return "general-purpose"

    text = (agent_request or "") + " " + (self_description or "")
    text_lower = text.lower()

    # Pattern matching for common agent types
    if any(word in text_lower for word in ["explore", "find", "search", "locate"]):
        return "Explore"
    elif any(word in text_lower for word in ["plan", "design", "architect", "strategy"]):
        return "Plan"
    elif any(word in text_lower for word in ["fetch", "scrape", "download", "retrieve url"]):
        return "WebFetch"
    elif "read-only" in text_lower or "readonly" in text_lower:
        return "ReadOnly"
    else:
        return "general-purpose"

def generate_config_hash(agent_type: str, model_used: str, tools_available: List[str]) -> str:
    """Generate SHA256 hash for agent configuration (for deduplication)."""
    # Create a deterministic string representation
    config_str = json.dumps({
        'agent_type': agent_type,
        'model_used': model_used,
        'tools_available': sorted(tools_available)  # Sort for consistency
    }, sort_keys=True)

    return hashlib.sha256(config_str.encode()).hexdigest()

def extract_configuration_params(messages: List[dict], tools_used: Counter) -> Dict:
    """Extract or infer configuration parameters."""
    params = {}

    # Tool usage stats
    params['tools_used_count'] = len(tools_used)
    params['total_tool_calls'] = sum(tools_used.values())

    # Count message exchanges
    user_msgs = sum(1 for m in messages if m.get('type') == 'user')
    assistant_msgs = sum(1 for m in messages if m.get('type') == 'assistant')
    params['conversation_turns'] = user_msgs

    # Detect if agent had errors (presence of error blocks)
    had_errors = False
    for msg in messages:
        if msg.get('type') == 'assistant':
            message_obj = msg.get('message', {})
            if isinstance(message_obj, dict):
                content = message_obj.get('content', [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get('type') == 'tool_result':
                            if block.get('is_error'):
                                had_errors = True
                                break

    params['had_tool_errors'] = had_errors

    return params

def parse_transcript(transcript_path: str) -> List[dict]:
    """Parse agent transcript JSONL file."""
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
        print(f"Error parsing transcript: {e}", file=sys.stderr)
        return []

    return messages

def extract_agent_definition(transcript_path: str) -> Dict:
    """
    Extract complete agent definition from transcript.

    Returns dict with:
        - agent_id
        - agent_type
        - model_used
        - tools_available
        - configuration_params
        - system_message (inferred from self-description)
        - config_hash
        - agent_request
    """
    messages = parse_transcript(transcript_path)
    if not messages:
        raise ValueError(f"No messages found in transcript: {transcript_path}")

    # Extract components
    agent_id = extract_agent_id(transcript_path)
    model_used = extract_model_used(messages)
    tools_used = extract_tools_used(messages)
    tools_available = get_tools_available(tools_used)
    agent_request = extract_agent_request(messages)
    self_description = extract_agent_self_description(messages)
    agent_type = infer_agent_type(agent_request, self_description)
    configuration_params = extract_configuration_params(messages, tools_used)

    # Generate config hash
    config_hash = generate_config_hash(
        agent_type,
        model_used or "unknown",
        tools_available
    )

    return {
        'agent_id': agent_id,
        'agent_type': agent_type,
        'model_used': model_used,
        'tools_available': tools_available,
        'configuration_params': configuration_params,
        'system_message': self_description,  # Use self-description as system message
        'config_hash': config_hash,
        'agent_request': agent_request
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 extract-agent-definition.py <agent-transcript.jsonl>", file=sys.stderr)
        sys.exit(1)

    transcript_path = sys.argv[1]

    if not Path(transcript_path).exists():
        print(f"Error: File not found: {transcript_path}", file=sys.stderr)
        sys.exit(1)

    try:
        definition = extract_agent_definition(transcript_path)

        # Pretty print the extracted definition
        print(json.dumps(definition, indent=2))

    except Exception as e:
        print(f"Error extracting agent definition: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
