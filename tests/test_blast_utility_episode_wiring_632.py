"""Shared utility wiring with explicit synthetic contracts and recorded boundaries.

No native executable, service, worker or database search runs in these checks.
The status receiver and typed-return journal are real; native observations and
already authenticated result bodies are named fixtures, not native evidence.
"""
import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator
from method_loop.identities import EpisodeRef

from gene_annotation_episode.blast_utility_result_views import FACT_SOURCES, blast_utility_fact_sources
from gene_annotation_episode.communication import (
    ReportBoundaryError, form_with_facts, validate_closed_schema, validate_form,
)
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest, plain
from gene_annotation_episode.execution_episodes import ExecutionEpisodes, LAUNCH_VERSION, RESULTS_VERSION
from gene_annotation_episode.native_blast_utility_contracts import LEGACY_MODES, requested_job_from_native_blast_utility
from gene_annotation_episode.numerical import NumericBand, YieldParameters
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

from test_blast_utility_contracts_625 import extraction
from test_blast_utility_result_views_629 import project, selected_sequences, selector
from test_native_blast_utility_producer_628 import POLICY, job_fixture
from test_practical_yield import completion_context


def form_schema(*sources):
    descriptors = blast_utility_fact_sources()
    props = {source.rsplit('_', 1)[-1]: descriptors[source]['report_schema'] for source in sources}
    return {'type': 'object', 'properties': props, 'required': list(props), 'additionalProperties': False}


@pytest.fixture
def host(tmp_path):
    with Store(tmp_path / 'store') as store:
        scope = {'subject_refs': store.create_problem(raw_sequence='ACGTACGT', molecule='dna')['subject_refs']}
        journal = Journal(store, 'utility-wiring-632')
        job = job_fixture(tmp_path)
        configuration = {'kind': 'local', 'workspace': str(tmp_path), 'policy': deepcopy(POLICY),
            'native_blast_utility': [{'program': job['operation']['program'], 'mode': job['operation']['mode'],
                'software': job['software'], 'molecules': ['dna']}]}
        family = ExecutionEpisodes(None, store=store, directory=tmp_path / 'run', run_id=journal.run_id,
            resources={'selected-local': configuration}, initial_information={}, tool_registry=ToolRegistry(store),
            handoff_unit=3, acquired_record_unit=2, log_window_bytes=32, log_roles=['stdout', 'stderr'])
        yield SimpleNamespace(store=store, scope=scope, journal=journal, job=job, family=family,
            configuration=configuration, tmp_path=tmp_path, receipts=EpisodeReceipts(store, journal.run_id))


def assignment(h, job=None):
    return {'version': 'practical_assignment_v1', 'assignment_id': 'utility-job',
        'resource_id': 'selected-local', 'resource_kind': 'local', 'workspace': str(h.tmp_path),
        'endpoint': 'usable_handoff', 'requested_job': requested_job_from_native_blast_utility(job or h.job),
        'progress_requirements': [{'key': 'handoff', 'credit': 3, 'predicate': {'kind': 'requested_job_handoff'}}],
        'completion_keys': ['handoff'], 'initial_context': {'revision': 0, 'cwd': str(h.tmp_path), 'environment': {}},
        'inventory_snapshot': {}, 'constraints': {'allocation': deepcopy(POLICY)}}


def context(h, role, selected, *, parent=None, index=0, schema=None):
    path = ((role, 'root'),) if parent is None else (*parent.path, (role, 'child_' + str(index)))
    report = {'decision': 'Return the selected utility fields', 'measurements': {'schema': schema or form_schema()}}
    request = {'message': {'scope': h.scope, 'episode_assignment': deepcopy(selected)}, 'report_contract': report}
    result = BindingContext(h.journal.run_id, EpisodeRef(h.journal.run_id, path).episode_id,
        role, path, h.scope, selected, request)
    with h.store.transaction():
        h.journal.save('runtime_episodes', {'episode_id': result.episode_id, 'path': canonical(path),
            'request': canonical(request), 'initial_credit': 0, 'state': 'running'})
    h.receipts.bind(result.episode_id, None if parent is None else parent.episode_id)
    return result


