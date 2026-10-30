"""Multiple experiments share a template without overwriting parent evidence."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain, validate_closed_schema
from gene_annotation_episode.domain import ContractError, canonical, identity, obj, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_a105_worksheet import VERSION, a105_worksheet_template
from gene_annotation_episode.literature_assay_grading import COMPONENTS
from gene_annotation_episode.literature_assay_grading_storage import (
    LiteratureAssayGradingRepository, REQUESTED, NAMESPACE, legacy_assay_grading_cells_schema,
    LEGACY_VERSION, PROVIDER,
)
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_a105_assay_type_binding_322 import grading_fixture
from test_runtime import FixtureController


def two_experiments(store):
    context, first, artifact = grading_fixture(store)
    text = store.get_artifact(artifact).decode()
    quote = 'Experiment B'
    start = text.index(quote)
    original = store.get(first['experiment_ref'])
    record = {k: deepcopy(v) for k, v in original.items() if k not in ('id', 'record_type', 'origin')}
    record.update(accession='synthetic_assay_B', label=quote,
        anchor={'source_ref': first['source_ref'], 'artifact_ref': artifact,
            'start': start, 'end': start + len(quote), 'quote': quote})
    experiment = store.put('reference', record, origin='caller')['id']
    second = deepcopy(first)
    second['experiment_ref'] = experiment
    for role, label, token, unit in (
        ('effect', 'effect', '0.2', 'fraction'),
        ('effect_variance', 'variance', '0.09', 'fraction_squared'),
    ):
        fragment = f'{label} {token} {unit}'
        offset = text.index(fragment, start)
        witness = {'source_ref': first['source_ref'], 'representation': 'original',
            'start': offset, 'end': offset + len(fragment), 'quote': fragment}
        unit_start = offset + len(label) + len(token) + 2
        second['quantities'][role] = {'kind': 'source_number',
            'number': {'witness': witness, 'number_start': len(label) + 1,
                'number_end': len(label) + 1 + len(token)},
            'unit': {**witness, 'start': unit_start, 'end': unit_start + len(unit), 'quote': unit},
            'origin': 'synthetic'}
    return replace(context, received_record_refs=[*context.received_record_refs, experiment]), first, second


def test_parent_retains_two_experiments_and_same_experiment_revision_across_reopen(tmp_path, monkeypatch):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        context, first, second = two_experiments(store)
        repo = LiteratureAssayGradingRepository(store, context.run_id)
        revised = deepcopy(first)
        revised['interpretations']['attribution_supported'] = {'status': 'unknown', 'support_refs': []}
        outcomes = [repo.populate(context, args, key) for args, key in
            ((first, 'experiment-A'), (second, 'experiment-B'), (revised, 'reassess-A'))]
        refs = [outcome['result']['sheet_ref'] for outcome in outcomes]
        parent = replace(context, episode_id='parent', role='annotation', assignment={},
            path=(('annotation', 'parent'),),
            received_record_refs=[*context.received_record_refs, *refs])
        for index, ref in enumerate(refs):
            cells = repo.project_cells([ref], permitted_record_refs=refs,
                components=['measured_effect', 'source_log_evidence_ratio'])
            repo.receive_cells(parent, cells, f'admitted-{index}')
            repo.receive_cells(parent, cells, f'admitted-{index}')
        # Repeated delivery under another receipt does not create another sheet.
        repo.receive_cells(parent, cells, 'repeated-delivery')
        groups = repo.experiment_sheets(parent)
        assert [g['experiment_ref'] for g in groups] == [first['experiment_ref'], second['experiment_ref']]
        assert [len(g['sheets']) for g in groups] == [2, 1]
        assert len(repo.received_cells(parent)) == 6
        assert {r['component'] for g in groups for s in g['sheets'] for r in s['cells']} == {
            'measured_effect', 'source_log_evidence_ratio'}
        assert groups[0]['sheets'][0]['cells'][0]['value'] == .8
        assert groups[1]['sheets'][0]['cells'][0]['value'] == .2
        assert groups[0]['sheets'][1]['cells'][1]['value'] is None
        assert groups[0]['sheets'][0]['cells'][0]['measurement_keys'] == groups[0]['sheets'][1]['cells'][0]['measurement_keys']
        assert groups[0]['sheets'][0]['cells'][0]['measurement_keys'] != groups[1]['sheets'][0]['cells'][0]['measurement_keys']
        # Merely possessing source identifiers does not expose another child's cells.
        outsider = replace(parent, episode_id='other', path=(('annotation', 'other'),))
        assert repo.experiment_sheets(outsider) == []
    def forbidden(*args, **kwargs):
        raise AssertionError('reconstruction must not re-extract or regrade')
    monkeypatch.setattr('gene_annotation_episode.literature_assay_grading_storage.read_assay_grading_inputs', forbidden)
    monkeypatch.setattr('gene_annotation_episode.literature_assay_grading_storage.grade_assay', forbidden)
    with Store(tmp_path) as cold:
        cold.db.execute('PRAGMA query_only=ON')
        changes = cold.db.total_changes
        repo = LiteratureAssayGradingRepository(cold, context.run_id)
        assert repo.experiment_sheets(parent, components=list(COMPONENTS)) == groups
        assert cold.db.total_changes == changes


def test_new_assessments_require_possessed_source_anchored_experiment_identity(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        context, args, _ = grading_fixture(store)
        repo = LiteratureAssayGradingRepository(store, context.run_id)
        missing = deepcopy(args); del missing['experiment_ref']
        with pytest.raises(ContractError, match='experiment_reference_required'):
            repo.populate(context, missing, 'missing')
        wrong = deepcopy(args); wrong['experiment_ref'] = args['assertion_ref']
        with pytest.raises(ContractError, match='anchored_support_required'):
            repo.populate(context, wrong, 'wrong')
        refs = [ref for ref in context.received_record_refs if ref != args['experiment_ref']]
        with pytest.raises(ContractError, match='record_not_received'):
            repo.populate(replace(context, received_record_refs=refs), args, 'unreceived')


def test_original_four_type_parent_contract_is_still_admitted():
    schema = legacy_assay_grading_cells_schema()
    assert 'experiment_ref' not in schema['items']['properties']
    assert len(schema['items']['properties']['assay_type']['enum']) == 4
    validate_closed_schema(obj({'experiment': schema}))


def test_legacy_saved_assessment_does_not_invent_experiment_identity(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        context, args, _ = grading_fixture(store)
        repo = LiteratureAssayGradingRepository(store, context.run_id)
        result = repo.populate(context, args, 'new')
        # Construct a committed historical-v1 fixture with its actual earlier
        # closed shape, rather than backfilling a fabricated experiment key.
        saved = deepcopy(repo.read(result['result']['sheet_ref']))
        saved['version'] = LEGACY_VERSION
        del saved['selection']['experiment_ref']
        saved['extraction']['quantities'].pop('effect_degrees_of_freedom', None)
        request = {'run_id': context.run_id, 'episode_id': context.episode_id,
            'operation_key': 'historical', 'arguments': saved['selection'],
            'scope': plain(context.scope), 'requested_components': list(COMPONENTS)}
        artifact = store.artifact(canonical(saved), 'application/json')
        request_ref = store.artifact(canonical(request), 'application/json')
        source = store.put('source', {'provider': PROVIDER, 'accession': None, 'uri': None,
            'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request_ref,
            'version': LEGACY_VERSION, 'retrieved_at': None,
            'parent_source_refs': saved['input_source_refs']}, origin='tool', scope=plain(context.scope))
        ref = source['id']
        rows = deepcopy(result['result']['cells'])
        for row in rows:
            row['sheet_ref'] = ref
            del row['experiment_ref']
        validate_schema(rows, legacy_assay_grading_cells_schema())
        outcome = {'status': 'completed', 'operation_ref': identity('operation', {
            'run_id': context.run_id, 'episode_id': context.episode_id, 'key': 'historical'}),
            'record_refs': [ref], 'changed_record_refs': [ref],
            'result': {'sheet_ref': ref, 'cells': rows}, 'feedback': None}
        store.db.execute('INSERT INTO literature_assay_grading_operations VALUES(?,?,?,?,?)',
            (context.run_id, context.episode_id, 'historical', canonical(request), canonical(outcome)))
        assert repo.read(ref) == saved
        context = replace(context, received_record_refs=[*context.received_record_refs, ref])
        assert repo.populate(context, saved['selection'], 'historical') == outcome
        groups = repo.experiment_sheets(context)
        assert len(groups) == 1 and groups[0]['experiment_ref'] is None
        assert groups[0]['sheets'][0]['sheet_ref'] == ref


def test_two_children_deliver_separate_experiments_to_same_parent_through_actual_loop(tmp_path):
    with Store(tmp_path / 'store') as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        original, first, second = two_experiments(store)
        selected = ['measured_effect', 'source_log_evidence_ratio']
        template = a105_worksheet_template([{'field': 'experiments', 'source': NAMESPACE, 'components': selected}])
        assessment = {'version': VERSION, 'assertion_refs': [first['assertion_ref']],
            'quantity_links': [], 'assertion_links': []}
        script = []
        for args in (first, second):
            assignment = {**plain(original.assignment), **template['assignment_rosters'],
                'question_context_refs': [args['assertion_ref'], args['experiment_ref']]}
            script.extend([
                {'selection': {'kind': 'episode_child', 'role': 'literature', 'assignment': assignment,
                    'goal': 'Assess this synthetic experiment with the shared assay template.',
                    'scope': store.validate_scope(), 'purpose': 'Retain this experiment in the A105 evidence collection.',
                    'schema_json': json.dumps(template['submitted_form']),
                    'initial_report_json': json.dumps({'assessment_context': assessment})}, 'report_update': {}},
                {'selection': {'kind': 'tool', 'tool': 'literature.assay_grading.populate', 'arguments': args},
                    'report_update': {'assessment_context': assessment}},
            ])
        choices = iter(script)
        contexts, controllers = [], []
        class Provider:
            async def complete(self, episode_id, role, instructions, context, output_schema):
                contexts.append(context)
                return deepcopy(next(choices))
            async def release(self, episode_id):
                pass
        def controller(path, initial):
            result = FixtureController(str(path), initial, 2 if len(path) == 1 else 1)
            controllers.append(result)
            return result
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=Provider(),
            run_dir=tmp_path / 'run', controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=list(original.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                assay_grading_population=True, reference_parent_sources=[first['source_ref']]),),
            binding_definitions={'credit': scorer.as_record()}))
        assert summary['credit'] == 0
        assert len(contexts) == 4 and [c.scores for c in controllers] == [[0, 0], [0], [0]]
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 4
        receipts = store.db.execute('SELECT * FROM literature_assay_grading_received ORDER BY rowid').fetchall()
        assert len(receipts) == 2 and receipts[0]['episode_id'] == receipts[1]['episode_id']
        delivered = [row for receipt in receipts for row in json.loads(receipt['cells'])]
        descriptor = json.loads((tmp_path / 'run' / 'run.json').read_text())['episode_bindings'][0]
        run_id = receipts[0]['run_id']
        services = WorkflowServices(SimpleNamespace(store=store, run_id=run_id))
        binding, = compose_episode_bindings(services, store=store,
            journal=SimpleNamespace(store=store, run_id=run_id), execution_backend=None,
            descriptors=[descriptor], job_episodes=None, resource_estimator=None,
            role_credit_bindings={}).bindings
        repo = binding._assay_grading_repository()
        parent = BindingContext(run_id, receipts[0]['episode_id'], 'annotation',
            (('annotation', receipts[0]['episode_id']),), store.validate_scope(), {}, {}, repo.cell_record_refs(delivered))
        groups = repo.experiment_sheets(parent)
        assert [g['experiment_ref'] for g in groups] == [first['experiment_ref'], second['experiment_ref']]
        assert [s['cells'][0]['value'] for g in groups for s in g['sheets']] == [.8, .2]
        assert all(len(g['sheets']) == 1 and len(g['sheets'][0]['cells']) == 2 for g in groups)
