"""Controlled selected A105 component custody; no configured model science."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.communication import ReportBoundaryError, plain, validate_closed_schema, validate_form
from gene_annotation_episode.episodic_workflow.root.a105.domain import ContractError, canonical, obj
from gene_annotation_episode.episodic_workflow.root.a105.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episodic_workflow.root.a105.episode_services import WorkflowServices
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.episode import LiteratureEpisode
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_product_coupling_storage import LiteratureProductCouplingRepository, product_coupling_cells_schema, COMPONENTS, NAMESPACE, REQUESTED, VIEW
from gene_annotation_episode.episodic_workflow.root.a105.state import Store
from gene_annotation_episode.episodic_workflow.root.a105.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_product_coupling_212 import Source, original
REQUEST = ['product_per_cofactor', 'productive_fraction', 'reported_coupling_percent', 'reconstructed_product_activity', 'productive_fraction_variance']
FORM = obj({'numbers': product_coupling_cells_schema()})

def rebind(value, references):
    if isinstance(value, dict):
        return {name: rebind(child, references) for name, child in value.items()}
    if isinstance(value, list):
        return [rebind(child, references) for child in value]
    return references.get(value, value) if isinstance(value, str) else value

def setup(path, *, requested=REQUEST, primary=None, covariance=False, scale=None, source_fixture=None):
    if primary is not None:
        source, args, _ = original(primary)
    else:
        source = source_fixture or Source(product=scale or '2', cofactor=scale or '4')
        args = source.args()
        args['context']['product_conditions'] = source.witness('pH7.4')
    if covariance:
        source.covariance(args)
    store = Store(path)
    manifest = store.path / 'empty-inputs.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'entries': []}))
    store.create_problem(manifest_path=manifest)
    refs = {}

    def publish(old, raw, provider):
        artifact = store.artifact(raw, 'application/xml' if raw.startswith(b'<') else 'application/json')
        row = store.put('source', {'provider': provider, 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': None, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')
        refs[old] = row['id']
    publish(source.reference, source.content, 'retained_207' if primary is not None else 'synthetic_coupling218')
    for ref, extra in source.extra.items():
        publish(ref, extra['content'], 'synthetic_covariance218')
    args = rebind(args, refs)
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [], 'source_refs': [refs[source.reference]], REQUESTED: list(requested)}
    ctx = BindingContext('coupling218', 'child218', 'literature', (('literature', 'child218'),), store.validate_scope(), assignment, {}, tuple(refs.values()))
    return (store, ctx, args)

def binding_for(store, context, **configuration):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisode(WorkflowServices(host), rate_population=True, **configuration)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding




def test_default_empty_catalog_no_state_and_possession(tmp_path):
    store, ctx, args = setup(tmp_path, requested=[])
    with store:
        binding = binding_for(store, ctx)
        assert 'literature.product_coupling.populate' in {r['name'] for r in binding.catalog(ctx)}
        assert 'product_coupling_population' not in binding.as_record()['configuration']
        assert not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='literature_product_coupling_operations'").fetchone()
        out = asyncio.run(binding.execute(replace(ctx, received_record_refs=()), 'literature.product_coupling.populate', args, 'missing'))
        assert out['feedback']['code'] == 'literature_source_not_received'
        out = asyncio.run(binding.execute(ctx, 'literature.product_coupling.populate', args, 'empty'))
        assert out['status'] == 'completed' and out['result']['cells'] == []
        repo = binding._product_coupling_repository()
        with pytest.raises(ContractError, match='component_not_selected'):
            repo.project_cells(out['record_refs'], permitted_record_refs=out['record_refs'], components=['productive_fraction'])







def test_exact_closed_registered_schema_cannot_be_loosened():
    form = deepcopy(FORM)
    form['properties']['numbers']['items']['properties']['source_value']['type'] = 'number'
    with pytest.raises(ReportBoundaryError, match='registered source'):
        validate_closed_schema(form)












