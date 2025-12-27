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
echo -e "${BLUE}[1/3] Checking database connection...${NC}"
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

# Import skills
echo -e "${BLUE}[2/3] Importing example skills...${NC}"
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

# Generate embeddings
echo -e "${BLUE}[3/3] Generating embeddings for semantic search...${NC}"
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
