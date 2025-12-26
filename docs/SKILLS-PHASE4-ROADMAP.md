# Skills System - Phase 4 Implementation Roadmap

**Phase:** Self-Learning (Weeks 7-8)
**Goal:** Skill evolution, optimization, and proactive assistance
**Status:** Planning
**Prerequisites:** Phases 1, 2, & 3 complete
**Target Duration:** 2 weeks

---

## Phase 4 Overview

### What We're Building

The **Self-Learning** capabilities - a system that continuously improves:

1. **Skill Evolution** - Skills improve based on user feedback
2. **Cross-Session Learning** - Learn patterns across multiple sessions
3. **Confidence Auto-Adjustment** - Dynamic confidence based on performance
4. **Skill Variants & A/B Testing** - Test different approaches
5. **Proactive Recommendations** - Suggest skills during work, not just at end
6. **Skill Optimization** - Identify and improve slow or failing skills

### What This Enables

**Before Phase 4:**
```
Skills are static - created once, never change
User feedback is logged but not acted upon
Skills suggested only at end of session
```

**After Phase 4:**
```
User: Actually, run tests before committing

Claude: 📝 Noted! Should I update the 'git-commit-protocol' skill
        to always run tests before committing?

        Current skill: git status → diff → commit
        Updated skill: git status → diff → npm test → commit

        [Yes, Update Skill] [No, Just This Time] [Make It Optional]

User: Make it optional

Claude: ✅ Updated skill with optional pre-commit tests
        Next time I'll ask: "Run tests before committing? [Y/n]"

        Skill version updated: v1 → v2
        Performance will be tracked separately for comparison
```

---

## Architecture Overview

### Self-Learning Pipeline

```
┌──────────────────┐
│  Skill Execution │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐      ┌──────────────────┐
│  User Feedback   │─────▶│  Learning Signal │
│  - Corrections   │      │  Detected        │
│  - Improvements  │      └────────┬─────────┘
│  - Rejections    │               │
└──────────────────┘               ▼
                          ┌──────────────────┐
                          │  Skill Evolution  │
                          │  - Update defn   │
                          │  - New version   │
                          │  - A/B test      │
                          └────────┬─────────┘
                                   │
                                   ▼
                          ┌──────────────────┐
                          │  Performance      │
                          │  Tracking         │
                          │  - Compare v1/v2 │
                          │  - Auto-adjust   │
                          └──────────────────┘
```

---

## Milestones

### Milestone 1: Skill Evolution Engine (Days 1-3)

**Goal:** Skills can be updated based on user feedback

**Concepts:**

1. **Versioning** - Track skill versions (v1, v2, v3...)
2. **Evolution Triggers** - User corrections, repeated failures, performance degradation
3. **Update Strategies** - Add steps, modify parameters, change prerequisites
4. **Performance Tracking** - Compare versions to validate improvements

**Tasks:**
- [ ] Implement skill versioning
- [ ] Create `evolve-skill.py` script
- [ ] Implement evolution strategies
- [ ] Track performance per version
- [ ] Create version comparison views
- [ ] Test evolution workflow
- [ ] Document evolution process

**Implementation:**

#### Skill Versioning

