#!/bin/bash
# Claude Memory - Path Migration Utility
# Migrates all stored paths when workspace location changes
# Created: 2025-12-19 (Phase 6B)
#
# Usage:
#   ./scripts/migrate-paths.sh preview /old/path /new/path
#   ./scripts/migrate-paths.sh apply /old/path /new/path

set -e  # Exit on error

# ============================================================
# Configuration
# ============================================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Load .env file if it exists (handle values with spaces)
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a  # Export all variables
    source <(grep -v '^#' "$PROJECT_ROOT/.env" | grep -v '^$' | sed 's/\([^=]*\)=\(.*\)/\1="\2"/')
    set +a
fi

DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_HOST_PORT:-5435}"
DB_NAME="${POSTGRES_DB:-claude_memory}"
DB_USER="${POSTGRES_USER:-memory_admin}"
DB_PASSWORD="${CONTEXT_DB_PASSWORD}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================
# Functions
# ============================================================

print_banner() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║        Claude Memory - Path Migration Utility             ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_help() {
    cat <<EOF
Usage: $0 <mode> <old_path> <new_path>

Modes:
  preview   Preview changes without applying (dry run - safe)
  apply     Apply changes to database (requires confirmation)

Arguments:
  old_path  Current path in database (e.g., /Users/jamesmba/Data/00 GITHUB)
  new_path  New path to migrate to (e.g., /Users/jamesmba/Projects)

Examples:
  # Preview migration (safe - no changes)
  $0 preview "/Users/jamesmba/Data/00 GITHUB" "/Users/jamesmba/Projects"

  # Apply migration (requires confirmation)
  $0 apply "/Users/jamesmba/Data/00 GITHUB" "/Users/jamesmba/Projects"

Environment:
  Database connection is configured via .env file or defaults:
  - Host: ${DB_HOST}
  - Port: ${DB_PORT}
  - Database: ${DB_NAME}
  - User: ${DB_USER}

Requirements:
  - PostgreSQL client (psql) installed
  - Docker containers running (docker-compose up)
  - .env file configured with CONTEXT_DB_PASSWORD

Workflow:
  1. Run 'preview' mode first to see what will change
  2. Review the output carefully
  3. Run 'apply' mode to execute the migration
  4. Update .env file with new CLAUDE_WORKSPACE_ROOT
  5. Restart containers: docker-compose down && docker-compose up -d

EOF
}

check_requirements() {
    # Check if psql is available
    if ! command -v psql &> /dev/null; then
        echo -e "${RED}❌ Error: psql command not found${NC}"
        echo "Please install PostgreSQL client:"
        echo "  macOS: brew install postgresql"
        echo "  Ubuntu: sudo apt-get install postgresql-client"
        exit 1
    fi

    # Check if database password is set
    if [ -z "$DB_PASSWORD" ]; then
        echo -e "${RED}❌ Error: CONTEXT_DB_PASSWORD not set${NC}"
        echo "Please set it in .env file or environment"
        exit 1
    fi

    # Check if containers are running
    if ! docker ps | grep -q claude-context-db; then
        echo -e "${YELLOW}⚠️  Warning: claude-context-db container not running${NC}"
        echo "Start it with: docker-compose up -d"
        echo ""
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

run_migration() {
    local mode=$1
    local old_path=$2
    local new_path=$3
    local dry_run="true"

    if [ "$mode" = "apply" ]; then
        dry_run="false"
    fi

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Migration Settings${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "Mode:     ${YELLOW}$mode${NC}"
    echo -e "Old path: ${RED}$old_path${NC}"
    echo -e "New path: ${GREEN}$new_path${NC}"
    echo -e "Dry run:  $dry_run"
    echo ""

    # Confirmation for apply mode
    if [ "$mode" = "apply" ]; then
        echo -e "${YELLOW}⚠️  WARNING: This will modify the database!${NC}"
        echo ""
        read -p "Are you sure you want to continue? (yes/NO): " -r
        echo
        if [[ ! $REPLY = "yes" ]]; then
            echo -e "${YELLOW}Migration cancelled${NC}"
            exit 0
        fi
    fi

    # Execute migration
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Executing Migration${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    export PGPASSWORD="$DB_PASSWORD"

    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF
SELECT * FROM migrate_project_paths(
    '$old_path',
    '$new_path',
    dry_run := $dry_run
);
EOF

    local exit_code=$?
    unset PGPASSWORD

    if [ $exit_code -eq 0 ]; then
        echo ""
        if [ "$mode" = "preview" ]; then
            echo -e "${GREEN}✅ Preview complete - no changes made${NC}"
            echo ""
            echo "Next steps:"
            echo "  1. Review the output above"
            echo "  2. Run with 'apply' mode to execute migration"
        else
            echo -e "${GREEN}✅ Migration complete!${NC}"
            echo ""
            echo "Next steps:"
            echo "  1. Update .env file:"
            echo "     CLAUDE_WORKSPACE_ROOT=$new_path"
            echo "  2. Restart containers:"
            echo "     docker-compose down && docker-compose up -d"
            echo "  3. Verify system is working"
        fi
    else
        echo -e "${RED}❌ Migration failed${NC}"
        exit $exit_code
    fi
}

# ============================================================
# Main
# ============================================================

print_banner

# Parse arguments
if [ "$#" -ne 3 ]; then
    print_help
    exit 1
fi

MODE=$1
OLD_PATH=$2
NEW_PATH=$3

# Validate mode
if [ "$MODE" != "preview" ] && [ "$MODE" != "apply" ]; then
    echo -e "${RED}❌ Error: Invalid mode '$MODE'${NC}"
    echo "Must be 'preview' or 'apply'"
    echo ""
    print_help
    exit 1
fi

# Validate paths
if [ -z "$OLD_PATH" ] || [ -z "$NEW_PATH" ]; then
    echo -e "${RED}❌ Error: Both old_path and new_path are required${NC}"
    print_help
    exit 1
fi

if [ "$OLD_PATH" = "$NEW_PATH" ]; then
    echo -e "${RED}❌ Error: old_path and new_path are identical${NC}"
    exit 1
fi

# Check requirements
check_requirements

# Run migration
run_migration "$MODE" "$OLD_PATH" "$NEW_PATH"
