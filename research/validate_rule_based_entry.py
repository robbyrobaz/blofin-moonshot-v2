"""Moonshot v2 Research — Validate Rule-Based Entry on Spike Coins.

Simulates the proposed strategy:
- Enter ALL new coins at listing (bar 0)
- Exit with trailing stop: activate at +15%, trail 10% below peak
- Hard stop: -5%
- Horizon: 42 bars (7 days)

Tests on: ROBO, MANTRA, KAT, CL, OPN (known spike coins)

Run: python research/validate_rule_based_entry.py
"""

import sqlite3
from pathlib import Path
from typing import Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "moonshot_v2.db"

SPIKE_COINS = ["ROBO-USDT", "MANTRA-USDT", "KAT-USDT", "CL-USDT", "OPN-USDT"]

# Strategy params
HARD_SL_PCT = 0.05  # -5%
TRAIL_ACTIVATE_PCT = 0.15  # Activate at +15%
TRAIL_DISTANCE_PCT = 0.10  # Trail 10% below peak
HORIZON_BARS = 42  # 7 days
LEVERAGE = 2  # 2x leverage


def simulate_trailing_stop(entry_price: float, candles: list, entry_idx: int) -> Dict:
    """Simulate trailing stop strategy on a long position.

    Returns:
        {
            "exit_price": float,
            "exit_bar": int,
            "pnl_pct_unleveraged": float,
            "pnl_pct_leveraged": float,
            "hit_tp": bool,
            "hit_sl": bool,
            "max_gain": float,
            "exit_reason": str
        }
    """
    hard_sl = entry_price * (1 - HARD_SL_PCT)
    peak_price = entry_price
    trail_active = False
    trail_stop = None

    for i in range(1, min(HORIZON_BARS + 1, len(candles) - entry_idx)):
        bar = candles[entry_idx + i]

        # Hard stop (before trail activates)
        if not trail_active and bar["low"] <= hard_sl:
            pnl = -HARD_SL_PCT
            return {
                "exit_price": hard_sl,
                "exit_bar": i,
                "pnl_pct_unleveraged": pnl,
                "pnl_pct_leveraged": pnl * LEVERAGE,
                "hit_tp": False,
                "hit_sl": True,
                "max_gain": 0.0,
                "exit_reason": "hard_stop",
            }

        # Update peak
        if bar["high"] > peak_price:
            peak_price = bar["high"]
            gain = (peak_price - entry_price) / entry_price

            # Activate trail
            if gain >= TRAIL_ACTIVATE_PCT:
                trail_active = True
                trail_stop = peak_price * (1 - TRAIL_DISTANCE_PCT)

        # Check trail stop
        if trail_active and bar["low"] <= trail_stop:
            pnl = (trail_stop - entry_price) / entry_price
            max_gain = (peak_price - entry_price) / entry_price
            return {
                "exit_price": trail_stop,
                "exit_bar": i,
                "pnl_pct_unleveraged": pnl,
                "pnl_pct_leveraged": pnl * LEVERAGE,
                "hit_tp": True,
                "hit_sl": False,
                "max_gain": max_gain,
                "exit_reason": "trailing_stop",
            }

    # Horizon expired - exit at market
    final_bar = candles[min(entry_idx + HORIZON_BARS, len(candles) - 1)]
    final_price = final_bar["close"]
    pnl = (final_price - entry_price) / entry_price
    max_gain = (peak_price - entry_price) / entry_price

    return {
        "exit_price": final_price,
        "exit_bar": min(HORIZON_BARS, len(candles) - entry_idx - 1),
        "pnl_pct_unleveraged": pnl,
        "pnl_pct_leveraged": pnl * LEVERAGE,
        "hit_tp": trail_active,  # Trail activated = reached +15%
        "hit_sl": False,
        "max_gain": max_gain,
        "exit_reason": "horizon_expired",
    }


def load_candles(db, symbol: str) -> list:
    """Load all candles for a symbol."""
    rows = db.execute(
        "SELECT ts, open, high, low, close, volume FROM candles WHERE symbol = ? ORDER BY ts ASC",
        (symbol,)
    ).fetchall()
    return [dict(row) for row in rows]


def backtest_coin(db, symbol: str) -> Dict:
    """Backtest rule-based entry on a single coin (enter at bar 0)."""
    candles = load_candles(db, symbol)
    if len(candles) < 2:
        return None

    # Enter at bar 0 (listing)
    entry_idx = 0
    entry_price = candles[entry_idx]["close"]

    result = simulate_trailing_stop(entry_price, candles, entry_idx)
    result["symbol"] = symbol
    result["entry_price"] = entry_price

    return result


