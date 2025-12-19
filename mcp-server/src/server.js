#!/usr/bin/env node

/**
 * Claude Memory MCP Server
 * Provides memory retrieval tools for Claude Code via Model Context Protocol
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import pg from 'pg';
import axios from 'axios';

const { Pool} = pg;

// PostgreSQL connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000
});

pool.on('error', (err) => {
  console.error('Unexpected database error:', err);
});

/**
 * Search memory using vector similarity
 */
async function searchMemory(query, projectPath = null, limit = 5) {
  const client = await pool.connect();

  try {
    // Generate embedding for the query
    const processorUrl = process.env.PROCESSOR_URL || 'http://context-processor:3200';
    let queryEmbedding;

    try {
      const embeddingResponse = await axios.post(
        `${processorUrl}/embed`,
        { text: query },
        { timeout: 10000 }
      );

      if (embeddingResponse.data.status !== 'success') {
        throw new Error('Embedding generation failed');
      }

      queryEmbedding = embeddingResponse.data.embedding;

    } catch (error) {
      console.error('Error generating query embedding:', error.message);
      // Fallback to text search if embedding fails
      return await searchMemoryByText(query, projectPath, limit, client);
    }

    // Use vector similarity search with pgvector
    // <=> is cosine distance operator (lower = more similar)
    let sql = `
      SELECT
        id,
        project_path,
        timestamp,
        summary,
        tags,
        mentioned_files,
        key_decisions,
        bugs_fixed,
        git_branch,
        trigger_event,
        (embedding <=> $1::vector) as distance
      FROM context_snapshots
      WHERE embedding IS NOT NULL
    `;

    const params = [JSON.stringify(queryEmbedding)];

    if (projectPath) {
      sql += ` AND project_path = $2`;
      params.push(projectPath);
    }

    sql += ` ORDER BY embedding <=> $1::vector LIMIT $${params.length + 1}`;
    params.push(limit);

    const result = await client.query(sql, params);
    return result.rows;

  } finally {
    client.release();
  }
}

/**
 * Fallback text search when embedding generation fails
 */
async function searchMemoryByText(query, projectPath = null, limit = 5, client) {
  let sql = `
    SELECT
      id,
      project_path,
      timestamp,
      summary,
      tags,
      mentioned_files,
      key_decisions,
      bugs_fixed,
      git_branch,
      trigger_event
    FROM context_snapshots
    WHERE summary ILIKE $1
  `;

  const params = [`%${query}%`];

  if (projectPath) {
    sql += ` AND project_path = $2`;
    params.push(projectPath);
  }

  sql += ` ORDER BY timestamp DESC LIMIT $${params.length + 1}`;
  params.push(limit);

  const result = await client.query(sql, params);
  return result.rows;
}

/**
 * Get timeline of recent context for a project
 */
async function getTimeline(projectPath, limit = 10) {
  const client = await pool.connect();

  try {
    const sql = `
      SELECT
        id,
        project_path,
        timestamp,
        summary,
        tags,
        mentioned_files,
        trigger_event,
        context_window_size
      FROM context_snapshots
      WHERE project_path = $1
      ORDER BY timestamp DESC
      LIMIT $2
    `;

    const result = await client.query(sql, [projectPath, limit]);
    return result.rows;

  } finally {
    client.release();
  }
}

/**
 * Get detailed snapshot by ID
 */
async function getSnapshot(snapshotId) {
  const client = await pool.connect();

  try {
    const sql = `
      SELECT
        id,
        project_path,
        timestamp,
        summary,
        tags,
        mentioned_files,
        key_decisions,
        bugs_fixed,
        git_commit_hash,
        git_branch,
        trigger_event,
        context_window_size,
        storage_size_bytes
      FROM context_snapshots
      WHERE id = $1
    `;

    const result = await client.query(sql, [snapshotId]);
    return result.rows[0] || null;

  } finally {
    client.release();
  }
}

/**
 * Format snapshot for display
 */
function formatSnapshot(snapshot) {
  if (!snapshot) return 'Snapshot not found';

  return `
📋 Snapshot #${snapshot.id}
📁 Project: ${snapshot.project_path}
📅 Date: ${new Date(snapshot.timestamp).toLocaleString()}
🔖 Tags: ${snapshot.tags?.join(', ') || 'none'}
📄 Files: ${snapshot.mentioned_files?.join(', ') || 'none'}
🎯 Trigger: ${snapshot.trigger_event}

📊 Summary:
${snapshot.summary}

${snapshot.key_decisions?.length > 0 ? `\n✅ Key Decisions:\n${snapshot.key_decisions.map(d => `  - ${d}`).join('\n')}` : ''}
${snapshot.bugs_fixed?.length > 0 ? `\n🐛 Bugs Fixed:\n${snapshot.bugs_fixed.map(b => `  - ${b}`).join('\n')}` : ''}
${snapshot.git_branch ? `\n🌿 Git Branch: ${snapshot.git_branch}` : ''}
${snapshot.git_commit_hash ? `📌 Commit: ${snapshot.git_commit_hash.substring(0, 8)}` : ''}
`.trim();
}

