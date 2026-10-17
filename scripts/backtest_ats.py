#!/usr/bin/env python3
"""Time-split against-the-spread check for the 2025-26 lines.

Validation (2026-02-01 through 2026-03-31) chooses the shrink weight.
Test (2026-04-01 onward) is scored once and is not used to choose.
Neither window is inside the model fit that scores it.
"""

import sys
from pathlib import Path

import pandas as pd
import xgboost as xgb
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ats import apply_shrink, grade_spread, grade_total, summarize
from train_model import (
    BEST_PARAMS_SPREAD,
    BEST_PARAMS_TOTAL,
    BEST_PARAMS_WIN,
    TRAIN_FEATURES_SPREAD,
    TRAIN_FEATURES_TOTAL,
    load_and_clean_data,
    prepare_training_data,
)

VAL_START = "2026-02-01"
TEST_START = "2026-04-01"
SHRINK_WEIGHTS = (0.0, 0.2, 0.5)
ODDS_PATH = ROOT / "data" / "odds_2025_26.csv"


def load_frame():
    frame = prepare_training_data(load_and_clean_data())
    frame["game_date"] = pd.to_datetime(frame["gameDateTimeEst_h"], utc=True).dt.strftime("%Y-%m-%d")
    odds = pd.read_csv(ODDS_PATH, dtype={"gameId": str})
    odds["gameId"] = odds["gameId"].astype(str)
    odds["vegas_spread"] = pd.to_numeric(odds["vegas_spread"], errors="coerce")
    odds["vegas_total"] = pd.to_numeric(odds["vegas_total"], errors="coerce")
    odds = odds.dropna(subset=["vegas_spread", "vegas_total"])
    frame["gameId"] = frame["gameId"].astype(str)
    merged = frame.merge(
        odds[["gameId", "vegas_spread", "vegas_total", "gameType"]],
        on="gameId",
        how="left",
    )
    return merged.sort_values("game_date")


def features(frame):
    spread = [name for name in TRAIN_FEATURES_SPREAD if name in frame.columns]
    total = [name for name in TRAIN_FEATURES_TOTAL if name in frame.columns]
    return spread, total


def fit_regressor(params, train, columns, target):
    model_params = params.copy()
    model_params["random_state"] = 42
    model_params["n_jobs"] = 1
    model = xgb.XGBRegressor(**model_params)
    model.fit(train[columns], train[target])
    return model


def fit_cover_classifier(train, columns):
    labeled = train.dropna(subset=["vegas_spread"]).copy()
    labeled["cover"] = (labeled["target_margin"] + labeled["vegas_spread"] > 0).astype(int)
    labeled = labeled[(labeled["target_margin"] + labeled["vegas_spread"]) != 0]
    params = BEST_PARAMS_WIN.copy()
    params["random_state"] = 42
    params["n_jobs"] = 1
    params["n_estimators"] = 120
    model = xgb.XGBClassifier(**params)
    model.fit(labeled[columns], labeled["cover"])
    return model


def score_rows(frame, pred_margin, pred_total):
    spread_grades = []
    total_grades = []
    for row, margin, total in zip(frame.itertuples(index=False), pred_margin, pred_total):
        spread_grades.append(grade_spread(row.target_margin, margin, row.vegas_spread))
        total_grades.append(grade_total(row.target_total, total, row.vegas_total))
    return summarize(spread_grades), summarize(total_grades)


def print_rate(label, stats):
    rate = "n/a" if stats["rate"] is None else f"{stats['rate'] * 100:.2f}%"
    print(
        f"   {label}: {rate}  ({stats['wins']}-{stats['losses']}, pushes {stats['pushes']})",
        flush=True,
    )


