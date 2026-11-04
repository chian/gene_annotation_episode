"""Explicit subprocess fixtures for the detached Workflow consumer.

The provider, gate, source-count unit and stopping controller are engineering
fixtures. Only the ordinary application Episode loop runs in the worker; no
configured model or scientific investigation is started by this module.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
import hashlib
import inspect
import json
import os
from pathlib import Path
from types import SimpleNamespace

from method_loop import EpisodeCompletion, EpisodeGoal
from method_loop.communication import ReportContract
from method_loop.durable import (DurableExecutionError, canonical, content_digest,
                                 validate_commission)
from gene_annotation_episode.runtime import (ReleasingContext, TypedReportContract,
                                             assemble_workflow)
from gene_annotation_episode.state import Store


VERSION = 'detached_workflow_fixture_v1'
FACTORY_MODULE = 'detached_workflow_fixture'


def obj(properties):
    return {'type': 'object', 'properties': properties,
            'required': list(properties), 'additionalProperties': False}


def implementation_sha256():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def make_binding(workspace, directory):
    """Pin this caller's fixture operands without needing future run settings."""
    workspace, directory = Path(workspace).resolve(), Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    configuration = {'version': VERSION, 'workspace': str(workspace),
        'run_directory': str(directory), 'child_completed_actions': 2,
        'credit_unit': 'one_distinct_received_fixture_source'}
    path = directory / 'detached-fixture.json'
    path.write_text(canonical(configuration) + '\n')
    return {'factory_module': FACTORY_MODULE, 'factory_name': 'open_commission',
        'arguments': {'version': VERSION, 'configuration_file': str(path)},
        'implementation_sha256': implementation_sha256(),
        'settings_sha256': content_digest(configuration)}


def gate_paths(directory, handle):
    gates = Path(directory) / 'fixture-gates'
    gates.mkdir(exist_ok=True)
    return gates / (handle + '.ready.json'), gates / (handle + '.release')


async def until(predicate, *, timeout=20):
    """Bounded test synchronization, never an episode polling policy."""
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        value = predicate()
        if value:
            return value
        if asyncio.get_running_loop().time() >= deadline:
            raise AssertionError('fixture synchronization did not complete')
        await asyncio.sleep(.01)


class FixtureTools:
    """Publish real source records with a test-only, idempotent operation port."""
    def __init__(self, store):
        self.store = store
        with store.transaction():
            store.db.execute('CREATE TABLE IF NOT EXISTS detached_fixture_operations '
                '(operation_key TEXT PRIMARY KEY, selection TEXT NOT NULL, result TEXT NOT NULL)')

    def resource_binding(self):
        return {'fixture_only': True, 'native_processes': False}

    def catalog(self, scope=None):
        return [{'name': 'fixture.publish', 'input_schema': obj({'label': {
                    'type': 'string', 'enum': ['parent_one', 'parent_followup', 'child_one']}})},
                {'name': 'fixture.read', 'input_schema': obj({'refs': {'type': 'array',
                    'items': {'type': 'string', 'format': 'reference'}}})}]

    def execute(self, name, arguments, *, scope, operation_key):
        selection = {'name': name, 'arguments': arguments, 'scope': scope}
        old = self.store.db.execute('SELECT selection,result FROM detached_fixture_operations '
            'WHERE operation_key=?', (operation_key,)).fetchone()
        if old is not None:
            assert json.loads(old['selection']) == selection
            return json.loads(old['result'])
        with self.store.transaction():
            if name == 'fixture.publish':
                artifact = self.store.artifact(canonical({'label': arguments['label'],
                    'operation_key': operation_key}), 'application/json')
                source = self.store.put('source', {'provider': 'fixture.detached_workflow',
                    'accession': arguments['label'], 'uri': None, 'artifact_ref': artifact,
                    'text_ref': artifact, 'request_ref': None, 'version': VERSION,
                    'retrieved_at': None, 'parent_source_refs': [],
                    'operand_refs': scope['subject_refs']}, origin='tool')['id']
                result = {'status': 'completed', 'record_refs': [source],
                    'changed_record_refs': [source], 'result': {'label': arguments['label']}}
            else:
                assert name == 'fixture.read'
                references = arguments['refs']
                result = {'status': 'completed', 'record_refs': references,
                    'changed_record_refs': [],
                    'result': {'records': [self.store.get(ref) for ref in references]}}
            self.store.db.execute('INSERT INTO detached_fixture_operations VALUES(?,?,?)',
                (operation_key, canonical(selection), canonical(result)))
        return result


