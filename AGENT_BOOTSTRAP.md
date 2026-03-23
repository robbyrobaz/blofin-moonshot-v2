# Crypto Agent Bootstrap

**Last updated:** 2026-03-23 00:03 MST (heartbeat)

## ✅ BLOFIN V1 — RETIRED (Mar 21 2026)

### Historical Note
- Blofin v1 tick ingestor RETIRED on Mar 21, 2026
- System transitioned to 1-min candle data only
- Paper trading and dashboard services remain stopped

## System Status (as of Mar 23 00:03)
- ⛔ Blofin v1: All services RETIRED
- ⛔ Pipeline timer: STOPPED per Rob's order — do NOT restart without approval
- ✅ Moonshot v2: HEALTHY

---

## Moonshot v2 — Tournament Status (Mar 23 00:03)

### Champion Performance
- **Current champion:** de44f72dbb01
  - FT PnL: +0.68% (68.37 basis points)
  - FT PF: 2.22
  - FT trades: 388
  - Direction: champion

### Tournament Numbers
| Stage | Count |
|-------|-------|
| FT backlog | 0 models |
| Champion | 1 model |
| Open positions | 933 |

### Notes
- Dashboard LIVE at http://127.0.0.1:8893 (200 OK)
- Service: moonshot-v2-dashboard.service ACTIVE
- No cycle running (normal)
- 1-min candle parquet files: 473 files at /mnt/data/blofin_tickers/raw/ (101% complete, target 468)

---

## Git Status
- `blofin-stack`: multiple sweep script versions (v2-v7) from restoration attempts
- `blofin-moonshot-v2`: CLEAN (no uncommitted changes, 0 unpushed commits)
