"""A107 original API selections and typed returns with controlled native bytes.

Store, Journal, API execution/publication, result graders, original result
identities, frozen forms and return readers remain actual. No network or native
process is needed. This fixture does not claim a complete autonomous workflow.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import patch

from ..test_information_connected import InformationCase, module
from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources


MINHASH_RESOURCE = {'kind': 'api', 'service': 'bvbrc_minhash',
    'endpoint': 'https://minhash.example.invalid/native/rpc'}
MINHASH_REQUEST = {'mode': 'genome', 'query': '511145.12', 'max_pvalue': .2,
    'max_distance': 1, 'max_hits': 10, 'include_reference': 1,
    'include_representative': 0, 'bacterial': 1, 'viral': 0}
MINHASH_ROWS = [['83333.1', '0.02', '0.001', '41/1000'],
    ['83333.1', '0.03', '0.002', '20/1000']]


def snapshot(rpc):
    sent = json.dumps(rpc, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()
    content = json.dumps({'version': '1.1', 'id': rpc['id'], 'result': [MINHASH_ROWS]}).encode()
    return module('acquisition').SourceSnapshot('bvbrc_analysis', MINHASH_RESOURCE['endpoint'],
        {'kind': 'rpc', 'rpc': deepcopy(rpc)}, '2026-10-24T12:00:00+00:00', content,
        'application/json', {'status': 200, 'body_complete': True,
            'request': {'method': 'POST', 'url': MINHASH_RESOURCE['endpoint'],
                'body_bytes': len(sent), 'body_sha256': hashlib.sha256(sent).hexdigest(),
                'headers': [['Content-Type', 'application/json']]},
            'representation': 'synthetic_native_rpc_response',
            'duration_measure': 'client_http_request_turnaround', 'http_turnaround_seconds': .125})


class ReceivedAPIFixture:
    def __init__(self, directory, service, *, connect=False):
        self.service = service
        configured = resources()
        configured['received-service'] = (deepcopy(MINHASH_RESOURCE) if service == 'bvbrc_minhash'
            else {'kind': 'api', 'service': 'bvbrc_data'})
        self.case = InformationCase(directory, received_resources=configured, connect=connect)
        self.api = self.case.execution['scientific_process']['launch_api'].api_execution
        self.owner = self.case.execution['scientific_process']['results']
        self.calls = []
        self.canonical = module('execution_contracts').canonical
        self.plain = module('communication').plain
        self.receipts = module('episode_receipts').EpisodeReceipts(self.case.store, self.case.run_id)
        self.case.root = self.bind_context(self.case.root)
        self.receipts.receive(self.case.root.episode_id, self.case.scope['subject_refs'], kind='initial')
        if service == 'bvbrc_minhash':
            facts = module('bvbrc_minhash_views').minhash_fact_sources()
            requested = ('bvbrc_minhash_matches', 'bvbrc_minhash_counts')
            request, selector = deepcopy(MINHASH_REQUEST), {}
            operation, result_operation = 'api.bvbrc.minhash.genome', 'api.bvbrc.minhash.result'
            self.host = self.api.minhash
            target, name = module('bvbrc_analysis_transport').BVBRCAnalysisClient, 'rpc'
            def response(client, rpc):
                self.calls.append(deepcopy(rpc))
                return snapshot(rpc)
        else:
            facts = module('bvbrc_data_views').bvbrc_data_fact_sources()
            requested = tuple(module('bvbrc_data_views').FACT_SOURCES)
            request = {'version': 'bvbrc_data_request_v2', 'collection': 'genome', 'mode': 'count', 'filters': []}
            selector = {'version': 'bvbrc_data_result_selector_v2', 'page': None,
                'projection': {'family': 'query_metadata'}, 'inputs': [], 'supplied_metadata': []}
            operation, result_operation = module('api_bvbrc').DATA_QUERY_OPERATION, module('api_bvbrc').DATA_RESULT_OPERATION
            self.host = self.api.bvbrc_data
            target, name = module('api_bvbrc').BVBRCDataClient, 'query_prepared'
            def response(client, prepared):
                self.calls.append(deepcopy(prepared))
                effective, native = prepared['effective_request'], prepared['native_request']
                payload = {'responseHeader': {'status': 0}, 'response': {
                    'docs': [], 'start': effective['offset'], 'numFound': 2, 'numFoundExact': True}}
                return module('acquisition').SourceSnapshot('bvbrc_data', native['url'], deepcopy(effective),
                    '2026-10-24T20:00:00+00:00', json.dumps(payload).encode(),
                    'application/solr+json; charset=utf-8', {'status': 200, 'body_complete': True,
                        'request': {field: deepcopy(native[field]) for field in ('method', 'url', 'headers', 'body')},
                        'effective_url': native['url'], 'automatic_redirects': False})
        properties = {'selected_' + str(index): facts[source]['report_schema']
            for index, source in enumerate(requested)}
        self.schema = {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}
        self.contract = module('runtime').TypedReportContract('Return original API numerical values', self.schema, lambda *_: True)
        self.case.root = self.bind_context(self.case.root, self.contract)
        parent_assignment = self.plain(self.case.parents['scientific_process'].assignment)
        self.parent = self.with_contract(self.case.root.path + (('scientific_process', 'child_2'),),
            parent_assignment, self.contract)
        assignment = {'version': 'api_service_assignment_v1', 'resource_id': 'received-service',
            'service': service, 'request': request, 'endpoint': 'usable_handoff', 'constraints': {}}
        launch = self.with_contract(self.parent.path + (('launch', 'child_0'),),
            {'version': 'execution_launch_assignment_v1', 'requests': {'received-service': assignment},
                'immutable_input_versions': [], 'constraints': {}}, None)
        self.native = self.with_contract(launch.path + (('launch_api', 'child_0'),), assignment, None)
        with patch.object(target, name, response):
            self.native_outcome = self.select(self.native, operation)
            self.handoff = self.native_outcome['result']['handoff_ref']
            result_assignment = {'version': 'execution_results_assignment_v1',
                'handoff_ref': self.handoff, 'selector': selector}
            self.result = self.with_contract(self.parent.path + (('results', 'child_1'),),
                result_assignment, self.contract)
            self.commission(self.parent, self.result, 1, self.contract)
            self.result_outcome = self.select(self.result, result_operation)
        assert len(self.calls) == 1
        self.facts = self.host.facts(self.result, self.schema)
        assert any(self.facts.values())
        self.form = module('communication').form_with_facts({}, self.schema, self.facts)
        self.freeze(self.result, self.form, self.facts)
        self.admit(self.parent, self.result, 1, self.form, self.contract)
        self.operation_key = f'{self.case.run_id}:{self.parent.episode_id}:1:typed_form'

    def bind_context(self, context, contract=None):
        parent = (module('method_loop/identities').EpisodeRef(self.case.run_id, context.path[:-1]).episode_id
            if len(context.path) > 1 else None)
        inheritance = self.receipts.bind(context.episode_id, parent)
        request = self.plain(context.request)
        request['message']['knowledge_inheritance'] = inheritance
        if contract is not None:
            request['report_contract'] = contract.as_record()
        self.case.journal.save('runtime_episodes', {'episode_id': context.episode_id,
            'path': self.canonical(context.path), 'request': self.canonical(request),
            'initial_credit': 0, 'state': 'running'})
        return replace(context, request=request)

    def with_contract(self, path, assignment, contract):
        return self.bind_context(self.case.context(path, assignment), contract)

    def select(self, context, operation):
        action = {'kind': 'tool', 'tool': operation, 'arguments': {}}
        self.case.journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': 0,
            'action': self.canonical(action), 'result': None, 'credit': None})
        outcome = asyncio.run(self.api.execute(context, operation, {}, f'{self.case.run_id}:{context.episode_id}:0'))
        assert outcome['status'] == 'completed', outcome
        self.case.journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': 0,
            'action': self.canonical(action), 'result': self.canonical(outcome), 'credit': 0})
        return outcome

    def commission(self, parent, child, index, contract):
        action = {'kind': 'episode_child', 'role': child.role,
            'assignment': self.plain(child.assignment), 'scope': self.plain(child.scope),
            'purpose': contract.decision, 'schema_json': self.canonical(contract.schema)}
        self.case.journal.save('runtime_actions', {'episode_id': parent.episode_id, 'decision_index': index,
            'action': self.canonical(action), 'result': None, 'credit': None})

    def freeze(self, context, form, facts):
        self.case.journal.save('runtime_forms', {'episode_id': context.episode_id,
            'facts': self.canonical(facts), 'form': self.canonical(form)})
        self.case.store.db.execute('UPDATE runtime_episodes SET state=? WHERE run_id=? AND episode_id=?',
            ('yielded', self.case.run_id, context.episode_id))

    def admit(self, parent, child, index, form, contract):
        self.case.journal.save('runtime_report_attempts', {'parent_episode_id': parent.episode_id,
            'decision_index': index, 'delivery_ref': 'original-api-return:' + child.episode_id,
            'child_episode_id': child.episode_id, 'contract': self.canonical(contract.as_record()),
            'form': self.canonical(form), 'failure': None})

    def record_original_admission(self):
        return self.host.record_admission(self.parent, self.form, self.schema, self.operation_key)

    def forward_to_root(self):
        facts = self.host.received_facts(self.parent, self.schema)
        form = module('communication').form_with_facts({}, self.schema, facts)
        self.freeze(self.parent, form, facts)
        self.commission(self.case.root, self.parent, 2, self.contract)
        self.admit(self.case.root, self.parent, 2, form, self.contract)
        key = f'{self.case.run_id}:{self.case.root.episode_id}:2:typed_form'
        self.host.record_admission(self.case.root, form, self.schema, key)
        return form, key

    def state(self):
        return tuple(self.case.store.db.iterdump())

    def action_state(self):
        return {table: [tuple(row) for row in self.case.store.db.execute('SELECT * FROM ' + table)]
            for table in ('runtime_actions', 'runtime_observations')}

    def runtime_receive(self, registry, *, redelivery=False):
        """Actual default runtime receipt projection with named controlled ports.

        This is a boundary test, not Workflow construction. No progress or
        attribution provider is configured and no specialist counterpart is
        selected by this port; full parent dispatch remains a separate probe.
        """
        runtime = module('runtime').Workflow.__new__(module('runtime').Workflow)
        runtime.store, runtime.run_id = self.case.store, self.case.run_id
        runtime.receipts, runtime.episode_bindings = self.receipts, registry
        runtime.progress_provider = runtime.native_timing_information = runtime.job_episodes = None
        runtime.specialist = lambda source: None
        runtime.is_job_source = lambda source: False
        runtime.binding_context = lambda source: self.parent
        runtime.receive_tool_attributions = lambda *args, **kwargs: []
        source = SimpleNamespace(episode_id=self.parent.episode_id,
            scope=self.case.store.validate_scope(self.plain(self.parent.scope)))
        return runtime.receive_form(source, self.form, self.schema, 1, redelivery=redelivery)

    def close(self):
        self.case.close()
