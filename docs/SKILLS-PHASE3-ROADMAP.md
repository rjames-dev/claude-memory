# Skills System - Phase 3 Implementation Roadmap

**Phase:** Watcher (Weeks 5-6)
**Goal:** Automatic pattern detection and skill suggestion
**Status:** Planning
**Prerequisites:** Phase 1 & 2 complete
**Target Duration:** 2 weeks

---

## Phase 3 Overview

### What We're Building

The **Watcher** - an intelligent system that learns from your conversations and suggests new skills:

1. **Pattern Detection** - Automatically identify repetitive workflows
2. **User Correction Learning** - Capture "the right way" from user feedback
3. **Iteration Loop Detection** - Spot inefficiencies where a skill would help
4. **Skill Suggestions** - Present candidates for user approval
5. **End-of-Session Analysis** - Automatic suggestions when saving snapshots
6. **Pattern Scoring** - Confidence calculation for skill candidates

### What This Enables

**Before Phase 3:**
```
User manually creates skills based on memory of repetitive tasks
```

**After Phase 3:**
```
[End of session]

Claude: 📊 Session Analysis Complete

        I noticed you corrected my git commit approach 2 times:
        - You specified: "Always use heredoc for commit messages"
        - You specified: "Include co-author footer"

        Would you like me to create a 'git-commit-protocol' skill?
        Confidence: ⭐⭐⭐ (High - 2 corrections, consistent pattern)

        [Create Skill] [Not Yet] [Show Details]
```

### What We're NOT Building Yet

- ❌ Automatic skill evolution (Phase 4)
- ❌ Cross-session learning (Phase 4)
- ❌ A/B testing of skill variants (Phase 4)
- ❌ Proactive skill recommendations during work (Phase 4)

---

## Architecture Overview

### Pattern Detection Pipeline

```
┌─────────────────────────────────────┐
│  Conversation (auto-capture hook)  │
└───────────────┬─────────────────────┘
                │
                ▼
        ┌───────────────────┐
        │  Snapshot Capture │  (existing)
        └────────┬──────────┘
                 │
                 ▼
    ┌────────────────────────────┐
    │  NEW: Watcher Analysis     │
    │  - detect_tool_sequences() │
    │  - detect_corrections()    │
    │  - detect_iterations()     │
    └────────┬───────────────────┘
             │
             ▼
    ┌────────────────────────┐
    │  Pattern Candidates    │  (skills_patterns table)
    │  - Scored & ranked     │
    │  - Awaiting review     │
    └────────┬───────────────┘
             │
             ▼
    ┌────────────────────────┐
    │  User Reviews          │  (/mem-skills-suggest)
    │  [Create] [Ignore]     │
    └────────┬───────────────┘
             │
             ▼
    ┌────────────────────────┐
    │  Skill Created         │  (skills_agents table)
    │  Ready to use          │
    └────────────────────────┘
```

---

## Milestones

### Milestone 1: Tool Sequence Detection (Days 1-3)

**Goal:** Detect repetitive sequences of tool calls

**Algorithm:**

1. Extract all tool calls from conversation
2. Find N-grams (sequences of 2-6 tool calls)
3. Count occurrences of each sequence
4. Filter for patterns that appear ≥2 times
5. Score based on consistency and frequency

**Tasks:**
- [ ] Create `detect-patterns.py` script
- [ ] Implement tool call extraction
- [ ] Implement N-gram detection
- [ ] Implement pattern scoring
- [ ] Store patterns in `skills_patterns` table
- [ ] Test with real conversations
- [ ] Document detection algorithm

**Implementation:**

#### detect-patterns.py - Tool Sequence Detection

