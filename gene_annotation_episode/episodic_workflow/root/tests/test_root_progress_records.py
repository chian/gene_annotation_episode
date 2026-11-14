"""Original progress contracts and real saved completion boundaries.

Status values and signed credit are engineered records, not measured native work
or scientific scores. No model provider, native worker or continuation controller runs.
"""
import base64
from copy import deepcopy
import json

import pytest

# Direct import intentionally retains an unambiguous missing-owner baseline.
import gene_annotation_episode.episodic_workflow.root.progress_records as progress
from gene_annotation_episode.episodic_workflow.root import job_progress_status_schema as native_schema
from gene_annotation_episode.domain import ContractError, canonical, validate_schema
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.episodic_workflow.root.completion_evidence import (
    CompletionEvidence, validate_completion_evidence,
)
from gene_annotation_episode.episodic_workflow.root.episode_completion import CompletionLedger, observes_action_outcome
from gene_annotation_episode.episodic_workflow.root.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.method_loop.durable import DurableExecutionStore
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef, UnitRef
from gene_annotation_episode.episodic_workflow.root.progress_observations import ProgressProvider, read_progress
from gene_annotation_episode.episodic_workflow.root.task_values import Record

STAMP = '2026-11-11T00:00:00+00:00'
RUN = 'engineering-progress-records'
SCOPE = {'subject_refs': []}


def native_job(state='execution_unknown', outcome='unknown'):
    return {'job_ref': 'homology_job_fixture', 'registry_ref': 'execution_registry_fixture',
        'state': state, 'outcome': outcome, 'elapsed_seconds': None,
        'duration_measure': 'systemd_service_wall_seconds', 'native_returncode': None,
        'failure_code': None, 'resource': None,
        'progress_kind': 'native_execution_state_and_output_bytes_not_search_fraction',
        'outputs': [{'role': role, 'available': False, 'bytes': None, 'writer_closed': False}
                    for role in native_schema.OUTPUTS]}


def resource_observation(state='unknown'):
    return {'observed_at': STAMP, 'state': state, 'returncode': None, 'failure_code': None,
        'result_available': False, 'measurements': [], 'outputs': [], 'logs': [],
        'provenance_refs': [], 'native': {'condition': 'unavailable'}}


def resource_target():
    return {'handle': 'resource_fixture', 'resource_id': 'engineering-resource',
        'resource_kind': 'local', 'execution_id': 'engineering-execution',
        'request_sha256': 'a' * 64}


def test_exact_canonical_contract_owners_and_full_native_schema():
    assert progress.ContractError is ContractError
    assert progress.plain is plain
    assert progress.STATUS_SCHEMA is native_schema.STATUS_SCHEMA
    assert progress.JOB_STATUS_SCHEMA['properties']['native'] == native_schema.STATUS_SCHEMA
    assert progress.JOB_STATUS_SCHEMA['properties']['native'] is not native_schema.STATUS_SCHEMA
    assert set(native_schema.OUTPUTS) == {'native_text', 'native_stderr', 'hit_table', 'domain_table'}
    native = native_job()
    validate_schema(native, native_schema.STATUS_SCHEMA)
    with pytest.raises(ContractError):
        validate_schema({**native, 'search_fraction': 0.5}, native_schema.STATUS_SCHEMA)


@pytest.mark.parametrize('state,outcome,lifecycle', [
    ('not_submitted', 'pending', 'pending'), ('prepared', 'pending', 'pending'),
    ('starting', 'pending', 'executing'), ('running', 'pending', 'executing'),
    ('submission_unconfirmed', 'unknown', None), ('execution_unknown', 'unknown', None),
    ('returned', 'failed', 'returned'), ('returned', 'succeeded', 'returned'),
])
def test_job_status_retains_original_unknowns_and_lifecycle(state, outcome, lifecycle):
    native = native_job(state, outcome)
    saved = deepcopy(native)
    status = progress.job_status(native['job_ref'], native, observed_at=STAMP)
    assert native == saved and status['native'] == saved
    assert status['lifecycle_state'] == lifecycle
    assert status['result_available'] is False
    assert status['native']['elapsed_seconds'] is None
    assert status['native']['native_returncode'] is None
    assert status['native']['resource'] is None
    status['native']['outputs'][0]['bytes'] = 42
    assert native == saved


