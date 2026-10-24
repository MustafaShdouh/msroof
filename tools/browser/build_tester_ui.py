import json
from pathlib import Path
from merchant_lab import build_merchant_lab

def build():
    root = Path(__file__).resolve().parents[2]
    with (root / "data" / "models" / "masroof_model.json").open("r", encoding="utf-8") as f:
        model_json_str = f.read()

    html_content = r'''<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Masroof ML Tester</title>
</head>
<body style="font-family: monospace; background-color: #fff; color: #000; padding: 15px;">

  <h1 style="color: darkred; margin-bottom: 5px;">Masroof ML Tester</h1>
  <small style="color: #666;">Jordan SMS engine and merchant category experiments</small>
  <hr>

  <div>
    <strong>PRESETS:</strong> <span style="color: gray;">&lt;----- click these if you're too lazy to type</span><br>
    <button onclick="loadPreset('arab_pos')">Arab Bank POS</button>
    <button onclick="loadPreset('cliq_in')">CliQ In</button>
    <button onclick="loadPreset('cliq_out')">CliQ Out</button>
    <button onclick="loadPreset('orange_wallet')">Orange Money</button>
    <button onclick="loadPreset('zain_bill')">Zain Cash</button>
    <button onclick="loadPreset('fx_usd_jod')">FX: USD Billed JOD</button>
    <button onclick="loadPreset('farm_to_table')">Collision: Farm To Table</button>
    <button onclick="loadPreset('balance_inquiry')">Trap: Balance Inquiry</button>
    <button onclick="loadPreset('incomplete_tx')">Trap: No Amount</button>
    <button onclick="loadPreset('internal_transfer')">Trap: Own Account Transfer</button>
    <button onclick="loadPreset('trap_otp')">Trap: OTP</button>
    <button onclick="loadPreset('declined')">Declined</button>
    <button onclick="loadPreset('chat_noise')">Chat Noise</button>
    <button onclick="loadPreset('gibberish')">Gibberish</button>
  </div>

  <br>
  <hr>

  <div>
    <label><strong>Sender:</strong></label><br>
    <input type="text" id="senderInput" value="ArabiBank" style="width: 250px;" oninput="runAnalysis()">
    <span>-----> this is where you put the sender name</span><br>
    <label style="font-size: 13px; color: #333; margin-top: 4px; display: inline-block;">
      <input type="checkbox" id="isContactInput" onchange="runAnalysis()">
      Sender is saved in your iPhone Contacts (e.g., Dad, Mom, Brother)
    </label>
  </div>
  <br>
  <div>
    <label><strong>SMS Body:</strong></label><br>
    <textarea id="bodyInput" rows="6" cols="70" style="vertical-align: top;" oninput="runAnalysis()"></textarea>
    <span style="vertical-align: top; display: inline-block; padding-left: 10px; margin-top: 10px;">-----> paste the actual sms message here</span>
  </div>

  <hr>

  <h3>Output Table <span style="font-size: 12px; font-weight: normal; color: blue;">-----> look here to see what the machine extracted</span></h3>
  <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; min-width: 400px;">
    <tr><td style="width: 140px;"><strong>Status:</strong></td><td id="decisionTitle">Ready</td></tr>
    <tr><td><strong>Confidence:</strong></td><td id="confidenceVal">--</td></tr>
    <tr><td><strong>Category:</strong></td><td id="fieldCategory">--</td></tr>
    <tr><td><strong>Direction:</strong></td><td id="fieldDirection">--</td></tr>
    <tr><td><strong>Amount:</strong></td><td id="fieldAmount">--</td></tr>
    <tr><td><strong>Original Amount (FX):</strong></td><td id="fieldOrigAmount">--</td></tr>
    <tr><td><strong>Exchange Rate:</strong></td><td id="fieldRate">--</td></tr>
    <tr><td><strong>Party:</strong></td><td id="fieldParty">--</td></tr>
    <tr><td><strong>Account:</strong></td><td id="fieldAccount">--</td></tr>
    <tr><td><strong>Balance:</strong></td><td id="fieldBalance">--</td></tr>
    <tr><td><strong>Latency:</strong></td><td id="latencyBadge">--</td></tr>
  </table>

  <br>
  <strong>Raw JSON:</strong><br>
  <pre id="jsonOutput" style="background: #f0f0f0; border: 1px solid #aaa; padding: 10px; width: 600px; max-height: 250px; overflow: auto;"></pre>

  __MERCHANT_LAB_MARKUP__
  <script>
    const MODEL = __MODEL_DATA__;

    const PRESETS = {
      arab_pos: {
        sender: "ArabiBank",
        body: "JO\nYou have a purchase transaction on account 1234*678 from ZAIN MARKET - ROSARY SIST amount JOD 5.450 on 20/10/2026 17:02. Balance JOD 39.132."
      },
      cliq_in: {
        sender: "ArabiBank",
        body: "JO\nJOD3.600 has been credited to 1234*678from RAAD MUNTHER MUNIER ALALI as CliQ transfer Balance 62.232JOD"
      },
      cliq_out: {
        sender: "Etihad",
        body: "JO\nOutward CliQ of JOD 15.000 debited from Acc. *9123 on 20/10/2026 to LAITH KHALED AL-OMARI. Available balance JOD 105.450."
      },
      orange_wallet: {
        sender: "OrangeMoney",
        body: "JO\nتم دفع مبلغ 6.750 JOD بنجاح إلى تاجر CARREFOUR EXPRESS بواسطة محفظة أورنج موني. رصيدك المتبقي 55.750 JOD. رقم العملية: 449012."
      },
      zain_bill: {
        sender: "ZainCash",
        body: "JO\nتم تسديد فاتورة كهرباء إربد بنجاح بقيمة 23.400 JOD من خلال خدمة إي فواتيركم. رصيدك الحالي هو 28.30 JOD."
      },
      fx_usd_jod: {
        sender: "ArabiBank",
        body: "Purchase of USD 50.00 billed as JOD 35.50 on card *1234 at AMAZON. Avail bal JOD 200."
      },
      farm_to_table: {
        sender: "Chase",
        body: "Purchase of $30.00 at FARM TO TABLE CAFE on card ending 1234. Available balance: $450.00."
      },
      balance_inquiry: {
        sender: "ArabiBank",
        body: "JOdson 20/10/2026 17:02. Balance JOD 39.132."
      },
      incomplete_tx: {
        sender: "ArabiBank",
        body: "You have a purchase transaction on account 1234*678 from ZAIN MARKET"
      },
      internal_transfer: {
        sender: "ArabiBank",
        body: "JO\nJOD 9.000 has been debited from 1234*678 and has been credited to 0108*500 on 29/09/2026 . Balance JOD 39.000"
      },
      trap_otp: {
        sender: "ArabiBank",
        body: "JO\nDO NOT SHARE THIS CODE.\nOne Time Password: 167713\nPurpose: Purchase of amount 9 JOD from PRIME CINEMAS AL ABDALI\nFees apply on international transactions."
      },
      declined: {
        sender: "CapitalBank",
        body: "حركة مرفوضة على بطاقتك المنتهية ب 8150 بقيمة JOD 5.000 بسبب عدم كفاية الرصيد, للمزيد اتصل على 065100220"
      },
      chat_noise: {
        sender: "+962791234567",
        body: "حولتلك 10 دنانير على كليك شيك عليها بالله"
      },
      gibberish: {
        sender: "Unknown",
        body: "BLAAAAH IANBDWANID"
      }
    };

    function loadPreset(key) {
      var p = PRESETS[key];
      if (p) {
        document.getElementById('senderInput').value = p.sender;
        document.getElementById('bodyInput').value = p.body;
        document.getElementById('isContactInput').checked = false;
        runAnalysis();
      }
    }

    function normalizeFinancialNumbers(text) {
      return text.replace(/[\u0660-\u0669\u06F0-\u06F9\u066B\u066C]/g, function(char) {
        var code = char.charCodeAt(0);
        if (code >= 0x0660 && code <= 0x0669) return String(code - 0x0660);
        if (code >= 0x06F0 && code <= 0x06F9) return String(code - 0x06F0);
        return code === 0x066B ? '.' : ',';
      });
    }

    function preprocess(text) {
      return normalizeFinancialNumbers(text)
        .replace(/\\n/g, '\n')
        .replace(/\r/g, '')
        .replace(/^[A-Z]{2}(\r?\n|\s+)/, '')
        .replace(/[\u064B-\u065F\u0670]/g, '')
        .replace(/\s+/g, ' ')
        .replace(/\b\d{6,}\b/g, ' NUM_LONG ')
        .trim()
        .toLowerCase();
    }

    function tokenize(text) {
      var words = text.match(/[\w\u0621-\u064A\u0660-\u0669\*\.\-]+/g) || [];
      var tokens = words.slice();
      for (var i = 0; i < words.length - 1; i++) {
        tokens.push(words[i] + ' ' + words[i + 1]);
      }
      return tokens;
    }

    function parseNumber(s) {
      if (!s) return null;
      var str = normalizeFinancialNumbers(String(s)).trim().replace(/['’\s]/g, '');
      if (str.indexOf(',') !== -1 && str.indexOf('.') !== -1) {
        if (str.lastIndexOf('.') > str.lastIndexOf(',')) {
          return parseFloat(str.replace(/,/g, ''));
        } else {
          return parseFloat(str.replace(/\./g, '').replace(/,/g, '.'));
        }
      } else if (str.indexOf(',') !== -1) {
        var parts = str.split(',');
        if (parts.length === 2 && (parts[1].length === 1 || parts[1].length === 2)) {
          return parseFloat(parts[0] + '.' + parts[1]);
        } else {
          return parseFloat(str.replace(/,/g, ''));
        }
      } else {
        return parseFloat(str);
      }
    }

    function isInternalTransfer(text) {
      var norm = text.toLowerCase();
      if (
        /between (?:your|own|my) accounts|transfer between accounts|internal transfer|own account transfer/i.test(norm) ||
        /تحويل بين حسابات(?:ك|كم|ي)|بين حسابات(?:ك|كم|ي)|تحويل داخلي|بين الحسابات/i.test(norm) ||
        /(?:transfer\s+from\s+your|from\s+your).*?(?:to\s+your|to\s+another)/i.test(norm) ||
        /(?:تحويل\s+من\s+حسابك|من\s+حسابك).*?(?:إلى\s+حسابك|إلى\s+بطاقتك|إلى\s+محفظتك)/i.test(norm)
      ) {
        return true;
      }

      var hasDebit = /debited|خصم|سحب|debit/i.test(norm);
      var hasCredit = /credited|قيد|إيداع|credit/i.test(norm);
      var accMaskRegex = /(?:[0-9]{2,4}\*[0-9]{2,4}|xxxx[0-9]{3,4}|\*[0-9]{4}|(?:ending (?:in |with )?|المنتهي(?:ة)? ب[ـ ]*)[0-9]{4})/gi;
      var matches = norm.match(accMaskRegex);
      if (matches) {
        var unique = {};
        var count = 0;
        for (var i = 0; i < matches.length; i++) {
          if (!unique[matches[i]]) {
            unique[matches[i]] = true;
            count++;
          }
        }
        if (count >= 2) {
          if ((hasDebit && hasCredit) || /transfer|تحويل/i.test(norm)) {
            return true;
          }
        }
      }
      return false;
    }

    function normalizeCurrency(token) {
      if (!token) return null;
      var t = token.trim();
      var upper = t.toUpperCase();
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

    var CATEGORIES = [
      'Groceries & Supermarket',
      'Dining & Food Delivery',
      'Shopping & Retail',
      'Utilities & Bills',
      'Transportation & Fuel',
      'Health & Pharmacy',
      'Financial Services & Transfers',
      'Entertainment & Leisure'
    ];

    // Milestone 2: host-persisted normalized merchant -> category index.
    var USER_OVERLAY = {};
    var CATEGORY_TO_INDEX = {
      'Groceries & Supermarket': 0,
      'Dining & Food Delivery': 1,
      'Shopping & Retail': 2,
      'Utilities & Bills': 3,
      'Transportation & Fuel': 4,
      'Health & Pharmacy': 5,
      'Financial Services & Transfers': 6,
      'Entertainment & Leisure': 7
    };

    function normalizeMerchant(name) {
      if (typeof name !== 'string') return '';
      return name.toLowerCase().trim()
        .replace(/[,\s._\-\/\\*#&'’]+/g, ' ')
        .replace(/[\u064B-\u065F\u0670\u0640]/g, '')
        .replace(/[إأآا]/g, 'ا')
        .replace(/ى/g, 'ي')
        .replace(/ة/g, 'ه')
        .trim();
    }

    function loadUserOverlay(jsonStr) {
      try {
        var parsed = JSON.parse(jsonStr);
        if (!parsed || typeof parsed !== 'object') return;
        var overlay = {};
        for (var merchant in parsed) {
          if (!Object.prototype.hasOwnProperty.call(parsed, merchant)) continue;
          var categoryIndex = parsed[merchant];
          var normalizedMerchant = normalizeMerchant(merchant);
          if (normalizedMerchant && Number.isInteger(categoryIndex) && categoryIndex >= 0 && categoryIndex < CATEGORIES.length) {
            overlay[normalizedMerchant] = categoryIndex;
          }
        }
        USER_OVERLAY = overlay;
      } catch (e) {}
    }

    function exportUserOverlay() {
      return Object.assign({}, USER_OVERLAY);
    }

    function applyCorrection(merchantOrText, correctedCategory) {
      var normalizedMerchant = normalizeMerchant(merchantOrText);
      var categoryIndex = CATEGORY_TO_INDEX[correctedCategory];
      if (normalizedMerchant && categoryIndex !== undefined) {
        USER_OVERLAY[normalizedMerchant] = categoryIndex;
      }
    }

    var SUBWORD_CATEGORY_MAP = {
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
      سينما: 7, فيلم: 7, جيم: 7, رياضة: 7, ترفيه: 7, العاب: 7, تذاكر: 7, نادي: 7, منتجع: 7, استجمام: 7, برايم: 7, ترفيهي: 7
    };

    var categoryScores = new Float32Array(8);

    function classifyCategory(merchant, bodyText) {
      var overlayIndex = merchant ? USER_OVERLAY[normalizeMerchant(merchant)] : undefined;
      if (overlayIndex !== undefined) {
        return { category: CATEGORIES[overlayIndex], confidence: 1.0 };
      }

      categoryScores.fill(0);
      var reSplit = /[\s,._\-\/\\*]+/;

      if (merchant) {
        var mWords = merchant.toLowerCase().split(reSplit);
        for (var i = 0; i < mWords.length; i++) {
          var w = mWords[i];
          if (w.length < 2) continue;
          var cat = SUBWORD_CATEGORY_MAP[w];
          if (cat !== undefined) categoryScores[cat] += 2.5;
        }
      }

      var bWords = bodyText.toLowerCase().split(reSplit);
      for (var i = 0; i < bWords.length; i++) {
        var w = bWords[i];
        if (w.length < 2) continue;
        var cat = SUBWORD_CATEGORY_MAP[w];
        if (cat !== undefined) categoryScores[cat] += 1.0;
      }

      var maxScore = 0;
      var bestIdx = -1;
      for (var c = 0; c < 8; c++) {
        if (categoryScores[c] > maxScore) {
          maxScore = categoryScores[c];
          bestIdx = c;
        }
      }

      if (bestIdx === -1 || maxScore < 1.5) {
        return { category: 'General & Uncategorized', confidence: 0.0 };
      }

      return {
        category: CATEGORIES[bestIdx],
        confidence: Math.min(1.0, Math.round((maxScore / 6.0) * 100) / 100)
      };
    }

    function extractEntities(text, txType) {
      var normText = text
        .replace(/\\n/g, '\n')
        .replace(/\\r/g, '')
        .replace(/[\u064B-\u065F\u0670]/g, '')
        .replace(/[\r\n\t]+/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();

      var data = {
        type: txType,
        direction: txType === 'INCOME' ? 'INCOMING' : 'OUTGOING',
        amount: null,
        currency: 'JOD',
        merchantOrParty: null,
        accountMask: null,
        balance: null
      };

      var amtRegex = '([0-9]{1,3}(?:,[0-9]{3})+(?:\\.[0-9]{1,3})?|[0-9]{1,2}(?:,[0-9]{2})*,[0-9]{3}(?:\\.[0-9]{1,3})?|[0-9]{1,3}(?:[\'’][0-9]{3})+(?:[\\.,][0-9]{1,3})?|[0-9]+(?:[\\.,][0-9]{1,3})?)';
      var currTerms = '(?:USD|EUR|GBP|JPY|CAD|AUD|CHF|CNY|INR|TRY|BRL|MXN|ZAR|JOD|SAR|AED|KWD|QAR|BHD|OMR|EGP|ILS|IQD|LBP|SR|KD|BD|RO|QR|DH|DHS|د\\.أ|دينار|دنانير|دينارا|ر\\.س|ريال|ريالات|ريالا|د\\.إ|درهم|دراهم|درهما|د\\.ك|ر\\.ق|د\\.ب|ر\\.ع|ج\\.م|جنيه|جنيها|[\\$€£¥₹₪])';

      var accMaskPat = '(?:\\*[0-9]{4}|xxxx[0-9]{3,4}|[0-9]{2,4}\\*[0-9]{2,4})';
      var qualifier = '(?:\\s+for\\s+acc(?:ount)?\\.?\\s*' + accMaskPat + '(?:\\s+as\\s+of\\s+\\d{1,2}[/-]\\d{1,2}(?:[/-]\\d{2,4})?)?|\\s+' + accMaskPat + ')?';
      var statusWords = '(?:\\s+[\\u0621-\\u064A]+){0,4}';

      // 1. Dynamic Balance Extraction FIRST + Masking
      var balPrefixPattern = new RegExp('(?:(?:available\\s+|current\\s+|remaining\\s+|account\\s+)?bal[a-z]?nce|avail(?:\\.|\\s+)bal|(?:رصيدك|الرصيد[دة]?|رصيد\\s+حسابك))' + qualifier + statusWords + '\\s*(?:is|هو|:)?\\s*(?:(?<![A-Za-z])' + currTerms + ')?\\s*' + amtRegex + '\\s*(?:' + currTerms + '(?![A-Za-z]))?', 'i');
      var balPostfixPattern = new RegExp(amtRegex + '\\s*(?:' + currTerms + ')?\\s*(?:(?:ال)?رصيد[دة]?(?:ك)?|bal[a-z]?nce)', 'i');

      var amtWorkingText = normText;
      var mBalPrefix = normText.match(balPrefixPattern);
      var mBalPostfix = normText.match(balPostfixPattern);

      if (mBalPrefix && mBalPrefix[1]) {
        try {
          data.balance = parseNumber(mBalPrefix[1]);
          var idx = mBalPrefix.index !== undefined ? mBalPrefix.index : amtWorkingText.indexOf(mBalPrefix[0]);
          if (idx !== -1) {
            amtWorkingText = amtWorkingText.slice(0, idx) + ' __BAL_MASK__ ' + amtWorkingText.slice(idx + mBalPrefix[0].length);
          }
        } catch(e) {}
      } else if (mBalPostfix && mBalPostfix[1]) {
        try {
          data.balance = parseNumber(mBalPostfix[1]);
          var idx = mBalPostfix.index !== undefined ? mBalPostfix.index : amtWorkingText.indexOf(mBalPostfix[0]);
          if (idx !== -1) {
            amtWorkingText = amtWorkingText.slice(0, idx) + ' __BAL_MASK__ ' + amtWorkingText.slice(idx + mBalPostfix[0].length);
          }
        } catch(e) {}
      }

      // 2. Dynamic Transaction Amount + Adjacent Currency Extraction
      var pBilled = amtWorkingText.match(new RegExp('(?:billed\\s+(?:as\\s+)?|\\(\\s*(?=[A-Za-z]{2,3}|د\\.أ|ر\\.س|د\\.إ|[0-9])|معادل\\s+لـ\\s*|ما\\s+يعادل\\s*)(?:(?<![A-Za-z])(' + currTerms + '))?\\s*' + amtRegex + '\\s*(?:(' + currTerms + ')(?![A-Za-z]))?', 'i'));
      var p1 = amtWorkingText.match(new RegExp('(?:amount|بمبلغ|بقيمة|مبلغ|دفعة|purchase\\s+of|transaction\\s+of|for)\\s*(?:is|:|of)?\\s*(?:(?<![A-Za-z])(' + currTerms + '))?\\s*' + amtRegex + '\\s*(?:(' + currTerms + ')(?![A-Za-z]))?', 'i'));
      var p2 = amtWorkingText.match(new RegExp('(?<![A-Za-z])(' + currTerms + ')\\s*' + amtRegex + '(?![*0-9])', 'i'));
      var p3 = amtWorkingText.match(new RegExp('(?<![*0-9])\\b' + amtRegex + '\\s*(' + currTerms + ')(?![A-Za-z])', 'i'));

      if (pBilled && pBilled[2]) {
        var billedAmt = parseNumber(pBilled[2]);
        var rawBilledCurr = pBilled[1] || pBilled[3] || null;
        data.amount = billedAmt;
        var normBilledCurr = normalizeCurrency(rawBilledCurr);
        if (normBilledCurr) data.currency = normBilledCurr;

        var bIdx = pBilled.index !== undefined ? pBilled.index : amtWorkingText.indexOf(pBilled[0]);
        if (bIdx !== -1) {
          amtWorkingText = amtWorkingText.slice(0, bIdx) + ' __BILLED_MASK__ ' + amtWorkingText.slice(bIdx + pBilled[0].length);
        }

        var pOrig1 = amtWorkingText.match(new RegExp('(?:amount|بمبلغ|بقيمة|مبلغ|دفعة|purchase\\s+of|transaction\\s+of|for)\\s*(?:is|:|of)?\\s*(?:(?<![A-Za-z])(' + currTerms + '))?\\s*' + amtRegex + '\\s*(?:(' + currTerms + ')(?![A-Za-z]))?', 'i'));
        var pOrig2 = amtWorkingText.match(new RegExp('(?<![A-Za-z])(' + currTerms + ')\\s*' + amtRegex + '(?![*0-9])', 'i'));
        var pOrig3 = amtWorkingText.match(new RegExp('(?<![*0-9])\\b' + amtRegex + '\\s*(' + currTerms + ')(?![A-Za-z])', 'i'));

        var rawOrigAmt = null;
        var origCurrRaw = null;

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
          data.originalAmount = parseNumber(rawOrigAmt);
          var normOrigCurr = normalizeCurrency(origCurrRaw);
          if (normOrigCurr) {
            data.originalCurrency = normOrigCurr;
          } else {
            var gCurr = amtWorkingText.match(new RegExp('(?<![A-Za-z])(' + currTerms + ')', 'i'));
            if (gCurr) {
              var nCurr = normalizeCurrency(gCurr[1]);
              if (nCurr) data.originalCurrency = nCurr;
            }
          }
          if (data.amount && data.originalAmount && data.originalAmount > 0) {
            data.exchangeRate = Number((data.amount / data.originalAmount).toFixed(4));
          }
        }
      } else {
        var rawAmt = null;
        var extractedCurr = null;

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
          try { data.amount = parseNumber(rawAmt); } catch(e) {}
        }

        var normExtracted = normalizeCurrency(extractedCurr);
        if (normExtracted) {
          data.currency = normExtracted;
        } else {
          var globalCurrMatch = amtWorkingText.match(new RegExp('(?<![A-Za-z])(USD|EUR|GBP|JPY|CAD|AUD|CHF|CNY|INR|TRY|BRL|MXN|ZAR|JOD|SAR|AED|KWD|QAR|BHD|OMR|EGP|ILS|IQD|LBP|SR|KD|BD|RO|QR|DH|DHS)(?![A-Za-z])|(?:^|[^\\w\\u0621-\\u064A])(د\\.أ|دينار|دنانير|دينارا|ر\\.س|ريال|ريالات|ريالا|د\\.إ|درهم|دراهم|درهما|د\\.ك|ر\\.ق|د\\.ب|ر\\.ع|ج\\.م|جنيه|جنيها)(?=[^\\w\\u0621-\\u064A]|$)|([\\$€£¥₹₪])', 'i'));
          if (globalCurrMatch) {
            var raw = globalCurrMatch[1] || globalCurrMatch[2] || globalCurrMatch[3];
            var norm = normalizeCurrency(raw);
            if (norm) data.currency = norm;
          }
        }
      }

      var accMatch = normText.match(/([0-9]{2,4}\*[0-9]{2,4}|xxxx[0-9]{3,4}|\*[0-9]{4}|(?:ending (?:in |with )?|المنتهي(?:ة)? ب[ـ ]*)([0-9]{4}))/i);
      if (accMatch) {
        data.accountMask = accMatch[2] ? accMatch[2] : accMatch[1];
      }

      // Dynamic Merchant / Recipient Party Extraction
      var mParen = normText.match(/(?:محفظة|من|إلى|كليك)?\s*0[7-9][0-9]{8}\s*\(([A-Za-z0-9\u0600-\u06FF\s\.\-_]+?)\)/i);
      if (mParen && mParen[1] && mParen[1].trim().length > 2) {
        data.merchantOrParty = mParen[1].trim();
      } else {
        var mBill = normText.match(/(?:دفع|تسديد)\s+فاتورة\s+(?:عبر\s+)?([A-Za-z0-9\u0600-\u06FF\s\.\-_]+?)(?=[.,;]?\s+(?:بنجاح|بقيمة|بمبلغ|عبر|من|في|\n|$))/i);
        if (mBill && mBill[1] && mBill[1].trim().length > 1) {
          var candBill = mBill[1].trim().replace(/^(?:خدمة|شركة)\s+/i, '').trim();
          data.merchantOrParty = candBill;
        } else {
          var delims = '(?:amount|on\\b|at\\b|to\\b|from\\b|via|through|as\\s+cliq|has\\s+been|with\\s+card|is|bal(?:[a-z]?nce|\\b)|avail|\\d{1,2}[/-]\\d{1,2}|ref\\s*#|بمبلغ|بقيمة|في\\s+\\d|لدى|إلى|من|عبر|بواسطة|باستخدام|بالبطاقة|بالبطاقه|رصيدك|الرصيد|بتاريخ|تم|رقم|$)';
          var partyRegex = new RegExp('(?:from|at|to|لدى|إلى|من|لحساب|عبر)\\s+([A-Za-z0-9\\u0600-\\u06FF\\s\\.\\-_*&/\'’]+?)(?=[.,;]?\\s+' + delims + '|\\n|$)', 'gi');
          var mMatch;
          var rePrepExtension = new RegExp('^(to|at|from|من|إلى)\\s+([A-Za-z0-9\\u0600-\\u06FF\\s\\.\\-_*&/\'’]+?)(?=[.,;]?\\s+' + delims + '|\\n|$)', 'i');
          var reClauseTarget = /^(?:account|acc\.?|card|wallet|حساب|بطاق|محفظ|your\s+account|your\s+card|[0-9x\*]{3,}|\d{1,2}:\d{2}|avail|bal[a-z]?nce|رصيد)/i;

          while ((mMatch = partyRegex.exec(normText)) !== null) {
            var cand = mMatch[1].trim();
            cand = cand.replace(/^(?:تاجر\s+)/i, '').trim();
            var candLower = cand.toLowerCase();
            if (/(?:account|acc\.?|card|wallet|حساب|بطاق|محفظ)/i.test(candLower)) continue;
            if (/^[x\*0-9]+$/.test(cand) || /^acc(?:\.|ount)?\s*(?:no\.?)?\s*[\*x0-9]+/i.test(candLower)) continue;
            if (candLower === 'cliq' || candLower === 'كليك' || candLower === 'أي فواتيركم' || candLower === 'اي فواتيركم' || /^(?:نقاط\s+البيع|apple\s+pay|مدى|الإنترنت)$/i.test(candLower)) continue;
            if (cand.length <= 2) continue;

            // Smart Preposition Extension
            var matchEnd = partyRegex.lastIndex;
            var remaining = normText.slice(matchEnd).trim();
            var mPrep = remaining.match(rePrepExtension);
            while (mPrep && mPrep[1] && mPrep[2]) {
              var prepWord = mPrep[1];
              var nextPart = mPrep[2].trim();
              if (reClauseTarget.test(nextPart)) break;
              cand = (cand + ' ' + prepWord + ' ' + nextPart).trim();
              matchEnd += mPrep[0].length;
              remaining = normText.slice(matchEnd).trim();
              mPrep = remaining.match(rePrepExtension);
            }

            cand = cand.replace(/\s+بنجاح$/i, '').trim();
            data.merchantOrParty = cand;
            break;
          }
        }
      }

      var catRes = classifyCategory(data.merchantOrParty, normText);
      data.category = catRes.category;
      data.categoryConfidence = catRes.confidence;

      return data;
    }

    function analyze(sender, body, isContact) {
      var t0 = performance.now();

      if (isContact) {
        return {
          result: {
            isValidTransaction: false,
            confidence: 0.0,
            reason: 'Personal sender (saved contact in phone)',
            data: null
          },
          latency: performance.now() - t0
        };
      }

      var cleanSender = normalizeFinancialNumbers(sender || '').trim().replace(/[\s-]/g, '');
      var isPersonal = /^(\+|00)[0-9]{7,15}$/.test(cleanSender) || /^0[7-9][0-9]{7,9}$/.test(cleanSender);

      if (isPersonal) {
        return {
          result: {
            isValidTransaction: false,
            confidence: 0.0,
            reason: 'Personal sender (phone number)',
            data: null
          },
          latency: performance.now() - t0
        };
      }

      var bodyStr = normalizeFinancialNumbers(body || '');

      // Check conversational chat noise spoofing
      if (/\b(?:i\s+(?:just\s+)?(?:sent|transferred|paid|wired|gave)|sent\s+you|just\s+sent|transferred\s+you|paid\s+you|check\s+(?:it|your\s+account)|did\s+you\s+(?:get|receive)|can\s+you\s+send\s+me|send\s+me)\b|حولتلك|حولتلكم|بعثتلك|بعتلك|شيك عليها|شيك عليه|شوفيها|شوفها|ابعثلي|وصلتك الحوالة|بالله|من\s+بنك.*?\bلحسابك/i.test(bodyStr)) {
        return {
          result: {
            isValidTransaction: false,
            confidence: 0.0,
            reason: 'Conversational chat noise',
            data: null
          },
          latency: performance.now() - t0
        };
      }

      // Check declined / failed transactions
      if (/\b(?:declined|failed|rejected|unsuccessful|insufficient\s+funds)\b|\bcard\b.*?\b(?:locked|blocked)\b|مرفوض(?:ة)?|تم\s+رفض|فشل(?:ت)?\s+(?:عملية|الحركة|الدفع)|تعذر\s+(?:إرسال|تنفيذ|إتمام)|لم\s+تتم\s+عملية|نأسف\s+لعدم\s+إتمام|غير\s+مكتمل(?:ة)?|تم\s+إلغاء\s+عملية|عدم\s+كفاية\s+الرصيد|عدم\s+توفر\s+رصيد|لتجاوز\s+الحد\s+المسموح/i.test(bodyStr)) {
        return {
          result: {
            isValidTransaction: false,
            confidence: 0.0,
            reason: 'Transaction declined or failed',
            data: null
          },
          latency: performance.now() - t0
        };
      }

      var cleaned = preprocess(bodyStr);
      var tokens = tokenize(cleaned);

      var scoreTx = MODEL.metadata.intercept_tx;
      var scoreCredit = MODEL.metadata.intercept_credit;

      for (var i = 0; i < tokens.length; i++) {
        var tok = tokens[i];
        var feat = MODEL.features[tok];
        if (feat) {
          scoreTx += feat[1] * feat[0];
          scoreCredit += feat[2] * feat[0];
        }
      }

      var probTx = 1.0 / (1.0 + Math.exp(-scoreTx));
      var probCredit = 1.0 / (1.0 + Math.exp(-scoreCredit));
      var isValid = probTx >= 0.70;

      if (!isValid) {
        return {
          result: {
            isValidTransaction: false,
            confidence: Number(probTx.toFixed(4)),
            reason: 'Classified as non-transaction (conversational noise, OTP, declined, or announcement)',
            data: null
          },
          latency: performance.now() - t0
        };
      }

      if (isInternalTransfer(bodyStr)) {
        return {
          result: {
            isValidTransaction: false,
            confidence: 0.0,
            reason: 'Internal transfer between own accounts (no net expense or income)',
            data: null
          },
          latency: performance.now() - t0
        };
      }

      // Check truncated carrier SMS
      var normBody = bodyStr.replace(/[\u064B-\u065F\u0670]/g, '').trim();
      if (/(?:لدى|إلى|من|عبر|بواسطة|\bat|\bto|\bfrom|\bwith|\bon)\s*$/i.test(normBody)) {
        return {
          result: {
            isValidTransaction: false,
            confidence: 0.0,
            reason: 'Truncated or malformed SMS',
            data: null
          },
          latency: performance.now() - t0
        };
      }

      // Direction calibration
      var isExp = /\b(?:purchase|debited|debit|withdrawn|withdrawal|outward|bill\s+payment|paid)\b|شراء|خصم|سحب|صادرة|تسديد\s+فاتورة|دفع\s+فاتورة|دفع\s+مبلغ/i.test(normBody);
      var isInc = /\b(?:refund|reversal|inward|deposit|cashback)\b|استرجاع|واردة|استلام|إيداع|حوالة\s+واردة/i.test(normBody);
      var txType;
      if (isExp && !isInc) {
        txType = 'EXPENSE';
      } else if (isInc && !isExp) {
        txType = 'INCOME';
      } else {
        txType = probCredit >= 0.50 ? 'INCOME' : 'EXPENSE';
      }

      var extracted = extractEntities(bodyStr, txType);

      if (!extracted || extracted.amount === null || extracted.amount <= 0) {
        return {
          result: {
            isValidTransaction: false,
            confidence: 0.0,
            reason: 'No transaction amount detected (balance notification, inquiry, or incomplete message)',
            data: null
          },
          latency: performance.now() - t0
        };
      }

      return {
        result: {
          isValidTransaction: true,
          confidence: Number(probTx.toFixed(4)),
          reason: null,
          data: extracted
        },
        latency: performance.now() - t0
      };
    }

    function runAnalysis() {
      var sender = document.getElementById('senderInput').value;
      var body = document.getElementById('bodyInput').value;
      var isContact = document.getElementById('isContactInput').checked;

      if (!body.trim()) {
        updateMerchantSms(null);
        document.getElementById('decisionTitle').innerText = "Ready (Type text or click preset)";
        document.getElementById('decisionTitle').style.color = "black";
        document.getElementById('confidenceVal').innerText = "--";
        document.getElementById('fieldCategory').innerText = "--";
        document.getElementById('fieldDirection').innerText = "--";
        document.getElementById('fieldAmount').innerText = "--";
        document.getElementById('fieldOrigAmount').innerText = "--";
        document.getElementById('fieldRate').innerText = "--";
        document.getElementById('fieldParty').innerText = "--";
        document.getElementById('fieldAccount').innerText = "--";
        document.getElementById('fieldBalance').innerText = "--";
        document.getElementById('jsonOutput').innerText = "{}";
        document.getElementById('latencyBadge').innerText = "0 ms";
        return;
      }

      var analysis = analyze(sender, body, isContact);
      var result = analysis.result;
      updateMerchantSms(result);
      var latency = analysis.latency;

      document.getElementById('latencyBadge').innerText = latency.toFixed(3) + " ms";
      document.getElementById('confidenceVal').innerText = result.confidence;

      var title = document.getElementById('decisionTitle');

      if (result.isValidTransaction) {
        title.innerText = "VALID TRANSACTION";
        title.style.color = "green";

        var d = result.data;
        document.getElementById('fieldCategory').innerText = d.category ? (d.category + " (" + Math.round(d.categoryConfidence * 100) + "%)") : "--";
        document.getElementById('fieldDirection').innerText = d.type + " (" + d.direction + ")";
        document.getElementById('fieldAmount').innerText = d.amount + " " + d.currency;
        document.getElementById('fieldOrigAmount').innerText = (d.originalAmount && d.originalCurrency) ? (d.originalAmount + " " + d.originalCurrency) : "None (Single Currency)";
        document.getElementById('fieldRate').innerText = d.exchangeRate ? ("1 " + d.originalCurrency + " = " + d.exchangeRate + " " + d.currency) : "None";
        document.getElementById('fieldParty').innerText = d.merchantOrParty || "None";
        document.getElementById('fieldAccount').innerText = d.accountMask || "None";
        document.getElementById('fieldBalance').innerText = d.balance !== null ? (d.balance + " " + d.currency) : "None";
      } else {
        title.innerText = "REJECTED (" + (result.reason || "Invalid") + ")";
        title.style.color = "red";

        document.getElementById('fieldCategory').innerText = "--";
        document.getElementById('fieldDirection').innerText = "--";
        document.getElementById('fieldAmount').innerText = "--";
        document.getElementById('fieldOrigAmount').innerText = "--";
        document.getElementById('fieldRate').innerText = "--";
        document.getElementById('fieldParty').innerText = "--";
        document.getElementById('fieldAccount').innerText = "--";
        document.getElementById('fieldBalance').innerText = "--";
      }

      document.getElementById('jsonOutput').innerText = JSON.stringify(result, null, 2);
    }

    __MERCHANT_LAB_SCRIPT__
    document.addEventListener("DOMContentLoaded", function() {
      loadPreset('arab_pos');
    });
  </script>
</body>
</html>'''

    final_html = html_content.replace("__MODEL_DATA__", model_json_str)
    markup, script = build_merchant_lab(root)
    final_html = final_html.replace("__MERCHANT_LAB_MARKUP__", markup).replace("__MERCHANT_LAB_SCRIPT__", script)

    final_html = "\n".join(line.rstrip() for line in final_html.splitlines()) + "\n"

    workspace_path = Path(__file__).resolve().with_name("tester.html")
    with workspace_path.open("w", encoding="utf-8") as f:
        f.write(final_html)
    print(f"Saved workspace tester: {workspace_path}")

if __name__ == "__main__":
    build()
