import json
import os
import re
import sys
from pathlib import Path

from .preprocessing import normalize_financial_numbers, preprocess_message, tokenize_features
from .service_notice import is_service_notice, SERVICE_NOTICE_REASON
from .authorization_request import is_authorization_request, AUTHORIZATION_REQUEST_REASON
from .legacy_transaction_model import score_legacy_transaction_model
from .entity_text import EntityText

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

class MasroofEngine:
    # 1. Pre-compiled Regex Cache for Microsecond Latency and Zero Allocation
    RE_PREPROCESS_ROUTING = re.compile(r'^[A-Z]{2}(\r?\n|\s+)')
    RE_PREPROCESS_DIACRITICS = re.compile(r'[\u064B-\u065F\u0670]')
    RE_PREPROCESS_SPACES = re.compile(r'\s+')
    RE_PREPROCESS_NUM_LONG = re.compile(r'\b\d{6,}\b')

    RE_TOKENIZE = re.compile(r'[\w\u0621-\u064A\u0660-\u0669\*\.\-]+')

    RE_PERSONAL_PHONE_1 = re.compile(r'^(\+|00)[0-9]{7,15}$')
    RE_PERSONAL_PHONE_2 = re.compile(r'^0[7-9][0-9]{7,9}$')

    RE_CHAT_NOISE = re.compile(
        r'\b(?:i\s+(?:just\s+)?(?:sent|transferred|paid|wired|gave)|sent\s+you|just\s+sent|transferred\s+you|paid\s+you|check\s+(?:it|your\s+account)|did\s+you\s+(?:get|receive)|can\s+you\s+send\s+me|send\s+me)\b|'
        r'حولتلك|حولتلكم|بعثتلك|بعتلك|شيك عليها|شيك عليه|'
        r'شوفيها|شوفها|ابعثلي|وصلتك الحوالة|بالله|'
        r'من\s+بنك.*?\bلحسابك',
        re.I
    )

    RE_DECLINED = re.compile(
        r'\b(?:declined|failed|rejected|unsuccessful|insufficient\s+funds)\b|'
        r'\bcard\b.*?\b(?:locked|blocked)\b|'
        r'مرفوض(?:ة)?|تم\s+رفض|'
        r'فشل(?:ت)?\s+(?:عملية|الحركة|الدفع)|'
        r'تعذر\s+(?:إرسال|تنفيذ|إتمام)|'
        r'لم\s+تتم\s+عملية|نأسف\s+لعدم\s+إتمام|'
        r'غير\s+مكتمل(?:ة)?|تم\s+إلغاء\s+عملية|'
        r'عدم\s+كفاية\s+الرصيد|عدم\s+توفر\s+رصيد|لتجاوز\s+الحد\s+المسموح',
        re.I
    )

    RE_INTERNAL_1 = re.compile(r'between (?:(?:your|my)(?: own)?|own) accounts|transfer between accounts|internal transfer|own account transfer', re.I)
    RE_INTERNAL_2 = re.compile(r'تحويل بين حسابات(?:ك|كم|ي)|بين حسابات(?:ك|كم|ي)|تحويل داخلي|بين الحسابات', re.I)
    RE_INTERNAL_3 = re.compile(r'(?:transfer\s+from\s+your|from\s+your).*?(?:to\s+your|to\s+another)', re.I)
    RE_INTERNAL_4 = re.compile(r'(?:تحويل\s+من\s+حسابك|من\s+حسابك).*?(?:إلى\s+حسابك|إلى\s+بطاقتك|إلى\s+محفظتك)', re.I)
    RE_DEBIT_IND = re.compile(r'debited|خصم|سحب|debit', re.I)
    RE_CREDIT_IND = re.compile(r'credited|قيد|إيداع|credit', re.I)
    RE_TRANSFER_VERBS = re.compile(r'transfer|تحويل', re.I)
    RE_ACC_MASKS = re.compile(r'(?:[0-9]{2,4}\*[0-9]{2,4}|xxxx[0-9]{3,4}|\*[0-9]{4}|(?:ending (?:in |with )?|المنتهي(?:ة)? ب[ـ ]*)[0-9]{4})', re.I)

    RE_TRUNCATED = re.compile(r'(?:لدى|إلى|من|عبر|بواسطة|\bat|\bto|\bfrom|\bwith|\bon)\s*$', re.I)

    RE_EXPENSE_DIR = re.compile(r'\b(?:purchase|debited|debit|withdrawn|withdrawal|outward|bill\s+payment|paid)\b|شراء|خصم|سحب|صادرة|تسديد\s+فاتورة|دفع\s+فاتورة|دفع\s+مبلغ', re.I)
    RE_INCOME_DIR = re.compile(r'\b(?:refund|reversal|inward|deposit|cashback)\b|استرجاع|واردة|استلام|إيداع|حوالة\s+واردة', re.I)

    RE_NORM_DIACRITICS = re.compile(r'[\u064B-\u065F\u0670]')
    RE_NORM_WHITESPACE = re.compile(r'[\r\n\t]+')
    RE_NORM_SPACES = re.compile(r'\s+')

    _AMT_PATTERN = r'([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]{1,3})?|[0-9]{1,2}(?:,[0-9]{2})*,[0-9]{3}(?:\.[0-9]{1,3})?|[0-9]{1,3}(?:[\'’][0-9]{3})+(?:[\.,][0-9]{1,3})?|[0-9]+(?:[\.,][0-9]{1,3})?)'
    _CURR_TERMS = r'(?:USD|EUR|GBP|JPY|CAD|AUD|CHF|CNY|INR|TRY|BRL|MXN|ZAR|JOD|SAR|AED|KWD|QAR|BHD|OMR|EGP|ILS|IQD|LBP|SR|KD|BD|RO|QR|DH|DHS|د\.أ|دينار|دنانير|دينارا|ر\.س|ريال|ريالات|ريالا|د\.إ|درهم|دراهم|درهما|د\.ك|ر\.ق|د\.ب|ر\.ع|ج\.م|جنيه|جنيها|[\$€£¥₹₪])'

    _ACC_MASK_PAT = r'(?:\*[0-9]{4}|xxxx[0-9]{3,4}|[0-9]{2,4}\*[0-9]{2,4})'
    _QUALIFIER = r'(?:\s+for\s+acc(?:ount)?\.?\s*' + _ACC_MASK_PAT + r'(?:\s+as\s+of\s+\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)?|\s+' + _ACC_MASK_PAT + r')?'
    _STATUS_WORDS = r'(?:\s+[\u0621-\u064A]+){0,4}'

    RE_BAL_PREFIX = re.compile(
        r'(?:(?:available\s+|current\s+|remaining\s+|account\s+)?(?:bal(?:[a-z]?nce|\.|\b)|avail(?:\.|\s+)bal)|(?:رصيدك|الرصيد[دة]?|رصيد\s+حسابك))' +
        _QUALIFIER + _STATUS_WORDS +
        r'\s*(?:is|هو|:)?\s*(?:(?<![A-Za-z])' + _CURR_TERMS + r')?\s*' + _AMT_PATTERN + r'\s*(?:' + _CURR_TERMS + r'(?![A-Za-z]))?',
        re.I
    )
    RE_BAL_POSTFIX = re.compile(
        _AMT_PATTERN + r'\s*(?:' + _CURR_TERMS + r')?\s*(?:(?:ال)?رصيد[دة]?(?:ك)?|bal[a-z]?nce)',
        re.I
    )

    RE_BILLED = re.compile(
        r'(?:billed\s+(?:as\s+)?|\(\s*(?=[A-Za-z]{2,3}|د\.أ|ر\.س|د\.إ|[0-9])|معادل\s+لـ\s*|ما\s+يعادل\s*)(?:(?<![A-Za-z])(' + _CURR_TERMS + r'))?\s*' + _AMT_PATTERN + r'\s*(?:(' + _CURR_TERMS + r')(?![A-Za-z]))?',
        re.I
    )

    RE_AMT_P1 = re.compile(
        r'(?:amount|بمبلغ|بقيمة|مبلغ|دفعة|purchase\s+of|transaction\s+of|for)\s*(?:is|:|of)?\s*(?:(?<![A-Za-z])(' + _CURR_TERMS + r'))?\s*' + _AMT_PATTERN + r'\s*(?:(' + _CURR_TERMS + r')(?![A-Za-z]))?',
        re.I
    )
    RE_AMT_P2 = re.compile(
        r'(?<![A-Za-z])(' + _CURR_TERMS + r')\s*' + _AMT_PATTERN + r'(?![*0-9])',
        re.I
    )
    RE_AMT_P3 = re.compile(
        r'(?<![*0-9])\b' + _AMT_PATTERN + r'\s*(' + _CURR_TERMS + r')(?![A-Za-z])',
        re.I
    )

    RE_GLOBAL_CURR = re.compile(
        r'(?<![A-Za-z])(USD|EUR|GBP|JPY|CAD|AUD|CHF|CNY|INR|TRY|BRL|MXN|ZAR|JOD|SAR|AED|KWD|QAR|BHD|OMR|EGP|ILS|IQD|LBP|SR|KD|BD|RO|QR|DH|DHS)(?![A-Za-z])|(?:^|[^\w\u0621-\u064A])(د\.أ|دينار|دنانير|دينارا|ر\.س|ريال|ريالات|ريالا|د\.إ|درهم|دراهم|درهما|د\.ك|ر\.ق|د\.ب|ر\.ع|ج\.م|جنيه|جنيها)(?=[^\w\u0621-\u064A]|$)|([\$€£¥₹₪])',
        re.I
    )

    RE_ACC_MASK = re.compile(
        r'([0-9]{2,4}\*[0-9]{2,4}|xxxx[0-9]{3,4}|\*[0-9]{4}|(?:ending (?:in |with )?|المنتهي(?:ة)? ب[ـ ]*)([0-9]{4}))',
        re.I
    )

    RE_PAREN_PARTY = re.compile(r'(?:محفظة|من|إلى|كليك)?\s*0[7-9][0-9]{8}\s*\(([A-Za-z0-9\u0600-\u06FF\s\.\-_]+?)\)', re.I)
    RE_BILL_PARTY = re.compile(r'(?:دفع|تسديد)\s+فاتورة\s+(?:عبر\s+)?([A-Za-z0-9\u0600-\u06FF\s\.\-_]+?)(?=[.,;]?\s+(?:بنجاح|بقيمة|بمبلغ|عبر|من|في|\n|$))', re.I)

    _DELIMS = r'(?:amount|on\b|at\b|to\b|from\b|via|through|as\s+cliq|has\s+been|with\s+card|is|bal(?:[a-z]?nce|\b)|your\b|avail|\d{1,2}[/-]\d{1,2}|ref\s*#|بمبلغ|بقيمة|في\s+\d|لدى|إلى|من(?=\s|[.,;]|$)|عبر|بواسطة|باستخدام|بالبطاقة|بالبطاقه|رصيدك|الرصيد|بتاريخ|تم(?![\u0621-\u064A])|رقم|$)'
    RE_PARTY = re.compile(r'(?:from|at|to|لدى|إلى|من|لحساب|عبر)\s+([A-Za-z0-9\u0600-\u06FF\s\.\-_*&/\'’]+?)(?=[.,;]?\s+' + _DELIMS + r'|\n|$)', re.I)
    RE_ADMIN_ALERT = re.compile(
        r'\bcredit\s+limit\b.*?\b(?:increased|decreased|adjusted)\b|\b(?:did\s+you\s+(?:attempt|make)\s+(?:a\s+|this\s+)?purchase|security\s+alert|refund\s+request)\b|تم\s+(?:زيادة|تعديل|رفع)\s+سقف\s+(?:الائتمان|البطاقة)|هل\s+قمت\s+(?:بإجراء|بمحاولة)|هل\s+حاولت|طلب\s+استرداد',
        re.I
    )
    RE_CLAUSE_TARGET = re.compile(r'^(?:account|acc\.?|card|wallet|حساب|بطاق|محفظ|your\s+account|your\s+card|[0-9x\*]{3,}|\d{1,2}:\d{2}|your\b|avail|bal[a-z]?nce|رصيد)', re.I)
    RE_PREP_EXTENSION = re.compile(r'^(to|at|from|من|إلى)\s+([A-Za-z0-9\u0600-\u06FF\s\.\-_*&/\'’]+?)(?=[.,;]?\s+' + _DELIMS + r'|\n|$)', re.I)

    # 2. Semantic Micro-Embedding Subword Categorizer (Zero-Allocation Layer 2)
    CATEGORIES = [
        'Groceries & Supermarket',
        'Dining & Food Delivery',
        'Shopping & Retail',
        'Utilities & Bills',
        'Transportation & Fuel',
        'Health & Pharmacy',
        'Financial Services & Transfers',
        'Entertainment & Leisure',
    ]

    # Milestone 2: normalized merchant -> category index, persisted by the host app.
    USER_OVERLAY = {}
    CATEGORY_TO_INDEX = {
        'Groceries & Supermarket': 0,
        'Dining & Food Delivery': 1,
        'Shopping & Retail': 2,
        'Utilities & Bills': 3,
        'Transportation & Fuel': 4,
        'Health & Pharmacy': 5,
        'Financial Services & Transfers': 6,
        'Entertainment & Leisure': 7,
    }

    SUBWORD_CATEGORY_MAP = {
        # 0: Groceries & Supermarket
        'supermarket': 0, 'grocery': 0, 'groceries': 0, 'market': 0, 'hypermarket': 0, 'baqala': 0, 'food': 0, 'carrefour': 0, 'safeer': 0, 'lulu': 0, 'mart': 0, 'safeway': 0,
        'سوبرماركت': 0, 'بقالة': 0, 'خضار': 0, 'تموينات': 0, 'ماركت': 0, 'اسواق': 0, 'هايبرماركت': 0, 'كارفور': 0, 'سيفوي': 0, 'البقالة': 0, 'السوبرماركت': 0,

        # 1: Dining & Food Delivery
        'restaurant': 1, 'cafe': 1, 'coffee': 1, 'burger': 1, 'pizza': 1, 'kitchen': 1, 'grill': 1, 'dining': 1, 'delivery': 1, 'talabat': 1, 'jahez': 1, 'barista': 1, 'starbucks': 1, 'mcdonald': 1, 'kfc': 1, 'shawarma': 1, 'bakery': 1,
        'مطعم': 1, 'كافيه': 1, 'مقهى': 1, 'قهوة': 1, 'شاورما': 1, 'وجبات': 1, 'برجر': 1, 'بيتزا': 1, 'توصيل': 1, 'طلبات': 1, 'ستاربكس': 1, 'ماكدونالدز': 1, 'كنتاكي': 1, 'مخبز': 1, 'مطاعم': 1,

        # 2: Shopping & Retail
        'mall': 2, 'retail': 2, 'fashion': 2, 'clothes': 2, 'apparel': 2, 'shop': 2, 'boutique': 2, 'zara': 2, 'amazon': 2, 'noon': 2, 'center': 2,
        'سوق': 2, 'مول': 2, 'متجر': 2, 'ملابس': 2, 'ازياء': 2, 'تسوق': 2, 'احذية': 2, 'سنتر': 2, 'سيتي': 2, 'المتاجر': 2,

        # 3: Utilities & Bills
        'electric': 3, 'water': 3, 'utility': 3, 'bill': 3, 'telecom': 3, 'recharge': 3, 'ooredoo': 3, 'stc': 3, 'zain': 3, 'orange': 3, 'fawateer': 3,
        'فاتورة': 3, 'كهرباء': 3, 'مياه': 3, 'انترنت': 3, 'اتصالات': 3, 'شحن': 3, 'فواتير': 3, 'مسقفات': 3, 'فواتيركم': 3, 'الفاتورة': 3,

        # 4: Transportation & Fuel
        'fuel': 4, 'gas': 4, 'petrol': 4, 'station': 4, 'uber': 4, 'careem': 4, 'taxi': 4, 'ride': 4, 'transportation': 4, 'parking': 4, 'travel': 4, 'shell': 4, 'total': 4, 'manaseer': 4,
        'مناصير': 4, 'بنزين': 4, 'بترول': 4, 'وقود': 4, 'محطة': 4, 'اوبر': 4, 'كريم': 4, 'تاكسي': 4, 'مواصلات': 4, 'مواقف': 4, 'جوبترول': 4, 'المحطة': 4,

        # 5: Health & Pharmacy
        'pharmacy': 5, 'hospital': 5, 'clinic': 5, 'dental': 5, 'medical': 5, 'doctor': 5, 'lab': 5, 'medicine': 5, 'care': 5,
        'صيدلية': 5, 'مستشفى': 5, 'عيادة': 5, 'اسنان': 5, 'دكتور': 5, 'مختبر': 5, 'علاج': 5, 'صحة': 5, 'دواء': 5, 'رعاية': 5, 'صيدليات': 5, 'الصيدلية': 5,

        # 6: Financial Services & Transfers
        'transfer': 6, 'cliq': 6, 'exchange': 6, 'remittance': 6, 'atm': 6, 'interest': 6, 'loan': 6, 'wire': 6, 'outward': 6, 'inward': 6, 'deposit': 6, 'withdrawal': 6, 'fee': 6,
        'صراف': 6, 'حوالة': 6, 'رسوم': 6, 'سداد': 6, 'تمويل': 6, 'ايداع': 6, 'تحويل': 6, 'كليك': 6, 'اقساط': 6, 'سحب': 6, 'الصراف': 6, 'واردة': 6, 'صادرة': 6, 'إيداع': 6,

        # 7: Entertainment & Leisure
        'cinema': 7, 'movie': 7, 'netflix': 7, 'spotify': 7, 'gym': 7, 'fitness': 7, 'game': 7, 'entertainment': 7, 'tickets': 7, 'park': 7, 'resort': 7,
        'سينما': 7, 'فيلم': 7, 'جيم': 7, 'رياضة': 7, 'ترفيه': 7, 'العاب': 7, 'تذاكر': 7, 'نادي': 7, 'منتجع': 7, 'استجمام': 7, 'برايم': 7, 'ترفيهي': 7,
    }

    _RE_SPLIT = re.compile(r'[\s,._\-\/\\*]+')

    @staticmethod
    def normalize_merchant(name):
        if not isinstance(name, str):
            return ''
        return re.sub(r'ى', 'ي', re.sub(r'ة', 'ه', re.sub(
            r'[إأآا]', 'ا', re.sub(r'[\u064B-\u065F\u0670\u0640]', '',
            re.sub(r"[,\s._\-/\\*#&'’]+", ' ', name.lower().strip()))))).strip()

    @classmethod
    def load_user_overlay(cls, json_str):
        try:
            parsed = json.loads(json_str) if isinstance(json_str, str) else json_str
            if not isinstance(parsed, dict):
                return
            overlay = {}
            for merchant, category_index in parsed.items():
                normalized_merchant = cls.normalize_merchant(merchant)
                if normalized_merchant and isinstance(category_index, int) and 0 <= category_index < len(cls.CATEGORIES):
                    overlay[normalized_merchant] = category_index
            cls.USER_OVERLAY = overlay
        except (TypeError, ValueError, json.JSONDecodeError):
            pass

    @classmethod
    def export_user_overlay(cls):
        return dict(cls.USER_OVERLAY)

    @classmethod
    def apply_correction(cls, merchant_or_text, corrected_category):
        normalized_merchant = cls.normalize_merchant(merchant_or_text)
        category_index = cls.CATEGORY_TO_INDEX.get(corrected_category)
        if normalized_merchant and category_index is not None:
            cls.USER_OVERLAY[normalized_merchant] = category_index

    @classmethod
    def classify_category(cls, merchant, body_text):
        overlay_index = cls.USER_OVERLAY.get(cls.normalize_merchant(merchant)) if merchant else None
        if overlay_index is not None:
            return {
                'category': cls.CATEGORIES[overlay_index],
                'confidence': 1.0
            }

        scores = [0.0] * 8

        # 1. Score merchant tokens with 2.5x weight
        if merchant:
            m_words = cls._RE_SPLIT.split(merchant.lower())
            for w in m_words:
                if len(w) < 2:
                    continue
                cat = cls.SUBWORD_CATEGORY_MAP.get(w)
                if cat is not None:
                    scores[cat] += 2.5

        # 2. Score body tokens with 1.0x weight
        b_words = cls._RE_SPLIT.split(body_text.lower())
        for w in b_words:
            if len(w) < 2:
                continue
            cat = cls.SUBWORD_CATEGORY_MAP.get(w)
            if cat is not None:
                scores[cat] += 1.0

        max_score = 0.0
        best_idx = -1
        for c in range(8):
            if scores[c] > max_score:
                max_score = scores[c]
                best_idx = c

        if best_idx == -1 or max_score < 1.5:
            return {
                'category': 'General & Uncategorized',
                'confidence': 0.0
            }

        return {
            'category': cls.CATEGORIES[best_idx],
            'confidence': min(1.0, round((max_score / 6.0), 2))
        }

    def __init__(self, model_path=None):
        if model_path is None:
            model_path = PROJECT_ROOT / "data" / "models" / "masroof_model.json"
        with open(model_path, "r", encoding="utf-8") as f:
            self.model = json.load(f)
        self.features = self.model["features"]
        self.intercept_tx = self.model["metadata"]["intercept_tx"]
        self.intercept_credit = self.model["metadata"]["intercept_credit"]

    @staticmethod
    def parse_number(s):
        if not s:
            return None
        s = re.sub(r'[\'’\s]', '', normalize_financial_numbers(str(s)).strip())
        if ',' in s and '.' in s:
            if s.rfind('.') > s.rfind(','):
                return float(s.replace(',', ''))
            else:
                return float(s.replace('.', '').replace(',', '.'))
        elif ',' in s:
            parts = s.split(',')
            if len(parts) == 2 and len(parts[1]) in (1, 2):
                return float(parts[0] + '.' + parts[1])
            else:
                return float(s.replace(',', ''))
        else:
            return float(s)

    def preprocess(self, text):
        return preprocess_message(text)

    def tokenize(self, text):
        return tokenize_features(text)

    def _score_tokens(self, tokens):
        return score_legacy_transaction_model(self.features, tokens, self.intercept_tx, self.intercept_credit)

    @classmethod
    def is_internal_transfer(cls, text):
        norm = text.lower()
        if cls.RE_INTERNAL_1.search(norm) or \
           cls.RE_INTERNAL_2.search(norm) or \
           cls.RE_INTERNAL_3.search(norm) or \
           cls.RE_INTERNAL_4.search(norm):
            return True

        has_debit = bool(cls.RE_DEBIT_IND.search(norm))
        has_credit = bool(cls.RE_CREDIT_IND.search(norm))
        acc_matches = [m.group(0) for m in cls.RE_ACC_MASKS.finditer(norm)]
        if len(set(acc_matches)) >= 2:
            if (has_debit and has_credit) or cls.RE_TRANSFER_VERBS.search(norm):
                return True

        return False

    def predict_detailed(self, input_value):
        from .detailed_assessment import assess
        return assess(input_value,
                      lambda body, direction: self.extract_entities(body, direction, categorize=False),
                      self.parse_number,
                      lambda text: self._score_tokens(self.tokenize(self.preprocess(text)))[0] >= 0.70)

    def predict(self, sender, body, is_contact=False, default_currency="JOD"):
        if is_contact:
            return {
                "isValidTransaction": False,
                "confidence": 0.0,
                "reason": "Personal sender (saved contact in phone)",
                "data": None
            }

        clean_sender = normalize_financial_numbers(sender).strip().replace(" ", "").replace("-", "")
        is_personal = bool(self.RE_PERSONAL_PHONE_1.match(clean_sender) or self.RE_PERSONAL_PHONE_2.match(clean_sender))
        if is_personal:
            return {
                "isValidTransaction": False,
                "confidence": 0.0,
                "reason": "Personal sender (phone number)",
                "data": None
            }

        original_body = body
        body = normalize_financial_numbers(body)
        # Check conversational chat noise spoofing
        if self.RE_CHAT_NOISE.search(body):
            return {
                "isValidTransaction": False,
                "confidence": 0.0,
                "reason": "Conversational chat noise",
                "data": None
            }

        # Check declined / failed transactions
        if self.RE_DECLINED.search(body):
            return {
                "isValidTransaction": False,
                "confidence": 0.0,
                "reason": "Transaction declined or failed",
                "data": None
            }

        # Check administrative alerts, credit limit updates, and security fraud prompts
        if self.RE_ADMIN_ALERT.search(body):
            return {
                "isValidTransaction": False,
                "confidence": 0.0,
                "reason": "Administrative alert, credit limit update, or security query (non-transaction)",
                "data": None
            }

        if is_service_notice(body):
            return {
                "isValidTransaction": False,
                "confidence": 0.0,
                "reason": SERVICE_NOTICE_REASON,
                "data": None
            }

        if is_authorization_request(body):
            return {
                "isValidTransaction": False,
                "confidence": 0.0,
                "reason": AUTHORIZATION_REQUEST_REASON,
                "data": None
            }

        # ML inference
        cleaned = self.preprocess(body)
        tokens = self.tokenize(cleaned)

        prob_tx, prob_credit = self._score_tokens(tokens)

        is_valid = prob_tx >= 0.70

        if not is_valid:
            return {
                "isValidTransaction": False,
                "confidence": round(prob_tx, 4),
                "reason": "Classified as non-transaction (conversational noise, OTP, declined, or announcement)",
                "data": None
            }

        # Inviolable rule: Internal transfer between user's own accounts
        if self.is_internal_transfer(body):
            return {
                "isValidTransaction": False,
                "confidence": 0.0,
                "reason": "Internal transfer between own accounts (no net expense or income)",
                "data": None
            }

        # Check truncated carrier SMS
        norm_body = self.RE_NORM_DIACRITICS.sub('', body).strip()
        if self.RE_TRUNCATED.search(norm_body):
            return {
                "isValidTransaction": False,
                "confidence": 0.0,
                "reason": "Truncated or malformed SMS",
                "data": None
            }

        # Calibrate transaction direction (EXPENSE vs INCOME)
        is_exp = bool(self.RE_EXPENSE_DIR.search(norm_body))
        is_inc = bool(self.RE_INCOME_DIR.search(norm_body))

        if is_exp and not is_inc:
            tx_type = "EXPENSE"
        elif is_inc and not is_exp:
            tx_type = "INCOME"
        else:
            tx_type = "INCOME" if prob_credit >= 0.50 else "EXPENSE"

        extracted = self.extract_entities(original_body, tx_type, default_currency=default_currency)

        # INVIOLABLE FINANCIAL LAW: A transaction MUST have an actual monetary amount > 0!
        if not extracted or extracted.get("amount") is None or extracted["amount"] <= 0:
            return {
                "isValidTransaction": False,
                "confidence": 0.0,
                "reason": "No transaction amount detected (balance notification, inquiry, or incomplete message)",
                "data": None
            }

        return {
            "isValidTransaction": True,
            "confidence": round(prob_tx, 4),
            "reason": None,
            "data": extracted
        }

    @staticmethod
    def normalize_currency(token):
        if not token:
            return None
        t = token.strip()
        upper = t.upper()
        if upper in ['د.أ', 'دينار', 'دنانير', 'دينارا', 'JD']:
            return 'JOD'
        if upper in ['ر.س', 'ريال', 'ريالات', 'ريالا', 'SAR', 'SR']:
            return 'SAR'
        if upper in ['د.إ', 'درهم', 'دراهم', 'درهما', 'AED', 'DH', 'DHS']:
            return 'AED'
        if upper in ['د.ك', 'KWD', 'KD']:
            return 'KWD'
        if upper in ['ر.ق', 'QAR', 'QR']:
            return 'QAR'
        if upper in ['د.ب', 'BHD', 'BD']:
            return 'BHD'
        if upper in ['ر.ع', 'OMR', 'RO']:
            return 'OMR'
        if upper in ['ج.م', 'جنيه', 'جنيها', 'EGP']:
            return 'EGP'
        if t == '$':
            return 'USD'
        if t == '€':
            return 'EUR'
        if t == '£':
            return 'GBP'
        if t == '¥':
            return 'JPY'
        if t == '₹':
            return 'INR'
        if t == '₪':
            return 'ILS'
        return upper

    def extract_entities(self, text, tx_type, default_currency="JOD", categorize=True):
        view = EntityText(text)
        data = {
            "type": tx_type,
            "direction": "INCOMING" if tx_type == "INCOME" else "OUTGOING",
            "amount": None,
            "currency": default_currency or "JOD",
            "merchantOrParty": None,
            "merchant_or_party": None,
            "accountMask": None,
            "account_mask": None,
            "balance": None,
            "category": "General & Uncategorized",
            "categoryConfidence": 0.0,
            "category_confidence": 0.0
        }

        # Normalize whitespace and Arabic diacritics
        norm_text = view.text

        # 1. Dynamic Balance Extraction FIRST + Masking
        m_bal_prefix = self.RE_BAL_PREFIX.search(norm_text)
        m_bal_postfix = self.RE_BAL_POSTFIX.search(norm_text)

        amt_working_text = norm_text
        if m_bal_prefix and m_bal_prefix.group(1):
            try:
                data["balance"] = self.parse_number(m_bal_prefix.group(1))
                s, e = m_bal_prefix.span()
                amt_working_text = amt_working_text[:s] + " __BAL_MASK__ " + amt_working_text[e:]
            except Exception:
                pass
        elif m_bal_postfix and m_bal_postfix.group(1):
            try:
                data["balance"] = self.parse_number(m_bal_postfix.group(1))
                s, e = m_bal_postfix.span()
                amt_working_text = amt_working_text[:s] + " __BAL_MASK__ " + amt_working_text[e:]
            except Exception:
                pass

        # 2. Dynamic Transaction Amount + Adjacent Currency Extraction
        p_billed = self.RE_BILLED.search(amt_working_text)
        p1 = self.RE_AMT_P1.search(amt_working_text)
        p2 = self.RE_AMT_P2.search(amt_working_text)
        p3 = self.RE_AMT_P3.search(amt_working_text)

        if p_billed and p_billed.group(2):
            billed_amt = self.parse_number(p_billed.group(2))
            raw_billed_curr = p_billed.group(1) or p_billed.group(3) or None
            data["amount"] = billed_amt
            norm_billed_curr = self.normalize_currency(raw_billed_curr)
            if norm_billed_curr:
                data["currency"] = norm_billed_curr

            # Mask out the billed portion so we can extract the foreign/original amount
            s, e = p_billed.span()
            amt_working_text = amt_working_text[:s] + " __BILLED_MASK__ " + amt_working_text[e:]

            # Scan remaining text for foreign/original transaction amount
            p_orig1 = self.RE_AMT_P1.search(amt_working_text)
            p_orig2 = self.RE_AMT_P2.search(amt_working_text)
            p_orig3 = self.RE_AMT_P3.search(amt_working_text)

            raw_orig_amt = None
            orig_curr_raw = None

            if p_orig1 and p_orig1.group(2):
                raw_orig_amt = p_orig1.group(2)
                orig_curr_raw = p_orig1.group(1) or p_orig1.group(3) or None
            elif p_orig2 and p_orig2.group(2):
                raw_orig_amt = p_orig2.group(2)
                orig_curr_raw = p_orig2.group(1)
            elif p_orig3 and p_orig3.group(1):
                raw_orig_amt = p_orig3.group(1)
                orig_curr_raw = p_orig3.group(2)

            if raw_orig_amt:
                data["originalAmount"] = self.parse_number(raw_orig_amt)
                data["original_amount"] = data["originalAmount"]
                norm_orig_curr = self.normalize_currency(orig_curr_raw)
                if norm_orig_curr:
                    data["originalCurrency"] = norm_orig_curr
                    data["original_currency"] = norm_orig_curr
                else:
                    g_curr = self.RE_GLOBAL_CURR.search(amt_working_text)
                    if g_curr:
                        r_curr = g_curr.group(1) or g_curr.group(2) or g_curr.group(3)
                        n_curr = self.normalize_currency(r_curr)
                        if n_curr:
                            data["originalCurrency"] = n_curr
                            data["original_currency"] = n_curr
                if data.get("amount") and data.get("originalAmount") and data["originalAmount"] > 0:
                    data["exchangeRate"] = round(data["amount"] / data["originalAmount"], 4)
                    data["exchange_rate"] = data["exchangeRate"]
        else:
            raw_amt = None
            extracted_curr = None

            if p1 and p1.group(2):
                raw_amt = p1.group(2)
                extracted_curr = p1.group(1) or p1.group(3) or None
            elif p2 and p2.group(2):
                raw_amt = p2.group(2)
                extracted_curr = p2.group(1)
            elif p3 and p3.group(1):
                raw_amt = p3.group(1)
                extracted_curr = p3.group(2)

            if raw_amt:
                try:
                    data["amount"] = self.parse_number(raw_amt)
                except Exception:
                    pass

            # Currency Resolution
            norm_extracted = self.normalize_currency(extracted_curr)
            if norm_extracted:
                data["currency"] = norm_extracted
            else:
                curr_match = self.RE_GLOBAL_CURR.search(amt_working_text)
                if curr_match:
                    raw_curr = curr_match.group(1) or curr_match.group(2) or curr_match.group(3)
                    norm_curr = self.normalize_currency(raw_curr)
                    if norm_curr:
                        data["currency"] = norm_curr

        # 3. Dynamic Account / Card Mask Detection
        acc_match = self.RE_ACC_MASK.search(norm_text)
        if acc_match:
            mask_val = acc_match.group(2) if acc_match.group(2) else acc_match.group(1)
            data["accountMask"] = mask_val
            data["account_mask"] = mask_val

        # 4. Dynamic Merchant / Recipient Party Extraction
        # Check wallet parenthesized party name first (e.g. "0771234567 (AHMAD SALEH)")
        m_paren = self.RE_PAREN_PARTY.search(norm_text)
        if m_paren and len(m_paren.group(1).strip()) > 2:
            matched = m_paren.group(1)
            start = m_paren.start(1) + len(matched) - len(matched.lstrip())
            party_val = view.exact(start, start + len(matched.strip()))
            data["merchantOrParty"] = party_val
            data["merchant_or_party"] = party_val
        else:
            # Check bill payment pattern (e.g. "فاتورة زين بنجاح", "فاتورة عبر إي فواتيركم")
            m_bill = self.RE_BILL_PARTY.search(norm_text)
            if m_bill and len(m_bill.group(1).strip()) > 1:
                cand = m_bill.group(1).strip()
                start = m_bill.start(1) + m_bill.group(1).index(cand)
                party_val = view.exact(start, start + len(cand))
                data["merchantOrParty"] = party_val
                data["merchant_or_party"] = party_val
            else:
                for m in self.RE_PARTY.finditer(norm_text):
                    cand = m.group(1).strip()
                    cand = re.sub(r'^(?:تاجر\s+)', '', cand).strip()
                    cand_lower = cand.lower()
                    if re.search(r'\b(?:account|acc\.?|card|wallet|حساب|بطاق|محفظ)', cand_lower):
                        continue
                    if re.match(r'^[x\*0-9]+$', cand) or re.match(r'^acc(?:\.|ount)?\s*(?:no\.?)?\s*[\*x0-9]+', cand_lower):
                        continue
                    if cand_lower in ['cliq', 'كليك', 'أي فواتيركم', 'اي فواتيركم'] or re.match(r'^(?:نقاط\s+البيع|apple\s+pay|مدى|الإنترنت)$', cand_lower, re.I):
                        continue
                    if len(cand) <= 2:
                        continue
                    candidate_start = m.start(1) + m.group(1).index(cand)
                    candidate_end = candidate_start + len(cand)

                    # Smart Preposition Chunker Extension: Check if candidate was cut by internal preposition
                    match_end = m.end()
                    match_end += len(norm_text[match_end:]) - len(norm_text[match_end:].lstrip())
                    remaining = norm_text[match_end:]
                    m_prep = self.RE_PREP_EXTENSION.match(remaining)
                    while m_prep and m_prep.group(1) and m_prep.group(2):
                        prep_word = m_prep.group(1)
                        next_part = m_prep.group(2).strip()
                        if self.RE_CLAUSE_TARGET.search(next_part):
                            break
                        candidate_end = match_end + len(m_prep.group(0).rstrip())
                        cand = norm_text[candidate_start:candidate_end]
                        match_end += len(m_prep.group(0))
                        match_end += len(norm_text[match_end:]) - len(norm_text[match_end:].lstrip())
                        remaining = norm_text[match_end:]
                        m_prep = self.RE_PREP_EXTENSION.match(remaining)

                    cand = re.sub(r'\s+بنجاح$', '', cand).strip()
                    party_val = view.exact(candidate_start, candidate_start + len(cand))
                    data["merchantOrParty"] = party_val
                    data["merchant_or_party"] = party_val
                    break

        if not categorize:
            return data

        # 4. Semantic Micro-Embedding Categorization (Layer 2)
        scoring_party = data.get("merchantOrParty")
        if scoring_party:
            scoring_party = re.sub(r'\s+', ' ', self.RE_NORM_DIACRITICS.sub('', normalize_financial_numbers(scoring_party))).strip()
        cat_res = self.classify_category(scoring_party, norm_text)
        data["category"] = cat_res["category"]
        data["categoryConfidence"] = cat_res["confidence"]
        data["category_confidence"] = cat_res["confidence"]

        return data

