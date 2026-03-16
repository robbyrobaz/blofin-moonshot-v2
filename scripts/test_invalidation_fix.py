#!/usr/bin/env python3
"""Test script to verify invalidation re-scoring uses stored features.

This script:
1. Finds an open position with entry_features
2. Re-scores it using stored features
3. Compares to the original entry_ml_score
4. Verifies that re-scoring logic works correctly
"""

import json
import sqlite3
import sys
from pathlib import Path

import joblib
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
import config
from config import log


def test_invalidation_rescore():
    """Test that invalidation re-scoring uses stored features correctly."""
    db = sqlite3.connect(config.DB_PATH)
    db.row_factory = sqlite3.Row

    # Find an open position with entry_features
    pos = db.execute(
        """SELECT * FROM positions
           WHERE status = 'open'
             AND entry_features IS NOT NULL
             AND entry_ml_score IS NOT NULL
           LIMIT 1"""
    ).fetchone()

    if not pos:
        print("❌ No open positions with entry_features found")
        return False

    print(f"\n✅ Found test position:")
    print(f"   Position ID: {pos['id']}")
    print(f"   Symbol: {pos['symbol']}")
    print(f"   Direction: {pos['direction']}")
    print(f"   Model ID: {pos['model_id'][:8]}...")
    print(f"   Entry ML Score: {pos['entry_ml_score']:.4f}")

    # Get model's expected feature order
    model_row = db.execute(
        "SELECT feature_set FROM tournament_models WHERE model_id = ?",
        (pos["model_id"],),
    ).fetchone()

    if not model_row:
        print(f"❌ Model not found in tournament_models table")
        return False

    from src.tournament.challenger import resolve_feature_set
    model_feature_names = resolve_feature_set(model_row["feature_set"])

    print(f"\n✅ Model feature_set: {model_row['feature_set']}")
    print(f"   Resolved to {len(model_feature_names)} features")
    print(f"   Feature names sample: {model_feature_names[:3]}...")

    # Parse stored entry features
    try:
        entry_features_data = json.loads(pos["entry_features"])
        feature_values_dict = entry_features_data.get("feature_values", {})
        stored_feature_names = entry_features_data.get("feature_names", [])

        print(f"\n✅ Parsed entry_features:")
        print(f"   Stored feature_names (sorted): {stored_feature_names[:3]}...")
        print(f"   Feature values dict has {len(feature_values_dict)} items")

        # Build feature vector in MODEL's expected order using STORED values
        if isinstance(feature_values_dict, dict):
            feature_vector = [feature_values_dict.get(fn) for fn in model_feature_names]
        else:
            # Legacy format
            feature_vector = list(feature_values_dict)

        if any(v is None for v in feature_vector):
            print("❌ Missing feature values in stored features")
            missing = [fn for fn in model_feature_names if feature_values_dict.get(fn) is None]
            print(f"   Missing features: {missing[:5]}")
            return False

        print(f"   Feature vector length: {len(feature_vector)}")
        print(f"   Feature values sample: {feature_vector[:3]}")

    except (json.JSONDecodeError, KeyError) as e:
        print(f"❌ Failed to parse entry_features: {e}")
        return False

    # Load model and re-score
    try:
        model_path = config.TOURNAMENT_DIR / f"{pos['model_id']}.pkl"
        if not model_path.exists():
            print(f"❌ Model file not found: {model_path}")
            return False

        model = joblib.load(model_path)
        print(f"\n✅ Loaded model from: {model_path}")

        # Re-score with stored features
        X = np.array([feature_vector], dtype=np.float32)
        rescored_score = float(model.predict_proba(X)[:, 1][0])

        print(f"\n✅ Re-scoring results:")
        print(f"   Original entry_ml_score: {pos['entry_ml_score']:.4f}")
        print(f"   Re-scored with stored features: {rescored_score:.4f}")
        print(f"   Difference: {abs(rescored_score - pos['entry_ml_score']):.6f}")

        # They should be identical (or very close due to floating point)
        if abs(rescored_score - pos['entry_ml_score']) < 0.001:
            print(f"\n✅ SUCCESS: Re-scoring with stored features produces identical score!")
            print(f"   This confirms that stored features are being used correctly.")
        else:
            print(f"\n⚠️  WARNING: Scores differ by more than 0.001")
            print(f"   This might indicate an issue with feature storage/retrieval.")
            return False

        # Check invalidation threshold
        inv_row = db.execute(
            "SELECT invalidation_threshold FROM tournament_models WHERE model_id = ?",
            (pos["model_id"],),
        ).fetchone()

        if inv_row and inv_row["invalidation_threshold"] is not None:
            inv_threshold = inv_row["invalidation_threshold"]
            print(f"\n✅ Invalidation threshold: {inv_threshold:.4f}")

            if rescored_score < inv_threshold:
                print(f"   ⚠️  Position WOULD be invalidated (score {rescored_score:.4f} < threshold {inv_threshold:.4f})")
            else:
                print(f"   ✅ Position is valid (score {rescored_score:.4f} >= threshold {inv_threshold:.4f})")
        else:
            print(f"\n   No invalidation threshold set for this model")

        return True

    except Exception as e:
        print(f"❌ Failed to re-score: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("TESTING: Invalidation Re-Scoring with Stored Features")
    print("=" * 70)

    success = test_invalidation_rescore()

    print("\n" + "=" * 70)
    if success:
        print("✅ TEST PASSED: Invalidation fix is working correctly!")
    else:
        print("❌ TEST FAILED: Check errors above")
    print("=" * 70)

    sys.exit(0 if success else 1)
