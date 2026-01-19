#!/usr/bin/env python3
"""
Capture and Monitor - Combined Workflow

Captures current Claude Code session and immediately monitors progress.
Combines auto-capture-current-session.py + monitor-capture-progress.py.

Usage:
    python3 capture-and-monitor.py
    python3 capture-and-monitor.py --timeout 300

This is the "all-in-one" command for end-of-session captures.

Author: Claude Sonnet 4.5
Created: 2025-12-27
Status: Production-ready
"""

import sys
import subprocess
import time
import argparse
import os
from datetime import datetime


def run_capture(project_path=None):
    """
    Run auto-capture-current-session.py to trigger capture.

    Args:
        project_path: Optional explicit project path to capture

    Returns:
        tuple: (success, session_id or None)
    """
    print("🔍 Step 1/2: Capturing current session...")
    print("=" * 60)

    try:
        # Build capture command
        cmd = [sys.executable, 'auto-capture-current-session.py']
        if project_path:
            cmd.extend(['--project', project_path])

        # Run capture script
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )

        # Print capture output
        print(result.stdout)

        if result.returncode != 0:
            print("❌ Capture failed")
            if result.stderr:
                print(result.stderr)
            return False, None

        # Extract session ID from output (if available)
        session_id = None
        for line in result.stdout.split('\n'):
            if 'Session ID:' in line:
                # Extract session ID from line like "   Session ID: 12cd285c-..."
                session_id = line.split(':')[1].strip().split('-')[0]
                break

        return True, session_id

    except Exception as e:
        print(f"❌ Capture error: {e}")
        return False, None


def run_monitor(session_id=None, timeout=180, capture_start_time=None):
    """
    Run monitor-capture-progress.py to track completion.

    Args:
        session_id: Optional specific session ID to monitor
        timeout: Timeout in seconds
        capture_start_time: ISO timestamp of when capture started (prevents finding old snapshots)

    Returns:
        bool: Success
    """
    print("", flush=True)
    print("🔍 Step 2/2: Monitoring capture progress...", flush=True)
    print("=" * 60, flush=True)

    # Wait a moment for capture to register in processor
    print("⏳ Waiting for capture to start processing...", flush=True)
    time.sleep(3)

    try:
        # Build monitor command
        cmd = [sys.executable, 'monitor-capture-progress.py', '--timeout', str(timeout)]

        if session_id:
            cmd.extend(['--session-id', session_id])

        # Pass capture start time to prevent finding old snapshots
        if capture_start_time:
            cmd.extend(['--since', capture_start_time])

        # Run monitor script (inherit stdout/stderr for real-time output)
        result = subprocess.run(cmd, check=False)

        return result.returncode == 0

    except Exception as e:
        print(f"❌ Monitor error: {e}")
        return False


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(
        description='Capture current session and monitor progress',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Capture and monitor with default settings
  python3 capture-and-monitor.py

  # Custom timeout (5 minutes)
  python3 capture-and-monitor.py --timeout 300

  # Capture specific project (when called from different directory)
  python3 capture-and-monitor.py --project /path/to/project

This command is ideal for end-of-session workflows.
        """
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=180,
        help='Monitoring timeout in seconds (default: 180)'
    )
    parser.add_argument(
        '--project',
        type=str,
        default=None,
        help='Explicit project path to capture (default: original working directory)'
    )

    args = parser.parse_args()

    # Print header
    print("", flush=True)
    print("╔══════════════════════════════════════════════════════════════╗", flush=True)
    print("║         Capture and Monitor - Combined Workflow             ║", flush=True)
    print("╚══════════════════════════════════════════════════════════════╝", flush=True)
    print("", flush=True)

    # Record start time BEFORE capture (to filter out old snapshots in monitor)
    capture_start_time = datetime.now().isoformat()

    # Show project being captured
    if args.project:
        print(f"📂 Target project: {args.project}", flush=True)
        print("", flush=True)

    # Step 1: Capture
    capture_success, session_id = run_capture(project_path=args.project)

    if not capture_success:
        print("")
        print("❌ Capture failed - cannot proceed to monitoring")
        return 1

    # Step 2: Monitor (pass start time to prevent finding old snapshots)
    monitor_success = run_monitor(session_id, args.timeout, capture_start_time)

    # Summary
    print("", flush=True)
    print("=" * 60, flush=True)
    if monitor_success:
        print("✅ Capture and monitoring complete!", flush=True)
    else:
        print("⚠️  Capture succeeded, but monitoring timed out or failed", flush=True)
        print("   Check dashboard: http://localhost:3200/dashboard", flush=True)
    print("=" * 60, flush=True)
    print("", flush=True)

    return 0 if monitor_success else 1


if __name__ == '__main__':
    # Ensure we're in the right directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    sys.exit(main())
