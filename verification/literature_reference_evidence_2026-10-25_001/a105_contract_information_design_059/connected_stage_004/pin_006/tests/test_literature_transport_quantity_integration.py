"""Actual retained BtsT HTML through the existing quantity return path.

Decisions and controller are fixtures. Primary source bytes are unchanged;
these checks do not establish configured-model scientific execution.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
from pathlib import Path

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_quantity_storage import LiteratureQuantityRepository, quantity_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider
from test_literature_quantity_integration import binding_for


BASE = Path(__file__).resolve().parents[1] / 'verification/literature_reference_evidence_2026-10-25_001'
PRIMARY = BASE / 'primary_btst/source/pmc_article.html'
COMPONENTS = ['reported_value', 'reported_spread', 'relative_reported_spread', 'source_presence_index']
FORM = obj({'measurements': quantity_cells_schema()})


def setup_html(path):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    artifact = store.artifact(PRIMARY.read_bytes(), 'text/html')
    source = store.put('source', {'provider': 'retained_primary_html', 'accession': 'PMC5738728',
        'uri': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC5738728/', 'artifact_ref': artifact,
        'text_ref': None, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
                  'source_refs': [source['id']], 'requested_quantity_components': COMPONENTS}
    context = BindingContext('btst-primary-quantity', 'btst-quantity-child', 'literature',
        (('literature', 'btst'),), store.validate_scope(), assignment, {}, (source['id'],))
    arguments = {'source_ref': source['id'], 'source_kind': 'primary_html', 'section_id': 'sec2-4',
        'paragraph_id': 'direct_paragraph:1', 'subject': 'BtsT', 'quantity': 'apparent_km', 'analyte': 'pyruvate'}
    return store, context, arguments


def test_original_html_saved_quantity_replays_without_original_bytes_or_reader(tmp_path, monkeypatch):
    store, context, args = setup_html(tmp_path)
    try:
        binding = binding_for(store, context)
        outcome = asyncio.run(binding.execute(context, 'literature.quantity.populate', args, 'html-km'))
        assert outcome['status'] == 'completed', outcome.get('feedback')
        repo = LiteratureQuantityRepository(store, context.run_id)
        sheet_ref = outcome['result']['sheet_ref']
        payload = repo.read(sheet_ref)
        extraction = payload['sheet']['extraction']
        assert extraction['version'] == 'a105_html_quantity_v1'
        assert extraction['value'] == 16.5 and extraction['uncertainty']['magnitude'] == 6.4
        assert extraction['uncertainty'] == {'kind': 'unspecified', 'magnitude': 6.4,
                                             'count': None, 'sampling_basis': 'unspecified'}
        assert extraction['source']['paragraph_id'] == 'direct_paragraph:1'
        assert extraction['source']['representation'] == 'primary_html'
        assert extraction['source']['paragraph_text'][extraction['source']['expression_start']:
            extraction['source']['expression_end']] == extraction['source']['expression']
        assert store.get_artifact(payload['input_artifact_ref']) == PRIMARY.read_bytes()
        current = replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))
        rows = repo.project_cells([sheet_ref], permitted_record_refs=current.received_record_refs, components=COMPONENTS)
        assert [r['value'] for r in rows] == [16.5, 6.4, 6.4/16.5, None]
        assert rows[-1]['unavailable_reason'] == 'quantity_not_activity_rate'
        assert all(r['experiment_ref'] is None and r['condition_ref'] is None for r in rows)
        binding.validate_report(current, {'measurements': rows}, FORM)
        wrong = deepcopy(rows)
        wrong[0]['reported_uncertainty_kind'] = 'unreported'
        with pytest.raises(ContractError, match='differs_from_saved'):
            repo.validate_returned_values(wrong, permitted_record_refs=current.received_record_refs)
        parent = replace(current, role='annotation', episode_id='parent', assignment={}, path=(('annotation', 'root'),))
        binding.received_form_references(parent, {'measurements': rows}, FORM, 'html-delivery')
        source = store.get(sheet_ref)
        allowed = {source['artifact_ref'], source['request_ref']}
        original_get = store.get_artifact
        def saved_only(reference):
            assert reference in allowed, 'replay must not read original HTML'
            return original_get(reference)
        def forbidden(*args, **kwargs):
            raise AssertionError('replay must not parse or calculate')
        monkeypatch.setattr(store, 'get_artifact', saved_only)
        monkeypatch.setattr('gene_annotation_episode.literature_html_quantity_reader.read_html_quantity', forbidden)
        monkeypatch.setattr('gene_annotation_episode.literature_activity_calculations.populate_corrected_activity', forbidden)
        store.db.execute('pragma query_only=ON')
        assert repo.populate(context, args, 'html-km') == outcome
        assert repo.read(sheet_ref) == payload
        assert repo.received_cells(parent) == rows
    finally:
        store.close()


def test_primary_html_ordinary_child_returns_only_requested_cells_and_actual_observations(tmp_path):
    store, context, args = setup_html(tmp_path / 'state')
    try:
        seen = []
        child = {'selection': {'kind': 'episode_child', 'role': 'literature',
            'assignment': plain(context.assignment), 'goal': 'Read the reported whole-cell pyruvate Km for BtsT',
            'scope': plain(context.scope), 'purpose': 'Preserve its fitted spread without borrowing caption SEM',
            'schema_json': json.dumps(FORM), 'initial_report_json': '{}'}, 'report_update': {}}
        selected = {'selection': {'kind': 'tool', 'tool': 'literature.quantity.populate',
                                  'arguments': args}, 'report_update': {}}
        def parent_receives(inputs):
            form, = inputs['child_reports']
            seen.append(form)
            assert [r['component'] for r in form['measurements']] == COMPONENTS
            assert [r['value'] for r in form['measurements']] == [16.5, 6.4, 6.4/16.5, None]
            assert all(r['reported_uncertainty_kind'] == 'unspecified' for r in form['measurements'])
            commit = {name: [] for name in store.reasoning_schema()['required']}
            source = store.get(args['source_ref'])
            raw = store.get_artifact(source['artifact_ref'])
            start = raw.index(b'BtsT')
            commit['source_subjects'] = [{'alias': 'source_name', 'reference_type': 'assay',
                'source_ref': source['id'], 'label': 'BtsT', 'anchor': {'source_ref': source['id'],
                    'artifact_ref': source['artifact_ref'], 'start': start, 'end': start+4, 'quote': 'BtsT'}}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store),
            provider=ScriptedProvider([child, selected, parent_receives]), run_dir=tmp_path / 'run',
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 2 if len(path) == 1 else 1),
            project_credit=scorer, initial_known_record_refs=[args['source_ref']],
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            binding_definitions={'credit': scorer.as_record()}))
        assert summary['credit'] == 0 and len(seen) == 1
        assert store.db.execute('select count(*) from runtime_observations').fetchone()[0] == 3
        assert store.db.execute('select count(*) from literature_quantity_operations').fetchone()[0] == 1
        assert store.db.execute('select count(*) from literature_quantity_received').fetchone()[0] == 1
        assert not store.list('observation') and not store.list('assessment')
    finally:
        store.close()
