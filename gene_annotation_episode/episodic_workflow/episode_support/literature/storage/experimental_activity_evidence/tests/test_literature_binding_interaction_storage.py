"""Synthetic selected four-cell persistence, custody and finite native returns."""
from dataclasses import replace
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import ContractError, canonical, obj
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_context import LiteratureContext
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_binding_interaction_storage import LiteratureBindingInteractionRepository, COMPONENTS, RAW_COMPONENTS, binding_interaction_cells_schema
from .unit_world import in_unit
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.tests.test_literature_binding_interaction_inputs import fixture, png

def setup(store, ctx, change=None, expressions=('5', '40', '2', '4'), unit='nM', extra=''):
    args, sources, *_ = fixture(expressions, unit, extra)
    if change:
        change(args)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    refs = {}
    for key, raw in sources.items():
        artifact = store.artifact(raw, 'image/png' if key == 'image' else 'text/plain')
        refs[key] = store.put('source', {'provider': 'synthetic_binding_' + key, 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact if key == 'methods' else None, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')['id']

    def bind(value):
        if isinstance(value, dict):
            return {k: refs.get(v, v) if k in ('source_ref', 'original_source_ref') else bind(v) for k, v in value.items()}
        if isinstance(value, list):
            return [bind(v) for v in value]
        return value
    args = bind(args)
    context = LiteratureContext(ctx.run_id, ctx.episode_id, 'literature', (('literature', 'case'),), store.validate_scope({'subject_refs': store.problem()['subject_refs']}), {'version': 'literature_assignment', 'question_context_refs': [], 'source_refs': list(refs.values())}, {}, tuple(refs.values()))
    return (store, context, args)






@in_unit
def test_authorization_precedes_bytes_and_page_ancestry_is_actual(store, ctx):
    store, context, args = setup(store, ctx)
    repo = LiteratureBindingInteractionRepository(store, context.run_id)

    def forbidden(*_):
        raise AssertionError('unauthorized source bytes')
    with pytest.raises(ContractError, match='not_received'):
        repo.populate(replace(context, received_record_refs=()), args, 'unauthorized')
    page = {'source_ref': args['source_ref']}
    with pytest.raises(ContractError, match='outside_assigned_source'):
        repo.populate(replace(context, role='literature_targeted', path=(('literature_targeted', 'case'),), assignment={'page': page}), args, 'wrong-page')






