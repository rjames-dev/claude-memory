#!/usr/bin/env python3
"""
Monitor Capture Progress - Claude Memory Skill

Monitors the progress of /mem-capture operations with real-time updates.
Prevents data loss from closing Claude Code before capture completes.

Usage:
    python3 monitor-capture-progress.py [--session-id SESSION_ID] [--timeout SECONDS]

Examples:
    # Monitor latest capture (most common use case)
    python3 monitor-capture-progress.py

    # Monitor specific session
    python3 monitor-capture-progress.py --session-id abc123

    # Custom timeout (default: 180 seconds)
    python3 monitor-capture-progress.py --timeout 300

Author: Claude Sonnet 4.5
Created: 2025-12-27
Status: Production-ready
"""

import sys
import time
import argparse
from datetime import datetime
from db_utils import get_db_connection


def get_latest_capture(cursor, session_id=None):
    """
    Query most recent auto-capture from database.

    Args:
        cursor: Database cursor
        session_id: Optional specific session ID to monitor

    Returns:
        dict: Snapshot metadata or None if not found
    """
    if session_id:
        query = """
            SELECT
                id,
                trigger_event,
                timestamp,
                jsonb_array_length(raw_context->'messages') as message_count,
                LENGTH(summary) as summary_len,
                CASE WHEN embedding IS NOT NULL THEN 1 ELSE 0 END as has_embedding,
                COALESCE(array_length(tags, 1), 0) as tag_count,
                COALESCE(array_length(mentioned_files, 1), 0) as file_count
            FROM context_snapshots
            WHERE trigger_event LIKE %s
            ORDER BY timestamp DESC
            LIMIT 1;
        """
        cursor.execute(query, (f'auto-capture-{session_id}%',))
    else:
        query = """
            SELECT
                id,
                trigger_event,
                timestamp,
                jsonb_array_length(raw_context->'messages') as message_count,
                LENGTH(summary) as summary_len,
                CASE WHEN embedding IS NOT NULL THEN 1 ELSE 0 END as has_embedding,
                COALESCE(array_length(tags, 1), 0) as tag_count,
                COALESCE(array_length(mentioned_files, 1), 0) as file_count
            FROM context_snapshots
            WHERE trigger_event LIKE 'auto-capture%'
            ORDER BY timestamp DESC
            LIMIT 1;
        """
        cursor.execute(query)

    row = cursor.fetchone()
    if not row:
        return None

    return {
        'id': row[0],
        'trigger_event': row[1],
        'timestamp': row[2],
        'message_count': row[3],
        'summary_len': row[4],
        'has_embedding': row[5],
        'tag_count': row[6],
        'file_count': row[7]
    }


def is_capture_complete(snapshot):
    """
    Check if capture has completed processing.

    Completion criteria:
    - Summary length > 100 characters

    Args:
        snapshot: Snapshot metadata dict

    Returns:
        bool: True if complete, False if still processing
    """
    if not snapshot:
        return False

    # Primary completion check: summary generated
    if snapshot['summary_len'] and snapshot['summary_len'] > 100:
        return True

    return False


def get_quality_score(cursor, snapshot_id):
    """
    Get quality score from v_snapshot_quality view.

    Args:
        cursor: Database cursor
        snapshot_id: Snapshot ID

    Returns:
        float: Quality score (0-10) or None
    """
    try:
        cursor.execute("""
            SELECT quality_score
            FROM v_snapshot_quality
            WHERE id = %s;
        """, (snapshot_id,))

        row = cursor.fetchone()
        if row and row[0]:
            return round(row[0], 1)
        return None
    except Exception as e:
        # View might not exist or other error - gracefully degrade
        return None


def display_progress(snapshot, elapsed):
    """
    Display progress message with elapsed time.

    Args:
        snapshot: Snapshot metadata dict
        elapsed: Elapsed seconds
    """
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Determine stage based on available data
    if snapshot['summary_len'] == 0 or snapshot['summary_len'] is None:
        stage = "🔄 Processing summary..."
    elif not snapshot['has_embedding']:
        stage = "🔄 Generating embeddings..."
    else:
        stage = "🔄 Finalizing..."

    print(f"{stage} ({elapsed}s elapsed)")
    print(f"   Last check: {timestamp_str}")
    print(f"   Snapshot ID: {snapshot['id']}")
    print("")


