/**
 * Embedding Generation via sentence-transformers
 * Generates 384-dimensional vector embeddings for semantic search
 * Uses same model as OpenWebUI: sentence-transformers/all-MiniLM-L6-v2
 */

const { exec } = require('child_process');
const { promisify } = require('util');
const execAsync = promisify(exec);
const fs = require('fs').promises;
const path = require('path');
const os = require('os');

/**
 * Generate embedding for text using sentence-transformers (Python)
 */
async function generateEmbedding(text) {
  try {
    // Use Python sentence-transformers for real embeddings
    const usePython = process.env.USE_REAL_EMBEDDINGS !== 'false';

    if (usePython) {
      return await generateEmbeddingViaPython(text);
    } else {
      // Fallback to mock for testing
      return generateMockEmbedding();
    }

  } catch (error) {
    console.error('Embedding generation error:', error);
    // Fallback to mock on error
    console.warn('⚠️  Falling back to mock embeddings');
    return generateMockEmbedding();
  }
}

/**
 * Generate embedding using Python sentence-transformers script
 * Fixed to handle special characters by writing to temp file instead of echo
 */
async function generateEmbeddingViaPython(text) {
  const scriptPath = '/app/scripts/generate_embedding.py';
  let tempFile = null;

  try {
    // Write text to temporary file to avoid shell escaping issues
    tempFile = path.join(os.tmpdir(), `embed-${Date.now()}-${Math.random().toString(36).slice(2)}.txt`);
    await fs.writeFile(tempFile, text, 'utf8');

    // Call Python script with temp file as stdin
    const { stdout, stderr } = await execAsync(
      `python3 ${scriptPath} < ${tempFile}`,
      { timeout: 10000 }
    );

    if (stderr && stderr.trim()) {
      console.warn('Python stderr:', stderr);
    }

    const result = JSON.parse(stdout);

    if (!result.success) {
      throw new Error(result.error || 'Python embedding generation failed');
    }

    if (result.embedding.length !== 384) {
      throw new Error(`Invalid embedding dimensions: ${result.embedding.length}, expected 384`);
    }

    return result.embedding;

  } catch (error) {
    throw new Error(`Python embedding error: ${error.message}`);
  } finally {
    // Clean up temp file
    if (tempFile) {
      try {
        await fs.unlink(tempFile);
      } catch (e) {
        // Ignore cleanup errors
      }
    }
  }
}

/**
 * Generate mock embedding for testing (384 dimensions)
 * This is a placeholder until OpenWebUI API integration is complete
 */
function generateMockEmbedding() {
  // Generate deterministic but varied embedding
  const embedding = [];
  for (let i = 0; i < 384; i++) {
    // Use sine wave pattern for variety
    embedding.push(Math.sin(i * 0.1) * 0.5);
  }
  return embedding;
}

module.exports = {
  generateEmbedding,
  generateMockEmbedding
};
