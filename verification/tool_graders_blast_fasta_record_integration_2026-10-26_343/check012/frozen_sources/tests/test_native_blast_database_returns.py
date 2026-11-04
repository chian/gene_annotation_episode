"""Synthetic original-action, typed-return and scientific-consumer authority."""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical
from test_native_blast_database_episode_binding import SyntheticHost, schema_for, selector
from test_native_blast_database_results import query_selection


def test_actual_received_form_is_required_and_saved_row_cannot_be_rewritten(tmp_path, monkeypatch):
    h = SyntheticHost(tmp_path, monkeypatch)
    try:
        child = h.results()
        body = h.select(child, 0, 'execution.results.collect')['result']
        row = body['publication']['rows_by_family']['hsp'][0]
        assert h.family.resolve_received_reference(h.root, row['record_key'], 'native_blast_database_row') is False
        h.receipts.receive(h.root.episode_id, [row['source_ref']], kind='initial')
        assert h.family.resolve_received_reference(h.root, row['record_key'], 'native_blast_database_row') is False
        form, schema = h.returned(child)
        assert h.family.resolve_received_reference(h.root, row['record_key'], 'native_blast_database_row') is True
        altered = deepcopy(form)
        field = next(k for k, v in schema['properties'].items() if v['x-source'] == 'execution_blast_database_hsp_rows')
        altered[field][0]['measurements'][0]['value'] = 21
        with pytest.raises(ValueError, match='facts_conflict'):
            h.family.validate_received_report(child, altered, schema)
        sibling = h.child(h.root, 'scientific_process', {}, schema_for('execution_blast_database_hsp_rows'), index=2)
        h.receipts.receive(sibling.episode_id, [row['source_ref']], kind='initial')
        assert h.family.resolve_received_reference(sibling, row['record_key'], 'native_blast_database_row') is False
        assert h.family.resolve_received_reference(sibling, row['source_ref'], 'execution_result') is False
        # Replacing only a saved form cannot manufacture an original result.
        h.store.db.execute('UPDATE runtime_forms SET form=? WHERE run_id=? AND episode_id=?',
            (canonical(altered), h.run_id, child.episode_id))
        with pytest.raises(ValueError, match='frozen_form_conflict'):
            h.family.native_blast_database_returns.received_facts(h.root, schema)
    finally:
        h.store.close()


def test_unchanged_scientific_forwarding_uses_immediate_child_forms(tmp_path, monkeypatch):
    h = SyntheticHost(tmp_path, monkeypatch)
    try:
        original_parent = h.root
        schema = schema_for('execution_blast_database_hsp_rows', 'execution_blast_database_acquisition',
            'execution_blast_database_failures')
        process = h.child(original_parent, 'scientific_process', {}, schema, index=1)
        h.root = process
        child = h.results(selector('hsp'), index=0)
        body = h.select(child, 0, 'execution.results.collect')['result']
        original, _ = h.returned(child)
        received = h.family.native_blast_database_returns.received_facts(process, schema)
        forwarded, _ = h.deliver(process, original_parent, received)
        assert forwarded == original
        assert h.family.native_blast_database_returns.received_facts(original_parent, schema) == received
        assert h.family.resolve_received_reference(original_parent,
            body['publication']['rows_by_family']['hsp'][0]['record_key'], 'native_blast_database_row') is True
    finally:
        h.store.close()


