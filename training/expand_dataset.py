import json
import csv
import random
import os
from pathlib import Path
from datetime import datetime, timedelta

random.seed(42)

# --- REPOSITORIES OF JORDANIAN ENTITIES ---

MERCHANTS = [
    # Supermarkets & Groceries
    "CARREFOUR EXPRESS", "CARREFOUR - CITY MALL", "COZMO SUPERMARKET", "MILES SUPERMARKET",
    "ZAIN MARKET - ROSARY SIST", "SAMEH MALL", "SAFEWAY", "C-TOWN", "FARAH MARKET", "AL-RAWDAH MARKET",
    # Cafes & Restaurants
    "STARBUCKS - ABDALI", "STARBUCKS - TAJ MALL", "TALABAT", "TALABAT GO", "MCDONALDS MECCA ST",
    "BURGER KING", "SHAWERMA REEM", "FIREFLY BURGER", "DUNKIN DONUTS", "CINNABON", "ARABICA CAFE",
    "PAUL BAKERY", "AL-DAYA'A RESTAURANT", "TCHE TCHE CAFE", "BUFFALO WINGS & RINGS",
    # Pharmacies & Health
    "SIR ALDAWAA PH -12 IRBID", "SIR ALDAWAA PH - ABDALI", "PHARMACY 1 MECCA ST",
    "RAWHI PHARMACY", "KHALAF PHARMACY", "MEDICARE LABS", "AL-ISRAA HOSPITAL",
    # Gas Stations
    "MANASEER GAS STATION", "MANASEER OIL & GAS AIRPORT", "TOTAL SHMEISANI", "TOTAL SEVENTH CIRCLE",
    "JOBPETROL UNIVERSITY ST", "JOBPETROL 8TH CIRCLE",
    # Retail, Fashion & Tech
    "ZARA TAJ MALL", "H&M CITY MALL", "PULL & BEAR", "MASSIMO DUTTI", "VIRGIN MEGASTORE",
    "LEADERS CENTER", "SMARTBUY SEVENTH CIRCLE", "DNA APPLE STORE", "IKEA AMMAN",
    # Online Services & Subscriptions
    "AMAZON.COM", "AMAZON EU", "SHEIN.COM", "GOOGLE*GOOGLE ONE MOUNTAIN VIEWUS",
    "NETFLIX.COM", "SPOTIFY P200", "APPLE.COM/BILL", "PLAYSTATION NETWORK", "UBER TRIP AMMAN", "CAREEM RIDE"
]

NAMES = [
    "BAKER NASIM MUSTAFA ELSHDOUH", "RAAD MUNTHER MUNIER ALALI", "ANMAR NIDAL FAWWAZ ALQUDAH",
    "ANMAR ALQUDAH", "OMAR KHALED AL-MASRI", "TARIQ AHMAD ZIAD", "AYA MOHAMMAD AL-KILANI",
    "LAITH KHALED AL-OMARI", "NOUR BASHAR HADDAD", "MAJED SULAIMAN AL-ALI", "HANI MAHMOUD SHANABLEH",
    "AHMAD SALEH AL-KHATIB", "YOUSEF IBRAHIM AL-ALI", "BILAL MAHMOUD OTHMAN", "SAMI KHALIL AL-NAJJAR",
    "RAMI NASSER DAWOOD", "ZEID TAREQ TARAWNEH", "DINA SAMER NABULSI", "FAISAL MAEN AL-MAJALI",
    "RANIA FARES HIJAZI", "HAMZA OMAR AL-ZO'BI", "SALMA MUNIR KASASBEH", "HASHEM WALID QASIM"
]

BILLERS = [
    "مياهنا (Miyahuna)", "شركة الكهرباء الأردنية (JEPCO)", "كهرباء إربد (IDECO)",
    "شركة زين الأردن", "شركة أورنج الأردن", "شركة أمنية للهواتف",
    "الجامعة الأردنية", "جامعة اليرموك", "جامعة العلوم والتكنولوجيا",
    "أمانة عمان الكبرى", "ضريبة الدخل والمبيعات", "المؤسسة العامة للضمان الاجتماعي"
]

CITIES_BRANCHES = [
    "Al-Thaqafa Br", "Shmeisani Branch", "Abdali Branch", "Gardens Br", "Sweifieh Branch",
    "University St Branch", "Irbid City Center", "Aqaba Branch", "Zarqa New Branch", "Salt Branch"
]

# Formatting helpers
def format_amount(val):
    fmt = random.choice([
        f"JOD {val:.3f}",
        f"{val:.3f}JOD",
        f"JOD {val:.2f}",
        f"{val:.2f} JOD",
        f"{val:.3f} د.أ",
        f"{val:.3f} دينار"
    ])
    return fmt

