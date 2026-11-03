const SmsSemanticsResearch = (() => {
const contract = {
  "contractVersion": "1.0.0",
  "scope": "Approved isolated weak-supervision A/B research; never an active runtime model",
  "arms": ["word", "word_char"],
  "normalization": "NFC; financial digit/separator normalization; literal backslash-n decoded; CR removed; exact JO-newline routing prefix removed; Arabic U+064B-065F/U+0670 marks removed; ASCII A-Z lowered; numeric runs replaced by spaced num; explicit whitespace collapsed",
  "numericPattern": "[0-9]+(?:[.,][0-9]+)*",
  "whitespacePattern": "[ \\t\\n\\r\\f\\v\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]+",
  "words": "Maximal Unicode letter/number/underscore runs; binary feature w|token",
  "characters": "word_char only: all contiguous Unicode-code-point substrings of lengths 3,4,5 of the entire normalized text, including spaces/punctuation; binary cN|substring; no padding",
  "ordering": "Distinct features sorted by Unicode code point; vocabulary built per head from training rows only with document frequency>=2; active vocabulary indices sorted ascending for scoring",
  "export": "Separate completion/direction heads with sorted vocabulary, aligned flat float64 weights, float64 intercept; no TF-IDF/scaling or hidden features",
  "score": "Float64 intercept, then one float64 weight addition per sorted active vocabulary index; positive iff score>0; ties negative; scores are not calibrated certainty",
  "scoreTolerance": 1e-12,
  "heads": {
    "completion": {"negative": "non_transaction", "positive": "completed"},
    "direction": {"negative": "outgoing", "positive": "incoming"}
  },
  "fit": {"solver": "liblinear", "C": 1.0, "l1Ratio": 0.0, "dual": false, "fitIntercept": true, "interceptScaling": 1, "tolerance": 0.0001, "maxIterations": 2000, "seed": 20261027, "minimumDocumentFrequency": 2, "classWeight": null, "sampleWeight": "one total per source expression per head", "convergenceFailure": "stop without another trial"},
  "cohorts": {"proposalManifestSha256": "60e44bb3ca335c36c93660a7385607c8f1fdd0d2a0b0e3497e5d861127d82eac", "validationManifestSha256": "a910150b95c0bbd2dddd99bed3d88338e57e04ca29de4e28d5afe7955ef223a7", "trainingCompletion": 944, "trainingDirection": 321, "validationCompletion": 18, "validationDirection": 4},
  "constraints": ["Exactly one fit per arm/head; no tuning or validation-derived vocabulary", "No eligibility flag edits, fresh augmentation, ownership/purpose/BIO fitting or active-loader migration", "Only unblocked weak validation representatives; no descendant inheritance or reserved merchant-final inference", "Report raw learned heads separately from unchanged structural baseline; no hybrid model/guard integration", "This development trial cannot authorize release or establish independent accuracy"]
}
;
const contextContract = {
  "contractVersion": "1.0.0",
  "scope": "Research completion candidate, with unchanged word-only direction reference",
  "normalization": "Reuse sms_semantics_model.json normalization exactly",
  "features": "Binary Unicode word unigrams w|, contiguous word bigrams b| and trigrams t|, joined with ASCII spaces; punctuation is a separator, not a scope parser",
  "lengths": [1, 2, 3],
  "prefixes": ["w|", "b|", "t|"],
  "minimumDocumentFrequency": 2,
  "ordering": "Unique code-point-sorted features; training-only vocabulary; ascending active-index float64 accumulation",
  "boundary": "completed iff score > 0, ties non_transaction; uncalibrated signed decision values",
  "direction": "Exact frozen sms_semantics_followup_v1 direction head; original word-only features",
  "limits": "Short word sequences do not implement general negation scope, quotation parsing, ownership or uncertainty"
}
;
/** Versioned preprocessing shared by Masroof inference and training tests. */

const PREPROCESSING_CONTRACT_VERSION = '1.1.0';

const ROUTING_PREFIX = /^[A-Z]{2}(\r?\n|\s+)/;
const ARABIC_DIACRITICS = /[\u064B-\u065F\u0670]/g;
const WHITESPACE = /\s+/g;
const LONG_NUMBER = /\b\d{6,}\b/g;
const TOKEN = /[A-Za-z0-9_\u0621-\u064A\u0660-\u0669*\.\-]+/g;

function normalizeFinancialNumbers(text        )         {
  return text.replace(/[\u0660-\u0669\u06F0-\u06F9\u066B\u066C]/g, char => {
    const code = char.charCodeAt(0);
    if (code >= 0x0660 && code <= 0x0669) return String(code - 0x0660);
    if (code >= 0x06F0 && code <= 0x06F9) return String(code - 0x06F0);
    return code === 0x066B ? '.' : ',';
  });
}

function preprocessMessage(text        )         {
  return normalizeFinancialNumbers(text)
    .replace(/\\n/g, '\n')
    .replace(/\r/g, '')
    .replace(ROUTING_PREFIX, '')
    .replace(ARABIC_DIACRITICS, '')
    .replace(WHITESPACE, ' ')
    .replace(LONG_NUMBER, ' NUM_LONG ')
    .trim()
    .toLowerCase();
}

function tokenizeFeatures(normalizedText        )           {
  const tokens = normalizedText.match(TOKEN) || [];
  const tokenCount = tokens.length;
  for (let index = 0; index < tokenCount - 1; index++) {
    tokens.push(`${tokens[index]} ${tokens[index + 1]}`);
  }
  return tokens;
}

/** Isolated research feature/export contract; never used by the active engine. */



function codePointCompare(left        , right        )         {
  const a = Array.from(left), b = Array.from(right);
  for (let index = 0; index < Math.min(a.length, b.length); index++) {
    const difference = a[index].codePointAt(0)  - b[index].codePointAt(0) ;
    if (difference) return difference;
  }
  return a.length - b.length;
}

function normalize(text        )         {
  if (typeof text !== 'string') throw new TypeError('text must be a string');
  let value = normalizeFinancialNumbers(text.normalize('NFC')).replace(/\\n/g, '\n').replace(/\r/g, '');
  if (value.startsWith('JO\n')) value = value.slice(3);
  value = value.replace(/[\u064b-\u065f\u0670]/g, '').replace(/[A-Z]/g, char => char.toLowerCase());
  return value.replace(new RegExp(contract.numericPattern, 'g'), ' num ')
    .replace(new RegExp(contract.whitespacePattern, 'g'), ' ').replace(/^ +| +$/g, '');
}

function features(text        , arm        )           {
  if (!contract.arms.includes(arm)) throw new Error('Unsupported research arm');
  const value = normalize(text);
  const result = new Set((value.match(/[\p{L}\p{N}_]+/gu) ?? []).map(word => 'w|' + word));
  if (arm === 'word_char') {
    const chars = Array.from(value);
    for (const length of [3, 4, 5]) {
      for (let index = 0; index <= chars.length - length; index++) result.add(`c${length}|` + chars.slice(index, index + length).join(''));
    }
  }
  return [...result].sort(codePointCompare);
}

function validateModel(model     )       {
  if (!model || model.contractVersion !== contract.contractVersion || !contract.arms.includes(model.arm) ||
      !model.heads || JSON.stringify(Object.keys(model.heads).sort()) !== JSON.stringify(Object.keys(contract.heads).sort())) throw new Error('Invalid research model/version/arm/heads');
  for (const [name, head] of Object.entries(model.heads)                   ) {
    if (!Array.isArray(head.vocabulary) || head.vocabulary.some((word     ) => typeof word !== 'string') ||
        head.vocabulary.some((word        , index        ) => index > 0 && codePointCompare(head.vocabulary[index - 1], word) >= 0)) throw new Error('Invalid vocabulary order/duplicates');
    const prefixes = model.arm === 'word' ? ['w|'] : ['w|', 'c3|', 'c4|', 'c5|'];
    if (head.vocabulary.some((word        ) => !prefixes.some(prefix => word.startsWith(prefix)))) throw new Error('Feature encoding does not match arm');
    if (!Array.isArray(head.weights) || head.weights.length !== head.vocabulary.length || head.weights.some((weight     ) => typeof weight !== 'number' || !Number.isFinite(weight)) ||
        typeof head.intercept !== 'number' || !Number.isFinite(head.intercept)) throw new Error('Invalid flat weights/intercept');
    const labels = (contract.heads       )[name];
    if (!head.labels || Object.keys(head.labels).length !== 2 || head.labels.positive !== labels.positive || head.labels.negative !== labels.negative) throw new Error('Invalid head labels');
  }
}

class SmsSemanticsModel {
  model     ;
  indices                                     ;
  constructor(model     ) {
    validateModel(model);
    this.model = model;
    this.indices = Object.fromEntries(Object.entries(model.heads).map(([name, head]               ) =>
      [name, new Map(head.vocabulary.map((word        , index        ) => [word, index]))]));
  }
  predict(text        )      {
    const emitted = features(text, this.model.arm);
    const heads                      = {};
    for (const [name, head] of Object.entries(this.model.heads)                   ) {
      const lookup = this.indices[name];
      const active = emitted.filter(word => lookup.has(word)).map(word => lookup.get(word) ).sort((a, b) => a - b);
      let score = head.intercept;
      for (const index of active) score += head.weights[index];
      if (!Number.isFinite(score)) throw new Error('Non-finite accumulated score');
      heads[name] = { activeIndices: active, score, prediction: head.labels[score > 0 ? 'positive' : 'negative'] };
    }
    return { normalized: normalize(text), features: emitted, heads };
  }
}

const wordFeatures = features;
/** Research-only short word sequences; no semantic keyword rules or threshold tuning. */




function contextFeatures(text        )           {
  const words = normalize(text).match(/[\p{L}\p{N}_]+/gu) ?? [];
  const result = new Set        ();
  contextContract.lengths.forEach((size, order) => {
    for (let i = 0; i <= words.length - size; i++) result.add(contextContract.prefixes[order] + words.slice(i, i + size).join(' '));
  });
  return [...result].sort(codePointCompare);
}

function validateContextModel(model     )       {
  if (!model || model.contractVersion !== contextContract.contractVersion || model.kind !== 'completion_context' || !model.heads ||
      JSON.stringify(Object.keys(model.heads).sort()) !== JSON.stringify(Object.keys(contract.heads).sort())) throw new Error('Invalid context model kind/version/heads');
  for (const [name, head] of Object.entries(model.heads)                   ) {
    const prefixes = name === 'completion' ? contextContract.prefixes : ['w|'];
    if (!Array.isArray(head.vocabulary) || head.vocabulary.some((x     ) => typeof x !== 'string' || !prefixes.some(p => x.startsWith(p))) ||
        head.vocabulary.some((x        , i        ) => i > 0 && codePointCompare(head.vocabulary[i - 1], x) >= 0)) throw new Error('Invalid context vocabulary/order/encoding');
    if (!Array.isArray(head.weights) || head.weights.length !== head.vocabulary.length || head.weights.some((x     ) => typeof x !== 'number' || !Number.isFinite(x)) ||
        typeof head.intercept !== 'number' || !Number.isFinite(head.intercept)) throw new Error('Invalid context flat weights/intercept');
    const labels = (contract.heads       )[name];
    if (!head.labels || Object.keys(head.labels).length !== 2 || head.labels.positive !== labels.positive || head.labels.negative !== labels.negative) throw new Error('Invalid context head labels');
  }
}

class SmsCompletionContextModel {
  model     ;
  indices                                     ;
  constructor(model     ) {
    validateContextModel(model);
    this.model = model;
    this.indices = Object.fromEntries(Object.entries(model.heads).map(([name, head]               ) =>
      [name, new Map(head.vocabulary.map((word        , index        ) => [word, index]))]));
  }
  predict(text        )      {
    const emitted                           = { completion: contextFeatures(text), direction: wordFeatures(text, 'word') };
    const heads                      = {};
    for (const [name, head] of Object.entries(this.model.heads)                   ) {
      const lookup = this.indices[name];
      const active = emitted[name].filter(x => lookup.has(x)).map(x => lookup.get(x) ).sort((a, b) => a - b);
      let score = head.intercept;
      for (const index of active) score += head.weights[index];
      if (!Number.isFinite(score)) throw new Error('Non-finite context score');
      heads[name] = { activeIndices: active, score, prediction: head.labels[score > 0 ? 'positive' : 'negative'] };
    }
    return { normalized: normalize(text), features: emitted, heads };
  }
}

return { SmsSemanticsModel: SmsCompletionContextModel, sourceSha256: {"src/typescript/Preprocessing.ts":"da78f44e489aec464635e8b7e3707f1f6dc6446e024f1a20bf12c5d4dab69a54","src/typescript/research/SmsSemantics.ts":"a9509ca002cb11954039ed584789ec39affb64f561177d6f85bd82ac73e43a41","src/typescript/research/SmsCompletionContext.ts":"62f7afaefece1d7842f303f7327264a4ad492c38d2ed2ad08699d00eed4acf07","config/contracts/sms_semantics_model.json":"2e8355c1ea059f0139bd563f2fe9b5ed5181e49b87fe10be9715d702ed4251b8","config/contracts/sms_completion_context.json":"5011125f43d5aa8787198b353ac6d82fe68c7d8c79b39c24ac8aa4b7bc6a16c3"} };
})();
