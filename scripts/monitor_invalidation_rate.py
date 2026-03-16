#!/usr/bin/env python3
"""Monitor invalidation exit rate over recent cycles.

Tracks the percentage of exits due to invalidation vs other exit reasons.
Target: < 30% invalidation rate (down from 76% before the fix).
"""

import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
import config


def monitor_invalidation_rate(hours_back: int = 24):
    """Show invalidation rate statistics for recent timeframes."""
    db = sqlite3.connect(config.DB_PATH)
    db.row_factory = sqlite3.Row

    cutoff_ms = int((datetime.now() - timedelta(hours=hours_back)).timestamp() * 1000)

    print("=" * 80)
    print(f"INVALIDATION RATE MONITOR — Last {hours_back} hours")
    print("=" * 80)
    print()

    # Overall stats for the time period
    stats = db.execute(
        """SELECT
               exit_reason,
               COUNT(*) as count,
               ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as pct
           FROM positions
           WHERE status = 'closed'
             AND exit_ts >= ?
           GROUP BY exit_reason
           ORDER BY count DESC""",
        (cutoff_ms,),
    ).fetchall()

    if not stats:
        print(f"⚠️  No closed positions in last {hours_back} hours")
        return

    total_exits = sum(row["count"] for row in stats)
    invalidation_exits = sum(
        row["count"]
        for row in stats
        if row["exit_reason"] and "invalidation" in row["exit_reason"].lower()
    )
    invalidation_pct = (invalidation_exits / total_exits * 100) if total_exits > 0 else 0

    print(f"📊 Exit Reasons (last {hours_back}h):")
    print(f"   Total exits: {total_exits}")
    print()
    for row in stats:
        emoji = "🔴" if "invalidation" in (row["exit_reason"] or "").lower() else "  "
        print(f"   {emoji} {row['exit_reason']:20s}  {row['count']:6d}  ({row['pct']:5.2f}%)")

    print()
    print(f"{'='*80}")

    if invalidation_pct < 30:
        status = "✅ SUCCESS"
        color = ""
    elif invalidation_pct < 50:
        status = "⚠️  IMPROVED"
        color = ""
    else:
        status = "❌ HIGH"
        color = ""

    print(f"{status}: Invalidation rate = {invalidation_pct:.1f}% (target: < 30%)")
    print(f"{'='*80}")
    print()

    # Breakdown by timeframe
    print("📈 Invalidation Rate by Timeframe:")
    print()

    for hours in [4, 8, 12, 24]:
        cutoff = int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)

        total = db.execute(
            "SELECT COUNT(*) as cnt FROM positions WHERE status='closed' AND exit_ts >= ?",
            (cutoff,),
        ).fetchone()["cnt"]

        inv = db.execute(
            """SELECT COUNT(*) as cnt FROM positions
               WHERE status='closed' AND exit_ts >= ?
               AND (LOWER(exit_reason) LIKE '%invalidation%')""",
            (cutoff,),
        ).fetchone()["cnt"]

        if total > 0:
            rate = (inv / total * 100)
            status_emoji = "✅" if rate < 30 else "⚠️" if rate < 50 else "❌"
            print(f"   {status_emoji} Last {hours:2d}h:  {inv:4d}/{total:4d} exits  ({rate:5.1f}%)")
        else:
            print(f"      Last {hours:2d}h:  No exits")

    print()

    # Champion vs FT positions
    print("🏆 Invalidation by Position Type:")
    print()

    for is_champ, label in [(1, "Champion"), (0, "Forward Test")]:
        total = db.execute(
            """SELECT COUNT(*) as cnt FROM positions
               WHERE status='closed' AND exit_ts >= ? AND is_champion_trade = ?""",
            (cutoff_ms, is_champ),
        ).fetchone()["cnt"]

        inv = db.execute(
            """SELECT COUNT(*) as cnt FROM positions
               WHERE status='closed' AND exit_ts >= ?
               AND is_champion_trade = ?
               AND (LOWER(exit_reason) LIKE '%invalidation%')""",
            (cutoff_ms, is_champ),
        ).fetchone()["cnt"]

        if total > 0:
            rate = (inv / total * 100)
            print(f"   {label:15s}:  {inv:4d}/{total:4d} exits  ({rate:5.1f}%)")
        else:
            print(f"   {label:15s}:  No exits")

    print()
    print("=" * 80)
    print()
    print("💡 Tips:")
    print("   - Run this script periodically to track improvement")
    print("   - Invalidation < 30% = success")
    print("   - If rate is still high, check logs for re-scoring errors")
    print("   - Next scheduled cycle:", end=" ")

    # Show next cycle time from systemd
    import subprocess
    try:
        result = subprocess.run(
            ["systemctl", "--user", "status", "moonshot-v2.timer"],
            capture_output=True,
            text=True,
        )
        for line in result.stdout.split("\n"):
            if "Trigger:" in line:
                print(line.split("Trigger:")[1].strip())
                break
        else:
            print("(check systemctl --user status moonshot-v2.timer)")
    except:
        print("(check systemctl --user status moonshot-v2.timer)")

    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Monitor Moonshot invalidation exit rates")
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Number of hours to look back (default: 24)",
    )
    args = parser.parse_args()

    monitor_invalidation_rate(args.hours)
