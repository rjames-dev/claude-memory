#!/usr/bin/env node

/**
 * CLI Dashboard for Claude Memory System
 * Displays analytics from Phase 1 analytical views
 *
 * Usage:
 *   node scripts/dashboard-cli.js              # Show overview
 *   node scripts/dashboard-cli.js --quality    # Quality metrics
 *   node scripts/dashboard-cli.js --projects   # Project stats
 *   node scripts/dashboard-cli.js --bugs       # Bug analysis
 *   node scripts/dashboard-cli.js --files      # File activity
 *   node scripts/dashboard-cli.js --decisions  # Recent decisions
 *   node scripts/dashboard-cli.js --all        # Show everything
 */

const http = require('http');

// ANSI color codes
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',

  // Colors
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
  white: '\x1b[37m',

  // Background
  bgRed: '\x1b[41m',
  bgGreen: '\x1b[42m',
  bgYellow: '\x1b[43m',
  bgBlue: '\x1b[44m'
};

const PROCESSOR_URL = process.env.PROCESSOR_URL || 'http://localhost:3200';

// Fetch JSON from API
function fetchJSON(endpoint) {
  return new Promise((resolve, reject) => {
    const url = `${PROCESSOR_URL}${endpoint}`;
    http.get(url, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (err) {
          reject(new Error(`Failed to parse JSON from ${endpoint}: ${err.message}`));
        }
      });
    }).on('error', reject);
  });
}

// Format helpers
function section(title) {
  console.log(`\n${colors.bright}${colors.cyan}${'='.repeat(60)}${colors.reset}`);
  console.log(`${colors.bright}${colors.cyan}${title}${colors.reset}`);
  console.log(`${colors.cyan}${'='.repeat(60)}${colors.reset}\n`);
}

function subsection(title) {
  console.log(`\n${colors.bright}${colors.blue}${title}${colors.reset}`);
  console.log(`${colors.dim}${'-'.repeat(40)}${colors.reset}`);
}

function row(label, value, color = colors.white) {
  const padding = ' '.repeat(Math.max(0, 25 - label.length));
  console.log(`  ${colors.dim}${label}:${colors.reset}${padding}${color}${value}${colors.reset}`);
}

function progressBar(percentage, width = 30) {
  const filled = Math.round(width * percentage / 100);
  const empty = width - filled;
  const bar = '█'.repeat(filled) + '░'.repeat(empty);

  let color = colors.green;
  if (percentage < 30) color = colors.red;
  else if (percentage < 70) color = colors.yellow;

  return `${color}${bar}${colors.reset} ${percentage.toFixed(1)}%`;
}

function badge(text, category) {
  const badgeColors = {
    database: colors.bgBlue,
    dependency: colors.bgMagenta,
    command: colors.bgYellow,
    syntax: colors.bgRed,
    runtime: colors.bgRed,
    documentation: colors.bgGreen,
    javascript: colors.bgYellow,
    python: colors.bgBlue,
    sql: colors.bgMagenta,
    config: colors.bgCyan,
    json: colors.bgYellow,
    other: colors.dim
  };

  const color = badgeColors[category] || colors.dim;
  return `${color}${colors.bright} ${text} ${colors.reset}`;
}

