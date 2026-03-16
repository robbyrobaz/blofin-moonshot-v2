"""Moonshot v2 Research — Exit Strategy Optimizer for 30%+ New Coin Spikes.

Tests different exit strategies on actual spike data to find which methodology
captures the most profit without exiting winners too early.

Exit Strategies Tested:
1. Fixed TP/SL (baseline): 30% TP, 5% SL
2. Trailing Stop: Activate at +15%, trail 10% back
3. Trailing Stop: Activate at +20%, trail 8% back
4. Partial Exit: 50% at +15%, rest trails with +10% back
5. Partial Exit: 33% at +20%, 33% at +30%, rest trails
6. Adaptive TP: 20% TP for new coins (<30d), 30% for others

Run: python research/spike_exit_optimizer.py
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "moonshot_v2.db"

# Known spike coins (from user spec)
SPIKE_COINS = [
    ("ROBO-USDT", 0.443),   # +44.3%
    ("MANTRA-USDT", 0.393), # +39.3%
    ("KAT-USDT", 0.306),    # +30.6%
    ("CL-USDT", None),      # Unknown magnitude
    ("OPN-USDT", None),     # Unknown magnitude
]

# Baseline config
BASELINE_TP = 0.30  # 30%
BASELINE_SL = 0.05  # 5%
HORIZON_BARS = 42   # 7 days


class ExitStrategy:
    """Base class for exit strategies."""

    def __init__(self, name: str):
        self.name = name

    def simulate(self, entry_price: float, candles: list, entry_idx: int, direction: str = "long") -> Dict:
        """Simulate strategy on candle data.

        Returns:
            {
                "exit_price": float,
                "exit_bar": int (relative to entry),
                "pnl_pct": float,
                "hit_tp": bool,
                "hit_sl": bool,
                "max_favorable_move": float (peak gain during trade)
            }
        """
        raise NotImplementedError


class FixedTPSL(ExitStrategy):
    """Fixed take-profit and stop-loss."""

    def __init__(self, tp_pct: float, sl_pct: float):
        super().__init__(f"Fixed_{int(tp_pct*100)}TP_{int(sl_pct*100)}SL")
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct

    def simulate(self, entry_price: float, candles: list, entry_idx: int, direction: str = "long") -> Dict:
        tp_price = entry_price * (1 + self.tp_pct) if direction == "long" else entry_price * (1 - self.tp_pct)
        sl_price = entry_price * (1 - self.sl_pct) if direction == "long" else entry_price * (1 + self.sl_pct)

        max_favorable = 0.0
        for i in range(1, min(HORIZON_BARS + 1, len(candles) - entry_idx)):
            bar = candles[entry_idx + i]

            if direction == "long":
                max_favorable = max(max_favorable, (bar["high"] - entry_price) / entry_price)

                if bar["high"] >= tp_price:
                    return {
                        "exit_price": tp_price,
                        "exit_bar": i,
                        "pnl_pct": self.tp_pct,
                        "hit_tp": True,
                        "hit_sl": False,
                        "max_favorable_move": max_favorable,
                    }
                if bar["low"] <= sl_price:
                    return {
                        "exit_price": sl_price,
                        "exit_bar": i,
                        "pnl_pct": -self.sl_pct,
                        "hit_tp": False,
                        "hit_sl": True,
                        "max_favorable_move": max_favorable,
                    }

        # Horizon expired
        final_price = candles[min(entry_idx + HORIZON_BARS, len(candles) - 1)]["close"]
        pnl_pct = (final_price - entry_price) / entry_price if direction == "long" else (entry_price - final_price) / entry_price
        return {
            "exit_price": final_price,
            "exit_bar": min(HORIZON_BARS, len(candles) - entry_idx - 1),
            "pnl_pct": pnl_pct,
            "hit_tp": False,
            "hit_sl": False,
            "max_favorable_move": max_favorable,
        }


class TrailingStop(ExitStrategy):
    """Trailing stop: activate at threshold, trail by trail_pct."""

    def __init__(self, activate_pct: float, trail_pct: float):
        super().__init__(f"Trail_Activate{int(activate_pct*100)}_Trail{int(trail_pct*100)}")
        self.activate_pct = activate_pct
        self.trail_pct = trail_pct
        self.sl_pct = 0.05  # Hard stop before activation

    def simulate(self, entry_price: float, candles: list, entry_idx: int, direction: str = "long") -> Dict:
        hard_sl = entry_price * (1 - self.sl_pct)
        peak_price = entry_price
        trail_active = False
        trail_stop = None
        max_favorable = 0.0

        for i in range(1, min(HORIZON_BARS + 1, len(candles) - entry_idx)):
            bar = candles[entry_idx + i]

            if direction == "long":
                max_favorable = max(max_favorable, (bar["high"] - entry_price) / entry_price)

                # Hit hard SL before trail activates
                if not trail_active and bar["low"] <= hard_sl:
                    return {
                        "exit_price": hard_sl,
                        "exit_bar": i,
                        "pnl_pct": -self.sl_pct,
                        "hit_tp": False,
                        "hit_sl": True,
                        "max_favorable_move": max_favorable,
                    }

                # Update peak and activate trail
                if bar["high"] > peak_price:
                    peak_price = bar["high"]
                    gain = (peak_price - entry_price) / entry_price
                    if gain >= self.activate_pct:
                        trail_active = True
                        trail_stop = peak_price * (1 - self.trail_pct)

                # Check trail stop
                if trail_active and bar["low"] <= trail_stop:
                    exit_pnl = (trail_stop - entry_price) / entry_price
                    return {
                        "exit_price": trail_stop,
                        "exit_bar": i,
                        "pnl_pct": exit_pnl,
                        "hit_tp": False,
                        "hit_sl": False,
                        "max_favorable_move": max_favorable,
                    }

        # Horizon expired
        final_price = candles[min(entry_idx + HORIZON_BARS, len(candles) - 1)]["close"]
        pnl_pct = (final_price - entry_price) / entry_price
        return {
            "exit_price": final_price,
            "exit_bar": min(HORIZON_BARS, len(candles) - entry_idx - 1),
            "pnl_pct": pnl_pct,
            "hit_tp": False,
            "hit_sl": False,
            "max_favorable_move": max_favorable,
        }


class PartialExitTrail(ExitStrategy):
    """Partial exit: scale out at TP levels, trail remainder."""

    def __init__(self, exits: List[Tuple[float, float]], trail_pct: float):
        """
        Args:
            exits: [(pct_gain, pct_to_exit), ...] e.g. [(0.15, 0.5), (0.30, 0.5)]
            trail_pct: trail % for remaining position
        """
        super().__init__(f"PartialExit_{len(exits)}Levels_Trail{int(trail_pct*100)}")
        self.exits = sorted(exits, key=lambda x: x[0])  # Sort by gain threshold
        self.trail_pct = trail_pct
        self.sl_pct = 0.05

    def simulate(self, entry_price: float, candles: list, entry_idx: int, direction: str = "long") -> Dict:
        hard_sl = entry_price * (1 - self.sl_pct)
        peak_price = entry_price
        remaining_pct = 1.0
        realized_pnl = 0.0
        exits_hit = []
        max_favorable = 0.0
        trail_stop = None

        for i in range(1, min(HORIZON_BARS + 1, len(candles) - entry_idx)):
            bar = candles[entry_idx + i]

            if direction == "long":
                max_favorable = max(max_favorable, (bar["high"] - entry_price) / entry_price)

                # Hard SL before any exits hit
                if remaining_pct > 0 and bar["low"] <= hard_sl:
                    total_pnl = realized_pnl + remaining_pct * (-self.sl_pct)
                    return {
                        "exit_price": hard_sl,
                        "exit_bar": i,
                        "pnl_pct": total_pnl,
                        "hit_tp": len(exits_hit) > 0,
                        "hit_sl": True,
                        "max_favorable_move": max_favorable,
                    }

                # Update peak
                if bar["high"] > peak_price:
                    peak_price = bar["high"]

                # Check partial exits
                current_gain = (peak_price - entry_price) / entry_price
                for exit_gain, exit_size in self.exits:
                    if current_gain >= exit_gain and (exit_gain, exit_size) not in exits_hit:
                        exits_hit.append((exit_gain, exit_size))
                        realized_pnl += remaining_pct * exit_size * exit_gain
                        remaining_pct -= remaining_pct * exit_size

                # After first exit, activate trail on remainder
                if exits_hit and remaining_pct > 0:
                    trail_stop = peak_price * (1 - self.trail_pct)

                # Check trail stop
                if trail_stop and bar["low"] <= trail_stop:
                    remainder_pnl = (trail_stop - entry_price) / entry_price
                    total_pnl = realized_pnl + remaining_pct * remainder_pnl
                    return {
                        "exit_price": trail_stop,
                        "exit_bar": i,
                        "pnl_pct": total_pnl,
                        "hit_tp": len(exits_hit) > 0,
                        "hit_sl": False,
                        "max_favorable_move": max_favorable,
                    }

        # Horizon expired
        final_price = candles[min(entry_idx + HORIZON_BARS, len(candles) - 1)]["close"]
        remainder_pnl = (final_price - entry_price) / entry_price
        total_pnl = realized_pnl + remaining_pct * remainder_pnl
        return {
            "exit_price": final_price,
            "exit_bar": min(HORIZON_BARS, len(candles) - entry_idx - 1),
            "pnl_pct": total_pnl,
            "hit_tp": len(exits_hit) > 0,
            "hit_sl": False,
            "max_favorable_move": max_favorable,
        }


def load_candles(db, symbol: str) -> list:
    """Load all candles for a symbol."""
    rows = db.execute(
        "SELECT ts, open, high, low, close, volume FROM candles WHERE symbol = ? ORDER BY ts ASC",
        (symbol,)
    ).fetchall()
    return [dict(row) for row in rows]


def find_spike_entries(candles: list) -> List[int]:
    """Find potential entry points using simple heuristics.

    Entry criteria:
    - New ATH in last 5 bars (breakout)
    - Volume spike (>2x 14-bar avg)
    - Not already in a huge spike (avoid chasing)
    """
    entries = []
    for i in range(20, len(candles) - HORIZON_BARS):
        bar = candles[i]

        # ATH breakout
        recent_high = max(c["high"] for c in candles[i-5:i])
        if bar["high"] <= recent_high:
            continue

        # Volume spike
        avg_vol = sum(c["volume"] for c in candles[i-14:i]) / 14
        if bar["volume"] < 2.0 * avg_vol:
            continue

        # Not already spiked >20%
        base_price = candles[i-5]["close"]
        if bar["close"] / base_price > 1.20:
            continue

        entries.append(i)

    return entries


def evaluate_strategy_on_coin(db, symbol: str, strategy: ExitStrategy) -> Dict:
    """Evaluate a strategy on all potential entries for a coin."""
    candles = load_candles(db, symbol)
    if len(candles) < HORIZON_BARS + 20:
        return {"trades": 0, "results": []}

    entry_indices = find_spike_entries(candles)
    results = []

    for idx in entry_indices:
        entry_price = candles[idx]["close"]
        result = strategy.simulate(entry_price, candles, idx, direction="long")
        result["symbol"] = symbol
        result["entry_idx"] = idx
        result["entry_ts"] = candles[idx]["ts"]
        result["entry_price"] = entry_price
        results.append(result)

    return {"trades": len(results), "results": results}


def aggregate_metrics(results: List[Dict]) -> Dict:
    """Compute aggregate performance metrics."""
    if not results:
        return {
            "trades": 0,
            "avg_pnl": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "avg_max_favorable": 0.0,
            "capture_ratio": 0.0,
        }

    pnls = [r["pnl_pct"] for r in results]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    win_rate = len(wins) / len(pnls) if pnls else 0.0
    avg_pnl = np.mean(pnls)

    sum_wins = sum(wins) if wins else 0.0
    sum_losses = abs(sum(losses)) if losses else 0.0
    profit_factor = sum_wins / sum_losses if sum_losses > 0 else 999.0

    avg_max_favorable = np.mean([r["max_favorable_move"] for r in results])
    avg_realized = np.mean([r["pnl_pct"] for r in results if r["pnl_pct"] > 0])
    capture_ratio = avg_realized / avg_max_favorable if avg_max_favorable > 0 else 0.0

    return {
        "trades": len(results),
        "avg_pnl": avg_pnl,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_max_favorable": avg_max_favorable,
        "capture_ratio": capture_ratio,
    }


def main():
    """Run exit strategy comparison."""
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    # Define strategies to test
    strategies = [
        FixedTPSL(0.30, 0.05),  # Baseline: 30% TP, 5% SL
        FixedTPSL(0.20, 0.05),  # Lower TP: 20% TP, 5% SL
        FixedTPSL(0.15, 0.05),  # Conservative: 15% TP, 5% SL
        TrailingStop(0.15, 0.10),  # Trail15_10: Activate at +15%, trail 10%
        TrailingStop(0.20, 0.08),  # Trail20_8: Activate at +20%, trail 8%
        TrailingStop(0.10, 0.12),  # Trail10_12: Early activation, wider trail
        PartialExitTrail([(0.15, 0.5)], 0.10),  # 50% at +15%, trail rest 10%
        PartialExitTrail([(0.20, 0.33), (0.30, 0.33)], 0.10),  # 33% at +20%, 33% at +30%, trail rest
    ]

    print("=" * 80)
    print("MOONSHOT V2: EXIT STRATEGY OPTIMIZATION")
    print("=" * 80)
    print(f"\nTarget: Capture 30%+ spikes on new coins (<30d old)")
    print(f"Test coins: {[s for s, _ in SPIKE_COINS]}")
    print(f"Horizon: {HORIZON_BARS} bars (7 days)\n")

    all_results = {}

    for strategy in strategies:
        print(f"\n{'─' * 80}")
        print(f"Strategy: {strategy.name}")
        print(f"{'─' * 80}")

        strategy_results = []

        for symbol, known_spike_pct in SPIKE_COINS:
            coin_data = evaluate_strategy_on_coin(db, symbol, strategy)
            strategy_results.extend(coin_data["results"])

            if coin_data["trades"] > 0:
                metrics = aggregate_metrics(coin_data["results"])
                print(f"\n{symbol} ({coin_data['trades']} entries):")
                print(f"  Avg PnL: {metrics['avg_pnl']:.1%}")
                print(f"  Win Rate: {metrics['win_rate']:.1%}")
                print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
                print(f"  Capture Ratio: {metrics['capture_ratio']:.1%} (realized / max favorable)")

                if known_spike_pct:
                    best_trade = max(coin_data["results"], key=lambda x: x["pnl_pct"])
                    print(f"  Best Trade: {best_trade['pnl_pct']:.1%} (known spike: {known_spike_pct:.1%})")

        # Aggregate across all coins
        all_metrics = aggregate_metrics(strategy_results)
        all_results[strategy.name] = all_metrics

        print(f"\n{'═' * 40}")
        print(f"AGGREGATE ({all_metrics['trades']} total trades):")
        print(f"  Avg PnL: {all_metrics['avg_pnl']:.1%}")
        print(f"  Win Rate: {all_metrics['win_rate']:.1%}")
        print(f"  Profit Factor: {all_metrics['profit_factor']:.2f}")
        print(f"  Avg Max Favorable: {all_metrics['avg_max_favorable']:.1%}")
        print(f"  Capture Ratio: {all_metrics['capture_ratio']:.1%}")

    # Summary table
    print(f"\n\n{'═' * 80}")
    print("SUMMARY: Strategy Comparison")
    print(f"{'═' * 80}\n")
    print(f"{'Strategy':<40} {'Trades':>8} {'Avg PnL':>10} {'Win%':>8} {'PF':>8} {'Capture':>10}")
    print(f"{'-' * 80}")

    sorted_strategies = sorted(all_results.items(), key=lambda x: x[1]["avg_pnl"], reverse=True)
    for name, metrics in sorted_strategies:
        print(f"{name:<40} {metrics['trades']:>8} {metrics['avg_pnl']:>9.1%} "
              f"{metrics['win_rate']:>7.1%} {metrics['profit_factor']:>8.2f} "
              f"{metrics['capture_ratio']:>9.1%}")

    # Recommendation
    best_strategy, best_metrics = sorted_strategies[0]
    print(f"\n{'═' * 80}")
    print(f"RECOMMENDATION: {best_strategy}")
    print(f"{'═' * 80}")
    print(f"Rationale:")
    print(f"  - Highest avg PnL: {best_metrics['avg_pnl']:.1%}")
    print(f"  - Profit Factor: {best_metrics['profit_factor']:.2f}")
    print(f"  - Capture Ratio: {best_metrics['capture_ratio']:.1%} (keeps more of favorable moves)")
    print(f"\nNext Steps:")
    print(f"  1. Implement this exit strategy in backtesting (src/tournament/backtest.py)")
    print(f"  2. Update label generation to reflect this methodology (src/labels/generate.py)")
    print(f"  3. Re-run tournament backtest on all models")
    print(f"  4. Monitor FT performance with new exit logic\n")


if __name__ == "__main__":
    main()
