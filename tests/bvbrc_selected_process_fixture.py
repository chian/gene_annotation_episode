"""Selected scientific-process engineering path, using the current libraries.

Only provider decisions/continuation and the urllib HTTP response are fixtures.
The selected native bytes are replayed; their old acquisition metadata is never
rewritten or represented as a new live request. No scientific closure is claimed.
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

from gene_annotation_episode.bvbrc_data_views import bvbrc_data_fact_sources
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.tools import ToolRegistry

from bvbrc_episode_fixture import (
    EVIDENCE, RESOURCES, child, handoff_form, request, result_form, retained_bytes,
    selected, selector,
)


ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = ROOT / 'research/slotted_process_library/publications/2026-10-24-001'
SELECTED_TOOLS = [{'name': name, 'resources': 'api'} for name in
                  ('api.bvbrc.data.query', 'api.bvbrc.data.result')]
REFERENCE_FORM = {'type': 'object', 'additionalProperties': False,
    'required': ['references'], 'properties': {'references': {
        'type': 'array', 'uniqueItems': True, 'items': {
            'type': 'string', 'format': 'reference'}, 'x-source': 'committed_record_refs'}}}


def count_form():
    """The parent's sole requested result; no child instructions or yield."""
    return {'type': 'object', 'additionalProperties': False, 'required': ['counts'],
        'properties': {'counts': deepcopy(
            bvbrc_data_fact_sources()['execution_bvbrc_counts']['report_schema'])}}


class RetainedHTTP:
    """Patch only urllib's I/O boundary; run the real request/snapshot code."""

    def __init__(self, monkeypatch, *, response_name='feature_count_solr'):
        self.body = retained_bytes(response_name)
        self.metadata = json.loads((EVIDENCE / (response_name + '.meta.json')).read_text())
        self.calls = []
        outer = self

        class Response:
            status = outer.metadata['status']

            def __init__(self):
                self.headers = Message()
                for name, value in outer.metadata['headers']:
                    self.headers[name] = value

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def geturl(self):
                return outer.metadata['effective_url']

            def read(self):
                return outer.body

        def open_response(opener, native_request, *, timeout):
            assert not self.calls, 'Unexpected additional HTTP request'
            assert native_request.full_url == self.metadata['url']
            assert native_request.get_method() == 'GET'
            assert native_request.data is None
            assert timeout == RESOURCES['bvbrc']['timeout']
            headers = {key.lower(): value for key, value in native_request.header_items()}
            assert headers['accept'] == 'application/solr+json'
            assert headers['content-type'] == 'application/solrquery+x-www-form-urlencoded'
            self.calls.append({'url': native_request.full_url, 'method': 'GET',
                'headers': headers, 'timeout': timeout})
            return Response()

        def forbidden(*args, **kwargs):
            raise AssertionError('Selected-process verification attempted a live connection')

        monkeypatch.setattr('urllib.request.OpenerDirector.open', open_response)
        monkeypatch.setattr('socket.create_connection', forbidden)


