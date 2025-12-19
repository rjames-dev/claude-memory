#!/bin/bash

# Claude Memory - Automatic Capture Hooks Setup
# Installs PreCompact hooks for automatic conversation capture

set -e

echo "🪝 Claude Memory - Automatic Capture Hooks Setup"
echo "================================================="
echo ""

# Get the absolute path to claude-memory directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CLAUDE_MEMORY_DIR="$(dirname "$SCRIPT_DIR")"

echo "📍 Claude Memory location: $CLAUDE_MEMORY_DIR"
echo ""

# Detect OS and set Claude config path
if [[ "$OSTYPE" == "darwin"* ]]; then
  CLAUDE_CONFIG_DIR="$HOME/.claude"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  CLAUDE_CONFIG_DIR="$HOME/.config/claude"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
  CLAUDE_CONFIG_DIR="$APPDATA/Claude"
else
  echo "⚠️  Unknown OS, using default"
  CLAUDE_CONFIG_DIR="$HOME/.claude"
fi

CLAUDE_SETTINGS="$CLAUDE_CONFIG_DIR/settings.json"

echo "📝 Claude Code config: $CLAUDE_SETTINGS"
echo ""

# Create config directory if it doesn't exist
mkdir -p "$CLAUDE_CONFIG_DIR"

# Check if processor is running
echo "🔍 Checking if claude-memory processor is running..."
if curl -s http://localhost:3200/health > /dev/null 2>&1; then
  echo "✅ Processor is running on port 3200"
else
  echo "⚠️  Warning: Processor not running. Start with:"
  echo "   cd $CLAUDE_MEMORY_DIR && docker compose up -d"
fi
echo ""

# Generate hook configuration
cat > /tmp/claude-memory-hooks.json << CONFIGEOF
{
  "hooks": {
    "PreCompact": [
      {
        "matcher": "auto",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_MEMORY_DIR/hooks/auto-capture-precompact.py",
            "timeout": 10
          }
        ]
      },
      {
        "matcher": "manual",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_MEMORY_DIR/hooks/auto-capture-precompact.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
CONFIGEOF

echo "✅ Generated hook configuration"
echo ""

# Check if settings file exists
if [ -f "$CLAUDE_SETTINGS" ]; then
  echo "⚠️  Claude Code settings file already exists"
  echo ""
  echo "Options:"
  echo "  1. Backup existing and merge hooks (recommended)"
  echo "  2. Show manual merge instructions"
  echo "  3. Cancel"
  echo ""
  read -p "Choose option (1/2/3): " choice
  
  case $choice in
    1)
      # Backup existing
      BACKUP_FILE="$CLAUDE_SETTINGS.backup-$(date +%Y%m%d-%H%M%S)"
      cp "$CLAUDE_SETTINGS" "$BACKUP_FILE"
      echo "✅ Backed up to: $BACKUP_FILE"
      
      # Merge hooks using Python
      python3 << PYPYTHON
import json
from pathlib import Path

# Load existing settings
with open("$CLAUDE_SETTINGS", 'r') as f:
    existing = json.load(f)

# Load new hooks
with open('/tmp/claude-memory-hooks.json', 'r') as f:
    new_hooks = json.load(f)

# Merge hooks
if 'hooks' not in existing:
    existing['hooks'] = {}

existing['hooks']['PreCompact'] = new_hooks['hooks']['PreCompact']

# Save merged settings
with open("$CLAUDE_SETTINGS", 'w') as f:
    json.dump(existing, f, indent=2)

print("✅ Merged hooks into existing settings")
PYPYTHON
      ;;
    2)
      echo ""
      echo "📋 Manual Merge Instructions:"
      echo "   1. Open: $CLAUDE_SETTINGS"
      echo "   2. Add the 'PreCompact' hooks from: /tmp/claude-memory-hooks.json"
      echo "   3. Save and restart Claude Code"
      echo ""
      cat /tmp/claude-memory-hooks.json
      exit 0
      ;;
    3)
      echo "Cancelled"
      exit 0
      ;;
    *)
      echo "Invalid choice"
      exit 1
      ;;
  esac
else
  # Create new settings file
  cp /tmp/claude-memory-hooks.json "$CLAUDE_SETTINGS"
  echo "✅ Created new Claude Code settings with hooks"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "What happens now:"
echo "  • When Claude Code context gets full → auto-compact triggers"
echo "  • PreCompact hook runs automatically"
echo "  • Your conversation is captured to claude-memory database"
echo "  • AI summary generated (llama3.2)"
echo "  • Embeddings created for semantic search"
echo "  • Snapshot stored permanently"
echo ""
echo "View capture log:"
echo "  cat ~/.claude/memory-captures.jsonl | jq ."
echo ""
echo "Test the hook manually:"
echo "  echo '{\"transcript_path\":\"/path/to/test.jsonl\",\"trigger\":\"manual\"}' | \\"
echo "    $CLAUDE_MEMORY_DIR/hooks/auto-capture-precompact.py"
echo ""
echo "📖 Full documentation: $CLAUDE_MEMORY_DIR/hooks/README.md"
echo ""
