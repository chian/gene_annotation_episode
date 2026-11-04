"""Real service contracts through the shared episode loop; no external requests.

Only HTTP responses and the scientific root/monitor's continuation are fixtures.
Resource endpoints, typed forms, result selectors and completion proofs use the
actual application implementations. These are engineering checks, not annotation
demonstrations or production continuation policies.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from method_loop.archive import iter_json

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode import independent_execution as reconstruction
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.providers import ModelConnection
from gene_annotation_episode.runtime import Workflow, assemble_workflow, run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_configuration import build_tools
from gene_annotation_episode.tools import ToolRegistry
from test_execution_episodes_family import context, launch_assignment, select, selection
from test_execution_wiring import child, controller, form
from test_practical_reconstruction import BeforeModel
from test_practical_runtime import selected
from test_public_search import Client


def resources():
    return json.loads((Path(__file__).parents[1]/'examples'/'api_services.json').read_text())


def assignment(resource_id, service, request):
    return {'version': 'api_service_assignment_v1', 'resource_id': resource_id,
        'service': service, 'request': deepcopy(request), 'endpoint': 'usable_handoff',
        'constraints': {}}


def uniprot_entry(accession):
    return {'primaryAccession': accession, 'sequence': {'value': 'MACDEFGH'},
        'organism': {'taxonId': 511145, 'scientificName': 'Escherichia coli'},
        'proteinDescription': {'recommendedName': {'fullName': {
            'value': 'Synthetic source label; not an annotation of the target'}}}}


class PublicResponses(Client):
    def __init__(self):
        super().__init__()
        self.requests = []

    def _response(self, operation, body, arguments, headers=None):
        self.requests.append((operation, deepcopy(arguments)))
        return SourceSnapshot('uniprot', 'https://rest.uniprot.org/uniprotkb/'+operation,
            arguments, f'2026-10-23T12:00:{len(self.requests):02d}+00:00',
            json.dumps(body).encode(), 'application/json', {'response': {
                'status': 200, 'headers': headers or {}},
                'representation': 'controlled_native_service_response'})

    def uniprot_record(self, accession):
        return self._response(accession, uniprot_entry(accession), {'accession': accession})

    def uniprot_search(self, query, *, size=10, cursor=None):
        arguments = {'query': query, 'size': size, **({'cursor': cursor} if cursor else {})}
        headers = {'x-total-results': '2', 'x-uniprot-release': 'fixture-release'}
        if cursor is None:
            headers['link'] = ('<https://rest.uniprot.org/uniprotkb/search?'
                'query=gene%3AybhP&cursor=actual-next-cursor&size=1>; rel="next"')
        return self._response('search', {'results': [uniprot_entry(
            'P12345' if cursor is None else 'P12346')]}, arguments, headers)


@pytest.fixture
def service_responses(monkeypatch):
    from gene_annotation_episode.api_bvbrc import BVBRCDataClient
    client = PublicResponses()
    bvbrc_calls = []

    def bvbrc_query(self, request):
        bvbrc_calls.append(deepcopy(request))
        offset, limit = request.get('offset', 0), request.get('limit', 25)
        rows = [{'feature_id': f'fig|511145.12.peg.{offset+i+1}',
            'genome_id': '511145.12', 'gene': 'ybhP',
            'product': 'Synthetic source annotation', 'aa_sequence': 'MACDEFGH'}
            for i in range(min(limit, 2))]
        content_range = f'items {offset}-{offset+len(rows)}/4'
        return SourceSnapshot('bvbrc_data', 'https://www.bv-brc.org/api/genome_feature/',
            request, f'2026-10-23T13:00:{len(bvbrc_calls):02d}+00:00',
            json.dumps(rows).encode(), 'application/json', {'status': 200,
                'headers': {'content-range': content_range},
                'header_items': [['Content-Range', content_range]]})

    monkeypatch.setattr(BVBRCDataClient, 'query', bvbrc_query)
    return client, bvbrc_calls


CASES = [
    ('uniprot', 'uniprot', {'operation': 'record', 'accession': 'P12345'},
        {}, 'api.uniprot.record', 'api.uniprot.collect'),
    ('uniprot', 'uniprot', {'operation': 'search', 'query': 'gene:ybhP', 'size': 1},
        {'cursor': 'actual-next-cursor', 'size': 1}, 'api.uniprot.search', 'api.uniprot.collect'),
    ('bvbrc', 'bvbrc_data', {'collection': 'genome_feature',
        'filters': [{'field': 'gene', 'operator': 'eq', 'value': 'ybhP'}],
        'fields': ['feature_id', 'genome_id', 'gene', 'product', 'aa_sequence'],
        'offset': 0, 'limit': 2}, {'offset': 2, 'limit': 2}, 'api.bvbrc.query', 'api.bvbrc.result'),
]


@pytest.mark.parametrize('resource_id,service,api_request,selector,launch_tool,result_tool', CASES)
def test_shared_loop_service_handoff_monitor_native_result_and_terminal_zero(
        tmp_path, service_responses, resource_id, service, api_request, selector,
        launch_tool, result_tool):
    client, bvbrc_calls = service_responses
    with Store(tmp_path/'state') as store:
        target, = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']
        scope = {'subject_refs': [target]}
        requested = assignment(resource_id, service, api_request)
        factory = ExecutionServiceFactory(resources(), {}, 3, 2, .5)
        launch = launch_assignment({resource_id: requested})
        handoff_form, result_form = form('execution_handoff_refs'), form('execution_result_refs')
        from gene_annotation_episode.episode_monitoring import MonitorEpisodes
        monitor_form = {'type': 'object', 'properties': {'progress': MonitorEpisodes(None)
            .fact_sources('monitor')['monitoring_progress_refs']['report_schema']},
            'required': ['progress'], 'additionalProperties': False}

        class Choices:
            def __init__(self):
                self.root_count = 0
                self.handoff = None
                self.launch_rows = None
                self.calls = {}

            async def complete(self, episode_id, role, instructions, current, schema):
                assert current.get('feedback') is None, current.get('feedback')
                execution = current.get('execution_assignment', {})
                self.calls[episode_id] = self.calls.get(episode_id, 0) + 1
                if execution or 'monitor_assignment' in current:
                    assert self.calls[episode_id] == 1, (
                        'This single-action fixture should have reached its real endpoint',
                        execution, current.get('last_local_outcome'))
                if execution.get('version') == 'execution_launch_assignment_v1':
                    assert execution == launch
                    assert {row['resource_id'] for row in
                        current['execution_resource_capabilities']} == set(resources())
                    blast = next(row for row in current['execution_resource_capabilities']
                        if row['resource_id'] == 'ncbi-blast')
                    assert blast['api_configuration_facts'] == {
                        'ncbi_contact_configured': False, 'provider_rate_state_configured': False}
                    return child('launch_api', requested, scope, handoff_form)
                if execution.get('version') == 'api_service_assignment_v1':
                    assert execution == requested
                    assert service in instructions
                    return selected(launch_tool)
                if 'monitor_assignment' in current:
                    return selected('progress.observe', {'requested_fields': [
                        'execution_status', 'measurements', 'log_windows']})
                if execution.get('version') == 'execution_results_assignment_v1':
                    assert execution['selector'] == selector
                    return selected(result_tool)
                self.root_count += 1
                if self.root_count == 1:
                    return child('launch', launch, scope, handoff_form)
                if self.root_count == 2:
                    received = current['child_reports'][-1]
                    assert received['completed'] is True
                    assert received['yield']['expected_next_gain'] == NumericBand.exact(0).as_record()
                    self.handoff, = received['references']
                    self.launch_rows = [dict(row) for row in store.db.execute(
                        "SELECT episode_id,decision_index,action,result,credit FROM runtime_actions "
                        "WHERE run_id=? AND json_extract(action,'$.tool')=?",
                        (workflow.run_id, launch_tool))]
                    return child('monitor', {'version': 'monitor_assignment_v1',
                        'target_handle': self.handoff,
                        'requested_fields': ['execution_status', 'measurements', 'log_windows'],
                        'known_progress_refs': [], 'permitted_committed_record_types': []},
                        scope, monitor_form)
                assert self.root_count == 3
                progress_ref, = current['child_reports'][-1]['progress']
                progress = workflow.progress_provider.read_progress(progress_ref, scope)
                assert progress['execution_status']['version'] == 'resource_execution_status_v1'
                assert progress['execution_status']['lifecycle_state'] == 'returned'
                assert progress['result_available'] is True
                assert progress['execution_status']['resource_id'] == resource_id
                assert progress['execution_status']['native']['state'] == 'completed'
                return child('results', {'version': 'execution_results_assignment_v1',
                    'handoff_ref': self.handoff, 'selector': selector}, scope, result_form)

            async def release(self, episode_id):
                pass

        choices = Choices()
        workflow = Workflow(store, ToolRegistry(store, clients=client), choices, tmp_path/'run',
            'connected-service-'+service+'-'+api_request.get('operation', 'query'),
            controller_factory=controller, project_credit=lambda *_: 0,
            episode_service_factory=factory, episode_service_binding=factory.as_record(),
            episode_service_inputs='actual_tool_registry_v1',
            annotation_child_roles=('launch', 'monitor', 'results'),
            episode_record_receipts=True, initial_known_record_refs=[])
        episode = workflow.build('annotation', 'root', 'Acquire the requested source evidence', scope)

        async def run():
            record = await episode.run_async(workflow.context)
            await episode.build_result(record)
            return record

        record = asyncio.run(run())
        assert record.units_consumed == 3
        archived = json.loads(''.join(iter_json(record.as_record())))
        launch_record = archived['units'][0]['child']
        api_record = launch_record['units'][0]['child']
        result_record = archived['units'][2]['child']
        for completed in (launch_record, api_record, result_record):
            assert completed['units_consumed'] == 1
            assert completed['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
            assert completed['units'][-1]['controller_step']['marginal_credit'] > 0
        launch_rows = [dict(row) for row in store.db.execute(
            "SELECT episode_id,decision_index,action,result,credit FROM runtime_actions "
            "WHERE run_id=? AND json_extract(action,'$.tool')=?", (workflow.run_id, launch_tool))]
        assert launch_rows == choices.launch_rows  # Monitor/results cannot reprice closed launch.
        returned = json.loads(workflow.journal.row('runtime_forms', result_record['episode_id'])['form'])
        assert returned['completed'] and returned['references']
        assert store.count('annotation') == 0  # Source acquisition does not annotate the target.

        family = workflow.episode_bindings.for_role('launch_api')
        saved = workflow.journal.row('runtime_episodes', api_record['episode_id'])
        original = json.loads(saved['request'])
        original_context = BindingContext(workflow.run_id, api_record['episode_id'], 'launch_api',
            tuple(tuple(part) for part in json.loads(saved['path'])), scope, requested, original)
        counts = len(client.requests), len(bvbrc_calls)
        replay = asyncio.run(family.execute(original_context, launch_tool, {},
            f'{workflow.run_id}:{api_record["episode_id"]}:0'))
        original_outcome = json.loads(launch_rows[0]['result'])
        # The runtime adds its own pending-work snapshot outside the service
        # receipt; replaying a binding operation restores the service outcome.
        original_outcome.pop('pending_work_after_action', None)
        assert replay == original_outcome
        assert (len(client.requests), len(bvbrc_calls)) == counts
        if service == 'bvbrc_data':
            assert [row['offset'] for row in bvbrc_calls] == [0, 2]
        elif api_request['operation'] == 'record':
            assert client.requests == [('P12345', {'accession': 'P12345'})]
        else:
            assert [row[1].get('cursor') for row in client.requests] == [None, 'actual-next-cursor']


@pytest.fixture
def generic_host(tmp_path, service_responses):
    client, _ = service_responses
    store = Store(tmp_path/'state')
    input_path = tmp_path/'two-inputs.fasta'
    input_path.write_text('>first\nMACDEFGH\n>second\nMARGKKIG\n')
    targets = store.create_problem(input_path,
        molecule='protein', format='fasta')['subject_refs']
    journal = Journal(store, 'generic-api-boundaries')
    family = ExecutionEpisodes(None, store=store, directory=tmp_path/'run', run_id=journal.run_id,
        resources=resources(), initial_information={}, tool_registry=ToolRegistry(store, clients=client),
        handoff_unit=3, acquired_record_unit=2, log_window_bytes=128, log_roles=[])
    yield SimpleNamespace(store=store, journal=journal, family=family,
        scope={'subject_refs': [targets[0]]}, target=targets[0], outside=targets[1], client=client)
    store.close()


def test_concrete_requests_and_scopes_are_checked_before_commission(generic_host):
    h = generic_host
    request = assignment('uniprot', 'uniprot', {'operation': 'record', 'accession': 'P12345'})
    parent = context(h, 'launch', launch_assignment({'uniprot': request}), 'parent')
    assert h.family.prepare_assignment(parent, 'launch_api', request, h.scope, 'unexecuted') == request
    child_context = replace(parent, role='launch_api', path=(('launch_api', 'child'),),
        assignment=request)
    assert h.family.permitted_common_actions(child_context) == ('tool', 'wait')
    schema = h.family.assignment_schema('launch')['properties']['requests']['properties']['uniprot']
    assert schema['type'] == 'object'
    assert schema['properties']['request']['additionalProperties'] is False
    assert schema['properties']['service']['const'] == 'uniprot'
    changed = deepcopy(request)
    changed['request']['accession'] = 'P12346'
    with pytest.raises(ValueError, match='original_request_conflict'):
        h.family.prepare_assignment(parent, 'launch_api', changed, h.scope, 'unexecuted')
    for service in ('unregistered-service', 'bvbrc_data'):
        wrong_service = {**deepcopy(request), 'service': service}
        with pytest.raises(ValueError):
            h.family.prepare_assignment(parent, 'launch_api', wrong_service, h.scope, 'unexecuted')
    invalid = deepcopy(request)
    invalid['request']['operation'] = 'search'  # accession is not a query.
    with pytest.raises(ValueError):
        h.family.prepare_assignment(parent, 'launch', launch_assignment({'uniprot': invalid}),
            h.scope, 'unexecuted')
    outside = assignment('ncbi-blast', 'ncbi_blast', {'subject_ref': h.outside,
        'program': 'blastp', 'database': 'swissprot'})
    with pytest.raises(ValueError):
        h.family.prepare_assignment(parent, 'launch', launch_assignment({'ncbi-blast': outside}),
            h.scope, 'unexecuted')
    assert h.client.requests == []


def test_native_selector_rejection_and_duplicate_content_credit(generic_host):
    h = generic_host
    request = assignment('uniprot', 'uniprot', {'operation': 'search', 'query': 'gene:ybhP', 'size': 1})
    parent = context(h, 'launch', launch_assignment({'uniprot': request}), 'search-parent')
    child_context = context(h, 'launch_api', request, 'search-api',
        path=(('launch', 'search-parent'), ('launch_api', 'search-api')))
    launched = select(h, child_context, 0, 'api.uniprot.search')
    assert launched['status'] == 'completed', launched
    handoff, = launched['record_refs']
    target = h.family.job_progress_provider.targets.read_target(handoff, h.scope)
    conflicting = deepcopy(target)
    conflicting['resource_id'] = 'bvbrc'
    with pytest.raises(ValueError):
        h.family.job_progress_provider.targets.observe_target(conflicting, operation_key='wrong-service')
    before = len(h.client.requests)
    bad_result = {'version': 'execution_results_assignment_v1', 'handoff_ref': handoff,
        'selector': {'page': 2}}
    with pytest.raises(ValueError):
        h.family.prepare_assignment(parent, 'results', bad_result, h.scope, 'unexecuted')
    assert len(h.client.requests) == before

    result_assignment = {'version': 'execution_results_assignment_v1', 'handoff_ref': handoff,
        'selector': {'cursor': 'actual-next-cursor', 'size': 1}}
    one = context(h, 'results', result_assignment, 'one')
    first = select(h, one, 0, 'api.uniprot.collect')
    assert first['status'] == 'completed', first
    two = context(h, 'results', result_assignment, 'two')
    again = select(h, two, 0, 'api.uniprot.collect')
    assert again['status'] == 'completed', again
    assert first['record_refs'] != again['record_refs']  # Actual different receipt timestamps.
    known = [*first['record_refs'], *again['record_refs']]
    view = h.family.project_credit(two, selection(two, known, first['record_refs']))
    assert view['credit'] == 0  # Same native page/content is not a fresh contribution.


def test_prechoice_configuration_facts_remain_unknown_availability_and_reject_conflicts(
        generic_host, monkeypatch):
    h = generic_host
    information = h.family._resource_information('ncbi-blast')
    assert information['availability'] == 'unknown'
    assert information['api_configuration_facts'] == {
        'ncbi_contact_configured': False, 'provider_rate_state_configured': False}
    original = h.family.api_execution.capabilities

    def conflicting(resource_id):
        rows = deepcopy(original(resource_id))
        if resource_id == 'ncbi-blast':
            rows[0]['configuration']['ncbi_contact_configured'] = True
        return rows

    monkeypatch.setattr(h.family.api_execution, 'capabilities', conflicting)
    with pytest.raises(ValueError, match='api_configuration_fact_conflict'):
        h.family._resource_information('ncbi-blast')
    assert h.client.requests == []


def test_new_service_resources_reconstruct_before_model_without_requests(tmp_path, monkeypatch):
    factory = ExecutionServiceFactory(resources(), {}, 3, 2, .5)
    expected = factory.as_record()
    directory, workspace = tmp_path/'run', tmp_path/'state'

    async def before_model(connection):
        with Store(workspace) as reopened:
            settings = json.loads(reopened.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])
            restored_options = reconstruction._standard_bindings(reopened, directory, settings)
            reconstruction._check_bindings(restored_options, settings)
            restored = assemble_workflow(reopened, build_tools(reopened), object(), directory,
                json.loads((directory/'run.json').read_text())['run_id'], settings,
                **{key: value for key, value in restored_options.items() if key != 'binding_definitions'})
            assert restored.episode_bindings.as_record() == settings['episode_bindings']
            assert restored_options['episode_service_factory'].as_record() == expected
            assert {row['resource_id'] for row in restored.resource_capabilities} == set(resources())
            for table in ('runtime_episodes', 'runtime_actions', 'provider_jobs'):
                assert reopened.db.execute('SELECT count(*) FROM '+table).fetchone()[0] == 0
        raise BeforeModel

    monkeypatch.setattr(ModelConnection, '__aenter__', before_model)
    with Store(workspace) as store:
        store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        with pytest.raises(BeforeModel):
            asyncio.run(run_workflow(store, build_tools(store), run_dir=directory,
                episode_service_factory=factory, episode_service_binding=factory.as_record(),
                episode_service_inputs='actual_tool_registry_v1',
                annotation_child_roles=('launch', 'monitor', 'results')))


def test_blast_results_choose_status_wait_and_fetch_without_required_monitor(tmp_path):
    from test_api_blast_service import Client as NativeBlastFixture

    class Responses(NativeBlastFixture):
        def __init__(self):
            super().__init__()
            self.status_count = 0

        def blast_delay(self, action, rid=None):
            return 0.  # Fixture clock permits each controlled request; no real HTTP.

        def blast(self, action, **arguments):
            value = super().blast(action, **arguments)
            if action == 'status':
                self.status_count += 1
                value = replace(value, content=(b'Status=WAITING\n' if self.status_count == 1
                    else b'Status=READY\nThereAreHits=yes\n'))
            return value

    def fixture_controller(path, initial):
        def estimate(history, parameters, contexts):
            return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= 2 else 1),
                parameters, {'fixture': 'two_scientific_commissions_only'})
        return YieldController(str(path), initial, 0, YieldParameters(100, 50),
            estimate_with_context=estimate if path[-1][0] == 'annotation' else None)

    client = Responses()
    with Store(tmp_path/'state') as store:
        target, = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']
        scope = {'subject_refs': [target]}
        request = assignment('ncbi-blast', 'ncbi_blast', {'subject_ref': target,
            'program': 'blastp', 'database': 'swissprot'})
        launch = launch_assignment({'ncbi-blast': request})
        factory = ExecutionServiceFactory({'ncbi-blast': resources()['ncbi-blast']}, {}, 3, 2, .5)
        handoff_form, result_form = form('execution_handoff_refs'), form('execution_result_refs')

        class Choices:
            def __init__(self):
                self.root_calls = 0
                self.result_calls = 0
                self.handoff = None

            async def complete(self, episode_id, role, instructions, current, schema):
                assert current.get('feedback') is None, current.get('feedback')
                execution = current.get('execution_assignment', {})
                if execution.get('version') == 'execution_launch_assignment_v1':
                    return child('launch_api', request, scope, handoff_form)
                if execution.get('version') == 'api_service_assignment_v1':
                    return selected('api.blast.submit')
                if execution.get('version') == 'execution_results_assignment_v1':
                    self.result_calls += 1
                    assert current['execution_progress']['execution_completed'] is False
                    assert current['execution_progress']['execution_result_refs'] == []
                    if self.result_calls == 1:
                        return selected('api.blast.status')
                    if self.result_calls == 2:
                        return {'selection': {'kind': 'wait', 'condition': {
                            'version': 'event_condition_v1', 'events': [],
                            'reconsider_at': datetime.now(timezone.utc).isoformat()}}, 'report_update': {}}
                    if self.result_calls == 3:
                        return selected('api.blast.status')
                    assert self.result_calls == 4, 'Fetch must complete this assignment immediately'
                    return selected('api.blast.fetch')
                self.root_calls += 1
                if self.root_calls == 1:
                    return child('launch', launch, scope, handoff_form)
                assert self.root_calls == 2
                self.handoff, = current['child_reports'][-1]['references']
                return child('results', {'version': 'execution_results_assignment_v1',
                    'handoff_ref': self.handoff, 'selector': {}}, scope, result_form)

            async def release(self, episode_id):
                pass

        choices = Choices()
        workflow = Workflow(store, ToolRegistry(store, clients=client), choices, tmp_path/'run',
            'connected-generic-blast', controller_factory=fixture_controller,
            project_credit=lambda *_: 0, episode_service_factory=factory,
            episode_service_binding=factory.as_record(), episode_service_inputs='actual_tool_registry_v1',
            annotation_child_roles=('launch', 'results'), episode_record_receipts=True,
            initial_known_record_refs=[])
        episode = workflow.build('annotation', 'root', 'Obtain the requested BLAST evidence', scope)

        async def run():
            record = await episode.run_async(workflow.context)
            await episode.build_result(record)
            return record

        record = asyncio.run(run())
        assert record.units_consumed == 2
        archived = json.loads(''.join(iter_json(record.as_record())))
        resource_record = archived['units'][0]['child']['units'][0]['child']
        results_record = archived['units'][1]['child']
        assert resource_record['units_consumed'] == 1
        assert results_record['units_consumed'] == 4
        gains = [unit['controller_step']['marginal_credit'] for unit in results_record['units']]
        assert gains[:3] == [0, 0, 0]
        assert gains[3] > 0
        assert results_record['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        assert [name for name, _ in client.calls] == ['submit', 'status', 'status', 'fetch']
        waits = list(store.db.execute('SELECT outcome FROM episode_waits WHERE run_id=?', (workflow.run_id,)))
        assert len(waits) == 1
        assert json.loads(waits[0][0])['wake_reason'] == 'reconsideration'
        observations = store.list('observation', limit=100)
        assert observations
        assert any(any(value['name'] == 'bitscore' and value['value']['value'] == 31.5
            for value in observation['measurements']) for observation in observations)
        assert store.count('annotation') == 0
