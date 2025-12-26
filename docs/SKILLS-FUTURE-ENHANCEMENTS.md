# Skills System - Future Enhancements

**Status:** Deferred (Post Phase 1 & 2)
**Created:** 2025-12-26
**Scope:** Advanced features for pattern detection, skill evolution, and self-learning

---

## Overview

This document outlines **future enhancements** to the Skills System beyond the initial 4-week implementation (Phase 1 + Phase 2).

**Current Scope (Phases 1-2, 4 weeks):**
- ✅ Manual skill creation (bash scripts, tool sequences, agent spawns)
- ✅ Semantic trigger matching
- ✅ Trust-based execution (low trust → high trust)
- ✅ Performance analytics
- ✅ Export/import capabilities

**Future Scope (Phases 3-4, TBD):**
- 🔮 Automatic pattern detection ("Watcher")
- 🔮 Skill suggestions from conversations
- 🔮 Self-learning and skill evolution
- 🔮 Cross-session learning
- 🔮 A/B testing of skill variants
- 🔮 Proactive recommendations

---

## Phase 3: Watcher (Automatic Pattern Detection)

### Vision

Transform skill creation from **manual** to **semi-automated**: the system watches your conversations, detects patterns, and suggests skills for you to approve.

### Key Features

#### 1. Pattern Detection Engine

**Tool Sequence Detection:**
- Identify repetitive sequences of tool calls (e.g., "Bash → Read → Edit" appearing 5+ times)
- Generate skill candidates automatically
- Score based on frequency and consistency

**User Correction Detection:**
- Parse user messages for correction language: "No, use...", "Always...", "Never..."
- Capture the "right way" from user feedback
- Create skill candidates from corrections

**Iteration Loop Detection:**
- Spot inefficiency: user makes multiple attempts before success
- Detect "debugging spirals" that could be avoided with a skill
- Suggest skills to prevent future iterations

**Example:**
```
[Conversation snippet]
User: Commit these changes
Claude: [runs: git add ., git commit -m "changes"]
User: No, always use heredoc format and include co-author

[Later in conversation]
User: Commit these too
Claude: [runs: git add ., git commit -m "more changes"]
User: Remember the heredoc format!

[End of session]
🔍 Pattern Detected: "git-commit-corrections"
   Type: User corrections (2 instances)
   Confidence: High (consistent feedback)

   Suggested Skill: git-commit-protocol
   - Use heredoc for messages
   - Include co-author footer

   [Create Skill] [Not Yet] [Ignore]
```

#### 2. End-of-Session Analysis

**Automatic Analysis:**
- Runs when `/mem-save` is executed
- Analyzes entire conversation for patterns
- Presents ranked list of skill candidates

**Example Output:**
```bash
$ /mem-save

📊 Session Analysis Complete
   206 messages captured
   3 skill candidates detected

🌟 High Confidence (3 patterns):
   1. git-commit-protocol (user corrections: 2x)
   2. docker-health-check (tool sequence: 4x)
   3. test-and-deploy (iteration loop: 1x, resolved in 3 attempts)

Would you like to review these candidates?
[Yes] [Skip]
```

#### 3. Pattern Scoring & Ranking

**Confidence Calculation:**
```python
confidence_score = (
    (occurrences / max_occurrences) * 0.4 +
    (session_span_days / 30) * 0.3 +
    (project_count / total_projects) * 0.2 +
    (user_corrections_count > 0) * 0.1
)
```

**Priority Scoring:**
```python
priority_score = occurrences × confidence_score × project_count
```

**Ranking:**
- Candidates sorted by priority_score (highest first)
- Minimum threshold: confidence >= 0.5, occurrences >= 2

#### 4. New CLI Commands

**`/mem-skills-suggest`**
```bash
$ /mem-skills-suggest

📋 Skill Candidates (5 pending review)

High Priority:
  [1] git-commit-protocol
      Pattern: User corrections (2x in session #206)
      Confidence: ⭐⭐⭐ (0.92)
      Would save: ~45 seconds per use

  [2] docker-health-check
      Pattern: Tool sequence (git status → docker ps → docker logs)
      Confidence: ⭐⭐ (0.78)
      Seen: 4 times across 2 sessions

Medium Priority:
  [3] test-before-deploy
      Pattern: Iteration loop (3 failed attempts → success)
      Confidence: ⭐⭐ (0.65)

[Review Candidate] [Create All High Priority] [Dismiss All]
```

