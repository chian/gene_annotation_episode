"""Selected endpoint integration with controlled choices, not model-backed science."""
import asyncio
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.communication import form_with_facts, plain, validate_closed_schema, ReportBoundaryError
from gene_annotation_episode.episodic_workflow.root.a105.domain import ContractError, canonical, obj, validate_schema
from gene_annotation_episode.episodic_workflow.root.a105.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episodic_workflow.root.a105.episode_services import WorkflowServices
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.episode import LiteratureEpisode
from gene_annotation_episode.episodic_workflow.root.a105.tests.runtime_fixtures import literature_binding_factories, literature_binding_for_role
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_endpoint_signal_storage import LiteratureEndpointSignalRepository, ENDPOINT_SIGNAL_CELLS_SCHEMA_V1, endpoint_signal_cells_schema, NAMESPACE, REQUESTED, VIEW, COMPONENTS
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_endpoint_signal_prompt import ENDPOINT_SIGNAL_TASK
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_figure_prompt import FIGURE_TASK
from gene_annotation_episode.episodic_workflow.root.a105.state import Store
from gene_annotation_episode.episodic_workflow.root.a105.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_endpoint_signal_components_241 import _paper
ROOT = Path(__file__).resolve().parents[5]
OWN = ROOT / 'gene_annotation_episode/episodic_workflow/root/a105/tests/fixtures/retained_reference/a105_endpoint_signal_binding_244'
SELECTED = ['retained_fraction', 'retained_fraction_variance']

