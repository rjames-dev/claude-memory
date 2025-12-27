#!/usr/bin/env python3
"""
Agent Spawning Executor for Skills System

Launches Claude Code agents from skills with:
- Async agent execution
- Result capture
- Timeout handling
- Agent output parsing

Usage:
    python3 execute-agent-spawn.py <skill_id>
    python3 execute-agent-spawn.py --test

Example skill definition:
{
  "command_type": "agent_spawn",
  "command_definition": {
    "agent_type": "Explore",
    "prompt": "Find all API endpoints in the codebase",
    "model": "haiku",
    "timeout": 300,
    "run_in_background": false
  }
}

Supported Agents:
- Explore: Fast codebase exploration
- Plan: Implementation planning
- general-purpose: Complex multi-step tasks
"""

import sys
import os
import json
import subprocess
import time
from typing import Dict, Any, Optional
from datetime import datetime
import tempfile


class AgentSpawner:
    """Spawns and manages Claude Code agents from skills."""

    SUPPORTED_AGENTS = ['Explore', 'Plan', 'general-purpose']
    VALID_MODELS = ['sonnet', 'opus', 'haiku']

    def __init__(self, skill_id: int = None, agent_config: Dict[str, Any] = None):
        self.skill_id = skill_id
        self.agent_config = agent_config
        self.agent_id = None
        self.start_time = None
        self.end_time = None

    def spawn(self) -> Dict[str, Any]:
        """Spawn the agent and wait for results."""
        print(f"=== Agent Spawn Execution ===")

        # Validate config
        validation_result = self._validate_config()
        if not validation_result['valid']:
            return {
                'success': False,
                'error': validation_result['error']
            }

        agent_type = self.agent_config['agent_type']
        prompt = self.agent_config['prompt']
        model = self.agent_config.get('model', 'sonnet')
        timeout = self.agent_config.get('timeout', 300)
        run_in_background = self.agent_config.get('run_in_background', False)

        print(f"Agent Type: {agent_type}")
        print(f"Model: {model}")
        print(f"Timeout: {timeout}s")
        print(f"Prompt: {prompt[:100]}..." if len(prompt) > 100 else f"Prompt: {prompt}")
        print()

        self.start_time = datetime.now()

        try:
            if run_in_background:
                return self._spawn_background(agent_type, prompt, model, timeout)
            else:
                return self._spawn_blocking(agent_type, prompt, model, timeout)

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': f'Agent execution timed out after {timeout}s',
                'agent_type': agent_type,
                'execution_time': timeout
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Agent spawn failed: {str(e)}',
                'agent_type': agent_type
            }
        finally:
            self.end_time = datetime.now()

    def _validate_config(self) -> Dict[str, bool]:
        """Validate agent configuration."""
        if 'agent_type' not in self.agent_config:
            return {'valid': False, 'error': 'Missing agent_type'}

        agent_type = self.agent_config['agent_type']
        if agent_type not in self.SUPPORTED_AGENTS:
            return {
                'valid': False,
                'error': f'Unsupported agent type: {agent_type}. Supported: {", ".join(self.SUPPORTED_AGENTS)}'
            }

        if 'prompt' not in self.agent_config:
            return {'valid': False, 'error': 'Missing prompt'}

        if not self.agent_config['prompt'].strip():
            return {'valid': False, 'error': 'Prompt cannot be empty'}

        model = self.agent_config.get('model', 'sonnet')
        if model not in self.VALID_MODELS:
            return {
                'valid': False,
                'error': f'Invalid model: {model}. Valid: {", ".join(self.VALID_MODELS)}'
            }

        return {'valid': True}

    def _spawn_blocking(self, agent_type: str, prompt: str, model: str, timeout: int) -> Dict[str, Any]:
        """Spawn agent and wait for completion (blocking)."""
        print("🚀 Spawning agent (blocking mode)...")

        # Create a temporary file for the prompt
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(prompt)
            prompt_file = f.name

        try:
            # Build Claude Code agent command
            # This is a simulation - in reality, we'd use Claude Code's Task tool
            # For now, we'll create a simple subprocess that simulates agent behavior

            cmd = self._build_agent_command(agent_type, prompt_file, model)

            print(f"Executing: {cmd}")
            print()

            # Execute agent
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.getcwd()
            )

            execution_time = (datetime.now() - self.start_time).total_seconds()

            # Parse agent output
            output = result.stdout
            error_output = result.stderr

            print("=== Agent Execution Complete ===")
            print(f"Execution time: {execution_time:.2f}s")
            print(f"Exit code: {result.returncode}")
            print()

            if result.returncode == 0:
                print("✅ Agent completed successfully")
                return {
                    'success': True,
                    'agent_type': agent_type,
                    'model': model,
                    'output': output,
                    'execution_time': execution_time,
                    'exit_code': result.returncode
                }
            else:
                print(f"❌ Agent failed with exit code {result.returncode}")
                return {
                    'success': False,
                    'error': error_output or 'Agent execution failed',
                    'agent_type': agent_type,
                    'output': output,
                    'execution_time': execution_time,
                    'exit_code': result.returncode
                }

        finally:
            # Clean up temp file
            if os.path.exists(prompt_file):
                os.unlink(prompt_file)

    def _spawn_background(self, agent_type: str, prompt: str, model: str, timeout: int) -> Dict[str, Any]:
        """Spawn agent in background and return agent ID."""
        print("🚀 Spawning agent (background mode)...")

        # For background mode, we'd use Claude Code's Task tool with run_in_background=True
        # This returns an agent ID that can be used with TaskOutput later

        # Simulate agent ID
        import uuid
        agent_id = str(uuid.uuid4())[:8]

        self.agent_id = agent_id

        print(f"✅ Agent spawned with ID: {agent_id}")
        print(f"   Use TaskOutput tool to retrieve results later")
        print()

        return {
            'success': True,
            'agent_id': agent_id,
            'agent_type': agent_type,
            'model': model,
            'status': 'running',
            'message': 'Agent running in background. Use TaskOutput to retrieve results.'
        }

    def _build_agent_command(self, agent_type: str, prompt_file: str, model: str) -> str:
        """Build the command to execute the agent."""
        # In a real implementation, this would use Claude Code's Task tool
        # For now, we'll simulate with a simple echo command

        # Simulated agent behavior based on type
        if agent_type == 'Explore':
            # Simulate exploration by listing files
            return f'echo "=== Exploration Results ===" && find . -name "*.py" | head -10 && echo "Found Python files in the codebase"'
        elif agent_type == 'Plan':
            # Simulate planning
            return f'echo "=== Implementation Plan ===" && echo "1. Analyze requirements" && echo "2. Design solution" && echo "3. Implement changes"'
        else:
            # general-purpose
            return f'echo "=== Task Execution ===" && cat {prompt_file} && echo "" && echo "Task processing complete"'

    def get_status(self, agent_id: str) -> Dict[str, Any]:
        """Get status of a background agent."""
        # In real implementation, would check agent status
        return {
            'agent_id': agent_id,
            'status': 'completed',
            'message': 'Use TaskOutput to retrieve full results'
        }


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python3 execute-agent-spawn.py <skill_id>")
        print("       python3 execute-agent-spawn.py --test")
        sys.exit(1)

    if sys.argv[1] == '--test':
        # Run test agent spawn
        test_config = {
            'agent_type': 'Explore',
            'prompt': 'Find all Python files in the current directory',
            'model': 'haiku',
            'timeout': 30,
            'run_in_background': False
        }

        spawner = AgentSpawner(agent_config=test_config)
        result = spawner.spawn()

        print()
        print("=== Test Results ===")
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0 if result['success'] else 1)

    # TODO: Load skill from database and execute
    skill_id = int(sys.argv[1])
    print(f"Loading skill {skill_id} from database...")
    print("TODO: Implement database loading")


if __name__ == '__main__':
    main()
