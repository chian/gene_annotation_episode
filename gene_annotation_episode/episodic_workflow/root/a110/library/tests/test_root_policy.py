"""Root-only policy preservation and actual cold owner entry."""
import pytest
from .root_policy_checks import (BOUNDARIES, cold_owner_entry, original,
    paired_root, paired_schema_filter)


@pytest.fixture(autouse=True)
def no_external_execution(monkeypatch, request):
    if request.node.originalname != 'test_cold_root_policy_owner_entry':
        monkeypatch.setattr('subprocess.Popen', original.forbidden)
    monkeypatch.setattr('socket.socket.connect', original.forbidden)
    monkeypatch.setattr('socket.socket.connect_ex', original.forbidden)


@pytest.mark.parametrize('boundary', BOUNDARIES)
def test_original_current_root_policy(tmp_path, boundary):
    paired_root(tmp_path, boundary)


@pytest.mark.parametrize('role', ['annotation', 'improvement', 'scientific_process'])
def test_all_actual_schema_owners_share_late_root_filter(tmp_path, role):
    paired_schema_filter(tmp_path, role)


def test_cold_root_policy_owner_entry(tmp_path):
    cold_owner_entry(tmp_path / 'cold')