def test_every_native_consumer_qualifies_frozen_measurements_and_missing_reference(tmp_path, monkeypatch):
    from gene_annotation_episode.native_blast_database_result_publication import validate_native_blast_database_observation
    from gene_annotation_episode.evidence_geometry import _observation_extent, _observation_extents
    from gene_annotation_episode.evidence_axis_contracts import native_metric_facts
    from gene_annotation_episode.blast_result_views import _original_hsp
    from gene_annotation_episode.alignment_site_native import source_descriptor, blast_grading
    from gene_annotation_episode.infernal_result_presentation import infernal_receiver_context
    from gene_annotation_episode.domain import REASONING_SCHEMA
    from test_evidence_axis_contracts import axis_entry
    h = SyntheticHost(tmp_path, monkeypatch)
    try:
        child = h.results(query_selection(h))
        body = h.select(child, 0, 'execution.results.collect')['result']
        row = body['publication']['rows_by_family']['hsp'][0]
        observed, source = h.store.get(row['observation_ref']), h.store.get(row['source_ref'])
        entry = axis_entry(); entry['native_measurements'][0]['binding']['measurement_name'] = 'native_score_bits'
        facts = native_metric_facts(entry, h.store, observation_refs=[observed['id']], received_record_refs=[observed['id']])
        assert facts['native_facts'][0]['native_value']['value'] == 20
        assert _observation_extents(h.store, observed)[0][0] == {h.scope['subject_refs'][0]: [(0, 4)]}
        readers = [lambda: _original_hsp(h.store, observed['id'], [observed['id']], h.scope),
            lambda: source_descriptor(h.store, source, observed),
            lambda: blast_grading(h.store, observed, source, None, None, 0, 4, grade_result=lambda *_: None)]
        for reader in readers:
            with pytest.raises(ValueError, match='biological_reference_unavailable'):
                reader()
        assert 'native_blast_database' not in REASONING_SCHEMA['properties']['observations']['items']['properties']
        context = dict(working_state=dict(observations=[observed]), child_returns=[{'explicit': row}])
        projected = infernal_receiver_context(context)
        assert projected['working_state']['observations'] == [] and projected['child_returns'] == context['child_returns']
        original_get = h.store.get
        changed = deepcopy(observed); changed['measurements'][0]['value']['value'] += 1
        monkeypatch.setattr(h.store, 'get', lambda ref: changed if ref == observed['id'] else original_get(ref))
        observed = changed
        checks = [lambda: validate_native_blast_database_observation(h.store, changed),
            lambda: _observation_extent(h.store, changed), lambda: _observation_extents(h.store, changed),
            lambda: native_metric_facts(entry, h.store, observation_refs=[changed['id']], received_record_refs=[changed['id']]), *readers]
        for check in checks:
            with pytest.raises(ValueError, match='frozen_observation_conflict'):
                check()
    finally:
        h.store.close()


def test_successful_original_collect_immediately_has_exact_zero_future_expectation(tmp_path, monkeypatch):
    from gene_annotation_episode.numerical import YieldParameters
    from test_practical_yield import completion_context
    h = SyntheticHost(tmp_path, monkeypatch)
    try:
        child = h.results()
        body = h.select(child, 0, 'execution.results.collect')['result']
        proof = h.family.completion_for_action(child, body['operation_key'])
        context = completion_context(run_id=h.run_id, episode_id=child.episode_id, unit_index=0, action_index=0)
        runtime_fields = {k: context['practical_completion'][k] for k in ('unit_ref', 'action_index')}
        context['practical_completion'] = {**proof, **runtime_fields}
        before = deepcopy(context)
        estimate = h.family.practical_estimator(child)((2.0,), YieldParameters(), (context,))
        assert estimate.expected_next_gain.lower == estimate.expected_next_gain.upper == 0
        assert context == before
        assert h.store.db.execute('SELECT COUNT(*) FROM runtime_actions WHERE run_id=? AND episode_id=?',
            (h.run_id, child.episode_id)).fetchone()[0] == 1
    finally:
        h.store.close()


def test_frozen_observation_requires_original_commission_handoff_and_record(tmp_path, monkeypatch):
    from gene_annotation_episode.native_blast_database_result_publication import (
        validate_native_blast_database_observation, validate_native_blast_database_publication)
    h = SyntheticHost(tmp_path, monkeypatch)
    try:
        child = h.results(query_selection(h))
        body = h.select(child, 0, 'execution.results.collect')['result']
        observation = h.store.get(body['publication']['rows_by_family']['hsp'][0]['observation_ref'])
        for episode_id, index in [(h.root.episode_id, 1), (h.hpc.episode_id, 0)]:
            saved = h.store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?',
                (h.run_id, episode_id, index)).fetchone()['action']
            altered = json.loads(saved)
            if episode_id == h.root.episode_id:
                altered['purpose'] = 'different parent commission'
            else:
                altered['arguments']['queue'] = 'different queue'
            h.store.db.execute('UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=?',
                (json.dumps(altered), h.run_id, episode_id, index))
            with pytest.raises(ValueError):
                validate_native_blast_database_observation(h.store, observation)
            h.store.db.execute('UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=?',
                (saved, h.run_id, episode_id, index))
            assert validate_native_blast_database_observation(h.store, observation)['family'] == 'hsp'
        h.store.db.execute('DELETE FROM records WHERE id=?', (observation['id'],))
        with pytest.raises(ValueError):
            validate_native_blast_database_publication(h.store, context=child, publication=body['publication'])
        assert h.store.query_records('observation')['total'] == 0
    finally:
        h.store.close()


