#!/usr/bin/env python3
"""Backfill time-normalized FT PnL metrics for all tournament models."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.db.schema import init_db
from src.tournament.forward_test import _compute_ft_pnl_metrics


def main() -> int:
    db = init_db()
    rows = db.execute(
        "SELECT model_id, ft_pnl FROM tournament_models ORDER BY created_at ASC, model_id ASC"
    ).fetchall()

    updated = 0
    for row in rows:
        model_id = row["model_id"]
        ft_pnl = float(row["ft_pnl"] or 0.0)
        ft_pnl_per_day, ft_pnl_last_7d = _compute_ft_pnl_metrics(db, model_id, ft_pnl)
        db.execute(
            """UPDATE tournament_models
               SET ft_pnl_per_day = ?, ft_pnl_last_7d = ?
               WHERE model_id = ?""",
            (ft_pnl_per_day, ft_pnl_last_7d, model_id),
        )
        updated += 1

    db.commit()
    print(f"Backfilled PnL metrics for {updated} models.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
