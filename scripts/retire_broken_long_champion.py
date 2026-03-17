#!/usr/bin/env python3
"""Retire broken LONG champion 9b842069b20d.

Root cause: Promoted with MIN_BT_PF_LONG=0.3 (now fixed to 1.5).
Model has BT PF=0.79, FT PF=0.22 after 39 trades (-200% PnL).

This script:
1. Retires model 9b842069b20d
2. Removes champion pickle if exists
3. Logs the action
"""

import sqlite3
import time
from pathlib import Path

DB_PATH = Path("data/moonshot_v2.db")
CHAMPION_LONG_PATH = Path("models/champion_long.pkl")
MODEL_ID = "9b842069b20d"

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Check current status
    row = c.execute(
        "SELECT stage, direction, ft_pf, ft_trades, bt_pf, retired_at "
        "FROM tournament_models WHERE model_id = ?",
        (MODEL_ID,)
    ).fetchone()

    if not row:
        print(f"ERROR: Model {MODEL_ID} not found")
        return

    stage, direction, ft_pf, ft_trades, bt_pf, retired_at = row
    print(f"Current status: {MODEL_ID[:12]}")
    print(f"  Stage: {stage}")
    print(f"  Direction: {direction}")
    print(f"  BT PF: {bt_pf:.2f}")
    print(f"  FT PF: {ft_pf:.2f}")
    print(f"  FT Trades: {ft_trades}")
    print(f"  Retired: {retired_at is not None}")

    if stage != "champion" or direction != "long":
        print(f"WARNING: Expected stage='champion' direction='long', got stage='{stage}' direction='{direction}'")
        print("Proceeding anyway...")

    # Retire the model
    now_ms = int(time.time() * 1000)
    retire_reason = f"unprofitable_long_champion_bt_pf_{bt_pf:.2f}_ft_pf_{ft_pf:.2f}_promoted_during_loose_gates"

    c.execute(
        """UPDATE tournament_models
           SET stage = 'retired',
               retired_at = ?,
               retire_reason = ?,
               promoted_to_champion_at = NULL
           WHERE model_id = ?""",
        (now_ms, retire_reason, MODEL_ID)
    )

    conn.commit()
    print(f"\n✓ Retired model {MODEL_ID[:12]}")
    print(f"  Reason: {retire_reason}")

    # Remove champion pickle if exists
    if CHAMPION_LONG_PATH.exists():
        CHAMPION_LONG_PATH.unlink()
        print(f"✓ Removed champion pickle: {CHAMPION_LONG_PATH}")
    else:
        print(f"  No champion pickle found (expected: {CHAMPION_LONG_PATH})")

    # Verify no LONG champion remains
    remaining = c.execute(
        "SELECT model_id FROM tournament_models WHERE stage = 'champion' AND direction = 'long'"
    ).fetchone()

    if remaining:
        print(f"\nWARNING: Another LONG champion still exists: {remaining[0][:12]}")
    else:
        print(f"\n✓ No LONG champion active (correct state)")

    conn.close()

if __name__ == "__main__":
    main()
