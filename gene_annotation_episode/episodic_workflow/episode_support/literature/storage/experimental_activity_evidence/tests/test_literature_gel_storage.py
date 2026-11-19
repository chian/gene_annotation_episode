"""Constructed original-image/Store fixtures, including manual runtime rows.

These tests establish repository custody and projection behavior. Inserted runtime
rows do not establish actual selected LiteratureEpisode or model interpretation.
"""
from copy import deepcopy as cp
from dataclasses import replace
import json
import sqlite3
import subprocess
import sys
import pytest
from jsonschema import Draft202012Validator
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import ContractError, canonical
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_context import LiteratureContext
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.episode_receipts import EpisodeReceipts
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence import literature_gel_storage as storage
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence import literature_gel_inputs as inputs
from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.experimental_activity_evidence import literature_gel_calculations as calculations
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.tests.test_literature_gel_inputs import make_case, select_v2

def source(store, data, *, parents=()):
    artifact = store.artifact(data)
    return store.put('source', {'provider': 'constructed_gel_fixture', 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None, 'parent_source_refs': list(parents)}, origin='caller')['id']

def native_case(path, *, alternatives=False, v2=True, assignment=None):
    store = Store(path)
    store.create_problem(raw_sequence='MKWAA', molecule='protein')
    selected, _, sources, _, comparison = make_case()
    caption = source(store, sources['source_caption', 'text']['content'])
    image = source(store, sources['source_image', 'original']['content'], parents=[caption])
    selected['image'].update(source_ref=image, artifact_ref=store.get(image)['artifact_ref'])
    for witness in inputs._witnesses(selected):
        witness['source_ref'] = caption
    if v2:
        select_v2(selected)
    if alternatives:
        alternate = cp(selected['roi_assignments'][0])
        alternate['assignment_id'] = 'same:region / α'
        selected['roi_assignments'].append(alternate)
    assignment = assignment or {'requested_gel_components': ['direct_competitor_sensitive_shift'], 'requested_gel_views': ['comparison']}
    scope = store.validate_scope({'subject_refs': store.problem()['subject_refs']})
    request = {'goal': {'goal_id': 'constructed-runtime-fixture'}, 'message': {'scope': plain(scope), 'episode_assignment': assignment}, 'report_contract': None}
    context = LiteratureContext('gel-fixture-run', 'gel-fixture-child', 'literature', (('literature', 'gel-fixture-parent'), ('literature', 'gel-fixture-child')), scope, assignment, request, (image, caption))
    return (store, context, {'selection': selected, 'comparison': comparison})

def repository(store, context):
    return storage.LiteratureGelRepository(store, context.run_id, evidence_origin='synthetic_fixture')

def owned(context, outcome):
    return replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))


def forbid_reexecution(monkeypatch):

    def forbidden(*a, **k):
        pytest.fail('scientific reexecution during saved access')
    for module, names in ((inputs, ('read_gel_inputs', 'validate_gel_extraction', '_decode')), (calculations, ('populate_gel_components', 'validate_gel_sheet'))):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)

