# Skills System Testing Plan

**Version:** 1.0
**Created:** 2025-12-26
**Scope:** Phase 1 + Phase 2 (4-week implementation)
**Status:** Pre-Implementation Testing Strategy

---

## Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [Test Environment Setup](#test-environment-setup)
3. [Phase 1 Testing: Foundation](#phase-1-testing-foundation)
4. [Phase 2 Testing: Intelligence](#phase-2-testing-intelligence)
5. [Integration Testing](#integration-testing)
6. [Performance Testing](#performance-testing)
7. [Security Testing](#security-testing)
8. [Test Data & Fixtures](#test-data--fixtures)
9. [Validation Criteria](#validation-criteria)
10. [Test Execution Schedule](#test-execution-schedule)

---

## Testing Philosophy

### Core Principles

1. **Test Before Commit**: All new features must have passing tests
2. **Incremental Testing**: Test each milestone as it completes
3. **Real-World Scenarios**: Use actual claude-memory workflows as test cases
4. **Regression Protection**: Build comprehensive test suite to prevent breakage
5. **Performance Awareness**: Monitor execution time, database impact

### Testing Pyramid

```
                    /\
                   /  \
                  / E2E \          10% - End-to-End (Full workflows)
                 /------\
                /        \
               / Integration \     30% - Integration (Database + Scripts)
              /--------------\
             /                \
            /   Unit Tests      \  60% - Unit (Functions, SQL, Validation)
           /____________________\
```

### Testing Approach

- **Unit Tests**: Python unittest/pytest for individual functions
- **Integration Tests**: Database tests with real PostgreSQL + pgvector
- **End-to-End Tests**: Simulate complete skill creation → execution workflows
- **Manual Testing**: User acceptance testing for UX flows

---

## Test Environment Setup

### Prerequisites

```bash
# 1. Test database (isolated from production)
createdb claude_memory_test

# 2. Apply schema
psql -d claude_memory_test -f schema/schema.sql
psql -d claude_memory_test -f schema/add-skills-tables.sql

# 3. Install test dependencies
pip install pytest pytest-cov pytest-postgresql psycopg2-binary sentence-transformers
```

### Environment Configuration

**`.env.test`:**
```bash
# Test database
DB_NAME=claude_memory_test
DB_USER=postgres
DB_PASSWORD=your_test_password
DB_HOST=localhost
DB_PORT=5432

# Test mode flags
SKILLS_TEST_MODE=true
SKILLS_AUTO_EXECUTE=false  # Always require confirmation in tests
```

### Test Data Generation

```python
# tests/fixtures/generator.py
import psycopg2
from datetime import datetime, timedelta

def create_test_snapshots(count=50):
    """Generate test snapshots with realistic data."""
    conn = psycopg2.connect(...)
    cur = conn.cursor()

    for i in range(count):
        cur.execute("""
            INSERT INTO context_snapshots
            (project_path, summary, captured_at, message_count)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (
            f"/Users/test/project_{i % 5}",
            f"Test snapshot {i}: Implemented feature X",
            datetime.now() - timedelta(days=i),
            20 + (i * 3)
        ))

    conn.commit()
    return count

def create_test_skill(name, triggers, command_type='bash_script'):
    """Create a test skill with specified triggers."""
    # Implementation...
```

---

## Phase 1 Testing: Foundation

### Milestone 1: Database Foundation (Days 1-2)

#### Unit Tests: Schema Validation

**`tests/test_schema.py`:**
```python
import pytest
import psycopg2

class TestSkillsSchema:
    def test_skills_agents_table_exists(self, db_conn):
        """Verify skills_agents table was created."""
        cur = db_conn.cursor()
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'skills_agents'
            )
        """)
        assert cur.fetchone()[0] == True

    def test_skills_agents_required_columns(self, db_conn):
        """Verify required columns exist with correct types."""
        cur = db_conn.cursor()
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'skills_agents'
            ORDER BY ordinal_position
        """)
        columns = {row[0]: row[1] for row in cur.fetchall()}

        assert columns['id'] == 'integer'
        assert columns['agent_name'] == 'character varying'
        assert columns['description'] == 'text'
        assert columns['success_rate'] == 'double precision'

    def test_success_rate_calculated_column(self, db_conn):
        """Verify success_rate is auto-calculated correctly."""
        cur = db_conn.cursor()

        # Insert test skill
        cur.execute("""
            INSERT INTO skills_agents
            (agent_name, use_count, success_count, created_by)
            VALUES ('test-calc', 10, 7, 'test')
            RETURNING id, success_rate
        """)
        skill_id, success_rate = cur.fetchone()

        assert success_rate == 70.0  # 7/10 * 100
        db_conn.rollback()

    def test_embedding_index_exists(self, db_conn):
        """Verify HNSW index on embeddings."""
        cur = db_conn.cursor()
        cur.execute("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'skills_triggers'
            AND indexname = 'idx_skills_triggers_embedding'
        """)
        assert cur.fetchone() is not None
```

#### Integration Tests: Database Constraints

**`tests/test_constraints.py`:**
```python
class TestDatabaseConstraints:
    def test_unique_agent_name_constraint(self, db_conn):
        """Agent names must be unique."""
        cur = db_conn.cursor()

        cur.execute("""
            INSERT INTO skills_agents (agent_name, created_by)
            VALUES ('duplicate-test', 'test')
        """)

        with pytest.raises(psycopg2.errors.UniqueViolation):
            cur.execute("""
                INSERT INTO skills_agents (agent_name, created_by)
                VALUES ('duplicate-test', 'test')
            """)

        db_conn.rollback()

    def test_cascade_delete_triggers(self, db_conn):
        """Deleting skill should cascade delete triggers."""
        cur = db_conn.cursor()

        # Create skill
        cur.execute("""
            INSERT INTO skills_agents (agent_name, created_by)
            VALUES ('cascade-test', 'test')
            RETURNING id
        """)
        skill_id = cur.fetchone()[0]

        # Create trigger
        cur.execute("""
            INSERT INTO skills_triggers (agent_id, trigger_phrase)
            VALUES (%s, 'test trigger')
        """, (skill_id,))

        # Delete skill
        cur.execute("DELETE FROM skills_agents WHERE id = %s", (skill_id,))

        # Verify trigger was deleted
        cur.execute("SELECT COUNT(*) FROM skills_triggers WHERE agent_id = %s", (skill_id,))
        assert cur.fetchone()[0] == 0

        db_conn.rollback()
```

**Validation Criteria:**
- ✅ All 5 tables created successfully
- ✅ All 31 indexes exist
- ✅ All 4 views return results
- ✅ Calculated columns compute correctly
- ✅ Cascade deletes work
- ✅ Unique constraints enforced

---

### Milestone 2: Skill Creation (Days 3-5)

#### Unit Tests: create-skill.py

**`tests/test_create_skill.py`:**
```python
import subprocess
import json

class TestCreateSkill:
    def test_create_bash_skill_success(self, db_conn):
        """Create a simple bash script skill."""
        result = subprocess.run([
            'python3', 'create-skill.py',
            '--name', 'test-bash-skill',
            '--display-name', 'Test Bash Skill',
            '--description', 'A test skill',
            '--category', 'testing',
            '--command-type', 'bash_script',
            '--script-content', 'echo "Hello from skill"',
            '--triggers', 'run test skill, execute test'
        ], capture_output=True, text=True)

        assert result.returncode == 0
        assert 'Skill created successfully' in result.stdout

        # Verify in database
        cur = db_conn.cursor()
        cur.execute("""
            SELECT id, agent_name, command_type
            FROM skills_agents sa
            JOIN skills_commands sc ON sa.id = sc.agent_id
            WHERE agent_name = 'test-bash-skill'
        """)
        row = cur.fetchone()
        assert row is not None
        assert row[2] == 'bash_script'

    def test_create_skill_with_parameters(self, db_conn):
        """Create skill with required parameters."""
        result = subprocess.run([
            'python3', 'create-skill.py',
            '--name', 'param-skill',
            '--description', 'Skill with params',
            '--command-type', 'bash_script',
            '--script-content', 'echo "Project: $PROJECT_NAME"',
            '--parameters', '{"PROJECT_NAME": {"type": "string", "required": true}}',
            '--triggers', 'param test'
        ], capture_output=True, text=True)

        assert result.returncode == 0

        # Verify parameters stored
        cur = db_conn.cursor()
        cur.execute("""
            SELECT parameters FROM skills_commands sc
            JOIN skills_agents sa ON sa.id = sc.agent_id
            WHERE sa.agent_name = 'param-skill'
        """)
        params = cur.fetchone()[0]
        assert params['PROJECT_NAME']['required'] == True

    def test_create_skill_invalid_name(self):
        """Reject invalid skill names."""
        result = subprocess.run([
            'python3', 'create-skill.py',
            '--name', 'Invalid Name With Spaces',
            '--description', 'Should fail',
            '--command-type', 'bash_script',
            '--script-content', 'echo test',
            '--triggers', 'invalid'
        ], capture_output=True, text=True)

        assert result.returncode != 0
        assert 'invalid' in result.stderr.lower()

    def test_create_skill_missing_required_field(self):
        """Reject creation without required fields."""
        result = subprocess.run([
            'python3', 'create-skill.py',
            '--name', 'missing-fields',
            # Missing description, command-type, etc.
        ], capture_output=True, text=True)

        assert result.returncode != 0
```

**Validation Criteria:**
- ✅ create-skill.py creates bash script skills
- ✅ create-skill.py creates tool sequence skills
- ✅ Script content stored in database (not filesystem)
- ✅ Triggers created and linked
- ✅ Parameters validated and stored
- ✅ Input validation prevents malformed skills

---

### Milestone 3: Skill Listing (Days 6-7)

#### Unit Tests: list-skills.py

**`tests/test_list_skills.py`:**
```python
class TestListSkills:
    def test_list_all_skills(self, db_conn, sample_skills):
        """List all active skills."""
        result = subprocess.run([
            'python3', 'list-skills.py'
        ], capture_output=True, text=True)

        assert result.returncode == 0
        assert 'backup-claude-memory' in result.stdout
        assert 'git-commit-protocol' in result.stdout

    def test_filter_by_category(self, db_conn, sample_skills):
        """Filter skills by category."""
        result = subprocess.run([
            'python3', 'list-skills.py',
            '--category', 'maintenance'
        ], capture_output=True, text=True)

        assert 'backup-claude-memory' in result.stdout
        assert 'git-commit-protocol' not in result.stdout

    def test_filter_by_project(self, db_conn, sample_skills):
        """Filter skills by project path."""
        result = subprocess.run([
            'python3', 'list-skills.py',
            '--project', '/Users/test/Code/NLQ'
        ], capture_output=True, text=True)

        # Should show NLQ-specific skills + global skills
        output_lines = result.stdout.count('\n')
        assert output_lines >= 2

    def test_json_output_format(self, db_conn, sample_skills):
        """Output skills in JSON format."""
        result = subprocess.run([
            'python3', 'list-skills.py',
            '--format', 'json'
        ], capture_output=True, text=True)

        skills = json.loads(result.stdout)
        assert isinstance(skills, list)
        assert len(skills) > 0
        assert 'agent_name' in skills[0]
        assert 'success_rate' in skills[0]
```

**Validation Criteria:**
- ✅ List all skills with basic info
- ✅ Filter by category, project, active status
- ✅ Sort by name, success rate, use count
- ✅ Multiple output formats (table, JSON)
- ✅ Performance: <100ms for 100 skills

---

### Milestone 4: Skill Details (Days 8-9)

#### Unit Tests: skill-info.py

**`tests/test_skill_info.py`:**
```python
class TestSkillInfo:
    def test_show_skill_details(self, db_conn, sample_skills):
        """Show complete skill information."""
        result = subprocess.run([
            'python3', 'skill-info.py',
            'git-commit-protocol'
        ], capture_output=True, text=True)

        assert result.returncode == 0
        assert 'agent_name: git-commit-protocol' in result.stdout
        assert 'command_type: tool_sequence' in result.stdout
        assert 'Triggers:' in result.stdout
        assert 'create commit' in result.stdout

    def test_show_nonexistent_skill(self, db_conn):
        """Handle nonexistent skill gracefully."""
        result = subprocess.run([
            'python3', 'skill-info.py',
            'does-not-exist'
        ], capture_output=True, text=True)

        assert result.returncode != 0
        assert 'not found' in result.stderr.lower()

    def test_show_performance_stats(self, db_conn, sample_skills):
        """Display performance statistics."""
        # Add performance data
        cur = db_conn.cursor()
        cur.execute("""
            UPDATE skills_agents
            SET use_count = 25, success_count = 23, avg_time_saved_ms = 45000
            WHERE agent_name = 'git-commit-protocol'
        """)
        db_conn.commit()

        result = subprocess.run([
            'python3', 'skill-info.py',
            'git-commit-protocol',
            '--stats'
        ], capture_output=True, text=True)

        assert 'Use Count: 25' in result.stdout
        assert 'Success Rate: 92.0%' in result.stdout
        assert 'Avg Time Saved: 45s' in result.stdout
```

**Validation Criteria:**
- ✅ Display complete skill configuration
- ✅ Show all triggers with match types
- ✅ Display command definition (formatted)
- ✅ Show performance statistics
- ✅ Handle missing skills gracefully

---

### Milestone 5: Basic Execution (Days 10-12)

#### Unit Tests: execute-skill.py

**`tests/test_execute_skill.py`:**
```python
class TestExecuteSkill:
    def test_execute_bash_script_success(self, db_conn, sample_skills):
        """Execute a simple bash script skill."""
        result = subprocess.run([
            'python3', 'execute-skill.py',
            'check-db-health',
            '--auto-confirm'  # For testing only
        ], capture_output=True, text=True)

        assert result.returncode == 0
        assert 'Execution successful' in result.stdout

        # Verify performance log
        cur = db_conn.cursor()
        cur.execute("""
            SELECT outcome, execution_time_ms
            FROM skills_performance_log
            WHERE agent_id = (
                SELECT id FROM skills_agents WHERE agent_name = 'check-db-health'
            )
            ORDER BY executed_at DESC
            LIMIT 1
        """)
        row = cur.fetchone()
        assert row[0] == 'success'
        assert row[1] > 0

    def test_execute_skill_with_parameters(self, db_conn, sample_skills):
        """Execute skill requiring parameters."""
        result = subprocess.run([
            'python3', 'execute-skill.py',
            'backup-claude-memory',
            '--params', '{"backup_dir": "/tmp/test-backup"}',
            '--auto-confirm'
        ], capture_output=True, text=True)

        assert result.returncode == 0

        # Verify backup was created
        import os
        assert os.path.exists('/tmp/test-backup')

    def test_execute_nonexistent_skill(self, db_conn):
        """Handle nonexistent skill execution."""
        result = subprocess.run([
            'python3', 'execute-skill.py',
            'does-not-exist',
            '--auto-confirm'
        ], capture_output=True, text=True)

        assert result.returncode != 0
        assert 'not found' in result.stderr.lower()

    def test_user_confirmation_required(self, db_conn, sample_skills):
        """Require user confirmation for low-trust skills."""
        # Create low-trust skill
        cur = db_conn.cursor()
        cur.execute("""
            UPDATE skills_agents
            SET confidence_score = 0.5, success_count = 2
            WHERE agent_name = 'check-db-health'
        """)
        db_conn.commit()

        # Execute without --auto-confirm
        result = subprocess.run([
            'python3', 'execute-skill.py',
            'check-db-health'
        ], input='n\n', capture_output=True, text=True)

        assert 'Execute skill?' in result.stdout
        assert result.returncode != 0  # User declined

    def test_script_execution_timeout(self, db_conn):
        """Handle long-running script timeout."""
        # Create skill with infinite loop
        cur = db_conn.cursor()
        cur.execute("""
            INSERT INTO skills_agents (agent_name, created_by)
            VALUES ('timeout-test', 'test')
            RETURNING id
        """)
        skill_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO skills_commands (agent_id, command_type, script_content)
            VALUES (%s, 'bash_script', 'sleep 300')
        """, (skill_id,))
        db_conn.commit()

        result = subprocess.run([
            'python3', 'execute-skill.py',
            'timeout-test',
            '--auto-confirm',
            '--timeout', '5'  # 5 second timeout
        ], capture_output=True, text=True)

        assert result.returncode != 0
        assert 'timeout' in result.stderr.lower()
```

**Validation Criteria:**
- ✅ Execute bash scripts successfully
- ✅ Pass parameters to scripts
- ✅ Log execution to performance_log
- ✅ Update use_count and success_count
- ✅ Require confirmation for low-trust skills
- ✅ Auto-execute high-trust skills
- ✅ Handle timeouts gracefully
- ✅ Capture and display script output

---

### Milestone 6: Integration Testing (Days 13-14)

#### End-to-End Tests: Complete Workflows

**`tests/test_e2e_workflows.py`:**
```python
class TestEndToEndWorkflows:
    def test_full_skill_lifecycle(self, db_conn):
        """Create → List → Execute → Delete skill."""
        # 1. Create skill
        result = subprocess.run([
            'python3', 'create-skill.py',
            '--name', 'e2e-test-skill',
            '--description', 'End-to-end test',
            '--category', 'testing',
            '--command-type', 'bash_script',
            '--script-content', 'echo "E2E test passed"',
            '--triggers', 'run e2e test'
        ], capture_output=True, text=True)
        assert result.returncode == 0

        # 2. List skills (verify it appears)
        result = subprocess.run([
            'python3', 'list-skills.py'
        ], capture_output=True, text=True)
        assert 'e2e-test-skill' in result.stdout

        # 3. Show skill info
        result = subprocess.run([
            'python3', 'skill-info.py',
            'e2e-test-skill'
        ], capture_output=True, text=True)
        assert result.returncode == 0
        assert 'E2E test passed' in result.stdout

        # 4. Execute skill
        result = subprocess.run([
            'python3', 'execute-skill.py',
            'e2e-test-skill',
            '--auto-confirm'
        ], capture_output=True, text=True)
        assert result.returncode == 0
        assert 'E2E test passed' in result.stdout

        # 5. Verify performance logged
        cur = db_conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM skills_performance_log spl
            JOIN skills_agents sa ON sa.id = spl.agent_id
            WHERE sa.agent_name = 'e2e-test-skill'
        """)
        assert cur.fetchone()[0] == 1

        # 6. Delete skill
        result = subprocess.run([
            'python3', 'delete-skill.py',
            'e2e-test-skill',
            '--confirm'
        ], capture_output=True, text=True)
        assert result.returncode == 0

        # 7. Verify deleted
        result = subprocess.run([
            'python3', 'list-skills.py'
        ], capture_output=True, text=True)
        assert 'e2e-test-skill' not in result.stdout

    def test_trust_progression(self, db_conn):
        """Skill progresses from low trust → high trust."""
        # Create low-trust skill
        subprocess.run([
            'python3', 'create-skill.py',
            '--name', 'trust-test',
            '--description', 'Trust progression test',
            '--command-type', 'bash_script',
            '--script-content', 'echo "Success"',
            '--triggers', 'trust test',
            '--confidence', '0.5'  # Low confidence
        ], capture_output=True, text=True)

        # Execute 10 times successfully
        for i in range(10):
            result = subprocess.run([
                'python3', 'execute-skill.py',
                'trust-test',
                '--auto-confirm'
            ], capture_output=True, text=True)
            assert result.returncode == 0

        # Verify confidence increased
        cur = db_conn.cursor()
        cur.execute("""
            SELECT confidence_score, success_count, use_count
            FROM skills_agents
            WHERE agent_name = 'trust-test'
        """)
        confidence, success, total = cur.fetchone()

        assert success == 10
        assert total == 10
        assert confidence > 0.5  # Should have increased
```

**Validation Criteria:**
- ✅ Complete skill lifecycle works end-to-end
- ✅ Trust progression from low → high
- ✅ Performance logging accurate
- ✅ Database consistency maintained
- ✅ All CRUD operations work together

---

## Phase 2 Testing: Intelligence

### Milestone 1: Embedding Generation (Days 1-3)

#### Unit Tests: generate-embeddings.py

**`tests/test_embeddings.py`:**
```python
from sentence_transformers import SentenceTransformer
import numpy as np

class TestEmbeddingGeneration:
    def test_generate_trigger_embedding(self, db_conn):
        """Generate embedding for trigger phrase."""
        result = subprocess.run([
            'python3', 'generate-embeddings.py',
            '--trigger-id', '1'
        ], capture_output=True, text=True)

        assert result.returncode == 0

        # Verify embedding stored
        cur = db_conn.cursor()
        cur.execute("""
            SELECT embedding FROM skills_triggers WHERE id = 1
        """)
        embedding = cur.fetchone()[0]
        assert embedding is not None
        assert len(embedding) == 384  # MiniLM dimension

    def test_bulk_embedding_generation(self, db_conn, sample_skills):
        """Generate embeddings for all triggers."""
        result = subprocess.run([
            'python3', 'generate-embeddings.py',
            '--all'
        ], capture_output=True, text=True)

        assert result.returncode == 0

        # Verify all triggers have embeddings
        cur = db_conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM skills_triggers WHERE embedding IS NULL
        """)
        assert cur.fetchone()[0] == 0

    def test_embedding_similarity(self, db_conn):
        """Similar phrases have similar embeddings."""
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

        emb1 = model.encode("create a git commit")
        emb2 = model.encode("make a commit in git")
        emb3 = model.encode("backup the database")

        # Cosine similarity
        def cosine_sim(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

        sim_similar = cosine_sim(emb1, emb2)
        sim_different = cosine_sim(emb1, emb3)

        assert sim_similar > 0.8  # High similarity
        assert sim_different < 0.5  # Low similarity
        assert sim_similar > sim_different
```

**Validation Criteria:**
- ✅ Generate 384-dim embeddings
- ✅ Store in pgvector column
- ✅ Similar phrases have high cosine similarity
- ✅ Bulk generation processes all triggers
- ✅ Performance: <1s for 100 triggers

---

### Milestone 2: Semantic Search (Days 4-6)

#### Unit Tests: search-skills.py

**`tests/test_semantic_search.py`:**
```python
class TestSemanticSearch:
    def test_semantic_trigger_matching(self, db_conn, sample_skills_with_embeddings):
        """Find skills using semantic search."""
        result = subprocess.run([
            'python3', 'search-skills.py',
            '--query', 'make a commit',
            '--threshold', '0.75'
        ], capture_output=True, text=True)

        assert result.returncode == 0
        assert 'git-commit-protocol' in result.stdout

    def test_search_threshold_filtering(self, db_conn, sample_skills_with_embeddings):
        """Only return matches above threshold."""
        # High threshold - should return fewer results
        result_high = subprocess.run([
            'python3', 'search-skills.py',
            '--query', 'database',
            '--threshold', '0.9'
        ], capture_output=True, text=True)

        # Low threshold - should return more results
        result_low = subprocess.run([
            'python3', 'search-skills.py',
            '--query', 'database',
            '--threshold', '0.5'
        ], capture_output=True, text=True)

        count_high = result_high.stdout.count('\n')
        count_low = result_low.stdout.count('\n')

        assert count_low >= count_high

    def test_search_with_context_filtering(self, db_conn, sample_skills_with_embeddings):
        """Filter results by context (git repo, project)."""
        result = subprocess.run([
            'python3', 'search-skills.py',
            '--query', 'commit',
            '--requires-git', 'true'
        ], capture_output=True, text=True)

        # Should only return git-related skills
        assert 'git-commit-protocol' in result.stdout
        assert 'backup-claude-memory' not in result.stdout

    def test_search_performance(self, db_conn):
        """Search is fast even with many skills."""
        # Create 1000 skills with embeddings
        # ... (fixture)

        import time
        start = time.time()

        result = subprocess.run([
            'python3', 'search-skills.py',
            '--query', 'test query',
            '--limit', '10'
        ], capture_output=True, text=True)

        elapsed = time.time() - start

        assert result.returncode == 0
        assert elapsed < 0.5  # Should be under 500ms
```

**Validation Criteria:**
- ✅ Find skills by semantic similarity
- ✅ Threshold filtering works
- ✅ Context filtering (git repo, project)
- ✅ Results sorted by similarity score
- ✅ Performance: <500ms for 1000 skills

---

### Milestone 3: Tool Sequence Execution (Days 7-9)

#### Integration Tests: Tool Sequences

**`tests/test_tool_sequences.py`:**
```python
class TestToolSequenceExecution:
    def test_execute_parallel_tools(self, db_conn, sample_skills):
        """Execute tools in parallel within a step."""
        # git-commit-protocol step 1: git status, git diff, git log (parallel)
        result = subprocess.run([
            'python3', 'execute-skill.py',
            'git-commit-protocol',
            '--auto-confirm',
            '--stop-after-step', '1'
        ], capture_output=True, text=True)

        assert result.returncode == 0
        assert 'git status' in result.stdout
        assert 'git diff' in result.stdout
        assert 'git log' in result.stdout

    def test_execute_sequential_steps(self, db_conn, sample_skills):
        """Execute steps sequentially."""
        result = subprocess.run([
            'python3', 'execute-skill.py',
            'git-commit-protocol',
            '--auto-confirm',
            '--verbose'
        ], capture_output=True, text=True)

        # Verify steps executed in order
        output_lines = result.stdout.split('\n')
        step1_idx = next(i for i, line in enumerate(output_lines) if 'Step 1:' in line)
        step2_idx = next(i for i, line in enumerate(output_lines) if 'Step 2:' in line)

        assert step1_idx < step2_idx

    def test_optional_step_handling(self, db_conn, sample_skills):
        """Skip optional steps that fail."""
        # git-commit-protocol step 2: npm test (optional)
        # If no package.json, should continue
        result = subprocess.run([
            'python3', 'execute-skill.py',
            'git-commit-protocol',
            '--auto-confirm'
        ], capture_output=True, text=True, cwd='/tmp')  # No package.json here

        assert result.returncode == 0  # Should still succeed
        assert 'optional' in result.stdout.lower()

    def test_validation_success_criteria(self, db_conn, sample_skills):
        """Validate step success based on criteria."""
        # git-commit-protocol step 5: verify "nothing to commit"
        result = subprocess.run([
            'python3', 'execute-skill.py',
            'git-commit-protocol',
            '--auto-confirm'
        ], capture_output=True, text=True)

        # Should validate final git status
        assert 'Validation: PASSED' in result.stdout

    def test_custom_function_step(self, db_conn, sample_skills):
        """Execute custom function in sequence."""
        # git-commit-protocol step 3: analyze_git_changes_and_draft_message
        result = subprocess.run([
            'python3', 'execute-skill.py',
            'git-commit-protocol',
            '--auto-confirm',
            '--stop-after-step', '3'
        ], capture_output=True, text=True)

        # Should generate commit message
        assert 'Commit message:' in result.stdout
```

**Validation Criteria:**
- ✅ Parallel tool execution within step
- ✅ Sequential step execution
- ✅ Optional steps skipped on failure
- ✅ Validation criteria checked
- ✅ Custom functions execute
- ✅ Error handling rolls back cleanly

---

### Milestone 4: Agent Spawning (Days 10-11)

#### Integration Tests: Agent Spawning

**`tests/test_agent_spawning.py`:**
```python
class TestAgentSpawning:
    def test_spawn_explore_agent(self, db_conn, sample_skills):
        """Spawn Explore agent from skill."""
        result = subprocess.run([
            'python3', 'execute-skill.py',
            'explore-auth-implementation',
            '--auto-confirm'
        ], capture_output=True, text=True)

        assert result.returncode == 0
        assert 'Spawning agent: Explore' in result.stdout

        # Verify agent_work logged
        cur = db_conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM agent_work
            WHERE agent_type = 'Explore'
            AND task_description LIKE '%auth%'
        """)
        assert cur.fetchone()[0] >= 1

    def test_spawn_agent_with_parameters(self, db_conn, sample_skills):
        """Pass parameters to spawned agent."""
        result = subprocess.run([
            'python3', 'execute-skill.py',
            'scaffold-nlq-feature',
            '--params', '{"feature_name": "user-dashboard"}',
            '--auto-confirm'
        ], capture_output=True, text=True)

        assert result.returncode == 0
        assert 'user-dashboard' in result.stdout

    def test_agent_timeout_handling(self, db_conn):
        """Handle agent timeout gracefully."""
        # Create skill with 5-second agent timeout
        # ... (setup)

        result = subprocess.run([
            'python3', 'execute-skill.py',
            'timeout-agent-skill',
            '--auto-confirm'
        ], capture_output=True, text=True)

        # Should timeout and log failure
        assert 'timeout' in result.stderr.lower()

        cur = db_conn.cursor()
        cur.execute("""
            SELECT outcome FROM skills_performance_log
            ORDER BY executed_at DESC LIMIT 1
        """)
        assert cur.fetchone()[0] == 'timeout'
```

**Validation Criteria:**
- ✅ Spawn Explore, Plan, general-purpose agents
- ✅ Pass parameters to agents
- ✅ Capture agent output
- ✅ Log agent work to agent_work table
- ✅ Handle timeouts gracefully
- ✅ Return agent results to user

---

### Milestone 5: Performance Analytics (Days 12-13)

#### Unit Tests: skill-analytics.py

**`tests/test_analytics.py`:**
```python
class TestSkillAnalytics:
    def test_dashboard_view(self, db_conn, sample_performance_data):
        """Query v_skills_dashboard view."""
        cur = db_conn.cursor()
        cur.execute("SELECT * FROM v_skills_dashboard")
        rows = cur.fetchall()

        assert len(rows) > 0
        # Verify columns
        assert len(rows[0]) >= 10  # Check expected column count

    def test_time_saved_calculation(self, db_conn):
        """Calculate total time saved."""
        result = subprocess.run([
            'python3', 'skill-analytics.py',
            '--metric', 'time-saved'
        ], capture_output=True, text=True)

        assert result.returncode == 0
        assert 'Total Time Saved:' in result.stdout

    def test_top_skills_by_usage(self, db_conn, sample_performance_data):
        """Show top skills by use count."""
        result = subprocess.run([
            'python3', 'skill-analytics.py',
            '--top', '5',
            '--sort-by', 'usage'
        ], capture_output=True, text=True)

        output_lines = result.stdout.split('\n')
        assert len([line for line in output_lines if line.strip()]) <= 5

    def test_success_rate_trends(self, db_conn, sample_performance_data):
        """Analyze success rate over time."""
        result = subprocess.run([
            'python3', 'skill-analytics.py',
            '--skill', 'git-commit-protocol',
            '--trends'
        ], capture_output=True, text=True)

        assert 'Success Rate Trend:' in result.stdout
```

**Validation Criteria:**
- ✅ Dashboard view returns accurate data
- ✅ Time saved calculation correct
- ✅ Top skills ranking works
- ✅ Success rate trends calculated
- ✅ Performance over time visualized

---

### Milestone 6: Export/Import (Day 14)

#### Integration Tests: Export/Import

**`tests/test_export_import.py`:**
```python
import json

class TestExportImport:
    def test_export_single_skill(self, db_conn, sample_skills):
        """Export skill to JSON."""
        result = subprocess.run([
            'python3', 'export-skill.py',
            '--name', 'git-commit-protocol',
            '--output', '/tmp/git-commit.json'
        ], capture_output=True, text=True)

        assert result.returncode == 0

        # Verify JSON structure
        with open('/tmp/git-commit.json', 'r') as f:
            skill = json.load(f)

        assert skill['agent_name'] == 'git-commit-protocol'
        assert 'triggers' in skill
        assert 'commands' in skill

    def test_import_skill(self, db_conn):
        """Import skill from JSON."""
        # Create test JSON
        skill_json = {
            "agent_name": "imported-skill",
            "description": "Imported from JSON",
            "category": "testing",
            "triggers": [
                {"trigger_phrase": "import test", "match_type": "exact"}
            ],
            "commands": {
                "command_type": "bash_script",
                "script_content": "echo 'Imported'"
            }
        }

        with open('/tmp/import-test.json', 'w') as f:
            json.dump(skill_json, f)

        result = subprocess.run([
            'python3', 'import-skill.py',
            '--file', '/tmp/import-test.json'
        ], capture_output=True, text=True)

        assert result.returncode == 0

        # Verify in database
        cur = db_conn.cursor()
        cur.execute("""
            SELECT id FROM skills_agents WHERE agent_name = 'imported-skill'
        """)
        assert cur.fetchone() is not None

    def test_export_all_skills(self, db_conn, sample_skills):
        """Export all skills to directory."""
        result = subprocess.run([
            'python3', 'export-skill.py',
            '--all',
            '--output-dir', '/tmp/skills-export'
        ], capture_output=True, text=True)

        assert result.returncode == 0

        import os
        files = os.listdir('/tmp/skills-export')
        assert len(files) >= 3  # At least 3 sample skills

    def test_import_with_conflict_handling(self, db_conn, sample_skills):
        """Handle import conflicts (existing skill name)."""
        # Export existing skill
        subprocess.run([
            'python3', 'export-skill.py',
            '--name', 'git-commit-protocol',
            '--output', '/tmp/conflict.json'
        ])

        # Attempt reimport
        result = subprocess.run([
            'python3', 'import-skill.py',
            '--file', '/tmp/conflict.json',
            '--on-conflict', 'skip'
        ], capture_output=True, text=True)

        assert 'already exists' in result.stdout
        assert result.returncode == 0  # Not an error, just skipped
```

**Validation Criteria:**
- ✅ Export single skill to JSON
- ✅ Export all skills to directory
- ✅ Import skill from JSON
- ✅ Import multiple skills from directory
- ✅ Handle naming conflicts
- ✅ Preserve all metadata (triggers, commands, performance)

---

## Integration Testing

### Database Integration

**`tests/test_db_integration.py`:**
```python
class TestDatabaseIntegration:
    def test_transaction_rollback_on_error(self, db_conn):
        """Verify transactions roll back on error."""
        cur = db_conn.cursor()

        try:
            # Start transaction
            cur.execute("""
                INSERT INTO skills_agents (agent_name, created_by)
                VALUES ('rollback-test', 'test')
                RETURNING id
            """)
            skill_id = cur.fetchone()[0]

            # Force error (invalid foreign key)
            cur.execute("""
                INSERT INTO skills_triggers (agent_id, trigger_phrase)
                VALUES (99999, 'should fail')
            """)

            db_conn.commit()
        except Exception:
            db_conn.rollback()

        # Verify skill was NOT created
        cur.execute("SELECT COUNT(*) FROM skills_agents WHERE agent_name = 'rollback-test'")
        assert cur.fetchone()[0] == 0

    def test_concurrent_skill_execution(self, db_conn, sample_skills):
        """Multiple processes executing same skill."""
        import multiprocessing

        def execute_skill():
            subprocess.run([
                'python3', 'execute-skill.py',
                'check-db-health',
                '--auto-confirm'
            ])

        # Execute 5 times concurrently
        processes = [multiprocessing.Process(target=execute_skill) for _ in range(5)]
        for p in processes:
            p.start()
        for p in processes:
            p.join()

        # Verify all 5 executions logged
        cur = db_conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM skills_performance_log spl
            JOIN skills_agents sa ON sa.id = spl.agent_id
            WHERE sa.agent_name = 'check-db-health'
        """)
        assert cur.fetchone()[0] >= 5
```

### Claude-Memory Integration

**`tests/test_claude_memory_integration.py`:**
```python
class TestClaudeMemoryIntegration:
    def test_skill_learned_from_snapshot(self, db_conn):
        """Link skill to snapshot it was learned from."""
        # Create snapshot
        cur = db_conn.cursor()
        cur.execute("""
            INSERT INTO context_snapshots (project_path, summary)
            VALUES ('/test/project', 'Created git-commit skill')
            RETURNING id
        """)
        snapshot_id = cur.fetchone()[0]

        # Create skill linked to snapshot
        subprocess.run([
            'python3', 'create-skill.py',
            '--name', 'snapshot-linked-skill',
            '--description', 'Test',
            '--command-type', 'bash_script',
            '--script-content', 'echo test',
            '--triggers', 'test',
            '--learned-from', str(snapshot_id)
        ])

        # Verify link
        cur.execute("""
            SELECT learned_from_snapshot_id FROM skills_agents
            WHERE agent_name = 'snapshot-linked-skill'
        """)
        assert cur.fetchone()[0] == snapshot_id

    def test_skill_performance_in_snapshot(self, db_conn, sample_skills):
        """Log skill execution to snapshot context."""
        # Create snapshot
        cur = db_conn.cursor()
        cur.execute("""
            INSERT INTO context_snapshots (project_path, summary)
            VALUES ('/test/project', 'Test session')
            RETURNING id
        """)
        snapshot_id = cur.fetchone()[0]
        db_conn.commit()

        # Execute skill
        result = subprocess.run([
            'python3', 'execute-skill.py',
            'check-db-health',
            '--auto-confirm',
            '--snapshot-id', str(snapshot_id)
        ], capture_output=True, text=True)

        # Verify logged with snapshot
        cur.execute("""
            SELECT snapshot_id FROM skills_performance_log
            WHERE snapshot_id = %s
        """, (snapshot_id,))
        assert cur.fetchone() is not None
```

**Validation Criteria:**
- ✅ Skills integrate with context_snapshots
- ✅ Performance logged per snapshot
- ✅ Skills can be traced back to learning source
- ✅ Existing claude-memory tools work unchanged

---

## Performance Testing

### Load Testing

**`tests/test_performance.py`:**
```python
import time

class TestPerformance:
    def test_list_skills_performance(self, db_conn):
        """List 1000 skills should be fast."""
        # Create 1000 skills
        for i in range(1000):
            # ... (bulk insert)

        start = time.time()
        result = subprocess.run([
            'python3', 'list-skills.py'
        ], capture_output=True, text=True)
        elapsed = time.time() - start

        assert result.returncode == 0
        assert elapsed < 1.0  # Under 1 second

    def test_semantic_search_performance(self, db_conn):
        """Semantic search with 1000 triggers."""
        # Create 1000 triggers with embeddings
        # ... (bulk insert)

        start = time.time()
        result = subprocess.run([
            'python3', 'search-skills.py',
            '--query', 'database backup',
            '--limit', '10'
        ], capture_output=True, text=True)
        elapsed = time.time() - start

        assert result.returncode == 0
        assert elapsed < 0.5  # Under 500ms

    def test_tool_sequence_execution_time(self, db_conn, sample_skills):
        """Tool sequence with 5 steps should complete quickly."""
        start = time.time()
        result = subprocess.run([
            'python3', 'execute-skill.py',
            'git-commit-protocol',
            '--auto-confirm'
        ], capture_output=True, text=True)
        elapsed = time.time() - start

        assert result.returncode == 0
        assert elapsed < 10.0  # Under 10 seconds for git workflow
```

### Database Performance

**`tests/test_db_performance.py`:**
```python
class TestDatabasePerformance:
    def test_index_usage_on_search(self, db_conn):
        """Verify HNSW index is used for semantic search."""
        cur = db_conn.cursor()

        # Explain query
        cur.execute("""
            EXPLAIN (ANALYZE, BUFFERS)
            SELECT * FROM skills_triggers
            WHERE 1 - (embedding <=> '[0.1, 0.2, ...]'::vector) >= 0.75
            LIMIT 10
        """)

        plan = '\n'.join([row[0] for row in cur.fetchall()])
        assert 'Index Scan using idx_skills_triggers_embedding' in plan

    def test_performance_log_insert_speed(self, db_conn):
        """Inserting 1000 performance logs should be fast."""
        cur = db_conn.cursor()

        start = time.time()
        for i in range(1000):
            cur.execute("""
                INSERT INTO skills_performance_log
                (agent_id, outcome, execution_time_ms)
                VALUES (1, 'success', %s)
            """, (100 + i,))
        db_conn.commit()
        elapsed = time.time() - start

        assert elapsed < 2.0  # Under 2 seconds for 1000 inserts
```

**Performance Targets:**
- List 1000 skills: <1s
- Semantic search (1000 triggers): <500ms
- Tool sequence (5 steps): <10s
- Bulk performance log insert (1000): <2s
- HNSW index used for vector search

---

## Security Testing

### Input Validation

**`tests/test_security.py`:**
```python
class TestSecurity:
    def test_sql_injection_prevention(self, db_conn):
        """Prevent SQL injection in skill names."""
        result = subprocess.run([
            'python3', 'create-skill.py',
            '--name', "'; DROP TABLE skills_agents; --",
            '--description', 'SQL injection attempt',
            '--command-type', 'bash_script',
            '--script-content', 'echo test',
            '--triggers', 'inject'
        ], capture_output=True, text=True)

        # Should fail validation
        assert result.returncode != 0

        # Verify table still exists
        cur = db_conn.cursor()
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'skills_agents'
            )
        """)
        assert cur.fetchone()[0] == True

    def test_command_injection_prevention(self, db_conn):
        """Prevent command injection in bash scripts."""
        result = subprocess.run([
            'python3', 'create-skill.py',
            '--name', 'command-inject-test',
            '--description', 'Test',
            '--command-type', 'bash_script',
            '--script-content', 'echo "test"; rm -rf /',  # Malicious
            '--triggers', 'inject'
        ], capture_output=True, text=True)

        # Should warn or require explicit confirmation
        assert ('warning' in result.stdout.lower() or
                'dangerous' in result.stdout.lower())

    def test_parameter_sanitization(self, db_conn):
        """Sanitize user-provided parameters."""
        # Attempt to pass malicious parameter
        result = subprocess.run([
            'python3', 'execute-skill.py',
            'backup-claude-memory',
            '--params', '{"backup_dir": "/; rm -rf /"}',
            '--auto-confirm'
        ], capture_output=True, text=True)

        # Should fail validation
        assert result.returncode != 0 or 'invalid' in result.stderr.lower()

    def test_script_content_size_limit(self, db_conn):
        """Prevent extremely large script content."""
        huge_script = 'echo "test"\n' * 100000  # 1MB+

        result = subprocess.run([
            'python3', 'create-skill.py',
            '--name', 'huge-script',
            '--description', 'Test',
            '--command-type', 'bash_script',
            '--script-content', huge_script,
            '--triggers', 'huge'
        ], capture_output=True, text=True)

        assert result.returncode != 0
        assert 'too large' in result.stderr.lower()
```

**Security Checklist:**
- ✅ SQL injection prevention (parameterized queries)
- ✅ Command injection prevention (input validation)
- ✅ Path traversal prevention (validate backup_dir, etc.)
- ✅ Script size limits (max 100KB)
- ✅ Parameter sanitization
- ✅ Dangerous command warnings (`rm -rf`, `DROP TABLE`)

---

## Test Data & Fixtures

### Sample Skills Fixture

**`tests/fixtures/sample_skills.py`:**
```python
import psycopg2
import json

def create_sample_skills(db_conn):
    """Create realistic sample skills for testing."""
    cur = db_conn.cursor()

    # 1. Bash script: check-db-health
    cur.execute("""
        INSERT INTO skills_agents
        (agent_name, display_name, description, category, created_by)
        VALUES ('check-db-health', 'Check DB Health',
                'Check PostgreSQL database health', 'maintenance', 'test')
        RETURNING id
    """)
    skill1_id = cur.fetchone()[0]

    cur.execute("""
        INSERT INTO skills_commands (agent_id, command_type, script_content)
        VALUES (%s, 'bash_script', %s)
    """, (skill1_id, """
#!/bin/bash
psql -d $DB_NAME -c "SELECT version();"
psql -d $DB_NAME -c "SELECT pg_database_size(current_database());"
psql -d $DB_NAME -c "SELECT count(*) FROM context_snapshots;"
"""))

    cur.execute("""
        INSERT INTO skills_triggers (agent_id, trigger_phrase, match_type)
        VALUES
            (%s, 'check database health', 'exact'),
            (%s, 'verify db status', 'exact')
    """, (skill1_id, skill1_id))

    # 2. Tool sequence: git-commit-protocol
    tool_sequence_def = {
        "steps": [
            {
                "step": 1,
                "description": "Check git status and recent commits",
                "tools": [
                    {"tool": "Bash", "command": "git status"},
                    {"tool": "Bash", "command": "git diff"},
                    {"tool": "Bash", "command": "git log --oneline -5"}
                ],
                "parallel": True
            },
            {
                "step": 2,
                "description": "Run tests (optional)",
                "tools": [{"tool": "Bash", "command": "npm test", "optional": True}]
            },
            {
                "step": 3,
                "description": "Analyze and draft commit message",
                "action": "custom_function",
                "function": "analyze_git_changes_and_draft_message"
            },
            {
                "step": 4,
                "description": "Commit with heredoc",
                "tools": [{
                    "tool": "Bash",
                    "command": "git add . && git commit -m \"$(cat <<'EOF'\\n{commit_message}\\nEOF\\n)\""
                }]
            },
            {
                "step": 5,
                "description": "Verify success",
                "tools": [{"tool": "Bash", "command": "git status"}],
                "validation": {"success_if_contains": ["nothing to commit"]}
            }
        ]
    }

    cur.execute("""
        INSERT INTO skills_agents
        (agent_name, display_name, description, category, created_by)
        VALUES ('git-commit-protocol', 'Git Commit Protocol',
                'Execute git commit workflow', 'version-control', 'test')
        RETURNING id
    """)
    skill2_id = cur.fetchone()[0]

    cur.execute("""
        INSERT INTO skills_commands (agent_id, command_type, command_definition)
        VALUES (%s, 'tool_sequence', %s)
    """, (skill2_id, json.dumps(tool_sequence_def)))

    cur.execute("""
        INSERT INTO skills_triggers (agent_id, trigger_phrase, match_type)
        VALUES
            (%s, 'create commit', 'exact'),
            (%s, 'make git commit', 'exact')
    """, (skill2_id, skill2_id))

    # 3. Agent spawn: explore-auth-implementation
    agent_config = {
        "agent_type": "Explore",
        "task_description": "Explore authentication implementation in codebase",
        "thoroughness": "medium"
    }

    cur.execute("""
        INSERT INTO skills_agents
        (agent_name, display_name, description, category, created_by)
        VALUES ('explore-auth-implementation', 'Explore Auth',
                'Explore how authentication works', 'exploration', 'test')
        RETURNING id
    """)
    skill3_id = cur.fetchone()[0]

    cur.execute("""
        INSERT INTO skills_commands (agent_id, command_type, agent_config)
        VALUES (%s, 'agent_spawn', %s)
    """, (skill3_id, json.dumps(agent_config)))

    cur.execute("""
        INSERT INTO skills_triggers (agent_id, trigger_phrase, match_type)
        VALUES (%s, 'explore authentication', 'exact')
    """, (skill3_id,))

    db_conn.commit()
    return [skill1_id, skill2_id, skill3_id]
```

### Performance Data Fixture

**`tests/fixtures/performance_data.py`:**
```python
from datetime import datetime, timedelta
import random

def create_sample_performance_data(db_conn, skill_ids):
    """Generate realistic performance logs."""
    cur = db_conn.cursor()

    for skill_id in skill_ids:
        for day in range(30):  # Last 30 days
            executions = random.randint(0, 5)
            for _ in range(executions):
                outcome = 'success' if random.random() > 0.1 else 'failed'
                exec_time = random.randint(100, 5000)
                time_saved = random.randint(10000, 60000) if outcome == 'success' else 0

                executed_at = datetime.now() - timedelta(days=day, hours=random.randint(0, 23))

                cur.execute("""
                    INSERT INTO skills_performance_log
                    (agent_id, outcome, execution_time_ms, time_saved_ms, executed_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (skill_id, outcome, exec_time, time_saved, executed_at))

    db_conn.commit()
```

---

## Validation Criteria

### Phase 1 Acceptance Criteria

**Must have ALL of these working:**
- ✅ Database schema created (5 tables, 31 indexes, 4 views)
- ✅ create-skill.py creates bash script skills with triggers
- ✅ create-skill.py creates tool sequence skills with parameters
- ✅ list-skills.py lists skills with filtering and sorting
- ✅ skill-info.py displays complete skill details
- ✅ execute-skill.py executes bash scripts successfully
- ✅ Trust levels: low trust requires confirmation, high trust auto-executes
- ✅ Performance logging captures outcome and time
- ✅ Success rate auto-calculated correctly
- ✅ Script content stored in database (not filesystem)

### Phase 2 Acceptance Criteria

**Must have ALL of these working:**
- ✅ generate-embeddings.py creates 384-dim embeddings
- ✅ search-skills.py finds skills semantically (threshold 0.75)
- ✅ Tool sequences execute steps in order (parallel + sequential)
- ✅ Optional steps handled gracefully
- ✅ Custom functions in sequences work
- ✅ Agent spawning (Explore, Plan, general-purpose) works
- ✅ skill-analytics.py shows dashboard metrics
- ✅ export-skill.py / import-skill.py work roundtrip
- ✅ Natural Language Skill Creation implemented

### Overall System Acceptance

**System is ready for production when:**
- ✅ All unit tests pass (100% pass rate)
- ✅ All integration tests pass
- ✅ Performance targets met
- ✅ Security tests pass (no vulnerabilities)
- ✅ Manual testing confirms good UX
- ✅ Documentation complete (README, examples)
- ✅ Zero critical bugs in issue tracker

---

## Test Execution Schedule

### Week 1 (Phase 1, Days 1-7)

**Day 1-2:** Database Foundation
- Run: `pytest tests/test_schema.py tests/test_constraints.py`
- Validate: All tables, indexes, views created

**Day 3-5:** Skill Creation
- Run: `pytest tests/test_create_skill.py`
- Manual: Create 5 different skills, verify in database

**Day 6-7:** Skill Listing & Details
- Run: `pytest tests/test_list_skills.py tests/test_skill_info.py`
- Manual: List skills, filter, sort, view details

### Week 2 (Phase 1, Days 8-14)

**Day 8-12:** Basic Execution
- Run: `pytest tests/test_execute_skill.py`
- Manual: Execute 10 skills, verify outcomes logged

**Day 13-14:** Integration Testing
- Run: `pytest tests/test_e2e_workflows.py`
- Manual: Complete lifecycle test (create → execute → delete)

### Week 3 (Phase 2, Days 1-7)

**Day 1-3:** Embedding Generation
- Run: `pytest tests/test_embeddings.py`
- Validate: All triggers have embeddings

**Day 4-6:** Semantic Search
- Run: `pytest tests/test_semantic_search.py`
- Manual: Search with various queries, verify relevance

**Day 7-9:** Tool Sequences
- Run: `pytest tests/test_tool_sequences.py`
- Manual: Execute git-commit-protocol, verify all steps

### Week 4 (Phase 2, Days 10-14)

**Day 10-11:** Agent Spawning
- Run: `pytest tests/test_agent_spawning.py`
- Manual: Spawn agents, verify output

**Day 12-13:** Analytics
- Run: `pytest tests/test_analytics.py`
- Manual: Review dashboard, verify metrics

**Day 14:** Export/Import
- Run: `pytest tests/test_export_import.py`
- Manual: Export all skills, reimport on clean database

### Final Validation (After Week 4)

**Day 15-16:** Full System Test
- Run: `pytest tests/` (all tests)
- Performance testing
- Security testing
- Manual acceptance testing

**Day 17:** Documentation Review
- Verify all docs complete
- Test installation on fresh system
- User acceptance testing

**Day 18:** Release Preparation
- Tag version in git
- Create release notes
- Deploy to production

---

## Continuous Testing

### Pre-Commit Hooks

**`.git/hooks/pre-commit`:**
```bash
#!/bin/bash
# Run tests before allowing commit

echo "Running skills system tests..."

# Run fast unit tests
pytest tests/test_schema.py tests/test_create_skill.py -v

if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi

echo "Tests passed. Proceeding with commit."
```

### CI/CD Integration (Future)

```yaml
# .github/workflows/skills-tests.yml
name: Skills System Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s

    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11

      - name: Install dependencies
        run: |
          pip install pytest psycopg2-binary sentence-transformers

      - name: Run tests
        run: pytest tests/ -v --cov=./ --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## Test Maintenance

### Adding New Tests

**When adding new feature:**
1. Write test FIRST (TDD approach)
2. Test should fail initially
3. Implement feature
4. Test should pass
5. Commit both test and feature together

### Updating Existing Tests

**When modifying features:**
1. Update tests to reflect new behavior
2. Ensure backward compatibility tests still pass
3. Add migration tests if schema changed

### Test Data Cleanup

**After each test run:**
```python
@pytest.fixture
def db_conn():
    """Provide clean test database."""
    conn = psycopg2.connect(dbname='claude_memory_test', ...)

    yield conn

    # Cleanup
    cur = conn.cursor()
    cur.execute("TRUNCATE skills_agents CASCADE")
    cur.execute("TRUNCATE context_snapshots CASCADE")
    conn.commit()
    conn.close()
```

---

## Success Metrics

### Code Coverage Targets

- **Unit Tests:** 80% coverage minimum
- **Integration Tests:** 60% coverage minimum
- **Overall:** 70% coverage minimum

### Performance Benchmarks

- All tests complete in <5 minutes
- Individual unit tests <100ms each
- Integration tests <5s each

### Quality Gates

**Before merging to main:**
- ✅ All tests passing
- ✅ No regressions
- ✅ Code coverage maintained or improved
- ✅ No critical security vulnerabilities
- ✅ Documentation updated

---

## Appendix: Test Commands

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/test_schema.py -v
```

### Run Specific Test Function
```bash
pytest tests/test_schema.py::TestSkillsSchema::test_skills_agents_table_exists -v
```

### Run with Coverage
```bash
pytest tests/ --cov=./ --cov-report=html
```

### Run Performance Tests Only
```bash
pytest tests/test_performance.py tests/test_db_performance.py -v
```

### Run Security Tests Only
```bash
pytest tests/test_security.py -v
```

---

**End of Testing Plan**

This testing plan ensures the Skills System (Phase 1 + Phase 2) is thoroughly validated before production deployment. All tests should pass before proceeding to the next phase.
