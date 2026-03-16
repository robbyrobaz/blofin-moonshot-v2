# Incident: Moonshot v2 Deadlock from Blofin Rate Limits

**Date:** 2026-03-15 19:55 MST  
**Duration:** ~2 hours deadlocked  
**Severity:** Medium (no data loss, auto-recovery possible)

---

## Summary

Two Moonshot v2 processes (backtest worker + cycle orchestrator) hung for 2+ hours, consuming CPU but making zero progress. Root cause: Blofin API 429 rate limit exhaustion from concurrent historical backfill + Moonshot data fetching.

---

## Timeline

- **17:42** - Moonshot cycle #109 started (PID 784272)
- **17:49** - Massive 429 errors logged (fetch_mark_prices, fetch_tickers)
- **17:49-19:55** - Both processes stuck, no DB writes, no backtest progress
- **19:55** - Main agent detected long-running processes (15+ hours CPU time)
- **19:55** - Investigation revealed deadlock on Blofin rate limits
- **19:55** - Killed both processes, removed stale lock file
- **20:05** - Next cycle scheduled (timer auto-recovery)

---

## Root Cause

**Blofin REST API limit:** 500 requests/minute shared across ALL processes

**Concurrent users:**
1. **Historical backfill** - downloading 469 symbols × 365 days (5 req/sec sustained)
2. **Moonshot cycle** - fetching mark prices for 343 coins (~343 req in burst)
3. **Moonshot social collector** - hourly data fetch (negligible)

**Result:** Combined load exceeded 500 req/min → 429 responses → retry loops → deadlock

---

## Why The Processes Hung

### Process 1: backtest_new_challengers (PID 671298)
- **Symptom:** 15+ hours CPU time, no backtests completed in 3.5 hours
- **Stuck on:** Likely waiting for feature data that depends on external API calls
- **State:** Running (R), consuming CPU but making no DB progress

### Process 2: run_cycle.py (PID 784272)
- **Symptom:** 10+ hours CPU time, 429 errors at 17:49, then silent
- **Stuck on:** fetch_mark_prices() and fetch_tickers() hitting 429s
- **State:** Probably in retry/backoff loop or waiting for locks

### Why Timer Didn't Kill Them

**Moonshot timer:** OnUnitActiveSec=4h (runs every 4 hours)
- Timer only STARTS new cycles, doesn't kill hung ones
- No timeout mechanism on the cycle itself
- Lock file prevents duplicate cycles, but doesn't detect hangs

---

## Data Impact

**✅ No data loss:**
- Last successful backtest: 209 minutes before kill (17:16)
- 193 models stuck in backtest queue (will retry next cycle)
- 227 models in FT (unaffected)
- Champion still active and trading

**⏸️ Work paused:**
- No new backtests for 3.5 hours
- No new FT promotions
- No champion updates (but existing champion still executing)

---

## Immediate Fix (Applied)

1. ✅ Killed hung processes (PID 671298, 784272)
2. ✅ Removed stale lock file (`moonshot_v2.cycle.lock`)
3. ✅ Next cycle auto-starts in 10 minutes (20:05 MST)

---

## Long-Term Fixes (To Implement)

### 1. Add Cycle Timeout (High Priority)

**Problem:** Cycles can run forever with no kill switch

**Solution:** Add timeout to systemd service
```ini
# In moonshot-v2.service:
[Service]
Type=oneshot
TimeoutStartSec=2h        # Kill if cycle takes >2 hours
RuntimeMaxSec=7200        # Same, in seconds
```

### 2. Respect Blofin Rate Limits (High Priority)

**Problem:** Moonshot doesn't coordinate with other Blofin API users

**Current approach:** Fetch all 343 coins in tight loop → instant 429s

**Solution A: Throttle Moonshot fetches**
```python
# In src/data/candles.py and src/data/extended.py:
BLOFIN_SHARED_RATE_LIMIT = 200  # req/min (40% of 500 total)
# Add sleep(60 / BLOFIN_SHARED_RATE_LIMIT) between requests
```

**Solution B: Pause Moonshot during backfill**
- Historical backfill sets a flag: `/tmp/blofin_backfill_active`
- Moonshot checks flag, skips cycle if set
- Auto-resumes when flag removed

**Solution C: Use WebSocket for live data (best long-term)**
- Switch from REST polling to WebSocket subscription
- WebSocket has separate rate limits
- Only use REST for historical catchup

### 3. Better Retry Logic (Medium Priority)

**Problem:** Moonshot retries 429s forever without exponential backoff

**Solution:** Add smart retry
```python
def fetch_with_backoff(url, max_retries=3):
    for attempt in range(max_retries):
        resp = requests.get(url)
        if resp.status_code == 429:
            wait = min(60, 2 ** attempt * 10)  # 10s, 20s, 40s
            log.warning(f"429 on {url}, waiting {wait}s")
            time.sleep(wait)
            continue
        return resp
    log.error(f"Gave up on {url} after {max_retries} 429s")
    return None  # Let caller handle gracefully
```

### 4. Graceful Degradation (Medium Priority)

**Problem:** If mark prices fail, entire cycle hangs

**Solution:** Make extended data optional
```python
# In tournament/backtest.py:
if mark_price is None:
    log.warning(f"No mark price for {symbol}, using close price")
    mark_price = latest_close  # Fallback
```

---

## Monitoring Improvements

### Add Deadlock Detection Cron

**Run every 30 min:**
```bash
#!/bin/bash
# Check if moonshot cycle has been running >90 min
cycle_pid=$(pgrep -f "run_cycle.py")
if [ -n "$cycle_pid" ]; then
    elapsed=$(ps -o etime= -p $cycle_pid | tr -d ' ')
    # If elapsed > 90 min, kill and alert
fi
```

### Dashboard Metrics

Add to moonshot dashboard:
- Last successful cycle timestamp
- Cycle duration (current vs average)
- Blofin API 429 count (last hour)
- Backtest queue staleness

---

## Prevention Checklist

Before running large Blofin API jobs:

- [ ] Check if Moonshot cycle is active (`pgrep run_cycle`)
- [ ] Pause Moonshot timer if needed (`systemctl --user stop moonshot-v2.timer`)
- [ ] Resume after job completes
- [ ] OR: Implement rate limit coordination (Solution B above)

---

## Related Issues

- Historical backfill (started 18:14) still running - will complete in 2-3 days
- Blofin Stack paper trading unaffected (uses WebSocket, not REST polling)
- Market macro collector unaffected (uses CoinGecko, not Blofin)

---

## Lessons Learned

1. **Shared rate limits need coordination** - multiple processes hitting same API = trouble
2. **Cycles need timeouts** - systemd can enforce this easily
3. **429s should fail gracefully** - don't retry forever, degrade gracefully
4. **Monitor for progress, not just process existence** - CPU time + no DB writes = deadlock

---

*Investigation by: Jarvis (OpenClaw agent)*  
*Incident closed: 2026-03-15 19:55 MST*  
*Next cycle: 2026-03-15 20:05 MST (auto-recovery)*
