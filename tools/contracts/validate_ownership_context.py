"""Validate the separate wrapper response without widening the canonical assessment."""
from src.python.ownership_context import CONTRACT, context_error
from tools.contracts.validate_transaction_behavior import require, validate_result


def validate_request(request):
    error = context_error(request)
    require(error is None, error)


def validate_response(response):
    require(isinstance(response, dict) and set(response) == set(CONTRACT["responseFields"]),
            "ownership response fields do not match the contract")
    require(response["ownershipContractVersion"] == CONTRACT["contractVersion"], "unsupported ownership version")
    status = response["contextStatus"]
    require(isinstance(status, str) and status in CONTRACT["diagnostics"], "unknown context status")
    require(response["contextReason"] in CONTRACT["diagnostics"][status], "invalid context status/reason pair")
    validate_result(response["assessment"])
