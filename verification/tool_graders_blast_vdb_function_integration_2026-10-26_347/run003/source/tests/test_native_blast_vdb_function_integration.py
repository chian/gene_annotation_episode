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
    catalog = native_blast_database_metric_definitions()
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
    child = h.child(parent, 'results', prepared, schema, index=index)
    h.family.initialize(child)
    h.receipts.receive(child.episode_id, h.family.initial_references(child), kind='initial')
    return child


def connected_fixture(tmp_path, monkeypatch, program='blastn_vdb', *, nonzero=False, values=None, assignments=None, census=True):
    if values is None:
        if program == 'blastn_vdb':
            values, assignments = whole_case()
        else:
            values, assignments = translated_case(), []
    values, assignments = deepcopy(values), deepcopy(assignments or [])
    native = deepcopy(values['search']['native']['report'])
    native['search_target']['db'] = 'target'
    query = 'ACGTACGT' if program == 'blastn_vdb' else 'PMAKPP'
    h = SyntheticHost(tmp_path, monkeypatch, program, nonzero=nonzero, sequence=query,
        query_bytes=('>q\n' + query + '\n').encode(), native_report=canonical({'BlastOutput2': [{'report': native}]}).encode())
    database = h.job['databases'][0]
    for row in values['dataset_records']:
        row['selected_input'] = dict(kind='alias', value=database['identity']['value'])
        row['snapshot'].update(release=database['identity']['release'], manifest_sha256=database['manifest_file']['sha256'])
    scientific = populate(values, assignments)
    scope = 'whole_sequence' if program == 'blastn_vdb' else 'feature'
    censuses = [census_for(scientific, scope=scope, extra=program == 'blastn_vdb')] if census else []
    # This retained JSON is the explicit source of the supplied fixture facts.
    original = dict(fixture_kind='synthetic_source_records', datasets=values['dataset_records'],
        members=values['member_bindings'], metadata=values['reference_metadata'], assignments=assignments,
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
        supplied_assignments=wire_fixture(assignments), dependency_records=[], census_records=wire_fixture(censuses))])
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
        h.returned(child)
        saved = h.family.native_blast_database_results.facts(child)[SAVED_INPUT_SOURCE][0]
        reused = reader.describe_target(h.handoff, h.scope, selector=selection(saved=saved, temperature=2))
        extract, = reused['extractors']
        assert not {'parser', 'input_population', 'sheet_population', 'function_sheet_population'} & extract.keys()
        assert extract['saved_input_validation'].endswith('resolve_saved_function_input')
        assert reused['status_operations'] == []
        assert old == reader.describe_target(h.handoff, h.scope, selector=selector('search'))
    finally:
        h.store.close()
