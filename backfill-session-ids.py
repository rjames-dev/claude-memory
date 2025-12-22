#!/usr/bin/env python3
"""
Claude Memory - Backfill Session IDs

Attempts to retroactively add session_id and transcript_path to legacy snapshots
by matching them with existing Claude Code transcript files.

Matching Strategy:
1. Timestamp proximity (snapshot timestamp vs file mtime)
2. Content similarity (compare first messages)
3. Message count alignment

Safety Features:
- Dry-run mode by default
- Confidence scoring for each match
- User confirmation before updates
- Detailed reporting

Usage:
    python3 backfill-session-ids.py --dry-run   # Preview matches
    python3 backfill-session-ids.py --execute   # Apply changes
"""

import os
import sys
import json
import argparse
import psycopg2
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5435")
DB_NAME = os.getenv("DB_NAME", "claude_memory")
DB_USER = os.getenv("DB_USER", "memory_admin")
DB_PASS = os.getenv("CONTEXT_DB_PASSWORD")
if not DB_PASS:
    raise ValueError("CONTEXT_DB_PASSWORD environment variable required. Set in .env file.")

# Claude Code transcript directory
CWD = os.getcwd()
ENCODED_PATH = CWD.replace('/', '-').replace(' ', '-')
TRANSCRIPT_DIR = Path.home() / '.claude' / 'projects' / ENCODED_PATH

# Matching thresholds
TIMESTAMP_THRESHOLD_MINUTES = 30  # Match if within 30 minutes
MIN_CONFIDENCE_SCORE = 60  # Only suggest matches with 60%+ confidence