def test_original_image_exact_rows_methods_and_original_scientific_ids(tmp_path):
    store, context, args = native_case(tmp_path, alternatives=True)
    try:
        repo = repository(store, context)
        outcome = repo.populate(context, args, 'engineering')
        ref = outcome['result']['sheet_ref']
        saved = repo.read(ref)
        rows = outcome['result']['cells']
        Draft202012Validator.check_schema(storage.gel_cells_schema())
        Draft202012Validator(storage.gel_cells_schema()).validate(rows)
        direct = [r for r in rows if r['view'] == 'comparison' and r['component'] == 'direct_competitor_sensitive_shift']
        assert [r['component_key'] for r in direct] == ['comparison:declared:direct_competitor_sensitive_shift', 'comparison:same%3Aregion%20%2F%20%CE%B1:direct_competitor_sensitive_shift']
        assert all((r['cell']['exact'] == {'numerator': '3', 'denominator': '5'} for r in direct))
        assert direct[0]['cell']['value'] == pytest.approx(0.6)
        assert [l['observation_id'] for l in direct[0]['scientific_context']['lanes']] == ['observation_baseline', 'observation_protein', 'observation_competitor']
        assert all((m['background_method'] == 'mean' and m['method_basis'] == 'explicit_v2_nomination' for m in direct[0]['roi_methods']))
        raw = next((r for r in rows if r['component_key'] == 'raw:declared:protein:band:shifted:sum_darkness'))
        assert type(raw['cell']['value']) is int and raw['cell']['value'] == 80
        assert saved['extraction']['origin'] == 'synthetic'
        bindings = repo.semantic_bindings(direct[:1])
        for binding in bindings[ref].values():
            assert store.get(binding['record_ref'])['record_type'] == 'reference'
        assert repo.requested_component_keys(ref, {}) == []
        assert repo.requested_component_keys(ref, context.assignment) == [r['component_key'] for r in direct]
        assert not store.list('observation')
        with pytest.raises(ContractError, match='original_runtime_required'):
            repo.fact_cells(owned(context, outcome), [ref], components=[direct[0]['component_key']])
    finally:
        store.close()

def test_names_views_and_exact_keys_do_not_grant_other_alternatives(tmp_path):
    store, context, args = native_case(tmp_path, alternatives=True)
    try:
        repo = repository(store, context)
        outcome = repo.populate(context, args, 'engineering')
        ref = outcome['result']['sheet_ref']
        request = {'requested_gel_components': ['direct_competitor_sensitive_shift'], 'requested_gel_views': ['sensitivity']}
        assert repo.requested_component_keys(ref, request) == ['sensitivity:direct_competitor_sensitive_shift']
        assert repo.project_cells([ref], permitted_record_refs=[ref], components=['sensitivity:direct_competitor_sensitive_shift'])[0]['cell']['lower'] == {'numerator': '3', 'denominator': '5'}
        for keys in (['comparison:declared:direct_competitor_sensitive_shift'], ['missing'], [True]):
            with pytest.raises(ContractError):
                repo.requested_component_keys(ref, {**request, 'requested_gel_component_keys': keys})
        request['requested_gel_views'] = ['comparison']
        request['requested_gel_component_keys'] = ['comparison:declared:direct_competitor_sensitive_shift']
        assert repo.requested_component_keys(ref, request) == request['requested_gel_component_keys']
    finally:
        store.close()

def test_parent_receives_reprojected_child_cells_bound_by_digest(tmp_path):
    store, context, args = native_case(tmp_path)
    try:
        repo = repository(store, context)
        outcome = repo.populate(context, args, 'engineering')
        ref = outcome['result']['sheet_ref']
        key = outcome['result']['component_keys'][0]
        cells = repo.project_cells([ref], permitted_record_refs=[ref], components=[key])
        parent = replace(context, episode_id='gel-fixture-parent', path=context.path[:1], received_record_refs=(*context.received_record_refs, ref))
        assert repo.received_cells(parent) == []
        repo.receive_cells(parent, cells, 'child_return:0')
        repo.receive_cells(parent, cells, 'child_return:0')
        assert repo.received_cells(parent) == cells
        assert repo.fact_cells(parent, [ref], components=[key]) == cells
        with pytest.raises(ContractError, match='literature_delivery_binding_mismatch'):
            repo.receive_cells(parent, [], 'child_return:0')
        store.db.execute(f'UPDATE {repo.received_table} SET cells=? WHERE episode_id=?', ('[]', parent.episode_id))
        with pytest.raises(ContractError, match='literature_delivery_binding_mismatch'):
            repo.received_cells(parent)
    finally:
        store.close()

