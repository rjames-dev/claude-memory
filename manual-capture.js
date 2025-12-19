#!/usr/bin/env node
/**
 * Manual capture script for exported Claude Code conversation
 * Parses exported .txt file and sends to claude-memory processor
 */

const fs = require('fs');
const path = require('path');

const PROCESSOR_URL = 'http://localhost:3200';
const exportFile = process.argv[2];

if (!exportFile) {
  console.error('Usage: node manual-capture.js <exported-file.txt>');
  process.exit(1);
}

if (!fs.existsSync(exportFile)) {
  console.error(`File not found: ${exportFile}`);
  process.exit(1);
}

// Read and parse the exported conversation
console.log(`📖 Reading: ${exportFile}`);
const content = fs.readFileSync(exportFile, 'utf-8');

// Parse conversation messages
// Format: "> user message" followed by "⏺ assistant response"
const messages = [];
const lines = content.split('\n');
let currentRole = null;
let currentContent = [];

for (let i = 0; i < lines.length; i++) {
  const line = lines[i];

  // User message starts with ">"
  if (line.startsWith('> ')) {
    // Save previous message
    if (currentRole && currentContent.length > 0) {
      messages.push({
        role: currentRole,
        content: currentContent.join('\n').trim()
      });
    }
    currentRole = 'user';
    currentContent = [line.substring(2).trim()];
  }
  // Assistant message starts with "⏺"
  else if (line.startsWith('⏺ ')) {
    // Save previous message
    if (currentRole && currentContent.length > 0) {
      messages.push({
        role: currentRole,
        content: currentContent.join('\n').trim()
      });
    }
    currentRole = 'assistant';
    currentContent = [line.substring(2).trim()];
  }
  // Continuation of current message
  else if (currentRole && line.trim()) {
    currentContent.push(line);
  }
}

// Save last message
if (currentRole && currentContent.length > 0) {
  messages.push({
    role: currentRole,
    content: currentContent.join('\n').trim()
  });
}

console.log(`✅ Parsed ${messages.length} messages`);

// Extract metadata
const filesExtracted = new Set();
const tags = ['manual-capture', 'nlq-tools', 'docker', 'git'];

// Scan for file paths and mentions
for (const msg of messages) {
  const fileMatches = msg.content.match(/\/[A-Za-z0-9_\-\/\.]+\.(js|json|yml|yaml|md|sh|py|txt)/g);
  if (fileMatches) {
    fileMatches.forEach(f => filesExtracted.add(f));
  }
}

// Detect project path from content
let projectPath = '/Users/jamesmba/Data/00 GITHUB/Code/NLQ-Tools';
if (content.includes('NLQ-Tools')) {
  projectPath = '/Users/jamesmba/Data/00 GITHUB/Code/NLQ-Tools';
} else if (content.includes('claude-memory')) {
  projectPath = '/Users/jamesmba/Data/00 GITHUB/Code/claude-memory';
}

// Build capture payload
const payload = {
  project_path: projectPath,
  trigger: 'manual-capture-2025-12-15-nlq-tools-deployment',
  conversation_data: {
    messages: messages
  },
  metadata: {
    tags: tags,
    files_mentioned: Array.from(filesExtracted).slice(0, 20) // Limit to 20 files
  }
};

console.log(`📊 Project: ${projectPath}`);
console.log(`📋 Tags: ${tags.join(', ')}`);
console.log(`📁 Files: ${Array.from(filesExtracted).length} detected`);

// Send to processor
console.log('\n🚀 Sending to processor...');

fetch(`${PROCESSOR_URL}/capture`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(payload)
})
  .then(async res => {
    const data = await res.json();
    if (res.status === 202) {
      console.log('✅ Capture accepted!');
      console.log(JSON.stringify(data, null, 2));
    } else {
      console.error('❌ Capture failed:', res.status);
      console.error(data);
      process.exit(1);
    }
  })
  .catch(err => {
    console.error('❌ Error:', err.message);
    console.error('Is the processor running? Check: docker compose ps');
    process.exit(1);
  });
