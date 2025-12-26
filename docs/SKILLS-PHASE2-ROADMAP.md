# Skills System - Phase 2 Implementation Roadmap

**Phase:** Intelligence (Weeks 3-4 of 4-week implementation)
**Goal:** Semantic matching, tool sequences, agent spawning, analytics, and natural language skill creation
**Status:** Planning
**Prerequisites:** Phase 1 complete
**Target Duration:** 2 weeks
**Target Completion:** End of Week 4 (Production-ready Skills System)

---

## Phase 2 Overview

### What We're Building

Advanced skill capabilities that complete the Skills System:
1. **Semantic trigger matching** - Find skills using embedding similarity, not just exact phrases
2. **Tool sequence execution** - Execute multi-step workflows (git status → diff → commit)
3. **Agent spawning** - Skills that launch specialized agents (Explore, Plan, etc.)
4. **Performance analytics** - Detailed stats via `/mem-skills-stats`
5. **Export/import** - Share skills across projects and users
6. **Natural Language Skill Creation** - Describe skills in plain language, system generates implementation

### What We're NOT Building in Phase 2

- ❌ Automatic pattern detection (deferred to future)
- ❌ Watcher agent analysis (deferred to future)
- ❌ End-of-session skill suggestions (deferred to future)
- ❌ Automatic skill evolution (deferred to future)
- ❌ Cross-session learning (deferred to future)

**Note:** Phases 3-4 (Watcher and Self-Learning) are deferred. See `SKILLS-FUTURE-ENHANCEMENTS.md` for details.

**After Phase 2:** Production-ready Skills System with all core capabilities!

---

## Phase 2 Foundation

### From Phase 1

Phase 1 delivered:
- ✅ Database schema with 5 tables
- ✅ Manual skill creation (`/mem-skills-create`)
- ✅ Skill listing (`/mem-skills`)
- ✅ Skill inspection (`/mem-skills-show`)
- ✅ Bash script execution with approval
- ✅ Performance logging

### Phase 2 Builds On

We'll extend Phase 1 with:
- **Smarter matching** - Semantic search instead of exact phrases
- **Complex execution** - Multi-step tool sequences and agents
- **Better insights** - Analytics and performance tracking
- **Portability** - Export/import for skill sharing

---

## Milestones

### Milestone 1: Embedding Generation (Days 1-3)

**Goal:** Generate embeddings for skill triggers to enable semantic matching

**Background:**
Phase 1 used exact phrase matching. Phase 2 uses vector embeddings so:
- "commit changes" matches "create a commit" (semantic similarity)
- "check database health" matches "verify postgres is running"
- User variations automatically work without adding every phrase

**Tasks:**
- [ ] Create `generate-trigger-embeddings.py` script
- [ ] Integrate with sentence-transformers model
- [ ] Backfill embeddings for existing triggers
- [ ] Add embedding generation to skill creation flow
- [ ] Test embedding similarity calculations
- [ ] Document embedding generation process

**Implementation Details:**

#### generate-trigger-embeddings.py

```python
#!/usr/bin/env python3
"""
Generate embeddings for skill triggers

Uses sentence-transformers/all-MiniLM-L6-v2 (384 dimensions)
Same model as used for snapshot embeddings

Usage:
  # Generate for specific trigger
  python3 generate-trigger-embeddings.py --trigger-id 5

  # Backfill all triggers missing embeddings
  python3 generate-trigger-embeddings.py --backfill

  # Regenerate all embeddings
  python3 generate-trigger-embeddings.py --regenerate
"""

import argparse
import psycopg2
import numpy as np
from sentence_transformers import SentenceTransformer
import os

# Load model (same as snapshot embeddings)
MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'
model = SentenceTransformer(MODEL_NAME)

def generate_embedding(text):
    """Generate 384-dim embedding for text"""
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()

def generate_trigger_embedding(trigger_id, trigger_phrase):
    """Generate and store embedding for a single trigger"""

    conn = psycopg2.connect(
        host=os.environ.get('POSTGRES_HOST', 'localhost'),
        port=int(os.environ.get('POSTGRES_PORT', 5432)),
        database='claude_memory',
        user='postgres',
        password=os.environ.get('POSTGRES_PASSWORD')
    )

    cur = conn.cursor()

    try:
        # Generate embedding
        print(f"Generating embedding for trigger {trigger_id}: '{trigger_phrase}'")
        embedding = generate_embedding(trigger_phrase)

        # Store in database
        cur.execute("""
            UPDATE skills_triggers
            SET embedding = %s
            WHERE id = %s
        """, (embedding, trigger_id))

        conn.commit()
        print(f"✅ Embedding stored for trigger {trigger_id}")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def backfill_embeddings():
    """Generate embeddings for all triggers missing them"""

    conn = psycopg2.connect(...)
    cur = conn.cursor()

    # Find triggers with semantic matching but no embedding
    cur.execute("""
        SELECT id, trigger_phrase
        FROM skills_triggers
        WHERE match_type = 'semantic'
          AND embedding IS NULL
          AND is_active = TRUE
    """)

    triggers = cur.fetchall()
    total = len(triggers)

    print(f"Found {total} triggers needing embeddings")

    cur.close()
    conn.close()

    for i, (trigger_id, phrase) in enumerate(triggers, 1):
        print(f"[{i}/{total}] ", end='')
        generate_trigger_embedding(trigger_id, phrase)

    print(f"\n✅ Backfill complete: {total} embeddings generated")

def regenerate_all():
    """Regenerate all embeddings (for model updates)"""

    conn = psycopg2.connect(...)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, trigger_phrase
        FROM skills_triggers
        WHERE match_type = 'semantic'
          AND is_active = TRUE
    """)

    triggers = cur.fetchall()
    total = len(triggers)

    print(f"Regenerating {total} embeddings")

    cur.close()
    conn.close()

    for i, (trigger_id, phrase) in enumerate(triggers, 1):
        print(f"[{i}/{total}] ", end='')
        generate_trigger_embedding(trigger_id, phrase)

    print(f"\n✅ Regeneration complete: {total} embeddings updated")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--trigger-id', type=int, help='Generate for specific trigger')
    parser.add_argument('--backfill', action='store_true', help='Generate for triggers missing embeddings')
    parser.add_argument('--regenerate', action='store_true', help='Regenerate all embeddings')

    args = parser.parse_args()

    if args.trigger_id:
        # Need to fetch phrase
        conn = psycopg2.connect(...)
        cur = conn.cursor()
        cur.execute("SELECT trigger_phrase FROM skills_triggers WHERE id = %s", (args.trigger_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()

        if result:
            generate_trigger_embedding(args.trigger_id, result[0])
        else:
            print(f"❌ Trigger {args.trigger_id} not found")

    elif args.backfill:
        backfill_embeddings()

    elif args.regenerate:
        regenerate_all()

    else:
        print("Usage: --trigger-id N | --backfill | --regenerate")
```

