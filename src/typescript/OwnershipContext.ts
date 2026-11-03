/** Message-bound human confirmation. Caller authenticity and storage stay outside the engine. */
import contract from '../../config/contracts/ownership_context.json' with { type: 'json' };
import type { DetailedInput, DetailedResult, OwnershipOverride } from './DetailedAssessment.ts';

export interface OwnershipRequest {
  ownerScopeId: string; messageId: string; message: DetailedInput;
  ownershipContext?: { schemaVersion: '1.0.0'; ownerScopeId: string; messageId: string;
    text: string; evidence: 'user_confirmed'; relationship: 'own_accounts' | 'other_person' | 'unknown' } | null;
}
export interface OwnershipResponse {
  ownershipContractVersion: '1.0.0'; assessment: DetailedResult;
  contextStatus: 'absent' | 'applied' | 'unresolved' | 'not_applicable' | 'invalid' | 'conflict';
  contextReason: string;
}
const blankIdentifier = new RegExp(contract.blankIdentifierPattern);
function identifier(value: unknown): boolean { return typeof value === 'string' && !blankIdentifier.test(value); }
function hasOwn(value: object, key: string): boolean { return Object.prototype.hasOwnProperty.call(value, key); }
function fields(value: any, required: string[], optional: string[] = []): boolean {
  return value !== null && typeof value === 'object' && !Array.isArray(value) &&
    required.every(key => hasOwn(value, key)) && Object.keys(value).every(key => required.includes(key) || optional.includes(key));
}
function contextError(request: any): string | null {
  if (!fields(request, contract.requestRequired, contract.requestOptional)) return 'invalid_request';
  const message = request.message;
  if (!identifier(request.ownerScopeId) || !identifier(request.messageId) ||
      !fields(message, contract.messageRequired, contract.messageOptional)) return 'invalid_request';
  if (typeof message.text !== 'string') return 'invalid_request';
  if (['sender', 'receivedAt'].some(key => hasOwn(message, key) && message[key] !== null && typeof message[key] !== 'string')) return 'invalid_request';
  if (hasOwn(message, 'isContact') && typeof message.isContact !== 'boolean') return 'invalid_request';
  const context = request.ownershipContext;
  if (context === null || context === undefined) return null;
  if (!fields(context, contract.contextFields) || !contract.contextFields.every(key => typeof context[key] === 'string')) return 'invalid_context';
  if (!identifier(context.ownerScopeId) || !identifier(context.messageId) || !contract.relationships.includes(context.relationship)) return 'invalid_context';
  if (context.schemaVersion !== contract.contractVersion) return 'unsupported_version';
  if (context.evidence !== 'user_confirmed') return 'untrusted_evidence';
  if (context.ownerScopeId !== request.ownerScopeId) return 'owner_mismatch';
  if (context.messageId !== request.messageId || context.text !== message.text) return 'message_mismatch';
  return null;
}
export function assessWithOwnership(request: unknown,
  evaluate: (input: DetailedInput, override?: OwnershipOverride) => DetailedResult): OwnershipResponse {
  const value = request as OwnershipRequest;
  const message = value?.message;
  const error = contextError(value);
  let assessment = evaluate(message);
  const transfer = contract.relationships.includes(assessment.transferRelationship);
  let contextStatus: OwnershipResponse['contextStatus'] = 'absent', contextReason = 'not_provided';
  let override: OwnershipOverride | undefined;
  if (error) {
    contextStatus = 'invalid'; contextReason = error;
    if (transfer) override = { relationship: 'unknown', uncertainDirection: false };
  } else if (value.ownershipContext !== null && value.ownershipContext !== undefined) {
    const relationship = value.ownershipContext.relationship, bodyRelation = assessment.transferRelationship;
    if (assessment.transactionStatus === 'non_transaction') {
      contextStatus = 'not_applicable'; contextReason = 'non_transaction';
    } else if (!transfer) {
      contextStatus = 'not_applicable'; contextReason = 'not_a_transfer';
    } else if (relationship === 'unknown') {
      contextStatus = 'unresolved'; contextReason = 'confirmation_unknown';
    } else if (bodyRelation !== 'unknown' && bodyRelation !== relationship) {
      contextStatus = 'conflict'; contextReason = 'text_context_conflict';
      override = { relationship: 'unknown', uncertainDirection: true };
    } else {
      contextStatus = 'applied'; contextReason = 'confirmed_relationship';
      override = { relationship, uncertainDirection: false };
    }
  }
  if (override) assessment = evaluate(message, override);
  return { ownershipContractVersion: '1.0.0', assessment, contextStatus, contextReason };
}
