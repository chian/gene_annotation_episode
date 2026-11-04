"""Practical child receipts cross typed forms as scoped original Store sources."""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.practical_execution_records import assess_validations, canonical, digest
from gene_annotation_episode.practical_execution_state import PracticalState
from gene_annotation_episode.practical_receipt_information import (
    PracticalReceiptInformation, PROVIDER, VERSION)
from gene_annotation_episode.state import Store


@pytest.fixture
def selected_receipt(tmp_path):
    store = Store(tmp_path / 'store')
    fasta = tmp_path / 'targets.faa'
    fasta.write_text('>first\nMKKL\n>second\nMTAQ\n')
    targets = store.create_problem(fasta, molecule='protein')['subject_refs']
    target, other = targets
    scope = {'subject_refs': [target], 'segments': [
        {'target_ref': target, 'start': 0, 'end': 2, 'unit': 'aa'}]}
    workspace = tmp_path / 'work'
    workspace.mkdir()
    assignment = {'version': 'practical_assignment_v1', 'assignment_id': 'one-practical-job',
        'resource_kind': 'local', 'workspace': str(workspace), 'endpoint': 'completed_job_outputs',
        'requested_job': {'argv': ['/bin/true'], 'environment': {}},
        'progress_requirements': [{'key': 'output', 'credit': 1,
            'predicate': {'kind': 'requested_job_outputs', 'output_paths': [str(workspace / 'out')]}}],
        'completion_keys': ['output'],
        'initial_context': {'revision': 0, 'cwd': str(workspace), 'environment': {}},
        'inventory_snapshot': {}, 'constraints': {}}
    request = {'message': {'scope': scope, 'episode_assignment': assignment}}
    bound = BindingContext('run-one', 'episode-child', 'launch_local',
        (('annotation', 'root'), ('launch_local', 'selected')), scope, assignment, request)
    journal = Journal(store, bound.run_id)
    with store.transaction():
        journal.save('runtime_episodes', {'episode_id': bound.episode_id,
            'path': canonical(plain(bound.path)), 'request': canonical(request),
            'initial_credit': 0, 'state': 'running'})
        journal.save('runtime_actions', {'episode_id': bound.episode_id, 'decision_index': 0,
            'action': canonical({'kind': 'tool', 'tool': 'practical.inspect', 'arguments': {}}),
            'result': None, 'credit': None})
    key = f'{bound.run_id}:{bound.episode_id}:0'
    state = PracticalState(tmp_path / 'practical-state', bound.run_id, bound.episode_id, assignment)
    state.begin(key, 'practical.inspect', {})
    outcome = {'status': 'completed', 'facts': {}}
    validations = assess_validations(assignment, outcome, state.context(), tool_name='practical.inspect')
    receipt = state.finish(key, outcome, validations)
    reader = PracticalReceiptInformation(store, bound.run_id)
    yield SimpleNamespace(store=store, journal=journal, bound=bound, receipt=receipt,
        reader=reader, target=target, other=other, state=state, tmp_path=tmp_path)
    store.close()


def save_outcome(r, reference, **extra):
    result = {'status': 'completed', 'record_refs': [reference],
        'changed_record_refs': [], 'result': deepcopy(r.receipt), **extra}
    with r.store.transaction():
        r.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? '
            'AND decision_index=0', (canonical(result), r.bound.run_id, r.bound.episode_id))
    return result


def publish_source(r, body, snapshot=None):
    """Construct a separately identified malicious/corrupt source for boundary tests."""
    reference = r.reader.publish(r.bound, r.receipt)
    original = r.store.get(reference)
    if snapshot is None:
        snapshot = json.loads(r.store.get_artifact(original['request_ref']))
    artifact = r.store.artifact(canonical(body), 'application/json')
    request = r.store.artifact(canonical(snapshot), 'application/json')
    payload = r.reader._source_payload(body, artifact, request)
    return r.store.put('source', payload, origin='tool')['id']