#### Update create-skill.py

```python
# In create-skill.py, after inserting triggers:

from generate_trigger_embeddings import generate_embedding

for trigger in triggers:
    cur.execute("""
        INSERT INTO skills_triggers
        (agent_id, trigger_phrase, match_type, confidence_threshold)
        VALUES (%s, %s, 'semantic', 0.75)
        RETURNING id
    """, (skill_id, trigger.strip()))

    trigger_id = cur.fetchone()[0]

    # Generate embedding immediately
    if match_type == 'semantic':
        embedding = generate_embedding(trigger.strip())
        cur.execute("""
            UPDATE skills_triggers
            SET embedding = %s
            WHERE id = %s
        """, (embedding, trigger_id))
```

**Validation:**
- [ ] Embeddings generate successfully
- [ ] Embeddings are 384-dimensional vectors
- [ ] Backfill works for existing triggers
- [ ] New triggers get embeddings automatically
- [ ] Similarity calculations work

**Deliverables:**
- ✅ `generate-trigger-embeddings.py` script
- ✅ Backfill script working
- ✅ Integration with skill creation
- ✅ Documentation updated

---

### Milestone 2: Semantic Search (Days 4-6)

**Goal:** Implement semantic skill matching using embeddings

**Tasks:**
- [ ] Create `search-skills-semantic.py` script
- [ ] Implement cosine similarity search
- [ ] Implement threshold filtering
- [ ] Integrate with skill suggestion flow
- [ ] Add context boosting (git repo presence, etc.)
- [ ] Test match quality and accuracy
- [ ] Document search algorithm

**Implementation Details:**

#### search-skills-semantic.py

```python
#!/usr/bin/env python3
"""
Search for skills using semantic similarity

Usage:
  python3 search-skills-semantic.py "commit these changes"
  python3 search-skills-semantic.py "check if database is running" --threshold 0.7
"""

import argparse
import psycopg2
from generate_trigger_embeddings import generate_embedding
import os
import subprocess

def check_context():
    """Check current context for boosting scores"""
    context = {
        'is_git_repo': False,
        'has_changes': False,
        'current_project': os.getcwd()
    }

    # Check if in git repo
    result = subprocess.run(['git', 'rev-parse', '--git-dir'],
                          capture_output=True, text=True)
    context['is_git_repo'] = (result.returncode == 0)

    # Check for uncommitted changes
    if context['is_git_repo']:
        result = subprocess.run(['git', 'status', '--porcelain'],
                              capture_output=True, text=True)
        context['has_changes'] = bool(result.stdout.strip())

    return context

def search_skills(query, threshold=0.75, limit=5):
    """
    Search for skills using semantic similarity

    Returns list of matches with:
    - skill details
    - similarity score
    - trigger that matched
    - context boost applied
    """

    # Generate query embedding
    query_embedding = generate_embedding(query)

    # Get current context
    context = check_context()

    conn = psycopg2.connect(...)
    cur = conn.cursor()

    # Search using vector similarity
    cur.execute("""
        SELECT
            sa.id,
            sa.agent_name,
            sa.display_name,
            sa.description,
            sa.category,
            sa.use_count,
            sa.success_rate,
            sa.confidence_score,
            sa.project_path,
            st.trigger_phrase,
            st.requires_git_repo,
            st.context_keywords,
            1 - (st.embedding <=> %s::vector) AS similarity_score
        FROM skills_triggers st
        JOIN skills_agents sa ON sa.id = st.agent_id
        WHERE st.match_type = 'semantic'
          AND st.is_active = TRUE
          AND sa.is_active = TRUE
          AND 1 - (st.embedding <=> %s::vector) >= %s
        ORDER BY similarity_score DESC
        LIMIT %s
    """, (query_embedding, query_embedding, threshold, limit * 2))  # Get 2x for filtering

    matches = []

    for row in cur.fetchall():
        (skill_id, name, display, desc, category, uses, success_rate,
         confidence, project_path, trigger, requires_git, keywords, similarity) = row

        # Context filtering
        if requires_git and not context['is_git_repo']:
            continue  # Skip if requires git but not in repo

        # Context boosting
        boost = 0
        if keywords:
            # Check if any context keywords in query
            query_lower = query.lower()
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    boost += 0.05  # +5% per matching keyword

        # Project path filtering
        if project_path and not context['current_project'].startswith(project_path):
            continue  # Skip project-specific skills outside that project

        # Final score with boost
        final_score = min(similarity + boost, 1.0)

        matches.append({
            'skill_id': skill_id,
            'agent_name': name,
            'display_name': display,
            'description': desc,
            'category': category,
            'use_count': uses,
            'success_rate': success_rate,
            'confidence_score': confidence,
            'matched_trigger': trigger,
            'similarity_score': similarity,
            'boost_applied': boost,
            'final_score': final_score
        })

    cur.close()
    conn.close()

    # Re-sort by final score and limit
    matches.sort(key=lambda x: x['final_score'], reverse=True)
    return matches[:limit]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('query', help='Search query')
    parser.add_argument('--threshold', type=float, default=0.75,
                       help='Minimum similarity threshold (0-1)')
    parser.add_argument('--limit', type=int, default=5,
                       help='Maximum results')
    parser.add_argument('--json', action='store_true',
                       help='Output as JSON')

    args = parser.parse_args()

    matches = search_skills(args.query, args.threshold, args.limit)

    if args.json:
        import json
        print(json.dumps(matches, indent=2))
    else:
        if not matches:
            print(f"No skills found matching '{args.query}' (threshold: {args.threshold})")
        else:
            print(f"\n🔍 Found {len(matches)} matching skills:\n")
            for i, match in enumerate(matches, 1):
                print(f"{i}. {match['display_name']} ({match['agent_name']})")
                print(f"   Category: {match['category']}")
                print(f"   Similarity: {match['similarity_score']:.2%}", end='')
                if match['boost_applied']:
                    print(f" + {match['boost_applied']:.2%} boost = {match['final_score']:.2%}")
                else:
                    print()
                print(f"   Matched trigger: \"{match['matched_trigger']}\"")
                print(f"   Performance: {match['use_count']} uses, {match['success_rate']:.0f}% success")
                print()
```

