"""Primary table inputs through ordinary episodes; controlled decisions only."""
import asyncio
from dataclasses import replace
from functools import partial
import json
from pathlib import Path
from types import SimpleNamespace

from gene_annotation_episode.communication import form_with_facts, plain
from gene_annotation_episode.domain import canonical, obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_binding_storage import binding_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider


PRIMARY = Path(__file__).resolve().parents[1] / 'verification/literature_reference_evidence_2026-10-25_001/primary_iscr2013'
COMPONENTS = ['reference_parameter', 'test_parameter', 'native_parameter_ratio', 'source_signed_index']
FORM = obj({'measurements': binding_cells_schema()})


def setup_primary(path):
    store = Store(path)
    # Synthetic material only supplies the engineering Store scope. No target
    # annotation or correspondence is asserted by these actual reference inputs.
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    def source(content, provider, parents=()):
        artifact = store.artifact(content, 'application/octet-stream')
        return store.put('source', {'provider': provider, 'accession': None, 'uri': None,
            'artifact_ref': artifact, 'text_ref': None, 'request_ref': None, 'version': None,
            'retrieved_at': None, 'parent_source_refs': list(parents)}, origin='caller')
    html = (PRIMARY / 'PMC3676455.html').read_bytes()
    paper = source(html, 'retained_primary_html')
    picture = source((PRIMARY / 'table3_original.jpg').read_bytes(), 'retained_primary_table_image', [paper['id']])
    table = {'version': 'binding_parameter_table_v1', 'table_id': 'Table3',
        'parameter_kind': 'ic50', 'unit': 'nM', 'uncertainty_basis': 'fit_to_averaged_curve',
        'minimum_experiment_count': 3, 'rows': []}
    # Explicit parent-inspected manual visual transcription; nM comes from the
    # competition Methods, not OCR. The host validates custody, not pixel truth.
    for ligand, expression, box in [('hya', '32 ± 2', [402, 62, 476, 83]),
                                    ('hya (7C to G)', '>510', [402, 110, 476, 131])]:
        table['rows'].append({'subject': 'IscR', 'state': 'apo', 'experiment': 'Table3 competition',
            'ligand': ligand, 'expression': expression, 'locator': {
                'original_source_ref': picture['id'], 'original_artifact_ref': picture['artifact_ref'],
                'image_region': box}})
    transcription = source(canonical(table), 'retained_manual_visual_transcription', [picture['id']])
    start = html.index(b'Equilibrium competition fluorescence assays')
    end = html.index(b'</p>', start)
    witness = {'source_ref': paper['id'], 'representation': 'original', 'start': start, 'end': end,
               'quote': html[start:end].decode('utf-8')}
    refs = [paper['id'], picture['id'], transcription['id']]
    arguments = {'source_ref': transcription['id'], 'representation': 'retained_visual_transcription',
        'subject': 'IscR', 'state': 'apo', 'experiment': 'Table3 competition', 'reference_ligand': 'hya',
        'test_ligand': 'hya (7C to G)', 'parameter_kind': 'ic50', 'design': 'equilibrium_competition',
        'protein_arrangement': 'single_preparation', 'interpretation_witnesses': [witness]}
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
        'source_refs': refs, 'requested_binding_components': COMPONENTS}
    context = BindingContext('binding-primary', 'child', 'literature', (('literature', 'case'),),
        store.validate_scope(), assignment, {}, refs)
    return store, context, arguments


def binding_for(store, context):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding


def assert_requested_components(rows):
    assert [row['component'] for row in rows] == COMPONENTS
    assert rows[0]['value'] == 32 and rows[0]['relation'] == 'eq'
    assert rows[1]['value'] == 510 and rows[1]['relation'] == 'gt'
    assert rows[2]['value'] == 15.9375 and rows[2]['relation'] == 'gt'
    assert rows[2]['bound_kind'] == 'reported_limit_arithmetic'
    assert rows[2]['confidence_bound'] is None
    assert rows[2]['parameter_identification_bound'] is None
    assert rows[2]['parameter_kind'] == 'ic50'
    assert rows[2]['uncertainty_basis'] == 'fit_to_averaged_curve'
    assert rows[2]['minimum_experiment_count'] == 3
    assert rows[2]['independent_preparation_count'] is None
    assert rows[2]['design'] == 'equilibrium_competition'
    assert rows[2]['protein_arrangement'] == 'single_preparation'
    assert rows[2]['source_origins'] == ['visual_transcription']
    assert rows[3]['value'] is None
    assert rows[3]['unavailable_reason'] == 'binding_observation_model_unimplemented'