**`/mem-skills-candidate [id]`**
```bash
$ /mem-skills-candidate 1

git-commit-protocol
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Detection Details:
  Pattern Type: User corrections
  First Seen: Session #204 (2025-12-20)
  Last Seen: Session #206 (2025-12-26)
  Occurrences: 2
  Confidence: 0.92 (High)

User Feedback Captured:
  1. "Always use heredoc format for commit messages"
  2. "Include co-author footer"

Proposed Skill:
  Trigger: "commit", "create commit"
  Steps:
    1. git status (check for changes)
    2. git diff (show changes)
    3. git log -5 (see recent commits for style)
    4. Draft message using heredoc
    5. Include co-author footer
    6. git commit
    7. git status (verify)

[Create Skill] [Edit Before Creating] [Dismiss]
```

### Implementation Details

#### Database Changes

**skills_patterns table** (already exists from Phase 1 schema):
```sql
CREATE TABLE skills_patterns (
    id SERIAL PRIMARY KEY,
    pattern_name VARCHAR(255),
    pattern_type VARCHAR(100),  -- tool_sequence, user_correction, iteration_loop
    detection_rules JSONB,
    signature_hash VARCHAR(64),  -- For deduplication

    occurrences INTEGER DEFAULT 1,
    first_seen_snapshot_id INTEGER REFERENCES context_snapshots(id),
    last_seen_snapshot_id INTEGER REFERENCES context_snapshots(id),
    seen_in_projects TEXT[],

    confidence_score FLOAT,
    priority_score FLOAT GENERATED ALWAYS AS (
        occurrences::FLOAT * confidence_score *
        COALESCE(array_length(seen_in_projects, 1), 1)::FLOAT
    ) STORED,

    status VARCHAR(50) DEFAULT 'candidate',  -- candidate, approved, rejected, created
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    rejection_reason TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### New Scripts

**`processor/src/watcher.js`**
- `detectToolSequences(messages)` - Find repeated N-grams
- `detectUserCorrections(messages)` - NLP for correction detection
- `detectIterationLoops(messages)` - Identify debugging spirals
- `scorePattern(pattern)` - Calculate confidence
- `suggestSkill(pattern)` - Generate skill definition from pattern

**`skills-suggest.py`**
- List all candidates ranked by priority
- Interactive review interface
- Bulk approve high-confidence patterns

**`skills-candidate.py`**
- Show detailed pattern information
- Allow editing before creation
- Dismiss patterns

### Testing Strategy

**Unit Tests:**
- Tool sequence N-gram detection
- Correction language parsing
- Iteration loop identification
- Confidence scoring accuracy

**Integration Tests:**
- End-to-end pattern → candidate → skill creation
- Cross-session pattern aggregation
- Deduplication (same pattern detected multiple times)

**Test Data:**
- Synthetic conversations with known patterns
- Real anonymized claude-memory sessions
- Edge cases (false positives, ambiguous patterns)

### Risks & Considerations

**False Positives:**
- One-time debugging != reusable pattern
- Solution: Require minimum occurrences (2-3x)
- Solution: User can dismiss patterns

**Privacy:**
- Pattern detection analyzes all conversations
- Solution: Only store pattern metadata, not full messages
- Solution: User controls what gets analyzed

**Noise:**
- Too many low-quality suggestions
- Solution: Minimum confidence threshold (0.5)
- Solution: Top 10 candidates only, ranked by priority

---

## Phase 4: Self-Learning (Skill Evolution & Optimization)

### Vision

Transform skills from **static** to **dynamic**: skills improve based on real-world usage, user feedback, and performance data.

### Key Features

#### 1. Skill Evolution Engine

**Version Tracking:**
- Each skill update creates a new version (v1 → v2 → v3...)
- Old versions preserved for rollback
- Performance tracked separately per version

**Evolution Triggers:**
- User corrections during execution
- Repeated failures (success rate drops)
- Performance degradation (slower than before)
- New prerequisites discovered

**Example:**
```
User: Actually, run tests before committing