```python
#!/usr/bin/env python3
"""
Evolve a skill based on feedback

Usage:
  python3 evolve-skill.py git-commit-protocol --add-step "npm test" --position 2
  python3 evolve-skill.py check-db-health --update-threshold 0.9
"""

import argparse
import psycopg2
import json
from datetime import datetime

def evolve_skill(skill_name, evolution_type, changes, reason):
    """
    Create a new version of a skill with modifications

    Args:
        skill_name: Name of skill to evolve
        evolution_type: "add_step", "remove_step", "modify_parameter", "update_prerequisite"
        changes: Dict describing the changes
        reason: User feedback or performance reason
    """

    conn = psycopg2.connect(...)
    cur = conn.cursor()

    # Get current skill version
    cur.execute("""
        SELECT id, version, command_type
        FROM skills_agents sa
        JOIN skills_commands sc ON sc.agent_id = sa.id
        WHERE sa.agent_name = %s
        ORDER BY sa.version DESC
        LIMIT 1
    """, (skill_name,))

    current = cur.fetchone()
    if not current:
        print(f"Skill not found: {skill_name}")
        return

    skill_id, current_version, cmd_type = current

    # Get current command definition
    cur.execute("""
        SELECT command_definition, parameters, prerequisites
        FROM skills_commands
        WHERE agent_id = %s
        ORDER BY version DESC
        LIMIT 1
    """, (skill_id,))

    cmd_data = cur.fetchone()
    current_defn, current_params, current_prereqs = cmd_data

    # Apply evolution
    new_defn = apply_evolution(
        evolution_type,
        changes,
        current_defn,
        current_params,
        current_prereqs
    )

    # Create new version
    new_version = current_version + 1

    # Update skills_agents version
    cur.execute("""
        UPDATE skills_agents
        SET version = %s,
            last_improved_snapshot_id = (SELECT MAX(id) FROM context_snapshots),
            updated_at = NOW()
        WHERE id = %s
    """, (new_version, skill_id))

    # Insert new command definition
    cur.execute("""
        INSERT INTO skills_commands
        (agent_id, version, command_type, command_definition, parameters, prerequisites)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        skill_id,
        new_version,
        cmd_type,
        json.dumps(new_defn['definition']),
        json.dumps(new_defn['parameters']),
        json.dumps(new_defn['prerequisites'])
    ))

    # Log evolution
    cur.execute("""
        INSERT INTO skills_performance_log
        (agent_id, outcome, user_feedback, before_definition, after_definition, executed_at)
        VALUES (%s, 'user_corrected', %s, %s, %s, NOW())
    """, (
        skill_id,
        reason,
        json.dumps(current_defn),
        json.dumps(new_defn['definition'])
    ))

    conn.commit()

    print(f"✅ Skill evolved: {skill_name}")
    print(f"   Version: v{current_version} → v{new_version}")
    print(f"   Reason: {reason}")
    print(f"\n   Changes applied:")
    describe_evolution(evolution_type, changes)

    cur.close()
    conn.close()

    return new_version

def apply_evolution(evolution_type, changes, current_defn, current_params, current_prereqs):
    """Apply evolution to skill definition"""

    new_defn = current_defn.copy() if current_defn else {}
    new_params = current_params.copy() if current_params else {}
    new_prereqs = current_prereqs.copy() if current_prereqs else {}

    if evolution_type == 'add_step':
        # Add a step to tool sequence
        steps = new_defn.get('steps', [])
        new_step = {
            'step': changes['position'],
            'description': changes['description'],
            'tools': changes['tools'],
            'parallel': changes.get('parallel', False)
        }

        # Insert at position
        steps.insert(changes['position'] - 1, new_step)

        # Renumber steps
        for i, step in enumerate(steps, 1):
            step['step'] = i

        new_defn['steps'] = steps

    elif evolution_type == 'remove_step':
        # Remove a step
        steps = new_defn.get('steps', [])
        steps = [s for s in steps if s['step'] != changes['step_number']]

        # Renumber
        for i, step in enumerate(steps, 1):
            step['step'] = i

        new_defn['steps'] = steps

    elif evolution_type == 'modify_parameter':
        # Update parameter definition
        param_name = changes['parameter']
        new_params[param_name] = changes['new_value']

    elif evolution_type == 'update_prerequisite':
        # Update prerequisite
        prereq_name = changes['prerequisite']
        new_prereqs[prereq_name] = changes['required']

    elif evolution_type == 'add_validation':
        # Add validation to final step
        steps = new_defn.get('steps', [])
        if steps:
            last_step = steps[-1]
            last_step['validation'] = changes['validation']

    return {
        'definition': new_defn,
        'parameters': new_params,
        'prerequisites': new_prereqs
    }

def describe_evolution(evolution_type, changes):
    """Print human-readable description of changes"""

    if evolution_type == 'add_step':
        print(f"   - Added step {changes['position']}: {changes['description']}")

    elif evolution_type == 'remove_step':
        print(f"   - Removed step {changes['step_number']}")

    elif evolution_type == 'modify_parameter':
        print(f"   - Updated parameter '{changes['parameter']}'")

    elif evolution_type == 'update_prerequisite':
        status = "required" if changes['required'] else "optional"
        print(f"   - Made '{changes['prerequisite']}' {status}")
```

**Example Evolution:**

```python
# User says: "Run tests before committing"

# Evolution 1: Add optional test step
evolve_skill(
    skill_name='git-commit-protocol',
    evolution_type='add_step',
    changes={
        'position': 2,  # Insert at step 2 (after status/diff, before commit)
        'description': 'Run tests (optional)',
        'tools': [{
            'tool': 'Bash',
            'command': 'npm test',
            'description': 'Run test suite',
            'optional': True
        }],
        'parallel': False
    },
    reason='User requested: Always run tests before committing'
)

# Result: Skill updated from v1 to v2 with new step
```