def test_invalid_comparison_and_missing_authorization_fail_before_source_bytes(tmp_path, monkeypatch):
    store, context, args = native_case(tmp_path)
    try:
        repo = repository(store, context)
        monkeypatch.setattr(repo, '_bytes', lambda *_: pytest.fail('bytes opened before complete input validation'))
        bad = cp(args)
        bad['comparison']['protein_lane_id'] = 'absent'
        with pytest.raises(ContractError):
            repo.populate(context, bad, 'bad-comparison')
        denied = replace(context, received_record_refs=context.received_record_refs[:1])
        with pytest.raises(ContractError):
            repo.populate(denied, args, 'denied-caption')
        assert not store.db.execute('SELECT 1 FROM literature_gel_operations').fetchall()
    finally:
        store.close()

def test_missing_background_and_baseline_preserve_valid_partial_rows(tmp_path):
    store, context, args = native_case(tmp_path)
    try:
        args['comparison']['baseline_lane_id'] = None
        args['selection']['roi_assignments'][0]['lanes'][0]['background'] = None
        repo = repository(store, context)
        outcome = repo.populate(context, args, 'partial')
        rows = {r['component_key']: r for r in outcome['result']['cells']}
        assert rows['raw:declared:baseline:band:free:sum_darkness']['cell']['value'] == 100
        assert rows['lane:declared:baseline:display_black_pixel_fraction']['cell']['value'] == 0
        assert rows['corrected:declared:baseline:free']['cell']['value'] is None
        assert rows['comparison:declared:direct_competitor_sensitive_shift']['cell']['value'] == pytest.approx(0.6)
        assert rows['comparison:declared:factorized_competitor_sensitive_shift']['cell']['value'] is None
        assert repo.read(outcome['result']['sheet_ref'])
    finally:
        store.close()




def test_unknown_conflicting_meanings_and_schema_relationships_survive(tmp_path):
    store, context, args = native_case(tmp_path, v2=False)
    try:
        args['selection']['context']['organism'] = {'state': 'unknown', 'value': None, 'witnesses': []}
        args['selection']['context']['genotype'].update(state='conflicting', value=None)
        args['selection']['lanes'][1]['condition'].update(state='conflicting', value=None)
        repo = repository(store, context)
        outcome = repo.populate(context, args, 'states')
        row = next((r for r in outcome['result']['cells'] if r['view'] == 'comparison'))
        assert row['scientific_context']['global']['organism'] == {'state': 'unknown', 'value_ref': None, 'witness_refs': []}
        assert row['scientific_context']['global']['genotype']['state'] == 'conflicting'
        assert row['scientific_context']['global']['genotype']['witness_refs']
        assert row['scientific_context']['interpretation']['status'] == 'conflicting'
        assert all((m['method_basis'] == 'v1_mean_definition' for m in row['roi_methods']))
        bad = cp(row)
        bad['scientific_context']['global']['organism']['state'] = 'known'
        with pytest.raises(ContractError):
            repo.validate_returned_values([bad], permitted_record_refs=[row['sheet_ref']])
        bad = cp(row)
        bad['cell']['value'] = True
        with pytest.raises(ContractError):
            repo.validate_returned_values([bad], permitted_record_refs=[row['sheet_ref']])
    finally:
        store.close()