```python
#!/usr/bin/env python3
"""
Detect patterns in conversations for skill creation

Part of the Watcher system - runs during snapshot capture
"""

import psycopg2
import json
from collections import Counter
import hashlib

def extract_tool_calls(messages):
    """
    Extract all tool calls from conversation messages

    Returns: List of (tool_name, command_pattern) tuples
    """
    tool_calls = []

    for msg in messages:
        if msg.get('role') != 'assistant':
            continue

        # Look for tool use in message
        content = msg.get('content', '')

        # Parse tool use (this depends on message format)
        # Example for Claude Code format with tool blocks
        if isinstance(content, list):
            for block in content:
                if block.get('type') == 'tool_use':
                    tool_name = block.get('name')
                    tool_input = block.get('input', {})

                    # Extract command pattern
                    if tool_name == 'Bash':
                        cmd = tool_input.get('command', '')
                        # Generalize command (remove specific values)
                        pattern = generalize_command(cmd)
                        tool_calls.append((tool_name, pattern))

                    elif tool_name in ['Read', 'Write', 'Edit']:
                        # File operations
                        tool_calls.append((tool_name, 'file_operation'))

                    elif tool_name in ['Grep', 'Glob']:
                        # Search operations
                        tool_calls.append((tool_name, 'search'))

                    else:
                        tool_calls.append((tool_name, 'other'))

    return tool_calls

def generalize_command(cmd):
    """
    Generalize bash commands to find patterns

    Examples:
    - "git commit -m 'Fix bug'"  → "git commit"
    - "cd /path/to/dir"          → "cd"
    - "npm run build"            → "npm run"
    """
    # Split on whitespace
    parts = cmd.split()

    if not parts:
        return cmd

    # Git commands
    if parts[0] == 'git' and len(parts) > 1:
        return f"git {parts[1]}"  # git status, git commit, etc.

    # npm/yarn commands
    if parts[0] in ['npm', 'yarn'] and len(parts) > 1:
        return f"{parts[0]} {parts[1]}"

    # Simple commands
    if parts[0] in ['cd', 'ls', 'pwd', 'cat', 'echo']:
        return parts[0]

    # Docker compose
    if len(parts) >= 2 and parts[0] == 'docker' and parts[1] == 'compose':
        if len(parts) > 2:
            return f"docker compose {parts[2]}"
        return "docker compose"

    # psql
    if parts[0] == 'psql':
        return "psql"

    # Default: first word
    return parts[0]

def find_ngrams(tool_calls, min_length=2, max_length=6):
    """
    Find N-grams (sequences) in tool calls

    Returns: List of sequences with occurrence counts
    """
    sequences = []

    for n in range(min_length, max_length + 1):
        for i in range(len(tool_calls) - n + 1):
            sequence = tuple(tool_calls[i:i+n])
            sequences.append(sequence)

    # Count occurrences
    sequence_counts = Counter(sequences)

    # Filter for repeated patterns (≥2 occurrences)
    repeated = [
        {'sequence': list(seq), 'count': count}
        for seq, count in sequence_counts.items()
        if count >= 2
    ]

    return sorted(repeated, key=lambda x: (x['count'], len(x['sequence'])), reverse=True)

def detect_tool_sequences(snapshot_id, messages, project_path):
    """
    Main function: Detect tool sequence patterns

    Returns: List of pattern candidates
    """
    tool_calls = extract_tool_calls(messages)

    if len(tool_calls) < 4:  # Need minimum tool calls to find patterns
        return []

    # Find N-grams
    sequences = find_ngrams(tool_calls, min_length=2, max_length=6)

    patterns = []

    for seq_data in sequences[:10]:  # Top 10 sequences
        sequence = seq_data['sequence']
        count = seq_data['count']

        # Generate pattern signature (for deduplication)
        signature = hashlib.sha256(
            json.dumps(sequence, sort_keys=True).encode()
        ).hexdigest()

        # Score confidence
        confidence = calculate_tool_sequence_confidence(sequence, count)

        if confidence < 0.5:  # Skip low-confidence patterns
            continue

        # Generate suggested skill name
        suggested_name = generate_skill_name_from_sequence(sequence)

        patterns.append({
            'pattern_name': suggested_name,
            'pattern_type': 'tool_sequence',
            'signature_hash': signature,
            'detection_rules': {
                'sequence': sequence,
                'min_occurrences': 2
            },
            'occurrences': count,
            'confidence_score': confidence,
            'snapshot_id': snapshot_id,
            'project_path': project_path
        })

    return patterns

def calculate_tool_sequence_confidence(sequence, count):
    """
    Calculate confidence score for tool sequence pattern

    Factors:
    - Occurrence count (more = higher)
    - Sequence length (longer = more specific = higher)
    - Tool variety (mix of tools = more interesting)
    """
    base_score = min(count / 5, 1.0)  # Cap at 5 occurrences

    # Length bonus
    length_bonus = min(len(sequence) / 6, 0.2)  # Up to +20% for 6+ tools

    # Variety bonus (different tools = better)
    unique_tools = len(set([t[0] for t in sequence]))
    variety_bonus = min(unique_tools / len(sequence) * 0.2, 0.2)  # Up to +20%

    final_score = min(base_score + length_bonus + variety_bonus, 1.0)

    return final_score

def generate_skill_name_from_sequence(sequence):
    """
    Generate suggested skill name from tool sequence

    Examples:
    - [("Bash", "git status"), ("Bash", "git diff")] → "git-status-diff"
    - [("Bash", "docker compose up"), ("Bash", "docker compose ps")] → "docker-compose-up-ps"
    """
    # Extract unique command patterns
    commands = [cmd for tool, cmd in sequence if cmd != 'other']

    # Take first 3 unique commands
    unique_cmds = []
    for cmd in commands:
        if cmd not in unique_cmds:
            unique_cmds.append(cmd)
        if len(unique_cmds) >= 3:
            break

    # Convert to kebab-case
    name_parts = []
    for cmd in unique_cmds:
        parts = cmd.replace(' ', '-').split('-')
        name_parts.extend(parts[:2])  # Max 2 words per command

    suggested = '-'.join(name_parts[:5])  # Max 5 total parts

    return suggested or 'tool-sequence-pattern'
```

