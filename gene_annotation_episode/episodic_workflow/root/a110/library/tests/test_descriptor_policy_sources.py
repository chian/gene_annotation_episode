import pytest
from .descriptor_source_checks import check_descriptor_source_sensitivity


@pytest.mark.parametrize('complete', [False, True], ids=['minimal', 'complete'])
def test_descriptor_policy_source_sensitivity(tmp_path, complete):
    check_descriptor_source_sensitivity(tmp_path, complete)
