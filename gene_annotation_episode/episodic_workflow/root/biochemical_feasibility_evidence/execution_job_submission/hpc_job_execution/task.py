"""The task: write and run shell commands for the assigned job, one command per unit.

Carried from the old ``terminal_execution.py`` (``TerminalExecutionBehavior``: ``instructions``,
``decision_context``, ``catalog``, ``execute``, ``_resource_information``, ``_resource_instructions``), the old
``task_instructions.py`` composition, ``presentation.py`` (the renderer choice) and the old ``task.py`` /
``task_decision.py`` action loop (the model may select the ``tool`` action only; ``permitted_common_actions``).
One unit is one ``exec_command``. The task always offers a unit and never ends the Episode: only the yield
controller does. The model's old ``report_update`` (the parent-written interpretation form) is not carried: the
return's facts are recorded facts (``messages/final_to_parent.py``).

Settings this episode reads (the old ``configuration.py`` values; ``ctx.settings``): ``resources`` (the configured
resources by id; the assignment's ``resource_id`` selects one, kind ``pbs_ssh``: workspace, ssh_argv,
python_executable, account, scheduler, optional policy and launch prompt entry), ``initial_information`` (the
recorded inventory of each resource, optional per resource), ``coordinator_workspace`` (the local run directory
``target=coordinator`` commands work in), ``launch_instructions_directory`` and ``tool_knowledge_directory``
(optional: the old workflow-level libraries), ``task_yield_profiles`` (``yield_estimator.py``).

BLOCKED-ON-JOB-SERVICE: the transport that runs the command on the resource (the old ``TerminalExecution.execute``
over a file-backed ``PracticalState``) is not wrapped as a service, and the handoff record kind of the job ledger
is not declared. ``exec_command`` names the service and the record and calls them, and raises where each is
missing."""
import inspect
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import PurePosixPath

from jsonschema import ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.biochemical_feasibility_evidence.acquisition import (
    AcquisitionError)
