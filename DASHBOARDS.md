# Claude Memory Dashboards

**Version**: 2.0.0
**Date**: 2025-12-16

Real-time monitoring for claude-memory with both web and terminal interfaces.

---

## Overview

Claude Memory now includes two monitoring interfaces:

1. **Web Dashboard** - Beautiful web UI at `http://localhost:3200/dashboard`
2. **Terminal Monitor** - Real-time terminal UI with live updates

Both dashboards show the same information:
- System status (Database, Ollama, Processor)
- Capture statistics (total, today, this week)
- Session tracking
- Recent captures with live updates

---

## Web Dashboard

### Access

**Open in browser:**
```bash
open http://localhost:3200/dashboard
```

**Or use npm script:**
```bash
cd ~/Data/00\ GITHUB/Code/claude-memory
npm run dashboard
```

### Features

- **Auto-refresh**: Updates every 10 seconds
- **Real-time stats**: See captures as they happen
- **Clean UI**: Dark theme, minimal design
- **Status indicators**: Green dots for healthy services
- **Recent captures**: Last 10 captures with timestamps
- **Badge system**: NEW vs UPDATE indicators

### What You See

```
┌─────────────────────────────────────────────────┐
│  Claude Memory Dashboard                        │
│                                                 │
│  System Status:                                 │
│  ● Database    Connected                        │
│  ● Ollama      llama3.2:latest                  │
│  ● Processor   port 3200 (uptime: 2h 15m)      │
│                                                 │
│  Capture Statistics:                            │
│  Total Snapshots:   24                          │
│  Today:             3                           │
│  This Week:         12                          │
│  Last Capture:      2 minutes ago               │
│                                                 │
│  Session Tracking:                              │
│  Sessions Tracked:  18                          │
│                                                 │
│  Recent Captures:                               │
│  20:29:21  NLQ-Tools    187 msgs  [UPDATE]     │
│  20:27:34  NLQ-Tools    187 msgs  [NEW]        │
│  19:47:24  claude-mem   2 msgs    [NEW]        │
└─────────────────────────────────────────────────┘
```

### API Endpoints

The dashboard uses these API endpoints:

**Stats:**
```bash
curl http://localhost:3200/api/stats
```

**Recent captures:**
```bash
curl http://localhost:3200/api/recent?limit=10
```

**Health check:**
```bash
curl http://localhost:3200/health
```

---

## Terminal Monitor

### Access

**Run from command line:**
```bash
cd ~/Data/00\ GITHUB/Code/claude-memory
node monitor.js
```

**Or use npm script:**
```bash
npm run monitor
```

### Features

- **Live updates**: Refreshes every 5 seconds
- **ANSI colors**: Beautiful terminal formatting
- **Compact layout**: Fits in standard terminal
- **Keyboard control**: Ctrl+C to quit
- **Responsive**: Adapts to terminal width

### What You See

```
╔══════════════════════════════════════════════════════╗
║  CLAUDE MEMORY MONITOR                               ║
╠══════════════════════════════════════════════════════╣
║                                                      ║
║  SYSTEM STATUS                                       ║
║  ● Database    connected                             ║
║  ● Ollama      llama3.2:latest                       ║
║  ● Processor   port 3200 (uptime: 2h 15m)           ║
║                                                      ║
║  CAPTURE STATISTICS                                  ║
║  Total Snapshots:       24                           ║
║  Today:                  3                           ║
║  This Week:             12                           ║
║  Last Capture:     2m ago                            ║
║                                                      ║
║  SESSION TRACKING                                    ║
║  Sessions Tracked:      18                           ║
║                                                      ║
║  RECENT CAPTURES (8)                                 ║
║  20:29:21  NLQ-Tools          187 msgs  UPDATE      ║
║  20:27:34  NLQ-Tools          187 msgs  NEW         ║
║  19:47:24  claude-mem         2 msgs    NEW         ║
║                                                      ║
╚══════════════════════════════════════════════════════╝

  Auto-refresh: 5s  |  Press Ctrl+C to quit
```

