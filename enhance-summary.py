#!/usr/bin/env python3
"""
Claude Memory - Enhance Summary
Generate detailed, comprehensive summaries using Claude Sonnet's full context analysis.

This script provides FULLY AUTOMATED enhanced summary generation:
- Fetches raw conversation from database
- Calls Claude API to generate comprehensive 1500-3000 word summary
- Regenerates embedding from enhanced summary
- Updates database with both summary and embedding

Usage:
    export ANTHROPIC_API_KEY='your-api-key-here'
    python3 enhance-summary.py <snapshot_id>

Requirements:
    - anthropic package: pip install anthropic
    - psycopg2 package: pip install psycopg2-binary
    - ANTHROPIC_API_KEY environment variable
    - Docker containers running (claude-context-processor, claude-context-db)

Cost:
    ~$0.15-0.25 per enhanced summary (Claude Sonnet 4.5 API)

Example:
    # Enhance a poor-quality summary from before Phase 6C
    python3 enhance-summary.py 26

    # Or use via slash command:
    /mem-enhance-summary 26
"""

import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path

# Database configuration
def get_database_url():
    """Get database URL from environment or .env file"""

    # First try DATABASE_URL directly
    if os.getenv("DATABASE_URL"):
        # If running from host, convert Docker internal URL to host URL
        db_url = os.getenv("DATABASE_URL")
        # Replace Docker internal hostname with localhost and port
        db_url = db_url.replace("@context-db:5432", "@localhost:5435")
        return db_url

    # Try to read from .env file
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        env_vars = {}
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value.strip()

        # Build connection string from .env variables
        db_user = env_vars.get('POSTGRES_USER', 'memory_admin')
        db_password = env_vars.get('CONTEXT_DB_PASSWORD', '')
        db_name = env_vars.get('POSTGRES_DB', 'claude_memory')
        db_port = env_vars.get('POSTGRES_HOST_PORT', '5435')

        if db_password:
            return f"postgresql://{db_user}:{db_password}@localhost:{db_port}/{db_name}"

    # Fallback: use default (will likely fail, but gives clear error)
    print("⚠️  Warning: Could not find database credentials in environment or .env file", file=sys.stderr)
    return "postgresql://memory_admin:your_secure_password_here@localhost:5435/claude_memory"

DATABASE_URL = get_database_url()

def fetch_snapshot(snapshot_id):
    """Fetch complete snapshot data including raw_context"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT
                id,
                project_path,
                session_id,
                transcript_path,
                timestamp,
                summary,
                raw_context,
                tags,
                mentioned_files,
                key_decisions,
                bugs_fixed,
                git_branch,
                git_commit_hash,
                trigger_event,
                context_window_size
            FROM context_snapshots
            WHERE id = %s
        """

        cursor.execute(query, (snapshot_id,))
        snapshot = cursor.fetchone()

        cursor.close()
        conn.close()

        return snapshot

    except Exception as e:
        print(f"❌ Error fetching snapshot: {e}", file=sys.stderr)
        return None

def get_anthropic_api_key():
    """Get Anthropic API key from environment or local .env file"""

    # First check environment variable
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if api_key:
        return api_key

    # Check local .env file in claude-memory directory
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('ANTHROPIC_API_KEY='):
                        key = line.split('=', 1)[1].strip().strip('"').strip("'")
                        if key:
                            return key
        except Exception as e:
            # File might be protected, skip
            pass

    return None