// ============================================================================
// AGENT MEMORY TOOLS - Phase 5
// ============================================================================

/**
 * Search agent work using vector similarity
 */
async function searchAgentWork(query, projectPath = null, limit = 5) {
  const client = await pool.connect();

  try {
    // Generate embedding for the query
    const processorUrl = process.env.PROCESSOR_URL || 'http://context-processor:3200';
    let queryEmbedding;

    try {
      const embeddingResponse = await axios.post(
        `${processorUrl}/embed`,
        { text: query },
        { timeout: 10000 }
      );

      if (embeddingResponse.data.status !== 'success') {
        throw new Error('Embedding generation failed');
      }

      queryEmbedding = embeddingResponse.data.embedding;

    } catch (error) {
      console.error('Error generating query embedding:', error.message);
      // Fallback to text search
      return await searchAgentWorkByText(query, projectPath, limit, client);
    }

    // Vector similarity search on agent work
    let sql = `
      SELECT
        aw.id,
        aw.agent_id,
        ad.agent_type,
        ad.version,
        ad.model_used,
        aw.agent_request,
        aw.result_summary,
        aw.tools_used,
        aw.files_examined,
        aw.urls_fetched,
        aw.duration_seconds,
        aw.timestamp_start,
        aw.parent_snapshot_id,
        (aw.embedding <=> $1::vector) as distance
      FROM agent_work aw
      JOIN agent_definitions ad ON ad.id = aw.agent_definition_id
      WHERE aw.embedding IS NOT NULL
    `;

    const params = [JSON.stringify(queryEmbedding)];

    if (projectPath) {
      sql += ` AND EXISTS (
        SELECT 1 FROM context_snapshots cs
        WHERE cs.id = aw.parent_snapshot_id
        AND cs.project_path = $2
      )`;
      params.push(projectPath);
    }

    sql += ` ORDER BY aw.embedding <=> $1::vector LIMIT $${params.length + 1}`;
    params.push(limit);

    const result = await client.query(sql, params);
    return result.rows;

  } finally {
    client.release();
  }
}

/**
 * Fallback text search for agent work
 */
async function searchAgentWorkByText(query, projectPath = null, limit = 5, client) {
  let sql = `
    SELECT
      aw.id,
      aw.agent_id,
      ad.agent_type,
      ad.version,
      ad.model_used,
      aw.agent_request,
      aw.result_summary,
      aw.tools_used,
      aw.files_examined,
      aw.duration_seconds,
      aw.timestamp_start
    FROM agent_work aw
    JOIN agent_definitions ad ON ad.id = aw.agent_definition_id
    WHERE (aw.agent_request ILIKE $1 OR aw.result_summary ILIKE $1)
  `;

  const params = [`%${query}%`];

  if (projectPath) {
    sql += ` AND EXISTS (
      SELECT 1 FROM context_snapshots cs
      WHERE cs.id = aw.parent_snapshot_id
      AND cs.project_path = $2
    )`;
    params.push(projectPath);
  }

  sql += ` ORDER BY aw.timestamp_start DESC LIMIT $${params.length + 1}`;
  params.push(limit);

  const result = await client.query(sql, params);
  return result.rows;
}

/**
 * Get agent analytics and performance metrics
 */
async function getAgentAnalytics(agentType = null, projectPath = null) {
  const client = await pool.connect();

  try {
    // Get overview stats
    let overviewSql = `
      SELECT
        COUNT(DISTINCT aw.id) as total_agents,
        COUNT(DISTINCT ad.id) as unique_configs,
        COUNT(DISTINCT aw.parent_snapshot_id) as sessions_with_agents,
        AVG(aw.duration_seconds)::numeric(10,1) as avg_duration,
        SUM(jsonb_array_length(aw.work_context)) as total_messages
      FROM agent_work aw
      JOIN agent_definitions ad ON ad.id = aw.agent_definition_id
      WHERE 1=1
    `;

    const overviewParams = [];

    if (agentType) {
      overviewSql += ` AND ad.agent_type = $${overviewParams.length + 1}`;
      overviewParams.push(agentType);
    }

    if (projectPath) {
      overviewSql += ` AND EXISTS (
        SELECT 1 FROM context_snapshots cs
        WHERE cs.id = aw.parent_snapshot_id
        AND cs.project_path = $${overviewParams.length + 1}
      )`;
      overviewParams.push(projectPath);
    }

    // Get performance by config
    let perfSql = `
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
    `;

    const perfParams = [];

    if (agentType) {
      perfSql += ` AND agent_type = $${perfParams.length + 1}`;
      perfParams.push(agentType);
    }

    perfSql += ` ORDER BY agent_type, version`;

    // Get tool usage stats
    let toolsSql = `
      SELECT
        agent_type,
        tool_name,
        total_uses,
        sessions_used_in,
        avg_duration_when_used
      FROM v_agent_tool_usage
      WHERE 1=1
    `;

    const toolsParams = [];

    if (agentType) {
      toolsSql += ` AND agent_type = $${toolsParams.length + 1}`;
      toolsParams.push(agentType);
    }

    toolsSql += ` ORDER BY total_uses DESC LIMIT 20`;

    const [overview, performance, tools] = await Promise.all([
      client.query(overviewSql, overviewParams),
      client.query(perfSql, perfParams),
      client.query(toolsSql, toolsParams)
    ]);

    return {
      overview: overview.rows[0],
      performance: performance.rows,
      tools: tools.rows
    };

  } finally {
    client.release();
  }
}