@pytest.mark.parametrize('reverse', [False, True])
def test_repeated_projection_receipts_union_only_actual_received_cells(tmp_path, monkeypatch, reverse):
    from gene_annotation_episode.communication import form_with_facts, validate_form
    h = SyntheticHost(tmp_path, monkeypatch, program='rpsblast')
    try:
        source = 'execution_blast_database_hsp_rows'
        schema = schema_for(source)
        outer = h.root
        process = h.child(outer, 'scientific_process', {}, schema, index=1)
        h.root = process
        choices = [['native_score_bits', 'native_evalue'], ['native_raw_score']]
        if reverse:
            choices.reverse()
        bodies, originals, children = [], [], []
        for index, metrics in enumerate(choices):
            selection = query_selection(h)
            selection['projections'][0]['metrics'] = metrics
            child = h.results(selection, index=index)
            bodies.append(h.select(child, 0, 'execution.results.collect')['result'])
            originals.append(h.returned(child)[0]); children.append(child)
        before_forms = [dict(row) for row in h.store.db.execute('SELECT * FROM runtime_forms ORDER BY episode_id')]
        before_actions = h.store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0]
        before_observations = h.store.query_records('observation')['total']
        # Re-reading frozen received values cannot parse, calculate or run work.
        import gene_annotation_episode.native_blast_database_result_worker as worker
        import gene_annotation_episode.blast_report_collection as collectors
        import gene_annotation_episode.blast_iteration_calculators as calculators
        def forbidden(*_args, **_kwargs):
            raise AssertionError('received-cell union attempted fresh scientific work')
        monkeypatch.setattr(worker, 'run_native_blast_database_result_worker', forbidden)
        monkeypatch.setattr(collectors, 'parse_blast_report_collection', forbidden)
        monkeypatch.setattr(calculators, 'calculate_blast_iteration_components', forbidden)
        returns = h.family.native_blast_database_returns
        received = returns.received_facts(process, schema)
        row, = received[source]
        assert [m['name'] for m in row['measurements']] == [name for names in choices for name in names]
        assert {m['name']: m['value'] for m in row['measurements']} == {
            'native_score_bits': 20, 'native_evalue': 0.0, 'native_raw_score': 40}
        assert before_observations == 1
        assert bodies[0]['publication']['rows_by_family']['hsp'][0]['observation_ref'] == row['observation_ref']
        assert bodies[1]['publication']['rows_by_family']['hsp'][0]['observation_ref'] == row['observation_ref']
        assert h.family.native_blast_database_results.credit_view(children[1], dict(
            known_record_refs=bodies[1]['record_refs'], initial_known_record_refs=bodies[0]['record_refs']))['credit'] == 0
        h.returned(children[1])  # Exact repeated delivery adds no cell or action.
        assert returns.received_facts(process, schema) == received
        assert [dict(item) for item in h.store.db.execute('SELECT * FROM runtime_forms ORDER BY episode_id')] == before_forms
        forged = form_with_facts({}, schema, received)
        fourth = deepcopy(row['measurements'][0]); fourth['name'] = 'alignment_columns'
        fourth['unit'] = 'alignment_column'
        forged['field_0'][0]['measurements'].append(fourth)
        with pytest.raises(ValueError, match='returned_facts_conflict'):
            h.family.validate_received_report(process, forged, schema)
        form, _ = h.deliver(process, outer, received)
        validate_form(form, schema, lambda ref, ns: h.family.resolve_received_reference(outer, ref, ns))
        assert returns.received_facts(outer, schema) == received
        assert h.store.query_records('observation')['total'] == before_observations
        assert h.store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == before_actions
        (tmp_path / 'projection-return-union.json').write_text(canonical(dict(
            original_forms=originals, schema=schema, received=received, forwarded=form)))
    finally:
        h.store.close()


