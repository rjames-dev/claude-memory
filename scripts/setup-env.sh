#!/bin/bash
# Claude Memory - Environment Setup Helper
# Helps configure .env file with correct workspace paths
# Created: 2025-12-19 (Phase 6B)
#
# Usage:
#   ./scripts/setup-env.sh

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        Claude Memory - Environment Setup Helper           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if .env exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${YELLOW}Creating .env from .env.example...${NC}"
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    echo -e "${GREEN}✅ Created .env file${NC}"
    echo ""
fi

echo "Current setup:"
echo "  Project root: $PROJECT_ROOT"
echo ""

# Detect workspace root (parent of Code/claude-memory)
DETECTED_WORKSPACE=$(dirname $(dirname "$PROJECT_ROOT"))
echo -e "${BLUE}Detected workspace root:${NC}"
echo "  $DETECTED_WORKSPACE"
echo ""

# Ask user to confirm or provide custom path
read -p "Use this workspace root? (Y/n): " -r
echo

if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo "Enter custom workspace root path:"
    read -r WORKSPACE_ROOT
else
    WORKSPACE_ROOT="$DETECTED_WORKSPACE"
fi

echo ""
echo -e "${BLUE}Configuration:${NC}"
echo "  CLAUDE_WORKSPACE_ROOT=$WORKSPACE_ROOT"
echo ""

# Update .env file
# Check if CLAUDE_WORKSPACE_ROOT already exists in .env
if grep -q "^CLAUDE_WORKSPACE_ROOT=" "$PROJECT_ROOT/.env"; then
    # Update existing value
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|^CLAUDE_WORKSPACE_ROOT=.*|CLAUDE_WORKSPACE_ROOT=$WORKSPACE_ROOT|" "$PROJECT_ROOT/.env"
    else
        # Linux
        sed -i "s|^CLAUDE_WORKSPACE_ROOT=.*|CLAUDE_WORKSPACE_ROOT=$WORKSPACE_ROOT|" "$PROJECT_ROOT/.env"
    fi
    echo -e "${GREEN}✅ Updated CLAUDE_WORKSPACE_ROOT in .env${NC}"
else
    # Add new value (shouldn't happen with .env.example, but just in case)
    echo "CLAUDE_WORKSPACE_ROOT=$WORKSPACE_ROOT" >> "$PROJECT_ROOT/.env"
    echo -e "${GREEN}✅ Added CLAUDE_WORKSPACE_ROOT to .env${NC}"
fi

echo ""

# Check if password is set
if grep -q "^CONTEXT_DB_PASSWORD=your_secure_password_here" "$PROJECT_ROOT/.env" || grep -q "^CONTEXT_DB_PASSWORD=$" "$PROJECT_ROOT/.env"; then
    echo -e "${YELLOW}⚠️  Warning: CONTEXT_DB_PASSWORD not configured${NC}"
    echo ""
    echo "Generate a secure password with:"
    echo "  openssl rand -base64 32"
    echo ""
    read -p "Generate password automatically? (Y/n): " -r
    echo

    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        PASSWORD=$(openssl rand -base64 32)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^CONTEXT_DB_PASSWORD=.*|CONTEXT_DB_PASSWORD=$PASSWORD|" "$PROJECT_ROOT/.env"
        else
            sed -i "s|^CONTEXT_DB_PASSWORD=.*|CONTEXT_DB_PASSWORD=$PASSWORD|" "$PROJECT_ROOT/.env"
        fi
        echo -e "${GREEN}✅ Generated and saved secure password${NC}"
    else
        echo "Please update CONTEXT_DB_PASSWORD in .env manually"
    fi
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              Environment Setup Complete!                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Next steps:"
echo "  1. Review .env file (do not commit to git!)"
echo "  2. Start containers: docker-compose up -d --build"
echo "  3. Verify: docker-compose ps"
echo "  4. Initialize schema: ./scripts/init-schema.sh"
echo ""
