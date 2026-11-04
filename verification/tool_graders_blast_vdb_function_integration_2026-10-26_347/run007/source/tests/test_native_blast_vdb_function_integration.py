"""Synthetic selected VDB function runs through real custody and typed returns.

The existing controlled PBS harness emits supplied bytes. It never invokes
BLAST, a database, SSH, an API, an LLM, or a live HPC scheduler.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_episodes import RESULTS_VERSION
from gene_annotation_episode.native_blast_database_result_views import (
    FUNCTION_SELECTOR, FUNCTION_FAMILIES, SAVED_INPUT_SOURCE,
    native_blast_database_fact_sources, native_blast_database_metric_definitions)
from gene_annotation_episode.native_blast_database_result_publication import _json
from test_native_blast_database_episode_binding import SyntheticHost, schema_for, selector
from test_native_blast_database_results import query_selection
from test_native_blast_database_metadata import wire_fixture, address
from test_blast_vdb_function_inputs import whole_case, translated_case, populate, census_for
from test_blast_vdb_function_calculators import model


def metric(row, name):
    return next(c for c in row['measurements'] if c['name'] == name)


def retain_source(h, payload, key):
    ref = h.store.artifact(canonical(payload), 'application/json')
    source = h.store.put('source', dict(provider='caller', accession='synthetic-' + key, uri=None,
        artifact_ref=ref, text_ref=None, request_ref=None, version='synthetic_v1', retrieved_at=None), origin='caller')['id']
    artifact = h.store.get(ref)
    value = dict(source_ref=source, artifact_ref=ref, sha256=artifact['sha256'], size_bytes=artifact['size'])
    h.receipts.receive(h.root.episode_id, [source, ref], kind='initial')
    return value


def metadata_input(h, payload, consumer):
    ref = h.store.artifact(canonical(payload), 'application/json')
    artifact = h.store.get(ref)
    h.receipts.receive(h.root.episode_id, [ref], kind='initial')
    return dict(input_key=consumer + '-selected', consumer=consumer, schema_id=payload['schema'],
        artifact_ref=ref, sha256=artifact['sha256'], size_bytes=artifact['size'])


def selection(*, temperature=1, saved=None, scope='whole_sequence', census='census-1', families=FUNCTION_FAMILIES):
    # Request every named cell in these four small fixture families.
    from gene_annotation_episode.native_blast_database_result_views import _METRICS, _BOOLEANS
    return dict(version=FUNCTION_SELECTOR, acquisition='complete_bound_bundle', metadata_inputs=[], retained_sources=[],
        vdb_function_model=model(temperature=temperature, census=census, scope=scope),
        calculation_input={'mode': 'captured_inputs'} if saved is None else
            dict(mode='saved_function_sheet', **{k: deepcopy(v) for k, v in saved.items() if k != 'schema'}),
        projections=[dict(family=f, rows={'offset': 0, 'limit': 100}, metrics=list(_METRICS[f]),
            booleans=list(_BOOLEANS.get(f, ()))) for f in families])


def results_child(h, selected, *, index=1, descriptors=True, parent=None, schema=None):
    parent = parent or h.root
    assignment = dict(version=RESULTS_VERSION, handoff_ref=h.handoff, selector=selected)
    prepared = h.family.prepare_assignment(parent, 'results', assignment, h.scope, 'commission-function-results')
    sources = ['execution_blast_database_' + row['family'] + '_rows' for row in selected['projections']]
    if descriptors:
        sources.append(SAVED_INPUT_SOURCE)
    schema = schema or schema_for(*sources, 'execution_blast_database_acquisition', 'execution_blast_database_failures')
    from gene_annotation_episode.communication import _compile_closed_schema
    assert _compile_closed_schema(schema) == schema
    child = h.child(parent, 'results', prepared, schema, index=index)
    h.family.initialize(child)
    h.receipts.receive(child.episode_id, h.family.initial_references(child), kind='initial')
    return child


def connected_fixture(tmp_path, monkeypatch, program='blastn_vdb', *, nonzero=False, values=None, assignments=None,
        census=True, census_records=None, dependency_records=(), report_transform=None):
    if values is None:
        if program == 'blastn_vdb':
            values, assignments = whole_case()
        else:
            values, assignments = translated_case(), []
    values, assignments = deepcopy(values), deepcopy(assignments or [])
    native = deepcopy(values['search']['native']['report'])
    native['search_target']['db'] = 'target'
    if report_transform is not None:
        report_transform(native)
    query = 'ACGTACGT' if program == 'blastn_vdb' else 'PMAKPP'
    h = SyntheticHost(tmp_path, monkeypatch, program, nonzero=nonzero, sequence=query,
        query_bytes=('>q\n' + query + '\n').encode(), native_report=canonical({'BlastOutput2': [{'report': native}]}).encode())
    database = h.job['databases'][0]
    for row in values['dataset_records']:
        row['selected_input'] = dict(kind='alias', value=database['identity']['value'])
        row['snapshot'].update(release=database['identity']['release'], manifest_sha256=database['manifest_file']['sha256'])
    scientific = populate(values, assignments)
    scope = 'whole_sequence' if program == 'blastn_vdb' else 'feature'
    censuses = deepcopy(census_records) if census_records is not None else (
        [census_for(scientific, scope=scope, extra=program == 'blastn_vdb')] if census else [])
    # These fixture records describe the explicitly selected synthetic snapshot.
    # Keep the supplied dependency and sample relationships unchanged.
    for census_record in censuses:
        for row in census_record['datasets']:
            actual = next(d for d in values['dataset_records'] if d['dataset_key'] == row['dataset_key'])
            row.update(selected_input=deepcopy(actual['selected_input']), snapshot=deepcopy(actual['snapshot']))
    # This retained JSON is the explicit source of the supplied fixture facts.
    original = dict(fixture_kind='synthetic_source_records', datasets=values['dataset_records'],
        members=values['member_bindings'], metadata=values['reference_metadata'], assignments=assignments, dependencies=dependency_records,
        census=censuses, records=[dict(sequence=r['sequence']['symbols']) for r in values['reference_metadata'] if r['sequence']])
    facts = retain_source(h, original, 'function-source')
    document = dict(document_key='facts', artifact=dict(kind='received', **facts), format='json')
    unit = wire_fixture({k: values[k] for k in ('dataset_records', 'member_bindings', 'sequence_identity_bindings', 'feature_bindings', 'reference_metadata')})
    unit.update(search_key=address(), sequence_proofs=[], population_records=[], parsed_sources=[], metadata_bindings=[])
    for i, row in enumerate(unit['sequence_identity_bindings']):
        sequence = original['records'][i]['sequence']
        row['binding'].update(source_ref='facts', pointer=f'/records/{i}', linkage_source_ref='facts', linkage_pointer='')
        unit['sequence_proofs'].append(dict(binding_index=i, document_key='facts', representation='json_sequence', record_ordinal=None,
            sequence_pointer=f'/records/{i}/sequence', molecule='nt', sha256=hashlib.sha256(sequence.encode()).hexdigest(), length=len(sequence)))
    payload = dict(schema='native_blast_database_vdb_metadata_v1', documents=[document], searches=[unit])
    function = dict(schema='native_blast_vdb_function_metadata_v1', documents=[document], searches=[dict(search_key=address(),
        supplied_assignments=wire_fixture(assignments), dependency_records=wire_fixture(list(dependency_records)), census_records=wire_fixture(censuses))])
    selected = selection(scope=scope, census='census-1' if census else None)
    query_selected = query_selection(h)
    selected['metadata_inputs'] = [*query_selected['metadata_inputs'], metadata_input(h, payload, 'vdb'), metadata_input(h, function, 'vdb_function')]
    selected['retained_sources'] = [*query_selected['retained_sources'], facts]
    (tmp_path / 'synthetic-selected-inputs.json').write_text(canonical(dict(selection=selected, original_source=original,
        base_metadata=payload, function_metadata=function, native_report={'BlastOutput2': [{'report': native}]})))
    return h, selected


def capture(h, selected, *, index=1, descriptors=True):
    child = results_child(h, selected, index=index, descriptors=descriptors)
    outcome = h.select(child, 0, 'execution.results.collect')
    assert outcome['status'] == 'completed', outcome
    body = outcome['result']
    if body['preparation'] is not None:
        (h.tmp_path / f'diagnostics-{index}.json').write_text(canonical(_json(h.store, body['preparation']['diagnostics_artifact_ref'])))
    (h.tmp_path / f'receipt-{index}.json').write_text(canonical(body))
    return child, body


@pytest.mark.parametrize('program', ['blastn_vdb', 'tblastn_vdb'])
def test_selected_capture_populates_calculates_and_delivers_all_function_families(tmp_path, monkeypatch, program):
    h, selected = connected_fixture(tmp_path, monkeypatch, program)
    try:
        child, body = capture(h, selected)
        assert body['complete'], body['failures']
        assert body['version'] == 'native_blast_database_result_receipt_vdb_function_v1'
        assert body['calculation_input'] == {'mode': 'captured_inputs'} and body['reused_result_receipt'] is None
        assert body['observation'] is not None and body['capture']['status'] == 'complete'
        sheets = _json(h.store, body['preparation']['sheets_artifact_ref'])
        calculations = _json(h.store, body['preparation']['calculations_artifact_ref'])
        assert len(sheets['vdb_function']) == len(sheets['vdb']) == 1
        full = sheets['vdb_function'][0]['sheet']
        assert full['base_sheet'] == sheets['vdb'][0]['sheet']
        assert full['base_components'] == calculations['vdb'][0]['components']
        assert full['base_components']['population_components']['function_weight_model']['reason'] == 'vdb_function_weight_model_not_defined'
        rows = body['publication']['rows_by_family']
        assert all(rows[f] for f in FUNCTION_FAMILIES)
        functions = {r['identity']['function']['value']: r for r in rows['vdb_function']}
        weights = {key: metric(row, 'conditional_function_weight')['value'] for key, row in functions.items()}
        assert weights == pytest.approx({'A': .8, 'B': .2})
        if program == 'blastn_vdb':
            assert {key: metric(row, 'representation_adjusted_function_weight')['value'] for key, row in functions.items()} == pytest.approx({'A': .5, 'B': .5})
        assert all(r['publication_status'] == 'source_only' and r['observation_ref'] is None for family in FUNCTION_FAMILIES for r in rows[family])
        form, schema = h.returned(child)
        admitted = h.family.native_blast_database_returns.received_facts(h.root, schema)
        for family in FUNCTION_FAMILIES:
            assert admitted['execution_blast_database_' + family + '_rows'] == rows[family]
        descriptor, = admitted[SAVED_INPUT_SOURCE]
        assert h.family.native_blast_database_returns.resolve_saved_function_input(h.root, descriptor) == body
        assert h.family.native_blast_database_results.read_saved_function_input(descriptor, h.scope) == body
        proof = h.family.completion_for_action(child, body['operation_key'])
        assert proof is not None and h.family.verify_completion(child, proof)
        assert h.store.query_records('observation')['total'] == 0
        assert h.store.db.execute('SELECT COUNT(*) FROM runtime_actions WHERE episode_id=?', (child.episode_id,)).fetchone()[0] == 1
        assert len(list(h.workspace.rglob('synthetic-emitter-invoked'))) == 1
        (tmp_path / 'typed-return.json').write_text(canonical(dict(form=form, schema=schema, received=admitted, completion=proof)))
    finally:
        h.store.close()


def test_operation_descriptions_expose_selected_work_and_preserve_old_selector(tmp_path, monkeypatch):
    import asyncio
    from gene_annotation_episode.native_blast_database_results import operation_catalog
    from test_native_blast_vdb_function_recalculation import forbid_acquisition
    h, selected = connected_fixture(tmp_path, monkeypatch)
    try:
        reader = h.family.job_progress_provider.targets
        old = reader.describe_target(h.handoff, h.scope, selector=selector('search'))
        original = old['extractors'][1]
        assert 'parser' in original and 'calculation_input' not in original
        new = reader.describe_target(h.handoff, h.scope, selector=selected)['extractors'][1]
        assert new['function_sheet_population'].endswith('populate_native_blast_vdb_function_sheets')
        assert 'calculation_input' in new['return_fields'] and 'reused_result_receipt' in new['return_fields']
        child, body = capture(h, selected)
        original_catalog = operation_catalog(selector('search'))
        assert h.family.catalog(child) == original_catalog
        assert original_catalog[1]['description'] == 'Capture the complete original database bundle and return the assigned frozen numerical view.'
        h.returned(child)
        saved = h.family.native_blast_database_results.facts(child)[SAVED_INPUT_SOURCE][0]
        reused = reader.describe_target(h.handoff, h.scope, selector=selection(saved=saved, temperature=2))
        extract, = reused['extractors']
        assert not {'parser', 'input_population', 'sheet_population', 'function_sheet_population'} & extract.keys()
        assert extract['saved_input_validation'].endswith('resolve_saved_function_input')
        assert reused['status_operations'] == []
        saved_child = results_child(h, selection(saved=saved, temperature=2), index=2)
        assert [r['name'] for r in h.family.catalog(saved_child)] == ['execution.results.collect']
        assert 'saved function sheet' in h.family.catalog(saved_child)[0]['description']
        forbid_acquisition(h, monkeypatch)
        attempted_status = asyncio.run(h.family.execute(saved_child, 'execution.results.status', {}, 'unselected-status'))
        assert attempted_status['status'] == 'invalid'
        assert attempted_status['feedback']['code'] == 'execution_operation_not_available'
        assert h.store.db.execute('SELECT COUNT(*) FROM runtime_actions WHERE episode_id=?', (saved_child.episode_id,)).fetchone()[0] == 0
        assert h.family.native_blast_database_results.facts(saved_child)['execution_blast_database_result_refs'] == []
        assert old == reader.describe_target(h.handoff, h.scope, selector=selector('search'))
    finally:
        h.store.close()


@pytest.mark.parametrize('fixture_name,grouping,policy,corrected', [
    ('unresolved_census_edge_baseline', 'target_duplicates_only', 'qualify_separate', {'A': .5, 'B': .5}),
    ('unresolved_census_edge_baseline', 'known_source_blocks', 'qualify_separate', {'A': .8, 'B': .2}),
    ('unresolved_census_edge_baseline', 'known_source_blocks', 'withhold_weights', None),
    ('census_observed_sample_contradiction', 'known_source_blocks', 'qualify_separate', None),
])
def test_census_dependency_policy_and_sample_conflict_cross_actual_parent_return(
        tmp_path, monkeypatch, fixture_name, grouping, policy, corrected):
    from test_blast_vdb_function_census_relations import fixture
    supplied = fixture(fixture_name)['fixture_input']
    values = {k: v for k, v in supplied['vdb_sheet'].items() if k != 'schema'}
    h, selected = connected_fixture(tmp_path, monkeypatch, values=values, assignments=supplied['supplied_assignments'],
        census_records=supplied['census_records'], dependency_records=supplied['dependency_records'])
    selected['vdb_function_model'].update(grouping_model=grouping, unknown_source_dependency=policy)
    try:
        child, body = capture(h, selected)
        assert body['complete'], body['failures']
        sheets = _json(h.store, body['preparation']['sheets_artifact_ref'])
        calculations = _json(h.store, body['preparation']['calculations_artifact_ref'])
        full = sheets['vdb_function'][0]['sheet']
        components = calculations['vdb_function'][0]['components']
        census_result, = components['census_results']
        conflict = fixture_name == 'census_observed_sample_contradiction'
        if conflict:
            assert full['entities'][2]['origin_sample_keys'] == ['S3']
            assert full['census_records'][0]['entities'][2]['origin_sample_keys'] == ['S1']
            assert census_result['status'] == 'incompatible'
            assert not census_result['correction_available']
            assert 'blast_vdb_function_census_membership_unverified' in {i['code'] for i in census_result['issues']}
        else:
            assert full['census_records'][0]['dependency_records'][0]['sources'] == []
            assert census_result['correction_available'] == (corrected is not None)
            assert census_result['status'] == ('available' if corrected is not None else 'unavailable')
        assert census_result['enumeration_complete'] is True
        assert components['status'] == ('complete' if grouping == 'target_duplicates_only' else 'partial')
        form, schema = h.returned(child)
        received = h.family.native_blast_database_returns.received_facts(h.root, schema)
        for family in FUNCTION_FAMILIES:
            assert received['execution_blast_database_' + family + '_rows'] == body['publication']['rows_by_family'][family]
        functions = {r['identity']['function']['value']: r for r in received['execution_blast_database_vdb_function_rows']}
        expected = {'A': 1/3, 'B': 1/3, 'C': 1/3} if conflict else {'A': .8, 'B': .2}
        assert {k: metric(r, 'conditional_function_weight')['value'] for k, r in functions.items()} == pytest.approx(expected)
        if corrected is None:
            for row in functions.values():
                cell = metric(row, 'representation_adjusted_function_weight')
                assert cell['value'] is None and cell['status'] == ('incompatible' if conflict else 'unavailable')
        else:
            assert {k: metric(r, 'representation_adjusted_function_weight')['value'] for k, r in functions.items()} == pytest.approx(corrected)
        assert h.store.query_records('observation')['total'] == 0
        (tmp_path / 'census-policy-typed-return.json').write_text(canonical(dict(form=form, schema=schema, received=received)))
    finally:
        h.store.close()


def numerical_rows(sheet, selected_model):
    """Pure port fixture, distinct from the connected capture tests above."""
    from gene_annotation_episode import native_blast_database_result_worker as worker
    from test_native_blast_database_result_worker import sheet_set, collection_for, ATTEMPT
    base = sheet['base_sheet']
    collection = collection_for(base['search'])
    collection['searches'] = [deepcopy(base['search'])]
    sheets = sheet_set(collection, vdb_sheet=deepcopy(base))
    sheets.update(schema=worker._FUNCTION_SHEETS, vdb_function=[dict(search_key=base['search']['search_key'], sheet=deepcopy(sheet))])
    components = worker.calculate_native_blast_database_sheets(sheets, sequence_model=None, vdb_function_model=selected_model)
    rows = worker.build_native_blast_database_rows(bundle_identity=ATTEMPT, calculation_id='a' * 64, sheet_set=sheets, calculations=components)
    function_rows = [r for r in rows if r['family'] in FUNCTION_FAMILIES]
    for row in function_rows:
        for cell in row['measurements'] + row['booleans']:
            assert cell['value'] == worker._at(components, cell['component_pointer'])
            assert any(cell['component_pointer'].startswith(ref['pointer'] + '/') for ref in row['component_refs'])
    return sheets, components, function_rows


@pytest.mark.parametrize('case_name', ['temperature1', 'temperature2', 'source_cap', 'census_bridge',
    'translated_siblings', 'underflow', 'out_of_range', 'zero_prior', 'unassigned', 'missing_snapshot', 'wrong_snapshot'])
def test_actual_calculator_values_survive_typed_row_projection(tmp_path, case_name):
    from test_blast_vdb_function_calculators import case, bridge_case, function, FROZEN
    expected, corrected = None, None
    selected_model = model()
    if case_name in ('temperature1', 'temperature2', 'zero_prior', 'missing_snapshot', 'wrong_snapshot'):
        sheet = json.loads((FROZEN / 'whole_sequence.json').read_text())
        selected_model = model(temperature=2 if case_name == 'temperature2' else 1, census='census-1')
        expected = {'A': 2/3, 'B': 1/3} if case_name == 'temperature2' else {'A': .8, 'B': .2}
        corrected = {'A': 1/3, 'B': 2/3} if case_name == 'temperature2' else {'A': .5, 'B': .5}
        if case_name == 'zero_prior':
            selected_model['function_priors'] = [dict(assignment_scope='whole_sequence', namespace='fixture_function', function=function(k), weight=w) for k,w in [('A',1),('B',0)]]
            expected = corrected = {'A':1, 'B':0}
        if case_name in ('missing_snapshot', 'wrong_snapshot'):
            from gene_annotation_episode.blast_vdb_function_inputs import populate_blast_vdb_function_sheet
            census = deepcopy(sheet['census_records'])
            census[0]['datasets'][0]['snapshot']['manifest_sha256'] = None if case_name == 'missing_snapshot' else '0' * 64
            sheet = populate_blast_vdb_function_sheet(sheet['base_sheet'], supplied_assignments=sheet['assignment_records'],
                dependency_records=sheet['dependency_records'], census_records=census)
            corrected = None
    elif case_name == 'source_cap':
        values, assignments = case(samples=('S1','S1','S2'))
        sheet = populate(values, assignments)
        selected_model = model(grouping='known_source_blocks')
        expected = {'A':3/4, 'B':1/4}
    elif case_name == 'census_bridge':
        sheet = bridge_case(); selected_model = model(grouping='known_source_blocks', census='census-1')
        expected = {'A':1/3, 'B':1/3, 'C':1/3}; corrected = {'A':1/7, 'B':2/7, 'C':4/7}
    elif case_name == 'translated_siblings':
        sheet = json.loads((FROZEN / 'translated_siblings.json').read_text())
        selected_model = model(temperature=2, scope='feature'); expected = {'A':2/3, 'B':1/3}
    else:
        values, assignments = case(scores=(2000,0) if case_name == 'underflow' else (1,0) if case_name == 'out_of_range' else (20,20,20),
            labels=('A','B',None) if case_name == 'unassigned' else ('A','B'))
        sheet = populate(values, assignments)
        if case_name == 'out_of_range': selected_model = model(temperature=1e-320)
        if case_name == 'unassigned': expected = {'A':.5,'B':.5}
    original = deepcopy(sheet)
    sheets, components, rows = numerical_rows(sheet, selected_model)
    functions = {r['identity']['function']['value']:r for r in rows if r['family'] == 'vdb_function'}
    if expected is not None:
        assert {k:metric(r,'conditional_function_weight')['value'] for k,r in functions.items()} == pytest.approx(expected)
    if corrected is not None:
        assert {k:metric(r,'representation_adjusted_function_weight')['value'] for k,r in functions.items()} == pytest.approx(corrected)
    if case_name in ('missing_snapshot','wrong_snapshot'):
        assert all(metric(r,'representation_adjusted_function_weight')['value'] is None for r in functions.values())
    if case_name == 'underflow':
        linear = metric(functions['B'], 'conditional_function_weight')
        assert linear['value'] is None and linear['status'] == 'unavailable' and linear['reason'] == 'linear_underflow'
        assert metric(functions['B'], 'log2_conditional_function_weight')['value'] == -2000
    if case_name == 'out_of_range':
        assert all(metric(r,'function_mass')['reason'] == 'arithmetic_out_of_range' and metric(r,'function_mass')['value'] is None for r in functions.values())
    if case_name == 'zero_prior':
        assert metric(functions['B'],'conditional_function_weight')['value'] == 0
        assert metric(functions['B'],'log2_conditional_function_weight')['value'] is None
        assert metric(functions['B'],'log2_conditional_function_weight')['reason'] == 'not_measured'
    if case_name == 'unassigned':
        summary, = [r for r in rows if r['family'] == 'vdb_function_summary']
        assert metric(summary, 'unassigned_target_unit_count')['value'] == 1
        assert metric(summary, 'unknown_reference_kernel_fraction')['value'] == pytest.approx(1/3)
    assert sheet == original
    (tmp_path / 'numerical-row-oracle.json').write_text(canonical(dict(sheet=sheet, model=selected_model, components=components, rows=rows)))


@pytest.mark.parametrize('mode', ['failed_native', 'malformed_sibling', 'zero_hits'])
def test_partial_native_work_and_explicit_zero_keep_distinct_receipts(tmp_path, monkeypatch, mode):
    transform = (lambda report: report['results']['search']['hits'][0]['hsps'].append(None)) if mode == 'malformed_sibling' else None
    if mode == 'zero_hits':
        native = dict(program='blastn', version='BLASTN 2.17.0+', search_target={'db':'target'}, params={},
            results={'search':dict(query_id='q', query_title='q', query_len=8, hits=[])})
        h = SyntheticHost(tmp_path, monkeypatch, 'blastn_vdb', sequence='ACGTACGT', query_bytes=b'>q\nACGTACGT\n',
            native_report=canonical({'BlastOutput2':[{'report':native}]}).encode())
        selected = selection(census=None)
    else:
        h, selected = connected_fixture(tmp_path, monkeypatch, nonzero=mode == 'failed_native', report_transform=transform)
    try:
        child, body = capture(h, selected)
        assert body['capture']['status'] == 'complete'
        calc = _json(h.store, body['preparation']['calculations_artifact_ref'])['vdb_function'][0]['components']
        if mode == 'zero_hits':
            assert body['complete'] and calc['status'] == 'no_reported_hits'
            assert all(not rows for rows in body['publication']['rows_by_family'].values())
        else:
            assert body['complete'] is (mode == 'malformed_sibling') and calc['status'] == 'partial'
            assert body['publication']['rows_by_family']['vdb_function']
            assert all(r['native_status'] == 'partial' for r in body['publication']['rows_by_family']['vdb_function'])
            assert (h.family.completion_for_action(child, body['operation_key']) is None) is (mode == 'failed_native')
        form, schema = h.returned(child)
        assert h.family.native_blast_database_returns.received_facts(h.root, schema)['execution_blast_database_failures'] == body['failures']
    finally:
        h.store.close()


@pytest.mark.parametrize('program',['blastn_vdb','tblastn_vdb'])
def test_legacy_vdb_components_rows_and_closed_forms_equal_released_before_bytes(tmp_path,program):
    import importlib.util
    import sys
    from gene_annotation_episode import native_blast_database_result_worker as worker
    from gene_annotation_episode import native_blast_database_result_views as views
    from test_native_blast_database_result_worker import vdb_sheets,ATTEMPT
    from test_blast_vdb_calculators import translated_case as old_translated
    directory=Path(__file__).resolve().parents[1]/'verification/tool_graders_blast_vdb_function_integration_2026-10-26_347/before'
    modules={}
    for name in ('native_blast_database_result_views','native_blast_database_result_worker'):
        module_name='gene_annotation_episode._before347_'+name
        spec=importlib.util.spec_from_file_location(module_name,directory/(name+'.py'))
        module=importlib.util.module_from_spec(spec);sys.modules[module_name]=module
        spec.loader.exec_module(module);modules[name]=module
    previous=modules['native_blast_database_result_worker'];old_views=modules['native_blast_database_result_views'];previous._views=old_views
    sheets=vdb_sheets(None if program=='blastn_vdb' else old_translated(reverse=True))
    old=previous.calculate_native_blast_database_sheets(sheets,sequence_model=None)
    current=worker.calculate_native_blast_database_sheets(sheets,sequence_model=None)
    assert canonical(current)==canonical(old)
    args=dict(bundle_identity=ATTEMPT,calculation_id='a'*64,sheet_set=sheets)
    old_rows=previous.build_native_blast_database_rows(calculations=old,**args)
    new_rows=worker.build_native_blast_database_rows(calculations=current,**args)
    assert canonical(new_rows)==canonical(old_rows)
    assert current['vdb'][0]['components']['population_components']['function_weight_model']['reason']=='vdb_function_weight_model_not_defined'
    assert 'vdb_function' not in current and 'vdb_function' not in sheets
    assert views.native_blast_database_metric_definitions(include_vdb_function=False)==old_views.native_blast_database_metric_definitions()
    for source,descriptor in old_views.native_blast_database_fact_sources().items():
        assert views.native_blast_database_fact_sources()[source]==descriptor
    (tmp_path/'legacy-byte-equivalence.json').write_text(canonical(dict(sheets=sheets,calculations=current,rows=new_rows)))


def test_versions_are_explicit_and_old_selection_does_not_import_new_science(tmp_path):
    import os, subprocess, sys
    from gene_annotation_episode.native_blast_database_result_views import validate_native_blast_database_result_selector as validate
    new=selection(census=None)
    for program in ('psiblast','deltablast','rpsblast','rpstblastn'):
        with pytest.raises(ValueError):validate(new,program=program)
    old=selector('search')
    old['projections']=deepcopy(new['projections'])
    with pytest.raises(ValueError):validate(old,program='blastn_vdb')
    for field in ('calculation_input','vdb_function_model'):
        invalid=deepcopy(new);del invalid[field]
        with pytest.raises(ValueError):validate(invalid,program='blastn_vdb')
    bad=deepcopy(new);bad['vdb_function_model']['version']='future_v1'
    with pytest.raises(ValueError):validate(bad,program='blastn_vdb')
    script='''import json,sys
from gene_annotation_episode.native_blast_database_result_views import validate_native_blast_database_result_selector
value=json.loads(sys.argv[1]);validate_native_blast_database_result_selector(value,program='blastn_vdb')
assert not any('blast_vdb_function' in name for name in sys.modules)
print('legacy selector loaded no candidate-function scientific modules')
'''
    result=subprocess.run([sys.executable,'-B','-c',script,canonical(selector('search'))],capture_output=True,text=True,check=False)
    assert result.returncode==0,result.stderr
    (tmp_path/'legacy-import-closure.txt').write_text(result.stdout)