def setup(path, components=SELECTED):
    args, blobs = _paper()
    store = Store(path)
    manifest = path / 'empty-manifest.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'entries': []}))
    store.create_problem(manifest_path=manifest)

    def source(raw, provider, *, text=None, parents=(), artifact=None):
        artifact = artifact or store.artifact(raw)
        return store.put('source', {'provider': provider, 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': store.artifact(text) if text is not None else artifact, 'request_ref': None, 'version': None, 'retrieved_at': None, 'parent_source_refs': list(parents)}, origin='caller')['id']
    article = source(blobs['source_kaster_primary', 'original'], 'controlled_retained_original244', text=blobs['source_kaster_primary', 'text'])
    image = source(blobs['source_kaster_original_figure4', 'original'], 'controlled_original_image244', parents=[article])

    def refs(value):
        if isinstance(value, dict):
            return {k: refs(v) for k, v in value.items()}
        if isinstance(value, list):
            return [refs(v) for v in value]
        return article if value == 'source_kaster_primary' else image if value == 'source_kaster_original_figure4' else value
    args = refs(args)
    args['requested_cells'] = list(components)
    context = json.loads((OWN / 'PAIRED_SELECTED_INPUT_002.json').read_text())['arguments']['return_context']
    request = {'version': 'literature_figure_endpoint_signal_population_v1', 'selection': args, 'return_context': context}
    assignment = {'version': 'literature_assignment_v1', 'source_refs': [article, image], 'question_context_refs': [], REQUESTED: list(components)}
    ctx = BindingContext('endpoint244', 'child244', 'literature', (('literature', 'child244'),), store.validate_scope(), assignment, {}, (article, image))
    host = SimpleNamespace(store=store, run_id=ctx.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisode(WorkflowServices(host), rate_population=True, reference_parent_sources=[article, image])
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return (store, ctx, request, binding, source)

def selected(store, ctx, args, binding):
    outcome = asyncio.run(binding.execute(ctx, 'literature.figure.populate', args, 'selected244'))
    assert outcome['status'] == 'completed', outcome
    current = replace(ctx, received_record_refs=(*ctx.received_record_refs, *outcome['record_refs']))
    schema = obj({'numbers': endpoint_signal_cells_schema()})
    rows = form_with_facts({}, schema, binding.facts(current, {'committed_record_refs': outcome['record_refs']}))['numbers']
    binding.validate_report(current, {'numbers': rows}, schema)
    return (current, outcome, rows)





@pytest.mark.parametrize('part', ['primary', 'image', 'context', 'covariance', 'order'])
def test_source_custody_and_request_preflight(tmp_path, part):
    store, ctx, args, binding, source = setup(tmp_path / 'state')
    try:
        alien = source(b'controlled unreceived source', 'controlled_unreceived244')
        if part == 'primary':
            args['selection']['source_ref'] = alien
        elif part == 'image':
            args['selection']['image']['source_ref'] = alien
        elif part == 'context':
            args['selection']['context']['subject']['source_ref'] = alien
        elif part == 'covariance':
            args['selection']['covariance_source_ref'] = alien
        else:
            args['selection']['requested_cells'].reverse()
        out = asyncio.run(binding.execute(ctx, 'literature.figure.populate', args, 'bad244'))
        assert out['status'] == 'invalid'
        assert out['feedback']['code'] == ('endpoint_assignment_request_roster_mismatch' if part == 'order' else 'literature_source_not_received')
        assert not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='literature_endpoint_signal_operations'").fetchone()
    finally:
        store.close()

def test_wrong_source_record_kind_returns_normal_repair_feedback(tmp_path):
    store, ctx, args, binding, _ = setup(tmp_path / 'state')
    try:
        artifact = store.get(args['selection']['source_ref'])['artifact_ref']
        for tool, arguments in [('source.read', {'source_ref': artifact, 'representation': 'original'}), ('source.locate', {'source_ref': artifact, 'representation': 'original', 'needle': 'controlled'})]:
            result = asyncio.run(binding.execute(ctx, tool, arguments, 'wrong_kind244' + tool))
            assert result['status'] == 'invalid' and result['feedback']
        args['selection']['source_ref'] = artifact
        result = asyncio.run(binding.execute(replace(ctx, received_record_refs=(*ctx.received_record_refs, artifact)), 'literature.figure.populate', args, 'wrong_population_kind244'))
        assert result['status'] == 'invalid' and result['feedback']
    finally:
        store.close()




def test_failed_endpoint_history_keeps_task_and_withholds_original_input_dump(tmp_path):
    store, ctx, args, _, _ = setup(tmp_path / 'state')
    try:
        state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1', 'aspect': 'source_experimental_evidence'}, 'literature_assignment': plain(ctx.assignment), 'working_state': {}}
        history = {'status': 'completed', 'result': {'view': 'records', 'records': [{'selection': {'kind': 'tool', 'tool': 'literature.figure.populate', 'arguments': args}, 'outcome': {'status': 'invalid', 'result': None, 'feedback': {'code': 'controlled_missing_source'}}}]}}
        prompt = render_literature_experimental_prompt(state, 'Repair the selected source dependency.', lookup_results=[history])
        task, steering = prompt.split('\n\nSTEERING\n')
        assert ENDPOINT_SIGNAL_TASK in task
        assert 'controlled_missing_source' in steering
        assert '∼0.6' not in steering and 'support_region' not in steering and ('point_rgb' not in steering)
    finally:
        store.close()

def test_union_contract_lookup_keeps_both_distinct_actual_tasks(tmp_path):
    from gene_annotation_episode.episodic_workflow.root.a105.episode_contract_information import operation_contract_information
    store, ctx, _, binding, _ = setup(tmp_path / 'state')
    try:
        state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1', 'aspect': 'source_experimental_evidence'}, 'literature_assignment': plain(ctx.assignment), 'working_state': {}, 'contract_information_profile': 'operation_contract_information_v1'}
        lookup = operation_contract_information(catalog=binding.catalog(ctx), operation='literature.figure.populate')
        task = render_literature_experimental_prompt(state, 'Choose the appropriate figure interpretation.', lookup_results=[lookup]).split('\n\nSTEERING\n')[0]
        assert ENDPOINT_SIGNAL_TASK in task and FIGURE_TASK in task
    finally:
        store.close()



def test_all_sources_keep_assigned_page_ancestry(tmp_path):
    store, ctx, args, binding, source = setup(tmp_path / 'state')
    try:
        primary = args['selection']['source_ref']
        page = {'version': 'page_assignment_v1', 'source_ref': primary, 'representation': 'original', 'artifact_ref': store.get(primary)['artifact_ref'], 'question_context_refs': [], 'prior_delivery_refs': [], REQUESTED: SELECTED}
        pagectx = replace(ctx, role='literature_page', path=(('literature_page', ctx.episode_id),), assignment=page)
        alien = source(store.get_artifact(store.get(args['selection']['image']['source_ref'])['artifact_ref']), 'controlled_unrelated_image244')
        args['selection']['image']['source_ref'] = alien
        pagectx = replace(pagectx, received_record_refs=(*pagectx.received_record_refs, alien))
        out = asyncio.run(literature_binding_for_role(binding, 'literature_page').execute(pagectx, 'literature.figure.populate', args, 'page244'))
        assert out['status'] == 'invalid' and out['feedback']['code'] == 'literature_reading_outside_assigned_source'
    finally:
        store.close()










