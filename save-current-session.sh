#!/bin/bash
# Save current Claude Code session to claude-memory database
# Usage: ./save-current-session.sh [project-path]

set -e

PROJECT_PATH="${1:-$(pwd)}"
PROCESSOR_URL="${CLAUDE_MEMORY_PROCESSOR_URL:-http://localhost:3200}"
TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)

echo "📦 Claude Memory - Manual Session Save"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if processor is running
if ! curl -sf "${PROCESSOR_URL}/health" > /dev/null 2>&1; then
    echo "❌ Error: claude-memory processor not responding"
    echo "   Check: docker compose ps in ~/Data/00 GITHUB/Code/claude-memory"
    exit 1
fi

# Prompt for exported file
echo "Step 1: Export your conversation"
echo "   Run: /export in Claude Code"
echo ""
read -p "Enter path to exported file: " EXPORT_FILE

if [ ! -f "$EXPORT_FILE" ]; then
    echo "❌ File not found: $EXPORT_FILE"
    exit 1
fi

# Capture using manual-capture.js
echo ""
echo "Step 2: Capturing to database..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
node "$SCRIPT_DIR/manual-capture.js" "$EXPORT_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Session saved successfully!"
    echo ""
    echo "Next step: Run /compact in Claude Code to compact the session"
    echo ""
    echo "Tomorrow: Resume work with fresh context, all memories preserved"
else
    echo "❌ Capture failed"
    exit 1
fi