**Validation:**
- [ ] Semantic matching works correctly
- [ ] Threshold filtering works
- [ ] Context boosting improves relevance
- [ ] Project-specific skills filter correctly
- [ ] Match quality is good (manual testing)

**Deliverables:**
- ✅ `search-skills-semantic.py` script
- ✅ Context checking and boosting
- ✅ Integration tests
- ✅ Documentation

---

### Milestone 3: Tool Sequence Execution (Days 7-9)

**Goal:** Execute multi-step tool sequences (e.g., git status → diff → commit)

**Tasks:**
- [ ] Design tool sequence JSON format
- [ ] Create `execute-tool-sequence.py` script
- [ ] Implement sequential execution
- [ ] Implement parallel execution
- [ ] Add step validation and error handling
- [ ] Update `execute-skill.py` to handle sequences
- [ ] Create example tool sequence skill
- [ ] Test complex multi-step workflows
- [ ] Document tool sequence format

**Implementation Details:**

#### Tool Sequence Format

```json
{
  "command_type": "tool_sequence",
  "command_definition": {
    "steps": [
      {
        "step": 1,
        "description": "Check current state",
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
          }
        ],
        "parallel": true,
        "continue_on_error": false
      },
      {
        "step": 2,
        "description": "Analyze and prepare",
        "action": "custom_function",
        "function": "analyze_git_changes",
        "inputs": {
          "status": "{step1.tool1.output}",
          "diff": "{step1.tool2.output}"
        }
      },
      {
        "step": 3,
        "description": "Execute commit",
        "tools": [
          {
            "tool": "Bash",
            "command": "git add . && git commit -m \"{step2.commit_message}\"",
            "description": "Stage and commit changes"
          }
        ],
        "parallel": false
      },
      {
        "step": 4,
        "description": "Verify success",
        "tools": [
          {
            "tool": "Bash",
            "command": "git status",
            "description": "Confirm clean working tree"
          }
        ],
        "validation": {
          "success_if_contains": ["nothing to commit, working tree clean"]
        }
      }
    ]
  },
  "success_indicators": ["nothing to commit, working tree clean"],
  "failure_indicators": ["error:", "fatal:"]
}
```

#### execute-tool-sequence.py

```python
#!/usr/bin/env python3
"""
Execute a tool sequence skill

Handles multi-step workflows with:
- Sequential and parallel execution
- Variable substitution between steps
- Custom function execution
- Error handling and validation
"""

import json
import subprocess
import concurrent.futures
import re

def execute_bash_tool(command, timeout=60):
    """Execute a bash command"""
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout
    )
    return {
        'returncode': result.returncode,
        'stdout': result.stdout,
        'stderr': result.stderr,
        'success': result.returncode == 0
    }

def substitute_variables(text, context):
    """Replace {step1.output} style variables with actual values"""
    pattern = r'\{([^}]+)\}'

    def replacer(match):
        var_path = match.group(1)
        parts = var_path.split('.')

        value = context
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return match.group(0)  # Return original if can't resolve

        return str(value) if value is not None else match.group(0)

    return re.sub(pattern, replacer, text)

def execute_tool_sequence(skill_id, sequence_definition, context={}):
    """
    Execute a tool sequence

    Args:
        skill_id: Skill ID for logging
        sequence_definition: JSONB command_definition
        context: Initial context (for variable substitution)

    Returns:
        dict with outcome, results, and any errors
    """

    steps = sequence_definition['steps']
    results = {
        'outcome': 'success',
        'step_results': [],
        'context': context.copy()
    }

    for step in steps:
        step_num = step['step']
        print(f"\nStep {step_num}/{len(steps)}: {step['description']}")

        step_result = {
            'step': step_num,
            'description': step['description'],
            'tools': []
        }

        # Handle custom actions
        if 'action' in step:
            if step['action'] == 'custom_function':
                # Execute custom function (would be implemented separately)
                func_name = step['function']
                inputs = step.get('inputs', {})

                # Substitute variables in inputs
                resolved_inputs = {}
                for key, value in inputs.items():
                    resolved_inputs[key] = substitute_variables(str(value), results['context'])

                # Call custom function (placeholder)
                print(f"   Calling custom function: {func_name}")
                # function_result = globals()[func_name](resolved_inputs)
                function_result = {'commit_message': 'Example commit message'}  # Placeholder

                # Store in context
                results['context'][f'step{step_num}'] = function_result
                step_result['function_result'] = function_result

        # Handle tool execution
        elif 'tools' in step:
            tools = step['tools']
            parallel = step.get('parallel', False)

            if parallel:
                # Execute tools in parallel
                print(f"   Executing {len(tools)} tools in parallel...")
                with concurrent.futures.ThreadPoolExecutor(max_workers=len(tools)) as executor:
                    futures = []
                    for tool in tools:
                        command = substitute_variables(tool['command'], results['context'])
                        futures.append(executor.submit(execute_bash_tool, command))

                    tool_results = [f.result() for f in futures]
            else:
                # Execute tools sequentially
                print(f"   Executing {len(tools)} tools sequentially...")
                tool_results = []
                for tool in tools:
                    command = substitute_variables(tool['command'], results['context'])
                    result = execute_bash_tool(command)
                    tool_results.append(result)

                    # Stop if error and continue_on_error is False
                    if not result['success'] and not step.get('continue_on_error', False):
                        print(f"   ❌ Tool failed, stopping")
                        results['outcome'] = 'failed'
                        results['error_step'] = step_num
                        results['step_results'].append(step_result)
                        return results

            # Store tool results
            step_result['tools'] = tool_results

            # Store in context for later steps
            results['context'][f'step{step_num}'] = {
                f'tool{i+1}': {'output': tr['stdout']} for i, tr in enumerate(tool_results)
            }

            # Validation
            if 'validation' in step:
                validation = step['validation']
                all_output = '\n'.join([tr['stdout'] for tr in tool_results])

                if 'success_if_contains' in validation:
                    for pattern in validation['success_if_contains']:
                        if pattern not in all_output:
                            print(f"   ⚠️  Validation failed: '{pattern}' not found")
                            results['outcome'] = 'validation_failed'
                            results['validation_error'] = f"Pattern not found: {pattern}"

        results['step_results'].append(step_result)

        # Check if we should stop
        if results['outcome'] != 'success':
            break

        print(f"   ✅ Step {step_num} complete")

    return results
```

