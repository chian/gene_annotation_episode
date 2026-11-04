"""Selected AppService actions, typed returns and zero endpoint in method_loop.

The choices and HTTP responses are explicit fixtures. Production commissions,
custody, selected execution, publication, forms and practical estimation run.
"""
import asyncio
from copy import deepcopy
import json

from method_loop.archive import iter_json

from gene_annotation_episode.api_bvbrc_appservice import BVBRCAppServiceService
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_api_bvbrc_appservice import CONFIG, PREFIX
from test_bvbrc_appservice_custody import request, selector
from test_bvbrc_appservice_inputs import NativeClient, output_target, download_args
from test_execution_episodes_family import launch_assignment
from test_execution_wiring import child, form
from test_practical_runtime import selected
from test_public_search import Client


def test_shared_method_loop_retains_download_and_returns_original_typed_form(tmp_path, monkeypatch):
    class Responses(NativeClient):
        def rpc(self, command):
            if command['method'] == 'AppService.start_app2':
                self.value = {'id': '123', 'application_id': 'Homology', 'state_code': 'Q'}
            elif command['method'] == 'Workspace.get_download_url':
                self.value = ['https://fixture.invalid/output']
            else:
                raise AssertionError(command)
            return super().rpc(command)
    native = Responses()
    native.body = b'exact downloaded native bytes'
    constructor = BVBRCAppServiceService.__init__
    def configured(self, *args, **kwargs):
        constructor(self, *args, **kwargs)
        self.client = native
    monkeypatch.setattr(BVBRCAppServiceService, '__init__', configured)
    def forbidden(*args, **kwargs):
        raise AssertionError('workflow fixture attempted live transport')
    monkeypatch.setattr('socket.create_connection', forbidden)

    def controllers(path, initial):
        def root_estimate(history, parameters, contexts):
            return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= 2 else 1),
                parameters, {'fixture': 'root_continuation_only'})
        return YieldController(str(path), initial, 0, YieldParameters(100, 50),
            estimate_with_context=root_estimate if path[-1][0] == 'annotation' else None)

    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']
        scope = {'subject_refs': [target]}
        original = request()
        obj = output_target(original)
        assignment = {'version': 'api_service_assignment_v1', 'resource_id': 'selected-api',
            'service': 'bvbrc_appservice', 'request': original, 'endpoint': 'usable_handoff', 'constraints': {}}
        launch = launch_assignment({'selected-api': assignment})
        handoff_form, result_form = form('execution_handoff_refs'), form('execution_result_refs')
        factory = ExecutionServiceFactory({'selected-api': CONFIG}, {}, 2, 3, .5)

        class Choices:
            def __init__(self):
                self.root_count = 0
                self.counts = {}
            def last(self, episode_id):
                row = store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? '
                    'AND result IS NOT NULL ORDER BY decision_index DESC LIMIT 1',
                    (workflow.run_id, episode_id)).fetchone()
                return json.loads(row['result'])['result']
            async def complete(self, episode_id, role, instructions, current, schema):
                assert current.get('feedback') is None, current.get('feedback')
                self.counts[episode_id] = self.counts.get(episode_id, 0) + 1
                count = self.counts[episode_id]
                execution = current.get('execution_assignment', {})
                if execution.get('version') == 'execution_launch_assignment_v1':
                    assert count == 1
                    return child('launch_api', assignment, scope, handoff_form)
                if execution.get('version') == 'api_service_assignment_v1':
                    if count == 1:
                        return selected(PREFIX + 'prepare', {'definition': {
                            'kind': 'packaged', 'required_application_id': 'Homology'}})
                    assert count == 2
                    return selected(PREFIX + 'submit', {'preparation_receipt_ref':
                        self.last(episode_id)['support_receipt_ref'], 'input_evidence_refs': []})
                if execution.get('version') == 'execution_results_assignment_v1':
                    if count == 1:
                        return selected(PREFIX + 'download_capability', {'objects': [obj],
                            'generation': 0, 'predecessor_receipt_ref': None})
                    assert count == 2
                    return selected(PREFIX + 'download', download_args(obj, {'kind': 'acquired',
                        'receipt_ref': self.last(episode_id)['support_receipt_ref'], 'input_index': 0}))
                self.root_count += 1
                if self.root_count == 1:
                    return child('launch', launch, scope, handoff_form)
                assert self.root_count == 2
                received = current['child_reports'][-1]
                assert received['completed'] and received['yield']['expected_next_gain'] == NumericBand.exact(0).as_record()
                handoff, = received['references']
                return child('results', {'version': 'execution_results_assignment_v1',
                    'handoff_ref': handoff, 'selector': selector()}, scope, result_form)
            async def release(self, episode_id):
                pass

        choices = Choices()
        workflow = Workflow(store, ToolRegistry(store, clients=Client()), choices, tmp_path / 'run',
            'appservice-artifact-workflow', controller_factory=controllers, project_credit=lambda *_: 0,
            episode_service_factory=factory, episode_service_binding=factory.as_record(),
            episode_service_inputs='actual_tool_registry_v1', annotation_child_roles=('launch', 'results'),
            episode_record_receipts=True, initial_known_record_refs=[])
        episode = workflow.build('annotation', 'root', 'Obtain the original requested output', scope)
        async def run():
            record = await episode.run_async(workflow.context)
            await episode.build_result(record)
            return record
        record = asyncio.run(run())
        archived = json.loads(''.join(iter_json(record.as_record())))
        launch_record = archived['units'][0]['child']
        api_record = launch_record['units'][0]['child']
        result_record = archived['units'][1]['child']
        assert record.units_consumed == 2
        assert launch_record['units_consumed'] == 1
        for closed in (api_record, result_record):
            assert closed['units_consumed'] == 2
            assert closed['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
            assert closed['units'][-1]['controller_step']['marginal_credit'] > 0
        returned = json.loads(workflow.journal.row('runtime_forms', result_record['episode_id'])['form'])
        assert returned['completed'] and len(returned['references']) == 1
        source = store.get(returned['references'][0])
        bundle = json.loads(store.get_artifact(source['artifact_ref']))
        assert store.get_artifact(bundle['artifacts'][0]['raw_artifact_ref']) == native.body
        assert [row[0] for row in native.calls] == ['rpc', 'rpc', 'download']
        assert store.count('annotation') == 0
