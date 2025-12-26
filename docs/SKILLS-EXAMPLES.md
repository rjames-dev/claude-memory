# Skills System - Example Skills

**Purpose:** Reference implementations validating the skills system architecture
**Status:** Design Examples
**Last Updated:** 2025-12-26

---

## Table of Contents

1. [Bash Script Skills](#bash-script-skills)
2. [Tool Sequence Skills](#tool-sequence-skills)
3. [Agent Spawn Skills](#agent-spawn-skills)
4. [Cross-Project Skills](#cross-project-skills)
5. [Temporal Skills](#temporal-skills)

---

## Bash Script Skills

### 1. check-db-health

**Category:** database
**Scope:** global
**Prerequisites:** docker running

**Purpose:** Verify PostgreSQL database health

**Script:** `~/.claude-memory/skills/scripts/check-db-health.sh`

```bash
#!/bin/bash
# check-db-health.sh
# Verifies PostgreSQL database is running and accessible

set -e

DB_NAME=${1:-"claude_memory"}
DB_HOST=${2:-"localhost"}
DB_PORT=${3:-"5432"}

echo "🔍 Checking Database Health: $DB_NAME"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check Docker container
echo ""
echo "1. Docker Container Status:"
if docker ps | grep -q postgres; then
    echo "   ✅ PostgreSQL container is running"
else
    echo "   ❌ PostgreSQL container not found"
    exit 1
fi

# Check connection
echo ""
echo "2. Connection Test:"
if psql -h $DB_HOST -p $DB_PORT -U postgres -d $DB_NAME -c "SELECT version();" > /dev/null 2>&1; then
    echo "   ✅ Connection successful"
else
    echo "   ❌ Connection failed"
    exit 1
fi

# Check tables exist
echo ""
echo "3. Schema Check:"
TABLE_COUNT=$(psql -h $DB_HOST -p $DB_PORT -U postgres -d $DB_NAME -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")

if [ "$TABLE_COUNT" -gt 0 ]; then
    echo "   ✅ Found $TABLE_COUNT tables"
else
    echo "   ⚠️  No tables found (database may be empty)"
fi

# Show table list
echo ""
echo "4. Tables:"
psql -h $DB_HOST -p $DB_PORT -U postgres -d $DB_NAME -c "\dt" | grep public | awk '{print "   - " $3}'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Database health check complete"
```

**Skill Definition:**

```json
{
  "agent_name": "check-db-health",
  "display_name": "Database Health Check",
  "description": "Verify PostgreSQL database is running and accessible",
  "category": "database",
  "scope": "global",
  "project_path": null,

  "triggers": [
    {
      "trigger_phrase": "check database health",
      "match_type": "semantic",
      "confidence_threshold": 0.75
    },
    {
      "trigger_phrase": "verify postgres is running",
      "match_type": "semantic",
      "confidence_threshold": 0.75
    },
    {
      "trigger_phrase": "is the database up",
      "match_type": "semantic",
      "confidence_threshold": 0.70
    }
  ],

  "command": {
    "command_type": "bash_script",
    "script_path": "~/.claude-memory/skills/scripts/check-db-health.sh",
    "parameters": {
      "db_name": {
        "type": "string",
        "default": "claude_memory",
        "description": "Database name to check"
      },
      "db_host": {
        "type": "string",
        "default": "localhost"
      },
      "db_port": {
        "type": "integer",
        "default": 5432
      }
    },
    "prerequisites": {
      "docker_running": true
    },
    "success_indicators": [
      "health check complete",
      "Connection successful"
    ],
    "failure_indicators": [
      "Connection failed",
      "container not found"
    ]
  }
}
```

### 2. backup-claude-memory

**Category:** maintenance
**Scope:** global

**Purpose:** Backup claude-memory database to SQL file

**Script:** `~/.claude-memory/skills/scripts/backup-claude-memory.sh`

```bash
#!/bin/bash
# backup-claude-memory.sh
# Creates a compressed backup of claude-memory database

set -e

BACKUP_DIR=${1:-"$HOME/claude-memory-backups"}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/claude_memory_$TIMESTAMP.sql.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "💾 Backing up claude-memory database"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Dump database
echo ""
echo "Creating backup: $BACKUP_FILE"
pg_dump -h localhost -p 5432 -U postgres -d claude_memory | gzip > "$BACKUP_FILE"

# Check size
SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "✅ Backup complete: $SIZE"

# Clean old backups (keep last 7 days)
echo ""
echo "Cleaning old backups (keeping last 7 days):"
find "$BACKUP_DIR" -name "claude_memory_*.sql.gz" -mtime +7 -exec rm {} \;
REMAINING=$(ls -1 "$BACKUP_DIR" | wc -l)
echo "✅ Retained $REMAINING backups"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Backup location: $BACKUP_FILE"
```

**Skill Definition:**

```json
{
  "agent_name": "backup-claude-memory",
  "display_name": "Backup Claude Memory",
  "description": "Creates compressed backup of claude-memory database",
  "category": "maintenance",
  "scope": "global",

  "triggers": [
    {
      "trigger_phrase": "backup the database",
      "match_type": "semantic",
      "confidence_threshold": 0.75
    },
    {
      "trigger_phrase": "create database backup",
      "match_type": "semantic",
      "confidence_threshold": 0.75
    }
  ],

  "command": {
    "command_type": "bash_script",
    "script_path": "~/.claude-memory/skills/scripts/backup-claude-memory.sh",
    "parameters": {
      "backup_dir": {
        "type": "string",
        "default": "$HOME/claude-memory-backups"
      }
    },
    "prerequisites": {
      "database_accessible": true
    },
    "success_indicators": ["Backup complete"],
    "failure_indicators": ["error:", "failed"]
  }
}
```

---

## Tool Sequence Skills

### 3. git-commit-protocol

**Category:** git
**Scope:** global
**Phases:** 1-4 (evolves across all phases)

**Purpose:** Complete git commit workflow following our established protocol

**Tool Sequence Definition:**

```json
{
  "agent_name": "git-commit-protocol",
  "display_name": "Git Commit (Our Protocol)",
  "description": "Commits changes following our protocol: check status, draft message, use heredoc, verify success",
  "category": "git",
  "scope": "global",
  "version": 2,

  "triggers": [
    {
      "trigger_phrase": "commit these changes",
      "match_type": "semantic",
      "confidence_threshold": 0.75
    },
    {
      "trigger_phrase": "create a commit",
      "match_type": "semantic",
      "confidence_threshold": 0.75
    },
    {
      "trigger_phrase": "git commit",
      "match_type": "semantic",
      "confidence_threshold": 0.80
    }
  ],

  "command": {
    "command_type": "tool_sequence",
    "version": 2,
    "command_definition": {
      "steps": [
        {
          "step": 1,
          "description": "Check git status and recent commits",
          "tools": [
            {
              "tool": "Bash",
              "command": "git status",
              "description": "Check working tree status",
              "capture_output": true
            },
            {
              "tool": "Bash",
              "command": "git diff",
              "description": "Show unstaged changes",
              "capture_output": true
            },
            {
              "tool": "Bash",
              "command": "git log --oneline -5",
              "description": "Show recent commit messages for style",
              "capture_output": true
            }
          ],
          "parallel": true,
          "continue_on_error": false
        },
        {
          "step": 2,
          "description": "Run tests (optional - added in v2)",
          "tools": [
            {
              "tool": "Bash",
              "command": "npm test",
              "description": "Run test suite",
              "optional": true
            }
          ],
          "parallel": false,
          "continue_on_error": true
        },
        {
          "step": 3,
          "description": "Analyze changes and draft commit message",
          "action": "custom_function",
          "function": "analyze_git_changes_and_draft_message",
          "inputs": {
            "status": "{step1.tool1.output}",
            "diff": "{step1.tool2.output}",
            "recent_commits": "{step1.tool3.output}"
          },
          "rules": [
            "Match existing commit style from git log",
            "Use format: Type: Brief description",
            "Focus on WHY not WHAT",
            "Keep concise (1-2 sentences)",
            "Add co-author footer"
          ]
        },
        {
          "step": 4,
          "description": "Add files and commit with heredoc",
          "tools": [
            {
              "tool": "Bash",
              "command": "git add . && git commit -m \"$(cat <<'EOF'\\n{step3.commit_message}\\n\\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\\n\\nCo-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>\\nEOF\\n)\"",
              "description": "Stage all changes and commit with heredoc format"
            }
          ],
          "parallel": false
        },
        {
          "step": 5,
          "description": "Verify commit success",
          "tools": [
            {
              "tool": "Bash",
              "command": "git status",
              "description": "Confirm working tree is clean"
            },
            {
              "tool": "Bash",
              "command": "git log -1 --stat",
              "description": "Show the commit that was created"
            }
          ],
          "parallel": false,
          "validation": {
            "success_if_contains": [
              "nothing to commit, working tree clean",
              "Your branch is ahead"
            ]
          }
        }
      ]
    },
    "prerequisites": {
      "git_repo": true,
      "has_changes": true
    },
    "success_indicators": [
      "nothing to commit, working tree clean",
      "Your branch is ahead"
    ],
    "failure_indicators": [
      "error:",
      "fatal:",
      "nothing added to commit"
    ]
  },

  "evolution_history": [
    {
      "version": 1,
      "date": "2025-12-15",
      "changes": "Initial creation from pattern detection",
      "performance": {"uses": 15, "success_rate": 100}
    },
    {
      "version": 2,
      "date": "2025-12-20",
      "changes": "Added optional test step (user feedback: 'always run tests')",
      "performance": {"uses": 8, "success_rate": 100}
    }
  ]
}
```

### 4. deploy-to-staging

**Category:** deployment
**Scope:** project-specific
**Project:** NLQ-Reporting

**Purpose:** Deploy current branch to staging environment with health checks

**Tool Sequence Definition:**

```json
{
  "agent_name": "deploy-to-staging",
  "display_name": "Deploy to Staging",
  "description": "Deploys current branch to staging with health checks and rollback capability",
  "category": "deployment",
  "scope": "project",
  "project_path": "/Users/jamesmba/Data/00 GITHUB/Code/NLQ-Reporting",

  "triggers": [
    {
      "trigger_phrase": "deploy to staging",
      "match_type": "semantic",
      "confidence_threshold": 0.80
    },
    {
      "trigger_phrase": "push to staging environment",
      "match_type": "semantic",
      "confidence_threshold": 0.75
    }
  ],

  "command": {
    "command_type": "tool_sequence",
    "command_definition": {
      "steps": [
        {
          "step": 1,
          "description": "Pre-deployment checks",
          "tools": [
            {
              "tool": "Bash",
              "command": "git status",
              "description": "Verify clean working tree"
            },
            {
              "tool": "Bash",
              "command": "npm test",
              "description": "Run test suite"
            }
          ],
          "parallel": false,
          "validation": {
            "success_if_contains": [
              "nothing to commit",
              "All tests passed"
            ]
          }
        },
        {
          "step": 2,
          "description": "Build application",
          "tools": [
            {
              "tool": "Bash",
              "command": "npm run build",
              "description": "Create production build"
            }
          ],
          "parallel": false
        },
        {
          "step": 3,
          "description": "Deploy to staging server",
          "tools": [
            {
              "tool": "Bash",
              "command": "ssh staging 'cd /var/www/nlq-reporting && git pull && npm install && pm2 restart nlq-reporting'",
              "description": "SSH deploy and restart"
            }
          ],
          "parallel": false
        },
        {
          "step": 4,
          "description": "Health check",
          "tools": [
            {
              "tool": "Bash",
              "command": "curl -f https://staging.nlq-reporting.com/health",
              "description": "Verify app responds"
            }
          ],
          "parallel": false,
          "validation": {
            "success_if_contains": ["\"status\":\"ok\""]
          }
        },
        {
          "step": 5,
          "description": "Smoke tests",
          "tools": [
            {
              "tool": "Bash",
              "command": "npm run test:smoke -- --env staging",
              "description": "Run smoke tests against staging"
            }
          ],
          "parallel": false
        }
      ]
    },
    "prerequisites": {
      "git_repo": true,
      "tests_passing": true,
      "ssh_key_configured": true
    },
    "success_indicators": [
      "Health check passed",
      "Smoke tests passed"
    ],
    "failure_indicators": [
      "error:",
      "failed",
      "connection refused"
    ]
  }
}
```

### 5. nlq-db-refresh

**Category:** database
**Scope:** project-specific
**Project:** NLQ-Reporting

**Purpose:** Refresh NLQ-Reporting database with latest schema and test data

**Tool Sequence Definition:**

```json
{
  "agent_name": "nlq-db-refresh",
  "display_name": "NLQ Database Refresh",
  "description": "Drops and recreates mcprpt database with latest schema and test data",
  "category": "database",
  "scope": "project",
  "project_path": "/Users/jamesmba/Data/00 GITHUB/Code/NLQ-Reporting",

  "triggers": [
    {
      "trigger_phrase": "refresh the database",
      "match_type": "semantic",
      "confidence_threshold": 0.75
    },
    {
      "trigger_phrase": "reset database to clean state",
      "match_type": "semantic",
      "confidence_threshold": 0.75
    }
  ],

  "command": {
    "command_type": "tool_sequence",
    "command_definition": {
      "steps": [
        {
          "step": 1,
          "description": "Confirm action (destructive operation)",
          "action": "user_confirmation",
          "message": "⚠️  This will DROP the mcprpt database and all data. Continue?",
          "default": "no"
        },
        {
          "step": 2,
          "description": "Backup existing database",
          "tools": [
            {
              "tool": "Bash",
              "command": "pg_dump -h localhost -p 5433 -U postgres -d mcprpt > ~/backups/mcprpt_$(date +%Y%m%d_%H%M%S).sql",
              "description": "Create backup before drop",
              "continue_on_error": true
            }
          ]
        },
        {
          "step": 3,
          "description": "Drop and recreate database",
          "tools": [
            {
              "tool": "Bash",
              "command": "psql -h localhost -p 5433 -U postgres -c 'DROP DATABASE IF EXISTS mcprpt'",
              "description": "Drop existing database"
            },
            {
              "tool": "Bash",
              "command": "psql -h localhost -p 5433 -U postgres -c 'CREATE DATABASE mcprpt'",
              "description": "Create fresh database"
            }
          ],
          "parallel": false
        },
        {
          "step": 4,
          "description": "Run migrations",
          "tools": [
            {
              "tool": "Bash",
              "command": "npm run migrate",
              "description": "Apply all migrations"
            }
          ]
        },
        {
          "step": 5,
          "description": "Seed test data",
          "tools": [
            {
              "tool": "Bash",
              "command": "npm run seed",
              "description": "Load test data"
            }
          ]
        },
        {
          "step": 6,
          "description": "Verify schema",
          "tools": [
            {
              "tool": "Bash",
              "command": "psql -h localhost -p 5433 -U postgres -d mcprpt -c '\\dt'",
              "description": "List tables"
            }
          ],
          "validation": {
            "success_if_contains": ["reports", "users", "sessions"]
          }
        }
      ]
    },
    "prerequisites": {
      "database_accessible": true
    },
    "success_indicators": ["Schema verified"],
    "failure_indicators": ["error:", "failed"]
  }
}
```

---

## Agent Spawn Skills

### 6. scaffold-nlq-feature

**Category:** scaffolding
**Scope:** project-specific
**Project:** NLQ-Reporting

**Purpose:** Create a new feature module following NLQ-Reporting architecture

**Agent Spawn Definition:**

```json
{
  "agent_name": "scaffold-nlq-feature",
  "display_name": "Scaffold NLQ-Reporting Feature",
  "description": "Creates a complete feature module with frontend, routes, controller, and service",
  "category": "scaffolding",
  "scope": "project",
  "project_path": "/Users/jamesmba/Data/00 GITHUB/Code/NLQ-Reporting",

  "triggers": [
    {
      "trigger_phrase": "create a new feature",
      "match_type": "semantic",
      "confidence_threshold": 0.70
    },
    {
      "trigger_phrase": "scaffold feature module",
      "match_type": "semantic",
      "confidence_threshold": 0.75
    },
    {
      "trigger_phrase": "add feature to the app",
      "match_type": "semantic",
      "confidence_threshold": 0.70
    }
  ],

  "command": {
    "command_type": "agent_spawn",
    "agent_config": {
      "agent_type": "general-purpose",
      "model": "sonnet",
      "run_in_background": false,
      "timeout_ms": 300000,

      "prompt_template": "Create a new feature module '{feature_name}' for NLQ-Reporting following our established architecture:\n\n## Frontend\n\n1. Create `public/js/features/{feature_name}/{FeatureName}.js`\n   - Export class {FeatureName}Feature\n   - Implement activate(), render(), destroy() methods\n   - Follow pattern from existing features (ai-assist, manual-build, ai-chat)\n\n## Backend\n\n2. Create route file `src/routes/{route_name}.js`\n   - Import express Router\n   - Define API endpoints\n   - Return 501 Not Implemented stubs for now\n   - Export router\n\n3. Create controller `src/controllers/{feature_name}Controller.js`\n   - Implement route handlers\n   - Call service layer\n   - Handle errors with try/catch\n   - Return JSON responses\n\n4. Create service `src/services/{feature_name}Service.js`\n   - Implement business logic\n   - Database operations\n   - Return data to controller\n\n## Integration\n\n5. Update `src/routes/index.js`\n   - Import new route file\n   - Register route: router.use('/{route_name}', {route_name}Routes)\n\n6. Update `public/js/app.js`\n   - Import {FeatureName}Feature\n   - Initialize in constructor\n   - Add to switchMode() cases\n\n7. Update `public/index.html` (if needed)\n   - Add mode selector button\n   - Add feature container div\n\n## Documentation\n\n8. Add TODO comments for Week X implementation\n9. Follow exact naming conventions\n10. Maintain consistent code style\n\n**Parameters:**\n- feature_name: {feature_name} (kebab-case)\n- route_name: {route_name}\n- FeatureName: {FeatureName} (PascalCase)\n\n**Example:**\n- feature_name: \"data-export\"\n- route_name: \"export\"\n- FeatureName: \"DataExport\"",

      "parameters": [
        {
          "name": "feature_name",
          "type": "string",
          "required": true,
          "description": "Feature name in kebab-case (e.g., 'data-export')"
        },
        {
          "name": "route_name",
          "type": "string",
          "required": true,
          "description": "Route path (e.g., 'export' for /api/export/*)"
        },
        {
          "name": "FeatureName",
          "type": "string",
          "required": false,
          "description": "PascalCase class name (auto-generated from feature_name if not provided)"
        }
      ]
    },
    "prerequisites": {
      "in_project_directory": true,
      "package_json_exists": true
    },
    "success_indicators": [
      "Feature scaffolding complete",
      "files created"
    ],
    "failure_indicators": [
      "error:",
      "failed to create"
    ]
  }
}
```

### 7. explore-auth-implementation

**Category:** codebase-exploration
**Scope:** global

**Purpose:** Find all authentication-related code in any project

**Agent Spawn Definition:**

```json
{
  "agent_name": "explore-auth-implementation",
  "display_name": "Explore Authentication Implementation",
  "description": "Uses Explore agent to find all authentication-related code",
  "category": "codebase-exploration",
  "scope": "global",

  "triggers": [
    {
      "trigger_phrase": "find authentication code",
      "match_type": "semantic",
      "confidence_threshold": 0.75
    },
    {
      "trigger_phrase": "where is auth handled",
      "match_type": "semantic",
      "confidence_threshold": 0.75
    },
    {
      "trigger_phrase": "explore authentication implementation",
      "match_type": "semantic",
      "confidence_threshold": 0.80
    }
  ],

  "command": {
    "command_type": "agent_spawn",
    "agent_config": {
      "agent_type": "Explore",
      "model": "haiku",
      "run_in_background": false,
      "timeout_ms": 60000,

      "prompt_template": "Find all files and code related to {topic} in this codebase.\n\nPlease:\n\n1. Search for relevant files using patterns like:\n   - **/auth*.js, **/login*.js, **/session*.js\n   - Files containing keywords: authentication, authorization, JWT, session, login, logout\n\n2. Read key files to understand the implementation\n\n3. Return a structured summary:\n   - **Main Files**: List file paths with brief descriptions\n   - **Authentication Method**: What's being used (JWT, session cookies, OAuth, etc.)\n   - **Key Functions**: Important functions/middleware\n   - **Storage**: Where are credentials/sessions stored\n   - **Dependencies**: Relevant packages (passport, bcrypt, jsonwebtoken, etc.)\n\n4. Highlight any security concerns if noticed\n\nTopic: {topic}",

      "parameters": [
        {
          "name": "topic",
          "type": "string",
          "required": false,
          "default": "authentication",
          "description": "Topic to explore (authentication, authorization, sessions, etc.)"
        }
      ]
    },
    "prerequisites": {},
    "success_indicators": ["Main Files:", "Authentication Method:"],
    "failure_indicators": ["error:", "no files found"]
  }
}
```

### 8. plan-feature-implementation

**Category:** planning
**Scope:** global

**Purpose:** Use Plan agent to design implementation strategy

**Agent Spawn Definition:**

```json
{
  "agent_name": "plan-feature-implementation",
  "display_name": "Plan Feature Implementation",
  "description": "Uses Plan agent to design implementation approach for a feature",
  "category": "planning",
  "scope": "global",

  "triggers": [
    {
      "trigger_phrase": "plan how to implement",
      "match_type": "semantic",
      "confidence_threshold": 0.75
    },
    {
      "trigger_phrase": "design implementation for",
      "match_type": "semantic",
      "confidence_threshold": 0.75
    }
  ],

  "command": {
    "command_type": "agent_spawn",
    "agent_config": {
      "agent_type": "Plan",
      "model": "sonnet",
      "run_in_background": false,
      "timeout_ms": 180000,

      "prompt_template": "Create an implementation plan for: {feature_description}\n\nPlease:\n\n1. **Explore Current Codebase**\n   - Identify similar features\n   - Find relevant patterns and conventions\n   - Locate files that will need modification\n\n2. **Design Approach**\n   - Break down into logical steps\n   - Identify critical files to modify/create\n   - Consider architectural trade-offs\n   - Flag potential risks or challenges\n\n3. **Create Implementation Plan**\n   - Step-by-step tasks\n   - File-by-file changes\n   - Dependencies and order of operations\n   - Testing strategy\n\n4. **Estimate Complexity**\n   - Simple/Medium/Complex\n   - Estimated file count\n   - Key challenges\n\nFeature: {feature_description}",

      "parameters": [
        {
          "name": "feature_description",
          "type": "string",
          "required": true,
          "description": "Description of feature to implement"
        }
      ]
    },
    "prerequisites": {},
    "success_indicators": [
      "Implementation Plan:",
      "Step-by-step"
    ],
    "failure_indicators": ["error:"]
  }
}
```

---

## Cross-Project Skills

### 9. git-create-pr

**Category:** git
**Scope:** global
**Works in:** Any git repository

**Purpose:** Create GitHub pull request with proper formatting

**Tool Sequence Definition:**

```json
{
  "agent_name": "git-create-pr",
  "display_name": "Create GitHub Pull Request",
  "description": "Creates PR with summary, test plan, and proper formatting",
  "category": "git",
  "scope": "global",

  "triggers": [
    {
      "trigger_phrase": "create a pull request",
      "match_type": "semantic",
      "confidence_threshold": 0.80
    },
    {
      "trigger_phrase": "make a PR",
      "match_type": "semantic",
      "confidence_threshold": 0.75
    }
  ],

  "command": {
    "command_type": "tool_sequence",
    "command_definition": {
      "steps": [
        {
          "step": 1,
          "description": "Analyze ALL commits in PR scope",
          "tools": [
            {
              "tool": "Bash",
              "command": "git log origin/main..HEAD --oneline",
              "description": "List all commits to be included"
            },
            {
              "tool": "Bash",
              "command": "git diff origin/main...HEAD --stat",
              "description": "Show files changed"
            },
            {
              "tool": "Bash",
              "command": "git diff origin/main...HEAD",
              "description": "Full diff for analysis"
            }
          ],
          "parallel": false
        },
        {
          "step": 2,
          "description": "Ensure branch is pushed",
          "tools": [
            {
              "tool": "Bash",
              "command": "git push -u origin HEAD",
              "description": "Push current branch to remote"
            }
          ]
        },
        {
          "step": 3,
          "description": "Draft PR summary from ALL commits",
          "action": "analyze_commits_and_draft_pr",
          "inputs": {
            "commits": "{step1.tool1.output}",
            "file_stats": "{step1.tool2.output}",
            "full_diff": "{step1.tool3.output}"
          },
          "rules": [
            "Analyze ALL commits, not just latest",
            "Summarize overall changes in 1-3 bullet points",
            "Create test plan checklist",
            "Add Claude Code footer"
          ]
        },
        {
          "step": 4,
          "description": "Create PR using gh CLI",
          "tools": [
            {
              "tool": "Bash",
              "command": "gh pr create --title \"{step3.pr_title}\" --body \"$(cat <<'EOF'\\n{step3.pr_body}\\nEOF\\n)\"",
              "description": "Create PR with formatted body"
            }
          ]
        },
        {
          "step": 5,
          "description": "Display PR URL",
          "tools": [
            {
              "tool": "Bash",
              "command": "gh pr view --web",
              "description": "Open PR in browser"
            }
          ]
        }
      ]
    },
    "prerequisites": {
      "git_repo": true,
      "gh_cli_installed": true,
      "has_commits": true
    },
    "success_indicators": ["pull request created"],
    "failure_indicators": ["error:", "failed"]
  }
}
```

### 10. env-validation

**Category:** configuration
**Scope:** global
**Works in:** Any project with .env files

**Purpose:** Validate environment configuration against .env.example

**Tool Sequence Definition:**

```json
{
  "agent_name": "env-validation",
  "display_name": "Environment Variable Validation",
  "description": "Checks .env file against .env.example for missing or invalid variables",
  "category": "configuration",
  "scope": "global",

  "triggers": [
    {
      "trigger_phrase": "validate environment variables",
      "match_type": "semantic",
      "confidence_threshold": 0.75
    },
    {
      "trigger_phrase": "check env file",
      "match_type": "semantic",
      "confidence_threshold": 0.70
    }
  ],

  "command": {
    "command_type": "tool_sequence",
    "command_definition": {
      "steps": [
        {
          "step": 1,
          "description": "Check if .env files exist",
          "tools": [
            {
              "tool": "Bash",
              "command": "test -f .env && echo 'exists' || echo 'missing'",
              "description": "Check .env existence"
            },
            {
              "tool": "Bash",
              "command": "test -f .env.example && echo 'exists' || echo 'missing'",
              "description": "Check .env.example existence"
            }
          ],
          "parallel": true,
          "validation": {
            "success_if_contains": ["exists"]
          }
        },
        {
          "step": 2,
          "description": "Extract required variables from .env.example",
          "tools": [
            {
              "tool": "Read",
              "file_path": ".env.example",
              "description": "Read template file"
            }
          ]
        },
        {
          "step": 3,
          "description": "Check for missing variables",
          "action": "compare_env_files",
          "inputs": {
            "example_content": "{step2.tool1.content}"
          },
          "logic": [
            "Parse .env.example for variable names",
            "Check if each exists in .env",
            "Report missing variables",
            "Check for dummy values (placeholder values not updated)"
          ]
        },
        {
          "step": 4,
          "description": "Validate variable formats",
          "action": "validate_env_formats",
          "validations": [
            {
              "var": "*_PORT",
              "pattern": "^[0-9]+$",
              "error": "Port must be numeric"
            },
            {
              "var": "*_API_KEY",
              "pattern": "^[a-zA-Z0-9_-]+$",
              "error": "API key format invalid"
            },
            {
              "var": "*_URL",
              "pattern": "^https?://",
              "error": "URL must start with http:// or https://"
            }
          ]
        }
      ]
    },
    "prerequisites": {
      "env_example_exists": true
    },
    "success_indicators": ["All required variables present"],
    "failure_indicators": [
      "missing variables",
      "invalid format"
    ]
  }
}
```

---

## Temporal Skills

### 11. friday-deployment-checklist

**Category:** deployment
**Scope:** global
**Temporal:** Friday afternoons

**Purpose:** Pre-deployment checklist for Friday releases

**Tool Sequence Definition:**

```json
{
  "agent_name": "friday-deployment-checklist",
  "display_name": "Friday Deployment Checklist",
  "description": "Pre-deployment safety checks for Friday releases",
  "category": "deployment",
  "scope": "global",
  "temporal_pattern": {
    "day_of_week": "Friday",
    "time_of_day": "afternoon"
  },

  "triggers": [
    {
      "trigger_phrase": "friday deployment checklist",
      "match_type": "exact",
      "confidence_threshold": 1.0
    }
  ],

  "command": {
    "command_type": "tool_sequence",
    "command_definition": {
      "steps": [
        {
          "step": 1,
          "description": "Pre-deployment safety checks",
          "checklist": [
            "All tests passing?",
            "Code reviewed and approved?",
            "Database migrations tested?",
            "Rollback plan documented?",
            "Monitoring alerts configured?",
            "On-call engineer available over weekend?"
          ]
        },
        {
          "step": 2,
          "description": "Run full test suite",
          "tools": [
            {
              "tool": "Bash",
              "command": "npm test -- --coverage",
              "description": "Run tests with coverage"
            }
          ]
        },
        {
          "step": 3,
          "description": "Check for critical issues",
          "tools": [
            {
              "tool": "Bash",
              "command": "npm run lint",
              "description": "Check for lint errors"
            },
            {
              "tool": "Bash",
              "command": "npm audit --audit-level=high",
              "description": "Check for high-severity security issues"
            }
          ],
          "parallel": true
        },
        {
          "step": 4,
          "description": "Verify deployment documentation",
          "tools": [
            {
              "tool": "Read",
              "file_path": "DEPLOYMENT.md",
              "description": "Check deployment docs exist"
            }
          ]
        },
        {
          "step": 5,
          "description": "Final confirmation",
          "action": "user_confirmation",
          "message": "⚠️  Friday Deployment - Are you sure? Consider waiting until Monday.",
          "options": ["Deploy Now", "Wait Until Monday", "Cancel"]
        }
      ]
    },
    "prerequisites": {
      "tests_passing": true
    }
  }
}
```

---

## Skill Statistics

**Total Example Skills:** 11

**By Category:**
- git: 2
- database: 3
- deployment: 2
- scaffolding: 1
- codebase-exploration: 1
- planning: 1
- configuration: 1

**By Type:**
- bash_script: 2
- tool_sequence: 7
- agent_spawn: 3

**By Scope:**
- global: 8
- project-specific: 3

**Complexity:**
- Simple (1-2 steps): 2
- Medium (3-4 steps): 4
- Complex (5+ steps): 5

---

## Using These Examples

### For Phase 1 Development

Start with bash script skills:
1. `check-db-health`
2. `backup-claude-memory`

### For Phase 2 Development

Implement tool sequences:
1. `git-commit-protocol` (v1 - without tests)
2. `git-create-pr`
3. `env-validation`

### For Phase 2 Testing (Agent Spawning)

Test agent spawn skills:
1. `explore-auth-implementation`
2. `plan-feature-implementation`

### For Phase 3 Pattern Detection

These skills could be detected as patterns:
- `git-commit-protocol`: Tool sequence pattern (detected after 3 manual commits)
- `env-validation`: User correction pattern ("Always check .env.example first")

### For Phase 4 Evolution

Evolution example:
- `git-commit-protocol` v1 → v2 (added optional tests based on user feedback)

---

**Document Version:** 1.0
**Last Updated:** 2025-12-26
**Purpose:** Validate architecture with concrete examples
