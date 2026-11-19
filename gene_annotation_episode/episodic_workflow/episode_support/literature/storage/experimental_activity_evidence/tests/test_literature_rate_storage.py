"""Controlled synthetic table -> saved source sheet -> real typed form boundary.

No paper acquisition, model decision or full LiteratureEpisode run is claimed.
"""
from dataclasses import replace
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import ContractError, obj
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_context import LiteratureContext
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_experimental_contracts import HEADERS
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_rate_storage import LiteratureRateRepository, rate_cells_schema
from gene_annotation_episode.state import Store

def setup_store(path):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    text = '\t'.join(HEADERS) + '\n' + '\n'.join(('\t'.join(row) for row in [['source construct', 'experiment 1', 'reference', 'without inhibitor', 'oxygen_rate', 'per_preparation', '2', 'umol/min', 'sd', '.2', '3', 'unspecified', 'synthetic'], ['source construct', 'experiment 1', 'test', 'with inhibitor', 'oxygen_rate', 'per_preparation', '1', 'umol/min', 'sd', '.3', '3', 'unspecified', 'synthetic']])) + '\n'
    artifact = store.artifact(text, 'text/tab-separated-values')
    source = store.put('source', {'provider': 'synthetic_rate_fixture', 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')
    context = LiteratureContext('source-rate-run', 'source-rate-episode', 'literature_table', (('literature_table', 'case'),), store.validate_scope({'subject_refs': store.problem()['subject_refs']}), {}, {}, (source['id'],))
    args = {'source_ref': source['id'], 'source_representation': 'original', 'table_kind': 'synthetic_fixture', 'delimiter': '\t', 'subject': 'source construct', 'experiment': 'experiment 1', 'reference_arm': 'reference', 'test_arm': 'test', 'reference_condition': 'without inhibitor', 'test_condition': 'with inhibitor', 'dependence': 'unknown', 'observation_model': 'none'}
    return (store, context, args)


def test_authoritative_values_reject_syntactically_valid_wrong_score(tmp_path):
    store, context, args = setup_store(tmp_path)
    with store:
        repo = LiteratureRateRepository(store, context.run_id)
        ref = repo.populate(context, args, 'selected')['result']['sheet_ref']
        received = (args['source_ref'], ref)
        cells = repo.project_cells([ref], permitted_record_refs=received, components=('rate_difference',))
        cells[0]['value'] = 999
        with pytest.raises(ContractError, match='differs_from_saved'):
            repo.validate_cells(cells, sheet_refs=[ref], permitted_record_refs=received, components=('rate_difference',))

def test_receipt_and_operation_identity_are_checked_on_replay(tmp_path):
    store, context, args = setup_store(tmp_path)
    try:
        repo = LiteratureRateRepository(store, context.run_id)
        result = repo.populate(context, args, 'selected')
        with pytest.raises(ContractError, match='not_received'):
            repo.populate(replace(context, received_record_refs=()), args, 'selected')
        changed = {**args, 'test_condition': 'another condition'}
        with pytest.raises(ContractError, match='reused_for_different_work'):
            repo.populate(context, changed, 'selected')
        with pytest.raises(ContractError, match='sheet_not_received'):
            repo.project_cells([result['result']['sheet_ref']], permitted_record_refs=())
        with pytest.raises(ContractError, match='run_mismatch'):
            repo.populate(replace(context, run_id='another-run'), args, 'new')
        assert store.db.execute('SELECT count(*) FROM literature_rate_operations').fetchone()[0] == 1
    finally:
        store.close()

def test_repeated_population_does_not_report_existing_source_facts_as_new(tmp_path):
    store, context, args = setup_store(tmp_path)
    try:
        repo = LiteratureRateRepository(store, context.run_id)
        first = repo.populate(context, args, 'first')
        second = repo.populate(context, args, 'second')
        first_semantic = set(first['record_refs']) - {first['result']['sheet_ref']}
        assert first_semantic <= set(second['record_refs'])
        assert not first_semantic.intersection(second['changed_record_refs'])
        assert second['changed_record_refs'] == [second['result']['sheet_ref']]
    finally:
        store.close()

def test_header_only_source_does_not_establish_requested_subject_or_experiment(tmp_path):
    store, context, args = setup_store(tmp_path)
    try:
        artifact = store.artifact('\t'.join(HEADERS) + '\n', 'text/tab-separated-values')
        source = store.put('source', {'provider': 'synthetic_empty_table', 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')
        repo = LiteratureRateRepository(store, context.run_id)
        result = repo.populate(replace(context, received_record_refs=(source['id'],)), {**args, 'source_ref': source['id']}, 'empty-source')
        saved = repo.read(result['result']['sheet_ref'])
        assert all((ref is None for ref in saved['experimental_bindings'].values()))
        assert all((cell['value'] is None for cell in saved['sheet']['cells'].values()))
        assert not store.list('reference') and (not store.list('context'))
    finally:
        store.close()

def test_invalid_comparison_does_not_publish_partial_source_sheet(tmp_path):
    store, context, args = setup_store(tmp_path)
    try:
        repo = LiteratureRateRepository(store, context.run_id)
        original_sources = store.list('source')
        with pytest.raises(ValueError, match='condition_mismatch'):
            repo.populate(context, {**args, 'test_condition': 'wrong condition'}, 'bad')
        assert store.db.execute('SELECT count(*) FROM literature_rate_operations').fetchone()[0] == 0
        assert store.list('source') == original_sources
    finally:
        store.close()