Claude: 📝 Skill Update Suggested

        Current: git-commit-protocol v1
        - git status
        - git diff
        - git commit

        Proposed: git-commit-protocol v2
        - git status
        - git diff
        - npm test ← NEW
        - git commit

        Should I update the skill?
        [Yes, Update] [No, Just This Time] [Make It Optional]

User: Make it optional

Claude: ✅ Updated to v2 with optional pre-commit tests
        Next execution will ask: "Run tests? [Y/n]"
```

**Update Strategies:**
- **Add Steps**: Insert new tool calls
- **Modify Parameters**: Change default values
- **Change Prerequisites**: Add/remove requirements
- **Adjust Triggers**: Improve semantic matching

#### 2. Cross-Session Learning

**Pattern Aggregation:**
- Patterns detected across multiple sessions
- Same pattern in different projects → global skill candidate
- Project-specific variations → project-scoped skills

**Example:**
```
Session #204 (NLQ project): git status → diff → commit (heredoc)
Session #206 (NLQ project): git status → diff → commit (heredoc)
Session #210 (pgquery project): git status → diff → commit (heredoc)

🔍 Cross-Session Pattern Detected
   Pattern: git-commit-heredoc
   Seen: 3 sessions across 2 projects
   Confidence: Very High (0.95)

   Suggestion: Create as GLOBAL skill (all projects)
   [Create Global] [Create Per-Project] [Not Yet]
```

#### 3. Confidence Auto-Adjustment

**Dynamic Confidence:**
```python
def update_confidence(skill):
    # Start with base confidence
    confidence = skill.confidence_score

    # Adjust based on recent performance (last 10 uses)
    recent_success_rate = get_recent_success_rate(skill, limit=10)
    if recent_success_rate >= 0.95:
        confidence = min(1.0, confidence + 0.05)  # Increase
    elif recent_success_rate < 0.7:
        confidence = max(0.3, confidence - 0.1)  # Decrease

    # User feedback adjustments
    recent_rejections = count_recent_rejections(skill, days=7)
    if recent_rejections >= 3:
        confidence = max(0.3, confidence - 0.15)

    return confidence
```

**Trust Level Transitions:**
```
High Trust (auto-execute) → Low Trust (require approval)
  Trigger: Success rate drops below 80%

Low Trust (require approval) → High Trust (auto-execute)
  Trigger: 10 consecutive successes + 90%+ success rate
```

#### 4. Skill Variants & A/B Testing

**Variant Creation:**
- When evolution creates v2, both v1 and v2 are active
- System randomly selects version (50/50 split)
- Performance tracked separately

**Example:**
```sql
-- skills_commands table
agent_id | version | command_definition               | is_active
---------+---------+----------------------------------+-----------
   42    |    1    | {steps: [status, diff, commit]}  | true
   42    |    2    | {steps: [status, diff, test, commit]} | true
```

**Performance Comparison:**
```bash
$ /mem-skills-show git-commit-protocol

git-commit-protocol
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Active Versions (A/B Testing):
  v1 (original): 15 uses, 93% success, avg 42s
  v2 (with tests): 12 uses, 100% success, avg 58s ← 16s slower but safer

Recommendation: Keep v2 (higher reliability despite time increase)
[Accept Recommendation] [Keep Both] [Revert to v1]
```

**Winner Selection:**
- After 20+ combined uses, system suggests best version
- Factors: success rate (primary), time saved (secondary), user feedback
- User makes final decision

#### 5. Proactive Recommendations

**During-Work Suggestions:**
- Monitor conversation in real-time (not just end-of-session)
- Suggest skills when relevant patterns detected
- Non-intrusive notifications

**Example:**
```
User: Can you check the database health?

[Claude detects: 'database health' matches 'check-db-health' skill]

Claude: 💡 I have a skill for this: check-db-health
           Used 15 times, 93% success rate

           Should I use it?
           [Yes] [No, show me manual steps]

User: Yes

Claude: ✓ Using check-db-health skill...
        [Executes: psql checks, connection test, row counts]

        ✅ Database healthy
           - Version: PostgreSQL 14.5
           - Size: 247 MB
           - Connections: 8/100
           - Total snapshots: 206
```

**Frequency Controls:**
- Maximum 1 suggestion per 5 minutes (avoid spam)
- User can disable proactive suggestions
- Only high-confidence skills (0.8+) suggested proactively

#### 6. Skill Optimization Dashboard

**Performance Analytics:**
```bash
$ /mem-skills-optimize