### Color Scheme

- **Green (●)**: Healthy status indicators
- **Cyan**: Borders and headers
- **Yellow**: UPDATE badges
- **Green**: NEW badges
- **Gray**: Timestamps and secondary info
- **Bright**: Important numbers

### Keyboard Commands

- **Ctrl+C**: Quit the monitor

---

## Use Cases

### Web Dashboard

**Best for:**
- Quick glance at system status
- Viewing while working in browser
- Sharing screen with team
- Keeping open in separate window
- Long-term monitoring

**How to use:**
```bash
# Open dashboard
open http://localhost:3200/dashboard

# Leave browser tab open
# Dashboard auto-refreshes every 10 seconds
```

### Terminal Monitor

**Best for:**
- Terminal-based workflows
- SSH sessions
- Dedicated monitoring terminal
- Advanced users who prefer CLI
- Integration with `/context` command workflow

**How to use:**
```bash
# Open dedicated terminal tab/pane
npm run monitor

# Leave running while you work
# Updates every 5 seconds automatically
```

---

## Setup

### Installation

Dashboards are included by default. No additional installation needed.

### Requirements

- Docker containers running (`docker compose up -d`)
- Processor accessible at port 3200
- Node.js (for terminal monitor)

### Verify Setup

```bash
# Check processor is running
curl http://localhost:3200/health

# Should return:
# {"status":"ok","service":"claude-context-processor","timestamp":"..."}

# Check dashboard is accessible
curl -I http://localhost:3200/dashboard

# Should return:
# HTTP/1.1 200 OK
```

---

## Advanced Usage

### Custom Refresh Intervals

**Terminal Monitor** (edit monitor.js):
```javascript
const REFRESH_INTERVAL = 5000; // Change to 3000 for 3 seconds
```

**Web Dashboard** (edit dashboard.html):
```javascript
refreshInterval = setInterval(updateDashboard, 10000); // Change to 5000 for 5 seconds
```

### API Integration

Build your own dashboard using the APIs:

```javascript
// Fetch stats
const stats = await fetch('http://localhost:3200/api/stats').then(r => r.json());

// Fetch recent captures
const recent = await fetch('http://localhost:3200/api/recent?limit=20').then(r => r.json());

// Process data
console.log(`Total snapshots: ${stats.captures.total}`);
console.log(`Sessions tracked: ${stats.sessions.tracked}`);
```

### Embedding in Other Tools

**Alfred Workflow:**
```bash
#!/bin/bash
curl -s http://localhost:3200/api/stats | jq -r '"Snapshots: \(.captures.total) | Today: \(.captures.today)"'
```

**tmux Status Bar:**
```bash
# .tmux.conf
set -g status-right "#(curl -s http://localhost:3200/api/stats 2>/dev/null | jq -r '.captures.total' || echo '?') snapshots"
```

**Menu Bar Widget** (future enhancement):
- See roadmap for macOS menu bar widget
- Will use same API endpoints

---

## Troubleshooting

### Web Dashboard Not Loading

**Symptom:** 404 or connection refused

**Diagnosis:**
```bash
# Check processor is running
docker ps --filter "name=claude-context-processor"

# Check logs
docker compose logs context-processor --tail=20
```

**Solution:**
```bash
# Restart processor
docker compose restart context-processor

# Or rebuild
docker compose up -d --build context-processor
```

### Terminal Monitor Shows Error

**Symptom:** "Cannot connect" or API errors

**Diagnosis:**
```bash
# Test API directly
curl http://localhost:3200/health
```

**Solution:**
```bash
# Check processor is running
docker compose ps

# Check port is correct
docker compose logs context-processor | grep "running on port"
```

### Stats Not Updating

**Symptom:** Dashboard shows stale data

**Web Dashboard:**
- Check browser console (F12) for errors
- Hard refresh (Cmd+Shift+R)

