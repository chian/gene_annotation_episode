"""Current descriptors and strict rejection through actual private constructors.

One actual Store per module. No action, provider request or native job executes.
The observation artifact retains every original failure before assertions run.
"""
import json
import pytest

from .saved_binding_boundaries import BINDINGS, PREFIX
from .saved_binding_controls import CASES, diagnose_with_controls


@pytest.fixture(scope='module')
def observations(tmp_path_factory):
    root = tmp_path_factory.mktemp('a104-saved-binding-restoration')
    rows = []
    def retain(row):
        rows.append(row)
        (root / 'observations.json').write_text(json.dumps(rows, indent=2, sort_keys=True) + '\n')
    diagnose_with_controls(root / 'fixture', retain)
    by_id = {row['boundary']: row for row in rows}
    expected = {prefix + home for home, _, _ in BINDINGS
                for prefix in ('actual_constructor:', 'saved_descriptor:')}
    expected |= {'control:' + home + ':' + case for home, _, case in CASES}
    assert len(by_id) == len(rows) and set(by_id) == expected
    return by_id


@pytest.mark.parametrize('home,kind,class_name', BINDINGS, ids=[row[0] for row in BINDINGS])
def test_actual_private_saved_descriptor(observations, home, kind, class_name):
    constructor = observations['actual_constructor:' + home]
    assert constructor['status'] == 'returned', constructor
    row = observations['saved_descriptor:' + home]
    assert row['status'] == 'returned', row
    actual = row['value']
    assert actual['same_descriptor'] and actual['original'] == actual['restored']
    assert actual['same_class'] and actual['original_type'] == actual['restored_type']
    assert all(actual['projector_identity'].values())
    assert actual['definitions'] == actual['original_definitions']
    assert actual['capabilities'] == actual['expected_capabilities']
    assert actual['actual_backend_identity'] and actual['actual_store_identity']
    assert actual['actual_run_id'] == 'a104-saved-binding-observations'
    assert actual['provider_calls'] == constructor['value']['provider_calls'] == []
    if kind == 'literature':
        assert actual['original_settings'] == actual['restored_settings'] == constructor['value']['settings']


@pytest.mark.parametrize('home,kind,case', CASES, ids=[home + ':' + case for home, _, case in CASES])
def test_original_saved_descriptor_admission(observations, home, kind, case):
    row = observations['control:' + home + ':' + case]
    assert row['status'] == 'raised', row
    assert row['error']['type'] == PREFIX + 'method_loop.durable.DurableExecutionError'
    assert row['error']['failure'] == row['expected_failure'], row