/**
 * Compare agent configurations
 */
async function compareAgentConfigs(agentType, versions = null) {
  const client = await pool.connect();

  try {
    let sql = `
      SELECT
        agent_type,
        version,
        model_used,
        times_used,
        avg_duration_seconds,
        avg_messages,
        success_rate_pct,
        LAG(avg_duration_seconds) OVER (PARTITION BY agent_type ORDER BY version) as prev_avg_duration,
        CASE
          WHEN LAG(avg_duration_seconds) OVER (PARTITION BY agent_type ORDER BY version) IS NOT NULL
          THEN ROUND(
            ((LAG(avg_duration_seconds) OVER (PARTITION BY agent_type ORDER BY version) - avg_duration_seconds)
            / LAG(avg_duration_seconds) OVER (PARTITION BY agent_type ORDER BY version) * 100)::numeric,
            1
          )
          ELSE NULL
        END as performance_improvement_pct
      FROM v_agent_config_performance
      WHERE agent_type = $1 AND times_used > 0
    `;

    const params = [agentType];

    if (versions && versions.length > 0) {
      sql += ` AND version = ANY($2::int[])`;
      params.push(versions);
    }

    sql += ` ORDER BY version`;

    const result = await client.query(sql, params);
    return result.rows;

  } finally {
    client.release();
  }
}

// ============================================================================
// PHASE 1 ANALYTICAL TOOLS - Using Views
// ============================================================================

/**
 * Search for exact phrase in assistant messages
 */
async function searchExactPhrase(phrase, projectPath = null, limit = 10) {
  const client = await pool.connect();

  try {
    let sql = `
      SELECT snapshot_id, project_path, pst_time, content
      FROM v_assistant_messages
      WHERE LOWER(content) LIKE LOWER($1)
    `;

    const params = [`%${phrase}%`];

    if (projectPath) {
      sql += ` AND project_path = $2`;
      params.push(projectPath);
    }

    sql += ` ORDER BY pst_time DESC LIMIT $${params.length + 1}`;
    params.push(limit);

    const result = await client.query(sql, params);
    return result.rows;

  } finally {
    client.release();
  }
}

/**
 * Get quality report for snapshots
 */
async function getQualityReport(minQualityScore = 0, projectPath = null, limit = 20) {
  const client = await pool.connect();

  try {
    let sql = `
      SELECT id, project_path, pst_time, quality_score,
             message_count, tag_count, file_count,
             decision_count, bug_count
      FROM v_snapshot_quality
      WHERE quality_score >= $1
    `;

    const params = [minQualityScore];

    if (projectPath) {
      sql += ` AND project_path = $2`;
      params.push(projectPath);
    }

    sql += ` ORDER BY quality_score DESC, id DESC LIMIT $${params.length + 1}`;
    params.push(limit);

    const result = await client.query(sql, params);

    // Also get summary stats
    const statsResult = await client.query(`
      SELECT
        AVG(quality_score)::numeric(4,2) as avg_quality,
        COUNT(*) FILTER (WHERE quality_score >= 8) as high_quality,
        COUNT(*) FILTER (WHERE quality_score >= 5 AND quality_score < 8) as medium_quality,
        COUNT(*) FILTER (WHERE quality_score < 5) as low_quality,
        COUNT(*) as total
      FROM v_snapshot_quality
    `);

    return {
      snapshots: result.rows,
      stats: statsResult.rows[0]
    };

  } finally {
    client.release();
  }
}

/**
 * Get project statistics
 */
async function getProjectStats(projectPath = null) {
  const client = await pool.connect();

  try {
    let sql = `SELECT * FROM v_project_dashboard`;

    if (projectPath) {
      sql += ` WHERE project_path = $1`;
      const result = await client.query(sql, [projectPath]);
      return result.rows[0] || null;
    } else {
      sql += ` ORDER BY last_activity DESC`;
      const result = await client.query(sql);
      return result.rows;
    }

  } finally {
    client.release();
  }
}

/**
 * Search decisions
 */
async function searchDecisions(keyword, projectPath = null, limit = 10) {
  const client = await pool.connect();

  try {
    let sql = `
      SELECT snapshot_id, project_path, pst_time, decision_text
      FROM v_all_decisions
      WHERE LOWER(decision_text) LIKE LOWER($1)
    `;

    const params = [`%${keyword}%`];

    if (projectPath) {
      sql += ` AND project_path = $2`;
      params.push(projectPath);
    }

    sql += ` ORDER BY pst_time DESC LIMIT $${params.length + 1}`;
    params.push(limit);

    const result = await client.query(sql, params);
    return result.rows;

  } finally {
    client.release();
  }
}

/**
 * Analyze bugs with optional category filter
 */