**Validation:**
- [ ] Tool calls extracted correctly
- [ ] N-gram detection works
- [ ] Patterns scored reasonably
- [ ] Signatures prevent duplicates
- [ ] Suggested names are meaningful

**Deliverables:**
- ✅ `detect-patterns.py` (tool sequence detection)
- ✅ Pattern storage in database
- ✅ Tests with sample conversations

---

### Milestone 2: User Correction Detection (Days 4-5)

**Goal:** Detect when user corrects Claude's approach

**Signals:**
- User messages with correction language ("No, use...", "Actually...", "Instead...")
- User provides alternative command after failed attempt
- System reminders triggered multiple times

**Tasks:**
- [ ] Implement correction language detection
- [ ] Implement alternative approach detection
- [ ] Implement system reminder tracking
- [ ] Store correction patterns
- [ ] Test with real correction scenarios
- [ ] Document correction detection

**Implementation:**

#### detect-patterns.py - User Correction Detection

```python
def detect_user_corrections(snapshot_id, messages, project_path):
    """
    Detect user corrections - strong signal for skill creation
    """
    corrections = []

    for i, msg in enumerate(messages):
        if msg.get('role') != 'user':
            continue

        content = msg.get('content', '')

        # Check for correction language
        correction_phrases = [
            'no, use',
            'actually,',
            'instead',
            'should be',
            'needs to be',
            'always use',
            'never use',
            'the correct way',
            'use heredoc',
            'make sure to',
            'don\'t forget'
        ]

        is_correction = any(phrase in content.lower() for phrase in correction_phrases)

        if not is_correction:
            continue

        # Get context: what was Claude trying before?
        previous_attempts = get_previous_assistant_actions(messages[:i])

        if not previous_attempts:
            continue

        # Extract the "right way" from user message
        corrected_approach = extract_corrected_approach(content)

        # Generate pattern
        signature = hashlib.sha256(
            (corrected_approach + str(previous_attempts)).encode()
        ).hexdigest()

        confidence = 0.95  # User corrections are high-confidence

        corrections.append({
            'pattern_name': generate_correction_skill_name(corrected_approach),
            'pattern_type': 'user_correction',
            'signature_hash': signature,
            'detection_rules': {
                'user_correction': content,
                'previous_attempts': previous_attempts,
                'corrected_approach': corrected_approach
            },
            'occurrences': 1,  # Corrections are powerful even once
            'confidence_score': confidence,
            'snapshot_id': snapshot_id,
            'project_path': project_path
        })

    return corrections

def get_previous_assistant_actions(messages_before):
    """Get what Claude was trying to do before user correction"""
    actions = []

    # Look backwards through recent messages
    for msg in reversed(messages_before[-5:]):  # Last 5 messages
        if msg.get('role') == 'assistant':
            # Extract tool uses
            content = msg.get('content', [])
            if isinstance(content, list):
                for block in content:
                    if block.get('type') == 'tool_use':
                        actions.append({
                            'tool': block.get('name'),
                            'input': block.get('input')
                        })

    return actions

def extract_corrected_approach(user_message):
    """
    Extract the corrected approach from user message

    Examples:
    - "No, use heredoc format for commit messages" → "use heredoc format for commit messages"
    - "Always check .env.example first" → "check .env.example first"
    """
    # Simple extraction - take sentence after correction phrase
    lower = user_message.lower()

    for phrase in ['no, use', 'always use', 'make sure to', 'instead', 'should be']:
        if phrase in lower:
            idx = lower.index(phrase) + len(phrase)
            remainder = user_message[idx:].strip()

            # Take first sentence
            sentence_end = remainder.find('.')
            if sentence_end > 0:
                return remainder[:sentence_end].strip()
            return remainder[:100].strip()  # Max 100 chars

    # Fallback: return truncated message
    return user_message[:100]

def generate_correction_skill_name(correction_text):
    """Generate skill name from correction"""
    # Extract key verbs/nouns
    words = correction_text.lower().split()

    # Filter stop words
    stop_words = {'the', 'a', 'an', 'to', 'for', 'in', 'on', 'with', 'use', 'using'}
    key_words = [w for w in words if w not in stop_words and len(w) > 2]

    # Take first 3-4 words
    name = '-'.join(key_words[:4])

    return name or 'corrected-approach'
```

