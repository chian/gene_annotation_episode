"""Real selected-action/Store custody with synthetic operational closures.

No optimization runs. One finite result worker reads absent native outputs from
a labelled operational fixture; pure publication tests project retained679
calculated values. Neither synthetic closure is an observed biological result.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
from types import MethodType, SimpleNamespace

import pytest
from method_loop.identities import EpisodeRef

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.communication import plain, form_with_facts
from gene_annotation_episode.domain import obj
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.flux_balance_result_receipts import (
    VERSION, FACT_SOURCES, PROJECTION_SOURCE, SAVED_SOURCE, FAILURE_SOURCE,
    FluxBalanceResultReceipts, empty_files, empty_facts, qualified_files, issue,
)
from gene_annotation_episode.flux_balance_return_views import fba_fact_sources
from gene_annotation_episode.flux_balance_returns import FluxBalanceReturns
from gene_annotation_episode.native_flux_balance_results import NativeFluxBalanceResults, operation_catalog
from gene_annotation_episode.flux_balance_result_views import project_fba_result
from gene_annotation_episode.native_file_capture import retained_native_file
from gene_annotation_episode.native_flux_balance_local import local_flux_balance_plan
from gene_annotation_episode.practical_resource_episodes import PracticalResourceEpisodes
from test_flux_balance_execution_inputs_704 import selected
from test_flux_balance_operation_binding_706 import case, _reader

pytestmark = pytest.mark.skipif('HMMER529_ATTEMPT' not in os.environ, reason='requires bounded529')
ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'verification/tool_graders_flux_balance_core_2026-10-29_679/VERIFIED_NUMERICAL_EXAMPLE_001.json'
REAL_NATIVE = {name: getattr(native, name) for name in (
    'prepare_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect')}


def schema(*sources):
    declarations = fba_fact_sources()
    return obj({'field_' + str(i): deepcopy(declarations[source]['report_schema']) for i, source in enumerate(sources)})


def selector():
    example = json.loads(EXAMPLE.read_text())
    return {'version': 'flux_balance_result_selector_v1', 'mode': 'native_result', 'saved_sheet_file': None,
        'calculation_parameters': deepcopy(example['calculations']['parameters']),
        'projection': {'version': 'flux_balance_projection_selector_v1', 'view': 'run_diagnostics',
            'fields': ['objective', 'candidate_feasibility', 'variable_bound_counts'],
            'row_window': {'offset': 0, 'limit': 99}}}


def finish_runtime(c, receipt, reference):
    result = {'status': 'completed', 'record_refs': [reference], 'changed_record_refs': [reference],
        'result': receipt, 'feedback': None}
    c.f.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?',
        (canonical(result), c.context.run_id, receipt['episode_id'], int(receipt['operation_key'].rsplit(':', 1)[1])))
    c.f.records.receipts.receive(receipt['episode_id'], [reference], kind='own_action',
        source_index=int(receipt['operation_key'].rsplit(':', 1)[1]))


@pytest.fixture
def host(case):
    c = case
    c.view['version'] = native.VERSION
    start, reference = c.action()
    finish_runtime(c, start, reference)
    # Actual immediate-child typed deliveries precede scientific commissioning.
    c.f.records.admit(c.f.parent, c.context, reference)
    c.f.records.admit(c.f.records.root, c.f.parent, reference)
    owner = SimpleNamespace(**vars(c.f.owner))
    owner.resources = {'selected-local': c.config}
    owner.job_progress_provider = SimpleNamespace(targets=_reader(c))
    owner._selected_result_action = MethodType(ExecutionEpisodes._selected_result_action, owner)
    owner._selection = lambda context, selection: {'initial_known_record_refs': []}
    owner.handoff_unit, owner.acquired_record_unit = 2, 3
    owner.native_flux_balance_results = NativeFluxBalanceResults(owner)
    owner.native_flux_balance_returns = FluxBalanceReturns(owner)
    host = owner.native_flux_balance_results
    def child(*, index=3, handoff=reference, selected=None, sources=FACT_SOURCES):
        assignment = {'version': 'execution_results_assignment_v1', 'handoff_ref': handoff,
            'selector': selector() if selected is None else selected}
        return c.f.records.child(c.f.records.root, 'results', assignment, index, schema=schema(*sources))
    def action(context, tool='execution.results.collect', *, index=0):
        c.f.records.journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': index,
            'action': canonical({'kind': 'tool', 'tool': tool, 'arguments': {}}), 'result': None, 'credit': None})
        key = f'{context.run_id}:{context.episode_id}:{index}'
        target = owner.job_progress_provider.targets.read_target(context.assignment['handoff_ref'], context.scope)
        result = asyncio.run(host.execute(context, target, tool, {}, key))
        c.f.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?',
            (canonical(result), context.run_id, context.episode_id, index))
        return result
    return SimpleNamespace(c=c, owner=owner, host=host, child=child, action=action,
        reference=reference, start=start)


def forbidden(*args, **kwargs):
    raise AssertionError('unexpected native/scientific work')


def test_status_freezes_original_custody_and_replays_without_poll(host, monkeypatch):
    f = host;context = f.child()
    result = f.action(context, 'execution.results.status')
    receipt = result['result']
    assert receipt['handoff_proof']['input_binding'] == f.c.control
    assert receipt['handoff_proof']['start_receipt'] == f.start
    assert receipt['observation']['state'] == 'running'
    assert receipt['worker_plan'] is None and receipt['capture'] is None
    assert receipt['facts'] == empty_facts() and receipt['acquired_population'] is None
    monkeypatch.setattr(native, 'status', forbidden)
    target = f.owner.job_progress_provider.targets.read_target(f.reference, context.scope)
    again = asyncio.run(f.host.execute(context, target, 'execution.results.status', {},
        f'{context.run_id}:{context.episode_id}:0'))
    assert again == result


@pytest.mark.parametrize('terminal,quiescent', [(False, False), (True, False)])
def test_collect_preserves_unclosed_writer_without_capture(host, monkeypatch, terminal, quiescent):
    f = host;context = f.child()
    f.c.view.update(state='returned' if terminal else 'running', terminal=terminal, quiescent=quiescent)
    if terminal: f.c.view['metadata']['native_returncode'] = 2
    monkeypatch.setattr('gene_annotation_episode.native_flux_balance_results.capture_flux_balance_native_files', forbidden)
    result = f.action(context)['result']
    assert result['capture'] is None and result['worker_plan'] is None
    assert result['host_failures'][0]['code'] == 'writer_not_closed'
    assert result['facts'][FAILURE_SOURCE][0]['code'] == 'writer_not_closed'
    assert not result['delivery_complete'] and f.host.completion(context) is None
    assert f.host.credit_view(context, {})['credit'] == 0


@pytest.mark.parametrize('field', ['input_file', 'original_start', 'owner_assignment', 'source_action'])
def test_handoff_proof_conflicts_reject_without_native_reads(host, monkeypatch, field):
    f = host;context = f.child();reader = f.host.receipts
    target = f.owner.job_progress_provider.targets.read_target(f.reference, context.scope)
    proof = reader._handoff_metadata(target, context.scope)
    c = deepcopy(proof)
    if field == 'input_file': c['input_binding']['file']['size_bytes'] += 1
    elif field == 'original_start': c['start_receipt']['operation_key'] += '-wrong'
    elif field == 'owner_assignment': c['start_assignment_snapshot']['assignment']['assignment_id'] += '-wrong'
    else: c['source_record']['artifact_ref'] = 'artifact_' + '0' * 64
    monkeypatch.setattr(native, 'status', forbidden)
    with pytest.raises(ValueError, match='handoff_conflict'):
        reader.validate_handoff(c, {'target': target, 'scope': plain(context.scope)})


def test_forwarded_target_handoff_keeps_original_producer(host):
    f = host;c = f.c
    practical = PracticalResourceEpisodes(None, directory=c.f.owner.directory,
        resources={'local': c.config}, store=c.f.store)
    receiver = c.f.records.child(c.f.parent, 'launch_local', deepcopy(c.state.assignment), 1)
    practical.state(receiver)
    arguments = {'receipt_ref': f.reference}
    c.f.records.journal.save('runtime_actions', {'episode_id': receiver.episode_id, 'decision_index': 0,
        'action': canonical({'kind': 'tool', 'tool': 'practical.job.status', 'arguments': arguments}),
        'result': None, 'credit': None})
    result = asyncio.run(practical.execute(receiver, 'practical.job.status', arguments,
        f'{receiver.run_id}:{receiver.episode_id}:0'))
    c.f.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0',
        (canonical(result), receiver.run_id, receiver.episode_id))
    reference = result['record_refs'][0]
    target = f.owner.job_progress_provider.targets.read_target(reference, receiver.scope)
    proof = f.host.receipts._handoff_metadata(target, receiver.scope)
    assert proof['body']['episode_id'] == receiver.episode_id
    assert proof['start_body']['episode_id'] == c.context.episode_id
    assert proof['start_receipt'] == f.start and proof['input_binding'] == c.control


@pytest.mark.parametrize('legacy', [False, True])
def test_compact_handoff_metadata_uses_original_projection_control(selected, monkeypatch, legacy):
    """Real v1/v2 custody; synthetic running status never claims native science."""
    from gene_annotation_episode.flux_balance_request_binding import (
        CONTROL_VERSION, LEGACY_CONTROL_VERSION, OUTPUT_ROLES, read_request_binding,
    )
    from test_flux_balance_resource_registration_707 import _compact, _compact_launch, _family

    f = selected; family = _family(f); compact = _compact(f)
    compact['endpoint'] = 'completed_job_outputs'
    compact['progress_requirements'] = [{'key': 'outputs', 'credit': 1,
        'predicate': {'kind': 'requested_job_outputs', 'output_roles': ['solution', 'flux_csv']}}]
    compact['completion_keys'] = ['outputs']
    launch = f.records.child(f.records.root, 'launch', _compact_launch(f, compact), 1)
    if legacy:
        _, requests = family.flux_balance_requests.preview(launch, plain(launch.assignment))
        family.flux_balance_requests._write(launch, requests, version=LEGACY_CONTROL_VERSION)
    family.initialize(launch)
    context = f.records.child(launch, 'launch_local', compact, 0)
    state = family.initialize(context)
    control = read_request_binding(f.store, f.records.run_id, context.episode_id)
    expected_version = LEGACY_CONTROL_VERSION if legacy else CONTROL_VERSION
    assert control['version'] == control['file']['format'] == control['parent_file']['format'] == expected_version
    assert control['requests'][0]['assignment'] == state.assignment

    # As in the existing706/710 engineering fixture, actual prepared controls
    # belong to this selected identity. No service is started and no native
    # observation, model quantity or closure is represented as a measurement.
    prepared, dispatched = [], []
    def prepare(*args, **kwargs):
        prepared.append((args, kwargs))
        return REAL_NATIVE['prepare_job'](*args, **kwargs)
    def dispatch(handle):
        assert handle.read()['stage'] == 'prepared'
        dispatched.append(str(handle.path))
        return handle
    status = {'version': native.VERSION, 'state': 'running', 'terminal': False, 'quiescent': False,
        'metadata': {'native_returncode': None, 'policy': deepcopy(family.resources['selected-local']['policy'])}}
    monkeypatch.setattr(native, 'prepare_job', prepare)
    monkeypatch.setattr(native, 'start_prepared', dispatch)
    monkeypatch.setattr(native, 'status', lambda _handle: deepcopy(status))
    for name in ('resume_start', 'wait_job', 'collect'):
        monkeypatch.setattr(native, name, forbidden)

    outcomes = []
    for index, tool in enumerate(('practical.job.start', 'practical.job.status')):
        action = {'kind': 'tool', 'tool': tool, 'arguments': {}}
        key = f'{context.run_id}:{context.episode_id}:{index}'
        f.records.journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': index,
            'action': canonical(action), 'result': None, 'credit': None})
        result = asyncio.run(family.execute(context, tool, {}, key))
        f.records.journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': index,
            'action': canonical(action), 'result': canonical(result), 'credit': None})
        f.records.receipts.receive(context.episode_id, result['record_refs'], kind='own_action', source_index=index)
        assert result['result']['version'] == ('flux_balance_practical_outcome_v1' if legacy
            else 'flux_balance_practical_outcome_v2')
        if not legacy:
            assert [row['role'] for row in result['result']['outputs']] == [*OUTPUT_ROLES, 'stdout', 'stderr']
        outcomes.append(result)
    start, later = family.state(context).receipts()
    assert start['operation_key'] != later['operation_key']
    assert family.state(context).completion_proof() is None
    target = family.job_progress_provider.targets.read_target(outcomes[1]['record_refs'][0], context.scope)
    reader = family.native_flux_balance_results.receipts
    before = list(f.store.db.iterdump())
    proof = reader._handoff_metadata(target, context.scope)
    assert proof['body']['receipt'] == later and proof['start_receipt'] == start
    assert proof['body']['receipt']['operation_key'] != proof['start_body']['receipt']['operation_key']
    assert proof['source_record']['id'] == outcomes[1]['record_refs'][0]
    assert proof['start_source_record']['id'] == outcomes[0]['record_refs'][0]
    assert proof['input_binding'] == family.flux_balance_inputs.received(context)
    assert target['origin_episode_id'] == context.episode_id
    for result, receipt in zip(outcomes, (start, later)):
        assert reader._practical_outcome(context, receipt) == result['result']
    assert reader._handoff_metadata(target, context.scope) == proof
    assert read_request_binding(f.store, context.run_id, context.episode_id) == control
    assert family.state(context).receipts() == [start, later]
    assert list(f.store.db.iterdump()) == before
    assert len(prepared) == len(dispatched) == 1
    assert f.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0


def test_pending_target_action_cannot_supply_completed_result_authority(host):
    f = host;c = f.c
    target = f.owner.job_progress_provider.targets.read_target(f.reference, c.context.scope)
    c.f.store.db.execute('UPDATE runtime_actions SET result=NULL WHERE run_id=? AND episode_id=? AND decision_index=0',
        (c.context.run_id, c.context.episode_id))
    with pytest.raises(ValueError, match='target_action_incomplete'):
        f.host.receipts._handoff_metadata(target, c.context.scope)


def test_non_scientific_parent_cannot_commission_results(host):
    f = host
    context = f.c.f.records.child(f.c.f.parent, 'results', {
        'version': 'execution_results_assignment_v1', 'handoff_ref': f.reference,
        'selector': selector()}, 4, schema=schema(*FACT_SOURCES))
    with pytest.raises(ValueError, match='fba_scientific_parent_required'):
        f.host.receipts._context(context)


@pytest.mark.parametrize('failed', [False, True])
def test_verified_partial_files_survive_worker_failure(failed):
    file = {'artifact_ref': 'artifact_' + 'a' * 64, 'sha256': 'a' * 64,
        'size_bytes': 7, 'format': 'flux_balance_sheet_v1'}
    captured = {'result': {}, 'outputs': [{'outcome': 'verified', 'observed': file},
        {'outcome': 'unavailable', 'observed': None}, {'outcome': 'declared_absent', 'observed': None},
        {'outcome': 'verified', 'observed': {**file, 'format': 'flux_balance_result_diagnostics_v1'}}]}
    result = qualified_files(captured, {'returncode': 2 if failed else 0, 'failure': {'code': 'synthetic'} if failed else None})
    assert result['sheet'] == file and result['diagnostics'] is not None
    assert result['calculations'] is result['projection'] is None


def test_published_numbers_are_existing_projection_and_unknown_units_remain_unknown(host):
    f = host;context = f.child();example = json.loads(EXAMPLE.read_text())
    selected = selector()['projection']
    projection = project_fba_result(example['sheet'], example['calculations'], selector=selected)
    file = {'artifact_ref': 'artifact_' + 'b' * 64, 'sha256': 'b' * 64, 'size_bytes': 1, 'format': 'flux_balance_sheet_v1'}
    receipt = {'intent': {'episode_id': context.episode_id, 'tool_name': 'execution.results.collect',
        'assignment': plain(context.assignment)}, 'qualified_files': {**empty_files(), 'sheet': file},
        'projection': projection, 'host_failures': [], 'capture': {'failures': []},
        'worker_capture': {'failures': [issue('binding_unavailable', 'capture', '/worker/execution')],
            'result': {'failures': []}},
        'worker_execution': {'terminal': True, 'quiescent': True, 'returncode': 2},
        'observation': {'native': {'terminal': True, 'quiescent': True}}}
    facts, complete = f.host.receipts.publication(receipt)
    assert facts[PROJECTION_SOURCE] == [projection]
    objective = next(row['value'] for row in projection['rows'] if row['field'] == 'objective')
    assert objective['check']['native_basis_calculated']['value'] == -4.25
    assert objective['check']['full_calculated']['value'] == -2.75
    assert complete  # qualified typed delivery, no optimality/worker-rc gate
    assert all('detail_file' not in row for row in facts[FAILURE_SOURCE])


def assert_receipt_control_faults(host, receipt):
    for fault in ('input_binding', 'request_format', 'native_owner', 'worker_issue_position', 'projection_value'):
        changed = deepcopy(receipt)
        if fault == 'input_binding': changed['capture']['input_binding_file']['size_bytes'] += 1
        elif fault == 'request_format': changed['native']['request_file']['format'] = 'unselected'
        elif fault == 'native_owner': changed['native']['original_plan']['identity']['episode_id'] += '-foreign'
        elif fault == 'worker_issue_position':
            problem = issue('artifact_missing', 'capture', '/worker/result')
            problem['reaction_position'] = 1
            changed['worker_capture']['failures'] = [problem]
        elif changed['projection'] is None: changed['projection'] = {'version': 'forged'}
        else: changed['projection']['page']['returned_row_count'] += 1
        with pytest.raises(ValueError): host.receipts.validate(changed, receipt['intent'])


def test_real_finite_partial_worker_and_closed_host_replay(host, monkeypatch):
    f = host;context = f.child();c = f.c
    from gene_annotation_episode import native_flux_balance_results as module
    adapter = module.prepare_flux_balance_result_worker
    c.view.update(state='returned', terminal=True, quiescent=True)
    c.view['metadata'].update(native_returncode=2,
        service_exit={'SERVICE_RESULT': 'success', 'EXIT_CODE': 'exited', 'EXIT_STATUS': '2'})
    original_worker = f.host._worker
    async def finite(action, receipt, plan):
        with monkeypatch.context() as patch:
            for name, function in REAL_NATIVE.items(): patch.setattr(native, name, function)
            await original_worker(action, receipt, plan)
    monkeypatch.setattr(f.host, '_worker', finite)
    result = f.action(context);receipt = result['result']
    assert receipt['worker_execution']['terminal'] and receipt['worker_execution']['quiescent']
    assert receipt['worker_capture']['result']['native_association'] == 'unavailable'
    assert not receipt['facts'][PROJECTION_SOURCE] and receipt['facts'][SAVED_SOURCE]
    assert any(row['code'] == 'missing_parameters' for row in receipt['facts'][FAILURE_SOURCE])
    assert receipt['facts'][FAILURE_SOURCE] and receipt['acquired_population'] is None
    assert not receipt['delivery_complete'] and f.host.completion(context) is None
    assert f.host.credit_view(context, {})['new_acquired_record_count'] == 0
    original = local_flux_balance_plan(c.state.assignment, receipt['intent']['target']['execution_id'])
    shutil.rmtree(Path(original['identity']['execution_id']).parent)
    monkeypatch.setattr(native, 'status', forbidden)
    monkeypatch.setattr('gene_annotation_episode.native_flux_balance_results.prepare_flux_balance_result_worker', forbidden)
    monkeypatch.setattr('gene_annotation_episode.flux_balance_result_worker.execute_flux_balance_worker', forbidden)
    assert f.host.own_fact_groups(context, verify_artifacts=False) == receipt['facts']
    assert f.host.receipts.read_completed(episode_id=context.episode_id,
        operation_key=receipt['intent']['operation_key'], scope=plain(context.scope)) == receipt
    assert f.host.completion(context) is None
    assert_receipt_control_faults(f.host, receipt)
    Path(os.environ['HMMER529_ATTEMPT']).joinpath('host710-real-partial.json').write_text(json.dumps({
        'receipt': receipt, 'finite_workers': 1, 'native_solves': 0,
        'qualification': 'synthetic native writer closure; actual partial sheet and parameter-population failure'}, allow_nan=False))


def test_original_partial_sheet_saved_repair_and_control_faults(monkeypatch):
    evidence = os.environ.get('HMMER_NATIVE_ORACLE_HOST710_EVIDENCE')
    if evidence is None: pytest.skip('requires explicit original710 receipt evidence')
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry
    record = json.loads(Path(evidence).read_text())
    receipt = record['receipt']
    assignment = receipt['intent']['target']['assignment']
    job = assignment['requested_job']['native_flux_balance']
    store_path = Path(job['model_input']['file']['path']).parents[2]
    directory = Path(receipt['worker_plan']['directory'])
    directory = next(parent for parent in directory.parents if parent.name == 'execution-results')
    configuration = {'kind': 'local', 'workspace': assignment['workspace'],
        'policy': receipt['native']['original_plan']['policy'], 'native_flux_balance': [{
            'version': 'flux_balance_local_binding_v1', 'operation': job['operation'],
            'mode': job['mode'], 'software': job['software'], 'model_formats': ['cobra_json', 'sbml']}]}
    for name in REAL_NATIVE: monkeypatch.setattr(native, name, forbidden)
    with Store(store_path) as store:
        family = ExecutionEpisodes(None, store=store, run_id=receipt['intent']['run_id'],
            directory=directory.parent, resources={assignment['resource_id']: configuration},
            initial_information={}, tool_registry=ToolRegistry(store), handoff_unit=2,
            acquired_record_unit=3, log_window_bytes=64, log_roles=['stdout', 'stderr'])
        current = family.native_flux_balance_results.receipts.read_completed(
            episode_id=receipt['intent']['episode_id'], operation_key=receipt['intent']['operation_key'],
            scope=receipt['intent']['scope'])
        assert current == receipt
        assert_receipt_control_faults(family.native_flux_balance_results, receipt)

        context = family.native_flux_balance_returns.context(receipt['intent']['episode_id'])
        parent = family.native_flux_balance_returns.context(
            EpisodeRef(context.run_id, context.path[:-1]).episode_id)
        from gene_annotation_episode.episode_journal import Journal
        from gene_annotation_episode.episode_receipts import EpisodeReceipts
        from test_bvbrc_appservice_custody import SavedRecords
        records = SavedRecords.__new__(SavedRecords)
        records.store, records.run_id, records.root = store, context.run_id, parent
        records.scope = plain(parent.scope)
        records.journal = Journal(store, context.run_id)
        records.receipts = EpisodeReceipts(store, context.run_id)
        original_schema = plain(context.request)['report_contract']['measurements']['schema']
        facts = family.native_flux_balance_returns.facts_for_closure(context, original_schema)
        form = form_with_facts({}, original_schema, facts)
        family.native_flux_balance_returns.validate_received_report(context, form, original_schema)
        records.journal.save('runtime_forms', {'episode_id': context.episode_id,
            'facts': canonical(facts), 'form': canonical(form)})
        records.journal.save('runtime_report_attempts', {'parent_episode_id': parent.episode_id,
            'decision_index': 3, 'delivery_ref': 'delivery_' + digest([context.episode_id, 3]),
            'child_episode_id': context.episode_id, 'contract': canonical(plain(context.request)['report_contract']),
            'form': canonical(form), 'failure': None})
        references = family.native_flux_balance_returns.record_admission(parent, form, original_schema,
            f'{context.run_id}:{parent.episode_id}:3:typed_form')
        records.receipts.receive(parent.episode_id, references, kind='child_form', source_index=3)
        saved_selector = selector()
        for field in saved_selector['calculation_parameters']:
            if field not in ('version', 'objective_absolute_tolerance'):
                saved_selector['calculation_parameters'][field] = []
        saved_selector.update(mode='saved_sheet_recalculation', saved_sheet_file=receipt['facts'][SAVED_SOURCE][0])
        saved_assignment = {'version': 'execution_results_assignment_v1',
            'handoff_ref': receipt['intent']['target']['handle'], 'selector': saved_selector}
        # Authenticate the received sheet against retained control records.
        # Admission and initialization must not observe the original native job.
        monkeypatch.setattr(family.job_progress_provider.targets, 'observe_target', forbidden)
        admitted = family.prepare_assignment(parent, 'results', saved_assignment,
            parent.scope, f'{parent.run_id}:{parent.episode_id}:4')
        assert admitted == saved_assignment
        later = records.child(parent, 'results', admitted, 4, schema=original_schema)
        records.receipts.receive(later.episode_id, family.initial_references(later), kind='initial')
        family.initialize(later)
        index, key = 0, f'{later.run_id}:{later.episode_id}:0'
        records.journal.save('runtime_actions', {'episode_id': later.episode_id, 'decision_index': index,
            'action': canonical({'kind': 'tool', 'tool': 'execution.results.collect', 'arguments': {}}),
            'result': None, 'credit': None})
        real_worker = family.native_flux_balance_results._worker
        async def finite(action, value, plan):
            with monkeypatch.context() as patch:
                for name, function in REAL_NATIVE.items(): patch.setattr(native, name, function)
                await real_worker(action, value, plan)
        monkeypatch.setattr(family.native_flux_balance_results, '_worker', finite)
        result = asyncio.run(family.execute(later, 'execution.results.collect', {}, key))
        assert result['status'] == 'completed', result
        records.journal.save('runtime_actions', {'episode_id': later.episode_id, 'decision_index': index,
            'action': canonical({'kind': 'tool', 'tool': 'execution.results.collect', 'arguments': {}}),
            'result': canonical(result), 'credit': None})
        saved = result['result']
        assert saved['capture'] is saved['native'] is saved['observation'] is None
        assert saved['worker_capture']['result']['native_association'] == 'not_applicable'
        assert saved['acquired_population'] is None and saved['delivery_complete']
        assert saved['facts'][PROJECTION_SOURCE] and saved['facts'][SAVED_SOURCE]
        assert saved['original_origins'] == [{'episode_id': context.episode_id,
            'operation_key': receipt['intent']['operation_key']}]
        assert saved['worker_plan']['selector']['calculation_parameters'] != receipt['worker_plan']['selector']['calculation_parameters']
        assert family.native_flux_balance_results.completion(later)
        monkeypatch.setattr(family.native_flux_balance_results, '_worker', forbidden)
        replay = asyncio.run(family.execute(later, 'execution.results.collect', {}, key))
        assert replay == result
        assert family.native_flux_balance_results.receipts.read_completed(episode_id=later.episode_id,
            operation_key=key, scope=plain(later.scope)) == saved
        Path(os.environ['HMMER529_ATTEMPT']).joinpath('host710-saved-repair.json').write_text(json.dumps({
            'original': receipt, 'saved': saved, 'additional_finite_workers': 1, 'native_solves': 0,
            'original_evidence_file': str(Path(evidence)),
            'qualification': 'explicit saved repair of the selected original partial numerical sheet; no original worker repeated'}, allow_nan=False))