def generate_enhanced_summary(snapshot):
    """Generate comprehensive summary using Claude API"""
    import anthropic

    # Get API key from environment or .env files
    api_key = get_anthropic_api_key()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment or .env files")

    client = anthropic.Anthropic(api_key=api_key)

    # Extract conversation from raw_context
    raw_context = snapshot['raw_context']
    if isinstance(raw_context, str):
        raw_context = json.loads(raw_context)

    messages = raw_context.get('messages', [])

    # Format conversation for Claude
    conversation_text = []
    for idx, msg in enumerate(messages, 1):
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')
        conversation_text.append(f"[Message {idx}] {role.upper()}:\n{content}")

    conversation_str = "\n\n".join(conversation_text)

    # Build comprehensive prompt
    prompt = f"""You are analyzing a development session for the claude-memory system's detailed archival feature.

**SNAPSHOT METADATA:**
- Snapshot ID: {snapshot['id']}
- Project: {snapshot['project_path']}
- Date: {snapshot['timestamp']}
- Tags: {', '.join(snapshot['tags']) if snapshot['tags'] else 'none'}
- Files mentioned: {len(snapshot['mentioned_files']) if snapshot['mentioned_files'] else 0}
- Messages: {len(messages)}
- Trigger: {snapshot['trigger_event']}

**CURRENT SUMMARY (to be replaced):**
{snapshot['summary'][:500]}{'...' if len(snapshot['summary']) > 500 else ''}

**FULL CONVERSATION:**

{conversation_str}

**YOUR TASK:**

Generate a comprehensive, detailed summary (1500-3000 words) following this EXACT structure:

## Primary Goal
[One sentence: What was the main objective of this session?]

## Work Completed

### Session Type
[Was this planning, implementation, debugging, research, etc.?]

### Files Modified
[List key files and what changed - be specific with file paths and line numbers where relevant]

### Features Added
[New capabilities or functionality - what can users do now that they couldn't before?]

### Bugs Fixed
[Problems solved - what was broken and how was it fixed?]

### Architecture Decisions Made
[Key architectural or implementation decisions and WHY they were chosen]

## Technical Decisions
[Detailed technical decisions made, with reasoning - why was approach X chosen over approach Y?]

## Session Metrics
- Messages: {len(messages)}
- Files touched: [count if determinable]
- Duration: [if inferable from timestamps]
- Commits: [if any git commits were made]

## Open Questions / Unresolved Issues
[What questions were raised but not answered? What needs follow-up?]

## Continuity

**How This Relates to Previous Work:**
[Context from earlier sessions that led to this work]

**What's Next:**
[What should be done in follow-up sessions? What remains incomplete?]

**Context for Future Sessions:**
[What someone needs to know when picking this work back up later]

**IMPORTANT:**
- Be technically precise with file names, function names, line numbers
- Capture WHY decisions were made, not just WHAT was done
- Include specific code snippets or technical details where relevant
- Note dead ends explored (helps prevent repeating mistakes)
- This is for archival and knowledge transfer - err on the side of too much detail

Generate the detailed summary now:"""

    print("🔄 Calling Claude API for enhanced summary...")
    print(f"   Context size: ~{len(prompt)} chars")
    print(f"   Messages in conversation: {len(messages)}")

    # Call Claude API
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,  # ~3000 words
        messages=[{
            "role": "user",
            "content": prompt
        }]
    )

    enhanced_summary = message.content[0].text

    print(f"✅ Enhanced summary generated ({len(enhanced_summary)} chars)")

    return enhanced_summary

def regenerate_embedding(summary_text):
    """Generate new embedding for the enhanced summary"""
    import subprocess
    import tempfile

    print("🔄 Generating new embedding from enhanced summary...")

    # Write summary to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(summary_text)
        temp_file = f.name

    try:
        # Call Docker processor to generate embedding
        result = subprocess.run(
            ['docker', 'exec', '-i', 'claude-context-processor',
             'python3', '/app/scripts/generate_embedding.py'],
            input=summary_text,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            raise Exception(f"Embedding generation failed: {result.stderr}")

        embedding_data = json.loads(result.stdout)

        if not embedding_data.get('success'):
            raise Exception(f"Embedding generation error: {embedding_data.get('error')}")

        embedding = embedding_data['embedding']

        print(f"✅ Generated {len(embedding)}-dimensional embedding")

        return embedding

    finally:
        # Clean up temp file
        import os as os_module
        try:
            os_module.unlink(temp_file)
        except:
            pass

def update_snapshot(snapshot_id, enhanced_summary, embedding):
    """Update snapshot with enhanced summary and new embedding"""
    print(f"🔄 Updating snapshot #{snapshot_id} in database...")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Update both summary and embedding
        cursor.execute(
            """
            UPDATE context_snapshots
            SET summary = %s,
                embedding = %s
            WHERE id = %s
            """,
            (enhanced_summary, embedding, snapshot_id)
        )

        conn.commit()

        print(f"✅ Updated snapshot #{snapshot_id}")
        print(f"   Summary: {len(enhanced_summary)} chars")
        print(f"   Embedding: {len(embedding)} dimensions")
        print(f"   Rows updated: {cursor.rowcount}")

        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"❌ Database update failed: {e}", file=sys.stderr)
        return False

