/**
 * Summary Agent — Post-Compaction Vault Writer
 *
 * An agentic loop (Claude Haiku + tools) that runs after every compaction.
 * Reads the auto-generated summary + metadata, then writes structured notes
 * to the Obsidian vault: session logs, decisions, open questions, learnings.
 *
 * Runs fire-and-forget from capture.js — does NOT block the capture pipeline.
 */

const Anthropic = require('@anthropic-ai/sdk');
const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

const VAULT_ROOT = process.env.VAULT_ROOT || '/vault';
const MAX_AGENT_ITERATIONS = 15;

// Separate pool for agent (avoids contention with capture pool)
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 3,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000
});

// ============================================================================
// Tool implementations
// ============================================================================

function resolveVaultPath(filePath) {
  // Accept absolute /vault/... paths or relative paths
  if (filePath.startsWith('/vault/')) return filePath;
  if (filePath.startsWith('/')) return filePath; // already absolute
  return path.join(VAULT_ROOT, filePath);
}

function toolReadObsidianFile(filePath) {
  const resolved = resolveVaultPath(filePath);
  if (!resolved.startsWith(VAULT_ROOT)) {
    return { error: `Path must be within vault: ${VAULT_ROOT}` };
  }
  if (!fs.existsSync(resolved)) {
    return { error: `File not found: ${filePath}`, exists: false };
  }
  try {
    const content = fs.readFileSync(resolved, 'utf8');
    return { content, path: resolved };
  } catch (err) {
    return { error: err.message };
  }
}

function toolWriteObsidianFile(filePath, content, mode = 'append') {
  const resolved = resolveVaultPath(filePath);
  if (!resolved.startsWith(VAULT_ROOT)) {
    return { error: `Path must be within vault: ${VAULT_ROOT}` };
  }
  try {
    fs.mkdirSync(path.dirname(resolved), { recursive: true });
    if (mode === 'append' && fs.existsSync(resolved)) {
      fs.appendFileSync(resolved, '\n' + content, 'utf8');
    } else {
      fs.writeFileSync(resolved, content, 'utf8');
    }
    return { success: true, path: resolved, mode };
  } catch (err) {
    return { error: err.message };
  }
}

function toolListObsidianFiles(directory) {
  const resolved = resolveVaultPath(directory);
  if (!resolved.startsWith(VAULT_ROOT)) {
    return { error: `Path must be within vault: ${VAULT_ROOT}` };
  }
  if (!fs.existsSync(resolved)) {
    return { error: `Directory not found: ${directory}`, exists: false };
  }
  try {
    const entries = fs.readdirSync(resolved, { withFileTypes: true });
    return {
      files: entries.filter(e => e.isFile()).map(e => e.name),
      directories: entries.filter(e => e.isDirectory()).map(e => e.name),
      path: resolved
    };
  } catch (err) {
    return { error: err.message };
  }
}

async function toolSearchMemory(query, limit = 5) {
  const client = await pool.connect();
  try {
    const result = await client.query(`
      SELECT id, project_path, session_id, compaction_index, timestamp,
             LEFT(summary, 500) AS summary_preview, tags
      FROM context_snapshots
      WHERE summary ILIKE $1 OR $1 = ANY(tags)
      ORDER BY timestamp DESC
      LIMIT $2
    `, [`%${query}%`, limit]);
    return { results: result.rows };
  } catch (err) {
    return { error: err.message };
  } finally {
    client.release();
  }
}

async function toolGetSnapshotDetails(snapshotId) {
  const client = await pool.connect();
  try {
    const result = await client.query(`
      SELECT id, project_path, session_id, compaction_index, message_start_index,
             context_window_size, timestamp, summary, tags, mentioned_files,
             key_decisions, bugs_fixed, trigger_event
      FROM context_snapshots WHERE id = $1
    `, [snapshotId]);
    if (!result.rows.length) return { error: `Snapshot ${snapshotId} not found` };
    return result.rows[0];
  } catch (err) {
    return { error: err.message };
  } finally {
    client.release();
  }
}

// ============================================================================
// Tool definitions for Claude
// ============================================================================

