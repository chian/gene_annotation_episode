"""Genuine root unit/replay support; scripted engineering estimation only.

Promoted from the retained V2 boundary diagnostic. No acquisition capability,
scientific decision, replacement controller, timer, or continuation gate is added.
"""
from contextlib import contextmanager
from dataclasses import fields, replace
from datetime import datetime, timezone
import hashlib
import inspect
import json
from pathlib import Path


def need(value, message):
    if not value:
        raise ValueError(message)


def save(p, value):
    with Path(p).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


class EstimateCaller:
    """One explicit operation, never a generated scientific decision or stop."""
    def __init__(self):
        self.requests = []

    async def complete(self, episode_id, purpose, instructions, context, output_schema):
        from jsonschema import Draft202012Validator
        stamp = datetime.now(timezone.utc).isoformat()
        response = {'selection': {'kind': 'tool', 'tool': 'episode.estimate_wait', 'arguments': {
            'condition': {'version': 'event_condition_v1', 'events': [], 'reconsider_at': stamp}}},
            'report_update': {}}
        # Validate the actual transport schema, not a modified caller schema.
        Draft202012Validator(output_schema).validate(response)
        self.requests.append(json.loads(json.dumps({'episode_id': episode_id, 'purpose': purpose,
            'instructions': instructions, 'context': context, 'output_schema': output_schema,
            'response': response, 'captured_utc': stamp})))
        return response


@contextmanager
def root_at(out, provider, *, initialize):
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.episodic_workflow.root.episode import SignedRootEpisodeBinding
    from gene_annotation_episode.episodic_workflow.root.root_assembly import create_signed_evidence_root_workflow
    from gene_annotation_episode.episodic_workflow.root.tests.fresh_decision_support import ConstructorTools, ActualRoot
    fixture = (Path(__file__).parent / 'fixtures/fresh_decision_binding.json').read_bytes()
    need(hashlib.sha256(fixture).hexdigest() == '14abad6673f40e74f2494ed9dec06125d4883720d903a30596b47fcfe662b437',
         'original_root_binding_fixture_changed')
    binding = SignedRootEpisodeBinding.from_record(json.loads(fixture))
    tools = ConstructorTools()
    with Store(out / 'store') as store:
        if initialize:
            store.create_problem(raw_sequence='ATGAAATAG', molecule='dna', role='assembly')
        scope = store.validate_scope()
        workflow = create_signed_evidence_root_workflow(store, tools, provider, out / 'workflow',
            'engineering-root-nonempty-outcome', binding.yield_controller,
            initial_known_record_refs=binding.initial_known_record_refs, project_credit=binding.task_credit,
            credit_binding=binding.task_credit.as_record(), controller_binding=binding.controller_record(),
            episode_binding_factories=(), annotation_child_roles=())
        episode = workflow.build('annotation', 'root', 'Engineering nonempty root outcome connection', scope)
        episode.source.bind_execution_context(workflow.context)
        yield ActualRoot(store, binding, workflow, episode, tools, provider, scope)


