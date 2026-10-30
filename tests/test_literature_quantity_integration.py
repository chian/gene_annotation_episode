"""Source-native extraction through real storage and scripted ordinary episodes.

No network or actual model inference is used. The primary-source case uses the
retained original XML bytes, without a manually normalized numerical table.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import ReportBoundaryError, form_with_facts, plain
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_quantity_storage import LiteratureQuantityRepository, quantity_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider

PRIMARY = Path(__file__).resolve().parents[1] / 'verification/literature_reference_evidence_2026-10-25_001/primary_csid/PMC6265302_original.xml'
SYNTHETIC = '<article><body><sec id="s"><p id="p">Protein P has a specific activity of 12 ± 2 umol/min/mg.</p></sec></body></article>'
COMPONENTS = ['reported_value', 'relative_reported_spread', 'source_presence_index']
FORM = obj({'measurements': quantity_cells_schema()})


def setup_store(path, *, primary=False):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    artifact = store.artifact(PRIMARY.read_bytes() if primary else SYNTHETIC, 'application/xml')
    source = store.put('source', {'provider': 'retained_primary_jats' if primary else 'synthetic_fixture',
        'accession': 'PMC6265302' if primary else None, 'uri': None, 'artifact_ref': artifact,
        'text_ref': None, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
                  'source_refs': [source['id']], 'requested_quantity_components': COMPONENTS}
    context = BindingContext('native-quantity-run', 'native-quantity-child', 'literature',
        (('literature', 'case'),), store.validate_scope(), assignment, {}, (source['id'],))
    args = {'source_ref': source['id'], 'source_kind': 'primary_jats' if primary else 'synthetic_fixture',
        'section_id': 'Sec3' if primary else 's', 'paragraph_id': 'Par4' if primary else 'p',
        'subject': 'CsiD' if primary else 'P', 'quantity': 'specific_activity', 'analyte': None}
    return store, context, args


def binding_for(store, context):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding


def test_native_saved_partial_score_exact_return_reopen_and_no_reparse(tmp_path, monkeypatch):
    store, context, args = setup_store(tmp_path)
    repo = LiteratureQuantityRepository(store, context.run_id)
    binding = binding_for(store, context)
    outcome = asyncio.run(binding.execute(context, 'literature.quantity.populate', args, 'native'))
    assert outcome['status'] == 'completed'
    sheet_ref = outcome['result']['sheet_ref']
    current = replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))
    form = form_with_facts({}, FORM, binding.facts(current, {'committed_record_refs': [sheet_ref]}))
    binding.validate_report(current, form, FORM)
    rows = form['measurements']
    assert [r['value'] for r in rows] == [12, 2/12, None]
    assert all(r['reported_uncertainty_kind'] == 'unspecified' for r in rows)
    assert all(r['condition_ref'] is None and r['analyte_ref'] is None for r in rows)
    assert store.get(rows[0]['quantity_ref'])['label'] == 'specific_activity'
    assert store.get(rows[0]['reported_subject_ref'])['label'] == 'P'
    assert all(r['experiment_ref'] is None for r in rows)
    assert rows[2]['unavailable_reason'] == 'correction_inputs_not_supplied'
    wrong = deepcopy(form)
    wrong['measurements'][0]['value'] = 100
    with pytest.raises(ReportBoundaryError, match='differs_from_saved'):
        binding.validate_report(current, wrong, FORM)
    wrong = deepcopy(form)
    wrong['measurements'][0]['reported_uncertainty_kind'] = 'unreported'
    with pytest.raises(ReportBoundaryError, match='differs_from_saved'):
        binding.validate_report(current, wrong, FORM)
    parent = replace(current, role='annotation', episode_id='parent', assignment={}, path=(('annotation', 'root'),))
    binding.received_form_references(parent, form, FORM, 'native-delivery')
    assert binding.received_report_facts(parent)['literature_quantity_cells'] == rows
    assert len(repo.read(sheet_ref)['sheet']['cells']) == 9
    saved = repo.read(sheet_ref)
    descriptors = [binding.as_record()]
    composition = compose_episode_bindings(binding.services, store=store,
        journal=Journal(store, context.run_id), execution_backend=None,
        descriptors=descriptors, job_episodes=None, resource_estimator=None,
        role_credit_bindings={})
    reconstructed, = composition.bindings
    assert reconstructed.as_record() == descriptors[0]
    assert asyncio.run(reconstructed.execute(context, 'literature.quantity.populate', args, 'native')) == outcome
    store.close()
    def forbidden(*args, **kwargs):
        raise AssertionError('reconstruction must not reparse/refit')
    monkeypatch.setattr('gene_annotation_episode.literature_prose_reader.read_jats_quantity', forbidden)
    monkeypatch.setattr('gene_annotation_episode.literature_activity_calculations.populate_corrected_activity', forbidden)
    with Store(tmp_path) as reopened:
        restored = LiteratureQuantityRepository(reopened, context.run_id)
        assert restored.populate(context, args, 'native') == outcome
        assert restored.read(sheet_ref) == saved
        assert restored.received_cells(parent) == rows
        with pytest.raises(ContractError, match='reused_for_different_work'):
            restored.populate(context, {**args, 'paragraph_id': 'other'}, 'native')
        with pytest.raises(ContractError, match='not_received'):
            restored.populate(replace(context, received_record_refs=()), args, 'native')
        with pytest.raises(ContractError, match='run_mismatch'):
            restored.populate(replace(context, run_id='wrong-run'), args, 'other')


def test_bad_source_selector_returns_structured_failure_without_publication(tmp_path):
    store, context, args = setup_store(tmp_path)
    try:
        binding = binding_for(store, context)
        original = len(store.list('source'))
        outcome = asyncio.run(binding.execute(context, 'literature.quantity.populate',
            {**args, 'subject': 'DifferentProtein'}, 'invalid'))
        assert outcome['status'] == 'invalid'
        assert outcome['record_refs'] == []
        assert 'subject_not_in_selected_prose' in outcome['feedback']['code']
        assert len(store.list('source')) == original
        assert store.db.execute('SELECT count(*) FROM literature_quantity_operations').fetchone()[0] == 0
    finally:
        store.close()


def test_primary_original_xml_through_scripted_child_parent_has_no_synthetic_observations(tmp_path):
    store, context, args = setup_store(tmp_path / 'state', primary=True)
    try:
        received, controllers = [], []
        def tool(arguments):
            return {'selection': {'kind': 'tool', 'tool': 'literature.quantity.populate',
                                  'arguments': arguments}, 'report_update': {}}
        child = {'selection': {'kind': 'episode_child', 'role': 'literature',
            'assignment': plain(context.assignment), 'goal': 'Read the selected reported source quantities',
            'scope': plain(context.scope), 'purpose': 'Retain the activity and separate substrate Km values',
            'schema_json': json.dumps(FORM), 'initial_report_json': '{}'}, 'report_update': {}}
        def parent_receives(inputs):
            form, = inputs['child_reports']
            received.append(form)
            rows = form['measurements']
            assert len(rows) == 9  # Three requested cells for each of three saved quantities.
            points = [r for r in rows if r['component'] == 'reported_value']
            assert [r['value'] for r in points] == [53, 650, 100]
            assert [r['unit'] for r in points] == ['umol/min/mg', 'uM', 'uM']
            assert [store.get(r['analyte_ref'])['label'] if r['analyte_ref'] else None for r in points] == [None, 'GA', 'αKG']
            assert all(r['reported_uncertainty_kind'] == 'unspecified' for r in rows)
            assert all(r['condition_ref'] is None for r in rows)
            scores = [r for r in rows if r['component'] == 'source_presence_index']
            assert all(r['value'] is None for r in scores)
            assert [r['unavailable_reason'] for r in scores] == ['correction_inputs_not_supplied',
                'quantity_not_activity_rate', 'quantity_not_activity_rate']
            # Ordinary own reasoning action; no source-to-target assertion added.
            commit = {name: [] for name in store.reasoning_schema()['required']}
            source = store.get(args['source_ref'])
            raw = store.get_artifact(source['artifact_ref'])
            token = args['subject'].encode('utf-8')
            start = raw.index(token)
            commit['source_subjects'] = [{'alias': 'source_name', 'reference_type': 'assay',
                'source_ref': source['id'], 'label': args['subject'], 'anchor': {
                    'source_ref': source['id'], 'artifact_ref': source['artifact_ref'],
                    'start': start, 'end': start + len(token), 'quote': args['subject']}}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
        provider = ScriptedProvider([child, tool(args),
            tool({**args, 'quantity': 'apparent_km', 'analyte': 'GA'}),
            tool({**args, 'quantity': 'apparent_km', 'analyte': 'αKG'}), parent_receives])
        def controller(path, initial):
            result = FixtureController(str(path), initial, 2 if len(path) == 1 else 3)
            controllers.append(result)
            return result
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=tmp_path / 'run', controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=[args['source_ref']],
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            binding_definitions={'credit': scorer.as_record()}))
        assert summary['credit'] == 0
        assert len(received) == 1
        assert [c.scores for c in controllers] == [[0, 0], [0, 0, 0]]
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 5
        assert store.db.execute('SELECT count(*) FROM literature_quantity_operations').fetchone()[0] == 3
        source = store.get(args['source_ref'])
        assert store.get_artifact(source['artifact_ref']) == PRIMARY.read_bytes()
        assert not store.list('observation') and not store.list('assessment')
    finally:
        store.close()
