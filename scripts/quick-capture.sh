#!/bin/bash
# Quick Capture Script
# Usage: ./quick-capture.sh <export-file> [project-path] [trigger-suffix]

set -e

MEMORY_DIR="/Users/jamesmba/Data/00 GITHUB/Code/claude-memory"
TEST_DIR="$MEMORY_DIR/test"

# Parameters
EXPORT_FILE="$1"
PROJECT_PATH="${2:-Code/claude-memory}"
TRIGGER_SUFFIX="${3:-capture}"
TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)

if [ -z "$EXPORT_FILE" ]; then
    echo "❌ Usage: ./quick-capture.sh <export-file> [project-path] [trigger-suffix]"
    echo ""
    echo "Examples:"
    echo "  ./quick-capture.sh ~/export.txt"
    echo "  ./quick-capture.sh ~/export.txt 'Code/nlq-system' 'phase4-checkpoint1'"
    exit 1
fi

if [ ! -f "$EXPORT_FILE" ]; then
    echo "❌ File not found: $EXPORT_FILE"
    exit 1
fi

echo "🚀 Claude Memory Quick Capture"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📁 File: $EXPORT_FILE"
echo "📂 Project: $PROJECT_PATH"
echo "🏷️  Trigger: $TRIGGER_SUFFIX-$TIMESTAMP"
echo ""

# Step 1: Copy to test directory
echo "📋 Copying export to test directory..."
BASENAME=$(basename "$EXPORT_FILE")
cp "$EXPORT_FILE" "$TEST_DIR/$BASENAME"

# Step 2: Parse transcript
echo "🔍 Parsing transcript..."
cd "$TEST_DIR"
node parse-transcript.js "$BASENAME"

# Check if parsing succeeded
if [ ! -f "parsed-conversation.json" ]; then
    echo "❌ Parsing failed - no output generated"
    exit 1
fi

MESSAGE_COUNT=$(node -e "console.log(JSON.parse(require('fs').readFileSync('parsed-conversation.json')).messages.length)")
echo "✅ Parsed $MESSAGE_COUNT messages"

# Step 3: Create capture request
echo "📦 Creating capture request..."
node -e "
const fs = require('fs');
const conv = JSON.parse(fs.readFileSync('parsed-conversation.json'));
const request = {
  project_path: '$PROJECT_PATH',
  trigger: '$TRIGGER_SUFFIX-$TIMESTAMP',
  conversation_data: conv
};
fs.writeFileSync('capture-request.json', JSON.stringify(request, null, 2));
"

# Step 4: Submit to capture API
echo "💾 Submitting to capture API..."
RESPONSE=$(curl -s -X POST 'http://localhost:3200/capture' \
  -H 'Content-Type: application/json' \
  --data '@capture-request.json')

if echo "$RESPONSE" | grep -q "accepted"; then
    echo "✅ Capture accepted by API"
else
    echo "❌ Capture failed:"
    echo "$RESPONSE"
    exit 1
fi

# Step 5: Wait for processing
echo "⏳ Waiting for processing..."
sleep 2

# Step 6: Verify capture
echo "🔍 Verifying capture..."
cd "$MEMORY_DIR"
CAPTURE_LOG=$(docker compose logs --tail=20 context-processor | grep -A 10 "Starting Context Capture" | tail -15)

if echo "$CAPTURE_LOG" | grep -q "Capture Complete"; then
    echo "✅ Capture completed successfully!"
    echo ""

    # Extract snapshot ID
    SNAPSHOT_ID=$(echo "$CAPTURE_LOG" | grep "Snapshot stored" | grep -oE 'ID: [0-9]+' | grep -oE '[0-9]+')

    if [ -n "$SNAPSHOT_ID" ]; then
        echo "📊 Snapshot Details:"
        docker exec claude-context-db psql -U memory_admin -d claude_memory \
          -c "SELECT id, trigger_event, context_window_size as messages, array_length(tags, 1) as tags, array_length(mentioned_files, 1) as files FROM context_snapshots WHERE id = $SNAPSHOT_ID;" \
          2>/dev/null || echo "   (Could not fetch details)"
    fi

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✨ Success! Context preserved in memory database"
    echo "💡 Safe to run: /compact"
else
    echo "⚠️  Capture status unclear - check logs:"
    echo "$CAPTURE_LOG"
fi
