"""Original case164 XLSX plus labelled synthetic workbook engineering cases."""
from copy import deepcopy
from dataclasses import replace
import asyncio
import io
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.communication import ReportBoundaryError, form_with_facts, plain, validate_closed_schema
from gene_annotation_episode.episodic_workflow.root.a105.domain import ContractError, canonical, obj
from gene_annotation_episode.episodic_workflow.root.a105.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episodic_workflow.root.a105.episode_services import WorkflowServices
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.episode import LiteratureEpisode
from gene_annotation_episode.episodic_workflow.root.a105.tests.runtime_fixtures import literature_binding_factories, literature_binding_for_role
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_observation_calculations import populate_rate_observation_contrast
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_observation_storage import COMPONENTS, NAMESPACE, REQUESTED, LiteratureRateObservationRepository, rate_observation_cells_schema
from gene_annotation_episode.episodic_workflow.root.a105.state import Store
from gene_annotation_episode.episodic_workflow.root.a105.tools import ToolRegistry
CASE = Path(__file__).resolve().parents[5] / 'gene_annotation_episode/episodic_workflow/root/a105/tests/fixtures/research_reference/a105_raw_rate_primary_case_164'
REQUEST = ['reference_rate', 'test_rate', 'reference_sample_sd', 'test_sample_sd', 'reference_cv', 'test_cv', 'rate_difference', 'retained_fraction', 'fractional_decrease']
FORM = obj({'activity': rate_observation_cells_schema()})

def label(cell, expected_text):
    return {'cell': cell, 'expected_text': expected_text}

def source_arguments(reference):
    return {'source_ref': reference, 'source_kind': 'primary_source', 'worksheet': 'Sheet1', 'panel': label('A1', 'Fig 2B. Raw data of catalytic activity of PKs from different species on different substrates'), 'subject': label('J3', 'Actinobacteria bifidobacterium'), 'native_unit': label('C2', 'U/mg'), 'groups': [{'label': label('C' + str(start - 1), name), 'observations': [{'label': label('C' + str(row), 'Parallel ' + str(index)), 'value_cell': 'J' + str(row)} for index, row in enumerate(range(start, start + 3), 1)]} for name, start in [('DHA', 8), ('L-EUS', 12), ('D-EUS', 16)]], 'reference_group': 'D-EUS', 'test_group': 'L-EUS'}

