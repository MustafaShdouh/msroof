// This file provides UI only; scoring is bundled directly from MerchantCategory.ts.
const merchantLabModels = testerStartup.ready ? Object.fromEntries(Object.entries(MERCHANT_LAB_DATA.models)
  .map(([key, model]) => [key, MerchantResearch.loadMerchantCategoryModel(model)])) : {};

function activeMerchantVariant() {
  return document.getElementById('merchantVariant').value;
}
function merchantLabPrediction(name) {
  return MerchantResearch.predictMerchantCategory(merchantLabModels[activeMerchantVariant()], name);
}
function merchantLabText(name) {
  if (!testerStartup.ready) return 'Engine not ready. No research prediction.';
  if (!name.trim()) return 'Enter a shop or service name to test.';
  const prediction = merchantLabPrediction(name);
  const model = merchantLabModels[activeMerchantVariant()].model;
  const reasons = {
    no_features: 'No usable name text.', insufficient_feature_evidence: 'Too little familiar text.',
    insufficient_class_support: 'Too few training businesses in this category.',
    low_model_score: 'Model score is below the acceptance threshold.', small_margin: 'Leading categories are too close.'
  };
  const ranked = prediction.scores.map((score, index) => ({score, category: model.classes[index]}))
    .sort((a, b) => b.score - a.score);
  return 'Name: ' + name + '\n' + (prediction.category ? 'Category: ' + prediction.category :
    'Uncertain — no category accepted. ' + reasons[prediction.reason]) +
    '\nTop suggestions (uncalibrated scores):\n' + ranked.slice(0, 3)
      .map(item => item.category + ': ' + item.score.toFixed(3)).join('\n');
}
function runMerchantLab() {
  if (!testerStartup.ready) {
    document.getElementById('merchantNameResult').textContent = 'Engine not ready. No research prediction.';
    updateMerchantSms(null);
    return;
  }
  const summary = MERCHANT_LAB_DATA.summary[activeMerchantVariant()];
  const human = summary.human, combined = summary.combined;
  document.getElementById('merchantMetrics').textContent =
    'Training: ' + summary.businessCount + ' distinct businesses, ' + summary.viewCount + ' name forms. ' +
    'Human validation: ' + human.correctAnswered + ' correct, ' + human.wrongAnswered + ' wrong, ' + human.abstained +
    ' uncertain out of ' + human.businessCount + '. Mixed human/assistant validation: ' +
    combined.correctAnswered + ' correct, ' + combined.wrongAnswered + ' wrong, ' + combined.abstained +
    ' uncertain out of ' + combined.businessCount + '. The human sample is very small.';
  document.getElementById('merchantNameResult').textContent = merchantLabText(document.getElementById('merchantNameInput').value);
}
function setMerchantExample(name) {
  document.getElementById('merchantNameInput').value = name;
  runMerchantLab();
}
function updateMerchantSms(result) {
  if (!testerStartup.ready) {
    document.getElementById('merchantSmsResult').textContent = 'Engine not ready. No message assessment.';
    return;
  }
  const data = result && result.isValidTransaction && result.data;
  document.getElementById('merchantSmsResult').textContent = !data ? 'No accepted transaction to categorize.' :
    data.type !== 'EXPENSE' ? 'Incoming transaction — no expense category assigned.' :
    !data.merchantOrParty ? 'No merchant extracted. Enter the name manually below.' : merchantLabText(data.merchantOrParty);
}
document.addEventListener('DOMContentLoaded', function() {
  document.getElementById('merchantVariant').value = MERCHANT_LAB_DATA.selected;
  runMerchantLab();
  updateMerchantSms(null);
});
