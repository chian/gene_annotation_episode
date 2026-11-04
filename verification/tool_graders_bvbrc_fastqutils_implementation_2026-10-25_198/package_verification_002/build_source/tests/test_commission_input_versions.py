"""C9 byte constraints cross the real Workflow/F1 commission boundary intact.

The resource fixture supplies actual Store sequences and a real homology binding.
Only selected intent creation runs: no DeferredUnit is acquired and no provider,
worker, native job or episode controller is started.
"""
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest

from method_loop import DeferredUnit
from method_loop.durable import DurableExecutionError, content_digest
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_commissions import CommissionError
from gene_annotation_episode.episode_input_versions import pin_commission_inputs
from gene_annotation_episode.independent_execution import _check_assignment
from gene_annotation_episode.materials import artifact_path
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.tools import ToolRegistry
from test_resource_episode_branches import resources, context, selected


def forbidden_execution(*args, **kwargs):
    pytest.fail('commission input checks must not start execution')


def source_record(store):
    artifact = store.artifact('Original source bytes α', 'text/plain')
    return store.put('source', {'provider': 'commission-input-fixture',
        'accession': 'original-source', 'uri': None, 'artifact_ref': artifact,
        'text_ref': artifact, 'request_ref': None, 'version': 'source-version-1',
        'retrieved_at': None}, origin='caller')


@pytest.fixture
def consumer(resources, tmp_path, monkeypatch):
    r = resources
    directory = tmp_path / 'run'
    directory.mkdir()
    # The actual C9 validator compares revision, even on a record without one.
    # Its string expectation must not become the C1 record's version value.
    r.launch['immutable_input_versions'][0]['version'] = str(r.store.get(r.query).get('revision'))
    source = source_record(r.store)
    r.launch['immutable_input_versions'].append({'reference': source['id'],
        'version': str(source.get('revision')), 'content_sha256': None})
    binding = {'factory_module': 'fixture', 'factory_name': 'open_commission',
        'arguments': {}, 'implementation_sha256': 'a' * 64, 'settings_sha256': 'b' * 64}
    tools = ToolRegistry(r.store)
    workflow = Workflow(r.store, tools, SimpleNamespace(complete=forbidden_execution),
        directory, 'commission-input-consumer', forbidden_execution,
        lambda *args, **kwargs: 0, episode_binding_factories=(lambda services: r.binding,),
        execution_binding=binding)
    monkeypatch.setattr(workflow.execution_backend, 'start', forbidden_execution)
    monkeypatch.setattr(workflow.execution_backend, 'commission', forbidden_execution)
    monkeypatch.setattr(tools, 'execute', forbidden_execution)
    monkeypatch.setattr(r.jobs, 'submit', forbidden_execution)
    parent = workflow.build('annotation', 'root', 'Commission the assigned work', r.scope)
    selection = {'kind': 'episode_child', 'role': 'launch',
        'goal': 'Investigate the assigned execution approach', 'scope': deepcopy(r.scope),
        'assignment': deepcopy(r.launch), 'purpose': 'Return the requested execution assessment',
        'schema_json': json.dumps({'type': 'object', 'properties': {
            'assessment': {'type': 'string', 'enum': ['unknown', 'usable']}},
            'required': ['assessment'], 'additionalProperties': False}),
        'initial_report_json': json.dumps({'assessment': 'unknown'})}
    workflow.journal.save('runtime_model_calls', {'episode_id': parent.source.episode_id,
        'call_index': 0, 'purpose': 'decision', 'request': json.dumps({'context': {}}),
        'response': json.dumps({'selection': selection, 'report_update': {}})})
    return SimpleNamespace(resources=r, workflow=workflow, parent=parent,
        selection=selection, source=source)


def test_workflow_selected_freezes_record_and_artifact_pins_without_execution(consumer):
    c, r = consumer, consumer.resources
    before = deepcopy(c.selection)
    unit = c.workflow.selected(c.parent.source, c.selection, 0)
    assert isinstance(unit, DeferredUnit)
    spec, = c.workflow.commissions.recover_selected(c.parent.source.episode_id)
    assignment = spec['child']['request']['message']['episode_assignment']
    assert c.selection == before
    assert assignment == before['assignment']
    assert assignment['immutable_input_versions'] == r.launch['immutable_input_versions']
    pins = {pin['reference']: pin for pin in spec['input_versions']}
    query = r.store.get(r.query)
    artifact = query['sequence_ref']
    original_digest = r.launch['immutable_input_versions'][0]['content_sha256']
    assert pins[r.query] == {'reference': r.query, 'version': None,
        'content_sha256': content_digest(query)}
    assert pins[r.query]['content_sha256'] != original_digest
    assert pins[artifact] == {'reference': artifact, 'version': None,
        'content_sha256': original_digest}
    assert pins[c.source['id']]['version'] == 'source-version-1'
    assert assignment['immutable_input_versions'][1]['version'] == 'None'
    assert len(pins) == len(spec['input_versions'])
    # Exercise worker validation directly, without entering its factory/loop.
    _check_assignment(r.store, spec)
    action = c.workflow.journal.row('runtime_actions', c.parent.source.episode_id, 0)
    assert json.loads(action['result'])['pending_handle'] == spec['handle']
    assert action['credit'] is None
    assert r.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
    assert r.jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
    assert not list(r.jobs.directory.glob('homology_job_*'))
    assert not list((c.workflow.directory / 'episode-execution').glob('execution_*'))


