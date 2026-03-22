#!/bin/bash
#
# Claude Memory - Install Slash Commands
#
# This script installs all /mem-* slash commands globally in ~/.claude/commands/
# and automatically fixes the paths to point to the current installation directory.
#
# Usage:
#   ./scripts/install-commands.sh
#

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMMANDS_SOURCE="$PROJECT_ROOT/.claude/commands"
COMMANDS_TARGET="$HOME/.claude/commands"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo ""
echo "========================================================================"
echo "Claude Memory - Slash Commands Installation"
echo "========================================================================"
echo ""

# Check if source commands directory exists
if [ ! -d "$COMMANDS_SOURCE" ]; then
    echo -e "${RED}❌ Commands directory not found: $COMMANDS_SOURCE${NC}"
    echo ""
    echo "Please ensure you're running this from the claude-memory directory."
    exit 1
fi

# Create target directory if it doesn't exist
echo -e "${BLUE}[1/3] Setting up commands directory...${NC}"
if [ ! -d "$COMMANDS_TARGET" ]; then
    mkdir -p "$COMMANDS_TARGET"
    echo -e "${GREEN}✅ Created $COMMANDS_TARGET${NC}"
else
    echo -e "${GREEN}✅ Directory exists: $COMMANDS_TARGET${NC}"
fi
echo ""

# Count command files
COMMAND_COUNT=$(find "$COMMANDS_SOURCE" -name "*.md" -not -name "README.md" | wc -l | tr -d ' ')
echo -e "${BLUE}[2/3] Installing $COMMAND_COUNT slash commands...${NC}"

INSTALLED=0
UPDATED=0
FAILED=0

# Install each command file
for CMD_FILE in "$COMMANDS_SOURCE"/*.md; do
    # Skip README
    BASENAME=$(basename "$CMD_FILE")
    if [ "$BASENAME" = "README.md" ]; then
        continue
    fi

    TARGET_FILE="$COMMANDS_TARGET/$BASENAME"

    # Read the file, replace the path, and write to target
    # Pattern handles both macOS (/Users/username/...) and Linux (/home/username/...) paths
    if sed -E "s|python3 (/Users|/home)/[^/]+/.*claude-memory/|python3 $PROJECT_ROOT/|g" "$CMD_FILE" > "$TARGET_FILE"; then
        if [ -f "$TARGET_FILE" ]; then
            COMMAND_NAME=$(echo "$BASENAME" | sed 's/\.md$//')

            # Check if this is an update or new installation
            if [ -f "$COMMANDS_TARGET/$BASENAME" ]; then
                echo "   ✅ Updated: /$COMMAND_NAME"
                UPDATED=$((UPDATED + 1))
            else
                echo "   ✅ Installed: /$COMMAND_NAME"
                INSTALLED=$((INSTALLED + 1))
            fi
        else
            echo "   ❌ Failed: /$COMMAND_NAME"
            FAILED=$((FAILED + 1))
        fi
    else
        echo "   ❌ Failed to process: $BASENAME"
        FAILED=$((FAILED + 1))
    fi
done
echo ""

# Verify installation
echo -e "${BLUE}[3/3] Verifying installation...${NC}"

# Check if commands are readable
READABLE=$(find "$COMMANDS_TARGET" -name "mem-*.md" -type f | wc -l | tr -d ' ')

if [ "$READABLE" -ge "$COMMAND_COUNT" ]; then
    echo -e "${GREEN}✅ All commands installed and readable${NC}"
else
    echo -e "${YELLOW}⚠️  Warning: Found $READABLE commands, expected $COMMAND_COUNT${NC}"
fi

# Check path correctness in one sample file
SAMPLE_FILE="$COMMANDS_TARGET/mem-skills.md"
if [ -f "$SAMPLE_FILE" ]; then
    if grep -q "$PROJECT_ROOT" "$SAMPLE_FILE"; then
        echo -e "${GREEN}✅ Paths correctly set to: $PROJECT_ROOT${NC}"
    else
        echo -e "${YELLOW}⚠️  Warning: Paths may not be correctly updated${NC}"
    fi
fi
echo ""

# Summary
echo "========================================================================"
echo -e "${GREEN}✅ Slash Commands Installation Complete!${NC}"
echo "========================================================================"
echo ""
echo "Summary:"
echo "  • New installations: $INSTALLED"
echo "  • Updates: $UPDATED"
if [ $FAILED -gt 0 ]; then
    echo "  • Failed: $FAILED"
fi
echo "  • Total active commands: $READABLE"
echo ""
echo "Installed commands:"
echo "  • /mem-skills               - List all skills"
echo "  • /mem-skills-search        - Search skills semantically"
echo "  • /mem-skills-stats         - View performance statistics"
echo "  • /mem-skills-info          - View detailed skill information"
echo "  • /mem-skills-execute       - Execute a skill"
echo "  • /mem-skills-create        - Create a new skill"
echo "  • /mem-skills-edit          - Edit an existing skill"
echo "  • /mem-skills-delete        - Delete a skill"
echo "  • /mem-skills-import        - Import skills from JSON"
echo "  • /mem-skills-export        - Export skills to JSON"
echo "  • /mem-skills-restore       - Restore a deleted skill"
echo "  • /mem-skills-embeddings    - Manage skill embeddings"
echo "  • /mem-enhance-summary      - Generate enhanced summaries"
echo ""
echo "You can now use these commands in any Claude Code session!"
echo "Try: /mem-skills"
echo ""
