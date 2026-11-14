"""Original source operands under controlled ordinary Workflow decisions."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
from importlib import import_module
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a102.communication import form_with_facts, plain
from gene_annotation_episode.episodic_workflow.root.a102.domain import ContractError, obj
from gene_annotation_episode.episodic_workflow.root.a102.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episodic_workflow.root.a102.episode_services import WorkflowServices
from gene_annotation_episode.episodic_workflow.root.a102.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.episodic_workflow.root.a102.published_evidence_assessment.episode import LiteratureEpisode
from gene_annotation_episode.episodic_workflow.root.a102.literature_structure_storage import LiteratureStructureRepository, structure_cells_schema
from gene_annotation_episode.episodic_workflow.root.a102.runtime import run_workflow
from gene_annotation_episode.episodic_workflow.root.a102.state import Store
from gene_annotation_episode.episodic_workflow.root.a102.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.root.a106.tests.test_literature_perturbation_integration import source, witness
from test_runtime import FixtureController, ScriptedProvider

LITERATURE_PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a102.published_evidence_assessment'
EXAMINATION = '.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination'
LITERATURE_HOMES = ('', '.evidence_search_strategy_improvement',
    '.evidence_search_strategy_improvement.source_relevance_assessment', EXAMINATION,
    EXAMINATION + '.table_evidence_extraction', EXAMINATION + '.source_coverage_improvement',
    EXAMINATION + '.passage_evidence_extraction')


def literature_home_factories(**configuration):
    """One factory per private A102 literature home, in the order of create_binding_tree."""
    return tuple(partial(import_module(LITERATURE_PACKAGE + home + '.episode').LiteratureEpisode, **configuration)
        for home in LITERATURE_HOMES)


BASE = Path(__file__).parent / 'fixtures/literature_structure'
COMPONENTS = ['local_fit_index', 'geometry_support_fraction', 'source_geometry_positive', 'source_geometry_signed']
FORM = obj({'measurements': structure_cells_schema()})


def setup_case(path, *, validation=True):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    raw = (BASE / 'PMC3676455.html').read_bytes()
    paper = source(store, raw)
    cif = (BASE / '4HF1_cif').read_bytes()
    coordinates = source(store, cif, parents=[paper['id']])
    refs = [paper['id'], coordinates['id']]
    validation_ref = None
    if validation:
        report = source(store, (BASE / '4hf1_validation.xml').read_bytes(),
            parents=[paper['id']])
        validation_ref = report['id']
        refs.append(validation_ref)
    def residue(chain, number, name):
        return {'auth_chain': chain, 'auth_seq_id': str(number), 'comp_id': name, 'insertion_code': '', 'alt_id': '.'}
    def endpoint(chain, number, name, atoms):
        return {**residue(chain, number, name), 'atom_names': atoms}
    geometry = []
    for pc, dc, number, name, atom in [('A', 'D', 7, 'DC', 'N4'), ('A', 'D', 8, 'DA', 'N6'),
            ('B', 'C', 7, 'DC', 'N4'), ('B', 'C', 8, 'DC', 'N4')]:
        geometry.append({'endpoint_a': endpoint(pc, 43, 'GLU', ['OE1', 'OE2']),
            'endpoint_b': endpoint(dc, number, name, [atom]), 'positive_max_A': 3.5, 'incompatible_min_A': 4.5})
    local = [residue(c, n, name) for c, n, name in [('A', 43, 'GLU'), ('B', 43, 'GLU'),
        ('D', 7, 'DC'), ('D', 8, 'DA'), ('C', 7, 'DC'), ('C', 8, 'DC')]]
    literals = {'molecule': witness(paper['id'], raw, 'IscR'),
        'construct': witness(coordinates['id'], cif, 'C92A, C98A, C104A'),
        'experimental_system': witness(paper['id'], raw, 'BL21(DE3)'),
        'partner': witness(coordinates['id'], cif, 'ATAAATCCACACAGTTTGTATTGTTTTGT'),
        'experiment': None, 'condition': None}
    args = {'source_ref': paper['id'], 'coordinate_source_ref': coordinates['id'],
        'validation_source_ref': validation_ref, 'source_kind': 'primary_source', 'model_number': 1,
        'literals': literals, 'geometry_panel': geometry, 'local_panel': local,
        'evaluation_scope': 'conditional_deposited_model_geometry'}
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
        'source_refs': refs, 'requested_structure_components': COMPONENTS}
    context = BindingContext('structure-fixture-run', 'structure-fixture-child', 'literature',
        (('literature', 'fixture'),), store.validate_scope(), assignment, {}, tuple(refs))
    return store, context, args


@pytest.mark.parametrize('validation', [False, True])
def test_original_source_selected_cells_and_saved_only_binding_reconstruction(tmp_path, monkeypatch, validation):
    from gene_annotation_episode.episodic_workflow.root.a102.episode_composition import compose_episode_bindings
    from gene_annotation_episode.episodic_workflow.root.a102.episode_journal import Journal
    store, context, args = setup_case(tmp_path, validation=validation)
    with store:
        host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
        binding = LiteratureEpisode(WorkflowServices(host), structure_population=True)
        host.episode_bindings = EpisodeBindingRegistry((binding,))
        outcome = asyncio.run(binding.execute(context, 'literature.structure.populate', args, 'selected'))
        assert outcome['status'] == 'completed', outcome.get('feedback')
        current = replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))
        selected = {'committed_record_refs': [outcome['result']['sheet_ref']]}
        facts = binding.facts(current, selected)
        form = form_with_facts({}, FORM, facts)
        binding.validate_report(current, form, FORM)
        rows = form['measurements']
        assert [row['component'] for row in rows] == COMPONENTS
        assert rows[1]['value'] == .75
        if validation:
            assert [row['value'] for row in rows] == pytest.approx([.815409, .75, .61155675, .61155675])
        else:
            assert rows[0]['value'] is rows[2]['value'] is rows[3]['value'] is None
            assert rows[0]['unavailable_reason'] == 'validation_not_joined'
        assert all(row['unconditional_uncertainty'] == 'unreported' for row in rows)
        assert all(row['occupancy_basis'] == 'conditioned_selected_model' for row in rows)
        assert all(row['bound_kind'] == 'conditional_arithmetic_outer' for row in rows)
        assert all(row['geometry_definition'] == args['geometry_panel'] for row in rows)
        assert all(row['local_validation_definition'] == args['local_panel'] for row in rows)
        assert all(row['local_validation_granularity'] == 'residue' for row in rows)
        assert all(row['transform_basis'] == 'identity_coordinates_only' for row in rows)
        repo = LiteratureStructureRepository(store, context.run_id)
        payload = repo.read(outcome['result']['sheet_ref'])
        distances = [row['distance_A'] for row in payload['sheet']['native_geometry']]
        assert distances == pytest.approx([2.814260471, 3.504470573, 2.648124053, 3.056920182])
        bad = deepcopy(rows)
        bad[0]['occupancy_basis'] = 'measured_population_fraction'
        with pytest.raises(ContractError):
            repo.validate_returned_values(bad, permitted_record_refs=current.received_record_refs)
        descriptor = binding.as_record()
        composition = compose_episode_bindings(binding.services, store=store,
            journal=Journal(store, context.run_id), execution_backend=None,
            descriptors=[descriptor], job_episodes=None, resource_estimator=None, role_credit_bindings={})
        reconstructed, = composition.bindings
        assert reconstructed.as_record() == descriptor
        saved = store.get(outcome['result']['sheet_ref'])
        allowed = {saved['artifact_ref'], saved['request_ref']}
        get_artifact = store.get_artifact
        def saved_only(ref):
            assert ref in allowed, 'no original coordinate, validation or paper reads on replay'
            return get_artifact(ref)
        def forbidden(*args, **kwargs):
            raise AssertionError('reconstruction must copy committed source values')
        monkeypatch.setattr(store, 'get_artifact', saved_only)
        monkeypatch.setattr('gene_annotation_episode.episodic_workflow.root.a102.literature_structure_storage.read_structure_inputs', forbidden)
        monkeypatch.setattr('gene_annotation_episode.episodic_workflow.root.a102.literature_structure_storage.populate_source_geometry', forbidden)
        store.db.execute('pragma query_only=ON')
        assert asyncio.run(reconstructed.execute(context, 'literature.structure.populate', args, 'selected')) == outcome
        assert form_with_facts({}, FORM, reconstructed.facts(current, selected)) == form


@pytest.mark.parametrize('validation', [False, True])
def test_structure_selected_in_ordinary_child_and_received_once(tmp_path, validation):
    store, context, args = setup_case(tmp_path / 'state', validation=validation)
    received = []
    with store:
        commission = {'selection': {'kind': 'episode_child', 'role': 'literature',
            'assignment': plain(context.assignment), 'goal': 'Evaluate the four stated contacts in the selected apo-IscR model',
            'scope': plain(context.scope), 'purpose': 'Return only requested source geometry and fit components',
            'schema_json': json.dumps(FORM), 'initial_report_json': '{}'}, 'report_update': {}}
        action = {'selection': {'kind': 'tool', 'tool': 'literature.structure.populate', 'arguments': args}, 'report_update': {}}
        def receive(inputs):
            form, = inputs['child_reports']
            received.append(form)
            rows = form['measurements']
            assert len(rows) == 4 and rows[1]['value'] == .75
            if validation:
                assert rows[2]['value'] == pytest.approx(.61155675)
            else:
                assert rows[2]['value'] is None
            commit = {name: [] for name in store.reasoning_schema()['required']}
            paper = store.get(args['source_ref'])
            raw = store.get_artifact(paper['artifact_ref'])
            start = raw.index(b'IscR')
            commit['source_subjects'] = [{'alias': 'studied_molecule', 'reference_type': 'assay',
                'source_ref': paper['id'], 'label': 'IscR', 'anchor': {'source_ref': paper['id'],
                    'artifact_ref': paper['artifact_ref'], 'start': start, 'end': start+4, 'quote': 'IscR'}}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=ScriptedProvider([
            commission, action, receive]), run_dir=tmp_path / 'run',
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 2 if len(path)==1 else 1),
            project_credit=scorer, initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=literature_home_factories(structure_population=True),
            binding_definitions={'credit': scorer.as_record()}))
        assert summary['credit'] == 0 and len(received) == 1
        assert store.db.execute('select count(*) from runtime_observations').fetchone()[0] == 3
        assert store.db.execute('select count(*) from literature_structure_operations').fetchone()[0] == 1
        assert store.db.execute('select count(*) from literature_structure_received').fetchone()[0] == 1
        assert not store.list('observation') and not store.list('assessment')
