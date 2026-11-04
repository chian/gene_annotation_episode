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
from gene_annotation_episode.runtime import (ReleasingContext, TypedReportContract,
                                             assemble_workflow)
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_records import scientific_digest
from gene_annotation_episode.state import Store
import detached_workflow_fixture as base


VERSION = 'scientific_process_worker_fixture_v1'
FACTORY_MODULE = 'scientific_process_worker_fixture'


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
        assert frame['assignment'] == child['request']['message']['episode_assignment']
        assert frame['selection'] == child['request']['message']['scientific_process']['selection']
        assert frame['thought']['id'] == 'P01' and [entry['name'] for entry in frame['tools']] == ['fixture.publish']
        assert 'revision' not in frame and 'revision_decision_index' not in frame
        ready, release = base.gate_paths(self.directory, self.spec['handle'])
        if self.calls == 0:
            assert frame['selection'] == child['request']['message']['scientific_process']['selection']
            assert frame['thought']['id'] == 'P01' and [entry['name'] for entry in frame['tools']] == ['fixture.publish']
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
                'thought_ref': self.library.reference('P77'),
                "tools": []}},
                'report_update': {'status': 'qualified'}}
        assert self.calls == 3
        preparation = context['last_local_outcome']
        proposal = preparation['result']
        assert proposal['version'] == 'scientific_process_child_selection_v1'
        assert proposal['parent_selection_sha256'] == scientific_digest(frame['selection'])
        assert proposal['selection'] == {**frame['selection'],
            'thought_ref': self.library.reference('P77'), "tools": []}
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
            'credit_unit', 'library', 'episode_bindings'} or configuration['version'] != VERSION
            or configuration['child_completed_actions'] != 3
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
        provider = ChildProvider(spec, directory, library)
        controllers = base.ControllerFactory(configuration['child_completed_actions'])
        workflow = assemble_workflow(store, base.FixtureTools(store), provider, directory,
            spec['run_id'], settings, controller_factory=controllers,
            project_credit=base.parent_credit, project_child_credit=base.child_credit,
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
        (directory / 'scientific-worker-reconstruction.json').write_text(canonical({
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