**Example Tool Sequence Skill:**

```python
# Create git-commit-sequence skill
skill_data = {
    "agent_name": "git-commit-sequence",
    "display_name": "Git Commit Workflow",
    "category": "git",
    "description": "Complete git commit workflow with analysis",
    "command_type": "tool_sequence",
    "command_definition": {
        "steps": [
            {
                "step": 1,
                "description": "Check git status and changes",
                "tools": [
                    {"tool": "Bash", "command": "git status"},
                    {"tool": "Bash", "command": "git diff"},
                    {"tool": "Bash", "command": "git log --oneline -5"}
                ],
                "parallel": True
            },
            {
                "step": 2,
                "description": "Add and commit",
                "tools": [
                    {"tool": "Bash", "command": "git add ."},
                    {"tool": "Bash", "command": "git commit -m 'Auto commit'"}
                ],
                "parallel": False
            },
            {
                "step": 3,
                "description": "Verify",
                "tools": [
                    {"tool": "Bash", "command": "git status"}
                ],
                "validation": {
                    "success_if_contains": ["nothing to commit"]
                }
            }
        ]
    }
}
```

**Validation:**
- [ ] Sequential execution works
- [ ] Parallel execution works
- [ ] Variable substitution works
- [ ] Error handling stops execution appropriately
- [ ] Validation detects success/failure
- [ ] Complex workflows execute correctly

**Deliverables:**
- ✅ `execute-tool-sequence.py` script
- ✅ Tool sequence format documented
- ✅ Example skills created
- ✅ Integration with execute-skill.py
- ✅ Tests passing

---

### Milestone 4: Agent Spawning (Days 10-11)

**Goal:** Skills can spawn specialized agents (Explore, Plan, general-purpose)

**Tasks:**
- [ ] Design agent spawn configuration format
- [ ] Create `execute-agent-spawn.py` script
- [ ] Implement agent spawning via Task tool
- [ ] Handle agent results and logging
- [ ] Create example agent-spawn skills
- [ ] Test agent execution and result capture
- [ ] Document agent spawn format

**Implementation Details:**

#### Agent Spawn Format

```json
{
  "command_type": "agent_spawn",
  "agent_config": {
    "agent_type": "general-purpose",
    "model": "sonnet",
    "prompt_template": "Create a new feature module '{feature_name}' following our established architecture:\n\n1. Create public/js/features/{feature_name}/{FeatureName}.js\n2. Add route to src/routes/{route_name}.js\n3. Create controller in src/controllers/{feature_name}Controller.js\n4. Create service in src/services/{feature_name}Service.js\n5. Update src/routes/index.js\n6. Update public/js/app.js\n\nFollow exact naming conventions from existing features.",
    "parameters": [
      {"name": "feature_name", "type": "string", "required": true},
      {"name": "route_name", "type": "string", "required": true}
    ],
    "run_in_background": false,
    "timeout_ms": 300000
  }
}
```

#### execute-agent-spawn.py

```python
#!/usr/bin/env python3
"""
Execute agent-spawn skills

This is a conceptual implementation - actual integration would
happen within Claude Code's Python context where the Task tool
is available.
"""

def execute_agent_spawn(skill_id, agent_config, parameters):
    """
    Spawn an agent using the Task tool

    Args:
        skill_id: Skill ID for logging
        agent_config: Agent configuration from skills_commands
        parameters: User-provided parameter values

    Returns:
        dict with agent_id, result, and performance metrics
    """

    # Validate parameters
    required_params = [p['name'] for p in agent_config['parameters'] if p.get('required')]
    for param in required_params:
        if param not in parameters:
            return {
                'outcome': 'failed',
                'error': f"Missing required parameter: {param}"
            }

    # Build prompt from template
    prompt = agent_config['prompt_template']
    for param_name, param_value in parameters.items():
        prompt = prompt.replace(f'{{{param_name}}}', str(param_value))

    # Spawn agent (this would use the Task tool in actual implementation)
    print(f"\n⚡ Spawning {agent_config['agent_type']} agent...")
    print(f"   Model: {agent_config.get('model', 'default')}")
    print(f"   Background: {agent_config.get('run_in_background', False)}")

    # Conceptual Task tool usage:
    # result = task_tool.spawn(
    #     agent_type=agent_config['agent_type'],
    #     prompt=prompt,
    #     model=agent_config.get('model'),
    #     run_in_background=agent_config.get('run_in_background', False),
    #     timeout=agent_config.get('timeout_ms', 120000)
    # )

    # Placeholder result
    result = {
        'agent_id': 'agent-12345',
        'outcome': 'success',
        'result_summary': 'Agent completed successfully',
        'execution_time_ms': 45000
    }

    print(f"   ✅ Agent {result['agent_id']} completed")

    return result
```