def source(h, *, version='native_blast_utility_bundle_v1'):
    bundle, auxiliary = h.store.artifact(b'{"explicit_contract_fixture":true}'), h.store.artifact(b'private fixture bytes')
    reference = h.store.put('source', {'provider': 'episode.execution_result', 'accession': 'fixture632',
        'uri': None, 'artifact_ref': bundle, 'text_ref': None, 'request_ref': None,
        'auxiliary_artifact_refs': [auxiliary], 'version': version,
        'retrieved_at': '2026-10-28T00:00:00+00:00'}, origin='tool')['id']
    return reference, bundle, auxiliary


def target_fixture(h, monkeypatch, selected=None):
    handoff = h.store.put('source', {'provider': 'explicit_protocol_fixture', 'accession': None,
        'uri': None, 'artifact_ref': h.store.artifact(b'handed-off fixture'), 'text_ref': None,
        'request_ref': None, 'version': 'fixture_v1', 'retrieved_at': '2026-10-28T00:00:00+00:00'}, origin='tool')['id']
    target = {'version': 'execution_target_v1', 'handle': handoff, 'run_id': h.journal.run_id,
        'resource_id': 'selected-local', 'resource_kind': 'local', 'execution_id': str(h.tmp_path / 'original/native.json'),
        'origin_episode_id': 'original-local', 'request_sha256': digest(assignment(h)['requested_job']),
        'assignment': assignment(h), 'scope': h.scope, 'attempt_id': digest('original-operation'),
        'original_operation_key': 'original-operation'}
    def read(reference, scope):
        assert reference == handoff
        h.store.validate_scope(target['scope'], parent_scope=plain(scope))
        return deepcopy(target)
    monkeypatch.setattr(h.family.job_progress_provider.targets, 'read_target', read)
    selected = {'version': RESULTS_VERSION, 'handoff_ref': handoff, 'selector': selected or selector()}
    return target, selected


@pytest.mark.parametrize('program,mode', LEGACY_MODES)
def test_configured_modes_reach_exact_assignment_and_commission_library(host, program, mode):
    h = host
    job = job_fixture(h.tmp_path, mode)
    configuration = deepcopy(h.configuration)
    configuration['native_blast_utility'] = [{'program': program, 'mode': mode,
        'software': job['software'], 'molecules': ['dna']}]
    family = ExecutionEpisodes(None, store=h.store, directory=h.tmp_path / 'other', run_id=h.journal.run_id,
        resources={'selected-local': configuration}, initial_information={}, tool_registry=h.family.tool_registry,
        handoff_unit=3, acquired_record_unit=2, log_window_bytes=32, log_roles=['stdout'])
    selected = assignment(h, job)
    Draft202012Validator(family.assignment_schema('launch_local')).validate(selected)
    assert family._validate_request(selected) == selected
    launch = {'version': LAUNCH_VERSION, 'requests': {'selected-local': selected},
        'immutable_input_versions': [], 'constraints': {}}
    assert family._launch(launch, scope=h.scope) == launch
    entry, = [row for row in family.resource_tool_contracts() if row['name'] == 'native.' + program + '.' + mode]
    Draft202012Validator(entry['input_schema']).validate(selected['requested_job'])
    assert entry['invocation_route']['routes'] == [{'entry_role': 'launch',
        'resource_id': 'selected-local', 'resource_role': 'launch_local'}]
    assert entry['instructions'] and entry['resources'] == 'local'
    launch_context = context(h, 'launch', launch)
    assert [row['name'] for row in family.catalog(launch_context)] == ['execution.capabilities']
    assert family.as_record()['configuration']['resources']['selected-local']['policy'] == POLICY


@pytest.mark.parametrize('kind', ['pbs_ssh', 'api'])
def test_utility_binding_rejects_unimplemented_resource_before_provider(host, kind):
    h = host
    configuration = {**h.configuration, 'kind': kind}
    with pytest.raises(ValueError, match='native_blast_utility_resource_execution_binding_unfinished'):
        ExecutionEpisodes(None, store=h.store, directory=h.tmp_path / 'invalid', run_id=h.journal.run_id,
            resources={'selected-local': configuration}, initial_information={}, tool_registry=h.family.tool_registry,
            handoff_unit=3, acquired_record_unit=2, log_window_bytes=32, log_roles=[])


