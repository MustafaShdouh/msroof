import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.python.verify_engine import MasroofEngine

engine = MasroofEngine()

test_cases = [
    # 1. Dual-Currency FX Transactions
    {
        "name": "FX: Amazon USD billed JOD",
        "sender": "ArabiBank",
        "body": "Purchase of USD 50.00 billed as JOD 35.50 on card *1234 at AMAZON. Avail bal JOD 200.",
        "exp": {
            "isValidTransaction": True,
            "amount": 35.50,
            "currency": "JOD",
            "originalAmount": 50.00,
            "originalCurrency": "USD",
            "exchangeRate": 0.71,
            "merchantOrParty": "AMAZON"
        }
    },
    {
        "name": "FX: Steam Games JOD for USD",
        "sender": "CapitalBank",
        "body": "Billed JOD 14.50 for USD 20.00 purchase on card *1234 at STEAM GAMES. Balance JOD 100.",
        "exp": {
            "isValidTransaction": True,
            "amount": 14.50,
            "currency": "JOD",
            "originalAmount": 20.00,
            "originalCurrency": "USD",
            "exchangeRate": 0.725,
            "merchantOrParty": "STEAM GAMES"
        }
    },
    {
        "name": "FX: Apple Store USD in AED",
        "sender": "ENBD",
        "body": "Transaction of USD 100.00 (AED 367.50) at APPLE STORE with card *5555.",
        "exp": {
            "isValidTransaction": True,
            "amount": 367.50,
            "currency": "AED",
            "originalAmount": 100.00,
            "originalCurrency": "USD",
            "exchangeRate": 3.675,
            "merchantOrParty": "APPLE STORE"
        }
    },

    # 2. South Asian & Swiss Number Formatting
    {
        "name": "Indian Lakhs: HDFC Bank",
        "sender": "HDFCBK",
        "body": "Your account *9876 debited by INR 1,50,000.00 on 20-Oct-26 at RELIANCE DIGITAL. Avail bal INR 2,45,000.00",
        "exp": {
            "isValidTransaction": True,
            "amount": 150000.00,
            "currency": "INR",
            "balance": 245000.00,
            "merchantOrParty": "RELIANCE DIGITAL"
        }
    },
    {
        "name": "Swiss Apostrophe: UBS",
        "sender": "UBS",
        "body": "Purchase of CHF 2'450.75 on card *3322 at ROLEX BOUTIQUE. Bal CHF 15'200.00",
        "exp": {
            "isValidTransaction": True,
            "amount": 2450.75,
            "currency": "CHF",
            "balance": 15200.00,
            "merchantOrParty": "ROLEX BOUTIQUE"
        }
    },

    # 3. Anchored Structural Chunker (Prepositions inside proper merchant names)
    {
        "name": "Merchant: Farm To Table Cafe",
        "sender": "Chase",
        "body": "Purchase of $30.00 at FARM TO TABLE CAFE on card ending 1234",
        "exp": {
            "isValidTransaction": True,
            "amount": 30.00,
            "currency": "USD",
            "merchantOrParty": "FARM TO TABLE CAFE"
        }
    },
    {
        "name": "Merchant: Subway At The Mall",
        "sender": "WellsFargo",
        "body": "Purchase of $12.00 at SUBWAY AT THE MALL on card ending 1234",
        "exp": {
            "isValidTransaction": True,
            "amount": 12.00,
            "currency": "USD",
            "merchantOrParty": "SUBWAY AT THE MALL"
        }
    },
    {
        "name": "Merchant: Door To Door Logistics",
        "sender": "BOA",
        "body": "Purchase of $50.00 at DOOR TO DOOR LOGISTICS on card ending 1234",
        "exp": {
            "isValidTransaction": True,
            "amount": 50.00,
            "currency": "USD",
            "merchantOrParty": "DOOR TO DOOR LOGISTICS"
        }
    },
    {
        "name": "Merchant: Arabic Restaurant from Home",
        "sender": "BankAlEtihad",
        "body": "شراء بمبلغ 20 دينار لدى مطعم من البيت بالبطاقة *1234",
        "exp": {
            "isValidTransaction": True,
            "amount": 20.00,
            "currency": "JOD",
            "merchantOrParty": "مطعم من البيت"
        }
    }
]

