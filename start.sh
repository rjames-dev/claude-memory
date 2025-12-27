#!/bin/bash
#
# Claude Memory System - Easy Startup Guide
#
# This script checks prerequisites and guides you through the setup process.
# It doesn't make changes - it just validates your configuration and provides
# clear next steps.
#
# Usage: ./start.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Status tracking
CHECKS_PASSED=0
CHECKS_FAILED=0
WARNINGS=0

echo ""
echo "========================================================================"
echo "Claude Memory System - Easy Startup Guide"
echo "========================================================================"
echo ""
echo "This script will check your setup and guide you through the process."
echo "Expected time: 5-10 minutes for first-time setup"
echo ""

# Function to print check status
check_pass() {
    echo -e "${GREEN}✅ $1${NC}"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
}

check_fail() {
    echo -e "${RED}❌ $1${NC}"
    CHECKS_FAILED=$((CHECKS_FAILED + 1))
}

check_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    WARNINGS=$((WARNINGS + 1))
}

info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

section() {
    echo ""
    echo -e "${BOLD}$1${NC}"
    echo "----------------------------------------"
}

# =============================================================================
# 1. PREREQUISITES CHECK
# =============================================================================

section "1. Checking Prerequisites"

# Check Docker
if command -v docker &> /dev/null; then
    if docker info &> /dev/null; then
        check_pass "Docker is installed and running"
    else
        check_fail "Docker is installed but not running"
        echo "   → Start Docker Desktop and try again"
    fi
else
    check_fail "Docker is not installed"
    echo "   → Download from: https://www.docker.com/products/docker-desktop"
fi

# Check Python 3
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    check_pass "Python 3 is installed (version $PYTHON_VERSION)"
else
    check_fail "Python 3 is not installed"
    echo "   → Usually pre-installed on macOS/Linux"
fi

# Check Node.js (optional for MCP)
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    check_pass "Node.js is installed ($NODE_VERSION) - MCP tools available"
else
    check_warn "Node.js not installed - MCP search tools won't work"
    echo "   → Download from: https://nodejs.org/ (optional)"
fi

# =============================================================================
# 2. ENVIRONMENT CONFIGURATION
# =============================================================================

section "2. Environment Configuration (.env file)"

if [ ! -f ".env" ]; then
    check_fail ".env file not found"
    echo ""
    echo "   → Run: cp .env.example .env"
    echo "   → Then edit .env to configure your setup"
    echo ""
else
    check_pass ".env file exists"

    # Load .env safely (handle values with spaces)
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ "$key" =~ ^#.*$ ]] && continue
        [[ -z "$key" ]] && continue

        # Remove quotes if present
        value="${value%\"}"
        value="${value#\"}"
        value="${value%\'}"
        value="${value#\'}"

        # Export the variable
        export "$key=$value"
    done < .env

    # Check CONTEXT_DB_PASSWORD
    if [ -z "$CONTEXT_DB_PASSWORD" ]; then
        check_fail "CONTEXT_DB_PASSWORD not set in .env"
        echo "   → Add to .env: CONTEXT_DB_PASSWORD=\$(openssl rand -base64 32)"
    else
        if [ "$CONTEXT_DB_PASSWORD" = "your_secure_password_here" ]; then
            check_fail "CONTEXT_DB_PASSWORD is still the example value"
            echo "   → Generate secure password: openssl rand -base64 32"
        else
            check_pass "Database password configured"
        fi
    fi

    # Check CLAUDE_WORKSPACE_ROOT
    if [ -z "$CLAUDE_WORKSPACE_ROOT" ]; then
        check_warn "CLAUDE_WORKSPACE_ROOT not set in .env"
        echo "   → This determines where Claude Code should be installed"
        echo "   → Example: CLAUDE_WORKSPACE_ROOT=/Users/yourname/workspace"
    else
        if [ -d "$CLAUDE_WORKSPACE_ROOT" ]; then
            check_pass "Workspace root configured: $CLAUDE_WORKSPACE_ROOT"
        else
            check_warn "Workspace root configured but directory doesn't exist: $CLAUDE_WORKSPACE_ROOT"
            echo "   → Create it: mkdir -p $CLAUDE_WORKSPACE_ROOT"
        fi
    fi

    # Check ANTHROPIC_API_KEY (optional)
    if [ -z "$ANTHROPIC_API_KEY" ]; then
        check_warn "ANTHROPIC_API_KEY not set (optional)"
        echo "   → Required for: /mem-enhance-summary feature (premium summaries)"
        echo "   → Get key from: https://console.anthropic.com/keys"
        echo "   → Add to .env: ANTHROPIC_API_KEY=sk-ant-..."
    else
        if [[ "$ANTHROPIC_API_KEY" == sk-ant-* ]]; then
            check_pass "Anthropic API key configured (enhance-summary available)"
        else
            check_warn "ANTHROPIC_API_KEY format looks incorrect (should start with sk-ant-)"
        fi
    fi
fi

# =============================================================================
# 3. WORKSPACE CONCEPT EXPLANATION
# =============================================================================

section "3. Understanding the Workspace"

echo "Claude Memory works with a 'workspace' concept:"
echo ""
echo "  ${BOLD}Workspace Root${NC} (set in .env as CLAUDE_WORKSPACE_ROOT)"
echo "  └── Project 1/"
echo "      ├── code/"
echo "      └── .claude/           ← Start Claude Code here"
echo "  └── Project 2/"
echo "      ├── code/"
echo "      └── .claude/           ← Or here"
echo ""
echo "Key Points:"
echo "  • Claude Code should be started ${BOLD}inside or below${NC} your workspace root"
echo "  • All /mem-* commands work in projects under the workspace"
echo "  • Install Claude Memory ${BOLD}outside${NC} your project directories"
echo ""

