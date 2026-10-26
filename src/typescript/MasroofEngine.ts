import { normalizeFinancialNumbers, preprocessMessage, tokenizeFeatures } from './Preprocessing.ts';
import { isServiceNotice, SERVICE_NOTICE_REASON } from './ServiceNotice.ts';
import { isAuthorizationRequest, AUTHORIZATION_REQUEST_REASON } from './AuthorizationRequest.ts';
import { scoreLegacyTransactionModel } from './LegacyTransactionModel.ts';
import { EntityText } from './EntityText.ts';
import { assess } from './DetailedAssessment.ts';
import type { DetailedInput, DetailedResult } from './DetailedAssessment.ts';

/**
 * Masroof Financial Transaction Engine (React Native / TypeScript)
 *
 * Offline model scoring, structural guards, and regex entity extraction.
 * - Legacy category scoring with optional user corrections
 * - Dynamic currency detection (JOD, USD, SAR, AED, EUR, etc.)
 * - Bundled JSON weights; no native bridges
 */

export interface MasroofInput {
  sender: string;
  body: string;
  isContact?: boolean; // True if iOS resolved the sender to an address-book contact
  defaultCurrency?: string; // Optional caller/locale default currency (fallback if message specifies no currency)
}

export type TransactionType = 'EXPENSE' | 'INCOME';
export type TransactionDirection = 'OUTGOING' | 'INCOMING';

export type TransactionCategory =
  | 'Groceries & Supermarket'
  | 'Dining & Food Delivery'
  | 'Shopping & Retail'
  | 'Utilities & Bills'
  | 'Transportation & Fuel'
  | 'Health & Pharmacy'
  | 'Financial Services & Transfers'
  | 'Entertainment & Leisure'
  | 'General & Uncategorized';

export interface ParsedTransactionData {
  type: TransactionType;
  direction: TransactionDirection;
  amount: number | null;
  currency: string;
  merchantOrParty: string | null;
  accountMask: string | null;
  balance: number | null;
  category: TransactionCategory;
  categoryConfidence: number;
  originalAmount?: number | null;
  originalCurrency?: string | null;
  exchangeRate?: number | null;
}

export interface MasroofResult {
  isValidTransaction: boolean;
  confidence: number;
  reason: string | null;
  data: ParsedTransactionData | null;
}

interface ModelWeights {
  metadata: {
    name: string;
    version: string;
    language?: string;
    accuracy?: string;
    intercept_tx: number;
    intercept_credit: number;
  };
  features: Record<string, [number, number, number]>; // [idf, w_tx, w_type]
}

// JSON-friendly export format produced by the Milestone 3 Python trainer.
export interface SequenceTaggerModel {
  version: string;
  tagCount: number;
  featureIndex: Record<string, number>;
  emissionWeights: number[];
  transitionWeights: number[];
  bias: number[];
}

interface SequenceTaggerRuntimeModel {
  featureIndex: Record<string, number>;
  featureCount: number;
  emissionWeights: Float32Array;
  transitionWeights: Float32Array;
  bias: Float32Array;
}

export class MasroofEngine {
  private static model: ModelWeights | null = null;
  private static readonly MODEL_SCORE_BUFFER = new Float64Array(2);

  // ===== MILESTONE 3: STRUCTURED BIO TAGGER (INFERENCE SKELETON) =====
  // The tagger is not wired into entity extraction until its trained accuracy
  // matches the current regex baseline.
  public static readonly BIO_TAGS = [
    'O', 'B-AMT', 'I-AMT', 'B-CURR', 'I-CURR', 'B-MERCHANT',
    'I-MERCHANT', 'B-ACCT', 'I-ACCT', 'B-BAL', 'I-BAL',
  ];
  private static readonly BIO_TAG_COUNT = 11;
  private static sequenceTaggerModel: SequenceTaggerRuntimeModel | null = null;
  private static readonly SEQUENCE_TAG_SCORE_BUFFER = new Float32Array(MasroofEngine.BIO_TAG_COUNT);

  // Loads flat weights once; inference never allocates an output array.
  public static loadSequenceTaggerModel(model: SequenceTaggerModel): boolean {
    if (!model || model.tagCount !== MasroofEngine.BIO_TAG_COUNT || !model.featureIndex) return false;
    const featureCount = Object.keys(model.featureIndex).length;
    const tagCount = MasroofEngine.BIO_TAG_COUNT;
    if (
      model.emissionWeights.length !== featureCount * tagCount ||
      model.transitionWeights.length !== tagCount * tagCount ||
      model.bias.length !== tagCount
    ) {
      return false;
    }
    MasroofEngine.sequenceTaggerModel = {
      featureIndex: model.featureIndex,
      featureCount,
      emissionWeights: new Float32Array(model.emissionWeights),
      transitionWeights: new Float32Array(model.transitionWeights),
      bias: new Float32Array(model.bias),
    };
    return true;
  }

  public static clearSequenceTaggerModel(): void {
    MasroofEngine.sequenceTaggerModel = null;
  }

  // Tokens must already be normalized to the exact form used by featureIndex.
  // outTags is caller-owned and must have at least tokens.length slots.
  public static tagNormalizedTokens(tokens: readonly string[], outTags: Uint8Array): number {
    const runtime = MasroofEngine.sequenceTaggerModel;
    if (!runtime || outTags.length < tokens.length) return 0;

    let previousTag = 0;
    const tagCount = MasroofEngine.BIO_TAG_COUNT;
    for (let tokenIndex = 0; tokenIndex < tokens.length; tokenIndex++) {
      const scores = MasroofEngine.SEQUENCE_TAG_SCORE_BUFFER;
      scores.set(runtime.bias);

      const featureIndex = runtime.featureIndex[tokens[tokenIndex]];
      if (featureIndex !== undefined && featureIndex >= 0 && featureIndex < runtime.featureCount) {
        let weightOffset = featureIndex * tagCount;
        for (let tagIndex = 0; tagIndex < tagCount; tagIndex++) {
          scores[tagIndex] += runtime.emissionWeights[weightOffset + tagIndex];
        }
      }

      if (tokenIndex > 0) {
        let transitionOffset = previousTag * tagCount;
        for (let tagIndex = 0; tagIndex < tagCount; tagIndex++) {
          scores[tagIndex] += runtime.transitionWeights[transitionOffset + tagIndex];
        }
      }

      let bestTag = 0;
      let bestScore = scores[0];
      for (let tagIndex = 1; tagIndex < tagCount; tagIndex++) {
        if (scores[tagIndex] > bestScore) {
          bestScore = scores[tagIndex];
          bestTag = tagIndex;
        }
      }
      outTags[tokenIndex] = bestTag;
      previousTag = bestTag;
    }
    return tokens.length;
  }

