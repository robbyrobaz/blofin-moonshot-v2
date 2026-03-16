"""Moonshot v2 Research — When Do New Coin Spikes Happen?

Critical Question: Do 30%+ spikes happen EARLY (first 7 days) or LATE (30+ days)?

If early: ML models CAN'T predict them (no historical data at listing time).
Solution: Rule-based entry on new listings + ML for established coins.

If late: ML models CAN predict them (enough historical data).
Solution: Fix exit strategy (trailing stops, etc).

Run: python research/spike_timing_analysis.py
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "moonshot_v2.db"

SPIKE_COINS = ["ROBO-USDT", "MANTRA-USDT", "KAT-USDT", "CL-USDT", "OPN-USDT"]


def analyze_spike_timing(db, symbol: str):
    """Analyze when 30%+ spikes occur relative to listing date."""
    rows = db.execute(
        "SELECT ts, datetime(ts/1000, 'unixepoch') as dt, high, low, close "
        "FROM candles WHERE symbol = ? ORDER BY ts ASC",
        (symbol,)
    ).fetchall()

    if not rows:
        print(f"{symbol}: NO DATA")
        return

    first_ts = rows[0]["ts"]
    first_dt = datetime.fromtimestamp(first_ts / 1000)

    print(f"\n{'═' * 80}")
    print(f"{symbol}")
    print(f"{'═' * 80}")
    print(f"First candle: {first_dt}")
    print(f"Total candles: {len(rows)}")

    # Find all 30%+ moves within 42 bars
    spikes = []
    for i in range(len(rows) - 10):
        entry_price = rows[i]["close"]
        entry_ts = rows[i]["ts"]
        hours_since_listing = (entry_ts - first_ts) / (1000 * 3600)
        days_since_listing = hours_since_listing / 24

        # Find peak within next 42 bars
        peak_price = max(r["high"] for r in rows[i+1:min(i+43, len(rows))])
        gain = (peak_price - entry_price) / entry_price

        if gain >= 0.30:  # 30%+ move
            # Find where peak occurred
            peak_bar_idx = None
            for j in range(i+1, min(i+43, len(rows))):
                if rows[j]["high"] >= peak_price * 0.999:  # Within 0.1% of peak
                    peak_bar_idx = j
                    break

            bars_to_peak = peak_bar_idx - i if peak_bar_idx else 0
            hours_to_peak = bars_to_peak * 4  # 4H candles

            spikes.append({
                "entry_bar": i,
                "days_since_listing": days_since_listing,
                "entry_price": entry_price,
                "peak_price": peak_price,
                "gain_pct": gain,
                "bars_to_peak": bars_to_peak,
                "hours_to_peak": hours_to_peak,
            })

    if not spikes:
        print(f"❌ NO 30%+ spikes found")
        return

    print(f"\n✅ Found {len(spikes)} entries with 30%+ gains")

    # Best spike
    best = max(spikes, key=lambda x: x["gain_pct"])
    print(f"\n🚀 BEST SPIKE:")
    print(f"   Entry at bar {best['entry_bar']} ({best['days_since_listing']:.1f} days after listing)")
    print(f"   Gain: {best['gain_pct']:.1%}")
    print(f"   Peak reached in {best['hours_to_peak']:.0f} hours ({best['bars_to_peak']} bars)")

    # Timing analysis
    early_spikes = [s for s in spikes if s["days_since_listing"] <= 7]
    mid_spikes = [s for s in spikes if 7 < s["days_since_listing"] <= 30]
    late_spikes = [s for s in spikes if s["days_since_listing"] > 30]

    print(f"\n📊 SPIKE TIMING:")
    print(f"   First 7 days: {len(early_spikes)} entries ({len(early_spikes)/len(spikes):.0%})")
    if early_spikes:
        avg_gain = sum(s["gain_pct"] for s in early_spikes) / len(early_spikes)
        max_gain = max(s["gain_pct"] for s in early_spikes)
        print(f"      Avg gain: {avg_gain:.1%}, Max gain: {max_gain:.1%}")

    print(f"   Days 8-30: {len(mid_spikes)} entries ({len(mid_spikes)/len(spikes):.0%})")
    if mid_spikes:
        avg_gain = sum(s["gain_pct"] for s in mid_spikes) / len(mid_spikes)
        max_gain = max(s["gain_pct"] for s in mid_spikes)
        print(f"      Avg gain: {avg_gain:.1%}, Max gain: {max_gain:.1%}")

    print(f"   After 30 days: {len(late_spikes)} entries ({len(late_spikes)/len(spikes):.0%})")
    if late_spikes:
        avg_gain = sum(s["gain_pct"] for s in late_spikes) / len(late_spikes)
        max_gain = max(s["gain_pct"] for s in late_spikes)
        print(f"      Avg gain: {avg_gain:.1%}, Max gain: {max_gain:.1%}")

    # Feature availability check
    print(f"\n🔬 ML MODEL FEASIBILITY:")
    first_7d_bar = int(7 * 24 / 4)  # 42 bars = 7 days
    first_30d_bar = int(30 * 24 / 4)  # 180 bars = 30 days

    if early_spikes:
        earliest_spike_bar = min(s["entry_bar"] for s in early_spikes)
        print(f"   Earliest spike at bar {earliest_spike_bar}")
        if earliest_spike_bar < first_7d_bar:
            print(f"   ❌ ML CANNOT PREDICT: Spike happens before 7 days of history (need 42+ bars for features)")
        elif earliest_spike_bar < first_30d_bar:
            print(f"   ⚠️  ML LIMITED: Only {earliest_spike_bar} bars of history (many features need 180+ bars)")
        else:
            print(f"   ✅ ML CAN PREDICT: {earliest_spike_bar} bars of history available")


def main():
    """Run spike timing analysis."""
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    print("=" * 80)
    print("MOONSHOT V2: NEW COIN SPIKE TIMING ANALYSIS")
    print("=" * 80)
    print("\nCritical Question: When do 30%+ spikes happen after listing?")
    print("  • Early (0-7 days): ML models CANNOT predict (no historical data)")
    print("  • Mid (8-30 days): ML models LIMITED (partial features)")
    print("  • Late (30+ days): ML models CAN predict (full feature set)\n")

    for symbol in SPIKE_COINS:
        analyze_spike_timing(db, symbol)

    print(f"\n\n{'═' * 80}")
    print("CONCLUSIONS & RECOMMENDATIONS")
    print(f"{'═' * 80}\n")
    print("1. If spikes are EARLY (0-7 days):")
    print("   → Use RULE-BASED entry on ALL new listings (<7d old)")
    print("   → Entry: Fixed % of portfolio on every new coin")
    print("   → Exit: Trailing stop (activate at +15%, trail 10%)")
    print("   → ML models are NOT useful for initial spike prediction\n")
    print("2. If spikes are MID (8-30 days):")
    print("   → Train models on LIMITED feature set (only 7-14 day indicators)")
    print("   → Lower backtest requirements (fewer bars needed)")
    print("   → Focus on volume + price action features (not 30d+ indicators)\n")
    print("3. If spikes are LATE (30+ days):")
    print("   → Current ML approach is correct (full feature set)")
    print("   → Problem is EXIT STRATEGY, not prediction")
    print("   → Implement trailing stops to let winners run\n")


if __name__ == "__main__":
    main()
