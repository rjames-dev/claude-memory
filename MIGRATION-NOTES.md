# Migration Notes - Fixing First-Time Installation Issues

**Date:** 2025-12-22
**Commit:** TBD
**Affects:** All installations (especially first-time setups)

## Issues Fixed

### Issue 1: Missing Python `requests` Dependency

**Problem:**
- Hook script `hooks/auto-capture-precompact.py` imports `requests` (line 14)
- No `requirements.txt` file existed for hooks
- First-time users got `ModuleNotFoundError: No module named 'requests'`

**Fix:**
- ✅ Created `requirements.txt` at project root
- ✅ Updated `hooks/README.md` with Prerequisites section
- ✅ Updated main `README.md` Prerequisites and Quick Start
- ✅ Added Step 5: Install Python Dependencies

**For Existing Users:**
```bash
cd /path/to/claude-memory
pip3 install -r requirements.txt
```

---

### Issue 2: Missing `transcript_path` Database Column

**Problem:**
- `schema/init.sql` line 50 created index on `transcript_path`
- BUT: Column was never defined in `CREATE TABLE context_snapshots`
- Code tried to INSERT into non-existent column → database error
- Migration script `schema/add-transcript-path-column.sql` existed but was never applied automatically

**Root Cause:**
- Schema inconsistency in `init.sql`
- Migration scripts not auto-applied during `docker-compose up`

**Fix:**
- ✅ Added `transcript_path TEXT` column to `schema/init.sql` (line 41)
- ✅ Column now defined BEFORE the index is created
- ✅ New installations will have column from the start

**For Existing Installations:**

Your database already has the column (you manually added it during debugging). No action needed!

**For Users Who Haven't Run First Capture Yet:**

If you see a database error about `transcript_path`, run the migration script:

```bash
docker exec claude-context-db psql -U memory_admin -d claude_memory -f /app/schema/add-transcript-path-column.sql
```

Or apply it manually:
```bash
docker exec claude-context-db psql -U memory_admin -d claude_memory -c "ALTER TABLE context_snapshots ADD COLUMN IF NOT EXISTS transcript_path TEXT;"
```

---

## Summary of Changes

### Files Modified:
1. **requirements.txt** (NEW)
   - Added Python dependencies for hooks

2. **schema/init.sql**
   - Added `transcript_path TEXT` column definition (line 41)
   - Fixes schema inconsistency

3. **README.md**
   - Added Python 3 to Prerequisites
   - Added Step 5: Install Python Dependencies
   - Updated checklist to include pip install
   - Renumbered subsequent steps (Step 5 → Step 6, etc.)

4. **hooks/README.md**
   - Added Prerequisites section with pip install instructions

### Files Not Changed (but relevant):
- `schema/add-transcript-path-column.sql` - Migration script still exists for reference
- `hooks/auto-capture-precompact.py` - No changes (still imports requests)

---

## Testing Recommendations

### For Fresh Installations:
1. Clone repo
2. Follow updated Quick Start guide
3. Verify no `ModuleNotFoundError` when hooks run
4. Verify no database errors during first capture

### For Existing Installations:
1. Pull latest changes
2. Run `pip3 install -r requirements.txt`
3. Database column already exists (you fixed it manually)
4. Test capture to confirm everything works

---

## Future Improvements (Optional)

### Automatic Migration Application
Currently, migration scripts in `schema/` are not automatically applied. Consider:
1. Adding all migration scripts to `docker-entrypoint-initdb.d/` (only runs on first init)
2. Creating a migration runner script that checks and applies pending migrations
3. Using a proper migration tool (e.g., Flyway, Liquibase, or node-pg-migrate)

### Hook Dependency Management
Consider:
1. Using only Python standard library (urllib instead of requests) - zero dependencies
2. Adding dependency check to `setup-hooks.sh` script
3. Creating a virtual environment for hooks

---

## Commit Message (Suggested)

```
Fix: Critical first-time installation issues (missing deps + schema bug)

Two critical bugs affecting first-time installations:

1. Missing Python dependency:
   - hooks/auto-capture-precompact.py imports 'requests'
   - No requirements.txt existed
   - Added requirements.txt and updated documentation

2. Schema inconsistency in init.sql:
   - Created index on transcript_path column that didn't exist
   - Added transcript_path TEXT column to table definition
   - Migration script existed but wasn't auto-applied

Changes:
- Add requirements.txt with requests>=2.31.0
- Fix schema/init.sql to define transcript_path column
- Update README.md: Add Python 3 prereq + pip install step
- Update hooks/README.md: Add Prerequisites section

Existing users: Run `pip3 install -r requirements.txt`
Database column fix already applied manually during debugging.

Discovered by: First-time install on M2 Max (jamesheidinger)
```

---

**Thank you for the thorough bug report! These fixes will save future users significant frustration.**