**Validation:**
- [ ] Correction language detected
- [ ] Context captured correctly
- [ ] High confidence assigned
- [ ] Skill names meaningful

**Deliverables:**
- ✅ User correction detection
- ✅ Integration with pattern storage
- ✅ Tests with correction examples

---

### Milestone 3: Iteration Loop Detection (Days 6-7)

**Goal:** Detect when Claude tries multiple approaches (inefficiency signal)

**Signals:**
- Multiple tool calls with similar intent but different parameters
- Error → retry → error → retry pattern
- Comments like "Let me try a different approach"

**Implementation:**

```python
def detect_iteration_loops(snapshot_id, messages, project_path):
    """
    Detect iteration loops - opportunities for skills
    """
    loops = []

    # Group tool calls by intent
    tool_groups = group_by_intent(messages)

    for intent, calls in tool_groups.items():
        if len(calls) < 3:  # Need at least 3 attempts
            continue

        # Check if this looks like iteration
        has_failures = any(call.get('failed') for call in calls)
        has_variations = has_parameter_variations(calls)

        if has_failures or has_variations:
            # This is an iteration loop
            final_success = calls[-1].get('success', False)

            if final_success:
                # We found the right way eventually
                confidence = 0.75 + (len(calls) * 0.05)  # More attempts = higher confidence

                loops.append({
                    'pattern_name': f"{intent}-workflow",
                    'pattern_type': 'iteration_loop',
                    'signature_hash': hashlib.sha256(intent.encode()).hexdigest(),
                    'detection_rules': {
                        'intent': intent,
                        'attempts': len(calls),
                        'final_approach': calls[-1]
                    },
                    'occurrences': 1,
                    'confidence_score': min(confidence, 0.95),
                    'snapshot_id': snapshot_id,
                    'project_path': project_path
                })

    return loops

def group_by_intent(messages):
    """
    Group tool calls by intent

    Example intents:
    - "search_codebase"
    - "check_database"
    - "run_tests"
    """
    groups = {}

    # Simplified - in reality would use NLP or heuristics
    # to determine intent from tool calls and context

    return groups

def has_parameter_variations(calls):
    """Check if calls vary in parameters (trying different approaches)"""
    if len(calls) < 2:
        return False

    # Check if inputs vary
    first_input = calls[0].get('input')
    for call in calls[1:]:
        if call.get('input') != first_input:
            return True

    return False
```

**Validation:**
- [ ] Iteration loops detected
- [ ] Final successful approach captured
- [ ] Confidence scoring reasonable

**Deliverables:**
- ✅ Iteration loop detection
- ✅ Integration complete

---

### Milestone 4: Pattern Scoring & Ranking (Days 8-9)

**Goal:** Score and rank pattern candidates for presentation

**Tasks:**
- [ ] Implement confidence calculation
- [ ] Implement priority scoring
- [ ] Create `/mem-skills-suggest` command
- [ ] Format pattern presentation
- [ ] Test with real pattern candidates
- [ ] Document scoring algorithm

**Implementation:**

#### /mem-skills-suggest Command

