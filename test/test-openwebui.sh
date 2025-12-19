#!/bin/bash

echo "════════════════════════════════════════════════"
echo "OpenWebUI / Ollama API Integration Test"
echo "════════════════════════════════════════════════"
echo ""

echo "1. Testing OpenWebUI Health..."
curl -s 'http://localhost:3000/health'
echo ""
echo ""

echo "2. Testing Ollama Embeddings (nomic-embed-text)..."
curl -s -X POST 'http://localhost:11434/api/embeddings' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "nomic-embed-text",
    "prompt": "This is a test sentence for embedding generation."
  }' | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'✅ Embedding dimensions: {len(data.get(\"embedding\", []))}'); print(f'   Sample values: {data.get(\"embedding\", [])[:5]}')" 2>/dev/null || echo "❌ Embeddings test failed"

echo ""

echo "3. Testing sentence-transformers model..."
curl -s -X POST 'http://localhost:11434/api/embeddings' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "sentence-transformers/all-MiniLM-L6-v2",
    "prompt": "Test embedding with sentence-transformers"
  }' | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'✅ Sentence-transformers dimensions: {len(data.get(\"embedding\", []))}');  print(f'   Model: sentence-transformers/all-MiniLM-L6-v2')" 2>/dev/null || echo "⚠️  sentence-transformers model not available in Ollama"

echo ""

echo "4. Testing Ollama Chat Completion (llama3)..."
curl -s -X POST 'http://localhost:11434/api/chat' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "llama3:8b",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant. Respond in 1 sentence."},
      {"role": "user", "content": "Say hello"}
    ],
    "stream": false
  }' | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'✅ Chat response: {data.get(\"message\", {}).get(\"content\", \"\")}');  print(f'   Model: {data.get(\"model\", \"unknown\")}')" 2>/dev/null || echo "❌ Chat completion test failed"

echo ""
echo "════════════════════════════════════════════════"
echo "Summary"
echo "════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "1. If tests passed: Update embed.js to use Ollama API"
echo "2. If tests passed: Update summarize.js to use Ollama chat API"
echo "3. Model for embeddings: nomic-embed-text (768-dim) or sentence-transformers (384-dim)"
echo "4. Model for summarization: llama3:8b"
echo ""