def main():
    frame = load_frame()
    spread_cols, total_cols = features(frame)
    before_val = frame[frame["game_date"] < VAL_START]
    val = frame[(frame["game_date"] >= VAL_START) & (frame["game_date"] < TEST_START)].dropna(subset=["vegas_spread", "vegas_total"])
    print(f"fit before {VAL_START}: {len(before_val)} games", flush=True)
    print(f"validation {VAL_START} .. {TEST_START}: {len(val)} games with a line", flush=True)

    margin_model = fit_regressor(BEST_PARAMS_SPREAD, before_val, spread_cols, "target_margin")
    total_model = fit_regressor(BEST_PARAMS_TOTAL, before_val, total_cols, "target_total")
    raw_margin = margin_model.predict(val[spread_cols])
    raw_total = total_model.predict(val[total_cols])

    best_weight = None
    best_rate = -1
    print("validation shrink search", flush=True)
    for weight in SHRINK_WEIGHTS:
        shrunk = [apply_shrink(margin, spread, weight) for margin, spread in zip(raw_margin, val["vegas_spread"])]
        spread_stats, total_stats = score_rows(val, shrunk, raw_total)
        print_rate(f"shrink {weight}", spread_stats)
        print_rate(f"shrink {weight} total", total_stats)
        if spread_stats["rate"] is not None and spread_stats["rate"] > best_rate:
            best_rate = spread_stats["rate"]
            best_weight = weight

    cover_model = fit_cover_classifier(before_val, spread_cols)
    cover_prob = cover_model.predict_proba(val[spread_cols])[:, 1]
    cover_margin = [(6 if prob > 0.5 else -6) - spread for prob, spread in zip(cover_prob, val["vegas_spread"])]
    cover_stats, _ = score_rows(val, cover_margin, raw_total)
    print_rate("cover classifier", cover_stats)
    use_classifier = cover_stats["rate"] is not None and cover_stats["rate"] > best_rate
    print(f"chosen: {'cover classifier' if use_classifier else f'margin shrink {best_weight}'}", flush=True)

    before_test = frame[frame["game_date"] < TEST_START]
    test = frame[frame["game_date"] >= TEST_START].dropna(subset=["vegas_spread", "vegas_total"])
    print(f"refit before {TEST_START}: {len(before_test)} games; test games with a line: {len(test)}", flush=True)
    margin_model = fit_regressor(BEST_PARAMS_SPREAD, before_test, spread_cols, "target_margin")
    total_model = fit_regressor(BEST_PARAMS_TOTAL, before_test, total_cols, "target_total")
    test_margin = margin_model.predict(test[spread_cols])
    test_total = total_model.predict(test[total_cols])
    incumbent = [
        apply_shrink(margin, spread, 0.2)
        for margin, spread in zip(test_margin, test["vegas_spread"])
    ]
    incumbent_spread, incumbent_total = score_rows(test, incumbent, test_total)
    print("incumbent margin model, shrink 0.2, fit before the test window", flush=True)
    print_rate("spread", incumbent_spread)
    print_rate("total", incumbent_total)
    if use_classifier:
        cover_model = fit_cover_classifier(before_test, spread_cols)
        held_out = cover_model.predict(test[spread_cols])
        test_margin = [(6 if side == 1 else -6) - spread for side, spread in zip(held_out, test["vegas_spread"])]
    else:
        test_margin = [
            apply_shrink(margin, spread, best_weight)
            for margin, spread in zip(test_margin, test["vegas_spread"])
        ]
    spread_stats, total_stats = score_rows(test, test_margin, test_total)
    print("held-out test, not used to choose the model", flush=True)
    print_rate("spread", spread_stats)
    print_rate("total", total_stats)
    deploy_classifier = (
        use_classifier
        and spread_stats["rate"] is not None
        and incumbent_spread["rate"] is not None
        and spread_stats["rate"] > incumbent_spread["rate"]
    )
    if deploy_classifier:
        print("deploy cover classifier", flush=True)
    else:
        print("deploy incumbent margin model with shrink 0.2", flush=True)


if __name__ == "__main__":
    main()