**Example Agent Spawn Skills:**

```python
# Skill 1: scaffold-nlq-feature
{
    "agent_name": "scaffold-nlq-feature",
    "display_name": "Scaffold NLQ-Reporting Feature",
    "category": "scaffolding",
    "project_path": "/Users/jamesmba/Data/00 GITHUB/Code/NLQ-Reporting",
    "command_type": "agent_spawn",
    "agent_config": {
        "agent_type": "general-purpose",
        "model": "sonnet",
        "prompt_template": "Create feature module '{feature_name}'...",
        "parameters": [
            {"name": "feature_name", "type": "string", "required": true},
            {"name": "route_name", "type": "string", "required": true}
        ],
        "run_in_background": false
    },
    "triggers": [
        "create a new feature",
        "scaffold feature module",
        "add feature to the app"
    ]
}

# Skill 2: explore-auth-files
{
    "agent_name": "explore-auth-files",
    "display_name": "Find Authentication Files",
    "category": "codebase-exploration",
    "command_type": "agent_spawn",
    "agent_config": {
        "agent_type": "Explore",
        "model": "haiku",
        "prompt_template": "Find all files related to {topic} in the codebase. Return file paths and brief descriptions.",
        "parameters": [
            {"name": "topic", "type": "string", "required": true, "default": "authentication"}
        ],
        "run_in_background": false,
        "timeout_ms": 60000
    },
    "triggers": [
        "find auth files",
        "where is authentication handled",
        "explore authentication code"
    ]
}
```

**Validation:**
- [ ] Agents spawn correctly
- [ ] Parameters are passed correctly
- [ ] Agent results are captured
- [ ] Background execution works
- [ ] Timeouts work
- [ ] Performance is logged

**Deliverables:**
- ✅ `execute-agent-spawn.py` script
- ✅ Integration plan with Task tool
- ✅ Example agent-spawn skills
- ✅ Documentation

---

### Milestone 5: Performance Analytics (Days 12-13)

**Goal:** `/mem-skills-stats` command for detailed performance analysis

**Tasks:**
- [ ] Create `skills-stats.py` script
- [ ] Implement performance aggregation
- [ ] Create trend analysis (7-day, 30-day)
- [ ] Generate usage charts (ASCII or data for visualization)
- [ ] Create `/mem-skills-stats` skill file
- [ ] Test with real performance data
- [ ] Document analytics features

**Implementation Details:**

#### skills-stats.py

