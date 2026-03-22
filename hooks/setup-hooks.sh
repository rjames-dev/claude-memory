#!/bin/bash

# Claude Memory - Automatic Capture Hooks Setup
# Installs PreCompact hooks for automatic conversation capture
# Also provisions the Obsidian vault if not already present

set -e

# ---------------------------------------------------------------------------
# Vault template repo — cloned on first install if vault doesn't exist
# Update this URL after publishing the template to GitHub
# ---------------------------------------------------------------------------
VAULT_TEMPLATE_REPO="git@github.com:rjames-dev/obsidian-vault-template.git"

echo "🪝 Claude Memory - Automatic Capture Hooks Setup"
echo "================================================="
echo ""

# Get the absolute path to claude-memory directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CLAUDE_MEMORY_DIR="$(dirname "$SCRIPT_DIR")"

echo "📍 Claude Memory location: $CLAUDE_MEMORY_DIR"
echo ""

# ---------------------------------------------------------------------------
# Provision Obsidian vault
# Uses VAULT_ROOT from .env (set by setup-env.sh)
# Falls back to CLAUDE_WORKSPACE_ROOT/claude-vault if not set
# ---------------------------------------------------------------------------

# Read env vars from .env if not already in environment
if [ -f "$CLAUDE_MEMORY_DIR/.env" ]; then
    [ -z "$VAULT_ROOT" ]             && VAULT_ROOT=$(grep "^VAULT_ROOT=" "$CLAUDE_MEMORY_DIR/.env" | cut -d= -f2 | tr -d '"' | tr -d "'")
    [ -z "$CLAUDE_WORKSPACE_ROOT" ]  && CLAUDE_WORKSPACE_ROOT=$(grep "^CLAUDE_WORKSPACE_ROOT=" "$CLAUDE_MEMORY_DIR/.env" | cut -d= -f2 | tr -d '"' | tr -d "'")
fi

# Derive default vault root if still not set
if [ -z "$VAULT_ROOT" ] && [ -n "$CLAUDE_WORKSPACE_ROOT" ]; then
    VAULT_ROOT="$CLAUDE_WORKSPACE_ROOT/claude-vault"
fi

if [ -n "$VAULT_ROOT" ]; then
    if [ -d "$VAULT_ROOT" ]; then
        echo "✅ Obsidian vault already exists at $VAULT_ROOT"
        echo ""
    else
        echo "📓 Obsidian vault not found at $VAULT_ROOT"
        echo ""
        echo "Choose how to provision it:"
        echo "  1) Clone vault template (fresh start — recommended for new installs)"
        echo "  2) Clone your existing private vault"
        echo "  3) Create minimal folder structure only"
        echo ""
        read -p "Choice [1/2/3]: " -r VAULT_CHOICE
        echo ""

        case "$VAULT_CHOICE" in
            2)
                read -p "Enter your vault git repo URL: " -r PRIVATE_VAULT_REPO
                echo ""
                if git clone "$PRIVATE_VAULT_REPO" "$VAULT_ROOT" 2>&1; then
                    echo "✅ Private vault cloned to $VAULT_ROOT"
                    echo ""
                else
                    echo "❌ Clone failed — check the URL and your SSH/token access"
                    exit 1
                fi
                ;;
            3)
                mkdir -p "$VAULT_ROOT"/{Calendar,Events,Research,Projects}
                mkdir -p "$VAULT_ROOT"/Claude/{Session-Logs,Knowledge-Base,Scratch}
                echo "✅ Minimal vault structure created at $VAULT_ROOT"
                echo ""
                ;;
            *)
                # Default: clone template
                echo "📥 Cloning vault template..."
                if git clone "$VAULT_TEMPLATE_REPO" "$VAULT_ROOT" 2>&1; then
                    rm -rf "$VAULT_ROOT/.git"
                    echo ""
                    echo "✅ Vault template cloned to $VAULT_ROOT"
                    echo "   Git history cleared — initialize as your own private repo when ready:"
                    echo "   cd $VAULT_ROOT && git init && git remote add origin <your-private-repo-url>"
                    echo ""
                else
                    echo "⚠️  Could not clone vault template — creating minimal structure instead..."
                    mkdir -p "$VAULT_ROOT"/{Calendar,Events,Research,Projects}
                    mkdir -p "$VAULT_ROOT"/Claude/{Session-Logs,Knowledge-Base,Scratch}
                    echo "✅ Minimal vault structure created at $VAULT_ROOT"
                    echo ""
                fi
                ;;
        esac

        echo "   Next: open Obsidian → 'Open folder as vault' → select:"
        echo "   $VAULT_ROOT"
        echo ""
    fi
else
    echo "⚠️  VAULT_ROOT not set — skipping vault setup"
    echo "   Run scripts/setup-env.sh first, then re-run this script."
    echo ""
fi

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
