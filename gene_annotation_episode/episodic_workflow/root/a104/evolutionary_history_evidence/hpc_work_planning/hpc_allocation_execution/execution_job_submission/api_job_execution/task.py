"""The task: one selected operation of the assigned API service per unit, until the original usable handoff is
established. The task always offers a unit and never ends the Episode: its completion controller stops it when the
credit of the verified original handoff reaches the commission's target.

Carried from the old ``task.py``, ``task_decision.py``, ``task_instructions.py``, ``decision_context.py``,
``api_actions.py``, ``api_state.py``, ``action_outcomes.py``, ``goal.py`` (``_with_selected_execution_task``),
``resource_information.py`` and ``api_service.py`` (``catalog``, ``execute``, ``_execute_locked``,
``_publish_handoff``). The old executor (``APIJobService`` with its per-operation directory, locks and immutable
intent, snapshot, event and outcome files; ``HMMERJobService`` with its own SQL tables) was the outside world and
its durable state: it is the ``job_access`` service, which does not exist yet. This episode only names it and calls
it (BLOCKED-ON-JOB-SERVICE, see ``carry_over_blocked``). The tool writes the records through ``ctx.store``.

What the service must offer (the calls this episode makes):

* ``job_access.read('launch_catalog', assignment)``: the operations the service offers for this assignment
  (``[{'name', 'description', 'input_schema'}]``; the old ``launch_catalog(request)`` and ``hmmer_operation_catalog``);
* ``job_access.read('capabilities', resource_id)``: the service's capability entries for the resource (the old
  ``api_execution.capabilities(resource_id)``; each entry has ``name`` and ``configuration``);
* ``job_access.launch_operation(assignment, name, arguments, inputs=, key=, resumed=)``: validate and run one
  operation (prepare, invoke, decode), idempotent on ``key`` (one operation key is one immutable intent; only one
  original remote-mutating submission; an unknown reply after a restart is reported as unknown, never as absence).
  It returns ``{'status', 'event', 'feedback', 'submission_outcome', 'response', 'handoff', 'results'}``."""
from copy import deepcopy

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.evolutionary_history_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

CHILD_SLOTS = {}
SERVICES = ('job_access',)

# The old ``binding_roles.KINDS``: the kind of each configured resource.
KINDS = {'local': 'local', 'pbs_ssh': 'hpc', 'hmmer_api': 'api', 'api': 'api'}

INSTRUCTIONS = ('Carry out the assigned work through {service} using one selected operation each turn. Keep the '
                'original inputs, request, resource and parent constraints fixed. Choose useful preparation, '
                'service requests, observations or repair from the actual available operations and received '
                'outcomes. Distinguish an immediate returned response from a service job that continues remotely. '
                'Preserve the actual request or job identity and submission uncertainty; a missing reply does not '
                'establish that no job was created. Establish the requested usable monitoring/results handoff from '
                'recorded service facts. The configured controller governs continuation; verified original handoff '
                'completion gives exact zero future credit.')


def instructions(assignment, *, knowledge, launch_library):
    """The old ``instructions`` composer with its inputs explicit: the specialist text replaces the default; the
    tool-knowledge and launch-instruction texts follow when their context is present. The reasoning-commit,
    redelivery, wait and native-event guidance described actions this episode does not have."""
    text = INSTRUCTIONS.format(service=assignment['service'])
    if knowledge:
        text += KNOWLEDGE_INSTRUCTIONS
    if launch_library:
        text += LAUNCH_INSTRUCTIONS
    return text


def _outcome(operation, status, *, feedback=None, event=None, submission_outcome=None, job=None, handoff_ref=None,
             result_refs=(), result_identities=()):
    """The old ``action_outcomes._outcome`` envelope (status, record refs, result, feedback), with the identities
    the credit counts."""
    return {'status': status, 'operation': operation, 'event': event, 'feedback': feedback,
            'submission_outcome': submission_outcome, 'job': job, 'handoff_ref': handoff_ref,
            'result_refs': list(result_refs), 'result_identities': [list(item) for item in result_identities]}


def _job_ledger():
    """The declaration of the job records' work table (handoff, check, closure).

    Not defined yet: no module of ``episode_support`` declares a job record kind."""
    raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job record kind (the handoff row of the job ledger work table); '
                              'wanted call: ctx.store.table(JOB_LEDGER).put({job, event: handoff, at, detail, '
                              'source_ref})')


def launch_operation(arguments, ctx):
    """Run one operation of the assigned service and, when it establishes the original handoff, write the handoff
    record (the old ``_execute_locked`` and ``_publish_handoff``). A failed or invalid operation is the outcome."""
    ledger = _job_ledger()
    assignment, name = arguments['assignment'], arguments['operation']
    try:
        held = {ref: ctx.store.get(ref) for ref in arguments['input_refs']}
        reply = ctx.services['job_access'].launch_operation(assignment, name, arguments['arguments'], inputs=held,
                                                            key=ctx.operation_key, resumed=ctx.resumed)
    except (ValueError, ContractError, KeyError, TypeError) as error:
        return _outcome(name, 'invalid', feedback={'category': 'arguments_or_reference', 'code': str(error)})
    if reply['status'] in ('invalid', 'failed'):
        return _outcome(name, reply['status'], feedback=reply['feedback'], event=reply['event'],
                        submission_outcome=reply['submission_outcome'])
    handoff_ref = job = None
    produced = []
    with ctx.store.transaction():
        if reply['handoff'] is not None:
            handoff = reply['handoff']
            response = ctx.store.artifact(reply['response'], 'application/json')
            row = ctx.store.table(ledger).put({'job': handoff['handle'], 'event': 'handoff', 'at': handoff['submitted_at'],
                                               'detail': {'resource_id': handoff['resource_id'],
                                                          'execution_id': handoff['execution_id'],
                                                          'service': assignment['service'], 'operation': name,
                                                          'event': reply['event'], 'receipt': handoff['receipt']},
                                               'source_ref': response})
            handoff_ref, job = row['id'], [handoff['resource_id'], handoff['execution_id']]
        for result in reply['results']:
            produced.append((ctx.store.artifact(result['data'], result['media_type']), result['identity']))
    return _outcome(name, reply['status'], feedback=reply['feedback'], event=reply['event'],
                    submission_outcome=reply['submission_outcome'], job=job, handoff_ref=handoff_ref,
                    result_refs=[ref for ref, _ in produced], result_identities=[item for _, item in produced])