  public static sequenceTagLabel(tagIndex: number): string {
    return MasroofEngine.BIO_TAGS[tagIndex] || 'O';
  }

  // ===== MILESTONE 2: ONLINE LEARNING LOOP (LAYER 3) — OVERLAY STORAGE =====
  // Pluggable storage adapter — zero dependency on AsyncStorage/MMKV in engine core
  public static USER_OVERLAY: Record<string, number> = Object.create(null);

  // Utility: category index lookup (aligned with CATEGORIES array)
  private static CATEGORY_TO_INDEX: Record<TransactionCategory, number> = {
    'Groceries & Supermarket': 0,
    'Dining & Food Delivery': 1,
    'Shopping & Retail': 2,
    'Utilities & Bills': 3,
    'Transportation & Fuel': 4,
    'Health & Pharmacy': 5,
    'Financial Services & Transfers': 6,
    'Entertainment & Leisure': 7,
  };

  // Public API: Load persisted overlay from JSON string (e.g., AsyncStorage.getItem(), MMKV)
  public static loadUserOverlay(jsonStr: string): void {
    try {
      const parsed = JSON.parse(jsonStr) as Record<string, unknown>;
      if (!parsed || typeof parsed !== 'object') return;

      const overlay: Record<string, number> = Object.create(null);
      for (const key in parsed) {
        if (!Object.prototype.hasOwnProperty.call(parsed, key)) continue;
        const categoryIndex = parsed[key];
        const normalizedKey = MasroofEngine.normalizeMerchant(key);
        if (normalizedKey && Number.isInteger(categoryIndex) && categoryIndex >= 0 && categoryIndex < MasroofEngine.CATEGORIES.length) {
          overlay[normalizedKey] = categoryIndex as number;
        }
      }
      this.USER_OVERLAY = overlay;
    } catch (e) {
      console.error('MasroofEngine: Failed to load user overlay:', e);
    }
  }

  // Public API: Export overlay for persistence (e.g., AsyncStorage.setItem(), MMKV)
  public static exportUserOverlay(): Record<string, number> {
    return { ...this.USER_OVERLAY };
  }

  // Public API: Apply user correction → store a direct merchant-specific override
  public static applyCorrection(merchantOrText: string, correctedCategory: TransactionCategory): void {
    const normMerchant = MasroofEngine.normalizeMerchant(merchantOrText);
    const categoryIndex = MasroofEngine.CATEGORY_TO_INDEX[correctedCategory];
    if (!normMerchant || typeof categoryIndex !== 'number') return;
    this.USER_OVERLAY[normMerchant] = categoryIndex;
  }

