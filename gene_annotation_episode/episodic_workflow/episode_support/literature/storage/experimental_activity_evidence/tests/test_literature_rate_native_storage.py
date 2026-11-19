"""Synthetic native rate custody, original saved cells and typed subsets."""
from copy import deepcopy
from dataclasses import replace
import sqlite3
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import ContractError, obj, canonical
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_context import LiteratureContext
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_rate_storage import LiteratureRateRepository, rate_cells_schema, rate_source_cells_schema
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.tests.test_literature_rate_native_inputs import synthetic_case, defined_case

def setup_native_store(path, *, defined=False, approximate=False, reference=None):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    raw, args = defined_case() if defined else synthetic_case()
    if approximate:
        raw, args = synthetic_case(reference='about 12')
        args['arms']['reference']['rate']['number']['number_start'] += len('about ')
    if reference is not None:
        raw, args = synthetic_case(reference=reference)
        args['arms']['reference']['rate']['number']['number_start'] += reference.index('12')
    artifact = store.artifact(raw, 'text/plain')
    source = store.put('source', {'provider': 'synthetic_native_rate_fixture', 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')

    def bind(value):
        if isinstance(value, dict):
            return {key: source['id'] if key == 'source_ref' else bind(child) for key, child in value.items()}
        if isinstance(value, list):
            return [bind(child) for child in value]
        return value
    args = bind(args)
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [], 'source_refs': [source['id']]}
    context = LiteratureContext('native-rate-run', 'native-rate-episode', 'literature', (('literature', 'native-case'),), store.validate_scope({'subject_refs': store.problem()['subject_refs']}), assignment, {}, (source['id'],))
    return (store, context, args)


def test_native_approximation_survives_projection_validation_and_receive(tmp_path):
    store, context, args = setup_native_store(tmp_path, approximate=True)
    try:
        repo = LiteratureRateRepository(store, context.run_id).source_projection()
        outcome = repo.populate_native(context, args, 'selected')
        sheet = outcome['result']['sheet_ref']
        permitted = (*context.received_record_refs, *outcome['record_refs'])
        cells = repo.project_cells([sheet], permitted_record_refs=permitted, components=('reference_rate', 'rate_difference'))
        assert all((row['approximate'] for row in cells))
        wrong = deepcopy(cells)
        wrong[0]['approximate'] = False
        with pytest.raises(ContractError, match='differs_from_saved'):
            repo.validate_returned_values(wrong, permitted_record_refs=permitted)
    finally:
        store.close()

def test_native_replay_rechecks_source_receipt_scope_and_exact_selection(tmp_path):
    store, context, args = setup_native_store(tmp_path)
    try:
        repo = LiteratureRateRepository(store, context.run_id)
        outcome = repo.populate_native(context, args, 'selected')
        with pytest.raises(ContractError, match='not_received'):
            repo.populate_native(replace(context, received_record_refs=()), args, 'selected')
        changed = deepcopy(args)
        changed['arms']['test']['construct'] = changed['arms']['reference']['construct']
        with pytest.raises(ContractError, match='reused_for_different_work'):
            repo.populate_native(context, changed, 'selected')
        with pytest.raises(ContractError, match='run_mismatch'):
            repo.populate_native(replace(context, run_id='another'), args, 'new')
        with pytest.raises(ContractError, match='sheet_not_received'):
            repo.source_projection().project_cells([outcome['result']['sheet_ref']], permitted_record_refs=())
        with pytest.raises(ContractError, match='projection_version_mismatch'):
            repo.project_cells([outcome['result']['sheet_ref']], permitted_record_refs=outcome['record_refs'])
        assert store.db.execute('select count(*) from literature_rate_operations').fetchone()[0] == 1
    finally:
        store.close()

def test_invalid_native_witness_has_no_partially_published_sheet(tmp_path):
    store, context, args = setup_native_store(tmp_path)
    try:
        repo = LiteratureRateRepository(store, context.run_id)
        before = {r[0]: r[1] for r in store.db.execute('select record_type,count(*) from records group by record_type')}
        args['arms']['reference']['subject']['quote'] = 'invented molecule'
        with pytest.raises(ValueError, match='source_quote_mismatch'):
            repo.populate_native(context, args, 'invalid')
        assert before == {r[0]: r[1] for r in store.db.execute('select record_type,count(*) from records group by record_type')}
        assert store.db.execute('select count(*) from literature_rate_operations').fetchone()[0] == 0
    finally:
        store.close()

def test_interrupted_native_publication_rolls_back_records_and_recovers_original_selected_key(tmp_path, monkeypatch):
    store, context, args = setup_native_store(tmp_path)
    try:
        repo = LiteratureRateRepository(store, context.run_id)
        original_put = store.put

        def fail_sheet(kind, value, **kwargs):
            if kind == 'source' and value.get('provider') == repo.provider:
                raise RuntimeError('synthetic interruption before native sheet commit')
            return original_put(kind, value, **kwargs)
        monkeypatch.setattr(store, 'put', fail_sheet)
        with pytest.raises(RuntimeError, match='synthetic interruption'):
            repo.populate_native(context, args, 'selected')
        assert not store.list('reference') and (not store.list('context'))
        assert store.db.execute('select count(*) from literature_rate_operations').fetchone()[0] == 0
        monkeypatch.setattr(store, 'put', original_put)
        first = repo.populate_native(context, args, 'selected')
        assert repo.populate_native(context, args, 'selected') == first
        assert store.db.execute('select count(*) from literature_rate_operations').fetchone()[0] == 1
    finally:
        store.close()