def display_completion(snapshot, elapsed, quality_score=None):
    """
    Display completion message with snapshot details.

    Args:
        snapshot: Snapshot metadata dict
        elapsed: Total elapsed seconds
        quality_score: Optional quality score
    """
    print(f"✅ Capture complete! ({elapsed}s total)")
    print("")
    print("📋 Snapshot Details:")
    print(f"   ID: {snapshot['id']}")
    print(f"   Timestamp: {snapshot['timestamp']}")

    if snapshot['message_count']:
        print(f"   Messages: {snapshot['message_count']}")

    if snapshot['summary_len']:
        # Convert character count to approximate words (avg 5 chars/word)
        approx_words = snapshot['summary_len'] // 5
        print(f"   Summary: {approx_words} words ({snapshot['summary_len']} chars)")

    if snapshot['tag_count']:
        print(f"   Tags: {snapshot['tag_count']} extracted")

    if snapshot['file_count']:
        print(f"   Files: {snapshot['file_count']} mentioned")

    if quality_score:
        print(f"   Quality Score: {quality_score}/10")

    print("")
    print("✅ Safe to close Claude Code!")
    print("")
    print("To enhance this summary with Claude Sonnet:")
    print(f"   /mem-enhance-summary {snapshot['id']}")


def main():
    """Main monitoring function."""
    parser = argparse.ArgumentParser(
        description='Monitor /mem-capture progress with real-time updates',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Monitor latest capture (most common)
  python3 monitor-capture-progress.py

  # Monitor specific session
  python3 monitor-capture-progress.py --session-id abc123

  # Custom timeout
  python3 monitor-capture-progress.py --timeout 300
        """
    )
    parser.add_argument(
        '--session-id',
        help='Specific session ID to monitor (default: latest)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=180,
        help='Timeout in seconds (default: 180)'
    )
    parser.add_argument(
        '--poll-interval',
        type=int,
        default=5,
        help='Poll interval in seconds (default: 5)'
    )

    args = parser.parse_args()

    # Connect to database
    try:
        conn = get_db_connection()
        cur = conn.cursor()
    except SystemExit:
        # get_db_connection already printed error message
        return 1

    # Start monitoring
    print("📊 Monitoring capture progress...")
    if args.session_id:
        print(f"Session: {args.session_id}")
    else:
        print("Session: Latest capture")
    print(f"Polling every {args.poll_interval}s, timeout {args.timeout}s")
    print("")

    start_time = time.time()
    last_snapshot_id = None

    while True:
        elapsed = int(time.time() - start_time)

        # Check timeout
        if elapsed > args.timeout:
            print(f"⏱️  Timeout reached ({args.timeout}s)")
            print("   Capture may still be processing")
            print("   Check dashboard: http://localhost:3200/dashboard")
            print("")
            cur.close()
            conn.close()
            return 0

        # Get latest capture
        snapshot = get_latest_capture(cur, args.session_id)

        if not snapshot:
            print("⚠️  No recent captures found")
            print("   Run /mem-capture first")
            print("")
            cur.close()
            conn.close()
            return 0

        # Track if we found a new snapshot
        if last_snapshot_id and snapshot['id'] != last_snapshot_id:
            print(f"ℹ️  New capture detected (ID: {snapshot['id']})")
            print("")

        last_snapshot_id = snapshot['id']

        # Check if complete
        if is_capture_complete(snapshot):
            # Get quality score for final display
            quality_score = get_quality_score(cur, snapshot['id'])

            display_completion(snapshot, elapsed, quality_score)
            cur.close()
            conn.close()
            return 0

        # Show progress
        display_progress(snapshot, elapsed)

        # Wait before next check
        time.sleep(args.poll_interval)


if __name__ == '__main__':
    sys.exit(main())
