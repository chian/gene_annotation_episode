"""Synthetic custody, exact-subset communication, rendering and source-free replay."""
from copy import deepcopy
from dataclasses import replace
import json
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import ContractError, obj, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_context import LiteratureContext
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_product_partition_storage import LiteratureProductPartitionRepository, product_partition_cells_schema, binding_references
from gene_annotation_episode.episodic_workflow.episode_support.literature.rendering.experimental_activity_evidence.literature_product_partition_render import render_received, is_row
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.tests.test_literature_product_partition_inputs import fixture, SOURCE, TEXT

def setup(path, raw=TEXT, arguments=None):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    artifact = store.artifact(raw, 'text/plain')
    source = store.put('source', {'provider': 'retained_primary_pmc12051542' if arguments and arguments['source_kind'] == 'primary_source' else 'synthetic_partition_fixture', 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')['id']
    args, _, witness = fixture(raw) if arguments is None else (deepcopy(arguments), None, None)
    if arguments is None:
        args['quantities']['a']['meanings']['denominator'] = witness('R5P 60.3% and Ru5P 39.7%')
        args['evidence'] = [{'role': 'composition', 'witness': witness('R5P 60.3% and Ru5P 39.7%')}, {'role': 'competing_contribution', 'witness': witness('HFP preparation')}]

    def replace_ref(value):
        if isinstance(value, dict):
            return {k: replace_ref(v) for k, v in value.items()}
        if isinstance(value, list):
            return [replace_ref(v) for v in value]
        return source if value == SOURCE else value
    args = replace_ref(args)
    context = LiteratureContext('partition-run', 'partition-child', 'literature', (('literature', 'case'),), store.validate_scope({'subject_refs': store.problem()['subject_refs']}), {'version': 'literature_assignment_v1', 'question_context_refs': [], 'source_refs': [source]}, {}, [source])
    return (store, context, args)


@pytest.mark.parametrize('mutation', [lambda r: r.update(value=99), lambda r: r['quantities'][0].update(basis='signal_fraction'), lambda r: r['relationships'].update(shared_denominator='unknown')])
def test_changed_returned_number_or_meaning_is_rejected(tmp_path, mutation):
    store, context, args = setup(tmp_path)
    try:
        repo = LiteratureProductPartitionRepository(store, context.run_id)
        outcome = repo.populate(context, args, 'selected')
        rows = repo.project_cells([outcome['result']['sheet_ref']], permitted_record_refs=outcome['record_refs'], components=['partition_a_over_b'])
        mutation(rows[0])
        with pytest.raises(ContractError, match='differs_from_saved'):
            repo.validate_returned_values(rows, permitted_record_refs=outcome['record_refs'])
    finally:
        store.close()

def test_source_scope_and_assigned_page_limit_access(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        repo = LiteratureProductPartitionRepository(store, context.run_id)
        with pytest.raises(ContractError, match='not_received'):
            repo.populate(replace(context, received_record_refs=[]), args, 'no-receipt')
        artifact = store.artifact('Other paper', 'text/plain')
        other = store.put('source', {'provider': 'other', 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')['id']
        with pytest.raises(ContractError, match='outside_assigned_source'):
            repo.populate(replace(context, role='literature_page', path=(('literature_page', 'page'),), assignment={'source_ref': other}), args, 'outside')
        assert not repo._installed()
    finally:
        store.close()

def test_cold_query_only_discovery_and_received_lookup_create_no_tables(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        store.db.execute('PRAGMA query_only=ON')
        before = store.db.total_changes
        repo = LiteratureProductPartitionRepository(store, context.run_id)
        assert repo.received_cells(context) == []
        assert repo.project_cells([], permitted_record_refs=[]) == []
        assert not repo._installed()
        assert store.db.total_changes == before
    finally:
        store.close()

def test_own_population_outcome_has_only_original_requested_typed_subset(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        context = replace(context, assignment={**plain(context.assignment), 'requested_product_partition_components': ['selected_fraction_sum']})
        repo = LiteratureProductPartitionRepository(store, context.run_id)
        outcome = repo.populate(context, args, 'selected')
        assert [row['component'] for row in outcome['result']['cells']] == ['selected_fraction_sum']
        assert outcome['result']['cells'][0]['quantities'][0]['meaning_status']['denominator'] == 'withheld_unrequested_numbers'
        assert len(repo.read(outcome['result']['sheet_ref'])['sheet']['cells']) == 5
        records = [store.get(ref) for ref in outcome['record_refs'] if store.get(ref)['record_type'] == 'reference']
        assert all(('60.3' not in row['label'] and '39.7' not in row['label'] for row in records))
        changed = replace(context, assignment={**plain(context.assignment), 'requested_product_partition_components': ['partition_a_fraction']})
        with pytest.raises(ContractError, match='operation_key_reused'):
            repo.populate(changed, args, 'selected')
    finally:
        store.close()
