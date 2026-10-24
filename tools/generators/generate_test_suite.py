import json
import os
from pathlib import Path
import re

def create_test_suite():
    cases = []

    # =========================================================================
    # 1. POSITIVE TRANSACTIONS - ARAB BANK
    # =========================================================================
    cases.append({
        "id": "TC_POS_ARAB_001",
        "category": "POSITIVE_PURCHASE",
        "provider": "Arab Bank",
        "sender": "ArabiBank",
        "description": "Arab Bank standard POS debit card purchase with JOD 3 decimals and merchant",
        "body": "JO\nYou have a purchase transaction on account 1234*678 from ZAIN MARKET - ROSARY SIST amount JOD 5.450 on 20/10/2026 17:02. Balance JOD 39.132.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 5.45,
            "currency": "JOD",
            "accountMask": "1234*678",
            "merchantOrParty": "ZAIN MARKET - ROSARY SIST",
            "balance": 39.132
        }
    })

    cases.append({
        "id": "TC_POS_ARAB_002",
        "category": "POSITIVE_PURCHASE",
        "provider": "Arab Bank",
        "sender": "ArabiBank",
        "description": "Arab Bank short merchant purchase with 1.000 integer-like amount",
        "body": "JO\nYou have a purchase transaction on account 1234*678 from BLK amount JOD 1.000 on 20/10/2026 10:17. Balance JOD 44.582.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 1.0,
            "currency": "JOD",
            "accountMask": "1234*678",
            "merchantOrParty": "BLK",
            "balance": 44.582
        }
    })

    cases.append({
        "id": "TC_POS_ARAB_003",
        "category": "POSITIVE_CLIQ_OUTWARD",
        "provider": "Arab Bank",
        "sender": "ArabiBank",
        "description": "Arab Bank outward CliQ transfer with glued currency format JOD2.000 and Balance 45.582JOD",
        "body": "JO\nJOD2.000 has been debited from 1234*678 to BAKER NASIM MUSTAFA ELSHDOUH as CliQ transfer Balance 45.582JOD",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 2.0,
            "currency": "JOD",
            "accountMask": "1234*678",
            "merchantOrParty": "BAKER NASIM MUSTAFA ELSHDOUH",
            "balance": 45.582
        }
    })

    cases.append({
        "id": "TC_POS_ARAB_004",
        "category": "POSITIVE_CLIQ_INWARD",
        "provider": "Arab Bank",
        "sender": "ArabiBank",
        "description": "Arab Bank inward CliQ transfer credit to account with glued currency and sender name",
        "body": "JO\nJOD3.600 has been credited to 1234*678from RAAD MUNTHER MUNIER ALALI as CliQ transfer Balance 62.232JOD",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 3.6,
            "currency": "JOD",
            "accountMask": "1234*678",
            "merchantOrParty": "RAAD MUNTHER MUNIER ALALI",
            "balance": 62.232
        }
    })

    cases.append({
        "id": "TC_POS_ARAB_005",
        "category": "POSITIVE_ATM_WITHDRAWAL",
        "provider": "Arab Bank",
        "sender": "ArabiBank",
        "description": "Arab Bank cash withdrawal at branch ATM with integer amount glued to JOD",
        "body": "JO\n30JOD has been debited from your account 1234*678 as an ATM Withdrawal from Al-Thaqafa Br on 20/10/2026 14:10. Available balance 20.134.\nREF 439821190234",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 30.0,
            "currency": "JOD",
            "accountMask": "1234*678",
            "merchantOrParty": "Al-Thaqafa Br",
            "balance": 20.134
        }
    })

    cases.append({
        "id": "TC_POS_ARAB_006",
        "category": "POSITIVE_ATM_DEPOSIT",
        "provider": "Arab Bank",
        "sender": "ArabiBank",
        "description": "Arab Bank online ATM cash deposit credited to customer account",
        "body": "JO\nJOD 50.000 has been credited to  1234*678 on 28/09/2026 as an Online ATM Deposit. Available balance 50.000.",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 50.0,
            "currency": "JOD",
            "accountMask": "1234*678",
            "merchantOrParty": None,
            "balance": 50.0
        }
    })

    cases.append({
        "id": "TC_POS_ARAB_007",
        "category": "POSITIVE_PURCHASE",
        "provider": "Arab Bank",
        "sender": "ArabiBank",
        "description": "Arab Bank online e-commerce purchase at SHEIN with missing balance",
        "body": "JO\nYou have a purchase transaction on account 1234*678 from SHEIN.COM amount JOD 23.628 on 10/09/2026 01:12.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 23.628,
            "currency": "JOD",
            "accountMask": "1234*678",
            "merchantOrParty": "SHEIN.COM",
            "balance": None
        }
    })

    cases.append({
        "id": "TC_POS_ARAB_008",
        "category": "POSITIVE_PURCHASE",
        "provider": "Arab Bank",
        "sender": "ArabiBank",
        "description": "Arab Bank credit card purchase in USD currency abroad",
        "body": "JO\nYou have a purchase transaction on account 1234*678 from AMAZON.COM amount USD 49.99 on 15/10/2026 19:45. Balance USD 520.10.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 49.99,
            "currency": "USD",
            "accountMask": "1234*678",
            "merchantOrParty": "AMAZON.COM",
            "balance": 520.10
        }
    })

    cases.append({
        "id": "TC_POS_ARAB_009",
        "category": "POSITIVE_PURCHASE",
        "provider": "Arab Bank",
        "sender": "ArabiBank",
        "description": "Arab Bank online purchase in EUR currency",
        "body": "JO\nYou have a purchase transaction on account 1234*678 from BOOKING.COM amount EUR 85.00 on 12/10/2026 11:20. Balance EUR 210.00.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 85.0,
            "currency": "EUR",
            "accountMask": "1234*678",
            "merchantOrParty": "BOOKING.COM",
            "balance": 210.0
        }
    })

    cases.append({
        "id": "TC_POS_ARAB_010",
        "category": "POSITIVE_REFUND_REVERSAL",
        "provider": "Arab Bank",
        "sender": "ArabiBank",
        "description": "Arab Bank refund credit from merchant",
        "body": "JO\nA refund of JOD 23.628 from SHEIN.COM has been credited to your account 1234*678. Available balance JOD 68.210.",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 23.628,
            "currency": "JOD",
            "accountMask": "1234*678",
            "merchantOrParty": "SHEIN.COM",
            "balance": 68.21
        }
    })

    # =========================================================================
    # 2. POSITIVE TRANSACTIONS - CAPITAL BANK
    # =========================================================================
    cases.append({
        "id": "TC_POS_CAP_001",
        "category": "POSITIVE_CLIQ_INWARD",
        "provider": "Capital Bank",
        "sender": "CapitalBank",
        "description": "Capital Bank Arabic inward CliQ credit with sender name and glued amount",
        "body": "JO\nتم قيد دفعة كليك 10.870JOD لحساب ANMAR ALQUDAH من 0175*600 10.870JOD الرصيد",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 10.87,
            "currency": "JOD",
            "accountMask": "0175*600",
            "merchantOrParty": "ANMAR ALQUDAH",
            "balance": 10.87
        }
    })

    cases.append({
        "id": "TC_POS_CAP_002",
        "category": "POSITIVE_CLIQ_OUTWARD",
        "provider": "Capital Bank",
        "sender": "CapitalBank",
        "description": "Capital Bank English outward CliQ transfer with xxxx mask and zero balance",
        "body": "Outward Cliq of JOD 5.100 debited from Acc. No xxxx833 on 16/09/2026 to ANMAR NIDAL FAWWAZ ALQUDAH. Available balance JOD 0.000",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 5.1,
            "currency": "JOD",
            "accountMask": "xxxx833",
            "merchantOrParty": "ANMAR NIDAL FAWWAZ ALQUDAH",
            "balance": 0.0
        }
    })

    cases.append({
        "id": "TC_POS_CAP_003",
        "category": "POSITIVE_PURCHASE",
        "provider": "Capital Bank",
        "sender": "CapitalBank",
        "description": "Capital Bank debit at Google Mountain View online subscription",
        "body": "JOD 5.000 debited from Acc. xxxx833 at GOOGLE*GOOGLE ONE MOUNTAIN VIEWUS on 16/09/2026. Available balance JOD 0.100",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 5.0,
            "currency": "JOD",
            "accountMask": "xxxx833",
            "merchantOrParty": "GOOGLE*GOOGLE ONE MOUNTAIN VIEWUS",
            "balance": 0.1
        }
    })

    cases.append({
        "id": "TC_POS_CAP_004",
        "category": "POSITIVE_REFUND_REVERSAL",
        "provider": "Capital Bank",
        "sender": "CapitalBank",
        "description": "Capital Bank transaction reversal / refund credited back to account",
        "body": "A reversal of JOD 5.000 has been processed on your card ending with xxxx833 from GOOGLE*GOOGLE ONE MOUNTAIN VIEWUS. Your available balance is JOD 5.100.",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 5.0,
            "currency": "JOD",
            "accountMask": "xxxx833",
            "merchantOrParty": "GOOGLE*GOOGLE ONE MOUNTAIN VIEWUS",
            "balance": 5.1
        }
    })

    cases.append({
        "id": "TC_POS_CAP_005",
        "category": "POSITIVE_CLIQ_INWARD",
        "provider": "Capital Bank",
        "sender": "CapitalBank",
        "description": "Capital Bank inward CliQ transfer in English",
        "body": "Inward Cliq of JOD 5.000 credited to Acc.xxxx833 on 16/09/2026 from ANMAR ALQUDAH. Available balance JOD 5.100",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 5.0,
            "currency": "JOD",
            "accountMask": "xxxx833",
            "merchantOrParty": "ANMAR ALQUDAH",
            "balance": 5.1
        }
    })

    cases.append({
        "id": "TC_POS_CAP_006",
        "category": "POSITIVE_PURCHASE",
        "provider": "Capital Bank",
        "sender": "CapitalBank",
        "description": "Capital Bank purchase in SAR currency during travel in Saudi Arabia",
        "body": "SAR 120.50 debited from Acc. xxxx833 at JARIR BOOKSTORE RIYADH on 12/10/2026. Available balance SAR 850.00",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 120.5,
            "currency": "SAR",
            "accountMask": "xxxx833",
            "merchantOrParty": "JARIR BOOKSTORE RIYADH",
            "balance": 850.0
        }
    })

    cases.append({
        "id": "TC_POS_CAP_007",
        "category": "POSITIVE_PURCHASE",
        "provider": "Capital Bank",
        "sender": "CapitalBank",
        "description": "Capital Bank purchase in EUR currency on Steam",
        "body": "EUR 39.99 debited from Acc. xxxx833 at STEAM GAMES on 10/10/2026. Available balance EUR 150.00",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 39.99,
            "currency": "EUR",
            "accountMask": "xxxx833",
            "merchantOrParty": "STEAM GAMES",
            "balance": 150.0
        }
    })

    # =========================================================================
    # 3. POSITIVE TRANSACTIONS - REFLECT (NEOMOBILE)
    # =========================================================================
    cases.append({
        "id": "TC_POS_REF_001",
        "category": "POSITIVE_PURCHASE",
        "provider": "Reflect",
        "sender": "Reflect",
        "description": "Reflect debit card POS transaction at Starbucks Abdali",
        "body": "JO\nYou have a purchase transaction on Reflect card 4123*789 at STARBUCKS - ABDALI amount JOD 3.750 on 20/10/2026 15:30. Available balance JOD 45.250.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 3.75,
            "currency": "JOD",
            "accountMask": "4123*789",
            "merchantOrParty": "STARBUCKS - ABDALI",
            "balance": 45.25
        }
    })

    cases.append({
        "id": "TC_POS_REF_002",
        "category": "POSITIVE_CLIQ_OUTWARD",
        "provider": "Reflect",
        "sender": "Reflect",
        "description": "Reflect outward CliQ transfer to individual contact",
        "body": "JO\nOutward CliQ of JOD 15.000 debited from Reflect account 4123*789 to OMAR KHALED AL-MASRI. Available balance JOD 30.250.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 15.0,
            "currency": "JOD",
            "accountMask": "4123*789",
            "merchantOrParty": "OMAR KHALED AL-MASRI",
            "balance": 30.25
        }
    })

    cases.append({
        "id": "TC_POS_REF_003",
        "category": "POSITIVE_CLIQ_INWARD",
        "provider": "Reflect",
        "sender": "Reflect",
        "description": "Reflect inward CliQ transfer credited to digital wallet account",
        "body": "JO\nInward CliQ of JOD 20.000 credited to Reflect account 4123*789 from TARIQ AHMAD ZIAD. Available balance JOD 50.250.",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 20.0,
            "currency": "JOD",
            "accountMask": "4123*789",
            "merchantOrParty": "TARIQ AHMAD ZIAD",
            "balance": 50.25
        }
    })

    cases.append({
        "id": "TC_POS_REF_004",
        "category": "POSITIVE_REFUND_REVERSAL",
        "provider": "Reflect",
        "sender": "Reflect",
        "description": "Reflect refund credited from Amazon e-commerce return",
        "body": "JO\nA refund of JOD 12.400 from AMAZON.COM has been credited to your Reflect card 4123*789. Available balance JOD 60.250.",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 12.4,
            "currency": "JOD",
            "accountMask": "4123*789",
            "merchantOrParty": "AMAZON.COM",
            "balance": 60.25
        }
    })

    cases.append({
        "id": "TC_POS_REF_005",
        "category": "POSITIVE_CLIQ_INWARD",
        "provider": "Reflect",
        "sender": "Reflect",
        "description": "Reflect Arabic inward CliQ credit format with glued JOD",
        "body": "JO\nتم قيد دفعة كليك بمبلغ 10.000JOD إلى حسابك في ريفلكت 4123*789 من AYA MOHAMMAD. الرصيد 47.850JOD.",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 10.0,
            "currency": "JOD",
            "accountMask": "4123*789",
            "merchantOrParty": "AYA MOHAMMAD",
            "balance": 47.85
        }
    })

    cases.append({
        "id": "TC_POS_REF_006",
        "category": "POSITIVE_PURCHASE",
        "provider": "Reflect",
        "sender": "Reflect",
        "description": "Reflect purchase in SAR currency at Al-Baik",
        "body": "JO\nYou have a purchase transaction on Reflect card 4123*789 at AL-BAIK RIYADH amount SAR 45.00 on 18/10/2026. Available balance SAR 220.00.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 45.0,
            "currency": "SAR",
            "accountMask": "4123*789",
            "merchantOrParty": "AL-BAIK RIYADH",
            "balance": 220.0
        }
    })

    # =========================================================================
    # 4. POSITIVE TRANSACTIONS - BANK AL ETIHAD
    # =========================================================================
    cases.append({
        "id": "TC_POS_ETI_001",
        "category": "POSITIVE_PURCHASE",
        "provider": "Bank al Etihad",
        "sender": "EtihadBank",
        "description": "Etihad debit card purchase ending in 5412 at Carrefour City Mall",
        "body": "JO\nYou have made a purchase of JOD 4.750 with card ending in 5412 at CARREFOUR - CITY MALL on 20/10/2026. Available balance is JOD 120.450.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 4.75,
            "currency": "JOD",
            "accountMask": "ending in 5412",
            "merchantOrParty": "CARREFOUR - CITY MALL",
            "balance": 120.45
        }
    })

    cases.append({
        "id": "TC_POS_ETI_002",
        "category": "POSITIVE_CLIQ_OUTWARD",
        "provider": "Bank al Etihad",
        "sender": "EtihadBank",
        "description": "Etihad outward CliQ transfer debited from Acc *9123",
        "body": "JO\nOutward CliQ of JOD 15.000 debited from Acc. *9123 on 20/10/2026 to LAITH KHALED AL-OMARI. Available balance JOD 105.450.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 15.0,
            "currency": "JOD",
            "accountMask": "*9123",
            "merchantOrParty": "LAITH KHALED AL-OMARI",
            "balance": 105.45
        }
    })

    cases.append({
        "id": "TC_POS_ETI_003",
        "category": "POSITIVE_CLIQ_INWARD",
        "provider": "Bank al Etihad",
        "sender": "EtihadBank",
        "description": "Etihad inward CliQ transfer in USD currency from international recipient",
        "body": "JO\nInward CliQ of USD 50.00 credited to Acc. *9123 on 19/10/2026 from NOUR HADDAD. Available balance USD 155.45.",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 50.0,
            "currency": "USD",
            "accountMask": "*9123",
            "merchantOrParty": "NOUR HADDAD",
            "balance": 155.45
        }
    })

    cases.append({
        "id": "TC_POS_ETI_004",
        "category": "POSITIVE_PURCHASE",
        "provider": "Bank al Etihad",
        "sender": "EtihadBank",
        "description": "Etihad purchase in EUR currency for European online retail",
        "body": "JO\nYou have made a purchase of EUR 29.99 with card ending in 5412 at ZARA on 20/10/2026. Available balance is EUR 120.45.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 29.99,
            "currency": "EUR",
            "accountMask": "ending in 5412",
            "merchantOrParty": "ZARA",
            "balance": 120.45
        }
    })

    cases.append({
        "id": "TC_POS_ETI_005",
        "category": "POSITIVE_ATM_WITHDRAWAL",
        "provider": "Bank al Etihad",
        "sender": "EtihadBank",
        "description": "Etihad ATM cash withdrawal at Shmeisani Branch",
        "body": "JO\nATM cash withdrawal of JOD 40.000 from card ending 5412 at Shmeisani Branch on 17/10/2026. Available balance JOD 97.200.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 40.0,
            "currency": "JOD",
            "accountMask": "ending 5412",
            "merchantOrParty": "Shmeisani Branch",
            "balance": 97.2
        }
    })

    cases.append({
        "id": "TC_POS_ETI_006",
        "category": "POSITIVE_PURCHASE",
        "provider": "Bank al Etihad",
        "sender": "EtihadBank",
        "description": "Etihad Arabic debit transaction at Taj Cinemas",
        "body": "JO\nتم خصم مبلغ 8.500 JOD من بطاقتك المنتهية بـ 5412 لدى TAJ CINEMAS. الرصيد المتاح هو 88.700 JOD.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 8.5,
            "currency": "JOD",
            "accountMask": "5412",
            "merchantOrParty": "TAJ CINEMAS",
            "balance": 88.7
        }
    })

    cases.append({
        "id": "TC_POS_ETI_007",
        "category": "POSITIVE_REFUND_REVERSAL",
        "provider": "Bank al Etihad",
        "sender": "EtihadBank",
        "description": "Etihad monthly credit card spending cashback deposit",
        "body": "JO\nCashback of JOD 3.250 credited to your account *9123 for monthly card spending. Available balance JOD 91.950.",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 3.25,
            "currency": "JOD",
            "accountMask": "*9123",
            "merchantOrParty": None,
            "balance": 91.95
        }
    })

    # =========================================================================
    # 5. POSITIVE TRANSACTIONS - HOUSING BANK (HBTF)
    # =========================================================================
    cases.append({
        "id": "TC_POS_HOU_001",
        "category": "POSITIVE_PURCHASE",
        "provider": "Housing Bank",
        "sender": "HousingBank",
        "description": "Housing Bank Arabic POS card purchase with دينار currency unit",
        "body": "JO\nتمت حركة شراء بمبلغ 8.500 دينار على بطاقتك *3412 لدى أسواق السلام في 20/10/2026. الرصيد المتاح 185.250 دينار.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 8.5,
            "currency": "JOD",
            "accountMask": "*3412",
            "merchantOrParty": "أسواق السلام",
            "balance": 185.25
        }
    })

    cases.append({
        "id": "TC_POS_HOU_002",
        "category": "POSITIVE_CLIQ_OUTWARD",
        "provider": "Housing Bank",
        "sender": "HousingBank",
        "description": "Housing Bank English outward CliQ transfer",
        "body": "JO\nOutward Cliq of JOD 25.000 debited from Acc *7890 to TARIQ AHMAD via CliQ. Available balance JOD 160.250.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 25.0,
            "currency": "JOD",
            "accountMask": "*7890",
            "merchantOrParty": "TARIQ AHMAD",
            "balance": 160.25
        }
    })

    cases.append({
        "id": "TC_POS_HOU_003",
        "category": "POSITIVE_CLIQ_INWARD",
        "provider": "Housing Bank",
        "sender": "HousingBank",
        "description": "Housing Bank Arabic inward CliQ credit with د.أ notation",
        "body": "JO\nتم قيد حوالة كليك بمبلغ 60.000 د.أ لحسابك *7890 من MAJED AL-ALI. رصيدك المتاح هو 220.250 د.أ.",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 60.0,
            "currency": "JOD",
            "accountMask": "*7890",
            "merchantOrParty": "MAJED AL-ALI",
            "balance": 220.25
        }
    })

    cases.append({
        "id": "TC_POS_HOU_004",
        "category": "POSITIVE_ATM_WITHDRAWAL",
        "provider": "Housing Bank",
        "sender": "HousingBank",
        "description": "Housing Bank ATM cash withdrawal in Arabic with branch name",
        "body": "JO\nتم سحب مبلغ 50.000 دينار من صراف آلي فرع الجاردنز بواسطة بطاقتك. الرصيد المتاح 156.050 دينار.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 50.0,
            "currency": "JOD",
            "accountMask": None,
            "merchantOrParty": "صراف آلي فرع الجاردنز",
            "balance": 156.05
        }
    })

    cases.append({
        "id": "TC_POS_HOU_005",
        "category": "POSITIVE_BILL_PAYMENT",
        "provider": "Housing Bank",
        "sender": "HousingBank",
        "description": "Housing Bank eFAWATEERcom utility bill settlement",
        "body": "JO\nتم تسديد فاتورة عبر إي فواتيركم بمبلغ 35.000 د.أ من حسابك *7890 بنجاح. الرصيد المتاح 121.050 د.أ.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 35.0,
            "currency": "JOD",
            "accountMask": "*7890",
            "merchantOrParty": "إي فواتيركم",
            "balance": 121.05
        }
    })

    cases.append({
        "id": "TC_POS_HOU_006",
        "category": "POSITIVE_PURCHASE",
        "provider": "Housing Bank",
        "sender": "HousingBank",
        "description": "Housing Bank AED purchase at Dubai Mall",
        "body": "JO\nتمت حركة شراء بمبلغ 75.00 د.إ على بطاقتك *3412 لدى DUBAI MALL في 14/10/2026. الرصيد المتاح 300.00 د.إ.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 75.0,
            "currency": "AED",
            "accountMask": "*3412",
            "merchantOrParty": "DUBAI MALL",
            "balance": 300.0
        }
    })

    # =========================================================================
    # 6. POSITIVE TRANSACTIONS - ORANGE MONEY
    # =========================================================================
    cases.append({
        "id": "TC_POS_ORA_001",
        "category": "POSITIVE_CLIQ_OUTWARD",
        "provider": "Orange Money",
        "sender": "OrangeMoney",
        "description": "Orange Money wallet outward CliQ transfer to phone number contact",
        "body": "JO\nتم تحويل مبلغ 15.000 JOD بنجاح إلى محفظة 0771234567 (AHMAD SALEH) عبر كليك. رصيدك الحالي هو 32.500 JOD. رقم الحركة: 9102834.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 15.0,
            "currency": "JOD",
            "accountMask": None,
            "merchantOrParty": "AHMAD SALEH",
            "balance": 32.5
        }
    })

    cases.append({
        "id": "TC_POS_ORA_002",
        "category": "POSITIVE_CLIQ_INWARD",
        "provider": "Orange Money",
        "sender": "OrangeMoney",
        "description": "Orange Money inward CliQ transfer from peer contact",
        "body": "JO\nتم استلام مبلغ 30.000 JOD بنجاح إلى محفظتك من 0778899001 (YOUSEF AL-ALI) كليك. رصيدك الحالي هو 62.500 JOD. رقم المرجع: 7721092.",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 30.0,
            "currency": "JOD",
            "accountMask": None,
            "merchantOrParty": "YOUSEF AL-ALI",
            "balance": 62.5
        }
    })

    cases.append({
        "id": "TC_POS_ORA_003",
        "category": "POSITIVE_PURCHASE",
        "provider": "Orange Money",
        "sender": "OrangeMoney",
        "description": "Orange Money Arabic merchant payment to Carrefour Express",
        "body": "JO\nتم دفع مبلغ 6.750 JOD بنجاح إلى تاجر CARREFOUR EXPRESS بواسطة محفظة أورنج موني. رصيدك المتبقي 55.750 JOD. رقم العملية: 449012.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 6.75,
            "currency": "JOD",
            "accountMask": None,
            "merchantOrParty": "CARREFOUR EXPRESS",
            "balance": 55.75
        }
    })

    cases.append({
        "id": "TC_POS_ORA_004",
        "category": "POSITIVE_BILL_PAYMENT",
        "provider": "Orange Money",
        "sender": "OrangeMoney",
        "description": "Orange Money telecom bill payment via eFAWATEERcom",
        "body": "JO\nتم دفع فاتورة زين بنجاح بقيمة 12.000 JOD عبر إي فواتيركم من محفظتك. الرصيد المتاح 43.750 JOD. رقم الفاتورة: 8812903.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 12.0,
            "currency": "JOD",
            "accountMask": None,
            "merchantOrParty": "زين",
            "balance": 43.75
        }
    })

    cases.append({
        "id": "TC_POS_ORA_005",
        "category": "POSITIVE_ATM_DEPOSIT",
        "provider": "Orange Money",
        "sender": "OrangeMoney",
        "description": "Orange Money wallet cash-in deposit at authorized agent shop",
        "body": "JO\nتم إيداع مبلغ 50.000 JOD في محفظتك عبر وكيل أورنج موني (الاتصالات السريعة). رصيدك الجديد 93.750 JOD.",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 50.0,
            "currency": "JOD",
            "accountMask": None,
            "merchantOrParty": None,
            "balance": 93.75
        }
    })

    cases.append({
        "id": "TC_POS_ORA_006",
        "category": "POSITIVE_CLIQ_INWARD",
        "provider": "Orange Money",
        "sender": "OrangeMoney",
        "description": "Orange Money incoming international remittance in SAR",
        "body": "JO\nتم استلام حوالة واردة بمبلغ 250.00 SAR بنجاح إلى محفظتك. رصيدك الجديد 250.00 SAR.",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 250.0,
            "currency": "SAR",
            "accountMask": None,
            "merchantOrParty": None,
            "balance": 250.0
        }
    })

    # =========================================================================
    # 7. POSITIVE TRANSACTIONS - ZAIN CASH
    # =========================================================================
    cases.append({
        "id": "TC_POS_ZAI_001",
        "category": "POSITIVE_CLIQ_OUTWARD",
        "provider": "Zain Cash",
        "sender": "ZainCash",
        "description": "Zain Cash Arabic CliQ outward transfer with 2 decimals (45.20 JOD)",
        "body": "JO\nتم تحويل مبلغ 20.00 JOD بنجاح إلى 0791234567 (BILAL MAHMOUD) عبر كليك. رصيدك الحالي هو 45.20 JOD. الرقم المرجعي: 6019284.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 20.0,
            "currency": "JOD",
            "accountMask": None,
            "merchantOrParty": "BILAL MAHMOUD",
            "balance": 45.2
        }
    })

    cases.append({
        "id": "TC_POS_ZAI_002",
        "category": "POSITIVE_CLIQ_INWARD",
        "provider": "Zain Cash",
        "sender": "ZainCash",
        "description": "Zain Cash Arabic CliQ inward credit from individual in Arabic letters",
        "body": "JO\nتم استلام مبلغ 15.00 JOD في محفظتك بنجاح من سامي خليل عبر كليك. رصيدك الحالي هو 60.20 JOD. الرقم المرجعي: 7102938.",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 15.0,
            "currency": "JOD",
            "accountMask": None,
            "merchantOrParty": "سامي خليل",
            "balance": 60.2
        }
    })

    cases.append({
        "id": "TC_POS_ZAI_003",
        "category": "POSITIVE_PURCHASE",
        "provider": "Zain Cash",
        "sender": "ZainCash",
        "description": "Zain Cash Mastercard POS purchase at Cozmo supermarket",
        "body": "JO\nتمت عملية الشراء بنجاح بقيمة 8.50 JOD لدى تاجر COZMO سوبرماركت باستخدام بطاقة زين كاش. رصيدك المتبقي 51.70 JOD.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 8.5,
            "currency": "JOD",
            "accountMask": None,
            "merchantOrParty": "COZMO",
            "balance": 51.7
        }
    })

    cases.append({
        "id": "TC_POS_ZAI_004",
        "category": "POSITIVE_BILL_PAYMENT",
        "provider": "Zain Cash",
        "sender": "ZainCash",
        "description": "Zain Cash electricity bill payment via eFAWATEERcom with 3 decimals",
        "body": "JO\nتم دفع فاتورة الكهرباء بنجاح بقيمة 23.400 JOD من خلال خدمة إي فواتيركم. رصيدك الحالي هو 28.30 JOD.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 23.4,
            "currency": "JOD",
            "accountMask": None,
            "merchantOrParty": "الكهرباء",
            "balance": 28.3
        }
    })

    cases.append({
        "id": "TC_POS_ZAI_005",
        "category": "POSITIVE_ATM_WITHDRAWAL",
        "provider": "Zain Cash",
        "sender": "ZainCash",
        "description": "Zain Cash cardless cash withdrawal at partner ATM (Cairo Amman Bank)",
        "body": "JO\nتم سحب مبلغ 10.00 JOD نقداً من صراف آلي بنك القاهرة عمان بواسطة محفظتك. رصيدك الحالي 58.30 JOD.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 10.0,
            "currency": "JOD",
            "accountMask": None,
            "merchantOrParty": "صراف آلي بنك القاهرة عمان",
            "balance": 58.3
        }
    })

    # =========================================================================
    # 8. POSITIVE TRANSACTIONS - UWALLET (UMNIAH)
    # =========================================================================
    cases.append({
        "id": "TC_POS_UWA_001",
        "category": "POSITIVE_CLIQ_OUTWARD",
        "provider": "UWallet",
        "sender": "UWallet",
        "description": "UWallet Arabic outward CliQ transfer with recipient name in parentheses",
        "body": "JO\nتم تحويل مبلغ 12.000 JOD بنجاح إلى محفظة 0781234567 (MAHMOUD ADEL) عبر كليك. رصيدك الحالي هو 24.600 JOD. رقم المرجع: 5501923.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 12.0,
            "currency": "JOD",
            "accountMask": None,
            "merchantOrParty": "MAHMOUD ADEL",
            "balance": 24.6
        }
    })

    cases.append({
        "id": "TC_POS_UWA_002",
        "category": "POSITIVE_CLIQ_INWARD",
        "provider": "UWallet",
        "sender": "UWallet",
        "description": "UWallet Arabic inward CliQ transfer from contact",
        "body": "JO\nتم استلام دفعة كليك بمبلغ 25.000 JOD إلى محفظة UWallet الخاصة بك من رامي ناصر. رصيدك الحالي هو 49.600 JOD.",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 25.0,
            "currency": "JOD",
            "accountMask": None,
            "merchantOrParty": "رامي ناصر",
            "balance": 49.6
        }
    })

    cases.append({
        "id": "TC_POS_UWA_003",
        "category": "POSITIVE_PURCHASE",
        "provider": "UWallet",
        "sender": "UWallet",
        "description": "UWallet Mastercard POS purchase in English at Miles Supermarket",
        "body": "JO\nYou have completed a purchase of JOD 6.500 with your UWallet Mastercard at MILES SUPERMARKET. Available balance JOD 43.100.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 6.5,
            "currency": "JOD",
            "accountMask": None,
            "merchantOrParty": "MILES SUPERMARKET",
            "balance": 43.1
        }
    })

    cases.append({
        "id": "TC_POS_UWA_004",
        "category": "POSITIVE_BILL_PAYMENT",
        "provider": "UWallet",
        "sender": "UWallet",
        "description": "UWallet internet bill payment via eFAWATEERcom",
        "body": "JO\nتم تسديد فاتورة أمنية إنترنت بنجاح بقيمة 15.000 JOD عبر إي فواتيركم من محفظتك. الرصيد المتاح 28.100 JOD.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 15.0,
            "currency": "JOD",
            "accountMask": None,
            "merchantOrParty": "أمنية إنترنت",
            "balance": 28.1
        }
    })

    cases.append({
        "id": "TC_POS_UWA_005",
        "category": "POSITIVE_ATM_WITHDRAWAL",
        "provider": "UWallet",
        "sender": "UWallet",
        "description": "UWallet cash withdrawal via agent",
        "body": "JO\nتم سحب مبلغ 15.000 JOD نقداً من محفظة UWallet عبر وكيل معتمد بنجاح. رصيدك المتبقي 63.100 JOD.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 15.0,
            "currency": "JOD",
            "accountMask": None,
            "merchantOrParty": "وكيل معتمد",
            "balance": 63.1
        }
    })

    # =========================================================================
    # 9. POSITIVE TRANSACTIONS - JORDAN ISLAMIC BANK (JIB)
    # =========================================================================
    cases.append({
        "id": "TC_POS_JIB_001",
        "category": "POSITIVE_PURCHASE",
        "provider": "Jordan Islamic Bank",
        "sender": "JIB",
        "description": "Jordan Islamic Bank debit card purchase at Carrefour in د.أ currency",
        "body": "تمت حركة شراء بمبلغ 18.750 د.أ بواسطة بطاقتك المنتهية بـ *5678 لدى CARREFOUR. الرصيد المتاح: 145.250 د.أ.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 18.75,
            "currency": "JOD",
            "accountMask": "*5678",
            "merchantOrParty": "CARREFOUR",
            "balance": 145.25
        }
    })

    cases.append({
        "id": "TC_POS_JIB_002",
        "category": "POSITIVE_CLIQ_INWARD",
        "provider": "Jordan Islamic Bank",
        "sender": "JIB",
        "description": "Jordan Islamic Bank inward CliQ transfer credit",
        "body": "تم قيد حوالة كليك واردة بمبلغ 40.000 د.أ لحسابك *1234 من TARIQ AHMAD. رصيدك المتاح 185.250 د.أ.",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 40.0,
            "currency": "JOD",
            "accountMask": "*1234",
            "merchantOrParty": "TARIQ AHMAD",
            "balance": 185.25
        }
    })

    cases.append({
        "id": "TC_POS_JIB_003",
        "category": "POSITIVE_CLIQ_OUTWARD",
        "provider": "Jordan Islamic Bank",
        "sender": "JIB",
        "description": "Jordan Islamic Bank outward CliQ transfer debit",
        "body": "تم تحويل دفعة كليك صادرة بمبلغ 15.000 د.أ من حسابك *1234 إلى OMAR KHALED. الرصيد المتاح 170.250 د.أ.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 15.0,
            "currency": "JOD",
            "accountMask": "*1234",
            "merchantOrParty": "OMAR KHALED",
            "balance": 170.25
        }
    })

    cases.append({
        "id": "TC_POS_JIB_004",
        "category": "POSITIVE_ATM_WITHDRAWAL",
        "provider": "Jordan Islamic Bank",
        "sender": "JIB",
        "description": "Jordan Islamic Bank ATM withdrawal at Shmeisani branch",
        "body": "تم قيد حركة سحب نقدي بمبلغ 50.000 د.أ من بطاقتك المنتهية برقم *4321 من صراف آلي فرع الشميساني. الرصيد المتاح 310.500 د.أ.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 50.0,
            "currency": "JOD",
            "accountMask": "*4321",
            "merchantOrParty": "صراف آلي فرع الشميساني",
            "balance": 310.5
        }
    })

    cases.append({
        "id": "TC_POS_JIB_005",
        "category": "POSITIVE_PURCHASE",
        "provider": "Jordan Islamic Bank",
        "sender": "JIB",
        "description": "Jordan Islamic Bank international purchase in USD on Amazon",
        "body": "تمت حركة شراء دولية بمبلغ 45.00 USD على بطاقتك *5678 لدى AMAZON.COM في 15/10/2026. الرصيد المتاح 410.00 USD.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 45.0,
            "currency": "USD",
            "accountMask": "*5678",
            "merchantOrParty": "AMAZON.COM",
            "balance": 410.0
        }
    })

    cases.append({
        "id": "TC_POS_JIB_006",
        "category": "POSITIVE_REFUND_REVERSAL",
        "provider": "Jordan Islamic Bank",
        "sender": "JIB",
        "description": "Jordan Islamic Bank refund credit from merchant",
        "body": "تم قيد حركة استرداد / إعادة قيد بمبلغ 18.750 د.أ إلى بطاقتك *5678 من CARREFOUR. الرصيد المتاح: 164.000 د.أ.",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 18.75,
            "currency": "JOD",
            "accountMask": "*5678",
            "merchantOrParty": "CARREFOUR",
            "balance": 164.0
        }
    })

    # =========================================================================
    # 10. POSITIVE TRANSACTIONS - CAIRO AMMAN BANK (CAB)
    # =========================================================================
    cases.append({
        "id": "TC_POS_CAB_001",
        "category": "POSITIVE_PURCHASE",
        "provider": "Cairo Amman Bank",
        "sender": "CAB",
        "description": "Cairo Amman Bank English debit purchase at Safeway with ending in 8891 mask",
        "body": "You have a debit transaction of JOD 22.500 on card ending in 8891 at SAFEWAY on 20/10/2026. Available balance JOD 140.200.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 22.5,
            "currency": "JOD",
            "accountMask": "ending in 8891",
            "merchantOrParty": "SAFEWAY",
            "balance": 140.2
        }
    })

    cases.append({
        "id": "TC_POS_CAB_002",
        "category": "POSITIVE_CLIQ_INWARD",
        "provider": "Cairo Amman Bank",
        "sender": "CAB",
        "description": "Cairo Amman Bank Arabic inward CliQ payment credit",
        "body": "تم قيد دفعة كليك بمبلغ 35.000 JOD لحسابك *4412 من BILAL OTHMAN. الرصيد 175.200 JOD.",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 35.0,
            "currency": "JOD",
            "accountMask": "*4412",
            "merchantOrParty": "BILAL OTHMAN",
            "balance": 175.2
        }
    })

    cases.append({
        "id": "TC_POS_CAB_003",
        "category": "POSITIVE_CLIQ_OUTWARD",
        "provider": "Cairo Amman Bank",
        "sender": "CAB",
        "description": "Cairo Amman Bank outward CliQ transfer to individual",
        "body": "Outward CliQ transfer of JOD 10.000 debited from Acc *4412 to HAMZA OMAR. Available balance JOD 165.200.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 10.0,
            "currency": "JOD",
            "accountMask": "*4412",
            "merchantOrParty": "HAMZA OMAR",
            "balance": 165.2
        }
    })

    cases.append({
        "id": "TC_POS_CAB_004",
        "category": "POSITIVE_PURCHASE",
        "provider": "Cairo Amman Bank",
        "sender": "CAB",
        "description": "Cairo Amman Bank international purchase in AED at Dubai Duty Free",
        "body": "CAB Alert: Purchase of AED 85.50 at DUBAI DUTY FREE on card ending 8891. Available balance AED 350.00.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 85.5,
            "currency": "AED",
            "accountMask": "ending 8891",
            "merchantOrParty": "DUBAI DUTY FREE",
            "balance": 350.0
        }
    })

    cases.append({
        "id": "TC_POS_CAB_005",
        "category": "POSITIVE_ATM_WITHDRAWAL",
        "provider": "Cairo Amman Bank",
        "sender": "CAB",
        "description": "Cairo Amman Bank cash withdrawal at 7th Circle branch ATM",
        "body": "تم سحب مبلغ 60.000 دينار من بطاقتك *8891 من صراف آلي فرع الدوار السابع. الرصيد المتاح 105.200 دينار.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 60.0,
            "currency": "JOD",
            "accountMask": "*8891",
            "merchantOrParty": "صراف آلي فرع الدوار السابع",
            "balance": 105.2
        }
    })

    cases.append({
        "id": "TC_POS_CAB_006",
        "category": "POSITIVE_REFUND_REVERSAL",
        "provider": "Cairo Amman Bank",
        "sender": "CAB",
        "description": "Cairo Amman Bank refund credit from Safeway",
        "body": "A refund of JOD 22.500 from SAFEWAY has been credited to your card ending in 8891. Available balance JOD 162.700.",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 22.5,
            "currency": "JOD",
            "accountMask": "ending in 8891",
            "merchantOrParty": "SAFEWAY",
            "balance": 162.7
        }
    })


    # =========================================================================
    # 11. ADVERSARIAL: CONVERSATIONAL CHAT NOISE (MENTIONING MONEY / CLIQ / BANKS)
    # =========================================================================
    chat_noise_samples = [
        ("TC_ADV_CHAT_001", "Reflect", "hey I just cliq-ed you 15 JOD check your balance"),
        ("TC_ADV_CHAT_002", "ArabiBank", "حولتلك 20 دينار كليك شيك عليها بالله وصلتك ولا لسا؟"),
        ("TC_ADV_CHAT_003", "EtihadBank", "did you finish the purchase at Zara? How much was the total?"),
        ("TC_ADV_CHAT_004", "OrangeMoney", "ابعثلي رقم الكليك تبعك ضروري عشان احولك حق الغدا 12 دينار"),
        ("TC_ADV_CHAT_005", "CapitalBank", "can you send me 15 JOD on cliq to pay the driver now?"),
        ("TC_ADV_CHAT_006", "ZainCash", "check your account, I just sent 20 JOD on Zain Cash"),
        ("TC_ADV_CHAT_007", "HousingBank", "معي 50 دينار كاش مين بده كليك ويبعتلي اياهم؟"),
        ("TC_ADV_CHAT_008", "UWallet", "حولت 5 دنانير بالغلط رجعلي اياهم على كليك لو سمحت"),
        ("TC_ADV_CHAT_009", "JIB", "I transferred you 35 JOD for yesterday's dinner at Reem Shawerma"),
        ("TC_ADV_CHAT_010", "CAB", "اشتريت من زارا ب 25 دينار مبارح طلع السعر غالي"),
        ("TC_ADV_CHAT_011", "Reflect", "the bill was 14.5 JOD each at Starbucks, let me know when you cliq"),
        ("TC_ADV_CHAT_012", "OrangeMoney", "رحت على كارفور واشتريت أغراض ب 18 ليرة وما كفى الكاش"),
        ("TC_ADV_CHAT_013", "ArabiBank", "send me the transaction receipt or screenshot from Arab Bank app"),
        ("TC_ADV_CHAT_014", "ZainCash", "كم رصيدك هسا في المحفظة؟ بدي احولك 50 دينار"),
        ("TC_ADV_CHAT_015", "CapitalBank", "دفعت الحساب للمطعم 30 دينار ولا ادفع انا؟"),
        ("TC_ADV_CHAT_016", "EtihadBank", "can you transfer 25 USD to my paypal or bank account please?"),
        ("TC_ADV_CHAT_017", "HousingBank", "مين يحولي 5 ليرات كليك وابعثلو رصيد زين هسا؟"),
        ("TC_ADV_CHAT_018", "UWallet", "عملت سحب من الصراف وما طلع مصاري بس انخصمت من الحساب"),
        ("TC_ADV_CHAT_019", "EtihadBank", "حولتلك 100 دينار من بنك الاتحاد لحسابك بالاسكان شيك عليها"),
        ("TC_ADV_CHAT_020", "CAB", "did you receive the transfer of JOD 45.000 on CliQ?"),
        ("TC_ADV_CHAT_021", "Reflect", "someone just told me to cliq 10 JOD to this number"),
        ("TC_ADV_CHAT_022", "ArabiBank", "did you deposit the cash into the ATM machine yesterday?"),
        ("TC_ADV_CHAT_023", "OrangeMoney", "شو صار بموضوع الحوالة؟ حولتلي ولا لسا بتستنى؟"),
        ("TC_ADV_CHAT_024", "CapitalBank", "I am standing at the cashier at H&M, send 30 JOD quickly"),
        ("TC_ADV_CHAT_025", "ZainCash", "الرصيد عندي صفر وما بقدر احول اي شي كليك")
    ]

    for cid, s, b in chat_noise_samples:
        cases.append({
            "id": cid,
            "category": "ADVERSARIAL_CHAT_NOISE",
            "provider": "Personal / Conversational",
            "sender": s,
            "description": "Conversational chat message mentioning amounts, CliQ, banks, or merchant purchases",
            "body": b,
            "expected": {
                "isValidTransaction": False,
                "type": None,
                "amount": None,
                "currency": None,
                "accountMask": None,
                "merchantOrParty": None,
                "balance": None
            }
        })


    # =========================================================================
    # 12. ADVERSARIAL: PERSONAL SENDER PHONE NUMBERS
    # =========================================================================
    personal_sender_samples = [
        ("TC_ADV_SND_001", "+962791234567", "JO\nYou have a purchase transaction on account 1234*678 from ZAIN MARKET amount JOD 5.450 on 20/10/2026. Balance JOD 39.132."),
        ("TC_ADV_SND_002", "0798765432", "JO\nتم تحويل مبلغ 15.000 JOD بنجاح إلى محفظة 0771234567 (AHMAD SALEH) عبر كليك. رصيدك الحالي هو 32.500 JOD."),
        ("TC_ADV_SND_003", "00962788123456", "JO\nYou have made a purchase of JOD 4.750 with card ending in 5412 at CARREFOUR. Available balance is JOD 120.450."),
        ("TC_ADV_SND_004", "+962775551234", "JO\nتم استلام مبلغ 30.000 JOD بنجاح إلى محفظتك من YOUSEF AL-ALI كليك. رصيدك الحالي هو 62.500 JOD."),
        ("TC_ADV_SND_005", "078-123-4567", "Outward Cliq of JOD 5.100 debited from Acc. No xxxx833 to ANMAR ALQUDAH. Available balance JOD 0.000"),
        ("TC_ADV_SND_006", "+962 7 9123 4567", "JO\nJOD2.000 has been debited from 1234*678 to BAKER NASIM as CliQ transfer Balance 45.582JOD"),
        ("TC_ADV_SND_007", "+12025550192", "You have a debit transaction of JOD 22.500 on card ending in 8891 at SAFEWAY. Available balance JOD 140.200."),
        ("TC_ADV_SND_008", "0791112233", "تمت حركة شراء بمبلغ 18.750 د.أ بواسطة بطاقتك المنتهية بـ *5678 لدى CARREFOUR. الرصيد المتاح: 145.250 د.أ."),
        ("TC_ADV_SND_009", "+962790001122", "JO\n30JOD has been debited from your account 1234*678 as an ATM Withdrawal. Available balance 20.134."),
        ("TC_ADV_SND_010", "00962795554433", "JO\nتمت حركة شراء بمبلغ 8.500 دينار على بطاقتك *3412 لدى أسواق السلام. الرصيد المتاح 185.250 دينار."),
        ("TC_ADV_SND_011", "+962780009988", "Inward Cliq of JOD 50.000 credited to Acc. *9123 on 19/10/2026 from NOUR HADDAD. Available balance JOD 155.450."),
        ("TC_ADV_SND_012", "0770001122", "JO\nتم دفع مبلغ 6.750 JOD بنجاح إلى تاجر CARREFOUR EXPRESS. رصيدك المتبقي 55.750 JOD.")
    ]

    for cid, s, b in personal_sender_samples:
        cases.append({
            "id": cid,
            "category": "ADVERSARIAL_PERSONAL_SENDER",
            "provider": "Personal Phone Number",
            "sender": s,
            "description": f"Legitimate-looking bank transaction text received from personal phone number {s} (MUST be rejected)",
            "body": b,
            "expected": {
                "isValidTransaction": False,
                "type": None,
                "amount": None,
                "currency": None,
                "accountMask": None,
                "merchantOrParty": None,
                "balance": None
            }
        })


    # =========================================================================
    # 13. ADVERSARIAL: 3DS PURCHASE AUTHORIZATION OTPs (TRAP CASES)
    # =========================================================================
    otp_3ds_samples = [
        ("TC_ADV_3DS_001", "ArabiBank", "JO\nDO NOT SHARE THIS CODE.\nOne Time Password: 167713\nPurpose: Purchase of amount 9 JOD from PRIME CINEMAS AL ABDALI\nFees apply on international transactions."),
        ("TC_ADV_3DS_002", "CapitalBank", "Your OTP is 875560 for transfer JOD 5.100 Please dont share.\nzHRFGVInIZI"),
        ("TC_ADV_3DS_003", "EtihadBank", "JO\nOne-Time Password: 391820 for your online purchase of JOD 25.000 at SHEIN.COM. Valid for 3 mins. Never share your OTP."),
        ("TC_ADV_3DS_004", "Reflect", "JO\nOne Time Password (OTP): 719204 for online purchase of JOD 15.500 at SHEIN.COM. Valid for 3 mins. Do not share."),
        ("TC_ADV_3DS_005", "HousingBank", "JO\nOne Time Password (OTP) for online purchase of JOD 28.500 at SHEIN is 812904. Do not share."),
        ("TC_ADV_3DS_006", "OrangeMoney", "JO\nرمز التأكيد لعملية الشراء عبر الإنترنت هو: 902144 بمبلغ 18.500 JOD لدى CARREFOUR. لا تشارك الرمز لحماية حسابك."),
        ("TC_ADV_3DS_007", "ZainCash", "JO\nرمز الأمان لعملية الشراء عبر الإنترنت هو: 491028 بمبلغ 12.00 JOD من TALABAT. صالح لمدة دقيقتين."),
        ("TC_ADV_3DS_008", "UWallet", "JO\nYour OTP for online payment is 482015 for amount JOD 14.200 at TALABAT. Valid for 2 minutes. Do not share."),
        ("TC_ADV_3DS_009", "JIB", "رمز الأمان لعملية الشراء عبر الإنترنت هو: 739102 بمبلغ 24.500 USD من متجر AMAZON.COM. لا تفصح عن هذا الرمز."),
        ("TC_ADV_3DS_010", "CAB", "One Time Password: 839201 for online transaction of JOD 19.990 at TALABAT. Valid for 2 mins. Do not share."),
        ("TC_ADV_3DS_011", "EtihadBank", "JO\nDO NOT DISCLOSE. OTP 991822 for online transaction of EUR 45.00 at ASOS UK. Valid for 5 minutes."),
        ("TC_ADV_3DS_012", "ArabiBank", "JO\nYour Arabi Online authorization passcode is 582910 for transfer of JOD 100.000 to CliQ contact. Never share.")
    ]

    for cid, s, b in otp_3ds_samples:
        cases.append({
            "id": cid,
            "category": "ADVERSARIAL_OTP_3DS_PURCHASE",
            "provider": s,
            "sender": s,
            "description": "3DS purchase verification OTP message explicitly containing transaction amount and merchant name",
            "body": b,
            "expected": {
                "isValidTransaction": False,
                "type": None,
                "amount": None,
                "currency": None,
                "accountMask": None,
                "merchantOrParty": None,
                "balance": None
            }
        })


    # =========================================================================
    # 14. ADVERSARIAL: LOGIN OTPs & 2FA ACTIVATION CODES
    # =========================================================================
    login_otp_samples = [
        ("TC_ADV_LOG_001", "ArabiBank", "JO\nTo continue with your account login process, enter the code 440589. Please ensure not to share your activation code with anyone."),
        ("TC_ADV_LOG_002", "CapitalBank", "201127 هو رمز المرور لمرة واحدة (OTP) لإضافة البطاقة الخاصة بك إلى المحفظة الرقمية، يرجى عدم مشاركته مع أي شخص، صالح لمدة 5 دقائق."),
        ("TC_ADV_LOG_003", "EtihadBank", "JO\nYour verification code is 829104 to log in to Bank al Etihad mobile banking. Please do not share this code."),
        ("TC_ADV_LOG_004", "Reflect", "JO\nYour Reflect verification code is 382910. Do not share this code with anyone, including Reflect support."),
        ("TC_ADV_LOG_005", "HousingBank", "JO\nرمز التحقق لمرة واحدة (OTP) لتسجيل الدخول إلى تطبيق إسكان موبايل هو: 519203. لا تشارك هذا الرمز مطلقاً."),
        ("TC_ADV_LOG_006", "OrangeMoney", "JO\nرمز التحقق لمرة واحدة (OTP) لتسجيل الدخول إلى محفظة Orange Money هو: 481920. يرجى عدم مشاركة هذا الرمز مع أي شخص."),
        ("TC_ADV_LOG_007", "ZainCash", "JO\nرمز التحقق لمرة واحدة في زين كاش هو: 582019 لإتمام عملية تسجيل الدخول. لا تشارك هذا الرمز مع أي كان."),
        ("TC_ADV_LOG_008", "UWallet", "JO\nرمز التحقق الخاص بك في محفظة UWallet هو: 610928 لإتمام تسجيل الدخول. لا تفصح عن هذا الرمز لأي جهة كانت."),
        ("TC_ADV_LOG_009", "JIB", "رمز التحقق لمرة واحدة (OTP) لتسجيل الدخول إلى تطبيق إسلامي موبايل هو: 492018. لا تشارك هذا الرمز مع أحد."),
        ("TC_ADV_LOG_010", "CAB", "CAB: Your OTP for mobile banking login is 619283. Do not share with anyone.")
    ]

    for cid, s, b in login_otp_samples:
        cases.append({
            "id": cid,
            "category": "ADVERSARIAL_OTP_LOGIN",
            "provider": s,
            "sender": s,
            "description": "Standard login, authentication, or tokenization OTP / verification code",
            "body": b,
            "expected": {
                "isValidTransaction": False,
                "type": None,
                "amount": None,
                "currency": None,
                "accountMask": None,
                "merchantOrParty": None,
                "balance": None
            }
        })


    # =========================================================================
    # 15. ADVERSARIAL: DECLINED / FAILED TRANSACTIONS
    # =========================================================================
    declined_samples = [
        ("TC_ADV_DEC_001", "CapitalBank", "حركة مرفوضة على بطاقتك المنتهية ب 8150 بقيمة JOD 5.000 بسبب عدم كفاية الرصيد, للمزيد اتصل على 065100220"),
        ("TC_ADV_DEC_002", "EtihadBank", "JO\nTransaction declined: purchase of JOD 120.000 on card ending 5412 at IKEA due to insufficient funds."),
        ("TC_ADV_DEC_003", "Reflect", "JO\nTransaction declined on Reflect card 4123*789 for amount JOD 85.000 at ZARA due to insufficient funds."),
        ("TC_ADV_DEC_004", "HousingBank", "JO\nحركة شراء مرفوضة بقيمة 150.000 د.أ على بطاقتك *3412 بسبب عدم كفاية الرصيد."),
        ("TC_ADV_DEC_005", "OrangeMoney", "JO\nفشلت عملية الدفع بمبلغ 85.000 JOD بسبب عدم توفر رصيد كافٍ في محفظة أورنج موني الخاصة بك."),
        ("TC_ADV_DEC_006", "ZainCash", "JO\nحركة غير مكتملة: تم رفض عملية التحويل بمبلغ 75.00 JOD بسبب عدم كفاية الرصيد في محفظة زين كاش."),
        ("TC_ADV_DEC_007", "UWallet", "JO\nتم رفض عملية الشراء بقيمة 60.000 JOD على بطاقة UWallet لعدم توفر رصيد كافٍ في المحفظة."),
        ("TC_ADV_DEC_008", "CAB", "حركة مرفوضة: تم رفض حركة شراء بمبلغ 250.000 JOD على بطاقتك المنتهية بـ 8891 بسبب تجاوز السقف أو عدم كفاية الرصيد."),
        ("TC_ADV_DEC_009", "JIB", "حركة شراء مرفوضة على بطاقتك المنتهية بـ *5678 بقيمة 120.000 د.أ لعدم كفاية الرصيد."),
        ("TC_ADV_DEC_010", "ArabiBank", "JO\nTransaction failed: Insufficient funds for debit of JOD 200.000 on account 1234*678 at LEADERS."),
        ("TC_ADV_DEC_011", "EtihadBank", "JO\nDeclined: Your CliQ transfer of JOD 30.000 was unsuccessful due to recipient account restriction."),
        ("TC_ADV_DEC_012", "OrangeMoney", "JO\nنعتذر، لم تتم عملية الشراء بمبلغ 25.000 JOD لعدم كفاية الرصيد.")
    ]

    for cid, s, b in declined_samples:
        cases.append({
            "id": cid,
            "category": "ADVERSARIAL_DECLINED_FAILED",
            "provider": s,
            "sender": s,
            "description": "Declined, rejected, or failed financial transaction notification due to insufficient balance or limits",
            "body": b,
            "expected": {
                "isValidTransaction": False,
                "type": None,
                "amount": None,
                "currency": None,
                "accountMask": None,
                "merchantOrParty": None,
                "balance": None
            }
        })


    # =========================================================================
    # 16. ADVERSARIAL: SYSTEM MAINTENANCE & ANNOUNCEMENTS
    # =========================================================================
    announcement_samples = [
        ("TC_ADV_ANN_001", "CapitalBank", "يرجى العلم بأن خدمة كليك ستتوقف مؤقتاً لغايات تحديث الأنظمة يوم الجمعة 8/7 من الساعة 2:00 وحتى 2:30 بعد منتصف الليل, مستعدون لخدمتكم."),
        ("TC_ADV_ANN_002", "EtihadBank", "JO\nPlease note that CliQ services will be temporarily unavailable on Friday from 02:00 to 04:00 AM for scheduled maintenance."),
        ("TC_ADV_ANN_003", "Reflect", "JO\nReflect services including CliQ transfers will undergo scheduled system maintenance on Friday from 03:00 AM to 05:00 AM."),
        ("TC_ADV_ANN_004", "HousingBank", "JO\nيرجى العلم بأن خدمة كليك ستكون غير متاحة مؤقتاً يوم الجمعة من 02:00 إلى 03:30 صباحاً لغايات الصيانة الدورية."),
        ("TC_ADV_ANN_005", "OrangeMoney", "JO\nيرجى العلم بأن خدمات كليك ستخضع لأعمال تحديث وتطوير يوم السبت من الساعة 02:00 ولغاية 04:00 صباحاً."),
        ("TC_ADV_ANN_006", "ZainCash", "JO\nتنويه: ستتوقف خدمات التحويل والدفع عبر كليك مؤقتاً لتحديث الأنظمة فجر يوم الجمعة من 01:00 حتى 03:00 صباحاً."),
        ("TC_ADV_ANN_007", "UWallet", "JO\nيرجى العلم بأنه سيتم إجراء تحديث لأنظمة خدمة كليك يوم السبت القادم من 2:30 إلى 4:00 فجراً."),
        ("TC_ADV_ANN_008", "ArabiBank", "Your eStatement has been issued for Account 1234*678. Please login to Arabi Online or Arab Bank App to view it."),
        ("TC_ADV_ANN_009", "EtihadBank", "JO\nYour card ending in 5412 was successfully added to Apple Pay. If you did not make this request, call +96265600444."),
        ("TC_ADV_ANN_010", "HousingBank", "صدر كشف حسابك الإلكتروني لشهر أيلول، يمكنك الاطلاع عليه عبر تطبيق إسكان أونلاين."),
        ("TC_ADV_ANN_011", "JIB", "يرجى العلم بأن القنوات الرقمية ستخضع لأعمال صيانة مبرمجة يوم السبت من الساعة 1:00 إلى 3:00 فجراً."),
        ("TC_ADV_ANN_012", "CAB", "تم تفعيل بطاقتك بنجاح على Apple Pay. إذا لم تقم بهذه العملية يرجى التواصل فوراً مع مركز الاتصال.")
    ]

    for cid, s, b in announcement_samples:
        cases.append({
            "id": cid,
            "category": "ADVERSARIAL_MAINTENANCE_DOWNTIME",
            "provider": s,
            "sender": s,
            "description": "System maintenance, scheduled downtime, eStatement notification, or Apple Pay pairing confirmation",
            "body": b,
            "expected": {
                "isValidTransaction": False,
                "type": None,
                "amount": None,
                "currency": None,
                "accountMask": None,
                "merchantOrParty": None,
                "balance": None
            }
        })


    # =========================================================================
    # 17. ADVERSARIAL: MARKETING PROMOTIONS & BONUS REWARDS
    # =========================================================================
    promo_samples = [
        ("TC_ADV_PRM_001", "ArabiBank", "JO\n20 Points were redeemed from your \"Arabi Points\" account as a reward voucher. For more information, login to Arab Bank app or the online banking service"),
        ("TC_ADV_PRM_002", "ArabiBank", "Your Talabat Voucher Code is : WSSHKHNFN7. 20 Points from your Arabi Points were redeemed as a Talabat voucher. For more information, please visit our website: www.arabbank.jo"),
        ("TC_ADV_PRM_003", "Reflect", "JO\nCongratulations! You have received 50 bonus Reflect Coins for completing 5 CliQ transfers this week. View rewards in app."),
        ("TC_ADV_PRM_004", "OrangeMoney", "اشحن خطك الخلوي بقيمة 5 دنانير أو أكثر عبر تطبيق Orange Money واحصل على 20% رصيد مجاني إضافي! العرض ساري حتى نهاية الشهر."),
        ("TC_ADV_PRM_005", "ZainCash", "استخدم بطاقة زين كاش ماستركارد في مشترياتك واحصل على خصم فوري 15% لدى المحال المشاركة طيلة عطلة نهاية الأسبوع!"),
        ("TC_ADV_PRM_006", "UWallet", "ادفع فواتيرك عبر إي فواتيركم باستخدام محفظة UWallet وادخل السحب على جوائز أسبوعية قيّمة تصل إلى 500 دينار!"),
        ("TC_ADV_PRM_007", "EtihadBank", "استمتع باسترداد نقدي لغاية 10% عند استخدام بطاقتك الائتمانية في المطاعم خلال عطلة نهاية الأسبوع! للمزيد زوروا موقعنا."),
        ("TC_ADV_PRM_008", "HousingBank", "احصل على تمويل شخصي يصل إلى 25000 دينار بفترة سداد ميسرة وبدون تحويل راتب! قدم طلبك الآن عبر التطبيق."),
        ("TC_ADV_PRM_009", "JIB", "استفد من تمويل مرابحة السيارات بنسب أرباح منافسة وإجراءات سريعة. تفضل بزيارة أقرب فرع للبنك الإسلامي الأردني."),
        ("TC_ADV_PRM_010", "CAB", "قدم على بطاقتك الائتمانية الآن واحصل على استرداد نقدي 5% على جميع مشترياتك لمدة ثلاثة أشهر!"),
        ("TC_ADV_PRM_011", "Reflect", "JO\nDouble your reward points every Tuesday when you shop with your Reflect debit card. Tap to learn more!"),
        ("TC_ADV_PRM_012", "OrangeMoney", "وفر 50% على اشتراكك الشهري عند الدفع بواسطة Orange Money! للاشتراك زوروا موقعنا.")
    ]

    for cid, s, b in promo_samples:
        cases.append({
            "id": cid,
            "category": "ADVERSARIAL_MARKETING_PROMO",
            "provider": s,
            "sender": s,
            "description": "Marketing offer, bonus reward voucher, discounts advertisement, or loan promotional campaign",
            "body": b,
            "expected": {
                "isValidTransaction": False,
                "type": None,
                "amount": None,
                "currency": None,
                "accountMask": None,
                "merchantOrParty": None,
                "balance": None
            }
        })


    # =========================================================================
    # 18. EDGE CASES: VARIED DECIMAL & CURRENCY FORMATS
    # =========================================================================
    cases.append({
        "id": "TC_EDG_DEC_001",
        "category": "EDGE_CASE_DECIMAL_FORMATS",
        "provider": "Arab Bank",
        "sender": "ArabiBank",
        "description": "Integer amount glued to currency without spaces (12JOD)",
        "body": "JO\nYou have a purchase transaction on account 1234*678 from ZAIN MARKET amount 12JOD on 20/10/2026. Balance 27.132JOD.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 12.0,
            "currency": "JOD",
            "accountMask": "1234*678",
            "merchantOrParty": "ZAIN MARKET",
            "balance": 27.132
        }
    })

    cases.append({
        "id": "TC_EDG_DEC_002",
        "category": "EDGE_CASE_DECIMAL_FORMATS",
        "provider": "Housing Bank",
        "sender": "HousingBank",
        "description": "One-decimal Arabic amount format (10.5 د.أ)",
        "body": "JO\nتمت حركة شراء بمبلغ 10.5 د.أ على بطاقتك *3412 لدى أسواق السلام في 20/10/2026. الرصيد المتاح 185.0 د.أ.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 10.5,
            "currency": "JOD",
            "accountMask": "*3412",
            "merchantOrParty": "أسواق السلام",
            "balance": 185.0
        }
    })

    cases.append({
        "id": "TC_EDG_DEC_003",
        "category": "EDGE_CASE_DECIMAL_FORMATS",
        "provider": "Bank al Etihad",
        "sender": "EtihadBank",
        "description": "Prefix currency without space (JOD5.450)",
        "body": "JO\nYou have made a purchase of JOD5.450 with card ending in 5412 at TALABAT on 20/10/2026. Available balance is JOD120.450.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 5.45,
            "currency": "JOD",
            "accountMask": "ending in 5412",
            "merchantOrParty": "TALABAT",
            "balance": 120.45
        }
    })

    cases.append({
        "id": "TC_EDG_DEC_004",
        "category": "EDGE_CASE_DECIMAL_FORMATS",
        "provider": "Cairo Amman Bank",
        "sender": "CAB",
        "description": "Integer amount with Arabic دينار suffix without space (50دينار)",
        "body": "تم سحب مبلغ 50دينار من بطاقتك *8891 من صراف آلي فرع الدوار السابع. الرصيد المتاح: 100دينار.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 50.0,
            "currency": "JOD",
            "accountMask": "*8891",
            "merchantOrParty": "صراف آلي فرع الدوار السابع",
            "balance": 100.0
        }
    })

    cases.append({
        "id": "TC_EDG_DEC_005",
        "category": "EDGE_CASE_DECIMAL_FORMATS",
        "provider": "Reflect",
        "sender": "Reflect",
        "description": "USD currency with standard 2 decimal format",
        "body": "JO\nYou have a purchase transaction on Reflect card 4123*789 at NETFLIX.COM amount USD 14.99 on 20/10/2026. Available balance USD 120.50.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 14.99,
            "currency": "USD",
            "accountMask": "4123*789",
            "merchantOrParty": "NETFLIX.COM",
            "balance": 120.50
        }
    })

    cases.append({
        "id": "TC_EDG_DEC_006",
        "category": "EDGE_CASE_DECIMAL_FORMATS",
        "provider": "Bank al Etihad",
        "sender": "EtihadBank",
        "description": "Currency symbol $ before amount",
        "body": "JO\nYou have made a purchase of $24.50 with card ending in 5412 at AMAZON on 20/10/2026. Available balance is $150.00.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 24.5,
            "currency": "$",
            "accountMask": "ending in 5412",
            "merchantOrParty": "AMAZON",
            "balance": 150.0
        }
    })

    cases.append({
        "id": "TC_EDG_DEC_007",
        "category": "EDGE_CASE_DECIMAL_FORMATS",
        "provider": "Bank al Etihad",
        "sender": "EtihadBank",
        "description": "Currency symbol € before amount",
        "body": "JO\nYou have made a purchase of €18.00 with card ending in 5412 at STEAM on 20/10/2026. Available balance is €82.00.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 18.0,
            "currency": "€",
            "accountMask": "ending in 5412",
            "merchantOrParty": "STEAM",
            "balance": 82.0
        }
    })


    # =========================================================================
    # 19. EDGE CASES: WHITESPACE, NEWLINES & UNUSUAL CHARACTERS
    # =========================================================================
    cases.append({
        "id": "TC_EDG_WSP_001",
        "category": "EDGE_CASE_WHITESPACE_NEWLINES",
        "provider": "Arab Bank",
        "sender": "ArabiBank",
        "description": "SMS with multiple excessive newlines and leading spaces",
        "body": "\n\n   JO\n\n\nYou have a purchase transaction on account 1234*678 from ZAIN MARKET amount JOD 5.450 on 20/10/2026.\n\n\nBalance JOD 39.132.   \n\n",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 5.45,
            "currency": "JOD",
            "accountMask": "1234*678",
            "merchantOrParty": "ZAIN MARKET",
            "balance": 39.132
        }
    })

    cases.append({
        "id": "TC_EDG_WSP_002",
        "category": "EDGE_CASE_WHITESPACE_NEWLINES",
        "provider": "Capital Bank",
        "sender": "CapitalBank",
        "description": "SMS with carriage returns \\r\\n and tabs inside party name and amount",
        "body": "JO\r\nOutward Cliq of\tJOD 12.000\tdebited from Acc. No xxxx833\r\non 16/09/2026 to\tANMAR ALQUDAH.\r\nAvailable balance JOD 45.000",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 12.0,
            "currency": "JOD",
            "accountMask": "xxxx833",
            "merchantOrParty": "ANMAR ALQUDAH",
            "balance": 45.0
        }
    })

    cases.append({
        "id": "TC_EDG_WSP_003",
        "category": "EDGE_CASE_WHITESPACE_NEWLINES",
        "provider": "Bank al Etihad",
        "sender": "EtihadBank",
        "description": "SMS with lowercase currency name 'jod' and double spaces",
        "body": "JO\nYou have made a purchase of  jod 14.500  with card ending in 5412 at  CARREFOUR  on 20/10/2026. Available balance is jod 105.500.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 14.5,
            "currency": "JOD",
            "accountMask": "ending in 5412",
            "merchantOrParty": "CARREFOUR",
            "balance": 105.5
        }
    })


    # =========================================================================
    # 20. EDGE CASES: ARABIC WITH DIACRITICS (TASHKEEL)
    # =========================================================================
    cases.append({
        "id": "TC_EDG_DIA_001",
        "category": "EDGE_CASE_ARABIC_DIACRITICS",
        "provider": "Housing Bank",
        "sender": "HousingBank",
        "description": "Arabic transaction with full vowel diacritics / tashkeel on purchase keywords",
        "body": "JO\nتَمَّتْ حَرَكَةُ شِرَاءٍ بِمَبْلَغِ 8.500 دِينَارٍ عَلَى بِطَاقَتِكَ *3412 لَدَى أَسْوَاقِ السَّلَامِ فِي 20/10/2026. الرَّصِيدُ الْمُتَاحُ 185.250 دِينَارٍ.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 8.5,
            "currency": "JOD",
            "accountMask": "*3412",
            "merchantOrParty": "أَسْوَاقِ السَّلَامِ",
            "balance": 185.25
        }
    })

    cases.append({
        "id": "TC_EDG_DIA_002",
        "category": "EDGE_CASE_ARABIC_DIACRITICS",
        "provider": "Orange Money",
        "sender": "OrangeMoney",
        "description": "Orange Money inward transfer with tashkeel on transfer verbs",
        "body": "JO\nتَمَّ اسْتِلَامُ مَبْلَغِ 30.000 JOD بِنَجَاحٍ إِلَى مَحْفَظَتِكَ مِنْ 0778899001 كِلِيكْ. رَصِيدُكَ الْحَالِي هُوَ 62.500 JOD.",
        "expected": {
            "isValidTransaction": True,
            "type": "INCOME",
            "amount": 30.0,
            "currency": "JOD",
            "accountMask": None,
            "merchantOrParty": None,
            "balance": 62.5
        }
    })

    cases.append({
        "id": "TC_EDG_DIA_003",
        "category": "EDGE_CASE_ARABIC_DIACRITICS",
        "provider": "Jordan Islamic Bank",
        "sender": "JIB",
        "description": "Jordan Islamic Bank debit with tashkeel",
        "body": "تَمَّ خَصْمُ مَبْلَغِ 18.750 د.أ بِوَاسِطَةِ بِطَاقَتِكَ الْمُنْتَهِيَةِ بِـ *5678 لَدَى CARREFOUR. الرَّصِيدُ الْمُتَاحُ: 145.250 د.أ.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 18.75,
            "currency": "JOD",
            "accountMask": "*5678",
            "merchantOrParty": "CARREFOUR",
            "balance": 145.25
        }
    })


    # =========================================================================
    # 21. EDGE CASES: TYPOS IN KEYWORDS
    # =========================================================================
    cases.append({
        "id": "TC_EDG_TYP_001",
        "category": "EDGE_CASE_TYPOS",
        "provider": "Arab Bank",
        "sender": "ArabiBank",
        "description": "Typo in purchase and balance ('purshase', 'balnce')",
        "body": "JO\nYou have a purshase transaction on account 1234*678 from ZAIN MARKET amount JOD 5.450 on 20/10/2026. Balnce JOD 39.132.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 5.45,
            "currency": "JOD",
            "accountMask": "1234*678",
            "merchantOrParty": "ZAIN MARKET",
            "balance": 39.132
        }
    })

    cases.append({
        "id": "TC_EDG_TYP_002",
        "category": "EDGE_CASE_TYPOS",
        "provider": "Bank al Etihad",
        "sender": "EtihadBank",
        "description": "Typo in transfer ('cliq tranfer')",
        "body": "JO\nOutward CliQ of JOD 15.000 debited from Acc. *9123 on 20/10/2026 to LAITH KHALED AL-OMARI as cliq tranfer. Available balance JOD 105.450.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 15.0,
            "currency": "JOD",
            "accountMask": "*9123",
            "merchantOrParty": "LAITH KHALED AL-OMARI",
            "balance": 105.45
        }
    })

    cases.append({
        "id": "TC_EDG_TYP_003",
        "category": "EDGE_CASE_TYPOS",
        "provider": "Housing Bank",
        "sender": "HousingBank",
        "description": "Repeated letters typo in Arabic ('حسابكك', 'الرصيدد')",
        "body": "JO\nتمت حركة شراء بمبلغ 12.000 د.أ من حسابكك *3412 لدى أسواق السلام. الرصيدد المتاح 140.000 د.أ.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 12.0,
            "currency": "JOD",
            "accountMask": "*3412",
            "merchantOrParty": "أسواق السلام",
            "balance": 140.0
        }
    })


    # =========================================================================
    # 22. EDGE CASES: MISSING OPTIONAL FIELDS (NO BALANCE, NO MERCHANT)
    # =========================================================================
    cases.append({
        "id": "TC_EDG_MIS_001",
        "category": "EDGE_CASE_MISSING_OPTIONAL_FIELDS",
        "provider": "Arab Bank",
        "sender": "ArabiBank",
        "description": "Arab Bank tuition fee debit with reference number but NO balance",
        "body": "JO\nJOD 1589.000 has been debited from 1234*678 on 20/09/2026 as Deposit_Student_Credit Payment Ref # 439821169455",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 1589.0,
            "currency": "JOD",
            "accountMask": "1234*678",
            "merchantOrParty": None,
            "balance": None
        }
    })

    cases.append({
        "id": "TC_EDG_MIS_002",
        "category": "EDGE_CASE_MISSING_OPTIONAL_FIELDS",
        "provider": "Reflect",
        "sender": "Reflect",
        "description": "Reflect debit transaction with NO merchant name mentioned",
        "body": "JO\nPurchase transaction of JOD 14.500 on your Reflect card 4123*789 on 19/10/2026. Available balance JOD 50.000.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 14.5,
            "currency": "JOD",
            "accountMask": "4123*789",
            "merchantOrParty": None,
            "balance": 50.0
        }
    })

    cases.append({
        "id": "TC_EDG_MIS_003",
        "category": "EDGE_CASE_MISSING_OPTIONAL_FIELDS",
        "provider": "Bank al Etihad",
        "sender": "EtihadBank",
        "description": "Etihad debit without account mask specified",
        "body": "JO\nYou have made a purchase of JOD 10.000 at CARREFOUR on 20/10/2026. Available balance is JOD 75.000.",
        "expected": {
            "isValidTransaction": True,
            "type": "EXPENSE",
            "amount": 10.0,
            "currency": "JOD",
            "accountMask": None,
            "merchantOrParty": "CARREFOUR",
            "balance": 75.0
        }
    })

    # Summary and metadata
    categories = {}
    providers = {}
    valid_count = 0
    invalid_count = 0

    for c in cases:
        cat = c["category"]
        categories[cat] = categories.get(cat, 0) + 1
        p = c["provider"]
        providers[p] = providers.get(p, 0) + 1
        if c["expected"]["isValidTransaction"]:
            valid_count += 1
        else:
            invalid_count += 1

    suite = {
        "metadata": {
            "title": "Masroof Financial Transaction Engine - Comprehensive Test Suite",
            "version": "2.0.0",
            "author": "Test Cases Designer Subagent",
            "description": "Extensive, rigorous, and adversarial test suite covering all 10 major Jordanian financial institutions and mobile wallets, multi-currency support (JOD, USD, SAR, AED, EUR), varied decimal notations, and hard negative traps (conversational chat noise, personal phone number senders, 3DS purchase authorization OTPs, login OTPs, declined transactions, system announcements, and marketing campaigns).",
            "totalCases": len(cases),
            "totalValidTransactions": valid_count,
            "totalInvalidOrAdversarial": invalid_count,
            "categoryBreakdown": categories,
            "providerBreakdown": providers
        },
        "testCases": cases
    }

    return suite

def main():
    suite = create_test_suite()
    out_path = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "test_suite_cases.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(suite, f, ensure_ascii=False, indent=2)

    print(f"Generated {suite['metadata']['totalCases']} test cases successfully!")
    print(f" - Valid Transactions: {suite['metadata']['totalValidTransactions']}")
    print(f" - Adversarial / Invalid: {suite['metadata']['totalInvalidOrAdversarial']}")
    print("\nCategory Breakdown:")
    for cat, count in suite['metadata']['categoryBreakdown'].items():
        print(f"   * {cat}: {count}")

if __name__ == "__main__":
    main()
