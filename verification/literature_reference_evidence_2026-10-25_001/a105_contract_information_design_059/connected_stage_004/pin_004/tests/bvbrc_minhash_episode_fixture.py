"""Scripted MinHash episode choices and a synthetic urllib response boundary.

The common Workflow, scientific construction, service transport, publication,
typed returns and practical estimator remain real. No model or BV-BRC service
is contacted. The supplied sequence is an input, not a claimed genome match.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from email.message import Message
import hashlib
import json
from pathlib import Path

from method_loop.archive import iter_json
from method_loop.identities import EpisodeRef

from gene_annotation_episode.bvbrc_minhash_views import minhash_fact_sources
from gene_annotation_episode.domain import identity
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_reports import report_sources
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.tools import ToolRegistry


ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = ROOT / 'research/slotted_process_library/publications/2026-10-24-001'
RESOURCES = {'minhash': {'kind': 'api', 'service': 'bvbrc_minhash',
    'endpoint': 'https://minhash.synthetic.invalid/rpc', 'timeout': 90}}
NATIVE_ROWS = [['83333.1', '0.02', '0.001', '41/1000'],
               ['83333.1', '0.03', '0.002', '20/1000']]
SOURCE_FORM = {'type': 'object', 'additionalProperties': False,
    'required': ['references'], 'properties': {'references': {
        'type': 'array', 'uniqueItems': True, 'items': {
            'type': 'string', 'format': 'reference'}, 'x-source': 'committed_record_refs'}}}


def request(mode='genome'):
    return {'mode': mode,
        'query': '83333.1' if mode == 'genome' else '/synthetic@bvbrc/home/inputs/query.fasta',
        'max_pvalue': 0.1, 'max_distance': 0.2, 'max_hits': 2,
        'include_reference': 1, 'include_representative': 0, 'bacterial': 1, 'viral': 0}


def native_request(query):
    return {'version': '1.1', 'method':
        'Minhash.compute_genome_distance_for_' + query['mode'] + '2',
        'params': [query[key] for key in ('query', 'max_pvalue', 'max_distance',
            'max_hits', 'include_reference', 'include_representative', 'bacterial', 'viral')],
        'id': identity('minhash_rpc', query)}


def fact_form(*families):
    properties = {family.removeprefix('bvbrc_minhash_'): deepcopy(
        minhash_fact_sources()[family]['report_schema']) for family in families}
    return {'type': 'object', 'properties': properties, 'required': list(properties),
        'additionalProperties': False}


def count_form():
    return fact_form('bvbrc_minhash_counts')


def result_form():
    value = fact_form('bvbrc_minhash_matches', 'bvbrc_minhash_counts')
    value['properties'].update({
        'completed': {'type': 'boolean', 'x-source': 'execution_completed'},
        'references': {'type': 'array', 'uniqueItems': True, 'items': {
            'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_result'},
            'x-source': 'execution_result_refs'},
        'yield': report_sources()['episode_yield']['report_schema']})
    value['required'] = list(value['properties'])
    return value


def handoff_form():
    return {'type': 'object', 'additionalProperties': False,
        'required': ['completed', 'references'], 'properties': {
            'completed': {'type': 'boolean', 'x-source': 'execution_completed'},
            'references': {'type': 'array', 'uniqueItems': True, 'items': {
                'type': 'string', 'format': 'reference',
                'x-reference-namespace': 'execution_handoff'}, 'x-source': 'execution_handoff_refs'}}}


def child(role, assignment, scope, form):
    return {'selection': {'kind': 'episode_child', 'role': role,
        'goal': 'Acquire the explicitly assigned MinHash genome-distance measurements',
        'scope': scope, 'purpose': 'Return only the requested typed native measurements',
        'assignment': deepcopy(assignment), 'schema_json': json.dumps(form),
        'initial_report_json': '{}'}, 'report_update': {}}


def selected(name):
    return {'selection': {'kind': 'tool', 'tool': name, 'arguments': {}}, 'report_update': {}}


class SyntheticHTTP:
    """Intercept only urllib I/O with retained, explicitly synthetic RPC bytes."""

    def __init__(self, monkeypatch, query, rows=NATIVE_ROWS):
        self.request = native_request(query)
        self.rows = deepcopy(rows)
        self.body = json.dumps({'version': '1.1', 'id': self.request['id'],
            'result': [self.rows]}, separators=(',', ':'), allow_nan=False).encode()
        self.calls = []
        outer = self

        class Response:
            status = 200

            def __init__(self):
                self.headers = Message()
                self.headers['Content-Type'] = 'application/json'
                self.headers['Content-Length'] = str(len(outer.body))

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def geturl(self):
                return RESOURCES['minhash']['endpoint']

            def read(self):
                return outer.body

        def open_response(opener, native, *, timeout):
            assert not self.calls, 'Unexpected repeated MinHash HTTP request'
            assert native.full_url == RESOURCES['minhash']['endpoint']
            assert native.get_method() == 'POST'
            assert json.loads(native.data) == self.request
            assert timeout == RESOURCES['minhash']['timeout']
            headers = {key.lower(): value for key, value in native.header_items()}
            assert headers['content-type'] == 'application/json'
            assert int(headers['content-length']) == len(native.data)
            self.calls.append({'url': native.full_url, 'method': native.get_method(),
                'request': json.loads(native.data), 'request_sha256': hashlib.sha256(native.data).hexdigest(),
                'request_bytes': len(native.data), 'headers': headers, 'timeout': timeout})
            return Response()

        def forbidden(*args, **kwargs):
            raise AssertionError('MinHash integration fixture attempted a network connection')

        monkeypatch.setattr('urllib.request.OpenerDirector.open', open_response)
        monkeypatch.setattr('socket.create_connection', forbidden)


class PartialResultDecisionReached(Exception):
    """Stop this engineering harness only after a partial action was observed."""


class MinhashRun:
    """Existing selected-process semantics with actual MinHash tool information."""

    def __init__(self, store, directory, *, mode='genome', scope=None, parent_form=None,
                 partial=False):
        self.store, self.directory = store, Path(directory)
        self.run_id = 'bvbrc-minhash-episode-fixture'
        self.sequence = ''.join(line.strip() for line in
            (ROOT / 'cases/gene_001/target.faa').read_text().splitlines()
            if not line.startswith('>'))
        self.scope = deepcopy(scope) if scope is not None else {'subject_refs':
            store.create_problem(raw_sequence=self.sequence, molecule='protein')['subject_refs']}
        self.parent_form = deepcopy(count_form() if parent_form is None else parent_form)
        self.result_form = result_form()
        self.query, self.selector = request(mode), {}
        self.selected_tools = [{'name': name, 'resources': 'api'} for name in
            ('api.bvbrc.minhash.' + mode, 'api.bvbrc.minhash.result')]
        self.api_assignment = {'version': 'api_service_assignment_v1', 'resource_id': 'minhash',
            'service': 'bvbrc_minhash', 'request': self.query, 'endpoint': 'usable_handoff',
            'constraints': {'allowed_resource_ids': ['minhash'], 'allowed_kinds': ['api']}}
        self.launch_assignment = {'version': 'execution_launch_assignment_v1',
            'requests': {'minhash': self.api_assignment}, 'immutable_input_versions': [],
            'constraints': {'allowed_resource_ids': ['minhash'], 'allowed_kinds': ['api']}}
        self.calls, self.contexts = {}, []
        self.scientific_after_result = self.root_after_result = self.received_form = None
        self.partial, self.partial_context, self.partial_episode_id = partial, None, None
        self.handoff = None
        tools = ToolRegistry(store)
        factory = ExecutionServiceFactory(RESOURCES, {}, 3, 2, .5)
        application = factory(store, run_id=self.run_id, directory=self.directory,
            tool_registry=tools, tool_catalog=tools.catalog())
        self.descriptor = prepare_scientific_binding(run_directory=self.directory,
            source_directory=PUBLICATION, tool_catalog=tools.catalog(),
            child_roles=('scientific_process', 'launch', 'results'),
            resource_catalogs=application.resource_tool_catalogs)
        self.library = ScientificProcessLibrary(self.directory / 'scientific-process-library')

        def controller(path, initial):
            def engineering_estimate(history, parameters, contexts):
                # Fixture continuation for scientific roles only. Resource
                # completion uses the production practical estimator.
                count = 2 if path[-1][0] == 'annotation' else 3
                return YieldEstimate(len(history), NumericBand.exact(
                    0 if len(history) >= count else 1), parameters,
                    {'fixture': 'engineering_scientific_continuation_only'})
            return YieldController(str(path), initial, 0, YieldParameters(100, 50),
                estimate_with_context=engineering_estimate
                if path[-1][0] in {'annotation', 'scientific_process'} else None)

        self.workflow = Workflow(store, tools, self, self.directory, self.run_id,
            controller_factory=controller, project_credit=lambda *_: 0,
            episode_binding_descriptors=(self.descriptor, *application.episode_binding_descriptors),
            role_credit_bindings=application.role_credit_bindings,
            job_progress_provider=application.job_progress_provider,
            annotation_child_roles=('scientific_process',),
            episode_record_receipts=True, initial_known_record_refs=[])
        self.episode = self.workflow.build('annotation', 'root',
            'Investigate the supplied protein using selected native measurements', self.scope)

    def commission(self):
        assignment = {'selection': {'version': 'scientific_process_selection_v3',
            'evidence_axis': self.library.reference('A101'),
            'thought_pattern': self.library.reference('P01'),
            'child_tool_info': deepcopy(self.selected_tools)},
            'evidence_refs': list(self.scope['subject_refs']),
            'constraints': {'preserve_original_query': True},
            'context': {'supplied_sequence': self.sequence, 'molecule': 'protein',
                'complete': True, 'label_is_public_identity': False,
                'selected_minhash_request': deepcopy(self.query)}}
        return child('scientific_process', assignment, self.scope, self.parent_form)

    @staticmethod
    def wait():
        return {'selection': {'kind': 'wait', 'condition': {'version': 'event_condition_v1',
            'events': [], 'reconsider_at': datetime.now(timezone.utc).isoformat()}},
            'report_update': {}}

    async def complete(self, episode_id, role, instructions, current, schema):
        self.calls[episode_id] = self.calls.get(episode_id, 0) + 1
        count = self.calls[episode_id]
        self.contexts.append((episode_id, deepcopy(current)))
        execution = current.get('execution_assignment', {})
        version = execution.get('version')
        if version == 'execution_results_assignment_v1' and count == 2 and self.partial:
            self.partial_context, self.partial_episode_id = deepcopy(current), episode_id
            raise PartialResultDecisionReached
        assert current.get('feedback') is None, current.get('feedback')
        if version == 'execution_launch_assignment_v1':
            assert count == 1 and execution == self.launch_assignment
            assert [item['resource_id'] for item in current['execution_resource_capabilities']] == ['minhash']
            return child('launch_api', self.api_assignment, self.scope, handoff_form())
        if version == 'api_service_assignment_v1':
            assert count == 1 and execution == self.api_assignment
            return selected('api.bvbrc.minhash.' + self.query['mode'])
        if version == 'execution_results_assignment_v1':
            assert count == 1 and execution['selector'] == {}
            return selected('api.bvbrc.minhash.result')
        if 'scientific_process' in current:
            if count == 1:
                assert current['received_minhash_values'] == []
                return child('launch', self.launch_assignment, self.scope, handoff_form())
            if count == 2:
                handoff = current['child_reports'][-1]
                assert handoff['completed'] is True
                self.handoff, = handoff['references']
                return child('results', {'version': 'execution_results_assignment_v1',
                    'handoff_ref': self.handoff, 'selector': {}}, self.scope, self.result_form)
            assert count == 3
            self.scientific_after_result = deepcopy(current)
            self.received_form = deepcopy(current['child_reports'][-1])
            return self.wait()
        if count == 1:
            assert current['received_minhash_values'] == []
            return self.commission()
        assert count == 2
        self.root_after_result = deepcopy(current)
        return self.wait()

    async def release(self, episode_id):
        pass

    def run(self):
        async def execute():
            record = await self.episode.run_async(self.workflow.context)
            await self.episode.build_result(record)
            return record
        record = asyncio.run(execute())
        self.archive = json.loads(''.join(iter_json(record.as_record())))
        return self.archive

    def rows(self, table, episode_id=None):
        query, operands = 'SELECT * FROM ' + table + ' WHERE run_id=?', [self.run_id]
        if episode_id is not None:
            query += ' AND episode_id=?'
            operands.append(episode_id)
        return [dict(row) for row in self.store.db.execute(query, operands)]

    def context(self, episode_id):
        saved = self.workflow.journal.row('runtime_episodes', episode_id)
        original = json.loads(saved['request'])
        path = tuple(map(tuple, json.loads(saved['path'])))
        assert EpisodeRef(self.run_id, path).episode_id == episode_id
        return BindingContext(self.run_id, episode_id, path[-1][0], path,
            original['message']['scope'], original['message'].get('episode_assignment', {}), original)

    @property
    def api(self):
        return self.workflow.episode_bindings.for_role('results').api_execution

    def frozen_hashes(self):
        return {str(path.relative_to(self.directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for folder in ('scientific-process-library', 'scientific-tool-library')
            for path in sorted((self.directory / folder).rglob('*')) if path.is_file()}