def test_primary_binding_selection_exposes_only_requested_cells(tmp_path):
    store, context, arguments = setup_primary(tmp_path)
    try:
        binding = binding_for(store, context)
        result = asyncio.run(binding.execute(context, 'literature.binding.populate', arguments, 'selected'))
        assert result['status'] == 'completed', result
        current = replace(context, received_record_refs=(*context.received_record_refs, *result['record_refs']))
        facts = binding.facts(current, {'committed_record_refs': [result['result']['sheet_ref']]})
        form = form_with_facts({}, FORM, facts)
        binding.validate_report(current, form, FORM)
        assert_requested_components(form['measurements'])
        assert store.db.execute('select count(*) from literature_binding_operations').fetchone()[0] == 1
    finally:
        store.close()


def test_primary_selected_child_return_preserves_limit_once_with_ordinary_accounting(tmp_path):
    store, context, arguments = setup_primary(tmp_path / 'state')
    controllers, received = [], []
    try:
        commission = {'selection': {'kind': 'episode_child', 'role': 'literature',
            'assignment': plain(context.assignment),
            'goal': 'Evaluate the supplied reference competition comparison and preserve reported limits and uncertainty basis.',
            'scope': plain(context.scope),
            'purpose': 'Return the requested source binding components with their experimental meaning.',
            'schema_json': json.dumps(FORM), 'initial_report_json': '{}'}, 'report_update': {}}
        work = {'selection': {'kind': 'tool', 'tool': 'literature.binding.populate', 'arguments': arguments},
                'report_update': {}}
        def receive(inputs):
            form, = inputs['child_reports']
            assert_requested_components(form['measurements'])
            received.append(form)
            source = store.get(context.received_record_refs[0])
            original = store.get_artifact(source['artifact_ref'])
            start = original.index(b'IscR')
            commit = {name: [] for name in store.reasoning_schema()['required']}
            commit['source_subjects'] = [{'alias': 'reported_source', 'reference_type': 'assay',
                'source_ref': source['id'], 'label': 'IscR', 'anchor': {
                    'source_ref': source['id'], 'artifact_ref': source['artifact_ref'],
                    'start': start, 'end': start + 4, 'quote': 'IscR'}}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
        def controller(path, initial):
            value = FixtureController(str(path), initial, 2 if len(path) == 1 else 1)
            controllers.append(value)
            return value
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=ScriptedProvider([commission, work, receive]),
            run_dir=tmp_path / 'run', controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            binding_definitions={'credit': scorer.as_record()}))
        assert summary['credit'] == 0
        assert len(received) == 1
        assert [value.scores for value in controllers] == [[0, 0], [0]]
        assert store.db.execute('select count(*) from runtime_observations').fetchone()[0] == 3
        assert store.db.execute('select count(*) from literature_binding_operations').fetchone()[0] == 1
        assert store.db.execute('select count(*) from literature_binding_received').fetchone()[0] == 1
    finally:
        store.close()


def test_native_text_retains_binding_task_and_limit_meaning(tmp_path):
    from gene_annotation_episode.decision_context import state_frame
    from gene_annotation_episode.literature_binding_prompt import BINDING_TASK
    from test_literature_experimental_prompt_delivery import LiteratureWire, snapshot, complete
    state = snapshot()
    state['last_local_outcome'] = {'status': 'completed', 'result': {'cells': {
        'native_parameter_ratio': {'value': 15.9375, 'relation': 'gt', 'unit': 'fraction',
            'status': 'reported_limit', 'origin': 'derived', 'unavailable_reason': None,
            'bound_kind': 'reported_limit_arithmetic', 'confidence_bound': None,
            'parameter_identification_bound': None}}, 'parameter_kind': 'ic50',
        'uncertainty_basis': 'fit_to_averaged_curve', 'minimum_experiment_count': 3,
        'independent_preparation_count': None}}
    wire = LiteratureWire(tmp_path / 'wire')
    asyncio.run(complete(wire, state_frame(state)))
    text = wire.turns_sent()[0]['input'][0]['text']
    task, steering = text.split('\n\nSTEERING\n', 1)
    assert BINDING_TASK in task
    assert 'reported_limit_arithmetic' in steering and 'gt' in steering
    assert 'confidence_bound' in steering and 'parameter_identification_bound' in steering
    assert 'fit_to_averaged_curve' in steering