def test_original_pins_reject_tampered_artifact_in_real_producer_and_worker(consumer):
    c, r = consumer, consumer.resources
    c.workflow.selected(c.parent.source, c.selection, 0)
    spec, = c.workflow.commissions.recover_selected(c.parent.source.episode_id)
    artifact = r.store.get(r.query)['sequence_ref']
    path = artifact_path(r.store, artifact)
    original_bytes = path.read_bytes()
    try:
        path.write_bytes(b'changed sequence bytes')
        with pytest.raises(DurableExecutionError) as worker_failure:
            _check_assignment(r.store, spec)
        assert worker_failure.value.failure['code'] == 'identity_conflict'
        assert worker_failure.value.failure['affected_refs'] == [artifact]
        # A distinct original decision reaches F1's actual validation instead
        # of replaying an already committed intent, whose history is immutable.
        with pytest.raises(CommissionError) as failure:
            c.workflow.commissions.select(parent=spec['parent'], child=spec['child'],
                original_decision_index=1, selection=c.selection,
                runtime_binding=spec['runtime_binding'], input_versions=spec['input_versions'],
                constraints=spec['constraints'], resource_selection=spec['resource_selection'],
                expectation_snapshot_refs=spec['expectation_snapshot_refs'],
                selected_at='2026-10-21T12:00:00+00:00')
        assert failure.value.failure['code'] == 'invalid_commission'
        assert c.workflow.commissions.recover_selected(c.parent.source.episode_id) == [spec]
        assert c.workflow.journal.row('runtime_actions', c.parent.source.episode_id, 1) is None
    finally:
        path.write_bytes(original_bytes)
    _check_assignment(r.store, spec)


def test_converter_preserves_order_deduplicates_and_leaves_all_inputs_and_state_unchanged(resources):
    r = resources
    query = r.store.get(r.query)
    artifact = query['sequence_ref']
    source = source_record(r.store)
    references = [source['id'], r.query, source['id']]
    rows = deepcopy(r.launch['immutable_input_versions'])
    rows += [deepcopy(rows[0]), {'reference': artifact, 'version': None,
        'content_sha256': rows[0]['content_sha256']}]
    handoff = {'submitted_input_versions': rows}
    before_inputs = deepcopy((references, handoff))
    before_database = list(r.store.db.iterdump())
    before_changes = r.store.db.total_changes
    before_bytes = artifact_path(r.store, artifact).read_bytes()
    pins = pin_commission_inputs(r.store, references,
        resource_input_versions=handoff['submitted_input_versions'])
    assert [pin['reference'] for pin in pins] == [source['id'], r.query, artifact]
    assert pins[0] == {'reference': source['id'], 'version': source['version'],
        'content_sha256': content_digest(source)}
    assert pins[1]['content_sha256'] == content_digest(query)
    assert pins[2]['content_sha256'] == hashlib.sha256(before_bytes).hexdigest()
    assert (references, handoff) == before_inputs
    assert list(r.store.db.iterdump()) == before_database
    assert r.store.db.total_changes == before_changes
    assert artifact_path(r.store, artifact).read_bytes() == before_bytes
    assert r.jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
    pins[1]['content_sha256'] = '0' * 64
    assert (references, handoff) == before_inputs


@pytest.mark.parametrize('operand', ['digest', 'revision'])
def test_c9_original_constraints_still_reject_conflicts_before_ordering(resources, operand):
    r = resources
    assignment = selected(r)
    row = assignment['immutable_input_versions'][0]
    row['content_sha256' if operand == 'digest' else 'version'] = (
        '0' * 64 if operand == 'digest' else 'unsupplied-revision')
    before = deepcopy(assignment)
    pins = pin_commission_inputs(r.store, [],
        resource_input_versions=assignment['immutable_input_versions'])
    assert pins[0]['content_sha256'] == content_digest(r.store.get(r.query))
    assert assignment == before
    with pytest.raises(ValueError, match='resource_input_version_conflict'):
        r.adapter.prepare_assignment(context(r, 'launch', r.launch), 'launch_local',
            assignment, r.scope, 'conflicting-original-' + operand)
    assert assignment == before
    assert r.jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0


@pytest.mark.parametrize('row', [None, {}, {'reference': 'unknown'},
    {'reference': '', 'version': None, 'content_sha256': None},
    {'reference': 1, 'version': None, 'content_sha256': None},
    {'reference': 'unknown', 'version': 1, 'content_sha256': None},
    {'reference': 'unknown', 'version': '', 'content_sha256': None},
    {'reference': 'unknown', 'version': None, 'content_sha256': 'bad-digest'},
    {'reference': 'unknown', 'version': None, 'content_sha256': 0},
    {'reference': 'unknown', 'version': None, 'content_sha256': None, 'extra': True}])
def test_malformed_resource_rows_fail_without_mutation(resources, row):
    before = list(resources.store.db.iterdump())
    with pytest.raises(ValueError):
        pin_commission_inputs(resources.store, [], resource_input_versions=[row])
    assert list(resources.store.db.iterdump()) == before


@pytest.mark.parametrize('resource', [False, True])
def test_unknown_references_fail_without_mutation(resources, resource):
    before = list(resources.store.db.iterdump())
    with pytest.raises(ContractError, match='unknown_reference'):
        pin_commission_inputs(resources.store, [] if resource else ['absent-record'],
            resource_input_versions=([{'reference': 'absent-record',
                'version': None, 'content_sha256': None}] if resource else ()))
    assert list(resources.store.db.iterdump()) == before


@pytest.mark.parametrize('references, rows', [('not-an-array', ()), ([None], ()),
    ([''], ()), ([], None), ([], {}), ([], 'not-an-array')])
def test_invalid_reference_collections_fail(resources, references, rows):
    with pytest.raises(ValueError):
        pin_commission_inputs(resources.store, references, resource_input_versions=rows)
