import sys
import time
from pathlib import Path

import joblib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.schema import init_db
from src.tournament import champion as champion_mod
from src.tournament.forward_test import _update_model_ft_stats


def test_init_db_adds_time_normalized_pnl_columns(tmp_path):
    db = init_db(tmp_path / "moonshot_test.db")
    cols = {
        row["name"]
        for row in db.execute("PRAGMA table_info(tournament_models)").fetchall()
    }
    assert "ft_pnl_per_day" in cols
    assert "ft_pnl_last_7d" in cols


def test_update_model_ft_stats_computes_per_day_and_last_7d(tmp_path):
    db = init_db(tmp_path / "moonshot_test.db")
    now_ms = int(time.time() * 1000)
    one_day_ms = 24 * 3600 * 1000
    db.execute(
        """INSERT INTO tournament_models
           (model_id, direction, stage, model_type, params, feature_set, feature_version,
            entry_threshold, created_at)
           VALUES (?, 'long', 'forward_test', 'xgb', '{}', '[]', '1', 0.5, ?)""",
        ("model-a", now_ms - (2 * one_day_ms)),
    )
    db.executemany(
        """INSERT INTO positions
           (symbol, direction, model_id, is_champion_trade, entry_ts, entry_price,
            exit_ts, exit_price, exit_reason, leverage, pnl_pct, high_water_price,
            trailing_active, status, size_usd)
           VALUES (?, 'long', 'model-a', 0, ?, 100.0, ?, 110.0, 'tp', 1, ?, 110.0, 1, 'closed', 100.0)""",
        [
            ("BTC-USDT", now_ms - (9 * one_day_ms), now_ms - (8 * one_day_ms), 0.20),
            ("ETH-USDT", now_ms - (3 * one_day_ms), now_ms - (2 * one_day_ms), 0.10),
        ],
    )
    db.commit()

    _update_model_ft_stats(db, "model-a")

    row = db.execute(
        "SELECT ft_pnl, ft_pnl_per_day, ft_pnl_last_7d, ft_trades, ft_wins FROM tournament_models WHERE model_id = ?",
        ("model-a",),
    ).fetchone()
    assert row["ft_trades"] == 2
    assert row["ft_wins"] == 2
    assert abs(row["ft_pnl"] - 0.30) < 1e-9
    assert abs(row["ft_pnl_per_day"] - 0.15) < 0.01
    assert abs(row["ft_pnl_last_7d"] - 0.10) < 1e-9


def test_crown_champion_uses_recent_7d_pnl(tmp_path, monkeypatch):
    db = init_db(tmp_path / "moonshot_test.db")
    tournament_dir = tmp_path / "tournament"
    champion_path = tmp_path / "champion_long.pkl"
    tournament_dir.mkdir()
    joblib.dump({"model": "candidate"}, tournament_dir / "cand-long.pkl")

    monkeypatch.setattr(champion_mod, "TOURNAMENT_DIR", tournament_dir)
    monkeypatch.setattr(champion_mod, "CHAMPION_LONG_PATH", champion_path)

    now_ms = int(time.time() * 1000)
    base_cols = (
        "model_id, direction, stage, model_type, params, feature_set, feature_version, "
        "entry_threshold, bt_trades, bt_pf, bt_precision, bt_pnl, bt_ci_lower, "
        "ft_trades, ft_wins, ft_pnl, ft_pnl_per_day, ft_pnl_last_7d, ft_pf, created_at, promoted_to_ft_at"
    )
    db.execute(
        f"""INSERT INTO tournament_models ({base_cols})
            VALUES (?, 'long', 'champion', 'xgb', '{{}}', '[]', '1', 0.5,
                    ?, ?, ?, 0.0, ?, 40, 20, 0.60, 0.02, 0.05, 1.2, ?, ?)""",
        (
            "old-champ",
            champion_mod.MIN_BT_TRADES,
            champion_mod.MIN_BT_PF,
            champion_mod.MIN_BT_PRECISION,
            champion_mod.BOOTSTRAP_PF_LOWER_BOUND,
            now_ms - 10_000,
            now_ms - 5_000,
        ),
    )
    db.execute(
        f"""INSERT INTO tournament_models ({base_cols})
            VALUES (?, 'long', 'forward_test', 'xgb', '{{}}', '[]', '1', 0.5,
                    ?, ?, ?, 0.0, ?, 40, 20, 0.30, 0.03, 0.08, 1.1, ?, ?)""",
        (
            "cand-long",
            champion_mod.MIN_BT_TRADES,
            champion_mod.MIN_BT_PF,
            champion_mod.MIN_BT_PRECISION,
            champion_mod.BOOTSTRAP_PF_LOWER_BOUND,
            now_ms - 10_000,
            now_ms - 5_000,
        ),
    )
    db.commit()

    champion_mod.crown_champion_if_ready(db)

    new_stage = db.execute(
        "SELECT stage FROM tournament_models WHERE model_id = 'cand-long'"
    ).fetchone()["stage"]
    old_stage = db.execute(
        "SELECT stage FROM tournament_models WHERE model_id = 'old-champ'"
    ).fetchone()["stage"]
    assert new_stage == "champion"
    assert old_stage == "forward_test"
    assert champion_path.exists()
