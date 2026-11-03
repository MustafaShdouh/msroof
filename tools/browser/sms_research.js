// Optional research view. No correction state, storage, model fitting or network.
var smsResearchCandidate = null;
var smsResearchCandidateKind = null;

function changeSmsResearchModel() {
  smsResearchCandidate = null;
  smsResearchCandidateKind = null;
  resetSmsResearch('Open to compare');
  toggleSmsResearch();
}

function resetSmsResearch(title) {
  document.getElementById('smsResearchTransaction').innerText = title;
  ['smsResearchDirection', 'smsResearchAmount', 'smsResearchTracking'].forEach(function(id) {
    document.getElementById(id).innerText = '—';
  });
  document.getElementById('smsResearchOutput').innerText = '{}';
}

function renderSmsResearch(text, assessment) {
  if (!document.getElementById('smsResearchPanel').open) {
    resetSmsResearch('Open to compare');
    return;
  }
  if (!text.trim()) {
    resetSmsResearch('Add a message to compare');
    return;
  }
  try {
    var kind = document.getElementById('smsResearchModelSelect').value === 'context' ? 'context' : 'word';
    var selectedModel = kind === 'context' ? SMS_CONTEXT_MODEL : SMS_RESEARCH_MODEL;
    if (!smsResearchCandidate || smsResearchCandidateKind !== kind) {
      var Runtime = kind === 'context' ? SmsCompletionContextResearch : SmsSemanticsResearch;
      smsResearchCandidate = new Runtime.SmsSemanticsModel(selectedModel);
      smsResearchCandidateKind = kind;
    }
    var prediction = smsResearchCandidate.predict(text).heads;
    var completed = prediction.completion.prediction === 'completed';
    document.getElementById('smsResearchTransaction').innerText = completed ? 'Predicted transaction' : 'Predicted non-transaction';
    document.getElementById('smsResearchDirection').innerText = completed ?
      (prediction.direction.prediction === 'incoming' ? 'Incoming' : 'Outgoing') : 'Not applicable';
    var decisions = { include: 'Include', exclude: 'Exclude', review: 'Review required' };
    document.getElementById('smsResearchAmount').innerText = assessment.amount === null ? 'No amount resolved' :
      assessment.amount + ' ' + assessment.currency + (assessment.currencyResolution.indexOf('default_') === 0 ? ' (default currency)' : '');
    document.getElementById('smsResearchTracking').innerText = decisions[assessment.trackingDecision];
    document.getElementById('smsResearchOutput').innerText = JSON.stringify({
      candidate: selectedModel.metadata.runId,
      completion: { prediction: prediction.completion.prediction, score: prediction.completion.score },
      direction: completed ? { prediction: prediction.direction.prediction, score: prediction.direction.score } : null,
      existingMessageOnlyAssessment: assessment,
      note: 'Model heads do not establish account ownership or recording eligibility. Scores are not certainty.'
    }, null, 2);
  } catch (error) {
    resetSmsResearch('Comparison unavailable');
    document.getElementById('smsResearchOutput').innerText = JSON.stringify({ error: String(error.message || error) }, null, 2);
  }
}

function toggleSmsResearch() {
  if (!testerStartup.ready) { resetSmsResearch('Engine not ready'); return; }
  var text = document.getElementById('bodyInput').value;
  var active = document.getElementById('smsResearchPanel').open && text.trim();
  var assessment = active ? analyzeDetailed({ text: text, sender: document.getElementById('senderInput').value,
    isContact: document.getElementById('isContactInput').checked }) : null;
  renderSmsResearch(text, assessment);
}
