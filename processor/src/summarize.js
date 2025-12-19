/**
 * Summarization via OpenWebUI
 * Generates condensed summaries of conversations
 */

const axios = require('axios');

/**
 * Generate summary of conversation using OpenWebUI's model
 */
async function summarize(conversation) {
  try {
    // Try AI summarization first (via Ollama)
    const useAI = process.env.USE_AI_SUMMARIES !== 'false';

    if (useAI) {
      try {
        return await summarizeViaOllama(conversation);
      } catch (aiError) {
        console.warn('⚠️  AI summarization failed, falling back to extractive:', aiError.message);
      }
    }

    // Fallback to extractive summary
    return generateExtractiveSummary(conversation);

  } catch (error) {
    console.error('Summarization error:', error);
    return generateExtractiveSummary(conversation);
  }
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
 * Uses Ollama running inside OpenWebUI container
 */
async function summarizeViaOllama(conversation) {
  // Ollama is proxied through OpenWebUI at /ollama
  const ollamaUrl = process.env.OLLAMA_URL || 'http://host.docker.internal:3000/ollama';
  const model = process.env.SUMMARY_MODEL || 'llama3.2:latest';

  // Build conversation text
  const conversationText = conversation.messages
    .map((msg, idx) => {
      const role = msg.role || 'unknown';
      const content = msg.content || '';
      return `[${idx + 1}] ${role}: ${content}`;
    })
    .join('\n\n');

  const prompt = `Summarize the following development conversation in 200-300 words. Focus on:
- Key technical decisions made
- Problems solved
- Files or components worked on
- Important code changes or fixes

Conversation:
${conversationText.slice(0, 10000)}`;

  try {
    const response = await axios.post(
      `${ollamaUrl}/api/generate`,
      {
        model: model,
        prompt: prompt,
        stream: false,
        options: {
          temperature: 0.3,  // Lower temperature for factual summaries
          num_predict: 400   // Limit length to ~300 words
        }
      },
      {
        timeout: 180000,  // 3 minutes for large sessions (increased from 30s)
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
    throw new Error(`Ollama summarization failed: ${error.message}`);
  }
}

module.exports = {
  summarize,
  generateExtractiveSummary
};