async def diagnose(out, result):
    from gene_annotation_episode.episodic_workflow.root.task_values import _plain
    from gene_annotation_episode.episodic_workflow.root.tests.fresh_decision_support import action_rows
    provider = EstimateCaller()
    saved = None
    for label, initialize in (('original', True), ('replay', False)):
        result['stage'] = label + '_construction'
        with root_at(out, provider, initialize=initialize) as root:
            source, episode, ctx = root.source, root.episode, root.workflow.context
            row = result[label] = {'episode_id': source.episode_id, 'request': _plain(source.request),
                'scope': _plain(root.scope)}
            try:
                row['credit_before_unit'] = _plain(root.workflow.source_credit_view(source)['credit'])
                row['original_initial_credit'] = _plain(root.workflow.journal.row('runtime_episodes', source.episode_id)['initial_credit'])
                need(row['credit_before_unit'] == row['original_initial_credit'], 'initial_binding_credit_changed')
                catalog = root.workflow.catalog(root.scope, source=source)
                row['catalog'] = catalog
                need('shared.request_information' not in {item['name'] for item in catalog}, 'parentless_shared_route_unexpectedly_available')
                need('episode.estimate_wait' in {item['name'] for item in catalog}, 'actual_estimate_operation_unavailable')
                result['stage'] = label + '_actual_run_unit_async'
                captured = []
                original_hook = episode.on_unit
                need(callable(original_hook), 'original_observation_hook_required')

                async def capture_after_original(item, contribution, actual_unit_view):
                    callback_result = original_hook(item, contribution, actual_unit_view)
                    if inspect.isawaitable(callback_result):
                        callback_result = await callback_result
                    need(ctx.path == source.path and actual_unit_view.unit_ref.episode_id == source.episode_id,
                         'actual_observation_scope_identity_changed')
                    observed_view = episode._view(ctx, ctx.path, [],
                        unit_offset=actual_unit_view.unit_ref.unit_index + 1)
                    captured.append((observed_view, actual_unit_view))
                    return callback_result

                observed_episode = replace(episode, on_unit=capture_after_original)
                need(type(observed_episode) is type(episode) and all(
                    getattr(observed_episode, field.name) is getattr(episode, field.name)
                    for field in fields(episode) if field.name != 'on_unit'), 'observation_wrapper_changed_episode_operands')
                unit = await observed_episode.run_unit_async(ctx, expected_label='tool:0')
                need(len(captured) == 1, 'original_unit_hook_not_captured_exactly_once')
                view, captured_unit_view = captured[0]
                need(captured_unit_view.unit_ref == unit.unit_ref
                     and captured_unit_view.controller_input is unit.controller_input
                     and captured_unit_view.controller_step is unit.controller_step
                     and view.units_consumed == unit.unit_ref.unit_index + 1,
                     'captured_observation_differs_from_returned_unit')
                row['unit'] = _plain(unit)
                row['last_outcome'] = _plain(source.last_outcome)
                row['rows'] = action_rows(root)
                actions, observations, calls = (row['rows'][name] for name in
                    ('runtime_actions', 'runtime_observations', 'runtime_model_calls'))
                need(len(actions) == len(observations) == len(calls) == 1, 'nonunique_actual_unit_records')
                selected = json.loads(actions[0]['action'])
                response = provider.requests[0]['response']
                need(selected == response['selection'] and selected['tool'] == 'episode.estimate_wait', 'saved_action_changed')
                need(source.last_outcome == json.loads(actions[0]['result']), 'saved_outcome_changed')
                outcome = source.last_outcome
                need(outcome['status'] == 'completed' and outcome['record_refs'] == []
                     and outcome['changed_record_refs'] == [], 'estimate_did_not_return_original_completed_empty_references')
                estimate = outcome['result']
                need(estimate['version'] == 'wait_estimate_v1'
                     and estimate['condition'] == selected['arguments']['condition']
                     and estimate['condition']['events'] == []
                     and estimate['condition']['reconsider_at'] == provider.requests[0]['captured_utc']
                     and estimate['scientific_gain'] is None and estimate['monitoring_gain'] is None,
                     'estimate_changed_timestamp_or_invented_gain')
                observation = json.loads(observations[0]['observation'])
                need(observation['unit_ref'] == row['unit']['unit_ref']
                     and observation['credit'] == row['unit']['controller_input']
                     and observation['step'] == row['unit']['controller_step'], 'actual_observation_identity_changed')
                recorded_credit = root.workflow.journal.row('runtime_actions', source.episode_id, 0)['credit']
                need(_plain(recorded_credit) == observation['credit']['credit'], 'original_action_credit_not_observed')
                row['credit_after_unit'] = _plain(root.workflow.source_credit_view(source)['credit'])
                need(row['credit_before_unit'] == row['credit_after_unit'] == _plain(recorded_credit),
                     'estimate_changed_original_scientific_credit')
                # ReleasingContext has now removed the controller. Use only the
                # actual post-observation view captured before release, not reentry.
                row['next_view'] = {'units_consumed': view.units_consumed, 'path': _plain(view.path),
                    'controller_state': _plain(view.controller_state), 'episode_ref': _plain(view.episode_ref),
                    'request': _plain(view.request)}
                need(view.units_consumed == 1 and view.episode_ref.episode_id == source.episode_id,
                     'next_view_lost_actual_position')
                stable = {'request': row['request'], 'unit': row['unit'], 'outcome': row['last_outcome'],
                    'action': selected, 'observation': observation, 'model_request': calls[0]['request'],
                    'model_response': calls[0]['response']}
                if saved is None:
                    saved = stable
                    save(out / 'observed_original.json', row)
                else:
                    need(stable == saved and len(provider.requests) == 1, 'genuine_replay_changed_identity_or_called_provider')
                    save(out / 'observed_replay.json', row)
                    result['replayed_original_without_provider_call'] = True
                    result['stage'] = 'actual_next_decision_inputs_after_observation_and_replay'
                    context, schema = source._decision_inputs(view)
                    save(out / 'next_decision_inputs.json', {'context': context, 'schema': schema})
                    result['next_decision_inputs_completed'] = True
            finally:
                row['rows_at_exit'] = action_rows(root)
                row['selected_waits'] = [dict(item) for item in root.store.db.execute(
                    'SELECT * FROM episode_waits WHERE run_id=?', (root.workflow.run_id,))]
                row['timed_commissions'] = [dict(item) for item in root.store.db.execute(
                    'SELECT * FROM runtime_timed_commissions WHERE run_id=?', (root.workflow.run_id,))]
                row['tools_execution_calls'] = _plain(root.tools.execution_calls)
                result['provider_requests'] = provider.requests
                need(not root.tools.execution_calls and not row['selected_waits'] and not row['timed_commissions'],
                     'unexpected_external_tool_acquisition_or_wait_schedule')


