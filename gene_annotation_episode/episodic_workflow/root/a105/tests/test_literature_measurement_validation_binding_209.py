"""Controlled selected work, original-source facts and durable typed custody.

All model decisions here are explicitly scripted. No configured model science,
common A105 score or final-credit implementation is claimed.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.communication import ReportBoundaryError, plain, validate_closed_schema, validate_form, form_with_facts
from gene_annotation_episode.episodic_workflow.root.a105.domain import ContractError, canonical, obj
from gene_annotation_episode.episodic_workflow.root.a105.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episodic_workflow.root.a105.episode_services import WorkflowServices
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.episode import LiteratureEpisode
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_measurement_validation_storage import LiteratureMeasurementValidationRepository, measurement_validation_cells_schema, COMPONENTS, NAMESPACE, REQUESTED, VIEW
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_calibration_recovery_storage import LiteratureCalibrationRecoveryRepository
from gene_annotation_episode.episodic_workflow.root.a105.state import Store
from gene_annotation_episode.episodic_workflow.root.a105.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_measurement_validation_205 import Source, original
from gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_calibration_recovery_binding_173 import rebind, OriginalRecoverySelection
REQUEST = ['reported_cv', 'relative_bias_squared', 'relative_squared_deviation_plugin', 'relative_rms_percent', 'reported_zprime', 'control_band_ratio', 'raw_control_zprime']
FORM = obj({'numbers': measurement_validation_cells_schema()})

def setup(path, *, requested=REQUEST, primary=False, native_only=False):
    if primary:
        source, args, _pure_rows, _fields = original(1)
        recovery_args = OriginalRecoverySelection(source.reference, source.content).arguments('buffer')
    else:
        base = Source()
        text = base.text.replace('<article><p>', '<article><p>Buffer20mM at pH7.4, constructE2. ')
        source = Source(content=text.encode())
        args = source.args()
        for field, text in [('analyte', 'NADPH'), ('matrix', 'Buffer20mM at pH7.4'), ('method', 'optical WST8'), ('endpoint', 'WST8 endpoint'), ('repetition', 'Repeated technical readings, count unknown')]:
            args['context'][field] = source.witness(text)
        recovery_args = {'source_ref': source.reference, 'source_kind': 'synthetic_fixture', **{name: None for name in ('experiment', 'analyte', 'matrix', 'endpoint', 'blank_treatment', 'expected_quantity_basis')}, 'control_kind': source.interpretation('reporter_standard', 'Prepared reporter standard'), 'applicability': source.interpretation('unknown'), 'spread_kind': source.interpretation('unknown'), 'nominal': source.synthetic_number('nominal'), 'measured': source.synthetic_number('measured'), 'measured_spread': None, 'shared_unit': source.witness('nmol'), 'reported_recovery': None, 'reported_recovery_unit': None}
    store = Store(path)
    manifest = store.path / 'empty-inputs.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'entries': []}))
    store.create_problem(manifest_path=manifest)
    artifact = store.artifact(source.content, 'application/xml')
    record = store.put('source', {'provider': 'retained_PMC6454709' if primary else 'synthetic_precision_fixture', 'accession': 'PMC6454709' if primary else None, 'uri': None, 'artifact_ref': artifact, 'text_ref': None, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')
    args = rebind(args, source.reference, record['id'])
    recovery_args = rebind(recovery_args, source.reference, record['id'])
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [], 'source_refs': [record['id']], REQUESTED: list(requested)}
    ctx = BindingContext('validation209', 'child209', 'literature', (('literature', 'child209'),), store.validate_scope(), assignment, {}, (record['id'],))
    if not native_only:
        recovery_context = replace(ctx, assignment={**assignment, 'requested_calibration_recovery_components': ['recovery', 'relative_bias']})
        prior = LiteratureCalibrationRecoveryRepository(store, ctx.run_id).populate(recovery_context, recovery_args, 'prior_recovery')
        ref = prior['result']['sheet_ref']
        ctx = replace(ctx, received_record_refs=(*ctx.received_record_refs, ref))
        for role in ('recovery', 'relative_bias'):
            args[role] = {'namespace': 'literature_calibration_recovery_cells', 'sheet_ref': ref, 'component': role}
    return (store, ctx, args)

def binding_for(store, context, **configuration):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisode(WorkflowServices(host), rate_population=True, **configuration)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding



def test_selected_execution_default_empty_and_source_possession(tmp_path):
    store, ctx, args = setup(tmp_path, native_only=True, requested=[])
    with store:
        binding = binding_for(store, ctx)
        assert 'literature.measurement_validation.populate' in {r['name'] for r in binding.catalog(ctx)}
        assert 'measurement_validation_population' not in binding.as_record()['configuration']
        binding.validate_report(ctx, {'numbers': []}, FORM)
        missing = asyncio.run(binding.execute(replace(ctx, received_record_refs=()), 'literature.measurement_validation.populate', args, 'missing'))
        assert missing['feedback']['code'] == 'literature_source_not_received'
        out = asyncio.run(binding.execute(ctx, 'literature.measurement_validation.populate', args, 'empty'))
        assert out['status'] == 'completed' and out['result']['cells'] == []
        repo = binding._measurement_validation_repository()
        current = replace(ctx, received_record_refs=(*ctx.received_record_refs, *out['record_refs']))
        assert repo.fact_cells(current, out['record_refs'], components=COMPONENTS) == []
        with pytest.raises(ContractError, match='component_not_selected'):
            repo.project_cells(out['record_refs'], permitted_record_refs=out['record_refs'], components=['reported_cv'])









def test_closed_exact_native_type_rejects_custom_loosened_fields(tmp_path):
    form = deepcopy(FORM)
    form['properties']['numbers']['items']['properties']['conditional_value']['type'] = 'number'
    with pytest.raises(ReportBoundaryError, match='registered source'):
        validate_closed_schema(form)

