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

# ---------------------------------------------------------------------------
# Vault root — where claude-vault lives on this machine
# ---------------------------------------------------------------------------
DEFAULT_VAULT_ROOT="$WORKSPACE_ROOT/claude-vault"

EXISTING_VAULT_ROOT=""
if grep -q "^VAULT_ROOT=" "$PROJECT_ROOT/.env" 2>/dev/null; then
    EXISTING_VAULT_ROOT=$(grep "^VAULT_ROOT=" "$PROJECT_ROOT/.env" | cut -d= -f2 | tr -d '"' | tr -d "'")
fi

if [ -n "$EXISTING_VAULT_ROOT" ] && [ "$EXISTING_VAULT_ROOT" != '${CLAUDE_WORKSPACE_ROOT}/claude-vault' ]; then
    echo -e "${GREEN}✅ VAULT_ROOT already set: $EXISTING_VAULT_ROOT${NC}"
else
    echo -e "${BLUE}── Vault Root ───────────────────────────────────────────────${NC}"
    echo ""
    echo "Where should the Obsidian vault (claude-vault) live?"
    echo "  Default: $DEFAULT_VAULT_ROOT"
    echo ""
    read -p "Vault path (press Enter for default): " -r VAULT_INPUT
    echo ""
    VAULT_ROOT="${VAULT_INPUT:-$DEFAULT_VAULT_ROOT}"

    if grep -q "^VAULT_ROOT=" "$PROJECT_ROOT/.env" 2>/dev/null; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^VAULT_ROOT=.*|VAULT_ROOT=$VAULT_ROOT|" "$PROJECT_ROOT/.env"
        else
            sed -i "s|^VAULT_ROOT=.*|VAULT_ROOT=$VAULT_ROOT|" "$PROJECT_ROOT/.env"
        fi
    else
        echo "VAULT_ROOT=$VAULT_ROOT" >> "$PROJECT_ROOT/.env"
    fi
    echo -e "${GREEN}✅ VAULT_ROOT set to $VAULT_ROOT${NC}"
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

# ---------------------------------------------------------------------------
# Anthropic API Key (required for enhance-summary and promote-to-obsidian)
# ---------------------------------------------------------------------------

EXISTING_API_KEY=""

# Check environment first
if [ -n "$ANTHROPIC_API_KEY" ]; then
    EXISTING_API_KEY="$ANTHROPIC_API_KEY"
fi

# Check .env file
if [ -z "$EXISTING_API_KEY" ] && grep -q "^ANTHROPIC_API_KEY=sk-ant-" "$PROJECT_ROOT/.env" 2>/dev/null; then
    EXISTING_API_KEY=$(grep "^ANTHROPIC_API_KEY=" "$PROJECT_ROOT/.env" | cut -d= -f2)
fi

if [ -n "$EXISTING_API_KEY" ]; then
    echo -e "${GREEN}✅ ANTHROPIC_API_KEY already configured${NC}"
    echo "   Key: ${EXISTING_API_KEY:0:20}..."
    echo ""
else
    echo -e "${BLUE}── Anthropic API Key ───────────────────────────────────────${NC}"
    echo ""
    echo "An Anthropic API key is required for:"
    echo "  • enhance-summary.py  — deep session summarization"
    echo "  • promote-to-obsidian.py — writing insights to Obsidian"
    echo ""
    echo "Get your key at: https://console.anthropic.com/settings/keys"
    echo ""
    read -p "Enter your Anthropic API key (or press Enter to skip): " -r API_KEY
    echo ""

    if [ -z "$API_KEY" ]; then
        echo -e "${YELLOW}⚠️  Skipped — enhance-summary and promote-to-obsidian will not work${NC}"
        echo "   Add ANTHROPIC_API_KEY to .env when ready."
        echo ""
    else
        # Validate the key with a minimal API call
        echo "🔄 Validating API key..."
        HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
            https://api.anthropic.com/v1/models \
            -H "x-api-key: $API_KEY" \
            -H "anthropic-version: 2023-06-01")

        if [ "$HTTP_STATUS" = "200" ]; then
            echo -e "${GREEN}✅ API key validated successfully${NC}"

            # Save to .env
            if grep -q "^ANTHROPIC_API_KEY=" "$PROJECT_ROOT/.env" 2>/dev/null; then
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    sed -i '' "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$API_KEY|" "$PROJECT_ROOT/.env"
                else
                    sed -i "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$API_KEY|" "$PROJECT_ROOT/.env"
                fi
            else
                echo "ANTHROPIC_API_KEY=$API_KEY" >> "$PROJECT_ROOT/.env"
            fi
            echo -e "${GREEN}✅ Saved to .env${NC}"
        elif [ "$HTTP_STATUS" = "401" ]; then
            echo -e "${RED}❌ Invalid API key (HTTP 401)${NC}"
            echo "   Check your key at: https://console.anthropic.com/settings/keys"
            echo "   Add manually to .env: ANTHROPIC_API_KEY=sk-ant-..."
        elif [ "$HTTP_STATUS" = "000" ]; then
            echo -e "${YELLOW}⚠️  Could not reach Anthropic API (no internet?)${NC}"
            echo "   Saving key without validation..."
            if grep -q "^ANTHROPIC_API_KEY=" "$PROJECT_ROOT/.env" 2>/dev/null; then
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    sed -i '' "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$API_KEY|" "$PROJECT_ROOT/.env"
                else
                    sed -i "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$API_KEY|" "$PROJECT_ROOT/.env"
                fi
            else
                echo "ANTHROPIC_API_KEY=$API_KEY" >> "$PROJECT_ROOT/.env"
            fi
            echo -e "${GREEN}✅ Saved to .env (unvalidated)${NC}"
        else
            echo -e "${YELLOW}⚠️  Unexpected response (HTTP $HTTP_STATUS) — saving key anyway${NC}"
            if grep -q "^ANTHROPIC_API_KEY=" "$PROJECT_ROOT/.env" 2>/dev/null; then
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    sed -i '' "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$API_KEY|" "$PROJECT_ROOT/.env"
                else
                    sed -i "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$API_KEY|" "$PROJECT_ROOT/.env"
                fi
            else
                echo "ANTHROPIC_API_KEY=$API_KEY" >> "$PROJECT_ROOT/.env"
            fi
            echo -e "${GREEN}✅ Saved to .env${NC}"
        fi
        echo ""
    fi
fi

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
