import json
import time
import math
import sys
import os
import re
from pathlib import Path

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.python.verify_engine import MasroofEngine

def normalize_str(s):
    if s is None:
        return None
    # normalize spaces and Arabic diacritics
    s = re.sub(r'[\u064B-\u065F\u0670]', '', str(s))
    s = re.sub(r'\s+', ' ', s).strip()
    return s.lower()

def normalize_curr(c):
    c = normalize_str(c)
    if c == '$':
        return 'usd'
    if c == '€':
        return 'eur'
    if c == '£':
        return 'gbp'
    return c

def run_python_suite(test_cases_path=None):
    if test_cases_path is None:
        test_cases_path = ROOT / "tests" / "fixtures" / "test_suite_cases.json"
    with open(test_cases_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    test_cases = data["testCases"] if isinstance(data, dict) and "testCases" in data else data
    engine = MasroofEngine()

    total = len(test_cases)
    tp = 0
    tn = 0
    fp = 0
    fn = 0

    category_stats = {}
    latencies = []

    entity_metrics = {
        "type": {"match": 0, "total": 0},
        "amount": {"match": 0, "total": 0},
        "currency": {"match": 0, "total": 0},
        "merchant": {"match": 0, "total": 0},
        "account_mask": {"match": 0, "total": 0},
        "balance": {"match": 0, "total": 0}
    }

    mismatches = []

    for tc in test_cases:
        tc_id = tc["id"]
        cat = tc["category"]
        sender = tc["sender"]
        body = tc["body"]
        exp = tc["expected"]
        exp_valid = exp["isValidTransaction"]

        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "correct": 0, "fp": 0, "fn": 0}
        category_stats[cat]["total"] += 1

        t0 = time.perf_counter_ns()
        res = engine.predict(sender, body)
        t1 = time.perf_counter_ns()
        latency_ms = (t1 - t0) / 1_000_000.0
        latencies.append(latency_ms)

        pred_valid = res["isValidTransaction"]

        # Classification metrics
        if exp_valid and pred_valid:
            tp += 1
            category_stats[cat]["correct"] += 1
        elif not exp_valid and not pred_valid:
            tn += 1
            category_stats[cat]["correct"] += 1
        elif not exp_valid and pred_valid:
            fp += 1
            category_stats[cat]["fp"] += 1
            mismatches.append({
                "id": tc_id,
                "category": cat,
                "sender": sender,
                "body": body,
                "type": "FALSE_POSITIVE",
                "predicted": res,
                "expected": exp
            })
        elif exp_valid and not pred_valid:
            fn += 1
            category_stats[cat]["fn"] += 1
            mismatches.append({
                "id": tc_id,
                "category": cat,
                "sender": sender,
                "body": body,
                "type": "FALSE_NEGATIVE",
                "predicted": res,
                "expected": exp
            })

        # Entity Extraction Metrics (only evaluated when expected is a valid transaction)
        if exp_valid:
            pred_data = res.get("data") or {}

            # Type
            if exp.get("type"):
                entity_metrics["type"]["total"] += 1
                if pred_data.get("type") == exp.get("type"):
                    entity_metrics["type"]["match"] += 1
                else:
                    mismatches.append({
                        "id": tc_id,
                        "category": cat,
                        "field": "type",
                        "predicted": pred_data.get("type"),
                        "expected": exp.get("type"),
                        "body": body
                    })

            # Amount
            if exp.get("amount") is not None:
                entity_metrics["amount"]["total"] += 1
                pred_amt = pred_data.get("amount")
                if pred_amt is not None and math.isclose(float(pred_amt), float(exp["amount"]), abs_tol=0.001):
                    entity_metrics["amount"]["match"] += 1
                else:
                    mismatches.append({
                        "id": tc_id,
                        "category": cat,
                        "field": "amount",
                        "predicted": pred_amt,
                        "expected": exp.get("amount"),
                        "body": body
                    })

            # Currency
            if exp.get("currency"):
                entity_metrics["currency"]["total"] += 1
                if normalize_curr(pred_data.get("currency")) == normalize_curr(exp.get("currency")):
                    entity_metrics["currency"]["match"] += 1
                else:
                    mismatches.append({
                        "id": tc_id,
                        "category": cat,
                        "field": "currency",
                        "predicted": pred_data.get("currency"),
                        "expected": exp.get("currency")
                    })

            # Merchant / Party
            exp_party = exp.get("merchantOrParty") if exp.get("merchantOrParty") is not None else exp.get("merchant_or_party")
            if exp_party is not None:
                entity_metrics["merchant"]["total"] += 1
                p_m = normalize_str(pred_data.get("merchant_or_party"))
                e_m = normalize_str(exp_party)
                if p_m and (p_m == e_m or e_m in p_m or p_m in e_m):
                    entity_metrics["merchant"]["match"] += 1
                else:
                    mismatches.append({
                        "id": tc_id,
                        "category": cat,
                        "field": "merchant_or_party",
                        "predicted": pred_data.get("merchant_or_party"),
                        "expected": exp_party,
                        "body": body
                    })

            # Account mask
            exp_mask = exp.get("accountMask") if exp.get("accountMask") is not None else exp.get("account_mask")
            if exp_mask is not None:
                entity_metrics["account_mask"]["total"] += 1
                p_a = normalize_str(pred_data.get("account_mask"))
                e_a = normalize_str(exp_mask)
                if p_a and (p_a == e_a or e_a in p_a or p_a in e_a):
                    entity_metrics["account_mask"]["match"] += 1
                else:
                    mismatches.append({
                        "id": tc_id,
                        "category": cat,
                        "field": "account_mask",
                        "predicted": pred_data.get("account_mask"),
                        "expected": exp_mask,
                        "body": body
                    })

            # Balance
            if exp.get("balance") is not None:
                entity_metrics["balance"]["total"] += 1
                p_b = pred_data.get("balance")
                if p_b is not None and math.isclose(float(p_b), float(exp["balance"]), abs_tol=0.001):
                    entity_metrics["balance"]["match"] += 1
                else:
                    mismatches.append({
                        "id": tc_id,
                        "category": cat,
                        "field": "balance",
                        "predicted": p_b,
                        "expected": exp.get("balance"),
                        "body": body
                    })

    latencies.sort()
    mean_lat = sum(latencies) / len(latencies)
    median_lat = latencies[len(latencies) // 2]
    p95_lat = latencies[int(len(latencies) * 0.95)]
    p99_lat = latencies[int(len(latencies) * 0.99)]
    min_lat = min(latencies)
    max_lat = max(latencies)

    accuracy = (tp + tn) / total
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    results = {
        "engine": "Python (verify_engine.py)",
        "total_cases": total,
        "classification": {
            "accuracy": round(accuracy * 100, 2),
            "precision": round(precision * 100, 2),
            "recall": round(recall * 100, 2),
            "f1_score": round(f1 * 100, 2),
            "true_positives": tp,
            "true_negatives": tn,
            "false_positives": fp,
            "false_negatives": fn
        },
        "latency_ms": {
            "mean": round(mean_lat, 4),
            "median": round(median_lat, 4),
            "p95": round(p95_lat, 4),
            "p99": round(p99_lat, 4),
            "min": round(min_lat, 4),
            "max": round(max_lat, 4)
        },
        "entity_extraction": {
            k: {
                "match": v["match"],
                "total": v["total"],
                "accuracy": round((v["match"] / v["total"] * 100), 2) if v["total"] > 0 else 100.0
            }
            for k, v in entity_metrics.items()
        },
        "category_breakdown": category_stats,
        "mismatches": mismatches
    }

    return results

if __name__ == "__main__":
    suite_file = sys.argv[1] if len(sys.argv) > 1 else ROOT / "tests" / "fixtures" / "test_suite_cases.json"
    res = run_python_suite(suite_file)
    print("======================================================")
    print("           MASROOF PYTHON ENGINE TEST REPORT          ")
    print("======================================================")
    print(f"Total Test Cases: {res['total_cases']}")
    print(f"Classification Accuracy: {res['classification']['accuracy']}% (F1: {res['classification']['f1_score']}%)")
    print(f"True Positives: {res['classification']['true_positives']} | True Negatives: {res['classification']['true_negatives']}")
    print(f"FALSE POSITIVES: {res['classification']['false_positives']} (CRITICAL)")
    print(f"FALSE NEGATIVES: {res['classification']['false_negatives']}")
    print("\n--- Latency Performance ---")
    for k, v in res["latency_ms"].items():
        print(f"  {k:8s}: {v:.4f} ms")
    print("\n--- Entity Extraction Accuracy ---")
    for k, v in res["entity_extraction"].items():
        print(f"  {k:15s}: {v['match']}/{v['total']} ({v['accuracy']}%)")
    print("\n--- Category Breakdown ---")
    for cat, stats in sorted(res["category_breakdown"].items()):
        acc = (stats["correct"] / stats["total"]) * 100
        print(f"  {cat:35s}: {stats['correct']}/{stats['total']} ({acc:.1f}%) | FP: {stats['fp']} | FN: {stats['fn']}")
    print(f"\nTotal Mismatches / Imperfections: {len(res['mismatches'])}")
    if res["mismatches"]:
        print("\nTop Mismatches Details:")
        for m in res["mismatches"][:15]:
            print(f"  [{m.get('type') or m.get('field')}] ID: {m['id']} (Cat: {m['category']})")
            print(f"    Expected: {m.get('expected')}")
            print(f"    Got:      {m.get('predicted')}")
    if (res['classification']['false_positives'] > 0 or
            res['classification']['false_negatives'] > 0 or
            res['mismatches']):
        sys.exit(1)