```python
#!/usr/bin/env python3
"""
Show skill candidates detected from patterns

Usage:
  python3 suggest-skills.py
  python3 suggest-skills.py --limit 5
  python3 suggest-skills.py --min-confidence 0.7
"""

import psycopg2
import argparse

def suggest_skills(limit=5, min_confidence=0.65):
    """
    Show top skill candidates
    """
    conn = psycopg2.connect(...)
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            pattern_name,
            pattern_type,
            occurrences,
            confidence_score,
            priority_score,
            detection_rules,
            seen_in_projects,
            first_seen_snapshot_id,
            last_seen_snapshot_id
        FROM v_skill_candidates
        WHERE confidence_score >= %s
        ORDER BY priority_score DESC
        LIMIT %s
    """, (min_confidence, limit))

    candidates = cur.fetchall()

    if not candidates:
        print("No skill candidates found")
        return

    print(f"\n📊 Analyzed recent sessions, found {len(candidates)} skill candidates:\n")

    for idx, candidate in enumerate(candidates, 1):
        (cand_id, name, ptype, occurrences, confidence, priority,
         rules, projects, first_snap, last_snap) = candidate

        # Confidence stars
        if confidence >= 0.9:
            stars = "⭐⭐⭐"
            conf_label = "High"
        elif confidence >= 0.75:
            stars = "⭐⭐"
            conf_label = "Medium"
        else:
            stars = "⭐"
            conf_label = "Low"

        print("━" * 60)
        print(f"{idx}. {stars} {name} ({conf_label} confidence)")
        print(f"\n   Pattern Type: {ptype}")
        print(f"   Seen: {occurrences} times across {len(projects)} project(s)")
        print(f"   Confidence: {confidence:.2f}")

        # Show pattern details
        if ptype == 'tool_sequence':
            sequence = rules.get('sequence', [])
            print(f"\n   You ran these {len(sequence)} commands {occurrences} times:")
            for tool, cmd in sequence[:5]:  # Show first 5
                print(f"   - {tool}: {cmd}")

        elif ptype == 'user_correction':
            correction = rules.get('user_correction', '')
            print(f"\n   User said: \"{correction[:100]}...\"")

        elif ptype == 'iteration_loop':
            intent = rules.get('intent', '')
            attempts = rules.get('attempts', 0)
            print(f"\n   Task: {intent}")
            print(f"   Tried {attempts} different approaches")

        print(f"\n   [Create Skill] [Ignore] [Show Details]")
        print()

    cur.close()
    conn.close()
```

**Validation:**
- [ ] Candidates sorted by priority
- [ ] Confidence levels clear
- [ ] Pattern details helpful
- [ ] UI is actionable

**Deliverables:**
- ✅ `/mem-skills-suggest` command
- ✅ Pattern ranking logic
- ✅ Documentation

---

### Milestone 5: Snapshot Integration (Days 10-11)

**Goal:** Run watcher analysis automatically during snapshot capture

**Tasks:**
- [ ] Update `save-snapshot.py` to call watcher
- [ ] Add watcher analysis to capture flow
- [ ] Store detected patterns
- [ ] Show end-of-session suggestions
- [ ] Test integrated workflow
- [ ] Document integration

**Implementation:**

#### Update save-snapshot.py