**Validation:**
- [ ] Skill versions tracked
- [ ] Evolution strategies work
- [ ] Definitions updated correctly
- [ ] Performance logged per version
- [ ] User can compare versions

**Deliverables:**
- ✅ `evolve-skill.py` script
- ✅ Versioning system
- ✅ Performance comparison views
- ✅ Documentation

---

### Milestone 2: Cross-Session Learning (Days 4-6)

**Goal:** Learn patterns across multiple sessions, not just single snapshots

**Concepts:**

1. **Aggregate Patterns** - Patterns that appear across sessions
2. **Cross-Project Intelligence** - Learn from similar work in different projects
3. **Temporal Patterns** - Detect weekly/daily rhythms (e.g., "Friday deployments")
4. **Skill Recommendations** - Suggest skills based on historical context

**Tasks:**
- [ ] Implement cross-session pattern aggregation
- [ ] Create pattern timeline analysis
- [ ] Build recommendation engine
- [ ] Test with multi-session data
- [ ] Document recommendation logic

**Implementation:**

#### Cross-Session Pattern Analysis

```python
#!/usr/bin/env python3
"""
Analyze patterns across multiple sessions

Usage:
  python3 analyze-cross-session-patterns.py --days 30
  python3 analyze-cross-session-patterns.py --project /path/to/project
"""

import psycopg2
from datetime import datetime, timedelta
from collections import Counter

def analyze_cross_session_patterns(days=30, project_path=None):
    """
    Analyze patterns across recent sessions

    Looks for:
    - Repeated patterns across sessions
    - Temporal patterns (daily, weekly rhythms)
    - Cross-project similarities
    """

    conn = psycopg2.connect(...)
    cur = conn.cursor()

    # Get recent snapshots
    query = """
        SELECT id, project_path, timestamp, raw_context
        FROM context_snapshots
        WHERE timestamp > NOW() - INTERVAL '%s days'
    """
    params = [days]

    if project_path:
        query += " AND project_path = %s"
        params.append(project_path)

    query += " ORDER BY timestamp DESC"

    cur.execute(query, params)
    snapshots = cur.fetchall()

    # Extract all tool sequences from all sessions
    all_sequences = []
    sequence_by_day = {}
    sequence_by_project = {}

    for snap_id, proj_path, timestamp, raw_context in snapshots:
        messages = raw_context.get('messages', [])

        # Extract tool calls
        from detect_patterns import extract_tool_calls, find_ngrams

        tool_calls = extract_tool_calls(messages)
        sequences = find_ngrams(tool_calls, min_length=2, max_length=4)

        # Track by day of week
        day_name = timestamp.strftime('%A')
        if day_name not in sequence_by_day:
            sequence_by_day[day_name] = []
        sequence_by_day[day_name].extend([s['sequence'] for s in sequences])

        # Track by project
        if proj_path not in sequence_by_project:
            sequence_by_project[proj_path] = []
        sequence_by_project[proj_path].extend([s['sequence'] for s in sequences])

        all_sequences.extend([s['sequence'] for s in sequences])

    # Find patterns that appear across multiple sessions
    sequence_counts = Counter([tuple(seq) for seq in all_sequences])
    cross_session_patterns = [
        (seq, count)
        for seq, count in sequence_counts.items()
        if count >= 3  # Appears in 3+ sessions
    ]

    # Temporal analysis
    temporal_patterns = []
    for day, sequences in sequence_by_day.items():
        day_counts = Counter([tuple(seq) for seq in sequences])
        # Find sequences specific to this day
        day_specific = [
            (seq, count)
            for seq, count in day_counts.items()
            if count >= 2  # Appears multiple times on this day
        ]
        if day_specific:
            temporal_patterns.append({
                'day': day,
                'patterns': day_specific
            })

    # Cross-project similarities
    project_similarities = []
    projects = list(sequence_by_project.keys())
    for i, proj1 in enumerate(projects):
        for proj2 in projects[i+1:]:
            # Find common sequences
            seqs1 = set([tuple(s) for s in sequence_by_project[proj1]])
            seqs2 = set([tuple(s) for s in sequence_by_project[proj2]])
            common = seqs1.intersection(seqs2)

            if common:
                project_similarities.append({
                    'project1': proj1,
                    'project2': proj2,
                    'common_patterns': len(common)
                })

    # Generate recommendations
    recommendations = generate_recommendations(
        cross_session_patterns,
        temporal_patterns,
        project_similarities
    )

    # Print results
    print(f"\n📊 Cross-Session Pattern Analysis ({days} days)")
    print("=" * 60)

    print(f"\nPatterns Across Multiple Sessions:")
    for pattern, count in cross_session_patterns[:5]:
        print(f"  {count}x: {' → '.join([f'{t[0]}:{t[1]}' for t in pattern])}")

    print(f"\nTemporal Patterns:")
    for temporal in temporal_patterns:
        print(f"  {temporal['day']}: {len(temporal['patterns'])} patterns")

    print(f"\nCross-Project Similarities:")
    for sim in project_similarities[:3]:
        print(f"  {sim['project1']} ↔ {sim['project2']}: {sim['common_patterns']} common patterns")

    print(f"\nRecommendations:")
    for rec in recommendations:
        print(f"  {rec['type']}: {rec['description']}")

    cur.close()
    conn.close()

    return {
        'cross_session_patterns': cross_session_patterns,
        'temporal_patterns': temporal_patterns,
        'project_similarities': project_similarities,
        'recommendations': recommendations
    }

def generate_recommendations(cross_session, temporal, similarities):
    """Generate skill creation recommendations from analysis"""

    recommendations = []

    # Recommend skills for cross-session patterns
    for pattern, count in cross_session[:3]:
        recommendations.append({
            'type': 'cross_session_skill',
            'description': f"Create skill for sequence appearing in {count} sessions",
            'pattern': pattern,
            'confidence': min(count / 10, 0.95)
        })

    # Recommend temporal skills (e.g., "Friday deployment workflow")
    for temporal in temporal:
        if temporal['day'] in ['Friday', 'Monday']:  # Common deploy days
            recommendations.append({
                'type': 'temporal_skill',
                'description': f"Create skill for {temporal['day']} workflows",
                'day': temporal['day'],
                'confidence': 0.75
            })

    # Recommend sharing skills across projects
    for sim in similarities:
        if sim['common_patterns'] >= 3:
            recommendations.append({
                'type': 'cross_project_skill',
                'description': f"Share skills between {sim['project1']} and {sim['project2']}",
                'projects': [sim['project1'], sim['project2']],
                'confidence': 0.80
            })

    return recommendations
```

