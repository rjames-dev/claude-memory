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
    const totalQuery = 'SELECT COUNT(*) as total FROM context_snapshots';
    const todayQuery = `SELECT COUNT(*) as today FROM context_snapshots WHERE timestamp >= CURRENT_DATE`;
    const weekQuery = `SELECT COUNT(*) as week FROM context_snapshots WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'`;
    const lastQuery = `SELECT timestamp FROM context_snapshots ORDER BY timestamp DESC LIMIT 1`;
    const sessionsQuery = `SELECT COUNT(DISTINCT session_id) as sessions FROM context_snapshots WHERE session_id IS NOT NULL`;

    const [total, today, week, last, sessions] = await Promise.all([
      pool.query(totalQuery),
      pool.query(todayQuery),
      pool.query(weekQuery),
      pool.query(lastQuery),
      pool.query(sessionsQuery)
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
        snapshots: parseInt(total.rows[0].total)
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
        total: parseInt(total.rows[0].total),
        today: parseInt(today.rows[0].today),
        week: parseInt(week.rows[0].week),
        lastCaptureSeconds: lastCaptureAgo
      },
      sessions: {
        tracked: parseInt(sessions.rows[0].sessions)
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
        context_window_size as messages,
        timestamp,
        CASE
          WHEN trigger_event LIKE '%post-compact%' THEN 'UPDATE'
          ELSE 'NEW'
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

    const query = `
      SELECT
        snapshot_id,
        decision_text,
        pst_time
      FROM v_all_decisions
      ORDER BY pst_time DESC
      LIMIT 10
    `;

    const result = await pool.query(query);
    await pool.end();

    res.json(result.rows);

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
  const { project_path, trigger = 'manual', conversation_data, session_id, transcript_path } = req.body;

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
          transcript_path
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