```python
# In processor/src/save-snapshot.py or similar

def save_snapshot(conversation):
    """Enhanced snapshot capture with pattern detection"""

    # Existing snapshot logic
    snapshot_id = save_messages(conversation)
    summary = generate_summary(conversation)
    embedding = create_embedding(summary)
    store_snapshot(snapshot_id, summary, embedding)

    # NEW: Watcher analysis
    project_path = os.getcwd()
    messages = conversation.get('messages', [])

    # Import detection functions
    from detect_patterns import (
        detect_tool_sequences,
        detect_user_corrections,
        detect_iteration_loops
    )

    # Run detections
    tool_patterns = detect_tool_sequences(snapshot_id, messages, project_path)
    correction_patterns = detect_user_corrections(snapshot_id, messages, project_path)
    iteration_patterns = detect_iteration_loops(snapshot_id, messages, project_path)

    all_patterns = tool_patterns + correction_patterns + iteration_patterns

    # Store patterns
    if all_patterns:
        store_patterns(all_patterns)
        print(f"\n📊 Pattern Analysis:")
        print(f"   Tool sequences: {len(tool_patterns)}")
        print(f"   User corrections: {len(correction_patterns)}")
        print(f"   Iteration loops: {len(iteration_patterns)}")
        print(f"\n   Run '/mem-skills-suggest' to review skill candidates")

    return snapshot_id

def store_patterns(patterns):
    """Store detected patterns in database"""
    conn = psycopg2.connect(...)
    cur = conn.cursor()

    for pattern in patterns:
        try:
            # Check if pattern already exists (by signature)
            cur.execute("""
                SELECT id, occurrences
                FROM skills_patterns
                WHERE signature_hash = %s AND status = 'candidate'
            """, (pattern['signature_hash'],))

            existing = cur.fetchone()

            if existing:
                # Update occurrence count
                pattern_id, current_count = existing
                cur.execute("""
                    UPDATE skills_patterns
                    SET occurrences = %s,
                        last_seen_snapshot_id = %s
                    WHERE id = %s
                """, (current_count + 1, pattern['snapshot_id'], pattern_id))

            else:
                # Insert new pattern
                cur.execute("""
                    INSERT INTO skills_patterns
                    (pattern_name, pattern_type, signature_hash,
                     detection_rules, occurrences, confidence_score,
                     first_seen_snapshot_id, last_seen_snapshot_id,
                     seen_in_projects)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    pattern['pattern_name'],
                    pattern['pattern_type'],
                    pattern['signature_hash'],
                    json.dumps(pattern['detection_rules']),
                    pattern['occurrences'],
                    pattern['confidence_score'],
                    pattern['snapshot_id'],
                    pattern['snapshot_id'],
                    [pattern['project_path']]
                ))

            conn.commit()

        except Exception as e:
            print(f"Error storing pattern: {e}")
            conn.rollback()

    cur.close()
    conn.close()
```

**Validation:**
- [ ] Patterns detected automatically
- [ ] Patterns stored correctly
- [ ] User sees suggestions
- [ ] Performance acceptable

**Deliverables:**
- ✅ Snapshot integration complete
- ✅ Automatic pattern detection working
- ✅ End-of-session notifications

---

### Milestone 6: Pattern Action Flow (Days 12-14)

**Goal:** Complete workflow from pattern → skill creation

**Tasks:**
- [ ] Implement pattern → skill conversion
- [ ] Create skill creation from pattern
- [ ] Handle pattern approval/rejection
- [ ] Update pattern status after action
- [ ] Create example workflow documentation
- [ ] Test complete end-to-end flow

**Implementation:**

#### create-skill-from-pattern.py

```python
#!/usr/bin/env python3
"""
Create a skill from a detected pattern

Usage:
  python3 create-skill-from-pattern.py --pattern-id 5
"""

import argparse
import psycopg2
import json

def create_skill_from_pattern(pattern_id):
    """
    Convert a pattern candidate into a skill
    """
    conn = psycopg2.connect(...)
    cur = conn.cursor()

    # Get pattern
    cur.execute("""
        SELECT
            pattern_name,
            pattern_type,
            detection_rules,
            confidence_score,
            seen_in_projects
        FROM skills_patterns
        WHERE id = %s
    """, (pattern_id,))

    pattern = cur.fetchone()
    if not pattern:
        print(f"Pattern {pattern_id} not found")
        return

    (name, ptype, rules, confidence, projects) = pattern

    # Convert to skill based on pattern type
    if ptype == 'tool_sequence':
        skill_data = create_skill_from_sequence(name, rules, confidence, projects)

    elif ptype == 'user_correction':
        skill_data = create_skill_from_correction(name, rules, confidence, projects)

    elif ptype == 'iteration_loop':
        skill_data = create_skill_from_iteration(name, rules, confidence, projects)

    else:
        print(f"Unknown pattern type: {ptype}")
        return

    # Insert skill (reuse logic from create-skill.py)
    from create_skill import create_skill_in_db

    skill_id = create_skill_in_db(skill_data)

    # Update pattern status
    cur.execute("""
        UPDATE skills_patterns
        SET status = 'created',
            suggested_agent_id = %s,
            reviewed_by = 'user',
            reviewed_at = NOW()
        WHERE id = %s
    """, (skill_id, pattern_id))

    conn.commit()

    print(f"✅ Skill created: {skill_data['agent_name']} (ID: {skill_id})")
    print(f"   Pattern {pattern_id} marked as 'created'")

    cur.close()
    conn.close()

    return skill_id

def create_skill_from_sequence(name, rules, confidence, projects):
    """Create tool sequence skill from pattern"""
    sequence = rules.get('sequence', [])

    # Determine category from tools
    has_git = any('git' in cmd for tool, cmd in sequence)
    category = 'git' if has_git else 'workflow'

    # Determine scope
    scope = 'global' if len(projects) > 1 else 'project'
    project_path = projects[0] if scope == 'project' else None

    # Build tool sequence command
    steps = []
    for i, (tool, cmd) in enumerate(sequence, 1):
        steps.append({
            'step': i,
            'description': f"{tool}: {cmd}",
            'tools': [{
                'tool': tool,
                'command': cmd
            }],
            'parallel': False
        })

    return {
        'agent_name': name,
        'display_name': name.replace('-', ' ').title(),
        'category': category,
        'scope': scope,
        'project_path': project_path,
        'confidence_score': confidence,
        'command_type': 'tool_sequence',
        'command_definition': {'steps': steps},
        'triggers': [f"run {name}", f"execute {name}"]
    }

# Similar functions for correction and iteration patterns...
```

