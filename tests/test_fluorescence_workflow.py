"""Real supplied-fluorescence execution through Workflow and requested returns.

Run only through529/run_checks.py (20GiB RAM, 4GiB scratch, swap0, no wall cap).
Scripted episode choices and synthetic supplied measurements are explicit; no
native measurement, driver validation, receipt or scientific result is stubbed.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from gene_annotation_episode import fluorescence_event_contracts as core
from gene_annotation_episode.communication import plain
from gene_annotation_episode.fluorescence_execution_common import canonical as control_canonical
from gene_annotation_episode.numerical import NumericBand
from gene_annotation_episode.state import Store

import fluorescence_workflow_support as F


def deny(*args, **kwargs):
    raise AssertionError('saved calculation or closed replay attempted original execution, acquisition, or network')


def receipts(store):
    return [json.loads(row['result'])['result'] for row in store.db.execute(
        "SELECT result FROM runtime_actions WHERE result IS NOT NULL AND "
        "json_extract(result,'$.result.version')='native_fluorescence_acquired_result_v1' ORDER BY rowid")]


def artifact_path(store, file):
    return store.path / 'artifacts' / file['sha256'][:2] / file['sha256']


def retained_result(store, receipt):
    return {role: {'file': deepcopy(file), 'raw': store.get_artifact(file['artifact_ref']),
            'value': json.loads(store.get_artifact(file['artifact_ref']))}
        for role, file in receipt['qualified_files'].items() if file is not None}


@pytest.fixture(scope='module', params=[
    ('perform_facs_cell_sorting', 'csv'),
    ('analyze_cytokine_production_in_cd4_tcells', 'table_snapshot'),
], ids=['facs-csv', 'cytokine-table'])
def connected_case(tmp_path_factory, request):
    operation, parser = request.param
    directory = tmp_path_factory.mktemp('fluorescence571-' + parser)
    evidence, patch = {'removed': [], 'saved_dispatches': [], 'saved_lifecycle_accesses': []}, pytest.MonkeyPatch()

    def remove(path, kind):
        path = Path(path)
        if path.is_file():
            raw = path.read_bytes()
            evidence['removed'].append(dict(path=str(path), kind=kind,
                size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
            path.unlink()

    def before_partial(case):
        original, = receipts(case.store)
        assert original['delivery_complete'] and original['observation']['native']['quiescent']
        evidence['original_receipt'] = deepcopy(original)
        evidence['original_return'] = deepcopy(case.original_return)
        evidence['original_result'] = retained_result(case.store, original)
        evidence['original_observations'] = F.rows(case.store, 'runtime_observations')
        evidence['original_actions'] = [row for row in F.rows(case.store, 'runtime_actions') if row['result'] is not None]
        evidence['native_plan'] = deepcopy(case.provider.plan)
        evidence['native_plan_raw'] = (Path(case.provider.target['execution_id']).parent / 'fluorescence-plan.json').read_bytes()
        # Controlled failure injection after the original writer closed and its
        # complete result was delivered. Preserve its receipt/form/history.
        spec = next(row for row in case.provider.plan['outputs'] if row['role'] == 'event_input:1')
        missing = Path(case.provider.plan['attempt_directory']) / spec['relative_path']
        assert missing.read_bytes() == case.provider.native_bytes['event_input:1']
        remove(missing, 'closed_writer_original_input_copy')
        evidence['missing_original'] = str(missing)

    def before_saved(case):
        original, partial = receipts(case.store)
        assert original == evidence['original_receipt'] and not partial['delivery_complete']
        assert partial['worker_capture']['result']['native_outcome'] == 'partial'
        evidence['partial_receipt'] = deepcopy(partial)
        evidence['partial_result'] = retained_result(case.store, partial)
        evidence['observations_before_saved'] = F.rows(case.store, 'runtime_observations')
        evidence['actions_before_saved'] = [row for row in F.rows(case.store, 'runtime_actions') if row['result'] is not None]
        sheet_file, = case.partial_return['saved']
        evidence['saved_sheet_file'] = deepcopy(sheet_file)
        evidence['saved_sheet_raw'] = case.store.get_artifact(sheet_file['artifact_ref'])
        evidence['origins'] = case.owner.native_fluorescence_returns.authenticate_received_saved_sheet(
            case.science_context, sheet_file)

        # Withdraw original source/producer bytes and its own copied executable.
        # Keep the received partial sheet and the durable control receipts only.
        for receipt in (original, partial):
            for row in receipt['capture']['files']:
                if row['retained'] is not None:
                    remove(artifact_path(case.store, row['retained']['file']), 'captured_native_scientific_bytes')
            for role in ('sheet', 'calculations', 'projection', 'context'):
                file = receipt['qualified_files'][role]
                if file is not None and file != sheet_file:
                    remove(artifact_path(case.store, file), 'retained_numerical_bytes')
        for run in F.worker_runs(directory):
            for name in ('sheet.json', 'calculations.json', 'projection.json', 'context.json'):
                remove(Path(run['directory']) / name, 'original_worker_numerical_copy')
        native_directory = Path(case.provider.target['execution_id']).parent
        evidence['withdrawn_producer_directory'] = str(native_directory)
        for path in sorted(native_directory.rglob('*')):
            if path.is_file():
                remove(path, 'original_producer_directory')
        shutil.rmtree(native_directory)
        for path in [Path(case.software['python']['path']),
                *(Path(row['path']) for row in case.software['implementation_files'])]:
            remove(path, 'original_producer_software')
        assert not native_directory.exists()
        assert not Path(case.software['python']['path']).exists()
        assert artifact_path(case.store, sheet_file).read_bytes() == evidence['saved_sheet_raw']

        from gene_annotation_episode import native_lifecycle
        prepare = native_lifecycle.prepare_job

        def saved_worker_only(command, **kwargs):
            assert command[1:5] == ['-B', '-S', '-m', 'gene_annotation_episode.fluorescence_result_worker']
            plan = json.loads(Path(command[-1]).read_bytes())
            assert plan['mode'] == 'saved_sheet_recalculation'
            assert plan['selector']['saved_sheet_file'] == sheet_file
            assert 'original_plan' not in plan and 'capture' not in plan
            assert kwargs['policy'].to_dict() == F.POLICY
            evidence['saved_dispatches'].append(dict(command=list(command), plan=deepcopy(plan)))
            return prepare(command, **kwargs)

        patch.setattr(native_lifecycle, 'prepare_job', saved_worker_only)
        for name in ('start_prepared', 'resume_start', 'status', 'wait_job', 'collect'):
            original_function = getattr(native_lifecycle, name)

            def saved_lifecycle_only(handle, *args, _name=name, _function=original_function, **kwargs):
                assert str(handle.path) != case.provider.target['execution_id']
                assert handle.path.name == 'worker.handle.json'
                evidence['saved_lifecycle_accesses'].append(dict(operation=_name, handle=str(handle.path)))
                return _function(handle, *args, **kwargs)

            patch.setattr(native_lifecycle, name, saved_lifecycle_only)
        patch.setattr('gene_annotation_episode.native_fluorescence_results.capture_fluorescence_native_files', deny)
        patch.setattr(type(case.owner.job_progress_provider.targets), 'observe_target', deny)
        patch.setattr('socket.create_connection', deny)
        patch.setattr('socket.socket.connect', deny)
        patch.setattr('socket.socket.connect_ex', deny)

    try:
        case = F.workflow_case(directory, operation=operation, parser=parser,
            before_partial=before_partial, before_saved=before_saved)
        case.evidence = evidence
        case.evidence['saved_result'] = retained_result(case.store, case.outcomes[2]['result'])
        F.write(directory / 'WITHDRAWAL_AND_REPLAY_INPUTS.json', {key: value for key, value in evidence.items()
            if key not in {'original_result', 'partial_result', 'saved_result', 'saved_sheet_raw', 'native_plan_raw'}})
    finally:
        patch.undo()
    try:
        yield case
    finally:
        case.store.close()


def test_actual_native_alias_and_shared_cells_reach_requested_parent(connected_case):
    case = connected_case
    assert {role: len(group) for role, group in case.by_role.items()} == {
        'annotation': 1, 'scientific_process': 1, 'launch': 1, 'launch_local': 1, 'results': 3}
    assert case.job['operation'] not in case.tools.catalog()
    information, = plain(case.scientific_context.assignment)['selection']['child_tool_info']
    assert information['name'] == case.job['operation'] and information['resources'] == 'local'
    assert information['description'] and information['instructions']
    assert case.provider.plan['requested_job']['native_fluorescence'] == case.job
    assert case.provider.plan['policy'] == F.POLICY
    native = json.loads((case.directory / 'native-lifecycle.json').read_bytes())
    assert native['returncode'] == 0 and native['metadata']['verified_cgroup'] == F.LIMITS
    assert case.software['dependency_roots'] == case.software['distributions'] == []
    assert case.software['runtime_files'] and case.software['implementation_files']
    result = case.evidence['original_result']
    sheet, components = result['sheet']['value'], result['calculations']['value']
    assert sheet['schema'] == core.SHEET_SCHEMA and components['schema'] == core.COMPONENTS_SCHEMA
    assert components['sheet_sha256'] == core.digest(sheet)
    assert sheet['gate_definitions'] == case.job['definitions']['gates']
    assert sheet['population_definitions'] == case.job['definitions']['populations']
    assert [row['label'] for row in sheet['samples']] == ['CD4 α 0', 'CD4 α 1']
    assert all(row['native_event_count'] is None and row['extent'] == 'complete' for row in sheet['input_sources'])
    for i in range(2):
        batch = json.loads(case.provider.native_bytes[f'event_batch:{i}'])
        assert case.provider.native_bytes[f'event_input:{i}'] == case.raw
        assert [event['values'][0]['measurement']['value'] for event in batch['parse']['events']] == F.VALUES
        assert {event['values'][0]['measurement']['state'] for event in batch['parse']['events']} == {'observed'}
        assert batch['parse']['sample']['condition'] == f'supplied-condition-{i}'
    first = case.returned[0]
    assert first['completed'] and first['failures'] == []
    assert [row['value'] for row in first['measurements'][0]['rows']] == [8, 5, .625, 62.5, 165, 150] * 2
    assert first['measurements'] == [result['projection']['value']]
    assert first['contexts'] == [result['context']['value']]
    assert all(row in components['cells'] for row in first['measurements'][0]['rows'])
    assert all(row['population']['denominator'] == 'parent' for row in first['measurements'][0]['rows']
        if row['request']['kind'] == 'fraction')
    assert all(row['unit'] == 'arbitrary_instrument_units' for row in first['measurements'][0]['rows']
        if row['request']['kind'] == 'intensity')
    expected = {field: [form[field][0] for form in case.returned] for field in ('measurements', 'contexts')}
    assert case.forwarded == expected
    assert case.owner.native_fluorescence_returns.received_facts(case.root_context, case.parent_form) == {
        F.PROJECTION_SOURCE: expected['measurements'], F.CONTEXT_SOURCE: expected['contexts']}
    F.write(case.directory / 'NUMERICAL_EXAMPLE.json', dict(input=F.VALUES,
        inclusive_gate=dict(lower=100, upper=250), selected=[100, 125, 150, 200, 250],
        selected_count=5, denominator=8, fraction=.625, percent=62.5, mean=165, median=150,
        returned=case.returned, forwarded=case.forwarded))


def test_unicode_artifacts_keep_numerical_and_control_hashes_distinct(connected_case):
    case = connected_case
    for label in ('original_result', 'partial_result', 'saved_result'):
        for role in ('sheet', 'calculations', 'projection', 'context'):
            artifact = case.evidence[label][role]
            raw, value, file = artifact['raw'], artifact['value'], artifact['file']
            assert raw == core.canonical(value) + b'\n'
            assert file['sha256'] == hashlib.sha256(raw).hexdigest() and file['size_bytes'] == len(raw)
        for role in ('sheet', 'context'):
            artifact = case.evidence[label][role]
            assert artifact['raw'] != control_canonical(artifact['value']) + b'\n'
    for i in range(2):
        raw = case.provider.native_bytes[f'event_batch:{i}']
        value = json.loads(raw)
        assert raw == core.canonical(value) + b'\n' and raw != control_canonical(value) + b'\n'
    manifest = case.provider.native_bytes['manifest']
    assert manifest == control_canonical(json.loads(manifest)) + b'\n'
    assert manifest != core.canonical(json.loads(manifest)) + b'\n'
    assert case.evidence['native_plan_raw'] == control_canonical(case.provider.plan) + b'\n'


def test_missing_original_bytes_preserve_partial_work_and_original_closed_history(connected_case):
    case, evidence = connected_case, connected_case.evidence
    original, partial, saved = [row['result'] for row in case.outcomes]
    assert original == evidence['original_receipt']
    assert case.returned[0] == evidence['original_return']
    assert original['worker_capture']['result']['native_outcome'] == 'complete'
    assert original['delivery_complete'] and not partial['delivery_complete']
    assert partial['worker_capture']['result']['native_outcome'] == 'partial'
    assert not partial['worker_capture']['result']['analysis_complete']
    assert any(row['code'] == 'capture_file_unavailable' and row['role'] == 'event_input:1'
        and row['input_index'] == 1 for row in case.returned[1]['failures'])
    view = case.returned[1]['measurements'][0]
    assert [row['value'] for row in view['rows']] == [8, 5, .625, 62.5, 165, 150] + [None] * 6
    assert all(row['state'] == 'unavailable' for row in view['rows'][6:])
    sheet = evidence['partial_result']['sheet']['value']
    assert [row['extent'] for row in sheet['input_sources']] == ['complete', 'unavailable']
    assert sheet['gate_definitions'] == case.job['definitions']['gates']
    assert all(row in F.rows(case.store, 'runtime_observations') for row in evidence['original_observations'])
    assert all(row in F.rows(case.store, 'runtime_actions') for row in evidence['original_actions'])
    assert saved['delivery_complete'] and case.returned[2]['completed']
    assert saved['worker_capture']['result']['analysis_complete']
    assert evidence['partial_result']['sheet']['raw'] == evidence['saved_result']['sheet']['raw']


def test_saved_partial_recalculation_and_requested_context_have_no_new_acquisition(connected_case):
    case, evidence = connected_case, connected_case.evidence
    original, partial, saved = [row['result'] for row in case.outcomes]
    assert original['acquired_population'] == partial['acquired_population'] is not None
    assert saved['acquired_population'] is None
    assert len(evidence['saved_dispatches']) == 1
    assert all(saved[key] is None for key in ('observation', 'native', 'capture', 'source_action_file', 'writer_closure_file'))
    assert not Path(evidence['withdrawn_producer_directory']).exists()
    assert not Path(case.software['python']['path']).exists()
    assert not Path(case.job['inputs'][0]['path']).exists()
    assert case.returned[1]['saved'] == case.returned[2]['saved'] == [evidence['saved_sheet_file']]
    assert case.store.get_artifact(evidence['saved_sheet_file']['artifact_ref']) == evidence['saved_sheet_raw']
    assert saved['worker_capture']['result']['native_outcome'] == 'not_applicable'
    assert not saved['worker_capture']['result']['original_events_acquired']
    view = case.returned[2]['measurements'][0]
    assert view['selection'] == F.selector(saved=evidence['saved_sheet_file'])['selection']
    assert (view['total_selected_rows'], view['returned_row_count'], view['has_more']) == (12, 4, True)
    assert [row['value'] for row in view['rows']] == [.625, 62.5, 165, 150]
    assert all(row['population']['denominator'] == 'evaluable' for row in view['rows']
        if row['request']['kind'] == 'fraction')
    assert all(row in evidence['saved_result']['calculations']['value']['cells'] for row in view['rows'])
    context = case.returned[2]['contexts'][0]
    assert [sample['key'] for sample in context['samples']] == ['sample-0']
    assert [gate['key'] for gate in context['gates']] == ['gate-0']
    assert not context['control_pairs'] and not context['native_reports']
    assert 'events' not in context and all('metadata' not in row for row in context['sources'])
    assert all('event_ordinals' not in row for row in context['populations'])
    assert all('correspondence' not in row for row in context['domains'])
    file = evidence['saved_sheet_file']
    assert case.owner.resolve_received_reference(case.scientific_context, file['artifact_ref'], 'artifact') is True
    assert case.owner.resolve_received_reference(case.root_context, file['artifact_ref'], 'artifact') is False
    with pytest.raises(ValueError, match='saved_sheet_not_received'):
        case.owner.native_fluorescence_returns.authenticate_received_saved_sheet(case.root_context, file)
    calculations = saved['qualified_files']['calculations']['artifact_ref']
    assert case.owner.resolve_received_reference(case.root_context, calculations, 'artifact') is False
    assert all(row in F.rows(case.store, 'runtime_observations') for row in evidence['observations_before_saved'])
    assert all(row in F.rows(case.store, 'runtime_actions') for row in evidence['actions_before_saved'])
    runs = F.worker_runs(case.directory)
    assert sorted(row['plan']['mode'] for row in runs) == ['native_result', 'native_result', 'saved_sheet_recalculation']
    for run in runs:
        execution = json.loads((Path(run['directory']) / 'execution.json').read_bytes())
        assert execution['returncode'] == 0 and execution['terminal'] and execution['quiescent']
        assert execution['metadata']['verified_cgroup'] == F.LIMITS
        assert execution['intent']['dependencies'] == []
        assert not {'fluorescence_event_readers.py', 'fluorescence_fcs_reader.py', 'native_fluorescence_driver.py'} & {
            Path(pin['path']).name for pin in execution['intent']['source_pins']}


def test_one_observation_per_action_original_credit_and_practical_terminal_zero(connected_case):
    case = connected_case
    for record in case.records:
        context = case.contexts[record['episode_id']]
        actions = [row for row in F.rows(case.store, 'runtime_actions') if row['episode_id'] == context.episode_id]
        observations = [row for row in F.rows(case.store, 'runtime_observations') if row['episode_id'] == context.episode_id]
        assert len(actions) == len(observations) == record['units_consumed']
        assert case.provider.turns[context.episode_id] == len(actions) + (context.role == 'scientific_process')
        if context.role in {'launch', 'launch_local', 'results'}:
            assert len(actions) == 1
            proof = case.owner.completion_for_action(context, f'{F.RUN_ID}:{context.episode_id}:0')
            partial = context.role == 'results' and context.path[-1][1] == 'child_2'
            assert (proof is None) is partial
            if not partial:
                assert case.owner.verify_completion(context, proof)
                assert record['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
    assert [F.history(row) for row in case.by_role['launch_local']] == [[7]]
    assert [F.history(row) for row in case.by_role['launch']] == [[3]]
    assert [F.history(row) for row in case.by_role['results']] == [[2], [0], [0]]
    assert case.store.count('annotation') == 0
    attempts = [row for row in F.rows(case.store, 'runtime_report_attempts')
        if row['parent_episode_id'] == case.scientific_context.episode_id]
    original = [row for row in attempts if row['child_episode_id'] == case.result_contexts[0].episode_id]
    assert len(original) == 2 and original[0]['form'] == original[1]['form']
    assert all(row['failure'] is None for row in original)


def test_closed_workflow_and_result_replay_without_producer_or_numerical_bytes(connected_case, monkeypatch):
    case = connected_case
    # Closed forms/receipts are sufficient even after all scientific bytes have
    # been withdrawn. A fresh calculation would require its saved-sheet bytes.
    removed = []
    for outcome in case.outcomes:
        result = outcome['result']
        for role in ('sheet', 'calculations', 'projection', 'context'):
            file = result['qualified_files'][role]
            path = artifact_path(case.store, file)
            if path.is_file():
                removed.append(F.pin(path))
                path.unlink()
        root = Path(result['worker_plan']['directory'])
        for folder in ('runtime', 'source_snapshot'):
            shutil.rmtree(root / folder)
        for name in ('sheet.json', 'calculations.json', 'projection.json', 'context.json'):
            (root / name).unlink(missing_ok=True)
    for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect'):
        monkeypatch.setattr('gene_annotation_episode.native_lifecycle.' + name, deny)
    for name in ('capture_fluorescence_native_files', 'prepare_fluorescence_result_worker'):
        monkeypatch.setattr('gene_annotation_episode.native_fluorescence_results.' + name, deny)
    monkeypatch.setattr('gene_annotation_episode.native_fluorescence_preparation._verify_pins', deny)
    monkeypatch.setattr(type(case.owner.job_progress_provider.targets), 'observe_target', deny)
    monkeypatch.setattr('socket.create_connection', deny)
    monkeypatch.setattr('socket.socket.connect', deny)
    monkeypatch.setattr('socket.socket.connect_ex', deny)

    class NoNewDecisions:
        async def complete(self, *args, **kwargs):
            raise AssertionError('closed Workflow requested a new decision')
        async def release(self, episode_id):
            pass

    with Store(case.directory / 'state') as store:
        before = {table: F.rows(store, table) for table in F.TABLES}
        flow, _ = F.assemble(store, case.directory, NoNewDecisions(), case.configuration)
        owner = flow.episode_bindings.for_role('results')
        for context, original in zip(case.result_contexts, case.outcomes):
            restored = owner.native_fluorescence_returns.context(context.episode_id)
            key = f'{F.RUN_ID}:{context.episode_id}:0'
            proof = owner.completion_for_action(restored, key)
            replay = asyncio.run(owner.execute(restored, 'execution.results.collect', {}, key))
            assert replay == {k: v for k, v in original.items() if k != 'pending_work_after_action'}
            if proof is not None:
                assert owner.verify_completion(restored, proof)
        _, _, archive = asyncio.run(F.run_root(flow, case.configuration))
        assert archive == case.archive
        assert {table: F.rows(store, table) for table in F.TABLES} == before
    F.write(case.directory / 'CLOSED_REPLAY.json', dict(removed_numerical_artifacts=removed,
        original_producer_directory_absent=True, original_producer_interpreter_absent=True,
        original_complete_and_partial_results_unchanged=True, new_actions=0, new_observations=0))
