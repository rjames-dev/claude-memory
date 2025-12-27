# Skills Phase 2 - Milestones 1-2 Status

**Date**: 2025-12-26
**Milestones**: Embedding Generation & Semantic Search
**Status**: 🚀 Starting (0% Complete)

---

## Overview

**Goal**: Implement semantic skill matching using vector embeddings instead of exact phrase matching

**Duration**: Days 1-6 (estimated 4-8 hours total)

**Why This Matters**:
- Current system uses exact phrase matching only
- Users must add every possible variation of a trigger phrase
- Semantic search enables natural language matching:
  - "commit changes" matches "create a commit"
  - "check database health" matches "verify postgres is running"
  - "find auth files" matches "where is authentication handled"

**Dependencies**:
- ✅ Phase 1 complete (basic skills system)
- ✅ Milestone 4 complete (tool sequences)
- ✅ Milestone 5 complete (analytics)
- ✅ Database has embedding column (vector type)

---

## Architecture

### Embedding Model

**Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Dimensions**: 384
- **Speed**: Very fast (~10ms per encoding)
- **Quality**: Good for short phrases
- **Same model** used for snapshot embeddings (consistency)

**Why This Model**:
- Lightweight (80MB)
- Fast inference
- Already used in claude-memory for snapshots
- Good balance of speed vs quality
- Works well offline

### Database Schema

**Already Exists** in `skills_triggers` table:
```sql
CREATE TABLE skills_triggers (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER NOT NULL,
    trigger_phrase VARCHAR(500) NOT NULL,
    match_type VARCHAR(50) DEFAULT 'semantic',  -- 'exact' or 'semantic'
    embedding vector(384),                       -- Embedding for semantic search
    confidence_threshold DOUBLE PRECISION DEFAULT 0.75,
    ...
);
```

**Similarity Search** (uses pgvector extension):
```sql
SELECT
    trigger_phrase,
    1 - (embedding <=> %s::vector) AS similarity
FROM skills_triggers
WHERE match_type = 'semantic'
  AND 1 - (embedding <=> %s::vector) >= 0.75
ORDER BY similarity DESC
LIMIT 5;
```

**Operator**: `<=>` is cosine distance (pgvector)
- `0.0` = identical vectors
- `1.0` = completely different
- `1 - distance` = similarity score (0.0 to 1.0)

---

## Milestone 1: Embedding Generation

### Objectives

1. Generate embeddings for all existing triggers
2. Automatically generate embeddings for new triggers
3. Support regeneration (model updates)
4. Validate embedding quality

### Implementation Plan

#### Task 1.1: Create generate-trigger-embeddings.py

**Features**:
- Generate embedding for single trigger
- Backfill all triggers missing embeddings
- Regenerate all embeddings (for model updates)
- Validate embedding dimensions

**Usage**:
```bash
# Generate for specific trigger
python3 generate-trigger-embeddings.py --trigger-id 5

# Backfill all triggers missing embeddings
python3 generate-trigger-embeddings.py --backfill

# Regenerate all embeddings (model update)
python3 generate-trigger-embeddings.py --regenerate

# Test with a phrase
python3 generate-trigger-embeddings.py --test "commit these changes"
```

**Functions**:
1. `load_model()` - Load sentence-transformers model
2. `generate_embedding(text)` - Generate 384-dim embedding
3. `store_embedding(trigger_id, embedding)` - Save to database
4. `backfill_embeddings()` - Generate for all missing
5. `regenerate_all()` - Regenerate for model updates
6. `validate_embedding(embedding)` - Check dimensions/format

#### Task 1.2: Test Embedding Generation

**Test Cases**:
1. Generate embedding for sample phrase
2. Verify 384 dimensions
3. Verify embedding is normalized
4. Test backfill with existing triggers
5. Verify database storage

**Expected Output**:
```
Generating embeddings for 12 triggers...

[1/12] commit these changes
✅ Generated (384 dims, norm: 1.00)

[2/12] check database health
✅ Generated (384 dims, norm: 1.00)

...

✅ Backfill complete: 12 embeddings generated
   Total time: 1.2s (100ms avg per embedding)
```