**Validation:**
- [ ] Cross-session patterns detected
- [ ] Temporal patterns identified
- [ ] Recommendations generated
- [ ] Confidence scores reasonable

**Deliverables:**
- ✅ Cross-session analysis script
- ✅ Recommendation engine
- ✅ Documentation

---

### Milestone 3: Confidence Auto-Adjustment (Days 7-8)

**Goal:** Dynamically adjust confidence based on performance

**Logic:**

```
Initial Confidence = 0.8 (default)

After each execution:
  If success:
    confidence += 0.02  (up to max 0.98)

  If failure:
    confidence -= 0.05  (down to min 0.3)

  If user rejects suggestion:
    confidence -= 0.10

  If success rate drops below 70% over last 10 uses:
    confidence = 0.5  (mark for review)
```

**Implementation:**

```python
def auto_adjust_confidence(skill_id, outcome, was_accepted):
    """
    Automatically adjust skill confidence based on performance
    """

    conn = psycopg2.connect(...)
    cur = conn.cursor()

    # Get current stats
    cur.execute("""
        SELECT
            confidence_score,
            use_count,
            success_count,
            failure_count
        FROM skills_agents
        WHERE id = %s
    """, (skill_id,))

    current_confidence, uses, successes, failures = cur.fetchone()

    # Calculate new confidence
    adjustment = 0

    if outcome == 'success':
        adjustment = +0.02  # Small boost for success

    elif outcome == 'failed':
        adjustment = -0.05  # Penalty for failure

    elif outcome == 'user_rejected':
        adjustment = -0.10  # Larger penalty for rejection

    # Apply adjustment
    new_confidence = max(0.3, min(0.98, current_confidence + adjustment))

    # Check recent performance (last 10 uses)
    if uses >= 10:
        recent_success_rate = successes / uses

        if recent_success_rate < 0.7:
            # Performance degradation - reset to medium confidence
            new_confidence = 0.5

    # Update database
    cur.execute("""
        UPDATE skills_agents
        SET confidence_score = %s
        WHERE id = %s
    """, (new_confidence, skill_id))

    conn.commit()

    # Log if significant change
    if abs(new_confidence - current_confidence) > 0.05:
        print(f"📊 Confidence adjusted: {current_confidence:.2f} → {new_confidence:.2f}")

        if new_confidence < 0.6:
            print(f"⚠️  Low confidence - skill may need review")

    cur.close()
    conn.close()
```

