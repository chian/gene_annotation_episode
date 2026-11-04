"""Launch manuals through the actual shared decision and commission paths.

Providers, resource capabilities and controller units are explicit engineering
fixtures. No configured model, remote authentication, API or PBS job runs here.
"""
import asyncio
from copy import deepcopy
import json

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.communication import plain
from gene_annotation_episode.launch_instructions import LaunchInstructions
from gene_annotation_episode.practical_execution_records import (
    ASSIGNMENT_SCHEMA, validate_assignment)
from gene_annotation_episode.resource_episodes import ResourceEpisodes
from gene_annotation_episode.resource_records import LAUNCH_SCHEMA
from gene_annotation_episode.runtime import Workflow
from test_runtime import FixtureController, obj, setup


def library_source(tmp_path, text='Keep exact caller inputs.\nSelect actual operations.\n'):
    source = tmp_path / 'launch-source'
    source.mkdir()
    (source / 'work.md').write_text(text)
    (source / 'results.md').write_text('Receive the original result identity.\n')
    (source / 'index.json').write_text(json.dumps({'version': 'tool_knowledge_v1',
        'entries': [{'entry_id': 'fixture-launch', 'title': 'Fixture launch',
            'summary': 'Instructions for runtime integration fixtures',
            'tags': ['launch'], 'tool_names': ['fixture.run'],
            'resource_kinds': ['local', 'api'], 'provenance': ['synthetic_test_fixture'],
            'sections': [{'section_id': 'work', 'title': 'Work', 'path': 'work.md'},
                {'section_id': 'results', 'title': 'Results', 'path': 'results.md'}]}]}))
    return source


def action(name, arguments):
    return {'selection': {'kind': 'tool', 'tool': name, 'arguments': arguments},
            'report_update': {}}


class Provider:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.contexts = []

    async def complete(self, episode_id, role, instructions, context, schema):
        assert role == 'REASONING'
        assert 'launch.instructions.select' in instructions
        self.contexts.append(deepcopy(context))
        response = next(self.responses)
        if isinstance(response, BaseException):
            raise response
        return response(context) if callable(response) else deepcopy(response)


class FixtureResource:
    """No real execution binding; prepare calls witness the side-effect boundary."""
    resource_id = 'fixture-local'

    def __init__(self):
        self.prepared = []

    def capability(self):
        return {'resource_id': self.resource_id, 'kind': 'local', 'availability': 'available',
            'observed_at': '2026-10-22T00:00:00+00:00', 'provenance_refs': [],
            'knowledge_entry_ids': [], 'tool_names': ['fixture.run']}

    def as_record(self):
        return {'version': 'synthetic_instruction_fixture', 'resource_id': self.resource_id}

    def prepare_assignment(self, context, role, value, scope, operation_key):
        self.prepared.append(deepcopy(value))
        return {**plain(value), 'adapter_assignment': {'fixture_native_identity': operation_key}}

    def catalog(self, context):
        return [{'name': 'fixture.run', 'input_schema': obj({})}]

    async def execute(self, context, name, arguments, operation_key):
        raise AssertionError('Instruction checks must not execute resource work')

    def fact_sources(self, role):
        return {}

    def facts(self, context, completion_snapshot):
        return {}

    def resolve(self, context, reference, namespace):
        return False

    def validate_report(self, context, form, original_schema):
        return None

    def credit_view(self, context, receiver_selection):
        return {'credit': 0}


class FixtureResources(ResourceEpisodes):
    def credit_view(self, context, receiver_selection):
        return {'credit': 0}  # Explicit fixture units, no operational policy change.


def launch_assignment(instructions=None):
    value = {'version': 'resource_launch_assignment_v1',
        'job_request': {'argv': ['fixture-program'], 'input': 'original-input'},
        'immutable_input_versions': [], 'constraints': {'allowed_kinds': ['local']},
        'resource_selection': None, 'software_knowledge_refs': [], 'resource_knowledge_refs': []}
    if instructions is not None:
        value['launch_instructions'] = instructions
    return value


def selected_assignment(value):
    return {**deepcopy(value), 'resource_selection': {
        'resource_id': 'fixture-local', 'kind': 'local', 'capability_binding_ref': 'fixture-registry',
        'allocation': {'cpu': 1, 'memory_bytes': None, 'scratch_bytes': None, 'wall_seconds': None}}}