def get_snapshots_without_session_id():
    """Fetch all snapshots that need backfilling"""
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS
    )

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                id, timestamp, trigger_event, raw_context,
                project_path
            FROM context_snapshots
            WHERE session_id IS NULL
            ORDER BY timestamp DESC
        """)

        snapshots = []
        for row in cursor.fetchall():
            snapshot_id, timestamp, trigger, raw_context, project_path = row

            # Extract message count and first message
            messages = raw_context.get('messages', []) if isinstance(raw_context, dict) else []
            first_msg = messages[0] if messages else None

            snapshots.append({
                'id': snapshot_id,
                'timestamp': timestamp,
                'trigger': trigger,
                'project_path': project_path,
                'message_count': len(messages),
                'first_message': first_msg,
                'messages': messages
            })

        return snapshots
    finally:
        conn.close()

def get_available_transcripts():
    """Scan for available transcript files"""
    if not TRANSCRIPT_DIR.exists():
        return []

    transcripts = []

    for jsonl_file in TRANSCRIPT_DIR.glob('*.jsonl'):
        # Skip agent files (these are sub-agents, not main sessions)
        if jsonl_file.stem.startswith('agent-'):
            continue

        stat = jsonl_file.stat()
        session_id = jsonl_file.stem

        # Read first few lines to get metadata
        messages = []
        try:
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if i >= 10:  # Only read first 10 lines for analysis
                        break
                    if line.strip():
                        try:
                            msg = json.loads(line)
                            messages.append(msg)
                        except:
                            pass

            # Count total lines (approx message count)
            with open(jsonl_file, 'r') as f:
                total_lines = sum(1 for _ in f)

            transcripts.append({
                'session_id': session_id,
                'path': str(jsonl_file),
                'modified_time': datetime.fromtimestamp(stat.st_mtime),
                'file_size': stat.st_size,
                'total_lines': total_lines,
                'first_messages': messages
            })

        except Exception as e:
            print(f"⚠️  Error reading {jsonl_file.name}: {e}")

    return transcripts

def calculate_match_confidence(snapshot, transcript):
    """
    Calculate confidence score (0-100) for a snapshot-transcript match.

    Factors:
    - Timestamp proximity (40 points)
    - Message count similarity (30 points)
    - Content similarity (30 points)
    """
    score = 0
    details = []

    # 1. Timestamp proximity (40 points max)
    if snapshot['timestamp'].tzinfo:
        snapshot_time = snapshot['timestamp'].replace(tzinfo=None)
    else:
        snapshot_time = snapshot['timestamp']

    time_diff = abs((transcript['modified_time'] - snapshot_time).total_seconds())
    time_diff_minutes = time_diff / 60

    if time_diff_minutes <= 5:
        timestamp_score = 40
    elif time_diff_minutes <= 15:
        timestamp_score = 30
    elif time_diff_minutes <= 30:
        timestamp_score = 20
    elif time_diff_minutes <= 60:
        timestamp_score = 10
    else:
        timestamp_score = 0

    score += timestamp_score
    details.append(f"Timestamp: {timestamp_score}/40 ({time_diff_minutes:.1f} min diff)")

    # 2. Message count similarity (30 points max)
    # Transcript lines != message count (has metadata), but should be proportional
    expected_transcript_lines = snapshot['message_count'] * 2  # Rough estimate

    if transcript['total_lines'] > 0:
        line_ratio = min(snapshot['message_count'], transcript['total_lines']) / max(snapshot['message_count'], transcript['total_lines'])
        count_score = int(30 * line_ratio)
    else:
        count_score = 0

    score += count_score
    details.append(f"Count: {count_score}/30 (snapshot:{snapshot['message_count']} vs transcript:{transcript['total_lines']} lines)")

    # 3. Content similarity (30 points max)
    # Check if first user message content appears in transcript
    content_score = 0

    if snapshot['first_message'] and 'content' in snapshot['first_message']:
        first_content = snapshot['first_message']['content'][:100]

        # Search transcript for this content
        found_match = False
        for trans_msg in transcript['first_messages']:
            if isinstance(trans_msg, dict) and 'message' in trans_msg:
                msg_obj = trans_msg['message']
                if isinstance(msg_obj, dict) and 'content' in msg_obj:
                    trans_content = str(msg_obj['content'])[:100]
                    if first_content in trans_content or trans_content in first_content:
                        found_match = True
                        break

        if found_match:
            content_score = 30
            details.append(f"Content: {content_score}/30 (first message matched)")
        else:
            details.append(f"Content: {content_score}/30 (no content match)")
    else:
        details.append(f"Content: {content_score}/30 (no content to compare)")

    score += content_score

    return score, details

def find_matches(snapshots, transcripts, min_confidence=MIN_CONFIDENCE_SCORE, debug=False):
    """Match snapshots to transcripts based on confidence scoring"""
    matches = []

    for snapshot in snapshots:
        best_match = None
        best_score = 0
        best_details = []

        if debug:
            print(f"\n  Snapshot #{snapshot['id']} ({snapshot['trigger'][:40]}):")

        for transcript in transcripts:
            score, details = calculate_match_confidence(snapshot, transcript)

            if debug:
                print(f"    vs {transcript['session_id'][:16]}...: {score}%")
                for detail in details:
                    print(f"       {detail}")

            if score > best_score:
                best_score = score
                best_match = transcript
                best_details = details

        if debug and best_match:
            print(f"    Best: {best_match['session_id'][:16]}... ({best_score}%)")

        if best_match and best_score >= min_confidence:
            matches.append({
                'snapshot_id': snapshot['id'],
                'snapshot_trigger': snapshot['trigger'],
                'snapshot_timestamp': snapshot['timestamp'],
                'transcript_session_id': best_match['session_id'],
                'transcript_path': best_match['path'],
                'confidence_score': best_score,
                'details': best_details
            })

    return matches

def apply_backfill(matches, dry_run=True):
    """Apply session_id and transcript_path updates to database"""
    if dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made")
        print("=" * 80)
        return

    print("\n✏️  APPLYING BACKFILL - Updating database")
    print("=" * 80)

    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS
    )

    try:
        cursor = conn.cursor()

        for match in matches:
            cursor.execute("""
                UPDATE context_snapshots
                SET
                    session_id = %s,
                    transcript_path = %s
                WHERE id = %s
            """, (
                match['transcript_session_id'],
                match['transcript_path'],
                match['snapshot_id']
            ))

            print(f"✅ Updated snapshot #{match['snapshot_id']}")

        conn.commit()
        print(f"\n✨ Successfully updated {len(matches)} snapshots")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error during update: {e}")
        raise
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(
        description='Backfill session IDs for legacy snapshots'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually apply changes (default is dry-run)'
    )
    parser.add_argument(
        '--min-confidence',
        type=int,
        default=MIN_CONFIDENCE_SCORE,
        help=f'Minimum confidence score to suggest match (default: {MIN_CONFIDENCE_SCORE})'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Show all match attempts and scores'
    )

    args = parser.parse_args()
    dry_run = not args.execute

    print("🔄 Claude Memory - Session ID Backfill Tool")
    print("=" * 80)
    print()

    # Step 1: Load data
    print("📂 Loading snapshots without session_id...")
    snapshots = get_snapshots_without_session_id()
    print(f"   Found {len(snapshots)} snapshots needing backfill")
    print()

    print("📁 Scanning for available transcript files...")
    transcripts = get_available_transcripts()
    print(f"   Found {len(transcripts)} transcript files (excluding agents)")
    print()

    if len(transcripts) == 0:
        print("❌ No transcript files found in:")
        print(f"   {TRANSCRIPT_DIR}")
        print("\n💡 Transcripts may have been deleted or project path encoding is wrong")
        return 1

    # Step 2: Find matches
    print("🔍 Matching snapshots to transcripts...")
    matches = find_matches(snapshots, transcripts, min_confidence=args.min_confidence, debug=args.debug)
    print(f"   Found {len(matches)} potential matches (≥{args.min_confidence}% confidence)")
    print()

    if len(matches) == 0:
        print("⚠️  No confident matches found")
        print("\n💡 Possible reasons:")
        print("   • Transcript files were deleted")
        print("   • Snapshots were test data (not from real transcripts)")
        print("   • Timestamps don't align (files modified after capture)")
        return 0

    # Step 3: Display matches
    print("📊 Proposed Matches:")
    print("=" * 80)
    print()

    for i, match in enumerate(matches, 1):
        print(f"{i}. Snapshot #{match['snapshot_id']} → Session {match['transcript_session_id'][:16]}...")
        print(f"   Confidence: {match['confidence_score']}%")
        print(f"   Trigger: {match['snapshot_trigger']}")
        print(f"   Snapshot time: {match['snapshot_timestamp']}")
        for detail in match['details']:
            print(f"      • {detail}")
        print()

    # Step 4: Confirmation and execution
    if dry_run:
        print("=" * 80)
        print("ℹ️  This was a DRY RUN - no changes were made")
        print()
        print("To apply these changes, run:")
        print("  python3 backfill-session-ids.py --execute")
        print()
        print(f"📊 Summary:")
        print(f"   • {len(matches)} snapshots will be updated")
        print(f"   • {len(snapshots) - len(matches)} snapshots have no confident match")
        return 0

    else:
        print("=" * 80)
        print("⚠️  WARNING: You are about to update the database!")
        print(f"   {len(matches)} snapshots will be modified")
        print()
        response = input("Continue? (yes/no): ").strip().lower()

        if response != 'yes':
            print("❌ Cancelled by user")
            return 1

        apply_backfill(matches, dry_run=False)
        return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