**Validation:**
- [ ] Confidence adjusts appropriately
- [ ] Min/max bounds enforced
- [ ] Performance degradation detected
- [ ] Low confidence flagged

**Deliverables:**
- ✅ Auto-adjustment logic
- ✅ Integration with execution
- ✅ Alerting for low confidence

---

### Milestone 4: Skill Variants & A/B Testing (Days 9-10)

**Goal:** Test different skill approaches and automatically choose the best

**Concept:**

```
Skill: git-commit-protocol

Variant A (v1): status → diff → commit
Variant B (v2): status → diff → test → commit

Test both variants alternately:
- Execution 1: Use Variant A
- Execution 2: Use Variant B
- Execution 3: Use Variant A
...

After 10 executions each:
- Compare success rates
- Compare execution times
- Compare user acceptance
- Promote winner as default
```

**Implementation:**

```python
#!/usr/bin/env python3
"""
A/B test skill variants

Usage:
  python3 ab-test-skills.py git-commit-protocol --variant-a 1 --variant-b 2 --samples 10
"""

def ab_test_variants(skill_name, version_a, version_b, samples_per_variant=10):
    """
    A/B test two skill versions

    Alternately suggests each variant and tracks performance
    """

    conn = psycopg2.connect(...)
    cur = conn.cursor()

    # Get skill ID
    cur.execute("SELECT id FROM skills_agents WHERE agent_name = %s", (skill_name,))
    skill_id = cur.fetchone()[0]

    # Track test results
    results_a = {'successes': 0, 'failures': 0, 'avg_time': []}
    results_b = {'successes': 0, 'failures': 0, 'avg_time': []}

    # Get performance for each variant
    cur.execute("""
        SELECT
            sc.version,
            spl.outcome,
            spl.execution_time_ms,
            spl.was_suggestion_accepted
        FROM skills_performance_log spl
        JOIN skills_commands sc ON sc.agent_id = spl.agent_id
        WHERE spl.agent_id = %s
          AND sc.version IN (%s, %s)
        ORDER BY spl.executed_at DESC
    """, (skill_id, version_a, version_b))

    for version, outcome, exec_time, accepted in cur.fetchall():
        result_set = results_a if version == version_a else results_b

        if outcome == 'success':
            result_set['successes'] += 1
            if exec_time:
                result_set['avg_time'].append(exec_time)
        else:
            result_set['failures'] += 1

    # Calculate metrics
    metrics_a = calculate_variant_metrics(results_a)
    metrics_b = calculate_variant_metrics(results_b)

    # Determine winner
    winner = determine_winner(metrics_a, metrics_b)

    # Print results
    print(f"\n🧪 A/B Test Results: {skill_name}")
    print("=" * 60)

    print(f"\nVariant A (v{version_a}):")
    print(f"  Success Rate: {metrics_a['success_rate']:.1f}%")
    print(f"  Avg Exec Time: {metrics_a['avg_time_ms'] / 1000:.1f}s")
    print(f"  Total Uses: {metrics_a['total']}")

    print(f"\nVariant B (v{version_b}):")
    print(f"  Success Rate: {metrics_b['success_rate']:.1f}%")
    print(f"  Avg Exec Time: {metrics_b['avg_time_ms'] / 1000:.1f}s")
    print(f"  Total Uses: {metrics_b['total']}")

    print(f"\n{'━' * 60}")
    print(f"Winner: Variant {winner} ({'v' + str(version_a if winner == 'A' else version_b)})")
    print(f"\nRecommendation: {'Promote this variant as default' if winner else 'Continue testing'}")

    cur.close()
    conn.close()

    return winner

def calculate_variant_metrics(results):
    """Calculate performance metrics for a variant"""
    total = results['successes'] + results['failures']
    success_rate = (results['successes'] / total * 100) if total > 0 else 0
    avg_time = sum(results['avg_time']) / len(results['avg_time']) if results['avg_time'] else 0

    return {
        'total': total,
        'success_rate': success_rate,
        'avg_time_ms': avg_time
    }

def determine_winner(metrics_a, metrics_b):
    """
    Determine winning variant based on multiple factors

    Priority:
    1. Success rate (most important)
    2. Execution time (tiebreaker)
    3. Statistical significance
    """

    # Need minimum samples
    if metrics_a['total'] < 5 or metrics_b['total'] < 5:
        return None  # Not enough data

    # Compare success rates
    if metrics_a['success_rate'] > metrics_b['success_rate'] + 5:  # >5% better
        return 'A'
    elif metrics_b['success_rate'] > metrics_a['success_rate'] + 5:
        return 'B'

    # Success rates similar - compare execution time
    if metrics_a['avg_time_ms'] < metrics_b['avg_time_ms'] * 0.9:  # >10% faster
        return 'A'
    elif metrics_b['avg_time_ms'] < metrics_a['avg_time_ms'] * 0.9:
        return 'B'

    # Too close to call
    return None
```

