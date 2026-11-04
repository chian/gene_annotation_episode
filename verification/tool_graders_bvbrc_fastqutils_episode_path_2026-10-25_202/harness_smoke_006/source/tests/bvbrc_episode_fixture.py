"""Engineering choices and transport for BV-BRC v2 shared-loop verification.

These fixtures do not replace host qualification, artifact custody, endpoint
validation, admission, or the resource episodes' practical yield estimator.
No configured model or live BV-BRC service is exercised.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from method_loop.archive import iter_json
from method_loop.identities import EpisodeRef

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.api_bvbrc import BVBRCDataClient
from gene_annotation_episode.bvbrc_data_views import bvbrc_data_fact_sources
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_reports import report_sources
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.tools import ToolRegistry


EVIDENCE = Path(__file__).resolve().parents[1] / 'verification/tool_graders_bvbrc_data_contract_2026-10-24'
FEATURE_IDS = ['PATRIC.511145.12.NC_000913.CDS.822959.823720.rev',
               'RefSeq.511145.12.NC_000913.CDS.822959.823720.rev']
RESOURCES = {'bvbrc': {'kind': 'api', 'service': 'bvbrc_data',
                       'base_url': 'https://www.bv-brc.org/api', 'timeout': 90}}


def request(collection='genome_feature', *, mode='count', fields=None, **extra):
    value = {'version': 'bvbrc_data_request_v2', 'collection': collection, 'mode': mode,
        'filters': ([{'field': 'feature_id', 'operator': 'in', 'value': FEATURE_IDS}]
                    if collection == 'genome_feature' else [])}
    if fields is not None:
        value['fields'] = list(fields)
    return {**value, **extra}


def selector(projection=None, *, page=None, inputs=(), supplied=()):
    return {'version': 'bvbrc_data_result_selector_v2', 'page': page,
        'projection': {'family': 'query_metadata'} if projection is None else deepcopy(projection),
        'inputs': deepcopy(list(inputs)), 'supplied_metadata': deepcopy(list(supplied))}


def rows_selector(*, rows=(0,), numbers=(), metadata=(), page=None):
    return selector({'family': 'collection_rows', 'row_indices': list(rows),
        'numeric_fields': list(numbers), 'metadata_fields': list(metadata)}, page=page)


def retained_bytes(name):
    body = (EVIDENCE / (name + '.body')).read_bytes()
    metadata = json.loads((EVIDENCE / (name + '.meta.json')).read_text())
    assert hashlib.sha256(body).hexdigest() == metadata['sha256']
    return body


def envelope(rows, *, total=None, start=0, partial=False):
    """Explicit synthetic Solr envelope, never a claimed live response."""
    header = {'status': 0}
    if partial:
        header['partialResults'] = True
    return json.dumps({'responseHeader': header, 'response': {'docs': rows,
        'numFound': len(rows) if total is None else total, 'numFoundExact': True,
        'start': start}}, ensure_ascii=False, allow_nan=False).encode()


class Transport:
    """One response per selected GET using the actual saved prepared request."""

    def __init__(self, monkeypatch, bodies):
        self.bodies = list(bodies)
        self.prepared = []

        def query_prepared(client, prepared):
            index = len(self.prepared)
            assert index < len(self.bodies), 'Unexpected extra BV-BRC GET'
            self.prepared.append(deepcopy(prepared))
            native = prepared['native_request']
            return SourceSnapshot('bvbrc_data', native['url'],
                deepcopy(prepared['effective_request']), f'2026-10-24T21:00:{index:02d}+00:00',
                self.bodies[index], 'application/solr+json', {'status': 200,
                    'body_complete': True, 'automatic_redirects': False,
                    'effective_url': native['url'], 'request': deepcopy(native),
                    'header_items': [['Content-Type', 'application/solr+json']],
                    'representation': 'engineering_fixture_with_explicit_native_or_synthetic_body'})

        monkeypatch.setattr(BVBRCDataClient, 'query_prepared', query_prepared)


def result_form(*sources):
    properties = {'completed': {'type': 'boolean', 'x-source': 'execution_completed'},
        'references': {'type': 'array', 'uniqueItems': True, 'items': {
            'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_result'},
            'x-source': 'execution_result_refs'},
        'yield': report_sources()['episode_yield']['report_schema']}
    for source in sources:
        properties[source.removeprefix('execution_bvbrc_')] = deepcopy(
            bvbrc_data_fact_sources()[source]['report_schema'])
    return {'type': 'object', 'properties': properties, 'required': list(properties),
        'additionalProperties': False}


def handoff_form():
    value = result_form()
    value['properties']['references']['x-source'] = 'execution_handoff_refs'
    value['properties']['references']['items']['x-reference-namespace'] = 'execution_handoff'
    return value


def child(role, assignment, scope, schema):
    return {'selection': {'kind': 'episode_child', 'role': role,
        'goal': 'Acquire the explicitly assigned BV-BRC native values', 'scope': scope,
        'purpose': 'Return the requested typed original source measurements',
        'assignment': deepcopy(assignment), 'schema_json': json.dumps(schema),
        'initial_report_json': '{}'}, 'report_update': {}}


def selected(tool):
    return {'selection': {'kind': 'tool', 'tool': tool, 'arguments': {}}, 'report_update': {}}


class PartialDecisionReached(Exception):
    """End only this engineering run after the real next decision is saved."""


class EpisodeRun:
    """Actual Workflow with a scripted parent/launch/API/results decision path."""

    def __init__(self, store, directory, query, selection, form, *, partial=False,
                 following_selection=None, redeliver=False, scope=None):
        self.store = store
        self.scope = deepcopy(scope) if scope is not None else {
            'subject_refs': store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']}
        self.query, self.selection, self.form = deepcopy(query), deepcopy(selection), deepcopy(form)
        self.partial = partial
        self.following_selection = deepcopy(following_selection)
        self.redeliver = redeliver
        self.api_assignment = {'version': 'api_service_assignment_v1', 'resource_id': 'bvbrc',
            'service': 'bvbrc_data', 'request': self.query, 'endpoint': 'usable_handoff',
            'constraints': {'allowed_resource_ids': ['bvbrc'], 'allowed_kinds': ['api']}}
        self.launch_assignment = {'version': 'execution_launch_assignment_v1',
            'requests': {'bvbrc': self.api_assignment}, 'immutable_input_versions': [],
            'constraints': {'allowed_resource_ids': ['bvbrc'], 'allowed_kinds': ['api']}}
        self.calls, self.contexts = {}, []
        self.root_calls = 0
        self.handoff = None
        self.parent_after_result = None
        self.result_next_decision = None
        self.received_forms = []
        factory = ExecutionServiceFactory(RESOURCES, {}, 3, 2, .5)

        def controller(path, initial):
            def root_estimate(history, parameters, contexts):
                count = 4 if self.following_selection is not None else 3
                return YieldEstimate(len(history), NumericBand.exact(
                    0 if len(history) >= count else 1), parameters,
                    {'fixture': 'engineering_root_continuation_only'})
            return YieldController(str(path), initial, 0, YieldParameters(100, 50),
                estimate_with_context=root_estimate if path[-1][0] == 'annotation' else None)

        self.workflow = Workflow(store, ToolRegistry(store), self, directory, 'bvbrc-episode-fixture',
            controller_factory=controller, project_credit=lambda *_: 0,
            episode_service_factory=factory, episode_service_binding=factory.as_record(),
            episode_service_inputs='actual_tool_registry_v1', annotation_child_roles=('launch', 'results'),
            episode_record_receipts=True, initial_known_record_refs=[])
        self.episode = self.workflow.build('annotation', 'root',
            'Acquire selected native molecular measurements for the supplied sequence', self.scope)

    async def complete(self, episode_id, role, instructions, current, schema):
        self.calls[episode_id] = self.calls.get(episode_id, 0) + 1
        self.contexts.append((episode_id, deepcopy(current)))
        execution = current.get('execution_assignment', {})
        version = execution.get('version')
        if version == 'execution_results_assignment_v1' and self.calls[episode_id] == 2 and self.partial:
            self.result_next_decision = deepcopy(current)
            raise PartialDecisionReached
        assert current.get('feedback') is None, current.get('feedback')
        if version == 'execution_launch_assignment_v1':
            assert self.calls[episode_id] == 1, 'Launch should close at its actual handoff endpoint'
            assert execution == self.launch_assignment
            assert [r['resource_id'] for r in current['execution_resource_capabilities']] == ['bvbrc']
            return child('launch_api', self.api_assignment, self.scope, handoff_form())
        if version == 'api_service_assignment_v1':
            assert self.calls[episode_id] == 1, 'API response must supply one completed command'
            assert execution == self.api_assignment
            return selected('api.bvbrc.data.query')
        if version == 'execution_results_assignment_v1':
            assert self.calls[episode_id] == 1, 'Successful requested result should immediately close'
            assert execution['selector'] in [self.selection, self.following_selection]
            return selected('api.bvbrc.data.result')
        self.root_calls += 1
        if self.root_calls == 1:
            assert current['received_bvbrc_values'] == []
            return child('launch', self.launch_assignment, self.scope, handoff_form())
        if self.root_calls == 2:
            received = current['child_reports'][-1]
            assert received['completed'] is True
            self.handoff, = received['references']
            return child('results', {'version': 'execution_results_assignment_v1',
                'handoff_ref': self.handoff, 'selector': self.selection}, self.scope, self.form)
        self.received_forms.append(deepcopy(current['child_reports'][-1]))
        self.parent_after_result = deepcopy(current)
        if self.root_calls == 3 and self.redeliver:
            return {'selection': {'kind': 'redeliver_report',
                'delivery_ref': current['report_deliveries'][-1]['delivery_ref'],
                'purpose': 'Return the requested typed original source measurements',
                'schema_json': json.dumps(self.form)}, 'report_update': {}}
        if self.root_calls == 3 and self.following_selection is not None:
            return child('results', {'version': 'execution_results_assignment_v1',
                'handoff_ref': self.handoff, 'selector': self.following_selection}, self.scope, self.form)
        # A real selected wait lets the parent receive and save its next decision
        # context. It is one explicitly zero-gain engineering action, not a
        # required workflow stage or a resource-completion turn.
        return {'selection': {'kind': 'wait', 'condition': {'version': 'event_condition_v1',
            'events': [], 'reconsider_at': datetime.now(timezone.utc).isoformat()}}, 'report_update': {}}

    async def release(self, episode_id):
        pass

    def run(self):
        async def run():
            record = await self.episode.run_async(self.workflow.context)
            await self.episode.build_result(record)
            return record
        record = asyncio.run(run())
        self.archive = json.loads(''.join(iter_json(record.as_record())))
        return self.archive

    def context(self, episode_id):
        saved = self.workflow.journal.row('runtime_episodes', episode_id)
        request, path = json.loads(saved['request']), tuple(map(tuple, json.loads(saved['path'])))
        assert EpisodeRef(self.workflow.run_id, path).episode_id == episode_id
        return BindingContext(self.workflow.run_id, episode_id, path[-1][0], path,
            request['message']['scope'], request['message'].get('episode_assignment', {}), request)

    @property
    def api(self):
        return self.workflow.episode_bindings.for_role('results').api_execution

    def rows(self, table, episode_id=None):
        query = 'SELECT * FROM ' + table + ' WHERE run_id=?'
        operands = [self.workflow.run_id]
        if episode_id is not None:
            query += ' AND episode_id=?'
            operands.append(episode_id)
        return [dict(row) for row in self.store.db.execute(query, operands)]