@pytest.mark.parametrize('fault', ['software', 'molecule', 'resource', 'allocation', 'workspace', 'unbound'])
def test_exact_configuration_and_parent_allocation_cannot_change(host, fault):
    h = host
    selected = assignment(h)
    if fault == 'software':
        changed = deepcopy(h.job); changed['software']['sha256'] = 'a' * 64
        selected['requested_job'] = requested_job_from_native_blast_utility(changed)
    elif fault == 'molecule':
        changed = deepcopy(h.job); changed['operation']['molecule'] = 'protein'
        selected['requested_job'] = requested_job_from_native_blast_utility(changed)
    elif fault == 'resource': selected['resource_id'] = 'other'
    elif fault == 'allocation': selected['constraints']['allocation']['memory_bytes'] -= 1
    elif fault == 'workspace': selected['workspace'] = '/unselected'
    elif fault == 'unbound':
        h.family._practical['selected-local'].resources['local']['native_blast_utility'] = []
    with pytest.raises(ValueError):
        h.family._validate_request(selected)
    assert h.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0


def test_original_launch_inputs_are_explicitly_admitted_and_repeated_in_child(host):
    h = host
    artifact = h.store.artifact(b'>ALPHA\nACGTACGT\n')
    h.job['inputs'][0]['artifact_ref'] = artifact
    selected = assignment(h)
    launch = {'version': LAUNCH_VERSION, 'requests': {'selected-local': selected},
        'immutable_input_versions': [], 'constraints': {}}
    root = context(h, 'annotation', {})
    with pytest.raises(ValueError, match='original_input_not_received'):
        h.family.prepare_assignment(root, 'launch', launch, h.scope, 'unexecuted')
    h.receipts.receive(root.episode_id, [artifact], kind='initial')
    assert h.family.prepare_assignment(root, 'launch', launch, h.scope, 'unexecuted') == launch
    parent = context(h, 'launch', launch, parent=root)
    assert h.family.initial_references(parent) == [artifact]
    assert h.family.prepare_assignment(parent, 'launch_local', selected, h.scope, 'unexecuted') == selected
    child = context(h, 'launch_local', selected, parent=parent)
    assert h.family.initial_references(child) == [artifact]
    h.family._check_parent_inputs(child)
    changed = deepcopy(selected)
    changed['requested_job']['native_blast_utility']['inputs'][0]['sha256'] = '0' * 64
    with pytest.raises(ValueError):
        h.family.native_blast_utility_results.validate_job_inputs(child, changed)


def test_selector_schema_and_target_conflicts_reject_before_result_action(host, monkeypatch):
    h = host
    target, selected = target_fixture(h, monkeypatch)
    Draft202012Validator(h.family.assignment_schema('results')).validate(selected)
    assert h.family._selector(selected, target) == selector()
    invalid = deepcopy(selected); invalid['selector']['saved_sheet_ref'] = 'artifact_not_selected'
    assert not Draft202012Validator(h.family.assignment_schema('results')).is_valid(invalid)
    invalid = deepcopy(selected); invalid['selector']['sequences'] = {'selector_ordinals': [0], 'sequence_fields': []}
    with pytest.raises(ValueError, match='not_applicable'):
        h.family._selector(invalid, target)
    invalid_target = deepcopy(target); invalid_target['resource_kind'] = 'hpc'
    with pytest.raises(ValueError, match='target_conflict'):
        h.family._selector(selected, invalid_target)
    invalid_target['assignment']['requested_job'] = {'argv': ['/bin/true'], 'environment': {}}
    with pytest.raises(ValueError, match='target_conflict'):
        h.family._selector(selected, invalid_target)


@pytest.mark.parametrize('fact_source', tuple(FACT_SOURCES))
def test_exact_registered_facts_compile_without_model_string_escape(host, fact_source):
    schema = form_schema(fact_source)
    assert validate_closed_schema(schema) == schema
    assert validate_form({next(iter(schema['properties'])): []}, schema) == {next(iter(schema['properties'])): []}
    assert host.family.received_report_sources('annotation')[fact_source] == FACT_SOURCES[fact_source]
    assert host.family.fact_sources('results')[fact_source] == FACT_SOURCES[fact_source]
    bad = deepcopy(schema)
    bad['properties'][next(iter(bad['properties']))]['items'] = {'type': 'object'}
    with pytest.raises(ReportBoundaryError, match='registered source'):
        validate_closed_schema(bad)