#### Task 1.3: Integrate with Skill Creation

**Modify**: `create-skill.py` (or import-skill.py)

Add automatic embedding generation:
```python
from generate_trigger_embeddings import generate_embedding

# After inserting trigger
trigger_id = cur.fetchone()[0]

if match_type == 'semantic':
    print(f"  Generating embedding for: '{trigger_phrase}'")
    embedding = generate_embedding(trigger_phrase)

    cur.execute("""
        UPDATE skills_triggers
        SET embedding = %s
        WHERE id = %s
    """, (embedding, trigger_id))

    print(f"  ✅ Embedding generated")
```

---

## Milestone 2: Semantic Search

### Objectives

1. Search skills using natural language
2. Rank results by similarity
3. Apply context boosting
4. Filter by prerequisites
5. Integrate with skill execution

### Implementation Plan

#### Task 2.1: Create search-skills-semantic.py

**Features**:
- Search by natural language query
- Similarity threshold filtering
- Context awareness (git repo, project path)
- Result ranking with boost
- JSON output for integration

**Usage**:
```bash
# Basic search
python3 search-skills-semantic.py "commit these changes"

# Custom threshold
python3 search-skills-semantic.py "check database" --threshold 0.7

# Limit results
python3 search-skills-semantic.py "find files" --limit 3

# JSON output (for integration)
python3 search-skills-semantic.py "backup db" --json
```

**Functions**:
1. `check_context()` - Detect git repo, project, etc.
2. `search_skills(query, threshold, limit)` - Main search
3. `apply_context_boost(matches, context)` - Boost relevant skills
4. `filter_by_prerequisites(matches, context)` - Filter incompatible
5. `format_results(matches)` - Pretty print results

#### Task 2.2: Implement Context Boosting

**Context Checks**:
```python
def check_context():
    """Check current environment context."""
    context = {
        'is_git_repo': False,
        'has_uncommitted_changes': False,
        'current_project': os.getcwd(),
        'is_docker_running': False,
        'database_accessible': False
    }

    # Check git
    result = subprocess.run(['git', 'rev-parse', '--git-dir'],
                          capture_output=True)
    context['is_git_repo'] = (result.returncode == 0)

    if context['is_git_repo']:
        result = subprocess.run(['git', 'status', '--porcelain'],
                              capture_output=True, text=True)
        context['has_uncommitted_changes'] = bool(result.stdout.strip())

    # Check docker
    result = subprocess.run(['docker', 'ps'],
                          capture_output=True)
    context['is_docker_running'] = (result.returncode == 0)

    return context
```

**Boosting Logic**:
```python
def apply_context_boost(match, context):
    """Apply context-aware score boosting."""
    boost = 0

    # Git-related skills get +10% if in git repo
    if match['requires_git_repo'] and context['is_git_repo']:
        boost += 0.10

    # Skills for current project get +5%
    if match['project_path'] == context['current_project']:
        boost += 0.05

    # Keyword matching in query
    if match['context_keywords']:
        for keyword in match['context_keywords']:
            if keyword.lower() in query.lower():
                boost += 0.05

    # Cap total boost at +20%
    return min(boost, 0.20)
```

#### Task 2.3: Implement Filtering

**Prerequisites Filtering**:
```python
def filter_by_prerequisites(matches, context):
    """Filter out skills that can't run in current context."""
    filtered = []

    for match in matches:
        # Skip if requires git but not in git repo
        if match['requires_git_repo'] and not context['is_git_repo']:
            continue

        # Skip if project-specific and not in that project
        if match['project_path']:
            if not context['current_project'].startswith(match['project_path']):
                continue

        filtered.append(match)

    return filtered
```

#### Task 2.4: Output Formatting

**Example Output**:
```
🔍 Searching for: "commit these changes"

Found 3 matching skills:

1. ✅ Git Commit (Our Protocol) (git-commit-protocol)
   Similarity: 87% + 10% boost = 97%
   Trigger: "commit these changes"
   Category: git
   Performance: 23 uses, 100% success, 45s avg saved

2. ✅ Git Commit & Push (git-commit-push)
   Similarity: 82% + 10% boost = 92%
   Trigger: "commit and push changes"
   Category: git
   Performance: 15 uses, 100% success, 60s avg saved

3. ✅ Create GitHub PR (create-pr)
   Similarity: 68%
   Trigger: "create a pull request"
   Category: git
   Performance: 8 uses, 100% success, 120s avg saved
```

