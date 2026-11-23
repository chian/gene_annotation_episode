"""The task: read the configured API resources, choose which permitted concrete execution request to commission on
an explicit resource_id, and commission the API job execution child that carries it out; commit a typed reasoning
when it is useful.

Carried from the old ``task.py`` (``OperationalTask``: ``apply_response``, ``execute``), ``task_decision.py``,
``task_instructions.py`` (``instructions``), ``decision_inputs.py``, ``decision_state.py``,
``decision_presentation.py`` (``decision_yield_table``), ``execution_operations.py`` (``capabilities``,
``_resource_information``, ``catalog``, ``execute``), ``execution_contracts.py`` (``launch_operation_catalog``,
``_outcome``), ``execution_state.py`` (``initialize``), ``episode.py`` (``allowed_children``,
``permitted_common_actions``) and ``internal_summary.py`` (``initial_decision_context``). One unit is one tool read,
one typed reasoning commit or one commission. The task always offers a unit and never ends the Episode: only the
yield controller does.

Settings this episode reads (the old ``configuration.py`` values; ``ctx.settings``): ``resources`` (resource_id ->
configuration of kind ``api`` with ``service`` and ``base_url``), ``initial_information`` (the recorded inventory per
resource, optional), ``launch_instructions_directory`` and ``tool_knowledge_directory`` (optional),
``task_yield_profiles`` (``yield_estimator.py``). The commissioner's assignment is in ``summary``
(``messages/read_from_parent.py``).

Not carried and why: the model's ``wait`` and ``redeliver_report`` actions (wait and redelivery machinery), the old
decision-exchange loop, the report update, ``pending_work``, the contract-information profile and every restore and
checkpoint step.

BLOCKED-ON-JOB-SERVICE: ``job_access``. The old ``APIServiceExecution`` (``api_execution.capabilities``) lived in the
old shared root; the library has no copy and no service wraps it. The call this episode wants is named in
``api_capabilities`` below; the run has no factory for the service yet, so linking a run of this episode raises
``LinkError('service_required:...')``."""
from copy import deepcopy

from jsonschema import ValidationError

