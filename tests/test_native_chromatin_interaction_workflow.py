"""011 full Workflow verification; scripted decisions and genuine synthetic Cooler.

Execute only through451/run_bounded.py. Positive result authority is generated
by actual production commissions/actions/receipts/returns, never fixture rows.
"""
import asyncio
from copy import deepcopy
import hashlib
from importlib import import_module
from io import BytesIO
import json
import os
from pathlib import Path

import pytest
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.numerical import NumericBand
from gene_annotation_episode.state import Store

F = import_module('verification.tool_graders_chromatin_workflow_2026-10-27_451.fixture_helpers')


def deny(*args, **kwargs):
    raise AssertionError('received-only saved calculation or closed replay attempted native work, acquisition, or network')


def worker_output(run, role):
    captured, = [r for r in run['capture']['outputs'] if r['role'] == role]
    assert captured['capture']['outcome'] == 'verified', captured
    return captured['capture']['observed']


def contained_versions(value):
    if isinstance(value, dict):
        if isinstance(value.get('version'), str):
            yield value['version']
        for item in value.values():
            yield from contained_versions(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from contained_versions(item)


def assert_pairs(rows, *, threshold):
    assert [r['promoter_element_key'] for r in rows] == ['P', 'Q']
    p, q = [r.get('fields', r.get('measurements')) for r in rows]
    assert [p[k]['value'] for k in ('raw_contact', 'expected_contact', 'fold_enrichment')] == [6, 4, 1.5]
    assert p['expected_contact']['numerator'] == 8 and p['expected_contact']['denominator'] == 2
    assert p['fold_enrichment']['numerator'] == 6 and p['fold_enrichment']['denominator'] == 4
    assert p['above_fold_threshold']['value'] is threshold
    assert [q[k]['value'] for k in ('raw_contact', 'expected_contact', 'fold_enrichment')] == [0, 0, None]
    assert q['raw_contact']['state'] == 'observed'
    assert q['expected_contact']['numerator'] == 0 and q['expected_contact']['denominator'] == 1
    assert q['fold_enrichment']['reason'] == 'zero_denominator'
    assert q['above_fold_threshold']['value'] is None
    for row in rows:
        assert row['enhancer_element_key'] == 'E'
        assert row['qualifications']['data_extent'] == 'complete'


@pytest.fixture(scope='module')
def software():
    from gene_annotation_episode.native_chromatin_interaction_preparation import freeze_chromatin_software_binding
    import gene_annotation_episode.native_chromatin_interaction_driver as driver
    return freeze_chromatin_software_binding(module_root=str(Path(driver.__file__).parents[1]),
        snapshot_directory=str(Path(os.environ['WORKFLOW451_ATTEMPT']) / 'native_software'),
        python_executable=os.sys.executable)


@pytest.fixture(scope='module')
def connected_case(tmp_path_factory, software):
    directory = tmp_path_factory.mktemp('chromatin451')
    evidence, patch = {}, pytest.MonkeyPatch()

    def before_saved(case):
        original, = F.worker_runs(directory)
        assert original['plan']['mode'] == 'native_result'
        evidence['original_worker'] = original
        evidence['bundle'] = deepcopy(case.bundle)
        evidence['sheet_bytes'] = case.store.get_artifact(case.bundle['sheet']['artifact_ref'])
        evidence['table_bytes'] = [case.store.get_artifact(f['artifact_ref']) for f in case.bundle['tables']]
        evidence['components_file'] = worker_output(original, 'components')
        evidence['components_bytes'] = case.store.get_artifact(evidence['components_file']['artifact_ref'])
        evidence['observations'] = F.rows(case.store, 'runtime_observations')
        evidence['completed_actions'] = [row for row in F.rows(case.store, 'runtime_actions') if row['result'] is not None]
        evidence['native_plans'] = {str(p): p.read_bytes() for p in case.workspace.rglob('chromatin-plan.json')}
        evidence['origins_before_saved'] = case.owner.native_chromatin_interaction_returns.authenticate_received_saved_bundle(
            case.science_context, case.bundle)
        preserved = {f['artifact_ref'] for f in (case.bundle['sheet'], *case.bundle['tables'])}
        removed = []

        def remove(path, kind):
            if path.is_file():
                raw = path.read_bytes()
                path.unlink()
                removed.append({'kind': kind, 'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})

        science_roles = {'original_contact', 'original_elements', 'original_metadata',
            'bins', 'contacts', 'weights', 'cell_states', 'dense_values'}
        for spec in case.provider.plan['outputs']:
            if spec['role'] not in science_roles:
                continue
            remove(Path(case.provider.plan['attempt_directory']) / spec['relative_path'], 'native_producer_scientific_copy')
            raw = case.provider.native_bytes.get(spec['file_key'])
            if raw is not None:
                sha = hashlib.sha256(raw).hexdigest()
                if 'artifact_' + sha not in preserved:
                    remove(case.store.path / 'artifacts' / sha[:2] / sha, 'retained_original_native_bytes')
        for item in case.provider.plan['requested_job']['native_chromatin_interactions']['input_bindings']:
            remove(Path(item['path']), 'original_caller_input')
        for row in original['capture']['outputs']:
            if row['role'] in {'sheet', 'components', 'projection', 'table'}:
                remove(Path(original['directory']) / row['capture']['declared']['relative_path'], 'original_worker_scientific_copy')
        assert removed and all(not Path(row['path']).exists() for row in removed)
        evidence['removed'], evidence['dispatches'] = removed, []
        from gene_annotation_episode import native_lifecycle
        actual_prepare = native_lifecycle.prepare_job

        def saved_worker_only(command, **kwargs):
            assert command[1:5] == ['-B', '-S', '-m', 'gene_annotation_episode.chromatin_interaction_result_worker']
            plan = json.loads(Path(command[-1]).read_bytes())
            assert plan['mode'] == 'saved_sheet_recalculation'
            assert set(plan) == {'version', 'mode', 'directory', 'sheet_bundle', 'selector'}
            assert plan['selector']['saved_sheet_bundle'] == case.bundle
            assert plan['sheet_bundle']['sheet']['file'] == case.bundle['sheet']
            assert [r['file'] for r in plan['sheet_bundle']['tables']] == case.bundle['tables']
            assert kwargs['policy'].to_dict() == F.POLICY
            evidence['dispatches'].append({'command': list(command), 'plan': deepcopy(plan)})
            return actual_prepare(command, **kwargs)

        patch.setattr(native_lifecycle, 'prepare_job', saved_worker_only)
        patch.setattr('gene_annotation_episode.native_chromatin_interaction_results.capture_chromatin_native_files', deny)
        patch.setattr(type(case.owner.job_progress_provider.targets), 'observe_target', deny)
        patch.setattr('h5py.File', deny)
        patch.setattr('socket.create_connection', deny)
        patch.setattr('socket.socket.connect', deny)
        patch.setattr('socket.socket.connect_ex', deny)

    try:
        case = F.workflow_case(directory, software, before_saved=before_saved)
        case.saved_evidence = evidence
        F.write(directory / 'SAVED_CHECK.json', {key: value for key, value in evidence.items()
            if key not in {'sheet_bytes', 'table_bytes', 'components_bytes', 'native_plans'}})
    finally:
        patch.undo()
    try:
        yield case
    finally:
        case.store.close()


def test_selected_tool_actual_local_native_and_exact_typed_return(connected_case):
    case, saved = connected_case, connected_case.saved_evidence
    assert {role: len(rows) for role, rows in case.by_role.items()} == {
        'annotation': 1, 'scientific_process': 1, 'launch': 1, 'launch_local': 1, 'results': 2}
    assert 'analyze_chromatin_interactions' not in case.tools.catalog()
    information, = plain(case.scientific_context.assignment)['selection']['child_tool_info']
    assert information['name'] == 'analyze_chromatin_interactions' and information['resources'] == 'local'
    assert information['description'] and information['instructions']
    assert case.provider.plan['requested_job']['native_chromatin_interactions'] == case.job
    assert case.provider.plan['policy'] == F.POLICY
    native = json.loads(case.provider.native_bytes['bundle'])
    assert [p['population_key'] for p in native['extraction']['populations']] == ['p0', 'p1']
    assert all(p['extent'] == 'complete' for p in native['extraction']['populations'])
    assert case.provider.native_bytes['p0.contacts'] == case.provider.native_bytes['p1.contacts']
    sheet = json.loads(saved['sheet_bytes'])
    components = json.loads(saved['components_bytes'])
    assert sheet['request'] == case.job['request']
    assert len(sheet['data_tables']) == 10
    assert saved['bundle']['tables'] == [d['file'] for d in sheet['data_tables'] if d['file'] is not None]
    assert len(saved['bundle']['tables']) == 6
    assert len({canonical(file) for file in saved['bundle']['tables']}) == 3
    assert saved['bundle']['tables'][:3] == saved['bundle']['tables'][3:]
    assert [p['population_key'] for p in components['contact']['populations']] == ['p0', 'p1']
    for population in components['contact']['populations']:
        assert_pairs(population['pairs'], threshold=False)
    first, second = [form['chromatin'][0] for form in case.returned]
    for projection, threshold in ((first, False), (second, True)):
        assert projection['population_keys'] == ['p1'] and projection['requested_fields'] == F.FIELDS
        assert {r['population_key'] for r in projection['rows']} == {'p1'}
        assert_pairs(projection['rows'], threshold=threshold)
        assert projection['page'] == {'offset': 0, 'returned_count': 2, 'total_row_count': 2, 'has_more': False}
    assert case.forwarded == {'chromatin': [first, second]}
    assert case.owner.native_chromatin_interaction_returns.facts(case.root_context, case.parent_form) == {
        F.PROJECTION_SOURCE: [first, second]}
    original = case.outcomes[0]['result']
    assert original['acquired_population'] == digest(case.provider.plan['identity'])
    assert [p['population_key'] for p in original['sheet_evidence']['populations']] == ['p0', 'p1']
    assert case.owner.native_chromatin_interaction_results.receipts.original_acquisition_complete(original)
    for call in case.provider.calls:
        if case.contexts[call['episode_id']].role in {'annotation', 'scientific_process'}:
            assert not {'chromatin_interaction_sheet_v1', 'chromatin_interaction_components_v1'}.intersection(
                contained_versions(call['context']))
    commissions = [json.loads(row['action']) for row in F.rows(case.store, 'runtime_actions')
        if json.loads(row['action'])['kind'] == 'episode_child']
    assert [sum(row['role'] == role for row in commissions) for role in
        ('scientific_process', 'launch', 'launch_local', 'results')] == [1, 1, 1, 2]
    for context, form in zip(case.result_contexts, case.returned):
        groups = case.owner.native_chromatin_interaction_results.own_fact_groups(context, verify_artifacts=False)
        assert form == {'chromatin': groups[F.PROJECTION_SOURCE], 'saved': groups[F.SAVED_SOURCE],
            'failures': groups[F.FAILURE_SOURCE], 'completed': True}


def test_received_bundle_recalculates_without_native_inputs_or_producer_copies(connected_case):
    case, saved = connected_case, connected_case.saved_evidence
    assert len(saved['dispatches']) == 1
    assert saved['dispatches'][0]['plan']['selector']['parameters']['contact']['fold_threshold'] == 1
    assert saved['origins_before_saved'] == ({'episode_id': case.result_contexts[0].episode_id,
        'operation_key': f'{F.RUN_ID}:{case.result_contexts[0].episode_id}:0'},)
    recalculated = case.outcomes[1]['result']
    assert recalculated['acquired_population'] is None and recalculated['observation'] is None and recalculated['capture'] is None
    assert case.returned[0]['saved'] == case.returned[1]['saved'] == [saved['bundle']]
    assert case.store.get_artifact(saved['bundle']['sheet']['artifact_ref']) == saved['sheet_bytes']
    assert [case.store.get_artifact(f['artifact_ref']) for f in saved['bundle']['tables']] == saved['table_bytes']
    assert all(not Path(row['path']).exists() for row in saved['removed'])
    assert {str(p): p.read_bytes() for p in case.workspace.rglob('chromatin-plan.json')} == saved['native_plans']
    assert sorted(r['plan']['mode'] for r in F.worker_runs(case.directory)) == ['native_result', 'saved_sheet_recalculation']
    old, new = [form['chromatin'][0]['rows'] for form in case.returned]
    for before, after in zip(old, new):
        assert {k: v for k, v in before['fields'].items() if k != 'above_fold_threshold'} == {
            k: v for k, v in after['fields'].items() if k != 'above_fold_threshold'}
    assert all(row in F.rows(case.store, 'runtime_observations') for row in saved['observations'])
    assert all(row in F.rows(case.store, 'runtime_actions') for row in saved['completed_actions'])


def test_projection_only_root_has_no_implicit_saved_bundle_authority(connected_case):
    case, bundle = connected_case, connected_case.saved_evidence['bundle']
    reader = case.owner.native_chromatin_interaction_returns
    assert reader.authenticate_received_saved_bundle(case.scientific_context, bundle) == tuple(
        {'episode_id': context.episode_id, 'operation_key': f'{F.RUN_ID}:{context.episode_id}:0'} for context in case.result_contexts)
    references = dict.fromkeys(file['artifact_ref'] for file in (bundle['sheet'], *bundle['tables']))
    for reference in references:
        assert reader.resolve_received(case.scientific_context, reference, 'artifact')
        assert not reader.resolve_received(case.root_context, reference, 'artifact')
        for namespace in ('artifact', None):
            assert case.owner.resolve_received_reference(case.scientific_context, reference, namespace) is True
            assert case.owner.resolve_received_reference(case.root_context, reference, namespace) is False
    with pytest.raises(ValueError, match='saved_bundle_not_received'):
        reader.authenticate_received_saved_bundle(case.root_context, bundle)
    facts = json.loads(case.flow.journal.row('runtime_forms', case.scientific_context.episode_id)['facts'])
    assert facts[F.PROJECTION_SOURCE] == case.forwarded['chromatin']
    assert len(facts['chromatin_received_report_prefix']['attempts']) == 2
    assert F.SAVED_SOURCE not in {r.get('x-source') for r in case.parent_form['properties'].values()}


def test_actual_action_counts_credit_and_immediate_zero_future_expectation(connected_case):
    case = connected_case
    for record in case.records:
        context = case.contexts[record['episode_id']]
        actions = [r for r in F.rows(case.store, 'runtime_actions') if r['episode_id'] == context.episode_id]
        observations = [r for r in F.rows(case.store, 'runtime_observations') if r['episode_id'] == context.episode_id]
        assert len(actions) == len(observations) == record['units_consumed'] == case.provider.turns[context.episode_id]
        if context.role in {'launch', 'launch_local', 'results'}:
            assert len(actions) == 1
            estimate = record['controller_state']['estimate']
            assert estimate['expected_next_gain'] == NumericBand.exact(0).as_record()
            assert estimate['provenance']['version'] == 'verified_practical_endpoint_yield_v1'
            proof = case.owner.completion_for_action(context, f'{F.RUN_ID}:{context.episode_id}:0')
            assert proof is not None and case.owner.verify_completion(context, proof)
    assert [F.history(row) for row in case.by_role['launch_local']] == [[7]]
    assert [F.history(row) for row in case.by_role['launch']] == [[3]]
    assert [F.history(row) for row in case.by_role['results']] == [[2], [0]]
    assert F.history(case.by_role['scientific_process'][0]) == [0, 0, 0]
    assert F.history(case.by_role['annotation'][0]) == [0]
    assert case.store.count('annotation') == 0


def test_closed_workflow_and_results_replay_without_new_decisions_or_work(connected_case, monkeypatch):
    case = connected_case
    for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect'):
        monkeypatch.setattr('gene_annotation_episode.native_lifecycle.' + name, deny)
    for name in ('capture_chromatin_native_files', 'prepare_chromatin_result_worker'):
        monkeypatch.setattr('gene_annotation_episode.native_chromatin_interaction_results.' + name, deny)
    monkeypatch.setattr(type(case.owner.job_progress_provider.targets), 'observe_target', deny)
    monkeypatch.setattr('h5py.File', deny)
    monkeypatch.setattr('socket.create_connection', deny)
    monkeypatch.setattr('socket.socket.connect', deny)
    monkeypatch.setattr('socket.socket.connect_ex', deny)

    class NoNewDecisions:
        async def complete(self, *args, **kwargs):
            raise AssertionError('closed Workflow replay requested a new decision')
        async def release(self, episode_id):
            pass

    with Store(case.directory / 'state') as store:
        before = {table: F.rows(store, table) for table in F.TABLES}
        retained = {str(p): p.read_bytes() for p in (case.directory / 'run').rglob('*.json')}
        flow, _ = F.assemble(store, case.directory, NoNewDecisions(), case.configuration)
        owner = flow.episode_bindings.for_role('results')
        proofs = []
        for original_context, original_outcome in zip(case.result_contexts, case.outcomes):
            context = owner.native_chromatin_interaction_returns.context(original_context.episode_id)
            key = f'{F.RUN_ID}:{context.episode_id}:0'
            proof = owner.completion_for_action(context, key)
            replay = asyncio.run(owner.execute(context, 'execution.results.collect', {}, key))
            assert replay == {k: v for k, v in original_outcome.items() if k != 'pending_work_after_action'}
            assert owner.completion_for_action(context, key) == proof and owner.verify_completion(context, proof)
            proofs.append(proof)
        _, _, archive = asyncio.run(F.run_root(flow, case.configuration))
        assert archive == case.archive
        assert {table: F.rows(store, table) for table in F.TABLES} == before
        assert {str(p): p.read_bytes() for p in (case.directory / 'run').rglob('*.json')} == retained
        assert all(not Path(row['path']).exists() for row in case.saved_evidence['removed'])
        F.write(case.directory / 'REPLAY_CHECK.json', {'reopened_store': True, 'new_decisions': 0,
            'new_native_or_calculation_workers': 0, 'unchanged_tables': list(F.TABLES),
            'unchanged_archive': True, 'original_completion_proofs': proofs})


def test_actual_missing_p1_contacts_preserves_p0_partial_and_one_job_credit(tmp_path, software):
    case = F.workflow_case(tmp_path / 'missing_p1_contacts', software, partial=True)
    try:
        returned, = case.returned
        projection, = returned['chromatin']
        assert not returned['completed'] and returned['failures']
        assert projection['population_keys'] == ['p0', 'p1']
        assert_pairs([r for r in projection['rows'] if r['population_key'] == 'p0'], threshold=False)
        missing = [r for r in projection['rows'] if r['population_key'] == 'p1']
        assert len(missing) == 2
        for row in missing:
            assert row['fields']['raw_contact']['value'] is None
            assert row['fields']['expected_contact']['value'] is None
            assert row['fields']['fold_enrichment']['value'] is None
            assert row['qualifications']['data_extent'] != 'complete'
        assert any(r['population_key'] == 'p1' and r['code'] == 'input_unavailable'
            and r['field_path'] for r in returned['failures'])
        assert not Path(case.provider.loss['path']).exists()
        assert json.loads(case.provider.native_bytes['bundle'])['extraction']['populations'][1]['extent'] == 'complete'
        receipt = case.outcomes[0]['result']
        assert receipt['acquired_population'] == digest(case.provider.plan['identity'])
        assert [p['extent'] for p in receipt['sheet_evidence']['populations']] == ['complete', 'partial']
        context, = case.result_contexts
        assert case.owner.native_chromatin_interaction_results.completion(context) is None
        assert case.owner.completion_for_action(context, f'{F.RUN_ID}:{context.episode_id}:0') is None
        actions = [json.loads(r['action']) for r in F.rows(case.store, 'runtime_actions') if r['episode_id'] == context.episode_id]
        assert [r['tool'] for r in actions] == ['execution.results.collect', 'execution.results.status']
        assert len([r for r in F.rows(case.store, 'runtime_observations') if r['episode_id'] == context.episode_id]) == 2
        assert F.history(case.by_role['results'][0]) == [2, 0]
        estimate = case.by_role['results'][0]['controller_state']['estimate']
        assert estimate['provenance'].get('version') != 'verified_practical_endpoint_yield_v1'
        assert estimate['expected_next_gain'] != NumericBand.exact(0).as_record()
        assert len(F.worker_runs(case.directory)) == 1
        assert len(list(case.workspace.rglob('native.json'))) == 1
    finally:
        case.store.close()


def test_complete_empty_sparse_populations_are_measured_zero_and_acquired_once(tmp_path, software):
    """012: genuinely empty native pixels, complete indexes, no synthetic receipts."""
    import h5py
    import numpy as np

    fixture = tmp_path / 'four-bin-complete-empty.cool'
    with h5py.File(fixture, 'x', libver='earliest', track_order=True) as container:
        container.attrs.update({'format': 'HDF5::Cooler', 'format-version': np.int64(3),
            'bin-type': 'fixed', 'bin-size': np.int64(10), 'storage-mode': 'symmetric-upper',
            'nchroms': np.int64(1), 'nbins': np.int64(4), 'nnz': np.int64(0), 'sum': np.int64(0),
            'generated-by': 'packet451-complete-empty-synthetic-fixture/' + h5py.__version__,
            'metadata': json.dumps({'origin': 'synthetic', 'biological_observation': False,
                'fixture_key': 'four_bin_complete_empty_sparse', 'normalization': 'raw'})})
        for group in ('chroms', 'bins', 'pixels', 'indexes'):
            container.create_group(group, track_order=True)
        for name, values, dtype in (
            ('chroms/name', [b'chrA'], 'S4'), ('chroms/length', [40], '<i4'),
            ('bins/chrom', [0, 0, 0, 0], h5py.enum_dtype({'chrA': 0}, basetype='<i4')),
            ('bins/start', [0, 10, 20, 30], '<i4'), ('bins/end', [10, 20, 30, 40], '<i4'),
            ('pixels/bin1_id', [], '<i8'), ('pixels/bin2_id', [], '<i8'), ('pixels/count', [], '<i4'),
            ('indexes/chrom_offset', [0, 4], '<i8'), ('indexes/bin1_offset', [0, 0, 0, 0, 0], '<i8')):
            container.create_dataset(name, data=np.asarray(values, dtype=dtype), dtype=dtype, track_times=False)
    supplied = fixture.read_bytes()
    F.write(tmp_path / 'EMPTY_INPUT.json', {'fixture': str(fixture), 'sha256': hashlib.sha256(supplied).hexdigest(),
        'size_bytes': len(supplied), 'h5py_version': h5py.__version__, 'numpy_version': np.__version__,
        'pixel_rows': 0, 'bin1_offset': [0, 0, 0, 0, 0], 'biological_observation': False})
    case = F.workflow_case(tmp_path / 'complete_empty_sparse', software, contact_bytes=supplied)
    try:
        original, saved = [row['result'] for row in case.outcomes]
        bundle, = case.returned[0]['saved']
        sheet = json.loads(case.store.get_artifact(bundle['sheet']['artifact_ref']))
        assert case.job['request']['contact']['file']['sha256'] == hashlib.sha256(supplied).hexdigest()
        assert [p['population_key'] for p in sheet['populations']] == ['p0', 'p1']
        for population in sheet['populations']:
            assert population['extent'] == 'complete' and population['bin_count'] == 4
            evidence = population['read_evidence']
            assert all(evidence[k] == 'complete' for k in ('axes_extent', 'index_extent', 'selected_records_extent'))
            assert evidence['implicit_zero_semantics'] == 'validated_sparse_absence'
            assert not evidence['failed_block_ids']
            counts = population['raw_cell_population']
            assert counts['stored_rows'] == counts['validated_observed_row_count'] == counts['explicit_zero_rows'] == 0
            assert counts['implicit_zero_directed_cells'] == 16 and counts['unavailable_directed_cells'] == 0
            descriptor, = [d for d in sheet['data_tables']
                if d['population_key'] == population['population_key'] and d['role'] == 'contacts']
            assert descriptor['availability'] == 'present' and descriptor['shape'] == [0]
            assert descriptor['file'] in bundle['tables'] and descriptor['file']['size_bytes'] > 0
            raw = case.store.get_artifact(descriptor['file']['artifact_ref'])
            assert raw == case.provider.native_bytes[population['population_key'] + '.contacts']
            table = np.load(BytesIO(raw), allow_pickle=False)
            assert table.shape == (0,) and set(table.dtype.names) == {'bin1_id', 'bin2_id', 'value', 'source_block', 'source_row'}
            assert case.owner.native_chromatin_interaction_results.receipts._population_acquired(original, population)
        assert len(bundle['tables']) == 6 and bundle['tables'][:3] == bundle['tables'][3:]
        assert all(form['completed'] for form in case.returned)
        for worker in F.worker_runs(case.directory):
            components = json.loads(case.store.get_artifact(worker_output(worker, 'components')['artifact_ref']))
            for population in components['contact']['populations']:
                assert [row['promoter_element_key'] for row in population['pairs']] == ['P', 'Q']
                for row, denominator in zip(population['pairs'], (2, 1)):
                    fields = row['measurements']
                    assert fields['raw_contact']['value'] == fields['expected_contact']['value'] == 0
                    assert fields['raw_contact']['state'] == 'observed'
                    assert fields['expected_contact']['numerator'] == 0 and fields['expected_contact']['denominator'] == denominator
                    assert fields['fold_enrichment']['value'] is None and fields['fold_enrichment']['reason'] == 'zero_denominator'
                    assert fields['above_fold_threshold']['value'] is None
                    assert row['qualifications']['data_extent'] == 'complete'
        for form in case.returned:
            projection, = form['chromatin']
            assert projection['population_keys'] == ['p1']
            assert [row['fields']['raw_contact']['value'] for row in projection['rows']] == [0, 0]
        assert original['acquired_population'] == digest(case.provider.plan['identity'])
        assert case.owner.native_chromatin_interaction_results.receipts.original_acquisition_complete(original)
        assert saved['acquired_population'] is None and saved['observation'] is None and saved['capture'] is None
        assert case.returned[1]['saved'] == [bundle]
        assert [F.history(record) for record in case.by_role['results']] == [[2], [0]]
        for context, record in zip(case.result_contexts, case.by_role['results']):
            assert record['units_consumed'] == case.provider.turns[context.episode_id] == 1
            assert record['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
            proof = case.owner.completion_for_action(context, f'{F.RUN_ID}:{context.episode_id}:0')
            assert proof is not None and case.owner.verify_completion(context, proof)
        assert len(list(case.workspace.rglob('native.json'))) == 1
        assert sorted(row['plan']['mode'] for row in F.worker_runs(case.directory)) == ['native_result', 'saved_sheet_recalculation']
    finally:
        case.store.close()


@pytest.fixture(scope='module')
def selected_mode_software(tmp_path_factory):
    """Use the bounded test's own directory; old451 selectors keep their setup."""
    from gene_annotation_episode.native_chromatin_interaction_preparation import freeze_chromatin_software_binding
    import gene_annotation_episode.native_chromatin_interaction_driver as driver
    return freeze_chromatin_software_binding(module_root=str(Path(driver.__file__).parents[1]),
        snapshot_directory=str(tmp_path_factory.mktemp('selected_chromatin_software')),
        python_executable=os.sys.executable)


def selected_mode_case(directory, software, *, request, native_bytes, first_selector, saved_template, objective):
    """Actual Workflow with one original producer and one saved-only calculation."""
    evidence = {}

    def saved_selector(bundle):
        value = deepcopy(saved_template)
        value.update(mode='saved_sheet_recalculation', saved_sheet_bundle=deepcopy(bundle))
        return value

    with pytest.MonkeyPatch.context() as patch:
        def before_saved(case):
            original, = F.worker_runs(directory)
            assert original['plan']['mode'] == 'native_result'
            assert original['plan']['selector'] == first_selector
            evidence.update(bundle=deepcopy(case.bundle), original_worker=original,
                sheet_bytes=case.store.get_artifact(case.bundle['sheet']['artifact_ref']),
                table_bytes=[case.store.get_artifact(file['artifact_ref']) for file in case.bundle['tables']],
                components=json.loads(case.store.get_artifact(worker_output(original, 'components')['artifact_ref'])),
                observations=F.rows(case.store, 'runtime_observations'),
                completed_actions=[row for row in F.rows(case.store, 'runtime_actions') if row['result'] is not None],
                native_plans={str(path): path.read_bytes() for path in case.workspace.rglob('chromatin-plan.json')},
                origins=case.owner.native_chromatin_interaction_returns.authenticate_received_saved_bundle(
                    case.science_context, case.bundle), removed=[], dispatches=[])
            preserved = {file['artifact_ref'] for file in (case.bundle['sheet'], *case.bundle['tables'])}

            def remove(path, kind):
                if path.is_file():
                    raw = path.read_bytes()
                    path.unlink()
                    evidence['removed'].append({'kind': kind, 'path': str(path), 'size_bytes': len(raw),
                        'sha256': hashlib.sha256(raw).hexdigest()})

            science_roles = {'original_contact', 'original_elements', 'original_metadata',
                'bins', 'contacts', 'weights', 'cell_states', 'dense_values'}
            for spec in case.provider.plan['outputs']:
                if spec['role'] in science_roles:
                    remove(Path(case.provider.plan['attempt_directory']) / spec['relative_path'], 'native_scientific_copy')
                    raw = case.provider.native_bytes.get(spec['file_key'])
                    if raw is not None:
                        sha = hashlib.sha256(raw).hexdigest()
                        if 'artifact_' + sha not in preserved:
                            remove(case.store.path / 'artifacts' / sha[:2] / sha, 'retained_native_scientific_copy')
            for binding in case.provider.plan['requested_job']['native_chromatin_interactions']['input_bindings']:
                remove(Path(binding['path']), 'original_selected_input')
            for output in original['capture']['outputs']:
                if output['role'] in {'sheet', 'components', 'projection', 'table'}:
                    remove(Path(original['directory']) / output['capture']['declared']['relative_path'],
                        'original_worker_scientific_copy')
            assert evidence['removed'] and all(not Path(row['path']).exists() for row in evidence['removed'])
            from gene_annotation_episode import native_lifecycle
            actual_prepare = native_lifecycle.prepare_job

            def saved_worker_only(command, **kwargs):
                assert not evidence['dispatches']
                assert command[1:5] == ['-B', '-S', '-m', 'gene_annotation_episode.chromatin_interaction_result_worker']
                plan = json.loads(Path(command[-1]).read_bytes())
                assert set(plan) == {'version', 'mode', 'directory', 'sheet_bundle', 'selector'}
                assert plan['mode'] == 'saved_sheet_recalculation'
                assert plan['selector'] == saved_selector(case.bundle)
                assert plan['sheet_bundle']['sheet']['file'] == case.bundle['sheet']
                assert [row['file'] for row in plan['sheet_bundle']['tables']] == case.bundle['tables']
                assert kwargs['policy'].to_dict() == F.POLICY
                evidence['dispatches'].append({'command': list(command), 'plan': deepcopy(plan)})
                return actual_prepare(command, **kwargs)

            patch.setattr(native_lifecycle, 'prepare_job', saved_worker_only)
            patch.setattr('gene_annotation_episode.native_chromatin_interaction_results.capture_chromatin_native_files', deny)
            patch.setattr(type(case.owner.job_progress_provider.targets), 'observe_target', deny)
            patch.setattr('gene_annotation_episode.chromatin_cooler_inputs.read_cooler_contacts', deny)
            patch.setattr('h5py.File', deny)
            patch.setattr('socket.create_connection', deny)
            patch.setattr('socket.socket.connect', deny)
            patch.setattr('socket.socket.connect_ex', deny)

        case = F.workflow_case(directory, software, request_template=request, contact_bytes=native_bytes,
            result_selector=first_selector, saved_selector_factory=saved_selector, objective=objective,
            before_saved=before_saved)
    case.saved_evidence = evidence
    return case


def assert_selected_delivery(case, first_selector, saved_template):
    """Check actual receiving/forwarding facts and counts, not fixture credit values."""
    evidence, request = case.saved_evidence, case.job['request']
    information, = plain(case.scientific_context.assignment)['selection']['child_tool_info']
    assert information['name'] == 'analyze_chromatin_interactions' and information['resources'] == 'local'
    assert information['description'] and information['instructions']
    assert case.provider.plan['requested_job']['native_chromatin_interactions'] == case.job
    assert case.provider.plan['policy'] == F.POLICY
    selected = [request['contact']['source_ref'], request['contact']['file']['artifact_ref']]
    if request['elements'] is not None:
        selected.extend((request['elements']['source_ref'], request['elements']['file']['artifact_ref'],
            request['elements']['reference']['source_ref']))
    selected.append(request['supplied_metadata']['reference']['source_ref'])
    selected.extend(row['source_ref'] for key in ('samples', 'contact_sample_links')
        for row in request['supplied_metadata'][key])
    assert case.provider.input_refs == list(dict.fromkeys(ref for ref in selected if ref is not None))
    assert set(case.provider.input_refs) <= set(case.configuration['initial_refs'])
    for binding in case.job['input_bindings']:
        spec, = [row for row in (request['contact'], request['elements'])
            if row is not None and row['input_key'] == binding['input_key']]
        assert case.store.get(spec['source_ref'])['artifact_ref'] == spec['file']['artifact_ref']
        assert binding['path'] == str(F.artifact_path(case.store, spec['file']))
        assert not Path(binding['path']).exists()
    sheet = json.loads(evidence['sheet_bytes'])
    assert sheet['request'] == request
    assert evidence['bundle']['tables'] == [row['file'] for row in sheet['data_tables'] if row['file'] is not None]
    assert case.store.get_artifact(evidence['bundle']['sheet']['artifact_ref']) == evidence['sheet_bytes']
    assert [case.store.get_artifact(file['artifact_ref']) for file in evidence['bundle']['tables']] == evidence['table_bytes']
    assert len(evidence['dispatches']) == len(evidence['native_plans']) == 1
    assert {str(path): path.read_bytes() for path in case.workspace.rglob('chromatin-plan.json')} == evidence['native_plans']
    assert len(list(case.workspace.rglob('native.json'))) == 1
    runs = F.worker_runs(case.directory)
    assert sorted(row['plan']['mode'] for row in runs) == ['native_result', 'saved_sheet_recalculation']
    assert all(row in F.rows(case.store, 'runtime_observations') for row in evidence['observations'])
    assert all(row in F.rows(case.store, 'runtime_actions') for row in evidence['completed_actions'])
    original, saved = [row['result'] for row in case.outcomes]
    assert original['acquired_population'] == digest(case.provider.plan['identity'])
    assert case.owner.native_chromatin_interaction_results.receipts.original_acquisition_complete(original)
    assert saved['acquired_population'] is saved['observation'] is saved['capture'] is None
    assert evidence['origins'] == ({'episode_id': case.result_contexts[0].episode_id,
        'operation_key': f'{F.RUN_ID}:{case.result_contexts[0].episode_id}:0'},)
    projections = [form['chromatin'][0] for form in case.returned]
    for context, form, projection, selector in zip(case.result_contexts, case.returned, projections,
            (first_selector, saved_template)):
        assert set(form) == {'chromatin', 'saved', 'failures', 'completed'} and form['completed'] is True
        assert form['saved'] == [evidence['bundle']]
        assert projection['kind'] == selector['projection']['kind']
        assert projection['requested_fields'] == selector['projection']['fields']
        assert projection['population_keys'] == selector['population_keys']
        assert projection['parameters'] == selector['parameters']
        assert all(set(row['fields']) == set(projection['requested_fields']) for row in projection['rows'])
        groups = case.owner.native_chromatin_interaction_results.own_fact_groups(context, verify_artifacts=False)
        assert form == {'chromatin': groups[F.PROJECTION_SOURCE], 'saved': groups[F.SAVED_SOURCE],
            'failures': groups[F.FAILURE_SOURCE], 'completed': True}
    assert case.forwarded == {'chromatin': projections}
    reader = case.owner.native_chromatin_interaction_returns
    assert reader.facts(case.root_context, case.parent_form) == {F.PROJECTION_SOURCE: projections}
    assert F.SAVED_SOURCE not in {node.get('x-source') for node in case.parent_form['properties'].values()}
    for file in (evidence['bundle']['sheet'], *evidence['bundle']['tables']):
        assert reader.resolve_received(case.scientific_context, file['artifact_ref'], 'artifact')
        assert not reader.resolve_received(case.root_context, file['artifact_ref'], 'artifact')
    with pytest.raises(ValueError, match='saved_bundle_not_received'):
        reader.authenticate_received_saved_bundle(case.root_context, evidence['bundle'])
    counts = []
    for record in case.records:
        context = case.contexts[record['episode_id']]
        actions = [row for row in F.rows(case.store, 'runtime_actions') if row['episode_id'] == context.episode_id]
        observations = [row for row in F.rows(case.store, 'runtime_observations') if row['episode_id'] == context.episode_id]
        assert len(actions) == len(observations) == record['units_consumed'] == case.provider.turns[context.episode_id]
        counts.append({'episode_id': context.episode_id, 'role': context.role, 'actions': len(actions),
            'observations': len(observations), 'marginal_credit': F.history(record)})
        if context.role in {'launch', 'launch_local', 'results'}:
            assert len(actions) == 1
            proof = case.owner.completion_for_action(context, f'{F.RUN_ID}:{context.episode_id}:0')
            assert proof is not None and case.owner.verify_completion(context, proof)
            estimate = record['controller_state']['estimate']
            assert estimate['expected_next_gain'] == NumericBand.exact(0).as_record()
            assert estimate['provenance']['version'] == 'verified_practical_endpoint_yield_v1'
    assert case.store.count('annotation') == 0
    F.write(case.directory / 'SELECTED_MODE_CHECK.json', {'input_refs_before_commission': case.provider.input_refs,
        'counts': counts, 'original_native_producers': len(evidence['native_plans']),
        'finite_calculation_workers': len(runs), 'removed_original_inputs_and_copies': evidence['removed'],
        'returned': case.returned, 'forwarded': case.forwarded})
    return sheet, projections


def assert_selected_closed_replay(case):
    class NoNewDecisions:
        async def complete(self, *args, **kwargs):
            raise AssertionError('closed selected Workflow requested a new decision')
        async def release(self, episode_id):
            pass

    with pytest.MonkeyPatch.context() as patch:
        for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect'):
            patch.setattr('gene_annotation_episode.native_lifecycle.' + name, deny)
        for name in ('capture_chromatin_native_files', 'prepare_chromatin_result_worker'):
            patch.setattr('gene_annotation_episode.native_chromatin_interaction_results.' + name, deny)
        patch.setattr(type(case.owner.job_progress_provider.targets), 'observe_target', deny)
        patch.setattr('gene_annotation_episode.chromatin_cooler_inputs.read_cooler_contacts', deny)
        patch.setattr('h5py.File', deny)
        patch.setattr('socket.create_connection', deny)
        patch.setattr('socket.socket.connect', deny)
        patch.setattr('socket.socket.connect_ex', deny)
        with Store(case.directory / 'state') as store:
            before = {table: F.rows(store, table) for table in F.TABLES}
            retained = {str(path): path.read_bytes() for path in (case.directory / 'run').rglob('*.json')}
            flow, _ = F.assemble(store, case.directory, NoNewDecisions(), case.configuration)
            owner = flow.episode_bindings.for_role('results')
            for original_context, original_outcome in zip(case.result_contexts, case.outcomes):
                context = owner.native_chromatin_interaction_returns.context(original_context.episode_id)
                key = f'{F.RUN_ID}:{context.episode_id}:0'
                proof = owner.completion_for_action(context, key)
                assert proof is not None and owner.verify_completion(context, proof)
                replay = asyncio.run(owner.execute(context, 'execution.results.collect', {}, key))
                assert replay == {key: value for key, value in original_outcome.items() if key != 'pending_work_after_action'}
                assert owner.completion_for_action(context, key) == proof
            _, _, archive = asyncio.run(F.run_root(flow, case.configuration))
            assert archive == case.archive
            assert {table: F.rows(store, table) for table in F.TABLES} == before
            assert {str(path): path.read_bytes() for path in (case.directory / 'run').rglob('*.json')} == retained
            assert all(not Path(row['path']).exists() for row in case.saved_evidence['removed'])
    F.write(case.directory / 'SELECTED_REPLAY_CHECK.json', {'new_decisions': 0,
        'new_native_or_calculation_workers': 0, 'unchanged_tables': list(F.TABLES), 'unchanged_archive': True})


def test_selected_weighted_cooler_received_saved_and_closed_workflow(tmp_path, selected_mode_software):
    request = deepcopy(F.WORKED['weighted.request'])
    request['populations'] = [dict(request['populations'][0], population_key=key) for key in ('p0', 'p1')]
    first = deepcopy(F.WORKED['weighted.selector'])
    first['population_keys'] = ['p1']
    saved = deepcopy(first)
    saved['parameters']['contact']['fold_threshold'] = 0.5
    native = (F.ROOT / 'verification/tool_graders_chromatin_native_prerequisites_2026-10-27_440/fixture_generation/fixtures/four-bin-raw-weighted.cool').read_bytes()
    case = selected_mode_case(tmp_path / 'selected_weighted', selected_mode_software, request=request,
        native_bytes=native, first_selector=first, saved_template=saved,
        objective='Measure the supplied weighted contacts for E-P and E-Q in selected population p1, then test fold threshold0.5 from the received saved sheet.')
    try:
        sheet, projections = assert_selected_delivery(case, first, saved)
        assert case.job['request']['normalization'] == {
            'kind': 'precomputed_weighted', 'weight_column': 'weight', 'convention': 'multiplicative'}
        assert case.job['request']['contact']['file']['sha256'] == hashlib.sha256(native).hexdigest()
        assert len(case.provider.input_refs) == 6
        assert [row['population_key'] for row in sheet['populations']] == ['p0', 'p1']
        assert all(row['normalization']['availability'] == 'available' for row in sheet['populations'])
        assert len([row for row in sheet['data_tables'] if row['role'] == 'weights' and row['file'] is not None]) == 2
        assert case.job['request']['supplied_metadata']['samples'][0]['condition_key'] is None
        assert case.job['request']['supplied_metadata']['samples'][0]['replicate_key'] is None
        assert case.job['request']['supplied_metadata']['dependence_groups'] == []
        for projection, flag in zip(projections, (False, True)):
            assert projection['page'] == {'offset': 0, 'returned_count': 2, 'total_row_count': 2, 'has_more': False}
            assert [row['promoter_element_key'] for row in projection['rows']] == ['P', 'Q']
            assert {row['population_key'] for row in projection['rows']} == {'p1'}
            p, q = [row['fields'] for row in projection['rows']]
            assert [p[key]['value'] for key in ('raw_contact', 'normalized_contact', 'expected_contact')] == [6, 6, 7]
            assert (p['expected_contact']['numerator'], p['expected_contact']['denominator']) == (14, 2)
            assert p['fold_enrichment']['value'] == pytest.approx(6 / 7)
            assert (p['fold_enrichment']['numerator'], p['fold_enrichment']['denominator']) == (6, 7)
            assert p['above_fold_threshold']['value'] is flag
            assert [q[key]['value'] for key in ('raw_contact', 'normalized_contact', 'expected_contact')] == [0, 0, 0]
            assert q['raw_contact']['state'] == 'observed'
            assert (q['expected_contact']['numerator'], q['expected_contact']['denominator']) == (0, 1)
            assert q['fold_enrichment']['value'] is None and q['fold_enrichment']['reason'] == 'zero_denominator'
            assert q['above_fold_threshold']['value'] is None
            assert p['normalized_contact']['unit'] == {'kind': 'normalized_contact', 'source_unit': 'contacts'}
            assert p['fold_enrichment']['unit'] == {'kind': 'dimensionless', 'source_unit': None}
            for row in projection['rows']:
                assert row['qualifications']['normalization_state'] == 'available'
                assert row['qualifications']['data_extent'] == 'complete'
                assert all(value['uncertainty'] == {'kind': 'not_measured', 'value': None, 'unit': None}
                    for value in row['fields'].values() if 'uncertainty' in value)
        for before, after in zip(projections[0]['rows'], projections[1]['rows']):
            assert {key: value for key, value in before['fields'].items() if key != 'above_fold_threshold'} == {
                key: value for key, value in after['fields'].items() if key != 'above_fold_threshold'}
        assert any(row['code'] == 'zero_denominator' and row['population_key'] == 'p1' and row['pair_key']
            for row in case.returned[0]['failures'])
        assert_selected_closed_replay(case)
    finally:
        case.store.close()


def test_selected_insulation_without_elements_received_domains_saved_and_closed_workflow(tmp_path, selected_mode_software):
    request = deepcopy(F.WORKED['insulation.request'])
    request['contact']['specimen_key'] = None
    metadata = request['supplied_metadata']
    metadata['reference'] = {'assembly_accession': None, 'assembly_label': None, 'contigs': None, 'source_ref': None}
    for key in ('samples', 'contact_sample_links', 'dependence_groups', 'native_attribute_bindings', 'supplied_uncertainty'):
        metadata[key] = []
    first, saved = deepcopy(F.WORKED['insulation.selector']), deepcopy(F.WORKED['domains.selector'])
    native = (F.ROOT / 'verification/tool_graders_chromatin_native_prerequisites_2026-10-27_440/fixture_generation/fixtures/six-bin-all-full-windows.cool').read_bytes()
    case = selected_mode_case(tmp_path / 'selected_insulation', selected_mode_software, request=request,
        native_bytes=native, first_selector=first, saved_template=saved,
        objective='Measure the supplied six-bin cross-window insulation heuristic with all full one-bin windows and return its domains from the received saved sheet; no elements are supplied.')
    try:
        sheet, (windows, domains) = assert_selected_delivery(case, first, saved)
        assert case.job['request']['elements'] is None
        assert case.job['request']['supplied_metadata'] == metadata
        assert len(case.job['input_bindings']) == 1
        assert len(case.provider.input_refs) == len(case.configuration['initial_refs']) == 2
        assert sheet['request']['supplied_metadata']['reference']['contigs'] is None
        assert case.job['request']['contact']['file']['sha256'] == hashlib.sha256(native).hexdigest()
        assert [row['boundary_bin_id'] for row in windows['rows']] == [1, 2, 3, 4, 5]
        assert [row['fields']['cross_contact_sum']['value'] for row in windows['rows']] == [5, 1, 5, 1, 5]
        assert [row['fields']['insulation_z']['value'] for row in windows['rows']] == pytest.approx([
            0.816496580927726, -1.224744871391589, 0.816496580927726, -1.224744871391589, 0.816496580927726])
        assert [row['fields']['is_boundary']['value'] for row in windows['rows']] == [False, True, False, True, False]
        assert [row['qualifications']['eligibility'] for row in windows['rows']] == [
            'ineligible_edge', 'eligible', 'eligible', 'eligible', 'ineligible_edge']
        assert windows['page'] == {'offset': 0, 'returned_count': 5, 'total_row_count': 5, 'has_more': False}
        domain, = domains['rows']
        assert [domain['fields'][key]['value'] for key in saved['projection']['fields']] == [20, 40, 20, 0.02]
        assert (domain['fields']['domain_size_kb']['numerator'], domain['fields']['domain_size_kb']['denominator']) == (20, 1000)
        assert domain['fields']['domain_size_kb']['unit'] == {'kind': 'kb', 'source_unit': None}
        assert domains['page'] == {'offset': 0, 'returned_count': 1, 'total_row_count': 1, 'has_more': False}
        for projection in (windows, domains):
            assert projection['parameters']['insulation'] == first['parameters']['insulation']
            assert projection['population_keys'] == ['p0']
            for row in projection['rows']:
                assert row['qualifications']['reference_relation'] == 'unknown'
                assert row['qualifications']['interpretation'] == 'heuristic_prediction'
                assert row['qualifications']['data_extent'] == 'complete'
                assert all(value['uncertainty'] == {'kind': 'not_measured', 'value': None, 'unit': None}
                    for value in row['fields'].values() if 'uncertainty' in value)
        components = case.saved_evidence['components']['insulation']['populations'][0]
        assert all(row['measurements']['nominal_window_cell_count']['value'] == 1
            and row['measurements']['valid_window_cell_count']['value'] == 1 for row in components['windows'])
        mean, variance = [components['statistics'][key] for key in ('z_population_mean', 'z_population_variance')]
        assert (mean['value'], mean['numerator'], mean['denominator']) == (3.4, 17, 5)
        assert variance['value'] == pytest.approx(3.84) and variance['numerator'] == pytest.approx(19.2)
        assert variance['denominator'] == 5
        saved_run, = [row for row in F.worker_runs(case.directory) if row['plan']['mode'] == 'saved_sheet_recalculation']
        saved_components = json.loads(case.store.get_artifact(worker_output(saved_run, 'components')['artifact_ref']))
        assert saved_components['insulation']['populations'] == case.saved_evidence['components']['insulation']['populations']
        assert all(not form['failures'] for form in case.returned)
        assert_selected_closed_replay(case)
    finally:
        case.store.close()
