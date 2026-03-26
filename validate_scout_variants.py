#!/usr/bin/env python3
"""Validate 2026-03-26 Moonshot Scout variant configs."""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.features.registry import FEATURE_REGISTRY

CONFIG_DIR = Path(__file__).parent / "configs" / "generated" / "2026-03-26"
VALID_MODEL_TYPES = {"xgboost", "lightgbm", "catboost", "randomforest"}
VALID_DIRECTIONS = {"short", "long"}

def validate_config(config_path):
    """Validate a single variant config. Returns (is_valid, error_msg)."""
    try:
        with open(config_path) as f:
            cfg = json.load(f)
    except Exception as e:
        return False, f"JSON parse error: {e}"
    
    # Check required fields
    required = ["direction", "model_type", "params", "feature_set", 
                "entry_threshold", "invalidation_threshold", "description"]
    for field in required:
        if field not in cfg:
            return False, f"Missing required field: {field}"
    
    # Validate direction
    if cfg["direction"] not in VALID_DIRECTIONS:
        return False, f"Invalid direction: {cfg['direction']} (must be {VALID_DIRECTIONS})"
    
    # Validate model_type
    if cfg["model_type"] not in VALID_MODEL_TYPES:
        return False, f"Invalid model_type: {cfg['model_type']} (must be {VALID_MODEL_TYPES})"
    
    # Validate feature_set
    if not isinstance(cfg["feature_set"], list) or len(cfg["feature_set"]) == 0:
        return False, "feature_set must be a non-empty list"
    
    unknown_features = [f for f in cfg["feature_set"] if f not in FEATURE_REGISTRY]
    if unknown_features:
        return False, f"Unknown features: {unknown_features}"
    
    # Validate thresholds
    if not (0.0 <= cfg["entry_threshold"] <= 1.0):
        return False, f"entry_threshold {cfg['entry_threshold']} not in [0, 1]"
    if not (0.0 <= cfg["invalidation_threshold"] <= 1.0):
        return False, f"invalidation_threshold {cfg['invalidation_threshold']} not in [0, 1]"
    
    # Validate params
    params = cfg["params"]
    if "learning_rate" in params and params["learning_rate"] <= 0:
        return False, f"learning_rate {params['learning_rate']} must be > 0"
    if "max_depth" in params and params["max_depth"] <= 0:
        return False, f"max_depth {params['max_depth']} must be > 0"
    if "n_estimators" in params and params["n_estimators"] <= 0:
        return False, f"n_estimators {params['n_estimators']} must be > 0"
    
    return True, None


def main():
    """Validate all variant configs in CONFIG_DIR."""
    if not CONFIG_DIR.exists():
        print(f"❌ Config directory not found: {CONFIG_DIR}")
        return 1
    
    config_files = sorted(CONFIG_DIR.glob("variant-*.json"))
    if not config_files:
        print(f"❌ No variant-*.json files found in {CONFIG_DIR}")
        return 1
    
    print(f"🔍 Validating {len(config_files)} variant configs...\n")
    
    valid_count = 0
    errors = []
    
    for config_path in config_files:
        is_valid, error_msg = validate_config(config_path)
        
        if is_valid:
            # Load for summary
            with open(config_path) as f:
                cfg = json.load(f)
            print(f"✅ {config_path.name}")
            print(f"   {cfg['direction']} | {cfg['model_type']} | {len(cfg['feature_set'])} features | {cfg['description'][:60]}...")
            valid_count += 1
        else:
            print(f"❌ {config_path.name}: {error_msg}")
            errors.append((config_path.name, error_msg))
    
    print(f"\n{'='*80}")
    if valid_count == len(config_files):
        print(f"✅ ALL {valid_count}/{len(config_files)} configs valid!")
        return 0
    else:
        print(f"❌ {valid_count}/{len(config_files)} configs valid, {len(errors)} errors:")
        for name, err in errors:
            print(f"   - {name}: {err}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