def test_returned_failed_job_retains_available_bytes_without_becoming_success():
    native = native_job('returned', 'failed')
    native.update(native_returncode=9, failure_code='native_nonzero_exit', elapsed_seconds=1.75)
    native['outputs'][0].update(available=True, bytes=3, writer_closed=True)
    status = progress.job_status(native['job_ref'], native, observed_at=STAMP)
    assert status['lifecycle_state'] == 'returned' and status['result_available'] is True
    assert status['native'] == native and status['native']['outcome'] == 'failed'
    assert status['native']['elapsed_seconds'] == 1.75
    assert status['native']['duration_measure'] == 'systemd_service_wall_seconds'
    assert status['native']['progress_kind'] == 'native_execution_state_and_output_bytes_not_search_fraction'


@pytest.mark.parametrize('defect,code', [
    ('handle', 'job_progress_status_relationship_mismatch'),
    ('lifecycle', 'job_progress_status_relationship_mismatch'),
    ('availability', 'job_progress_status_relationship_mismatch'),
    ('premature_outcome', 'job_progress_status_relationship_mismatch'),
    ('duplicate_output', 'job_progress_output_identity_conflict'),
    ('unavailable_bytes', 'job_progress_output_relationship_mismatch'),
    ('closed_while_running', 'job_progress_output_relationship_mismatch'),
    ('naive_timestamp', 'invalid_job_progress_status'),
])
def test_job_status_rejects_inconsistent_original_facts(defect, code):
    native = native_job('running', 'pending')
    value = progress.job_status(native['job_ref'], native, observed_at=STAMP)
    if defect == 'handle':
        value['handle'] = 'another_job'
    elif defect == 'lifecycle':
        value['lifecycle_state'] = 'returned'
    elif defect == 'availability':
        value['result_available'] = True
    elif defect == 'premature_outcome':
        value['native']['outcome'] = 'failed'
    elif defect == 'duplicate_output':
        value['native']['outputs'].append(deepcopy(value['native']['outputs'][0]))
    elif defect == 'unavailable_bytes':
        value['native']['outputs'][0]['bytes'] = 0
    elif defect == 'closed_while_running':
        value['native']['outputs'][0].update(available=True, bytes=0, writer_closed=True)
        value['result_available'] = True
    else:
        value['observed_at'] = '2026-11-11T00:00:00'
    before = deepcopy(value)
    with pytest.raises(ContractError, match=code) as caught:
        progress.validate_job_status(value)
    assert type(caught.value) is ContractError and value == before


@pytest.mark.parametrize('state,lifecycle', [
    ('submitted', 'pending'), ('running', 'executing'), ('completed', 'returned'),
    ('failed', 'returned'), ('unknown', None),
])
def test_resource_status_does_not_infer_a_result_from_terminal_state(state, lifecycle):
    observation = resource_observation(state)
    value = progress.resource_status(resource_target(), observation)
    assert value['lifecycle_state'] == lifecycle and value['result_available'] is False
    assert value['native'] == observation
    assert value['native']['measurements'] == []
    assert value['native']['returncode'] is None
    value['native']['native']['condition'] = 'changed-copy'
    assert observation['native']['condition'] == 'unavailable'


def logged_observation():
    raw = b'A\x00\xff'
    value = resource_observation('failed')
    value.update(returncode=1, failure_code='engineering_failure',
        measurements=[{'measure': 'service_wall_seconds', 'seconds': 1.25}],
        outputs=[{'role': 'stderr', 'available': True, 'bytes': len(raw), 'writer_closed': True}],
        logs=[{'role': 'stderr', 'path': 'native.stderr', 'offset': 0,
               'observed_size': len(raw), 'bytes_base64': base64.b64encode(raw).decode('ascii')}])
    return value, raw