const TOOLS = [
  {
    name: 'read_obsidian_file',
    description: 'Read a file from the Obsidian vault. Use paths like /vault/Claude/Session-Logs/2026-03-22.md or relative paths like Claude/Session-Logs/2026-03-22.md',
    input_schema: {
      type: 'object',
      properties: {
        path: { type: 'string', description: 'Path to the vault file' }
      },
      required: ['path']
    }
  },
  {
    name: 'write_obsidian_file',
    description: 'Write or append content to a vault file. Use mode="append" to add to existing files (session logs, decisions logs). Use mode="write" to create new files.',
    input_schema: {
      type: 'object',
      properties: {
        path: { type: 'string', description: 'Path to the vault file' },
        content: { type: 'string', description: 'Content to write' },
        mode: { type: 'string', enum: ['append', 'write'], description: 'append adds to existing file, write creates/overwrites' }
      },
      required: ['path', 'content', 'mode']
    }
  },
  {
    name: 'list_obsidian_files',
    description: 'List files and directories in a vault folder',
    input_schema: {
      type: 'object',
      properties: {
        directory: { type: 'string', description: 'Vault directory path to list' }
      },
      required: ['directory']
    }
  },
  {
    name: 'search_memory',
    description: 'Search past session snapshots by keyword or topic. Returns matching snapshots with summaries.',
    input_schema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Search term or topic' },
        limit: { type: 'number', description: 'Max results (default 5)' }
      },
      required: ['query']
    }
  },
  {
    name: 'get_snapshot_details',
    description: 'Get full details for a specific snapshot by ID, including summary, tags, decisions, and bugs.',
    input_schema: {
      type: 'object',
      properties: {
        snapshot_id: { type: 'number', description: 'Snapshot ID' }
      },
      required: ['snapshot_id']
    }
  }
];

// ============================================================================
// Tool dispatcher
// ============================================================================

async function dispatchTool(name, input) {
  switch (name) {
    case 'read_obsidian_file':
      return toolReadObsidianFile(input.path);
    case 'write_obsidian_file':
      return toolWriteObsidianFile(input.path, input.content, input.mode || 'append');
    case 'list_obsidian_files':
      return toolListObsidianFiles(input.directory);
    case 'search_memory':
      return await toolSearchMemory(input.query, input.limit || 5);
    case 'get_snapshot_details':
      return await toolGetSnapshotDetails(input.snapshot_id);
    default:
      return { error: `Unknown tool: ${name}` };
  }
}

// ============================================================================
// Agent system prompt
// ============================================================================

const SYSTEM_PROMPT = `You are a session analysis agent for a software development memory system. After each compaction event in a Claude Code session, you analyze the work done and write structured notes to an Obsidian vault.

## Your Job

1. **Always write a session log entry** to \`/vault/Claude/Session-Logs/YYYY-MM-DD.md\` (today's date). If the file already has an entry for this session/compaction, append a new section rather than duplicating.

2. **Write to project files only if relevant content was found:**
   - Architecture decisions → \`/vault/Projects/_Active/<ProjectName>/Decisions Log.md\` (append)
   - Unresolved issues → \`/vault/Projects/_Active/<ProjectName>/Open Questions.md\` (append)
   - Errors and patterns → \`/vault/Knowledge/Learnings Log.md\` (append)

3. **Keep entries concise and actionable.** No padding. Each entry should be useful to a developer reading it 3 months later.

## Vault Conventions

- YAML frontmatter on new files: tags, created, status
- Headings for structure (not bold text)
- Wikilinks \`[[Note Name]]\` for internal references
- Callouts \`> [!note]\` for highlighted info
- Nested tags: \`#project/active\`, \`#status/draft\`, \`#type/log\`
- Always include a back-reference to the snapshot ID: \`(snapshot #N)\`

## Session Log Format

Append a section like:

\`\`\`
## Compaction #N — HH:MM
*Project: <path> | Messages: M–N | Tags: [...]*

<2-4 sentence summary of what was accomplished>

### Decisions
- <decision> (snapshot #N)

### Issues / Open Questions
- <unresolved issue>

### Errors / Learnings
- **Error:** <what went wrong> → **Fix:** <resolution>
\`\`\`

Only include sections that have content. Skip empty sections.

## Project Detection

Derive the project name from the project_path. For example:
- \`/home/hp-admin/code/claude-memory/mcp-server\` → Claude Memory
- \`/home/hp-admin/data/code/NLQ\` → NLQ
- \`/home/hp-admin/code/claude-vault\` → Claude Vault

Projects are organized into three subfolders by lifecycle status:
- \`Projects/_Active/\` — current work (check here first)
- \`Projects/_Parked/\` — paused projects
- \`Projects/_Archive/\` — completed or abandoned

Check \`Projects/_Active/\` first for a matching project folder. If not found, check \`_Parked/\` then \`_Archive/\`. Always write to the folder where the project actually lives.

## Efficiency

Start by listing \`/vault/Projects/_Active/\` to know what active projects exist, then read the session log file if it already exists. Do your writes in 2-3 tool calls maximum. Do not over-read.`;