if [ -n "$CLAUDE_WORKSPACE_ROOT" ]; then
    info "Your workspace is configured as: $CLAUDE_WORKSPACE_ROOT"
    info "Claude Code can run in any project inside that directory"
else
    check_warn "Set CLAUDE_WORKSPACE_ROOT in .env to enable workspace tracking"
fi

# =============================================================================
# 4. DOCKER STATUS
# =============================================================================

section "4. Docker Containers Status"

if docker info &> /dev/null; then
    RUNNING_CONTAINERS=$(docker ps --filter "name=claude-" --format "{{.Names}}" 2>/dev/null | wc -l)

    if [ "$RUNNING_CONTAINERS" -gt 0 ]; then
        check_pass "Claude Memory containers are running ($RUNNING_CONTAINERS containers)"
        docker ps --filter "name=claude-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    else
        check_warn "Claude Memory containers are not running"
        echo "   → Start them with: docker-compose up -d"
    fi
else
    check_warn "Cannot check Docker status (Docker not running)"
fi

# =============================================================================
# 5. PYTHON DEPENDENCIES
# =============================================================================

section "5. Python Dependencies"

if [ -f "requirements.txt" ]; then
    # Check if any key dependencies are installed
    if python3 -c "import psycopg2" &> /dev/null; then
        check_pass "Python dependencies installed"
    else
        check_warn "Python dependencies not installed"
        echo "   → Run: pip3 install -r requirements.txt"
    fi
else
    check_warn "requirements.txt not found"
fi

# =============================================================================
# 6. SKILLS SYSTEM STATUS
# =============================================================================

section "6. Skills System Status"

if [ -f "skills/example-skills.json" ]; then
    SKILL_COUNT=$(python3 -c "import json; data=json.load(open('skills/example-skills.json')); print(data.get('skill_count', 0))" 2>/dev/null || echo "?")
    check_pass "Skills package found ($SKILL_COUNT example skills ready)"
else
    check_warn "Skills package not found (skills/example-skills.json)"
fi

# Check if skills are loaded in database (requires DB to be running)
if docker ps --filter "name=claude-context-db" --format "{{.Names}}" &> /dev/null; then
    LOADED_SKILLS=$(python3 -c "
from db_utils import get_db_connection
try:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM skills_agents WHERE is_active = TRUE')
    print(cur.fetchone()[0])
    cur.close()
    conn.close()
except:
    print('0')
" 2>/dev/null || echo "0")

    if [ "$LOADED_SKILLS" -gt 0 ]; then
        check_pass "Skills loaded in database ($LOADED_SKILLS active skills)"
    else
        check_warn "No skills loaded in database yet"
        echo "   → Run: ./scripts/import-and-initialize-skills.sh"
    fi
fi

# =============================================================================
# SUMMARY AND NEXT STEPS
# =============================================================================

echo ""
echo "========================================================================"
echo "Setup Status Summary"
echo "========================================================================"
echo ""
echo -e "${GREEN}Checks Passed: $CHECKS_PASSED${NC}"
if [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
fi
if [ $CHECKS_FAILED -gt 0 ]; then
    echo -e "${RED}Checks Failed: $CHECKS_FAILED${NC}"
fi
echo ""

# =============================================================================
# NEXT STEPS
# =============================================================================

if [ $CHECKS_FAILED -gt 0 ]; then
    echo -e "${BOLD}❌ Setup Incomplete${NC}"
    echo ""
    echo "Please fix the failed checks above before continuing."
    echo ""
    exit 1
fi

echo -e "${BOLD}Next Steps:${NC}"
echo ""

# Determine what needs to be done
CONTAINERS_RUNNING=$(docker ps --filter "name=claude-" --format "{{.Names}}" 2>/dev/null | wc -l || echo "0")

if [ "$CONTAINERS_RUNNING" -eq 0 ]; then
    echo "1️⃣  ${BOLD}Start Docker Containers${NC} (2-3 minutes)"
    echo "   ${BLUE}docker-compose up -d${NC}"
    echo ""
    echo "   This starts:"
    echo "   • PostgreSQL database (context storage)"
    echo "   • Ollama (AI summaries with llama3.2)"
    echo "   • Node processor (auto-capture worker)"
    echo ""
fi

if [ "$LOADED_SKILLS" -eq 0 ]; then
    echo "2️⃣  ${BOLD}Load Skills${NC} (1-2 minutes)"
    echo "   ${BLUE}./scripts/import-and-initialize-skills.sh${NC}"
    echo ""
    echo "   This loads 9 example skills and generates embeddings."
    echo ""
fi

echo "3️⃣  ${BOLD}Install Slash Commands${NC} (<1 minute)"
echo "   ${BLUE}./scripts/install-commands.sh${NC}"
echo ""
echo "   This installs 13 /mem-* commands globally."
echo ""

echo "4️⃣  ${BOLD}Configure Auto-Capture Hooks${NC} (2 minutes)"
echo "   See README section: 'Configure Auto-Capture Hooks'"
echo ""

echo "5️⃣  ${BOLD}Start Using Claude Memory!${NC}"
echo "   • Open Claude Code in a project under: $CLAUDE_WORKSPACE_ROOT"
echo "   • Try: ${BLUE}/mem-skills${NC}"
echo "   • Try: ${BLUE}/mem-skills-search \"database\"${NC}"
echo ""

echo "========================================================================"
echo "Expected Total Time: 5-10 minutes"
echo "========================================================================"
echo ""

echo "For detailed instructions, see: README.md"
echo ""

if [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}Note: Warnings indicate optional features that won't work until configured.${NC}"
    echo ""
fi

exit 0
