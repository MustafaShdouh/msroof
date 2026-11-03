"""Historical safeguards use their frozen inputs while live recording rules evolve."""
from tests.python.frozen_sms_tests import frozen_test_class

SmsSemanticsModelTests = frozen_test_class('sms_semantics_ab_v1', __name__, 'SmsSemanticsModelTests')