def setup(path, *, content=None, requested=REQUEST):
    store = Store(path)
    manifest = store.path / 'empty-manifest.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'entries': []}))
    store.create_problem(manifest_path=manifest)
    artifact = store.artifact((CASE / 'originals/S1Data.xlsx').read_bytes() if content is None else content, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    source = store.put('source', {'provider': 'retained_original_case164' if content is None else 'synthetic_xlsx_fixture', 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': None, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')
    args = source_arguments(source['id'])
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [], 'source_refs': [source['id']], REQUESTED: list(requested)}
    context = BindingContext('original-xlsx-166', 'source-child', 'literature', (('literature', 'source-child'),), store.validate_scope(), assignment, {}, (source['id'],))
    return (store, context, args)

def binding_for(store, context, *, reference_parent=False):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    services = WorkflowServices(host)
    binding = LiteratureEpisode(services, rate_population=True, reference_parent_sources=list(context.received_record_refs[:1]) if reference_parent else None)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return (services, binding)

def populated(store, context, args, key='selected'):
    repo = LiteratureRateObservationRepository(store, context.run_id)
    out = repo.populate(context, args, key)
    return (repo, out, replace(context, received_record_refs=(*context.received_record_refs, *out['record_refs'])))

def synthetic_workbook(cells):
    """Explicit synthetic OOXML fixture; never a scientific measurement."""
    from xml.sax.saxutils import escape
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as z:
        z.writestr('_rels/.rels', '<Relationships><Relationship Id="root" Type="x/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml', '<workbook xmlns:r="urn:r"><sheets><sheet name="Sheet1" sheetId="1" r:id="s1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships><Relationship Id="s1" Type="x/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        entries = []
        for address, value in cells.items():
            if isinstance(value, tuple):
                entries.append(f'<c r="{address}"><f>{escape(value[0])}</f><v>{value[1]}</v></c>')
            elif type(value) in (int, float):
                entries.append(f'<c r="{address}"><v>{value}</v></c>')
            elif value is not None:
                entries.append(f'<c r="{address}" t="inlineStr"><is><t>{escape(value)}</t></is></c>')
        z.writestr('xl/worksheets/sheet1.xml', '<worksheet><sheetData><row r="1">' + ''.join(entries) + '</row></sheetData></worksheet>')
    return buffer.getvalue()

def synthetic_case(path, values, *, repeated_label=False):
    cells = {'A1': 'reported activity panel', 'J3': 'synthetic molecule', 'C2': 'symbolic units', 'C7': 'other', 'C11': 'test', 'C15': 'reference'}
    for start in (8, 12, 16):
        for index, row in enumerate(range(start, start + 3), 1):
            cells['C' + str(row)] = 'reading ' + str(index)
            cells['J' + str(row)] = values.get(row, float(row))
    if repeated_label:
        cells['C17'] = cells['C16']
    store, context, args = setup(path, content=synthetic_workbook(cells), requested=COMPONENTS)
    args['panel'] = label('A1', cells['A1'])
    args['subject'] = label('J3', cells['J3'])
    args['native_unit'] = label('C2', cells['C2'])
    args['source_kind'] = 'synthetic_fixture'
    args['reference_group'] = 'reference'
    args['test_group'] = 'test'
    for group, name, start in zip(args['groups'], ('other', 'test', 'reference'), (8, 12, 16)):
        group['label']['expected_text'] = name
        for index, observation in enumerate(group['observations'], 1):
            observation['label']['expected_text'] = 'reading ' + str(index)
    if repeated_label:
        args['groups'][2]['observations'][1]['label']['expected_text'] = 'reading 1'
    return (store, context, args)

def test_original_workbook_native_arithmetic_exact_lexemes_and_shared_reference(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        repo, out, current = populated(store, context, args)
        cells = {r['component']: r for r in out['result']['cells']}
        assert [cells[n]['value'] for n in REQUEST] == pytest.approx([0.5044733333333334, 0.18895333333333333, 0.03403624734504868, 0.012470787197820887, 0.06746887317145674, 0.06599929716942925, 0.3155200000000001, 0.3745556421878923, 0.6254443578121077])
        assert cells['reference_rate']['unit'] == 'U/mg'
        assert all((row['grouping'] == 'unknown' and row['physical_conversion'] == 'unknown' for row in cells.values()))
        saved = repo.read(out['result']['sheet_ref'])
        entries = saved['sheet']['extraction']['entries']
        j16 = next((e for e in entries if e['value_source']['cell'] == 'J16'))
        assert j16['value_source']['raw_value'] == '0.53756666666666675'
        assert j16['value_source']['formula'] is None
        assert j16['value_source']['workbook_sha256'] == 'e6d31a25930fe62cf10dd13c1b3e8193202687e78ed935cb3dfd21fd51ff4a7a'
        assert j16['value_source']['member_sha256'] == '50a15623fb2543e42d1d09c7990f0e18f1428e6f6253ac1832cbfe56dc63224e'
        assert repo.populate(context, args, 'selected') == out
        other = {**args, 'test_group': 'DHA'}
        _, out2, _ = populated(store, context, other, 'second-comparison')
        first_ids = cells['rate_difference']['groups']['reference']['observed']['observation_labels']
        assert first_ids == out2['result']['cells'][0]['groups']['reference']['observed']['observation_labels']
        assert out2['result']['cells'][1]['value'] == pytest.approx(0.15676666666666664)
        assert out2['result']['cells'][1]['value'] != 0.1569
        import xml.etree.ElementTree as ET
        import hashlib
        summary_bytes = (CASE / 'originals/S1Table.xlsx').read_bytes()
        assert hashlib.sha256(summary_bytes).hexdigest() == '331a7dd5f2f28fb5d538714e9617430e28bc427b8a899183c64f0502105c476b'
        with zipfile.ZipFile(io.BytesIO(summary_bytes)) as z:
            ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            strings = [''.join(si.itertext()) for si in ET.fromstring(z.read('xl/sharedStrings.xml'))]
            h7 = next((c for c in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('.//m:c', ns) if c.get('r') == 'H7'))
            assert h7.get('t') == 's' and h7.find('m:f', ns) is None
            assert strings[int(h7.find('m:v', ns).text)] == '0.1569±0.0054'
        assert store.targets() == []
    finally:
        store.close()

@pytest.mark.parametrize('value,status,reason', [(None, 'missing', 'source_measurement_unavailable'), ('ND', 'not_detected', 'nondetection_without_point'), ('<5', 'censored', 'censored_measurement'), (('1+1', '2'), 'unsupported_cell', 'formula_measurement_unsupported'), ('14', 'unsupported_cell', 'numeric_cell_type_required')])
def test_incomplete_selected_roster_retains_points_and_synthetic_origins(tmp_path, value, status, reason):
    store, context, args = synthetic_case(tmp_path, {16: 10.0, 17: value, 18: 30.0})
    try:
        repo, out, _ = populated(store, context, args)
        cells = {r['component']: r for r in out['result']['cells']}
        assert cells['reference_rate']['value'] is None
        assert cells['reference_rate']['unavailable_reason'] == 'incomplete_selected_roster'
        assert cells['reference_observed_point_mean']['value'] == 20
        assert cells['reference_observed_point_sd']['value'] == pytest.approx(2 ** 0.5 * 10)
        assert cells['test_rate']['value'] == 13
        group = cells['reference_rate']['groups']['reference']['observed']
        assert (group['entry_count'], group['point_entry_count'], group['representation_count']) == (3, 2, 3)
        assert group['observation_labels'][1]['status'] == status
        assert group['observation_labels'][1]['unavailable_reason'] == reason
        assert all((c['input_origins'] == ['synthetic'] and c['origin'] == 'derived' for c in cells.values()))
        entries = repo.read(out['result']['sheet_ref'])['sheet']['extraction']['entries']
        assert all((e['origin'] == 'synthetic' for e in entries))
        if status == 'unsupported_cell' and isinstance(value, tuple):
            entry = next((e for e in entries if e['value_source']['cell'] == 'J17'))
            assert entry['value_source']['value_is_formula_cache'] is True
            assert entry['value_source']['formula']['text'] == '1+1'
            assert entry['exact_value'] is None
    finally:
        store.close()

def test_duplicate_representations_and_conflicting_source_labels_do_not_invent_experiments(tmp_path):
    store, context, args = synthetic_case(tmp_path, {16: 10.0, 17: 10.0, 18: 30.0})
    try:
        args['groups'][2]['observations'].append(deepcopy(args['groups'][2]['observations'][0]))
        repo, out, _ = populated(store, context, args)
        first = out['result']['cells'][0]
        assert first['value'] == pytest.approx(50 / 3)
        observed = first['groups']['reference']['observed']
        assert (observed['entry_count'], observed['representation_count']) == (3, 4)
        assert observed['observation_labels'][0]['record_identity'] != observed['observation_labels'][1]['record_identity']
        changed = deepcopy(args)
        changed['groups'][2]['observations'][-1]['value_cell'] = 'J18'
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_experimental_contracts import ExperimentalContractError
        with pytest.raises(ExperimentalContractError, match='label_value_row_mismatch'):
            populated(store, context, changed, 'misbound')
        data = repo.read(out['result']['sheet_ref'])['sheet']['extraction']
        extra = deepcopy(data['entries'][-1])
        extra['exact_value'] = {'numerator': '999', 'denominator': '1'}
        data['entries'].append(extra)
        sheet = populate_rate_observation_contrast(data, reference_group='reference', test_group='test')
        assert sheet['cells']['reference_rate']['unavailable_reason'] == 'conflicting_reported_entry'
        assert sheet['cells']['reference_observed_point_mean']['value'] == 20
    finally:
        store.close()

def test_requested_absent_group_is_not_a_source_label_omission_or_zero(tmp_path):
    store, context, args = setup(tmp_path, requested=COMPONENTS)
    try:
        args['test_group'] = 'requested but absent'
        _, out, _ = populated(store, context, args)
        cells = {r['component']: r for r in out['result']['cells']}
        assert cells['reference_rate']['value'] == pytest.approx(0.5044733333333334)
        assert cells['test_rate']['value'] is None and cells['rate_difference']['unavailable_reason'] == 'missing_test_group'
        assert cells['test_rate']['groups']['test']['status'] == 'not_observed'
        assert cells['test_rate']['groups']['test']['observed'] is None
        assert cells['test_rate']['groups']['test']['requested_label'] == 'requested but absent'
    finally:
        store.close()

def test_selected_binding_exact_facts_repairable_label_mismatch_and_custody(tmp_path):
    store, context, args = setup(tmp_path, requested=['rate_difference', 'retained_fraction'])
    try:
        services, binding = binding_for(store, context)
        binding.validate_report(context, {'activity': []}, FORM)
        bad = deepcopy(args)
        bad['subject']['expected_text'] = 'unrelated molecule'
        failed = asyncio.run(binding.execute(context, 'literature.rate.observations.populate', bad, 'wrong-label'))
        assert failed['status'] == 'invalid' and 'source_label_witness_mismatch' in failed['feedback']['code']
        bad = deepcopy(args)
        bad['mean'] = 99
        failed = asyncio.run(binding.execute(context, 'literature.rate.observations.populate', bad, 'invented-value'))
        assert failed['status'] == 'invalid'
        missing = asyncio.run(binding.execute(replace(context, received_record_refs=()), 'literature.rate.observations.populate', args, 'not-received'))
        assert missing['feedback']['code'] == 'literature_source_not_received'
        out = asyncio.run(binding.execute(context, 'literature.rate.observations.populate', args, 'selected'))
        assert out['status'] == 'completed', out
        binding.validate_report(context, {'activity': []}, FORM)
        current = replace(context, received_record_refs=(*context.received_record_refs, *out['record_refs']))
        form = form_with_facts({}, FORM, binding.facts(current, {'committed_record_refs': out['record_refs']}))
        binding.validate_report(current, form, FORM)
        assert [r['component'] for r in form['activity']] == ['rate_difference', 'retained_fraction']
        with pytest.raises(ReportBoundaryError, match='requested_subset_mismatch'):
            binding.validate_report(current, {'activity': []}, FORM)
        wrong = deepcopy(form)
        wrong['activity'][0]['value'] = 9
        with pytest.raises(ReportBoundaryError, match='differs_from_saved'):
            binding.validate_report(current, wrong, FORM)
        omitted = deepcopy(form)
        omitted['activity'].pop()
        with pytest.raises(ReportBoundaryError, match='requested_subset_mismatch'):
            binding.validate_report(current, omitted, FORM)
        wrong_schema = deepcopy(FORM)
        wrong_schema['properties']['activity']['items']['properties']['subject'] = {'type': 'string'}
        with pytest.raises(ReportBoundaryError, match='registered source'):
            validate_closed_schema(wrong_schema)
        no_request = replace(current, assignment={k: v for k, v in current.assignment.items() if k != REQUESTED})
        assert binding.facts(no_request, {'committed_record_refs': out['record_refs']})[NAMESPACE] == []
        with pytest.raises(ReportBoundaryError, match='unrequested'):
            binding.validate_report(no_request, form, FORM)
        other_artifact = store.artifact(b'unrelated fixture')
        other = store.put('source', {'provider': 'unrelated_fixture', 'accession': None, 'uri': None, 'artifact_ref': other_artifact, 'text_ref': None, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')
        page = replace(context, role='literature_page', path=(('literature_page', 'page'),), assignment={'version': 'page_assignment_v1', 'source_ref': args['source_ref'], 'representation': 'original', 'artifact_ref': store.get(args['source_ref'])['artifact_ref'], 'question_context_refs': [], 'prior_delivery_refs': [], REQUESTED: ['rate_difference']}, received_record_refs=(*context.received_record_refs, other['id']))
        failed = asyncio.run(literature_binding_for_role(binding, 'literature_page').execute(page, 'literature.rate.observations.populate', {**args, 'source_ref': other['id']}, 'outside-page'))
        assert failed['feedback']['code'] == 'literature_reading_outside_assigned_source'
    finally:
        store.close()




@pytest.mark.parametrize('mean_values', [(0.0, 0.0, 0.0), (-2.0, -1.0, 0.0)])
def test_cv_requires_positive_mean_without_discarding_signed_native_values(tmp_path, mean_values):
    store, context, args = synthetic_case(tmp_path, dict(zip((16, 17, 18), mean_values)))
    try:
        _, out, _ = populated(store, context, args)
        cells = {r['component']: r for r in out['result']['cells']}
        assert cells['reference_rate']['value'] == sum(mean_values) / 3
        assert cells['reference_sample_sd']['value'] is not None
        assert cells['rate_difference']['value'] == sum(mean_values) / 3 - 13
        assert cells['reference_cv']['value'] is None
        assert cells['reference_cv']['unavailable_reason'] == 'nonpositive_mean'
    finally:
        store.close()

@pytest.mark.parametrize('change,reason', [('wrong_column', 'observation_subject_column_mismatch'), ('wrong_group', 'observation_group_row_mismatch'), ('repeated_group_text', 'ambiguous_group_label_scope'), ('row_gap', 'contiguous_group_observation_rows_required')])
def test_finite_row_layout_rejects_misbound_or_ambiguous_selectors(tmp_path, change, reason):
    from gene_annotation_episode.episodic_workflow.root.a105.library.literature_experimental_contracts import ExperimentalContractError
    store, context, args = synthetic_case(tmp_path, {})
    try:
        if change == 'wrong_column':
            args['groups'][2]['observations'][0]['value_cell'] = 'K16'
        elif change == 'wrong_group':
            args['groups'][2]['observations'][0]['label']['cell'] = 'B16'
        elif change == 'repeated_group_text':
            args['groups'][0]['label']['expected_text'] = 'reference'
        elif change == 'row_gap':
            args['groups'][2]['observations'].pop(1)
        with pytest.raises(ExperimentalContractError, match=reason):
            populated(store, context, args)
    finally:
        store.close()

def test_reused_observation_label_on_different_rows_preserves_unknown_association(tmp_path):
    store, context, args = synthetic_case(tmp_path, {16: 10.0, 17: 10.0, 18: 30.0}, repeated_label=True)
    try:
        repo, out, _ = populated(store, context, args)
        cells = {r['component']: r for r in out['result']['cells']}
        assert cells['reference_rate']['value'] is None
        assert cells['reference_rate']['unavailable_reason'] == 'source_entry_association_unresolved'
        assert cells['reference_observed_point_mean']['value'] == 30
        group = cells['reference_rate']['groups']['reference']['observed']
        assert group['entry_count'] is None and group['selected_row_count'] == 3
        assert group['known_entry_count'] == group['point_entry_count'] == 1
        assert group['association_unresolved']
        assert [e['association_unresolved'] for e in group['observation_labels']] == [True, True, False]
        assert len(repo.read(out['result']['sheet_ref'])['sheet']['extraction']['entries']) == 9
    finally:
        store.close()