📊 Skill Performance Analysis

⚠️  Needs Attention (3 skills):
    1. deploy-to-staging
       Success rate: 67% (down from 95% last month)
       Issue: Failing on new Docker version
       Suggestion: Update prerequisites to check Docker version

    2. backup-database
       Avg execution time: 145s (up from 45s)
       Issue: Database size increased 3x
       Suggestion: Add compression step

    3. api-health-check
       False positive rate: 40%
       Issue: Trigger too broad ("check", "api")
       Suggestion: Tighten semantic match to 0.85

✅ High Performers (5 skills):
   - git-commit-protocol: 100% success, 42s avg
   - test-and-deploy: 98% success, 3.2min avg
   - scaffold-feature: 100% success, 1.8min avg

[Fix All Issues] [Review Individually] [Dismiss]
```

**Optimization Actions:**
- Identify slow skills (> 2 standard deviations from mean)
- Detect degrading skills (success rate trending down)
- Suggest improvements (caching, parallelization, better prerequisites)

### Implementation Details

#### Database Changes

**skills_agents (add columns):**
```sql
ALTER TABLE skills_agents
ADD COLUMN auto_adjust_confidence BOOLEAN DEFAULT TRUE,
ADD COLUMN min_confidence_threshold FLOAT DEFAULT 0.3,
ADD COLUMN max_confidence_threshold FLOAT DEFAULT 1.0;
```

**skills_commands (version tracking):**
- `version` column already exists
- Multiple rows per agent_id for different versions
- `is_active` determines which versions are in A/B testing

**skills_performance_log (add evolution tracking):**
```sql
ALTER TABLE skills_performance_log
ADD COLUMN command_version INTEGER,
ADD COLUMN evolution_triggered BOOLEAN DEFAULT FALSE,
ADD COLUMN evolution_suggestion TEXT;
```

#### New Scripts

**`processor/src/evolver.js`**
- `detectEvolutionTrigger(skill, feedback)` - Identify when skill needs updating
- `proposeSkillUpdate(skill, trigger)` - Generate v2 definition
- `compareVersions(v1, v2)` - A/B test analysis
- `autoAdjustConfidence(skill)` - Dynamic confidence calculation

**`skills-optimize.py`**
- Analyze all skills for performance issues
- Suggest improvements
- Batch fix common problems

**`skills-evolve.py`**
- Manually trigger skill evolution
- Preview proposed changes
- Rollback to previous version

### Testing Strategy

**Unit Tests:**
- Confidence calculation accuracy
- Evolution trigger detection
- Version comparison logic
- Winner selection algorithm

**Integration Tests:**
- Full evolution cycle (v1 → v2 → winner)
- Cross-session pattern aggregation
- A/B testing with synthetic data

**Performance Tests:**
- Confidence updates don't slow down execution
- Real-time monitoring overhead < 50ms
- Dashboard query performance (< 500ms)

### Risks & Considerations

**Skill Instability:**
- Too frequent updates confuse users
- Solution: Minimum 1 week between evolution cycles
- Solution: User approval required for all changes

**A/B Testing Confusion:**
- User gets inconsistent behavior
- Solution: Clear notification when using different version
- Solution: User can lock to specific version

**Complexity:**
- System becomes difficult to understand
- Solution: Comprehensive documentation
- Solution: Opt-in for advanced features
- Solution: Simple mode (disable evolution)

---

## Implementation Timeline (When Ready)

### Phase 3: Watcher (2 weeks)

**Week 5:**
- Days 1-3: Tool sequence detection
- Days 4-5: User correction detection
- Days 6-7: Iteration loop detection

**Week 6:**
- Days 8-9: Pattern scoring & ranking
- Days 10-11: Snapshot integration (auto-capture hook)
- Days 12-14: Pattern action flow, CLI commands, testing

### Phase 4: Self-Learning (2 weeks)

**Week 7:**
- Days 1-3: Skill evolution engine
- Days 4-6: Cross-session learning
- Days 7-8: Confidence auto-adjustment

**Week 8:**
- Days 9-10: Skill variants & A/B testing
- Days 11-12: Proactive recommendations
- Days 13-14: Optimization dashboard, testing

**Total: 4 additional weeks**

---

## Why Defer Phases 3-4?

### Focus on Solid Foundation

**Phase 1 + Phase 2 provides:**
- Complete manual skill creation workflow
- Proven execution framework (bash, tool sequences, agents)
- Semantic matching and discovery
- Trust-based execution model
- Performance tracking and analytics
- Export/import for portability

**This is a complete, usable system** that adds immediate value to claude-memory.

### Incremental Validation

**Learn from usage before automating:**
- Which skill types are most valuable?
- What patterns are actually repetitive?
- How accurate is pattern detection?
- Do users trust automated suggestions?

**User feedback will shape Phase 3-4 design:**
- Real usage data informs detection algorithms
- User preferences guide automation level
- Performance metrics validate optimization strategies

### Reduced Complexity Risk

**Phase 3-4 adds significant complexity:**
- Pattern detection algorithms (false positives)
- NLP for correction parsing
- A/B testing infrastructure
- Real-time monitoring overhead
- Version management complexity

**Better to:**
1. Ship working foundation (Phases 1-2)
2. Validate with real users
3. Refine approach based on feedback
4. Then add automation (Phases 3-4)

---

## Decision Points Before Implementing

### User Research Needed

**Questions to answer:**
1. Do users actually want automatic pattern detection?
2. How much automation vs control do users prefer?
3. What false positive rate is acceptable for skill suggestions?
4. Should skill evolution be automatic or always require approval?

### Technical Validation Needed

**Proof of concepts:**
1. Pattern detection accuracy (test with real conversations)
2. NLP quality for correction parsing
3. Confidence scoring effectiveness
4. A/B testing infrastructure feasibility

### Resource Requirements

**Phase 3 complexity:**
- Medium (pattern detection algorithms, NLP parsing)
- Estimated: 2 weeks with testing

**Phase 4 complexity:**
- High (version management, A/B testing, real-time monitoring)
- Estimated: 2 weeks with testing

**Total additional investment:** 4 weeks

**Question:** Is this worth it vs other claude-memory enhancements?

---

## Alternative Approaches

### Simplified Pattern Detection

**Instead of full Watcher:**
- Manual pattern marking: User marks sequences as "skill candidate"
- Simpler detection: Only obvious repetition (3+ identical tool sequences)
- No NLP: User writes correction patterns manually

**Pros:**
- Much simpler to implement (3 days vs 2 weeks)
- No false positives
- User maintains full control

**Cons:**
- Less automated
- Requires user vigilance
- Misses subtle patterns

### Community Skill Marketplace

**Instead of per-user pattern detection:**
- Share skills across users
- Upvote/downvote skills
- Community maintains skill library
- Import popular skills

**Pros:**
- Leverage collective intelligence
- Faster skill accumulation
- Quality filtering via voting

**Cons:**
- Privacy concerns (sharing workflow patterns)
- Not personalized to user
- Requires infrastructure

---

## Next Steps

**Before implementing Phases 3-4:**

1. **Complete Phase 1-2** (4 weeks)
2. **Deploy to production**
3. **Gather user feedback** (4-8 weeks of usage)
4. **Analyze skill usage patterns**
   - Which categories most used?
   - Success rate trends?
   - Common pain points?
5. **Decide:** Phase 3-4 worth it vs other priorities?
6. **If yes:** Refine design based on learnings
7. **If no:** Consider alternative approaches

**Documentation to update when ready:**
- This file (refined scope based on learnings)
- SKILLS-PHASE3-ROADMAP.md (original preserved for reference)
- SKILLS-PHASE4-ROADMAP.md (original preserved for reference)
- SKILLS-SYSTEM-ARCHITECTURE.md (add Phase 3-4 architecture if implemented)

---

## Conclusion

Phases 3-4 represent **powerful future enhancements** that could significantly improve the Skills System. However, **delivering a solid foundation first** (Phases 1-2) is the pragmatic approach.

**Key Principle:** Ship, learn, iterate.

**Timeline:**
- **Now → Month 1:** Phase 1-2 implementation
- **Month 2-3:** Production usage, feedback gathering
- **Month 4:** Decision point on Phase 3-4
- **Month 5-6 (if approved):** Phase 3-4 implementation

This phased approach **reduces risk**, **validates assumptions**, and ensures the Skills System provides **immediate value** while leaving room for future sophistication.