**Terminal Monitor:**
- Check terminal for error messages
- Restart monitor: Ctrl+C, then `npm run monitor`

### Database Connection Errors

**Symptom:** API returns 500 errors

**Diagnosis:**
```bash
# Check database is running
docker ps --filter "name=claude-context-db"

# Test connection
docker exec claude-context-db psql -U memory_admin -d claude_memory -c "SELECT COUNT(*) FROM context_snapshots;"
```

**Solution:**
```bash
# Restart database
docker compose restart context-db

# Wait for health check
docker compose logs context-db --tail=10
```

---

## Performance

### Resource Usage

**Web Dashboard:**
- Memory: ~5MB (browser tab)
- Network: ~1KB per refresh (every 10s)
- CPU: Negligible

**Terminal Monitor:**
- Memory: ~30MB (Node.js process)
- Network: ~1KB per refresh (every 5s)
- CPU: Negligible

### Database Impact

**API queries per dashboard:**
- 5 SQL queries per refresh
- All queries indexed
- Typical response time: <10ms

**Total overhead:**
- Web Dashboard (10s refresh): 0.5 queries/second
- Terminal Monitor (5s refresh): 1 query/second
- Combined: ~1.5 queries/second (negligible)

---

## Roadmap

### Planned Features

**Phase 1: Current** ✅
- [x] Web dashboard
- [x] Terminal monitor
- [x] Stats API
- [x] Recent captures API

**Phase 2: Enhanced (Next)**
- [ ] Real-time updates via WebSockets
- [ ] Charts/graphs (captures over time)
- [ ] Project breakdown (captures per project)
- [ ] Search functionality
- [ ] Export dashboard data

**Phase 3: Advanced**
- [ ] macOS menu bar widget
- [ ] Desktop notifications
- [ ] Alerts for failures
- [ ] Custom dashboard layouts
- [ ] Multi-instance monitoring

---

## Files

**Dashboard:**
- `processor/public/dashboard.html` - Web dashboard UI
- `processor/src/server.js` - API endpoints + dashboard route

**Monitor:**
- `monitor.js` - Terminal UI script
- `package.json` - npm scripts

**Documentation:**
- `DASHBOARDS.md` - This file
- `ENHANCED-CAPTURE-SYSTEM.md` - Technical details

---

## Examples

### Monitoring During Development

**Scenario:** You're building a feature and want to see captures happening

```bash
# Terminal 1: Your work
cd ~/Data/00\ GITHUB/Code/my-project
# ... coding ...

# Terminal 2: Monitor
cd ~/Data/00\ GITHUB/Code/claude-memory
npm run monitor

# See captures appear in real-time as you work!
```

### Checking System Health

**Quick health check:**
```bash
curl -s http://localhost:3200/api/stats | jq '{
  database: .database.status,
  snapshots: .captures.total,
  last_capture: .captures.lastCaptureSeconds
}'
```

**Output:**
```json
{
  "database": "connected",
  "snapshots": 24,
  "last_capture": 120
}
```

### Debugging Capture Issues

**Check if captures are working:**
```bash
# Before work session
BEFORE=$(curl -s http://localhost:3200/api/stats | jq '.captures.total')

# ... do some work that should trigger capture ...

# After work session
AFTER=$(curl -s http://localhost:3200/api/stats | jq '.captures.total')

echo "Captures increased by: $(($AFTER - $BEFORE))"
```

---

## Support

**Questions?**
- Check logs: `docker compose logs context-processor`
- Check database: `docker exec claude-context-db psql -U memory_admin -d claude_memory`
- Test APIs: `curl http://localhost:3200/api/stats`

**Issues?**
- Restart services: `docker compose restart`
- Rebuild processor: `docker compose up -d --build context-processor`
- Check documentation: `ENHANCED-CAPTURE-SYSTEM.md`

---

**Last Updated:** 2025-12-16
**Author:** James (with Claude Sonnet 4.5)
**Version:** 2.0.0
