#!/usr/bin/env node
/**
 * OpenWebUI API Integration Test
 * Tests embedding and chat completion endpoints
 */

const axios = require('axios');

const OPENWEBUI_URL = process.env.OPENWEBUI_URL || 'http://localhost:3000';
const OPENWEBUI_API_KEY = process.env.OPENWEBUI_API_KEY || '';

async function testHealth() {
  console.log('\n🏥 Testing OpenWebUI Health...');
  try {
    const response = await axios.get(`${OPENWEBUI_URL}/health`);
    console.log('✅ Health check:', response.data);
    return true;
  } catch (error) {
    console.error('❌ Health check failed:', error.message);
    return false;
  }
}

async function testEmbeddings() {
  console.log('\n🧮 Testing Embeddings API...');

  if (!OPENWEBUI_API_KEY) {
    console.log('⚠️  No OPENWEBUI_API_KEY provided');
    console.log('   You need to create an API key in OpenWebUI:');
    console.log('   1. Visit http://localhost:3000');
    console.log('   2. Go to Settings → Account → API Keys');
    console.log('   3. Create a new API key');
    console.log('   4. Run: export OPENWEBUI_API_KEY=sk-xxx');
    return false;
  }

  // Try different possible embedding endpoints
  const endpoints = [
    '/api/v1/embeddings',
    '/ollama/api/embeddings',
    '/api/embeddings',
  ];

  const testText = 'This is a test sentence for embedding generation.';
  const model = 'sentence-transformers/all-MiniLM-L6-v2';

  for (const endpoint of endpoints) {
    try {
      console.log(`   Trying: ${endpoint}`);

      const response = await axios.post(
        `${OPENWEBUI_URL}${endpoint}`,
        {
          model: model,
          input: testText
        },
        {
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${OPENWEBUI_API_KEY}`
          },
          timeout: 5000
        }
      );

      console.log('✅ Embeddings endpoint found:', endpoint);
      console.log('   Response structure:', Object.keys(response.data));

      if (response.data.data && response.data.data[0]) {
        const embedding = response.data.data[0].embedding;
        console.log('   Embedding dimensions:', embedding.length);
        console.log('   Sample values:', embedding.slice(0, 5));
      }

      return { endpoint, response: response.data };
    } catch (error) {
      console.log(`   ❌ Failed: ${error.message}`);
    }
  }

  console.log('⚠️  Could not find working embeddings endpoint');
  return false;
}

async function testChatCompletion() {
  console.log('\n💬 Testing Chat Completion API (for summarization)...');

  if (!OPENWEBUI_API_KEY) {
    console.log('⚠️  No OPENWEBUI_API_KEY provided');
    return false;
  }

  const endpoints = [
    '/api/v1/chat/completions',
    '/ollama/api/chat',
    '/api/chat',
  ];

  const testMessages = [
    {
      role: 'system',
      content: 'You are a helpful assistant that summarizes conversations.'
    },
    {
      role: 'user',
      content: 'Summarize this: User asked about implementing a feature. Assistant explained the approach and provided code examples.'
    }
  ];

  for (const endpoint of endpoints) {
    try {
      console.log(`   Trying: ${endpoint}`);

      const response = await axios.post(
        `${OPENWEBUI_URL}${endpoint}`,
        {
          model: 'llama3:8b',
          messages: testMessages,
          stream: false
        },
        {
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${OPENWEBUI_API_KEY}`
          },
          timeout: 30000
        }
      );

      console.log('✅ Chat completion endpoint found:', endpoint);
      console.log('   Response structure:', Object.keys(response.data));

      if (response.data.choices && response.data.choices[0]) {
        const message = response.data.choices[0].message;
        console.log('   Summary:', message.content.substring(0, 100) + '...');
      }

      return { endpoint, response: response.data };
    } catch (error) {
      console.log(`   ❌ Failed: ${error.message}`);
    }
  }

  console.log('⚠️  Could not find working chat completion endpoint');
  return false;
}

async function testOllamaDirectly() {
  console.log('\n🦙 Testing Ollama API Directly...');

  // OpenWebUI uses Ollama, try direct Ollama endpoints
  const ollamaUrl = 'http://localhost:11434';

  try {
    // Test embeddings
    console.log('   Testing Ollama embeddings...');
    const embResponse = await axios.post(
      `${ollamaUrl}/api/embeddings`,
      {
        model: 'nomic-embed-text',
        prompt: 'Test embedding'
      },
      { timeout: 5000 }
    );

    console.log('✅ Ollama embeddings working');
    console.log('   Embedding dimensions:', embResponse.data.embedding.length);

    return true;
  } catch (error) {
    console.log(`   ❌ Ollama not accessible: ${error.message}`);
    return false;
  }
}

async function main() {
  console.log('╔════════════════════════════════════════════════╗');
  console.log('║  OpenWebUI API Integration Test               ║');
  console.log('╚════════════════════════════════════════════════╝');
  console.log('');
  console.log('Configuration:');
  console.log('  OpenWebUI URL:', OPENWEBUI_URL);
  console.log('  API Key:', OPENWEBUI_API_KEY ? '✅ Set (sk-***' + OPENWEBUI_API_KEY.slice(-8) + ')' : '❌ Not set');
  console.log('');

  const healthOk = await testHealth();

  if (!healthOk) {
    console.log('\n❌ OpenWebUI is not accessible. Make sure it\'s running on port 3000');
    process.exit(1);
  }

  await testEmbeddings();
  await testChatCompletion();
  await testOllamaDirectly();

  console.log('\n╔════════════════════════════════════════════════╗');
  console.log('║  Next Steps                                    ║');
  console.log('╚════════════════════════════════════════════════╝');
  console.log('');
  console.log('1. If no API key: Create one in OpenWebUI Settings → API Keys');
  console.log('2. Export the key: export OPENWEBUI_API_KEY=sk-xxx');
  console.log('3. Re-run this test: node openwebui-api-test.js');
  console.log('4. Update embed.js and summarize.js with working endpoints');
  console.log('');
}

main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
