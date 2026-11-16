"""Selected reported-curve integration: controlled source fixtures, not model science."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.communication import form_with_facts, plain, validate_closed_schema, ReportBoundaryError
from gene_annotation_episode.episodic_workflow.root.a105.domain import ContractError, canonical, obj
from gene_annotation_episode.episodic_workflow.root.a105.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episodic_workflow.root.a105.episode_services import WorkflowServices
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.episode import LiteratureEpisode
from gene_annotation_episode.episodic_workflow.root.a105.tests.runtime_fixtures import literature_binding_factories, literature_binding_for_role
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_observation_storage import LiteratureRateObservationRepository, LiteratureReportedCurveRepository, GRID_NAMESPACE, GRID_REQUESTED, GRID_RECORD, GRID_POPULATION, GRID_VIEW, rate_grid_cells_schema, rate_observation_operation_schema, _grid_scoped_label
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_rate_observation_prompt import REPORTED_CURVE_TASK, REPORTED_CURVE_SCOPE_TASK, RATE_OBSERVATION_TASK, render_received
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_experimental_prompt import EXPERIMENTAL_TASK, render_literature_experimental_prompt
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_reference_parent_prompt import REFERENCE_PARENT_TASK, render_reference_evidence_parent_prompt
from gene_annotation_episode.episodic_workflow.root.a105.state import Store
from gene_annotation_episode.episodic_workflow.root.a105.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_reported_curve_precision_228 import source_setup, edit_workbook, select
SELECTORS = [select('point', 'cv', concentration_cell='Q196'), select('estimator', 'Km', estimator='fit_of_point_means'), select('estimator', 'log_efficiency_variance', estimator='fit_of_point_means')]

def setup(path, *, selectors=SELECTORS, nondetection=False):
    raw, grid, docs, _ = source_setup()
    if nondetection:
        from xml.etree import ElementTree as ET

        def mutate(_, cells):
            c = cells['R196']
            c.set('t', 'inlineStr')
            for child in list(c):
                c.remove(child)
            ET.SubElement(ET.SubElement(c, '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}is'), '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t').text = 'ND'
        raw = edit_workbook(mutate)
        grid['source_kind'] = 'synthetic_fixture'
    store = Store(path)
    manifest = path / 'empty-manifest.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'entries': []}))
    store.create_problem(manifest_path=manifest)

    def put(content, provider, parents=None):
        artifact = store.artifact(content)
        return store.put('source', {'provider': provider, 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None, **({'parent_source_refs': parents} if parents else {})}, origin='caller')['id']
    article = put(docs[0]['content'], 'retained_original_225_article')
    source = put(raw, 'synthetic_grid231' if nondetection else 'retained_original_225_xlsx', [article])
    original_source = grid['source_ref']
    original_context = docs[0]['source_ref']

    def replace_refs(v):
        if isinstance(v, dict):
            return {k: replace_refs(c) for k, c in v.items()}
        if isinstance(v, list):
            return [replace_refs(c) for c in v]
        return source if v == original_source else article if v == original_context else v
    grid = replace_refs(grid)
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [], 'source_refs': [source, article], GRID_REQUESTED: deepcopy(selectors)}
    ctx = BindingContext('curve231', 'child231', 'literature', (('literature', 'child231'),), store.validate_scope(), assignment, {}, (source, article))
    args = {'version': GRID_POPULATION, 'grid': grid, 'calculation': {'version': 'a105_reported_curve_precision_request_v1', 'fit_model': 'unweighted_positive_km_mm', 'requested_components': deepcopy(selectors)}}
    return (store, ctx, args, source, article)

def binding_for(store, ctx, profile=None):
    host = SimpleNamespace(store=store, run_id=ctx.run_id, tools=ToolRegistry(store))
    services = WorkflowServices(host)
    binding = LiteratureEpisode(services, rate_population=True, reference_parent_sources=list(ctx.received_record_refs[:2]), contract_information_profile=profile)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding

def selected(store, ctx, args, key='selected231'):
    binding = binding_for(store, ctx)
    outcome = asyncio.run(binding.execute(ctx, 'literature.rate.observations.populate', args, key))
    assert outcome['status'] == 'completed', outcome
    current = replace(ctx, received_record_refs=(*ctx.received_record_refs, *outcome['record_refs']))
    form = obj({'numbers': rate_grid_cells_schema()})
    rows = form_with_facts({}, form, binding.facts(current, {'committed_record_refs': outcome['record_refs']}))['numbers']
    binding.validate_report(current, {'numbers': rows}, form)
    return (binding, current, outcome, rows)





def test_empty_order_possession_page_and_exact_admitted_subset(tmp_path):
    store, ctx, args, source, article = setup(tmp_path / 'state')
    try:
        binding = binding_for(store, ctx)
        bad = deepcopy(args)
        bad['calculation']['requested_components'].reverse()
        assert asyncio.run(binding.execute(ctx, 'literature.rate.observations.populate', bad, 'order'))['feedback']['code'] == 'literature_rate_grid_requested_subset_mismatch'
        denied = replace(ctx, received_record_refs=(source,))
        assert asyncio.run(binding.execute(denied, 'literature.rate.observations.populate', args, 'missing'))['feedback']['code'] == 'literature_source_not_received'
        page = replace(ctx, role='literature_page', path=(('literature_page', ctx.episode_id),), assignment={'version': 'page_assignment_v1', 'source_ref': source, 'representation': 'original', 'artifact_ref': store.get(source)['artifact_ref'], 'question_context_refs': [], 'prior_delivery_refs': [], GRID_REQUESTED: SELECTORS})
        assert asyncio.run(literature_binding_for_role(binding, 'literature_page').execute(page, 'literature.rate.observations.populate', args, 'page'))['feedback']['code'] == 'literature_reading_outside_assigned_source'
        binding, current, out, rows = selected(store, ctx, args)
        repo = LiteratureRateObservationRepository(store, ctx.run_id).grid_projection()
        parent = replace(current, episode_id='parent231', role='annotation', path=(('annotation', 'parent231'),), assignment={})
        repo.receive_cells(parent, rows[:1], 'trusted231')
        assert repo.fact_cells(parent, [out['result']['sheet_ref']], components=SELECTORS) == rows[:1]
        with pytest.raises(ContractError, match='not_received'):
            repo.validate_fact_values(parent, rows[1:])
        changed = deepcopy(rows[:1])
        changed[0]['value'] = 999
        with pytest.raises(ContractError, match='differs_from_saved'):
            repo.validate_fact_values(parent, changed)
        empty = deepcopy(args)
        empty['calculation']['requested_components'] = []
        _, _, emptyout, emptyrows = selected(store, replace(ctx, assignment={**plain(ctx.assignment), GRID_REQUESTED: []}), empty, 'empty')
        assert emptyrows == [] and emptyout['result']['cells'] == []
        validate_closed_schema(obj({'numbers': rate_grid_cells_schema()}))
    finally:
        store.close()

@pytest.mark.parametrize('status', ['supported', 'unknown', 'conflicting'])
def test_selected_sampling_qualification_never_becomes_physical_total_uncertainty(tmp_path, status):
    store, ctx, args, _, _ = setup(tmp_path / 'state')
    try:
        sampling = args['grid']['curve_sampling']
        sampling['status'] = status
        sampling['source_claim'] = {'supported': 'iid_reporting_vectors_supported', 'unknown': 'unknown', 'conflicting': 'conflicting'}[status]
        if status == 'unknown':
            sampling.update(assumption='none', witnesses=[])
        if status == 'supported':
            args['grid']['source_kind'] = 'synthetic_fixture'
        _, _, _, rows = selected(store, ctx, args)
        assert rows[0]['status'] == 'populated' and rows[0]['value'] is not None
        assert rows[2]['status'] == ('conditional_scenario' if status == 'supported' else 'unavailable')
        assert rows[2]['sampling']['status'] == status and rows[2]['value'] is None
        assert rows[2]['scientific_scope']['physical_preparation_count'] is None
        assert rows[2]['scientific_scope']['published_estimate_covariance'] is None
        if status != 'supported':
            assert 'sampling_model_' + status in rows[2]['relationship_reasons']
    finally:
        store.close()

def test_each_public_selector_scope_keeps_order_and_only_named_coordinate_context(tmp_path):
    selectors = [*deepcopy(SELECTORS[:2]), select('curve', 'Vmax', curve_header_cell='R192'), select('reported_curve_covariance', 'sample_covariance', left_concentration_cell='Q196', right_concentration_cell='Q197'), select('parameter_covariance', 'covariance', estimator='mean_of_reported_curve_fits', left_parameter='Vmax', right_parameter='Km'), select('sensitivity', 'd_parameter_d_point_mean', estimator='fit_of_point_means', parameter='Vmax', concentration_cell='Q196'), select('variance_term', 'signed_log_efficiency_variance_term', estimator='fit_of_point_means', left_parameter='Vmax', right_parameter='Km'), select('grid', 'complete_curve_count')]
    store, ctx, args, _, _ = setup(tmp_path / 'state', selectors=selectors)
    try:
        _, _, out, rows = selected(store, ctx, args)
        assert [r['selector'] for r in rows] == selectors
        assert [len(r['coordinate_context']) for r in rows] == [1, 0, 0, 2, 0, 1, 0, 0]
        assert rows[3]['value'] is not None and rows[4]['conditional_value'] is not None
        assert rows[6]['conditional_value'] < 0 and rows[7]['value'] == 3
        saved = LiteratureReportedCurveRepository(store, ctx.run_id).read(out['result']['sheet_ref'])
        assert len(saved['projected_cells']) == 8
        assert [c['location']['cell'] for c in rows[3]['coordinate_context']] == ['Q196', 'Q197']
    finally:
        store.close()

@pytest.mark.parametrize('label,withheld', [('dose5mM', True), ('pH8.0', True), ('Kd34uM', True), ('CV=0.5', True), ('P450cam', False), ('K116A', False), ('5-methyluridine', False), ('NADH consumption rate µmol min-1', False)])
def test_bounded_label_scope_preserves_names_and_hides_values(label, withheld):
    w = {'value': label, 'source_ref': 'source_' + '1' * 24, 'artifact_ref': 'artifact_' + '2' * 64, 'member': 'sheet.xml', 'cell': 'A1'}
    projected = _grid_scoped_label(w)
    assert (projected['implementation_reason'] is not None) == withheld
    assert projected['display_text'] != label if withheld else projected['display_text'] == label

def test_broad_alias_history_current_own_and_direct_parent_do_not_expand_private_cells(tmp_path):
    store, ctx, args, source, article = setup(tmp_path / 'state')
    try:
        _, current, out, rows = selected(store, ctx, args)
        w = args['grid']['endpoint_relationship']['witnesses'][-1]
        secret = 'reference_' + 'a' * 24
        record = {'id': secret, 'record_type': 'reference', 'origin': 'tool', 'reference_type': 'assay', 'label': 'broad numerical context', 'source_ref': article, 'anchor': {**{k: w[k] for k in ('source_ref', 'artifact_ref', 'start', 'end', 'quote')}}}
        base = {'literature_experimental_work': {'version': 'literature_experimental_task_v1', 'aspect': 'source_experimental_evidence'}, 'literature_assignment': {GRID_REQUESTED: SELECTORS[:1]}, 'working_state': {}, 'literature_received_fact_display': {'records': {secret: record}, 'received_refs': [secret]}, 'goal': {'objective': 'Evaluate reported precision.'}}
        narrow = {'numbers': rows[:1], 'alias': secret}
        surfaces = [({**base, 'child_reports': [narrow]}, ()), ({**base, 'current_report_update': narrow}, ()), ({**base, 'last_local_outcome': {'status': 'completed', 'result': {**out['result'], 'cells': rows[:1]}}}, ()), ({**base, 'child_reports': [narrow]}, ({'status': 'completed', 'result': {'view': 'records', 'records': [{'outcome': out, 'admitted_report': narrow}]}},))]
        private = str(rows[1]['value'])
        for state, lookups in surfaces:
            text = render_literature_experimental_prompt(state, 'Evaluate the requested source evidence.', lookup_results=lookups)
            assert REPORTED_CURVE_TASK in text.split('\n\nSTEERING\n')[0]
            assert private not in text and w['quote'] not in text and (secret not in text)
        parent = {**base, 'child_reports': [narrow], 'literature_experimental_work': {'version': 'literature_experimental_task_v1', 'aspect': 'reference_evidence_parent'}, 'reference_evidence_parent': {'version': 'reference_evidence_parent_v1', 'source_refs': [source, article]}}
        text = render_reference_evidence_parent_prompt(parent, 'Evaluate source precision.')
        assert REPORTED_CURVE_TASK in text and REPORTED_CURVE_SCOPE_TASK in text and (private not in text) and (secret not in text)

        def rendered(values):
            p = []
            render_received(p, values, section=lambda p, t, c: p.append(t + '\n' + c), table=lambda h, r: '\n'.join(('|'.join(map(str, x)) for x in r)))
            return '\n'.join(p)
        assert rendered(rows[:1]) == rendered(iter(rows[:1]))
    finally:
        store.close()






