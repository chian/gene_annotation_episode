"""Actual original request port, original override ABI and invalid prelude.

The only controlled port is applicability of the optional assembler method.
Child validation, original Store/Journal, Workflow.selected/build, declarations,
instruction pins and request/receipt writes remain actual own-A104 code.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
from types import MethodType

import pytest

from .api_cases import HOMES, Responses, assignment, canonical, error_record, module, rows
from .api_saved_carriers import build_case, SCHEMA


def preserve(request, record_property, name, value):
    value = canonical(value)
    record_property(name, json.dumps(value, sort_keys=True))
    if os.environ['A104_REQUEST_PORT_PHASE'] == 'connected':
        baseline = json.loads(Path(os.environ['A104_REQUEST_PORT_BASELINE']).read_bytes())
        original = [json.loads(payload) for row in baseline['reports']
            if row['nodeid'] == request.node.nodeid and row['phase'] == 'call'
            for key, payload in row['properties'] if key == name]
        assert len(original) == 1 and value == original[0]


@pytest.mark.parametrize('home', HOMES, ids=HOMES)
@pytest.mark.parametrize('applicability', ('absent', 'returns_none'))
def test_actual_selected_nonparticipant_preserves_original_build_signature(
        tmp_path, home, applicability, monkeypatch, request, record_property):
    client = Responses()
    with module('state').Store(tmp_path / 'store') as store:
        scope = {'subject_refs': store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']}
        workflow, factory = build_case(store, tmp_path, home, 'launch', client)
        chosen = assignment(scope['subject_refs'][0])
        launch = {'version': 'execution_launch_assignment_v1', 'requests': {'uniprot': deepcopy(chosen)},
            'immutable_input_versions': [], 'constraints': {}}
        parent = workflow.build('launch', 'original-parent', 'Retain original ABI', scope,
            episode_assignment=launch)
        binding = workflow.specialist(parent.source)
        routing_calls = []
        if applicability == 'absent':
            for cls in type(binding).__mro__:
                if 'child_request_assembler' in cls.__dict__:
                    monkeypatch.delattr(cls, 'child_request_assembler')
            assert not hasattr(binding, 'child_request_assembler')
        else:
            def no_assembler(self, role):
                routing_calls.append(role)
                return None
            monkeypatch.setattr(binding, 'child_request_assembler', MethodType(no_assembler, binding), raising=False)
        actual_build = workflow.build
        calls = []
        # Exact original public build signature, intentionally without **kwargs
        # or the new optional keyword. A stray request_assembler=None fails here.
        def original_override(self, name, key, goal_text, scope, *, parent=None, parent_path=(),
                contract=None, initial=None, job_assignment=None, episode_assignment=None,
                scientific_process=None, report_contract_declaration=None):
            calls.append({'role': name, 'key': key, 'transaction_open': self.store.db.in_transaction,
                'assignment': canonical(episode_assignment)})
            return actual_build(name, key, goal_text, scope, parent=parent, parent_path=parent_path,
                contract=contract, initial=initial, job_assignment=job_assignment,
                episode_assignment=episode_assignment, scientific_process=scientific_process,
                report_contract_declaration=report_contract_declaration)
        monkeypatch.setattr(workflow, 'build', MethodType(original_override, workflow))
        selected = {'kind': 'episode_child', 'role': 'launch_api', 'goal': 'Keep the original request',
            'scope': scope, 'purpose': 'Return completion', 'assignment': chosen,
            'schema_json': json.dumps(SCHEMA), 'initial_report_json': '{}'}
        try:
            child = workflow.selected(parent.source, selected, 4).child
            observed = {'request': child.request.as_record(),
                'context': workflow.binding_context(child.source).as_record()}
        except Exception as error:
            observed = {'raised': error_record(error)}
        if home in HOMES[:2]:
            assert observed.get('raised', {}).get('message') == 'unknown_execution_episode_role'
            assert calls == [] and routing_calls == []
        else:
            assert 'raised' not in observed and len(calls) == 1
            assert calls[0]['transaction_open'] is True
            assert calls[0]['assignment'] == chosen
            expected = ['launch_api'] if applicability == 'returns_none' and os.environ['A104_REQUEST_PORT_PHASE'] == 'connected' else []
            assert routing_calls == expected
        assert client.calls == []
        preserve(request, record_property, 'original_nonparticipant_request_and_ABI',
            {'outcome': observed, 'original_signature_calls': calls, 'original_selection': selected})


@pytest.mark.parametrize('home', HOMES, ids=HOMES)
@pytest.mark.parametrize('invalid', ('declaration_without_contract', 'incomplete_declaration', 'invalid_instruction_pin'))
def test_actual_invalid_request_prelude_preserves_original_failure_and_no_publication(
        tmp_path, home, invalid, request, record_property):
    client = Responses()
    runtime = module('runtime')
    with module('state').Store(tmp_path / 'store') as store:
        scope = {'subject_refs': store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']}
        workflow, factory = build_case(store, tmp_path, home, 'launch', client)
        owner = workflow.episode_bindings.for_role('launch')
        options = {'episode_assignment': assignment(scope['subject_refs'][0])}
        if invalid == 'declaration_without_contract':
            options['report_contract_declaration'] = {}
        elif invalid == 'incomplete_declaration':
            options['contract'] = runtime.TypedReportContract('Return completion', SCHEMA, lambda *_: True)
            options['report_contract_declaration'] = {'submitted_schema_json': '{}'}
        else:
            options['episode_assignment']['launch_instructions'] = {'version': 'controlled_invalid_pin'}
        if os.environ['A104_REQUEST_PORT_PHASE'] == 'connected':
            assembler = owner.child_request_assembler('launch_api')
            assert callable(assembler)
            options['request_assembler'] = assembler
        before = rows(store)
        try:
            workflow.build('launch_api', 'invalid-original-request', 'Keep original preflight', scope, **options)
        except Exception as error:
            observed = {'raised': error_record(error)}
        else:
            pytest.fail('original invalid request prelude unexpectedly returned')
        assert rows(store) == before and client.calls == []
        preserve(request, record_property, 'original_invalid_prelude_boundary',
            {'case': invalid, 'outcome': observed, 'logical_rows_unchanged': True})
