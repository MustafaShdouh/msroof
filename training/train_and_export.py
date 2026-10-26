import json
import argparse
import os
import re
import sys
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from training.corpus_io import DATASET, load_development_split, write_immutable, sha256
from src.python.preprocessing import preprocess_message

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

def preprocess_text(text):
    return preprocess_message(text)

def main():
    parser = argparse.ArgumentParser(description="Legacy TF-IDF experiment on sanitized grouped data; export math remains unsuitable for runtime promotion")
    parser.add_argument("--output", type=Path, help="New candidate JSON output; existing files cannot be replaced")
    parser.add_argument("--check-inputs", action="store_true")
    args = parser.parse_args()
    dataset_path = DATASET
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    train_indices, validation_indices, split = load_development_split(data)
    if args.check_inputs:
        print(f"Sanitized legacy-experiment inputs valid: {len(train_indices)} train / {len(validation_indices)} validation; no fitting")
        return
    if args.output is None:
        parser.error("--output is required; the active runtime model cannot be overwritten")
    export_path = args.output.resolve()
    if export_path.exists():
        raise ValueError("Output exists; choose a new candidate path")
    texts = []
    binary_labels = [] # 1 = VALID TRANSACTION (DEBIT/CREDIT), 0 = NOISE/OTP/DECLINED/PROMO/CHAT
    type_labels = []   # 1 = CREDIT (Income), 0 = DEBIT (Expense), -1 = None
    detailed_labels = []

    for item in data:
        cleaned = preprocess_text(item["text"])
        texts.append(cleaned)
        label = item["label"]
        detailed_labels.append(label)

        if label in ["TRANSACTION_DEBIT", "TRANSACTION_CREDIT"]:
            binary_labels.append(1)
            type_labels.append(1 if label == "TRANSACTION_CREDIT" else 0)
        else:
            binary_labels.append(0)
            type_labels.append(-1)

    print(f"Total dataset size: {len(texts)}")
    print(f"Transactions: {sum(binary_labels)}, Non-transactions (Noise/OTP/Declined): {len(binary_labels) - sum(binary_labels)}")

    # 1. Train / Test Split
    X_train_raw = [texts[i] for i in train_indices]
    X_test_raw = [texts[i] for i in validation_indices]
    y_train = [binary_labels[i] for i in train_indices]
    y_test = [binary_labels[i] for i in validation_indices]
    det_test = [detailed_labels[i] for i in validation_indices]

    # 2. Vectorization (Word unigrams & bigrams, capturing Arabic and English)
    # Using token_pattern that supports Arabic Unicode characters
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.95,
        token_pattern=r'(?u)\b[\w\*\.\-]+|\b\w+\b'
    )
    X_train = vectorizer.fit_transform(X_train_raw)
    X_test = vectorizer.transform(X_test_raw)

    print(f"\nVocabulary size: {len(vectorizer.vocabulary_)} features")

    # 3. Model 1: Is Transaction Classifier (Logistic Regression with uncalibrated scores)
    clf = LogisticRegression(C=5.0, max_iter=1000, random_state=42)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    print(f"\n================ MODEL EVALUATION ================")
    print(f"Test Set Accuracy: {acc * 100:.2f}%")
    print("\nClassification Report (0 = Drop/Ignore, 1 = Log Transaction):")
    print(classification_report(y_test, y_pred, target_names=["Drop / Noise", "Valid Transaction"]))

    # Check breakdown per detailed label to see if any OTPs or chats leaked into transactions
    print("\nAccuracy Breakdown by Sub-Category:")
    leakage = 0
    cat_counts = {}
    cat_correct = {}
    for actual_cat, pred_binary, true_binary in zip(det_test, y_pred, y_test):
        cat_counts[actual_cat] = cat_counts.get(actual_cat, 0) + 1
        if pred_binary == true_binary:
            cat_correct[actual_cat] = cat_correct.get(actual_cat, 0) + 1
        else:
            if pred_binary == 1 and true_binary == 0:
                leakage += 1
                print(f"  [FALSE POSITIVE LEAK] Category '{actual_cat}' was incorrectly predicted as TRANSACTION!")

    for cat in sorted(cat_counts.keys()):
        correct = cat_correct.get(cat, 0)
        total = cat_counts[cat]
        print(f" - {cat:20s}: {correct}/{total} ({correct/total*100:.1f}%)")

    print(f"\nTotal False Positive Leaks on Test Set: {leakage}")

    # Top Features for Transaction vs Noise
    feature_names = vectorizer.get_feature_names_out()
    coefs = clf.coef_[0]
    top_pos_idx = np.argsort(coefs)[-15:]
    top_neg_idx = np.argsort(coefs)[:15]

    print("\nTop 10 Strongest Signals FOR Transaction:")
    for idx in reversed(top_pos_idx[-10:]):
        print(f"  + {feature_names[idx]:20s} (weight: +{coefs[idx]:.3f})")

    print("\nTop 10 Strongest Signals FOR Rejection (Noise/OTP/Declined):")
    for idx in top_neg_idx[:10]:
        print(f"  - {feature_names[idx]:20s} (weight: {coefs[idx]:.3f})")

    # 4. Model 2: Transaction Type Classifier (DEBIT vs CREDIT)
    tx_indices = [i for i in train_indices if binary_labels[i] == 1]
    X_tx_raw = [texts[i] for i in tx_indices]
    y_tx_type = [type_labels[i] for i in tx_indices] # 1 = CREDIT, 0 = DEBIT

    X_tx = vectorizer.transform(X_tx_raw)
    clf_type = LogisticRegression(C=5.0, max_iter=1000, random_state=42)
    clf_type.fit(X_tx, y_tx_type)

    # 5. Export lightweight JSON package for React Native
    # Convert weights to dictionary format for O(1) lookup in TypeScript
    vocab = vectorizer.vocabulary_
    idf_arr = vectorizer.idf_.tolist()
    tx_coefs = clf.coef_[0].tolist()
    tx_intercept = float(clf.intercept_[0])

    type_coefs = clf_type.coef_[0].tolist()
    type_intercept = float(clf_type.intercept_[0])

    # Store compact model dictionary: { token: { idf: x, w_tx: y, w_type: z } }
    model_export = {
        "metadata": {
            "name": "Masroof ML Transaction Classifier",
            "version": "legacy-sanitized-experiment",
            "scope": "Synthetic grouped development only; TF-IDF export/runtime math not reconciled; do not promote",
            "datasetSha256": sha256(DATASET),
            "splitSha256": sha256(ROOT / "data/training/splits/transaction_direction_sanitized_v1.json"),
            "language": "Arabic + English (Jordanian Ecosystem)",
            "accuracy": f"{acc * 100:.2f}%",
            "intercept_tx": tx_intercept,
            "intercept_credit": type_intercept
        },
        "features": {}
    }

    for token, idx in vocab.items():
        # Only export features that have meaningful weight to keep size tiny
        w_tx = round(tx_coefs[idx], 4)
        w_type = round(type_coefs[idx], 4)
        idf_val = round(idf_arr[idx], 4)
        if abs(w_tx) > 0.05 or abs(w_type) > 0.05:
            model_export["features"][token] = [idf_val, w_tx, w_type]

    write_immutable(export_path, json.dumps(model_export, ensure_ascii=False, separators=(',', ':')))

    file_size_kb = os.path.getsize(export_path) / 1024
    print(f"\n================ EXPORT COMPLETE ================")
    print(f"Exported model file: {export_path}")
    print(f"Number of active features exported: {len(model_export['features'])}")
    print(f"File size: {file_size_kb:.2f} KB (Lightning-fast for React Native!)")

if __name__ == "__main__":
    main()
