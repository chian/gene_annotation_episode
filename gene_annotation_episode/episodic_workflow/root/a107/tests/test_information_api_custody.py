"""Own-A107 BLAST host publication and saved progress; controlled transport.

The client returns synthetic accepted/waiting protocol bytes. No network request
or native command occurs. API handoff publication, target reads and saved-action
context are actual implementations, independently read by the factory bundle.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from unittest.mock import patch

import pytest

from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources
from .test_information_connected import InformationCase, module, original_initial, private_information

EPOCH = '2026-10-23T00:00:00+00:00'
RID = 'FIXTURE_ORIGINAL_RID'


@pytest.fixture(autouse=True)
def no_external_transport(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('initial-information fixture attempted external transport or process execution')
    monkeypatch.setattr('socket.create_connection', denied)
    monkeypatch.setattr('urllib.request.OpenerDirector.open', denied)
    monkeypatch.setattr('subprocess.Popen', denied)


class ControlledBlastClient:
    ncbi_email = 'synthetic-fixture@example.invalid'
    def __init__(self):
        self.calls = []
    def blast_delay(self, action, rid=None):
        return 60. if action == 'status' else 10.
    def blast(self, action, **arguments):
        self.calls.append({'action': action, 'arguments': deepcopy(arguments)})
        request = {'action': action, **{key: value for key, value in arguments.items() if key != 'query_fasta'}}
        if action == 'submit':
            request['query_sha256'] = hashlib.sha256(arguments['query_fasta'].encode()).hexdigest()
            content, retrieved = b'    RID = FIXTURE_ORIGINAL_RID\n    RTOE = 17\n', EPOCH
        else:
            assert action == 'status' and arguments['rid'] == RID
            content, retrieved = b'Status=WAITING\n', '2026-10-23T00:02:00+00:00'
        return module('acquisition').SourceSnapshot('ncbi_blast', 'https://blast.ncbi.nlm.nih.gov/Blast.cgi',
            request, retrieved, content, 'application/json', {'representation': 'synthetic_protocol_fixture', 'status': 200})


def test_original_accepted_waiting_and_aged_payloads_are_read_without_new_observation(tmp_path, connected=True):
    configured = resources()
    configured['blast'] = {'kind': 'api', 'service': 'ncbi_blast'}
    client = ControlledBlastClient()
    case = InformationCase(tmp_path, received_resources=configured, clients=client, connect=connected)
    try:
        own = case.execution['scientific_process']['launch_api']
        science = case.parents['scientific_process']
        assignment = {'version': 'api_service_assignment_v1', 'resource_id': 'blast', 'service': 'ncbi_blast',
            'request': {'subject_ref': case.scope['subject_refs'][0], 'program': 'blastp', 'database': 'swissprot'},
            'endpoint': 'usable_handoff', 'constraints': {}}
        launch = case.context(science.path + (('launch', 'original-api-launch'),),
            {'version': 'execution_launch_assignment_v1', 'requests': {'blast': assignment},
                'immutable_input_versions': [], 'constraints': {}})
        native = case.context(launch.path + (('launch_api', 'original-api'),), assignment)
        action = {'kind': 'tool', 'tool': 'api.blast.submit', 'arguments': {}}
        canonical = module('execution_contracts').canonical
        case.journal.save('runtime_actions', {'episode_id': native.episode_id, 'decision_index': 0,
            'action': canonical(action), 'result': None, 'credit': None})
        now, rows = [EPOCH], []
        with patch.object(module('api_service_execution'), '_now', lambda: now[0]):
            outcome = asyncio.run(own.api_execution.execute(native, action['tool'], {},
                f'{case.run_id}:{native.episode_id}:0'))
            assert outcome['status'] == 'completed'
            case.journal.save('runtime_actions', {'episode_id': native.episode_id, 'decision_index': 0,
                'action': canonical(action), 'result': canonical(outcome), 'credit': 0})
            handoff, = outcome['record_refs']
            for phase, time in (('accepted', EPOCH), ('waiting', '2026-10-23T00:02:00+00:00'),
                    ('aged-without-new-observation', '2026-10-23T00:10:00+00:00')):
                if phase == 'waiting':
                    own.job_progress_provider.observe(handoff, ['execution_status'], case.scope,
                        operation_key='original-context-waiting-observation')
                now[0] = time
                before_calls, before_store = deepcopy(client.calls), list(case.store.db.iterdump())
                for context in (replace(case.root, received_record_refs=(handoff,)),
                        replace(science, received_record_refs=(handoff,))):
                    expected = original_initial(case.owner, context)
                    actual = private_information(case, context)
                    assert actual == expected
                    jobs = actual['received_blast_jobs']
                    assert len(jobs) == 1 and jobs[0]['evidence_axis'] == 'A107'
                    assert jobs[0]['proposed_annotation_ref'] == 'hypothesis_fixture'
                    if context.role == 'scientific_process':
                        assert jobs[0]['rid'] == RID and jobs[0]['handoff_ref'] == handoff
                    rows.append({'phase': phase, 'context': context.as_record(), 'received_record_refs': [handoff],
                        'expected': expected, 'actual': actual})
                assert client.calls == before_calls
                assert list(case.store.db.iterdump()) == before_store
            assert [row['action'] for row in client.calls] == ['submit', 'status']
        (tmp_path / 'api-initial-information-complete-payloads.json').write_text(json.dumps(rows, indent=2) + '\n')
    finally:
        case.close()


def test_nonempty_bvbrc_typed_admission_payload_retains_original_source_custody(tmp_path, connected=True):
    configured = resources()
    configured['selected-bvbrc'] = {'kind': 'api', 'service': 'bvbrc_data'}
    case = InformationCase(tmp_path, received_resources=configured, connect=connected)
    calls = []
    canonical = module('execution_contracts').canonical
    plain = module('communication').plain
    def native_response(client, prepared):
        calls.append(deepcopy(prepared))
        effective, native = prepared['effective_request'], prepared['native_request']
        payload = {'responseHeader': {'status': 0}, 'response': {
            'docs': [], 'start': effective['offset'], 'numFound': 2, 'numFoundExact': True}}
        return module('acquisition').SourceSnapshot('bvbrc_data', native['url'], deepcopy(effective),
            '2026-10-24T20:00:00+00:00', json.dumps(payload).encode(),
            'application/solr+json; charset=utf-8', {'status': 200, 'body_complete': True,
                'request': {name: deepcopy(native[name]) for name in ('method', 'url', 'headers', 'body')},
                'effective_url': native['url'], 'automatic_redirects': False})
    def selected(api, context, operation):
        action = {'kind': 'tool', 'tool': operation, 'arguments': {}}
        case.journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': 0,
            'action': canonical(action), 'result': None, 'credit': None})
        outcome = asyncio.run(api.execute(context, operation, {}, f'{case.run_id}:{context.episode_id}:0'))
        assert outcome['status'] == 'completed', outcome
        case.journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': 0,
            'action': canonical(action), 'result': canonical(outcome), 'credit': 0})
        return outcome
    try:
        parent = case.parents['scientific_process']
        api = case.execution['scientific_process']['launch_api'].api_execution
        assignment = {'version': 'api_service_assignment_v1', 'resource_id': 'selected-bvbrc',
            'service': 'bvbrc_data', 'request': {'version': 'bvbrc_data_request_v2',
                'collection': 'genome', 'mode': 'count', 'filters': []},
            'endpoint': 'usable_handoff', 'constraints': {}}
        launch = case.context(parent.path + (('launch', 'child_0'),),
            {'version': 'execution_launch_assignment_v1', 'requests': {'selected-bvbrc': assignment},
                'immutable_input_versions': [], 'constraints': {}})
        native = case.context(launch.path + (('launch_api', 'child_0'),), assignment)
        with patch.object(module('api_bvbrc').BVBRCDataClient, 'query_prepared', native_response):
            response = selected(api, native, module('api_bvbrc').DATA_QUERY_OPERATION)
            handoff = response['result']['handoff_ref']
            selector = {'version': 'bvbrc_data_result_selector_v2', 'page': None,
                'projection': {'family': 'query_metadata'}, 'inputs': [], 'supplied_metadata': []}
            assignment = {'version': 'execution_results_assignment_v1', 'handoff_ref': handoff, 'selector': selector}
            views = module('bvbrc_data_views')
            descriptors = views.bvbrc_data_fact_sources()
            properties = {'selected_' + str(i): descriptors[source]['report_schema']
                for i, source in enumerate(views.FACT_SOURCES)}
            schema = {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}
            contract = module('runtime').TypedReportContract('Return exact recorded BV-BRC query facts', schema, lambda *_: True)
            result_context = case.context(parent.path + (('results', 'child_1'),), assignment)
            request = {**plain(result_context.request), 'report_contract': contract.as_record()}
            result_context = replace(result_context, request=request)
            case.journal.save('runtime_episodes', {'episode_id': result_context.episode_id,
                'path': canonical(result_context.path), 'request': canonical(request), 'initial_credit': 0, 'state': 'running'})
            commission = {'kind': 'episode_child', 'role': 'results', 'assignment': assignment,
                'scope': case.scope, 'purpose': contract.decision, 'schema_json': canonical(schema)}
            case.journal.save('runtime_actions', {'episode_id': parent.episode_id, 'decision_index': 1,
                'action': canonical(commission), 'result': None, 'credit': None})
            result = selected(api, result_context, module('api_bvbrc').DATA_RESULT_OPERATION)
            assert result['result']['requested_projection_complete'] is True
            host = api.bvbrc_data
            facts = host.facts(result_context, schema)
            assert any(facts.values())
            form = module('communication').form_with_facts({}, schema, facts)
            case.journal.save('runtime_forms', {'episode_id': result_context.episode_id,
                'facts': canonical(facts), 'form': canonical(form)})
            case.journal.save('runtime_report_attempts', {'parent_episode_id': parent.episode_id, 'decision_index': 1,
                'delivery_ref': 'controlled-original-bvbrc-delivery', 'child_episode_id': result_context.episode_id,
                'contract': canonical(contract.as_record()), 'form': canonical(form), 'failure': None})
            operation_key = f'{case.run_id}:{parent.episode_id}:1:typed_form'
            host.record_admission(parent, form, schema, operation_key)
            before, transport = list(case.store.db.iterdump()), deepcopy(calls)
            actual = private_information(case, parent)
            assert actual == original_initial(case.owner, parent)
            assert actual['received_bvbrc_values'] and any(row['facts'] for row in actual['received_bvbrc_values'])
            assert list(case.store.db.iterdump()) == before and calls == transport and len(calls) == 1
            (tmp_path / 'bvbrc-initial-information-complete-payload.json').write_text(json.dumps(
                {'context': parent.as_record(), 'result': result, 'form': form, 'payload': actual}, indent=2) + '\n')
            # Altering the saved admitted form does not grant an alternate view.
            altered = deepcopy(form)
            field = next(name for name in altered if altered[name])
            altered[field] = []
            case.store.db.execute('UPDATE runtime_report_attempts SET form=? WHERE run_id=? AND parent_episode_id=? AND decision_index=1',
                (canonical(altered), case.run_id, parent.episode_id))
            errors = []
            for callback in (lambda: original_initial(case.owner, parent),
                    lambda: private_information(case, parent)):
                with pytest.raises(Exception) as error:
                    callback()
                errors.append((type(error.value), str(error.value)))
            assert errors[0] == errors[1]
    finally:
        case.close()
