"""Explicit scientific-mother subprocess host for engineering checks only.

The ordinary Workflow and shared Episode loop execute the child. The provider,
source-count credit, stop controller and durable gate are declared fixtures;
this module starts no configured model or native scientific investigation.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
import hashlib
import json
import os
from pathlib import Path

from method_loop import EpisodeCompletion
from method_loop.communication import ReportContract
from method_loop.durable import (DurableExecutionError, canonical, content_digest,
                                 validate_commission)
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.runtime import (ReleasingContext, TypedReportContract,
                                             assemble_workflow)
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_records import scientific_digest, selector_selection
from gene_annotation_episode.state import Store
import detached_workflow_fixture as base


VERSION = 'scientific_process_worker_fixture_v1'
FACTORY_MODULE = 'scientific_process_worker_fixture'


class ScientificFixtureTools(base.FixtureTools):
    """Current scientific catalog for the fixture's actual local Store operations."""
    def catalog(self, scope=None):
        information = {
            'fixture.publish': {
                'description': 'Publish a literal synthetic engineering source in the local Store.',
                'instructions': 'Accept the selected fixture label and retain it with the operation key '
                    'in a local JSON artifact and source record. Return that source reference; '
                    'replay the same operation key without publishing another source. '
                    'This fixture performs no biological analysis.'},
            'fixture.read': {
                'description': 'Read the selected existing fixture records from the local Store.',
                'instructions': 'Resolve the supplied record references in the local Store and return '
                    'their exact records. Preserve the references and return no changed records. '
                    'This read creates no scientific measurement or new source.'}}
        return [{**entry, 'resources': 'local', **information[entry['name']]}
            for entry in super().catalog(scope)]


def child_credit(store, scope, *, assignment, episode_id, run_id,
                 known_assessment_refs=None):
    """Count actual received fixture sources, including frozen inherited receipts."""
    references = EpisodeReceipts(store, run_id).known(episode_id, record_type='source')
    return float(sum(store.get(ref).get('provider') == 'fixture.detached_workflow'
                     for ref in references))


child_credit.requires_episode_receipts = True


def implementation_sha256():
    digest = hashlib.sha256()
    for path in (Path(__file__), Path(base.__file__)):
        digest.update(path.name.encode() + b'\0')
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def make_binding(workspace, directory, descriptors):
    workspace, directory = Path(workspace).resolve(), Path(directory).resolve()
    library = ScientificProcessLibrary(directory / 'scientific-process-library')
    configuration = {'version': VERSION, 'workspace': str(workspace),
        'run_directory': str(directory), 'child_completed_actions': 3,
        'helper_completed_actions': 1,
        'credit_unit': 'one_distinct_received_fixture_source',
        'library': library.as_record(), 'episode_bindings': descriptors}
    path = directory / 'scientific-worker-fixture.json'
    path.write_text(canonical(configuration) + '\n')
    return {'factory_module': FACTORY_MODULE, 'factory_name': 'open_commission',
        'arguments': {'version': VERSION, 'configuration_file': str(path)},
        'implementation_sha256': implementation_sha256(),
        'settings_sha256': content_digest(configuration)}


