// One local tester profile; confirmations live only in this page's memory.
var ownershipState = { text: null, sender: null, isContact: null, serial: 0, context: null, fresh: false };

function syncOwnershipMessage(sender, text, isContact) {
  if (ownershipState.fresh || ownershipState.text !== text || ownershipState.sender !== sender || ownershipState.isContact !== isContact) {
    ownershipState.serial += 1;
    ownershipState.text = text;
    ownershipState.sender = sender;
    ownershipState.isContact = isContact;
    ownershipState.context = null;
    ownershipState.fresh = false;
  }
}

function ownershipRequest() {
  return {
    ownerScopeId: 'tester-local-profile',
    messageId: 'tester-message-' + ownershipState.serial,
    message: { text: ownershipState.text, sender: ownershipState.sender, isContact: ownershipState.isContact },
    ownershipContext: ownershipState.context
  };
}

function confirmOwnership(relationship) {
  if (!testerStartup.ready) { renderTesterNotReady(); return; }
  // A button click is the only path that constructs a human confirmation.
  if (['own_accounts', 'other_person', 'unknown'].indexOf(relationship) < 0) return;
  var sender = document.getElementById('senderInput').value;
  var text = document.getElementById('bodyInput').value;
  var isContact = document.getElementById('isContactInput').checked;
  syncOwnershipMessage(sender, text, isContact);
  if (!text.trim()) return;
  var request = ownershipRequest();
  ownershipState.context = {
    schemaVersion: '1.0.0', ownerScopeId: request.ownerScopeId,
    messageId: request.messageId, text: text,
    evidence: 'user_confirmed', relationship: relationship
  };
  runAnalysis();
}

function clearOwnershipConfirmation() {
  ownershipState.context = null;
  runAnalysis();
}

function startNewOwnershipMessage() {
  ownershipState.fresh = true;
  runAnalysis();
}

function renderOwnership(sender, text, isContact) {
  if (!testerStartup.ready) { renderTesterNotReady(); return; }
  syncOwnershipMessage(sender, text, isContact);
  var chosen = ownershipState.context && ownershipState.context.relationship;
  [['ownershipOwn', 'own_accounts'], ['ownershipOther', 'other_person'], ['ownershipUnknown', 'unknown']].forEach(function(pair) {
    var button = document.getElementById(pair[0]);
    button.disabled = !text.trim();
    button.ariaPressed = String(chosen === pair[1]);
    button.className = chosen === pair[1] ? 'is-selected' : '';
  });
  document.getElementById('ownershipClear').disabled = !ownershipState.context;
  var summary = document.getElementById('ownershipSummary');
  var status = document.getElementById('ownershipStatus');
  if (!text.trim()) {
    summary.innerText = 'Add a message to try a confirmation.';
    status.innerText = 'No confirmation';
    document.getElementById('ownershipOutput').innerText = '{}';
    return;
  }
  var response = MasroofRuntime.MasroofEngine.analyzeWithOwnership(ownershipRequest());
  var result = response.assessment;
  var decisions = { include: 'Include', exclude: 'Exclude', review: 'Review required' };
  var directions = { incoming: 'Incoming', outgoing: 'Outgoing', uncertain: 'Direction unresolved', not_applicable: 'Direction not applicable' };
  summary.innerText = decisions[result.trackingDecision] + ' · ' + directions[result.direction] +
    (result.amount !== null ? ' · ' + result.amount + ' ' + result.currency : '') +
    (result.expenseCategory ? ' · ' + result.expenseCategory : '');
  summary.style.color = result.trackingDecision === 'review' ? '#846434' :
    (result.trackingDecision === 'include' ? '#35634c' : '#68716a');
  var statuses = {
    absent: 'No confirmation. Showing the message-only assessment.',
    applied: chosen === 'own_accounts' ? 'Your confirmation: my own accounts.' : 'Your confirmation: another person.',
    unresolved: 'You are not sure. The message-only assessment is preserved.',
    conflict: 'Your confirmation conflicts with the message. Review is required.',
    invalid: 'This confirmation does not match the current message. Clear it and review again.',
    not_applicable: response.contextReason === 'non_transaction' ? 'This message is not a transaction. Ownership does not change that.' :
      'This message is not a recognized transfer. Ownership does not change its assessment.'
  };
  status.innerText = statuses[response.contextStatus];
  document.getElementById('ownershipOutput').innerText = JSON.stringify(response, null, 2);
}
