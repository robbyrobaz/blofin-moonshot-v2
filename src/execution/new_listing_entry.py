"""Moonshot v2 — Rule-Based Entry for New Listings.

Automatically enters ALL coins <7 days old with trailing stop exits.
This captures initial listing spikes that ML models cannot predict (bar 0-10).

Strategy:
- Enter: All coins with days_since_listing <= NEW_LISTING_MAX_AGE_DAYS
- Position: NEW_LISTING_POSITION_PCT of portfolio (default 2%)
- Exit: Trailing stop (activate at +15%, trail 10% below peak)
- Hard Stop: -5%
- Horizon: 42 bars (7 days)

Rationale: 76% of 30%+ spikes happen in first 7 days when ML has insufficient data.
"""

import time

from config import (
    NEW_LISTING_ENABLED,
    NEW_LISTING_MAX_AGE_DAYS,
    NEW_LISTING_POSITION_PCT,
    NEW_LISTING_LEVERAGE,
    MAX_LONG_POSITIONS,
    log,
)


def get_new_listings(db) -> list[str]:
    """Find all coins ≤ NEW_LISTING_MAX_AGE_DAYS old that are active.

    Returns:
        List of symbol strings eligible for rule-based entry.
    """
    if not NEW_LISTING_ENABLED:
        return []

    rows = db.execute(
        """SELECT symbol, days_since_listing
           FROM coins
           WHERE is_active = 1
             AND days_since_listing IS NOT NULL
             AND days_since_listing <= ?
           ORDER BY days_since_listing ASC""",
        (NEW_LISTING_MAX_AGE_DAYS,),
    ).fetchall()

    return [row["symbol"] for row in rows]


def already_entered(db, symbol: str) -> bool:
    """Check if we already have a position for this symbol (open or recently closed).

    Returns:
        True if position exists (don't re-enter), False if eligible for entry.
    """
    # Check open positions
    open_pos = db.execute(
        "SELECT COUNT(*) as cnt FROM positions WHERE symbol = ? AND status = 'open'",
        (symbol,),
    ).fetchone()
    if open_pos and open_pos["cnt"] > 0:
        return True

    # Check recently closed (within 7 days) to avoid re-entering same coin
    ms_7d = 7 * 24 * 3600 * 1000
    now_ms = int(time.time() * 1000)
    recent_closed = db.execute(
        "SELECT COUNT(*) as cnt FROM positions "
        "WHERE symbol = ? AND status != 'open' AND exit_ts > ?",
        (symbol, now_ms - ms_7d),
    ).fetchone()
    if recent_closed and recent_closed["cnt"] > 0:
        return True

    return False


def count_open_new_listing_positions(db) -> int:
    """Count how many open positions are for new listings (model_id = 'new_listing')."""
    row = db.execute(
        "SELECT COUNT(*) as cnt FROM positions "
        "WHERE status = 'open' AND model_id = 'new_listing'"
    ).fetchone()
    return row["cnt"] if row else 0


def enter_new_listing(db, symbol: str, leverage: int = None) -> bool:
    """Create a position for a new listing.

    Args:
        db: sqlite3 connection
        symbol: coin symbol
        leverage: leverage multiplier (default from config)

    Returns:
        True if position created, False if skipped.
    """
    if leverage is None:
        leverage = NEW_LISTING_LEVERAGE

    # Get latest candle for entry price
    candle = db.execute(
        "SELECT close FROM candles WHERE symbol = ? ORDER BY ts DESC LIMIT 1",
        (symbol,),
    ).fetchone()
    if not candle:
        log.warning("enter_new_listing: no candle data for %s", symbol)
        return False

    entry_price = candle["close"]
    now_ms = int(time.time() * 1000)
    size_usd = NEW_LISTING_POSITION_PCT * 1000  # Assume $1000 portfolio for size calc

    db.execute(
        """INSERT INTO positions
           (symbol, direction, model_id, entry_price, entry_ts, leverage,
            size_usd, status, high_water_price, trailing_active)
           VALUES (?, 'long', 'new_listing', ?, ?, ?, ?, 'open', ?, 0)""",
        (
            symbol,
            entry_price,
            now_ms,
            leverage,
            size_usd,
            entry_price,  # Initialize high_water_price to entry_price
        ),
    )
    db.commit()

    log.info(
        "enter_new_listing: opened %s @ %.4f (leverage=%dx, size_usd=%.2f)",
        symbol, entry_price, leverage, size_usd,
    )
    return True


def process_new_listings(db):
    """Main entry point: find and enter new listings.

    Called by orchestration/run_cycle.py on every 4H cycle.
    """
    if not NEW_LISTING_ENABLED:
        log.info("process_new_listings: disabled by config")
        return

    candidates = get_new_listings(db)
    if not candidates:
        log.info("process_new_listings: no new listings found")
        return

    log.info("process_new_listings: %d candidates (≤%d days old)", len(candidates), NEW_LISTING_MAX_AGE_DAYS)

    # Check position limits
    open_count = count_open_new_listing_positions(db)
    if open_count >= MAX_LONG_POSITIONS:
        log.info(
            "process_new_listings: position limit reached (%d/%d open)",
            open_count, MAX_LONG_POSITIONS,
        )
        return

    entered = 0
    for symbol in candidates:
        if already_entered(db, symbol):
            log.debug("process_new_listings: %s already entered, skipping", symbol)
            continue

        if count_open_new_listing_positions(db) >= MAX_LONG_POSITIONS:
            log.info("process_new_listings: hit position limit, stopping")
            break

        if enter_new_listing(db, symbol):
            entered += 1

    log.info("process_new_listings: entered %d new positions", entered)
