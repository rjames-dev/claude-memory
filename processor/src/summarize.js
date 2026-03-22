/**
 * Summarization — Claude API (primary) with Ollama fallback
 * Delta-aware: each compaction event summarizes only new messages since the last.
 */

const axios = require('axios');
const { getLastSnapshotForProject, getLastSnapshotForSession } = require('./storage');

/**
 * Enhanced system message for Phase 6C session-aware summarization
 * Explains the AI's role in the claude-memory system
 */
const SYSTEM_MESSAGE = `You are the summarization component of the claude-memory system,
a persistent context memory system for Claude Code that enables long-term project memory
across development sessions.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR ROLE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Generate searchable summaries of development sessions
2. Focus on technical decisions, files changed, and problems solved
3. Maintain session continuity by referencing previous work
4. Use structured format for consistent search and retrieval
5. Be factual and specific (file names, functions, line numbers)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GUIDELINES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ DO:
- Mention specific file names, function names, line numbers
- Extract key technical decisions (WHY something was done, not just WHAT)
- Identify patterns across messages (e.g., "fixed 5 SQL injection vulnerabilities")
- Note unresolved issues or next steps
- Connect this session to previous work when relevant
- Use the metadata provided (tags, files, decisions, bugs)
- Be concise but technically precise

✗ DON'T:
- Write vague summaries ("worked on the code", "made improvements")
- Ignore the metadata provided
- Summarize tangential discussions that didn't result in work
- Miss the main accomplishments of the session
- Forget to note what comes next

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT REQUIREMENTS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Format: Use the structured template provided below
Length: 200-400 words (prioritize technical specificity over prose)
Tone: Technical, factual, searchable
Structure: Follow template exactly for consistency across all summaries
`;

/**
 * Structured output template for Phase 6C summaries
 * Ensures consistent, searchable format
 */
const STRUCTURED_OUTPUT_TEMPLATE = `
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRED OUTPUT FORMAT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generate your summary using this EXACT structure:

## Primary Goal
[One sentence: What was the main objective of this session?]

## Work Completed

### Files Modified
[List key files and what changed - be specific with file paths]

### Features Added
[New capabilities or functionality - what can users do now that they couldn't before?]

### Bugs Fixed
[Problems solved - what was broken and how was it fixed?]

## Technical Decisions
[Key architectural or implementation decisions made and WHY]

## Session Metrics
- Messages: [count]
- Files touched: [count]
- Duration: [if inferable from timestamps]
- Commits: [if any git commits were made]

## Continuity
[How this session relates to previous work AND what's next]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Now generate the summary following this structure exactly:
`;

/**
 * Generate summary of conversation using OpenWebUI's model
 * Phase 6C: Now accepts metadata and context for session-aware summarization
 *
 * @param {Object} conversation - Conversation object with messages
 * @param {Object} metadata - Extracted metadata (tags, files, decisions, bugs)
 * @param {Object} context - Session context (project_path, session_id, trigger)
 */
async function summarize(conversation, metadata = {}, context = {}) {
  try {
    const useAI = process.env.USE_AI_SUMMARIES !== 'false';
    if (!useAI) return generateExtractiveSummary(conversation);

    // Prefer Claude API when key is available (higher quality, delta-aware)
    if (process.env.ANTHROPIC_API_KEY) {
      try {
        return await summarizeViaClaude(conversation, metadata, context);
      } catch (claudeError) {
        console.warn('⚠️  Claude API summarization failed, falling back to Ollama:', claudeError.message);
      }
    }

    // Fallback: Ollama
    try {
      return await summarizeViaOllama(conversation, metadata, context);
    } catch (ollamaError) {
      console.warn('⚠️  Ollama summarization failed, falling back to extractive:', ollamaError.message);
    }

    return generateExtractiveSummary(conversation);

  } catch (error) {
    console.error('Summarization error:', error);
    return generateExtractiveSummary(conversation);
  }
}

/**
 * Summarize via Claude API — delta-aware, high quality.
 * Only sees the delta messages (new since last compaction). Includes previous
 * compaction summary as context so the summary is self-contained.
 */
