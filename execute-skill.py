#!/usr/bin/env python3
"""
Claude Memory - Skills System: Skill Execution Tool

Executes a skill and logs performance metrics.

Usage:
    python3 execute-skill.py <skill_name>          # By name
    python3 execute-skill.py --id <skill_id>       # By ID
    python3 execute-skill.py <skill_name> --dry-run  # Preview without executing
    python3 execute-skill.py <skill_name> --time-saved 30  # Specify time saved estimate

Arguments:
    skill_name              Skill name (e.g., "check-db-health")
    --id ID                 Skill ID instead of name
    --dry-run               Show what would be executed without running
    --time-saved SECONDS    Estimated time saved by automation (default: auto-calculate)
    --request TEXT          User request that triggered this (for logging)
    --session-id ID         Session ID (for logging)
"""

import sys
import os
import argparse
import subprocess
import tempfile
import time
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Import new executors for Phase 2 Milestone 4
try:
    import importlib.util
    import sys as _sys

    # Load execute-tool-sequence.py
    spec = importlib.util.spec_from_file_location(
        "execute_tool_sequence",
        os.path.join(os.path.dirname(__file__), "execute-tool-sequence.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ToolSequenceExecutor = module.ToolSequenceExecutor
    TOOL_SEQUENCE_AVAILABLE = True
except Exception as e:
    TOOL_SEQUENCE_AVAILABLE = False
    print(f"Note: Tool sequences not available: {e}", file=sys.stderr)

try:
    # Load execute-agent-spawn.py
    spec = importlib.util.spec_from_file_location(
        "execute_agent_spawn",
        os.path.join(os.path.dirname(__file__), "execute-agent-spawn.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    AgentSpawner = module.AgentSpawner
    AGENT_SPAWN_AVAILABLE = True
except Exception as e:
    AGENT_SPAWN_AVAILABLE = False
    print(f"Note: Agent spawning not available: {e}", file=sys.stderr)

# Database configuration (matches existing claude-memory scripts)
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', '5435'))

# Try to read password from .env file
def get_db_password():
    """Get database password from .env file or environment."""
    password = os.environ.get('CONTEXT_DB_PASSWORD')
    if password:
        return password

    # Try reading from .env file
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('CONTEXT_DB_PASSWORD='):
                    return line.strip().split('=', 1)[1]

    return 'memory_secure_2024'  # Fallback

DB_CONFIG = {
    'host': DB_HOST,
    'port': DB_PORT,
    'database': 'claude_memory',
    'user': 'memory_admin',
    'password': get_db_password()
}


def get_db_connection():
    """Create database connection."""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"❌ Database connection failed: {e}", file=sys.stderr)
        print(f"   Host: {DB_HOST}:{DB_PORT}", file=sys.stderr)
        sys.exit(1)


def get_skill_by_name(conn, skill_name):
    """Fetch skill by name."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT * FROM skills_agents
        WHERE agent_name = %s
    """, (skill_name,))
    skill = cur.fetchone()
    cur.close()
    return dict(skill) if skill else None


def get_skill_by_id(conn, skill_id):
    """Fetch skill by ID."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT * FROM skills_agents
        WHERE id = %s
    """, (skill_id,))
    skill = cur.fetchone()
    cur.close()
    return dict(skill) if skill else None


def get_skill_command(conn, skill_id):
    """Fetch command definition for a skill."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT
            id,
            command_type,
            script_content,
            command_definition,
            parameters,
            prerequisites
        FROM skills_commands
        WHERE agent_id = %s AND is_active = TRUE
    """, (skill_id,))
    command = cur.fetchone()
    cur.close()
    return dict(command) if command else None