**Validation:**
- [ ] Variants tracked separately
- [ ] Performance compared accurately
- [ ] Winner determined correctly
- [ ] Statistical significance checked

**Deliverables:**
- ✅ A/B testing system
- ✅ Variant comparison
- ✅ Documentation

---

### Milestone 5: Proactive Recommendations (Days 11-12)

**Goal:** Suggest skills during work, not just at end of session

**Triggers:**

1. **Context Match** - Skill matches current file/directory
2. **Time-Based** - Recurring tasks at specific times
3. **Error Detection** - Suggest skill after repeated errors
4. **Workflow Similarity** - Current actions match skill pattern

**Implementation:**

```python
#!/usr/bin/env python3
"""
Proactive skill recommendation engine

Monitors current work and suggests skills in real-time
"""

def check_for_proactive_suggestions(current_context):
    """
    Check if any skills should be proactively suggested

    Args:
        current_context: {
            'current_directory': '/path/to/project',
            'recent_tool_calls': [...],
            'recent_errors': [...],
            'time_of_day': 'morning|afternoon|evening',
            'day_of_week': 'Monday|Tuesday|...'
        }
    """

    suggestions = []

    # Check context-based suggestions
    suggestions.extend(check_context_match(current_context))

    # Check pattern-based suggestions
    suggestions.extend(check_pattern_match(current_context))

    # Check error-based suggestions
    suggestions.extend(check_error_recovery(current_context))

    # Check time-based suggestions
    suggestions.extend(check_temporal_suggestions(current_context))

    # Rank and return top suggestion
    if suggestions:
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        return suggestions[0]

    return None

def check_context_match(context):
    """Find skills matching current directory/project"""

    conn = psycopg2.connect(...)
    cur = conn.cursor()

    current_dir = context['current_directory']

    # Find skills for this project
    cur.execute("""
        SELECT
            agent_name,
            display_name,
            confidence_score,
            use_count
        FROM skills_agents
        WHERE project_path = %s
          AND is_active = TRUE
          AND confidence_score > 0.7
        ORDER BY use_count DESC
        LIMIT 3
    """, (current_dir,))

    suggestions = []
    for name, display, confidence, uses in cur.fetchall():
        suggestions.append({
            'skill_name': name,
            'display_name': display,
            'reason': f"Available for this project ({uses} previous uses)",
            'confidence': confidence * 0.8,  # Slightly lower for proactive
            'type': 'context_match'
        })

    cur.close()
    conn.close()

    return suggestions

def check_pattern_match(context):
    """Check if recent tool calls match a skill pattern"""

    recent_calls = context.get('recent_tool_calls', [])

    if len(recent_calls) < 2:
        return []

    # Search for skills whose patterns partially match
    from search_skills_semantic import search_skills

    # Convert recent calls to query
    query = ' '.join([f"{tool} {cmd}" for tool, cmd in recent_calls])

    matches = search_skills(query, threshold=0.7, limit=3)

    suggestions = []
    for match in matches:
        # Check if pattern is starting to form
        suggestions.append({
            'skill_name': match['agent_name'],
            'display_name': match['display_name'],
            'reason': f"Your recent actions match this skill's pattern",
            'confidence': match['final_score'] * 0.75,
            'type': 'pattern_match'
        })

    return suggestions

def check_error_recovery(context):
    """Suggest skills after repeated errors"""

    recent_errors = context.get('recent_errors', [])

    if len(recent_errors) < 2:
        return []

    # Find skills that might help with this error
    # (Simplified - would use error message similarity)

    return []

def check_temporal_suggestions(context):
    """Suggest skills based on time/day patterns"""

    day = context.get('day_of_week')
    time = context.get('time_of_day')

    suggestions = []

    # Example: Friday afternoon = deployment workflows
    if day == 'Friday' and time == 'afternoon':
        conn = psycopg2.connect(...)
        cur = conn.cursor()

        cur.execute("""
            SELECT agent_name, display_name, confidence_score
            FROM skills_agents
            WHERE category IN ('deployment', 'git')
              AND is_active = TRUE
            LIMIT 2
        """)

        for name, display, confidence in cur.fetchall():
            suggestions.append({
                'skill_name': name,
                'display_name': display,
                'reason': "Friday afternoon - deployment time?",
                'confidence': confidence * 0.6,  # Lower for temporal
                'type': 'temporal'
            })

        cur.close()
        conn.close()

    return suggestions
```