print("=" * 70)
print("VERIFYING NEW ARCHITECTURAL CAPABILITIES (PYTHON ENGINE)")
print("=" * 70)

all_passed = True
for tc in test_cases:
    res = engine.predict(tc["sender"], tc["body"])
    exp = tc["exp"]
    data = res.get("data") or {}

    errors = []
    if res["isValidTransaction"] != exp["isValidTransaction"]:
        errors.append(f"Valid: got {res['isValidTransaction']} exp {exp['isValidTransaction']}")
    if "amount" in exp and data.get("amount") != exp["amount"]:
        errors.append(f"Amount: got {data.get('amount')} exp {exp['amount']}")
    if "currency" in exp and data.get("currency") != exp["currency"]:
        errors.append(f"Currency: got {data.get('currency')} exp {exp['currency']}")
    if "originalAmount" in exp and data.get("originalAmount") != exp["originalAmount"]:
        errors.append(f"OrigAmount: got {data.get('originalAmount')} exp {exp['originalAmount']}")
    if "originalCurrency" in exp and data.get("originalCurrency") != exp["originalCurrency"]:
        errors.append(f"OrigCurrency: got {data.get('originalCurrency')} exp {exp['originalCurrency']}")
    if "exchangeRate" in exp and data.get("exchangeRate") != exp["exchangeRate"]:
        errors.append(f"ExchangeRate: got {data.get('exchangeRate')} exp {exp['exchangeRate']}")
    if "merchantOrParty" in exp and data.get("merchantOrParty") != exp["merchantOrParty"]:
        errors.append(f"Merchant: got '{data.get('merchantOrParty')}' exp '{exp['merchantOrParty']}'")
    if "balance" in exp and data.get("balance") != exp["balance"]:
        errors.append(f"Balance: got {data.get('balance')} exp {exp['balance']}")

    if not errors:
        print(f"  [PASS] {tc['name']}")
    else:
        all_passed = False
        print(f"  [FAIL] {tc['name']}")
        for err in errors:
            print(f"         >>> {err}")

# Milestone 2: local merchant corrections must be normalized, persistent, and isolated.
MasroofEngine.load_user_overlay('{}')
baseline_category = MasroofEngine.classify_category('Starbucks Cafe', 'purchase at Starbucks Cafe')
baseline_passes = baseline_category['category'] == 'Dining & Food Delivery'
print(f"  [{'PASS' if baseline_passes else 'FAIL'}] Overlay baseline classification")
all_passed = all_passed and baseline_passes

MasroofEngine.apply_correction(' STARBUCKS-CAFE ', 'Shopping & Retail')
corrected_category = MasroofEngine.classify_category('starbucks cafe', 'purchase at Starbucks Cafe')
correction_passes = corrected_category['category'] == 'Shopping & Retail' and corrected_category['confidence'] == 1.0
print(f"  [{'PASS' if correction_passes else 'FAIL'}] Overlay correction override")
all_passed = all_passed and correction_passes

persisted_overlay = json.dumps(MasroofEngine.export_user_overlay())
MasroofEngine.load_user_overlay('{}')
MasroofEngine.load_user_overlay(persisted_overlay)
restored_category = MasroofEngine.classify_category('STARBUCKS CAFE', 'purchase at Starbucks Cafe')
persistence_passes = restored_category['category'] == 'Shopping & Retail' and restored_category['confidence'] == 1.0
print(f"  [{'PASS' if persistence_passes else 'FAIL'}] Overlay export and load")
all_passed = all_passed and persistence_passes

unrelated_category = MasroofEngine.classify_category('Starbucks Cafe Downtown', 'purchase at Starbucks Cafe Downtown')
isolation_passes = unrelated_category['category'] == 'Dining & Food Delivery'
print(f"  [{'PASS' if isolation_passes else 'FAIL'}] Overlay merchant isolation")
all_passed = all_passed and isolation_passes
MasroofEngine.load_user_overlay('{}')

print("\nResult:", "ALL NEW ARCHITECTURAL TESTS PASSED!" if all_passed else "SOME TESTS FAILED!")
if not all_passed:
    sys.exit(1)
