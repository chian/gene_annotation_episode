"""Six substantive return owners, original recursive traversal and fallback."""
import pytest
from .resource_return_checks import check_receivers, check_receiver_native_namespace


@pytest.mark.parametrize('mode', ('value', 'error', 'missing', 'custom'))
def test_original_resource_handoff_receivers(mode):
    check_receivers(mode)


def test_resource_receiver_native_namespace_and_inert_selection():
    check_receiver_native_namespace()
