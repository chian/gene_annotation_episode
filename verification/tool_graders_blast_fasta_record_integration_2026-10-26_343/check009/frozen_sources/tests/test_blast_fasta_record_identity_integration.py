"""343 supplied-record integration, with synthetic emission and original forms.

No native database search or real scheduler submission occurs. The production
producer/capture, bounded workers, saved reuse and typed parent admission run.
"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import blast_fasta_record_identity as fasta
from gene_annotation_episode import native_blast_standard_database_contracts as sc
from gene_annotation_episode import native_blast_standard_database_result_views as sv
from gene_annotation_episode import native_blast_standard_database_calculators as calc
from gene_annotation_episode import native_blast_standard_database_result_worker as sw
from gene_annotation_episode import native_blast_standard_database_metadata as sm
from gene_annotation_episode import native_blast_database_result_views as nv
from gene_annotation_episode import native_blast_database_result_worker as nw
from gene_annotation_episode import native_blast_database_metadata as nm
from gene_annotation_episode import blast_sequence_database as sequence
import test_native_blast_standard_database_metadata as sf
import test_native_blast_standard_database_result_worker as sr
import test_native_blast_database_result_worker as nr
from test_native_blast_standard_database_episode_binding import SyntheticHost as StandardHost
from test_native_blast_database_episode_binding import SyntheticHost as NativeHost
from test_native_blast_standard_database_results import query_selection

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / 'verification/tool_graders_blast_fasta_record_integration_2026-10-26_343'
V2 = 'native_blast_database_sequence_metadata_v2'
Q = ('completeness_fraction', 'contamination_fraction', 'contig_count', 'contig_n50', 'total_sequence_length')


def save(path, value):
    path.write_bytes(sf.encoded(value))


def rows(request):
    return [json.loads(line) for line in (Path(request['output_directory']) / 'rows.ndjson').read_bytes().splitlines()]


def values(row):
    return {r['name']: r['value'] for r in row['measurements']}


def quality(payload, *, same=True, equal=False):
    """Explicit synthetic supplied fractions, not inferred from FASTA headers."""
    for i, row in enumerate(payload['searches'][0]['reference_metadata']):
        if same:
            row['functions'][0]['function'] = 'synthetic-same-function'
        row['assembly'] = dict(accession='synthetic-assembly-' + str(i), completeness_fraction=.9 if i == 0 or equal else .6,
            contamination_fraction=None, contig_count=None, contig_n50=None, total_sequence_length=None,
            quality_method='synthetic-supplied-measurement', quality_version=None,
            measurement_methods={k: None for k in Q}, source='record-assignments', linkage_source='record-assignments')
    return payload


def standard_inputs(*, supplied_quality=False, same=True, equal=False):
    inputs = sf.fixture()
    sf.subject(inputs, 'ACDEFGHI')
    payload = sf.record_metadata(inputs)
    if supplied_quality:
        quality(payload, same=same, equal=equal)
    sf.add_metadata(inputs, payload, 'sequence_database', key='records-v2')
    return inputs


def assert_quality(actual, *, equal=False, same=True):
    selected = [r for r in actual if r['family'] == 'sequence_record_quality']
    assert len(selected) == len({r['record_key'] for r in selected}) == 4
    assert not [r for r in actual if r['family'] == 'sequence_quality']
    assert {r['identity']['function'] for r in selected} == ({None, 'synthetic-same-function'} if same else {None, 'F', 'G'})
    for row in selected:
        source = row['identity']['assembly_source']
        assert set(source) == {'source_ref', 'pointer', 'record_locator'} and source['pointer'] == ''
        ordinal = source['record_locator']['record_ordinal']
        assert type(ordinal) is int and source['record_locator']['kind'] == 'fasta_record'
        assert values(row) == dict(completeness_fraction=.9 if ordinal == 0 or equal else .6,
            contamination_fraction=None, contig_count=None, contig_n50=None, total_sequence_length=None)
        assert row['booleans'] == []
        assert any('/reference_metadata/' in p['pointer'] for p in row['component_refs'])
        assert any('/associations/' in p['pointer'] for p in row['component_refs'])
    assert len({r['identity']['assembly_source']['source_ref'] for r in selected}) == 1
    return selected


def forbid_reparse(monkeypatch):
    def forbidden(*a, **kw):
        pytest.fail('saved reuse attempted parsing, population, acquisition or execution')
    for module, names in [(fasta, ('parse_blast_fasta_source_records', 'parse_sequences')),
            (sm, ('parse_sequences', 'prepare_standard_blast_database_inputs', 'populate_standard_blast_database_sheets')),
            (nm, ('parse_blast_fasta_source_records', 'parse_sequences', 'prepare_native_blast_database_inputs', 'populate_native_blast_database_sheets')),
            (sw, ('parse_blast_report_collection',)), (nw, ('parse_blast_report_collection',)),
            (socket, ('socket', 'getaddrinfo')), (subprocess, ('run', 'Popen'))]:
        for name in names:
            monkeypatch.setattr(module, name, forbidden)


def test_retained339_exact_wire_real_standard_worker_and_saved_T2(tmp_path, monkeypatch):
    retained = ROOT / 'verification/tool_graders_blast_fasta_record_metadata_2026-10-26_340/check003/temporary/pytest/test_record_v2_retained337_byt0'
    original = json.loads((retained / 'supplied_inputs.json').read_bytes())
    inputs = original['inputs']
    inputs.update(contents={k: bytes.fromhex(v) for k, v in original['contents_hex'].items()},
        subject_contents={k: bytes.fromhex(v) for k, v in original['subject_contents_hex'].items()})
    public = ROOT / 'verification/tool_graders_blast_fasta_record_public_associations_2026-10-26_339/check008'
    descriptor = json.loads((public/'new_descriptor_v2.json').read_bytes())
    supplied = next(r for r in inputs['metadata_payloads'] if r['descriptor']['schema_id'] == V2)
    assert supplied['descriptor'] == descriptor
    assert inputs['contents'][descriptor['artifact_ref']] == (public/'new_wire_payload_v2.json').read_bytes()
    request = sr.request_for(tmp_path, inputs=inputs)
    manifest, diagnostics = sr.invoke(request)
    assert manifest['status'] != 'failed', diagnostics
    actual = rows(request)
    assert [values(r)['native_score_bits'] for r in actual if r['family'] == 'hsp'] == [20, 18]
    functions = {r['identity']['function']: values(r) for r in actual if r['family'] == 'sequence_function'}
    assert {k: v['function_mass'] for k, v in functions.items()} == {'F': 1, 'G': .25}
    assert {k: v['unadjusted_probability'] for k, v in functions.items()} == {'F': .8, 'G': .2}
    before = {p.name: p.read_bytes() for p in Path(request['output_directory']).iterdir()}
    revised = sr.reuse(request, manifest, tmp_path/'generation-2')
    with monkeypatch.context() as blocked:
        forbid_reparse(blocked)
        reused, diagnostics = sr.invoke(revised)
    assert reused['status'] != 'failed', diagnostics
    assert [values(r)['unadjusted_probability'] for r in rows(revised) if r['family'] == 'sequence_function'] == pytest.approx([2/3, 1/3])
    assert before == {p.name: p.read_bytes() for p in Path(request['output_directory']).iterdir()}
    assert manifest['input_identity'] == reused['input_identity']
    assert [r['record_key'] for r in actual] == [r['record_key'] for r in rows(revised)]
    assert any(r['module'] == 'gene_annotation_episode.blast_fasta_record_identity' for r in request['implementation']['files'])


@pytest.mark.parametrize('equal', [False, True])
def test_standard_quality_actual_worker_distinct_records(tmp_path, equal):
    request = sr.request_for(tmp_path, inputs=standard_inputs(supplied_quality=True, equal=equal))
    manifest, diagnostics = sr.invoke(request)
    assert manifest['status'] == 'complete', diagnostics
    assert_quality(rows(request), equal=equal)
    save(tmp_path/'quality-oracle.json', dict(record_ordinals=[0, 1], supplied_fractions=[.9, .9 if equal else .6], rows=rows(request)))


def native_request(tmp_path, program):
    inputs = standard_inputs(supplied_quality=True, same=False)
    document = sf.report(program)
    request = nr.request_fixture(tmp_path, program, native_report=sf.encoded(document), query_bytes=b'>q\nACDEFGHI\n',
        metadata_payload=dict(schema=V2, documents=[], searches=[]),
        metadata_tuples=[dict(input_key='metadata', consumer='sequence_database', schema_id=V2)])
    # Explicit supplied metadata is adapted only by the exact native description
    # values; source bytes, original FASTA file and ordinal addresses stay intact.
    payloads = deepcopy(inputs['metadata_payloads'])
    payloads = [p for p in payloads if p['descriptor']['consumer'] == 'sequence_database']
    if program == 'deltablast':
        p = sf.query_payload()
        p['documents'] = deepcopy(payloads[0]['payload']['documents'])
        p['search_bindings'] = [dict(search_key=sf.address(), stage='sequence_database', biological_round=None,
            database_key='target', input_pssm_key=None, provenance=dict(source_ref='record-assignments', pointer=''))]
        sf.add_metadata(inputs, p, 'query_identity', key='delta-stage')
        payloads.append(deepcopy(inputs['metadata_payloads'][-1]))
    for i, source in enumerate(inputs['artifact_catalog']['retained_sources']):
        path = tmp_path / ('retained-' + str(i))
        path.write_bytes(inputs['contents'][source['artifact_ref']])
        request['retained_sources'].append({**source, 'path': str(path)})
    request['metadata_descriptors'].extend(p['descriptor'] for p in payloads)
    request['calculation_id'] = nw.native_blast_database_calculation_identity(input_identity=nw.native_blast_database_input_identity(request),
        input_implementation_sha256=request['implementation']['manifest_sha256'], sequence_model=None,
        implementation_manifest_sha256=request['implementation']['manifest_sha256'])['calculation_id']
    return request


@pytest.mark.parametrize('program', ['psiblast', 'deltablast'])
def test_native_actual_worker_record_quality_and_saved_iteration_reuse(tmp_path, monkeypatch, program):
    request = native_request(tmp_path, program)
    calls = []
    actual_iteration = nw._iteration.calculate_blast_iteration_components
    actual_sequence = sequence.calculate_blast_sequence_database_components
    def iteration_once(*args, **kwargs):
        calls.append('iteration')
        return actual_iteration(*args, **kwargs)
    def sequence_once(*args, **kwargs):
        calls.append('sequence')
        return actual_sequence(*args, **kwargs)
    monkeypatch.setattr(nw._iteration, 'calculate_blast_iteration_components', iteration_once)
    monkeypatch.setattr(sequence, 'calculate_blast_sequence_database_components', sequence_once)
    manifest = nr.run_request(tmp_path, request)
    assert manifest['status'] != 'failed', manifest['failures']
    assert calls == ['iteration', 'sequence']
    first = assert_quality(rows(request), same=False)
    assert [values(r)['function_mass'] for r in rows(request) if r['family'] == 'sequence_function'] == [1, .25]
    assert [values(r)['unadjusted_probability'] for r in rows(request) if r['family'] == 'sequence_function'] == [.8, .2]
    sheet = json.loads((Path(request['output_directory'])/'sheets.json').read_bytes())
    assert [r['binding']['record_locator']['record_ordinal'] for r in sheet['iteration']['sequence_metadata'][0]['sequence_identity_bindings']] == [0, 1]
    before = {p.name: p.read_bytes() for p in Path(request['output_directory']).iterdir()}
    revised = nr.reuse_request(request, manifest)
    with monkeypatch.context() as blocked:
        forbid_reparse(blocked)
        reused = nr.run_request(tmp_path, revised, name='reuse.json')
    assert reused['status'] != 'failed', reused['failures']
    assert calls == ['iteration', 'sequence', 'iteration', 'sequence']
    second = assert_quality(rows(revised), same=False)
    assert [values(r)['unadjusted_probability'] for r in rows(revised) if r['family'] == 'sequence_function'] == pytest.approx([2/3, 1/3])
    assert [(r['record_key'], values(r)) for r in first] == [(r['record_key'], values(r)) for r in second]
    assert before == {p.name: p.read_bytes() for p in Path(request['output_directory']).iterdir()}
    assert manifest['input_identity'] == reused['input_identity']
    assert any(r['module'] == 'gene_annotation_episode.blast_fasta_record_identity' for r in request['implementation']['files'])


def host_selection(h, *, same=True):
    inputs = standard_inputs(supplied_quality=True, same=same)
    payload = deepcopy(next(r['payload'] for r in inputs['metadata_payloads'] if r['descriptor']['consumer'] == 'sequence_database'))
    selection = query_selection(h)
    for document in payload['documents']:
        original = document['artifact']
        artifact = h.store.artifact(inputs['contents'][original['artifact_ref']], 'text/plain' if document['format'] == 'fasta' else 'application/json')
        ref = h.store.put('source', dict(provider='caller', accession=document['document_key'], uri=None,
            artifact_ref=artifact, text_ref=None, request_ref=None, version='synthetic_v1', retrieved_at=None), origin='caller')['id']
        record = h.store.get(artifact)
        document['artifact'] = dict(kind='received', source_ref=ref, artifact_ref=artifact, sha256=record['sha256'], size_bytes=record['size'])
        selection['retained_sources'].append({k: v for k, v in document['artifact'].items() if k != 'kind'})
        h.receipts.receive(h.root.episode_id, [ref, artifact], kind='initial')
    artifact = h.store.artifact(sf.encoded(payload), 'application/json')
    record = h.store.get(artifact)
    selection['metadata_inputs'].append(dict(input_key='record-input', consumer='sequence_database', schema_id=V2,
        artifact_ref=artifact, sha256=record['sha256'], size_bytes=record['size']))
    h.receipts.receive(h.root.episode_id, [artifact], kind='initial')
    selection['projections'].extend([dict(family='sequence_record_quality', rows=dict(offset=0, limit=10), metrics=['completeness_fraction'], booleans=[]),
        dict(family='sequence_function', rows=dict(offset=0, limit=10), metrics=['function_mass', 'unadjusted_probability'], booleans=[])])
    return selection, payload


@pytest.mark.parametrize('program,same', [('blastp', True), ('blastp', False), ('psiblast', True), ('deltablast', True)])
def test_actual_child_worker_original_typed_parent_return_and_frozen_projection(tmp_path, monkeypatch, program, same):
    standard = program == 'blastp'
    host = StandardHost if standard else NativeHost
    h = host(tmp_path, monkeypatch, program, query_bytes=b'>q\nACDEFGHI\n', sequence='ACDEFGHI',
        native_report=sf.encoded(sf.report(program)), metadata=dict(schema=V2, documents=[], searches=[]),
        tuples=[dict(input_key='metadata', consumer='sequence_database', schema_id=V2)])
    try:
        selection, payload = host_selection(h, same=same)
        if not standard:
            selection['version'] = 'native_blast_database_result_selector_v1'
        child = h.results(selection)
        outcome = h.select(child, 0, 'execution.results.collect')
        assert outcome['status'] == 'completed', outcome
        body = outcome['result']
        assert body['complete'], body['failures']
        family = 'native_blast_standard_database' if standard else 'native_blast_database'
        returned, schema = h.returned(child)
        facts = getattr(h.family, family + '_returns').received_facts(h.root, schema)
        key = 'execution_blast_' + ('standard_database' if standard else 'database') + '_sequence_record_quality_rows'
        published = facts[key]
        assert len(published) == len({r['record_key'] for r in published}) == 4
        for row in published:
            ordinal = row['identity']['assembly_source']['record_locator']['record_ordinal']
            assert values(row) == {'completeness_fraction': (.9, .6)[ordinal]}
            assert row['booleans'] == [] and row['observation_ref'] is None
            assert row['publication_status'] == 'source_only'
        function_key = key.replace('sequence_record_quality', 'sequence_function')
        assert {r['identity']['function']: values(r) for r in facts[function_key]} == (
            {'synthetic-same-function': {'function_mass': 1.25, 'unadjusted_probability': 1}} if same else
            {'F': {'function_mass': 1, 'unadjusted_probability': .8}, 'G': {'function_mass': .25, 'unadjusted_probability': .2}})
        save(tmp_path/'original-parent-form.json', returned)
        save(tmp_path/'original-parent-schema.json', schema)
        save(tmp_path/'received-parent-facts.json', facts)
        save(tmp_path/'selected-v2-wire.json', payload)
        save(tmp_path/'selected-selector.json', selection)
        save(tmp_path/'actual-result.json', body)
        # The native host's fresh import inventory must match the worker closure;
        # successful actual worker invocation above checks this across processes.
        count = len(list(h.workspace.rglob('synthetic-emitter-invoked')))
        assert count == 1
        module = __import__('gene_annotation_episode.' + family + '_result_publication', fromlist=['x'])
        prepared = body['preparation']
        frozen = module._validate_preparation(h.store, child, prepared)
        request, manifest = frozen['request'], frozen['manifest']
        revised = sr.reuse(request, manifest, tmp_path/'received-T2') if standard else nr.reuse_request(request, manifest)
        with monkeypatch.context() as blocked:
            forbid_reparse(blocked)
            reused = sr.invoke(revised)[0] if standard else nr.run_request(tmp_path, revised, name='received-reuse.json')
        assert reused['status'] != 'failed', reused['failures']
        if not same:
            assert [values(r)['unadjusted_probability'] for r in rows(revised) if r['family'] == 'sequence_function'] == pytest.approx([2/3, 1/3])
        before_rows = module._full_rows(h.store, prepared, frozen)
        document_roles = ('inputs', 'collection', 'calculations', 'sheets') if standard else ('inputs', 'collection', 'calculations')
        original_documents = tuple(json.loads(h.store.get_artifact(frozen['grading']['artifact_refs'][role])) for role in document_roles)
        revised_documents = tuple(json.loads((Path(revised['output_directory'])/(role+'.json')).read_bytes()) for role in document_roles)
        for old_row, new_row in zip([r for r in before_rows if r['family'] == 'hsp'], [r for r in rows(revised) if r['family'] == 'hsp']):
            assert old_row['record_key'] == new_row['record_key'] and old_row['calculation_id'] != new_row['calculation_id']
            assert module._hsp_payload(h.store, child, prepared, frozen, old_row, original_documents) == module._hsp_payload(
                h.store, child, prepared, frozen, new_row, revised_documents)
        save(tmp_path/'received-T2-manifest.json', reused)
        assert h.store.query_records('observation')['total'] == 2
        def forbidden(*a, **kw): pytest.fail('frozen projection attempted worker or calculation')
        monkeypatch.setattr(calc, 'calculate_standard_blast_database_sheets', forbidden)
        monkeypatch.setattr(nw, 'calculate_native_blast_database_sheets', forbidden)
        monkeypatch.setattr(module, 'run_local_job', forbidden)
        validate = getattr(module, 'validate_standard_blast_database_publication' if standard else 'validate_native_blast_database_publication')
        assert validate(h.store, context=child, publication=body['publication']) == body['publication']
        assert getattr(h.family, family + '_returns').received_facts(h.root, schema)[key] == published
    finally:
        h.store.close()


def load_before(name):
    spec = importlib.util.spec_from_file_location('gene_annotation_episode._343_before_' + name, PACKET/'before'/ (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_additive_catalogs_preserve_all_old_exact_registered_forms():
    for current, name, catalog, row_schema, sources in [
        (sv, 'native_blast_standard_database_result_views', 'standard_blast_database_metric_definitions', 'standard_blast_database_row_schema', 'standard_blast_database_fact_sources'),
        (nv, 'native_blast_database_result_views', 'native_blast_database_metric_definitions', 'native_blast_database_row_schema', 'native_blast_database_fact_sources')]:
        before = load_before(name)
        old = getattr(before, catalog)()
        new = getattr(current, catalog)()
        assert set(new) - set(old) == {'sequence_record_quality'}
        assert new['sequence_record_quality'] == old['sequence_quality']
        assert {k: new[k] for k in old} == old
        for family in old:
            assert getattr(before, row_schema)(family) == getattr(current, row_schema)(family)
        old_sources, new_sources = getattr(before, sources)(), getattr(current, sources)()
        assert {k: new_sources[k] for k in old_sources} == old_sources
        assert len(set(new_sources) - set(old_sources)) == 1


@pytest.mark.parametrize('consumer,schema', [('query_identity', V2), ('sequence_database', 'native_blast_database_query_metadata_v1'),
    ('sequence_database', 'native_blast_database_sequence_metadata_v3'), ('query_identity', 'native_blast_database_query_metadata_v2')])
def test_exact_tuple_rejection_in_job_selector_worker_schema(consumer, schema):
    from gene_annotation_episode.domain import validate_schema
    from test_native_blast_standard_database_contracts import job_for, identity
    job = job_for()
    job['inputs'].append(dict(input_key='metadata', role='metadata', format='json', **identity('/supplied/metadata')))
    job['metadata_inputs'] = [dict(input_key='metadata', consumer=consumer, schema_id=schema)]
    with pytest.raises(ValueError):
        sc.validate_standard_blast_database_job(job)
    with pytest.raises(ValueError):
        validate_schema(job, sc.NATIVE_BLAST_STANDARD_DATABASE_JOB_SCHEMA)
    item = dict(input_key='metadata', consumer=consumer, schema_id=schema, artifact_ref='artifact-metadata', sha256='a'*64, size_bytes=10)
    selection = dict(version='native_blast_standard_database_selector_v1', acquisition='complete_bound_bundle',
        metadata_inputs=[item], retained_sources=[], projections=[dict(family='sequence_record_quality', rows=dict(offset=0, limit=5), metrics=['completeness_fraction'], booleans=[])])
    with pytest.raises(ValueError):
        sv.validate_standard_blast_database_selector(selection, program='blastp')
    with pytest.raises(ValueError):
        validate_schema(selection, sv._selector_schema('blastp'))
    with pytest.raises(ValueError):
        sw._shape({**item, 'origin': 'selected_results_input'}, sw._DESCRIPTOR)


def test_old_v1_rows_and_explicit_null_quality_remain_exact(tmp_path):
    before = load_before('native_blast_standard_database_calculators')
    inputs = sf.fixture()
    payload = sf.numerical_metadata(inputs, census=False)
    # All assertions reside in the supplied JSON; this is file/pointer provenance.
    payload['documents'].append(sf.received(inputs, 'record-assignments', sf.encoded({'synthetic': True})))
    quality(payload)
    sf.add_metadata(inputs, payload, 'sequence_database')
    sheets = sf.run(inputs)
    calculated = calc.calculate_standard_blast_database_sheets(sheets, sequence_model=None)
    args = dict(bundle_identity=inputs['bundle']['identity'], calculation_id='a'*64, sheet_set=sheets, calculations=calculated)
    actual = calc.build_standard_blast_database_rows(**args)
    assert actual == before.build_standard_blast_database_rows(**args)
    assert len([r for r in actual if r['family'] == 'sequence_quality']) == 4
    assert not [r for r in actual if r['family'] == 'sequence_record_quality']
    nullable = deepcopy(sheets)
    scientific = nullable['sequence'][0]['sheet']
    scientific['schema'] = 'blast_sequence_database_result_sheet_v2'
    for row in scientific['reference_metadata']: row['record_locator'] = None
    for row in scientific['description_bindings']: row['binding']['metadata_record_locator'] = None
    for row in scientific['sequence_identity_bindings']: row['binding']['record_locator'] = None
    changed = calc.calculate_standard_blast_database_sheets(nullable, sequence_model=None)
    assert calc.build_standard_blast_database_rows(**{**args, 'sheet_set': nullable, 'calculations': changed}) == actual
    save(tmp_path/'original-v1-rows.json', actual)


def test_repeated_exact_record_coalesces_and_mixed_old_new_quality_survives(tmp_path):
    document = sf.report()
    document['BlastOutput2'][0]['report']['results']['search']['hits'].append(deepcopy(document['BlastOutput2'][0]['report']['results']['search']['hits'][0]))
    inputs = sf.fixture(doc=document)
    sf.subject(inputs, 'ACDEFGHI')
    payload = quality(sf.record_metadata(inputs))
    unit = payload['searches'][0]
    for field in ('description_bindings', 'sequence_identity_bindings'):
        new = deepcopy(unit[field][0]); new['binding']['hit_index'] = 2; unit[field].append(new)
    proof = deepcopy(unit['sequence_proofs'][0]); proof['binding_index'] = 2; unit['sequence_proofs'].append(proof)
    sf.add_metadata(inputs, payload, 'sequence_database', 'record-v2')
    old = sf.numerical_metadata(inputs, census=False, key='legacy-json')
    old['documents'].append(deepcopy(next(d for d in payload['documents'] if d['document_key'] == 'record-assignments')))
    quality(old)
    sf.add_metadata(inputs, old, 'sequence_database', 'old-v1')
    request = sr.request_for(tmp_path, inputs=inputs)
    manifest, diagnostics = sr.invoke(request)
    assert manifest['status'] == 'complete', diagnostics
    actual = rows(request)
    records = [r for r in actual if r['family'] == 'sequence_record_quality']
    old_rows = [r for r in actual if r['family'] == 'sequence_quality']
    assert len(records) == len(old_rows) == 4
    assert len({r['record_key'] for r in records + old_rows}) == 8
    first = [r for r in records if r['identity']['assembly_source']['record_locator']['record_ordinal'] == 0]
    assert all(sum('/associations/' in ref['pointer'] for ref in row['component_refs']) == 2 for row in first)
    assert all(set(row['identity']['assembly_source']) == {'source_ref', 'pointer'} for row in old_rows)


@pytest.mark.parametrize('mutation', ['bool', 'float', 'negative', 'pointer', 'binding_ordinal', 'metadata_index', 'association_assembly'])
def test_record_quality_rejects_malformed_or_borrowed_association(tmp_path, mutation):
    inputs = standard_inputs(supplied_quality=True)
    sheets = sf.run(inputs)
    calculations = calc.calculate_standard_blast_database_sheets(sheets, sequence_model=None)
    database = calculations['sequence'][0]['components']['components']['database_sheet']
    row = database['reference_metadata'][0]
    if mutation in {'bool', 'float', 'negative'}:
        row['record_locator']['record_ordinal'] = {'bool': True, 'float': 0.0, 'negative': -1}[mutation]
    elif mutation == 'pointer': row['native_pointer'] = '/0'
    elif mutation == 'binding_ordinal': database['hits'][0]['associations'][0]['description_binding']['metadata_record_locator']['record_ordinal'] = 1
    elif mutation == 'metadata_index': database['hits'][0]['associations'][0]['metadata_index'] = 1
    else: database['hits'][0]['associations'][0]['assembly'] = deepcopy(database['reference_metadata'][1]['assembly'])
    with pytest.raises(ValueError):
        calc.build_standard_blast_database_rows(bundle_identity=inputs['bundle']['identity'], calculation_id='a'*64,
            sheet_set=sheets, calculations=calculations)


@pytest.mark.parametrize('variant', ['census', 'unassigned', 'duplicate'])
def test_actual_standard_worker_record_weight_oracles(tmp_path, variant):
    inputs = sf.fixture()
    sf.subject(inputs, 'ACDEFGHI')
    payload = sf.record_metadata(inputs, sequences=('ACDEFGHIKL', 'ACDEFGHIKL') if variant == 'duplicate' else ('ACDEFGHIKL', 'ACDEPQRSTV'))
    unit = payload['searches'][0]
    if variant == 'unassigned':
        for row in unit['reference_metadata']: row['functions'] = []
    if variant == 'duplicate':
        for row in unit['reference_metadata']: row['functions'][0]['function'] = 'F'
    if variant == 'census':
        doc = sf.received(inputs, 'census', sf.encoded(dict(total=1000, F=100, G=10)))
        payload['documents'].append(doc)
        unit['database_profile'] = dict(database='target', release='r1', scope='selected_sequences', count_unit='unique_sequences',
            total_count=1000, function_counts={'F': 100, 'G': 10}, source='census')
    sf.add_metadata(inputs, payload, 'sequence_database', 'v2-weight-oracle')
    request = sr.request_for(tmp_path, inputs=inputs)
    manifest, diagnostics = sr.invoke(request)
    assert manifest['status'] == 'complete', diagnostics
    functions = [r for r in rows(request) if r['family'] == 'sequence_function']
    if variant == 'unassigned': assert functions == []
    elif variant == 'census':
        assert [values(r)['representation_adjusted_probability'] for r in functions] == pytest.approx([2/7, 5/7])
    else:
        assert len([r for r in rows(request) if r['family'] == 'sequence_group']) == 1
        assert [values(r)['function_mass'] for r in functions] == [1]


@pytest.mark.parametrize('program', ['blastn', 'blastp', 'blastx', 'tblastn', 'tblastx'])
def test_v2_real_worker_geometry_uses_full_record_units(tmp_path, monkeypatch, program):
    qnt = program in {'blastn', 'blastx', 'tblastx'}
    snt = program in {'blastn', 'tblastn', 'tblastx'}
    qwidth = 3 if qnt and program != 'blastn' else 1
    swidth = 3 if snt and program != 'blastn' else 1
    native = sf.hsp(qseq='AAAA', hseq='AAAA', query_to=4*qwidth, hit_to=4*swidth,
        **({'query_frame': 1} if qwidth == 3 else {}), **({'hit_frame': 1} if swidth == 3 else {}))
    query = 'A'*(8*qwidth)
    inputs = sf.fixture(program, query=('>q\n'+query+'\n').encode(),
        doc=sf.report(program, query_len=len(query), hits=[sf.hit(length=10*swidth, hsps=[native])]))
    sf.subject(inputs, query, molecule='dna' if qnt else 'protein')
    payload = sf.record_metadata(inputs, sequences=('A'*(10*swidth),), molecule='nt' if snt else 'aa',
        indices=(0,), description_ordinals=(0,), ordinals=(0,))
    sf.add_metadata(inputs, payload, 'sequence_database', 'record-v2')
    calls = []
    original = sequence.calculate_blast_sequence_database_components
    def counted(*args, **kwargs):
        calls.append(deepcopy(kwargs))
        return original(*args, **kwargs)
    monkeypatch.setattr(sequence, 'calculate_blast_sequence_database_components', counted)
    request = sr.request_for(tmp_path, inputs=inputs)
    manifest, diagnostics = sr.invoke(request)
    assert manifest['status'] == 'complete', diagnostics
    assert len(calls) == 1
    row, = [r for r in rows(request) if r['family'] == 'hsp']
    assert row['context']['query_unit'] == ('nt' if qnt else 'aa')
    assert row['context']['reference_unit'] == ('nt' if snt else 'aa')
    assert values(row)['qualified_paired_query_units'] == 4*qwidth
    assert values(row)['qualified_paired_reference_units'] == 4*swidth
    assert values(row)['full_query_paired_coverage'] == .5
    assert values(row)['full_reference_paired_coverage'] == .4


def test_native_old_rows_keep_exact_calculated_values_and_forms():
    before = load_before('native_blast_database_result_worker')
    for sheets in (nr.psi_sheets(), nr.profile_sheets(), nr.vdb_sheets()):
        calculations, actual = nr.calculate_rows(sheets)
        assert before.build_native_blast_database_rows(bundle_identity=nr.ATTEMPT,
            calculation_id=nr.CALCULATION_ID, sheet_set=sheets, calculations=calculations) == actual