from gene_annotation_episode.episodic_workflow.episode_support.findings.biochemical_feasibility_evidence.terminal_scientific_evidence import (
    finalize_scientific_command, terminal_artifact_paths)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.biochemical_feasibility_evidence.terminal_execution import (
    TerminalExecution)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.domain import (
    ContractError, obj, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.practical_execution_records import (
    RECEIPT_VERSION, assess_validations, canonical, digest, validate_receipt)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

from .goal import GOAL

CHILD_SLOTS = {}
SERVICES = ('job_access',)

TRANSPORT_ERROR = 'a110_hpc_job_execution_selection_has_no_argument_transport'
RESOURCE_KEYS = ('kind', 'policy', 'account', 'ssh_argv', 'python_executable', 'scheduler')

# The old terminal goal text (``TerminalExecutionBehavior.instructions``), unchanged.
INSTRUCTIONS = "You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run the shell code needed for that job. Choose scripts, environment preparation, software invocation and recovery from the actual resource instructions and observed results. No sequence of setup or job-stage operations is prescribed. Preserve the caller's scientific inputs, desired outputs and acceptance criteria. Historical inventory is context, not proof of present usability. Each command is one ordinary episode action: its actual result and earned credit enter the iterator, including failure or zero progress. Host bookkeeping records command versions and actual native job identities; do not maintain a parallel receipt ledger. If a submission outcome is uncertain, investigate that original submission rather than create a duplicate. Use the provided resource-specific instructions, account, storage and existing authentication route. workdir and env apply to the selected command only. target=resource runs on the assigned resource; target=coordinator runs in the local run directory for supplied-input and transport work. Both are ordinary journaled actions; resource computation belongs on its actual allocation. For coordinator-side transfers, execution_resource.ssh_argv, when present, is the exact configured transport prefix. Append the remote shell command as its final argument and preserve stdin. The supplied configuration gives the existing connection details. target=resource uses that transport directly. The episode iterator decides continuation from credit; add no stopping budget."

EXEC_COMMAND = {
    'name': 'exec_command',
    'description': 'Execute the shell command you write on the assigned resource. Use normal shell/file tools to inspect files, author scripts, prepare an environment, run software, or submit/observe the actual job as needed. Returns its actual output and saved action receipt. workdir and env apply to this command; select them explicitly on each action.',
    'input_schema': {'type': 'object', 'properties': {
        'cmd': {'anyOf': [{'type': 'string', 'minLength': 1},
                          {'type': 'array', 'minItems': 1, 'items': {'type': 'string', 'minLength': 1}}]},
        'workdir': {'type': 'string', 'minLength': 1},
        'target': {'type': 'string', 'enum': ['resource', 'coordinator'],
                   'description': 'Assigned resource (default), or local coordinator run directory for input-file work.'},
        'env': {'type': 'object', 'additionalProperties': {'type': 'string'}}},
        'required': ['cmd', 'workdir', 'env'], 'additionalProperties': False}}


def operation_catalog():
    """The one tool, identical for every resource (the old library ``operation_catalog('hpc')``)."""
    return [deepcopy(EXEC_COMMAND)]


def _resource_configuration(settings, assignment):
    """The configured resource the assignment names. The old role check: the assignment is for an HPC resource
    (kind ``pbs_ssh``) that is configured (``execution_resource_assignment_mismatch``)."""
    resource = settings['resources'].get(assignment['resource_id'])
    if resource is None or resource.get('kind') != 'pbs_ssh' or assignment['resource_kind'] != 'hpc':
        raise ValueError('execution_resource_assignment_mismatch')
    return resource


def terminal(settings, assignment):
    """The library's validator of an assignment and of a command for the assignment's configured resource (the old
    ``TerminalExecutionBehavior._operations`` and ``_assignment``). A configuration or an assignment it refuses
    raises: it is a wrong commission, not a model answer."""
    operations = TerminalExecution(_resource_configuration(settings, assignment),
                                   coordinator_workspace=settings['coordinator_workspace'],
                                   artifact_selector=terminal_artifact_paths)
    operations.validate_assignment(assignment)
    return operations


def _now():
    return datetime.now(timezone.utc).isoformat()


async def exec_command(arguments, ctx):
    """The old ``TerminalExecutionBehavior.execute``: run the command, turn an execution error into a recorded
    failure, finalize the scientific command, carry ``cwd`` and ``environment`` forward only when it ran on the
    resource inside the workspace, assess the assignment's validations, save the receipt and return it with its
    record. The command travels with the assignment and the working context it starts from, because a tool is
    handed no summary.

    BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ``await ctx.services['job_access'].exec_command(assignment,
    command, run_id=ctx.run_id, episode_id=ctx.episode_id, key=ctx.operation_key, resumed=ctx.resumed)``,
    idempotent on ``ctx.operation_key`` (a submission whose outcome is uncertain must be found again, not
    repeated). The library has the transport (``TerminalExecution.execute`` over a file-backed practical state) but
    no service wraps it."""
    assignment, command, before = arguments['assignment'], arguments['command'], arguments['context_before']
    service = ctx.services['job_access']
    if not hasattr(service, 'exec_command'):
        raise NotImplementedError(
            'BLOCKED-ON-JOB-SERVICE: job_access.exec_command(assignment, command, *, run_id, episode_id, key, '
            "resumed); wanted call: await ctx.services['job_access'].exec_command(assignment, command, "
            'run_id=ctx.run_id, episode_id=ctx.episode_id, key=ctx.operation_key, resumed=ctx.resumed)')
    started_at = _now()
    try:
        reply = service.exec_command(assignment, command, run_id=ctx.run_id, episode_id=ctx.episode_id,
                                     key=ctx.operation_key, resumed=ctx.resumed)
        outcome = await reply if inspect.isawaitable(reply) else reply
    except (ValueError, TypeError, OSError, AcquisitionError) as error:
        outcome = {'facts': {}, 'native_outcome': {'failure': {
            'code': 'execution_action_failed', 'exception_type': type(error).__name__, 'detail': str(error)}}}
    outcome = finalize_scientific_command(assignment, command, outcome)
    after = deepcopy(before)
    if (command.get('target', 'resource') == 'resource'
            and PurePosixPath(command['workdir']).is_relative_to(assignment['workspace'])):
        after.update({'cwd': command['workdir'], 'environment': command['env']})
    after['revision'] += int(any(after[name] != before[name] for name in ('cwd', 'environment')))
    validations = assess_validations(assignment, outcome, after, tool_name='exec_command')
    receipt = validate_receipt({
        'version': RECEIPT_VERSION, 'run_id': ctx.run_id, 'episode_id': ctx.episode_id,
        'assignment_sha256': digest(assignment), 'operation_key': ctx.operation_key, 'tool_name': 'exec_command',
        'arguments': command, 'context_before': before, 'context_after': after, 'outcome': outcome,
        'validations': validations, 'started_at': started_at, 'finished_at': _now()})
    # The old ``PracticalReceiptInformation.publish`` wrote the receipt as a source record of the old runner's
    # binding context; here the receipt is one artifact written through custody and held as produced.
    receipt_ref = ctx.store.artifact(canonical(receipt), 'application/json')
    if receipt['outcome'].get('facts', {}).get('requested_job', {}).get('handoff') is not None:
        raise NotImplementedError(
            "BLOCKED-ON-JOB-SERVICE: job record kind (the handoff row of the job ledger, MECHANICS section 6); "
            "wanted call: ctx.store.table(JOB_LEDGER).put({'job': <native job identity>, 'event': 'handoff', "
            "'at': <submission time UTC>, 'detail': <job kind, how to find the job, launch estimates>, "
            "'source_ref': receipt_ref})")
    return {'status': 'completed', 'receipt': receipt, 'receipt_ref': receipt_ref,
            'operation_ref': digest(ctx.operation_key)}


TOOLS = {'exec_command': exec_command}


def selection_schema():
    """What the model answers with: the one tool and its arguments (the old action schema, tool kind only)."""
    return obj({'selection': {'anyOf': [obj({'kind': {'const': 'tool'}, 'tool': {'const': EXEC_COMMAND['name']},
                                             'arguments': EXEC_COMMAND['input_schema']})]}})


def generation_schema(schema):
    return strict_output_schema(schema, open_records_as_text=False, argument_transport_error=TRANSPORT_ERROR)


def decode_response(value, schema):
    return decode_strict_output(value, schema, open_records_as_text=False, argument_transport_error=TRANSPORT_ERROR)


def resource_information(settings, assignment):
    """The old ``_resource_information``: what the model is shown of the configured resource and its recorded
    inventory (historical context, not proof of present usability)."""
    configuration = _resource_configuration(settings, assignment)
    return {'resource_kind': 'hpc', 'workspace': configuration['workspace'],
            **{name: deepcopy(configuration[name]) for name in RESOURCE_KEYS if name in configuration},
            'inventory_snapshot': deepcopy(settings.get('initial_information', {}).get(assignment['resource_id']))}


def instructions(*, resource_sections, knowledge, launch_library):
    """The old composition (``TerminalExecutionBehavior.instructions`` then ``task_instructions.instructions``) for
    the one tool the episode offers: the goal text, the resource instructions of the frozen library, then the
    tool-knowledge and launch-library texts when those libraries are present. The reasoning-commit,
    ``pending_child_delivery``, wait, native-event and decision-exchange paragraphs describe actions this episode
    never had or no longer has."""
    text = INSTRUCTIONS
    if resource_sections:
        text += '\nResource instructions supplied from the frozen library:\n' + '\n\n'.join(
            section['text'] for section in resource_sections['sections'])
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if launch_library is not None:
        text += LAUNCH_INSTRUCTIONS
    return text


def _task_text(summary):
    """The old HPC prompt presentation over this episode's own summary: the assignment, what the commands did so
    far, and the progress and verified completion."""
    parts = ['TASK', '', 'Execute the assigned job on the HPC resource.', '', 'Assignment', '',
             json.dumps(summary['assignment'], indent=1, sort_keys=True)]
    if summary['commands']:
        parts.extend(['', 'Commands run so far', '', json.dumps(summary['commands'], indent=1, sort_keys=True)])
    parts.extend(['', 'Progress', '', json.dumps({'execution_progress': summary['progress'],
                                                  'execution_completion': summary['completion_proof']},
                                                 indent=1, sort_keys=True)])
    return '\n'.join(parts)


def decide(summary, feedback, ctx):
    """Ask the model for the next command, shown the assignment, the resource, the practical progress and
    completion, its commands so far, the tool, the measured time, the yield table and the library listings (the old
    decision state and inputs, over this episode's summary). A wrong assignment for the configured resource fails
    here (it is a wrong commission)."""
    settings = ctx.settings
    assignment = summary['assignment']
    terminal(settings, assignment)
    knowledge_directory = settings.get('tool_knowledge_directory')
    launch_directory = settings.get('launch_instructions_directory')
    launch = None if launch_directory is None else LaunchInstructions(launch_directory)
    resource_sections = None if launch is None else launch.for_resource(
        _resource_configuration(settings, assignment))
    knowledge = None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()
    context = {'goal': GOAL, 'task': _task_text(summary), 'message': summary['message'],
               'execution_assignment': assignment,
               'execution_resource': resource_information(settings, assignment),
               'coordinator_workspace': settings['coordinator_workspace'],
               'execution_progress': summary['progress'], 'execution_completion': summary['completion_proof'],
               'current_credit': summary['progress']['credit'],
               'credit_binding': summary['progress']['operational_credit_binding'],
               'execution_context': summary['context'], 'commands': summary['commands'],
               'last_local_outcome': summary['last_command'],
               'tools': operation_catalog(), 'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['action_yields'], 'tool_knowledge': knowledge,
        'launch_instruction_library': None if launch is None else launch.context(),
        'selected_launch_instructions': (None if launch is None or 'launch_instructions' not in assignment
                                         else launch.materialize(assignment['launch_instructions']))},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(resource_sections=resource_sections, knowledge=knowledge,
                                                  launch_library=context.get('launch_instruction_library')),
                        context, generation_schema(selection_schema()))


def action(response, summary, records, ctx):
    """Turn the model's answer into one ``exec_command`` call, or reject it (no unit). An answer that does not fit
    the schema, or a command the resource's own validation refuses (a workdir outside the workspace, a malformed
    command or environment, an unavailable target), is invalid. The command travels with the assignment and the
    working context it starts from, because a tool is handed no summary."""
    operations = terminal(ctx.settings, summary['assignment'])
    schema = selection_schema()
    try:
        value = decode_response(response, schema)
        validate_schema(value, schema)
        command = value['selection']['arguments']
        operations.validate_action(summary['assignment'], 'exec_command', command)
    except (ValueError, KeyError, TypeError, ValidationError, ContractError) as error:
        raise Rejected(rejection_feedback(error, category='selection'))
    return ToolCall('exec_command', {'assignment': summary['assignment'], 'command': command,
                                     'context_before': summary['context']})