async function analyzeBugs(category = null, projectPath = null, limit = 20) {
  const client = await pool.connect();

  try {
    let sql = `
      SELECT snapshot_id, project_path, pst_time, bug_text, bug_category
      FROM v_bug_patterns
      WHERE 1=1
    `;

    const params = [];

    if (category) {
      sql += ` AND bug_category = $${params.length + 1}`;
      params.push(category);
    }

    if (projectPath) {
      sql += ` AND project_path = $${params.length + 1}`;
      params.push(projectPath);
    }

    sql += ` ORDER BY pst_time DESC LIMIT $${params.length + 1}`;
    params.push(limit);

    const result = await client.query(sql, params);

    // Also get category stats
    const statsResult = await client.query(`
      SELECT bug_category, COUNT(*) as count
      FROM v_bug_patterns
      GROUP BY bug_category
      ORDER BY count DESC
    `);

    return {
      bugs: result.rows,
      stats: statsResult.rows
    };

  } finally {
    client.release();
  }
}

/**
 * Get file activity heatmap
 */
async function getFileActivity(fileType = null, minMentions = 1, limit = 20) {
  const client = await pool.connect();

  try {
    let sql = `
      SELECT file_path, mention_count, file_type,
             first_mentioned, last_mentioned, mentioned_in_projects
      FROM v_file_heatmap
      WHERE mention_count >= $1
    `;

    const params = [minMentions];

    if (fileType) {
      sql += ` AND file_type = $2`;
      params.push(fileType);
    }

    sql += ` ORDER BY mention_count DESC LIMIT $${params.length + 1}`;
    params.push(limit);

    const result = await client.query(sql, params);

    // Also get file type stats
    const statsResult = await client.query(`
      SELECT file_type, COUNT(*) as file_count, SUM(mention_count) as total_mentions
      FROM v_file_heatmap
      GROUP BY file_type
      ORDER BY total_mentions DESC
    `);

    return {
      files: result.rows,
      stats: statsResult.rows
    };

  } finally {
    client.release();
  }
}

// ============================================================================
// FORMATTERS FOR PHASE 1 TOOLS
// ============================================================================

function formatExactPhraseResults(results, phrase) {
  if (results.length === 0) {
    return `No occurrences found for: "${phrase}"`;
  }

  const formatted = results.map(r => `
📋 Snapshot #${r.snapshot_id} - ${new Date(r.pst_time).toLocaleString()}
📁 Project: ${r.project_path}
💬 Preview: ${r.content.substring(0, 150)}...
  `.trim()).join('\n\n');

  return `Found ${results.length} occurrence(s) of "${phrase}":\n\n${formatted}`;
}

function formatQualityReport(data) {
  const { snapshots, stats } = data;

  const header = `
📊 Data Quality Report

Average Quality: ${stats.avg_quality}/10
Total Snapshots: ${stats.total}
High Quality (≥8): ${stats.high_quality} (${Math.round(stats.high_quality / stats.total * 100)}%)
Medium Quality (5-7): ${stats.medium_quality} (${Math.round(stats.medium_quality / stats.total * 100)}%)
Low Quality (<5): ${stats.low_quality} (${Math.round(stats.low_quality / stats.total * 100)}%)
  `.trim();

  if (snapshots.length === 0) {
    return header + '\n\nNo snapshots match the quality criteria.';
  }

  const snapshotList = snapshots.map(s => `
#${s.id} | Score: ${s.quality_score}/10 | Messages: ${s.message_count} | Tags: ${s.tag_count} | Files: ${s.file_count}
     Project: ${s.project_path.split('/').pop()}
  `.trim()).join('\n\n');

  return `${header}\n\nTop Snapshots:\n\n${snapshotList}`;
}

function formatProjectStats(data) {
  if (!data) {
    return 'No project data found';
  }

  // Single project
  if (!Array.isArray(data)) {
    const formatInterval = (interval) => {
      if (!interval) return 'N/A';
      const match = interval.match(/(\d+):(\d+):(\d+)/);
      if (!match) return interval;
      const [_, hours, minutes] = match;
      if (hours === '00') return `${parseInt(minutes)} minutes ago`;
      if (hours < 24) return `${parseInt(hours)} hours ago`;
      return `${Math.floor(hours / 24)} days ago`;
    };

    return `
📊 Project Statistics: ${data.project_path.split('/').pop()}

Activity:
  Total Snapshots: ${data.total_snapshots}
  Tracked Sessions: ${data.tracked_sessions}
  First Activity: ${new Date(data.first_activity).toLocaleString()}
  Last Activity: ${new Date(data.last_activity).toLocaleString()}
  Time Since Last: ${formatInterval(data.time_since_last_activity)}

Messages:
  Total Messages: ${data.total_messages}
  Average per Snapshot: ${data.avg_messages_per_snapshot}
  Max Messages: ${data.max_messages}

Metadata Richness:
  Avg Tags: ${data.avg_tags}
  Avg Files: ${data.avg_files}
  Avg Decisions: ${data.avg_decisions}
  Avg Bugs: ${data.avg_bugs}

Quality:
  With Summary: ${data.snapshots_with_summary}/${data.total_snapshots} (${Math.round(data.snapshots_with_summary / data.total_snapshots * 100)}%)
  With Embedding: ${data.snapshots_with_embedding}/${data.total_snapshots} (${Math.round(data.snapshots_with_embedding / data.total_snapshots * 100)}%)
  With Session ID: ${data.snapshots_with_session_id}/${data.total_snapshots} (${Math.round(data.snapshots_with_session_id / data.total_snapshots * 100)}%)

Most Common Tag: ${data.most_common_tag || 'none'}
    `.trim();
  }

  // All projects
  const projectList = data.map(p => `
📁 ${p.project_path.split('/').pop()}
   Snapshots: ${p.total_snapshots} | Messages: ${p.total_messages} | Tag: ${p.most_common_tag || 'none'}
  `.trim()).join('\n\n');

  return `📊 All Projects (${data.length} total):\n\n${projectList}`;
}