def child_selection(assignment):
    return {'kind': 'episode_child', 'role': 'launch_local',
        'goal': 'Investigate the original selected execution',
        'scope': {'subject_refs': ['subject_A']},
        'purpose': 'Return original recorded references without manual prose',
        'assignment': assignment, 'schema_json': json.dumps(obj({'received': {
            'type': 'array', 'items': {'type': 'string', 'format': 'reference'},
            'x-source': 'changed_record_refs'}})), 'initial_report_json': '{}'}


def workflow(tmp_path, store, tools, provider, *, adapter=None, count=6):
    adapter = adapter or FixtureResource()
    value = Workflow(store, tools, provider, tmp_path / 'run', 'launch-instruction-fixture',
        lambda path, initial: FixtureController(str(path), initial, count if len(path) == 1 else 2),
        lambda *_: 0, root_role='launch',
        episode_binding_factories=(lambda services: FixtureResources(services,
            resource_adapters=(adapter,)),))
    return value, adapter


def test_retrieval_selection_and_child_first_context_use_exact_saved_instructions(tmp_path):
    store, tools = setup(tmp_path)
    tools.launch_instruction_library_directory = source = library_source(tmp_path)
    parent_assignment = launch_assignment()
    selected = {}

    def commission(context):
        selected.update(context['last_local_outcome']['result'])
        assert context['current_credit'] == 0
        child = selected_assignment(parent_assignment)
        child['launch_instructions'] = deepcopy(selected)
        return {'selection': child_selection(child), 'report_update': {}}

    def child_first(context):
        supplied = context['selected_launch_instructions']
        assert supplied['selection'] == selected
        assert supplied['sections'][0]['text'] == (source / 'work.md').read_text()
        assert supplied['sections'][0]['section_sha256'] == selected['sections'][0]['sha256']
        assert context['resource_capabilities'][0]['resource_id'] == 'fixture-local'
        assert context['assignment']['job_request'] == parent_assignment['job_request']
        assert context['current_credit'] == 0
        return action('launch.instructions.read', {'entry_id': 'fixture-launch',
            'section_id': 'results', 'offset': 0, 'limit': 1})

    provider = Provider([
        action('launch.instructions.search', {'query': '', 'offset': 0, 'limit': 3}),
        action('launch.instructions.entry', {'entry_id': 'fixture-launch'}),
        action('launch.instructions.read', {'entry_id': 'fixture-launch',
            'section_id': 'work', 'offset': 0, 'limit': 1}),
        action('launch.instructions.select', {'sections': [
            {'entry_id': 'fixture-launch', 'section_id': 'work'}]}),
        commission, child_first,
        action('launch.instructions.entry', {'entry_id': 'fixture-launch'}),
        action('launch.instructions.entry', {'entry_id': 'fixture-launch'})])
    value, adapter = workflow(tmp_path, store, tools, provider)
    root = value.build('launch', 'root', 'Investigate the selected launch',
        {'subject_refs': ['subject_A']}, episode_assignment=parent_assignment)
    record = asyncio.run(root.run_async(value.context))
    assert record.units_consumed == 6
    assert len(adapter.prepared) == 1
    assert adapter.prepared[0]['launch_instructions'] == selected
    assert tools.executions == 0
    assert len(provider.contexts) == 8
    assert all(context['launch_instruction_library']['entry_count'] == 1
               for context in provider.contexts)
    assert all('selected_launch_instructions' not in context
               for context in provider.contexts[:5])
    observations = [json.loads(row[0]) for row in store.db.execute(
        'SELECT observation FROM runtime_observations')]
    assert len(observations) == 8
    assert all(item['step']['delta'] == 0 for item in observations)
    assert store.references({'subject_refs': ['subject_A']})['observation'] == []
    child_requests = [json.loads(row[0]) for row in store.db.execute(
        "SELECT request FROM runtime_model_calls WHERE json_type(request,"
        "'$.context.selected_launch_instructions')='object'")]
    assert len(child_requests) == 2
    assert child_requests[0]['context']['selected_launch_instructions']['selection'] == selected