def main():
    """Main execution function - fully automated enhanced summary generation"""

    if len(sys.argv) < 2:
        print("❌ Error: snapshot_id required", file=sys.stderr)
        print("\nUsage: python3 enhance-summary.py <snapshot_id>", file=sys.stderr)
        print("\nExample: python3 enhance-summary.py 31", file=sys.stderr)
        print("\nRequires: ANTHROPIC_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)

    try:
        snapshot_id = int(sys.argv[1])
    except ValueError:
        print(f"❌ Error: Invalid snapshot_id '{sys.argv[1]}' (must be a number)", file=sys.stderr)
        sys.exit(1)

    # Check for API key
    api_key = get_anthropic_api_key()
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not found", file=sys.stderr)
        print("\nOptions to configure:", file=sys.stderr)
        print("  1. Set environment variable:", file=sys.stderr)
        print("     export ANTHROPIC_API_KEY='your-api-key-here'", file=sys.stderr)
        print("\n  2. Add to .env file in claude-memory directory:", file=sys.stderr)
        print("     echo \"ANTHROPIC_API_KEY='your-api-key-here'\" >> .env", file=sys.stderr)
        sys.exit(1)

    print("="*80)
    print(f"🚀 ENHANCED SUMMARY GENERATION - Snapshot #{snapshot_id}")
    print("="*80)
    print()

    # Step 1: Fetch snapshot
    print(f"📂 [1/4] Fetching snapshot #{snapshot_id}...")
    snapshot = fetch_snapshot(snapshot_id)

    if not snapshot:
        print(f"❌ Snapshot #{snapshot_id} not found", file=sys.stderr)
        sys.exit(1)

    print(f"✅ Found snapshot #{snapshot_id}")
    print(f"   Project: {snapshot['project_path']}")
    print(f"   Date: {snapshot['timestamp']}")
    print(f"   Messages: {snapshot['context_window_size']}")
    print(f"   Current summary: {len(snapshot['summary'])} chars")
    print()

    # Step 2: Generate enhanced summary
    print(f"🤖 [2/4] Generating enhanced summary via Claude API...")
    print(f"   Model: claude-sonnet-4-5")
    print(f"   Estimated cost: ~$0.15-0.25")
    print()

    try:
        enhanced_summary = generate_enhanced_summary(snapshot)
    except Exception as e:
        print(f"❌ Enhanced summary generation failed: {e}", file=sys.stderr)
        sys.exit(1)

    print()

    # Step 3: Generate embedding
    print(f"🧮 [3/4] Generating embedding from enhanced summary...")

    try:
        embedding = regenerate_embedding(enhanced_summary)
    except Exception as e:
        print(f"❌ Embedding generation failed: {e}", file=sys.stderr)
        print("⚠️  Summary generated but not saved to database", file=sys.stderr)
        sys.exit(1)

    print()

    # Step 4: Update database
    print(f"💾 [4/4] Updating database...")

    success = update_snapshot(snapshot_id, enhanced_summary, embedding)

    if not success:
        print("❌ Database update failed", file=sys.stderr)
        sys.exit(1)

    print()
    print("="*80)
    print("✨ ENHANCEMENT COMPLETE!")
    print("="*80)
    print()
    print(f"📊 Summary Comparison:")
    print(f"   Before: {len(snapshot['summary'])} chars")
    print(f"   After:  {len(enhanced_summary)} chars")
    print(f"   Improvement: {len(enhanced_summary) - len(snapshot['summary']):+d} chars")
    print()
    print(f"🔍 Semantic search will now use the enhanced summary.")
    print(f"   Try: /mem-search \"<topic from this session>\"")
    print()

if __name__ == '__main__':
    main()