**User Experience:**

```
[User working on NLQ-Reporting project]

User: check if postgres is running

Claude: 🔍 I found a skill that might help: 'check-db-health'
        You've used this 12 times in this project.

        This skill will:
        - Check docker-compose status
        - Test PostgreSQL connection
        - List tables

        Would you like me to use it?
        [Yes] [No, manual this time]
```

**Validation:**
- [ ] Suggestions appear at appropriate times
- [ ] Not too frequent (avoid annoyance)
- [ ] Confidence thresholds appropriate
- [ ] User can easily dismiss

**Deliverables:**
- ✅ Proactive recommendation engine
- ✅ Integration with workflow
- ✅ User experience testing

---

### Milestone 6: Skill Optimization Dashboard (Days 13-14)

**Goal:** Identify and optimize underperforming skills

**Features:**

1. **Performance Monitoring** - Track execution time trends
2. **Failure Analysis** - Identify common failure modes
3. **Usage Patterns** - Understand when skills are used
4. **Optimization Recommendations** - Suggest improvements

**Implementation:**

```python
#!/usr/bin/env python3
"""
Skill optimization dashboard

Usage:
  python3 optimize-skills.py --dashboard
  python3 optimize-skills.py --skill git-commit-protocol
  python3 optimize-skills.py --find-slow
  python3 optimize-skills.py --find-failing
"""

def skills_optimization_dashboard():
    """
    Show optimization opportunities
    """

    conn = psycopg2.connect(...)
    cur = conn.cursor()

    # Find slow skills (>30s avg execution time)
    cur.execute("""
        SELECT
            sa.agent_name,
            sa.display_name,
            AVG(spl.execution_time_ms) as avg_time_ms,
            sa.use_count
        FROM skills_agents sa
        JOIN skills_performance_log spl ON spl.agent_id = sa.id
        WHERE spl.outcome = 'success'
          AND sa.use_count >= 5
        GROUP BY sa.id
        HAVING AVG(spl.execution_time_ms) > 30000
        ORDER BY avg_time_ms DESC
    """)

    slow_skills = cur.fetchall()

    # Find frequently failing skills
    cur.execute("""
        SELECT
            sa.agent_name,
            sa.display_name,
            sa.success_rate,
            sa.use_count
        FROM skills_agents sa
        WHERE sa.success_rate < 80
          AND sa.use_count >= 10
        ORDER BY sa.success_rate ASC
    """)

    failing_skills = cur.fetchall()

    # Find unused skills
    cur.execute("""
        SELECT
            agent_name,
            display_name,
            created_at
        FROM skills_agents
        WHERE use_count = 0
          AND created_at < NOW() - INTERVAL '7 days'
        ORDER BY created_at ASC
    """)

    unused_skills = cur.fetchall()

    # Print dashboard
    print("\n📊 Skills Optimization Dashboard")
    print("=" * 70)

    if slow_skills:
        print("\n🐌 Slow Skills (>30s avg execution time):")
        for name, display, avg_time, uses in slow_skills:
            print(f"  {name}: {avg_time/1000:.1f}s avg ({uses} uses)")
            print(f"    💡 Optimization: Consider parallel execution or caching")

    if failing_skills:
        print("\n❌ Frequently Failing Skills (<80% success rate):")
        for name, display, success_rate, uses in failing_skills:
            print(f"  {name}: {success_rate:.0f}% success ({uses} uses)")
            print(f"    💡 Optimization: Review prerequisites or error handling")

    if unused_skills:
        print("\n💤 Unused Skills (0 uses in 7+ days):")
        for name, display, created in unused_skills:
            days_old = (datetime.now(created.tzinfo) - created).days
            print(f"  {name}: Created {days_old} days ago")
            print(f"    💡 Consider: Archive or improve triggers")

    # Generate optimization recommendations
    recommendations = []

    for name, display, avg_time, uses in slow_skills:
        recommendations.append({
            'skill': name,
            'issue': 'slow_execution',
            'recommendation': 'Consider parallel execution or remove unnecessary steps'
        })

    for name, display, success_rate, uses in failing_skills:
        recommendations.append({
            'skill': name,
            'issue': 'low_success_rate',
            'recommendation': 'Review prerequisites and add validation'
        })

    print(f"\n📋 Optimization Recommendations ({len(recommendations)} total):")
    for rec in recommendations[:5]:
        print(f"\n  {rec['skill']}:")
        print(f"    Issue: {rec['issue']}")
        print(f"    Recommendation: {rec['recommendation']}")

    cur.close()
    conn.close()

if __name__ == '__main__':
    skills_optimization_dashboard()
```

