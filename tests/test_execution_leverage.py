import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from src.db.schema import init_db
from src.execution.entry import _compute_position_size
from src.execution.exit import compute_pnl_pct


def test_compute_pnl_pct_uses_position_leverage():
    assert compute_pnl_pct(100.0, 110.0, "long", 2) == 0.2
    assert compute_pnl_pct(100.0, 90.0, "short", 2) == 0.2
    assert compute_pnl_pct(100.0, 95.0, "long", 3) == -0.15


def test_positions_can_preserve_historical_leverage_independent_of_config():
    config_leverage = config.LEVERAGE
    try:
        config.LEVERAGE = 2
        historical_pnl = compute_pnl_pct(100.0, 110.0, "long", 3)
    finally:
        config.LEVERAGE = config_leverage

    assert historical_pnl == 0.3


def test_new_positions_use_default_2x_leverage(tmp_path):
    db = init_db(tmp_path / "moonshot_test.db")
    db.execute(
        """INSERT INTO tournament_models
           (model_id, direction, model_type, params, feature_set, feature_version, entry_threshold)
           VALUES ('champ', 'long', 'xgboost', '{}', '[]', '1', 0.7)"""
    )
    db.execute(
        """INSERT INTO positions
           (symbol, direction, model_id, is_champion_trade, entry_ts, entry_price,
            high_water_price, status, size_usd, leverage)
           VALUES ('BTC-USDT', 'long', 'champ', 1, 1, 100.0, 100.0, 'open', 2000.0, ?)""",
        (config.LEVERAGE,),
    )
    row = db.execute("SELECT leverage FROM positions").fetchone()
    assert row["leverage"] == 2


def test_position_size_is_not_scaled_by_leverage():
    size = _compute_position_size(days_since_listing=None, confidence_mult=1.0, symbol_mult=1.0)
    assert size == config.PAPER_ACCOUNT_SIZE * config.BASE_POSITION_PCT