def test_file(engine, file_path, sender="BANK_SERVICE"):
    print(f"\n========================================================")
    print(f"Testing notification engine: {os.path.basename(file_path)}")
    print(f"========================================================")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    raw_blocks = [b.strip() for b in re.split(r'\n\s*\n', content) if b.strip()]

    for i, block in enumerate(raw_blocks, 1):
        res = engine.predict(sender=sender, body=block)
        status = "LOG [TRANSACTION]" if res["isValidTransaction"] else f"IGNORE [{res['reason']}]"
        preview = block.replace('\n', ' ')[:85]
        print(f"[#{i:02d}] {status:35s} (Conf: {res['confidence']:.2f}) | \"{preview}...\"")
        if res["isValidTransaction"]:
            print(f"     -> Data: {res['data']}")

def main():
    engine = MasroofEngine()
    test_file(engine, "ARAB_BANK.txt", sender="ArabiBank")
    test_file(engine, "CAPITAL_BANK.txt", sender="CapitalBank")
    test_file(engine, "BANK_AL_ETIHAD.txt", sender="BankAlEtihad")
    test_file(engine, "HOUSING_BANK.txt", sender="HousingBank")
    test_file(engine, "REFLECT.txt", sender="Reflect")
    test_file(engine, "ORANGE_MONEY.txt", sender="OrangeMoney")
    test_file(engine, "ZAIN_CASH.txt", sender="ZainCash")
    test_file(engine, "UWALLET.txt", sender="UWallet")
    test_file(engine, "CHAT_NOISE.txt", sender="Personal_Or_Bank")

if __name__ == "__main__":
    main()