---

## Integration Points

### 1. Skill Execution Flow

**Current** (exact matching):
```
User query → Check exact matches → Execute skill
```

**New** (semantic matching):
```
User query → Generate query embedding
          → Search similar triggers (cosine similarity)
          → Apply context boost
          → Filter by prerequisites
          → Rank by final score
          → Present top matches
          → Execute selected skill
```

### 2. create-skill.py Integration

Add automatic embedding generation when creating skills with semantic triggers.

### 3. import-skill.py Integration

Generate embeddings for imported skills automatically.

### 4. Future: Auto-suggest

When user says something that matches a skill semantically:
```
User: "I need to check if the database is healthy"

🤖 Claude: I found a skill that can help:
    "Database Health Check" (87% match)
    Would you like me to run it? [Yes] [No] [Show details]
```

---

## Success Criteria

| Criterion | Status | Notes |
|-----------|--------|-------|
| sentence-transformers installed | ⏸️ Pending | pip install sentence-transformers |
| generate-trigger-embeddings.py created | ⏸️ Pending | Core embedding generation |
| Embeddings generated for all triggers | ⏸️ Pending | Backfill complete |
| search-skills-semantic.py created | ⏸️ Pending | Core search functionality |
| Context boosting implemented | ⏸️ Pending | Git, project, keywords |
| Prerequisites filtering working | ⏸️ Pending | Skip incompatible skills |
| Search accuracy validated | ⏸️ Pending | Manual testing |
| Integration with create-skill.py | ⏸️ Pending | Auto-generate on create |
| Integration with import-skill.py | ⏸️ Pending | Auto-generate on import |
| Documentation complete | ⏸️ Pending | Usage guide |

---

## Expected Deliverables

**New Files**:
1. `generate-trigger-embeddings.py` (~200-300 lines)
2. `search-skills-semantic.py` (~300-400 lines)
3. Updated `create-skill.py` (add embedding generation)
4. Updated `import-skill.py` (add embedding generation)
5. `SKILLS-PHASE2-MILESTONES1-2-STATUS.md` (this document)

**No Database Changes Required** ✅
- `embedding vector(384)` column already exists
- pgvector extension already installed
- Indexes already created

---

## Technical Challenges & Solutions

### Challenge 1: Model Download Size

**Issue**: sentence-transformers model is 80MB

**Solution**:
- First run downloads model to `~/.cache/torch/sentence_transformers/`
- Subsequent runs use cached model (instant load)
- Consider pre-downloading in installation docs

### Challenge 2: Similarity Threshold Tuning

**Issue**: What threshold to use? (0.75? 0.80? 0.70?)

**Solution**:
- Default: 0.75 (good balance)
- Make configurable per skill
- Test with real queries
- Allow user override: `--threshold 0.70`

### Challenge 3: Embedding Normalization

**Issue**: sentence-transformers returns normalized embeddings, but should verify

**Solution**:
```python
import numpy as np

def validate_embedding(embedding):
    """Validate embedding format."""
    embedding_array = np.array(embedding)

    # Check dimensions
    assert embedding_array.shape == (384,), f"Wrong dimensions: {embedding_array.shape}"

    # Check normalization (should be ~1.0 for normalized vectors)
    norm = np.linalg.norm(embedding_array)
    assert 0.99 <= norm <= 1.01, f"Not normalized: {norm}"

    return True
```

### Challenge 4: Performance

**Issue**: Generating embeddings might be slow

**Benchmarks**:
- Model load: ~1-2 seconds (first time)
- Embedding generation: ~10ms per phrase
- 100 triggers: ~1 second total

**Solution**: Fast enough for our use case. If needed:
- Batch processing (encode multiple at once)
- Cache loaded model in memory

---

## Testing Strategy

### Phase 1: Embedding Quality

