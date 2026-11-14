"""Only the changed A102 commissioning policy boundaries, without child work."""
import pytest
from .commissioning_checks import paired


@pytest.mark.parametrize('scenario', (
    'wait', 'receipt', 'declarations', 'declaration_none', 'late_filter',
    'fresh_arm', 'replay_arm', 'wrong_arm', 'catalog_none', 'catalog_wait',
    'execute_rejection', 'execute_lookup', 'selected_fresh', 'selected_replay', 'return_form'))
def test_original_commissioning_boundaries(tmp_path, scenario):
    paired(tmp_path, scenario)
