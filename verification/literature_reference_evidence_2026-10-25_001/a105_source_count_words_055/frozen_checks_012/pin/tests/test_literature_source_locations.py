"""Controlled synthetic selected lookup -> native cells -> ordinary typed return."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_assay_inputs import ASSAY_LITERAL_FIELDS, PRIMITIVE_ORDER
from gene_annotation_episode.literature_assay_storage import LiteratureAssayRepository, assay_cells_schema
from gene_annotation_episode.literature_episodes import LiteratureEpisodes, ROLES
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider
from test_source_locations import source

RAW = 'α Protein P; measured product formation. Reported sample-minus-no-enzyme-blank net rate 1.00 µM/min.\r\n'.encode()
COMPONENTS = ['net_rate', 'corrected_activity']
FORM = obj({'measurements': assay_cells_schema()})


def fixture(path):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    row = source(store, RAW, text='Protein P; product formation; 1.00 µM/min.')
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
        'source_refs': [row['id']], 'requested_assay_components': COMPONENTS}
    context = BindingContext('location-run', 'location-child', 'literature', (('literature', 'fixture'),),
        store.validate_scope(), assignment, {}, (row['id'],))
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return store, row, context, binding


def tool(name, arguments):
    return {'selection': {'kind': 'tool', 'tool': name, 'arguments': arguments}, 'report_update': {}}


def lookup(row, quote):
    return tool('source.locate', {'source_ref': row['id'], 'representation': 'original',
        'needle': quote, 'context_bytes': 12})


def assay_args(row, witnesses):
    literals = dict.fromkeys(ASSAY_LITERAL_FIELDS)
    literals.update(molecule=witnesses['Protein P'])
    literals['endpoint'] = {'value': 'product_formation', 'witnesses': [witnesses['product formation']]}
    literals['arrangement'] = {'value': 'unknown', 'witnesses': []}
    primitives = dict.fromkeys(PRIMITIVE_ORDER)
    primitives['q'] = {'witness': witnesses['1.00 µM/min'], 'number_start': 0, 'number_end': 4,
        'unit_start': 5, 'unit_end': 11}
    return {'source_ref': row['id'], 'source_kind': 'synthetic_fixture', 'assay': literals,
        'primitives': primitives, 'covariance_source_ref': None, 'distinct_residual_variance': None,
        'variance_status': 'unknown', 'observation_model': 'none', 'model_witnesses': []}


def test_selected_read_lookup_native_population_and_exact_typed_parent_accounting(tmp_path):
    store, row, context, binding = fixture(tmp_path / 'state')
    witnesses, received, controllers, original_args = {}, [], [], []
    with store:
        initial_source_count = len(store.list('source'))
        commission = {'selection': {'kind': 'episode_child', 'role': 'literature',
            'assignment': plain(context.assignment), 'goal': 'Extract the synthetic reference rate and retain missing corrections',
            'scope': plain(context.scope), 'purpose': 'Return exactly the requested native assay cells and source endpoint',
            'schema_json': json.dumps(FORM), 'initial_report_json': '{}'}, 'report_update': {}}
        def initial_lookup(inputs):
            assert inputs['last_local_outcome']['result']['text'] == RAW.decode()
            return lookup(row, 'Protein P')
        def next_lookup(previous, quote):
            def select(inputs):
                match, = inputs['last_local_outcome']['result']['matches']
                witnesses[previous] = plain(match['witness'])
                return lookup(row, quote)
            return select
        def populate(inputs):
            match, = inputs['last_local_outcome']['result']['matches']
            witnesses['1.00 µM/min'] = plain(match['witness'])
            args = assay_args(row, witnesses)
            original_args.append(deepcopy(args))
            return tool('literature.assay.populate', args)
        def receive(inputs):
            form, = inputs['child_reports']
            cells = plain(form['measurements'])
            assert [cell['component'] for cell in cells] == COMPONENTS
            assert cells[0]['value'] == 1 and cells[0]['unit'] == 'uM/min'
            assert cells[1]['value'] is None and cells[1]['unavailable_reason'] == 'correction_inputs_unreported'
            assert all(cell['evidence_source_ref'] == row['id'] for cell in cells)
            assert all(cell['endpoint_kind'] == 'product_formation' for cell in cells)
            refs = {ref['id']: ref for ref in inputs['working_state']['references']}
            assert refs[cells[0]['assayed_subject_ref']]['label'] == 'Protein P'
            terms = {term['id']: term for term in inputs['working_state']['terms']}
            assert terms[cells[0]['endpoint_ref']]['label'] == 'product_formation'
            received.append(cells)
            commit = {name: [] for name in store.reasoning_schema()['required']}
            anchor = {name: value for name, value in witnesses['Protein P'].items() if name != 'representation'}
            anchor['artifact_ref'] = row['artifact_ref']
            commit['source_subjects'] = [{'alias': 'source_molecule', 'reference_type': 'assay',
                'source_ref': row['id'], 'label': 'Protein P', 'anchor': anchor}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
        def controller(path, initial):
            instance = FixtureController(str(path), initial, 2 if len(path) == 1 else 5)
            controllers.append(instance)
            return instance
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        actions = [commission, tool('source.read', {'source_ref': row['id'], 'representation': 'original'}),
            initial_lookup, next_lookup('Protein P', 'product formation'),
            next_lookup('product formation', '1.00 µM/min'), populate, receive]
        result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=ScriptedProvider(actions),
            run_dir=tmp_path/'run', controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=[row['id']], episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            binding_definitions={'credit': scorer.as_record()}))
        assert len(received) == 1 and result['credit'] == 0
        assert [item.scores for item in controllers] == [[0, 0], [0, 0, 0, 0, 0]]
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 7
        assert store.db.execute('SELECT count(*) FROM tool_operations WHERE name=?', ('source.locate',)).fetchone()[0] == 3
        assert store.db.execute('SELECT count(*) FROM literature_assay_operations').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM literature_assay_received').fetchone()[0] == 1
        assert not store.list('observation') and not store.list('assessment')
        # Lookups are literal operations, not newly acquired source records.
        assert len(store.list('source')) == initial_source_count + 1  # selected populated sheet only
        operation = store.db.execute('SELECT run_id,outcome FROM literature_assay_operations').fetchone()
        sheet_ref = json.loads(operation['outcome'])['result']['sheet_ref']
        saved = LiteratureAssayRepository(store, operation['run_id']).read(sheet_ref)
        request = json.loads(store.get_artifact(store.get(sheet_ref)['request_ref']))
        assert request['arguments'] == original_args[0]
        parsed = saved['sheet']['extraction']['primitive_observations']['q']['witness']
        assert {name: parsed[name] for name in witnesses['1.00 µM/min']} == witnesses['1.00 µM/min']
        assert parsed['artifact_ref'] == row['artifact_ref']


def page_context(context, row, role='literature_page'):
    page = {'version': 'page_assignment_v1', 'source_ref': row['id'], 'representation': 'original',
        'artifact_ref': row['artifact_ref'], 'question_context_refs': [], 'prior_delivery_refs': []}
    assignment = page if role == 'literature_page' else {'version': 'reading_assignment_v1', 'page': page,
        'selection': {'source_ref': row['id'], 'representation': 'original', 'offset': 0, 'limit': 20}}
    return replace(context, role=role, path=((role, 'fixture'),), assignment=assignment)


@pytest.mark.parametrize('role', ['literature_page', 'literature_ordered'])
def test_c7_page_descendants_wrong_page_unreceived_and_ancestor_scope(tmp_path, monkeypatch, role):
    store, row, context, binding = fixture(tmp_path)
    with store:
        child = source(store, b'descendant quote', parents=(row['id'],))
        other = source(store, b'other page')
        context = page_context(context, row, role)
        context = replace(context, received_record_refs=(row['id'], child['id'], other['id']))
        args = lookup(child, 'quote')['selection']['arguments']
        outcome = asyncio.run(binding.execute(context, 'source.locate', args, 'descendant'))
        assert outcome['status'] == 'completed', outcome
        denied = asyncio.run(binding.execute(context, 'source.locate',
            lookup(other, 'page')['selection']['arguments'], 'wrong-page'))
        assert denied['feedback']['code'] == 'literature_reading_outside_assigned_source'
        denied = asyncio.run(binding.execute(replace(context, received_record_refs=(row['id'],)),
            'source.locate', args, 'descendant'))
        assert denied['feedback']['code'] == 'source_location_source_not_received'
        original = store.reference_subset
        monkeypatch.setattr(store, 'reference_subset', lambda refs, scope:
            [] if row['id'] in refs else original(refs, scope))
        denied = asyncio.run(binding.execute(context, 'source.locate', args, 'descendant'))
        assert denied['status'] == 'invalid'
        assert denied['feedback']['code'] in ('literature_reference_unavailable', 'source_location_outside_scope')


def test_real_catalog_initial_task_delta_restoration_and_helper_fingerprint(tmp_path, monkeypatch):
    from method_loop.durable import DurableExecutionError
    from gene_annotation_episode.decision_context import state_frame
    from gene_annotation_episode.episode_composition import compose_episode_bindings
    from gene_annotation_episode.episode_journal import Journal
    from gene_annotation_episode.literature_experimental_prompt import EXPERIMENTAL_TASK
    from test_literature_experimental_prompt_delivery import LiteratureWire, snapshot, complete
    store, row, context, binding = fixture(tmp_path/'state')
    with store:
        catalog = binding.catalog(context)
        assert 'source.locate' in {entry['name'] for entry in catalog}
        for role in ROLES:
            assert 'source.locate' in {entry['name'] for entry in binding.catalog(
                replace(context, role=role, path=((role, 'fixture'),)))}
        first = snapshot()
        first['tools'] = catalog
        first['literature_assignment'] = plain(context.assignment)
        first['requested_form'] = FORM
        first['goal']['objective'] = 'Extract the supplied synthetic reference rate with exact quote locations'
        args = lookup(row, '1.00 µM/min')['selection']['arguments']
        outcome = asyncio.run(binding.execute(context, 'source.locate', args, 'lookup'))
        second = deepcopy(first)
        second['last_local_outcome'] = outcome
        wires = [LiteratureWire(tmp_path/'initial'), LiteratureWire(tmp_path/'restored')]
        async def exercise():
            await complete(wires[0], state_frame(first))
            await complete(wires[0], state_frame(second, first))
            await complete(wires[1], state_frame(second))
        asyncio.run(exercise())
        tasks = []
        for wire in wires:
            for turn in wire.turns_sent():
                task, steering = turn['input'][0]['text'].split('\n\nSTEERING\n', 1)
                assert EXPERIMENTAL_TASK in task
                assert 'source.locate' in task and 'context_bytes' in task
                assert 'exact supplied literal quote' in task
                assert 'implementation_sha256' not in task
                tasks.append(task)
        assert all(task == tasks[0] for task in tasks)
        shown = wires[1].turns_sent()[0]['input'][0]['text'].split('\n\nSTEERING\n', 1)[1]
        assert 'matches[0].witness.start' in shown and '1.00 µM/min' in shown
        descriptor = binding.as_record()
        restored, = compose_episode_bindings(binding.services, store=store,
            journal=Journal(store, context.run_id), execution_backend=None, descriptors=[descriptor],
            job_episodes=None, resource_estimator=None, role_credit_bindings={}).bindings
        assert 'source.locate' in {entry['name'] for entry in restored.catalog(context)}
        original = Path.read_bytes
        monkeypatch.setattr(Path, 'read_bytes', lambda path: original(path) + b'\n# changed helper'
            if path.name == 'source_locations.py' else original(path))
        assert binding.as_record()['implementation_sha256'] != descriptor['implementation_sha256']
        with pytest.raises(DurableExecutionError, match='identity_conflict'):
            compose_episode_bindings(binding.services, store=store, journal=Journal(store, context.run_id),
                execution_backend=None, descriptors=[descriptor], job_episodes=None,
                resource_estimator=None, role_credit_bindings={})