Test that embeddings capture meaning:
```python
phrases = [
    "commit these changes",
    "create a commit",
    "save my work",
    "check database health",
    "verify postgres is running"
]

for phrase in phrases:
    embedding = generate_embedding(phrase)
    print(f"{phrase}: {embedding[:5]}...")  # Show first 5 dims
```

### Phase 2: Similarity Accuracy

Test that similar phrases have high similarity:
```python
query = "commit my changes"
similar = ["commit these changes", "create a commit"]
dissimilar = ["check database", "find files"]

for phrase in similar + dissimilar:
    similarity = calculate_similarity(query, phrase)
    expected = "HIGH" if phrase in similar else "LOW"
    print(f"{phrase}: {similarity:.2%} ({expected})")
```

Expected output:
```
commit these changes: 92% (HIGH)
create a commit: 85% (HIGH)
check database: 23% (LOW)
find files: 15% (LOW)
```

### Phase 3: Real-World Queries

Test with actual use cases:
```
Query: "commit and push my code"
Expected: git-commit-push (high), git-commit-protocol (medium)

Query: "is the database healthy"
Expected: database-health-check (high)

Query: "find where authentication happens"
Expected: explore-auth-files (high)

Query: "make a backup"
Expected: backup-database (high)
```

---

## Milestone Breakdown

### Milestone 1: Embedding Generation (Days 1-3)

**Tasks**:
1. Install sentence-transformers
2. Create generate-trigger-embeddings.py
3. Test embedding generation
4. Backfill existing triggers
5. Integrate with create-skill.py

**Time Estimate**: 2-3 hours

**Deliverable**: All triggers have embeddings

### Milestone 2: Semantic Search (Days 4-6)

**Tasks**:
1. Create search-skills-semantic.py
2. Implement similarity search
3. Add context boosting
4. Add prerequisites filtering
5. Test search accuracy
6. Create usage documentation

**Time Estimate**: 2-4 hours

**Deliverable**: Semantic search working

---

## Integration Example

**Before** (exact matching):
```bash
# User must have exact trigger phrase
# Trigger: "commit these changes"

$ execute-skill.py git-commit-protocol
✅ Executing skill...
```

**After** (semantic matching):
```bash
# User can use natural language
$ search-skills-semantic.py "save my work with git"

🔍 Found 2 matching skills:

1. Git Commit (Our Protocol) - 89% match
2. Git Commit & Push - 82% match

# Integration with execute-skill.py:
$ execute-skill.py git-commit-protocol --query "save my work with git"
   ↑ Logs semantic match for analytics
```

---

## Next Steps After Milestones 1-2

Once semantic search is complete:

**Option A**: Export/Import Enhancement
- Share skills with embeddings
- Cross-project skill libraries

**Option B**: Auto-Suggestion System
- Detect user intent from conversation
- Suggest relevant skills proactively
- "I notice you're committing code. Would you like to use git-commit-protocol?"

**Option C**: Skill Discovery
- Browse skills by similarity
- "Show me skills similar to backup-database"
- Category-based recommendations

---

## Milestone Completion Estimate

**Current Progress**: 0%

**Breakdown**:
- Planning: ✅ 100% (this document)
- sentence-transformers installation: ⏸️ 0%
- generate-trigger-embeddings.py: ⏸️ 0%
- Embedding backfill: ⏸️ 0%
- search-skills-semantic.py: ⏸️ 0%
- Context boosting: ⏸️ 0%
- Testing: ⏸️ 0%
- Integration: ⏸️ 0%
- Documentation: 🔄 20% (this status doc)

**Estimated Time to Complete**: 4-8 hours
- Milestone 1 (Embeddings): 2-3 hours
- Milestone 2 (Search): 2-4 hours
- Testing & integration: 1-2 hours

---

## Conclusion

**Semantic search will transform the Skills System** from exact matching to intelligent, natural language understanding.

**Benefits**:
- Users can use any phrasing
- Better skill discovery
- Context-aware suggestions
- Foundation for auto-suggestion
- Improved user experience

**This is a key milestone** that makes the Skills System truly intelligent and user-friendly.

---

**Next**: Install sentence-transformers and implement generate-trigger-embeddings.py! 🚀
