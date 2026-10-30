"""Selected reparsing of controlled retained utility captures, inside bounded529.

Native subprocesses are replaced while building explicit fixture bytes. Result
workers, publication custody, selected-action authentication, typed returns and
the shared episode loop are real. No original113b files or real native jobs are
read or changed; the fixture numbers are not scientific measurements.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest
from method_loop.archive import iter_json

from gene_annotation_episode import blast_preparation_result_assembly as assembly
from gene_annotation_episode import native_blast_utility_acquisition as acquisition
from gene_annotation_episode import native_blast_utility_driver as driver
from gene_annotation_episode import native_blast_utility_result_publication as publication
from gene_annotation_episode import native_blast_utility_results as results
from gene_annotation_episode.blast_utility_result_views import FACT_SOURCES
from gene_annotation_episode.communication import form_with_facts, plain
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes, RESULTS_VERSION
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

from test_blast_preparation_publication_653 import controlled_outputs
from test_blast_utility_episode_wiring_632 import context
from test_native_blast_preparation_649 import preparation_job
from test_native_blast_utility_producer_628 import POLICY, identity, reserved_fixture
from test_native_blast_utility_publication_631 import inline_workers, selector
from test_native_hmmer_preparation_nested_workflow import history, provider_value, walk
from test_practical_yield import completion_context


def forbidden(*args, **kwargs):
    pytest.fail('retained result work attempted native execution or reacquisition')


def schema():
    properties = {source.removeprefix('execution.blast_utility_'): deepcopy(row['report_schema'])
        for source, row in FACT_SOURCES.items()}
    return {'type': 'object', 'properties': properties, 'required': list(properties),
        'additionalProperties': False}


def selected(**changes):
    return selector(database_fields=['database_sequence_count', 'database_residue_count'],
        preparation={'fields': ['kind', 'inventory_complete', 'materializations']},
        prepared_database=True, include_checks=True, saved_data=['result', 'prepared_database'], **changes)


def build_host(tmp_path, monkeypatch, *, returncode=0, chosen=None, bind_context=True):
    job = preparation_job(tmp_path, 'aggregate_volumes')
    # Recreate the separately retained database-file/metadata roles behind 657.
    # Both roles have identical original bytes and remain distinct occurrences.
    for database in job['databases']:
        member = next(row for row in database['manifest']['files'] if row['path'].endswith('.njs'))
        database['manifest']['metadata_manifests'].append({**member, 'artifact_ref': None})
        database['manifest_file'] = identity(Path(database['manifest_file']['path']),
            json.dumps(database['manifest'], sort_keys=True).encode())
    _, _, plan, target = reserved_fixture(tmp_path, monkeypatch, job=job)
    with monkeypatch.context() as native_fixture:
        native_calls = controlled_outputs(native_fixture, job, rc=returncode)
        driver.run_native_blast_utility(plan)
    assert len(native_calls) == 1  # One explicit mocked subprocess; no executable ran.
    monkeypatch.setattr(driver.subprocess, 'run', forbidden)
    monkeypatch.setattr(driver.subprocess, 'Popen', forbidden)
    store = Store(tmp_path / 'store')
    scope = {'subject_refs': store.create_problem(raw_sequence='ACGTACGT', molecule='dna')['subject_refs']}
    target['scope'] = scope
    handoff = store.put('source', {'provider': 'explicit_retained_capture_fixture659',
        'accession': None, 'uri': None, 'artifact_ref': store.artifact(canonical(
            {'receipt': {'tool_name': 'controlled_fixture659'}}).encode()),
        'text_ref': None, 'request_ref': None, 'version': 'fixture659_v1',
        'retrieved_at': '2026-10-28T00:00:00+00:00'}, origin='tool')['id']
    target['handle'] = handoff
    resources = {target['resource_id']: {'kind': 'local', 'workspace': str(tmp_path),
        'policy': deepcopy(POLICY), 'native_blast_utility': [{'program': job['operation']['program'],
            'mode': job['operation']['mode'], 'software': job['software'], 'molecules': ['dna'], 'variants': [{}]}]}}
    journal = Journal(store, plan['identity']['run_id'])
    family = ExecutionEpisodes(None, store=store, directory=tmp_path / 'run', run_id=journal.run_id,
        resources=resources, initial_information={}, tool_registry=ToolRegistry(store),
        handoff_unit=3, acquired_record_unit=2, log_window_bytes=32, log_roles=['stdout', 'stderr'])
    h = SimpleNamespace(store=store, scope=scope, journal=journal, family=family, job=job, plan=plan,
        resources=resources, target=target, handoff=handoff, tmp_path=tmp_path,
        receipts=EpisodeReceipts(store, journal.run_id), native_calls=native_calls,
        worker_calls=inline_workers(monkeypatch), observations=[], acquisitions=[])

    def read_target(self, reference, scope):
        assert reference == h.handoff
        h.store.validate_scope(h.scope, parent_scope=plain(scope))
        return deepcopy(h.target)

    def observe_target(self, received, *, operation_key):
        assert received == h.target
        h.observations.append(operation_key)
        return {'state': 'succeeded' if returncode == 0 else 'failed', 'returncode': returncode,
            'observed_at': '2026-10-28T00:00:01+00:00'}

    monkeypatch.setattr(type(family.job_progress_provider.targets), 'read_target', read_target)
    monkeypatch.setattr(type(family.job_progress_provider.targets), 'observe_target', observe_target)
    capture = results.capture_local_utility_bundle

    def retained_capture(store, *, target, directory):
        if not (directory / 'capture.json').exists():
            h.acquisitions.append(str(directory))
        return capture(store, target=target, directory=directory)

    monkeypatch.setattr(results, 'capture_local_utility_bundle', retained_capture)
    h.assignment = {'version': RESULTS_VERSION, 'handoff_ref': handoff, 'selector': chosen or selected()}
    h.schema = schema()
    if bind_context:
        h.parent = context(h, 'annotation', {}, schema=h.schema)
        h.receipts.receive(h.parent.episode_id, [handoff], kind='initial')
        h.child = context(h, 'results', h.assignment, parent=h.parent, schema=h.schema)
        h.family.initialize(h.child)
    return h


@pytest.fixture
def host(tmp_path, monkeypatch):
    h = build_host(tmp_path, monkeypatch)
    yield h
    h.store.close()


def select_collect(h, index):
    key = f'{h.child.run_id}:{h.child.episode_id}:{index}'
    h.journal.save('runtime_actions', {'episode_id': h.child.episode_id, 'decision_index': index,
        'action': canonical({'kind': 'tool', 'tool': 'execution.results.collect', 'arguments': {}}),
        'result': None})
    outcome = asyncio.run(h.family.execute(h.child, 'execution.results.collect', {}, key))
    assert outcome['status'] == 'completed', outcome
    h.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?',
        (canonical(outcome), h.child.run_id, h.child.episode_id, index))
    h.receipts.receive(h.child.episode_id, outcome['record_refs'], kind='own_action', source_index=index)
    return outcome


def fail_parser(monkeypatch, attempts):
    original = assembly.assemble_blast_preparation_result
    calls = []

    def parse(**kwargs):
        calls.append(kwargs['capture']['bundle_artifact_ref'])
        if len(calls) <= attempts:
            raise ContractError('blast_utility_materialization_original_ambiguous')
        return original(**kwargs)

    monkeypatch.setattr(assembly, 'assemble_blast_preparation_result', parse)
    return calls


def action_directory(h, body):
    return h.family.native_blast_utility_results._saved_directory(h.child.episode_id, body['operation_key'])


def pins(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob('*')) if path.is_file()}


def deny_original_reads(h, monkeypatch):
    shutil.rmtree(h.plan['attempt_directory'])
    for database in h.job['databases']:
        shutil.rmtree(Path(database['manifest_file']['path']).parent)
    monkeypatch.setattr(acquisition, '_capture_file', forbidden)
    monkeypatch.setattr(acquisition, 'local_blast_utility_plan', forbidden)


def assert_current_view(h, body):
    facts = h.family.facts(h.child, {})
    for source in FACT_SOURCES:
        field = source.removeprefix('execution.blast_utility_')
        assert facts[source] == ([body[field]] if field == 'status' else body.get(field, []))
    return facts


def freeze_parent_return(h, facts):
    form = form_with_facts({}, h.schema, facts)
    h.family.validate_report(h.child, form, h.schema)
    h.journal.save('runtime_forms', {'episode_id': h.child.episode_id,
        'facts': canonical(facts), 'form': canonical(form)})
    h.journal.save('runtime_actions', {'episode_id': h.parent.episode_id, 'decision_index': 0,
        'action': canonical({'kind': 'episode_child', 'role': 'results', 'scope': h.scope,
            'assignment': h.assignment, 'schema_json': canonical(h.schema),
            'purpose': h.child.request['report_contract']['decision']}), 'result': None})
    h.journal.save('runtime_report_attempts', {'parent_episode_id': h.parent.episode_id,
        'decision_index': 0, 'delivery_ref': 'controlled-return659', 'child_episode_id': h.child.episode_id,
        'contract': canonical(h.child.request['report_contract']), 'form': canonical(form), 'failure': None})
    references = h.family.received_form_references(h.parent, form, h.schema,
        f'{h.parent.run_id}:{h.parent.episode_id}:0:typed_form')
    h.receipts.receive(h.parent.episode_id, references, kind='child_form', source_index=0)
    h.family.validate_received_report(h.parent, form, h.schema)
    return form


def test_new_selected_collect_repairs_original_capture_and_freezes_current_parent_return(host, monkeypatch):
    h = host
    parses = fail_parser(monkeypatch, 1)
    failed = select_collect(h, 0)
    before = failed['result']
    assert before['prepared'] is not None and before['prepared']['result_artifact_ref'] is None
    assert before['status']['native_state'] == 'succeeded' and not before['complete']
    assert before['failures'] and any(row['reason'] == 'result_unavailable' for row in before['missing'])
    frozen_files = pins(action_directory(h, before))
    frozen_action = dict(h.journal.row('runtime_actions', h.child.episode_id, 0))
    frozen_source = deepcopy(h.store.get(before['source_ref']))
    facts_before = assert_current_view(h, before)
    assert h.family.completion_for_action(h.child, before['operation_key']) is None
    assert len(parses) == len(h.acquisitions) == len(h.observations) == 1
    deny_original_reads(h, monkeypatch)
    assert asyncio.run(h.family.execute(h.child, 'execution.results.collect', {}, before['operation_key'])) == failed
    assert len(parses) == 1 and len(h.worker_calls) == 2

    # Make the immutable target index encounter the failed preparation first.
    index = next(i for i in range(1, 100) if digest(f'{h.child.run_id}:{h.child.episode_id}:{i}')
        > digest(before['operation_key']))
    repaired = select_collect(h, index)
    body = repaired['result']
    assert len(parses) == 2 and len(h.worker_calls) == 4
    assert len(h.acquisitions) == len(h.observations) == 1
    assert body['capture'] == before['capture'] and body['observation'] == before['observation']
    assert body['reused_from'] == {key: before[key] for key in ('run_id', 'episode_id', 'operation_key')}
    assert body['prepared']['result_artifact_ref'] is not None and body['complete']
    assert body['status']['state'] == 'complete' and body['missing'] == []
    assert body['failures'] == []
    assert {row['field_name']: row['value'] for row in body['database_fields']} == {
        'database_sequence_count': 3, 'database_residue_count': 24}
    result = json.loads(h.store.get_artifact(body['prepared']['result_artifact_ref']))
    assert body['preparation'][0]['fields']['materializations'] == result['materializations']
    assert len(result['materializations']) == 12
    assert body['prepared_database'][0]['status'] == 'available'
    assert {row['kind'] for row in body['saved_data']} == {'result', 'prepared_database'}
    assert pins(action_directory(h, before)) == frozen_files
    assert dict(h.journal.row('runtime_actions', h.child.episode_id, 0)) == frozen_action
    assert h.store.get(before['source_ref']) == frozen_source
    assert list(h.family.native_blast_utility_results._own_bodies(h.child)) == [before, body]
    assert h.family.native_blast_utility_results._prior(h.target, h.scope) == body
    facts = assert_current_view(h, body)
    assert facts_before['execution.blast_utility_failures'] == before['failures']
    assert facts['execution_result_refs'] == list(dict.fromkeys([*before['record_refs'], *body['record_refs']]))
    selection = {'known_record_refs': list(h.receipts.known(h.child.episode_id)), 'initial_known_record_refs': []}
    credit = h.family.project_credit(h.child, selection)
    assert credit['credit'] == 2 and credit['new_acquired_record_count'] == 1
    proof = h.family.completion_for_action(h.child, body['operation_key'])
    assert proof is not None and h.family.verify_completion(h.child, proof)
    latest = completion_context(run_id=h.child.run_id, episode_id=h.child.episode_id,
        unit_index=1, action_index=index)
    latest['practical_completion'].update(proof)
    estimate = h.family.practical_estimator(h.child)((2.0, 0.0), YieldParameters(), (None, latest))
    assert estimate.turns == 2 and estimate.expected_next_gain == NumericBand.exact(0)
    form = freeze_parent_return(h, facts)

    # Reconstruct the ordinary host, authenticate original forms and replay both
    # actions without invoking either parser or projection worker again.
    h.family = ExecutionEpisodes(None, store=h.store, directory=h.tmp_path / 'run', run_id=h.journal.run_id,
        resources=h.resources, initial_information={}, tool_registry=ToolRegistry(h.store),
        handoff_unit=3, acquired_record_unit=2, log_window_bytes=32, log_roles=['stdout', 'stderr'])
    h.child = h.family.native_blast_utility_returns.context(h.child.episode_id)
    monkeypatch.setattr(results, 'prepare_native_blast_utility_result', forbidden)
    monkeypatch.setattr(results, 'publish_selected_utility_result', forbidden)
    monkeypatch.setattr(publication, 'run_local_job', forbidden)
    frozen_db = list(h.store.db.iterdump())
    for outcome in (failed, repaired):
        assert asyncio.run(h.family.execute(h.child, 'execution.results.collect', {},
            outcome['result']['operation_key'])) == outcome
    assert h.family.received_report_facts(h.parent) == {source: form[source.removeprefix('execution.blast_utility_')]
        for source in FACT_SOURCES}
    h.family.validate_received_report(h.parent, form, h.schema)
    assert list(h.store.db.iterdump()) == frozen_db
    assert pins(action_directory(h, before)) == frozen_files
    # A new operation cannot reopen a completed assignment.
    key = f'{h.child.run_id}:{h.child.episode_id}:{index + 1}'
    h.journal.save('runtime_actions', {'episode_id': h.child.episode_id, 'decision_index': index + 1,
        'action': canonical({'kind': 'tool', 'tool': 'execution.results.collect', 'arguments': {}}), 'result': None})
    rejected = asyncio.run(h.family.execute(h.child, 'execution.results.collect', {}, key))
    assert rejected['status'] != 'completed' and 'assignment_already_completed' in canonical(rejected)
    assert len(parses) == 2 and len(h.worker_calls) == 4


def test_each_failed_new_selection_parses_once_and_reuse_points_to_original_acquisition(host, monkeypatch):
    h = host
    parses = fail_parser(monkeypatch, 3)
    outcomes = [select_collect(h, 0)]
    deny_original_reads(h, monkeypatch)
    for index in (1, 2):
        outcomes.append(select_collect(h, index))
        current = outcomes[-1]
        assert current['result']['prepared']['result_artifact_ref'] is None
        assert asyncio.run(h.family.execute(h.child, 'execution.results.collect', {},
            current['result']['operation_key'])) == current
        assert len(parses) == index + 1
    original = outcomes[0]['result']
    for item in outcomes[1:]:
        assert item['result']['reused_from'] == {key: original[key]
            for key in ('run_id', 'episode_id', 'operation_key')}
    assert len(h.acquisitions) == len(h.observations) == 1
    assert h.family.native_blast_utility_results.completion(h.child) is None
    facts = h.family.facts(h.child, {})
    assert facts['execution.blast_utility_failures'] and facts['execution.blast_utility_missing']
    assert len(list(h.family.native_blast_utility_results._own_bodies(h.child))) == 3


@pytest.mark.parametrize('returncode', [0, 2])
def test_valid_partial_or_native_failed_parsed_result_is_reused(tmp_path, monkeypatch, returncode):
    chosen = selected()
    chosen['database_fields'].append('database_format_version')
    h = build_host(tmp_path, monkeypatch, returncode=returncode, chosen=chosen)
    try:
        first = select_collect(h, 0)
        body = first['result']
        assert body['prepared']['result_artifact_ref'] is not None
        assert body['status']['state'] == 'partial' and not body['complete']
        assert body['status']['native_state'] == ('succeeded' if returncode == 0 else 'failed')
        assert h.family.native_blast_utility_results._prior(h.target, h.scope) == body
        deny_original_reads(h, monkeypatch)
        monkeypatch.setattr(results, 'prepare_native_blast_utility_result', forbidden)
        second = select_collect(h, 1)['result']
        assert second['prepared'] == body['prepared']
        assert len([p for p in h.worker_calls if p['task'] == 'parse_original']) == 1
        assert len(h.acquisitions) == len(h.observations) == 1
        assert second['database_fields'] == body['database_fields']
        assert second['missing'] == body['missing']
        assert_current_view(h, second)
    finally:
        h.store.close()


@pytest.mark.parametrize('ordering,expected', [
    (['missing_a', 'parsed_a'], ['parsed_a']),
    (['parsed_a', 'missing_a'], ['parsed_a', 'missing_a']),
    (['missing_a', 'parsed_b'], ['missing_a', 'parsed_b']),
    (['missing_a', 'missing_b'], ['missing_a', 'missing_b']),
    (['partial_a', 'parsed_a'], ['partial_a', 'parsed_a']),
])
def test_current_projection_requires_later_same_bundle_and_preserves_parsed_partial(ordering, expected):
    # Pure projection boundary: these labels are not acquired native records.
    rows = {name: {'name': name, 'capture': {'bundle_artifact_ref': name.rsplit('_', 1)[1]},
        'prepared': {'result_artifact_ref': None if name.startswith('missing') else 'actual_result'}}
        for name in ordering}
    bodies = [rows[name] for name in ordering]
    before = deepcopy(bodies)
    assert [row['name'] for row in results._current_bodies(bodies)] == expected
    assert bodies == before


def test_shared_episode_loop_records_two_actions_and_exact_zero_without_extra_turn(tmp_path, monkeypatch):
    h = build_host(tmp_path, monkeypatch, bind_context=False)
    parses = fail_parser(monkeypatch, 1)
    factory = ExecutionServiceFactory(h.resources, {}, 3, 2, 1, log_window_bytes=32)
    tools = ToolRegistry(h.store)
    application = factory(h.store, run_id=h.journal.run_id, directory=tmp_path / 'run', tool_registry=tools)
    calls = []

    class Choices:
        async def complete(self, episode_id, role, instructions, current, contract):
            assert not current.get('feedback'), current.get('feedback')
            selected_role = ('results' if current.get('execution_assignment', {}).get('version')
                == RESULTS_VERSION else 'annotation')
            calls.append(selected_role)
            if selected_role == 'results':
                answer = {'selection': {'kind': 'tool', 'tool': 'execution.results.collect', 'arguments': {}},
                    'report_update': {}}
            else:
                answer = {'selection': {'kind': 'episode_child', 'role': 'results',
                    'goal': 'Return the selected retained aggregate-volume database facts.',
                    'scope': h.scope, 'purpose': 'Return requested retained preparation facts.',
                    'assignment': h.assignment, 'schema_json': canonical(h.schema), 'initial_report_json': '{}'},
                    'report_update': {}}
            return provider_value(plain(answer), plain(contract))

        async def release(self, episode_id):
            pass

    def controller(path, initial):
        def parent_estimate(raw, parameters, contexts):
            return YieldEstimate(len(raw), NumericBand.exact(0), parameters,
                {'fixture': 'parent_has_one_requested_child_return'})
        return YieldController(str(path), initial, 0, YieldParameters(100, 50),
            estimate_with_context=parent_estimate if path[-1][0] == 'annotation' else None)

    flow = Workflow(h.store, tools, Choices(), tmp_path / 'run', h.journal.run_id,
        controller_factory=controller, project_credit=lambda *a, **k: 0,
        annotation_child_roles=('results',), episode_record_receipts=True,
        initial_known_record_refs=[h.handoff], episode_binding_descriptors=application.episode_binding_descriptors,
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
    root = flow.build('annotation', 'root', 'Read selected retained database preparation facts.', h.scope)

    async def run():
        record = await root.run_async(flow.context)
        await root.build_result(record)
        return record

    try:
        record = asyncio.run(run())
        records = list(walk(json.loads(''.join(iter_json(record.as_record())))))
        child_record, = [row for row in records if row['path'][-1][0] == 'results']
        h.child = h.family.native_blast_utility_returns.context(child_record['episode_id'])
        own = list(h.family.native_blast_utility_results._own_bodies(h.child))
        assert len(own) == len(parses) == child_record['units_consumed'] == 2
        assert calls == ['annotation', 'results', 'results']
        assert history(child_record) == [2, 0]
        assert child_record['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        for table in ('runtime_actions', 'runtime_observations', 'runtime_estimation_contexts'):
            assert h.store.db.execute('SELECT count(*) FROM ' + table + ' WHERE episode_id=?',
                (h.child.episode_id,)).fetchone()[0] == 2
        returned = json.loads(flow.journal.row('runtime_forms', h.child.episode_id)['form'])
        assert returned['missing'] == returned['failures'] == []
        assert returned['status'] == [own[-1]['status']]
        assert len(h.acquisitions) == len(h.observations) == 1
        assert h.store.count('observation') == h.store.count('annotation') == 0
    finally:
        h.store.close()
