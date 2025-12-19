#!/bin/bash
# Test Agent MCP Tools - Phase 5
# Comprehensive testing of all agent memory tools

set -e

echo "🧪 Testing Agent MCP Tools - Phase 5"
echo "===================================="
echo ""

MEMORY_DIR="/Users/jamesmba/Data/00 GITHUB/Code/claude-memory"
DB_HOST="localhost"
DB_PORT="5435"
DB_NAME="claude_memory"
DB_USER="memory_admin"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Direct database queries to verify agent data exists
echo -e "${BLUE}Test 1: Verify agent data in database${NC}"
echo "--------------------------------------"

AGENT_COUNT=$(docker exec claude-context-db psql -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM agent_work;" | tr -d ' ')
DEFINITION_COUNT=$(docker exec claude-context-db psql -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM agent_definitions;" | tr -d ' ')

echo "✓ Agent work records: $AGENT_COUNT"
echo "✓ Agent definitions: $DEFINITION_COUNT"

if [ "$AGENT_COUNT" -eq "0" ]; then
    echo -e "${YELLOW}⚠️  No agent work found - some tests may fail${NC}"
fi

echo ""

# Test 2: Test search_agent_work function via SQL
echo -e "${BLUE}Test 2: Test agent work search (vector similarity)${NC}"
echo "---------------------------------------------------"

cat <<'EOF' | docker exec -i claude-context-db psql -U $DB_USER -d $DB_NAME
SELECT
    aw.id,
    aw.agent_id,
    ad.agent_type,
    LEFT(aw.agent_request, 50) as request,
    aw.duration_seconds,
    CASE WHEN aw.embedding IS NOT NULL THEN 'YES' ELSE 'NO' END as has_embedding
FROM agent_work aw
JOIN agent_definitions ad ON ad.id = aw.agent_definition_id
WHERE aw.embedding IS NOT NULL
LIMIT 5;
EOF

echo ""

# Test 3: Test get_agent_analytics via SQL views
echo -e "${BLUE}Test 3: Test agent analytics (performance views)${NC}"
echo "------------------------------------------------"

cat <<'EOF' | docker exec -i claude-context-db psql -U $DB_USER -d $DB_NAME
SELECT
    agent_type,
    version,
    times_used,
    avg_duration_seconds,
    success_rate_pct
FROM v_agent_config_performance
WHERE times_used > 0
ORDER BY agent_type, version
LIMIT 5;
EOF

echo ""

# Test 4: Test compare_agent_configs via SQL
echo -e "${BLUE}Test 4: Test agent config comparison (evolution)${NC}"
echo "-----------------------------------------------"

cat <<'EOF' | docker exec -i claude-context-db psql -U $DB_USER -d $DB_NAME
SELECT
    agent_type,
    version,
    times_used,
    avg_duration_seconds,
    LAG(avg_duration_seconds) OVER (PARTITION BY agent_type ORDER BY version) as prev_duration,
    CASE
        WHEN LAG(avg_duration_seconds) OVER (PARTITION BY agent_type ORDER BY version) IS NOT NULL
        THEN ROUND(
            ((LAG(avg_duration_seconds) OVER (PARTITION BY agent_type ORDER BY version) - avg_duration_seconds)
            / LAG(avg_duration_seconds) OVER (PARTITION BY agent_type ORDER BY version) * 100)::numeric,
            1
        )
        ELSE NULL
    END as improvement_pct
FROM v_agent_config_performance
WHERE agent_type = 'Explore' AND times_used > 0
ORDER BY version;
EOF

echo ""

# Test 5: Test tool usage analytics
echo -e "${BLUE}Test 5: Test tool usage analytics${NC}"
echo "-----------------------------------"

cat <<'EOF' | docker exec -i claude-context-db psql -U $DB_USER -d $DB_NAME
SELECT
    agent_type,
    tool_name,
    total_uses,
    sessions_used_in
FROM v_agent_tool_usage
ORDER BY total_uses DESC
LIMIT 10;
EOF

echo ""

# Test 6: Test agent-snapshot linkage
echo -e "${BLUE}Test 6: Test agent-snapshot linkage (3-table JOIN)${NC}"
echo "--------------------------------------------------"

cat <<'EOF' | docker exec -i claude-context-db psql -U $DB_USER -d $DB_NAME
SELECT
    cs.id as snapshot_id,
    cs.trigger_event,
    COUNT(aw.id) as linked_agents,
    ARRAY_AGG(DISTINCT ad.agent_type) as agent_types
FROM context_snapshots cs
LEFT JOIN agent_work aw ON aw.parent_snapshot_id = cs.id
LEFT JOIN agent_definitions ad ON ad.id = aw.agent_definition_id
WHERE aw.id IS NOT NULL
GROUP BY cs.id
ORDER BY cs.id DESC
LIMIT 5;
EOF

echo ""

# Test 7: Verify embeddings are populated
echo -e "${BLUE}Test 7: Verify embedding coverage${NC}"
echo "-----------------------------------"

cat <<'EOF' | docker exec -i claude-context-db psql -U $DB_USER -d $DB_NAME
SELECT
    COUNT(*) as total,
    COUNT(embedding) as with_embedding,
    ROUND(COUNT(embedding)::numeric / COUNT(*) * 100, 1) as coverage_pct
FROM agent_work;
EOF

echo ""

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ All database tests completed${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Start MCP server: cd mcp-server && npm start"
echo "2. Configure in Claude Desktop settings"
echo "3. Test via Claude Code using MCP tools:"
echo "   - search_agent_work"
echo "   - get_agent_analytics"
echo "   - compare_agent_configs"
echo ""
echo "MCP Server Configuration:"
echo "  DATABASE_URL: postgresql://$DB_USER:***@$DB_HOST:$DB_PORT/$DB_NAME"
echo "  PROCESSOR_URL: http://localhost:3200"
echo ""
