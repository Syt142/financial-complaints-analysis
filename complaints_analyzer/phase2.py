"""Leakage-aware product-month baseline; stdlib only, no raw narratives."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import statistics
import time
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]


def months(start, end):
    def ordinal(value):
        import re
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
            raise ValueError(f"Invalid month: {value}")
        year, month = map(int, value.split("-"))
        return year * 12 + month - 1
    left, right = ordinal(start), ordinal(end)
    if left > right:
        raise ValueError("Reversed month range")
    return [f"{i//12:04d}-{i%12+1:02d}" for i in range(left, right + 1)]


def load_counts(path):
    counts = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["table"] != "month_product":
                continue
            month, product = row["key_1"], row["key_2"]
            if month == "(invalid or missing date)":
                continue
            months(month, month)
            key = (month, product)
            if key in counts:
                raise ValueError(f"Duplicate product-month: {key}")
            count = int(row["count"])
            if count < 0:
                raise ValueError("Negative count")
            counts[key] = count
    if not counts:
        raise ValueError("No valid month_product data")
    return counts


def validate_config(cfg):
    boundaries = [cfg[k] for k in ("panel_start", "warmup_end", "development_end", "validation_end", "test_end")]
    for value in boundaries:
        months(value, value)
    if boundaries != sorted(set(boundaries)) or cfg["panel_end"] != cfg["test_end"]:
        raise ValueError("Invalid chronological boundaries")
    if cfg["window"] != 12 or cfg["budget"] < 1 or cfg["scale_floor"] <= 0 or cfg["mad_multiplier"] <= 0:
        raise ValueError("Invalid window, budget or scale")
    if len(months(cfg["panel_start"], cfg["warmup_end"])) != cfg["window"]:
        raise ValueError("Warmup must contain exactly 12 months")
    if not cfg["products"] or len(set(cfg["products"])) != len(cfg["products"]):
        raise ValueError("Products must be unique and nonempty")
    if not cfg["seeds"] or cfg["trials_per_seed"] < 1 or any(x <= 0 for x in cfg["growth_fractions"]):
        raise ValueError("Invalid injection settings")


def split_of(month, cfg):
    if month <= cfg["warmup_end"]:
        return "warmup"
    if month <= cfg["development_end"]:
        return "development"
    if month <= cfg["validation_end"]:
        return "validation"
    return "test"


def score_point(current, history, floor=1.0, multiplier=1.4826):
    if not history or floor <= 0 or multiplier <= 0 or current < 0 or any(x < 0 for x in history):
        raise ValueError("Invalid counts or scale")
    median = statistics.median(history)
    mad = statistics.median(abs(x - median) for x in history)
    scale = max(multiplier * mad, floor)
    return {"baseline": median, "mad": mad, "scale": scale,
            "score": max(0.0, (current - median) / scale),
            "zero_mad": mad == 0, "scale_floored": multiplier * mad < floor}


def score_panel(counts, cfg, end=None):
    """Current row is explicitly excluded; a missing history month is an error."""
    timeline = months(cfg["panel_start"], end or cfg["validation_end"])
    rows = []
    for product in cfg["products"]:
        for i, month in enumerate(timeline):
            if (month, product) not in counts:
                raise ValueError(f"Missing product-month, do not fill zero: {month} {product}")
            if i < cfg["window"]:
                continue
            history = [counts[(m, product)] for m in timeline[i-cfg["window"]:i]]
            row = {"month": month, "product": product, "count": counts[(month, product)],
                   "split": split_of(month, cfg), "history_start": timeline[i-cfg["window"]],
                   "history_end": timeline[i-1]}
            row.update(score_point(row["count"], history, cfg["scale_floor"], cfg["mad_multiplier"]))
            rows.append(row)
    return rows


def top_k(rows, budget):
    if budget < 1:
        raise ValueError("Budget must be positive")
    # Ignore downward/equal changes. Fixed tie-break: month, then product.
    return sorted((r for r in rows if r["score"] > 0),
                  key=lambda r: (-r["score"], r["month"], r["product"]))[:budget]


def injection_experiment(counts, cfg):
    """One independent perturbation per copy; same positions across amplitudes."""
    candidates = sorted((m, p) for m, p in counts
                        if cfg["development_end"] < m <= cfg["validation_end"] and p in cfg["products"])
    clean_rows = [r for r in score_panel(counts, cfg) if r["split"] == "validation"]
    clean_selected = {(r["month"], r["product"]) for r in top_k(clean_rows, cfg["budget"])}
    trials, summaries = [], []
    for seed in cfg["seeds"]:
        rng = random.Random(seed)
        if cfg["trials_per_seed"] > len(candidates):
            raise ValueError("More trials than validation positions")
        for trial, (month, product) in enumerate(rng.sample(candidates, cfg["trials_per_seed"])):
            for fraction in cfg["growth_fractions"]:
                altered = counts.copy()
                original = counts[(month, product)]
                added = max(1, math.ceil(original * fraction))
                altered[(month, product)] = original + added
                scored = [r for r in score_panel(altered, cfg) if r["split"] == "validation"]
                selected = {(r["month"], r["product"]) for r in top_k(scored, cfg["budget"])}
                trials.append({"seed": seed, "trial": trial, "month": month, "product": product,
                               "fraction": fraction, "original": original, "added": added,
                               "baseline_selected": (month, product) in clean_selected,
                               "hit": (month, product) in selected})
    for fraction in cfg["growth_fractions"]:
        rates = [statistics.mean(t["hit"] for t in trials if t["fraction"] == fraction and t["seed"] == seed)
                 for seed in cfg["seeds"]]
        subset = [t for t in trials if t["fraction"] == fraction]
        summaries.append({"fraction": fraction, "hits": sum(t["hit"] for t in subset),
                          "trials": len(subset), "rate": statistics.mean(rates),
                          "already_selected": sum(t["baseline_selected"] for t in subset),
                          "newly_selected": sum(t["hit"] and not t["baseline_selected"] for t in subset),
                          "seed_rate_min": min(rates), "seed_rate_max": max(rates),
                          "seed_rate_sd": statistics.stdev(rates) if len(rates) > 1 else 0})
    return trials, summaries


def write_csv(path, rows):
    if not rows:
        raise ValueError("Cannot export empty table")
    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(input_path, config_path, outdir):
    start = time.perf_counter()
    cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))
    validate_config(cfg)
    counts = load_counts(input_path)
    # Validate test structure but never calculate or rank its scores here.
    panel = []
    for month in months(cfg["panel_start"], cfg["panel_end"]):
        for product in cfg["products"]:
            if (month, product) not in counts:
                raise ValueError(f"Missing product-month: {month}, {product}")
            panel.append({"month": month, "product": product, "count": counts[(month, product)],
                          "split": split_of(month, cfg)})
    # Reconcile independently exported full-run and monthly totals.
    reference_path = Path(input_path).with_name("full_run.json")
    if not reference_path.exists():
        raise ValueError("full_run.json is required next to cross_tables.csv for reconciliation")
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    monthly_total = sum(counts.values())
    invalid = reference["quality"].get("invalid_received", 0)
    if monthly_total + invalid != reference["rows"]:
        raise ValueError("Monthly total does not reconcile with full_run rows")
    scored = [r for r in score_panel(counts, cfg) if r["split"] == "validation"]
    ranked = top_k(scored, cfg["budget"])
    trials, simulations = injection_experiment(counts, cfg)
    outdir = Path(outdir).resolve()
    for protected in (Path(input_path).resolve().parent, Path(config_path).resolve().parent):
        if outdir == protected or outdir in protected.parents:
            raise ValueError("Output must not overwrite inputs")
    outdir.mkdir(parents=True, exist_ok=True)
    write_csv(outdir / "panel.csv", panel)
    write_csv(outdir / "validation_scores.csv", scored)
    write_csv(outdir / "top20.csv", ranked)
    write_csv(outdir / "injection_trials.csv", trials)
    write_csv(outdir / "injection_summary.csv", simulations)
    splits = Counter(r["split"] for r in panel)
    validation_count = sum(r["count"] for r in panel if r["split"] == "validation")
    all_validation_count = sum(n for (m, _), n in counts.items() if cfg["development_end"] < m <= cfg["validation_end"])
    result = {"config": cfg, "source_sha256": digest(input_path), "config_sha256": digest(config_path),
              "full_run_sha256": digest(reference_path), "rows_reconciled": monthly_total + invalid,
              "panel_rows": len(panel), "split_rows": dict(splits),
              "validation_complaints": validation_count, "all_validation_complaints": all_validation_count,
              "validation_coverage": validation_count / all_validation_count,
              "candidate_count": len(scored), "positive_score_count": sum(r["score"] > 0 for r in scored),
              "top20_products": dict(Counter(r["product"] for r in ranked)),
              "zero_mad_count": sum(r["zero_mad"] for r in scored), "injections": simulations,
              "environment": {"python": platform.python_version(), "platform": platform.platform()},
              "elapsed_seconds": round(time.perf_counter() - start, 3),
              "limitations": ["No true anomaly labels; no real accuracy/precision/false-positive-rate.",
                               "Seed ranges describe simulation placement sensitivity, not confidence intervals.",
                               "Snapshot retrospective ranking is not proof of real-time availability.",
                               "Test structure checked, test scoring deferred; annual totals were seen in phase 1."]}
    (outdir / "metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {p.name: digest(p) for p in sorted(outdir.iterdir()) if p.is_file() and p.name != "manifest.json"}
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "evidence/cross_tables.csv")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/phase2.json")
    parser.add_argument("--outdir", type=Path, default=ROOT / "results/phase2")
    args = parser.parse_args()
    result = run(args.input, args.config, args.outdir)
    print(json.dumps({k: result[k] for k in ("panel_rows", "split_rows", "candidate_count", "injections", "elapsed_seconds")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