**Validation:**
- [ ] Slow skills identified
- [ ] Failing skills identified
- [ ] Recommendations helpful
- [ ] Dashboard actionable

**Deliverables:**
- ✅ Optimization dashboard
- ✅ Recommendations engine
- ✅ Documentation

---

## Success Criteria

Phase 4 is complete when:

- [ ] All 6 milestones delivered
- [ ] Skills evolve based on feedback
- [ ] Cross-session learning works
- [ ] Confidence auto-adjusts
- [ ] A/B testing functional
- [ ] Proactive recommendations work
- [ ] Optimization dashboard complete
- [ ] At least 2 skills evolved and improved
- [ ] Documentation complete

---

## File Structure After Phase 4

```
claude-memory/
├── evolve-skill.py (NEW)
├── analyze-cross-session-patterns.py (NEW)
├── ab-test-skills.py (NEW)
├── proactive-recommend.py (NEW)
├── optimize-skills.py (NEW)
└── docs/
    ├── SKILLS-SYSTEM-ARCHITECTURE.md
    ├── SKILLS-PHASE1-ROADMAP.md
    ├── SKILLS-PHASE2-ROADMAP.md
    ├── SKILLS-PHASE3-ROADMAP.md
    └── SKILLS-PHASE4-ROADMAP.md (THIS FILE)
```

---

## Complete Skills System

After Phase 4, the complete system includes:

### Phase 1 (Foundation):
- ✅ Manual skill creation
- ✅ Bash script execution
- ✅ Performance logging

### Phase 2 (Intelligence):
- ✅ Semantic matching
- ✅ Tool sequences
- ✅ Agent spawning
- ✅ Analytics & export/import

### Phase 3 (Watcher):
- ✅ Automatic pattern detection
- ✅ End-of-session suggestions
- ✅ Pattern scoring

### Phase 4 (Self-Learning):
- ✅ Skill evolution
- ✅ Cross-session learning
- ✅ Confidence auto-adjustment
- ✅ A/B testing
- ✅ Proactive recommendations
- ✅ Optimization dashboard

---

## Maintenance & Future Enhancements

### Post Phase 4

**Ongoing:**
- Monitor skill performance
- Review low-confidence skills
- Archive unused skills
- Share successful skills across projects

**Future Possibilities:**
- **Team Collaboration**: Shared skill marketplace
- **Natural Language Creation**: "Create a skill that runs tests before committing"
- **Skill Composition**: Chain multiple skills into workflows
- **Conditional Execution**: "Use skill A if X, otherwise skill B"
- **Machine Learning**: Use ML models for pattern detection
- **IDE Integration**: Surface skills in VS Code/IDEs

---

## System Maturity Timeline

```
Week 1-2:  Phase 1 (Foundation)
           → Manual skill creation working

Week 3-4:  Phase 2 (Intelligence)
           → Semantic matching, complex execution

Week 5-6:  Phase 3 (Watcher)
           → Automatic pattern detection

Week 7-8:  Phase 4 (Self-Learning)
           → Skill evolution, optimization

Week 9+:   Production Refinement
           → Bug fixes, performance tuning
           → User feedback integration
           → Documentation polish
```

---

**Document Version:** 1.0
**Last Updated:** 2025-12-26
**Status:** Planning - Ready After Phase 3
**Estimated Duration:** 2 weeks (Days 1-14)
**Total Project Duration:** 8 weeks (all phases)