function formatTimeAgo(seconds) {
  if (seconds === null || seconds === undefined) return 'Never';
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

// Display functions
async function displayOverview() {
  section('📊 Claude Memory System - Overview');

  const stats = await fetchJSON('/api/stats');

  subsection('System Status');
  row('Database', stats.database.status === 'connected' ?
    `${colors.green}✓ Connected${colors.reset}` :
    `${colors.red}✗ Disconnected${colors.reset}`);
  row('Ollama', stats.ollama.status === 'running' ?
    `${colors.green}✓ Running${colors.reset}` :
    `${colors.red}✗ Stopped${colors.reset}`);
  row('Ollama Model', stats.ollama.model, colors.cyan);
  row('Processor Uptime', `${Math.floor(stats.processor.uptime / 60)}m ${Math.floor(stats.processor.uptime % 60)}s`, colors.cyan);

  subsection('Capture Statistics');
  row('Total Snapshots', stats.captures.total.toLocaleString(), colors.bright + colors.green);
  row('Today', stats.captures.today.toLocaleString(), colors.green);
  row('This Week', stats.captures.week.toLocaleString(), colors.yellow);
  row('Last Capture', formatTimeAgo(stats.captures.lastCaptureSeconds), colors.cyan);
  row('Tracked Sessions', stats.sessions.tracked.toLocaleString(), colors.magenta);
}

async function displayQuality() {
  section('📈 Data Quality Metrics');

  const quality = await fetchJSON('/api/quality');

  subsection('Quality Score Distribution');
  const total = parseInt(quality.total);
  const highPct = (quality.high_quality / total * 100);
  const mediumPct = (quality.medium_quality / total * 100);
  const lowPct = (quality.low_quality / total * 100);

  row('Average Quality', `${quality.avg_quality}/10`, colors.bright + colors.cyan);
  row('Max Score', `${quality.max_score}/10`, colors.green);
  row('Min Score', `${quality.min_score}/10`, colors.red);
  console.log();
  row('High Quality (≥8)', `${quality.high_quality} snapshots`, colors.green);
  console.log(`    ${progressBar(highPct)}`);
  row('Medium Quality (5-7)', `${quality.medium_quality} snapshots`, colors.yellow);
  console.log(`    ${progressBar(mediumPct)}`);
  row('Low Quality (<5)', `${quality.low_quality} snapshots`, colors.red);
  console.log(`    ${progressBar(lowPct)}`);
}

async function displayProjects() {
  section('📁 Project Statistics');

  const projects = await fetchJSON('/api/projects');

  if (projects.length === 0) {
    console.log('  No projects found.');
    return;
  }

  projects.forEach((proj, idx) => {
    subsection(`${idx + 1}. ${proj.project_path}`);
    row('Total Snapshots', proj.total_snapshots.toLocaleString(), colors.cyan);
    row('Tracked Sessions', proj.tracked_sessions.toLocaleString(), colors.magenta);
    row('Total Messages', proj.total_messages.toLocaleString(), colors.green);
    row('Avg Messages/Snapshot', proj.avg_messages_per_snapshot, colors.yellow);
    row('Most Common Tag', proj.most_common_tag || 'None', colors.blue);
    row('Last Activity', formatTimeAgo(proj.last_activity_seconds), colors.dim);
  });
}

async function displayBugs() {
  section('🐛 Bug Analysis');

  const bugs = await fetchJSON('/api/bugs');

  if (bugs.categories.length === 0) {
    console.log('  No bugs tracked yet.');
    return;
  }

  subsection('Bug Categories');
  const total = bugs.categories.reduce((sum, cat) => sum + parseInt(cat.count), 0);

  bugs.categories.forEach(cat => {
    const pct = (cat.count / total * 100).toFixed(1);
    console.log(`  ${badge(cat.bug_category, cat.bug_category)} ${cat.count} bugs (${pct}%)`);
  });

  subsection('Recent Bugs Fixed');
  if (bugs.recent.length === 0) {
    console.log('  No recent bugs.');
  } else {
    bugs.recent.slice(0, 10).forEach(bug => {
      const date = new Date(bug.pst_time).toLocaleString();
      console.log(`  ${badge(bug.bug_category, bug.bug_category)} #${bug.snapshot_id} - ${date}`);
      console.log(`    ${colors.dim}${bug.bug_text.substring(0, 80)}...${colors.reset}`);
    });
  }
}

async function displayFiles() {
  section('📂 File Activity Heatmap');

  const files = await fetchJSON('/api/files');

  if (files.length === 0) {
    console.log('  No file activity tracked yet.');
    return;
  }

  subsection('Hottest Files');
  files.slice(0, 20).forEach((file, idx) => {
    const heat = file.mention_count > 5 ? '🔥' : file.mention_count > 2 ? '🌡️' : '📄';
    console.log(`  ${heat} ${badge(file.file_type, file.file_type)} ${colors.bright}${file.file_path}${colors.reset}`);
    console.log(`     ${colors.dim}${file.mention_count} mentions in ${file.project_count} project(s)${colors.reset}`);
  });
}

async function displayDecisions() {
  section('💡 Recent Decisions');

  const decisions = await fetchJSON('/api/decisions');

  if (decisions.length === 0) {
    console.log('  No decisions tracked yet.');
    return;
  }

  decisions.forEach(decision => {
    const date = new Date(decision.pst_time).toLocaleString();
    console.log(`\n  ${colors.bright}#${decision.snapshot_id}${colors.reset} - ${colors.dim}${date}${colors.reset}`);
    console.log(`  ${colors.cyan}${decision.decision_text}${colors.reset}`);
  });
}

// Main
async function main() {
  const args = process.argv.slice(2);
  const showAll = args.includes('--all');

  try {
    // Show header
    console.log(`\n${colors.bright}${colors.magenta}Claude Memory System Dashboard${colors.reset}`);
    console.log(`${colors.dim}${new Date().toLocaleString()}${colors.reset}`);

    // Determine what to show
    if (showAll || args.length === 0 || args.includes('--overview')) {
      await displayOverview();
    }

    if (showAll || args.includes('--quality')) {
      await displayQuality();
    }

    if (showAll || args.includes('--projects')) {
      await displayProjects();
    }

    if (showAll || args.includes('--bugs')) {
      await displayBugs();
    }

    if (showAll || args.includes('--files')) {
      await displayFiles();
    }

    if (showAll || args.includes('--decisions')) {
      await displayDecisions();
    }

    // Footer
    console.log(`\n${colors.dim}${'─'.repeat(60)}${colors.reset}`);
    console.log(`${colors.dim}Dashboard URL: ${PROCESSOR_URL}/dashboard${colors.reset}\n`);

  } catch (error) {
    console.error(`\n${colors.red}${colors.bright}Error:${colors.reset} ${error.message}`);
    console.error(`${colors.dim}Make sure the processor is running at ${PROCESSOR_URL}${colors.reset}\n`);
    process.exit(1);
  }
}

// Show help
if (process.argv.includes('--help') || process.argv.includes('-h')) {
  console.log(`
${colors.bright}Claude Memory System - CLI Dashboard${colors.reset}

${colors.cyan}Usage:${colors.reset}
  node scripts/dashboard-cli.js [options]

${colors.cyan}Options:${colors.reset}
  ${colors.green}--overview${colors.reset}    Show system overview and capture stats (default)
  ${colors.green}--quality${colors.reset}     Show data quality metrics
  ${colors.green}--projects${colors.reset}    Show per-project statistics
  ${colors.green}--bugs${colors.reset}        Show bug analysis and patterns
  ${colors.green}--files${colors.reset}       Show file activity heatmap
  ${colors.green}--decisions${colors.reset}   Show recent architectural decisions
  ${colors.green}--all${colors.reset}         Show everything
  ${colors.green}--help, -h${colors.reset}    Show this help message

${colors.cyan}Examples:${colors.reset}
  node scripts/dashboard-cli.js
  node scripts/dashboard-cli.js --quality --projects
  node scripts/dashboard-cli.js --all
  npm run dashboard-cli

${colors.cyan}Environment:${colors.reset}
  PROCESSOR_URL    Processor URL (default: http://localhost:3200)
`);
  process.exit(0);
}

main();
