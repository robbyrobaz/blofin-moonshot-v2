"""Helpers for safe entry threshold selection."""

import config


def effective_entry_threshold(
    entry_threshold: float | int | None,
    invalidation_threshold: float | int | None = None,
) -> float:
    """Apply entry threshold cap (ENTRY_THRESHOLD_FLOOR is actually a ceiling/max).

    BUG FIX 2026-03-15: ENTRY_THRESHOLD_FLOOR=0.50 is meant to LOWER thresholds, not raise them.
    Despite the name "floor", it acts as a MAXIMUM/CAP on entry thresholds.

    - Models created with entry_threshold=0.70 should be capped at 0.50
    - Use min() to apply the cap: min(0.70, 0.50) = 0.50
    - Invalidation_threshold is NOT part of entry filtering (has grace period)

    Before: max(0.50, 0.70, 0.75) = 0.75 (TOO HIGH - long models got 0 trades)
    After:  min(0.70, 0.50) = 0.50 (CORRECT - enables long entries)
    """
    model_threshold = float(entry_threshold) if entry_threshold is not None else 1.0
    # Cap at ENTRY_THRESHOLD_FLOOR (despite name, acts as maximum)
    return min(model_threshold, config.ENTRY_THRESHOLD_FLOOR)