def test_resource_failed_observation_preserves_exact_retained_log_bytes_and_units():
    value, raw = logged_observation()
    result = progress.validate_resource_observation(value)
    assert result == value and result is not value
    assert base64.b64decode(result['logs'][0]['bytes_base64'], validate=True) == raw
    assert result['measurements'] == [{'measure': 'service_wall_seconds', 'seconds': 1.25}]
    assert result['result_available'] is False


@pytest.mark.parametrize('defect', ['duplicate_measure', 'infinite_seconds', 'nan_seconds',
    'non_utc', 'bad_base64', 'noncanonical_base64', 'log_range', 'unavailable_log', 'writer_running'])
def test_resource_observation_rejects_invalid_measurements_and_retained_bytes(defect):
    value, _ = logged_observation()
    if defect == 'duplicate_measure':
        value['measurements'].append(deepcopy(value['measurements'][0]))
    elif defect in {'infinite_seconds', 'nan_seconds'}:
        value['measurements'][0]['seconds'] = float('inf' if defect == 'infinite_seconds' else 'nan')
    elif defect == 'non_utc':
        value['observed_at'] = '2026-11-11T01:00:00+01:00'
    elif defect == 'bad_base64':
        value['logs'][0]['bytes_base64'] = '!'
    elif defect == 'noncanonical_base64':
        value['logs'][0]['bytes_base64'] = 'AB=='
    elif defect == 'log_range':
        value['logs'][0]['offset'] = 1
    elif defect == 'unavailable_log':
        value['outputs'][0].update(available=False, bytes=None, writer_closed=False)
    else:
        value['state'] = 'running'
    with pytest.raises(ContractError, match='invalid_resource_progress_observation') as caught:
        progress.validate_resource_observation(value)
    assert type(caught.value) is ContractError


@pytest.mark.parametrize('field,value', [('lifecycle_state', 'returned'),
    ('observed_at', '2026-11-11T00:00:01+00:00'), ('result_available', True)])
def test_resource_status_rejects_wrapper_native_disagreement(field, value):
    status = progress.resource_status(resource_target(), resource_observation())
    status[field] = value
    with pytest.raises(ContractError, match='invalid_resource_progress_status'):
        progress.validate_resource_status(status)


def test_real_progress_provider_does_not_publish_unavailable_targets(tmp_path):
    with Store(tmp_path / 'store') as store:
        durable = DurableExecutionStore(tmp_path / 'durable')
        provider = ProgressProvider(store, durable, run_id=RUN)
        with pytest.raises(ContractError, match='progress_target_unavailable') as caught:
            provider.observe('missing-handle', ['execution_status'], SCOPE, operation_key='attempt')
        assert type(caught.value) is ContractError
        with pytest.raises(ContractError, match='progress_reference_unavailable'):
            read_progress(store, RUN, 'progress_missing', SCOPE)
        assert store.db.execute('SELECT count(*) FROM runtime_progress_observations').fetchone()[0] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_progress_selections').fetchone()[0] == 0
        assert provider.flush_notifications() == {'published': 0, 'pending': 0}


def save_outcome(store, journal, *, kind='tool', status='failed'):
    episode = EpisodeRef(RUN, (('annotation', 'root'),))
    # This engineering runtime record owns no biological inputs. No problem or
    # material intake, original-input scope, or successful C8 observation is claimed.
    journal.save('runtime_episodes', {'episode_id': episode.episode_id,
        'path': canonical(episode.path), 'request': canonical({'message': {'scope': SCOPE}}),
        'initial_credit': -0.375, 'state': 'running', 'completion': None, 'archive': None})
    journal.save('runtime_actions', {'episode_id': episode.episode_id, 'decision_index': 7,
        'action': canonical({'kind': kind, 'tool': 'engineering.saved_outcome'}),
        'result': canonical({'status': status, 'record_refs': [],
                             'progress_refs': ['progress_missing', 'progress_missing']}),
        'credit': -0.375, 'timing': None})
    body = Record({'credit': -0.375, 'estimation_action_index': 7})
    ledger = CompletionLedger(store, journal)
    if observes_action_outcome(kind, status):
        slot = ledger.stage(episode.episode_id, 7, label='saved-action:7', kind='own_action',
                            controller_input=body, child_return=None)
        assert slot['sequence'] == 0 and slot['original_decision_index'] == 7
        assert slot['controller_input']['credit'] == -0.375
    return episode, UnitRef(episode.episode_id, 0), body, ledger


