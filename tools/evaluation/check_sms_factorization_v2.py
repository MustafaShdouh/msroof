"""Audit the fresh comparison without training or text encoding."""
import json
from training.transactions import factorization_comparison_v2 as trial
from tools.evaluation.check_sms_factorization_comparison import check

if __name__ == "__main__":
    if trial.FAILURE.exists():
        raise RuntimeError("Fresh comparison failed; preserve failure/resource evidence, no retry")
    print(json.dumps(check(trial)))