def _received_credit(store, episode_id):
    # The unit is explicitly synthetic. Child work in the shared Store is not
    # counted until this owner has its own outcome or the requested typed form.
    references = set()
    for row in store.db.execute('SELECT result FROM runtime_actions WHERE episode_id=? '
            "AND json_extract(result,'$.status') IN ('completed','partial')", (episode_id,)):
        references.update(json.loads(row[0]).get('record_refs', []))
    for row in store.db.execute('SELECT form FROM runtime_report_attempts '
            'WHERE parent_episode_id=? AND form IS NOT NULL', (episode_id,)):
        references.update(json.loads(row[0]).get('sources', []))
    return float(sum(store.get(ref).get('provider') == 'fixture.detached_workflow'
                     for ref in references))


def parent_credit(store, scope):
    row = store.db.execute("SELECT episode_id FROM runtime_episodes WHERE "
        "json_extract(path,'$[0][0]')='annotation' AND json_array_length(path)=1").fetchone()
    return 0.0 if row is None else _received_credit(store, row[0])


def child_credit(store, scope, *, assignment, episode_id, run_id):
    return _received_credit(store, episode_id)


class FixtureController:
    """Local fixture stop seam; it claims no production yield formula."""
    def __init__(self, path, initial, completed_actions):
        self.epoch = content_digest(path)
        self.current, self.limit, self.deltas = initial, completed_actions, []

    def observe(self, label, value, *, is_root):
        credit = value.as_record()['credit']
        self.deltas.append(credit - self.current)
        self.current = credit
        return FixtureStep(len(self.deltas) >= self.limit, self.deltas[-1])

    def state(self):
        return FixtureState(self.current, self.deltas, len(self.deltas) >= self.limit)

    def transitioned(self, epoch):
        raise AssertionError('fixture requests no controller epoch transition')


class FixtureStep:
    requests_transition = False

    def __init__(self, stop, delta):
        self.stop, self.delta = stop, delta

    def as_record(self):
        return {'stop': self.stop, 'delta': self.delta, 'requests_transition': False}


class FixtureState:
    def __init__(self, credit, deltas, stop):
        self.credit, self.deltas, self.decision = credit, list(deltas), SimpleNamespace(stop=stop)

    def as_record(self):
        return {'credit': self.credit, 'deltas': self.deltas,
                'decision': {'stop': self.decision.stop}}


class ControllerFactory:
    def __init__(self, completed_actions):
        self.completed_actions, self.controllers = completed_actions, []

    def __call__(self, path, initial):
        controller = FixtureController(path, initial, self.completed_actions)
        self.controllers.append(controller)
        return controller


class ScriptedProvider:
    def __init__(self, script):
        self.script, self.contexts, self.released = iter(script), [], []

    async def complete(self, episode_id, role, instructions, context, output_schema):
        assert role == 'REASONING'
        self.contexts.append(deepcopy(context))
        response = next(self.script)
        if isinstance(response, BaseException):
            raise response
        result = response(context) if callable(response) else deepcopy(response)
        return await result if inspect.isawaitable(result) else result

    async def release(self, episode_id):
        self.released.append(episode_id)


class ChildProvider:
    def __init__(self, spec, directory):
        self.spec, self.directory, self.calls = spec, directory, 0
        self.released = []

    async def complete(self, episode_id, role, instructions, context, output_schema):
        assert episode_id == self.spec['child']['episode_id']
        assert context['goal'] == self.spec['child']['request']['goal']
        assert context['scope'] == self.spec['child']['scope']
        assert role == 'REASONING'
        ready, release = gate_paths(self.directory, self.spec['handle'])
        if not self.calls:
            ready.write_text(canonical({'pid': os.getpid(), 'handle': self.spec['handle']}) + '\n')
            await until(lambda: release.exists(), timeout=45)
        with (self.directory / 'fixture-child-calls.jsonl').open('a') as stream:
            stream.write(canonical({'pid': os.getpid(), 'episode_id': episode_id,
                'handle': self.spec['handle'], 'context': context}) + '\n')
        self.calls += 1
        if context['last_local_outcome'] is None:
            assert self.calls == 1
            return tool('child_one', report={'finding': 'unknown'})
        assert self.calls == 2
        assert context['last_local_outcome']['result']['label'] == 'child_one'
        return {'selection': {'kind': 'tool', 'tool': 'fixture.read', 'arguments': {
            'refs': context['last_local_outcome']['record_refs']}},
            'report_update': {'finding': 'qualified'}}

    async def release(self, episode_id):
        self.released.append(episode_id)


def tool(label, *, report=None):
    return {'selection': {'kind': 'tool', 'tool': 'fixture.publish',
            'arguments': {'label': label}}, 'report_update': report or {}}


