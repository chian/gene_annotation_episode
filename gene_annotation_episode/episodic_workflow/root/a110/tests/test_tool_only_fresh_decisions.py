"""Real tool-only permission dispatch and controlled instruction/fresh-call ports."""
from __future__ import annotations
import asyncio
from copy import deepcopy
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
AXIS = 'gene_annotation_episode.episodic_workflow.root.a110'
PREFIXES = ('', 'hpc_work_planning', 'hpc_work_planning/hpc_allocation_execution', 'scientific_process', 'scientific_process/hpc_work_planning', 'scientific_process/hpc_work_planning/hpc_allocation_execution')
HOMES = [('/'.join(filter(None, (prefix, suffix))), role) for prefix in PREFIXES for suffix, role in (
    ('execution_job_submission/local_job_execution', 'launch_local'), ('execution_job_submission/hpc_job_execution', 'launch_hpc'), ('execution_result_acquisition', 'results'))]
CASES = ('instructions_plain', 'instructions_context', 'instructions_exchange', 'instructions_job_overlap', 'fresh_context', 'saved_contract_failure')

class CapturedFreshContext(Exception):
    def __init__(self, context, schema): self.context, self.schema = deepcopy(context), deepcopy(schema)


def observations(home, role, case):
    from gene_annotation_episode.episodic_workflow.root.a110.episode_bindings import EpisodeBindingRegistry
    from gene_annotation_episode.episodic_workflow.root.a110.runtime import Workflow, WorkflowError
    episode = importlib.import_module(AXIS + '.' + home.replace('/', '.') + '.episode')
    instructions_module = importlib.import_module(AXIS + '.' + home.replace('/', '.') + '.task_instructions')
    decision_module = importlib.import_module(AXIS + '.' + home.replace('/', '.') + '.task_decision')
    owner = object.__new__(episode.ExecutionEpisode)
    owner.as_record = lambda: {'controlled_descriptor': home}
    owner.instructions = lambda context: 'Original private tool work and failed-outcome handling.'
    registry = EpisodeBindingRegistry(); registry.register(owner)
    workflow = object.__new__(Workflow)
    workflow.episode_bindings, workflow.receipts = registry, None
    workflow.run_id, workflow.root_action_boundary = 'controlled-fresh', None
    workflow.decision_protocol = 'decision_exchange_v1' if case == 'instructions_exchange' else None
    events = []
    workflow.job_episodes = SimpleNamespace(roles=(role,), instructions=lambda actual: events.append('job.instructions:' + actual) or 'Original configured job instructions.') if case == 'instructions_job_overlap' else None
    workflow.knowledge = SimpleNamespace(instructions=' Original knowledge.')
    workflow.launch_instructions = SimpleNamespace(instructions=' Original launch context.', context=lambda: {'actual_library': []}, materialize=lambda value: None)
    workflow.native_event_information = object() if case in {'instructions_context', 'instructions_exchange'} else None
    message = SimpleNamespace(as_record=lambda: {'episode_assignment': {}})
    request = SimpleNamespace(message=message, as_record=lambda: {'message': message.as_record()})
    source = SimpleNamespace(workflow=workflow, path=((role, 'standalone'),), scope={'subject_refs': []}, episode_id='controlled-owner', request=request, calls=0)
    assert workflow.specialist(source) is owner
    assert workflow.permits_common_action(source, 'tool') is True
    assert workflow.permits_common_action(source, 'reason') is False
    assert workflow.permits_common_action(source, 'wait') is False
    if case.startswith('instructions_'):
        context = {'tool_knowledge': {}, 'launch_instruction_library': {}} if case in {'instructions_context', 'instructions_exchange'} else {}
        value = instructions_module.instructions(source, context)
        assert 'common scientific reason action' not in value and 'pending_child_ handle' not in value and 'separate native_event_targets input' not in value
        return {'instructions': value, 'events': events}
    workflow.journal = SimpleNamespace(row=lambda *args: {'purpose': 'wrong-original-purpose', 'request': '{}', 'response': None} if case == 'saved_contract_failure' else None)
    workflow.contract_information_profile = lambda source: None
    workflow.resource_context = workflow.shared_information_context = lambda source: None
    workflow.available_child_roles = lambda source: ()
    registry.initial_decision_context = lambda context: {'controlled_initial_information': {'status': 'unavailable'}}
    workflow.execution_expectations = workflow.resource_estimator = None
    workflow.native_estimation_context = lambda source, context: None
    workflow.waiting_support = lambda *args: (_ for _ in ()).throw(AssertionError('unselected_waiting_support_executed'))
    def capture(source, context, schema): raise CapturedFreshContext(context, schema)
    workflow.freeze_literature_numerical_contracts = capture
    decision_type = getattr(decision_module, 'ResultsTaskDecision' if role == 'results' else 'NativeTaskDecision')
    context = {'literature_completed_work': {'existing_received_context': True}, 'pending_work': [], 'feedback': {'status': 'invalid', 'detail': 'original invalid outcome'}, '_completed_work_axis_results': {}}
    schema = {'original_schema': True}
    try:
        asyncio.run(decision_type.call(source, context, schema))
    except CapturedFreshContext as captured:
        assert case == 'fresh_context' and source.calls == 1
        assert captured.context['feedback'] == context['feedback'] and 'waiting_support' not in captured.context
        return {'context': captured.context, 'schema': captured.schema, 'calls': source.calls}
    except WorkflowError as error:
        assert case == 'saved_contract_failure'
        return {'exception': type(error).__module__ + '.' + type(error).__name__, 'message': str(error), 'calls': source.calls}
    raise AssertionError('actual_decision_boundary_not_reached')


@pytest.mark.parametrize('home,role', HOMES, ids=[home for home, _ in HOMES])
@pytest.mark.parametrize('case', CASES)
def test_original_tool_only_instruction_and_fresh_decision_boundaries(home, role, case):
    baseline = json.loads((Path(__file__).parent / 'fixtures/organization_preservation/a110_tool_only_fresh_baseline.json').read_bytes())
    assert observations(home, role, case) == baseline['observations'][home][case]
