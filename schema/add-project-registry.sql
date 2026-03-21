-- ============================================================================
-- Claude Memory - Project Registry Migration
-- Maps project_path entries to Obsidian vault folders
-- Created: 2026-03-21
-- ============================================================================
--
-- Background:
-- The promote-to-obsidian workflow needs to know which Obsidian folder
-- corresponds to each captured project. This table is the single source
-- of truth for that mapping.
--
-- vault_root is derived from CLAUDE_WORKSPACE_ROOT env var + "/vault"
-- and is therefore NOT stored here — it's a convention, not config.
--
-- obsidian_folder is the subfolder name under Projects/ in the vault.
-- NULL = not yet affiliated; promote-to-obsidian will auto-create on
-- first promotion and populate this column.
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'project_registry'
    ) THEN

        CREATE TABLE project_registry (
            -- The captured project path (matches context_snapshots.project_path)
            project_path     TEXT PRIMARY KEY,

            -- Obsidian Projects/ subfolder name for this project
            -- NULL until first promote-to-obsidian run (auto-populated then)
            obsidian_folder  TEXT,

            -- Human-readable display name (defaults to last path segment)
            display_name     TEXT,

            -- Whether this project is actively being worked on
            active           BOOLEAN DEFAULT TRUE,

            -- When this project was first captured
            created_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

            -- When obsidian_folder was last confirmed/updated
            obsidian_linked_at TIMESTAMP WITH TIME ZONE
        );

        RAISE NOTICE '✅ Created project_registry table';

    ELSE
        RAISE NOTICE 'ℹ️  project_registry table already exists - skipping create';
    END IF;
END $$;


-- ============================================================================
-- INDEXES
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'project_registry'
          AND indexname = 'idx_project_registry_active'
    ) THEN
        CREATE INDEX idx_project_registry_active
            ON project_registry(active)
            WHERE active = TRUE;
        RAISE NOTICE '✅ Created idx_project_registry_active';
    ELSE
        RAISE NOTICE 'ℹ️  idx_project_registry_active already exists';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'project_registry'
          AND indexname = 'idx_project_registry_obsidian_folder'
    ) THEN
        CREATE INDEX idx_project_registry_obsidian_folder
            ON project_registry(obsidian_folder)
            WHERE obsidian_folder IS NOT NULL;
        RAISE NOTICE '✅ Created idx_project_registry_obsidian_folder';
    ELSE
        RAISE NOTICE 'ℹ️  idx_project_registry_obsidian_folder already exists';
    END IF;
END $$;


-- ============================================================================
-- COLUMN COMMENTS
-- ============================================================================

COMMENT ON TABLE project_registry IS
'Maps project_path values from context_snapshots to their corresponding
Obsidian vault folder under Projects/. vault_root is a convention
($CLAUDE_WORKSPACE_ROOT/vault) and is not stored here.';

COMMENT ON COLUMN project_registry.project_path IS
'Absolute path to the project root. Matches context_snapshots.project_path.
Example: /Users/jamesheidinger/code/claude-memory';

COMMENT ON COLUMN project_registry.obsidian_folder IS
'Subfolder name under Projects/ in the Obsidian vault.
Example: "Claude Memory + Obsidian Integration"
NULL = not yet linked. promote-to-obsidian auto-creates and populates on first run.';

COMMENT ON COLUMN project_registry.display_name IS
'Human-readable project name. Defaults to last segment of project_path
if not explicitly set. Used in Obsidian note headings and frontmatter.';

COMMENT ON COLUMN project_registry.obsidian_linked_at IS
'Timestamp of when obsidian_folder was last confirmed or set.
Used to detect stale links if vault structure changes.';


-- ============================================================================
-- AUTO-POPULATE: register any projects already in context_snapshots
-- ============================================================================

INSERT INTO project_registry (project_path, display_name, created_at)
SELECT
    project_path,
    -- Default display_name: last segment of path, hyphens replaced with spaces
    REGEXP_REPLACE(
        SPLIT_PART(project_path, '/', ARRAY_LENGTH(STRING_TO_ARRAY(project_path, '/'), 1)),
        '-', ' ', 'g'
    ) AS display_name,
    MIN(timestamp) AS created_at
FROM context_snapshots
WHERE project_path IS NOT NULL
GROUP BY project_path
ON CONFLICT (project_path) DO NOTHING;

DO $$
DECLARE
    row_count INTEGER;
BEGIN
    GET DIAGNOSTICS row_count = ROW_COUNT;
    IF row_count > 0 THEN
        RAISE NOTICE '✅ Auto-registered % existing project(s) from context_snapshots', row_count;
    ELSE
        RAISE NOTICE 'ℹ️  No new projects to auto-register (all already present)';
    END IF;
END $$;


-- ============================================================================
-- VIEW: project overview with snapshot counts
-- ============================================================================

CREATE OR REPLACE VIEW v_project_registry AS
SELECT
    pr.project_path,
    pr.display_name,
    pr.obsidian_folder,
    pr.active,
    pr.created_at,
    pr.obsidian_linked_at,
    COUNT(cs.id)                              AS snapshot_count,
    MAX(cs.timestamp)                         AS last_captured_at,
    CASE
        WHEN pr.obsidian_folder IS NOT NULL THEN 'linked'
        ELSE 'unaffiliated'
    END                                       AS obsidian_status
FROM project_registry pr
LEFT JOIN context_snapshots cs ON cs.project_path = pr.project_path
GROUP BY pr.project_path, pr.display_name, pr.obsidian_folder,
         pr.active, pr.created_at, pr.obsidian_linked_at
ORDER BY last_captured_at DESC NULLS LAST;

COMMENT ON VIEW v_project_registry IS
'Project overview joining registry with snapshot counts.
obsidian_status: "linked" = has Obsidian folder, "unaffiliated" = not yet promoted.';


-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Project Registry Migration Complete';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Tables Created: 1';
    RAISE NOTICE '  - project_registry';
    RAISE NOTICE '';
    RAISE NOTICE 'Views Created: 1';
    RAISE NOTICE '  - v_project_registry';
    RAISE NOTICE '';
    RAISE NOTICE 'Indexes Created: 2';
    RAISE NOTICE '  - idx_project_registry_active';
    RAISE NOTICE '  - idx_project_registry_obsidian_folder';
    RAISE NOTICE '';
    RAISE NOTICE 'Existing projects auto-registered from context_snapshots';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Next Steps:';
    RAISE NOTICE '  1. Run: psql -f schema/add-project-registry.sql';
    RAISE NOTICE '  2. Set obsidian_folder for each project (or let';
    RAISE NOTICE '     promote-to-obsidian auto-create on first run)';
    RAISE NOTICE '  3. Run promote-to-obsidian.py <snapshot_id>';
    RAISE NOTICE '========================================';
END $$;
