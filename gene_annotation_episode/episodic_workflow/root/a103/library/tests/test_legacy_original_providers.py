"""A103's already-private legacy guards remain part of the current request."""
import pytest
from . import provider_checks as checks


@pytest.mark.parametrize('role', ['annotation', 'improvement'])
def test_legacy_request_keeps_original_goal_record_request_provider_order(role):
    checks.check_legacy_request(role)
