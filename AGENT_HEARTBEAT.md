# HEARTBEAT.md — Crypto Agent Autonomous Health Checks

## Hang Detection Protocol (Mar 24 2026 — MANDATORY)

**Prime Directive #7: INVESTIGATE BEFORE KILLING**

### ⛔ NEVER Kill Based on Duration Alone
ML training, backtests, and data pipelines can run 4+ hours. **Slow is normal.**

### ✅ Evidence Required Before Killing ANY Process

Run ALL checks before killing:

```bash
# 1. Check last log timestamp (recent = making progress)
tail -20 logs/run_cycle.log | grep -E "INFO|ERROR" | tail -1

# 2. Check for stage progression (backtest → feature generation → scoring)
journalctl --user -u moonshot-v2.service --since "30 minutes ago" | grep "INFO.*moonshot" | tail -10

# 3. Check for error patterns
journalctl --user -u moonshot-v2.service --since "30 minutes ago" | grep -i -E "error|exception|traceback|OOM"

# 4. Check resource state
ps aux | grep "python.*run_cycle" | awk '{print "CPU:", $3"%", "RAM:", $6/1024"MB"}'

# 5. Check DB activity (recent writes = working)
sqlite3 data/moonshot_v2.db "SELECT MAX(entry_ts) FROM positions" | xargs -I {} date -d @{} '+%Y-%m-%d %H:%M:%S'
```

### Kill ONLY If ALL True:
- ✅ Same stage for >30min (check logs for stage transitions)
- ✅ No log updates in last 30min (tail shows old timestamps)
- ✅ No errors in logs (not stuck on retry loop)
- ✅ No DB writes in last 30min (check `positions`, `candles`, `features` tables)
- ✅ Process exists but not making syscalls (strace shows nothing)

### Examples of VALID Long Runs (Do NOT Kill):
- **Backtest stage:** 20 models × 1-3min = 20-60min (NORMAL)
- **Extended data fetch:** 470 symbols × 2.5 req/sec = 10-15min (NORMAL)
- **Feature generation:** 470 symbols × compute = 10-20min (NORMAL)
- **FT scoring:** 713 models × 935 positions = 15-30min (NORMAL)
- **Total cycle time:** 60-120min is EXPECTED, not broken

### If Truly Hung:
1. Capture diagnostics BEFORE killing:
   ```bash
   journalctl --user -u moonshot-v2.service --since "2 hours ago" > /tmp/moonshot_hung_$(date +%s).log
   ps aux | grep moonshot >> /tmp/moonshot_hung_$(date +%s).log
   ```
2. Kill gracefully: `systemctl --user stop moonshot-v2.service`
3. Investigate root cause (OOM? infinite loop? API timeout?)
4. Fix code if needed, commit
5. Restart: `systemctl --user start moonshot-v2.service`
6. Document in daily memory

## Heartbeat Tasks (Every 4h)

### Phase 1: Service Health
- Check all services active: `systemctl --user is-active moonshot-v2.timer blofin-stack-paper.service`
- Check dashboards responding: `curl -s http://127.0.0.1:8892 http://127.0.0.1:8893`
- Check last cycle completion time (should be <4h ago)

### Phase 2: Data Freshness
- Check latest candle timestamp (should be <5min old)
- Check champion FT trades (should be growing if market active)
- Check open positions count (sudden 0 = problem)

### Phase 3: Error Detection
- Check for cycle failures in last 4h: `journalctl --user -u moonshot-v2.service --since "4 hours ago" | grep -c ERROR`
- If >5 errors: investigate, attempt auto-fix, restart if needed
- Check for specific known bugs (feature mismatch, DB lock, OOM)

### Phase 4: Git Hygiene
- Check for uncommitted changes in AGENT_BOOTSTRAP.md / AGENT_MEMORY.md
- Commit and push if dirty
- Check if repo is behind origin (should auto-pull? no, never auto-pull on active systems)

### Phase 5: Performance Monitoring
- Check champion PnL trend (last 24h vs last 7d)
- Check FT model count (should be growing or stable, not dropping)
- Check for prolonged drawdowns (>50% on champion = pause needed?)

## Auto-Healing Actions

### Service Down
- Restart: `systemctl --user restart <service>.service`
- Check logs for root cause
- If persistent: escalate to Jarvis

### Cycle Errors (>5 in 4h)
- Check if already fixed in git (git log --since="4 hours ago")
- If NOT fixed: investigate error pattern, spawn subagent to fix code
- Commit + push fix
- Restart service

### Dashboard Down
- Check for port conflicts: `lsof -i :8892 -i :8893`
- Kill zombie processes if needed
- Restart dashboard service

### Data Stale (>30min old candles)
- Check WebSocket ingestor service
- Check Blofin API status (might be down)
- Restart ingestor if needed

## Escalation Criteria

Escalate to Jarvis (sessions_send) if:
- System-wide resource exhaustion (disk >90%, RAM thrashing)
- Multiple services failing simultaneously
- Auto-fix attempts failed 3+ times
- Unknown error patterns (not in MEMORY.md)
- Strategic decisions needed (deprecate a feature? change architecture?)
