"""The product-coupling repository on the custody-scoped store: a sheet saved from a source with no selected
quantity, read back, projected and listed, through the real runner."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.evolutionary_history_evidence.literature_product_coupling_inputs import (
    CONTEXT_FIELDS, RELATIONSHIPS, ROLES)

from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.evolutionary_history_evidence.literature_product_coupling_storage import COMPONENTS

from .evolutionary_history_world import call, read, run, source, world  # noqa: F401

REPOSITORY = 'literature_product_coupling_storage:LiteratureProductCouplingRepository'
REQUESTED = 'requested_product_coupling_components'
SHEET = {'from_step': 0, 'path': ['result', 'sheet_ref']}
TEXT = 'The enzyme formed product and consumed cofactor; no coupling value was reported.'


def selection(reference):
    return {'source_ref': reference, 'source_kind': 'synthetic_fixture', 'context': dict.fromkeys(CONTEXT_FIELDS),
            'quantities': dict.fromkeys(ROLES),
            'relationships': {name: {'value': 'unknown', 'witnesses': []} for name in RELATIONSHIPS},
            'nu_cofactor_per_product': {'kind': 'interpreted_reaction_account', 'direction': 'cofactor_per_product',
                                        'status': 'unknown', 'exact_value': None, 'witnesses': []},
            'covariance_source_ref': None}


def test_a_product_coupling_sheet_is_saved_read_back_projected_and_listed(world):
    saved_source, artifact = source(world, TEXT)
    assignment = {REQUESTED: list(COMPONENTS[:2]), 'source_ref': saved_source}
    populated, held, saved, cells, owned = run(world, 'coupling', [
        call(REPOSITORY, 'populate', selection(saved_source), scope=world['scope'], assignment=assignment),
        read(REPOSITORY, 'held_sheet_refs'),
        read(REPOSITORY, 'read', SHEET),
        read(REPOSITORY, 'project_cells', [SHEET]),
        read(REPOSITORY, 'owned_sheet_refs', {})], held=[saved_source, artifact])
    sheet = populated['result']['sheet_ref']
    assert held == owned == [sheet] and saved['input_source_ref'] == saved_source
    assert [row['component'] for row in cells] == list(COMPONENTS[:2]) and {row['sheet_ref'] for row in cells} == {sheet}