@pytest.mark.parametrize('damage,expected', [
    ('library', 'launch_instruction_selection_library_mismatch'),
    ('digest', 'launch_instruction_selection_digest_mismatch'),
    ('section', 'launch_instruction_section_unknown'),
])
def test_bad_child_pins_fail_before_native_assignment_preparation(tmp_path, damage, expected):
    store, tools = setup(tmp_path)
    tools.launch_instruction_library_directory = library_source(tmp_path)
    value, adapter = workflow(tmp_path, store, tools, Provider([]))
    root = value.build('launch', 'root', 'Investigate the selected launch',
        {'subject_refs': ['subject_A']}, episode_assignment=launch_assignment())
    pin = value.launch_instructions.select([{'entry_id': 'fixture-launch', 'section_id': 'work'}])
    if damage == 'library':
        pin['library_id'] = 'launch_instructions_' + '0' * 64
    elif damage == 'digest':
        pin['sections'][0]['sha256'] = '0' * 64
    else:
        pin['sections'][0]['section_id'] = 'unknown'
    assignment = selected_assignment(launch_assignment(pin))
    with pytest.raises(ValueError, match=expected):
        value.selected(root.source, child_selection(assignment), 0)
    assert adapter.prepared == []
    assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0


@pytest.mark.parametrize('change', ['drop', 'replace', 'addition', 'changed_job'])
def test_resource_child_retains_parent_pins_and_original_job(tmp_path, change):
    store, tools = setup(tmp_path)
    tools.launch_instruction_library_directory = library_source(tmp_path)
    value, adapter = workflow(tmp_path, store, tools, Provider([]))
    library = value.launch_instructions
    original = library.select([{'entry_id': 'fixture-launch', 'section_id': 'work'}])
    parent_assignment = launch_assignment(original)
    root = value.build('launch', 'root', 'Investigate the selected launch',
        {'subject_refs': ['subject_A']}, episode_assignment=parent_assignment)
    selected = selected_assignment(parent_assignment)
    if change == 'drop':
        del selected['launch_instructions']
    elif change == 'replace':
        selected['launch_instructions'] = library.select([
            {'entry_id': 'fixture-launch', 'section_id': 'results'}])
    elif change == 'addition':
        selected['launch_instructions'] = library.select([
            {'entry_id': 'fixture-launch', 'section_id': 'results'},
            {'entry_id': 'fixture-launch', 'section_id': 'work'}])
    else:
        selected['job_request']['input'] = 'substituted-input'
    if change == 'addition':
        child = value.selected(root.source, child_selection(selected), 0)
        assert child is not None
        assert len(adapter.prepared) == 1
        assert adapter.prepared[0]['launch_instructions'] == selected['launch_instructions']
    else:
        with pytest.raises(ValueError, match=('resource_assignment_conflict' if change == 'changed_job'
                else 'launch_instruction_inheritance_conflict')):
            value.selected(root.source, child_selection(selected), 0)
        assert adapter.prepared == []


def test_selected_saved_and_interrupted_contexts_survive_source_revision(tmp_path):
    store, tools = setup(tmp_path)
    tools.launch_instruction_library_directory = source = library_source(tmp_path)
    first = Provider([action('launch.instructions.read', {'entry_id': 'fixture-launch',
        'section_id': 'work', 'offset': 0, 'limit': 1}), KeyboardInterrupt()])
    value, _ = workflow(tmp_path, store, tools, first, count=2)
    selection = value.launch_instructions.select([{'entry_id': 'fixture-launch', 'section_id': 'work'}])
    assignment = launch_assignment(selection)
    root = value.build('launch', 'root', 'Investigate the selected launch',
        {'subject_refs': ['subject_A']}, episode_assignment=assignment)
    with pytest.raises(KeyboardInterrupt):
        asyncio.run(root.run_async(value.context))
    original_calls = list(store.db.execute('SELECT call_index,request FROM runtime_model_calls ORDER BY call_index'))
    saved_context = json.loads(original_calls[1]['request'])['context']
    observation = store.db.execute('SELECT observation FROM runtime_observations').fetchone()[0]
    (source / 'work.md').write_text('A later revision must not alter this run.\n')

    def resume(context):
        assert context == saved_context
        assert context['selected_launch_instructions']['sections'][0]['text'] == 'Keep exact caller inputs.\nSelect actual operations.\n'
        return action('launch.instructions.entry', {'entry_id': 'fixture-launch'})

    provider = Provider([resume])
    resumed, _ = workflow(tmp_path, store, tools, provider, count=2)
    root = resumed.build('launch', 'root', 'Investigate the selected launch',
        {'subject_refs': ['subject_A']}, episode_assignment=assignment)
    # Reopening validates the frozen root assignment; replaying actual saved
    # calls must then use their original delivered bytes, without a new read.
    resumed.launch_instructions.materialize = lambda *_: (_ for _ in ()).throw(
        AssertionError('Saved decision rematerialized its selected manuals'))
    record = asyncio.run(root.run_async(resumed.context))
    assert record.units_consumed == 2
    assert len(provider.contexts) == 1
    assert list(store.db.execute('SELECT request FROM runtime_model_calls ORDER BY call_index'))[0][0] == original_calls[0]['request']
    assert list(store.db.execute('SELECT request FROM runtime_model_calls ORDER BY call_index'))[1][0] == original_calls[1]['request']
    assert store.db.execute('SELECT observation FROM runtime_observations ORDER BY unit_index LIMIT 1').fetchone()[0] == observation
    assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 2
    assert LaunchInstructions.freeze(tmp_path / 'future-run', source=source).context()['library_id'] != selection['library_id']


