"""Specialist composition consumed by the actual application Episode loop.

Model decisions and credit units here are explicit fixtures. No configured-model
scientific investigation or independently executing application is claimed.
"""
import asyncio
import json

from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_monitoring import MonitorEpisodes
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_recursive_monitoring import assignment, durable_target
from test_runtime import FixtureController, ScriptedProvider
from method_loop.durable import DurableExecutionStore


def build_workflow(tmp_path, store, provider, *, counts=(2, 2)):
    directory = tmp_path / 'run'
    directory.mkdir(exist_ok=True)
    controllers, selections = [], []
    holder = {}

    def project(context, selection):
        selections.append(selection)
        progress = holder['workflow'].progress_provider
        known = {progress.observation_identity(ref) for ref in selection['known_progress_refs']}
        baseline = {progress.observation_identity(ref) for ref in selection['initial_progress_refs']}
        return {'credit': len(known - baseline)}

    def controller(path, initial):
        value = FixtureController(str(path), initial, counts[0] if len(path) == 1 else counts[1])
        controllers.append(value)
        return value

    workflow = Workflow(store, ToolRegistry(store), provider, directory, 'durable-fixture-run',
        controller, lambda store, scope: 0,
        episode_binding_descriptors=[MonitorEpisodes(None).as_record()],
        role_credit_bindings={'monitor': {
            'definition': {'kind': 'fixture_unique_observation', 'units': 'fixture_information'},
            'project': project}})
    holder['workflow'] = workflow
    return workflow, controllers, selections


def test_monitor_composition_returns_typed_progress_without_scientific_receipt_binding(tmp_path):
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='MKWAA', molecule='protein')
        backend = DurableExecutionStore(tmp_path / 'run' / 'episode-execution')
        target = durable_target(tmp_path, store, backend)
        scope = target['child']['scope']
        report_schema = obj({
            'progress': {'type': 'array', 'items': {'type': 'string', 'format': 'reference',
                'x-reference-namespace': 'episode_progress'}, 'x-source': 'monitoring_progress_refs'},
            'state': {'type': ['string', 'null'], 'enum': ['pending', 'executing', 'returned', 'admitted', None],
                'x-source': 'monitoring_execution_state'}})
        observe = {'selection': {'kind': 'tool', 'tool': 'progress.observe',
            'arguments': {'requested_fields': ['execution_status', 'result_available']}}, 'report_update': {}}
        received = []

        def parent_uses_return(context):
            report, = context['child_reports']
            received.append(report)
            assert report['state'] == 'pending' and len(report['progress']) == 1
            return {'selection': {'kind': 'tool', 'tool': 'episode.history',
                'arguments': {'view': 'records', 'decision_indices': [0]}}, 'report_update': {}}

        provider = ScriptedProvider([
            {'selection': {'kind': 'episode_child', 'role': 'monitor',
                'assignment': assignment(target['handle'], fields=['execution_status', 'result_available']),
                'goal': 'Investigate whether further exposed status is informative', 'scope': scope,
                'purpose': 'Return received status and its original observation references',
                'schema_json': json.dumps(report_schema), 'initial_report_json': '{}'}, 'report_update': {}},
            observe, observe, parent_uses_return])
        workflow, controllers, selections = build_workflow(tmp_path, store, provider)
        root = workflow.build('annotation', 'root', 'Investigate the fixture uncertainty', scope)
        record = asyncio.run(root.run_async(workflow.context))
        asyncio.run(root.build_result(record))

        assert workflow.receipts is None
        assert [controller.scores for controller in controllers] == [[0, 0], [1, 0]]
        assert len(received) == 1
        references = workflow.progress_provider.received_progress_refs(root.source.episode_id)
        assert references == received[0]['progress']
        assert selections[-1]['known_progress_refs'] == references
        assert all(not selection['known_record_refs'] for selection in selections)
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 4
        assert not store.list('assessment') and not store.list('observation')


def test_specialist_resolver_cannot_bypass_actual_progress_delivery(tmp_path):
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='MKWAA', molecule='protein')
        backend = DurableExecutionStore(tmp_path / 'run' / 'episode-execution')
        target = durable_target(tmp_path, store, backend)
        workflow, _, _ = build_workflow(tmp_path, store, ScriptedProvider([]))
        scope = target['child']['scope']
        root = workflow.build('annotation', 'root', 'Investigate the fixture', scope)
        from gene_annotation_episode.runtime import TypedReportContract
        schema = obj({'progress': {'type': 'array', 'items': {'type': 'string', 'format': 'reference',
            'x-reference-namespace': 'episode_progress'}}})
        contract = TypedReportContract('Return the actually received progress', schema, workflow.resolver(scope))
        child = workflow.build('monitor', 'child', 'Investigate exposed status', scope,
            parent=root.goal, parent_path=root.source.path, contract=contract, initial={'progress': []},
            episode_assignment=assignment(target['handle']))
        snapshot = workflow.progress_provider.observe(target['handle'], ['execution_status'], scope)
        reference = snapshot['progress_ref']
        assert workflow.progress_provider.resolve(reference, scope, 'episode_progress')
        assert not workflow.resolver(scope, source=child.source)(reference, 'episode_progress')
        assert not workflow.resolver(scope, source=child.source)(reference)
        with store.transaction():
            workflow.receive_form(child.source, {'progress': [reference]}, schema, 0)
        assert workflow.resolver(scope, source=child.source)(reference, 'episode_progress')
