// Display only: the canonical engine owns decisions, defaults and ownership.
function renderPrimaryAssessment(result, latency) {
  var badge = document.getElementById('detailedDecision');
  var decision = result && result.trackingDecision;
  badge.innerText = { include: 'Include', exclude: 'Exclude', review: 'Review required' }[decision] || 'Ready';
  badge.style.color = decision === 'review' ? '#846434' : decision === 'include' ? '#35634c' : '#68716a';
  badge.style.backgroundColor = decision === 'review' ? '#f5efe3' : decision === 'include' ? '#edf1e9' : '#f3f5f1';
  var fields = {
    primaryStatus: '—', primaryAmount: '—', primaryCurrency: '—', primaryDirection: '—',
    primaryOwnership: '—', primaryReasons: 'Add a message to analyze.', primaryLatency: '—'
  };
  if (result) {
    fields.primaryStatus = { completed: 'Completed movement', non_transaction: 'No completed transaction', uncertain: 'Completion uncertain' }[result.transactionStatus];
    fields.primaryAmount = result.amount === null ? (result.transactionStatus === 'non_transaction' ? 'Not applicable' : 'Unresolved') : String(result.amount);
    var resolution = {
      explicit: 'explicit in message', default_missing: 'default (currency missing)',
      default_ambiguous: 'default (currency ambiguous)', not_applicable: 'Not applicable'
    }[result.currencyResolution];
    fields.primaryCurrency = result.currency ? result.currency + ' · ' + resolution : resolution;
    fields.primaryDirection = { incoming: 'Incoming', outgoing: 'Outgoing', uncertain: 'Direction unresolved', not_applicable: 'Not applicable' }[result.direction];
    fields.primaryOwnership = { not_transfer: 'Not a transfer', own_accounts: 'My own accounts', other_person: 'Another person', unknown: 'Ownership unresolved', not_applicable: 'Not applicable' }[result.transferRelationship];
    var reasons = {
      completed_transaction: 'Completed transaction evidence.', completion_unresolved: 'Completion is not established.',
      amount_unresolved: 'No single transaction amount is resolved.', direction_unresolved: 'Money-flow direction is unresolved.',
      transfer_ownership_unresolved: 'The other account owner is unknown.', own_account_transfer: 'Transfers between your own accounts are excluded.',
      category_unresolved: 'Optional expense category is unresolved.', personal_conversation: 'Personal conversation or a request.',
      otp_or_authorization: 'OTP or authorization request.', declined_or_failed: 'Declined or failed movement.',
      pending_or_requested: 'Pending, requested or conditional movement.', promotion_or_administration: 'Promotion, administration or noncash notice.',
      balance_only: 'Balance information only.', empty_or_malformed: 'Empty or malformed message.'
    };
    fields.primaryReasons = result.reasonCodes.map(function(code) { return reasons[code] || code.replace(/_/g, ' '); }).join('\n');
    fields.primaryLatency = latency.toFixed(3) + ' ms';
  }
  Object.keys(fields).forEach(function(id) { document.getElementById(id).innerText = fields[id]; });
  document.getElementById('detailedOutput').innerText = JSON.stringify(result || {}, null, 2);
}

function renderLegacyComparison(analysis, error) {
  ['confidenceVal', 'fieldCategory', 'fieldDirection', 'fieldAmount', 'fieldOrigAmount',
    'fieldRate', 'fieldParty', 'fieldAccount', 'fieldBalance', 'latencyBadge'].forEach(function(id) {
    document.getElementById(id).innerText = '--';
  });
  var title = document.getElementById('decisionTitle');
  title.innerText = error ? 'Legacy comparison unavailable' : 'Ready (Type text or click preset)';
  title.style.color = '#626b65';
  document.getElementById('jsonOutput').innerText = JSON.stringify(error ? { error: error } : {}, null, 2);
  if (!analysis) return;
  var result = analysis.result;
  document.getElementById('latencyBadge').innerText = analysis.latency.toFixed(3) + ' ms';
  document.getElementById('confidenceVal').innerText = result.confidence;
  title.innerText = result.isValidTransaction ? 'VALID TRANSACTION' : 'REJECTED (' + (result.reason || 'Invalid') + ')';
  title.style.color = result.isValidTransaction ? '#35634c' : '#984b47';
  if (result.isValidTransaction) {
    var d = result.data;
    document.getElementById('fieldCategory').innerText = d.category ? (d.category + ' (' + Math.round(d.categoryConfidence * 100) + '%)') : '--';
    document.getElementById('fieldDirection').innerText = d.type + ' (' + d.direction + ')';
    document.getElementById('fieldAmount').innerText = d.amount + ' ' + d.currency;
    document.getElementById('fieldOrigAmount').innerText = d.originalAmount && d.originalCurrency ? d.originalAmount + ' ' + d.originalCurrency : 'None (Single Currency)';
    document.getElementById('fieldRate').innerText = d.exchangeRate ? '1 ' + d.originalCurrency + ' = ' + d.exchangeRate + ' ' + d.currency : 'None';
    document.getElementById('fieldParty').innerText = d.merchantOrParty || 'None';
    document.getElementById('fieldAccount').innerText = d.accountMask || 'None';
    document.getElementById('fieldBalance').innerText = d.balance !== null ? d.balance + ' ' + d.currency : 'None';
  }
  document.getElementById('jsonOutput').innerText = JSON.stringify(result, null, 2);
}
