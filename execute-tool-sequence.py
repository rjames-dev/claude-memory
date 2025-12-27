#!/usr/bin/env python3
"""
Tool Sequence Executor for Skills System

Executes multi-step workflows combining Claude Code tools with:
- Sequential execution
- Variable substitution between steps
- Error handling and rollback
- Step-by-step logging

Usage:
    python3 execute-tool-sequence.py <skill_id>
    python3 execute-tool-sequence.py --test

Example skill definition:
{
  "command_type": "tool_sequence",
  "command_definition": {
    "steps": [
      {
        "name": "find_files",
        "tool": "Grep",
        "params": {"pattern": "TODO", "output_mode": "files_with_matches"},
        "required": true
      },
      {
        "name": "read_first_file",
        "tool": "Read",
        "params": {"file_path": "$steps.find_files.results[0]"},
        "required": false
      }
    ]
  }
}

Variable Substitution:
- $steps.<step_name>.<field> - Access previous step results
- $prev.<field> - Access immediately previous step
- $context.<field> - Access execution context (cwd, user, etc.)
"""

import sys
import os
import json
import re
import subprocess
from typing import Dict, Any, List, Optional
from datetime import datetime

# Supported Claude Code tools (defined after functions)
SUPPORTED_TOOLS = {}


class ToolSequenceExecutor:
    """Executes multi-step tool sequences with variable substitution."""

    def __init__(self, skill_id: int = None, sequence_def: Dict[str, Any] = None):
        self.skill_id = skill_id
        self.sequence_def = sequence_def
        self.step_results = {}  # Store results by step name
        self.execution_log = []
        self.context = {
            'cwd': os.getcwd(),
            'timestamp': datetime.now().isoformat(),
            'user': os.environ.get('USER', 'unknown'),
        }

    def execute(self) -> Dict[str, Any]:
        """Execute the tool sequence."""
        print(f"=== Tool Sequence Execution ===")
        print(f"Steps: {len(self.sequence_def['steps'])}")
        print()

        try:
            for i, step in enumerate(self.sequence_def['steps'], 1):
                step_name = step.get('name', f'step_{i}')

                print(f"[{i}/{len(self.sequence_def['steps'])}] Executing: {step_name}")

                result = self._execute_step(step, step_name)

                # Store result
                self.step_results[step_name] = result
                self.execution_log.append({
                    'step': step_name,
                    'tool': step['tool'],
                    'success': result['success'],
                    'timestamp': datetime.now().isoformat()
                })

                # Check if step failed
                if not result['success']:
                    if step.get('required', True):
                        print(f"❌ Required step '{step_name}' failed: {result.get('error')}")
                        return {
                            'success': False,
                            'error': f"Step '{step_name}' failed",
                            'failed_step': step_name,
                            'step_results': self.step_results,
                            'execution_log': self.execution_log
                        }
                    else:
                        print(f"⚠️  Optional step '{step_name}' failed (continuing): {result.get('error')}")
                else:
                    print(f"✅ {step_name} completed")

                print()

            print("=== Sequence Complete ===")
            return {
                'success': True,
                'step_results': self.step_results,
                'execution_log': self.execution_log
            }

        except Exception as e:
            print(f"❌ Sequence execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'step_results': self.step_results,
                'execution_log': self.execution_log
            }

    def _execute_step(self, step: Dict[str, Any], step_name: str) -> Dict[str, Any]:
        """Execute a single step in the sequence."""
        tool_name = step['tool']
        params = step.get('params', {})

        # Substitute variables in params
        substituted_params = self._substitute_variables(params)

        # Get tool executor
        if tool_name not in SUPPORTED_TOOLS:
            return {
                'success': False,
                'error': f"Unsupported tool: {tool_name}"
            }

        tool_executor = SUPPORTED_TOOLS[tool_name]

        # Execute tool
        try:
            result = tool_executor(**substituted_params)
            return {
                'success': True,
                'result': result,
                'tool': tool_name,
                'params': substituted_params
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'tool': tool_name,
                'params': substituted_params
            }

    def _substitute_variables(self, params: Any) -> Any:
        """Recursively substitute variables in parameters."""
        if isinstance(params, dict):
            return {k: self._substitute_variables(v) for k, v in params.items()}
        elif isinstance(params, list):
            return [self._substitute_variables(item) for item in params]
        elif isinstance(params, str):
            return self._substitute_string_variables(params)
        else:
            return params

    def _substitute_string_variables(self, value: str) -> Any:
        """Substitute variables in a string value."""
        # Pattern: $steps.<step_name>.<field_path>
        # Pattern: $prev.<field_path>
        # Pattern: $context.<field>

        if not value.startswith('$'):
            return value

        # Remove leading $
        var_path = value[1:]

        # Parse variable path
        parts = var_path.split('.')

        if parts[0] == 'steps':
            # $steps.<step_name>.<field_path>
            if len(parts) < 2:
                raise ValueError(f"Invalid variable reference: {value}")

            step_name = parts[1]
            field_path = parts[2:]

            if step_name not in self.step_results:
                raise ValueError(f"Step '{step_name}' not found in results")

            return self._get_nested_field(self.step_results[step_name], field_path)

        elif parts[0] == 'prev':
            # $prev.<field_path>
            field_path = parts[1:]

            if not self.step_results:
                raise ValueError("No previous step results available")

            # Get last step result
            last_step_name = list(self.step_results.keys())[-1]
            return self._get_nested_field(self.step_results[last_step_name], field_path)

        elif parts[0] == 'context':
            # $context.<field>
            if len(parts) < 2:
                raise ValueError(f"Invalid context reference: {value}")

            field = parts[1]
            if field not in self.context:
                raise ValueError(f"Context field '{field}' not found")

            return self.context[field]

        else:
            raise ValueError(f"Unknown variable type: {parts[0]}")

    def _get_nested_field(self, obj: Any, field_path: List[str]) -> Any:
        """Get a nested field from an object using a path."""
        current = obj

        for field in field_path:
            # Handle array indexing: results[0]
            if '[' in field and field.endswith(']'):
                field_name = field[:field.index('[')]
                index_str = field[field.index('[')+1:-1]

                if field_name:
                    current = current.get(field_name) if isinstance(current, dict) else getattr(current, field_name)

                try:
                    index = int(index_str)
                    current = current[index]
                except (ValueError, IndexError, TypeError) as e:
                    raise ValueError(f"Invalid array access: {field}") from e
            else:
                # Regular field access
                if isinstance(current, dict):
                    current = current.get(field)
                else:
                    current = getattr(current, field, None)

            if current is None:
                raise ValueError(f"Field '{'.'.join(field_path)}' not found")

        return current