// ============================================================================
// Main agent runner
// ============================================================================

async function runSummaryAgent({ snapshot_id, project_path, session_id, compaction_index,
                                  message_start_index, context_window_size, summary, tags,
                                  mentioned_files, key_decisions, bugs_fixed }) {
  const startTime = Date.now();
  console.log(`\n🤖 [Agent] Starting vault writer for snapshot #${snapshot_id} (compaction #${compaction_index})`);

  if (!process.env.ANTHROPIC_API_KEY) {
    console.log('⚠️  [Agent] ANTHROPIC_API_KEY not set — skipping vault agent');
    return;
  }

  const client = new Anthropic();
  const today = new Date().toISOString().slice(0, 10);
  const deltaCount = context_window_size - message_start_index;

  const userMessage = `Analyze this compaction and write notes to the vault.

**Snapshot ID:** ${snapshot_id}
**Session ID:** ${session_id}
**Project Path:** ${project_path}
**Compaction:** #${compaction_index}
**Messages:** ${message_start_index}–${context_window_size} (${deltaCount} in this delta)
**Date:** ${today}
**Tags:** ${(tags || []).join(', ') || 'none'}
**Mentioned Files:** ${(mentioned_files || []).slice(0, 10).join(', ') || 'none'}
**Key Decisions:** ${(key_decisions || []).slice(0, 5).join('; ') || 'none'}
**Bugs Fixed:** ${(bugs_fixed || []).slice(0, 5).join('; ') || 'none'}

**Auto-Generated Summary:**
${summary}

Write the session log entry and any relevant project notes. Check what projects exist in the vault first.`;

  const messages = [{ role: 'user', content: userMessage }];
  let iterations = 0;
  let filesWritten = [];

  try {
    while (iterations < MAX_AGENT_ITERATIONS) {
      iterations++;

      const response = await client.messages.create({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 2048,
        system: SYSTEM_PROMPT,
        tools: TOOLS,
        messages
      });

      // Add assistant response to history
      messages.push({ role: 'assistant', content: response.content });

      if (response.stop_reason === 'end_turn') {
        console.log(`✅ [Agent] Done after ${iterations} iterations. Files written: ${filesWritten.join(', ') || 'none'}`);
        break;
      }

      if (response.stop_reason !== 'tool_use') {
        console.log(`⚠️  [Agent] Unexpected stop_reason: ${response.stop_reason}`);
        break;
      }

      // Process tool calls
      const toolResults = [];
      for (const block of response.content) {
        if (block.type !== 'tool_use') continue;

        console.log(`🔧 [Agent] Tool: ${block.name}(${JSON.stringify(block.input).slice(0, 120)})`);
        const result = await dispatchTool(block.name, block.input);

        if (block.name === 'write_obsidian_file' && result.success) {
          filesWritten.push(result.path.replace(VAULT_ROOT + '/', ''));
        }

        toolResults.push({
          type: 'tool_result',
          tool_use_id: block.id,
          content: JSON.stringify(result)
        });
      }

      messages.push({ role: 'user', content: toolResults });
    }

    if (iterations >= MAX_AGENT_ITERATIONS) {
      console.log(`⚠️  [Agent] Hit max iterations (${MAX_AGENT_ITERATIONS})`);
    }

  } catch (err) {
    console.error(`❌ [Agent] Failed: ${err.message}`);
  }

  const duration = ((Date.now() - startTime) / 1000).toFixed(1);
  console.log(`⏱️  [Agent] Vault writer completed in ${duration}s\n`);
}

module.exports = { runSummaryAgent };
