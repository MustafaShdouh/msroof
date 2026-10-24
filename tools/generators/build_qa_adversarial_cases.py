import json
from pathlib import Path
import os

cases = [
    # =========================================================================
    # Group 1: Attached Currency Variations (e.g. 5.450usd, 10jod, 25eur, $5.45, 5.45$, 10.500د.أ, د.أ10.500)
    # =========================================================================
    {
        "id": "TC_ADV_CURR_001",
        "category": "EDGE_CASE_ATTACHED_CURRENCY",
        "provider": "Arab Bank",
        "sender": "ArabiBank",
        "description": "Purchase with attached lowercase USD currency (5.450usd) and balance in JOD (39.132jod)",
        "body": "JO\nYou have a purchase transaction on account 1234*678 from STEAM GAMES amount 5.450usd on 20/10/2026. Balance 39.132jod.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 5.45,
            "currency": "USD",
            "balance": 39.132,
            "account_mask": "1234*678",
            "merchant_or_party": "STEAM GAMES",
            "accountMask": "1234*678",
            "merchantOrParty": "STEAM GAMES"
        }
    },
    {
        "id": "TC_ADV_CURR_002",
        "category": "EDGE_CASE_ATTACHED_CURRENCY",
        "provider": "Bank al Etihad",
        "sender": "BankAlEtihad",
        "description": "Outward CliQ with attached lowercase JOD currency (10jod) and balance in USD (145.20usd)",
        "body": "JO\nOutward CliQ of 10jod debited from Acc. *9123 to LAITH OMARI. Available balance 145.20usd.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 10.0,
            "currency": "JOD",
            "balance": 145.2,
            "account_mask": "*9123",
            "merchant_or_party": "LAITH OMARI",
            "accountMask": "*9123",
            "merchantOrParty": "LAITH OMARI"
        }
    },
    {
        "id": "TC_ADV_CURR_003",
        "category": "EDGE_CASE_ATTACHED_CURRENCY",
        "provider": "Capital Bank",
        "sender": "CapitalBank",
        "description": "Purchase with attached EUR currency (25eur) and balance with euro symbol (€120.50)",
        "body": "Purchase of 25eur with card ending 5412 at ZARA ROME on 18/10/2026. Avail bal €120.50.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 25.0,
            "currency": "EUR",
            "balance": 120.5,
            "account_mask": "5412",
            "merchant_or_party": "ZARA ROME",
            "accountMask": "5412",
            "merchantOrParty": "ZARA ROME"
        }
    },
    {
        "id": "TC_ADV_CURR_004",
        "category": "EDGE_CASE_ATTACHED_CURRENCY",
        "provider": "Reflect",
        "sender": "Reflect",
        "description": "Purchase with prefix dollar sign ($5.45) and balance in JOD (JOD 50.000)",
        "body": "JO\nYou made a purchase of $5.45 with Reflect card 4123*789 at NETFLIX.COM. Available balance JOD 50.000.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 5.45,
            "currency": "USD",
            "balance": 50.0,
            "account_mask": "4123*789",
            "merchant_or_party": "NETFLIX.COM",
            "accountMask": "4123*789",
            "merchantOrParty": "NETFLIX.COM"
        }
    },
    {
        "id": "TC_ADV_CURR_005",
        "category": "EDGE_CASE_ATTACHED_CURRENCY",
        "provider": "Housing Bank",
        "sender": "HousingBank",
        "description": "Purchase transaction with postfix dollar sign (5.45$) and balance prefix ($85.20)",
        "body": "Purchase transaction of 5.45$ on card *3412 at SPOTIFY on 19/10/2026. Available balance $85.20.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 5.45,
            "currency": "USD",
            "balance": 85.2,
            "account_mask": "*3412",
            "merchant_or_party": "SPOTIFY",
            "accountMask": "*3412",
            "merchantOrParty": "SPOTIFY"
        }
    },
    {
        "id": "TC_ADV_CURR_006",
        "category": "EDGE_CASE_ATTACHED_CURRENCY",
        "provider": "Orange Money",
        "sender": "OrangeMoney",
        "description": "Arabic attached postfix currency (10.500د.أ) with balance in attached postfix (125.000د.أ)",
        "body": "JO\nتم دفع مبلغ 10.500د.أ بنجاح إلى تاجر CARREFOUR EXPRESS بواسطة محفظة أورنج موني. رصيدك المتبقي 125.000د.أ.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 10.5,
            "currency": "JOD",
            "balance": 125.0,
            "account_mask": None,
            "merchant_or_party": "CARREFOUR EXPRESS",
            "accountMask": None,
            "merchantOrParty": "CARREFOUR EXPRESS"
        }
    },
    {
        "id": "TC_ADV_CURR_007",
        "category": "EDGE_CASE_ATTACHED_CURRENCY",
        "provider": "UWallet",
        "sender": "UWallet",
        "description": "Arabic attached prefix currency (د.أ10.500) with balance in USD ($45.00)",
        "body": "JO\nتمت عملية شراء بقيمة د.أ10.500 لدى MILES SUPERMARKET بواسطة بطاقتك المنتهية بـ 8821. رصيدك $45.00.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 10.5,
            "currency": "JOD",
            "balance": 45.0,
            "account_mask": "8821",
            "merchant_or_party": "MILES SUPERMARKET",
            "accountMask": "8821",
            "merchantOrParty": "MILES SUPERMARKET"
        }
    },
    {
        "id": "TC_ADV_CURR_008",
        "category": "EDGE_CASE_ATTACHED_CURRENCY",
        "provider": "Zain Cash",
        "sender": "ZainCash",
        "description": "Arabic attached postfix SAR currency (150.00ر.س) with balance in JOD (450.250 د.أ)",
        "body": "تم تحويل مبلغ 150.00ر.س بنجاح إلى محمد ناصر عبر كليك. الرصيد المتاح 450.250 د.أ.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 150.0,
            "currency": "SAR",
            "balance": 450.25,
            "account_mask": None,
            "merchant_or_party": "محمد ناصر",
            "accountMask": None,
            "merchantOrParty": "محمد ناصر"
        }
    },

    # =========================================================================
    # Group 2: Internal Account-to-Account Transfers (MUST have isValidTransaction = False)
    # =========================================================================
    {
        "id": "TC_ADV_INTERNAL_001",
        "category": "ADVERSARIAL_INTERNAL_TRANSFER",
        "provider": "Arab Bank",
        "sender": "ArabiBank",
        "description": "Internal transfer between checking and savings accounts with dual account masks",
        "body": "JO\nInternal transfer: JOD 200.000 has been debited from checking account 1234*678 and credited to savings account 1234*890. Avl bal JOD 840.120.",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },
    {
        "id": "TC_ADV_INTERNAL_002",
        "category": "ADVERSARIAL_INTERNAL_TRANSFER",
        "provider": "Bank al Etihad",
        "sender": "BankAlEtihad",
        "description": "Arabic internal transfer between user's own checking and savings accounts (بين حساباتك)",
        "body": "JO\nتم تحويل مبلغ 100.000 JOD بنجاح بين حساباتك من الحساب الجاري *9123 إلى حساب التوفير *4451. الرصيد المتاح 350.000 JOD.",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },
    {
        "id": "TC_ADV_INTERNAL_003",
        "category": "ADVERSARIAL_INTERNAL_TRANSFER",
        "provider": "Capital Bank",
        "sender": "CapitalBank",
        "description": "English transfer between user's own accounts with dual account masks",
        "body": "Transfer between your accounts: JOD 50.000 debited from Acc. xxxx833 to Acc. xxxx911 on 18/10/2026. Available balance JOD 120.500.",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },
    {
        "id": "TC_ADV_INTERNAL_004",
        "category": "ADVERSARIAL_INTERNAL_TRANSFER",
        "provider": "Housing Bank",
        "sender": "HousingBank",
        "description": "Arabic internal transfer between primary account and sub-account (تحويل داخلي)",
        "body": "JO\nتم تنفيذ تحويل داخلي بمبلغ 75.000 د.أ من حسابك *7890 إلى حسابك الفرعي *7891. رصيدك المتاح هو 180.250 د.أ.",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },
    {
        "id": "TC_ADV_INTERNAL_005",
        "category": "ADVERSARIAL_INTERNAL_TRANSFER",
        "provider": "Reflect",
        "sender": "Reflect",
        "description": "Internal rebalancing from Reflect main account to savings space",
        "body": "JO\nTransfer from your Reflect main account 4123*789 to your savings space 4123*999 of JOD 30.000. New space balance JOD 150.000.",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },
    {
        "id": "TC_ADV_INTERNAL_006",
        "category": "ADVERSARIAL_INTERNAL_TRANSFER",
        "provider": "UWallet",
        "sender": "UWallet",
        "description": "Arabic transfer from wallet balance to linked debit card (تحويل بين حساباتك)",
        "body": "تم تحويل مبلغ 25.000 JOD من حساب المحفظة إلى بطاقتك المرتبطة xxxx4321 بنجاح (تحويل بين حساباتك). رصيد المحفظة 60.000 JOD.",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },
    {
        "id": "TC_ADV_INTERNAL_007",
        "category": "ADVERSARIAL_INTERNAL_TRANSFER",
        "provider": "HSBC",
        "sender": "HSBC",
        "description": "International multi-currency own account transfer between internal sub-accounts",
        "body": "Own account transfer: USD 500.00 transferred from Global Money account ending 1122 to Premier Checking account ending 3344. Balance USD 2,450.00.",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },

    # =========================================================================
    # Group 3: OTP Traps (MUST have isValidTransaction = False)
    # =========================================================================
    {
        "id": "TC_ADV_OTP_001",
        "category": "ADVERSARIAL_OTP_3DS_PURCHASE",
        "provider": "Bank al Etihad",
        "sender": "BankAlEtihad",
        "description": "3DS purchase OTP specifying exact amount and merchant NOON.COM",
        "body": "JO\nOne-Time Password: 492018 for your online purchase of JOD 45.000 at NOON.COM on card ending 5412. Valid for 3 mins. Never share your OTP.",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },
    {
        "id": "TC_ADV_OTP_002",
        "category": "ADVERSARIAL_OTP_3DS_PURCHASE",
        "provider": "Housing Bank",
        "sender": "HousingBank",
        "description": "Arabic 3DS online purchase OTP specifying merchant ZARA and amount in د.أ",
        "body": "JO\nرمز التحقق لمرة واحدة (OTP) لعملية الشراء عبر الإنترنت بمبلغ 32.500 د.أ لدى متجر ZARA هو: 710294. صالح لمدة دقيقتين. لا تشارك الرمز.",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },
    {
        "id": "TC_ADV_OTP_003",
        "category": "ADVERSARIAL_OTP_3DS_PURCHASE",
        "provider": "Reflect",
        "sender": "Reflect",
        "description": "3DS authorization OTP for international online shopping in USD at SHEIN.COM",
        "body": "Your Reflect OTP is 829410 for online transaction of USD 64.99 at SHEIN.COM. If you did not request this, freeze your card immediately.",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },
    {
        "id": "TC_ADV_OTP_004",
        "category": "ADVERSARIAL_OTP_3DS_PURCHASE",
        "provider": "Capital Bank",
        "sender": "CapitalBank",
        "description": "Transfer authorization OTP trap with amount and counterparty name",
        "body": "Your OTP is 654321 to authorize CliQ transfer of JOD 120.000 to OMAR HADDAD. Valid for 3 mins. Do not share this OTP.",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },
    {
        "id": "TC_ADV_OTP_005",
        "category": "ADVERSARIAL_OTP_LOGIN",
        "provider": "Arab Bank",
        "sender": "ArabiBank",
        "description": "Mobile banking login authentication passcode",
        "body": "JO\nYour Arabi Mobile login verification code is 381920. Do not disclose this passcode to anyone including bank staff.",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },
    {
        "id": "TC_ADV_OTP_006",
        "category": "ADVERSARIAL_OTP_LOGIN",
        "provider": "Orange Money",
        "sender": "OrangeMoney",
        "description": "Arabic wallet authentication OTP for digital card enrollment in Apple Pay",
        "body": "رمز التحقق لمرة واحدة OTP الخاص بك هو: 905128 لإضافة بطاقتك إلى Apple Pay بمحفظة أورنج موني. الرمز صالح لـ 5 دقائق. لا تشاركه مع أي شخص.",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },
    {
        "id": "TC_ADV_OTP_007",
        "category": "ADVERSARIAL_OTP_3DS_PURCHASE",
        "provider": "Chase",
        "sender": "Chase",
        "description": "International fraud prevention 3DS verification code mentioning Best Buy and USD amount",
        "body": "Chase: 481902 is your one-time code to approve a $189.99 charge at BEST BUY. Don't share it. We will never call to ask for this code.",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },

    # =========================================================================
    # Group 4: CliQ Transfers (Valid Transactions: Outward Expenses & Inward Income)
    # =========================================================================
    {
        "id": "TC_POS_CLIQ_001",
        "category": "POSITIVE_CLIQ_OUTWARD",
        "provider": "Bank al Etihad",
        "sender": "BankAlEtihad",
        "description": "Outward CliQ transfer with full 4-part Arabic recipient name",
        "body": "JO\nOutward CliQ of JOD 35.000 debited from Acc. *9123 to أحمد خليل عبد الرحيم المجالي. Available balance JOD 210.500.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 35.0,
            "currency": "JOD",
            "balance": 210.5,
            "account_mask": "*9123",
            "merchant_or_party": "أحمد خليل عبد الرحيم المجالي",
            "accountMask": "*9123",
            "merchantOrParty": "أحمد خليل عبد الرحيم المجالي"
        }
    },
    {
        "id": "TC_POS_CLIQ_002",
        "category": "POSITIVE_CLIQ_INWARD",
        "provider": "Arab Bank",
        "sender": "ArabiBank",
        "description": "Inward CliQ transfer credited to Arab Bank account from Arabic sender",
        "body": "JO\nJOD50.000 has been credited to 1234*678 from منى يوسف إبراهيم قاسم as CliQ transfer Balance 180.450JOD",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 50.0,
            "currency": "JOD",
            "balance": 180.45,
            "account_mask": "1234*678",
            "merchant_or_party": "منى يوسف إبراهيم قاسم",
            "accountMask": "1234*678",
            "merchantOrParty": "منى يوسف إبراهيم قاسم"
        }
    },
    {
        "id": "TC_POS_CLIQ_003",
        "category": "POSITIVE_CLIQ_OUTWARD",
        "provider": "Capital Bank",
        "sender": "CapitalBank",
        "description": "Outward CliQ transfer debited from Capital Bank account to English name",
        "body": "Outward Cliq of JOD 14.500 debited from Acc. No xxxx833 on 20/10/2026 to ZEID SAMER AL-FAYEZ. Available balance JOD 85.500",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 14.5,
            "currency": "JOD",
            "balance": 85.5,
            "account_mask": "xxxx833",
            "merchant_or_party": "ZEID SAMER AL-FAYEZ",
            "accountMask": "xxxx833",
            "merchantOrParty": "ZEID SAMER AL-FAYEZ"
        }
    },
    {
        "id": "TC_POS_CLIQ_004",
        "category": "POSITIVE_CLIQ_INWARD",
        "provider": "Housing Bank",
        "sender": "HousingBank",
        "description": "Arabic inward CliQ transfer in Housing Bank with sender name and د.أ currency",
        "body": "JO\nتم قيد حوالة كليك بمبلغ 120.000 د.أ لحسابك *7890 من طارق حسني النجار. رصيدك المتاح هو 340.250 د.أ.",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 120.0,
            "currency": "JOD",
            "balance": 340.25,
            "account_mask": "*7890",
            "merchant_or_party": "طارق حسني النجار",
            "accountMask": "*7890",
            "merchantOrParty": "طارق حسني النجار"
        }
    },
    {
        "id": "TC_POS_CLIQ_005",
        "category": "POSITIVE_CLIQ_OUTWARD",
        "provider": "Reflect",
        "sender": "Reflect",
        "description": "Outward CliQ transfer in Reflect with English female recipient name",
        "body": "JO\nOutward CliQ of JOD 22.000 debited from Reflect account 4123*789 to DINA NASER SHABAN. Available balance JOD 48.750.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 22.0,
            "currency": "JOD",
            "balance": 48.75,
            "account_mask": "4123*789",
            "merchant_or_party": "DINA NASER SHABAN",
            "accountMask": "4123*789",
            "merchantOrParty": "DINA NASER SHABAN"
        }
    },
    {
        "id": "TC_POS_CLIQ_006",
        "category": "POSITIVE_CLIQ_INWARD",
        "provider": "Orange Money",
        "sender": "OrangeMoney",
        "description": "Inward CliQ payment in Orange Money wallet from English sender name",
        "body": "JO\nتم استلام مبلغ 45.000 JOD بنجاح إلى محفظتك من HUSSEIN ALI AL-MASRI عبر كليك. رصيدك الحالي هو 102.500 JOD. رقم المرجع: 9912041.",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 45.0,
            "currency": "JOD",
            "balance": 102.5,
            "account_mask": None,
            "merchant_or_party": "HUSSEIN ALI AL-MASRI",
            "accountMask": None,
            "merchantOrParty": "HUSSEIN ALI AL-MASRI"
        }
    },
    {
        "id": "TC_POS_CLIQ_007",
        "category": "POSITIVE_CLIQ_OUTWARD",
        "provider": "Zain Cash",
        "sender": "ZainCash",
        "description": "Outward CliQ transfer in Zain Cash wallet to Arabic recipient name",
        "body": "JO\nتم تحويل مبلغ 18.00 JOD بنجاح إلى رانيا فؤاد حداد عبر كليك. رصيدك الحالي هو 72.40 JOD. الرقم المرجعي: 8192047.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 18.0,
            "currency": "JOD",
            "balance": 72.4,
            "account_mask": None,
            "merchant_or_party": "رانيا فؤاد حداد",
            "accountMask": None,
            "merchantOrParty": "رانيا فؤاد حداد"
        }
    },
    {
        "id": "TC_POS_CLIQ_008",
        "category": "POSITIVE_CLIQ_INWARD",
        "provider": "UWallet",
        "sender": "UWallet",
        "description": "Inward CliQ transfer in UWallet wallet from English sender name",
        "body": "JO\nتم استلام دفعة كليك بمبلغ 30.000 JOD إلى محفظة UWallet الخاصة بك من BILAL KHALIL ODEH. رصيدك الحالي هو 75.200 JOD.",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 30.0,
            "currency": "JOD",
            "balance": 75.2,
            "account_mask": None,
            "merchant_or_party": "BILAL KHALIL ODEH",
            "accountMask": None,
            "merchantOrParty": "BILAL KHALIL ODEH"
        }
    },

    # =========================================================================
    # Group 5: Declined / Failed Transactions (MUST have isValidTransaction = False)
    # =========================================================================
    {
        "id": "TC_ADV_DECLINED_001",
        "category": "ADVERSARIAL_DECLINED_FAILED",
        "provider": "Bank al Etihad",
        "sender": "BankAlEtihad",
        "description": "English transaction declined due to insufficient funds",
        "body": "JO\nTransaction declined: purchase of JOD 85.000 on card ending 5412 at CARREFOUR AMMAN due to insufficient funds.",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },
    {
        "id": "TC_ADV_DECLINED_002",
        "category": "ADVERSARIAL_DECLINED_FAILED",
        "provider": "Arab Bank",
        "sender": "ArabiBank",
        "description": "Arabic transaction declined due to card credit limit exceeded (حركة شراء مرفوضة)",
        "body": "JO\nحركة شراء مرفوضة: نأسف لعدم إتمام عملية الشراء بمبلغ 150.000 JOD لدى IKEA على بطاقتك 1234*678 لتجاوز الحد المسموح.",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },
    {
        "id": "TC_ADV_DECLINED_003",
        "category": "ADVERSARIAL_DECLINED_FAILED",
        "provider": "Orange Money",
        "sender": "OrangeMoney",
        "description": "Arabic failed wallet payment (فشلت عملية الدفع) due to insufficient wallet funds",
        "body": "JO\nفشلت عملية الدفع بمبلغ 40.000 JOD لدى تاجر كارفور لعدم توفر رصيد كافٍ في محفظة أورنج موني الخاصة بك.",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },
    {
        "id": "TC_ADV_DECLINED_004",
        "category": "ADVERSARIAL_DECLINED_FAILED",
        "provider": "Capital Bank",
        "sender": "CapitalBank",
        "description": "Online card purchase rejected due to incorrect CVV security code",
        "body": "Declined transaction: JOD 65.000 at ASOS.COM on card xxxx833 was rejected due to incorrect CVV entered. Your balance is JOD 210.00.",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },
    {
        "id": "TC_ADV_DECLINED_005",
        "category": "ADVERSARIAL_DECLINED_FAILED",
        "provider": "Housing Bank",
        "sender": "HousingBank",
        "description": "Arabic rejected CliQ transfer due to invalid counterparty alias (حركة كليك مرفوضة)",
        "body": "حركة كليك مرفوضة: تعذر إرسال مبلغ 20.000 د.أ من حسابك *7890 لعدم صحة معرف المستفيد (الاسم المستعار غير موجود).",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },
    {
        "id": "TC_ADV_DECLINED_006",
        "category": "ADVERSARIAL_DECLINED_FAILED",
        "provider": "Zain Cash",
        "sender": "ZainCash",
        "description": "Arabic incomplete ATM withdrawal cancelled due to timeout (حركة غير مكتملة)",
        "body": "حركة غير مكتملة: تم إلغاء عملية السحب النقدي بمبلغ 50.00 JOD من الصراف الآلي لانتهاء الوقت المحدد.",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },
    {
        "id": "TC_ADV_DECLINED_007",
        "category": "ADVERSARIAL_DECLINED_FAILED",
        "provider": "HSBC",
        "sender": "HSBC",
        "description": "International card declined notification because user card was frozen/locked",
        "body": "HSBC Alert: Transaction of GBP 120.00 at HARRODS LONDON was declined because your card ending 9944 is locked.",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },

    # =========================================================================
    # Group 6: Subtle Edge Cases (Arabic diacritics, decimal comma vs point, multiline headers, trap balances, maintenance, reversals)
    # =========================================================================
    {
        "id": "TC_EDGE_DIACRITICS_001",
        "category": "EDGE_CASE_ARABIC_DIACRITICS",
        "provider": "Housing Bank",
        "sender": "HousingBank",
        "description": "Purchase transaction with heavy Arabic Tashkeel / diacritics",
        "body": "JO\nتَمَّتْ عَمَلِيَّةُ شِرَاءٍ بِمَبْلَغِ 14.500 دِينَارٍ عَلَى بِطَاقَتِكَ *3412 لَدَى مَخَابِزِ السُّفَرَاءِ. الرَّصِيدُ الْمُتَاحُ 95.500 دِينَارٍ.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 14.5,
            "currency": "JOD",
            "balance": 95.5,
            "account_mask": "*3412",
            "merchant_or_party": "مخابز السفراء",
            "accountMask": "*3412",
            "merchantOrParty": "مخابز السفراء"
        }
    },
    {
        "id": "TC_EDGE_DIACRITICS_002",
        "category": "EDGE_CASE_ARABIC_DIACRITICS",
        "provider": "Arab Bank",
        "sender": "ArabiBank",
        "description": "Inward transfer with full Arabic diacritics and recipient name",
        "body": "JO\nتَمَّ قَيْدُ حَوَالَةٍ وَارِدَةٍ بِمَبْلَغِ 80.000 د.أ إِلَى حِسَابِكَ 1234*678 مِنْ خَالِدِ الْعُمَرِيِّ. الرَّصِيدُ 240.120 د.أ.",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 80.0,
            "currency": "JOD",
            "balance": 240.12,
            "account_mask": "1234*678",
            "merchant_or_party": "خالد العمري",
            "accountMask": "1234*678",
            "merchantOrParty": "خالد العمري"
        }
    },
    {
        "id": "TC_EDGE_DECIMAL_COMMA_001",
        "category": "EDGE_CASE_DECIMAL_FORMATS",
        "provider": "Bank al Etihad",
        "sender": "BankAlEtihad",
        "description": "Continental European decimal comma format (1500,50 EUR) with balance (2300,75 EUR)",
        "body": "Purchase of 1500,50 EUR on card ending 5412 at AIR FRANCE on 15/10/2026. Avail bal 2300,75 EUR.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 1500.5,
            "currency": "EUR",
            "balance": 2300.75,
            "account_mask": "5412",
            "merchant_or_party": "AIR FRANCE",
            "accountMask": "5412",
            "merchantOrParty": "AIR FRANCE"
        }
    },
    {
        "id": "TC_EDGE_THOUSANDS_COMMA_002",
        "category": "EDGE_CASE_DECIMAL_FORMATS",
        "provider": "Capital Bank",
        "sender": "CapitalBank",
        "description": "Standard thousands separator comma with decimal dot (1,250.75 USD) and balance (3,420.50 USD)",
        "body": "Debit card purchase of USD 1,250.75 at APPLE STORE FIFTH AVE with card xxxx833. Available balance USD 3,420.50.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 1250.75,
            "currency": "USD",
            "balance": 3420.5,
            "account_mask": "xxxx833",
            "merchant_or_party": "APPLE STORE FIFTH AVE",
            "accountMask": "xxxx833",
            "merchantOrParty": "APPLE STORE FIFTH AVE"
        }
    },
    {
        "id": "TC_EDGE_MULTILINE_HEADER_001",
        "category": "EDGE_CASE_WHITESPACE_NEWLINES",
        "provider": "Arab Bank",
        "sender": "ArabiBank",
        "description": "Gateway multiline routing header (JO\\n\\n) and newline separated key-value message body",
        "body": "JO\n\nYou have a purchase transaction\non account 1234*678\nfrom COZMO SUPERMARKET\namount JOD 18.750\non 20/10/2026 14:15.\nBalance JOD 112.430.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 18.75,
            "currency": "JOD",
            "balance": 112.43,
            "account_mask": "1234*678",
            "merchant_or_party": "COZMO SUPERMARKET",
            "accountMask": "1234*678",
            "merchantOrParty": "COZMO SUPERMARKET"
        }
    },
    {
        "id": "TC_EDGE_TRAP_BALANCE_001",
        "category": "ADVERSARIAL_TRAP_BALANCE",
        "provider": "Bank al Etihad",
        "sender": "BankAlEtihad",
        "description": "Periodic account balance statement alert without any transaction activity (MUST be isValidTransaction = False)",
        "body": "JO\nDear customer, your account balance for Acc. *9123 as of 20/10/2026 is JOD 1,450.250. Thank you for banking with Bank al Etihad.",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },
    {
        "id": "TC_EDGE_TRAP_BALANCE_002",
        "category": "ADVERSARIAL_TRAP_BALANCE",
        "provider": "Housing Bank",
        "sender": "HousingBank",
        "description": "Arabic account balance notification trap without transaction (MUST be isValidTransaction = False)",
        "body": "JO\nرصيد حسابك *7890 المتوفر حالياً هو 512.400 د.أ. لإدارة حسابك يرجى تحميل تطبيق إسكان أونلاين.",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },
    {
        "id": "TC_EDGE_MAINTENANCE_TRAP_001",
        "category": "ADVERSARIAL_MAINTENANCE_DOWNTIME",
        "provider": "Reflect",
        "sender": "Reflect",
        "description": "System maintenance announcement mentioning monetary limit trap (MUST be isValidTransaction = False)",
        "body": "JO\nReflect reminder: CliQ transfers up to 10,000 JOD will be unavailable on Saturday from 02:00 to 05:00 AM due to central bank core banking upgrade.",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },
    {
        "id": "TC_EDGE_TRUNCATED_SMS_001",
        "category": "ADVERSARIAL_TRUNCATED_SMS",
        "provider": "Housing Bank",
        "sender": "HousingBank",
        "description": "Malformed / truncated carrier SMS cut mid-stream (MUST be isValidTransaction = False)",
        "body": "JO\nتمت حركة شراء بمبلغ 15.000 دينار على بطاقتك *3412 لدى",
        "expected": {
            "isValidTransaction": False,
            "type": None,
            "amount": None,
            "currency": None,
            "balance": None,
            "account_mask": None,
            "merchant_or_party": None,
            "accountMask": None,
            "merchantOrParty": None
        }
    },
    {
        "id": "TC_EDGE_REVERSAL_REFUND_001",
        "category": "POSITIVE_REFUND_REVERSAL",
        "provider": "Capital Bank",
        "sender": "CapitalBank",
        "description": "Merchant reversal / refund credited back to customer debit card",
        "body": "A reversal of JOD 18.250 has been processed on your card ending with xxxx833 from TALABAT. Your available balance is JOD 78.350.",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 18.25,
            "currency": "JOD",
            "balance": 78.35,
            "account_mask": "xxxx833",
            "merchant_or_party": "TALABAT",
            "accountMask": "xxxx833",
            "merchantOrParty": "TALABAT"
        }
    },
    {
        "id": "TC_EDGE_EFAWATEERCOM_001",
        "category": "POSITIVE_BILL_PAYMENT",
        "provider": "Orange Money",
        "sender": "OrangeMoney",
        "description": "Arabic eFAWATEERcom utility bill payment via mobile wallet",
        "body": "JO\nتم تسديد فاتورة كهرباء إربد بنجاح بقيمة 28.350 JOD عبر إي فواتيركم من محفظتك. الرصيد المتاح 56.400 JOD.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 28.35,
            "currency": "JOD",
            "balance": 56.4,
            "account_mask": None,
            "merchant_or_party": "كهرباء إربد",
            "accountMask": None,
            "merchantOrParty": "كهرباء إربد"
        }
    }
]

output_path = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "qa_adversarial_cases.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(cases, f, ensure_ascii=False, indent=2)

print(f"Successfully generated {len(cases)} test cases in {output_path}")
