# Timezone Handling Migration Plan

**Created:** 2025-12-28
**Status:** Planning Phase
**Priority:** CRITICAL - Affects all users outside PST timezone

---

## Executive Summary

**Problem:** Database views hardcode PST timezone conversion, making the system unusable for non-PST users.

**Solution:** Change view calculations to return UTC timestamps with timezone info (`timestamptz`). Display layer (JavaScript, Python) will automatically convert to user's local timezone.

**Key Insight:** Keep field name `pst_time` but change what it returns - from PST-only to timezone-aware UTC. This maintains backwards compatibility while fixing the timezone issue.

**Migration Strategy:** Rename existing views as backups, create new versions with updated calculations. Python scripts get minor updates, JavaScript works as-is.

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Discovery Process](#discovery-process)
3. [Solution Architecture](#solution-architecture)
4. [Migration Plan](#migration-plan)
5. [Testing Plan](#testing-plan)
6. [Rollback Procedures](#rollback-procedures)

---

## Problem Statement

### Current Behavior (Broken for Non-PST Users)

**Database View:**
```sql
-- Current definition
timestamp AT TIME ZONE 'America/Los_Angeles' AS pst_time
-- Returns: timestamp without time zone (PST-only, no timezone info)
```

**What user sees:**
- PST user (California): **CORRECT** - Times match local clock
- EST user (New York): **WRONG** - Shows PST times (3 hours behind)
- UTC user (London): **WRONG** - Shows PST times (8 hours behind)
- JST user (Tokyo): **WRONG** - Shows PST times (17 hours behind)

### Why This Happened

**Historical Investigation Results:**
- PST was hardcoded in **initial commit** (Dec 19, 2025)
- No architectural discussion found in memory system
- System predates memory capture (designed Dec 13-19, before memory was mature)
- Original design assumption: Single-seat, single-timezone (PST) use
- Not a deliberate decision, just a convenience default

**Conclusion:** No architectural reasoning to preserve. We have freedom to fix this properly.

---

## Discovery Process

### Affected Views (7 Total)

All views using `AT TIME ZONE 'America/Los_Angeles'`:

1. **v_snapshot_quality** - Quality metrics dashboard
   - Column: `pst_time`
   - Used by: Python skills, dashboards

2. **v_agent_evolution** - Agent configuration history
   - Columns: `pst_created`, `last_used_pst`
   - Used by: Analytics dashboard

3. **v_agent_work_full** - Agent execution details
   - Columns: `pst_start`, `pst_end`, `parent_pst_time`
   - Used by: Agent analytics

4. **v_all_decisions** - Architectural decisions timeline
   - Column: `pst_time`
   - Used by: Decisions dashboard

5. **v_bug_patterns** - Bug analysis
   - Column: `pst_time`
   - Used by: Bug analytics dashboard

6. **v_file_heatmap** - File activity tracking
   - Columns: `first_mentioned`, `last_mentioned`
   - Used by: Files dashboard

7. **v_messages_flat** - Message search
   - Column: `pst_time`
   - Used by: v_assistant_messages (derived view)

### Base Tables (Correct - No Changes Needed)

✅ `context_snapshots.timestamp` - **TIMESTAMPTZ** (stores UTC correctly)
✅ `agent_work.timestamp_start` - **TIMESTAMPTZ**
✅ `agent_work.timestamp_end` - **TIMESTAMPTZ**
✅ All skills tables - **TIMESTAMPTZ**

**The database correctly stores UTC. Only views are broken.**

---

## Solution Architecture

### Design Decision: Simple Field Swap

**Instead of adding new fields, we update the calculation behind existing field names.**

**Before:**
```sql
timestamp AT TIME ZONE 'America/Los_Angeles' AS pst_time
-- Returns: timestamp without time zone
-- Type: naive timestamp (no timezone info)
-- User sees: PST time only
```

**After:**
```sql
timestamp AS pst_time
-- Returns: timestamp with time zone (timestamptz)
-- Type: timezone-aware UTC timestamp
-- User sees: Automatically converted to local time
```

**Why keep the name `pst_time`?**
- Backwards compatible (Python/JS code unchanged except for timezone handling)
- No breaking changes to API contracts
- Field name is just a label - what matters is the data type
- Gradual migration path

### How Automatic Conversion Works

#### JavaScript (Dashboards) - NO CODE CHANGES NEEDED

```javascript
// Current code:
new Date(pst_time)

// Before fix: pst_time = "2025-12-28 18:30:00" (naive, assumes local)
//   PST browser: Shows 6:30 PM (correct)
//   EST browser: Shows 6:30 PM (WRONG - should be 9:30 PM)

// After fix: pst_time = "2025-12-28T18:30:00+00:00" (UTC with timezone)
//   PST browser: Shows 10:30 AM (correct - auto-converted from UTC)
//   EST browser: Shows 1:30 PM (correct - auto-converted from UTC)
//   JST browser: Shows 3:30 AM Dec 29 (correct - auto-converted from UTC)
```

**The `Date` object automatically converts UTC to browser's local timezone!**

#### Python Scripts - MINOR CHANGES NEEDED

```python
# Before:
snap_date = datetime.fromisoformat(snap['timestamp']).strftime('%Y-%m-%d')
# Problem: No timezone conversion, shows UTC time

# After:
snap_date = datetime.fromisoformat(snap['timestamp']).astimezone().strftime('%Y-%m-%d')
#                                                      ^^^^^^^^^^^^
#                                                      Auto-converts UTC → system timezone
```

**The `.astimezone()` method (no argument) converts to system local timezone!**

### Golden Rule Still Applies

**Store UTC → Transport UTC → Display Local**

- ✅ Store: PostgreSQL TIMESTAMPTZ (UTC) - Already correct
- ✅ Transport: Views return TIMESTAMPTZ (UTC) - What we're fixing
- ✅ Display: JavaScript/Python convert to local - Auto-magic!

---

## Migration Plan

### Phase 1: Database Schema Updates

#### Step 1.1: Create Migration Script

**File:** `schema/migrations/20251228-timezone-handling.sql`

**Migration approach:** Rename existing views as backups, create new versions.

**Why rename instead of DROP?**
- Old view preserved as backup
- Can test new view alongside old one
- Instant rollback (just rename back)
- Zero data loss risk

**Example for v_snapshot_quality:**

```sql
BEGIN;

-- Backup existing view
ALTER VIEW v_snapshot_quality
RENAME TO v_snapshot_quality_backup_20251228;

-- Create new version with timezone-aware timestamps
CREATE VIEW v_snapshot_quality AS
SELECT
    id,
    project_path,
    timestamp AS pst_time,  -- Changed: was "timestamp AT TIME ZONE 'America/Los_Angeles'"
    session_id,
    trigger_event,
    jsonb_array_length(raw_context->'messages') AS message_count,
    CASE WHEN summary IS NOT NULL AND length(summary) > 50 THEN 1 ELSE 0 END AS has_summary,
    CASE WHEN embedding IS NOT NULL THEN 1 ELSE 0 END AS has_embedding,
    CASE WHEN tags IS NOT NULL AND array_length(tags, 1) > 0 THEN 1 ELSE 0 END AS has_tags,
    CASE WHEN mentioned_files IS NOT NULL AND array_length(mentioned_files, 1) > 0 THEN 1 ELSE 0 END AS has_files,
    CASE WHEN key_decisions IS NOT NULL AND array_length(key_decisions, 1) > 0 THEN 1 ELSE 0 END AS has_decisions,
    CASE WHEN bugs_fixed IS NOT NULL AND array_length(bugs_fixed, 1) > 0 THEN 1 ELSE 0 END AS has_bugs,
    CASE WHEN git_commit_hash IS NOT NULL THEN 1 ELSE 0 END AS has_git_hash,
    CASE WHEN session_id IS NOT NULL THEN 1 ELSE 0 END AS has_session_id,
    COALESCE(array_length(tags, 1), 0) AS tag_count,
    COALESCE(array_length(mentioned_files, 1), 0) AS file_count,
    COALESCE(array_length(key_decisions, 1), 0) AS decision_count,
    COALESCE(array_length(bugs_fixed, 1), 0) AS bug_count,
    (
        CASE WHEN summary IS NOT NULL AND length(summary) > 50 THEN 1 ELSE 0 END +
        CASE WHEN embedding IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN tags IS NOT NULL AND array_length(tags, 1) > 0 THEN 1 ELSE 0 END +
        CASE WHEN mentioned_files IS NOT NULL AND array_length(mentioned_files, 1) > 0 THEN 1 ELSE 0 END +
        CASE WHEN key_decisions IS NOT NULL AND array_length(key_decisions, 1) > 0 THEN 1 ELSE 0 END +
        CASE WHEN bugs_fixed IS NOT NULL AND array_length(bugs_fixed, 1) > 0 THEN 1 ELSE 0 END +
        CASE WHEN git_commit_hash IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN session_id IS NOT NULL THEN 1 ELSE 0 END
    ) AS quality_score,
    length(summary) AS summary_length
FROM context_snapshots;

COMMIT;
```

**Apply to all 7 views with similar changes.**

#### Step 1.2: Update schema/init.sql

**File:** `schema/init.sql`

Update view definitions for future deployments:

```sql
-- Find all instances of:
timestamp AT TIME ZONE 'America/Los_Angeles'

-- Replace with:
timestamp

-- For all 7 views listed above
```

**This ensures new deployments have correct timezone handling from the start.**

#### Step 1.3: Apply Migration to Running Container

**Cannot re-run init.sql on existing database**, so we apply migration script:

```bash
# Apply migration
docker exec -i claude-context-db psql -U memory_admin -d claude_memory \
  < schema/migrations/20251228-timezone-handling.sql

# Verify new view structure
docker exec claude-context-db psql -U memory_admin -d claude_memory \
  -c "\d+ v_snapshot_quality"

# Expected output:
# pst_time | timestamp with time zone  (was: timestamp without time zone)
```

### Phase 2: Python Script Updates

#### Files Requiring Updates (4 files total)

**CRITICAL: User-facing Python Scripts**

| File | Lines | Affected Fields | Changes | Priority |
|------|-------|----------------|---------|----------|
| **get-up-to-speed.py** | 375 | `timestamp` from v_snapshot_quality | 1 line | **HIGH** |
| **skills-stats.py** | 269-270, 336, 443 | `last_used`, `last_used_pst` | 4 lines | **HIGH** |
| **monitor-capture-progress.py** | 153 | `datetime.now()` | 1 line | **MEDIUM** |
| **list-skills.py** | 262-263 | `created_at`, `last_used` | 2 lines (optional) | **LOW** |

**Total: ~7-10 lines of code across 4 files**

#### Detailed Changes

**1. get-up-to-speed.py (1 change)**

```python
# Line 375:
# Before:
snap_date = datetime.fromisoformat(snap['timestamp']).strftime('%Y-%m-%d')

# After:
snap_date = datetime.fromisoformat(snap['timestamp']).astimezone().strftime('%Y-%m-%d')
```

**2. skills-stats.py (4 changes)**

```python
# Lines 269-270:
# Before:
days_ago = (datetime.now(last_used.tzinfo) - last_used).days
print(f"  Last Used: {last_used.strftime('%Y-%m-%d %H:%M')} ({days_ago} days ago)")

# After:
last_used_local = last_used.astimezone()
days_ago = (datetime.now(last_used_local.tzinfo) - last_used_local).days
print(f"  Last Used: {last_used_local.strftime('%Y-%m-%d %H:%M')} ({days_ago} days ago)")

# Lines 336 and 443:
# Before:
last_used_str = last_used.strftime('%Y-%m-%d') if last_used else 'Never'

# After:
last_used_str = last_used.astimezone().strftime('%Y-%m-%d') if last_used else 'Never'
```

**3. monitor-capture-progress.py (1 change)**

```python
# Line 153:
# Before:
timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# After:
timestamp_str = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
```

**4. list-skills.py (Optional - 2 changes for better readability)**

```python
# Lines 262-263:
# Before:
print(f"  Created: {skill['created_at']}")
print(f"  Last Used: {skill['last_used'] or 'Never'}")

# After (optional):
from datetime import datetime
created_str = datetime.fromisoformat(skill['created_at']).astimezone().strftime('%Y-%m-%d %H:%M') if skill['created_at'] else 'Unknown'
last_used_str = datetime.fromisoformat(skill['last_used']).astimezone().strftime('%Y-%m-%d %H:%M') if skill['last_used'] else 'Never'
print(f"  Created: {created_str}")
print(f"  Last Used: {last_used_str}")
```

**Key pattern:** Add `.astimezone()` between parsing and formatting.

**Note:** Other Python files (32+ scripts) don't need updates because they:
- Store timestamps only (no formatting)
- Output JSON/ISO format (already timezone-aware)
- Don't interact with the affected views

### Phase 3: JavaScript/Dashboard Updates

#### Required Changes: NONE!

The browser `Date` object automatically handles timezone conversion:

```javascript
// This code already works correctly:
new Date(pst_time)
// When pst_time is timestamptz, browser auto-converts to local timezone
```

**Dashboards work as-is after view updates!**

---

### Phase 4: MCP Server Updates (Custom Commands)

#### Critical Finding: MCP Tools Use Affected Views

**File:** `mcp-server/src/server.js`

**Affected MCP Tools (/ commands):**

| Tool | Lines | Views Used | Fields Used | Auto-Fixed? |
|------|-------|-----------|-------------|-------------|
| **search_exact_phrase** | 696-697 | v_assistant_messages | `pst_time` | ✅ YES |
| **get_quality_report** | 727-730 | v_snapshot_quality | `pst_time` | ✅ YES |
| **search_decisions** | 799-800 | v_all_decisions | `pst_time` | ✅ YES |
| **analyze_bugs** | 830-831 | v_bug_patterns | `pst_time` | ✅ YES |
| **get_timeline** | 980-981 | context_snapshots (table) | `timestamp` | ✅ YES |
| **get_file_activity** | 1073 | v_file_heatmap | `last_mentioned` | ✅ YES |
| **get_agent_analytics** | 1092 | agent_work (table) | `timestamp_start` | ✅ YES |

**Timestamp Formatting (Lines using `toLocaleString()`):**
- Line 286: `new Date(snapshot.timestamp).toLocaleString()`
- Line 407: `new Date(snapshot.timestamp).toLocaleString()`
- Line 924: `new Date(r.pst_time).toLocaleString()` ← **Will auto-fix with view change**
- Line 980-981: Timeline timestamps
- Line 1019: `new Date(r.pst_time).toLocaleString()` ← **Will auto-fix with view change**
- Line 1045: `new Date(b.pst_time).toLocaleString()` ← **Will auto-fix with view change**
- Line 1073: File activity timestamps
- Line 1092: Agent work timestamps

#### Why MCP Tools Don't Need Code Changes

**JavaScript's `new Date()` automatically converts timestamptz to local timezone!**

```javascript
// Current code (works correctly after view fix):
new Date(r.pst_time).toLocaleString()

// Before view fix: pst_time = "2025-12-28 18:30:00" (naive timestamp)
//   Node.js in PST container: Shows 6:30 PM PST (correct)
//   User in EST: Sees PST time (WRONG - 3 hours off)

// After view fix: pst_time = "2025-12-28T18:30:00+00:00" (UTC timestamptz)
//   Node.js in PST container: Shows 10:30 AM PST (correct - auto-converted)
//   User in EST: Sees 1:30 PM EST (correct - auto-converted)
```

**Verdict:** ✅ **NO MCP server code changes needed!** Just fix the views.

#### MCP Tools Impact Summary

- **7 MCP tools** use the affected views
- **All 7 tools** will automatically show correct local times after view migration
- **Zero code changes** required in mcp-server/src/server.js
- **Testing required:** Verify each tool shows local time correctly

---

## Testing Plan

### Test Environment Setup

**1. Verify current behavior (PST hardcoding):**
```bash
docker exec claude-context-db psql -U memory_admin -d claude_memory -c "
SELECT
    id,
    pst_time,
    pg_typeof(pst_time) as type
FROM v_snapshot_quality
LIMIT 1;
"
# Expected: timestamp without time zone
```

**2. Apply migration to test view:**
```bash
# Test with just v_snapshot_quality first
docker exec -i claude-context-db psql -U memory_admin -d claude_memory << 'EOF'
BEGIN;
ALTER VIEW v_snapshot_quality RENAME TO v_snapshot_quality_backup_20251228;
-- (create new view as shown above)
COMMIT;
EOF
```

**3. Verify new behavior:**
```bash
docker exec claude-context-db psql -U memory_admin -d claude_memory -c "
SELECT
    id,
    pst_time,
    pg_typeof(pst_time) as type,
    pst_time AT TIME ZONE 'America/Los_Angeles' as pst_display,
    pst_time AT TIME ZONE 'America/New_York' as est_display,
    pst_time AT TIME ZONE 'UTC' as utc_display
FROM v_snapshot_quality
LIMIT 1;
"
# Expected: All times should be the same UTC moment, displayed in different timezones
```

### Test Cases

**1. Database Layer:**
- [ ] View returns `timestamp with time zone`
- [ ] UTC value matches base table `timestamp` column
- [ ] Can convert to any timezone with `AT TIME ZONE`

**2. Python Scripts (4 files):**
- [ ] `get-up-to-speed.py` shows local time
- [ ] `skills-stats.py` shows local time for last_used
- [ ] `monitor-capture-progress.py` shows local time
- [ ] `list-skills.py` shows local time (optional)
- [ ] Relative time calculations work ("2 hours ago")
- [ ] Date formatting displays correctly

**3. Web Dashboards:**
- [ ] Basic dashboard shows browser local time
- [ ] Analytics dashboard tabs show local time
- [ ] Terminal monitor shows system local time

**4. MCP Tools (7 custom commands):**
- [ ] `/mem-search` (search_exact_phrase) - Shows local time
- [ ] `/mem-quality` (get_quality_report) - Shows local time
- [ ] `/mem-decisions` (search_decisions) - Shows local time
- [ ] `/mem-bugs` (analyze_bugs) - Shows local time
- [ ] `/mem-timeline` (get_timeline) - Shows local time
- [ ] `/mem-files` (get_file_activity) - Shows local time
- [ ] `/mem-agents` (get_agent_analytics) - Shows local time

**5. Cross-Timezone Testing:**
- [ ] Set system timezone to EST: `sudo ln -sf /usr/share/zoneinfo/America/New_York /etc/localtime`
- [ ] Verify Python scripts show EST times
- [ ] Set browser timezone (dev tools) to JST
- [ ] Verify dashboard shows JST times
- [ ] Test MCP tools in different timezone contexts

### Success Criteria

- ✅ Database views return `timestamptz` (not naive timestamp)
- ✅ JavaScript shows browser local time (no code changes)
- ✅ Python shows system local time (with `.astimezone()`)
- ✅ All times represent the same UTC moment
- ✅ No errors in dashboards or scripts
- ✅ Backup views exist for rollback

---

## Rollback Procedures

### Immediate Rollback (If Issues Found During Testing)

**Rollback is instant - just rename views back:**

```sql
BEGIN;

-- Drop new view
DROP VIEW v_snapshot_quality;

-- Restore backup
ALTER VIEW v_snapshot_quality_backup_20251228
RENAME TO v_snapshot_quality;

COMMIT;
```

**Repeat for any views that were migrated.**

### Full Rollback Script

**File:** `schema/migrations/20251228-timezone-handling-rollback.sql`

```sql
BEGIN;

-- Rollback all 7 views
DROP VIEW IF EXISTS v_snapshot_quality;
ALTER VIEW IF EXISTS v_snapshot_quality_backup_20251228
  RENAME TO v_snapshot_quality;

DROP VIEW IF EXISTS v_agent_evolution;
ALTER VIEW IF EXISTS v_agent_evolution_backup_20251228
  RENAME TO v_agent_evolution;

DROP VIEW IF EXISTS v_agent_work_full;
ALTER VIEW IF EXISTS v_agent_work_full_backup_20251228
  RENAME TO v_agent_work_full;

DROP VIEW IF EXISTS v_all_decisions;
ALTER VIEW IF EXISTS v_all_decisions_backup_20251228
  RENAME TO v_all_decisions;

DROP VIEW IF EXISTS v_bug_patterns;
ALTER VIEW IF EXISTS v_bug_patterns_backup_20251228
  RENAME TO v_bug_patterns;

DROP VIEW IF EXISTS v_file_heatmap;
ALTER VIEW IF EXISTS v_file_heatmap_backup_20251228
  RENAME TO v_file_heatmap;

DROP VIEW IF EXISTS v_messages_flat;
ALTER VIEW IF EXISTS v_messages_flat_backup_20251228
  RENAME TO v_messages_flat;

COMMIT;
```

### Git Rollback

```bash
# If schema/init.sql was updated, revert:
git checkout HEAD -- schema/init.sql

# If Python scripts were updated, revert:
git checkout HEAD -- get-up-to-speed.py monitor-capture-progress.py
```

---

## Implementation Checklist

### Phase 1: Database Schema (Container-level testing)

- [ ] Create `schema/migrations/20251228-timezone-handling.sql`
- [ ] Test migration on v_snapshot_quality ONLY first
- [ ] Verify view returns `timestamptz`
- [ ] Test web dashboard still works
- [ ] Test Python script (get-up-to-speed.py) still works
- [ ] Test MCP tool (/mem-quality) still works
- [ ] If successful, migrate remaining 6 views
- [ ] Update `schema/init.sql` for future deployments
- [ ] Verify all 7 views return `timestamptz`

### Phase 2: Python Scripts (4 files, ~7-10 lines)

- [ ] Update `get-up-to-speed.py` (line 375) with `.astimezone()`
- [ ] Update `skills-stats.py` (lines 269-270, 336, 443) with `.astimezone()`
- [ ] Update `monitor-capture-progress.py` (line 153) with `.astimezone()`
- [ ] Update `list-skills.py` (lines 262-263) - Optional
- [ ] Test each script shows local time
- [ ] Verify relative time calculations work

### Phase 3: JavaScript/Dashboard Verification

- [ ] Test basic dashboard in browser (PST timezone)
- [ ] Test analytics dashboard (7 tabs)
- [ ] Test dashboard in browser with EST timezone (dev tools)
- [ ] Verify no code changes needed (auto-converts)

### Phase 4: MCP Tools Verification (7 tools)

- [ ] Test `/mem-search` (search_exact_phrase) shows local time
- [ ] Test `/mem-quality` (get_quality_report) shows local time
- [ ] Test `/mem-decisions` (search_decisions) shows local time
- [ ] Test `/mem-bugs` (analyze_bugs) shows local time
- [ ] Test `/mem-timeline` (get_timeline) shows local time
- [ ] Test `/mem-files` (get_file_activity) shows local time
- [ ] Test `/mem-agents` (get_agent_analytics) shows local time
- [ ] Verify no MCP server code changes needed

### Phase 5: Comprehensive Testing

- [ ] Test all Python scripts on PST system
- [ ] Test all Python scripts on EST system (if possible)
- [ ] Verify no errors in logs (processor, database, MCP)
- [ ] Check database query performance (should be identical)
- [ ] Test edge cases (null timestamps, missing data)

### Phase 6: Cleanup (After 7 days of stable operation)

- [ ] Drop backup views:
  ```sql
  DROP VIEW v_snapshot_quality_backup_20251228;
  -- (repeat for all 7)
  ```
- [ ] Document migration in project archive
- [ ] Update DASHBOARDS.md if needed
- [ ] Update this plan with actual results

---

## Migration Scope Options

We identified 7 views with PST hardcoding. User needs to decide scope:

### Option A: Minimal (1 view)
- Migrate: `v_snapshot_quality` only
- Why: Used by Python skills, most critical
- Timeline: 1 day testing
- Risk: Lowest

### Option B: Dashboard Complete (5 views)
- Migrate: v_snapshot_quality, v_bug_patterns, v_all_decisions, v_file_heatmap, v_agent_work_full
- Why: Makes dashboards fully timezone-aware
- Timeline: 2-3 days testing
- Risk: Medium

### Option C: Comprehensive (7 views)
- Migrate: All 7 views
- Why: Complete timezone awareness
- Timeline: 3-5 days testing
- Risk: Highest (more surface area)

**Current recommendation: Option C (Comprehensive)** - Fix it once, fix it right.

---

## Notes

### Why This Solution is Simpler Than Originally Planned

**Original plan complexity:**
- Dual fields (`timestamp` + `pst_time`)
- Display layer formatters
- Complex migration with backward compatibility

**Actual solution simplicity:**
- Single field (`pst_time` with different type)
- Automatic conversion by JavaScript/Python
- Simple view rename + recreate
- Minor Python changes (`.astimezone()`)

**Key insight:** Modern languages auto-handle timezone conversion when given proper timezone-aware data!

### PostgreSQL Timezone Behavior

```sql
-- Original (broken):
timestamp AT TIME ZONE 'America/Los_Angeles'
-- Returns: timestamp without time zone
-- Value: "2025-12-28 10:30:00" (naive, no timezone info)

-- Fixed:
timestamp
-- Returns: timestamp with time zone
-- Value: "2025-12-28 18:30:00+00:00" (UTC with timezone info)
```

**The `AT TIME ZONE` operator strips timezone information!** That's the bug.

### Display Format Standards

**Already implemented correctly in dashboards:**
- Relative times: "2 minutes ago", "3 hours ago"
- ISO date format: `YYYY-MM-DD HH:MM`
- No seconds (cleaner)
- No explicit timezone indicator (implied local for per-seat installation)

**No changes needed - just fix the data type!**

---

---

## Summary: Impact Assessment

### Components Affected

| Component | Files/Objects | Changes Needed | Auto-Fixed? |
|-----------|--------------|----------------|-------------|
| **Database Views** | 7 views | Rename + recreate | ⚙️ MANUAL |
| **Python Scripts** | 4 files (~7-10 lines) | Add `.astimezone()` | ⚙️ MANUAL |
| **Web Dashboards** | 2 HTML files | None | ✅ AUTO |
| **MCP Tools** | 7 custom commands | None | ✅ AUTO |
| **JavaScript (general)** | All JS code | None | ✅ AUTO |

### Effort Estimate

**Database Migration:**
- Create migration script: 30 minutes
- Test v_snapshot_quality: 15 minutes
- Migrate remaining 6 views: 30 minutes
- Update schema/init.sql: 15 minutes
- **Total: ~1.5 hours**

**Python Updates:**
- 4 files, 7-10 lines total
- Mechanical changes (add `.astimezone()`)
- **Total: ~30 minutes**

**Testing:**
- Database layer: 30 minutes
- Python scripts: 30 minutes
- Dashboards: 15 minutes
- MCP tools: 30 minutes
- Cross-timezone: 30 minutes
- **Total: ~2 hours**

**Grand Total: ~4 hours** (plus 7 days observation period)

### Risk Assessment

**Low Risk Migration:**
- ✅ Views don't store data (just queries)
- ✅ Backup views preserved (instant rollback)
- ✅ Base tables unchanged (zero data migration)
- ✅ Small code surface area (4 files)
- ✅ Automatic conversion handles most cases
- ✅ Incremental testing (one view first)

**Highest Risk Areas:**
1. Python datetime calculations (timezone math)
2. MCP tools with complex formatting
3. Edge cases with null timestamps

**Mitigation:**
- Test with v_snapshot_quality first
- Keep backup views for 7 days
- Comprehensive testing plan
- Rollback script ready

---

**Last Updated:** 2025-12-28
**Next Review:** After Phase 1 testing
**Status:** Ready for implementation (Option C - Comprehensive)
**Owner:** James + Claude Sonnet 4.5