def test_practical_assignment_pins_are_optional_and_precede_initial_native_probe(tmp_path, monkeypatch):
    from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
    from gene_annotation_episode.practical_resource_episodes import PracticalResourceEpisodes
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry
    from test_practical_runtime import make_assignment

    source = library_source(tmp_path)
    spec = make_assignment(tmp_path / 'project')
    assert validate_assignment(spec.assignment) == spec.assignment
    assert Draft202012Validator(ASSIGNMENT_SCHEMA).is_valid(spec.assignment)
    with Store(tmp_path / 'state') as store:
        subject, = store.create_problem(raw_sequence='MARGKK', molecule='protein')['subject_refs']
        tools = ToolRegistry(store)
        tools.launch_instruction_library_directory = source
        directory = tmp_path / 'run'
        resources = {'local': {'kind': 'local', 'workspace': str(spec.workspace),
            'policy': {'memory_bytes': 128 * 1024**2, 'scratch_bytes': 8 * 1024**2,
                       'wall_seconds': None}}}
        value = Workflow(store, tools, Provider([]), directory, 'practical-library-fixture',
            lambda path, initial: FixtureController(str(path), initial, 1), lambda *_: 0,
            root_role='launch_local', episode_binding_factories=(
                lambda services: PracticalResourceEpisodes(services, directory=directory,
                    resources=resources),))
        selection = value.launch_instructions.select([
            {'entry_id': 'fixture-launch', 'section_id': 'work'}])
        valid = {**spec.assignment, 'launch_instructions': selection}
        assert validate_assignment(valid) == valid
        assert Draft202012Validator(ASSIGNMENT_SCHEMA).is_valid(valid)
        probes = []
        original = LocalPracticalOperations.initial_outcome
        def initial(operations, assignment):
            probes.append(deepcopy(assignment))
            return original(operations, assignment)
        monkeypatch.setattr(LocalPracticalOperations, 'initial_outcome', initial)
        invalid = deepcopy(valid)
        invalid['launch_instructions']['sections'][0]['sha256'] = '0' * 64
        with pytest.raises(ValueError, match='launch_instruction_selection_digest_mismatch'):
            value.build('launch_local', 'root', 'Run the original assignment',
                {'subject_refs': [subject]}, episode_assignment=invalid)
        assert probes == []
        root = value.build('launch_local', 'root', 'Run the original assignment',
            {'subject_refs': [subject]}, episode_assignment=valid)
        assert probes == [valid]
        value.provider = Provider([action('launch.instructions.entry', {'entry_id': 'fixture-launch'})])
        asyncio.run(root.source.call({}, value.action_schema(root.source)))
        supplied, = value.provider.contexts
        assert supplied['selected_launch_instructions']['selection'] == selection
        assert supplied['selected_launch_instructions']['sections'][0]['text'] == (source / 'work.md').read_text()
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0


@pytest.mark.parametrize('resource_kind', ['api', 'local', 'hpc'])
def test_existing_resource_assignments_keep_exact_job_and_optional_selection(tmp_path, resource_kind):
    source = library_source(tmp_path)
    library = LaunchInstructions.freeze(tmp_path / 'frozen', source=source)
    legacy = launch_assignment()
    selected = selected_assignment(legacy)
    selected['resource_selection']['kind'] = resource_kind
    assert Draft202012Validator(LAUNCH_SCHEMA).is_valid(selected)
    assert 'launch_instructions' not in selected
    for instructions in (None, library.select([
            {'entry_id': 'fixture-launch', 'section_id': 'work'}])):
        with_manuals = {**selected, 'launch_instructions': instructions}
        assert Draft202012Validator(LAUNCH_SCHEMA).is_valid(with_manuals)
        assert {key: item for key, item in with_manuals.items()
                if key != 'launch_instructions'} == selected
