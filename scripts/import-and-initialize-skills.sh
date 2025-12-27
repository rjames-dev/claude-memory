#!/bin/bash
#
# Import Skills and Initialize Embeddings
#
# One-step script to import example skills and generate embeddings.
# Run this after first-time installation to populate the skills database.
#
# Usage:
#   ./scripts/import-and-initialize-skills.sh
#   ./scripts/import-and-initialize-skills.sh --skip-existing
#

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SKILLS_FILE="$PROJECT_ROOT/skills/example-skills.json"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo "========================================================================"
echo "Claude Memory - Skills System Initialization"
echo "========================================================================"
echo ""

# Check if skills file exists
if [ ! -f "$SKILLS_FILE" ]; then
    echo -e "${RED}❌ Skills file not found: $SKILLS_FILE${NC}"
    echo ""
    echo "Please ensure you're running this from the claude-memory directory."
    exit 1
fi

# Check if database is accessible
echo -e "${BLUE}[1/5] Checking database connection...${NC}"
if ! python3 "$PROJECT_ROOT/db_utils.py" > /dev/null 2>&1; then
    echo -e "${RED}❌ Database connection failed${NC}"
    echo ""
    echo "Please ensure:"
    echo "  1. Docker containers are running: docker-compose ps"
    echo "  2. .env file is configured with CONTEXT_DB_PASSWORD"
    echo ""
    exit 1
fi
echo -e "${GREEN}✅ Database connection successful${NC}"
echo ""

# Check if skills tables exist, create if needed
echo -e "${BLUE}[2/5] Checking skills database schema...${NC}"

# Load database password
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep "^CONTEXT_DB_PASSWORD=" "$PROJECT_ROOT/.env" | grep -v "^#" | xargs)
fi
DB_PASSWORD="${CONTEXT_DB_PASSWORD:-memory_secure_2024}"

# Check if skills_agents table exists
TABLE_EXISTS=$(docker exec claude-context-db psql -U memory_admin -d claude_memory -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'skills_agents');" 2>/dev/null)

if [ "$TABLE_EXISTS" = "t" ]; then
    echo -e "${GREEN}✅ Skills tables already exist${NC}"

    # Check embedding dimension (should be 1024 for Ollama mxbai-embed-large)
    CURRENT_DIM=$(docker exec claude-context-db psql -U memory_admin -d claude_memory -tAc "SELECT atttypmod - 4 FROM pg_attribute WHERE attrelid = 'skills_triggers'::regclass AND attname = 'embedding';" 2>/dev/null)

    if [ -n "$CURRENT_DIM" ] && [ "$CURRENT_DIM" != "1024" ]; then
        echo "   Fixing embedding dimension ($CURRENT_DIM → 1024)..."
        if docker exec -i claude-context-db psql -U memory_admin -d claude_memory < "$PROJECT_ROOT/schema/migrate-skills-embedding-dimension.sql" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Embedding dimension migrated to 1024${NC}"
        else
            echo -e "${YELLOW}⚠️  Migration had warnings (this is usually OK)${NC}"
        fi
    elif [ "$CURRENT_DIM" = "1024" ]; then
        echo -e "${GREEN}✅ Embedding dimension correct (1024)${NC}"
    fi
else
    echo "Skills tables not found. Creating schema..."

    if [ ! -f "$PROJECT_ROOT/schema/add-skills-tables.sql" ]; then
        echo -e "${RED}❌ Schema file not found: schema/add-skills-tables.sql${NC}"
        exit 1
    fi

    if docker exec -i claude-context-db psql -U memory_admin -d claude_memory < "$PROJECT_ROOT/schema/add-skills-tables.sql" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Skills tables created successfully${NC}"
    else
        echo -e "${RED}❌ Failed to create skills tables${NC}"
        echo "   Try running manually:"
        echo "   docker exec -i claude-context-db psql -U memory_admin -d claude_memory < schema/add-skills-tables.sql"
        exit 1
    fi
fi
echo ""

# Import skills
echo -e "${BLUE}[3/5] Importing example skills...${NC}"
cd "$PROJECT_ROOT"

IMPORT_ARGS=()
IMPORT_ARGS+=("$SKILLS_FILE")

if [ "$1" = "--skip-existing" ]; then
    IMPORT_ARGS+=("--skip-existing")
    echo "(Using --skip-existing mode)"
fi

if python3 import-skill.py "${IMPORT_ARGS[@]}"; then
    echo -e "${GREEN}✅ Skills imported successfully${NC}"
else
    echo -e "${RED}❌ Skill import failed${NC}"
    exit 1
fi
echo ""

# Check if Ollama embedding model is available
echo -e "${BLUE}[4/5] Checking Ollama embedding model...${NC}"

# Check if mxbai-embed-large model exists
MODEL_EXISTS=$(docker exec claude-ollama ollama list 2>/dev/null | grep -c "mxbai-embed-large" || echo "0")

if [ "$MODEL_EXISTS" -gt 0 ]; then
    echo -e "${GREEN}✅ Embedding model already available${NC}"
else
    echo "Embedding model not found. Pulling mxbai-embed-large (~669MB, one-time download)..."

    if docker exec claude-ollama ollama pull mxbai-embed-large; then
        echo -e "${GREEN}✅ Embedding model downloaded successfully${NC}"
    else
        echo -e "${RED}❌ Failed to download embedding model${NC}"
        echo "   Try running manually:"
        echo "   docker exec claude-ollama ollama pull mxbai-embed-large"
        exit 1
    fi
fi
echo ""

# Generate embeddings
echo -e "${BLUE}[5/5] Generating embeddings for semantic search...${NC}"
if python3 generate-trigger-embeddings.py --backfill; then
    echo -e "${GREEN}✅ Embeddings generated successfully${NC}"
else
    echo -e "${RED}❌ Embedding generation failed${NC}"
    exit 1
fi
echo ""

# Success summary
echo "========================================================================"
echo -e "${GREEN}✅ Skills System Initialization Complete!${NC}"
echo "========================================================================"
echo ""
echo "You can now use:"
echo "  • /mem-skills               - List all skills"
echo "  • /mem-skills-search <query> - Search skills semantically"
echo "  • /mem-skills-stats --all   - View performance statistics"
echo ""
echo "Example:"
echo "  /mem-skills-search \"check database health\""
echo ""
echo "For more information, see README.md"
echo ""
