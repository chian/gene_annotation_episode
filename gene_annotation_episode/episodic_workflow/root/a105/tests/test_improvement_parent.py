"""Annotation's actual outgoing/returned exchange with its improvement child."""
import pytest
from . import implicit_parent_checks as original
from . import improvement_parent_checks as check


@pytest.fixture(autouse=True)
def no_external_execution(monkeypatch):
    monkeypatch.setattr('subprocess.Popen', original.forbidden)
    monkeypatch.setattr('socket.socket.connect', original.forbidden)
    monkeypatch.setattr('socket.socket.connect_ex', original.forbidden)


@pytest.mark.parametrize('parent_kind', ('annotation',))
@pytest.mark.parametrize('scenario', ('valid-return', 'invalid-return', 'saved-return'))
def test_actual_conditional_child_preserves_semantic_validation_and_return_custody(tmp_path, parent_kind, scenario):
    observed = check.paired_connected(tmp_path, parent_kind, scenario)
    assert len(observed['attempts']) == 1
    events = observed['events']
    assert events.index(('resolver', 'improvement')) < events.index(('validate_report', original.INITIAL)) < events.index('build')
    if scenario == 'invalid-return':
        assert observed['failure'] is not None and observed['last_outcome_index'] == 7
        assert observed['action']['credit'] == 0.375 and observed['action']['result'] is not None
    else:
        assert observed['failure'] is None and observed['result'] == original.INITIAL