def test_publication_before_runtime_result_and_replay_are_original_and_read_only(selected_receipt, monkeypatch):
    r = selected_receipt
    reference = r.reader.publish(r.bound, r.receipt)
    body = r.reader.read(reference, r.bound.scope)
    assert body == {'version': VERSION, 'run_id': r.bound.run_id, 'episode_id': r.bound.episode_id,
        'assignment_sha256': digest(plain(r.bound.assignment)), 'scope': plain(r.bound.scope),
        'receipt': r.receipt}
    source = r.store.get(reference)
    assert source['retrieved_at'] == r.receipt['finished_at']
    assert source['artifact_ref'] == source['text_ref']
    assert 'operand_refs' not in source  # Assigned scope does not assert sequence operands.
    assert r.store.get_artifact(source['artifact_ref']) == canonical(body).encode('utf-8')
    assert r.journal.row('runtime_actions', r.bound.episode_id, 0)['result'] is None
    assert r.reader.publish(r.bound, deepcopy(r.receipt)) == reference

    def no_native(*args, **kwargs):
        raise AssertionError('source admission must not inspect practical state or native execution')
    monkeypatch.setattr(PracticalState, 'receipts', no_native)
    monkeypatch.setattr(PracticalState, 'context', no_native)
    assert PracticalReceiptInformation(r.store, r.bound.run_id).read(reference, r.bound.scope) == body
    save_outcome(r, reference, pending_work_after_action=[])
    assert r.reader.read(reference, r.bound.scope) == body
    assert r.reader.publish(r.bound, r.receipt) == reference
    assert r.store.db.execute("SELECT count(*) FROM records WHERE json_extract(data,'$.provider')=?",
        (PROVIDER,)).fetchone()[0] == 1


def test_parent_can_resolve_original_child_source_without_claiming_ownership(selected_receipt):
    r = selected_receipt
    reference = r.reader.publish(r.bound, r.receipt)
    parent = BindingContext(r.bound.run_id, 'parent', 'annotation', (('annotation', 'root'),),
        {'subject_refs': [r.target]}, {}, {})
    assert r.reader.resolve(parent, reference, 'practical_receipt') is True
    assert r.reader.resolve(parent, reference, 'source') is True
    assert r.reader.read(reference, parent.scope)['episode_id'] == r.bound.episode_id
    assert r.reader.resolve(parent, reference, 'scientific_finding') is False


@pytest.mark.parametrize('scope', ['other_target', 'narrower_segment', 'disjoint_segment'])
def test_explicit_scope_check_prevents_rootless_source_escape(selected_receipt, scope):
    r = selected_receipt
    reference = r.reader.publish(r.bound, r.receipt)
    receiving = ({'subject_refs': [r.other]} if scope == 'other_target' else
        {'subject_refs': [r.target], 'segments': [{'target_ref': r.target,
            'start': 0 if scope == 'narrower_segment' else 2,
            'end': 1 if scope == 'narrower_segment' else 4, 'unit': 'aa'}]})
    # Generic sources have no roots; this source-specific boundary is necessary.
    assert r.store.roots(reference) == []
    assert reference in r.store.reference_subset([reference], receiving)
    with pytest.raises(ValueError, match='outside_receiving_scope'):
        r.reader.read(reference, receiving)
    parent = BindingContext(r.bound.run_id, 'parent', 'annotation', (('annotation', 'root'),),
        receiving, {}, {})
    assert r.reader.resolve(parent, reference, 'practical_receipt') is False


def test_cross_run_reader_and_receiver_rejected(selected_receipt):
    r = selected_receipt
    reference = r.reader.publish(r.bound, r.receipt)
    with pytest.raises(ValueError, match='identity_conflict'):
        PracticalReceiptInformation(r.store, 'another-run').read(reference, r.bound.scope)
    assert r.reader.resolve(replace(r.bound, run_id='another-run'), reference, 'source') is False
    with pytest.raises(ValueError, match='publication_context_conflict'):
        r.reader.publish(replace(r.bound, episode_id='another-child'), r.receipt)