```python
#!/usr/bin/env python3
"""
Show detailed performance statistics for a skill

Usage:
  python3 skills-stats.py git-commit-protocol
  python3 skills-stats.py --all
  python3 skills-stats.py --category git
"""

import argparse
import psycopg2
from datetime import datetime, timedelta
from tabulate import tabulate

def get_skill_stats(skill_name):
    """Get detailed stats for a single skill"""

    conn = psycopg2.connect(...)
    cur = conn.cursor()

    # Overall stats
    cur.execute("""
        SELECT
            agent_name,
            display_name,
            category,
            use_count,
            success_count,
            failure_count,
            success_rate,
            avg_time_saved_ms,
            total_time_saved_ms,
            confidence_score,
            last_used,
            created_at
        FROM skills_agents
        WHERE agent_name = %s
    """, (skill_name,))

    skill = cur.fetchone()
    if not skill:
        print(f"❌ Skill not found: {skill_name}")
        return

    # Recent performance (last 7 days)
    cur.execute("""
        SELECT
            DATE(executed_at) as date,
            COUNT(*) as executions,
            COUNT(*) FILTER (WHERE outcome = 'success') as successes,
            AVG(execution_time_ms) as avg_time_ms
        FROM skills_performance_log
        WHERE agent_id = (SELECT id FROM skills_agents WHERE agent_name = %s)
          AND executed_at > NOW() - INTERVAL '7 days'
        GROUP BY DATE(executed_at)
        ORDER BY date DESC
    """, (skill_name,))

    recent_perf = cur.fetchall()

    # Suggestion acceptance
    cur.execute("""
        SELECT
            COUNT(*) as total_suggestions,
            COUNT(*) FILTER (WHERE was_suggestion_accepted = TRUE) as accepted,
            COUNT(*) FILTER (WHERE was_suggestion_accepted = FALSE) as rejected
        FROM skills_performance_log
        WHERE agent_id = (SELECT id FROM skills_agents WHERE agent_name = %s)
    """, (skill_name,))

    suggestions = cur.fetchone()

    # Project usage
    cur.execute("""
        SELECT
            project_path,
            COUNT(*) as uses
        FROM skills_performance_log
        WHERE agent_id = (SELECT id FROM skills_agents WHERE agent_name = %s)
        GROUP BY project_path
        ORDER BY uses DESC
    """, (skill_name,))

    projects = cur.fetchall()

    # Last 5 executions
    cur.execute("""
        SELECT
            executed_at,
            outcome,
            execution_time_ms,
            project_path
        FROM skills_performance_log
        WHERE agent_id = (SELECT id FROM skills_agents WHERE agent_name = %s)
        ORDER BY executed_at DESC
        LIMIT 5
    """, (skill_name,))

    recent_execs = cur.fetchall()

    cur.close()
    conn.close()

    # Format output
    (name, display, category, uses, successes, failures, success_rate,
     avg_saved_ms, total_saved_ms, confidence, last_used, created) = skill

    print(f"\n{name} - Performance Statistics")
    print("=" * 60)

    print(f"\nOverall:")
    print(f"  Total Uses: {uses}")
    print(f"  Success: {successes} ({success_rate:.1f}%)")
    print(f"  Failed: {failures}")
    if avg_saved_ms:
        print(f"  Avg Time Saved: {avg_saved_ms / 1000:.1f} seconds")
        print(f"  Total Time Saved: {total_saved_ms / 1000 / 60:.1f} minutes")

    print(f"\nRecent Performance (Last 7 days):")
    if recent_perf:
        for date, execs, succs, avg_time in recent_perf:
            success_pct = (succs / execs * 100) if execs > 0 else 0
            print(f"  {date}: {execs} uses, {success_pct:.0f}% success, {avg_time/1000:.1f}s avg")
    else:
        print("  No activity in last 7 days")

    if suggestions:
        total_sug, accepted, rejected = suggestions
        if total_sug > 0:
            acceptance = (accepted / total_sug * 100)
            print(f"\nUser Acceptance:")
            print(f"  Suggested: {total_sug} times")
            print(f"  Accepted: {accepted} ({acceptance:.0f}%)")
            print(f"  Rejected: {rejected}")

    print(f"\nUsage by Project:")
    for project, count in projects[:5]:
        proj_name = project or "(unknown)"
        print(f"  {proj_name}: {count} uses")

    print(f"\nLast 5 Executions:")
    for exec_time, outcome, duration_ms, project in recent_execs:
        status = "✅" if outcome == 'success' else "❌"
        print(f"  {exec_time.strftime('%Y-%m-%d %H:%M')}  {status} {outcome:15}  {duration_ms/1000:5.1f}s  [{project or 'unknown'}]")

    print(f"\nMetadata:")
    print(f"  Category: {category}")
    print(f"  Confidence: {confidence:.2f}")
    print(f"  Created: {created.strftime('%Y-%m-%d')}")
    if last_used:
        print(f"  Last Used: {last_used.strftime('%Y-%m-%d %H:%M')} ({(datetime.now(last_used.tzinfo) - last_used).days} days ago)")
    print()

def get_all_stats():
    """Get summary stats for all skills"""

    conn = psycopg2.connect(...)
    cur = conn.cursor()

    cur.execute("""
        SELECT
            category,
            agent_name,
            display_name,
            use_count,
            success_rate,
            total_time_saved_ms / 1000 / 60 as minutes_saved
        FROM v_skills_dashboard
        WHERE use_count > 0
        ORDER BY category, use_count DESC
    """)

    skills = cur.fetchall()

    # Group by category
    by_category = {}
    for cat, name, display, uses, success, minutes in skills:
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append([name, uses, f"{success:.0f}%", f"{minutes:.1f}m"])

    print("\n📊 All Skills Performance Summary\n")

    for category, cat_skills in sorted(by_category.items()):
        print(f"{category.upper()} ({len(cat_skills)} skills)")
        print(tabulate(cat_skills,
                      headers=["Skill", "Uses", "Success", "Time Saved"],
                      tablefmt="simple"))
        print()

    cur.close()
    conn.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('skill_name', nargs='?', help='Skill name')
    parser.add_argument('--all', action='store_true', help='Show all skills')
    parser.add_argument('--category', help='Filter by category')

    args = parser.parse_args()

    if args.all:
        get_all_stats()
    elif args.skill_name:
        get_skill_stats(args.skill_name)
    else:
        print("Usage: skills-stats.py SKILL_NAME | --all")
```

#### /mem-skills-stats Skill File

```markdown
# /mem-skills-stats

Show detailed performance statistics for skills

## Usage

```bash
# Show stats for specific skill
/mem-skills-stats git-commit-protocol

# Show stats for all skills
/mem-skills-stats --all

# Show stats for specific category
/mem-skills-stats --category git
```

## Output

```
git-commit-protocol - Performance Statistics
============================================================

Overall:
  Total Uses: 23
  Success: 23 (100.0%)
  Failed: 0
  Avg Time Saved: 45.0 seconds
  Total Time Saved: 17.3 minutes

Recent Performance (Last 7 days):
  2025-12-26: 3 uses, 100% success, 7.8s avg
  2025-12-25: 5 uses, 100% success, 8.1s avg

User Acceptance:
  Suggested: 25 times
  Accepted: 23 (92%)
  Rejected: 2

Usage by Project:
  NLQ-Reporting: 12 uses
  claude-memory: 6 uses
  pgquery-dev: 5 uses
```

## Arguments

python3 /Users/jamesmba/Data/00\ GITHUB/Code/claude-memory/skills-stats.py "$@"
```

**Validation:**
- [ ] Stats display correctly
- [ ] Trend analysis works
- [ ] Project breakdown correct
- [ ] Recent executions shown
- [ ] Formatting is clear

**Deliverables:**
- ✅ `skills-stats.py` script
- ✅ `/mem-skills-stats` skill file
- ✅ Documentation

---

### Milestone 6: Export/Import (Day 14)

**Goal:** Share skills across projects with `/mem-skills-export` and `/mem-skills-import`

**Tasks:**
- [ ] Create `export-skills.py` script
- [ ] Create `import-skills.py` script
- [ ] Design export JSON format
- [ ] Handle skill dependencies
- [ ] Create selective import UI
- [ ] Test export/import workflow
- [ ] Document export/import process

**Implementation Details:**

#### Export Format

```json
{
  "export_metadata": {
    "version": "1.0",
    "exported_at": "2025-12-26T10:30:00Z",
    "exported_by": "user",
    "source_project": "/path/to/NLQ-Reporting",
    "skill_count": 12
  },
  "skills": [
    {
      "agent_name": "git-commit-protocol",
      "display_name": "Git Commit (Our Protocol)",
      "description": "...",
      "category": "git",
      "scope": "global",
      "triggers": [
        {
          "trigger_phrase": "commit these changes",
          "match_type": "semantic",
          "confidence_threshold": 0.75
        }
      ],
      "command": {
        "command_type": "bash_script",
        "script_path": "/path/to/script.sh",
        "script_content": "#!/bin/bash\n...",  // Include script content
        "parameters": {},
        "prerequisites": {"git_repo": true}
      }
    }
  ]
}
```