def validate_prerequisites(prerequisites):
    """
    Validate prerequisites before execution.

    Returns:
        tuple: (valid, error_message)
    """
    if not prerequisites:
        return True, None

    # Check docker_running
    if prerequisites.get('docker_running'):
        try:
            result = subprocess.run(
                ['docker', 'ps'],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                return False, "Docker is not running or not accessible"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False, "Docker is not available"

    # Check git_repo
    if prerequisites.get('git_repo'):
        if not os.path.exists('.git'):
            return False, "Not a git repository"

    # Add more prerequisite checks as needed

    return True, None


def execute_bash_script(script_content, timeout=300):
    """
    Execute a bash script and return results.

    Args:
        script_content: Bash script as string
        timeout: Timeout in seconds (default: 5 minutes)

    Returns:
        dict: {
            'success': bool,
            'stdout': str,
            'stderr': str,
            'exit_code': int,
            'execution_time_ms': int,
            'error_message': str or None
        }
    """
    result = {
        'success': False,
        'stdout': '',
        'stderr': '',
        'exit_code': -1,
        'execution_time_ms': 0,
        'error_message': None
    }

    # Create temporary script file
    temp_script = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.sh',
            delete=False
        ) as f:
            temp_script = f.name
            f.write(script_content)

        # Make executable
        os.chmod(temp_script, 0o755)

        # Execute script
        start_time = time.time()

        try:
            proc = subprocess.run(
                ['/bin/bash', temp_script],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            execution_time = (time.time() - start_time) * 1000  # Convert to ms

            result['stdout'] = proc.stdout
            result['stderr'] = proc.stderr
            result['exit_code'] = proc.returncode
            result['execution_time_ms'] = int(execution_time)
            result['success'] = (proc.returncode == 0)

            if proc.returncode != 0:
                result['error_message'] = f"Script exited with code {proc.returncode}"
                if proc.stderr:
                    result['error_message'] += f": {proc.stderr[:200]}"

        except subprocess.TimeoutExpired:
            execution_time = (time.time() - start_time) * 1000
            result['execution_time_ms'] = int(execution_time)
            result['error_message'] = f"Script timed out after {timeout} seconds"

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            result['execution_time_ms'] = int(execution_time)
            result['error_message'] = f"Execution error: {str(e)}"

    finally:
        # Clean up temporary file
        if temp_script and os.path.exists(temp_script):
            try:
                os.unlink(temp_script)
            except Exception as e:
                print(f"Warning: Failed to delete temp file {temp_script}: {e}", file=sys.stderr)

    return result


def log_performance(conn, skill_id, execution_result, args):
    """
    Log execution performance to skills_performance_log.

    Args:
        conn: Database connection
        skill_id: Skill ID
        execution_result: Result dict from execute_bash_script
        args: Command line arguments
    """
    cur = conn.cursor()

    # Determine outcome
    if execution_result['success']:
        outcome = 'success'
    else:
        outcome = 'failed'

    # Calculate time saved (if not provided, estimate based on execution time)
    if args.time_saved:
        time_saved_ms = args.time_saved * 1000
    else:
        # Heuristic: manual task takes 10x longer than automated
        time_saved_ms = execution_result['execution_time_ms'] * 10

    cur.execute("""
        INSERT INTO skills_performance_log (
            agent_id,
            outcome,
            execution_time_ms,
            time_saved_ms,
            error_message,
            user_request,
            session_id,
            executed_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        RETURNING id
    """, (
        skill_id,
        outcome,
        execution_result['execution_time_ms'],
        time_saved_ms,
        execution_result['error_message'],
        args.request,
        args.session_id
    ))

    log_id = cur.fetchone()[0]
    cur.close()

    return log_id


def update_skill_counters(conn, skill_id, success):
    """
    Update skill performance counters in skills_agents.

    Args:
        conn: Database connection
        skill_id: Skill ID
        success: True if execution succeeded
    """
    cur = conn.cursor()

    if success:
        cur.execute("""
            UPDATE skills_agents
            SET use_count = use_count + 1,
                success_count = success_count + 1,
                last_used = NOW(),
                updated_at = NOW()
            WHERE id = %s
        """, (skill_id,))
    else:
        cur.execute("""
            UPDATE skills_agents
            SET use_count = use_count + 1,
                failure_count = failure_count + 1,
                last_used = NOW(),
                updated_at = NOW()
            WHERE id = %s
        """, (skill_id,))

    cur.close()


def update_time_saved_metrics(conn, skill_id):
    """
    Update avg_time_saved_ms and total_time_saved_ms from performance logs.

    Args:
        conn: Database connection
        skill_id: Skill ID
    """
    cur = conn.cursor()

    cur.execute("""
        UPDATE skills_agents
        SET avg_time_saved_ms = (
                SELECT AVG(time_saved_ms)::INTEGER
                FROM skills_performance_log
                WHERE agent_id = %s AND time_saved_ms IS NOT NULL
            ),
            total_time_saved_ms = (
                SELECT SUM(time_saved_ms)::INTEGER
                FROM skills_performance_log
                WHERE agent_id = %s AND time_saved_ms IS NOT NULL
            )
        WHERE id = %s
    """, (skill_id, skill_id, skill_id))

    cur.close()


def execute_skill(args):
    """
    Execute a skill and log performance.

    Returns:
        int: 0 on success, 1 on failure
    """
    conn = get_db_connection()

    try:
        # Fetch skill
        if args.id:
            skill = get_skill_by_id(conn, args.id)
            if not skill:
                print(f"❌ Skill with ID {args.id} not found", file=sys.stderr)
                conn.close()
                return 1
        else:
            skill = get_skill_by_name(conn, args.skill_name)
            if not skill:
                print(f"❌ Skill '{args.skill_name}' not found", file=sys.stderr)
                conn.close()
                return 1

        # Check if skill is active
        if not skill['is_active']:
            print(f"❌ Skill '{skill['agent_name']}' is inactive", file=sys.stderr)
            conn.close()
            return 1

        # Fetch command
        command = get_skill_command(conn, skill['id'])
        if not command:
            print(f"❌ No active command found for skill '{skill['agent_name']}'", file=sys.stderr)
            conn.close()
            return 1

        # Validate command type
        supported_types = ['bash_script']
        if TOOL_SEQUENCE_AVAILABLE:
            supported_types.append('tool_sequence')
        if AGENT_SPAWN_AVAILABLE:
            supported_types.append('agent_spawn')

        if command['command_type'] not in supported_types:
            print(f"❌ Unsupported command type: {command['command_type']}", file=sys.stderr)
            print(f"   Supported types: {', '.join(supported_types)}", file=sys.stderr)
            conn.close()
            return 1

        # Validate prerequisites
        valid, error = validate_prerequisites(command['prerequisites'])
        if not valid:
            print(f"❌ Prerequisite check failed: {error}", file=sys.stderr)
            conn.close()
            return 1

        # Dry run mode
        if args.dry_run:
            print(f"\n🔍 DRY RUN MODE - Would execute:")
            print(f"   Skill: {skill['agent_name']} (ID: {skill['id']})")
            print(f"   Type: {command['command_type']}")

            if command['command_type'] == 'bash_script':
                print(f"   Script Length: {len(command['script_content'])} characters")
                print(f"\n   Script Content:")
                print("   " + "-"*76)
                for line in command['script_content'].split('\n'):
                    print(f"   {line}")
                print("   " + "-"*76)
            elif command['command_type'] == 'tool_sequence':
                seq_def = command.get('command_definition', {})
                steps = seq_def.get('steps', [])
                print(f"   Sequence Steps: {len(steps)}")
                print(f"\n   Steps:")
                for i, step in enumerate(steps, 1):
                    step_name = step.get('name', f'step_{i}')
                    tool = step.get('tool', 'unknown')
                    required = step.get('required', True)
                    req_str = 'required' if required else 'optional'
                    print(f"     {i}. {step_name} ({tool}) - {req_str}")
            elif command['command_type'] == 'agent_spawn':
                agent_def = command.get('command_definition', {})
                print(f"   Agent Type: {agent_def.get('agent_type', 'unknown')}")
                print(f"   Model: {agent_def.get('model', 'sonnet')}")
                print(f"   Timeout: {agent_def.get('timeout', 300)}s")
                prompt = agent_def.get('prompt', '')
                print(f"   Prompt: {prompt[:100]}..." if len(prompt) > 100 else f"   Prompt: {prompt}")

            print(f"\n✅ Dry run complete (no execution performed)")
            conn.close()
            return 0

        # Execute script
        print(f"🚀 Executing skill: {skill['agent_name']}")
        print(f"   Type: {command['command_type']}")
        print(f"   Confidence: {skill['confidence_score']}")
        print()

        # Execute based on command type
        if command['command_type'] == 'bash_script':
            execution_result = execute_bash_script(command['script_content'])

        elif command['command_type'] == 'tool_sequence':
            sequence_def = command.get('command_definition')
            if not sequence_def:
                print(f"❌ Missing command_definition for tool_sequence", file=sys.stderr)
                conn.close()
                return 1

            executor = ToolSequenceExecutor(
                skill_id=skill['id'],
                sequence_def=sequence_def
            )
            result = executor.execute()

            # Convert to standard execution_result format
            execution_result = {
                'success': result['success'],
                'stdout': json.dumps(result.get('step_results', {}), indent=2, default=str),
                'stderr': result.get('error', ''),
                'exit_code': 0 if result['success'] else 1,
                'execution_time_ms': int(result.get('execution_time', 0) * 1000) if 'execution_time' in result else 0,
                'error_message': result.get('error')
            }

        elif command['command_type'] == 'agent_spawn':
            agent_config = command.get('command_definition')
            if not agent_config:
                print(f"❌ Missing command_definition for agent_spawn", file=sys.stderr)
                conn.close()
                return 1

            spawner = AgentSpawner(
                skill_id=skill['id'],
                agent_config=agent_config
            )
            result = spawner.spawn()

            # Convert to standard execution_result format
            execution_result = {
                'success': result['success'],
                'stdout': result.get('output', ''),
                'stderr': result.get('error', ''),
                'exit_code': result.get('exit_code', 0 if result['success'] else 1),
                'execution_time_ms': int(result.get('execution_time', 0) * 1000),
                'error_message': result.get('error')
            }

        else:
            print(f"❌ Unsupported command type: {command['command_type']}", file=sys.stderr)
            conn.close()
            return 1

        # Print output
        if execution_result['stdout']:
            print(execution_result['stdout'])

        if execution_result['stderr']:
            print(execution_result['stderr'], file=sys.stderr)

        # Log performance and update counters in transaction
        try:
            log_id = log_performance(conn, skill['id'], execution_result, args)
            update_skill_counters(conn, skill['id'], execution_result['success'])
            update_time_saved_metrics(conn, skill['id'])
            conn.commit()

            print()
            print("="*80)
            if execution_result['success']:
                print(f"✅ Skill executed successfully")
                print(f"   Execution Time: {execution_result['execution_time_ms'] / 1000:.2f} seconds")
                if args.time_saved:
                    print(f"   Time Saved: {args.time_saved} seconds")
                else:
                    estimated_time_saved = (execution_result['execution_time_ms'] * 10) / 1000
                    print(f"   Estimated Time Saved: {estimated_time_saved:.2f} seconds")
                print(f"   Performance Log ID: {log_id}")
                print("="*80)
                conn.close()
                return 0
            else:
                print(f"❌ Skill execution failed")
                print(f"   Exit Code: {execution_result['exit_code']}")
                print(f"   Execution Time: {execution_result['execution_time_ms'] / 1000:.2f} seconds")
                if execution_result['error_message']:
                    print(f"   Error: {execution_result['error_message']}")
                print(f"   Performance Log ID: {log_id}")
                print("="*80)
                conn.close()
                return 1

        except psycopg2.Error as e:
            conn.rollback()
            print(f"❌ Failed to log performance: {e}", file=sys.stderr)
            conn.close()
            return 1

    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        conn.close()
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='Execute a skill and log performance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Execute skill by name
  python3 execute-skill.py check-db-health

  # Execute skill by ID
  python3 execute-skill.py --id 2

  # Dry run (preview without executing)
  python3 execute-skill.py check-db-health --dry-run

  # Specify time saved estimate
  python3 execute-skill.py backup-claude-memory --time-saved 60

  # With user request context
  python3 execute-skill.py check-db-health --request "check database health"
        """
    )

    # Positional or named skill identifier
    parser.add_argument('skill_name', nargs='?',
                        help='Skill name (e.g., "check-db-health")')
    parser.add_argument('--id', type=int,
                        help='Skill ID instead of name')

    # Execution options
    parser.add_argument('--dry-run',
                        action='store_true',
                        help='Show what would be executed without running')
    parser.add_argument('--time-saved',
                        type=int,
                        help='Estimated time saved in seconds (default: auto-calculate)')

    # Logging context
    parser.add_argument('--request',
                        help='User request that triggered this skill')
    parser.add_argument('--session-id',
                        help='Session ID for tracking')

    args = parser.parse_args()

    # Validate input
    if not args.skill_name and not args.id:
        parser.error("Either skill_name or --id must be provided")

    # Execute skill
    exit_code = execute_skill(args)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