def test_frozen_forwarded_projection_remains_an_authorized_subset(tmp_path, monkeypatch):
    h = SyntheticHost(tmp_path, monkeypatch, program='rpsblast')
    try:
        source = 'execution_blast_database_hsp_rows'
        schema = schema_for(source)
        outer = h.root
        process = h.child(outer, 'scientific_process', {}, schema, index=1)
        h.root = process
        first = h.results(selector('hsp'), index=0)
        h.select(first, 0, 'execution.results.collect'); h.returned(first)
        returns = h.family.native_blast_database_returns
        original = returns.received_facts(process, schema)
        h.deliver(process, outer, original)
        frozen_form = h.store.db.execute('SELECT facts,form FROM runtime_forms WHERE episode_id=?',
            (process.episode_id,)).fetchone()
        selection = selector('hsp'); selection['projections'][0]['metrics'] = ['native_raw_score']
        second = h.results(selection, index=1)
        h.select(second, 0, 'execution.results.collect'); h.returned(second)
        assert len(returns.received_facts(process, schema)[source][0]['measurements']) == 3
        assert returns.received_facts(outer, schema) == original
        assert tuple(h.store.db.execute('SELECT facts,form FROM runtime_forms WHERE episode_id=?',
            (process.episode_id,)).fetchone()) == tuple(frozen_form)
        # A changed frozen child form is rejected before subset proof.
        altered = json.loads(frozen_form['form']); altered['field_0'][0]['measurements'][0]['value'] += 1
        h.store.db.execute('UPDATE runtime_forms SET form=? WHERE episode_id=?', (canonical(altered), process.episode_id))
        with pytest.raises(ValueError, match='frozen_form_conflict'):
            returns.received_facts(outer, schema)
    finally:
        h.store.close()


def test_distinct_saved_calculations_keep_separate_rows_without_new_observations(tmp_path, monkeypatch):
    h = SyntheticHost(tmp_path, monkeypatch, program='rpsblast')
    try:
        selection = query_selection(h)
        child = h.results(selection, index=1)
        first = h.select(child, 0, 'execution.results.collect')['result']
        h.returned(child)
        # A separately supplied, explicitly selected retained document changes
        # the calculation input identity, without changing the original model
        # or the native experiment. It has no numerical/query binding claim.
        artifact_ref = h.store.artifact(b'{"synthetic_auxiliary":true}', 'application/json')
        source_ref = h.store.put('source', dict(provider='caller', accession='synthetic-auxiliary', uri=None,
            artifact_ref=artifact_ref, text_ref=None, request_ref=None, version='synthetic_v1', retrieved_at=None), origin='caller')['id']
        h.receipts.receive(h.root.episode_id, [source_ref, artifact_ref], kind='initial')
        artifact = h.store.get(artifact_ref)
        selected = deepcopy(selection)
        selected['retained_sources'].append(dict(source_ref=source_ref, artifact_ref=artifact_ref,
            sha256=artifact['sha256'], size_bytes=artifact['size']))
        child = h.results(selected, index=2)
        second = h.select(child, 0, 'execution.results.collect')['result']
        h.returned(child)
        schema = schema_for('execution_blast_database_hsp_rows')
        received = h.family.native_blast_database_returns.received_facts(h.root, schema)
        rows = received['execution_blast_database_hsp_rows']
        assert len(rows) == 2 and len({row['calculation_id'] for row in rows}) == 2
        assert rows[0]['record_key'] == rows[1]['record_key']
        assert rows[0]['source_ref'] == rows[1]['source_ref']
        assert rows[0]['observation_ref'] == rows[1]['observation_ref']
        assert rows[0]['measurements'] == rows[1]['measurements']
        assert h.store.query_records('observation')['total'] == 1
        assert h.family.native_blast_database_results.credit_view(child, dict(
            known_record_refs=second['record_refs'], initial_known_record_refs=first['record_refs']))['credit'] == 0
        assert artifact_ref not in h.store.get(rows[0]['source_ref'])['auxiliary_artifact_refs']
        (tmp_path / 'distinct-calculations.json').write_text(canonical(received))
    finally:
        h.store.close()


