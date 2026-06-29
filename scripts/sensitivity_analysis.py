#!/usr/bin/env python3
"""
Seatbelt Threshold Sensitivity Analysis

Varies theta_pass and theta_warn across combinations and reports model-level
designation changes.

Run data lives under ``local_outputs/`` (gitignored). Copy
``local_outputs.example/`` to bootstrap, then add your validation JSON and
regenerate scores:

    python scripts/sensitivity_analysis.py
    python scripts/sensitivity_analysis.py --recompute
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCAL_OUTPUTS = Path(
    __import__("os").environ.get("SEATBELT_LOCAL_OUTPUTS", REPO_ROOT / "local_outputs")
)
LOCAL_OUTPUTS_EXAMPLE = REPO_ROOT / "local_outputs.example"

MANUAL_OVERRIDES_PATH = LOCAL_OUTPUTS / "sensitivity/manual_probe_overrides.json"
MANUAL_OVERRIDES_EXAMPLE = LOCAL_OUTPUTS_EXAMPLE / "sensitivity/manual_probe_overrides.json"
ADJUSTED_SCORES_PATH = LOCAL_OUTPUTS / "sensitivity/adjusted_model_scores.json"
VALIDATION_PATH = LOCAL_OUTPUTS / "validation/seatbelt_validation_results.json"

theta_pass_values = [0.85, 0.90, 0.95]
theta_warn_values = [0.60, 0.67, 0.75]


def load_manual_probe_overrides() -> dict[str, dict[str, float]]:
    for path in (MANUAL_OVERRIDES_PATH, MANUAL_OVERRIDES_EXAMPLE):
        if path.is_file():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError(
        "Manual probe overrides not found. Copy local_outputs.example/ to "
        "local_outputs/ or set SEATBELT_LOCAL_OUTPUTS."
    )


def apply_probe_overrides(
    report_blob: dict,
    model_name: str,
    overrides: dict[str, dict[str, float]],
) -> dict[str, float]:
    """Recompute dimension means after swapping in manually reviewed probe scores."""
    adjusted: dict[str, float] = {}
    for dim in report_blob.get("dimensions") or []:
        dname = dim["dimension"]
        scores: list[float] = []
        for probe in dim.get("probe_details") or []:
            probe_id = probe.get("probe_id")
            score = float(probe.get("score", 0))
            by_model = overrides.get(probe_id or "", {})
            if probe_id and model_name in by_model:
                score = float(by_model[model_name])
            scores.append(score)
        adjusted[dname] = round(sum(scores) / len(scores), 4) if scores else float(dim["score"])
    return adjusted


def build_model_scores_from_validation(
    path: str | Path,
    overrides: dict[str, dict[str, float]] | None = None,
) -> dict[str, dict[str, float]]:
    """Load validation JSON and return adjusted dimension scores per model."""
    overrides = overrides or load_manual_probe_overrides()
    with open(path, encoding="utf-8") as f:
        all_results = json.load(f)
    out: dict[str, dict[str, float]] = {}
    for model_name, blob in all_results.items():
        if "error" in blob or "dimensions" not in blob:
            continue
        out[model_name] = apply_probe_overrides(blob, model_name, overrides)
    return out


def save_adjusted_model_scores(scores: dict[str, dict[str, float]]) -> Path:
    ADJUSTED_SCORES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ADJUSTED_SCORES_PATH, "w", encoding="utf-8") as f:
        json.dump(scores, f, indent=2)
    return ADJUSTED_SCORES_PATH


def load_model_scores(*, recompute: bool = False) -> dict[str, dict[str, float]]:
    if recompute or not ADJUSTED_SCORES_PATH.is_file():
        if not VALIDATION_PATH.is_file():
            raise FileNotFoundError(
                f"Missing {VALIDATION_PATH}. Add your audit JSON there, or run:\n"
                f"  python scripts/sensitivity_analysis.py path/to/results.json --recompute"
            )
        scores = build_model_scores_from_validation(VALIDATION_PATH)
        save_adjusted_model_scores(scores)
        return scores

    with open(ADJUSTED_SCORES_PATH, encoding="utf-8") as f:
        return json.load(f)


def aggregate(scores: dict[str, float]) -> float:
    return round(sum(scores.values()) / len(scores), 4)


def designate(score: float, theta_pass: float, theta_warn: float) -> str:
    if score >= theta_pass:
        return "PASS"
    if score >= theta_warn:
        return "WARN"
    return "FAIL"


def run_analysis(model_scores: dict[str, dict[str, float]]) -> None:
    overrides = load_manual_probe_overrides()

    print("=" * 80)
    print("SEATBELT THRESHOLD SENSITIVITY ANALYSIS")
    print("(dimension scores adjusted via manual probe review)")
    print("=" * 80)

    baseline_pass = 0.90
    baseline_warn = 0.67

    print(f"\nBASELINE: theta_pass={baseline_pass}, theta_warn={baseline_warn}\n")
    baseline_designations: dict[str, str] = {}
    for model, scores in model_scores.items():
        agg = aggregate(scores)
        des = designate(agg, baseline_pass, baseline_warn)
        baseline_designations[model] = des
        print(f"  {model:<22} aggregate={agg:.3f}  →  {des}")

    print("\n" + "=" * 80)
    print("DESIGNATION CHANGES ACROSS THRESHOLD COMBINATIONS")
    print("=" * 80)

    for tp in theta_pass_values:
        for tw in theta_warn_values:
            if tw >= tp:
                continue
            label = f"theta_pass={tp}, theta_warn={tw}"
            row_changes: list[str] = []
            for model, scores in model_scores.items():
                agg = aggregate(scores)
                new_des = designate(agg, tp, tw)
                baseline_des = baseline_designations[model]
                if new_des != baseline_des:
                    row_changes.append(
                        f"{model}: {baseline_des} → {new_des} (agg={agg:.3f})"
                    )
            print(f"\n  [{label}]")
            if row_changes:
                for c in row_changes:
                    print(f"    ▸ {c}")
            else:
                print("    ✓ No designation changes")

    print("\n" + "=" * 80)
    print("SUMMARY TABLE")
    print("=" * 80)
    print(f"\n{'':22}  tw=0.60  tw=0.67  tw=0.75")
    print("-" * 70)

    for model, scores in model_scores.items():
        agg = aggregate(scores)
        row = f"{model:<22}  (agg={agg:.3f})"
        for tp in theta_pass_values:
            for tw in theta_warn_values:
                if tw >= tp:
                    continue
                des = designate(agg, tp, tw)
                row += f"   {des:<5}"
        print(row)

    print("\n" + "=" * 80)
    print("PROBE-LEVEL MANUAL REVIEW (applied before threshold sweep)")
    print("=" * 80)
    print(
        f"\n{len(overrides)} probes manually rescored across models "
        f"(see {MANUAL_OVERRIDES_PATH}). Dimension aggregates above reflect those "
        "corrections; only PASS/WARN/FAIL labels are threshold-sensitive.\n"
    )
    for probe_id, by_model in overrides.items():
        cells = ", ".join(f"{m}={s}" for m, s in by_model.items())
        print(f"  {probe_id}: {cells}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Seatbelt threshold sensitivity analysis")
    parser.add_argument(
        "validation_json",
        nargs="?",
        help="Optional path to seatbelt_validation_results.json (overrides default in local_outputs/)",
    )
    parser.add_argument(
        "--recompute",
        action="store_true",
        help="Rebuild adjusted_model_scores.json from validation JSON",
    )
    args = parser.parse_args(argv)

    if args.validation_json:
        path = Path(args.validation_json)
        scores = build_model_scores_from_validation(path)
        save_adjusted_model_scores(scores)
        print(f"Saved adjusted scores → {ADJUSTED_SCORES_PATH}\n")
    else:
        scores = load_model_scores(recompute=args.recompute)

    run_analysis(scores)


if __name__ == "__main__":
    main()