TOOLS = {'launch_operation': launch_operation}


def _resource_information(resource_id, config, entries, initial_information):
    """The old ``_resource_information`` and ``capabilities``: the configured capability of the resource (its
    availability is unknown: no probe), the configuration facts the service reports, the recorded inventory."""
    value = {'resource_id': resource_id, 'resource_kind': KINDS[config['kind']], 'availability': 'unknown',
             'tool_names': [entry['name'] for entry in entries],
             **{key: deepcopy(config[key]) for key in ('workspace', 'policy', 'account', 'python_executable',
                                                       'service', 'base_url') if key in config},
             'inventory_snapshot': deepcopy(initial_information.get(resource_id))}
    facts = {}
    for entry in entries:
        reported = entry.get('configuration', {})
        for name in ('ncbi_contact_configured', 'provider_rate_state_configured'):
            if name not in reported:
                continue
            actual = reported[name]
            if type(actual) is not bool:
                raise ValueError('api_configuration_fact_must_be_boolean')
            if name in facts and facts[name] != actual:
                raise ValueError('api_configuration_fact_conflict')
            facts[name] = actual
    if facts:
        value['api_configuration_facts'] = facts
    return value


def _selected_execution_task(summary, resource):
    """The old ``_with_selected_execution_task`` (only the EBI HMMER request is shown as a selected task)."""
    assignment = summary['assignment']
    if assignment.get('service') != 'ebi_hmmer':
        return None
    return {'version': 'selected_execution_task_v1', 'scientific_question': summary['scientific_question'],
            'selected_tool_info': summary['selected_tool_info'],
            'requests': [{'resource_id': assignment['resource_id'], 'resource_kind': 'api',
                          'endpoint': deepcopy(assignment.get('endpoint')),
                          'constraints': deepcopy(assignment.get('constraints', {})), 'job': deepcopy(assignment),
                          'resource': resource}],
            'constraints': assignment.get('constraints', {}), 'selector': assignment.get('selector'),
            'result_description': None}


def _selection_schema(catalog):
    """The old action schema over the service's own catalog: one tool selection per offered operation."""
    options = [{'type': 'object', 'additionalProperties': False, 'required': ['kind', 'tool', 'arguments'],
                'properties': {'kind': {'const': 'tool'}, 'tool': {'const': entry['name']},
                               'arguments': entry['input_schema']}} for entry in catalog]
    if not options:
        raise ValueError('api_launch_catalog_empty')
    return {'anyOf': options}


def decide(summary, feedback, ctx):
    assignment = summary['assignment']
    access = ctx.services['job_access']
    catalog = access.read('launch_catalog', assignment)
    resource_id = assignment['resource_id']
    resource = _resource_information(resource_id, ctx.settings['resources'][resource_id],
                                     access.read('capabilities', resource_id), ctx.settings['initial_information'])
    knowledge = ToolKnowledge(ctx.settings['tool_knowledge_directory']).context()
    launch = LaunchInstructions(ctx.settings['launch_instruction_directory'])
    context = {'execution_assignment': assignment, 'execution_progress': {
                   'execution_handoff_refs': summary['handoff_refs'], 'execution_result_refs': summary['result_refs'],
                   'execution_completed': summary['completed']},
               'api_service': assignment['service'], 'api_received_progress': summary['received_progress'],
               'api_execution_completed': summary['completed'], 'operations_run': summary['operations'],
               'submission_uncertain': summary['submission_uncertain'],
               'execution_resource_capabilities': [resource],
               'execution_initial_information': ctx.settings['initial_information'],
               'credit_binding': summary['operational_credit_binding'],
               'tools': catalog, 'tool_knowledge': knowledge,
               'launch_instruction_library': launch.context(),
               'resource_launch_instructions': launch.for_resource(ctx.settings['resources'][resource_id]),
               'time_accounting': time_accounting(ctx.clock.progress_time), 'feedback': feedback}
    if 'launch_instructions' in assignment:
        context['selected_launch_instructions'] = launch.materialize(assignment['launch_instructions'])
    selected = _selected_execution_task(summary, resource)
    if selected is not None:
        context['selected_execution_task'] = selected
    return ModelRequest('REASONING', instructions(assignment, knowledge=True, launch_library=True), context,
                        generation_schema(_selection_schema(catalog)))


def action(response, summary, records, ctx):
    schema = _selection_schema(ctx.services['job_access'].read('launch_catalog', summary['assignment']))
    try:
        selection = decode_response(response, schema)
        Draft202012Validator(schema).validate(selection)
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='selection'))
    return ToolCall('launch_operation', {'operation': selection['tool'], 'arguments': selection['arguments'],
                                         'assignment': summary['assignment'], 'input_refs': summary['input_refs']})