@pytest.mark.parametrize('kind', ['measurements', 'booleans'])
@pytest.mark.parametrize('field,value', [('value', 1.0), ('unit', 'bits'), ('status', 'unavailable'),
    ('reason', 'missing_input'), ('component_pointer', '/other')])
def test_received_cell_conflicts_are_specific_and_preserve_originals(kind, field, value):
    from gene_annotation_episode.native_blast_database_returns import NativeBLASTDatabaseReturns
    returns = NativeBLASTDatabaseReturns.__new__(NativeBLASTDatabaseReturns)
    returns.failure_prefix = 'native_blast_database_return_'
    row = dict(calculation_id='calculation', record_key='row', context={}, source_ref='source',
        measurements=[], booleans=[])
    row[kind] = [dict(name='cell', value=1, unit='count', status='available', reason=None,
        component_pointer='/original')]
    saved, changed = deepcopy(row), deepcopy(row)
    changed[kind][0][field] = value
    with pytest.raises(ValueError, match='native_blast_database_return_received_cell_conflict'):
        returns._merge_received_row(row, changed)
    assert row == saved


@pytest.mark.parametrize('field,value', [('context', {'different': True}), ('source_ref', 'other'),
    ('publication_status', 'source_only'), ('calculation_id', 'different-calculation')])
def test_received_row_context_conflicts_never_choose_a_projection(field, value):
    from gene_annotation_episode.native_blast_database_returns import NativeBLASTDatabaseReturns
    returns = NativeBLASTDatabaseReturns.__new__(NativeBLASTDatabaseReturns)
    returns.failure_prefix = 'native_blast_database_return_'
    row = dict(calculation_id='calculation', record_key='row', context={}, source_ref='source',
        measurements=[], booleans=[], publication_status='observation')
    changed = deepcopy(row); changed[field] = value
    with pytest.raises(ValueError, match='native_blast_database_return_received_row_context_conflict'):
        returns._merge_received_row(row, changed)