def test_fresh_process_sqlite_readonly_projection_forbids_original_bytes_and_calculators(tmp_path):
    store, context, args = native_case(tmp_path)
    repo = repository(store, context)
    outcome = repo.populate(context, args, 'engineering')
    ref = outcome['result']['sheet_ref']
    key = 'comparison:declared:direct_competitor_sensitive_shift'
    expected = repo.project_cells([ref], permitted_record_refs=[ref], components=[key])
    descriptor = repo.descriptor()
    store.close()
    script = "import json, sqlite3, sys\nfrom pathlib import Path\nfrom gene_annotation_episode.state import Store\nfrom gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence import literature_gel_storage as m\npath, ref, key, descriptor = sys.argv[1:]\nstore = Store.__new__(Store)\nstore.path = Path(path)\nstore._savepoint = 0\nstore.db = sqlite3.connect('file:' + str(store.path / 'state.sqlite3') + '?mode=ro', uri=True, isolation_level=None)\nstore.db.row_factory = sqlite3.Row\nstore.db.execute('PRAGMA query_only=1')\nrepo = m.LiteratureGelRepository(store, 'gel-fixture-run', evidence_origin='synthetic_fixture', expected_descriptor=json.loads(descriptor))\nrecord = store.get(ref)\nallowed = {record['artifact_ref'], record['request_ref']}\nget = store.get_artifact\n\ndef forbidden(*a, **k):\n    raise AssertionError('original-byte access, science reexecution, or mutation')\nstore.get_artifact = lambda r: get(r) if r in allowed else forbidden()\nstore.put = store.artifact = repo.receive_cells = forbidden\nfor name in ('read_gel_inputs', 'validate_gel_extraction', '_decode'):\n    setattr(m.inputs, name, forbidden)\nfor name in ('populate_gel_components', 'validate_gel_sheet'):\n    setattr(m.calculations, name, forbidden)\nbefore = store.db.total_changes\nrows = repo.project_cells([ref], permitted_record_refs=[ref], components=[key])\nassert before == store.db.total_changes\nprint(json.dumps(rows, sort_keys=True))\nstore.close()\n"
    result = subprocess.run([sys.executable, '-B', '-c', script, str(tmp_path), ref, key, canonical(descriptor)], text=True, capture_output=True, check=True)
    assert json.loads(result.stdout) == expected

def test_long_authenticated_passage_and_value_keep_full_spans_without_store_anchor_limit(tmp_path, monkeypatch):
    store, context, args = native_case(tmp_path)
    try:
        long_value = 'X' * 17001
        caption = ('Protein P construct C DNA shift. ' + long_value + '; full source passage.').encode()
        caption_ref = source(store, caption)
        for w in inputs._witnesses(args['selection']):
            w.update(source_ref=caption_ref, end=len(caption), quote=caption.decode())
        args['selection']['context']['experiment']['value'] = long_value
        context = replace(context, received_record_refs=(*context.received_record_refs, caption_ref))
        repo = repository(store, context)
        outcome = repo.populate(context, args, 'long-passage')
        ref = outcome['result']['sheet_ref']
        saved = repo.read(ref)
        assert saved['extraction']['authenticated_witnesses'][0]['quote'] == caption.decode()
        experiment = saved['meanings']['global']['experiment']
        record = store.get(experiment['value_ref'])
        assert record['anchor'] is None and len(record['label']) == 512
        assert saved['semantic_bindings'][experiment['value_ref']]['label_preview'] is True
        location = saved['semantic_bindings'][experiment['value_ref']]['canonical_witness_locations'][0]
        start = caption.index(long_value.encode())
        assert (location['start'], location['end']) == (start, start + len(long_value))
        for witness_ref in experiment['witness_refs']:
            witness = store.get(witness_ref)
            binding = saved['semantic_bindings'][witness_ref]
            assert witness['anchor'] is None and binding['canonical_witness_locations'][0]['end'] == len(caption)
        row = next((r for r in outcome['result']['cells'] if r['component_key'] == 'comparison:declared:direct_competitor_sensitive_shift'))
        assert row['cell']['exact'] == {'numerator': '3', 'denominator': '5'}
        allowed = {store.get(ref)['artifact_ref'], store.get(ref)['request_ref']}
        get = store.get_artifact

        def saved_only(reference):
            assert reference in allowed, 'original source bytes opened during saved replay'
            return get(reference)
        monkeypatch.setattr(store, 'get_artifact', saved_only)
        forbid_reexecution(monkeypatch)
        store.db.execute('PRAGMA query_only=1')
        before = store.db.total_changes
        assert repo.project_cells([ref], permitted_record_refs=[ref], components=[row['component_key']]) == [row]
        assert store.db.total_changes == before
    finally:
        store.close()