@pytest.mark.parametrize('field', ['arguments', 'tool', 'operation', 'episode', 'assignment'])
def test_forged_receipt_must_match_actual_selected_action_and_original_assignment(selected_receipt, field):
    r = selected_receipt
    changed = deepcopy(r.receipt)
    if field == 'arguments':
        changed['arguments'] = {'invented': True}
    elif field == 'tool':
        changed['tool_name'] = 'practical.job.start'
    elif field == 'operation':
        changed['operation_key'] = f'{r.bound.run_id}:{r.bound.episode_id}:1'
    elif field == 'episode':
        changed['episode_id'] = 'another-child'
    else:
        changed['assignment_sha256'] = '0' * 64
    with pytest.raises(ValueError):
        r.reader.publish(r.bound, changed)
    assert r.store.db.execute("SELECT count(*) FROM records WHERE json_extract(data,'$.provider')=?",
        (PROVIDER,)).fetchone()[0] == 0


@pytest.mark.parametrize('mutation', ['assignment', 'scope', 'role'])
def test_saved_original_episode_is_authoritative_on_read(selected_receipt, mutation):
    r = selected_receipt
    reference = r.reader.publish(r.bound, r.receipt)
    request = plain(r.bound.request)
    path = plain(r.bound.path)
    if mutation == 'assignment':
        request['message']['episode_assignment']['requested_job']['argv'] = ['/bin/false']
    elif mutation == 'scope':
        request['message']['scope'] = {'subject_refs': [r.other]}
    else:
        path[-1][0] = 'launch_hpc'
    with r.store.transaction():
        r.store.db.execute('UPDATE runtime_episodes SET request=?,path=? WHERE run_id=? AND episode_id=?',
            (canonical(request), canonical(path), r.bound.run_id, r.bound.episode_id))
    with pytest.raises(ValueError, match='original_.*conflict'):
        r.reader.read(reference, r.bound.scope)


def test_immutable_assignment_snapshot_supports_read_when_episode_row_absent(selected_receipt):
    r = selected_receipt
    reference = r.reader.publish(r.bound, r.receipt)
    with r.store.transaction():
        r.store.db.execute('DELETE FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (r.bound.run_id, r.bound.episode_id))
    assert r.reader.read(reference, r.bound.scope)['receipt'] == r.receipt


@pytest.mark.parametrize('mutation', ['receipt', 'missing_reference', 'failed'])
def test_later_runtime_result_must_retain_published_receipt_and_source_reference(selected_receipt, mutation):
    r = selected_receipt
    reference = r.reader.publish(r.bound, r.receipt)
    result = save_outcome(r, reference)
    if mutation == 'receipt':
        result['result']['outcome']['invented'] = True
    elif mutation == 'missing_reference':
        result['record_refs'] = []
    else:
        result['status'] = 'failed'
    with r.store.transaction():
        r.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=?',
            (canonical(result), r.bound.run_id, r.bound.episode_id))
    with pytest.raises(ValueError, match='saved_outcome_conflict'):
        r.reader.read(reference, r.bound.scope)


def test_false_validation_is_not_blessed_by_store_source_publication(selected_receipt):
    r = selected_receipt
    receipt = deepcopy(r.receipt)
    receipt['validations'] = [{'key': 'output', 'satisfied': True,
        'predicate': plain(r.bound.assignment)['progress_requirements'][0]['predicate'],
        'evidence_refs': [], 'evidence': {'source': 'outcome', 'value': None},
        'checked_at': receipt['finished_at']}]
    with pytest.raises(ValueError, match='invalid_practical_validation'):
        r.reader.publish(r.bound, receipt)


def test_source_metadata_and_body_have_exact_content_identities(selected_receipt):
    r = selected_receipt
    reference = r.reader.publish(r.bound, r.receipt)
    source = r.store.get(reference)
    source['retrieved_at'] = '2000-01-01T00:00:00+00:00'
    with r.store.transaction():
        r.store.db.execute('UPDATE records SET data=? WHERE id=?', (canonical(source), reference))
    with pytest.raises(ValueError, match='source_identity_conflict'):
        r.reader.read(reference, r.bound.scope)


def test_conflicting_publication_cannot_replace_one_selected_action(selected_receipt):
    r = selected_receipt
    reference = r.reader.publish(r.bound, r.receipt)
    body = r.reader.read(reference, r.bound.scope)
    body['receipt']['outcome']['additional_result'] = 'changed'
    with pytest.raises(ValueError, match='publication_identity_conflict'):
        r.reader.publish(r.bound, body['receipt'])
    assert r.reader.read(reference, r.bound.scope)['receipt'] == r.receipt