def random_date_str():
    base = datetime(2026, 1, 1) + timedelta(days=random.randint(0, 300), hours=random.randint(0, 23), minutes=random.randint(0, 59))
    date_formats = ["%d/%m/%Y %H:%M", "%d/%m/%Y", "%d/%m %H:%M"]
    return base.strftime(random.choice(date_formats))

def random_account():
    choice = random.choice([1, 2, 3, 4, 5])
    if choice == 1:
        return f"{random.randint(1000, 9999)}*{random.randint(100, 999)}"
    elif choice == 2:
        return f"xxxx{random.randint(100, 999)}"
    elif choice == 3:
        return f"*{random.randint(1000, 9999)}"
    elif choice == 4:
        return f"{random.randint(1000, 9999)}"
    else:
        return f"0175*{random.randint(100, 999)}"

def random_ref():
    return str(random.randint(100000000000, 999999999999))

def random_otp():
    return f"{random.randint(100000, 999999)}"

# --- TEMPLATE DEFINITIONS PER CATEGORY & PROVIDER ---

def generate_samples():
    dataset = []

    # 1. ARAB BANK (DEBIT, CREDIT, OTP, DECLINED, ANNOUNCEMENT)
    for _ in range(60):
        acc = random_account()
        m = random.choice(MERCHANTS)
        amt = round(random.uniform(0.75, 120.0), 3)
        bal = round(random.uniform(10.0, 850.0), 3)
        dt = random_date_str()
        text = f"JO\nYou have a purchase transaction on account {acc} from {m} amount JOD {amt:.3f} on {dt}. Balance JOD {bal:.3f}."
        dataset.append({
            "text": text,
            "label": "TRANSACTION_DEBIT",
            "provider": "ARAB_BANK",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": m,
            "type": "DEBIT"
        })

    for _ in range(35):
        acc = random_account()
        name = random.choice(NAMES)
        amt = round(random.uniform(2.0, 75.0), 3)
        bal = round(random.uniform(15.0, 400.0), 3)
        text = f"JO\nJOD{amt:.3f} has been debited from {acc} to {name} as CliQ transfer Balance {bal:.3f}JOD"
        dataset.append({
            "text": text,
            "label": "TRANSACTION_DEBIT",
            "provider": "ARAB_BANK",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": name,
            "type": "DEBIT"
        })

    for _ in range(35):
        acc = random_account()
        name = random.choice(NAMES)
        amt = round(random.uniform(3.0, 150.0), 3)
        bal = round(random.uniform(20.0, 600.0), 3)
        text = f"JO\nJOD{amt:.3f} has been credited to {acc} from {name} as CliQ transfer Balance {bal:.3f}JOD"
        dataset.append({
            "text": text,
            "label": "TRANSACTION_CREDIT",
            "provider": "ARAB_BANK",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": name,
            "type": "CREDIT"
        })

    for _ in range(25):
        acc = random_account()
        br = random.choice(CITIES_BRANCHES)
        amt = round(random.choice([10, 20, 30, 50, 100, 150, 200]), 3)
        bal = round(random.uniform(5.0, 250.0), 3)
        dt = random_date_str()
        text = f"JO\n{int(amt)}JOD has been debited from your account {acc} as an ATM Withdrawal from {br} on {dt}. Available balance {bal:.3f}.\nREF {random_ref()}"
        dataset.append({
            "text": text,
            "label": "TRANSACTION_DEBIT",
            "provider": "ARAB_BANK",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": f"ATM {br}",
            "type": "DEBIT"
        })

    for _ in range(20):
        acc = random_account()
        amt = round(random.choice([20, 50, 100, 300, 500]), 3)
        bal = round(random.uniform(100.0, 900.0), 3)
        dt = random_date_str()
        text = f"JO\nJOD {amt:.3f} has been credited to {acc} on {dt} as an Online ATM Deposit. Available balance {bal:.3f}."
        dataset.append({
            "text": text,
            "label": "TRANSACTION_CREDIT",
            "provider": "ARAB_BANK",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": "ATM Deposit",
            "type": "CREDIT"
        })

    # 2. CAPITAL BANK
    for _ in range(40):
        acc = random_account()
        name = random.choice(NAMES)
        amt = round(random.uniform(1.0, 80.0), 3)
        bal = round(random.uniform(0.0, 350.0), 3)
        dt = random_date_str()
        text = f"Outward Cliq of JOD {amt:.3f} debited from Acc. No {acc} on {dt} to {name}. Available balance JOD {bal:.3f}"
        dataset.append({
            "text": text,
            "label": "TRANSACTION_DEBIT",
            "provider": "CAPITAL_BANK",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": name,
            "type": "DEBIT"
        })

    for _ in range(40):
        acc = random_account()
        name = random.choice(NAMES)
        amt = round(random.uniform(2.5, 95.0), 3)
        bal = round(random.uniform(10.0, 420.0), 3)
        dt = random_date_str()
        text = f"Inward Cliq of JOD {amt:.3f} credited to Acc.{acc} on {dt} from {name}. Available balance JOD {bal:.3f}"
        dataset.append({
            "text": text,
            "label": "TRANSACTION_CREDIT",
            "provider": "CAPITAL_BANK",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": name,
            "type": "CREDIT"
        })

    for _ in range(40):
        acc = random_account()
        m = random.choice(MERCHANTS)
        amt = round(random.uniform(1.5, 65.0), 3)
        bal = round(random.uniform(0.1, 280.0), 3)
        dt = random_date_str()
        text = f"JOD {amt:.3f} debited from Acc. {acc} at {m} on {dt}. Available balance JOD {bal:.3f}"
        dataset.append({
            "text": text,
            "label": "TRANSACTION_DEBIT",
            "provider": "CAPITAL_BANK",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": m,
            "type": "DEBIT"
        })

    for _ in range(30):
        acc = random_account()
        name = random.choice(NAMES)
        amt = round(random.uniform(5.0, 70.0), 3)
        bal = round(random.uniform(0.0, 200.0), 3)
        text = f"JO\nتم قيد دفعة كليك بمبلغ {amt:.3f}JOD إلى {acc} من حساب {name} الرصيد {bal:.3f}JOD"
        dataset.append({
            "text": text,
            "label": "TRANSACTION_CREDIT",
            "provider": "CAPITAL_BANK",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": name,
            "type": "CREDIT"
        })

    for _ in range(25):
        acc = random_account()
        m = random.choice(MERCHANTS)
        amt = round(random.uniform(3.0, 45.0), 3)
        bal = round(random.uniform(5.0, 150.0), 3)
        text = f"A reversal of JOD {amt:.3f} has been processed on your card ending with {acc} from {m}. Your available balance is JOD {bal:.3f}."
        dataset.append({
            "text": text,
            "label": "TRANSACTION_CREDIT",
            "provider": "CAPITAL_BANK",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": m,
            "type": "CREDIT"
        })

    # 3. REFLECT (ARAB BANK NEOMOBILE)
    for _ in range(45):
        acc = random_account()
        m = random.choice(MERCHANTS)
        amt = round(random.uniform(1.25, 55.0), 3)
        bal = round(random.uniform(12.0, 310.0), 3)
        dt = random_date_str()
        text = f"JO\nYou have a purchase transaction on Reflect card {acc} at {m} amount JOD {amt:.3f} on {dt}. Available balance JOD {bal:.3f}."
        dataset.append({
            "text": text,
            "label": "TRANSACTION_DEBIT",
            "provider": "REFLECT",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": m,
            "type": "DEBIT"
        })

    for _ in range(35):
        acc = random_account()
        name = random.choice(NAMES)
        amt = round(random.uniform(5.0, 60.0), 3)
        bal = round(random.uniform(10.0, 240.0), 3)
        text = f"JO\nOutward CliQ of JOD {amt:.3f} debited from Reflect account {acc} to {name}. Available balance JOD {bal:.3f}."
        dataset.append({
            "text": text,
            "label": "TRANSACTION_DEBIT",
            "provider": "REFLECT",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": name,
            "type": "DEBIT"
        })

    for _ in range(35):
        acc = random_account()
        name = random.choice(NAMES)
        amt = round(random.uniform(4.0, 80.0), 3)
        bal = round(random.uniform(25.0, 400.0), 3)
        text = f"JO\nInward CliQ of JOD {amt:.3f} credited to Reflect account {acc} from {name}. Available balance JOD {bal:.3f}."
        dataset.append({
            "text": text,
            "label": "TRANSACTION_CREDIT",
            "provider": "REFLECT",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": name,
            "type": "CREDIT"
        })

    # 4. ORANGE MONEY (ARABIC WALLET)
    for _ in range(50):
        phone = f"077{random.randint(1000000, 9999999)}"
        name = random.choice(NAMES)
        amt = round(random.uniform(2.0, 50.0), 3)
        bal = round(random.uniform(5.0, 180.0), 3)
        ref = random.randint(1000000, 9999999)
        text = f"JO\nتم تحويل مبلغ {amt:.3f} JOD بنجاح إلى محفظة {phone} ({name}) عبر كليك. رصيدك الحالي هو {bal:.3f} JOD. رقم الحركة: {ref}."
        dataset.append({
            "text": text,
            "label": "TRANSACTION_DEBIT",
            "provider": "ORANGE_MONEY",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": name,
            "type": "DEBIT"
        })

    for _ in range(45):
        phone = f"077{random.randint(1000000, 9999999)}"
        name = random.choice(NAMES)
        amt = round(random.uniform(3.0, 75.0), 3)
        bal = round(random.uniform(15.0, 250.0), 3)
        ref = random.randint(1000000, 9999999)
        text = f"JO\nتم استلام مبلغ {amt:.3f} JOD بنجاح إلى محفظتك من {phone} ({name}) كليك. رصيدك الحالي هو {bal:.3f} JOD. رقم المرجع: {ref}."
        dataset.append({
            "text": text,
            "label": "TRANSACTION_CREDIT",
            "provider": "ORANGE_MONEY",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": name,
            "type": "CREDIT"
        })

    for _ in range(40):
        m = random.choice(MERCHANTS)
        amt = round(random.uniform(1.5, 35.0), 3)
        bal = round(random.uniform(4.0, 160.0), 3)
        ref = random.randint(100000, 999999)
        text = f"JO\nتم دفع مبلغ {amt:.3f} JOD بنجاح إلى تاجر {m} بواسطة محفظة أورنج موني. رصيدك المتبقي {bal:.3f} JOD. رقم العملية: {ref}."
        dataset.append({
            "text": text,
            "label": "TRANSACTION_DEBIT",
            "provider": "ORANGE_MONEY",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": m,
            "type": "DEBIT"
        })

    for _ in range(30):
        biller = random.choice(BILLERS)
        amt = round(random.uniform(5.0, 60.0), 3)
        bal = round(random.uniform(10.0, 200.0), 3)
        ref = random.randint(1000000, 9999999)
        text = f"JO\nتم دفع فاتورة {biller} بنجاح بقيمة {amt:.3f} JOD عبر إي فواتيركم من محفظتك. الرصيد المتاح {bal:.3f} JOD. رقم الفاتورة: {ref}."
        dataset.append({
            "text": text,
            "label": "TRANSACTION_DEBIT",
            "provider": "ORANGE_MONEY",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": biller,
            "type": "DEBIT"
        })

    # 5. ZAIN CASH (ARABIC WALLET)
    for _ in range(50):
        phone = f"079{random.randint(1000000, 9999999)}"
        name = random.choice(NAMES)
        amt = round(random.uniform(1.0, 60.0), 2)
        bal = round(random.uniform(5.0, 190.0), 2)
        ref = random.randint(1000000, 9999999)
        text = f"JO\nتم تحويل مبلغ {amt:.2f} JOD بنجاح إلى {phone} ({name}) عبر كليك. رصيدك الحالي هو {bal:.2f} JOD. الرقم المرجعي: {ref}."
        dataset.append({
            "text": text,
            "label": "TRANSACTION_DEBIT",
            "provider": "ZAIN_CASH",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": name,
            "type": "DEBIT"
        })

    for _ in range(45):
        name = random.choice(NAMES)
        amt = round(random.uniform(3.0, 80.0), 2)
        bal = round(random.uniform(12.0, 260.0), 2)
        ref = random.randint(1000000, 9999999)
        text = f"JO\nتم استلام مبلغ {amt:.2f} JOD في محفظتك بنجاح من {name} عبر كليك. رصيدك الحالي هو {bal:.2f} JOD. الرقم المرجعي: {ref}."
        dataset.append({
            "text": text,
            "label": "TRANSACTION_CREDIT",
            "provider": "ZAIN_CASH",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": name,
            "type": "CREDIT"
        })

    for _ in range(40):
        m = random.choice(MERCHANTS)
        amt = round(random.uniform(2.0, 40.0), 2)
        bal = round(random.uniform(5.0, 170.0), 2)
        text = f"JO\nتمت عملية الشراء بنجاح بقيمة {amt:.2f} JOD لدى تاجر {m} باستخدام بطاقة زين كاش. رصيدك المتبقي {bal:.2f} JOD."
        dataset.append({
            "text": text,
            "label": "TRANSACTION_DEBIT",
            "provider": "ZAIN_CASH",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": m,
            "type": "DEBIT"
        })

    for _ in range(25):
        amt = round(random.uniform(5.0, 100.0), 2)
        bal = round(random.uniform(amt, amt + 150.0), 2)
        agent = random.choice(["وكيل زين", "فرع زين", "صراف آلي", "معتمد زين"])
        text = f"JO\nتم إيداع مبلغ {amt:.2f} JOD نقداً في محفظة زين كاش الخاصة بك عبر {agent}. رصيدك الجديد {bal:.2f} JOD."
        dataset.append({
            "text": text,
            "label": "TRANSACTION_CREDIT",
            "provider": "ZAIN_CASH",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": agent,
            "type": "CREDIT"
        })

    for _ in range(25):
        amt = round(random.uniform(5.0, 80.0), 2)
        bal = round(random.uniform(2.0, 90.0), 2)
        atm = random.choice(["صراف آلي بنك القاهرة عمان", "صراف آلي البنك العربي", "صراف آلي بنك الإسكان", "وكيل زين"])
        text = f"JO\nتم سحب مبلغ {amt:.2f} JOD نقداً من {atm} بواسطة محفظتك. رصيدك الحالي {bal:.2f} JOD."
        dataset.append({
            "text": text,
            "label": "TRANSACTION_DEBIT",
            "provider": "ZAIN_CASH",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": atm,
            "type": "DEBIT"
        })

    for _ in range(20):
        biller = random.choice(BILLERS)
        amt = round(random.uniform(4.0, 50.0), 3)
        bal = round(random.uniform(5.0, 120.0), 2)
        text = f"JO\nتم دفع فاتورة {biller} بنجاح بقيمة {amt:.3f} JOD من خلال خدمة إي فواتيركم. رصيدك الحالي هو {bal:.2f} JOD."
        dataset.append({
            "text": text,
            "label": "TRANSACTION_DEBIT",
            "provider": "ZAIN_CASH",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": biller,
            "type": "DEBIT"
        })

    # 6. UWALLET (UMNIAH)
    for _ in range(45):
        phone = f"078{random.randint(1000000, 9999999)}"
        name = random.choice(NAMES)
        amt = round(random.uniform(2.5, 45.0), 3)
        bal = round(random.uniform(8.0, 180.0), 3)
        ref = random.randint(1000000, 9999999)
        text = f"JO\nتم تحويل مبلغ {amt:.3f} JOD بنجاح إلى محفظة {phone} ({name}) عبر كليك. رصيدك الحالي هو {bal:.3f} JOD. رقم المرجع: {ref}."
        dataset.append({
            "text": text,
            "label": "TRANSACTION_DEBIT",
            "provider": "UWALLET",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": name,
            "type": "DEBIT"
        })

    for _ in range(40):
        m = random.choice(MERCHANTS)
        amt = round(random.uniform(1.8, 38.0), 3)
        bal = round(random.uniform(10.0, 220.0), 3)
        text = f"JO\nYou have completed a purchase of JOD {amt:.3f} with your UWallet Mastercard at {m}. Available balance JOD {bal:.3f}."
        dataset.append({
            "text": text,
            "label": "TRANSACTION_DEBIT",
            "provider": "UWALLET",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": m,
            "type": "DEBIT"
        })

    # 7. BANK AL ETIHAD
    for _ in range(50):
        acc = random_account()
        m = random.choice(MERCHANTS)
        amt = round(random.uniform(1.5, 75.0), 3)
        bal = round(random.uniform(15.0, 600.0), 3)
        dt = random_date_str()
        text = f"JO\nYou have made a purchase of JOD {amt:.3f} with card ending in {acc} at {m} on {dt}. Available balance is JOD {bal:.3f}."
        dataset.append({
            "text": text,
            "label": "TRANSACTION_DEBIT",
            "provider": "BANK_AL_ETIHAD",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": m,
            "type": "DEBIT"
        })

    for _ in range(40):
        acc = random_account()
        name = random.choice(NAMES)
        amt = round(random.uniform(5.0, 100.0), 3)
        bal = round(random.uniform(20.0, 500.0), 3)
        dt = random_date_str()
        text = f"JO\nOutward CliQ of JOD {amt:.3f} debited from Acc. {acc} on {dt} to {name}. Available balance JOD {bal:.3f}."
        dataset.append({
            "text": text,
            "label": "TRANSACTION_DEBIT",
            "provider": "BANK_AL_ETIHAD",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": name,
            "type": "DEBIT"
        })

    for _ in range(40):
        acc = random_account()
        name = random.choice(NAMES)
        amt = round(random.uniform(5.0, 120.0), 3)
        bal = round(random.uniform(30.0, 700.0), 3)
        dt = random_date_str()
        text = f"JO\nInward CliQ of JOD {amt:.3f} credited to Acc. {acc} on {dt} from {name}. Available balance JOD {bal:.3f}."
        dataset.append({
            "text": text,
            "label": "TRANSACTION_CREDIT",
            "provider": "BANK_AL_ETIHAD",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": name,
            "type": "CREDIT"
        })

    # 8. HOUSING BANK (HBTF)
    for _ in range(45):
        acc = random_account()
        m = random.choice(MERCHANTS)
        amt = round(random.uniform(2.0, 65.0), 3)
        bal = round(random.uniform(15.0, 450.0), 3)
        dt = random_date_str()
        text = f"JO\nتمت حركة شراء بمبلغ {amt:.3f} دينار على بطاقتك {acc} لدى {m} في {dt}. الرصيد المتاح {bal:.3f} دينار."
        dataset.append({
            "text": text,
            "label": "TRANSACTION_DEBIT",
            "provider": "HOUSING_BANK",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": m,
            "type": "DEBIT"
        })

    for _ in range(35):
        acc = random_account()
        name = random.choice(NAMES)
        amt = round(random.uniform(5.0, 80.0), 3)
        bal = round(random.uniform(20.0, 380.0), 3)
        text = f"JO\nتم قيد حوالة كليك بمبلغ {amt:.3f} د.أ لحسابك {acc} من {name}. رصيدك المتاح هو {bal:.3f} د.أ."
        dataset.append({
            "text": text,
            "label": "TRANSACTION_CREDIT",
            "provider": "HOUSING_BANK",
            "expected_amount": amt,
            "expected_currency": "JOD",
            "expected_merchant": name,
            "type": "CREDIT"
        })

    # --- NEGATIVE CLASS 1: OTP & 2FA CODES (CRUCIAL!) ---
    # Login OTPs
    for _ in range(120):
        code = random_otp()
        prov = random.choice(["ARAB_BANK", "CAPITAL_BANK", "REFLECT", "ORANGE_MONEY", "ZAIN_CASH", "UWALLET", "BANK_AL_ETIHAD", "HOUSING_BANK"])
        tpls = [
            f"JO\nTo continue with your account login process, enter the code {code}. Please ensure not to share your activation code with anyone.",
            f"JO\n{code} هو رمز المرور لمرة واحدة (OTP) لتسجيل الدخول، يرجى عدم مشاركته مع أي شخص، صالح لمدة 5 دقائق.",
            f"JO\nYour verification code is {code} to log in to mobile banking. Please do not share this code with anyone.",
            f"JO\nرمز التحقق الخاص بك في محفظة Orange Money هو: {code}. لا تشارك هذا الرمز مع أي شخص لحماية حسابك.",
            f"JO\nرمز التحقق لمرة واحدة في زين كاش هو: {code} لإتمام عملية تسجيل الدخول. لا تشارك هذا الرمز مع أي كان.",
            f"JO\nYour Reflect verification code is {code}. Do not share this code with anyone, including Reflect support.",
            f"JO\nرمز التحقق لمرة واحدة (OTP) لتسجيل الدخول إلى تطبيق إسكان موبايل هو: {code}. لا تشارك هذا الرمز مطلقاً."
        ]
        dataset.append({
            "text": random.choice(tpls),
            "label": "OTP",
            "provider": prov,
            "expected_amount": None,
            "expected_currency": None,
            "expected_merchant": None,
            "type": "NONE"
        })

    # Purchase Authorization OTPs (TRAP!)
    for _ in range(120):
        code = random_otp()
        m = random.choice(MERCHANTS)
        amt = round(random.uniform(2.0, 90.0), 3)
        prov = random.choice(["ARAB_BANK", "CAPITAL_BANK", "REFLECT", "ORANGE_MONEY", "ZAIN_CASH", "UWALLET", "BANK_AL_ETIHAD", "HOUSING_BANK"])
        tpls = [
            f"JO\nDO NOT SHARE THIS CODE.\nOne Time Password: {code}\nPurpose: Purchase of amount {amt:.3f} JOD from {m}\nFees apply on international transactions.",
            f"JO\nOne-Time Password: {code} for your online purchase of JOD {amt:.3f} at {m}. Valid for 3 mins. Never share your OTP.",
            f"JO\nYour OTP is {code} for transfer JOD {amt:.3f} Please dont share.\n{random_ref()[:8]}",
            f"JO\nرمز التأكيد لعملية الشراء عبر الإنترنت هو: {code} بمبلغ {amt:.3f} JOD لدى {m}. لا تشارك الرمز لحماية حسابك.",
            f"JO\nOne Time Password (OTP) for online purchase of JOD {amt:.3f} at {m} is {code}. Do not share."
        ]
        dataset.append({
            "text": random.choice(tpls),
            "label": "OTP",
            "provider": prov,
            "expected_amount": None,
            "expected_currency": None,
            "expected_merchant": None,
            "type": "NONE"
        })

    # --- NEGATIVE CLASS 2: DECLINED / FAILED TRANSACTIONS ---
    for _ in range(120):
        acc = random_account()
        m = random.choice(MERCHANTS)
        amt = round(random.uniform(5.0, 150.0), 3)
        prov = random.choice(["ARAB_BANK", "CAPITAL_BANK", "REFLECT", "ORANGE_MONEY", "ZAIN_CASH", "UWALLET", "BANK_AL_ETIHAD", "HOUSING_BANK"])
        tpls = [
            f"JO\nحركة مرفوضة على بطاقتك المنتهية ب {acc} بقيمة JOD {amt:.3f} بسبب عدم كفاية الرصيد, للمزيد اتصل على 065100220",
            f"JO\nTransaction declined: purchase of JOD {amt:.3f} on card ending {acc} at {m} due to insufficient funds.",
            f"JO\nTransaction declined on Reflect card {acc} for amount JOD {amt:.3f} at {m} due to insufficient funds.",
            f"JO\nفشلت عملية الدفع بمبلغ {amt:.3f} JOD بسبب عدم توفر رصيد كافٍ في محفظتك. يرجى إعادة شحن المحفظة والمحاولة لاحقاً.",
            f"JO\nحركة غير مكتملة: تم رفض عملية التحويل بمبلغ {amt:.3f} JOD بسبب عدم كفاية الرصيد في محفظة زين كاش.",
            f"JO\nحركة شراء مرفوضة بقيمة {amt:.3f} د.أ على بطاقتك {acc} بسبب عدم كفاية الرصيد."
        ]
        dataset.append({
            "text": random.choice(tpls),
            "label": "DECLINED",
            "provider": prov,
            "expected_amount": None,
            "expected_currency": None,
            "expected_merchant": None,
            "type": "NONE"
        })

    # --- NEGATIVE CLASS 3: SYSTEM ANNOUNCEMENTS, DOWNTIME & BALANCE INQUIRIES ---
    for _ in range(160):
        prov = random.choice(["ARAB_BANK", "CAPITAL_BANK", "REFLECT", "ORANGE_MONEY", "ZAIN_CASH", "UWALLET", "BANK_AL_ETIHAD", "HOUSING_BANK"])
        acc = random_account()
        bal = round(random.uniform(5.0, 950.0), 3)
        dt = random_date_str()
        tpls = [
            f"JO\nYour available balance on account {acc} is JOD {bal:.3f} on {dt}.",
            f"JO\nBalance JOD {bal:.3f} on account {acc}.",
            f"JO\nرصيد حسابك الحالي هو {bal:.3f} دينار على حسابك {acc}.",
            f"رصيدك المتوفر في المحفظة هو {bal:.3f} JOD.",
            f"Your current balance is JOD {bal:.3f}.",
            f"JO\nBalance inquiry: Account {acc} available balance JOD {bal:.3f}.",
            f"JOdson {dt}. Balance JOD {bal:.3f}.",
            "يرجى العلم بأن خدمة كليك ستتوقف مؤقتاً لغايات تحديث الأنظمة يوم الجمعة من الساعة 2:00 وحتى 2:30 بعد منتصف الليل, مستعدون لخدمتكم.",
            "JO\nYour eStatement has been issued for Account. Please login to Arabi Online or Arab Bank App to view it.",
            "JO\nReflect services including CliQ transfers will undergo scheduled system maintenance on Friday from 03:00 AM to 05:00 AM.",
            "تنويه: ستتوقف خدمات التحويل والدفع عبر كليك مؤقتاً لتحديث الأنظمة فجر يوم الجمعة من 01:00 حتى 03:00 صباحاً.",
            "JO\nYour card ending in was successfully added to Apple Pay. If you did not make this request, call customer service.",
            "JO\nيرجى العلم بأن خدمة كليك ستكون غير متاحة مؤقتاً يوم الجمعة من 02:00 إلى 03:30 صباحاً لغايات الصيانة الدورية.",
            "تم تفعيل بطاقتك بنجاح على Apple Pay. إذا لم تقم بهذه العملية يرجى التواصل فوراً مع مركز الاتصال.",
            "عميلنا العزيز، تم تفعيل بطاقتك الائتمانية بنجاح، نتمنى لك تجربة مصرفية مميزة.",
            "تم إصدار بطاقتك الجديدة وهي جاهزة للاستلام من الفرع الرئيسي."
        ]
        dataset.append({
            "text": random.choice(tpls),
            "label": "ANNOUNCEMENT",
            "provider": prov,
            "expected_amount": None,
            "expected_currency": None,
            "expected_merchant": None,
            "type": "NONE"
        })

    # --- NEGATIVE CLASS 4: MARKETING PROMOS & REWARD VOUCHERS ---
    for _ in range(120):
        prov = random.choice(["ARAB_BANK", "CAPITAL_BANK", "REFLECT", "ORANGE_MONEY", "ZAIN_CASH", "UWALLET", "BANK_AL_ETIHAD", "HOUSING_BANK"])
        loan_amt = random.choice([5000, 10000, 15000, 20000, 25000, 30000])
        tpls = [
            "JO\n20 Points were redeemed from your 'Arabi Points' account as a reward voucher. For more information, login to Arab Bank app.",
            "JO\nYour Talabat Voucher Code is : WSSHKHNFN7. 20 Points from your Arabi Points were redeemed as a Talabat voucher.",
            "JO\nCongratulations! You have received 50 bonus Reflect Coins for completing 5 CliQ transfers this week. View rewards in app.",
            "اشحن خطك الخلوي بقيمة 5 دنانير أو أكثر عبر تطبيق المحفظة واحصل على 20% رصيد مجاني إضافي!",
            "استخدم بطاقتك في مشترياتك واحصل على خصم فوري 15% لدى المحال المشاركة طيلة عطلة نهاية الأسبوع!",
            "ادفع فواتيرك عبر إي فواتيركم باستخدام المحفظة وادخل السحب على جوائز أسبوعية قيّمة!",
            f"احصل على تمويل شخصي يصل إلى {loan_amt} دينار بفترة سداد ميسرة وبدون تحويل راتب! قدم طلبك الآن عبر التطبيق.",
            "استفد من تمويل مرابحة السيارات بنسب أرباح منافسة وإجراءات سريعة. تفضل بزيارة أقرب فرع للبنك الإسلامي الأردني.",
            f"عرض خاص: قرض شخصي فوري لغاية {loan_amt} د.أ بأقل فائدة وأطول فترة سداد، اتصل بنا اليوم أو قدم أونلاين.",
            "تقدم بطلب الحصول على البطاقة الائتمانية بدون رسوم سنوية للسنة الأولى واستمتع بعروض حصرية."
        ]
        dataset.append({
            "text": random.choice(tpls),
            "label": "PROMO",
            "provider": prov,
            "expected_amount": None,
            "expected_currency": None,
            "expected_merchant": None,
            "type": "NONE"
        })

    # --- NEGATIVE CLASS 5: CASUAL CHAT NOISE & SELF-MESSAGES ---
    chat_phrases = [
        "حولتلك 10 دنانير على كليك شيك عليها بالله",
        "حولتلك 15 ليرة هسا شوف وصلتك ولا لسا؟",
        "وصلتك الحوالة ولا لسا؟",
        "ابعثلي اسم الكليك تبعك عشان احولك حق الغدا",
        "ابعثلي رقم الكليك ضروري",
        "كم رصيدك هسا في المحفظة؟",
        "اشتريت من زارا ب 25 دينار مبارح",
        "رحت على كارفور واشتريت أغراض ب 18 ليرة",
        "did you finish the transaction?",
        "did the cliq transfer go through?",
        "can you send me 15 JOD on cliq to pay the driver",
        "can you transfer 20 JOD to my cliq alias",
        "send me the transaction receipt or screenshot",
        "دفعت الحساب للمطعم ولا ادفع انا؟",
        "معي 50 دينار كاش مين بده كليك؟",
        "حولت 5 دنانير بالغلط رجعلي اياهم",
        "I transferred you the money for yesterday's dinner",
        "did you receive the payment on Zain cash?",
        "شو رقم محفظتك في اورنج موني؟",
        "check your account, I just sent 20 JOD",
        "عملت سحب من الصراف وما طلع مصاري",
        "مين يحولي 5 ليرات كليك وابعثلو رصيد؟",
        "دفعت الفاتورة على إي فواتيركم وخصموا مرتين",
        "كم خصموا عليك رسوم التحويل؟",
        "I am at Starbucks, do you want anything?",
        "the bill was 14.5 JOD each",
        "hey bro did you send the cliq?",
        "transfer me 10 jod please"
    ]

    for _ in range(350):
        phrase = random.choice(chat_phrases)
        dataset.append({
            "text": phrase,
            "label": "CHAT_NOISE",
            "provider": "PERSONAL",
            "expected_amount": None,
            "expected_currency": None,
            "expected_merchant": None,
            "type": "NONE"
        })

    # Shuffle the dataset
    random.shuffle(dataset)
    return dataset

def main():
    print("Generating comprehensive dataset for Masroof...")
    dataset = generate_samples()
    print(f"Total samples generated: {len(dataset)}")

    # Distribution breakdown
    counts = {}
    for item in dataset:
        counts[item['label']] = counts.get(item['label'], 0) + 1

    print("\nDataset Breakdown:")
    for label, count in counts.items():
        print(f" - {label}: {count} samples")

    # Export to JSON
    root = Path(__file__).resolve().parents[1]
    json_path = root / "data" / "training" / "dataset_expanded.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    print(f"\nSaved JSON dataset: {json_path}")

    # Export to CSV
    csv_path = root / "data" / "training" / "dataset_expanded.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "label", "provider", "type", "expected_amount", "expected_merchant"])
        for d in dataset:
            writer.writerow([d["text"], d["label"], d["provider"], d["type"], d["expected_amount"], d["expected_merchant"]])
    print(f"Saved CSV dataset: {csv_path}")

if __name__ == "__main__":
    main()