class ChildProvider:
    def __init__(self, spec, directory, library):
        self.spec, self.directory, self.library = spec, directory, library
        self.calls, self.released = 0, []

    async def complete(self, episode_id, role, instructions, context, output_schema):
        child = self.spec['child']
        assert episode_id == child['episode_id'] and role == 'REASONING'
        assert context['goal'] == child['request']['goal']
        assert context['scope'] == child['scope']
        assert context['requested_form'] == child['request']['report_contract']['measurements']['schema']
        frame = context['scientific_process']
        assignment = child['request']['message']['episode_assignment']
        filled_selection = child['request']['message']['scientific_process']['selection']
        selected = selector_selection(filled_selection)
        assert frame['assignment'] == {**assignment, 'selection': selected}
        assert frame['selection'] == selected
        assert frame['child_tool_info'] == filled_selection['child_tool_info']
        assert frame['thought_pattern']['id'] == 'P01' and [entry['name'] for entry in frame['child_tool_info']] == ['fixture.publish']
        assert 'revision' not in frame and 'revision_decision_index' not in frame
        ready, release = base.gate_paths(self.directory, self.spec['handle'])
        if self.calls == 0:
            assert frame['selection'] == selected
            assert frame['thought_pattern']['id'] == 'P01' and [entry['name'] for entry in frame['child_tool_info']] == ['fixture.publish']
            assert 'fixture.publish' in [entry['name'] for entry in context['tools']]
            assert 'fixture.read' not in [entry['name'] for entry in context['tools']]
            ready.write_text(canonical({'pid': os.getpid(), 'handle': self.spec['handle']}) + '\n')
            await base.until(release.exists, timeout=45)
        with (self.directory / 'scientific-worker-calls.jsonl').open('a') as stream:
            stream.write(canonical({'pid': os.getpid(), 'episode_id': episode_id,
                'handle': self.spec['handle'], 'context': context, 'schema': output_schema}) + '\n')
        self.calls += 1
        if self.calls == 1:
            assert context['last_local_outcome'] is None
            return base.tool('child_one', report={'status': 'unresolved'})
        if self.calls == 2:
            assert context['last_local_outcome']['result']['label'] == 'child_one'
            assert context['current_credit'] == 1
            return {'selection': {'kind': 'tool', 'tool': 'process.revise', 'arguments': {
                'thought_pattern': self.library.reference('P77'),
                'child_tool_info': []}},
                'report_update': {'status': 'qualified'}}
        assert self.calls == 3
        preparation = context['last_local_outcome']
        proposal = preparation['result']
        assert proposal['version'] == 'scientific_process_child_selection_v1'
        assert proposal['parent_selection_sha256'] == scientific_digest(filled_selection)
        assert proposal['selection'] == {**filled_selection,
            'thought_pattern': self.library.reference('P77'), 'child_tool_info': []}
        assert preparation['revision_origin'] == {
            'version': 'scientific_process_revision_origin_v1',
            'parent_invocation_ref': child['request']['message']['scientific_invocation_ref'],
            'preparation_operation_ref': preparation['operation_ref']}
        assert preparation['record_refs'] == preparation['changed_record_refs'] == []
        assert context['current_credit'] == 1
        assert 'fixture.publish' in [entry['name'] for entry in context['tools']]
        return {'selection': {'kind': 'tool', 'tool': 'process.entry',
            'arguments': {'option_id': 'P77'}}, 'report_update': {'status': 'qualified'}}

    async def release(self, episode_id):
        self.released.append(episode_id)


class SourceHelperProvider:
    """One selected source operation; an explicit fixture, not a runtime itinerary."""
    def __init__(self, spec, directory):
        self.spec, self.directory = spec, directory
        self.calls, self.released = 0, []

    async def complete(self, episode_id, role, instructions, context, output_schema):
        child = self.spec['child']
        assignment = child['request']['message']['episode_assignment']
        operation = assignment['context']['fixture_operation']
        assert self.calls == 0 and role == 'REASONING'
        assert episode_id == child['episode_id']
        assert context['goal'] == child['request']['goal'] and context['scope'] == child['scope']
        assert context['requested_form'] == child['request']['report_contract']['measurements']['schema']
        filled_selection = child['request']['message']['scientific_process']['selection']
        selected = selector_selection(filled_selection)
        frame = context['scientific_process']
        assert frame['assignment'] == {**assignment, 'selection': selected}
        assert frame['selection'] == selected
        assert frame['child_tool_info'] == filled_selection['child_tool_info']
        tool_name = {'publish_parent_source': 'fixture.publish',
                     'read_returned_source': 'fixture.read'}[operation]
        assert [entry['name'] for entry in frame['child_tool_info']] == [tool_name]
        assert tool_name in [entry['name'] for entry in context['tools']]
        assert context['last_local_outcome'] is None
        assert context['current_credit'] == (0 if operation == 'publish_parent_source' else 2)
        ready, release = base.gate_paths(self.directory, self.spec['handle'])
        ready.write_text(canonical({'pid': os.getpid(), 'handle': self.spec['handle']}) + '\n')
        await base.until(release.exists, timeout=45)
        with (self.directory / ('scientific-helper-calls-' + self.spec['handle'] + '.jsonl')).open('a') as stream:
            stream.write(canonical({'pid': os.getpid(), 'episode_id': episode_id,
                'handle': self.spec['handle'], 'context': context, 'schema': output_schema}) + '\n')
        self.calls += 1
        if operation == 'publish_parent_source':
            return base.tool('parent_one')
        assert len(assignment['evidence_refs']) == 1
        return {'selection': {'kind': 'tool', 'tool': 'fixture.read',
            'arguments': {'refs': assignment['evidence_refs']}}, 'report_update': {}}

    async def release(self, episode_id):
        self.released.append(episode_id)


