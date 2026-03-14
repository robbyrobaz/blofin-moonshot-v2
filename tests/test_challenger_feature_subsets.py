import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.schema import init_db
from src.tournament.challenger import (
    FEATURE_SUBSETS,
    generate_challengers,
    generate_random_feature_subset,
    resolve_feature_set,
)


def test_generate_random_feature_subset_focus_areas():
    random.seed(7)

    minimal = generate_random_feature_subset("minimal")
    assert 10 <= len(minimal) <= 15

    maximal = generate_random_feature_subset("maximal")
    assert maximal == FEATURE_SUBSETS["all"]
    assert len(maximal) == 50

    social_boost = generate_random_feature_subset("social_boost")
    assert set(FEATURE_SUBSETS["core_only"]).issubset(social_boost)
    assert len(social_boost) == len(FEATURE_SUBSETS["core_only"]) + 13

    for focus_area in ("price_heavy", "volume_heavy", "volatility_heavy", "regime_aware"):
        subset = generate_random_feature_subset(focus_area)
        assert len(subset) >= 5
        assert len(subset) == len(set(subset))


def test_generate_challengers_creates_diverse_feature_sets(tmp_path):
    random.seed(11)
    db = init_db(tmp_path / "moonshot_test.db")

    challengers = generate_challengers(db, n=20)

    assert len(challengers) == 20

    feature_sets = [tuple(resolve_feature_set(ch["feature_set"])) for ch in challengers]
    unique_feature_sets = {fs for fs in feature_sets}
    random_subsets = [fs for fs in unique_feature_sets if list(fs) not in FEATURE_SUBSETS.values()]

    assert len(unique_feature_sets) >= 10
    assert len(random_subsets) >= 6

    rows = db.execute(
        "SELECT params, feature_set FROM tournament_models ORDER BY created_at, model_id"
    ).fetchall()
    assert len(rows) == 20

    for row in rows:
        params = json.loads(row["params"])
        stored_feature_set = json.loads(row["feature_set"])
        assert resolve_feature_set(params["feature_set"]) == stored_feature_set