async function summarizeViaClaude(conversation, metadata, context) {
  const Anthropic = require('@anthropic-ai/sdk');
  const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

  const { project_path, session_id, trigger, message_start_index = 0, compaction_index = 1 } = context;
  const messages = conversation.messages || [];

  // Get previous compaction summary for within-session continuity
  let prevSummary = null;
  if (session_id && compaction_index > 1) {
    try {
      const prev = await getLastSnapshotForSession(session_id);
      if (prev) prevSummary = prev.summary;
    } catch (e) {
      console.warn('⚠️  Could not fetch previous compaction summary:', e.message);
    }
  }

  // Format delta messages (no truncation — Claude handles full context)
  const conversationText = messages.map((msg, idx) => {
    const role = (msg.role || 'unknown').toUpperCase();
    const content = msg.content || '';
    return `[MSG ${message_start_index + idx + 1}] ${role}:\n${content}`;
  }).join('\n\n');

  const metadataBlock = buildMetadataContext(
    { ...metadata, messageCount: messages.length },
    context
  );

  const continuityBlock = prevSummary
    ? `## Previous Compaction Summary (compaction ${compaction_index - 1}):\n${prevSummary.slice(0, 800)}${prevSummary.length > 800 ? '\n...[truncated]' : ''}`
    : compaction_index === 1
      ? '## Session Context: This is the first compaction of this session.'
      : '## Session Context: No previous compaction summary available.';

  const prompt = `You are the summarization engine for claude-memory, a persistent memory system for Claude Code sessions.

${metadataBlock}

## Compaction Context
- Session ID: ${session_id || 'N/A'}
- This is compaction #${compaction_index} of this session
- Messages in this delta: ${messages.length} (messages ${message_start_index + 1}–${message_start_index + messages.length})
- Trigger: ${trigger}

${continuityBlock}

## Your Task
Summarize ONLY the work in this compaction's messages (shown below). Do not re-summarize prior compactions.
Write 300–600 words. Be technically precise — file names, function names, decisions and their rationale.

${STRUCTURED_OUTPUT_TEMPLATE}

## Conversation (this compaction only):

${conversationText}`;

  console.log(`🤖 Summarizing via Claude API (compaction #${compaction_index}, ${messages.length} delta messages)...`);

  const response = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 2048,
    messages: [{ role: 'user', content: prompt }]
  });

  return response.content[0].text.trim();
}

/**
 * Intelligently select messages for summarization
 * Prioritizes: beginning (context), middle (work), end (outcome)
 * Phase 6C enhancement to fix arbitrary truncation
 *
 * @param {Array} messages - All messages in conversation
 * @param {Object} options - Selection options
 * @returns {Object} Selected messages with metadata
 */
function selectMessagesForSummary(messages, options = {}) {
  const {
    firstN = 20,   // Initial context
    middleN = 30,  // Sample from middle
    lastN = 50     // Recent work (most important)
  } = options;

  const totalMessages = messages.length;

  // If conversation is small enough, use all messages
  if (totalMessages <= firstN + lastN + middleN) {
    return {
      messages,
      strategy: 'full',
      totalMessages,
      selectedMessages: totalMessages
    };
  }

  // Take first N messages
  const first = messages.slice(0, firstN);

  // Take last N messages
  const last = messages.slice(-lastN);

  // Sample evenly from middle
  const middleStart = firstN;
  const middleEnd = totalMessages - lastN;
  const middleRange = middleEnd - middleStart;
  const middleStep = Math.floor(middleRange / middleN);

  const middle = [];
  for (let i = middleStart; i < middleEnd; i += middleStep) {
    middle.push(messages[i]);
    if (middle.length >= middleN) break;
  }

  const selected = [...first, ...middle, ...last];

  return {
    messages: selected,
    strategy: 'sampled',
    totalMessages,
    selectedMessages: selected.length,
    coverage: {
      first: firstN,
      middle: middle.length,
      last: lastN
    }
  };
}

/**
 * Build metadata context for summarization prompt
 * Uses already-extracted metadata to guide AI
 * Phase 6C enhancement
 *
 * @param {Object} metadata - Extracted metadata
 * @param {Object} context - Session context
 * @returns {string} Formatted metadata context
 */
function buildMetadataContext(metadata, context) {
  const { project_path, session_id, trigger } = context;

  return `
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 SESSION METADATA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Project Path: ${project_path}
Session ID: ${session_id || 'N/A'}
Trigger: ${trigger} (${trigger === 'auto' ? 'automatic compact' : 'manual save'})
Total Messages: ${metadata.messageCount || 'N/A'}

Identified Topics (${metadata.tags?.length || 0} tags):
${metadata.tags?.join(', ') || 'None'}

Files Modified (${metadata.files?.length || 0} total, showing first 15):
${metadata.files?.slice(0, 15).join(', ') || 'None'}

Architectural Decisions Documented: ${metadata.decisions?.length || 0}
${metadata.decisions?.map((d, i) => `  ${i + 1}. ${d.slice(0, 100)}...`).join('\n') || '  None'}

Bugs/Issues Addressed: ${metadata.bugs?.length || 0}
${metadata.bugs?.map((b, i) => `  ${i + 1}. ${b.slice(0, 100)}...`).join('\n') || '  None'}

Git Context:
- Branch: ${metadata.gitBranch || 'N/A'}
- Commit: ${metadata.gitHash || 'N/A'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`;
}

/**
 * Build session boundary context from previous snapshot
 * Provides continuity across sessions
 * Phase 6C enhancement
 *
 * @param {Object|null} lastSnapshot - Previous snapshot or null
 * @returns {string} Formatted session boundary context
 */