def main():
    """Run validation backtest on spike coins."""
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    print("=" * 80)
    print("MOONSHOT V2: RULE-BASED ENTRY VALIDATION")
    print("=" * 80)
    print("\nStrategy:")
    print(f"  • Enter: ALL new coins at bar 0 (listing)")
    print(f"  • Hard Stop: -{HARD_SL_PCT:.0%}")
    print(f"  • Trail: Activate at +{TRAIL_ACTIVATE_PCT:.0%}, trail {TRAIL_DISTANCE_PCT:.0%} below peak")
    print(f"  • Horizon: {HORIZON_BARS} bars (7 days)")
    print(f"  • Leverage: {LEVERAGE}x")
    print(f"\nTest Coins: {SPIKE_COINS}\n")

    results = []
    for symbol in SPIKE_COINS:
        result = backtest_coin(db, symbol)
        if result:
            results.append(result)

            print(f"{'═' * 80}")
            print(f"{symbol}")
            print(f"{'═' * 80}")
            print(f"Entry: ${result['entry_price']:.4f} at bar 0")
            print(f"Exit:  ${result['exit_price']:.4f} at bar {result['exit_bar']} ({result['exit_reason']})")
            print(f"")
            print(f"PnL (unleveraged): {result['pnl_pct_unleveraged']:+.1%}")
            print(f"PnL (2x leverage): {result['pnl_pct_leveraged']:+.1%}")
            print(f"Max Favorable Move: {result['max_gain']:.1%}")
            print(f"")
            if result['hit_tp']:
                capture = result['pnl_pct_unleveraged'] / result['max_gain'] if result['max_gain'] > 0 else 0
                print(f"✅ Trail activated - captured {capture:.0%} of max gain")
            elif result['hit_sl']:
                print(f"❌ Hard stop hit")
            else:
                print(f"⏱️  Horizon expired")
            print()

    # Aggregate stats
    print(f"\n{'═' * 80}")
    print("AGGREGATE PERFORMANCE")
    print(f"{'═' * 80}\n")

    total_trades = len(results)
    winners = [r for r in results if r["pnl_pct_leveraged"] > 0]
    losers = [r for r in results if r["pnl_pct_leveraged"] <= 0]

    win_rate = len(winners) / total_trades if total_trades > 0 else 0
    avg_win = sum(r["pnl_pct_leveraged"] for r in winners) / len(winners) if winners else 0
    avg_loss = sum(r["pnl_pct_leveraged"] for r in losers) / len(losers) if losers else 0
    avg_pnl = sum(r["pnl_pct_leveraged"] for r in results) / total_trades if total_trades > 0 else 0

    sum_wins = sum(r["pnl_pct_leveraged"] for r in winners)
    sum_losses = abs(sum(r["pnl_pct_leveraged"] for r in losers))
    profit_factor = sum_wins / sum_losses if sum_losses > 0 else 999.0

    print(f"Total Trades: {total_trades}")
    print(f"Winners: {len(winners)} ({win_rate:.0%})")
    print(f"Losers: {len(losers)} ({1-win_rate:.0%})")
    print(f"")
    print(f"Avg Win: {avg_win:+.1%} (2x leverage)")
    print(f"Avg Loss: {avg_loss:+.1%} (2x leverage)")
    print(f"Avg PnL: {avg_pnl:+.1%} (2x leverage)")
    print(f"")
    print(f"Profit Factor: {profit_factor:.2f}")
    print(f"")

    # Trail effectiveness
    trail_activated = [r for r in results if r["hit_tp"]]
    if trail_activated:
        avg_capture = sum(
            r["pnl_pct_unleveraged"] / r["max_gain"]
            for r in trail_activated if r["max_gain"] > 0
        ) / len(trail_activated)
        print(f"Trail Activation Rate: {len(trail_activated)}/{total_trades} ({len(trail_activated)/total_trades:.0%})")
        print(f"Avg Capture Ratio (when trail active): {avg_capture:.0%}")

    # Expected value per trade
    print(f"\n{'─' * 80}")
    print("EXPECTED VALUE ANALYSIS")
    print(f"{'─' * 80}\n")
    ev_per_trade = avg_pnl * 0.02  # 2% position size
    print(f"Position Size: 2% of portfolio")
    print(f"Expected Value per Trade: {ev_per_trade:+.2%} of portfolio")
    print(f"")

    if total_trades >= 5:
        # Simulate 100 random new coins with same win rate
        simulated_wins = int(100 * win_rate)
        simulated_losses = 100 - simulated_wins
        simulated_pnl = (simulated_wins * avg_win + simulated_losses * avg_loss) * 0.02
        print(f"Simulated: 100 new coins entered @ 2% each")
        print(f"  Winners: {simulated_wins} @ {avg_win:+.1%} each = {simulated_wins * avg_win * 0.02:+.1%}")
        print(f"  Losers: {simulated_losses} @ {avg_loss:+.1%} each = {simulated_losses * avg_loss * 0.02:+.1%}")
        print(f"  Net PnL: {simulated_pnl:+.1%} of portfolio")

    # Decision
    print(f"\n{'═' * 80}")
    if profit_factor >= 1.2 and avg_pnl > 0:
        print("✅ RECOMMENDATION: DEPLOY RULE-BASED STRATEGY")
        print(f"{'═' * 80}")
        print(f"Rationale:")
        print(f"  • Profit Factor {profit_factor:.2f} > 1.2 (profitable)")
        print(f"  • Positive expected value: {avg_pnl:+.1%} per trade (2x leverage)")
        print(f"  • Trail activation captures {len(trail_activated)}/{total_trades} spikes")
        print(f"")
        print(f"Next Steps:")
        print(f"  1. Implement src/execution/new_listing_entry.py")
        print(f"  2. Add trailing stop logic to src/execution/exit.py")
        print(f"  3. Deploy and monitor for 4 weeks (20+ new coins)")
    else:
        print("❌ RECOMMENDATION: DO NOT DEPLOY")
        print(f"{'═' * 80}")
        print(f"Rationale:")
        print(f"  • Profit Factor {profit_factor:.2f} < 1.2 (insufficient edge)")
        print(f"  • Need higher win rate or better capture ratio")
        print(f"")
        print(f"Alternative Actions:")
        print(f"  1. Adjust trail parameters (wider activation, tighter trail)")
        print(f"  2. Test on more coins (current sample n={total_trades})")
        print(f"  3. Consider ML-only approach for 30+ day old coins")

    print()


if __name__ == "__main__":
    main()