@pytest.mark.parametrize('kind,status', [(kind, status) for kind in ('tool', 'reason')
    for status in ('failed', 'invalid', 'unavailable')])
def test_saved_executed_outcomes_keep_signed_input_identity_and_missing_progress(tmp_path, kind, status):
    directory = tmp_path / 'store'
    durable = DurableExecutionStore(tmp_path / 'durable')
    with Store(directory) as store:
        journal = Journal(store, RUN)
        provider = ProgressProvider(store, durable, run_id=RUN)
        episode, unit, body, ledger = save_outcome(store, journal, kind=kind, status=status)
        reader = CompletionEvidence(store, journal, durable, provider)
        before = store.db.total_changes
        packet = reader.capture(episode.episode_id, original_decision_index=7, unit_ref=unit, controller_input=body)
        assert reader.capture(episode.episode_id, original_decision_index=7, unit_ref=unit, controller_input=body) == packet
        assert store.db.total_changes == before
        assert packet['unit_ref'] == unit.as_record() and packet['original_decision_index'] == 7
        assert packet['action_kind'] == kind and packet['child_return'] is None
        assert packet['received_record_refs'] == [] and packet['received_progress_refs'] == ['progress_missing']
        assert packet['progress_records'] == []
        assert packet['unavailable_reasons'] == ['progress_body_unavailable:progress_missing']
        assert journal.row('runtime_actions', episode.episode_id, 7)['credit'] == -0.375
        assert ledger.slot(episode.episode_id, 0)['controller_input'] == body.as_record()
        copied = validate_completion_evidence(packet, run_id=RUN, episode_id=episode.episode_id,
            original_decision_index=7, unit_ref=unit)
        copied['unavailable_reasons'].clear()
        assert packet['unavailable_reasons'] == ['progress_body_unavailable:progress_missing']
    with Store(directory) as reopened:
        journal = Journal(reopened, RUN)
        provider = ProgressProvider(reopened, durable, run_id=RUN)
        reader = CompletionEvidence(reopened, journal, durable, provider)
        assert reader.capture(episode.episode_id, original_decision_index=7, unit_ref=unit, controller_input=body) == packet
        assert json.loads(journal.row('runtime_actions', episode.episode_id, 7)['result'])['status'] == status


@pytest.mark.parametrize('status', ['pending', 'rejected'])
def test_pending_or_rejected_outcomes_do_not_become_completed_actions(tmp_path, status):
    with Store(tmp_path / 'store') as store:
        journal = Journal(store, RUN)
        durable = DurableExecutionStore(tmp_path / 'durable')
        episode, unit, body, ledger = save_outcome(store, journal, status=status)
        assert ledger.slot(episode.episode_id, 0) is None
        reader = CompletionEvidence(store, journal, durable, None)
        with pytest.raises(ValueError, match='completion_evidence_requires_completed_outcome_and_credit'):
            reader.capture(episode.episode_id, original_decision_index=7, unit_ref=unit, controller_input=body)


def test_saved_completion_rejects_changed_signed_credit_and_original_index(tmp_path):
    with Store(tmp_path / 'store') as store:
        journal = Journal(store, RUN)
        durable = DurableExecutionStore(tmp_path / 'durable')
        episode, unit, body, _ = save_outcome(store, journal)
        reader = CompletionEvidence(store, journal, durable, None)
        packet = reader.capture(episode.episode_id, original_decision_index=7, unit_ref=unit, controller_input=body)
        assert packet['unavailable_reasons'] == ['progress_reader_unavailable:progress_missing']
        for changed in ({'credit': 0.0, 'estimation_action_index': 7},
                        {'credit': -0.375, 'estimation_action_index': 8}):
            with pytest.raises(ValueError, match='completion_evidence_identity_conflict'):
                reader.capture(episode.episode_id, original_decision_index=7, unit_ref=unit,
                               controller_input=Record(changed))