function formatDecisions(results, keyword) {
  if (results.length === 0) {
    return `No decisions found matching: "${keyword}"`;
  }

  const formatted = results.map(r => `
📋 Snapshot #${r.snapshot_id} - ${new Date(r.pst_time).toLocaleString()}
📁 Project: ${r.project_path.split('/').pop()}
💡 Decision: ${r.decision_text}
  `.trim()).join('\n\n');

  return `Found ${results.length} decision(s) matching "${keyword}":\n\n${formatted}`;
}

function formatBugAnalysis(data) {
  const { bugs, stats } = data;

  const total = stats.reduce((sum, s) => sum + parseInt(s.count), 0);

  const header = `
🐛 Bug Analysis Report

Total Bugs Fixed: ${total}
Category Breakdown:
${stats.map(s => `  - ${s.bug_category}: ${s.count} (${Math.round(s.count / total * 100)}%)`).join('\n')}
  `.trim();

  if (bugs.length === 0) {
    return header + '\n\nNo bugs match the filter criteria.';
  }

  const bugList = bugs.map(b => `
📋 Snapshot #${b.snapshot_id} - ${new Date(b.pst_time).toLocaleString()}
🔴 Bug: ${b.bug_text.substring(0, 100)}${b.bug_text.length > 100 ? '...' : ''}
📦 Category: ${b.bug_category}
  `.trim()).join('\n\n');

  return `${header}\n\nRecent Bugs:\n\n${bugList}`;
}

function formatFileActivity(data) {
  const { files, stats } = data;

  const totalFiles = stats.reduce((sum, s) => sum + parseInt(s.file_count), 0);

  const header = `
📁 File Activity Heatmap

Total Files Tracked: ${totalFiles}
File Type Breakdown:
${stats.map(s => `  - ${s.file_type}: ${s.file_count} files (${Math.round(s.file_count / totalFiles * 100)}%)`).join('\n')}
  `.trim();

  if (files.length === 0) {
    return header + '\n\nNo files match the criteria.';
  }

  const fileList = files.map(f => `
🔥 ${f.file_path} (${f.mention_count} mentions)
   Type: ${f.file_type}
   Last Touched: ${new Date(f.last_mentioned).toLocaleString()}
   Projects: ${f.mentioned_in_projects.length}
  `.trim()).join('\n\n');

  return `${header}\n\nHottest Files:\n\n${fileList}`;
}

// ============================================================================
// FORMATTERS FOR AGENT TOOLS - Phase 5
// ============================================================================

