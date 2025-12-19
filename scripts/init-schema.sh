#!/bin/bash
# Claude Memory - Schema Initialization Script
# Applies all schema migrations in correct order
# Created: 2025-12-19 (Phase 6B)
#
# Usage:
#   ./scripts/init-schema.sh

set -e  # Exit on error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
SCHEMA_DIR="$PROJECT_ROOT/schema"

# Load .env file if it exists (handle values with spaces)
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a  # Export all variables
    source <(grep -v '^#' "$PROJECT_ROOT/.env" | grep -v '^$' | sed 's/\([^=]*\)=\(.*\)/\1="\2"/')
    set +a
fi

# Database connection
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_HOST_PORT:-5435}"
DB_NAME="${POSTGRES_DB:-claude_memory}"
DB_USER="${POSTGRES_USER:-memory_admin}"
DB_PASSWORD="${CONTEXT_DB_PASSWORD}"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Claude Memory - Schema Initialization & Migration     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check password
if [ -z "$DB_PASSWORD" ]; then
    echo -e "${RED}❌ Error: CONTEXT_DB_PASSWORD not set${NC}"
    echo "Please set it in .env file"
    exit 1
fi

export PGPASSWORD="$DB_PASSWORD"

# Function to run SQL file
run_sql() {
    local file=$1
    local description=$2

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Running: $description${NC}"
    echo -e "${BLUE}File: $(basename $file)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$file"; then
        echo -e "${GREEN}✅ Success${NC}"
        echo ""
    else
        echo -e "${RED}❌ Failed${NC}"
        exit 1
    fi
}

# Check if database exists
echo "Checking database connection..."
if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${RED}❌ Cannot connect to PostgreSQL${NC}"
    echo "Make sure Docker containers are running:"
    echo "  docker-compose up -d"
    exit 1
fi
echo -e "${GREEN}✅ Database connection OK${NC}"
echo ""

# Check if claude_memory database exists
DB_EXISTS=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'")

if [ -z "$DB_EXISTS" ]; then
    echo -e "${YELLOW}Database '$DB_NAME' does not exist${NC}"
    echo "This is normal on first setup - database will be created by Docker init script"
    echo ""
    echo "Wait for Docker to initialize the database, then run this script again"
    exit 0
fi

# Apply migrations in order
echo -e "${GREEN}Database '$DB_NAME' found, applying migrations...${NC}"
echo ""

# Migration 1: Base schema (already applied by Docker init, but safe to re-run)
echo -e "${YELLOW}ℹ️  Skipping init.sql (already applied by Docker)${NC}"
echo ""

# Migration 2: Add Phase 1 views (if not already applied)
if [ -f "$SCHEMA_DIR/migrate-add-phase1-views.sql" ]; then
    run_sql "$SCHEMA_DIR/migrate-add-phase1-views.sql" "Phase 1 Analytical Views"
fi

# Migration 3: Add agent tables (if not already applied)
if [ -f "$SCHEMA_DIR/add-agent-tables.sql" ]; then
    run_sql "$SCHEMA_DIR/add-agent-tables.sql" "Agent Capture Tables & Views"
fi

# Migration 4: Add transcript_path column (Phase 6B)
if [ -f "$SCHEMA_DIR/add-transcript-path-column.sql" ]; then
    run_sql "$SCHEMA_DIR/add-transcript-path-column.sql" "Add transcript_path Column"
fi

# Migration 5: Add path migration function
if [ -f "$SCHEMA_DIR/migrate_project_paths.sql" ]; then
    run_sql "$SCHEMA_DIR/migrate_project_paths.sql" "Path Migration Function"
fi

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║            Schema Initialization Complete!                ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Next steps:"
echo "  1. Verify schema: psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c '\\dt'"
echo "  2. Run path migration if needed: ./scripts/migrate-paths.sh preview <old> <new>"
echo ""

unset PGPASSWORD