def test_typed_numeric_relationships_and_native_identity_references_are_validated():
    view, _ = project(extraction(), selected_sequences(0))
    schema = form_schema('execution.blast_utility_sequences')
    allowed = {(view['sequences'][0]['source_ref'], 'execution_result'),
        ('out#/records/2', 'native_blast_utility_record'), ('out', 'native_blast_utility_occurrence')}
    result = validate_form({'sequences': view['sequences']}, schema, lambda ref, ns: (ref, ns) in allowed)
    assert result['sequences'][0]['native_reported_length'] == 4
    assert result['sequences'][0]['native_row_ordinal'] == 2
    with pytest.raises(ReportBoundaryError, match='reference is unavailable'):
        validate_form(result, schema, lambda ref, ns: ns != 'native_blast_utility_record')
    invalid = deepcopy(result); invalid['sequences'][0]['native_row_ordinal'] = 0
    with pytest.raises(ReportBoundaryError, match='Invalid recorded BLAST utility fact'):
        validate_form(invalid, schema, lambda *_: True)
    status = form_schema('execution.blast_utility_status')
    invalid = deepcopy(view['status']); invalid.update(writer_closed=False, inventory_complete=True)
    with pytest.raises(ReportBoundaryError, match='Invalid recorded BLAST utility fact'):
        validate_form({'status': [invalid]}, status, lambda *_: True)


@pytest.mark.parametrize('version', ['native_blast_utility_bundle_v1', 'native_blast_masking_bundle_v1'])
def test_source_only_receipts_exclude_auxiliary_bytes_and_explicit_grants_survive(host, version):
    h = host
    root = context(h, 'annotation', {})
    reference, bundle, auxiliary = source(h, version=version)
    h.receipts.receive(root.episode_id, [reference], kind='initial')
    assert set(h.receipts.known(root.episode_id)) == {reference}
    h.receipts.receive(root.episode_id, [auxiliary], kind='initial')
    assert set(h.receipts.known(root.episode_id)) == {reference, auxiliary}
    assert bundle not in h.receipts.known(root.episode_id)


def test_status_dispatch_replay_is_recorded_once_without_acquisition_or_completion(host, monkeypatch):
    h = host
    target, selected = target_fixture(h, monkeypatch)
    root = context(h, 'annotation', {})
    h.receipts.receive(root.episode_id, [selected['handoff_ref']], kind='initial')
    assert h.family.prepare_assignment(root, 'results', selected, h.scope, 'commission') == selected
    child = context(h, 'results', selected, parent=root)
    h.family.initialize(child)
    assert h.family.initial_references(child) == [selected['handoff_ref']]
    assert [row['name'] for row in h.family.catalog(child)] == ['execution.results.status', 'execution.results.collect']
    calls = []
    def observe(received, *, operation_key):
        assert received == target
        calls.append(operation_key)
        return {'state': 'running', 'returncode': None, 'observed_at': '2026-10-28T00:00:00+00:00'}
    monkeypatch.setattr(h.family.job_progress_provider.targets, 'observe_target', observe)
    key = f'{child.run_id}:{child.episode_id}:0'
    h.journal.save('runtime_actions', {'episode_id': child.episode_id, 'decision_index': 0,
        'action': canonical({'kind': 'tool', 'tool': 'execution.results.status', 'arguments': {}}), 'result': None})
    result = asyncio.run(h.family.execute(child, 'execution.results.status', {}, key))
    assert result['status'] == 'completed' and result['record_refs'] == []
    h.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=?',
        (canonical(result), child.run_id, child.episode_id))
    assert asyncio.run(h.family.execute(child, 'execution.results.status', {}, key)) == result
    assert calls == [key]
    assert h.family.facts(child, {})['execution_completed'] is False
    assert h.family.completion_for_action(child, key) is None
    assert h.family.project_credit(child, {'known_record_refs': [], 'initial_known_record_refs': []})['credit'] == 0
    assert h.family._target(child) == target
    assert h.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 1
    assert h.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0


