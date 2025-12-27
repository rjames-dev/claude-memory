# /mem-skills-stats

Show detailed performance statistics for the Skills System

## Usage

```bash
# Show stats for a specific skill
/mem-skills-stats git-commit-protocol

# Show stats for all skills (grouped by category)
/mem-skills-stats --all

# Show all skills in a specific category
/mem-skills-stats --category git

# Show top 10 most used skills
/mem-skills-stats --top 10

# Show 30 days of history for a skill
/mem-skills-stats git-commit-protocol --days 30
```

## What This Shows

For individual skills:
- Total uses, success rate, failures
- Average and total time saved
- Recent performance (last N days with daily breakdown)
- User acceptance rate (how often suggestions were accepted)
- Usage by project
- Last 10 executions with status

For all skills summary:
- Total skills, uses, and time saved
- Skills grouped by category
- Uses, success rate, and time saved per skill
- Last used date

For top performers:
- Most used skills ranked
- Medal indicators (🥇🥈🥉) for top 3

## Output Example

```
======================================================================
Git Commit (Our Protocol) - Performance Statistics
======================================================================

📊 Overall:
  Total Uses: 23
  Success: 23 (100.0%)
  Failed: 0
  Avg Time Saved: 45.0s
  Total Time Saved: 17.3m

📈 Recent Performance (Last 7 days):
  2025-12-26: 3 uses, 100% success, 7.8s avg
  2025-12-25: 5 uses, 100% success, 8.1s avg
  2025-12-24: 2 uses, 100% success, 6.5s avg

👍 User Acceptance:
  Suggested: 25 times
  Accepted: 23 (92%)
  Rejected: 2

📁 Usage by Project:
  /Users/jamesmba/Data/00 GITHUB/Code/NLQ: 12 uses (8.2s avg)
  /Users/jamesmba/Data/00 GITHUB/Code/claude-memory: 6 uses (7.1s avg)

🕐 Last 10 Executions:
  2025-12-26 14:32  ✅ success           7.2s  [claude-memory]
  2025-12-26 12:15  ✅ success           8.1s  [claude-memory]
  2025-12-25 16:45  ✅ success           7.8s  [NLQ]

ℹ️  Metadata:
  Category: git
  Confidence: 0.95
  Created: 2025-12-15
  Last Used: 2025-12-26 14:32 (0 days ago)
```

## Arguments

python3 /Users/jamesmba/Data/00\ GITHUB/Code/claude-memory/skills-stats.py "$@"