#### export-skills.py

```python
#!/usr/bin/env python3
"""
Export skills to JSON file

Usage:
  python3 export-skills.py output.json
  python3 export-skills.py output.json --category git
  python3 export-skills.py output.json --global-only
"""

import argparse
import psycopg2
import json
from datetime import datetime
import os

def export_skills(output_file, category=None, global_only=False, project_path=None):
    """Export skills to JSON"""

    conn = psycopg2.connect(...)
    cur = conn.cursor()

    # Build query
    query = """
        SELECT
            sa.agent_name,
            sa.display_name,
            sa.description,
            sa.category,
            sa.scope,
            sa.project_path,
            sa.version,
            sa.confidence_score
        FROM skills_agents sa
        WHERE sa.is_active = TRUE
    """

    params = []

    if category:
        query += " AND sa.category = %s"
        params.append(category)

    if global_only:
        query += " AND sa.project_path IS NULL"
    elif project_path:
        query += " AND (sa.project_path = %s OR sa.project_path IS NULL)"
        params.append(project_path)

    cur.execute(query, params)
    skills_data = cur.fetchall()

    skills_export = []

    for skill in skills_data:
        (name, display, desc, cat, scope, proj_path, version, confidence) = skill
        skill_id = get_skill_id(cur, name)

        # Get triggers
        cur.execute("""
            SELECT trigger_phrase, match_type, confidence_threshold
            FROM skills_triggers
            WHERE agent_id = %s AND is_active = TRUE
        """, (skill_id,))

        triggers = [
            {
                'trigger_phrase': phrase,
                'match_type': match_type,
                'confidence_threshold': threshold
            }
            for phrase, match_type, threshold in cur.fetchall()
        ]

        # Get command
        cur.execute("""
            SELECT command_type, script_path, command_definition, parameters, prerequisites
            FROM skills_commands
            WHERE agent_id = %s
            ORDER BY version DESC
            LIMIT 1
        """, (skill_id,))

        cmd_row = cur.fetchone()
        command = None

        if cmd_row:
            cmd_type, script_path, definition, params, prereqs = cmd_row
            command = {
                'command_type': cmd_type,
                'parameters': params,
                'prerequisites': prereqs
            }

            if cmd_type == 'bash_script' and script_path:
                # Read script content
                if os.path.exists(script_path):
                    with open(script_path, 'r') as f:
                        command['script_content'] = f.read()
                command['script_path'] = script_path

            elif cmd_type == 'tool_sequence':
                command['command_definition'] = definition

            elif cmd_type == 'agent_spawn':
                command['agent_config'] = definition

        skills_export.append({
            'agent_name': name,
            'display_name': display,
            'description': desc,
            'category': cat,
            'scope': scope,
            'project_path': proj_path,
            'version': version,
            'confidence_score': confidence,
            'triggers': triggers,
            'command': command
        })

    # Create export object
    export = {
        'export_metadata': {
            'version': '1.0',
            'exported_at': datetime.utcnow().isoformat() + 'Z',
            'exported_by': 'user',
            'source_project': project_path or 'global',
            'skill_count': len(skills_export)
        },
        'skills': skills_export
    }

    # Write to file
    with open(output_file, 'w') as f:
        json.dump(export, f, indent=2)

    print(f"✅ Exported {len(skills_export)} skills to {output_file}")
    print(f"\nBreakdown:")
    categories = {}
    for skill in skills_export:
        cat = skill['category']
        categories[cat] = categories.get(cat, 0) + 1

    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")

    cur.close()
    conn.close()

def get_skill_id(cur, agent_name):
    cur.execute("SELECT id FROM skills_agents WHERE agent_name = %s", (agent_name,))
    return cur.fetchone()[0]
```

#### import-skills.py

