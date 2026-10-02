#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.candidate_ranking import FEATURE_NAMES, MODEL_SCHEMA, feature_vector  # noqa: E402


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def stable_bucket(org: str, domain: str) -> int:
    digest = hashlib.sha256(f"{org}|{domain}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % 10


def resolved_label(status: str, identity: dict) -> int | None:
    if status == "available":
        identity_status = str(identity.get("status") or "")
        if identity.get("publishable") and identity_status == "exact":
            return 1
        if identity_status in {"related_or_uncertain", "review", "ambiguous", "blocked", "wrong_company"}:
            return 0
    if status == "not_found":
        return 0
    return None


def collect_h1a(enriched_path: Path, predictions_path: Path) -> list[dict]:
    profiles = {str(row.get("organisation_number")): row for row in read_jsonl(enriched_path)}
    examples: list[dict] = []
    for prediction in read_jsonl(predictions_path):
        org = str(prediction.get("organisation_number") or "")
        profile = profiles.get(org)
        if not profile:
            continue
        for candidate in prediction.get("candidate_results") or []:
            domain = str(candidate.get("domain") or "").strip().casefold()
            label = resolved_label(str(candidate.get("fetch_status") or ""), candidate.get("identity") or {})
            if not domain or label is None:
                continue
            examples.append({"profile": profile, "domain": domain, "label": label, "source": "h1a_registry_email"})
    return examples


def collect_h1d(path: Path) -> list[dict]:
    examples: list[dict] = []
    for profile in read_jsonl(path):
        discovery = (profile.get("evidence") or {}).get("website_discovery_zero_cost") or {}
        candidate = (profile.get("evidence") or {}).get("website_discovered_zero_cost") or {}
        domain = str((discovery.get("value") or {}).get("candidate_domain") or "").strip().casefold()
        label = resolved_label(str(candidate.get("status") or ""), (candidate.get("value") or {}).get("identity_assessment") or {})
        if domain and label is not None:
            examples.append({"profile": profile, "domain": domain, "label": label, "source": "h1d_legal_name"})
        email_candidate = (profile.get("evidence") or {}).get("website_email_candidate") or {}
        email_discovery = (profile.get("evidence") or {}).get("website_email_discovery") or {}
        email_domain = str((email_discovery.get("value") or {}).get("candidate_domain") or "").strip().casefold()
        email_label = resolved_label(str(email_candidate.get("status") or ""), (email_candidate.get("value") or {}).get("identity_assessment") or {})
        if email_domain and email_label is not None:
            examples.append({"profile": profile, "domain": email_domain, "label": email_label, "source": "h1d_registry_email"})
    return examples


def dedupe(examples: list[dict]) -> list[dict]:
    chosen: dict[tuple[str, str], dict] = {}
    for item in examples:
        org = str(item["profile"].get("organisation_number") or "")
        key = (org, item["domain"])
        prior = chosen.get(key)
        if prior is None or item["label"] > prior["label"]:
            chosen[key] = item
    return list(chosen.values())


def matrix(examples: list[dict]) -> tuple[list[list[float]], list[int]]:
    x: list[list[float]] = []
    y: list[int] = []
    for item in examples:
        features = feature_vector(item["profile"], {"domain": item["domain"]})
        x.append([float(features[name]) for name in FEATURE_NAMES])
        y.append(int(item["label"]))
    return x, y


def fit_logistic(x: list[list[float]], y: list[int], *, steps: int = 1400, rate: float = 0.08, l2: float = 0.04) -> dict:
    n = len(x)
    d = len(FEATURE_NAMES)
    means = [statistics.fmean(row[j] for row in x) for j in range(d)]
    scales = []
    for j in range(d):
        variance = statistics.fmean((row[j] - means[j]) ** 2 for row in x)
        scales.append(max(math.sqrt(variance), 1e-6))
    zrows = [[(row[j] - means[j]) / scales[j] for j in range(d)] for row in x]
    pos = max(sum(y), 1)
    neg = max(n - sum(y), 1)
    pos_weight = n / (2 * pos)
    neg_weight = n / (2 * neg)
    weights = [0.0] * d
    intercept = 0.0
    for step in range(steps):
        gw = [0.0] * d
        gb = 0.0
        for row, label in zip(zrows, y):
            linear = intercept + sum(w * value for w, value in zip(weights, row))
            linear = max(-30.0, min(30.0, linear))
            prob = 1.0 / (1.0 + math.exp(-linear))
            sample_weight = pos_weight if label else neg_weight
            error = (prob - label) * sample_weight
            gb += error
            for j in range(d):
                gw[j] += error * row[j]
        eta = rate / (1.0 + step / 600.0)
        intercept -= eta * gb / n
        for j in range(d):
            weights[j] -= eta * (gw[j] / n + l2 * weights[j])
    return {
        "intercept": intercept,
        "weights": weights,
        "means": means,
        "scales": scales,
    }


def probability(row: list[float], fitted: dict) -> float:
    z = fitted["intercept"]
    for j, value in enumerate(row):
        z += fitted["weights"][j] * ((value - fitted["means"][j]) / fitted["scales"][j])
    z = max(-30.0, min(30.0, z))
    return 1.0 / (1.0 + math.exp(-z))


def ranking_metrics(examples: list[dict], fitted: dict) -> dict:
    grouped: dict[str, list[tuple[float, int]]] = defaultdict(list)
    for item in examples:
        features = feature_vector(item["profile"], {"domain": item["domain"]})
        row = [float(features[name]) for name in FEATURE_NAMES]
        grouped[str(item["profile"].get("organisation_number") or "")].append((probability(row, fitted), int(item["label"])))
    groups_with_positive = 0
    top1 = 0
    top2 = 0
    for values in grouped.values():
        if not any(label for _, label in values):
            continue
        groups_with_positive += 1
        ranked = sorted(values, reverse=True)
        top1 += int(bool(ranked and ranked[0][1]))
        top2 += int(any(label for _, label in ranked[:2]))
    return {
        "groups_with_positive": groups_with_positive,
        "top1_positive_hit_rate": top1 / groups_with_positive if groups_with_positive else None,
        "top2_positive_hit_rate": top2 / groups_with_positive if groups_with_positive else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the V6c local website-candidate logistic ranker from historical resolved attempts only.")
    parser.add_argument("--h1a-enriched", required=True)
    parser.add_argument("--h1a-predictions", required=True)
    parser.add_argument("--h1d-profiles", required=True)
    parser.add_argument("--model-output", required=True)
    parser.add_argument("--report-output", required=True)
    args = parser.parse_args()

    examples = dedupe([
        *collect_h1a(Path(args.h1a_enriched), Path(args.h1a_predictions)),
        *collect_h1d(Path(args.h1d_profiles)),
    ])
    train = []
    holdout = []
    for item in examples:
        org = str(item["profile"].get("organisation_number") or "")
        (holdout if stable_bucket(org, item["domain"]) >= 8 else train).append(item)
    if not train or not any(item["label"] for item in train) or all(item["label"] for item in train):
        raise RuntimeError("Historical training set lacks both positive and negative resolved attempts")

    x_train, y_train = matrix(train)
    fitted = fit_logistic(x_train, y_train)
    model = {
        "schema": MODEL_SCHEMA,
        "model_id": "website.candidate_rank.ml.v1",
        "algorithm": "local_logistic_regression_gradient_descent",
        "feature_names": FEATURE_NAMES,
        "intercept": fitted["intercept"],
        "weights": {name: fitted["weights"][i] for i, name in enumerate(FEATURE_NAMES)},
        "means": {name: fitted["means"][i] for i, name in enumerate(FEATURE_NAMES)},
        "scales": {name: fitted["scales"][i] for i, name in enumerate(FEATURE_NAMES)},
        "training_examples": len(train),
        "training_positive": sum(y_train),
        "training_negative": len(y_train) - sum(y_train),
        "training_policy": "Historical independently fetched and exact-identity-gated attempts only; source errors and robots blocks are excluded.",
    }
    Path(args.model_output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.model_output).write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    x_hold, y_hold = matrix(holdout) if holdout else ([], [])
    binary_correct = 0
    for row, label in zip(x_hold, y_hold):
        binary_correct += int((probability(row, fitted) >= 0.5) == bool(label))
    report = {
        "resolved_examples_total": len(examples),
        "label_counts": dict(Counter(str(item["label"]) for item in examples)),
        "source_counts": dict(Counter(item["source"] for item in examples)),
        "train_examples": len(train),
        "holdout_examples": len(holdout),
        "holdout_binary_accuracy": binary_correct / len(holdout) if holdout else None,
        "holdout_ranking": ranking_metrics(holdout, fitted),
        "fresh_v6c_data_used": False,
        "optimization_note": "Model selection is decided by fresh-cohort verified websites per charged request, not this offline classification metric.",
    }
    Path(args.report_output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
