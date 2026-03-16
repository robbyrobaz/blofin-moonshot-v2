#!/usr/bin/env python3
"""Run a full tournament cycle: generate challengers, backtest, crown champions."""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import log
from src.db.schema import get_db
from src.tournament.challenger import generate_challengers
from src.tournament.backtest import backtest_new_challengers
from src.tournament.champion import crown_champion_if_ready, demote_underperformers


def main():
    """Run tournament: generate -> backtest -> crown."""
    log.info("=" * 80)
    log.info("FULL TOURNAMENT CYCLE START")
    log.info("=" * 80)

    db = get_db()

    # Step 1: Generate 25 challengers for each direction (forced balance)
    log.info("STEP 1: Generating 50 challengers (25 long, 25 short)...")
    start = time.time()
    created = generate_challengers(db, n=50)
    elapsed = time.time() - start

    long_count = sum(1 for c in created if c.get("direction") == "long")
    short_count = sum(1 for c in created if c.get("direction") == "short")
    log.info(
        "Generated %d challengers in %.1fs (long=%d, short=%d)",
        len(created), elapsed, long_count, short_count,
    )

    # Step 2: Backtest all pending challengers
    log.info("STEP 2: Backtesting all challengers...")
    start = time.time()
    backtest_new_challengers(db)
    elapsed = time.time() - start
    log.info("Backtest complete in %.1fs", elapsed)

    # Check how many passed to FT
    ft_models = db.execute(
        "SELECT model_id, direction FROM tournament_models WHERE stage IN ('forward_test', 'ft')"
    ).fetchall()
    ft_long = sum(1 for m in ft_models if m["direction"] == "long")
    ft_short = sum(1 for m in ft_models if m["direction"] == "short")
    log.info("FT models: %d total (long=%d, short=%d)", len(ft_models), ft_long, ft_short)

    # Step 3: Demote catastrophic underperformers
    log.info("STEP 3: Demoting catastrophic underperformers...")
    demote_underperformers(db)

    # Step 4: Crown champions
    log.info("STEP 4: Crowning champions...")
    crown_champion_if_ready(db)

    # Final status
    champions = db.execute(
        "SELECT model_id, direction, ft_pnl, ft_pf, ft_trades FROM tournament_models WHERE stage='champion'"
    ).fetchall()

    log.info("=" * 80)
    log.info("TOURNAMENT CYCLE COMPLETE")
    log.info("=" * 80)
    log.info("Champions: %d", len(champions))
    for champ in champions:
        log.info(
            "  %s %s: pnl=%.2f%% pf=%.2f trades=%d",
            champ["direction"].upper(),
            champ["model_id"][:12],
            champ["ft_pnl"] or 0,
            champ["ft_pf"] or 0,
            champ["ft_trades"] or 0,
        )

    db.close()


if __name__ == "__main__":
    main()