```python
#!/usr/bin/env python3
"""
Import skills from JSON file

Usage:
  python3 import-skills.py skills.json
  python3 import-skills.py skills.json --global-only
  python3 import-skills.py skills.json --dry-run
"""

import argparse
import psycopg2
import json
import os

def import_skills(input_file, global_only=False, dry_run=False):
    """Import skills from JSON"""

    with open(input_file, 'r') as f:
        export = json.load(f)

    skills = export['skills']

    if global_only:
        skills = [s for s in skills if s.get('scope') == 'global']

    print(f"\n📥 Importing {len(skills)} skills from {input_file}")
    print(f"   Source: {export['export_metadata'].get('source_project')}")
    print(f"   Exported: {export['export_metadata'].get('exported_at')}")

    if dry_run:
        print("\n🔍 DRY RUN - No changes will be made\n")

    # Review skills
    print("\nSkills to import:\n")
    global_skills = [s for s in skills if s.get('scope') == 'global']
    project_skills = [s for s in skills if s.get('scope') != 'global']

    if global_skills:
        print("Global Skills (recommended):")
        for skill in global_skills:
            print(f"  ✅ {skill['agent_name']} ({skill['category']})")

    if project_skills:
        print("\nProject-Specific Skills:")
        for skill in project_skills:
            print(f"  ❓ {skill['agent_name']} ({skill['category']})")
            print(f"      From: {skill.get('project_path')}")

    if dry_run:
        return

    # Confirm
    confirm = input("\nImport these skills? [y/N]: ")
    if confirm.lower() != 'y':
        print("Cancelled")
        return

    conn = psycopg2.connect(...)
    cur = conn.cursor()

    imported = 0
    skipped = 0

    for skill in skills:
        try:
            # Check if exists
            cur.execute(
                "SELECT id FROM skills_agents WHERE agent_name = %s",
                (skill['agent_name'],)
            )

            if cur.fetchone():
                print(f"⏭️  Skipping {skill['agent_name']} (already exists)")
                skipped += 1
                continue

            # Insert skill
            cur.execute("""
                INSERT INTO skills_agents
                (agent_name, display_name, description, category, scope,
                 project_path, version, confidence_score, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'imported')
                RETURNING id
            """, (
                skill['agent_name'],
                skill['display_name'],
                skill.get('description'),
                skill['category'],
                skill.get('scope', 'global'),
                skill.get('project_path'),
                skill.get('version', 1),
                skill.get('confidence_score', 0.8)
            ))

            skill_id = cur.fetchone()[0]

            # Insert triggers
            for trigger in skill.get('triggers', []):
                cur.execute("""
                    INSERT INTO skills_triggers
                    (agent_id, trigger_phrase, match_type, confidence_threshold)
                    VALUES (%s, %s, %s, %s)
                """, (
                    skill_id,
                    trigger['trigger_phrase'],
                    trigger.get('match_type', 'semantic'),
                    trigger.get('confidence_threshold', 0.75)
                ))

            # Insert command
            command = skill.get('command')
            if command:
                cmd_type = command['command_type']

                # Handle script content
                script_path = None
                if cmd_type == 'bash_script' and 'script_content' in command:
                    # Save script to ~/.claude-memory/skills/scripts/
                    scripts_dir = os.path.expanduser('~/.claude-memory/skills/scripts')
                    os.makedirs(scripts_dir, exist_ok=True)

                    script_path = os.path.join(scripts_dir, f"{skill['agent_name']}.sh")
                    with open(script_path, 'w') as f:
                        f.write(command['script_content'])
                    os.chmod(script_path, 0o755)  # Make executable

                cur.execute("""
                    INSERT INTO skills_commands
                    (agent_id, command_type, script_path, command_definition, parameters, prerequisites)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    skill_id,
                    cmd_type,
                    script_path,
                    command.get('command_definition'),
                    json.dumps(command.get('parameters', {})),
                    json.dumps(command.get('prerequisites', {}))
                ))

            print(f"✅ Imported {skill['agent_name']}")
            imported += 1

        except Exception as e:
            print(f"❌ Failed to import {skill['agent_name']}: {e}")
            conn.rollback()
            continue

    conn.commit()
    cur.close()
    conn.close()

    print(f"\n✅ Import complete:")
    print(f"   Imported: {imported}")
    print(f"   Skipped: {skipped}")
```

**Validation:**
- [ ] Export creates valid JSON
- [ ] Import handles all skill types
- [ ] Script content is preserved
- [ ] Selective import works
- [ ] Duplicate detection works

**Deliverables:**
- ✅ `export-skills.py` script
- ✅ `import-skills.py` script
- ✅ `/mem-skills-export` skill file
- ✅ `/mem-skills-import` skill file
- ✅ Documentation

---

### Enhancement: Natural Language Skill Creation

**Goal:** Create skills by describing them in plain language (Optional milestone)

**Concept:**
```bash
$ /mem-skills-create-nl "I want a skill that checks database health"

🤖 Generating skill...

Created: check-database-health
- Category: database
- Triggers: "check db health", "verify postgres"
- Type: bash_script
- Parameters: database_name

[View Details] [Create] [Cancel]
```

**Implementation:**
- Use Claude API to generate skill definition from description
- Parse natural language into: name, triggers, script/sequence, parameters
- User reviews and edits before creating
- Falls back to `create-skill.py` for actual creation

**Files:**
- `create-skill-nl.py` - Natural language skill generator
- Requires `ANTHROPIC_API_KEY` environment variable
- Cost: ~$0.01-0.02 per skill generation

This is an optional enhancement that can be added during or after Phase 2 based on user feedback.

---

## Success Criteria

Phase 2 is complete when:

- [ ] All 6 core milestones delivered
- [ ] Semantic matching works accurately
- [ ] Tool sequences execute correctly
- [ ] Agents can be spawned from skills
- [ ] Performance analytics are comprehensive
- [ ] Export/import works reliably
- [ ] Documentation is complete
- [ ] At least 5 real skills using new features created
- [ ] (Optional) Natural language skill creation works

---

## File Structure After Phase 2

```
claude-memory/
├── generate-trigger-embeddings.py (NEW)
├── search-skills-semantic.py (NEW)
├── execute-tool-sequence.py (NEW)
├── execute-agent-spawn.py (NEW)
├── skills-stats.py (NEW)
├── export-skills.py (NEW)
├── import-skills.py (NEW)
├── .claude/
│   └── commands/
│       ├── mem-skills-stats.md (NEW)
│       ├── mem-skills-export.md (NEW)
│       └── mem-skills-import.md (NEW)
└── docs/
    ├── SKILLS-SYSTEM-ARCHITECTURE.md
    ├── SKILLS-PHASE1-ROADMAP.md
    └── SKILLS-PHASE2-ROADMAP.md (THIS FILE)
```

---

## Future Enhancements (Deferred)

After Phase 2 delivers the production-ready Skills System, potential future enhancements include:

1. **Watcher agent** - Automatic pattern detection from conversations
2. **End-of-session suggestions** - "Create skill for this?"
3. **Pattern scoring** - Confidence calculation for skill candidates
4. **Skill candidates view** - `/mem-skills-suggest`
5. **Automatic skill evolution** - Skills improve based on feedback
6. **Cross-session learning** - Learn patterns across multiple sessions

**Decision:** These features are deferred to allow focus on the core Skills System foundation.

See `SKILLS-FUTURE-ENHANCEMENTS.md` for detailed specifications of deferred features.

---

## Integration with Phase 1

Phase 2 extends Phase 1 components:

| Component | Phase 1 | Phase 2 Enhancement |
|-----------|---------|---------------------|
| create-skill.py | Bash scripts only | + Tool sequences, agent spawning |
| execute-skill.py | Exact matching | + Semantic search |
| list-skills.py | Basic listing | + Performance stats integration |
| Triggers | Exact phrases | + Vector embeddings |

---

**Document Version:** 1.0
**Last Updated:** 2025-12-26
**Status:** Planning - Ready After Phase 1
**Estimated Duration:** 2 weeks (Days 1-14)
