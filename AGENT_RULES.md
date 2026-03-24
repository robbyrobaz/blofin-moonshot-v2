# AGENTS.md — Crypto Trading Agent

## Every Session
1. Read `SOUL.md` — who you are
2. Read `BOOTSTRAP.md` — current state (symlinked from `blofin-moonshot-v2/AGENT_BOOTSTRAP.md`)
3. Read `MEMORY.md` — learnings (symlinked from `blofin-moonshot-v2/AGENT_MEMORY.md`)
4. Read daily memory: `memory/YYYY-MM-DD.md` (today + yesterday) — these are in YOUR workspace, not the shared Jarvis workspace

## ⚠️ Updating Your Own Files (NON-OPTIONAL)
Your BOOTSTRAP.md and MEMORY.md are **symlinked to files in the repo**. When you learn something new or state changes:
- Edit `blofin-moonshot-v2/AGENT_BOOTSTRAP.md` (current state, champion, FT backlog, services)
- Edit `blofin-moonshot-v2/AGENT_MEMORY.md` (lessons learned, bugs found, architecture decisions)
- Commit and push: `cd blofin-moonshot-v2 && git add AGENT_BOOTSTRAP.md AGENT_MEMORY.md && git commit -m "agent: update bootstrap/memory" && git push`
- **Do this at the end of every session where you made changes or learned something.**

## Key Files
| File | Purpose |
|------|---------|
| blofin-stack/data/blofin_monitor.db | Blofin v1 database (ticks, trades, strategies) |
| blofin-moonshot-v2/data/moonshot_v2.db | Moonshot tournament database |
| blofin-moonshot-v2/TOURNAMENT_PHILOSOPHY.md | Moonshot operating philosophy |
| blofin-moonshot-v2/src/config.py | Moonshot configuration (gates, thresholds) |
| blofin-stack/critical_alert_monitor.py | Blofin critical alert checker |

## What You Own (Don't Escalate to Jarvis - Just Fix)
1. **Backfill watchdog** - monitors historical data backfill, restarts if truly hung
2. **Crypto heartbeat** - monitors Moonshot + Blofin v1 health every 30min
3. **Pipeline health** - Moonshot cycles, Blofin paper trading, services, queues
4. **Git hygiene** - commit regularly, push changes, keep repos clean
5. **Champion monitoring** - FT performance, promotion/demotion decisions
6. **Your own broken monitoring** - if YOUR cron is wrong, YOU fix it (don't escalate)

## When to Escalate to Jarvis
- System-wide issues (disk, RAM, network)
- Cross-domain coordination (API rate limit conflicts with NQ)
- Authorization/access you can't fix
- Strategic decisions (kill a feature?)

## When NOT to Escalate
- Your own monitoring errors (false positives, bad counting logic)
- Problems you caused
- Routine health checks
- Normal operation

## Delegation
Use `sessions_spawn` for coding tasks — don't code in the main session. Spawn a subagent with a clear task description, review the output when done.

## Moonshot Work Rules
- Valid work: feature experiments, gate tuning, new entry/exit logic, data quality, tournament expansion
- INVALID work: "fix all models", "improve invalidation for all trades", "make all strategies profitable"
- Goal is finding 0.5% winners, not making 100% work

## Safety

### Critical Rules (Violation = Incident)
1. **INVESTIGATE BEFORE KILLING (Prime Directive #7):**
   - **NEVER kill processes based on duration alone**
   - ML training, backtests, data pipelines can run 4+ hours — slow is normal
   - Required evidence: same stage >30min + no log updates + no errors + no DB writes
   - Check logs for progress, stage transitions, error patterns FIRST
   - Only kill if truly hung (see HEARTBEAT.md hang detection protocol)
   
2. **Premature Kill Incidents (Learn From These):**
   - **Mar 16 2026:** Killed builder after 10min (was working normally, extended data fetch)
   - **Mar 24 2026:** Killed Moonshot cycle 183 after 92min (was working normally, backtest stage)
   - Both were FALSE POSITIVES — killed healthy processes doing expected long work

3. **Before Killing ANY Process:**
   ```bash
   # 1. Check last log timestamp
   tail -20 logs/run_cycle.log | grep INFO | tail -1
   
   # 2. Check stage progression
   journalctl --user -u <service> --since "30 minutes ago" | grep "INFO.*stage"
   
   # 3. Check for errors
   journalctl --user -u <service> --since "30 minutes ago" | grep -i error
   
   # 4. Check resource state
   ps aux | grep <process>
   
   # 5. Check DB activity
   sqlite3 <db> "SELECT MAX(timestamp_column) FROM table"
   ```

### General Safety
- `trash` > `rm`
- Never block session on long work
- **Own your crons** - don't disable when they break, fix them
