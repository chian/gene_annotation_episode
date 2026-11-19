"""Selected source custody, exact requested subsets and source-free replay."""
from copy import deepcopy
from dataclasses import replace
import json
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import ContractError, obj, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_context import LiteratureContext
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_active_site_storage import LiteratureActiveSiteRepository, active_site_cells_schema
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.tests.test_literature_active_site_inputs import fixture, SOURCE, TEXT

def setup(path, *, text=TEXT, arguments=None):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    artifact = store.artifact(text, 'text/plain')
    source = store.put('source', {'provider': 'active_site_test_input', 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')['id']
    args = deepcopy(arguments) if arguments else fixture(text)[0]

    def replace_source(value):
        if isinstance(value, dict):
            return {key: replace_source(child) for key, child in value.items()}
        if isinstance(value, list):
            return [replace_source(child) for child in value]
        return source if value == SOURCE else value
    args = replace_source(args)
    context = LiteratureContext('active-run', 'active-child', 'literature', (('literature', 'case'),), store.validate_scope({'subject_refs': store.problem()['subject_refs']}), {'version': 'literature_assignment_v1', 'question_context_refs': [], 'source_refs': [source]}, {}, [source])
    return (store, context, args)


def test_source_scope_and_unselected_copies_cannot_acquire_sheet_ownership(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        repo = LiteratureActiveSiteRepository(store, context.run_id)
        with pytest.raises(ContractError, match='not_received'):
            repo.populate(replace(context, received_record_refs=()), args, 'none')
        assert not repo._installed(repo.operations_table)
        outcome = repo.populate(context, args, 'selected')
        ref = outcome['result']['sheet_ref']
        other = replace(context, episode_id='unrelated', received_record_refs=(ref,))
        assert repo.fact_cells(other, [ref], components=list(repo.components)) == []
        with pytest.raises(ContractError, match='cell_not_received'):
            repo.validate_fact_values(other, outcome['result']['cells'])
    finally:
        store.close()