@asynccontextmanager
async def open_commission(spec):
    """Restore exactly the frozen filled request, using no research directory."""
    spec = validate_commission(spec)
    binding, args = spec['runtime_binding'], spec['runtime_binding']['arguments']
    if (binding['factory_module'] != FACTORY_MODULE or binding['factory_name'] != 'open_commission'
            or set(args) != {'version', 'configuration_file'} or args['version'] != VERSION
            or binding['implementation_sha256'] != implementation_sha256()):
        raise DurableExecutionError('identity_conflict', affected_refs=[spec['handle']])
    configuration = json.loads(Path(args['configuration_file']).read_text())
    if (set(configuration) != {'version', 'workspace', 'run_directory', 'child_completed_actions',
            'helper_completed_actions', 'credit_unit', 'library', 'episode_bindings'}
            or configuration['version'] != VERSION
            or configuration['child_completed_actions'] != 3
            or configuration['helper_completed_actions'] != 1
            or configuration['credit_unit'] != 'one_distinct_received_fixture_source'
            or binding['settings_sha256'] != content_digest(configuration)):
        raise DurableExecutionError('identity_conflict', affected_refs=[spec['handle']])
    directory = Path(configuration['run_directory']).resolve()
    library = ScientificProcessLibrary(directory / 'scientific-process-library')
    assert library.as_record() == configuration['library']
    with Store(configuration['workspace']) as store:
        from gene_annotation_episode.independent_execution import _check_assignment
        parent_goal, scope = _check_assignment(store, spec)
        settings = json.loads(store.db.execute('SELECT settings FROM runtime_runs WHERE run_id=?',
            (spec['run_id'],)).fetchone()[0])
        assert settings['directory'] == str(directory)
        assert settings['episode_bindings'] == configuration['episode_bindings']
        operation = spec['child']['request']['message']['episode_assignment']['context'].get(
            'fixture_operation')
        assert operation in {None, 'publish_parent_source', 'read_returned_source'}
        provider = (ChildProvider(spec, directory, library) if operation is None
                    else SourceHelperProvider(spec, directory))
        controllers = base.ControllerFactory(configuration[
            'child_completed_actions' if operation is None else 'helper_completed_actions'])
        workflow = assemble_workflow(store, ScientificFixtureTools(store), provider, directory,
            spec['run_id'], settings, controller_factory=controllers,
            project_credit=base.parent_credit, project_child_credit=child_credit,
            episode_binding_descriptors=settings['episode_bindings'], execution_binding=binding,
            episode_record_receipts=True, initial_known_record_refs=[])
        workflow.execution_handle = spec['handle']
        child, message = spec['child'], spec['child']['request']['message']
        original = ReportContract.from_record(child['request']['report_contract'])
        schema = original.as_record()['measurements']['schema']
        contract = TypedReportContract(original.decision, schema,
            workflow.resolver(scope, grain=child['role']),
            lambda form: workflow.validate_report(form, scope, grain=child['role'], schema=schema))
        episode = workflow.build(child['role'], child['key'], child['request']['goal']['objective'],
            scope, parent=parent_goal, parent_path=tuple(tuple(part) for part in spec['parent']['path']),
            contract=contract, initial=message['initial_report'],
            episode_assignment=message['episode_assignment'], scientific_process=message['scientific_process'])
        assert episode.request.as_record() == child['request']
        reconstruction = ('scientific-worker-reconstruction.json' if operation is None else
            'scientific-helper-reconstruction-' + spec['handle'] + '.json')
        (directory / reconstruction).write_text(canonical({
            'request': episode.request.as_record(), 'library': library.as_record(),
            'descriptor': workflow.scientific_process_binding.as_record(),
            'pid': os.getpid()}) + '\n')
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
            (directory / ('scientific-retired-' + spec['handle'] + '.json')).write_text(canonical({
                'episode_id': child['episode_id'], 'released': provider.released,
                'active_controllers': len(context.runtime._controllers),
                'active_episodes': len(context._active_episodes)}) + '\n')
