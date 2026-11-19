"""Engineering fixtures for optional exact source-rate meaning custody.

Constructed source bytes and scripted choices are not primary-source findings.
"""
from copy import deepcopy
from dataclasses import replace
import sqlite3
import pytest
from jsonschema import Draft202012Validator
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import ContractError, obj
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_rate_meaning_delivery import NAMESPACE, COMPONENT_ROLES, source_meaning_projection, rate_source_meaning_cells_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.rendering.experimental_activity_evidence.literature_rate_meaning_render import base_rows, render_received
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_rate_storage import LiteratureRateRepository
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.tests.test_literature_rate_native_storage import setup_native_store

@pytest.mark.parametrize('defined', [False, True])
def test_exact_meaning_view_preserves_cells_and_dependency_roles_without_new_work(tmp_path, defined):
    store, context, args = setup_native_store(tmp_path, defined=defined)
    try:
        repository = LiteratureRateRepository(store, context.run_id)
        outcome = repository.populate_native(context, args, 'selected')
        reference = outcome['result']['sheet_ref']
        owner = replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))
        before = store.db.total_changes
        view = source_meaning_projection(repository)
        assert view.received_cells(owner) == []
        assert store.db.total_changes == before
        rows = view.fact_cells(owner, [reference], components=list(COMPONENT_ROLES))
        assert base_rows(rows) == repository.source_domain_projection().fact_cells(owner, [reference], components=list(COMPONENT_ROLES))
        extraction = repository.read(reference)['sheet']['extraction']
        validator = Draft202012Validator(rate_source_meaning_cells_schema())
        assert validator.is_valid(rows), list(validator.iter_errors(rows))
        for row in rows:
            assert [meaning['arm'] for meaning in row['rate_meanings']] == list(COMPONENT_ROLES[row['component']])
            assert row['comparison_intended_change'] == extraction['native_context']['comparison']['intended_change']
            for meaning in row['rate_meanings']:
                original = next((item for item in extraction['rows'] if item['arm'] == meaning['arm']))['source']
                assert meaning['rate_unit'] == original['unit']
                assert meaning['endpoint'] == original['meanings']['endpoint']
                assert meaning['normalization'] == original['meanings']['normalization']
                assert set(meaning) == {'arm', 'endpoint', 'normalization', 'rate_unit'}
        assert store.db.total_changes == before
        assert store.db.execute('SELECT count(*) FROM literature_rate_operations').fetchone()[0] == 1
        assert not store.list('observation') and (not store.list('assessment'))
    finally:
        store.close()








