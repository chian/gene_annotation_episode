"""Full caller/Workflow consumers with explicit fixture decisions and HTTP.

No configured model or public service runs. Ordinary shared episodes, original
typed forms, received records, separate credit channels and later contexts are
real. This first consumer deliberately uses in-process child execution; durable
worker reconstruction is tested separately.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.assembled_service_setup import bind_assembled_services_with_public_search
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.resource_episodes import LAUNCH_VERSION, RESULTS_VERSION
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.tools import ToolRegistry
from test_assembled_service_setup import PUBLICATION, RETRIEVAL, ROOT_ROLES
from test_hmmer_api_operations import registry
from test_hmmer_api_progress import local_service
from test_resource_receipt_runtime import FORM, own, resource_episode, observations
from test_resource_service_setup import resources
from test_recursive_monitoring import assignment as monitor_assignment
from test_runtime import FixtureController, ScriptedProvider, obj


HANDOFF = 3.25
ACQUIRED = .375
MONITOR = .5


def host(r, directory, client, *, script, counts=None):
    problem = r.store.create_problem(raw_sequence='MKWAA', molecule='protein')
    subject = problem['subject_refs'][0]
    r.scope = {'subject_refs': [subject]}
    r.journal = Journal(r.store, r.run_id)
    r.launch = {'version': LAUNCH_VERSION,
        'job_request': {'provider': 'hmmer', 'subject_ref': subject,
            'algorithm': 'phmmer', 'database': 'fixture', 'parameters': {}, 'page_size': 2},
        'immutable_input_versions': [{'reference': subject, 'version': None,
            'content_sha256': hashlib.sha256(b'MKWAA').hexdigest()}],
        'constraints': {'allowed_kinds': ['api'], 'cpu': None},
        'resource_selection': None, 'software_knowledge_refs': [], 'resource_knowledge_refs': []}
    tools = ToolRegistry(r.store, clients=client)
    bound_registry = registry(client)
    applications, controllers = [], {}

    def services(store, *, run_id, directory, job_episodes, resource_estimator,
                 tool_catalog, tool_registry):
        assert tool_registry is tools
        assert set(tool_catalog) == set(tools.catalog())
        value = bind_assembled_services_with_public_search(store, run_id=run_id,
            directory=directory, job_episodes=job_episodes, resource_estimator=resource_estimator,
            source_directory=PUBLICATION, tool_catalog=tool_catalog,
            tool_retrieval=deepcopy(RETRIEVAL), scientific_child_roles=ROOT_ROLES,
            handoff_unit=HANDOFF, acquired_record_unit=ACQUIRED,
            monitoring_information_unit=MONITOR, literature_outcome_page_size=7,
            monitor_outcome_page_size=13, log_window_bytes=123,
            log_roles=('native_stderr',), public_search_registry=bound_registry,
            tool_registry=tool_registry)
        applications.append(value)
        return value

    limits = {'launch': 2, 'launch_api': 2, 'results': 2, 'monitor': 2, **(counts or {})}

    def controller(path, initial):
        value = FixtureController(str(path), initial, limits.get(path[-1][0], 1))
        controllers[path] = value
        return value

    provider = ScriptedProvider(script)
    workflow = Workflow(r.store, tools, provider, directory, r.run_id,
        controller_factory=controller, project_credit=lambda *_: 0,
        job_episodes=r.homology, resource_estimator=r.estimator,
        episode_service_factory=services, episode_service_binding={
            'version': 'explicit_api_connected_fixture_v1', 'registry': bound_registry},
        episode_service_inputs='actual_tool_registry_v1',
        episode_record_receipts=True, initial_known_record_refs=[subject],
        annotation_child_roles=ROOT_ROLES)
    owner = workflow.build('annotation', 'unexecuted_owner', 'Exercise only fixture custody', r.scope)
    return SimpleNamespace(workflow=workflow, owner=owner, provider=provider,
        controllers=controllers, applications=applications, registry=bound_registry)


def api_child(r, workflow):
    binding = workflow.episode_bindings.for_role('launch')
    adapter = next(a for a in binding.adapters.values() if a.capability()['kind'] == 'api')
    return {'selection': {'kind': 'episode_child', 'role': 'launch_api',
        'goal': 'Establish the original selected fixture receiving interfaces',
        'scope': r.scope, 'purpose': 'Return only the original checked handoff',
        'schema_json': json.dumps(FORM), 'initial_report_json': '{}',
        'assignment': {**deepcopy(r.launch), 'resource_selection': adapter.information.selection()}},
        'report_update': {}}


def test_actual_caller_child_form_receipt_parent_followup_and_external_monitor(resources, tmp_path):
    r = resources
    with local_service() as (service, client):
        seen_followup = []

        def choose_child(_context):
            return api_child(r, h.workflow)

        def followup(context):
            assert context['current_credit'] == HANDOFF
            assert context['last_local_outcome'] is not None
            seen_followup.append(deepcopy(context['last_local_outcome']))
            return own('resource.capabilities')

        h = host(r, tmp_path/'connected', client, script=[choose_child,
            own('api_search.submit', retry_of=None), own('api_search.check_handoff'), followup,
            own('progress.observe', requested_fields=['execution_status', 'result_available']),
            own('progress.observe', requested_fields=['execution_status', 'result_available'])])
        assert h.workflow.episode_application_services_binding['version'] == 'episode_application_services_v3'
        parent, boundary = resource_episode(h, r, 'launch', r.launch)
        record = asyncio.run(parent.run_async(boundary))
        asyncio.run(parent.build_result(record))
        assert record.units_consumed == 2 and len(seen_followup) == 1
        parent_form = json.loads(r.journal.row('runtime_forms', parent.source.episode_id)['form'])
        handoff = parent_form['handoff']
        assert handoff['execution_handle'].startswith('provider_job_')
        assert handoff['resource_selection']['capability_binding_ref'] == h.registry['registry_ref']
        assert [row[0] for row in service.calls] == ['POST', 'GET']
        child = next(row for row in r.store.db.execute('SELECT episode_id,path FROM runtime_episodes')
            if json.loads(row['path'])[-1][0] == 'launch_api')
        child_form = json.loads(r.journal.row('runtime_forms', child['episode_id'])['form'])
        assert child_form == parent_form
        child_path = tuple(tuple(value) for value in json.loads(child['path']))
        assert h.controllers[child_path].scores == [0, HANDOFF]
        assert h.controllers[parent.source.path].scores == [HANDOFF, 0]
        proof_refs = [ref for ref in h.workflow.record_selection(parent.source.episode_id)['known_record_refs']
            if r.store.get(ref).get('provider') == 'episode.api_search_handoff']
        assert len(proof_refs) == 1
        assert r.store.count('assessment') == r.store.count('annotation') == 0

        sources = h.workflow.report_sources('monitor')
        schema = obj({'updates': sources['monitoring_progress_refs']['report_schema'],
            'state': sources['monitoring_execution_state']['report_schema'],
            'ready': sources['monitoring_result_available']['report_schema']})
        monitor, monitoring_boundary = resource_episode(h, r, 'monitor',
            monitor_assignment(handoff['execution_handle'], fields=('execution_status', 'result_available')),
            schema=schema)
        record = asyncio.run(monitor.run_async(monitoring_boundary))
        asyncio.run(monitor.build_result(record))
        returned = json.loads(r.journal.row('runtime_forms', monitor.source.episode_id)['form'])
        assert returned['state'] == 'pending' and returned['ready'] is False
        assert len(returned['updates']) == 1
        assert h.controllers[monitor.source.path].scores == [MONITOR, 0]
        assert len(observations(r, monitor.source.episode_id)) == 2
        assert [row[0] for row in service.calls] == ['POST', 'GET', 'GET', 'GET']
        assert r.store.count('assessment') == r.store.count('annotation') == 0


def test_explicit_registry_reconstruction_and_foreign_resource_routing(resources, tmp_path):
    r = resources
    with local_service() as (service, client):
        h = host(r, tmp_path/'reconstruction', client, script=[])
        binding = h.workflow.episode_bindings.for_role('launch_api')
        api = next(a for a in binding.adapters.values() if a.capability()['kind'] == 'api')
        native = next(a for a in binding.adapters.values() if a.capability()['kind'] == 'local')
        parent, _ = resource_episode(h, r, 'launch', r.launch)
        context = h.workflow.binding_context(parent.source)
        assigned = binding.prepare_assignment(context, 'launch_api',
            {**deepcopy(r.launch), 'resource_selection': api.information.selection()},
            r.scope, r.run_id+':assigned')
        child, _ = resource_episode(h, r, 'launch_api', assigned)
        bound = h.workflow.binding_context(child.source)
        assert native._legacy(bound) is None
        assert native.resolve(bound, 'homology.status.v1', 'resource_interface') is False
        native.validate_report(bound, {}, obj({}))
        assert h.workflow.source_credit_view(child.source)['credit'] == 0
        assert service.calls == []
        reopened = h.workflow.services.public_search_ports(h.registry)
        assert reopened.operations.open_order(assigned['adapter_assignment']['job_ref']) == assigned['adapter_assignment']
        changed = {**h.registry, 'client_binding_sha256': '0'*64}
        with pytest.raises(Exception) as error:
            h.workflow.services.public_search_ports(changed)
        assert getattr(error.value, 'failure', {})['code'] == 'identity_conflict'
        assert service.calls == [] and not h.provider.contexts
