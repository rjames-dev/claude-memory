/**
 * Claude Context Processor - Main Server
 * Handles context capture requests and processes them out-of-band
 */

require('dotenv').config();
const express = require('express');
const path = require('path');
const capture = require('./capture');
const { generateEmbedding } = require('./embed');

const app = express();
const PORT = process.env.PORT || 3100;

// Middleware
app.use(express.json({ limit: '50mb' }));
app.use(express.static('public'));

// Dashboard route
app.get('/dashboard', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/dashboard.html'));
});

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    service: 'claude-context-processor',
    timestamp: new Date().toISOString()
  });
});

// Dashboard stats API
app.get('/api/stats', async (req, res) => {
  try {
    const { Pool } = require('pg');
    const pool = new Pool({
      connectionString: process.env.DATABASE_URL
    });

    // Get database stats
    const compactionsQuery = 'SELECT COUNT(*) as total FROM context_snapshots';
    const todayQuery = `SELECT COUNT(*) as today FROM context_snapshots WHERE timestamp >= CURRENT_DATE`;
    const weekQuery = `SELECT COUNT(*) as week FROM context_snapshots WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'`;
    const lastQuery = `SELECT timestamp FROM context_snapshots ORDER BY timestamp DESC LIMIT 1`;
    const sessionsQuery = `
      SELECT
        COUNT(DISTINCT session_id) FILTER (WHERE session_id IS NOT NULL) as total,
        COUNT(DISTINCT session_id) FILTER (WHERE session_id IS NOT NULL AND timestamp >= CURRENT_DATE) as today,
        COUNT(DISTINCT session_id) FILTER (WHERE session_id IS NOT NULL AND timestamp >= CURRENT_DATE - INTERVAL '7 days') as week
      FROM context_snapshots
    `;
    const avgCompactionsQuery = `
      SELECT ROUND(AVG(compaction_count)::numeric, 1) as avg_compactions_per_session
      FROM (
        SELECT session_id, MAX(compaction_index) as compaction_count
        FROM context_snapshots
        WHERE session_id IS NOT NULL
        GROUP BY session_id
      ) s
    `;

    const [compactions, today, week, last, sessions, avgCompactions] = await Promise.all([
      pool.query(compactionsQuery),
      pool.query(todayQuery),
      pool.query(weekQuery),
      pool.query(lastQuery),
      pool.query(sessionsQuery),
      pool.query(avgCompactionsQuery)
    ]);

    const lastCapture = last.rows[0]?.timestamp;
    const now = new Date();
    const lastCaptureAgo = lastCapture
      ? Math.floor((now - new Date(lastCapture)) / 1000)
      : null;

    await pool.end();

    res.json({
      database: {
        status: 'connected',
        snapshots: parseInt(compactions.rows[0].total)
      },
      ollama: {
        status: 'running',
        url: process.env.OLLAMA_URL,
        model: process.env.SUMMARY_MODEL || 'llama3.2:latest'
      },
      processor: {
        status: 'healthy',
        port: process.env.PORT || 3200,
        uptime: process.uptime()
      },
      captures: {
        total: parseInt(compactions.rows[0].total),
        today: parseInt(today.rows[0].today),
        week: parseInt(week.rows[0].week),
        lastCaptureSeconds: lastCaptureAgo
      },
      sessions: {
        tracked: parseInt(sessions.rows[0].total),
        today: parseInt(sessions.rows[0].today),
        week: parseInt(sessions.rows[0].week),
        avgCompactionsPerSession: parseFloat(avgCompactions.rows[0].avg_compactions_per_session) || 1.0
      }
    });

  } catch (error) {
    console.error('Stats API error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Recent captures API
app.get('/api/recent', async (req, res) => {
  try {
    const { Pool } = require('pg');
    const pool = new Pool({
      connectionString: process.env.DATABASE_URL
    });

    const limit = parseInt(req.query.limit) || 10;

    const query = `
      SELECT
        id,
        session_id,
        project_path,
        trigger_event,
        compaction_index,
        context_window_size - message_start_index AS delta_messages,
        context_window_size AS total_messages,
        message_start_index,
        timestamp,
        CASE
          WHEN compaction_index = 1 THEN 'FIRST'
          ELSE 'CONTINUATION'
        END as capture_type
      FROM context_snapshots
      ORDER BY timestamp DESC
      LIMIT $1
    `;

    const result = await pool.query(query, [limit]);
    await pool.end();

    res.json(result.rows);

  } catch (error) {
    console.error('Recent API error:', error);
    res.status(500).json({ error: error.message });
  }
});

// ============================================================================
// PHASE 1 ANALYTICAL API ENDPOINTS - Using Views
// ============================================================================

// Quality metrics API
app.get('/api/quality', async (req, res) => {
  try {
    const { Pool } = require('pg');
    const pool = new Pool({
      connectionString: process.env.DATABASE_URL
    });

    const query = `
      SELECT
        AVG(quality_score)::numeric(4,2) as avg_quality,
        COUNT(*) FILTER (WHERE quality_score >= 8) as high_quality,
        COUNT(*) FILTER (WHERE quality_score >= 5 AND quality_score < 8) as medium_quality,
        COUNT(*) FILTER (WHERE quality_score < 5) as low_quality,
        COUNT(*) as total,
        MAX(quality_score) as max_score,
        MIN(quality_score) as min_score
      FROM v_snapshot_quality
    `;

    const result = await pool.query(query);
    await pool.end();

    res.json(result.rows[0]);

  } catch (error) {
    console.error('Quality API error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Project stats API
app.get('/api/projects', async (req, res) => {
  try {
    const { Pool } = require('pg');
    const pool = new Pool({
      connectionString: process.env.DATABASE_URL
    });

    const query = `
      SELECT
        project_path,
        total_snapshots,
        tracked_sessions,
        total_messages,
        avg_messages_per_snapshot,
        most_common_tag,
        EXTRACT(EPOCH FROM time_since_last_activity) as last_activity_seconds
      FROM v_project_dashboard
      ORDER BY last_activity DESC
      LIMIT 10
    `;

    const result = await pool.query(query);
    await pool.end();

    res.json(result.rows);

  } catch (error) {
    console.error('Projects API error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Bug analysis API
app.get('/api/bugs', async (req, res) => {
  try {
    const { Pool } = require('pg');
    const pool = new Pool({
      connectionString: process.env.DATABASE_URL
    });

    const statsQuery = `
      SELECT bug_category, COUNT(*) as count
      FROM v_bug_patterns
      GROUP BY bug_category
      ORDER BY count DESC
    `;

    const recentQuery = `
      SELECT snapshot_id, bug_text, bug_category, pst_time
      FROM v_bug_patterns
      ORDER BY pst_time DESC
      LIMIT 10
    `;

    const [stats, recent] = await Promise.all([
      pool.query(statsQuery),
      pool.query(recentQuery)
    ]);

    await pool.end();

    res.json({
      categories: stats.rows,
      recent: recent.rows
    });

  } catch (error) {
    console.error('Bugs API error:', error);
    res.status(500).json({ error: error.message });
  }
});

// File activity API
app.get('/api/files', async (req, res) => {
  try {
    const { Pool } = require('pg');
    const pool = new Pool({
      connectionString: process.env.DATABASE_URL
    });

    const query = `
      SELECT
        file_path,
        mention_count,
        file_type,
        last_mentioned,
        project_count
      FROM v_file_heatmap
      ORDER BY mention_count DESC
      LIMIT 15
    `;

    const result = await pool.query(query);
    await pool.end();

    res.json(result.rows);

  } catch (error) {
    console.error('Files API error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Decisions API
app.get('/api/decisions', async (req, res) => {
  try {
    const { Pool } = require('pg');
    const pool = new Pool({
      connectionString: process.env.DATABASE_URL
    });

    // Pull from key_decisions array AND extract from Claude API summary markdown.
    // Summary decisions are more reliable — Claude API writes structured "## Decisions" sections.
    const query = `
      SELECT
        id AS snapshot_id,
        project_path,
        timestamp AS pst_time,
        compaction_index,
        key_decisions,
        summary
      FROM context_snapshots
      ORDER BY timestamp DESC
      LIMIT 20
    `;

    const result = await pool.query(query);
    await pool.end();

    // Extract decisions from both sources, deduplicate, return newest first
    const decisions = [];

    for (const row of result.rows) {
      const source = `${row.project_path} (snapshot #${row.snapshot_id}, compaction #${row.compaction_index})`;

      // Extract from summary markdown — bullet points under decision headers
      if (row.summary) {
        const lines = row.summary.split('\n');
        let inDecisionSection = false;
        for (const line of lines) {
          if (/^#{1,3}\s.*(decision|decided|chose|architecture)/i.test(line)) {
            inDecisionSection = true;
            continue;
          }
          if (/^#{1,3}\s/.test(line)) {
            inDecisionSection = false;
            continue;
          }
          if (inDecisionSection && /^[-*]\s+/.test(line)) {
            const text = line.replace(/^[-*]\s+/, '').replace(/\*\*/g, '').trim();
            if (text.length > 15) {
              decisions.push({ snapshot_id: row.snapshot_id, decision_text: text, pst_time: row.pst_time, source });
            }
          }
        }
      }
    }

    // Sort by timestamp desc, deduplicate by text similarity, cap at 20
    const seen = new Set();
    const deduped = decisions.filter(d => {
      const key = d.decision_text.slice(0, 60).toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    }).slice(0, 20);

    res.json(deduped);

  } catch (error) {
    console.error('Decisions API error:', error);
    res.status(500).json({ error: error.message });
  }
});

// ============================================================================
// AGENT MEMORY API ENDPOINTS
// ============================================================================

// Agent stats overview API
app.get('/api/agents/stats', async (req, res) => {
  try {
    const { Pool } = require('pg');
    const pool = new Pool({
      connectionString: process.env.DATABASE_URL
    });

    const statsQuery = `
      SELECT
        COUNT(DISTINCT aw.id) as total_agents,
        COUNT(DISTINCT ad.id) as unique_configs,
        COUNT(DISTINCT aw.parent_snapshot_id) as sessions_with_agents,
        AVG(aw.duration_seconds)::numeric(10,1) as avg_duration,
        SUM(jsonb_array_length(aw.work_context)) as total_messages
      FROM agent_work aw
      JOIN agent_definitions ad ON ad.id = aw.agent_definition_id
    `;

    const typesQuery = `
      SELECT ad.agent_type, COUNT(*) as count
      FROM agent_work aw
      JOIN agent_definitions ad ON ad.id = aw.agent_definition_id
      GROUP BY ad.agent_type
      ORDER BY count DESC
    `;

    const [stats, types] = await Promise.all([
      pool.query(statsQuery),
      pool.query(typesQuery)
    ]);

    await pool.end();

    res.json({
      overview: stats.rows[0],
      byType: types.rows
    });

  } catch (error) {
    console.error('Agent stats API error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Agent configuration performance API
app.get('/api/agents/performance', async (req, res) => {
  try {
    const { Pool } = require('pg');
    const pool = new Pool({
      connectionString: process.env.DATABASE_URL
    });

    const query = `
      SELECT
        agent_type,
        version,
        model_used,
        times_used,
        avg_duration_seconds,
        avg_messages,
        success_rate_pct
      FROM v_agent_config_performance
      WHERE times_used > 0
      ORDER BY agent_type, version
    `;

    const result = await pool.query(query);
    await pool.end();

    res.json(result.rows);

  } catch (error) {
    console.error('Agent performance API error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Agent tool usage API
app.get('/api/agents/tools', async (req, res) => {
  try {
    const { Pool } = require('pg');
    const pool = new Pool({
      connectionString: process.env.DATABASE_URL
    });

    const query = `
      SELECT
        agent_type,
        tool_name,
        total_uses,
        sessions_used_in,
        avg_duration_when_used
      FROM v_agent_tool_usage
      ORDER BY total_uses DESC
      LIMIT 20
    `;

    const result = await pool.query(query);
    await pool.end();

    res.json(result.rows);

  } catch (error) {
    console.error('Agent tools API error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Recent agent work API
app.get('/api/agents/recent', async (req, res) => {
  try {
    const { Pool } = require('pg');
    const pool = new Pool({
      connectionString: process.env.DATABASE_URL
    });

    const limit = parseInt(req.query.limit) || 10;

    const query = `
      SELECT
        work_id,
        agent_id,
        agent_type,
        LEFT(agent_request, 60) as request,
        duration_seconds,
        pst_start,
        project_path
      FROM v_agent_work_full
      ORDER BY pst_start DESC NULLS LAST
      LIMIT $1
    `;

    const result = await pool.query(query, [limit]);
    await pool.end();

    res.json(result.rows);

  } catch (error) {
    console.error('Agent recent API error:', error);
    res.status(500).json({ error: error.message });
  }
});

// ============================================================================
// ACTIVE WORK API — vault projects + planning session states
// ============================================================================

// Vault project states — reads Current State.md files from claude-vault
app.get('/api/vault/projects', (req, res) => {
  const fs = require('fs');
  const path = require('path');
  const vaultRoot = process.env.VAULT_ROOT || '/home/hp-admin/code/claude-vault';
  const projectsDir = path.join(vaultRoot, 'Projects');

  function extract(text) {
    const updated = (text.match(/^updated:\s*(.+)$/m) || [])[1]?.trim() || null;
    const phaseMatch =
      text.match(/\*\*Phase[:\s]+([^\n*]+)\*\*/) ||
      text.match(/## Where We Are\s*\n+\*\*([^\n*]+)\*\*/s);
    const phase = phaseMatch ? phaseMatch[1].trim() : null;
    const stepsBlock = (text.match(/## Immediate Next Steps\s*\n([\s\S]*?)(?=\n##|$)/) || [])[1] || '';
    const steps = (stepsBlock.match(/^\d+\.\s+\*\*([^*]+)\*\*/gm) || stepsBlock.match(/^\d+\.\s+(.+)$/gm) || [])
      .slice(0, 3)
      .map(s => s.replace(/^\d+\.\s+/, '').replace(/\*\*/g, '').trim());
    return { updated, phase, steps };
  }

  try {
    if (!fs.existsSync(projectsDir)) return res.json([]);
    const projects = fs.readdirSync(projectsDir)
      .filter(name => fs.statSync(path.join(projectsDir, name)).isDirectory())
      .map(name => {
        const csPath = path.join(projectsDir, name, 'Current State.md');
        if (!fs.existsSync(csPath)) return null;
        const data = extract(fs.readFileSync(csPath, 'utf8'));
        return { name, ...data };
      })
      .filter(Boolean)
      .sort((a, b) => (b.updated || '').localeCompare(a.updated || ''));
    res.json(projects);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Planning session states — reads SESSION-STATE.md files from hp-feature-planning
app.get('/api/planning/states', (req, res) => {
  const fs = require('fs');
  const path = require('path');
  const planningRoot = process.env.PLANNING_ROOT || '/home/hp-admin/data/code/hp-feature-planning';

  function extract(text) {
    const updated   = (text.match(/\*\*Last Updated:\*\*\s*(.+)/) || [])[1]?.trim() || null;
    const status    = (text.match(/\*\*Session Status:\*\*\s*(.+)/) || [])[1]?.trim() || null;
    const nextMatch = text.match(/\*\*Next Action:\*\*\s*\n([^\n]+)/) || text.match(/\*\*Next Action:\*\*\s*(.+)/);
    const next      = nextMatch ? nextMatch[1].trim() : null;
    return { updated, status, next };
  }

  try {
    if (!fs.existsSync(planningRoot)) return res.json([]);
    const states = fs.readdirSync(planningRoot)
      .filter(name => name !== 'TEMPLATE' && fs.statSync(path.join(planningRoot, name)).isDirectory())
      .map(name => {
        const ssPath = path.join(planningRoot, name, 'SESSION-STATE.md');
        if (!fs.existsSync(ssPath)) return null;
        const data = extract(fs.readFileSync(ssPath, 'utf8'));
        return { folder: name, ...data };
      })
      .filter(Boolean)
      .sort((a, b) => (b.updated || '').localeCompare(a.updated || ''));
    res.json(states);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ============================================================================
// VAULT STATS API — deep scan of claude-vault filesystem
// ============================================================================

app.get('/api/vault/stats', (req, res) => {
  const fs = require('fs');
  const pathMod = require('path');
  const vaultRoot = process.env.VAULT_ROOT || '/home/hp-admin/code/claude-vault';

  function walk(dir, results = []) {
    if (!fs.existsSync(dir)) return results;
    let entries;
    try { entries = fs.readdirSync(dir); } catch { return results; }
    for (const name of entries) {
      if (name.startsWith('.')) continue;
      const full = pathMod.join(dir, name);
      let stat;
      try { stat = fs.statSync(full); } catch { continue; }
      if (stat.isDirectory()) walk(full, results);
      else if (name.endsWith('.md')) results.push(full);
    }
    return results;
  }

  try {
    // 1. Last active file from workspace.json
    let lastActive = null;
    try {
      const wsPath = pathMod.join(vaultRoot, '.obsidian', 'workspace.json');
      const ws = JSON.parse(fs.readFileSync(wsPath, 'utf8'));
      // Try the leaf active file first, then lastOpenFiles
      const getLeafFile = (node) => {
        if (!node) return null;
        if (node.type === 'leaf' && node.state?.type === 'markdown') return node.state.state?.file || null;
        for (const child of node.children || []) { const f = getLeafFile(child); if (f) return f; }
        return null;
      };
      lastActive = getLeafFile(ws.main) || ws.lastOpenFiles?.[0] || null;
    } catch (e) {}

    // 2. Session cadence from Claude/Session-Logs/
    const sessionLogsDir = pathMod.join(vaultRoot, 'Claude', 'Session-Logs');
    let sessionDates = [];
    if (fs.existsSync(sessionLogsDir)) {
      sessionDates = fs.readdirSync(sessionLogsDir)
        .filter(f => /^\d{4}-\d{2}-\d{2}\.md$/.test(f))
        .map(f => f.replace('.md', ''))
        .sort();
    }

    // 3. Document depth per project
    const projectsDir = pathMod.join(vaultRoot, 'Projects');
    let projectDepth = [];
    if (fs.existsSync(projectsDir)) {
      projectDepth = fs.readdirSync(projectsDir)
        .filter(name => { try { return fs.statSync(pathMod.join(projectsDir, name)).isDirectory(); } catch { return false; } })
        .map(name => ({ project: name, fileCount: walk(pathMod.join(projectsDir, name)).length }))
        .sort((a, b) => b.fileCount - a.fileCount);
    }

    // 4. Scan all notes: open items, tags, decision velocity
    const allFiles = walk(vaultRoot);
    const openItemsByFile = {};
    const tagCounts = {};
    const decisionDates = [];

    for (const file of allFiles) {
      const rel = file.slice(vaultRoot.length + 1);
      let text;
      try { text = fs.readFileSync(file, 'utf8'); } catch { continue; }

      // Open items — capture mtime for time-based sorting
      const items = [...text.matchAll(/^- \[ \] (.+)$/gm)].map(m => m[1].trim());
      if (items.length) {
        let mtime = 0;
        try { mtime = fs.statSync(file).mtimeMs; } catch {}
        openItemsByFile[rel] = { items, mtime };
      }

      // Tags from YAML frontmatter
      const fmMatch = text.match(/^---\n([\s\S]*?)\n---/);
      if (fmMatch) {
        for (const m of fmMatch[1].matchAll(/^\s*-\s+(.+)$/gm)) {
          const tag = m[1].trim();
          tagCounts[tag] = (tagCounts[tag] || 0) + 1;
        }
      }

      // Decision dates from Decisions Log files (## YYYY-MM-DD headers)
      if (pathMod.basename(file).toLowerCase().includes('decisions')) {
        for (const m of text.matchAll(/^## (\d{4}-\d{2}-\d{2})/gm)) decisionDates.push(m[1]);
      }
    }

    // Tag cloud — top 20 tags, skip single-word non-hierarchical common tokens
    const tagCloud = Object.entries(tagCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20)
      .map(([tag, count]) => ({ tag, count }));

    // Decision timeline — group by month
    const decisionsByMonth = {};
    for (const d of decisionDates) {
      const month = d.slice(0, 7);
      decisionsByMonth[month] = (decisionsByMonth[month] || 0) + 1;
    }

    // Open items summary — sorted by file modification time descending (freshest first)
    const openItemsSummary = Object.entries(openItemsByFile)
      .map(([file, { items, mtime }]) => ({ file: file.replace(/^Projects\//, ''), items: items.slice(0, 5), total: items.length, mtime }))
      .sort((a, b) => b.mtime - a.mtime)
      .slice(0, 12);

    res.json({
      lastActive,
      sessions: {
        dates: sessionDates,
        total: sessionDates.length,
        last: sessionDates[sessionDates.length - 1] || null,
        first: sessionDates[0] || null,
      },
      projectDepth,
      openItems: {
        byFile: openItemsSummary,
        totalFiles: openItemsSummary.length,
        totalItems: openItemsSummary.reduce((s, f) => s + f.total, 0),
      },
      decisions: {
        total: decisionDates.length,
        byMonth: Object.entries(decisionsByMonth).sort().map(([month, count]) => ({ month, count })),
      },
      tagCloud,
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ============================================================================
// SKILLS API
// ============================================================================

app.get('/api/skills', async (req, res) => {
  try {
    const { Pool } = require('pg');
    const pool = new Pool({ connectionString: process.env.DATABASE_URL });

    const skillsQuery = `
      SELECT
        sa.id,
        sa.agent_name,
        sa.display_name,
        sa.description,
        sa.category,
        sa.scope,
        sa.is_active,
        sa.use_count,
        sa.success_count,
        sa.success_rate,
        sa.confidence_score,
        sa.created_at,
        sa.last_used,
        COUNT(st.id) as trigger_count,
        sc.command_type
      FROM skills_agents sa
      LEFT JOIN skills_triggers st ON st.agent_id = sa.id AND st.is_active = true
      LEFT JOIN skills_commands sc ON sc.agent_id = sa.id
      GROUP BY sa.id, sc.command_type
      ORDER BY sa.category, sa.agent_name
    `;

    const categoryQuery = `
      SELECT category, COUNT(*) as count, SUM(use_count) as total_uses
      FROM skills_agents
      WHERE is_active = true
      GROUP BY category
      ORDER BY count DESC
    `;

    const [skills, categories] = await Promise.all([
      pool.query(skillsQuery),
      pool.query(categoryQuery)
    ]);

    await pool.end();
    res.json({ skills: skills.rows, categories: categories.rows });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Embedding generation endpoint (for query embeddings)
app.post('/embed', async (req, res) => {
  const { text } = req.body;

  if (!text || typeof text !== 'string') {
    return res.status(400).json({
      status: 'error',
      message: 'Missing or invalid "text" parameter'
    });
  }

  try {
    const embedding = await generateEmbedding(text);

    res.json({
      status: 'success',
      embedding: embedding,
      dimensions: embedding.length
    });

  } catch (error) {
    console.error('Embedding generation error:', error);
    res.status(500).json({
      status: 'error',
      message: error.message
    });
  }
});

// Capture endpoint - triggered by hooks or manual requests
app.post('/capture', async (req, res) => {
  const { project_path, trigger = 'manual', conversation_data, session_id, transcript_path,
          message_start_index, compaction_index } = req.body;

  console.log(`[${new Date().toISOString()}] Capture request received:`, {
    project_path,
    trigger,
    session_id,
    transcript_path
  });

  try {
    // Acknowledge immediately (async processing)
    res.status(202).json({
      status: 'accepted',
      message: 'Context capture initiated',
      project_path,
      trigger
    });

    // Process asynchronously (don't block the response)
    setImmediate(async () => {
      try {
        await capture.captureContext({
          project_path,
          trigger,
          conversation_data,
          session_id,
          transcript_path,
          message_start_index: message_start_index || 0,
          compaction_index: compaction_index || 1
        });
        console.log(`[${new Date().toISOString()}] ✅ Capture completed for ${project_path}`);
      } catch (error) {
        console.error(`[${new Date().toISOString()}] ❌ Capture failed:`, error.message);
      }
    });

  } catch (error) {
    console.error('Error initiating capture:', error);
    res.status(500).json({
      status: 'error',
      message: error.message
    });
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`🚀 Claude Context Processor running on port ${PORT}`);
  console.log(`📍 Workspace: ${process.env.CLAUDE_CODE_ROOT}`);
  console.log(`🔗 Database: ${process.env.DATABASE_URL ? 'Connected' : 'Not configured'}`);
  console.log(`🤖 Ollama: ${process.env.OLLAMA_URL}`);
  console.log(`🧠 Embeddings: ${process.env.EMBEDDING_MODEL}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully...');
  process.exit(0);
});
