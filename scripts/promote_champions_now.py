#!/usr/bin/env python3
"""Promote champions from existing FT models."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import log
from src.db.schema import get_db
from src.tournament.champion import crown_champion_if_ready, demote_underperformers

def main():
    """Run champion promotion only."""
    log.info("=" * 80)
    log.info("CHAMPION PROMOTION")
    log.info("=" * 80)

    db = get_db()

    # Step 1: Demote catastrophic underperformers
    log.info("STEP 1: Demoting catastrophic underperformers...")
    demote_underperformers(db)

    # Step 2: Crown champions
    log.info("STEP 2: Crowning champions...")
    crown_champion_if_ready(db)

    # Final status
    champions = db.execute(
        """SELECT model_id, direction, ft_pnl, ft_pf, ft_trades, bt_pf, ft_pnl_last_7d
           FROM tournament_models WHERE stage='champion'"""
    ).fetchall()

    log.info("=" * 80)
    log.info("PROMOTION COMPLETE")
    log.info("=" * 80)
    log.info("Champions: %d", len(champions))
    for champ in champions:
        log.info(
            "  %s %s: ft_pnl=%.2f%% ft_pf=%.2f bt_pf=%.2f ft_trades=%d ft_7d=%.2f%%",
            champ["direction"].upper(),
            champ["model_id"][:12],
            champ["ft_pnl"] or 0,
            champ["ft_pf"] or 0,
            champ["bt_pf"] or 0,
            champ["ft_trades"] or 0,
            champ["ft_pnl_last_7d"] or 0,
        )

    db.close()


if __name__ == "__main__":
    main()