function buildSessionBoundary(lastSnapshot) {
  if (!lastSnapshot) {
    return '📌 SESSION CONTEXT: This is the first session for this project.\n';
  }

  return `📌 SESSION CONTEXT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Previous Session: #${lastSnapshot.id}
Previous Timestamp: ${lastSnapshot.timestamp}
Previous Summary: ${lastSnapshot.summary?.slice(0, 300) || 'N/A'}...
Previous Topics: ${lastSnapshot.tags?.join(', ') || 'None'}

This session continues from where that session left off.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`;
}

/**
 * Generate simple extractive summary (no API needed)
 * Extracts key sentences from the conversation
 */
function generateExtractiveSummary(conversation) {
  const messages = conversation.messages || [];

  // Take first and last few messages as summary
  const firstMessages = messages.slice(0, 3);
  const lastMessages = messages.slice(-3);

  const summary = [];

  // Add first user message (usually the request)
  const firstUser = firstMessages.find(m => m.role === 'user');
  if (firstUser) {
    summary.push(`Request: ${firstUser.content?.slice(0, 200) || 'N/A'}`);
  }

  // Add last assistant message (usually the conclusion)
  const lastAssistant = [...messages].reverse().find(m => m.role === 'assistant');
  if (lastAssistant) {
    summary.push(`Outcome: ${lastAssistant.content?.slice(0, 300) || 'N/A'}`);
  }

  // Add message count
  summary.push(`Total messages: ${messages.length}`);

  return summary.join('\n\n');
}

/**
 * Call Ollama API for AI summarization
 * Phase 6C: Complete rewrite with session-aware, metadata-driven approach
 *
 * @param {Object} conversation - Conversation object
 * @param {Object} metadata - Extracted metadata
 * @param {Object} context - Session context
 */
async function summarizeViaOllama(conversation, metadata, context) {
  const ollamaUrl = process.env.OLLAMA_URL || 'http://ollama:11434';
  const model = process.env.SUMMARY_MODEL || 'llama3.2:latest';

  // 1. Get session boundary — prefer within-session continuity over project-level
  const { project_path, session_id, compaction_index = 1 } = context;
  let lastSnapshot = null;
  try {
    if (session_id && compaction_index > 1) {
      lastSnapshot = await getLastSnapshotForSession(session_id);
    }
    if (!lastSnapshot) {
      lastSnapshot = await getLastSnapshotForProject(project_path);
    }
  } catch (error) {
    console.warn('⚠️  Could not get last snapshot:', error.message);
  }
  const sessionBoundary = buildSessionBoundary(lastSnapshot);

  // 2. Select messages intelligently (not arbitrary truncation)
  const selection = selectMessagesForSummary(conversation.messages);
  console.log(`📊 Message selection: ${selection.strategy} - ${selection.selectedMessages}/${selection.totalMessages} messages`);

  // 3. Format selected messages (reduced to 500 chars for Ollama context limits)
  const conversationText = selection.messages
    .map((msg, idx) => {
      const role = msg.role || 'unknown';
      const content = msg.content || '';
      // Limit each message to 500 chars to fit within Ollama's 4096 token context
      const truncated = content.length > 500
        ? content.slice(0, 500) + '...[truncated]'
        : content;
      return `[Message ${idx + 1}] ${role}: ${truncated}`;
    })
    .join('\n\n');

  // 4. Build metadata context
  const metadataContext = buildMetadataContext(
    { ...metadata, messageCount: conversation.messages.length },
    context
  );

  // 5. Construct comprehensive prompt
  const prompt = `${SYSTEM_MESSAGE}

${metadataContext}

${sessionBoundary}

${STRUCTURED_OUTPUT_TEMPLATE}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONVERSATION (${selection.selectedMessages} of ${selection.totalMessages} messages):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

${conversationText}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generate the structured summary now following the template exactly:`;

  // 6. Call Ollama with enhanced prompt
  try {
    const response = await axios.post(
      `${ollamaUrl}/api/generate`,
      {
        model: model,
        prompt: prompt,
        stream: false,
        options: {
          temperature: 0.3,  // Lower = more factual
          num_predict: 600,  // ~400 words (increased from 400 for structured format)
          top_p: 0.9,
          top_k: 40
        }
      },
      {
        timeout: 300000,  // 5 minutes (increased for larger prompts)
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );

    if (response.data && response.data.response) {
      return response.data.response.trim();
    }

    throw new Error('Invalid response from Ollama');

  } catch (error) {
    console.error('❌ Ollama summarization failed:', error.message);
    throw new Error(`Ollama summarization failed: ${error.message}`);
  }
}

module.exports = {
  summarize,
  summarizeViaClaude,
  generateExtractiveSummary,
  selectMessagesForSummary,
  buildMetadataContext,
  buildSessionBoundary
};
