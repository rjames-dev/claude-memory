# Tutorial: Querying Conversation History with SQL + LLM Formatting

**Created:** 2025-12-23
**Difficulty:** Intermediate
**Time:** 10-15 minutes
**Prerequisites:** Docker running, claude-memory installed, basic SQL knowledge

---

## What You'll Learn

This tutorial demonstrates how to:
1. Query raw conversation data directly from PostgreSQL
2. Format SQL results using LLM for beautiful, user-friendly presentation
3. Compare token consumption: MCP tools vs SQL vs file reads
4. Choose the right approach for different use cases

---

## The Scenario

**User Question:**
> "What did we discuss about token consumption in Phase 8?"

**Challenge:**
- The discussion happened in a previous session (Snapshot #32)
- Multiple approaches available: MCP tools, SQL queries, reading planning docs
- Need to balance: accuracy, token cost, and presentation quality

---

## Approach 1: Using MCP Tools (Phase 8 Feature)

### Step 1: Try Summary Search

```javascript
mcp__claude-memory__search_memory({
  query: "Phase 8 token consumption reduction",
  limit: 5
})
```

**Result:** ✅ Found Snapshot #32
**Token Cost:** ~500 tokens
**Output Quality:** Good high-level summary, but lacking specific details

### Step 2: Try Raw Message Search

```javascript
mcp__claude-memory__search_raw_messages({
  query: "89% reduction",
  limit: 3
})
```

**Result:** ✅ Found matching messages with snippets
**Token Cost:** ~1,500 tokens
**Output Quality:** Better - shows 200-char context around matches

**Limitations:**
- Snippets only (not full context)
- Pre-formatted output (limited customization)
- Can't do complex queries (multiple conditions, joins, etc.)

---

## Approach 2: Direct SQL Queries + LLM Formatting

### Step 1: Connect to Database

```bash
cd /path/to/claude-memory
docker exec -i claude-context-db psql \
  -U memory_admin \
  -d claude_memory
```

### Step 2: Find Messages About "89% reduction"

```sql
-- Extract messages containing specific phrase
SELECT
  cs.id,
  cs.timestamp,
  cs.project_path,
  msg->>'role' as role,
  LEFT(msg->>'content', 200) as content_preview
FROM context_snapshots cs,
  jsonb_array_elements(cs.raw_context->'messages') as msg
WHERE msg->>'content' ILIKE '%89% reduction%'
ORDER BY cs.timestamp DESC;
```

**Raw Output:**
```
id |           timestamp           | project_path | role      | content_preview
----+-------------------------------+--------------+-----------+-------------------------
 32 | 2025-12-24 01:05:42.574134+00 | .../claude-memory | assistant | **EXCELLENT insight!** You've identified the root cause of your short sessions...
(1 row)
```

**Token Cost:** ~200 tokens (raw SQL output)
**Output Quality:** Accurate but hard to read

### Step 3: Get Full Context Around Match

```sql
-- Extract context around the "89% reduction" phrase
SELECT
  SUBSTRING(
    msg->>'content'
    FROM POSITION('13,500 tokens' IN msg->>'content') - 200
    FOR 600
  ) as context_snippet
FROM context_snapshots cs,
  jsonb_array_elements(cs.raw_context->'messages') as msg
WHERE cs.id = 32
  AND msg->>'content' ILIKE '%89% reduction%';
```

**Raw Output:**
```
   → 1,500 tokens

 vs Current:
   → search_memory (summary only)
   → Grep files
   → Read files
   → 13,500 tokens

 Savings: 89% token reduction!
```

**Token Cost:** ~300 tokens
**Output Quality:** Precise but unformatted

### Step 4: LLM Format the Results

**Prompt to LLM:**
> "Based on the SQL query output, format this information in a user-friendly way with clear sections, highlights, and context."

**Formatted Output:**

---

# 🔍 Search Results: "89% Reduction" Discussion

## 📊 Query Summary
- **Search Term:** "89% reduction"
- **Results Found:** 1 message
- **Source:** Snapshot #32
- **Date:** December 24, 2025 at 1:05 AM
- **Project:** claude-memory
- **Context:** Phase 8 planning conversation

## 💡 What We Discussed

### The Problem You Identified
You noticed that I was burning through tokens by:
1. Searching summaries (didn't find enough detail)
2. Falling back to grepping files
3. Reading multiple files to find what I needed
4. This pattern was causing your sessions to end in just 20-30 minutes

### The Solution: Phase 8 Raw Message Search
A new database search tool that queries actual conversation content.

## 📈 Token Consumption Comparison

| Approach | Search Process | Token Cost | Time |
|----------|---------------|------------|------|
| **Before Phase 8** | Summary search → Grep → Read files | **13,500 tokens** | 5-10 min |
| **After Phase 8** | Direct message search | **1,500 tokens** | 1 min |
| **Savings** | — | **89% reduction** | **90% faster** |

## ⏱️ Session Length Impact

### Before (Current State)
- 3-5 searches × 10K tokens = 30-50K tokens
- **Total: 80-100K tokens in 20-30 minutes** → Auto-compact triggered

### After (With Phase 8)
- 5-10 searches × 1.5K tokens = 7.5-15K tokens
- **Total: 40-65K tokens in 2-3 hours** → Much longer sessions

### Result
**Your sessions would be 4-6x longer!**

---

**Token Cost:** ~1,800 tokens (SQL output + LLM formatting)
**Output Quality:** ⭐⭐⭐⭐⭐ Excellent - readable, contextualized, actionable

---

## Approach 3: Reading Planning Documents

For comparison, let's see what reading the planning doc costs:

```bash
# Read the Phase 8 planning document
Read file_path="/path/to/dev-docs/planning/phase-8-raw-message-search.md"
```

**Result:** Complete information about Phase 8
**Token Cost:** ~8,000 tokens (634 lines × ~12 tokens/line)
**Output Quality:** Comprehensive but overwhelming

---

## Token Consumption Comparison

| Approach | Method | Token Cost | Quality | Best For |
|----------|--------|------------|---------|----------|
| **MCP Summary Search** | search_memory | ~500 | Good overview | "What did we work on?" |
| **MCP Raw Search** | search_raw_messages | ~1,500 | Snippets with context | Finding specific code/text |
| **SQL + LLM Formatting** | Direct query + format | ~2,000 | Customized presentation | Specific analysis needs |
| **Read Planning Doc** | Read tool | ~8,000 | Complete but verbose | Need full specification |
| **Traditional Grep+Read** | Grep → Read files | ~13,500 | Comprehensive but costly | Current state of files |

### Cost Savings Analysis

**Scenario:** Finding Phase 8 token discussion details

- ❌ **Read planning doc:** 8,000 tokens
- ❌ **Grep + Read files:** 13,500 tokens
- ✅ **SQL + LLM format:** 2,000 tokens

**Savings:**
- vs Reading doc: **75% reduction**
- vs Grep+Read: **85% reduction**

---

## When to Use Each Approach

### Use MCP Search Tools When:
✅ You want quick answers without leaving Claude Code
✅ General "what did we work on?" questions
✅ Finding code snippets or error messages
✅ Standard format is good enough

**Example:** "What security fixes did we implement?"

### Use SQL Queries When:
✅ You need complex filtering (multiple conditions)
✅ You want to analyze patterns across snapshots
✅ You're debugging or doing data analysis
✅ You need exact control over what's returned

**Example:** "Show me all user messages about sessions from the last week"

### Use SQL + LLM Formatting When:
✅ Everything from SQL queries, PLUS:
✅ You want beautiful, user-friendly output
✅ You're creating documentation or reports
✅ You need customized presentation
✅ The data needs context and explanation

**Example:** "Create a formatted report of our Phase 8 discussion"

### Use File Reads When:
✅ You need the CURRENT state of a file (not historical)
✅ The file hasn't been captured yet
✅ You're verifying what's on disk right now

**Example:** "What's in the .env file right now?"

---

## Real-World Workflow Example

This tutorial is based on an actual conversation. Here's how it unfolded:

### The Question
**User:** "What did we discuss about token consumption in Phase 8?"

### Iteration 1: Try MCP Search
```javascript
search_memory("Phase 8 token consumption")
```
**Result:** Found Snapshot #32, but summary was high-level

### Iteration 2: Try Raw Message Search
```javascript
search_raw_messages("89% reduction")
```
**Result:** Found the message with 200-char snippets - better!

### Iteration 3: Get Full Context via SQL
```bash
docker exec -i claude-context-db psql -U memory_admin -d claude_memory -c "
  SELECT msg->>'content'
  FROM context_snapshots cs,
    jsonb_array_elements(cs.raw_context->'messages') as msg
  WHERE cs.id = 32 AND msg->>'content' ILIKE '%89% reduction%';
"
```
**Result:** Full message content retrieved

### Iteration 4: Format for User
LLM processed the SQL output and created the beautiful formatted report shown earlier.

### Follow-Up Question
**User:** "What was my comment that generated this discussion?"

### Solution: Another SQL Query
```sql
SELECT msg->>'content'
FROM context_snapshots cs,
  jsonb_array_elements(cs.raw_context->'messages') as msg
WHERE cs.id = 32
  AND msg->>'role' = 'user'
  AND msg->>'content' ILIKE '%quick time outs%'
LIMIT 1;
```

**Result:** Found the exact user observation that sparked Phase 8

**Then formatted it beautifully** with emoji headers, tables, and context explanation.

**Total Token Cost for Entire Exploration:** ~4,000 tokens

**Alternative Approach Cost:**
- Read Phase 8 planning doc: 8,000 tokens
- Read multiple conversation logs: 15,000+ tokens
- Grep + Read workflow: 20,000+ tokens

**Savings: 75-80%** compared to traditional approaches!

---

## Useful SQL Query Templates

### 1. Find Messages by Content
```sql
SELECT
  cs.id,
  to_char(cs.timestamp, 'YYYY-MM-DD HH24:MI') as time,
  msg->>'role' as role,
  LEFT(msg->>'content', 200) as preview
FROM context_snapshots cs,
  jsonb_array_elements(cs.raw_context->'messages') as msg
WHERE msg->>'content' ILIKE '%search_term%'
ORDER BY cs.timestamp DESC
LIMIT 10;
```

### 2. Get Full Conversation for a Snapshot
```sql
SELECT
  msg->>'role' as role,
  msg->>'content' as content
FROM context_snapshots cs,
  jsonb_array_elements(cs.raw_context->'messages') as msg
WHERE cs.id = 32
ORDER BY jsonb_array_elements_index(cs.raw_context->'messages');
```

### 3. Search User Messages Only
```sql
SELECT
  cs.id,
  cs.timestamp,
  msg->>'content' as user_message
FROM context_snapshots cs,
  jsonb_array_elements(cs.raw_context->'messages') as msg
WHERE msg->>'role' = 'user'
  AND msg->>'content' ILIKE '%keyword%'
ORDER BY cs.timestamp DESC;
```

### 4. Get Context Around a Match
```sql
SELECT
  cs.id,
  SUBSTRING(
    msg->>'content'
    FROM POSITION('search_term' IN msg->>'content') - 200
    FOR 600
  ) as context
FROM context_snapshots cs,
  jsonb_array_elements(cs.raw_context->'messages') as msg
WHERE msg->>'content' ILIKE '%search_term%';
```

### 5. Count Messages by Type
```sql
SELECT
  cs.id,
  cs.timestamp,
  msg->>'role' as role,
  COUNT(*) as message_count
FROM context_snapshots cs,
  jsonb_array_elements(cs.raw_context->'messages') as msg
GROUP BY cs.id, cs.timestamp, msg->>'role'
ORDER BY cs.timestamp DESC;
```

### 6. Find Tool Results
```sql
SELECT
  cs.id,
  msg->>'role' as role,
  msg->'content'->0->>'type' as tool_name,
  LEFT(msg->'content'->0->>'text', 200) as result_preview
FROM context_snapshots cs,
  jsonb_array_elements(cs.raw_context->'messages') as msg
WHERE msg->>'role' = 'tool_result'
  AND msg->'content'->0->>'text' ILIKE '%search_term%'
ORDER BY cs.timestamp DESC;
```

---

## LLM Formatting Guidelines

When asking the LLM to format SQL results, use clear prompts:

### Good Prompt Examples

**For Search Results:**
> "Based on this SQL output showing our Phase 8 discussion, create a user-friendly report with:
> 1. Clear section headers with emoji
> 2. A summary table comparing before/after token costs
> 3. Key insights highlighted
> 4. Context about what the discussion was about"

**For Timeline Analysis:**
> "Format these SQL results as a timeline showing when we made key decisions. Include dates, who said what, and why it mattered."

**For Comparison:**
> "Take these two SQL query results and create a side-by-side comparison table showing the differences."

### Formatting Best Practices

✅ **DO:**
- Use headers (##, ###) for structure
- Add emoji for visual scanning (📊, ✅, ⚠️)
- Create tables for comparisons
- Include context and explanation
- Highlight key numbers and insights
- Add "What This Means" sections

❌ **DON'T:**
- Just dump raw SQL output
- Use overly technical language
- Assume user knows the context
- Skip the "why this matters" explanation

---

## Performance Considerations

### Database Query Performance

**Fast Queries (<100ms):**
- Queries by snapshot ID (indexed)
- Queries by project_path (indexed)
- Simple ILIKE searches on small result sets

**Moderate Queries (100-500ms):**
- Full-text searches across all snapshots
- JSONB extraction with filtering
- Queries with GIN index support

**Slow Queries (>500ms):**
- Complex regex on large datasets
- Multiple JSONB array expansions without indexes
- Searching without WHERE clauses (full table scan)

### Optimization Tips

1. **Use GIN Index for JSONB searches:**
```sql
CREATE INDEX idx_raw_context_gin ON context_snapshots
USING gin (raw_context jsonb_path_ops);
```

2. **Filter by project or date first:**
```sql
-- Good: Filter before expanding JSONB
WHERE cs.project_path = '/path/to/project'
  AND cs.timestamp > NOW() - INTERVAL '7 days'
  AND msg->>'content' ILIKE '%search%'

-- Bad: Expand all JSONB first
WHERE msg->>'content' ILIKE '%search%'  -- Scans everything
```

3. **Use LIMIT to reduce result sets:**
```sql
-- Limit snapshots first, then expand
WITH recent_snapshots AS (
  SELECT * FROM context_snapshots
  WHERE timestamp > NOW() - INTERVAL '30 days'
  LIMIT 50
)
SELECT ... FROM recent_snapshots ...
```

---

## Troubleshooting

### Issue: "No messages found"

**Check:**
1. Is the snapshot ID correct? `SELECT id FROM context_snapshots ORDER BY timestamp DESC;`
2. Is the search term spelled correctly? Use `ILIKE` for case-insensitive
3. Does the message exist? Check: `SELECT COUNT(*) FROM context_snapshots WHERE raw_context::text ILIKE '%term%';`

### Issue: "Query too slow"

**Solutions:**
1. Add GIN index (see optimization tips)
2. Filter by project_path or timestamp first
3. Use LIMIT to reduce result set
4. Check with EXPLAIN ANALYZE: `EXPLAIN ANALYZE SELECT ...`

### Issue: "Container not running"

```bash
# Check status
docker ps --filter "name=claude-memory"

# Start if needed
cd /path/to/claude-memory
docker-compose up -d
```

### Issue: "Permission denied"

```bash
# Wrong user/database
docker exec -i claude-context-db psql -U postgres -d context_db  # ❌

# Correct credentials
docker exec -i claude-context-db psql -U memory_admin -d claude_memory  # ✅
```

---

## Advanced Use Cases

### Use Case 1: Project Timeline Report

**Goal:** Create a timeline of all major decisions in a project

```sql
-- Get all assistant messages mentioning "decision" or "decided"
SELECT
  cs.id,
  to_char(cs.timestamp, 'YYYY-MM-DD') as date,
  LEFT(msg->>'content', 150) as decision_snippet
FROM context_snapshots cs,
  jsonb_array_elements(cs.raw_context->'messages') as msg
WHERE cs.project_path ILIKE '%your-project%'
  AND msg->>'role' = 'assistant'
  AND (msg->>'content' ILIKE '%decision%' OR msg->>'content' ILIKE '%decided%')
ORDER BY cs.timestamp ASC;
```

**Then:** Ask LLM to format as a chronological timeline with context.

### Use Case 2: Error Pattern Analysis

**Goal:** Find all error messages to identify patterns

```sql
-- Find all tool_result messages containing errors
SELECT
  cs.id,
  cs.timestamp,
  msg->'content'->0->>'text' as error_message
FROM context_snapshots cs,
  jsonb_array_elements(cs.raw_context->'messages') as msg
WHERE msg->>'role' = 'tool_result'
  AND msg->'content'->0->>'text' ILIKE '%error%'
ORDER BY cs.timestamp DESC
LIMIT 20;
```

**Then:** Ask LLM to categorize errors and suggest patterns.

### Use Case 3: Code Evolution Tracking

**Goal:** Track how a specific function evolved

```sql
-- Find all mentions of a specific function
SELECT
  cs.id,
  to_char(cs.timestamp, 'YYYY-MM-DD HH24:MI') as time,
  msg->>'role' as role,
  SUBSTRING(msg->>'content' FROM POSITION('validateIdentifier' IN msg->>'content') - 100 FOR 400) as context
FROM context_snapshots cs,
  jsonb_array_elements(cs.raw_context->'messages') as msg
WHERE msg->>'content' ILIKE '%validateIdentifier%'
ORDER BY cs.timestamp ASC;
```

**Then:** Ask LLM to create a "function evolution story" showing how it changed.

---

## Key Takeaways

1. **Three-Tier Approach:**
   - MCP tools: Quick, automated, good for most cases
   - SQL queries: Precise, flexible, for complex needs
   - SQL + LLM: Beautiful, contextualized, for reporting

2. **Token Efficiency:**
   - SQL + LLM: ~2,000 tokens
   - Reading docs: ~8,000 tokens
   - Traditional grep+read: ~13,500 tokens
   - **Savings: 75-85%**

3. **When to Use SQL:**
   - Complex filtering needed
   - Custom output format required
   - Data analysis or debugging
   - Creating reports or documentation

4. **The Power of LLM Formatting:**
   - Transforms raw data into readable stories
   - Adds context and explanation
   - Creates custom presentations
   - Makes data actionable

5. **Best Practice Workflow:**
   1. Start with MCP tools (fast, easy)
   2. If not satisfied, use SQL for precision
   3. Format with LLM for presentation
   4. Document the pattern for reuse

---

## Next Steps

**Try It Yourself:**

1. Find a conversation you had about a specific topic
2. Use `search_memory` to find the snapshot ID
3. Write a SQL query to extract the exact details
4. Ask the LLM to format it beautifully
5. Compare token costs vs reading files

**Explore More:**

- `dev-docs/database-dictionary.md` - Complete schema reference
- `dev-docs/analytical-views-guide.md` - Pre-built analytical queries
- `README.md#search-types` - MCP search tool documentation
- `dev-docs/planning/phase-8-raw-message-search.md` - Technical spec

---

**Tutorial Complete!** You now know how to efficiently query conversation history and present it beautifully while saving 75-85% on token costs. 🎉
