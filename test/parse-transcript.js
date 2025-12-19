#!/usr/bin/env node
/**
 * Parse Claude Code transcript into conversation format
 */

const fs = require('fs');
const path = require('path');

function parseTranscript(filePath) {
  const content = fs.readFileSync(filePath, 'utf-8');
  const lines = content.split('\n');

  const messages = [];
  let currentRole = null;
  let currentContent = [];
  let inToolUse = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // User message indicator: starts with ">"
    if (line.trim().startsWith('> ')) {
      // Save previous message
      if (currentRole && currentContent.length > 0) {
        messages.push({
          role: currentRole,
          content: currentContent.join('\n').trim()
        });
      }

      currentRole = 'user';
      currentContent = [line.substring(2).trim()];
      inToolUse = false;
      continue;
    }

    // Assistant message indicator: starts with "⏺"
    if (line.trim().startsWith('⏺')) {
      // Check if it's a tool use (has parentheses indicating a tool call)
      if (line.includes('(') || line.includes('Read(') || line.includes('Bash(') || line.includes('Write(')) {
        inToolUse = true;
        continue;
      }

      // Save previous message if switching roles
      if (currentRole === 'user' && currentContent.length > 0) {
        messages.push({
          role: currentRole,
          content: currentContent.join('\n').trim()
        });
        currentContent = [];
      }

      currentRole = 'assistant';
      const content = line.substring(line.indexOf('⏺') + 1).trim();
      if (content && !inToolUse) {
        currentContent.push(content);
      }
      continue;
    }

    // Tool output indicator: starts with "⎿"
    if (line.trim().startsWith('⎿')) {
      inToolUse = false;
      continue;
    }

    // Regular content line
    if (currentRole && !inToolUse && line.trim()) {
      // Skip lines that look like formatting or expansion hints
      if (line.includes('ctrl+o to expand') || line.includes('lines (ctrl+o')) {
        continue;
      }

      currentContent.push(line.trim());
    }
  }

  // Save last message
  if (currentRole && currentContent.length > 0) {
    messages.push({
      role: currentRole,
      content: currentContent.join('\n').trim()
    });
  }

  return messages;
}

// Main execution
const transcriptPath = process.argv[2] || '/Users/jamesmba/Data/00 GITHUB/Code/2025-12-13-ive-organized-this-folder-for-the-purpose-of-esta.txt';

console.log('Parsing transcript:', transcriptPath);

const messages = parseTranscript(transcriptPath);

console.log(`\nExtracted ${messages.length} messages`);
console.log(`User messages: ${messages.filter(m => m.role === 'user').length}`);
console.log(`Assistant messages: ${messages.filter(m => m.role === 'assistant').length}`);

// Output as JSON
const conversation = {
  source: 'claude-code-transcript',
  date: '2025-12-13',
  messages: messages
};

// Write to file
const outputPath = path.join(__dirname, 'parsed-conversation.json');
fs.writeFileSync(outputPath, JSON.stringify(conversation, null, 2));

console.log(`\nSaved to: ${outputPath}`);
console.log(`\nFirst user message preview:`);
console.log(messages.find(m => m.role === 'user')?.content.substring(0, 200) + '...');
console.log(`\nFirst assistant message preview:`);
console.log(messages.find(m => m.role === 'assistant')?.content.substring(0, 200) + '...');
