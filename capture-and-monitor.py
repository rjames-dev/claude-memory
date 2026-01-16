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


def run_capture():
    """
    Run auto-capture-current-session.py to trigger capture.

    Returns:
        tuple: (success, session_id or None)
    """
    print("🔍 Step 1/2: Capturing current session...")
    print("=" * 60)

    try:
        # Run capture script
        result = subprocess.run(
            [sys.executable, 'auto-capture-current-session.py'],
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
    print("")
    print("🔍 Step 2/2: Monitoring capture progress...")
    print("=" * 60)

    # Wait a moment for capture to register in processor
    print("⏳ Waiting for capture to start processing...")
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

This command is ideal for end-of-session workflows.
        """
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=180,
        help='Monitoring timeout in seconds (default: 180)'
    )

    args = parser.parse_args()

    # Print header
    print("")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║         Capture and Monitor - Combined Workflow             ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print("")

    # Record start time BEFORE capture (to filter out old snapshots in monitor)
    capture_start_time = datetime.now().isoformat()

    # Step 1: Capture
    capture_success, session_id = run_capture()

    if not capture_success:
        print("")
        print("❌ Capture failed - cannot proceed to monitoring")
        return 1

    # Step 2: Monitor (pass start time to prevent finding old snapshots)
    monitor_success = run_monitor(session_id, args.timeout, capture_start_time)

    # Summary
    print("")
    print("=" * 60)
    if monitor_success:
        print("✅ Capture and monitoring complete!")
    else:
        print("⚠️  Capture succeeded, but monitoring timed out or failed")
        print("   Check dashboard: http://localhost:3200/dashboard")
    print("=" * 60)
    print("")

    return 0 if monitor_success else 1


if __name__ == '__main__':
    # Ensure we're in the right directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    sys.exit(main())
