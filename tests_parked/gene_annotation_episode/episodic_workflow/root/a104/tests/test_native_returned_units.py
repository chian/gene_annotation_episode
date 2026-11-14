"""168 controlled returns plus42 real native admission outcomes/exceptions."""
import json
import os
import socket
import subprocess
import pytest
from .native_result_owner_controls import FAMILIES, HOMES
from .native_returned_units import returned_unit

PHASE = os.environ['A104_NATIVE_RESULT_OWNER_PHASE']
assert PHASE in {'baseline', 'connected'}


@pytest.mark.parametrize('home', HOMES)
@pytest.mark.parametrize('family', FAMILIES, ids=lambda value: value[0])
@pytest.mark.parametrize('status', ('completed', 'invalid', 'failed', 'unavailable'))
def test_acquired_native_family_return_enters_actual_iterator(tmp_path, monkeypatch, home, family, status):
    def forbidden(*args, **kwargs):
        raise AssertionError('native returned-unit test attempted external execution')
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    result = returned_unit(tmp_path, home, family, status, PHASE)
    assert result['single_return_and_observation'] is True
    assert result['saved_action_replayed_without_execution'] is True
    assert result['native_producer_or_seven_family_admission_claimed'] is False


@pytest.mark.parametrize('home', HOMES)
@pytest.mark.parametrize('family', FAMILIES, ids=lambda value: value[0])
def test_actual_native_admission_return_or_exception_keeps_iterator_boundary(tmp_path, monkeypatch,
        record_property, home, family):
    def forbidden(*args, **kwargs):
        raise AssertionError('native admission unit control attempted external execution')
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    result = returned_unit(tmp_path, home, family, 'invalid', PHASE, actual_native_admission=True)
    assert result['actual_native_admission'] is True
    assert result['native_producer_or_seven_family_admission_claimed'] is False
    record_property('actual_native_admission_boundary', json.dumps(result, sort_keys=True))