**Validation:**
- [ ] Pattern → skill conversion works
- [ ] All pattern types supported
- [ ] Skills created successfully
- [ ] Pattern status updated
- [ ] Complete workflow functional

**Deliverables:**
- ✅ Pattern → skill conversion
- ✅ Complete action flow
- ✅ Example workflows documented
- ✅ End-to-end tests passing

---

## Success Criteria

Phase 3 is complete when:

- [ ] All 6 milestones delivered
- [ ] Patterns detected automatically
- [ ] Tool sequences, corrections, iterations all detected
- [ ] Suggestions shown at end of session
- [ ] Users can create skills from patterns
- [ ] Pattern → skill workflow complete
- [ ] At least 3 skills created from detected patterns
- [ ] Documentation complete

---

## File Structure After Phase 3

```
claude-memory/
├── detect-patterns.py (NEW)
├── suggest-skills.py (NEW)
├── create-skill-from-pattern.py (NEW)
├── processor/
│   └── src/
│       └── save-snapshot.py (UPDATED - watcher integration)
├── .claude/
│   └── commands/
│       └── mem-skills-suggest.md (NEW)
└── docs/
    ├── SKILLS-SYSTEM-ARCHITECTURE.md
    ├── SKILLS-PHASE1-ROADMAP.md
    ├── SKILLS-PHASE2-ROADMAP.md
    └── SKILLS-PHASE3-ROADMAP.md (THIS FILE)
```

---

## Integration Points

### With Phase 1 & 2

Phase 3 uses:
- `create-skill.py` (Phase 1) - For creating skills from patterns
- `skills_agents`, `skills_patterns` tables (Phase 1) - For storage
- Semantic matching (Phase 2) - For trigger generation

### With Existing claude-memory

Integrates with:
- Snapshot capture hooks
- `context_snapshots` table
- Auto-capture pipeline

---

## Next Steps (Phase 4)

After Phase 3, we'll add:

1. **Skill Evolution** - Update skills based on feedback
2. **Cross-Session Learning** - Learn across multiple sessions
3. **Confidence Auto-Adjustment** - Dynamic confidence scores
4. **A/B Testing** - Compare skill variants
5. **Proactive Recommendations** - Suggest skills during work

See `SKILLS-PHASE4-ROADMAP.md` (to be created)

---

## Example Workflow

**User Experience:**

```bash
# User has been working, commits changes manually 3 times

[Session end - /mem-save]

Claude: 📊 Session Analysis Complete
        Captured 156 messages to snapshot #47

        Pattern Detection Results:
        - Tool sequences: 1
        - User corrections: 0
        - Iteration loops: 0

        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        1. ⭐⭐⭐ git-status-diff-commit (High confidence)

           Pattern Type: tool_sequence
           Seen: 3 times in this session
           Confidence: 0.92

           You ran these commands 3 times:
           - Bash: git status
           - Bash: git diff
           - Bash: git commit

           Would you like to create a skill for this workflow?

           [Create Skill] [Not Yet] [Show Details]

User: Create Skill

Claude: ✅ Skill created: git-status-diff-commit (ID: 12)

        Next time you need to commit changes, I'll suggest using this skill!

        Try it: Just say "commit these changes"
```

---

**Document Version:** 1.0
**Last Updated:** 2025-12-26
**Status:** Planning - Ready After Phase 2
**Estimated Duration:** 2 weeks (Days 1-14)
