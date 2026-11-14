"""Actual local Store evidence for source failures and pending parent inputs.

No provider, workflow, child, scientific calculation or continuation controller.
"""
from copy import deepcopy
import json
from types import MappingProxyType

import pytest

from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.episode_source_failure import (
    child_completion_status, record_source_failure,
)
from gene_annotation_episode.episodic_workflow.root.pending_assignment import original_assignment


@pytest.mark.parametrize('diagnostic,retained', [
    ({'cause_code': 'input_too_large', 'input_chars': 12, 'provider_max_chars': 10,
      'private_context': 'secret'}, {'cause_code': 'input_too_large', 'input_chars': 12,
                                    'provider_max_chars': 10}),
    ({'cause_code': 'input_too_large', 'input_chars': True, 'provider_max_chars': -1},
     {'cause_code': 'input_too_large'}),
    ({'cause_code': 'provider_output_incomplete', 'input_chars': 12, 'raw': 'secret'},
     {'cause_code': 'provider_output_incomplete'}),
    ({'cause_code': 'untrusted', 'input_chars': 12, 'raw': 'secret'},
     {'cause_code': 'model_call_failed'}),
])
def test_failure_persists_only_controlled_metadata(tmp_path, diagnostic, retained):
    error = RuntimeError('private transport message secret')
    error.diagnostic = diagnostic
    with Store(tmp_path / 'failure-store') as store:
        before_records = store.db.execute('SELECT count(*) FROM records').fetchone()[0]
        failure = record_source_failure(store, 'run', 'child', 3, error)
        expected = {'category': 'decision_source', 'exception_type': 'RuntimeError', **retained}
        assert failure == expected
        row = store.db.execute('SELECT failure FROM runtime_source_failures').fetchone()
        assert json.loads(row[0]) == expected
        assert 'secret' not in row[0]
        assert store.db.execute('SELECT count(*) FROM records').fetchone()[0] == before_records


def test_failure_same_original_action_keeps_first_saved_record(tmp_path):
    with Store(tmp_path / 'failure-store') as store:
        first = record_source_failure(store, 'run', 'child', 3, RuntimeError('first'))
        second = record_source_failure(store, 'run', 'child', 3, ValueError('second'),
                                       cause_code='different_attempt')
        # INSERT OR IGNORE retains the original action's record. The function's
        # return describes the supplied call, not an invented rewrite of history.
        assert first != second
        rows = list(store.db.execute('SELECT failure FROM runtime_source_failures'))
        assert len(rows) == 1 and json.loads(rows[0][0]) == first


def test_child_status_selects_latest_failure_of_exact_run_and_child(tmp_path):
    with Store(tmp_path / 'failure-store') as store:
        completion = {'ended_by': 'source_failed', 'end_reason': 'source_failed'}
        fallback = child_completion_status(store, 'run', 'child', completion, delivery='pending')
        assert fallback['failure'] == {'category': 'decision_source', 'cause_code': 'source_failed'}
        record_source_failure(store, 'run', 'child', 1, RuntimeError(), cause_code='earlier')
        latest = record_source_failure(store, 'run', 'child', 2, RuntimeError(), cause_code='latest')
        record_source_failure(store, 'other-run', 'child', 99, RuntimeError(), cause_code='wrong-run')
        record_source_failure(store, 'run', 'other-child', 99, RuntimeError(), cause_code='wrong-child')
        status = child_completion_status(store, 'run', 'child', completion, delivery='delivered')
        assert status == {**completion, 'result_status': 'partial',
                          'report_delivery': 'delivered', 'failure': latest}
        normal = child_completion_status(store, 'run', 'child',
            {'ended_by': 'source_exhausted', 'end_reason': 'completed'}, delivery='delivered')
        assert normal['result_status'] == 'returned' and normal['failure'] is None


def test_handoff_failure_retains_controlled_recovery_without_private_exception_text(tmp_path):
    with Store(tmp_path / 'failure-store') as store:
        failure = record_source_failure(store, 'run', 'parent', 0,
            ValueError('original_handoff_not_received_by_this_parent'))
        assert failure['code'] == 'original_handoff_not_received_by_this_parent'
        assert 'does not authorize replacement work' in failure['recovery']
        assert failure['exception_type'] == 'ValueError'


def test_pending_assignment_detaches_original_context_constraints_and_evidence():
    assignment = {'context': {'investigation_focus': {'task': 'compare', 'focus': ['a', 'b']},
                              'nested': {'values': [1, 2]}},
                  'constraints': {'source_only': True}, 'evidence_refs': ['source_original'],
                  'private_child_state': {'not_parent_inputs': True}}
    request = {'goal': {'objective': 'Retain original task'},
               'message': {'scope': {'subject_refs': ['subject_original']},
                           'episode_assignment': assignment}}
    before = deepcopy(request)
    retained = original_assignment(MappingProxyType(request), 7)
    assert retained == {'objective': 'Retain original task',
        'scope': {'subject_refs': ['subject_original']}, 'decision_index': 7,
        'context': assignment['context'], 'constraints': assignment['constraints'],
        'evidence_refs': assignment['evidence_refs'],
        'investigation_focus': assignment['context']['investigation_focus']}
    assert 'private_child_state' not in retained
    retained['context']['nested']['values'].append(3)
    retained['investigation_focus']['focus'].append('c')
    retained['evidence_refs'].append('source_other')
    assert request == before


def test_pending_assignment_none_and_absent_optional_fields_remain_absent():
    assert original_assignment(None, 0) is None
    assert original_assignment({'goal': {'objective': 'same'}, 'message': {'scope': {}}}, 0) == {
        'objective': 'same', 'scope': {}, 'decision_index': 0}
