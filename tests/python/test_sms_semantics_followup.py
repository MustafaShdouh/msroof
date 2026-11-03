"""Historical safeguards use their frozen inputs while live recording rules evolve."""
from tests.python.frozen_sms_tests import frozen_test_class

SmsSemanticsFollowupTests = frozen_test_class('sms_semantics_followup_v1', __name__, 'SmsSemanticsFollowupTests')
