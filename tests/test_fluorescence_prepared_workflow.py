"""Prepared fluorescence reaches scientific and annotation parents unchanged.

Run only with the existing bounded529 runner and591's installed native closure.
The FCS values and supplied FACS-format report are synthetic fixtures. Native
preparation, custody, calculation, delivery and terminal proofs are not stubbed.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3

from fluorescence_flowio_test_support import require_bounded_runtime

require_bounded_runtime()

import pytest

from gene_annotation_episode import fluorescence_event_contracts as core
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.fluorescence_execution_common import canonical as control_canonical
from gene_annotation_episode.numerical import NumericBand
from gene_annotation_episode.state import Store

import fluorescence_workflow_support as F
import fluorescence_prepared_workflow_support as P


def deny(*args, **kwargs):
    raise AssertionError('saved calculation or closed replay attempted producer work, parsing, acquisition, or network')


def receipts(store):
    return [json.loads(row['result'])['result'] for row in store.db.execute(
        "SELECT result FROM runtime_actions WHERE result IS NOT NULL AND "
        "json_extract(result,'$.result.version')='native_fluorescence_acquired_result_v1' ORDER BY rowid")]


def retained_result(store, receipt):
    return {role: dict(file=deepcopy(file), raw=store.get_artifact(file['artifact_ref']),
        value=json.loads(store.get_artifact(file['artifact_ref'])))
        for role, file in receipt['qualified_files'].items() if file is not None}


def episode_rows(store, episode_id):
    return {table: [row for row in F.rows(store, table) if row.get('episode_id') == episode_id]
        for table in ('runtime_episodes', 'runtime_actions', 'runtime_observations',
            'runtime_forms', 'runtime_estimation_contexts')}


@pytest.fixture(scope='module', params=P.OPERATIONS, ids=['facs-prepared', 'cytokine-prepared'])
def prepared_case(tmp_path_factory, request):
    directory = tmp_path_factory.mktemp('fluorescence-prepared595-' + request.param)
    evidence = dict(removed=[], saved_dispatches=[], saved_lifecycle_accesses=[])
    patch = pytest.MonkeyPatch()

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
        evidence['original_closed_rows'] = episode_rows(case.store, original['intent']['episode_id'])
        evidence['original_observations'] = F.rows(case.store, 'runtime_observations')
        evidence['original_actions'] = [row for row in F.rows(case.store, 'runtime_actions') if row['result'] is not None]
        evidence['native_plan_raw'] = (Path(case.provider.target['execution_id']).parent / 'fluorescence-plan.json').read_bytes()
        # Explicit failure injection after authenticated native writer closure
        # and the first complete delivery. Other domains and the report survive.
        spec = next(row for row in case.provider.plan['outputs'] if row['role'] == 'prepared_data:1')
        missing = Path(case.provider.plan['attempt_directory']) / spec['relative_path']
        assert missing.read_bytes() == case.provider.native_bytes['prepared_data:1']
        remove(missing, 'closed_writer_compensated_data')
        evidence['missing_compensated_data'] = str(missing)

    def before_saved(case):
        original, partial = receipts(case.store)
        assert original == evidence['original_receipt'] and not partial['delivery_complete']
        assert partial['worker_capture']['result']['native_outcome'] == 'partial'
        evidence['partial_receipt'] = deepcopy(partial)
        evidence['partial_result'] = retained_result(case.store, partial)
        evidence['partial_closed_rows'] = episode_rows(case.store, partial['intent']['episode_id'])
        evidence['observations_before_saved'] = F.rows(case.store, 'runtime_observations')
        evidence['actions_before_saved'] = [row for row in F.rows(case.store, 'runtime_actions') if row['result'] is not None]
        sheet_file, = case.partial_return['saved']
        evidence['saved_sheet_file'] = deepcopy(sheet_file)
        evidence['saved_sheet_raw'] = case.store.get_artifact(sheet_file['artifact_ref'])
        evidence['origins'] = case.owner.native_fluorescence_returns.authenticate_received_saved_sheet(
            case.science_context, sheet_file)

        # Keep the actually received partial sheet and durable control receipts.
        # The selected producer's private interpreter/modules are withdrawn;
        # the bounded runner's shared stdlib remains available to the pure worker.
        for receipt in (original, partial):
            for row in receipt['capture']['files']:
                if row['retained'] is not None:
                    remove(P.artifact_path(case.store, row['retained']['file']), 'captured_native_scientific_bytes')
            for role in ('sheet', 'calculations', 'projection', 'context'):
                file = receipt['qualified_files'][role]
                if file is not None and file != sheet_file:
                    remove(P.artifact_path(case.store, file), 'retained_numerical_bytes')
        for file, path in P.selected_inputs(case.job):
            assert path == str(P.artifact_path(case.store, file))
            remove(path, 'original_supplied_artifact')
        for run in F.worker_runs(directory):
            for name in ('sheet.json', 'calculations.json', 'projection.json', 'context.json'):
                remove(Path(run['directory']) / name, 'original_worker_numerical_copy')
        native_directory = Path(case.provider.target['execution_id']).parent
        evidence['withdrawn_producer_directory'] = str(native_directory)
        for path in sorted(native_directory.rglob('*')):
            if path.is_file():
                remove(path, 'original_producer_directory')
        shutil.rmtree(native_directory)
        for folder in (directory / 'supplied', directory / 'original-software'):
            for path in sorted(folder.rglob('*')):
                if path.is_file():
                    remove(path, 'original_supplied_or_software_copy')
            shutil.rmtree(folder)
        assert not native_directory.exists() and not Path(case.software['python']['path']).exists()
        assert P.artifact_path(case.store, sheet_file).read_bytes() == evidence['saved_sheet_raw']

        from gene_annotation_episode import native_lifecycle
        prepare = native_lifecycle.prepare_job

        def saved_worker_only(command, **kwargs):
            assert command[1:5] == ['-B', '-S', '-m', 'gene_annotation_episode.fluorescence_result_worker']
            plan = json.loads(Path(command[-1]).read_bytes())
            assert plan['mode'] == 'saved_sheet_recalculation'
            assert plan['selector']['saved_sheet_file'] == sheet_file
            assert 'original_plan' not in plan and 'capture' not in plan
            assert kwargs['policy'].to_dict() == P.POLICY
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
        for module, names in (
            ('fluorescence_event_preparation', ('prepare_fcs_scaling', 'prepare_spill_compensation')),
            ('fluorescence_event_readers', ('parse_fluorescence_csv', 'parse_fluorescence_table_snapshot')),
            ('fluorescence_fcs_reader', ('parse_fluorescence_fcs', 'decode_selected_fcs')),
            ('fluorescence_native_reports', ('parse_fluorescence_native_reports',)),
            ('native_fluorescence_driver', ('run_fluorescence_driver',)),
        ):
            for name in names:
                patch.setattr('gene_annotation_episode.' + module + '.' + name, deny)
        patch.setattr('gene_annotation_episode.native_fluorescence_results.capture_fluorescence_native_files', deny)
        patch.setattr(type(case.owner.job_progress_provider.targets), 'observe_target', deny)
        patch.setattr('socket.create_connection', deny)
        patch.setattr('socket.socket.connect', deny)
        patch.setattr('socket.socket.connect_ex', deny)

    try:
        case = P.workflow_case(directory, operation=request.param,
            before_partial=before_partial, before_saved=before_saved)
        case.evidence = evidence
        evidence['saved_result'] = retained_result(case.store, case.outcomes[2]['result'])
        F.write(directory / 'WITHDRAWAL_AND_REPLAY_INPUTS.json', {key: value for key, value in evidence.items()
            if key not in {'original_result', 'partial_result', 'saved_result', 'saved_sheet_raw', 'native_plan_raw'}})
    finally:
        patch.undo()
    try:
        yield case
    finally:
        case.store.close()


def test_real_v2_resource_custody_and_shared_cells_reach_both_parents(prepared_case):
    case = prepared_case
    assert {role: len(group) for role, group in case.by_role.items()} == {
        'annotation': 1, 'scientific_process': 1, 'launch': 1, 'launch_local': 1, 'results': 3}
    assert case.job['operation'] not in case.tools.catalog()
    information, = plain(case.scientific_context.assignment)['selection']['child_tool_info']
    assert information['name'] == case.job['operation'] and information['resources'] == 'local'
    assert information['description'] and information['instructions']
    selected = case.provider.plan['requested_job']['native_fluorescence']
    assert selected == case.job and selected['version'] == 'native_fluorescence_job_v2'
    assert case.provider.plan['policy'] == P.POLICY
    bindings = case.configuration['factory']['resources']['here']['native_fluorescence']
    assert {row['operation'] for row in bindings} == set(P.OPERATIONS)
    for binding in bindings:
        assert binding['version'] == 'native_fluorescence_binding_v2'
        assert binding['parsers'] == ['fcs_encoded']
        assert binding['preparation_methods'] == [P.SCALE, P.COMPENSATE]
        assert binding['report_profiles'] == [P.FACS] and binding['software'] == case.software
    distributions = {row['name'].lower(): row['version'] for row in case.software['distributions']}
    assert distributions['flowio'] == '1.4.0' and distributions['flowutils'] == '1.2.2'
    assert distributions['numpy'] and case.software['runtime_files'] and case.software['implementation_files']
    native = json.loads((case.directory / 'native-lifecycle.json').read_bytes())
    assert native['returncode'] == 0 and native['metadata']['verified_cgroup'] == F.LIMITS
    assert case.configuration['initial_refs'] == list(dict.fromkeys([
        *case.scope['subject_refs'], *[file['artifact_ref'] for file in case.supplied]]))
    assert {row['reference'] for row in case.launch['immutable_input_versions']} == {
        file['artifact_ref'] for file, _ in P.selected_inputs(case.job)}
    ledger = EpisodeReceipts(case.store, F.RUN_ID)
    baseline = set(ledger.known(case.root_context.episode_id, baseline=True))
    target_artifact_ref = P.assert_initial_input_custody(baseline,
        case.configuration['initial_refs'], case.target_record_refs, case.supplied)
    assert {case.store.get(ref)['sequence_ref'] for ref in case.scope['subject_refs']} == {target_artifact_ref}
    assert case.store.get_artifact(target_artifact_ref) == P.TARGET_SEQUENCE.encode('utf-8')

    result = case.evidence['original_result']
    sheet, components = result['sheet']['value'], result['calculations']['value']
    assert sheet['schema'] == core.SHEET_SCHEMA and components['schema'] == core.COMPONENTS_SCHEMA
    assert components['sheet_sha256'] == core.digest(sheet)
    first = case.returned[0]
    assert first['completed'] and first['failures'] == []
    assert [row['value'] for row in first['measurements'][0]['rows']] == pytest.approx(
        [2, 2, 1, 100, 130, 65, 50, 1.5, 100, 0], abs=1e-12)
    assert first['measurements'] == [result['projection']['value']]
    assert first['contexts'] == [result['context']['value']]
    assert all(row in components['cells'] for row in first['measurements'][0]['rows'])
    expected = {field: [form[field][0] for form in case.returned] for field in ('measurements', 'contexts')}
    assert case.forwarded == expected
    assert case.owner.native_fluorescence_returns.received_facts(case.root_context, case.parent_form) == {
        F.PROJECTION_SOURCE: expected['measurements'], F.CONTEXT_SOURCE: expected['contexts']}
    F.write(case.directory / 'NUMERICAL_EXAMPLE.json', dict(fixture='synthetic supplied FCS and source-format FACS report',
        input_rows=P.INPUT_ROWS, expected_scaled_rows=[[110, 60, 1], [20, 100, 2]],
        expected_compensated_ab=[[100, 50], [0, 100]], retained_event_count=2,
        returned=case.returned, forwarded=case.forwarded))


def test_native_domains_event_identity_residue_and_report_provenance(prepared_case):
    case = prepared_case
    batches = [json.loads(case.provider.native_bytes[role])
        for role in ('event_batch:0', 'prepared_batch:0', 'prepared_batch:1')]
    parsed = [batch['parse'] for batch in batches]
    values = [[[cell['measurement']['value'] for cell in event['values']] for event in batch['events']]
        for batch in parsed]
    assert values[0] == [list(row) for row in P.INPUT_ROWS]
    assert values[1] == [[110, 60, 1], [20, 100, 2]]
    for actual, expected in zip(values[2], ([100, 50, 1], [0, 100, 2])):
        assert actual == pytest.approx(expected, abs=1e-12)
    assert -1e-12 < values[2][1][0] < 0, 'the actual native negative residue must not be clipped'
    assert [batch['domain']['key'] for batch in parsed] == ['domain-0', 'scaled', 'compensated']
    assert [batch['domain']['parent_domain_key'] for batch in parsed] == [None, 'domain-0', 'scaled']
    for batch in parsed:
        assert [row['event_ordinal'] for row in batch['events']] == [0, 1]
        assert [row['source_ordinal'] for row in batch['events']] == [0, 1]
        assert batch['sample']['key'] == 'sample-0'
    for batch in parsed[1:]:
        assert batch['domain']['correspondence'] == [dict(source_ordinal=i, event_ordinal=i) for i in range(2)]
        assert batch['channels'][2]['unit'] == 'seconds'
        assert all(cell['measurement']['state'] == 'derived'
            for event in batch['events'] for cell in event['values'])
    assert all(cell['measurement']['state'] == 'supplied_predicted'
        for event in parsed[0]['events'] for cell in event['values'])
    sheet = case.evidence['original_result']['sheet']['value']
    assert len(sheet['samples']) == 1 and len(sheet['events']) == 6
    assert sheet['gate_definitions'] == case.job['definitions']['gates']
    assert sheet['population_definitions'] == case.job['definitions']['populations']
    assert {row['sample_key'] for row in sheet['events']} == {'sample-0'}
    report = json.loads(case.provider.native_bytes['report_batch:0'])
    assert report['parse']['provenance']['artifact_origin'] == 'received_supplied'
    assert report['parse']['provenance']['producer_execution'] == 'unverified'
    assert report['report_file'] == case.job['report_inputs'][0]['file']
    assert report['association_file'] == case.job['report_inputs'][0]['association_file']
    assert sheet['native_reports'][0]['value'] == 100
    for role in ('event_batch:0', 'preparation_parameters:0', 'prepared_data:0', 'prepared_batch:0',
            'preparation_parameters:1', 'prepared_data:1', 'prepared_batch:1', 'report_batch:0'):
        raw = case.provider.native_bytes[role]
        assert raw == core.canonical(json.loads(raw)) + b'\n'
    manifest = case.provider.native_bytes['manifest']
    assert manifest == control_canonical(json.loads(manifest)) + b'\n'
    assert case.evidence['native_plan_raw'] == control_canonical(case.provider.plan) + b'\n'
    for label in ('original_result', 'partial_result', 'saved_result'):
        for role in ('sheet', 'calculations', 'projection', 'context'):
            item = case.evidence[label][role]
            assert item['raw'] == core.canonical(item['value']) + b'\n'
            assert item['file']['sha256'] == hashlib.sha256(item['raw']).hexdigest()
            assert item['file']['size_bytes'] == len(item['raw'])


def test_missing_compensated_data_preserves_independent_values_and_closed_history(prepared_case):
    case, evidence = prepared_case, prepared_case.evidence
    original, partial, saved = [row['result'] for row in case.outcomes]
    assert original == evidence['original_receipt'] and case.returned[0] == evidence['original_return']
    assert original['delivery_complete'] and original['worker_capture']['result']['native_outcome'] == 'complete'
    assert not partial['delivery_complete'] and partial['worker_capture']['result']['native_outcome'] == 'partial'
    assert not partial['worker_capture']['result']['analysis_complete']
    assert any(row['code'] == 'capture_file_unavailable' and row['role'] == 'prepared_data:1'
        and row['input_index'] == 1 for row in case.returned[1]['failures'])
    rows = case.returned[1]['measurements'][0]['rows']
    assert [row['value'] for row in rows] == [2, 2, 1, 100, 130, 65, None, 1.5, 100, 0]
    assert rows[6]['state'] == 'unavailable' and rows[6]['request']['domain_key'] == 'compensated'
    sheet = evidence['partial_result']['sheet']['value']
    assert {row['key']: row['extent'] for row in sheet['input_sources']} == {
        'source-0': 'complete', 'scaled.source': 'complete', 'compensated.source': 'unavailable',
        'native.report': 'complete'}
    assert [row['state'] for row in sheet['measurement_domains']] == ['available', 'available', 'unavailable']
    assert sheet['measurement_domains'][2]['parent_domain_key'] == 'scaled'
    assert len(sheet['events']) == 4 and len(sheet['samples']) == 1
    assert sheet['gate_definitions'] == case.job['definitions']['gates']
    assert all(row in F.rows(case.store, 'runtime_observations') for row in evidence['original_observations'])
    assert all(row in F.rows(case.store, 'runtime_actions') for row in evidence['original_actions'])
    assert episode_rows(case.store, original['intent']['episode_id']) == evidence['original_closed_rows']
    assert episode_rows(case.store, partial['intent']['episode_id']) == evidence['partial_closed_rows']
    assert saved['delivery_complete'] and case.returned[2]['completed']
    assert evidence['partial_result']['sheet']['raw'] == evidence['saved_result']['sheet']['raw']


def test_saved_recalculation_has_no_original_execution_or_unrequested_authority(prepared_case):
    case, evidence = prepared_case, prepared_case.evidence
    original, partial, saved = [row['result'] for row in case.outcomes]
    assert original['acquired_population'] == partial['acquired_population'] is not None
    assert saved['acquired_population'] is None and len(evidence['saved_dispatches']) == 1
    assert all(saved[key] is None for key in ('observation', 'native', 'capture', 'source_action_file', 'writer_closure_file'))
    assert not Path(evidence['withdrawn_producer_directory']).exists()
    assert not Path(case.software['python']['path']).exists()
    assert all(not Path(path).exists() for _, path in P.selected_inputs(case.job))
    assert not (case.directory / 'supplied').exists()
    assert case.returned[1]['saved'] == case.returned[2]['saved'] == [evidence['saved_sheet_file']]
    assert case.store.get_artifact(evidence['saved_sheet_file']['artifact_ref']) == evidence['saved_sheet_raw']
    assert saved['worker_capture']['result']['native_outcome'] == 'not_applicable'
    assert not saved['worker_capture']['result']['original_events_acquired']
    assert saved['worker_capture']['result']['analysis_complete']
    view = case.returned[2]['measurements'][0]
    assert view['selection'] == P.selector(saved=evidence['saved_sheet_file'])['selection']
    assert (view['total_selected_rows'], view['returned_row_count'], view['has_more']) == (10, 4, True)
    assert [row['value'] for row in view['rows']] == [1, 100, 130, 65]
    assert all(row['population']['denominator'] == 'evaluable' for row in view['rows']
        if row['request']['kind'] == 'fraction')
    assert all(row in evidence['saved_result']['calculations']['value']['cells'] for row in view['rows'])
    context = case.returned[2]['contexts'][0]
    assert [row['key'] for row in context['domains']] == ['domain-0', 'scaled']
    assert [row['key'] for row in context['channels']] == ['raw.c0', 'scaled.c0']
    for form in case.returned:
        projected = form['contexts'][0]
        assert projected['context_fields'] == P.CONTEXT_FIELDS
        assert not projected['sources'] and not projected['control_pairs'] and not projected['native_reports']
        assert 'events' not in projected
        assert all('event_ordinals' not in row for row in projected['populations'])
        assert all('correspondence' not in row for row in projected['domains'])
    file = evidence['saved_sheet_file']
    assert case.owner.resolve_received_reference(case.scientific_context, file['artifact_ref'], 'artifact') is True
    assert case.owner.resolve_received_reference(case.root_context, file['artifact_ref'], 'artifact') is False
    with pytest.raises(ValueError, match='saved_sheet_not_received'):
        case.owner.native_fluorescence_returns.authenticate_received_saved_sheet(case.root_context, file)
    for receipt in (original, partial, saved):
        for role in ('calculations', 'projection', 'context'):
            ref = receipt['qualified_files'][role]['artifact_ref']
            assert case.owner.resolve_received_reference(case.root_context, ref, 'artifact') is False
    for row in original['capture']['files']:
        if row['role'].startswith(('event_batch:', 'prepared_data:', 'prepared_batch:', 'report_batch:')):
            ref = row['retained']['file']['artifact_ref']
            assert case.owner.resolve_received_reference(case.root_context, ref, 'artifact') is False
            assert case.owner.resolve_received_reference(case.scientific_context, ref, 'artifact') is False
    assert all(row in F.rows(case.store, 'runtime_observations') for row in evidence['observations_before_saved'])
    assert all(row in F.rows(case.store, 'runtime_actions') for row in evidence['actions_before_saved'])
    runs = F.worker_runs(case.directory)
    assert sorted(row['plan']['mode'] for row in runs) == ['native_result', 'native_result', 'saved_sheet_recalculation']
    for run in runs:
        execution = json.loads((Path(run['directory']) / 'execution.json').read_bytes())
        assert execution['returncode'] == 0 and execution['terminal'] and execution['quiescent']
        assert execution['metadata']['verified_cgroup'] == F.LIMITS
        assert execution['intent']['dependencies'] == []
        assert not {'fluorescence_event_preparation.py', 'fluorescence_preparation_readers.py',
            'fluorescence_event_readers.py', 'fluorescence_fcs_reader.py', 'fluorescence_native_reports.py',
            'native_fluorescence_driver.py', 'native_fluorescence_prepared_driver.py'} & {
                Path(pin['path']).name for pin in execution['intent']['source_pins']}


def test_observations_credit_and_practical_terminal_zero_are_unchanged(prepared_case):
    case = prepared_case
    for record in case.records:
        context = case.contexts[record['episode_id']]
        actions = [row for row in F.rows(case.store, 'runtime_actions') if row['episode_id'] == context.episode_id]
        observations = [row for row in F.rows(case.store, 'runtime_observations') if row['episode_id'] == context.episode_id]
        assert len(actions) == len(observations) == record['units_consumed']
        assert case.provider.turns[context.episode_id] == len(actions)
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
    assert len(F.rows(case.store, 'runtime_observations')) == 10
    assert len(F.rows(case.store, 'runtime_actions')) == 10


def test_closed_workflow_and_returns_replay_after_numerical_payload_withdrawal(prepared_case, monkeypatch):
    case = prepared_case
    removed = []
    for outcome in case.outcomes:
        result = outcome['result']
        for role in ('sheet', 'calculations', 'projection', 'context'):
            file = result['qualified_files'][role]
            path = P.artifact_path(case.store, file)
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
    monkeypatch.setattr('gene_annotation_episode.fluorescence_event_calculations.calculate_fluorescence_sheet', deny)
    monkeypatch.setattr('gene_annotation_episode.fluorescence_result_worker.calculate_fluorescence_sheet', deny)
    monkeypatch.setattr('gene_annotation_episode.fluorescence_result_worker.execute_fluorescence_worker', deny)
    monkeypatch.setattr(type(case.owner.job_progress_provider.targets), 'observe_target', deny)
    monkeypatch.setattr('socket.create_connection', deny)
    monkeypatch.setattr('socket.socket.connect', deny)
    monkeypatch.setattr('socket.socket.connect_ex', deny)

    class NoNewDecisions:
        async def complete(self, *args, **kwargs):
            raise AssertionError('closed Workflow requested a new decision')

        async def release(self, episode_id):
            pass

    archive_before = {str(path.relative_to(case.directory / 'run/archive')): path.read_bytes()
        for path in sorted((case.directory / 'run/archive').rglob('*')) if path.is_file()}
    assert archive_before
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
        assert {str(path.relative_to(case.directory / 'run/archive')): path.read_bytes()
            for path in sorted((case.directory / 'run/archive').rglob('*')) if path.is_file()} == archive_before
    F.write(case.directory / 'CLOSED_REPLAY.json', dict(removed_numerical_artifacts=removed,
        original_producer_directory_absent=True, original_producer_interpreter_absent=True,
        original_complete_and_partial_results_unchanged=True, archives_unchanged=True,
        new_actions=0, new_observations=0, new_model_calls=0))


def test_initial_input_custody_from_closed_saved_case():
    """Recheck the original failed baseline without invoking prepared_case.

    Root supplies a closed case copied into this bounded attempt's snapshot.
    All declarations come from its pre-action contexts; the receipt set comes
    from its original read-only database. No Workflow or native job is rerun.
    """
    selected = os.environ.get('HMMER_NATIVE_ORACLE_FLUORESCENCE_SAVED_CASE')
    if selected is None:
        pytest.skip('select the original closed prepared case for the saved custody check')
    attempt = require_bounded_runtime()
    directory = Path(selected).resolve(strict=True)
    assert directory.is_relative_to(attempt / 'source_snapshot')
    configuration = json.loads((directory / 'fixture-configuration.json').read_bytes())
    saved_case = json.loads((directory / 'CASE.json').read_bytes())
    first = json.loads((directory / 'decision-0.json').read_bytes())
    scientific = json.loads((directory / 'decision-1.json').read_bytes())
    archive = saved_case['archive']
    assert first['episode_id'] == archive['episode_id']
    assert not first['context']['child_reports'] and not scientific['context']['child_reports']
    assignment = scientific['context']['scientific_process']['assignment']
    declared = assignment['context']
    assert declared['supplied_sequence'] == P.TARGET_SEQUENCE and declared['molecule'] == 'dna'
    assert assignment['evidence_refs'] == configuration['scope']['subject_refs']
    supplied = declared['supplied_fluorescence_files']
    assert configuration['initial_refs'] == list(dict.fromkeys([
        *assignment['evidence_refs'], *[file['artifact_ref'] for file in supplied]]))

    # These five records describe the declared ordinary target before any
    # selected work. Do not infer allowed artifacts from later state/receipts.
    state = first['context']['working_state']
    subject, = state['subjects']
    source, = state['sources']
    material, = state['materials']
    collection, = state['collections']
    parse, = state['parse_attempts']
    assert configuration['scope']['subject_refs'] == [subject['id']]
    assert subject['source_ref'] == material['source_ref'] == collection['source_ref'] == parse['source_ref'] == source['id']
    assert subject['source_record']['material_ref'] == collection['material_ref'] == parse['material_ref'] == material['id']
    assert parse['collection_ref'] == collection['id']
    assert source['origin'] == source['provider'] == subject['origin'] == 'caller'
    assert material['use'] == 'target' and material['requested_format'] == 'raw'
    target_record_refs = {row['id'] for row in (subject, source, material, collection, parse)}
    target_bytes = P.TARGET_SEQUENCE.encode('utf-8')
    target_sha256 = hashlib.sha256(target_bytes).hexdigest()
    target_artifact_ref = 'artifact_' + target_sha256
    assert subject['sequence_ref'] == source['artifact_ref'] == source['text_ref'] == target_artifact_ref
    assert (subject['molecule'], subject['unit'], subject['length']) == ('dna', 'nt', len(target_bytes))
    assert (directory / 'state/artifacts' / target_sha256[:2] / target_sha256).read_bytes() == target_bytes

    database = directory / 'state/state.sqlite3'
    wal = database.with_name(database.name + '-wal')
    assert not wal.exists() or wal.stat().st_size == 0, 'copy the closed, checkpointed original case'
    database_before = hashlib.sha256(database.read_bytes()).hexdigest()
    with sqlite3.connect(database.as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        db.row_factory = sqlite3.Row
        run_id, root_id = archive['run_id'], archive['episode_id']
        inheritance = EpisodeReceipts.read_manifest(db, run_id, root_id)
        assert inheritance == archive['request']['message']['knowledge_inheritance']
        assert inheritance['parent_episode_id'] is None and inheritance['through_receipt_index'] is None
        root = db.execute('SELECT request,state FROM runtime_episodes WHERE episode_id=?', (root_id,)).fetchone()
        assert root['state'] == 'yielded' and json.loads(root['request']) == archive['request']
        # With no inherited parent, this is precisely the root's original
        # initial subset selected by EpisodeReceipts.known(baseline=True).
        baseline = {row[0] for row in db.execute('SELECT record_ref FROM runtime_record_receipts '
            'WHERE run_id=? AND episode_id=? AND receipt_kind=?', (run_id, root_id, 'initial'))}
        metadata = dict(db.execute('SELECT * FROM artifacts WHERE id=?', (target_artifact_ref,)).fetchone())
        assert metadata == dict(id=target_artifact_ref, sha256=target_sha256,
            media_type='application/octet-stream', size=len(target_bytes))
    assert hashlib.sha256(database.read_bytes()).hexdigest() == database_before
    old_allowed = target_record_refs | {file['artifact_ref'] for file in supplied}
    assert baseline - old_allowed == {target_artifact_ref}
    assert P.assert_initial_input_custody(baseline, configuration['initial_refs'],
        target_record_refs, supplied) == target_artifact_ref

    withdrawal = json.loads((directory / 'WITHDRAWAL_AND_REPLAY_INPUTS.json').read_bytes())
    unrequested = withdrawal['original_receipt']['qualified_files']['sheet']['artifact_ref']
    assert unrequested not in old_allowed | {target_artifact_ref}
    with pytest.raises(AssertionError):
        P.assert_initial_input_custody(baseline | {unrequested}, configuration['initial_refs'],
            target_record_refs, supplied)
    F.write(attempt / 'temporary' / 'SAVED_INITIAL_CUSTODY_602.json', dict(
        original_case=str(directory), operation=saved_case['operation'], root_episode_id=root_id,
        original_baseline=sorted(baseline), original_assertion_extra=[target_artifact_ref],
        allowed_target_records=sorted(target_record_refs), supplied_files=supplied,
        target_artifact=metadata, target_utf8=P.TARGET_SEQUENCE,
        rejected_unrequested_sheet=unrequested, database_sha256=database_before,
        corrected_assertion_passed=True, database_unchanged=True,
        new_workflow_runs=0, new_native_jobs=0, new_actions=0, new_observations=0))
