#!/bin/bash

# Claude Memory MCP Server - Quick Setup Script
# This script helps you configure the MCP server for Claude Code

set -e

echo "🧠 Claude Memory MCP Server - Setup"
echo "===================================="
echo ""

# Get the absolute path to this script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CLAUDE_MEMORY_DIR="$(dirname "$SCRIPT_DIR")"

echo "📍 Claude Memory location: $CLAUDE_MEMORY_DIR"
echo ""

# Check if .env exists
if [ ! -f "$CLAUDE_MEMORY_DIR/.env" ]; then
  echo "❌ Error: .env file not found!"
  echo "   Please run 'docker compose up -d' first to create .env"
  exit 1
fi

# Get database password
DB_PASSWORD=$(grep CONTEXT_DB_PASSWORD "$CLAUDE_MEMORY_DIR/.env" | cut -d '=' -f2 | tr -d '"' | tr -d "'")

if [ -z "$DB_PASSWORD" ]; then
  echo "❌ Error: CONTEXT_DB_PASSWORD not found in .env"
  exit 1
fi

echo "✅ Found database password in .env"
echo ""

# Detect OS and set config path
if [[ "$OSTYPE" == "darwin"* ]]; then
  CLAUDE_CONFIG="$HOME/.claude/config.json"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  CLAUDE_CONFIG="$HOME/.config/claude/config.json"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
  CLAUDE_CONFIG="$APPDATA/Claude/config.json"
else
  echo "⚠️  Unknown OS, please manually set config path"
  CLAUDE_CONFIG="$HOME/.claude/config.json"
fi

echo "📝 Claude Code config: $CLAUDE_CONFIG"
echo ""

# Create config directory if it doesn't exist
mkdir -p "$(dirname "$CLAUDE_CONFIG")"

# Generate MCP configuration
cat > /tmp/claude-memory-mcp-config.json << CONFIGEOF
{
  "mcpServers": {
    "claude-memory": {
      "command": "node",
      "args": [
        "$CLAUDE_MEMORY_DIR/mcp-server/src/server.js"
      ],
      "env": {
        "DATABASE_URL": "postgresql://memory_admin:$DB_PASSWORD@localhost:5435/claude_memory",
        "PROCESSOR_URL": "http://localhost:3200",
        "EMBEDDING_MODEL": "sentence-transformers/all-MiniLM-L6-v2"
      }
    }
  }
}
CONFIGEOF

echo "✅ Generated MCP configuration:"
echo ""
cat /tmp/claude-memory-mcp-config.json
echo ""
echo "----------------------------------------"
echo ""

# Check if config file exists
if [ -f "$CLAUDE_CONFIG" ]; then
  echo "⚠️  Claude Code config file already exists"
  echo ""
  echo "Options:"
  echo "  1. Backup existing config and create new one"
  echo "  2. Show merge instructions (recommended)"
  echo "  3. Cancel"
  echo ""
  read -p "Choose option (1/2/3): " choice

  case $choice in
    1)
      cp "$CLAUDE_CONFIG" "$CLAUDE_CONFIG.backup-$(date +%Y%m%d-%H%M%S)"
      echo "✅ Backed up existing config"
      cp /tmp/claude-memory-mcp-config.json "$CLAUDE_CONFIG"
      echo "✅ Created new config with claude-memory MCP server"
      ;;
    2)
      echo ""
      echo "📋 Manual Merge Instructions:"
      echo "   1. Open: $CLAUDE_CONFIG"
      echo "   2. Add the 'claude-memory' section to 'mcpServers'"
      echo "   3. Config is in: /tmp/claude-memory-mcp-config.json"
      echo ""
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
  cp /tmp/claude-memory-mcp-config.json "$CLAUDE_CONFIG"
  echo "✅ Created new Claude Code config"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Verify Docker services running: docker compose ps"
echo "  2. Start Claude Code: claude"
echo "  3. Ask Claude to search your memory!"
echo ""
echo "📖 Full documentation: $CLAUDE_MEMORY_DIR/MCP-SETUP.md"
echo ""
