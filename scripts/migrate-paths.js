#!/usr/bin/env node
/**
 * Claude Memory - Path Migration Utility (Node.js version)
 * Migrates all stored paths when workspace location changes
 * Created: 2025-12-19 (Phase 6B)
 *
 * Usage:
 *   node scripts/migrate-paths.js preview /old/path /new/path
 *   node scripts/migrate-paths.js apply /old/path /new/path
 */

const { Client } = require('pg');
const readline = require('readline');
const path = require('path');
const fs = require('fs');

// ============================================================
// Configuration
// ============================================================

const PROJECT_ROOT = path.resolve(__dirname, '..');

// Load .env file if it exists
let envConfig = {};
const envPath = path.join(PROJECT_ROOT, '.env');
if (fs.existsSync(envPath)) {
  const envContent = fs.readFileSync(envPath, 'utf8');
  envContent.split('\n').forEach(line => {
    const match = line.match(/^([^#=]+)=(.*)$/);
    if (match) {
      envConfig[match[1].trim()] = match[2].trim();
    }
  });
}

const config = {
  host: process.env.POSTGRES_HOST || envConfig.POSTGRES_HOST || 'localhost',
  port: parseInt(process.env.POSTGRES_HOST_PORT || envConfig.POSTGRES_HOST_PORT || '5435'),
  database: process.env.POSTGRES_DB || envConfig.POSTGRES_DB || 'claude_memory',
  user: process.env.POSTGRES_USER || envConfig.POSTGRES_USER || 'memory_admin',
  password: process.env.CONTEXT_DB_PASSWORD || envConfig.CONTEXT_DB_PASSWORD
};

// Colors for terminal output
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m'
};

// ============================================================
// Utility Functions
// ============================================================

function printBanner() {
  console.log(`${colors.blue}╔════════════════════════════════════════════════════════════╗${colors.reset}`);
  console.log(`${colors.blue}║        Claude Memory - Path Migration Utility             ║${colors.reset}`);
  console.log(`${colors.blue}╚════════════════════════════════════════════════════════════╝${colors.reset}`);
  console.log('');
}

function printHelp() {
  console.log(`
Usage: node scripts/migrate-paths.js <mode> <old_path> <new_path>

Modes:
  preview   Preview changes without applying (dry run - safe)
  apply     Apply changes to database (requires confirmation)

Arguments:
  old_path  Current path in database
  new_path  New path to migrate to

Examples:
  # Preview migration (safe - no changes)
  node scripts/migrate-paths.js preview "/Users/jamesmba/Data/00 GITHUB" "/Users/jamesmba/Projects"

  # Apply migration (requires confirmation)
  node scripts/migrate-paths.js apply "/Users/jamesmba/Data/00 GITHUB" "/Users/jamesmba/Projects"

Environment:
  Database connection is configured via .env file or defaults:
  - Host: ${config.host}
  - Port: ${config.port}
  - Database: ${config.database}
  - User: ${config.user}

Requirements:
  - Docker containers running (docker-compose up)
  - .env file configured with CONTEXT_DB_PASSWORD

Workflow:
  1. Run 'preview' mode first to see what will change
  2. Review the output carefully
  3. Run 'apply' mode to execute the migration
  4. Update .env file with new CLAUDE_WORKSPACE_ROOT
  5. Restart containers: docker-compose down && docker-compose up -d
`);
}

function checkRequirements() {
  if (!config.password) {
    console.error(`${colors.red}❌ Error: CONTEXT_DB_PASSWORD not set${colors.reset}`);
    console.error('Please set it in .env file or environment');
    process.exit(1);
  }
}

async function askQuestion(query) {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  return new Promise(resolve => rl.question(query, ans => {
    rl.close();
    resolve(ans);
  }));
}

async function runMigration(mode, oldPath, newPath) {
  const dryRun = mode === 'preview';

  console.log(`${colors.blue}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${colors.reset}`);
  console.log(`${colors.blue}Migration Settings${colors.reset}`);
  console.log(`${colors.blue}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${colors.reset}`);
  console.log(`Mode:     ${colors.yellow}${mode}${colors.reset}`);
  console.log(`Old path: ${colors.red}${oldPath}${colors.reset}`);
  console.log(`New path: ${colors.green}${newPath}${colors.reset}`);
  console.log(`Dry run:  ${dryRun}`);
  console.log('');

  // Confirmation for apply mode
  if (mode === 'apply') {
    console.log(`${colors.yellow}⚠️  WARNING: This will modify the database!${colors.reset}`);
    console.log('');
    const answer = await askQuestion('Are you sure you want to continue? (yes/NO): ');
    if (answer !== 'yes') {
      console.log(`${colors.yellow}Migration cancelled${colors.reset}`);
      process.exit(0);
    }
  }

  // Execute migration
  console.log(`${colors.blue}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${colors.reset}`);
  console.log(`${colors.blue}Executing Migration${colors.reset}`);
  console.log(`${colors.blue}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${colors.reset}`);
  console.log('');

  const client = new Client(config);

  try {
    await client.connect();
    console.log(`${colors.green}✅ Connected to database${colors.reset}`);
    console.log('');

    const query = `
      SELECT * FROM migrate_project_paths(
        $1,
        $2,
        dry_run := $3
      );
    `;

    const result = await client.query(query, [oldPath, newPath, dryRun]);

    // Display results
    console.log('Migration Results:');
    console.log('─'.repeat(80));
    console.table(result.rows);

    console.log('');
    if (mode === 'preview') {
      console.log(`${colors.green}✅ Preview complete - no changes made${colors.reset}`);
      console.log('');
      console.log('Next steps:');
      console.log('  1. Review the output above');
      console.log("  2. Run with 'apply' mode to execute migration");
    } else {
      console.log(`${colors.green}✅ Migration complete!${colors.reset}`);
      console.log('');
      console.log('Next steps:');
      console.log('  1. Update .env file:');
      console.log(`     CLAUDE_WORKSPACE_ROOT=${newPath}`);
      console.log('  2. Restart containers:');
      console.log('     docker-compose down && docker-compose up -d');
      console.log('  3. Verify system is working');
    }

  } catch (error) {
    console.error(`${colors.red}❌ Migration failed:${colors.reset}`, error.message);
    process.exit(1);
  } finally {
    await client.end();
  }
}

// ============================================================
// Main
// ============================================================

async function main() {
  printBanner();

  // Parse arguments
  const args = process.argv.slice(2);

  if (args.length !== 3) {
    printHelp();
    process.exit(1);
  }

  const [mode, oldPath, newPath] = args;

  // Validate mode
  if (mode !== 'preview' && mode !== 'apply') {
    console.error(`${colors.red}❌ Error: Invalid mode '${mode}'${colors.reset}`);
    console.error("Must be 'preview' or 'apply'");
    console.log('');
    printHelp();
    process.exit(1);
  }

  // Validate paths
  if (!oldPath || !newPath) {
    console.error(`${colors.red}❌ Error: Both old_path and new_path are required${colors.reset}`);
    printHelp();
    process.exit(1);
  }

  if (oldPath === newPath) {
    console.error(`${colors.red}❌ Error: old_path and new_path are identical${colors.reset}`);
    process.exit(1);
  }

  // Check requirements
  checkRequirements();

  // Run migration
  await runMigration(mode, oldPath, newPath);
}

main().catch(error => {
  console.error(`${colors.red}❌ Fatal error:${colors.reset}`, error);
  process.exit(1);
});