function formatAgentWork(agent) {
  const toolsList = agent.tools_used ? Object.entries(agent.tools_used).map(([tool, count]) => `${tool}(${count})`).join(', ') : 'none';
  const filesList = agent.files_examined?.length > 0 ? agent.files_examined.join(', ') : 'none';
  const urlsList = agent.urls_fetched?.length > 0 ? agent.urls_fetched.join(', ') : 'none';

  return `
🤖 Agent #${agent.id} (${agent.agent_id})
📋 Type: ${agent.agent_type} v${agent.version} ${agent.model_used ? `(${agent.model_used})` : ''}
📅 When: ${agent.timestamp_start ? new Date(agent.timestamp_start).toLocaleString() : 'N/A'}
⏱️  Duration: ${agent.duration_seconds ? `${agent.duration_seconds}s` : 'N/A'}

🎯 Request:
${agent.agent_request}

${agent.result_summary ? `\n✅ Result:\n${agent.result_summary.substring(0, 200)}${agent.result_summary.length > 200 ? '...' : ''}` : ''}

🔧 Tools Used: ${toolsList}
📄 Files: ${filesList}
🌐 URLs: ${urlsList}
${agent.parent_snapshot_id ? `\n📎 Parent Snapshot: #${agent.parent_snapshot_id}` : ''}
  `.trim();
}

function formatAgentAnalytics(data) {
  const { overview, performance, tools } = data;

  const header = `
🤖 Agent Analytics Report

Overview:
  Total Agents: ${overview.total_agents}
  Unique Configurations: ${overview.unique_configs}
  Sessions with Agents: ${overview.sessions_with_agents}
  Average Duration: ${overview.avg_duration || 'N/A'}s
  Total Messages: ${overview.total_messages}
  `.trim();

  if (performance.length === 0) {
    return header + '\n\nNo performance data available.';
  }

  const perfList = performance.map(p => `
📊 ${p.agent_type} v${p.version} ${p.model_used ? `(${p.model_used})` : ''}
   Used: ${p.times_used}x | Avg Duration: ${p.avg_duration_seconds || 'N/A'}s | Avg Messages: ${p.avg_messages}
   Success Rate: ${p.success_rate_pct}%
  `.trim()).join('\n\n');

  const toolsHeader = '\n\n🔧 Top Tools:';
  const toolsList = tools.slice(0, 10).map(t =>
    `  - ${t.tool_name} by ${t.agent_type}: ${t.total_uses} uses in ${t.sessions_used_in} sessions`
  ).join('\n');

  return `${header}\n\nPerformance by Configuration:\n\n${perfList}${toolsHeader}\n${toolsList}`;
}

function formatAgentComparison(configs) {
  if (configs.length === 0) {
    return 'No agent configurations found for comparison.';
  }

  const agentType = configs[0].agent_type;

  const header = `
🔬 Agent Configuration Comparison: ${agentType}

Showing evolution across ${configs.length} version(s)
  `.trim();

  const configList = configs.map(c => {
    const improvement = c.performance_improvement_pct !== null
      ? `(${c.performance_improvement_pct > 0 ? '+' : ''}${c.performance_improvement_pct}% vs previous)`
      : '';

    return `
📊 Version ${c.version} ${c.model_used ? `- ${c.model_used}` : ''}
   Used: ${c.times_used}x
   Avg Duration: ${c.avg_duration_seconds || 'N/A'}s ${improvement}
   Avg Messages: ${c.avg_messages}
   Success Rate: ${c.success_rate_pct}%
    `.trim();
  }).join('\n\n');

  return `${header}\n\n${configList}`;
}

// Create MCP server
const server = new Server(
  {
    name: 'claude-memory',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'search_memory',
        description: 'Search through past conversations and context using semantic similarity. Finds relevant previous work, decisions, and solutions.',
        inputSchema: {
          type: 'object',
          properties: {
            query: {
              type: 'string',
              description: 'Search query (keywords or natural language question)',
            },
            project_path: {
              type: 'string',
              description: 'Optional: Filter to specific project path (e.g., "Code/claude-memory")',
            },
            limit: {
              type: 'number',
              description: 'Maximum number of results to return (default: 5)',
              default: 5,
            },
          },
          required: ['query'],
        },
      },
      {
        name: 'get_timeline',
        description: 'Get chronological timeline of recent context snapshots for a project. Shows what work was done and when.',
        inputSchema: {
          type: 'object',
          properties: {
            project_path: {
              type: 'string',
              description: 'Project path (e.g., "Code/claude-memory")',
            },
            limit: {
              type: 'number',
              description: 'Number of snapshots to retrieve (default: 10)',
              default: 10,
            },
          },
          required: ['project_path'],
        },
      },
      {
        name: 'get_snapshot',
        description: 'Retrieve detailed information about a specific context snapshot by ID.',
        inputSchema: {
          type: 'object',
          properties: {
            snapshot_id: {
              type: 'number',
              description: 'Snapshot ID to retrieve',
            },
          },
          required: ['snapshot_id'],
        },
      },
      {
        name: 'search_exact_phrase',
        description: 'Search for exact phrases in assistant (Claude) messages. Useful for finding specific things Claude said.',
        inputSchema: {
          type: 'object',
          properties: {
            phrase: {
              type: 'string',
              description: 'Exact phrase to search for',
            },
            project_path: {
              type: 'string',
              description: 'Optional: Filter to specific project path',
            },
            limit: {
              type: 'number',
              description: 'Maximum number of results (default: 10)',
              default: 10,
            },
          },
          required: ['phrase'],
        },
      },
      {
        name: 'get_quality_report',
        description: 'Get data quality report for snapshots. Shows quality scores based on metadata completeness.',
        inputSchema: {
          type: 'object',
          properties: {
            min_quality_score: {
              type: 'number',
              description: 'Filter by minimum quality score 0-10 (default: 0)',
              default: 0,
            },
            project_path: {
              type: 'string',
              description: 'Optional: Filter to specific project',
            },
            limit: {
              type: 'number',
              description: 'Maximum number of results (default: 20)',
              default: 20,
            },
          },
          required: [],
        },
      },
      {
        name: 'get_project_stats',
        description: 'Get comprehensive statistics for a project or all projects. Shows activity, messages, metadata richness.',
        inputSchema: {
          type: 'object',
          properties: {
            project_path: {
              type: 'string',
              description: 'Project path (omit for all projects)',
            },
          },
          required: [],
        },
      },
      {
        name: 'search_decisions',
        description: 'Search through all architectural decisions across snapshots.',
        inputSchema: {
          type: 'object',
          properties: {
            keyword: {
              type: 'string',
              description: 'Search keyword',
            },
            project_path: {
              type: 'string',
              description: 'Optional: Filter to specific project',
            },
            limit: {
              type: 'number',
              description: 'Maximum number of results (default: 10)',
              default: 10,
            },
          },
          required: ['keyword'],
        },
      },
      {
        name: 'analyze_bugs',
        description: 'Analyze bug patterns with automatic categorization (database, dependency, command, syntax, runtime, other).',
        inputSchema: {
          type: 'object',
          properties: {
            category: {
              type: 'string',
              description: 'Optional: Filter by category',
              enum: ['database', 'dependency', 'command', 'syntax', 'runtime', 'other'],
            },
            project_path: {
              type: 'string',
              description: 'Optional: Filter to specific project',
            },
            limit: {
              type: 'number',
              description: 'Maximum number of results (default: 20)',
              default: 20,
            },
          },
          required: [],
        },
      },
      {
        name: 'get_file_activity',
        description: 'Get file activity heatmap. Shows which files are most frequently mentioned/modified.',
        inputSchema: {
          type: 'object',
          properties: {
            file_type: {
              type: 'string',
              description: 'Optional: Filter by file type',
              enum: ['documentation', 'javascript', 'python', 'sql', 'config', 'json', 'other'],
            },
            min_mentions: {
              type: 'number',
              description: 'Minimum mention count (default: 1)',
              default: 1,
            },
            limit: {
              type: 'number',
              description: 'Maximum number of results (default: 20)',
              default: 20,
            },
          },
          required: [],
        },
      },
      {
        name: 'search_agent_work',
        description: 'Search through agent work using semantic similarity. Find what agents did, which tools they used, and what they discovered.',
        inputSchema: {
          type: 'object',
          properties: {
            query: {
              type: 'string',
              description: 'Search query (what the agent worked on or discovered)',
            },
            project_path: {
              type: 'string',
              description: 'Optional: Filter to specific project path',
            },
            limit: {
              type: 'number',
              description: 'Maximum number of results (default: 5)',
              default: 5,
            },
          },
          required: ['query'],
        },
      },
      {
        name: 'get_agent_analytics',
        description: 'Get comprehensive agent performance analytics. Shows agent usage patterns, configuration performance, and tool usage statistics.',
        inputSchema: {
          type: 'object',
          properties: {
            agent_type: {
              type: 'string',
              description: 'Optional: Filter to specific agent type (e.g., "Explore", "Plan", "general-purpose")',
            },
            project_path: {
              type: 'string',
              description: 'Optional: Filter to specific project',
            },
          },
          required: [],
        },
      },
      {
        name: 'compare_agent_configs',
        description: 'Compare different versions of agent configurations. Shows performance evolution and improvements across versions.',
        inputSchema: {
          type: 'object',
          properties: {
            agent_type: {
              type: 'string',
              description: 'Agent type to analyze (e.g., "Explore", "Plan")',
            },
            versions: {
              type: 'array',
              items: { type: 'number' },
              description: 'Optional: Specific versions to compare (default: all versions)',
            },
          },
          required: ['agent_type'],
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'search_memory': {
        const results = await searchMemory(
          args.query,
          args.project_path || null,
          args.limit || 5
        );

        if (results.length === 0) {
          return {
            content: [
              {
                type: 'text',
                text: `No memories found matching: "${args.query}"`,
              },
            ],
          };
        }

        const formatted = results.map(formatSnapshot).join('\n\n---\n\n');

        return {
          content: [
            {
              type: 'text',
              text: `Found ${results.length} relevant memories:\n\n${formatted}`,
            },
          ],
        };
      }

      case 'get_timeline': {
        const snapshots = await getTimeline(args.project_path, args.limit || 10);

        if (snapshots.length === 0) {
          return {
            content: [
              {
                type: 'text',
                text: `No context history found for project: ${args.project_path}`,
              },
            ],
          };
        }

        const timeline = snapshots.map((s, idx) =>
          `${idx + 1}. [#${s.id}] ${new Date(s.timestamp).toLocaleString()} - ${s.tags?.join(', ') || 'no tags'}\n   ${s.summary.split('\n')[0].substring(0, 100)}...`
        ).join('\n\n');

        return {
          content: [
            {
              type: 'text',
              text: `📅 Timeline for ${args.project_path} (${snapshots.length} snapshots):\n\n${timeline}`,
            },
          ],
        };
      }

      case 'get_snapshot': {
        const snapshot = await getSnapshot(args.snapshot_id);

        return {
          content: [
            {
              type: 'text',
              text: formatSnapshot(snapshot),
            },
          ],
        };
      }

      case 'search_exact_phrase': {
        if (!args.phrase) {
          return {
            content: [
              {
                type: 'text',
                text: 'Error: phrase parameter is required',
              },
            ],
            isError: true,
          };
        }

        const results = await searchExactPhrase(
          args.phrase,
          args.project_path || null,
          args.limit || 10
        );

        return {
          content: [
            {
              type: 'text',
              text: formatExactPhraseResults(results, args.phrase),
            },
          ],
        };
      }

      case 'get_quality_report': {
        const data = await getQualityReport(
          args.min_quality_score || 0,
          args.project_path || null,
          args.limit || 20
        );

        return {
          content: [
            {
              type: 'text',
              text: formatQualityReport(data),
            },
          ],
        };
      }

      case 'get_project_stats': {
        const data = await getProjectStats(args.project_path || null);

        if (!data) {
          return {
            content: [
              {
                type: 'text',
                text: `No project data found for: ${args.project_path}`,
              },
            ],
            isError: true,
          };
        }

        return {
          content: [
            {
              type: 'text',
              text: formatProjectStats(data),
            },
          ],
        };
      }

      case 'search_decisions': {
        if (!args.keyword) {
          return {
            content: [
              {
                type: 'text',
                text: 'Error: keyword parameter is required',
              },
            ],
            isError: true,
          };
        }

        const results = await searchDecisions(
          args.keyword,
          args.project_path || null,
          args.limit || 10
        );

        return {
          content: [
            {
              type: 'text',
              text: formatDecisions(results, args.keyword),
            },
          ],
        };
      }

      case 'analyze_bugs': {
        const validCategories = ['database', 'dependency', 'command', 'syntax', 'runtime', 'other'];

        if (args.category && !validCategories.includes(args.category)) {
          return {
            content: [
              {
                type: 'text',
                text: `Error: Invalid category. Valid categories: ${validCategories.join(', ')}`,
              },
            ],
            isError: true,
          };
        }

        const data = await analyzeBugs(
          args.category || null,
          args.project_path || null,
          args.limit || 20
        );

        return {
          content: [
            {
              type: 'text',
              text: formatBugAnalysis(data),
            },
          ],
        };
      }

      case 'get_file_activity': {
        const validFileTypes = ['documentation', 'javascript', 'python', 'sql', 'config', 'json', 'other'];

        if (args.file_type && !validFileTypes.includes(args.file_type)) {
          return {
            content: [
              {
                type: 'text',
                text: `Error: Invalid file_type. Valid types: ${validFileTypes.join(', ')}`,
              },
            ],
            isError: true,
          };
        }

        const data = await getFileActivity(
          args.file_type || null,
          args.min_mentions || 1,
          args.limit || 20
        );

        return {
          content: [
            {
              type: 'text',
              text: formatFileActivity(data),
            },
          ],
        };
      }

      case 'search_agent_work': {
        if (!args.query) {
          return {
            content: [
              {
                type: 'text',
                text: 'Error: query parameter is required',
              },
            ],
            isError: true,
          };
        }

        const results = await searchAgentWork(
          args.query,
          args.project_path || null,
          args.limit || 5
        );

        if (results.length === 0) {
          return {
            content: [
              {
                type: 'text',
                text: `No agent work found matching: "${args.query}"`,
              },
            ],
          };
        }

        const formatted = results.map(formatAgentWork).join('\n\n---\n\n');

        return {
          content: [
            {
              type: 'text',
              text: `Found ${results.length} agent(s) matching "${args.query}":\n\n${formatted}`,
            },
          ],
        };
      }

      case 'get_agent_analytics': {
        const data = await getAgentAnalytics(
          args.agent_type || null,
          args.project_path || null
        );

        return {
          content: [
            {
              type: 'text',
              text: formatAgentAnalytics(data),
            },
          ],
        };
      }

      case 'compare_agent_configs': {
        if (!args.agent_type) {
          return {
            content: [
              {
                type: 'text',
                text: 'Error: agent_type parameter is required',
              },
            ],
            isError: true,
          };
        }

        const results = await compareAgentConfigs(
          args.agent_type,
          args.versions || null
        );

        if (results.length === 0) {
          return {
            content: [
              {
                type: 'text',
                text: `No configurations found for agent type: ${args.agent_type}`,
              },
            ],
          };
        }

        return {
          content: [
            {
              type: 'text',
              text: formatAgentComparison(results),
            },
          ],
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error('========================================');
  console.error('🧠 Claude Memory MCP Server');
  console.error('========================================');
  console.error('📍 Database:', process.env.DATABASE_URL?.replace(/:[^:]*@/, ':****@'));
  console.error('');
  console.error('🔧 Available Tools (12):');
  console.error('   Core Tools:');
  console.error('   - search_memory (semantic similarity)');
  console.error('   - get_timeline (chronological view)');
  console.error('   - get_snapshot (detailed snapshot)');
  console.error('');
  console.error('   Analytical Tools:');
  console.error('   - search_exact_phrase (exact matching)');
  console.error('   - get_quality_report (data quality)');
  console.error('   - get_project_stats (project metrics)');
  console.error('   - search_decisions (decision tracking)');
  console.error('   - analyze_bugs (bug patterns)');
  console.error('   - get_file_activity (file heatmap)');
  console.error('');
  console.error('   Agent Memory Tools (Phase 5):');
  console.error('   - search_agent_work (find agent activities)');
  console.error('   - get_agent_analytics (agent performance)');
  console.error('   - compare_agent_configs (config comparison)');
  console.error('========================================');
  console.error('✅ Ready for requests');
  console.error('========================================');
}

main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