def commission(subject):
    schema = obj({'finding': {'type': 'string', 'enum': ['unknown', 'qualified']},
        'sources': {'type': 'array', 'items': {'type': 'string', 'format': 'reference',
            'x-reference-namespace': 'source'}, 'x-source': 'changed_record_refs'},
        'subjects': {'type': 'array', 'items': {'type': 'string', 'format': 'reference',
            'x-reference-namespace': 'input'}, 'x-source': 'subject_refs'},
        'child_credit': {'type': 'number', 'x-source': 'credit'}})
    return {'selection': {'kind': 'child',
        'goal': 'Iteratively investigate the fixed detached fixture distinction',
        'scope': {'subject_refs': [subject]},
        'purpose': 'Return the constrained fixture distinction and actual changed source references',
        'schema_json': canonical(schema), 'initial_report_json': canonical({'finding': 'unknown'})},
        'report_update': {}}


@asynccontextmanager
async def open_commission(spec):
    """Reconstruct exactly the C1 child with independently owned live resources."""
    spec = validate_commission(spec)
    binding = spec['runtime_binding']
    args = binding['arguments']
    if (binding['factory_module'] != FACTORY_MODULE or binding['factory_name'] != 'open_commission'
            or set(args) != {'version', 'configuration_file'} or args['version'] != VERSION
            or binding['implementation_sha256'] != implementation_sha256()):
        raise DurableExecutionError('identity_conflict', affected_refs=[spec['handle']])
    configuration = json.loads(Path(args['configuration_file']).read_text())
    if (set(configuration) != {'version', 'workspace', 'run_directory',
            'child_completed_actions', 'credit_unit'} or configuration['version'] != VERSION
            or configuration['credit_unit'] != 'one_distinct_received_fixture_source'
            or binding['settings_sha256'] != content_digest(configuration)):
        raise DurableExecutionError('identity_conflict', affected_refs=[spec['handle']])
    directory = Path(configuration['run_directory']).resolve()
    with Store(configuration['workspace']) as store:
        # Use the production assignment/input check, including actual saved
        # parent/child identity, original request, normalized scope and hashes.
        from gene_annotation_episode.independent_execution import _check_assignment
        parent_goal, scope = _check_assignment(store, spec)
        assert parent_goal == EpisodeGoal.from_record(json.loads(store.db.execute(
            'SELECT request FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (spec['run_id'], spec['parent']['episode_id'])).fetchone()[0])['goal'])
        settings = json.loads(store.db.execute('SELECT settings FROM runtime_runs WHERE run_id=?',
            (spec['run_id'],)).fetchone()[0])
        assert settings['directory'] == str(directory)
        provider = ChildProvider(spec, directory)
        controllers = ControllerFactory(configuration['child_completed_actions'])
        workflow = assemble_workflow(store, FixtureTools(store), provider, directory,
            spec['run_id'], settings, controller_factory=controllers,
            project_credit=parent_credit, project_child_credit=child_credit,
            episode_binding_descriptors=settings['episode_bindings'], execution_binding=binding)
        workflow.execution_handle = spec['handle']
        child = spec['child']
        message = child['request']['message']
        original = ReportContract.from_record(child['request']['report_contract'])
        schema = original.as_record()['measurements']['schema']
        contract = TypedReportContract(original.decision, schema, workflow.resolver(scope, grain=child['role']),
            lambda form: workflow.validate_report(form, scope, grain=child['role'], schema=schema))
        episode = workflow.build(child['role'], child['key'], child['request']['goal']['objective'],
            scope, parent=parent_goal, parent_path=tuple(tuple(part) for part in spec['parent']['path']),
            contract=contract, initial=message['initial_report'],
            job_assignment=message.get('job_assignment'), episode_assignment=message.get('episode_assignment'))
        assert episode.request.as_record() == child['request']
        context = ReleasingContext.from_commission(tree=workflow.tree, run_id=spec['run_id'],
            parent_path=spec['parent']['path'], parent_goal_id=parent_goal.goal_id,
            child_goal_id=episode.goal.goal_id, grain=child['role'], key=child['key'])
        workflow.context = context

        def pack_result(record, result):
            saved = workflow.journal.row('runtime_forms', child['episode_id'])
            assert saved is not None
            facts = json.loads(saved['facts'])
            facts.pop('interpretations', None)
            return {'completion': EpisodeCompletion.from_record(record).as_record(),
                'episode_archive': (record.archived_record or workflow.archive.store(record)).descriptor(),
                'result_archive': workflow.archive.store(result).descriptor(),
                'form': result.as_record()['form'], 'facts_archive': workflow.archive.store(facts).descriptor(),
                'pending_handles': workflow.pending_handles(episode.source)}

        try:
            yield {'episode': episode, 'context': context, 'pack_result': pack_result}
        finally:
            await workflow.release(child['episode_id'])
            (directory / ('fixture-retired-' + spec['handle'] + '.json')).write_text(canonical({
                'episode_id': child['episode_id'], 'released': provider.released,
                'active_controllers': len(context.runtime._controllers),
                'active_episodes': len(context._active_episodes)}) + '\n')