def test_actual_pre325_generation_and_forwarded_form_replay_without_interpretation(tmp_path, monkeypatch):
    """Read a copy of the retained successful pre325 synthetic run, unchanged."""
    import hashlib
    import shutil
    from pathlib import Path
    import sys
    from gene_annotation_episode.execution_episodes import ExecutionEpisodes
    from gene_annotation_episode.episode_journal import Journal
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry
    from gene_annotation_episode.practical_pbs_operations import PBSPracticalOperations
    from gene_annotation_episode.native_blast_database_result_publication import _json
    old = Path(__file__).resolve().parents[1] / 'verification/tool_graders_native_blast_database_episode_binding_2026-10-26_321/check_20261026T200411295390Z/tmp/test_unchanged_scientific_forw0'
    before = {str(p.relative_to(old)): hashlib.sha256(p.read_bytes()).hexdigest()
        for directory in ('store', 'run') for p in (old / directory).rglob('*') if p.is_file()}
    for directory in ('store', 'run'):
        shutil.copytree(old / directory, tmp_path / directory)
    with Store(tmp_path / 'store') as store:
        actual = store.db.execute("SELECT result FROM runtime_actions WHERE json_extract(result,'$.result.version')='native_blast_database_result_receipt_v1'").fetchone()
        body = json.loads(actual['result'])['result']
        run_id, prepared = body['run_id'], body['preparation']
        bundle = _json(store, prepared['bundle_artifact_ref']); job = bundle['requested_job']['native_blast_database']
        producer = json.loads(Path(bundle['plan']['producer_manifest']['path']).read_text())
        config = dict(kind='pbs_ssh', workspace=body['target']['assignment']['workspace'],
            ssh_argv=['mock-ssh', 'explicit-bastion', 'explicit-aurora'], python_executable=sys.executable, account='EpiCalib',
            native_blast_database=dict(version='native_blast_database_resource_v1', environment={},
                producer=dict(module_root=producer['module_root'], manifest=bundle['plan']['producer_manifest']),
                bindings=[dict(program=job['program'], mode='database', software=job['software'],
                    database_manifests=[db['manifest_file'] for db in job['databases']])]))
        family = ExecutionEpisodes(None, store=store, directory=tmp_path / 'run', run_id=run_id,
            resources={'synthetic-hpc': config}, initial_information={}, tool_registry=ToolRegistry(store),
            handoff_unit=3, acquired_record_unit=2, log_window_bytes=1024, log_roles=['stdout', 'stderr'])
        returns = family.native_blast_database_returns
        root = returns.context(store.db.execute("SELECT episode_id FROM runtime_episodes WHERE json_array_length(path)=1").fetchone()['episode_id'])
        original = dict(store.db.execute('SELECT * FROM runtime_report_attempts WHERE parent_episode_id=? AND decision_index=1',
            (root.episode_id,)).fetchone())
        schema = json.loads(original['contract'])['measurements']['schema']
        expected_form = json.loads(original['form'])
        expected = {node['x-source']: expected_form[name] for name, node in schema['properties'].items()}
        assert _json(store, prepared['worker_manifest_artifact_ref'])['version'] == 'native_blast_database_result_worker_manifest_v1'
        assert _json(store, prepared['sheets_artifact_ref'])['schema'] == 'native_blast_database_sheet_set_v1'
        import gene_annotation_episode.native_blast_database_result_worker as worker
        import gene_annotation_episode.native_blast_database_metadata as metadata
        import gene_annotation_episode.native_blast_database_convergence as bridge
        import gene_annotation_episode.blast_native_iteration_records as native
        import gene_annotation_episode.blast_iteration_inputs as inputs
        import gene_annotation_episode.blast_iteration_calculators as calculator
        def forbidden(*_args, **_kwargs):
            raise AssertionError('pre325 frozen replay attempted interpretation or execution')
        for module, names in [(worker, ['run_native_blast_database_result_worker', 'calculate_native_blast_database_sheets',
                'build_native_blast_database_rows', 'parse_blast_report_collection']),
                (metadata, ['prepare_native_blast_database_inputs', 'populate_native_blast_database_sheets']),
                (bridge, ['bind_native_blast_database_convergence']), (native, ['extract_blast_tabular7_convergence']),
                (inputs, ['populate_blast_iteration_sheet']), (calculator, ['calculate_blast_iteration_components'])]:
            for name in names:
                monkeypatch.setattr(module, name, forbidden)
        monkeypatch.setattr(PBSPracticalOperations, '_invoke', forbidden)
        forms_before = [dict(r) for r in store.db.execute('SELECT * FROM runtime_forms ORDER BY episode_id')]
        actions_before = store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0]
        assert returns.received_facts(root, schema) == expected
        journal = Journal(store, run_id)
        journal.save('runtime_model_calls', dict(episode_id=root.episode_id, call_index=2,
            purpose='decision', request=canonical({'synthetic_record': True}),
            response=canonical(dict(selection=dict(kind='redeliver_report', delivery_ref=original['delivery_ref'],
                purpose=json.loads(original['contract'])['decision'], schema_json=canonical(schema))))))
        original['decision_index'] = 2
        journal.save('runtime_report_attempts', {k: v for k, v in original.items() if k != 'run_id'})
        admitted = family.received_form_references(root, expected_form, schema, f'{run_id}:{root.episode_id}:2:typed_form')
        assert admitted and returns.received_facts(root, schema) == expected
        assert [dict(r) for r in store.db.execute('SELECT * FROM runtime_forms ORDER BY episode_id')] == forms_before
        assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == actions_before
    assert {str(p.relative_to(old)): hashlib.sha256(p.read_bytes()).hexdigest()
        for directory in ('store', 'run') for p in (old / directory).rglob('*') if p.is_file()} == before