class SelectedProcessRun:
    """Actual common scientific child and selected launch/API/results episodes."""

    def __init__(self, store, directory, *, scope=None, parent_form=None,
                 selected_query=None, result_sources=None, question=None):
        self.store, self.directory = store, Path(directory)
        self.run_id = 'bvbrc-selected-process-fixture'
        self.sequence = ''.join(line.strip() for line in
            (ROOT / 'cases/gene_001/target.faa').read_text().splitlines()
            if not line.startswith('>'))
        self.scope = deepcopy(scope) if scope is not None else {'subject_refs':
            store.create_problem(raw_sequence=self.sequence, molecule='protein')['subject_refs']}
        self.parent_form = deepcopy(REFERENCE_FORM if parent_form is None else parent_form)
        self.result_form = result_form(*(('execution_bvbrc_counts', 'execution_bvbrc_pages')
            if result_sources is None else result_sources))
        self.query = request() if selected_query is None else deepcopy(selected_query)
        self.selection, self.question = selector(), question
        self.api_assignment = {'version': 'api_service_assignment_v1', 'resource_id': 'bvbrc',
            'service': 'bvbrc_data', 'request': self.query, 'endpoint': 'usable_handoff',
            'constraints': {'allowed_resource_ids': ['bvbrc'], 'allowed_kinds': ['api']}}
        self.launch_assignment = {'version': 'execution_launch_assignment_v1',
            'requests': {'bvbrc': self.api_assignment}, 'immutable_input_versions': [],
            'constraints': {'allowed_resource_ids': ['bvbrc'], 'allowed_kinds': ['api']}}
        self.calls, self.contexts = {}, []
        self.scientific_after_result = self.root_after_result = self.received_form = None
        self.handoff = None
        self.controllers = {}
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
                # Explicit test continuation, never a production scientific
                # completion criterion. Resource roles retain their real
                # practical endpoint estimator installed by Workflow.
                count = 2 if path[-1][0] == 'annotation' else 3
                return YieldEstimate(len(history), NumericBand.exact(
                    0 if len(history) >= count else 1), parameters,
                    {'fixture': 'engineering_scientific_continuation_only'})
            value = YieldController(str(path), initial, 0, YieldParameters(100, 50),
                estimate_with_context=engineering_estimate
                if path[-1][0] in {'annotation', 'scientific_process'} else None)
            self.controllers[path] = value
            return value

        self.workflow = Workflow(store, tools, self, self.directory, self.run_id,
            controller_factory=controller, project_credit=lambda *_: 0,
            episode_binding_descriptors=(self.descriptor, *application.episode_binding_descriptors),
            role_credit_bindings=application.role_credit_bindings,
            job_progress_provider=application.job_progress_provider,
            annotation_child_roles=('scientific_process',),
            episode_record_receipts=True, initial_known_record_refs=[])
        self.episode = self.workflow.build('annotation', 'root',
            'Investigate the supplied protein using selected native source measurements'
            if question is None else question, self.scope)

    def commission(self):
        assignment = {'selection': {'version': 'scientific_process_selection_v3',
            'evidence_axis': self.library.reference('A101'),
            'thought_pattern': self.library.reference('P01'),
            'child_tool_info': deepcopy(SELECTED_TOOLS)},
            'evidence_refs': list(self.scope['subject_refs']),
            'constraints': {'preserve_original_query': True},
            'context': {'supplied_sequence': self.sequence, 'molecule': 'protein',
                'complete': True, 'label_is_public_identity': False,
                'selected_native_count_query': deepcopy(self.query)}}
        action = child('scientific_process', assignment, self.scope, self.parent_form)
        if self.question is not None:
            action['selection']['goal'] = self.question
            action['selection']['assignment']['context']['question'] = self.question
        return action

    @staticmethod
    def wait():
        # A selected ordinary zero-gain action saves the next received context.
        # This is engineering-only; no compulsory scientific/resource itinerary.
        return {'selection': {'kind': 'wait', 'condition': {'version': 'event_condition_v1',
            'events': [], 'reconsider_at': datetime.now(timezone.utc).isoformat()}},
            'report_update': {}}

    async def complete(self, episode_id, role, instructions, current, schema):
        self.calls[episode_id] = self.calls.get(episode_id, 0) + 1
        count = self.calls[episode_id]
        self.contexts.append((episode_id, deepcopy(current)))
        assert current.get('feedback') is None, current.get('feedback')
        execution = current.get('execution_assignment', {})
        version = execution.get('version')
        if version == 'execution_launch_assignment_v1':
            assert count == 1 and execution == self.launch_assignment
            assert [item['resource_id'] for item in current['execution_resource_capabilities']] == ['bvbrc']
            return child('launch_api', self.api_assignment, self.scope, handoff_form())
        if version == 'api_service_assignment_v1':
            assert count == 1 and execution == self.api_assignment
            return selected('api.bvbrc.data.query')
        if version == 'execution_results_assignment_v1':
            assert count == 1 and execution['selector'] == self.selection
            return selected('api.bvbrc.data.result')
        if 'scientific_process' in current:
            if count == 1:
                assert current['received_bvbrc_values'] == []
                return child('launch', self.launch_assignment, self.scope, handoff_form())
            if count == 2:
                handoff = current['child_reports'][-1]
                assert handoff['completed'] is True
                self.handoff, = handoff['references']
                return child('results', {'version': 'execution_results_assignment_v1',
                    'handoff_ref': self.handoff, 'selector': self.selection},
                    self.scope, self.result_form)
            assert count == 3
            self.scientific_after_result = deepcopy(current)
            self.received_form = deepcopy(current['child_reports'][-1])
            return self.wait()
        if count == 1:
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
        original, path = json.loads(saved['request']), tuple(map(tuple, json.loads(saved['path'])))
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