  // Utility: Normalize merchant name for exact matching (Hermes-safe, zero GC)
  private static normalizeMerchant(name: string): string {
    return name
      .toLowerCase()
      .trim()
      .replace(/[,\s._\-\/\\*#&'’]+/g, ' ')
      .replace(/[\u064B-\u065F\u0670\u0640]/g, '') // diacritics/tatweel/alef/teh marbuta
      .replace(/[إأآا]/g, 'ا')
      .replace(/ى/g, 'ي')
      .replace(/ة/g, 'ه')
      .trim();
  }

  // 1. Pre-compiled Regex Cache for Sub-millisecond Execution and Zero Allocation
  private static readonly RE_CLEAN_SENDER = /[\s-]/g;
  private static readonly RE_PERSONAL_PHONE_1 = /^(\+|00)[0-9]{7,15}$/;
  private static readonly RE_PERSONAL_PHONE_2 = /^0[7-9][0-9]{7,9}$/;

  private static readonly RE_CHAT_NOISE = /\b(?:i\s+(?:just\s+)?(?:sent|transferred|paid|wired|gave)|sent\s+you|just\s+sent|transferred\s+you|paid\s+you|check\s+(?:it|your\s+account)|did\s+you\s+(?:get|receive)|can\s+you\s+send\s+me|send\s+me)\b|حولتلك|حولتلكم|بعثتلك|بعتلك|شيك عليها|شيك عليه|شوفيها|شوفها|ابعثلي|وصلتك الحوالة|بالله|من\s+بنك.*?\bلحسابك/i;

  private static readonly RE_DECLINED = /\b(?:declined|failed|rejected|unsuccessful|insufficient\s+funds)\b|\bcard\b.*?\b(?:locked|blocked)\b|مرفوض(?:ة)?|تم\s+رفض|فشل(?:ت)?\s+(?:عملية|الحركة|الدفع)|تعذر\s+(?:إرسال|تنفيذ|إتمام)|لم\s+تتم\s+عملية|نأسف\s+لعدم\s+إتمام|غير\s+مكتمل(?:ة)?|تم\s+إلغاء\s+عملية|عدم\s+كفاية\s+الرصيد|عدم\s+توفر\s+رصيد|لتجاوز\s+الحد\s+المسموح/i;



  private static readonly RE_INTERNAL_1 = /between (?:(?:your|my)(?: own)?|own) accounts|transfer between accounts|internal transfer|own account transfer/i;
  private static readonly RE_INTERNAL_2 = /تحويل بين حسابات(?:ك|كم|ي)|بين حسابات(?:ك|كم|ي)|تحويل داخلي|بين الحسابات/i;
  private static readonly RE_INTERNAL_3 = /(?:transfer\s+from\s+your|from\s+your).*?(?:to\s+your|to\s+another)/i;
  private static readonly RE_INTERNAL_4 = /(?:تحويل\s+من\s+حسابك|من\s+حسابك).*?(?:إلى\s+حسابك|إلى\s+بطاقتك|إلى\s+محفظتك)/i;
  private static readonly RE_TRANSFER_VERBS = /transfer|تحويل/i;
  private static readonly RE_DEBIT_IND = /debited|خصم|سحب|debit/i;
  private static readonly RE_CREDIT_IND = /credited|قيد|إيداع|credit/i;
  private static readonly RE_ACC_MASKS = /(?:[0-9]{2,4}\*[0-9]{2,4}|xxxx[0-9]{3,4}|\*[0-9]{4}|(?:ending (?:in |with )?|المنتهي(?:ة)? ب[ـ ]*)[0-9]{4})/gi;

  private static readonly RE_TRUNCATED = /(?:لدى|إلى|من|عبر|بواسطة|\bat|\bto|\bfrom|\bwith|\bon)\s*$/i;

  private static readonly RE_EXPENSE_DIR = /\b(?:purchase|debited|debit|withdrawn|withdrawal|outward|bill\s+payment|paid)\b|شراء|خصم|سحب|صادرة|تسديد\s+فاتورة|دفع\s+فاتورة|دفع\s+مبلغ/i;
  private static readonly RE_INCOME_DIR = /\b(?:refund|reversal|inward|deposit|cashback)\b|استرجاع|واردة|استلام|إيداع|حوالة\s+واردة/i;

  private static readonly RE_NORM_DIACRITICS = /[\u064B-\u065F\u0670]/g;
  private static readonly RE_NORM_SPACES = /\s+/g;

  private static readonly AMT_PATTERN = '([0-9]{1,3}(?:,[0-9]{3})+(?:\\.[0-9]{1,3})?|[0-9]{1,2}(?:,[0-9]{2})*,[0-9]{3}(?:\\.[0-9]{1,3})?|[0-9]{1,3}(?:[\'’][0-9]{3})+(?:[\\.,][0-9]{1,3})?|[0-9]+(?:[\\.,][0-9]{1,3})?)';
  private static readonly CURR_TERMS = '(?:USD|EUR|GBP|JPY|CAD|AUD|CHF|CNY|INR|TRY|BRL|MXN|ZAR|JOD|SAR|AED|KWD|QAR|BHD|OMR|EGP|ILS|IQD|LBP|SR|KD|BD|RO|QR|DH|DHS|د\\.أ|دينار|دنانير|دينارا|ر\\.س|ريال|ريالات|ريالا|د\\.إ|درهم|دراهم|درهما|د\\.ك|ر\\.ق|د\\.ب|ر\\.ع|ج\\.م|جنيه|جنيها|[\\$€£¥₹₪])';

  private static readonly ACC_MASK_PAT = '(?:\\*[0-9]{4}|xxxx[0-9]{3,4}|[0-9]{2,4}\\*[0-9]{2,4})';
  private static readonly QUALIFIER = '(?:\\s+for\\s+acc(?:ount)?\\.?\\s*' + MasroofEngine.ACC_MASK_PAT + '(?:\\s+as\\s+of\\s+\\d{1,2}[/-]\\d{1,2}(?:[/-]\\d{2,4})?)?|\\s+' + MasroofEngine.ACC_MASK_PAT + ')?';
  private static readonly STATUS_WORDS = '(?:\\s+[\\u0621-\\u064A]+){0,4}';

  private static readonly RE_BAL_PREFIX = new RegExp(
    '(?:(?:available\\s+|current\\s+|remaining\\s+|account\\s+)?(?:bal(?:[a-z]?nce|\\.|\\b)|avail(?:\\.|\\s+)bal)|(?:رصيدك|الرصيد[دة]?|رصيد\\s+حسابك))' +
    MasroofEngine.QUALIFIER + MasroofEngine.STATUS_WORDS +
    '\\s*(?:is|هو|:)?\\s*(?:(?<![A-Za-z])' +
    MasroofEngine.CURR_TERMS +
    ')?\\s*' +
    MasroofEngine.AMT_PATTERN +
    '\\s*(?:' +
    MasroofEngine.CURR_TERMS +
    '(?![A-Za-z]))?',
    'i'
  );
  private static readonly RE_BAL_POSTFIX = new RegExp(
    MasroofEngine.AMT_PATTERN + '\\s*(?:' + MasroofEngine.CURR_TERMS + ')?\\s*(?:(?:ال)?رصيد[دة]?(?:ك)?|bal[a-z]?nce)',
    'i'
  );

  private static readonly RE_BILLED = new RegExp(
    '(?:billed\\s+(?:as\\s+)?|\\(\\s*(?=[A-Za-z]{2,3}|د\\.أ|ر\\.س|د\\.إ|[0-9])|معادل\\s+لـ\\s*|ما\\s+يعادل\\s*)(?:(?<![A-Za-z])(' +
    MasroofEngine.CURR_TERMS +
    '))?\\s*' +
    MasroofEngine.AMT_PATTERN +
    '\\s*(?:(' +
    MasroofEngine.CURR_TERMS +
    ')(?![A-Za-z]))?',
    'i'
  );

  private static readonly RE_AMT_P1 = new RegExp(
    '(?:amount|بمبلغ|بقيمة|مبلغ|دفعة|purchase\\s+of|transaction\\s+of|for)\\s*(?:is|:|of)?\\s*(?:(?<![A-Za-z])(' +
    MasroofEngine.CURR_TERMS +
    '))?\\s*' +
    MasroofEngine.AMT_PATTERN +
    '\\s*(?:(' +
    MasroofEngine.CURR_TERMS +
    ')(?![A-Za-z]))?',
    'i'
  );
  private static readonly RE_AMT_P2 = new RegExp(
    '(?<![A-Za-z])(' + MasroofEngine.CURR_TERMS + ')\\s*' + MasroofEngine.AMT_PATTERN + '(?![*0-9])',
    'i'
  );
  private static readonly RE_AMT_P3 = new RegExp(
    '(?<![*0-9])\\b' + MasroofEngine.AMT_PATTERN + '\\s*(' + MasroofEngine.CURR_TERMS + ')(?![A-Za-z])',
    'i'
  );

  private static readonly RE_GLOBAL_CURR = /(?<![A-Za-z])(USD|EUR|GBP|JPY|CAD|AUD|CHF|CNY|INR|TRY|BRL|MXN|ZAR|JOD|SAR|AED|KWD|QAR|BHD|OMR|EGP|ILS|IQD|LBP|SR|KD|BD|RO|QR|DH|DHS)(?![A-Za-z])|(?:^|[^\w\u0621-\u064A])(د\.أ|دينار|دنانير|دينارا|ر\.س|ريال|ريالات|ريالا|د\.إ|درهم|دراهم|درهما|د\.ك|ر\.ق|د\.ب|ر\.ع|ج\.م|جنيه|جنيها)(?=[^\w\u0621-\u064A]|$)|([\$€£¥₹₪])/i;

  private static readonly RE_ACC_MASK = /([0-9]{2,4}\*[0-9]{2,4}|xxxx[0-9]{3,4}|\*[0-9]{4}|(?:ending (?:in |with )?|المنتهي(?:ة)? ب[ـ ]*)([0-9]{4}))/i;

  private static readonly RE_PAREN_PARTY = /(?:محفظة|من|إلى|كليك)?\s*0[7-9][0-9]{8}\s*\(([A-Za-z0-9\u0600-\u06FF\s\.\-_]+?)\)/i;
  private static readonly RE_BILL_PARTY = /(?:دفع|تسديد)\s+فاتورة\s+(?:عبر\s+)?([A-Za-z0-9\u0600-\u06FF\s\.\-_]+?)(?=[.,;]?\s+(?:بنجاح|بقيمة|بمبلغ|عبر|من|في|\n|$))/i;

  private static readonly DELIMS = '(?:amount|on\\b|at\\b|to\\b|from\\b|via|through|as\\s+cliq|has\\s+been|with\\s+card|is|bal(?:[a-z]?nce|\\b)|your\\b|avail|\\d{1,2}[/-]\\d{1,2}|ref\\s*#|بمبلغ|بقيمة|في\\s+\\d|لدى|إلى|من(?=\\s|[.,;]|$)|عبر|بواسطة|باستخدام|بالبطاقة|بالبطاقه|رصيدك|الرصيد|بتاريخ|تم(?![\\u0621-\\u064A])|رقم|$)';
  private static readonly RE_PARTY = new RegExp('(?:from|at|to|لدى|إلى|من|لحساب|عبر)\\s+([A-Za-z0-9\\u0600-\\u06FF\\s\\.\\-_*&/\'’]+?)(?=[.,;]?\\s+' + MasroofEngine.DELIMS + '|\\n|$)', 'gi');
  private static readonly RE_ADMIN_ALERT = /\bcredit\s+limit\b.*?\b(?:increased|decreased|adjusted)\b|\b(?:did\s+you\s+(?:attempt|make)\s+(?:a\s+|this\s+)?purchase|security\s+alert|refund\s+request)\b|تم\s+(?:زيادة|تعديل|رفع)\s+سقف\s+(?:الائتمان|البطاقة)|هل\s+قمت\s+(?:بإجراء|بمحاولة)|هل\s+حاولت|طلب\s+استرداد/i;
  private static readonly RE_CLAUSE_TARGET = /^(?:account|acc\.?|card|wallet|حساب|بطاق|محفظ|your\s+account|your\s+card|[0-9x\*]{3,}|\d{1,2}:\d{2}|your\\b|avail|bal[a-z]?nce|رصيد)/i;
  private static readonly RE_PREP_EXTENSION = new RegExp('^(to|at|from|من|إلى)\\s+([A-Za-z0-9\\u0600-\\u06FF\\s\\.\\-_*&/\'’]+?)(?=[.,;]?\\s+' + MasroofEngine.DELIMS + '|\\n|$)', 'i');

  // 2. Semantic Micro-Embedding Subword Categorizer (Zero-Allocation Layer 2)
  public static readonly CATEGORIES: readonly TransactionCategory[] = [
    'Groceries & Supermarket',
    'Dining & Food Delivery',
    'Shopping & Retail',
    'Utilities & Bills',
    'Transportation & Fuel',
    'Health & Pharmacy',
    'Financial Services & Transfers',
    'Entertainment & Leisure',
  ];

  private static readonly CATEGORY_SCORE_BUFFER = new Float32Array(8);

  private static readonly SUBWORD_CATEGORY_MAP: Record<string, number> = {
    // 0: Groceries & Supermarket
    supermarket: 0, grocery: 0, groceries: 0, market: 0, hypermarket: 0, baqala: 0, food: 0, carrefour: 0, safeer: 0, lulu: 0, mart: 0, safeway: 0,
    سوبرماركت: 0, بقالة: 0, خضار: 0, تموينات: 0, ماركت: 0, اسواق: 0, هايبرماركت: 0, كارفور: 0, سيفوي: 0, البقالة: 0, السوبرماركت: 0,

    // 1: Dining & Food Delivery
    restaurant: 1, cafe: 1, coffee: 1, burger: 1, pizza: 1, kitchen: 1, grill: 1, dining: 1, delivery: 1, talabat: 1, jahez: 1, barista: 1, starbucks: 1, mcdonald: 1, kfc: 1, shawarma: 1, bakery: 1,
    مطعم: 1, كافيه: 1, مقهى: 1, قهوة: 1, شاورما: 1, وجبات: 1, برجر: 1, بيتزا: 1, توصيل: 1, طلبات: 1, ستاربكس: 1, ماكدونالدز: 1, كنتاكي: 1, مخبز: 1, مطاعم: 1,

    // 2: Shopping & Retail
    mall: 2, retail: 2, fashion: 2, clothes: 2, apparel: 2, shop: 2, boutique: 2, zara: 2, amazon: 2, noon: 2, center: 2,
    سوق: 2, مول: 2, متجر: 2, ملابس: 2, ازياء: 2, تسوق: 2, احذية: 2, سنتر: 2, سيتي: 2, المتاجر: 2,

    // 3: Utilities & Bills
    electric: 3, water: 3, utility: 3, bill: 3, telecom: 3, recharge: 3, ooredoo: 3, stc: 3, zain: 3, orange: 3, fawateer: 3,
    فاتورة: 3, كهرباء: 3, مياه: 3, انترنت: 3, اتصالات: 3, شحن: 3, فواتير: 3, مسقفات: 3, فواتيركم: 3, الفاتورة: 3,

    // 4: Transportation & Fuel
    fuel: 4, gas: 4, petrol: 4, station: 4, uber: 4, careem: 4, taxi: 4, ride: 4, transportation: 4, parking: 4, travel: 4, shell: 4, total: 4, manaseer: 4,
    مناصير: 4, بنزين: 4, بترول: 4, وقود: 4, محطة: 4, اوبر: 4, كريم: 4, تاكسي: 4, مواصلات: 4, مواقف: 4, جوبترول: 4, المحطة: 4,

    // 5: Health & Pharmacy
    pharmacy: 5, hospital: 5, clinic: 5, dental: 5, medical: 5, doctor: 5, lab: 5, medicine: 5, care: 5,
    صيدلية: 5, مستشفى: 5, عيادة: 5, اسنان: 5, دكتور: 5, مختبر: 5, علاج: 5, صحة: 5, دواء: 5, رعاية: 5, صيدليات: 5, الصيدلية: 5,

    // 6: Financial Services & Transfers
    transfer: 6, cliq: 6, exchange: 6, remittance: 6, atm: 6, interest: 6, loan: 6, wire: 6, outward: 6, inward: 6, deposit: 6, withdrawal: 6, fee: 6,
    صراف: 6, حوالة: 6, رسوم: 6, سداد: 6, تمويل: 6, ايداع: 6, تحويل: 6, كليك: 6, اقساط: 6, سحب: 6, الصراف: 6, واردة: 6, صادرة: 6, إيداع: 6,

    // 7: Entertainment & Leisure
    cinema: 7, movie: 7, netflix: 7, spotify: 7, gym: 7, fitness: 7, game: 7, entertainment: 7, tickets: 7, park: 7, resort: 7,
    سينما: 7, فيلم: 7, جيم: 7, رياضة: 7, ترفيه: 7, العاب: 7, تذاكر: 7, نادي: 7, منتجع: 7, استجمام: 7, برايم: 7, ترفيهي: 7,
  };

  public static classifyCategory(merchant: string | null, bodyText: string): { category: TransactionCategory; confidence: number } {
    // Corrected merchants bypass baseline scoring, preventing double-counting.
    const overlayIdx = merchant ? MasroofEngine.USER_OVERLAY[MasroofEngine.normalizeMerchant(merchant)] : undefined;
    if (overlayIdx !== undefined) {
      return { category: MasroofEngine.CATEGORIES[overlayIdx], confidence: 1.0 };
    }

    MasroofEngine.CATEGORY_SCORE_BUFFER.fill(0);

      // 1. Score merchant tokens with 2.5x weight
    if (merchant) {
      const mWords = merchant.toLowerCase().split(/[\s,._\-\/\\*]+/);
      for (let i = 0; i < mWords.length; i++) {
        const w = mWords[i];
        if (w.length < 2) continue;
        const cat = MasroofEngine.SUBWORD_CATEGORY_MAP[w];
        if (typeof cat === 'number') {
          MasroofEngine.CATEGORY_SCORE_BUFFER[cat] += 2.5;
        }
      }
    }

    // 2. Score message body tokens with 1.0x weight
    const bWords = bodyText.toLowerCase().split(/[\s,._\-\/\\*]+/);
    for (let i = 0; i < bWords.length; i++) {
      const w = bWords[i];
      if (w.length < 2) continue;
      const cat = MasroofEngine.SUBWORD_CATEGORY_MAP[w];
      if (typeof cat === 'number') {
        MasroofEngine.CATEGORY_SCORE_BUFFER[cat] += 1.0;
      }
    }

    let maxScore = 0;
    let bestIdx = -1;
    for (let c = 0; c < 8; c++) {
      const score = MasroofEngine.CATEGORY_SCORE_BUFFER[c];
      if (score > maxScore) {
        maxScore = score;
        bestIdx = c;
      }
    }

    if (bestIdx === -1 || maxScore < 1.5) {
      return {
        category: 'General & Uncategorized',
        confidence: 0.0,
      };
    }

    return {
      category: MasroofEngine.CATEGORIES[bestIdx],
      confidence: Math.min(1.0, Math.round((maxScore / 6.0) * 100) / 100),
    };
  }

  /**
   * Parse numeric string with comma, dot, Indian Lakhs, or Swiss apostrophe decimal format
   */
  public static parseNumber(s?: string | null): number | null {
    if (!s) return null;
    const str = normalizeFinancialNumbers(String(s)).trim().replace(/['’\s]/g, '');
    if (str.includes(',') && str.includes('.')) {
      if (str.lastIndexOf('.') > str.lastIndexOf(',')) {
        return parseFloat(str.replace(/,/g, ''));
      } else {
        return parseFloat(str.replace(/\./g, '').replace(/,/g, '.'));
      }
    } else if (str.includes(',')) {
      const parts = str.split(',');
      if (parts.length === 2 && (parts[1].length === 1 || parts[1].length === 2)) {
        return parseFloat(parts[0] + '.' + parts[1]);
      } else {
        return parseFloat(str.replace(/,/g, ''));
      }
    } else {
      return parseFloat(str);
    }
  }

  /**
   * Initialize with model weights (bundled JSON)
   */
  public static init(modelJson: ModelWeights) {
    this.model = modelJson;
  }

  /**
   * Analyzes an incoming SMS payload from Apple Shortcuts
   */
  public static analyzeDetailed(input: DetailedInput): DetailedResult {
    return assess(input,
      (body, type) => this.extractEntities(body, type, 'JOD', false),
      value => this.parseNumber(value),
      text => {
        if (!this.model) return false;
        scoreLegacyTransactionModel(this.model, this.tokenize(this.preprocess(text)), this.MODEL_SCORE_BUFFER);
        return this.MODEL_SCORE_BUFFER[0] >= 0.70;
      });
  }

  public static analyze(input: MasroofInput): MasroofResult {
    const { sender, body, isContact } = input || {};

    // 1. Check if sender is a saved personal contact in the device's address book
    if (isContact) {
      return {
        isValidTransaction: false,
        confidence: 0.0,
        reason: 'Personal sender (saved contact in phone)',
        data: null,
      };
    }

    // 2. Generic sender check: personal phone numbers vs service/bank sender IDs
    const cleanSender = normalizeFinancialNumbers(typeof sender === 'string' ? sender : '').trim().replace(this.RE_CLEAN_SENDER, '');
    const isPersonalPhoneNumber = this.RE_PERSONAL_PHONE_1.test(cleanSender) || this.RE_PERSONAL_PHONE_2.test(cleanSender);

    if (isPersonalPhoneNumber) {
      return {
        isValidTransaction: false,
        confidence: 0.0,
        reason: 'Personal sender (phone number)',
        data: null,
      };
    }

    const bodyStr = normalizeFinancialNumbers(typeof body === 'string' ? body : '');

    // Check conversational chat noise spoofing bank sender
    if (this.RE_CHAT_NOISE.test(bodyStr)) {
      return {
        isValidTransaction: false,
        confidence: 0.0,
        reason: 'Conversational chat noise',
        data: null,
      };
    }

    // Check declined / failed transactions
    if (this.RE_DECLINED.test(bodyStr)) {
      return {
        isValidTransaction: false,
        confidence: 0.0,
        reason: 'Transaction declined or failed',
        data: null,
      };
    }

    // Check administrative alerts, credit limit updates, and security fraud prompts
    if (this.RE_ADMIN_ALERT.test(bodyStr)) {
      return {
        isValidTransaction: false,
        confidence: 0.0,
        reason: 'Administrative alert, credit limit update, or security query (non-transaction)',
        data: null,
      };
    }

    if (isServiceNotice(bodyStr)) {
      return {
        isValidTransaction: false,
        confidence: 0.0,
        reason: SERVICE_NOTICE_REASON,
        data: null,
      };
    }

    if (isAuthorizationRequest(bodyStr)) {
      return {
        isValidTransaction: false,
        confidence: 0.0,
        reason: AUTHORIZATION_REQUEST_REASON,
        data: null,
      };
    }

    // 3. Machine Learning Inference
    if (!this.model) {
      try {
        this.model = require('./masroof_model.json');
      } catch (e) {
        throw new Error('MasroofEngine: masroof_model.json not loaded. Call MasroofEngine.init(json) first.');
      }
    }

    const cleaned = this.preprocess(bodyStr);
    const tokens = this.tokenize(cleaned);

    scoreLegacyTransactionModel(this.model!, tokens, this.MODEL_SCORE_BUFFER);
    const probTx = this.MODEL_SCORE_BUFFER[0];
    const probCredit = this.MODEL_SCORE_BUFFER[1];

    // Decision threshold for transactions
    const isValid = probTx >= 0.70;

    if (!isValid) {
      return {
        isValidTransaction: false,
        confidence: Number(probTx.toFixed(4)),
        reason: 'Classified as non-transaction (conversational noise, OTP, declined, or announcement)',
        data: null,
      };
    }

    // Inviolable rule: Internal transfer between user's own accounts is asset rebalancing, not net expense or income
    if (this.isInternalTransfer(bodyStr)) {
      return {
        isValidTransaction: false,
        confidence: 0.0,
        reason: 'Internal transfer between own accounts (no net expense or income)',
        data: null,
      };
    }

    // Check truncated carrier SMS
    const normBody = bodyStr.replace(this.RE_NORM_DIACRITICS, '').trim();
    if (this.RE_TRUNCATED.test(normBody)) {
      return {
        isValidTransaction: false,
        confidence: 0.0,
        reason: 'Truncated or malformed SMS',
        data: null,
      };
    }

    // Direction Calibration: Debit vs Credit keywords
    const isExp = this.RE_EXPENSE_DIR.test(normBody);
    const isInc = this.RE_INCOME_DIR.test(normBody);
    let txType: TransactionType;

    if (isExp && !isInc) {
      txType = 'EXPENSE';
    } else if (isInc && !isExp) {
      txType = 'INCOME';
    } else {
      txType = probCredit >= 0.50 ? 'INCOME' : 'EXPENSE';
    }

    // 4. Dynamic Entity Extraction (Amounts, Currencies, Parties, Balances)
    const extractedData = this.extractEntities(typeof body === 'string' ? body : '', txType, input.defaultCurrency);

    // INVIOLABLE FINANCIAL LAW: A transaction MUST have an actual monetary amount > 0!
    if (!extractedData || extractedData.amount === null || !Number.isFinite(extractedData.amount) || extractedData.amount <= 0) {
      return {
        isValidTransaction: false,
        confidence: 0.0,
        reason: 'No transaction amount detected (balance notification, inquiry, or incomplete message)',
        data: null,
      };
    }

    return {
      isValidTransaction: true,
      confidence: Number(probTx.toFixed(4)),
      reason: null,
      data: extractedData,
    };
  }

  private static preprocess(text: string): string {
    return preprocessMessage(text);
  }

  private static tokenize(text: string): string[] {
    return tokenizeFeatures(text);
  }

  private static isInternalTransfer(text: string): boolean {
    const norm = text.toLowerCase();

    if (
      this.RE_INTERNAL_1.test(norm) ||
      this.RE_INTERNAL_2.test(norm) ||
      this.RE_INTERNAL_3.test(norm) ||
      this.RE_INTERNAL_4.test(norm)
    ) {
      return true;
    }

    const hasDebit = this.RE_DEBIT_IND.test(norm);
    const hasCredit = this.RE_CREDIT_IND.test(norm);
    const matches = norm.match(this.RE_ACC_MASKS);
    if (matches && new Set(matches).size >= 2) {
      if ((hasDebit && hasCredit) || this.RE_TRANSFER_VERBS.test(norm)) {
        return true;
      }
    }

    return false;
  }

  private static normalizeCurrency(token?: string | null): string | null {
    if (!token) return null;
    const t = token.trim();
    const upper = t.toUpperCase();
    if (upper === 'د.أ' || upper === 'دينار' || upper === 'دنانير' || upper === 'دينارا' || upper === 'JD') return 'JOD';
    if (upper === 'ر.س' || upper === 'ريال' || upper === 'ريالات' || upper === 'ريالا' || upper === 'SAR' || upper === 'SR') return 'SAR';
    if (upper === 'د.إ' || upper === 'درهم' || upper === 'دراهم' || upper === 'درهما' || upper === 'AED' || upper === 'DH' || upper === 'DHS') return 'AED';
    if (upper === 'د.ك' || upper === 'KWD' || upper === 'KD') return 'KWD';
    if (upper === 'ر.ق' || upper === 'QAR' || upper === 'QR') return 'QAR';
    if (upper === 'د.ب' || upper === 'BHD' || upper === 'BD') return 'BHD';
    if (upper === 'ر.ع' || upper === 'OMR' || upper === 'RO') return 'OMR';
    if (upper === 'ج.م' || upper === 'جنيه' || upper === 'جنيها' || upper === 'EGP') return 'EGP';
    if (t === '$') return 'USD';
    if (t === '€') return 'EUR';
    if (t === '£') return 'GBP';
    if (t === '¥') return 'JPY';
    if (t === '₹') return 'INR';
    if (t === '₪') return 'ILS';
    return upper;
  }

  private static extractEntities(text: string, txType: TransactionType, defaultCurrency?: string, categorize = true): ParsedTransactionData {
    const view = new EntityText(text);
    const normText = view.text;

    const data: ParsedTransactionData = {
      type: txType,
      direction: txType === 'INCOME' ? 'INCOMING' : 'OUTGOING',
      amount: null,
      currency: defaultCurrency || 'JOD',
      merchantOrParty: null,
      accountMask: null,
      balance: null,
      category: 'General & Uncategorized',
      categoryConfidence: 0.0,
    };

    // 1. Dynamic Balance Extraction FIRST + Masking
    let amtWorkingText = normText;
    const mBalPrefix = normText.match(this.RE_BAL_PREFIX);
    const mBalPostfix = normText.match(this.RE_BAL_POSTFIX);

    if (mBalPrefix && mBalPrefix[1]) {
      try {
        data.balance = this.parseNumber(mBalPrefix[1]);
        const idx = mBalPrefix.index !== undefined ? mBalPrefix.index : amtWorkingText.indexOf(mBalPrefix[0]);
        if (idx !== -1) {
          amtWorkingText = amtWorkingText.slice(0, idx) + ' __BAL_MASK__ ' + amtWorkingText.slice(idx + mBalPrefix[0].length);
        }
      } catch (e) {}
    } else if (mBalPostfix && mBalPostfix[1]) {
      try {
        data.balance = this.parseNumber(mBalPostfix[1]);
        const idx = mBalPostfix.index !== undefined ? mBalPostfix.index : amtWorkingText.indexOf(mBalPostfix[0]);
        if (idx !== -1) {
          amtWorkingText = amtWorkingText.slice(0, idx) + ' __BAL_MASK__ ' + amtWorkingText.slice(idx + mBalPostfix[0].length);
        }
      } catch (e) {}
    }

    // 2. Dynamic Transaction Amount + Adjacent Currency Extraction
    const pBilled = amtWorkingText.match(this.RE_BILLED);
    const p1 = amtWorkingText.match(this.RE_AMT_P1);
    const p2 = amtWorkingText.match(this.RE_AMT_P2);
    const p3 = amtWorkingText.match(this.RE_AMT_P3);

    if (pBilled && pBilled[2]) {
      const billedAmt = this.parseNumber(pBilled[2]);
      const rawBilledCurr = pBilled[1] || pBilled[3] || null;
      data.amount = billedAmt;
      const normBilledCurr = this.normalizeCurrency(rawBilledCurr);
      if (normBilledCurr) {
        data.currency = normBilledCurr;
      }

      // Mask out the billed amount to find the foreign/original amount
      const bIdx = pBilled.index !== undefined ? pBilled.index : amtWorkingText.indexOf(pBilled[0]);
      if (bIdx !== -1) {
        amtWorkingText = amtWorkingText.slice(0, bIdx) + ' __BILLED_MASK__ ' + amtWorkingText.slice(bIdx + pBilled[0].length);
      }

      // Scan remaining text for foreign/original transaction amount
      const pOrig1 = amtWorkingText.match(this.RE_AMT_P1);
      const pOrig2 = amtWorkingText.match(this.RE_AMT_P2);
      const pOrig3 = amtWorkingText.match(this.RE_AMT_P3);

      let rawOrigAmt: string | null = null;
      let origCurrRaw: string | null = null;

      if (pOrig1 && pOrig1[2]) {
        rawOrigAmt = pOrig1[2];
        origCurrRaw = pOrig1[1] || pOrig1[3] || null;
      } else if (pOrig2 && pOrig2[2]) {
        rawOrigAmt = pOrig2[2];
        origCurrRaw = pOrig2[1];
      } else if (pOrig3 && pOrig3[1]) {
        rawOrigAmt = pOrig3[1];
        origCurrRaw = pOrig3[2];
      }

      if (rawOrigAmt) {
        data.originalAmount = this.parseNumber(rawOrigAmt);
        const normOrigCurr = this.normalizeCurrency(origCurrRaw);
        if (normOrigCurr) {
          data.originalCurrency = normOrigCurr;
        } else {
          const gCurr = amtWorkingText.match(this.RE_GLOBAL_CURR);
          if (gCurr) {
            const rCurr = gCurr[1] || gCurr[2] || gCurr[3];
            const nCurr = this.normalizeCurrency(rCurr);
            if (nCurr) data.originalCurrency = nCurr;
          }
        }
        if (data.amount && data.originalAmount && data.originalAmount > 0) {
          data.exchangeRate = Number((data.amount / data.originalAmount).toFixed(4));
        }
      }
    } else {
      let rawAmt: string | null = null;
      let extractedCurr: string | null = null;

      if (p1 && p1[2]) {
        rawAmt = p1[2];
        extractedCurr = p1[1] || p1[3] || null;
      } else if (p2 && p2[2]) {
        rawAmt = p2[2];
        extractedCurr = p2[1];
      } else if (p3 && p3[1]) {
        rawAmt = p3[1];
        extractedCurr = p3[2];
      }

      if (rawAmt) {
        try {
          data.amount = this.parseNumber(rawAmt);
        } catch (e) {}
      }

      // Currency Resolution
      const normExtracted = this.normalizeCurrency(extractedCurr);
      if (normExtracted) {
        data.currency = normExtracted;
      } else {
        const globalCurrMatch = amtWorkingText.match(this.RE_GLOBAL_CURR);
        if (globalCurrMatch) {
          const raw = globalCurrMatch[1] || globalCurrMatch[2] || globalCurrMatch[3];
          const norm = this.normalizeCurrency(raw);
          if (norm) data.currency = norm;
        }
      }
    }

    // 3. Dynamic Account / Card Mask Detection
    const accMatch = normText.match(this.RE_ACC_MASK);
    if (accMatch) {
      data.accountMask = accMatch[2] ? accMatch[2] : accMatch[1];
    }

    // 4. Dynamic Merchant / Recipient Party Extraction
    const mParen = normText.match(this.RE_PAREN_PARTY);
    if (mParen && mParen[1] && mParen[1].trim().length > 2) {
      const start = mParen.index! + mParen[0].lastIndexOf(mParen[1]) + mParen[1].length - mParen[1].trimStart().length;
      data.merchantOrParty = view.exact(start, start + mParen[1].trim().length);
    } else {
      const mBill = normText.match(this.RE_BILL_PARTY);
      if (mBill && mBill[1] && mBill[1].trim().length > 1) {
        let cand = mBill[1].trim();
        const start = mBill.index! + mBill[0].length - mBill[1].length + mBill[1].indexOf(cand);
        data.merchantOrParty = view.exact(start, start + cand.length);
      } else {
        this.RE_PARTY.lastIndex = 0;
        let m: RegExpExecArray | null;
        while ((m = this.RE_PARTY.exec(normText)) !== null) {
          let cand = m[1].trim();
          cand = cand.replace(/^(?:تاجر\s+)/i, '').trim();
          const candLower = cand.toLowerCase();
          if (/(?:account|acc\.?|card|wallet|حساب|بطاق|محفظ)/i.test(candLower)) {
            continue;
          }
          if (/^[x\*0-9]+$/.test(cand) || /^acc(?:\.|ount)?\s*(?:no\.?)?\s*[\*x0-9]+/i.test(candLower)) {
            continue;
          }
          if (candLower === 'cliq' || candLower === 'كليك' || candLower === 'أي فواتيركم' || candLower === 'اي فواتيركم' || /^(?:نقاط\s+البيع|apple\s+pay|مدى|الإنترنت)$/i.test(candLower)) {
            continue;
          }
          if (cand.length <= 2) {
            continue;
          }
          const candidateStart = m.index + m[0].length - m[1].length + m[1].indexOf(cand);
          let candidateEnd = candidateStart + cand.length;

          // Smart Preposition Chunker Extension: If candidate was prematurely cut by an internal preposition (e.g. Farm To Table, Subway At The Mall)
          let matchEnd = this.RE_PARTY.lastIndex;
          matchEnd += normText.slice(matchEnd).length - normText.slice(matchEnd).trimStart().length;
          let remaining = normText.slice(matchEnd);
          let mPrep = remaining.match(MasroofEngine.RE_PREP_EXTENSION);
          while (mPrep && mPrep[1] && mPrep[2]) {
            const prepWord = mPrep[1];
            const nextPart = mPrep[2].trim();
            if (MasroofEngine.RE_CLAUSE_TARGET.test(nextPart)) {
              break;
            }
            candidateEnd = matchEnd + mPrep[0].trimEnd().length;
            cand = normText.slice(candidateStart, candidateEnd);
            matchEnd += mPrep[0].length;
            matchEnd += normText.slice(matchEnd).length - normText.slice(matchEnd).trimStart().length;
            remaining = normText.slice(matchEnd);
            mPrep = remaining.match(MasroofEngine.RE_PREP_EXTENSION);
          }

          cand = cand.replace(/\s+بنجاح$/i, '').trim();
          data.merchantOrParty = view.exact(candidateStart, candidateStart + cand.length);
          break;
        }
      }
    }

    if (!categorize) return data;

    // 4. Semantic Micro-Embedding Categorization (Layer 2)
    const scoringParty = data.merchantOrParty ? normalizeFinancialNumbers(data.merchantOrParty).replace(this.RE_NORM_DIACRITICS, '').replace(this.RE_NORM_SPACES, ' ').trim() : null;
    const catResult = MasroofEngine.classifyCategory(scoringParty, normText);
    data.category = catResult.category;
    data.categoryConfidence = catResult.confidence;

    return data;
  }
}