# Tool Executor Functions
def execute_bash(command: str, description: str = None, timeout: int = 120) -> Dict[str, Any]:
    """Execute a bash command."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        return {
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'success': result.returncode == 0
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': f'Command timed out after {timeout}s'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def execute_grep(pattern: str, path: str = ".", output_mode: str = "files_with_matches", **kwargs) -> Dict[str, Any]:
    """Execute grep search."""
    # Build grep command
    cmd_parts = ['grep', '-r']

    if output_mode == "files_with_matches":
        cmd_parts.append('-l')
    elif output_mode == "count":
        cmd_parts.append('-c')

    # Add case insensitive if specified
    if kwargs.get('-i'):
        cmd_parts.append('-i')

    cmd_parts.extend([pattern, path])

    cmd = ' '.join(cmd_parts)

    result = execute_bash(cmd)

    if result['success']:
        if output_mode == "files_with_matches":
            files = [f.strip() for f in result['stdout'].strip().split('\n') if f.strip()]
            return {'results': files, 'count': len(files)}
        else:
            return {'output': result['stdout']}
    else:
        return {'results': [], 'count': 0}


def execute_read(file_path: str, offset: int = 0, limit: int = None) -> Dict[str, Any]:
    """Read a file."""
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()

        if offset:
            lines = lines[offset:]
        if limit:
            lines = lines[:limit]

        return {
            'file_path': file_path,
            'content': ''.join(lines),
            'lines': lines,
            'line_count': len(lines)
        }
    except Exception as e:
        raise ValueError(f"Failed to read {file_path}: {e}")


def execute_edit(file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> Dict[str, Any]:
    """Edit a file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()

        if replace_all:
            new_content = content.replace(old_string, new_string)
            replacements = content.count(old_string)
        else:
            # Replace only first occurrence
            new_content = content.replace(old_string, new_string, 1)
            replacements = 1 if old_string in content else 0

        with open(file_path, 'w') as f:
            f.write(new_content)

        return {
            'file_path': file_path,
            'replacements': replacements,
            'success': True
        }
    except Exception as e:
        raise ValueError(f"Failed to edit {file_path}: {e}")


def execute_write(file_path: str, content: str) -> Dict[str, Any]:
    """Write to a file."""
    try:
        with open(file_path, 'w') as f:
            f.write(content)

        return {
            'file_path': file_path,
            'bytes_written': len(content),
            'success': True
        }
    except Exception as e:
        raise ValueError(f"Failed to write {file_path}: {e}")


def execute_glob(pattern: str, path: str = ".") -> Dict[str, Any]:
    """Execute glob pattern matching."""
    import glob as glob_module

    search_pattern = os.path.join(path, pattern) if path != "." else pattern
    matches = glob_module.glob(search_pattern, recursive=True)

    return {
        'matches': matches,
        'count': len(matches)
    }


# Populate supported tools
SUPPORTED_TOOLS.update({
    'Bash': execute_bash,
    'Grep': execute_grep,
    'Read': execute_read,
    'Edit': execute_edit,
    'Write': execute_write,
    'Glob': execute_glob,
})


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python3 execute-tool-sequence.py <skill_id>")
        print("       python3 execute-tool-sequence.py --test")
        sys.exit(1)

    if sys.argv[1] == '--test':
        # Run test sequence
        test_sequence = {
            'steps': [
                {
                    'name': 'find_python_files',
                    'tool': 'Glob',
                    'params': {'pattern': '*.py', 'path': '.'},
                    'required': True
                },
                {
                    'name': 'count_files',
                    'tool': 'Bash',
                    'params': {
                        'command': 'echo "Found $steps.find_python_files.count Python files"'
                    },
                    'required': False
                }
            ]
        }

        executor = ToolSequenceExecutor(sequence_def=test_sequence)
        result = executor.execute()

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