from episode_runtime import ChildCall, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.perturbation_evidence.literature_investigation_prompt import (
    REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.perturbation_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import (
    obj, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

from .goal import GOAL

CHILD_SLOTS = {
    'launch_api': 'perturbation_evidence/published_evidence_assessment/execution_job_submission/api_job_execution',
}
SERVICES = ('job_access',)

# The old ``execution_contracts`` constants: the kind of a configured resource.
KINDS = {'api': 'api'}
CAPABILITIES_TOOL = 'execution_capabilities'
REASON_TOOL = 'reason'
CHILD_SLOT = 'launch_api'

# The old ``launch_operation_catalog``: the one operation of this episode's own tool.
CAPABILITIES_DESCRIPTION = ('Read the actual caller-bound resource configuration and already recorded inventory; '
                            'no discovery or selection.')
REASON_DESCRIPTION = ('Commit a typed scientific reasoning over the records you hold. A commit with every section '
                      'empty is rejected.')


def checked_resources(settings):
    """The old ``configuration.__init__`` checks of the configured resources."""
    resources = settings['resources']
    information = settings.get('initial_information', {})
    if (not isinstance(resources, dict) or not resources or any(
            not isinstance(key, str) or not key or not isinstance(value, dict) or value.get('kind') not in KINDS
            for key, value in resources.items())):
        raise ValueError('explicit_execution_resources_required')
    if not isinstance(information, dict) or not set(information) <= set(resources):
        raise ValueError('initial_inventory_resource_not_bound')
    return resources


def resource_information(settings, resource_id, capability):
    """The old ``_resource_information``: what the model is shown of one configured resource. ``capability`` is the
    job-access service's answer for the resource: ``availability`` and ``tool_names``."""
    configuration = checked_resources(settings)[resource_id]
    return {'resource_id': resource_id, 'resource_kind': 'api', 'availability': capability['availability'],
            'tool_names': list(capability['tool_names']),
            **{key: deepcopy(configuration[key]) for key in ('service', 'base_url') if key in configuration},
            'inventory_snapshot': deepcopy(settings.get('initial_information', {}).get(resource_id))}


def initial_decision_context(settings, capability_of):
    """The old ``initial_decision_context``: the capabilities of every configured resource and the recorded
    inventory, with no discovery. ``capability_of(resource_id)`` asks the job-access service."""
    resources = checked_resources(settings)
    return {'execution_resource_capabilities': [resource_information(settings, key, capability_of(key))
                                                for key in resources],
            'execution_initial_information': deepcopy(settings.get('initial_information', {}))}


def execution_capabilities(arguments, ctx):
    """The old ``execution.capabilities``: the caller-bound resource configuration and the recorded inventory, with
    no discovery. The old invalid-arguments outcome is not carried: the arguments are the empty record.

    Wanted call: ``ctx.services['job_access'].api_capabilities(resource_id)`` for each configured resource (old
    ``capabilities()``: availability ``unknown`` and the tool names of ``api_execution.capabilities``)."""
    if arguments != {}:
        raise ValueError('invalid_execution_operation_arguments')
    service = ctx.services['job_access']
    return {'status': 'completed',
            'result': initial_decision_context(ctx.settings, lambda resource_id: service.api_capabilities(resource_id))}


def named_refs(value):
    """The record references a model-built value names: values under ``ref``, ``..._ref`` and ``..._refs``, other
    than an ``@alias`` of the same payload."""
    found = []
    if isinstance(value, dict):
        for name, child in value.items():
            if name == 'ref' or name.endswith('_ref'):
                found.append(child)
            elif name.endswith('_refs'):
                found.extend(child)
            else:
                found.extend(named_refs(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(named_refs(child))
    return [ref for ref in found if isinstance(ref, str) and not ref.startswith('@')]


def reason(arguments, ctx):
    """Commit the model's typed reasoning (the old ``Store.commit_reasoning`` path of ``execute``; the owner of the
    interpretation accounts is named by the system). A reference the payload names that this Episode does not hold
    is an invalid outcome and nothing is committed."""
    unheld = [ref for ref in named_refs(arguments['commit']) if not ctx.store.holds(ref)]
    if unheld:
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': 'record_not_held:' + ','.join(unheld)}}
    return ctx.store.commit_reasoning(arguments['commit'], arguments['scope'], ctx.operation_key)


TOOLS = {CAPABILITIES_TOOL: execution_capabilities, REASON_TOOL: reason}


def catalog(commit_schema):
    """The tools the model is shown: name, description and input schema (the old catalog)."""
    return [{'name': CAPABILITIES_TOOL, 'description': CAPABILITIES_DESCRIPTION, 'input_schema': obj({})},
            {'name': REASON_TOOL, 'description': REASON_DESCRIPTION, 'input_schema': obj({'commit': commit_schema})}]


def selection_schema(resource_ids, commit_schema):
    """What the model answers with: the capabilities tool, the reasoning commit, or the commission of one permitted
    resource's request (the old action schema: ``tool``, ``reason`` and ``child``; the resource is the explicit
    ``resource_id``)."""
    alternatives = [obj({'kind': {'const': 'tool'}, 'tool': {'const': CAPABILITIES_TOOL}, 'arguments': obj({})}),
                    obj({'kind': {'const': 'tool'}, 'tool': {'const': REASON_TOOL},
                         'arguments': obj({'commit': commit_schema})})]
    if resource_ids:
        alternatives.append(obj({'kind': {'const': 'child'},
                                 'resource_id': {'type': 'string', 'enum': list(resource_ids)}}))
    return obj({'selection': {'anyOf': alternatives}})


def instructions(*, knowledge, launch_library):
    """The old composition (``OperationalGoal.instructions`` replaced the default text, then
    ``task_instructions.instructions``) for the actions this episode has: the goal, the reasoning-commit
    requirement, then the tool-knowledge and launch-library texts when those libraries are present. The
    ``pending_child_delivery``, wait, native-event and decision-exchange paragraphs describe actions this episode no
    longer has."""
    text = GOAL + '\n' + REASONING_COMMIT_REQUIREMENT
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if launch_library is not None:
        text += LAUNCH_INSTRUCTIONS
    return text


def child_options(summary):
    """The children the model may commission (the old ``allowed_children``): the API job execution child for each
    unconsumed resource of the input list (a resource already handed off or commissioned is not offered again)."""
    return [{'resource_id': resource_id, 'resource_kind': 'api', 'child': CHILD_SLOT}
            for resource_id in summary['input_list']]


def decide(summary, feedback, ctx):
    """Ask the model for the next action, shown the commission, the received handoffs, the credit binding, the
    capabilities of the configured resources (a recorded read of the job-access service), the children it may
    commission, the measured time, the yield table and the library listings (the old decision state and inputs,
    over this episode's summary).

    Wanted call: ``ctx.services['job_access'].read('api_capabilities', resource_id)`` (see
    ``execution_capabilities``)."""
    settings = ctx.settings
    knowledge_directory = settings.get('tool_knowledge_directory')
    launch_directory = settings.get('launch_instructions_directory')
    launch = None if launch_directory is None else LaunchInstructions(launch_directory)
    knowledge = None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()
    service = ctx.services['job_access']
    context = {'goal': GOAL,
               'execution_assignment': {name: summary[name] for name in (
                   'version', 'requests', 'immutable_input_versions', 'constraints', 'launch_instructions')},
               'execution_progress': {'handoff_resource_ids': list(summary['handed_off']),
                                      'new_handoff_resource_ids': summary['new_handoff_resource_ids'],
                                      'completed': summary['completed'], 'commissions': summary['commissions']},
               'credit_binding': {'version': 'execution_received_records_credit',
                                  'handoff_unit': summary['handoff_unit'],
                                  'qualification': 'original_request_resource_scope_selector_and_actual_received_'
                                                   'unique_information'},
               'child_options': child_options(summary), 'tools': catalog(summary['reasoning_schema']),
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        **initial_decision_context(settings, lambda resource_id: service.read('api_capabilities', resource_id)),
        'feedback': feedback, 'action_yields': summary['action_yields'],
        'tool_knowledge': knowledge,
        'launch_instruction_library': None if launch is None else launch.context(),
        'selected_launch_instructions': (None if launch is None or summary['launch_instructions'] is None
                                         else launch.materialize(summary['launch_instructions']))},
        conflict='initial_binding_context_field_conflict')
    schema = selection_schema(summary['input_list'], summary['reasoning_schema'])
    context['input_list'] = list(summary['input_list'])
    context['consumed_resource_ids'] = list(summary['consumed_resource_ids'])
    return ModelRequest('REASONING', instructions(knowledge=knowledge,
                                                  launch_library=context.get('launch_instruction_library')),
                        context, generation_schema(schema))


def empty_commit(commit, commit_schema):
    """The old empty-reasoning test (``reasoning_has_task_content``): every section the schema names is present or
    absent and none has a row."""
    return (set(commit_schema.get('required', commit_schema['properties'])) <= set(commit)
            <= set(commit_schema['properties']) and all(value == [] for value in commit.values()))


def action(response, summary, records, ctx):
    """Turn the model's answer into the capabilities read, the reasoning commit or the commission of one permitted
    resource's request, or reject it (no unit). An answer that does not fit the schema, an empty reasoning commit,
    or a resource the commissioner did not permit is invalid. The capabilities tool is always acceptable, so a unit
    is always offered. A permitted resource that the run's settings do not bind is a configuration conflict and
    raises (the old ``execution_resource_not_bound``)."""
    eligible = summary['input_list']
    commit_schema = summary['reasoning_schema']
    schema = selection_schema(eligible, commit_schema)
    try:
        value = decode_response(response, schema)
        validate_schema(value, schema)
        selection = value['selection']
        if selection['kind'] == 'tool':
            if selection['tool'] == REASON_TOOL and empty_commit(selection['arguments']['commit'], commit_schema):
                raise ValueError('empty_reasoning_commit')
            if selection['tool'] == CAPABILITIES_TOOL:
                return ToolCall(CAPABILITIES_TOOL, {})
            return ToolCall(REASON_TOOL, {'commit': selection['arguments']['commit'], 'scope': summary['scope']})
        resource_id = selection['resource_id']
        if resource_id not in eligible:
            raise ValueError('execution_resource_not_permitted:' + resource_id)
    except (ValueError, KeyError, TypeError, ValidationError, ContractError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    if resource_id not in checked_resources(ctx.settings):
        raise ValueError('execution_resource_not_bound')
    return ChildCall(CHILD_SLOT, {'resource_id': resource_id})
