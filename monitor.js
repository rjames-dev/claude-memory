#!/usr/bin/env node
/**
 * Claude Memory Terminal Monitor
 * Real-time terminal UI for monitoring claude-memory
 *
 * Usage:
 *   node monitor.js
 *   npm run monitor
 */

const http = require('http');
const readline = require('readline');

const API_URL = 'http://localhost:3200';
const REFRESH_INTERVAL = 5000; // 5 seconds

let stats = null;
let recent = [];
let error = null;

// ANSI color codes
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  gray: '\x1b[90m',
  red: '\x1b[31m'
};

function fetchJSON(path) {
  return new Promise((resolve, reject) => {
    http.get(`${API_URL}${path}`, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(e);
        }
      });
    }).on('error', reject);
  });
}

let agentStats = null;

async function fetchData() {
  try {
    [stats, recent, agentStats] = await Promise.all([
      fetchJSON('/api/stats'),
      fetchJSON('/api/recent?limit=8'),
      fetchJSON('/api/agents/stats').catch(() => ({ overview: null, byType: [] }))
    ]);
    error = null;
  } catch (e) {
    error = e.message;
  }
}

function formatUptime(seconds) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function formatTimeAgo(seconds) {
  if (seconds === null) return 'Never';
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

function formatTimestamp(timestamp) {
  const date = new Date(timestamp);
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');
  return `${hours}:${minutes}:${seconds}`;
}

function getProjectName(path) {
  const parts = path.split('/');
  return parts[parts.length - 1] || parts[parts.length - 2] || 'Unknown';
}

function drawBox(width) {
  return '═'.repeat(width);
}

function padRight(str, length) {
  return str + ' '.repeat(Math.max(0, length - str.length));
}

function padLeft(str, length) {
  return ' '.repeat(Math.max(0, length - str.length)) + str;
}

function clearScreen() {
  process.stdout.write('\x1b[2J\x1b[H');
}

function render() {
  clearScreen();

  const width = process.stdout.columns || 80;
  const boxWidth = Math.min(width - 4, 100);

  // Header
  console.log(colors.bright + colors.cyan);
  console.log('╔' + drawBox(boxWidth) + '╗');
  console.log('║' + padRight('  CLAUDE MEMORY MONITOR', boxWidth) + '║');
  console.log('╠' + drawBox(boxWidth) + '╣');
  console.log(colors.reset);

  if (error) {
    console.log(colors.red + '║  ' + padRight('⚠ ERROR: ' + error, boxWidth - 2) + '║' + colors.reset);
    console.log(colors.cyan + '╚' + drawBox(boxWidth) + '╝' + colors.reset);
    return;
  }

  if (!stats) {
    console.log(colors.gray + '║  ' + padRight('Loading...', boxWidth - 2) + '║' + colors.reset);
    console.log(colors.cyan + '╚' + drawBox(boxWidth) + '╝' + colors.reset);
    return;
  }

  // System Status
  console.log(colors.bright + '║  SYSTEM STATUS' + colors.reset);
  console.log(colors.cyan + '║' + colors.reset);
  console.log('║  ' + colors.green + '●' + colors.reset + ' Database    ' + colors.gray + stats.database.status + colors.reset);
  console.log('║  ' + colors.green + '●' + colors.reset + ' Ollama      ' + colors.gray + stats.ollama.model + colors.reset);
  console.log('║  ' + colors.green + '●' + colors.reset + ' Processor   ' + colors.gray + 'port ' + stats.processor.port + ' (uptime: ' + formatUptime(stats.processor.uptime) + ')' + colors.reset);
  console.log(colors.cyan + '║' + colors.reset);

  // Capture Statistics
  console.log(colors.bright + '║  CAPTURE STATISTICS' + colors.reset);
  console.log(colors.cyan + '║' + colors.reset);
  console.log('║  Total Snapshots:  ' + colors.bright + colors.green + padLeft(String(stats.captures.total), 6) + colors.reset);
  console.log('║  Today:            ' + colors.bright + padLeft(String(stats.captures.today), 6) + colors.reset);
  console.log('║  This Week:        ' + colors.bright + padLeft(String(stats.captures.week), 6) + colors.reset);
  console.log('║  Last Capture:     ' + colors.gray + formatTimeAgo(stats.captures.lastCaptureSeconds) + colors.reset);
  console.log(colors.cyan + '║' + colors.reset);

  // Session Tracking
  console.log(colors.bright + '║  SESSION TRACKING' + colors.reset);
  console.log(colors.cyan + '║' + colors.reset);
  console.log('║  Sessions Tracked: ' + colors.bright + padLeft(String(stats.sessions.tracked), 6) + colors.reset);
  console.log(colors.cyan + '║' + colors.reset);

  // Agent Memory Statistics
  if (agentStats && agentStats.overview) {
    console.log(colors.bright + '║  AGENT MEMORY' + colors.reset);
    console.log(colors.cyan + '║' + colors.reset);
    console.log('║  Total Agents:     ' + colors.bright + colors.blue + padLeft(String(agentStats.overview.total_agents), 6) + colors.reset);
    console.log('║  Unique Configs:   ' + colors.bright + padLeft(String(agentStats.overview.unique_configs), 6) + colors.reset);

    const avgDuration = agentStats.overview.avg_duration ? parseFloat(agentStats.overview.avg_duration).toFixed(1) + 's' : 'N/A';
    console.log('║  Avg Duration:     ' + colors.gray + padLeft(avgDuration, 6) + colors.reset);

    // By Type breakdown
    if (agentStats.byType && agentStats.byType.length > 0) {
      agentStats.byType.slice(0, 5).forEach(type => {
        const typeLabel = ('  ' + type.agent_type).substring(0, 17).padEnd(17);
        const count = padLeft(String(type.count), 4);
        console.log('║  ' + colors.dim + typeLabel + count + colors.reset);
      });
    }
    console.log(colors.cyan + '║' + colors.reset);
  }

  // Recent Captures
  console.log(colors.bright + '║  RECENT CAPTURES (' + recent.length + ')' + colors.reset);
  console.log(colors.cyan + '║' + colors.reset);

  recent.forEach((capture, index) => {
    const time = formatTimestamp(capture.timestamp);
    const project = getProjectName(capture.project_path);
    const messages = String(capture.messages) + ' msgs';
    const type = capture.capture_type;

    const typeColor = type === 'NEW' ? colors.green : colors.yellow;
    const typeBadge = typeColor + type.padEnd(6) + colors.reset;

    const line = '║  ' +
      colors.gray + time + colors.reset + '  ' +
      project.substring(0, 20).padEnd(20) + '  ' +
      messages.padEnd(10) + '  ' +
      typeBadge;

    console.log(line);
  });

  // Footer
  console.log(colors.cyan + '║' + colors.reset);
  console.log(colors.cyan + '╚' + drawBox(boxWidth) + '╝' + colors.reset);
  console.log(colors.gray + '\n  Auto-refresh: 5s  |  Press Ctrl+C to quit' + colors.reset);
}

// Handle terminal resize
process.stdout.on('resize', () => {
  render();
});

// Handle Ctrl+C gracefully
process.on('SIGINT', () => {
  clearScreen();
  console.log(colors.cyan + '\n  Claude Memory Monitor stopped.' + colors.reset + '\n');
  process.exit(0);
});

// Initial fetch and render
async function start() {
  console.log(colors.cyan + '\n  Starting Claude Memory Monitor...\n' + colors.reset);

  await fetchData();
  render();

  // Auto-refresh
  setInterval(async () => {
    await fetchData();
    render();
  }, REFRESH_INTERVAL);
}

start();
