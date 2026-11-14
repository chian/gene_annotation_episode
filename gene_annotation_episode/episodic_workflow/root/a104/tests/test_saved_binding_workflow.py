"""Actual restored Workflow and original cached action/credit custody.

Without external operands, pytest creates a current controlled archive. The
stage acceptance additionally supplies the authenticated pre-change archive;
same-code capture alone is never counted as historical compatibility.
"""
import hashlib
import json
import os
from pathlib import Path
import pytest

from .api_cases import HOMES
from .api_saved_carriers import capture_custody
from .saved_binding_workflow import capture, reopen

CASES = tuple((home, role) for home in HOMES for role in ('launch_api', 'launch', 'results'))


@pytest.fixture(scope='module')
def replay_observations(tmp_path_factory):
    root = tmp_path_factory.mktemp('a104-descriptor-workflow')
    captured = os.environ.get('A104_SAVED_BINDING_CAPTURE')
    expected = os.environ.get('A104_SAVED_BINDING_CAPTURE_CUSTODY')
    expected_sha = os.environ.get('A104_SAVED_BINDING_CAPTURE_CUSTODY_SHA256')
    if captured is None:
        assert expected is None and expected_sha is None
        captured = root / 'captured'
        capture(captured)
        custody = capture_custody(captured)
        historical_input = False
    else:
        assert expected is not None and expected_sha is not None
        captured = Path(captured).resolve()
        raw = Path(expected).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected_sha
        custody = json.loads(raw)
        assert capture_custody(captured) == custody
        historical_input = True
    rows = reopen(captured, root / 'reopened', authenticated_custody=custody)
    index = json.loads((Path(captured) / 'capture_index.json').read_text())
    mapping = {(entry['home'], entry['role']): row for entry, row in zip(index, rows, strict=True)}
    assert len(mapping) == len(rows) == len(CASES) and set(mapping) == set(CASES)
    (root / 'input_provenance.json').write_text(json.dumps({
        'actual_pre_change_capture_operand_supplied': historical_input,
        'custody': custody}, indent=2, sort_keys=True) + '\n')
    return mapping


@pytest.mark.parametrize('home,role', CASES, ids=[home + ':' + role for home, role in CASES])
def test_actual_workflow_saved_request_and_action(replay_observations, home, role):
    row = replay_observations[home, role]
    assert 'raised_boundary' not in row and 'close_failure' not in row, row
    assert row['copied_bytes_verified_before_constructor']
    assert row['original_capture_files_unchanged'] and row['rows_unchanged_after_reads']
    restored = row['descriptor_construction']
    assert restored['status'] == 'returned'
    assert all(restored['projector_identities'].values())
    assert restored['capabilities'] == restored['expected_capabilities']
    replay = row['cached_replay']
    assert replay['status'] == 'returned'
    assert replay['unfinished_queue_before'] == replay['unfinished_queue_after'] == [0]
    assert row['full_iterator_restoration_claimed'] is False