def test_received_typed_values_and_explicit_references_reach_scientific_parent(host, monkeypatch):
    h = host
    _, selected = target_fixture(h, monkeypatch)
    schema = form_schema('execution.blast_utility_sequences')
    parent = context(h, 'annotation', {}, schema=schema)
    child = context(h, 'results', selected, parent=parent, schema=schema)
    reference, bundle, auxiliary = source(h)
    view, _ = project(extraction(), selected_sequences(0), source_ref=reference)
    body = {**view, 'complete': False}
    # This test starts at the already authenticated result-body port. Native
    # acquisition and result publication are covered by their separate checks.
    monkeypatch.setattr(h.family.native_blast_utility_results, '_own_bodies',
        lambda ctx: iter([deepcopy(body)]) if ctx.episode_id == child.episode_id else iter([]))
    facts = h.family.facts(child, {})
    form = form_with_facts({}, schema, facts)
    h.family.validate_report(child, form, schema)
    h.journal.save('runtime_forms', {'episode_id': child.episode_id, 'facts': canonical(facts), 'form': canonical(form)})
    h.journal.save('runtime_actions', {'episode_id': parent.episode_id, 'decision_index': 0,
        'action': canonical({'kind': 'episode_child', 'role': 'results', 'scope': h.scope,
            'assignment': selected, 'schema_json': canonical(schema),
            'purpose': child.request['report_contract']['decision']}), 'result': None})
    h.journal.save('runtime_report_attempts', {'parent_episode_id': parent.episode_id, 'decision_index': 0,
        'delivery_ref': 'fixture-delivery', 'child_episode_id': child.episode_id,
        'contract': canonical(child.request['report_contract']), 'form': canonical(form), 'failure': None})
    admitted = h.family.received_form_references(parent, form, schema,
        f'{parent.run_id}:{parent.episode_id}:0:typed_form')
    assert admitted == [reference]
    h.receipts.receive(parent.episode_id, admitted, kind='child_form', source_index=0)
    received = h.family.received_report_facts(parent)
    assert received['execution.blast_utility_sequences'] == form['sequences']
    assert h.family.resolve_received_reference(parent, 'out#/records/2', 'native_blast_utility_record')
    assert not h.family.resolve_received_reference(parent, 'out#/records/0', 'native_blast_utility_record')
    assert not h.family.resolve_received_reference(parent, auxiliary, 'artifact')
    assert not h.family.resolve_received_reference(parent, bundle, 'artifact')
    h.family.validate_received_report(parent, form, schema)
    forged = deepcopy(form); forged['sequences'][0]['native_reported_length'] = 999
    with pytest.raises(ValueError, match='returned_facts_conflict'):
        h.family.validate_received_report(parent, forged, schema)
    assert set(h.receipts.known(parent.episode_id)) == {reference}
    assert h.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0


def test_original_completion_and_unique_acquisition_use_normal_credit_and_estimator(host, monkeypatch):
    h = host
    _, selected = target_fixture(h, monkeypatch)
    child = context(h, 'results', selected)
    reference, bundle, _ = source(h)
    key = f'{child.run_id}:{child.episode_id}:0'
    view, _ = project(extraction(), selected_sequences(0), source_ref=reference)
    body = {**view, 'complete': True, 'source_ref': reference, 'operation_key': key,
        'tool_name': 'execution.results.collect', 'arguments': {}, 'reused_from': None,
        'capture': {'bundle_artifact_ref': bundle}}
    monkeypatch.setattr(h.family.native_blast_utility_results, '_own_bodies', lambda ctx: iter([deepcopy(body)]))
    h.journal.save('runtime_actions', {'episode_id': child.episode_id, 'decision_index': 0,
        'action': canonical({'kind': 'tool', 'tool': 'execution.results.collect', 'arguments': {}}),
        'result': canonical({'status': 'completed', 'record_refs': [reference], 'result': body})})
    selection = {'known_record_refs': [reference], 'initial_known_record_refs': []}
    credit = h.family.project_credit(child, selection)
    assert credit['credit'] == 2 and credit['new_acquired_record_count'] == 1
    assert credit['operational_credit_binding']['scientific_credit'] is False
    assert h.family.project_credit(child, selection) == credit
    proof = h.family.completion_for_action(child, key)
    assert proof == h.family._proof_for_action(child, key) and h.family.verify_completion(child, proof)
    assert h.family.completion_for_action(child, key + '1') is None
    wrong = {**proof, 'receipt_sha256': '0' * 64}
    assert not h.family.verify_completion(child, wrong)
    estimation = completion_context(run_id=child.run_id, episode_id=child.episode_id, unit_index=0, action_index=0)
    estimation['practical_completion'].update(proof)
    estimate = h.family.practical_estimator(child)((2.0,), YieldParameters(), (estimation,))
    assert estimate.expected_next_gain == NumericBand.exact(0) and estimate.turns == 1
    assert not h.family._native_results_complete(child, [])
    assert h.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 1
