# Moonshot long label audit

Date: 2026-03-14 UTC

## Scope

- Verify 10 random `long label=1` rows for the current label config (`tp_pct=0.15`, `sl_pct=0.05`, `horizon_bars=42`).
- Compare realized closed-position PnL by direction.
- Decide whether long labels are broken or whether long should be disabled operationally.

## Label distribution

Current-config labels are balanced:

- Long: `231,924 / 1,760,666 = 13.17%` positive
- Short: `236,315 / 1,765,232 = 13.39%` positive

Important caveat: the `labels` table contains two parameter sets:

- Current: `tp=15%`, `sl=5%`, `horizon=42`
- Legacy: `tp=30%`, `sl=10%`, `horizon=42`

Any audit query that does not filter by `tp_pct/sl_pct/horizon_bars` can mix the two populations and produce false mismatches.

## Manual verification

All 10 sampled rows from the current config replayed correctly: price hit `+15%` before `-5%`, with no sampled same-bar TP/SL ambiguity.

| # | Symbol | Entry TS (UTC) | First hit bar | First hit TS (UTC) | Result |
|---|---|---|---:|---|---|
| 1 | DOGE-USDT | 2025-03-22T08:00:00+00:00 | 22 | 2025-03-26T00:00:00+00:00 | TP first |
| 2 | ADA-USDT | 2024-11-06T00:00:00+00:00 | 12 | 2024-11-08T00:00:00+00:00 | TP first |
| 3 | SNX-USDT | 2025-01-14T12:00:00+00:00 | 20 | 2025-01-17T20:00:00+00:00 | TP first |
| 4 | ETC-USDT | 2025-02-28T08:00:00+00:00 | 14 | 2025-03-02T16:00:00+00:00 | TP first |
| 5 | BLUR-USDT | 2024-09-16T00:00:00+00:00 | 17 | 2024-09-18T20:00:00+00:00 | TP first |
| 6 | ZORA-USDT | 2025-08-10T16:00:00+00:00 | 2 | 2025-08-11T00:00:00+00:00 | TP first |
| 7 | ATH-USDT | 2024-11-05T12:00:00+00:00 | 9 | 2024-11-07T00:00:00+00:00 | TP first |
| 8 | TREE-USDT | 2026-01-22T16:00:00+00:00 | 11 | 2026-01-24T12:00:00+00:00 | TP first |
| 9 | XLM-USDT | 2025-07-08T12:00:00+00:00 | 6 | 2025-07-09T12:00:00+00:00 | TP first |
| 10 | SUSHI-USDT | 2025-01-14T08:00:00+00:00 | 7 | 2025-01-15T12:00:00+00:00 | TP first |

## Realized PnL

Closed positions in `positions`:

- Long: `0` closed positions
- Short: `21,850` closed positions, average PnL `-0.00687`, total PnL `-150.09337`

Closed champion positions:

- Long: `0`
- Short: `10`, average PnL `-0.21618`, total PnL `-2.16175`

## Model registry evidence

- Active champions: short only (`1`), long has `0`
- Active forward-test models: short only (`146`), long has `0`
- Backtest gate-like passes (`bt_pf>=1.0`, `bt_trades>=50`, `bt_precision>=0.20`):
  - Long: `0 / 441`
  - Short: `77 / 457`

Interpretation: long is not failing because the positive labels are obviously incorrect. Long is failing because the current pipeline is not producing competitive long models.

## Recommendation

Disable long operationally for now.

Reasoning:

- Current-config long labels passed the manual audit.
- There are no active long FT models, no active long champion, and no realized long closed positions.
- Making `LONG_DISABLED=True` explicit in config prevents accidental long activation before a dedicated long-model rebuild or relabel study.

## Follow-up

- If long is revisited, rerun the audit with the query explicitly filtered to `tp_pct=0.15`, `sl_pct=0.05`, `horizon_bars=42`.
- If long model development resumes, inspect why long backtests have `0` gate passes despite balanced labels.