def test_new_partial_visibility_does_not_expand_original_empty_received_history(tmp_path, monkeypatch):
    """The actual pre010 failure kept empty forms; no new receipt is invented."""
    import hashlib
    import shutil
    from pathlib import Path
    import sys
    from gene_annotation_episode.execution_episodes import ExecutionEpisodes, RESULTS_VERSION
    from gene_annotation_episode.episode_receipts import EpisodeReceipts
    from gene_annotation_episode.practical_pbs_operations import PBSPracticalOperations
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry
    old = Path(__file__).resolve().parents[1] / 'verification/tool_graders_native_blast_database_episode_binding_2026-10-26_321/check_20261026T203134870571Z/tmp/test_native_convergence_occurr2'
    before = {str(p.relative_to(old)): hashlib.sha256(p.read_bytes()).hexdigest()
        for directory in ('store', 'run') for p in (old / directory).rglob('*') if p.is_file()}
    for directory in ('store', 'run'):
        shutil.copytree(old / directory, tmp_path / directory)
    with Store(tmp_path / 'store') as store:
        episodes = [dict(r) for r in store.db.execute('SELECT * FROM runtime_episodes')]
        native = next(r for r in episodes if json.loads(r['path'])[-1][0] == 'launch_hpc')
        assignment = json.loads(native['request'])['message']['episode_assignment']
        actual = json.loads(store.db.execute('SELECT result FROM runtime_actions WHERE episode_id=?',
            (native['episode_id'],)).fetchone()['result'])
        detail = actual['result']['outcome']['native_outcome']
        plan = json.loads(Path(detail['native_blast_database_plan_path']).read_text())
        producer = json.loads(Path(plan['producer_manifest']['path']).read_text())
        job = assignment['requested_job']['native_blast_database']
        config = dict(kind='pbs_ssh', workspace=assignment['workspace'],
            ssh_argv=['mock-ssh', 'explicit-bastion', 'explicit-aurora'], python_executable=sys.executable, account='EpiCalib',
            native_blast_database=dict(version='native_blast_database_resource_v1', environment={},
                producer=dict(module_root=producer['module_root'], manifest=plan['producer_manifest']),
                bindings=[dict(program=job['program'], mode='database', software=job['software'],
                    database_manifests=[db['manifest_file'] for db in job['databases']])]))
        family = ExecutionEpisodes(None, store=store, directory=tmp_path / 'run', run_id=native['run_id'],
            resources={'synthetic-hpc': config}, initial_information={}, tool_registry=ToolRegistry(store),
            handoff_unit=3, acquired_record_unit=2, log_window_bytes=1024, log_roles=['stdout', 'stderr'])
        contexts = {json.loads(r['path'])[-1][0]: family.native_blast_database_returns.context(r['episode_id']) for r in episodes}
        root, launch = contexts['annotation'], contexts['launch']
        handoff = actual['record_refs'][0]
        def forbidden(*_args, **_kwargs):
            raise AssertionError('historical handoff validation attempted external work')
        monkeypatch.setattr(PBSPracticalOperations, '_invoke', forbidden)
        forms = [dict(r) for r in store.db.execute('SELECT * FROM runtime_forms ORDER BY episode_id')]
        assert all(json.loads(r['form']) == {'handoffs': []} for r in forms)
        assert family.job_progress_provider.targets.returnable_handoff(
            family.job_progress_provider.targets.read_target(handoff, root.scope))
        assert family.facts(launch, {})['execution_handoff_refs'] == []
        assert handoff not in EpisodeReceipts(store, native['run_id']).known(root.episode_id)
        with pytest.raises(ValueError, match='original_handoff_not_received'):
            family.prepare_assignment(root, 'results', dict(version=RESULTS_VERSION,
                handoff_ref=handoff, selector=selector('iteration_convergence')), root.scope, 'not-commissioned')
        assert [dict(r) for r in store.db.execute('SELECT * FROM runtime_forms ORDER BY episode_id')] == forms
    assert {str(p.relative_to(old)): hashlib.sha256(p.read_bytes()).hexdigest()
        for directory in ('store', 'run') for p in (old / directory).rglob('*') if p.is_file()} == before
