/**
 * Context Capture Logic
 * Orchestrates the entire capture pipeline
 */

const fs = require('fs').promises;
const path = require('path');
const { extractMetadata } = require('./metadata');
const { summarize } = require('./summarize');
const { generateEmbedding } = require('./embed');
const { storeSnapshot } = require('./storage');

/**
 * Main capture function - orchestrates the entire pipeline
 * IMPORTANT: This runs out-of-band and consumes ZERO tokens from main Claude session
 */
async function captureContext({ project_path, trigger, conversation_data, session_id, transcript_path }) {
  const startTime = Date.now();

  console.log(`\n=== Starting Context Capture ===`);
  console.log(`Project: ${project_path}`);
  console.log(`Trigger: ${trigger}`);
  console.log(`Session: ${session_id || 'N/A'}`);
  console.log(`Transcript: ${transcript_path || 'N/A'}`);

  try {
    // Step 1: Get conversation data (from parameter or filesystem)
    let conversation;
    if (conversation_data) {
      console.log('🔄 [1/5] Parsing transcript...');
      conversation = conversation_data;
    } else {
      console.log('🔄 [1/5] Reading conversation from filesystem...');
      conversation = await readConversation(project_path);
    }

    if (!conversation || !conversation.messages || conversation.messages.length === 0) {
      throw new Error('No conversation messages found');
    }

    console.log(`✅ [1/5] Loaded ${conversation.messages.length} messages`);

    // Step 2: Extract metadata (files, tags, git state)
    console.log('🔄 [2/5] Extracting metadata...');
    const metadata = await extractMetadata(conversation, project_path);
    console.log(`✅ [2/5] Extracted: ${metadata.tags?.length || 0} tags, ${metadata.files?.length || 0} files`);

    // Step 3: Generate session-aware summary with metadata and context
    console.log('🔄 [3/5] Generating session-aware summary (may take 30-60 seconds)...');
    const summaryContext = {
      project_path,
      session_id,
      trigger
    };
    const summary = await summarize(conversation, metadata, summaryContext);
    console.log(`✅ [3/5] Summary generated (${summary.length} chars)`);

    // Step 4: Generate embedding using OpenWebUI
    console.log('🔄 [4/5] Generating embeddings (may take 1-2 minutes for large sessions)...');
    console.log('💡 Tip: This is normal for verbose sessions - please wait...');
    const embedding = await generateEmbedding(summary);
    console.log(`✅ [4/5] Embedding generated (${embedding.length} dimensions)`);

    // Step 5: Store in PostgreSQL (with upsert logic)
    console.log('🔄 [5/5] Storing snapshot in database...');
    const snapshot = await storeSnapshot({
      project_path,
      session_id,
      transcript_path,
      raw_context: conversation,
      summary,
      embedding,
      tags: metadata.tags || [],
      mentioned_files: metadata.files || [],
      key_decisions: metadata.decisions || [],
      bugs_fixed: metadata.bugs || [],
      git_commit_hash: metadata.gitHash,
      git_branch: metadata.gitBranch,
      trigger_event: trigger,
      context_window_size: conversation.messages.length,
      storage_size_bytes: JSON.stringify(conversation).length
    });

    const duration = Date.now() - startTime;
    console.log(`✅ [5/5] Snapshot stored successfully!`);
    console.log(`📋 Snapshot ID: ${snapshot.id}`);
    console.log(`📊 Messages: ${conversation.messages.length} | Tags: ${metadata.tags?.length || 0} | Files: ${metadata.files?.length || 0}`);
    console.log(`⏱️  Total time: ${(duration / 1000).toFixed(1)}s`);
    console.log(`=== Capture Complete ===\n`);

    return snapshot;

  } catch (error) {
    const duration = Date.now() - startTime;
    console.error(`❌ Capture failed after ${duration}ms:`, error.message);
    throw error;
  }
}

/**
 * Read conversation from filesystem
 * This is where we need to find Claude Code's conversation cache
 *
 * NOTE: Claude Code's conversation location varies by setup
 * For now, we'll accept it as a parameter and implement filesystem reading later
 */
async function readConversation(project_path) {
  // TODO: Implement actual filesystem reading
  // Claude Code stores conversations in different locations:
  // - macOS: ~/Library/Application Support/Claude/
  // - Linux: ~/.config/Claude/
  // - Could also be in project-specific .claude/ folders

  throw new Error('Filesystem conversation reading not yet implemented. Pass conversation_data in request.');
}

module.exports = {
  captureContext,
  readConversation
};
