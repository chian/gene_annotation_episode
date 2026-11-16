"""Controlled engineering integration of the already converted concentration case."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episodic_workflow.root.a105.episode_services import WorkflowServices
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.episode import LiteratureEpisode
from gene_annotation_episode.episodic_workflow.root.a105.tests.runtime_fixtures import literature_binding_factories, literature_binding_for_role
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_concentration_window_storage import LiteratureConcentrationWindowRepository, concentration_window_cells_schema, concentration_window_operation_schema, ORIGINAL_SCHEMAS, NAMESPACE, REQUESTED, VIEW, VERSION, OPERATION, POPULATION, COMPONENTS
from gene_annotation_episode.episodic_workflow.root.a105.state import Store
from gene_annotation_episode.episodic_workflow.root.a105.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_concentration_window_275 import synthetic, load, CASE
SELECTED = ['substrate_loss', 'chemical_discrepancy', 'fate_fraction', 'source_interval_average_total_product', 'scenario_interval_average_total_product', 'chemical_discrepancy_variance']

def setup(path, components=SELECTED, *, original=False, covariance=None, partial_pair=False):
    if original:
        selection = load('SOURCE_SELECTION_PROPOSAL_002.json')
        docs = {'source:elife65773_original_fig6_xlsx': (CASE / 'elife65773_fig6.xlsx').read_bytes(), 'source:elife65773_original_html': (CASE / 'elife65773.html').read_bytes()}
    else:
        selection, docs = synthetic()
    store = Store(path)
    manifest = path / 'empty-manifest.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'entries': []}))
    store.create_problem(manifest_path=manifest)

    def source(raw, parents=(), origin='caller'):
        artifact = store.artifact(raw)
        return store.put('source', dict(provider='retained_original_concentration281' if original else 'explicit_synthetic_concentration281', accession=None, uri=None, artifact_ref=artifact, text_ref=artifact, request_ref=None, version=None, retrieved_at=None, parent_source_refs=list(parents)), origin=origin)['id']
    mapping = {}
    for old, data in docs.items():
        mapping[old] = source(data, parents=list(mapping.values())[:1])

    def remap(value):
        if isinstance(value, dict):
            return {k: remap(v) for k, v in value.items()}
        if isinstance(value, list):
            return [remap(v) for v in value]
        return mapping.get(value, value) if isinstance(value, str) else value
    selection = remap(selection)
    selection['requested_cells'] = list(components)
    sources = list(mapping.values())

    def read(ref, rep):
        r = store.get(ref)
        a = r['artifact_ref'] if rep == 'original' else r['text_ref']
        return dict(artifact_ref=a, content=store.get_artifact(a))
    if covariance is not None:
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_concentration_window_inputs import read_concentration_window_inputs
        if covariance == 'unsupported':
            raw = b'explicit synthetic observation table; no implemented C estimator'
        else:
            e = read_concentration_window_inputs(selection, read_source=read)
            doc = load('SYNTHETIC_COVARIANCE_DOCUMENT_001.json')
            doc['owner_keys'] = [e['quantities'][r]['owner_key'] for r in doc['roles']]
            doc['dependency_keys'] = [e['quantities'][r]['dependency_keys'] for r in doc['roles']]
            doc['variance_status'] = covariance
            if covariance == 'unknown':
                doc['covariance'] = None
            raw = json.dumps(doc).encode()
        ref = source(raw, parents=[selection['source_ref']])
        sources.append(ref)
        selection['covariance_source_ref'] = ref
        selection['covariance_material'] = 'unsupported_observation_table' if covariance == 'unsupported' else 'closed_joint_estimator_covariance_document'
    if partial_pair:
        selection['pair_relationships']['total_product']['endpoint_comparability'] = dict(value='unknown', witnesses=[])
    context = []
    for name, field in selection['assay'].items():
        if name not in ('arrangement', 'participants') and field is not None:
            context.append(dict(field='assay.' + name, participant_index=None, windows=[dict(start=0, end=len(field['quote'].encode()))]))
    for i, p in enumerate(selection['assay']['participants']):
        context.append(dict(field='assay.participants.identity', participant_index=i, windows=[dict(start=0, end=len(p['identity']['quote'].encode()))]))
    for role, q in selection['quantities'].items():
        if q:
            for name in ('analyte', 'unit'):
                if q[name] is not None:
                    context.append(dict(field='quantities.' + role + '.' + name, participant_index=None, windows=[dict(start=0, end=len(q[name]['quote'].encode()))]))
    args = dict(version=POPULATION, selection=selection, return_context=context)
    assignment = dict(version='literature_assignment_v1', source_refs=sources, question_context_refs=[], **{REQUESTED: list(components)})
    ctx = BindingContext('window281', 'child281', 'literature', (('literature', 'child281'),), store.validate_scope(), assignment, {}, tuple(sources))
    host = SimpleNamespace(store=store, run_id=ctx.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisode(WorkflowServices(host), rate_population=True, reference_parent_sources=sources)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return (store, ctx, args, binding, source)







def test_source_bytes_and_nested_covariance_custody(tmp_path):
    store, ctx, args, binding, source = setup(tmp_path / 'state', ['substrate_loss_variance'])
    try:
        alien = source(b'unreceived covariance')
        args['selection'].update(covariance_source_ref=alien, covariance_material='unsupported_observation_table')
        out = asyncio.run(binding.execute(ctx, OPERATION, args, 'unreceived281'))
        assert out['status'] == 'invalid' and 'not_received' in out['feedback']['code']
        page = dict(version='page_assignment_v1', source_ref=args['selection']['source_ref'], representation='original', artifact_ref=store.get(args['selection']['source_ref'])['artifact_ref'], question_context_refs=[], prior_delivery_refs=[], **{REQUESTED: ['substrate_loss_variance']})
        page_ctx = replace(ctx, role='literature_page', path=(('literature_page', ctx.episode_id),), assignment=page, received_record_refs=(*ctx.received_record_refs, alien))
        out = asyncio.run(literature_binding_for_role(binding, 'literature_page').execute(page_ctx, OPERATION, args, 'outside281'))
        assert out['status'] == 'invalid' and 'outside_assigned_source' in out['feedback']['code']
    finally:
        store.close()


@pytest.mark.parametrize('failure', ['roster', 'source', 'context_number', 'participant', 'utf8', 'overlap'])
def test_selected_preflight_failures_do_not_commit(tmp_path, failure):
    store, ctx, args, binding, source = setup(tmp_path / 'state', original=failure == 'utf8')
    try:
        if failure == 'roster':
            args['selection']['requested_cells'].reverse()
        elif failure == 'source':
            args['selection']['source_ref'] = source(b'not received')
        elif failure == 'context_number':
            q = args['selection']['quantities']['substrate_start']
            args['selection']['assay']['conditions'] = deepcopy(q['number']['field'])
            entry = next((v for v in args['return_context'] if v['field'] == 'assay.conditions'))
            entry['windows'] = [dict(start=0, end=len(q['number']['field']['quote'].encode()))]
        elif failure == 'participant':
            args['return_context'][0]['participant_index'] = 0
        elif failure == 'utf8':
            field = args['selection']['assay']['conditions']
            raw = field['quote'].encode()
            index = next((i for i, b in enumerate(raw) if b >= 128))
            entry = next((v for v in args['return_context'] if v['field'] == 'assay.conditions'))
            entry['windows'] = [dict(start=index + 1, end=len(raw))]
        else:
            args['return_context'][0]['windows'] *= 2
        outcome = asyncio.run(binding.execute(ctx, OPERATION, args, 'bad281'))
        assert outcome['status'] == 'invalid' and outcome['feedback']
        assert not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='literature_concentration_window_operations'").fetchone()
    finally:
        store.close()





