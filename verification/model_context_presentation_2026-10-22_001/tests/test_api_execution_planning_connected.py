"""Real scientific precommission forecast consumers with explicit fixture choices.

Only loopback provider fixtures run. The fixed controller counts and semantic
retrieval responses are engineering operands, not configured-model science.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.api_timing_records import ApiTimingBinding
from gene_annotation_episode.assembled_service_setup import (
    bind_assembled_services_with_public_search_timing_planning,
)
from gene_annotation_episode.communication import ReportBoundaryError, plain
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.run_statistics import RunHistory
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.tools import ToolRegistry
from test_api_timing_connected import reported_service
from test_assembled_service_setup import PUBLICATION, RETRIEVAL, ROOT_ROLES
import test_hmmer_api_connected as connected
from test_resource_receipt_runtime import FORM, observations, own
from test_resource_service_setup import resources
from test_runtime import FixtureController, ScriptedProvider, obj
from test_scientific_process_library import independent_source, write


MARKER = {'version': 'hmmer_api_execution_planning_v1',
          'callable': 'execution.estimate', 'target': 'public.hmmer.search'}


class SemanticFixtureProvider(ScriptedProvider):
    roles = {'FAST': deepcopy(RETRIEVAL['model'])}

    def __init__(self, script, names):
        super().__init__(script)
        self.names = names
        self.retrieval_contexts = []

    async def complete(self, episode_id, role, instructions, context, output_schema):
        if role == 'FAST':
            assert 'Retrieve actual callable tools' in instructions
            self.retrieval_contexts.append(deepcopy(context))
            return {'tools': list(self.names)}
        return await super().complete(episode_id, role, instructions, context, output_schema)


def synthetic_ap_source(directory):
    """Retain only synthetic A/P metadata; no production support adoption."""
    independent_source(directory)
    index = json.loads((directory / 'index.json').read_text())
    index['slots'] = [r for r in index['slots'] if r['slot'] != 'tools']
    index['entries'] = [r for r in index['entries'] if r['slot'] != 'tools']
    write(directory / 'index.json', index)
    table = json.loads((directory / 'option_sources.json').read_text())
    table['rows'] = [r for r in table['rows'] if not r['option_id'].startswith('T')]
    write(directory / 'option_sources.json', table)
    (directory / 'entries/T01.json').unlink()
    return directory


def planning_host(r, directory, client, *, script, counts=None,
                  source_directory=None, provider=None):
    problem = r.store.create_problem(raw_sequence='MKWAA', molecule='protein')
    subject = problem['subject_refs'][0]
    r.scope = {'subject_refs': [subject]}
    r.journal = Journal(r.store, r.run_id)
    r.launch = {'version': 'resource_launch_assignment_v1',
        'job_request': {'provider': 'hmmer', 'subject_ref': subject, 'algorithm': 'phmmer',
                        'database': 'fixture', 'parameters': {}, 'page_size': 2},
        'immutable_input_versions': [{'reference': subject, 'version': None,
                                     'content_sha256': hashlib.sha256(b'MKWAA').hexdigest()}],
        'constraints': {'allowed_kinds': ['api'], 'cpu': None},
        'resource_selection': None, 'software_knowledge_refs': [], 'resource_knowledge_refs': []}
    tools = ToolRegistry(r.store, clients=client)
    registry = connected.registry(client)
    history_path = directory.parent / 'reported-history.sqlite'
    RunHistory(history_path).close()
    timing = ApiTimingBinding(ledger_path=directory.parent / 'api-ledger.sqlite',
        history_path=history_path, resource_id=registry['resource_id'],
        monitoring_information_unit=connected.MONITOR)
    r.estimator = ResourceToolEstimator.with_reported_results()
    applications, controllers = [], {}

    def services(store, *, run_id, directory, job_episodes, resource_estimator,
                 tool_catalog, tool_registry):
        assert tool_registry is tools
        value = bind_assembled_services_with_public_search_timing_planning(store,
            run_id=run_id, directory=directory, job_episodes=job_episodes,
            resource_estimator=resource_estimator, tool_registry=tool_registry,
            tool_catalog=tool_catalog, source_directory=source_directory or PUBLICATION,
            tool_retrieval=deepcopy(RETRIEVAL), scientific_child_roles=ROOT_ROLES,
            handoff_unit=connected.HANDOFF, acquired_record_unit=connected.ACQUIRED,
            monitoring_information_unit=connected.MONITOR, literature_outcome_page_size=7,
            monitor_outcome_page_size=13, log_window_bytes=123, log_roles=('native_stderr',),
            public_search_registry=registry, api_timing=timing)
        applications.append(value)
        return value

    limits = {'annotation': 3, 'scientific_process': 2, 'launch': 1,
              'launch_api': 2, 'results': 2, **(counts or {})}

    def controller(path, initial):
        value = FixtureController(str(path), initial, limits.get(path[-1][0], 1))
        controllers[path] = value
        return value

    provider = provider or ScriptedProvider(script)
    workflow = Workflow(r.store, tools, provider, directory, r.run_id, controller,
        project_credit=lambda *_args, **_kwargs: 0,
        job_episodes=r.homology, resource_estimator=r.estimator,
        episode_service_factory=services, episode_service_binding={
            'version': 'explicit_api_planning_connected_fixture_v1',
            'registry': registry, 'api_timing': timing.as_record(),
            'api_execution_planning': deepcopy(MARKER)},
        episode_service_inputs='actual_tool_registry_v1', episode_record_receipts=True,
        initial_known_record_refs=[subject], annotation_child_roles=ROOT_ROLES)
    root = workflow.build('annotation', 'root', 'Exercise original scientific planning inputs', r.scope)
    return SimpleNamespace(workflow=workflow, owner=root, tools=tools, provider=provider,
        controllers=controllers, applications=applications, timing=timing, registry=registry)


def estimate_arguments(h, r):
    return {'tool': 'public.hmmer.search',
        'arguments': {k: v for k, v in r.launch['job_request'].items() if k != 'provider'},
        'resource_selection': next(a for a in h.workflow.episode_bindings.for_role('launch').adapters.values()
                 if a.capability()['kind'] == 'api').information.selection(),
        'constraints': deepcopy(r.launch['constraints']),
        'immutable_input_versions': deepcopy(r.launch['immutable_input_versions'])}


def close(h):
    record = asyncio.run(h.owner.run_async(h.workflow.context))
    asyncio.run(h.owner.build_result(record))
    return record


def test_scientific_forecast_precedes_first_launch_and_original_survives_learning(resources, tmp_path):
    r = resources
    initial, returned, seen = [], [], []
    with reported_service() as (http, client):
        def estimate_first(context):
            assert context['requested_form'] is None
            assert 'api_execution_proposal' not in context
            assert not http.calls
            return own('execution.estimate', **estimate_arguments(h, r))

        def first_launch(context):
            proposal = context['api_execution_proposal']
            assert proposal['arguments'] == estimate_arguments(h, r)['arguments']
            forecast, = context['api_reported_execution_forecasts']
            assert forecast['status'] == 'no_matching_history'
            assert forecast['reported_result_support'] == {'reported_result_count': 0}
            assert proposal['api_reported_execution_forecasts'] == [forecast]
            initial.append(deepcopy(proposal))
            assert not http.calls
            assert r.store.db.execute('SELECT count(*) FROM provider_jobs').fetchone()[0] == 0
            assert r.store.db.execute("SELECT count(*) FROM runtime_actions WHERE "
                "json_extract(action,'$.kind')='episode_child'").fetchone()[0] == 0
            return {'selection': {'kind': 'episode_child', 'role': 'launch',
                'goal': 'Establish explicitly proposed fixture execution', 'scope': r.scope,
                'purpose': 'Return only the original checked handoff',
                'schema_json': json.dumps(FORM), 'initial_report_json': '{}',
                'assignment': deepcopy(r.launch)}, 'report_update': {}}

        def api_child(_context):
            return connected.api_child(r, h.workflow)

        def request_results(context):
            assert context['requested_form'] is None
            handoff = context['child_reports'][0]['handoff']
            schema = obj({'timing': deepcopy(h.workflow.report_sources('results')[
                'api_execution_measurements']['report_schema'])})
            return {'selection': {'kind': 'episode_child', 'role': 'results',
                'goal': 'Acquire the two selected fixture pages', 'scope': r.scope,
                'purpose': 'Return the original source-qualified duration',
                'schema_json': json.dumps(schema), 'initial_report_json': '{}',
                'assignment': {'version': 'resource_results_assignment_v1', 'handoff': handoff,
                    'requested_data_selector': {'version': 'public_search_result_selector_v1',
                        'provider': 'hmmer', 'first_page': 1, 'last_page': 2, 'page_size': 2}}},
                'report_update': {}}

        def estimate_after_return(context):
            fact, = context['child_reports'][-1]['timing']
            returned.append(deepcopy(fact))
            assert fact['elapsed_seconds'] == http.elapsed
            assert context['current_credit'] == 0
            assert context['monitoring_information_credit'] == connected.MONITOR
            assert context['api_execution_proposal'] == initial[0]
            return own('execution.estimate', **estimate_arguments(h, r))

        def use_new_forecast(context):
            forecast, = context['api_reported_execution_forecasts']
            assert forecast['reported_result_support'] == {'reported_result_count': 1}
            assert forecast['expected_total_seconds'] == http.elapsed
            assert forecast['outcome_support'] is None and forecast['elapsed_seconds'] is None
            assert context['api_execution_proposal'] != initial[0]
            seen.append(deepcopy(context['api_execution_proposal']))
            return own('episode.history', view='records', decision_indices=[0])

        h = planning_host(r, tmp_path / 'run', client, counts={'annotation': 5}, script=[
            estimate_first, first_launch, api_child, own('api_search.submit', retry_of=None),
            own('api_search.check_handoff'), request_results, own('api_search.acquire', page=1),
            own('api_search.acquire', page=2), estimate_after_return, use_new_forecast])
        planner = h.tools.api_execution_planner
        adapter = next(a for a in h.workflow.episode_bindings.for_role('launch').adapters.values()
                       if a.capability()['kind'] == 'api')
        assert planner.ports is adapter.ports
        assert planner.timing is adapter.timing is h.workflow.api_timing_reader.ledger
        closed = close(h)
        assert closed.units_consumed == 5 and len(returned) == len(seen) == 1
        assert [row[0] for row in http.calls] == ['POST', 'GET', 'GET', 'GET']
        assert h.controllers[h.owner.source.path].scores == [0] * 5
        assert len(observations(r, h.owner.source.episode_id)) == 5
        assert r.store.count('assessment') == r.store.count('annotation') == 0
        first_action = json.loads(r.journal.row('runtime_actions', h.owner.source.episode_id, 0)['result'])
        assert first_action['result'] == initial[0]
        assert first_action['api_reported_execution_forecasts'] == initial[0]['api_reported_execution_forecasts']
        saved = json.loads(r.journal.row('runtime_model_calls', h.owner.source.episode_id, 1)['request'])
        assert saved['context']['api_execution_proposal'] == initial[0]
        for value in initial[0]['api_reported_execution_forecasts']:
            assert value['job_ref'] is None and value['sample_ref'] is None
        assert h.workflow.source_credit_view(h.owner.source)['monitoring_information_credit'] == connected.MONITOR


def test_semantic_actual_map_constructed_child_returns_only_declared_original_forecast(resources, tmp_path):
    r = resources
    source = synthetic_ap_source(tmp_path / 'synthetic-options')
    selected, child_contexts, forms = [], [], []
    with reported_service() as (http, client):
        def commission(context):
            retrieval = context['last_local_outcome']['result']
            assert retrieval['tools'] == ['execution.estimate', 'sequence.inspect']
            selected.extend(retrieval['tools'])
            library = h.workflow.scientific_process_binding.library
            schema = obj({'forecasts': deepcopy(h.workflow.report_sources('scientific_process')[
                'api_reported_execution_forecasts']['report_schema'])})
            return {'selection': {'kind': 'episode_child', 'role': 'scientific_process',
                'goal': 'Assess this proposed search using original timing support', 'scope': r.scope,
                'purpose': 'Return only the requested original forecast',
                'schema_json': json.dumps(schema), 'initial_report_json': '{}',
                'assignment': {'selection': {'version': 'scientific_process_selection_v2',
                    'annotation_ref': library.reference('A01'), 'thought_ref': library.reference('P01'),
                    'tools': list(selected)}, 'evidence_refs': r.scope['subject_refs'],
                    'constraints': {'target_only': True}, 'context': {'fixture': 'prospective'}}},
                'report_update': {}}

        def child_estimate(context):
            assert 'scientific_process' in context
            assert context['scientific_process']['selection']['tools'] == selected
            names = {entry['name'] for entry in context['tools']}
            assert {'execution.estimate', 'sequence.inspect'} <= names
            assert 'public.hmmer.search' not in names
            child_contexts.append(deepcopy(context))
            return own('execution.estimate', **estimate_arguments(h, r))

        def child_later(context):
            assert context['api_execution_proposal']['arguments'] == estimate_arguments(h, r)['arguments']
            assert context['api_reported_execution_forecasts'][0]['reported_result_support'] == {
                'reported_result_count': 0}
            child_contexts.append(deepcopy(context))
            return own('episode.history', view='records', decision_indices=[0])

        def receive(context):
            form, = context['child_reports']
            assert set(form) == {'forecasts'}
            assert form['forecasts'] == child_contexts[-1]['api_reported_execution_forecasts']
            assert 'api_execution_proposal' not in context
            assert context['current_credit'] == context['monitoring_information_credit'] == 0
            forms.append(deepcopy(form))
            return own('episode.history', view='index')

        provider = SemanticFixtureProvider([own('process.tools', investigation=
            'Obtain duration expectations for proposed remote protein homology work'), commission,
            child_estimate, child_later, receive], ['execution.estimate', 'sequence.inspect'])
        h = planning_host(r, tmp_path / 'run', client, script=[], provider=provider,
                          source_directory=source)
        closed = close(h)
        assert closed.units_consumed == 3 and len(forms) == 1
        assert not http.calls and r.store.db.execute('SELECT count(*) FROM provider_jobs').fetchone()[0] == 0
        assert len(provider.retrieval_contexts) == 1
        actual = next(row for row in provider.retrieval_contexts[0]['catalog']
                      if row['name'] == 'execution.estimate')
        assert actual == {'name': 'execution.estimate', **h.tools.catalog()['execution.estimate']}
        row = r.store.db.execute("SELECT * FROM runtime_episodes WHERE "
            "json_extract(path,'$[#-1][0]')='scientific_process'").fetchone()
        child_id = row['episode_id']
        assert len(observations(r, child_id)) == 2
        original_count = r.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]
        schema = json.loads(row['request'])['report_contract']['measurements']['schema']
        h.workflow.receive_form(h.owner.source, forms[0], schema, 1, redelivery=True)
        assert r.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == original_count
        bad = deepcopy(forms[0])
        bad['forecasts'][0]['expected_total_seconds'] = 99
        with pytest.raises((ReportBoundaryError, ValueError)):
            h.workflow.validate_report(bad, r.scope, schema=schema, source=h.owner.source)
        assert h.workflow.source_credit_view(h.owner.source)['monitoring_information_credit'] == 0
