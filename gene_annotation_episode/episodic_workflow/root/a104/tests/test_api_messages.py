"""Actual typed API handoffs and parent receipt/redelivery boundaries.

Saved parent contexts are explicitly controlled. They do not assert that an
HPC commission authorized an API request. The real missing two parent schemas
remain observed failures; no child validator or reference reader is patched.
"""
from copy import deepcopy
from dataclasses import replace
import json
import os
from types import SimpleNamespace

import pytest

from .api_cases import Case, HOMES, canonical, module, outcome, rows


@pytest.mark.parametrize('home', HOMES, ids=HOMES)
def test_actual_saved_api_parent_admission_and_typed_redelivery(tmp_path, home, record_property):
    case = Case(tmp_path, home, parented=True, initialize=False)
    runtime = module('runtime')
    try:
        admitted = outcome(lambda: case.binding.prepare_assignment(case.parent_context, 'launch_api',
            deepcopy(case.assignment), case.scope, 'controlled-parent-request'))
        record_property('controlled_saved_parent_admission', json.dumps(admitted, sort_keys=True))
        if home in HOMES[:2]:
            assert admitted.get('raised', {}).get('message') == 'unknown_execution_episode_role'
            assert case.client.calls == []
            return  # Required observed blocker, not a passed typed-return claim.
        assert admitted == {'returned': canonical(case.assignment)}
        case.binding.initialize(case.context)
        completed = case.act('api.uniprot.record', index=0)
        assert completed['status'] == 'completed'
        definitions = case.binding.fact_sources('launch_api')
        schema = runtime._object({'handoffs': deepcopy(definitions['execution_handoff_refs']['report_schema']),
            'completed': {'type': 'boolean', 'x-source': 'execution_completed'}})
        contract = runtime.TypedReportContract('Return the original API handoff', schema, lambda *_: True)
        request = {**canonical(case.context.request), 'report_contract': contract.as_record()}
        case.context = replace(case.context, request=request)
        case.journal.save('runtime_episodes', {'episode_id': case.episode_id,
            'path': runtime._json(case.path), 'request': runtime._json(request), 'initial_credit': 0,
            'state': 'active', 'completion': None, 'archive': None})
        facts = case.binding.facts(case.context, {})
        form = {'handoffs': facts['execution_handoff_refs'], 'completed': facts['execution_completed']}
        assert form['completed'] is True and form['handoffs'] == completed['record_refs']
        case.binding.validate_report(case.context, form, schema)
        case.journal.save('runtime_forms', {'episode_id': case.episode_id,
            'facts': runtime._json(facts), 'form': runtime._json(form)})
        parent = next(value for value in case.family if value.roles == ('launch',))
        registry = module('episode_bindings').EpisodeBindingRegistry((parent, case.binding))
        progress, attribution, timing = [], [], []
        timing_ref = case.store.artifact(b'explicitly controlled timing projection port; not a native measurement')
        def receive_timing(*args):
            timing.append(canonical(args[1:]))
            return {'native_execution_refs': [timing_ref]}
        source = SimpleNamespace(episode_id=case.parent_context.episode_id,
            path=case.parent_context.path, scope=deepcopy(case.scope), _delivery_resolution_ref=None)
        workflow = SimpleNamespace(store=case.store, journal=case.journal, run_id=case.run_id,
            receipts=case.receipts, specialist=lambda source: parent,
            binding_context=lambda source: case.parent_context, is_job_source=lambda source: False,
            episode_bindings=registry, progress_provider=SimpleNamespace(receive_form=lambda *args: progress.append(canonical(args))),
            native_timing_information=object(), job_episodes=SimpleNamespace(received_timing_records=receive_timing),
            receive_tool_attributions=lambda *args, **kwargs: attribution.append([args[1], kwargs]) or [])
        def attempt(index, *, redelivery=False, child_id=None):
            selected = ({'kind': 'redeliver_report', 'delivery_ref': 'delivery-original-api',
                'schema_json': runtime._json(schema), 'purpose': contract.decision} if redelivery else
                {'kind': 'episode_child', 'role': 'launch_api', 'assignment': deepcopy(case.assignment),
                 'scope': deepcopy(case.scope), 'purpose': contract.decision, 'schema_json': runtime._json(schema)})
            case.journal.save('runtime_actions', {'episode_id': source.episode_id, 'decision_index': index,
                'action': runtime._json(selected), 'result': None, 'credit': None})
            case.journal.save('runtime_report_attempts', {'parent_episode_id': source.episode_id,
                'decision_index': index, 'delivery_ref': 'delivery-original-api',
                'child_episode_id': case.episode_id if child_id is None else child_id,
                'contract': runtime._json(contract.as_record()), 'form': runtime._json(form), 'failure': None})
        attempt(3)
        references = runtime.Workflow._receive_form(workflow, source, form, schema, 3)
        assert set(form['handoffs']) <= set(references) and timing_ref in references
        assert progress[0][-1] == f'{case.run_id}:{source.episode_id}:3:typed_form'
        assert len(timing) == 1
        original = case.journal.row('runtime_actions', source.episode_id, 3)
        case.journal.save('runtime_actions', {'episode_id': source.episode_id, 'decision_index': 3,
            'action': original['action'], 'result': runtime._json({'status': 'completed', 'record_refs': references}),
            'credit': 3.})
        before, counts = rows(case.store), (len(progress), len(attribution), len(timing))
        assert runtime.Workflow._receive_form(workflow, source, form, schema, 3) == references
        assert rows(case.store) == before and (len(progress), len(attribution), len(timing)) == counts
        attempt(4, redelivery=True)
        delivered = runtime.Workflow._receive_form(workflow, source, form, schema, 4, redelivery=True)
        assert delivered == references and len(timing) == 2
        timing_rows = [dict(row) for row in case.store.db.execute('SELECT decision_index,timing_receipts '
            'FROM runtime_report_attempts ORDER BY decision_index')]
        assert all(json.loads(row['timing_receipts']) == {'native_execution_refs': [timing_ref]} for row in timing_rows)
        assert runtime.Workflow._receive_form(workflow, source, form, schema, 4, redelivery=True) == delivered
        assert len(timing) == 2  # Persisted attempt projection, never repriced.
        wrong_path = (('launch', 'different-parent'), ('launch_api', 'child_3'))
        wrong_id = module('method_loop.identities').EpisodeRef(case.run_id, wrong_path).episode_id
        case.journal.save('runtime_episodes', {'episode_id': wrong_id, 'path': runtime._json(wrong_path),
            'request': runtime._json(request), 'initial_credit': 0, 'state': 'yielded', 'completion': None, 'archive': None})
        attempt(7, redelivery=True, child_id=wrong_id)
        original_owner_guard = outcome(lambda: module('episode_return_records').EpisodeReturnRecords(
            case.store, case.run_id, failure_prefix='original_api_delivery_')._attempt(case.parent_context, 7))
        assert 'raised' in original_owner_guard
        denied = outcome(lambda: runtime.Workflow._receive_form(workflow, source, form, schema, 7, redelivery=True))
        receiver = getattr(parent, 'child_report_receiver', None)
        if os.environ.get('A104_API_PHASE') == 'connected':
            assert receiver is not None and receiver('launch_api').__module__.endswith('.from_child_api_job_execution')
            assert 'raised' in denied
        record_property('actual_typed_receipt', json.dumps({'scope': 'Controlled saved parent/API contexts; actual typed validators',
            'child_context': case.context.as_record(), 'parent_context': case.parent_context.as_record(),
            'selected_api_outcome': completed, 'facts': facts, 'form': form, 'schema': schema,
            'references': references, 'progress_calls': progress, 'attributions': attribution,
            'timing_projection_port': timing_rows, 'original_saved_owner_guard': original_owner_guard,
            'isolated_receive_form_wrong_parent_observation': denied,
            'baseline_dispatch_without_new_counterpart_is_not_complete_admission': receiver is None}, sort_keys=True))
    finally:
        case.close()
