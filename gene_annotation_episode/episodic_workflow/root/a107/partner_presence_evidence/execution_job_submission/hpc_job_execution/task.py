"""The task: write and run shell commands for the assigned job, one command per unit.

Carried from the old ``terminal_execution.py`` (``TerminalExecutionBehavior``: ``instructions``, ``catalog``,
``execute``, ``_resource_information``, ``_resource_instructions``), ``work_operations.py``, ``task_instructions.py``,
``task.py`` and ``task_decision.py`` (the model may select the ``tool`` action only; the old
``permitted_common_actions`` was ``('tool',)``). The exec_command catalog (the old ``operation_catalog('hpc')`` of
the old shared root's ``execution_operation_information``, which is not read) is written here from the old
``terminal_execution.py``: the tool name ``exec_command`` and its arguments ``cmd``, ``workdir``, ``env``,
``target``, which ``TerminalExecution.validate_action`` checks. One unit is one ``exec_command``. The task always offers a unit and never ends the Episode: only the yield
controller does. The model's old ``report_update`` (the parent-written interpretation form) is not carried: the
return's facts are recorded facts (``messages/final_to_parent.py``).

Settings this episode reads (the old ``configuration.py`` values; ``ctx.settings``): ``resource`` (the configured
HPC resource: kind ``pbs_ssh``, workspace, ssh_argv, python_executable, account, scheduler, optional policy and
launch prompt entry), ``initial_information`` (the recorded inventory of that resource, optional),
``coordinator_workspace`` (the local run directory ``target=coordinator`` commands work in),
``launch_instructions_directory`` and ``knowledge_library_directory`` (optional), ``task_yield_profiles``
(``yield_estimator.py``).

BLOCKED-ON-JOB-SERVICE: the transport that runs the command on the resource (the old ``TerminalExecution.execute``
over a file-backed ``PracticalState``) is not wrapped as a service. ``run_command`` names the service and the call
it wants and raises where it is reached."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import PurePosixPath

from jsonschema import ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.partner_presence_evidence.acquisition import (
    AcquisitionError)
from gene_annotation_episode.episodic_workflow.episode_support.findings.partner_presence_evidence.terminal_scientific_evidence import (
    finalize_scientific_command, terminal_artifact_paths)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.partner_presence_evidence.terminal_execution import (
    TerminalExecution)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import (
    ContractError, obj, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.practical_execution_records import (
    RECEIPT_VERSION, assess_validations, canonical, digest, validate_receipt)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

from .goal import GOAL

CHILD_SLOTS = {}
SERVICES = ('job_access',)

TRANSPORT_ERROR = 'a107_hpc_job_execution_selection_has_no_argument_transport'
RECEIPT_INFORMATION_VERSION = 'practical_receipt_information_v1'

# The old terminal goal text (``TerminalGoal.instructions``), unchanged.
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
    """The one tool, identical for every resource (the old ``terminal_contracts.operation_catalog``)."""
    return [deepcopy(EXEC_COMMAND)]


def terminal(settings):
    """The library's validator of an assignment and of a command for the configured resource."""
    return TerminalExecution(settings['resource'], coordinator_workspace=settings['coordinator_workspace'],
                             artifact_selector=terminal_artifact_paths)


def _now():
    return datetime.now(timezone.utc).isoformat()


async def run_command(assignment, command, ctx):
    """Run one command on the resource (or in the coordinator run directory) and return the old factual outcome
    ``{'facts': ..., 'native_outcome': ...}``.

    BLOCKED-ON-JOB-SERVICE: job_access; wanted call: ``await ctx.services['job_access'].exec_command(assignment,
    command, key=ctx.operation_key, resumed=ctx.resumed)``, idempotent on ``ctx.operation_key`` (a submission whose
    outcome is uncertain must be found again, not repeated). The library has the transport (``TerminalExecution
    .execute`` over a file-backed practical state) but no service wraps it."""
    raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access; wanted call: await '
                              "ctx.services['job_access'].exec_command(assignment, command, "
                              'key=ctx.operation_key, resumed=ctx.resumed)')
    return await ctx.services['job_access'].exec_command(assignment, command, key=ctx.operation_key,
                                                         resumed=ctx.resumed)


async def exec_command(arguments, ctx):
    """The old ``TerminalOperations.execute``: run the command, turn an execution error into a recorded failure,
    carry ``cwd`` and ``environment`` forward only when it ran on the resource inside the workspace, assess the
    assignment's validations, save the receipt and return it with its record."""
    assignment, command, before = arguments['assignment'], arguments['command'], arguments['context_before']
    started_at = _now()
    try:
        outcome = await run_command(assignment, command, ctx)
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
    body = {'version': RECEIPT_INFORMATION_VERSION, 'run_id': ctx.run_id, 'episode_id': ctx.episode_id,
            'assignment_sha256': digest(assignment), 'receipt': receipt}
    # The old ``PracticalReceiptInformation.publish`` wrote the receipt as a source record of the old runner's
    # binding context; here the receipt is one artifact written through custody and held as produced.
    reference = ctx.store.artifact(canonical(body), 'application/json')
    return {'status': 'completed', 'receipt': receipt, 'receipt_ref': reference,
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


def resource_information(settings):
    """The old ``TerminalSummary._resource_information``: what the model is shown of the configured resource."""
    configuration = settings['resource']
    return {'resource_kind': 'hpc', 'workspace': configuration['workspace'],
            **{name: deepcopy(configuration[name])
               for name in ('kind', 'policy', 'account', 'ssh_argv', 'python_executable', 'scheduler')
               if name in configuration},
            'inventory_snapshot': deepcopy(settings.get('initial_information'))}


def instructions(*, resource_sections, knowledge, launch_library):
    """The old composition (``TerminalGoal.instructions`` then ``instructions.instructions``) for the one tool the
    episode offers: the goal text, the resource instructions of the frozen library, then the tool-knowledge and
    launch-library texts when those libraries are present. The reasoning-commit, ``pending_child_delivery``,
    wait, native-event and decision-exchange paragraphs describe actions this episode never had or no longer
    has."""
    text = INSTRUCTIONS
    if resource_sections:
        text += '\nResource instructions supplied from the frozen library:\n' + '\n\n'.join(
            section['text'] for section in resource_sections['sections'])
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if launch_library is not None:
        text += LAUNCH_INSTRUCTIONS
    return text


def decide(summary, feedback, ctx):
    """Ask the model for the next command, shown the assignment, the resource, the practical progress and
    completion, its last command, the tool, the measured time, the yield table and the library listings (the old
    decision state and inputs, over this episode's summary). A wrong assignment for the configured resource fails
    here (it is a wrong commission)."""
    settings = ctx.settings
    terminal(settings).validate_assignment(summary['assignment'])
    knowledge_directory = settings.get('knowledge_library_directory')
    launch_directory = settings.get('launch_instructions_directory')
    launch = None if launch_directory is None else LaunchInstructions(launch_directory)
    resource_sections = None if launch is None else launch.for_resource(settings['resource'])
    knowledge = None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()
    context = {'goal': GOAL, 'execution_assignment': summary['assignment'],
               'execution_resource': resource_information(settings),
               'coordinator_workspace': settings['coordinator_workspace'],
               'execution_progress': summary['progress'], 'execution_completion': summary['completion_proof'],
               'current_credit': summary['progress']['credit'],
               'credit_binding': summary['progress']['operational_credit_binding'],
               'execution_context': summary['context'], 'last_local_outcome': summary['last_command'],
               'tools': operation_catalog(), 'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['action_yields'], 'tool_knowledge': knowledge,
        'launch_instruction_library': None if launch is None else launch.context(),
        'selected_launch_instructions': (None if launch is None or 'launch_instructions' not in summary['assignment']
                                         else launch.materialize(summary['assignment']['launch_instructions']))},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(resource_sections=resource_sections, knowledge=knowledge,
                                                  launch_library=context.get('launch_instruction_library')),
                        context, generation_schema(selection_schema()))


def action(response, summary, records, ctx):
    """Turn the model's answer into one ``exec_command`` call, or reject it (no unit). An answer that does not fit
    the schema, or a command the resource's own validation refuses (a workdir outside the workspace, a malformed
    command or environment, an unavailable target), is invalid. The command travels with the assignment and the
    working context it starts from, because a tool is handed no summary."""
    schema = selection_schema()
    try:
        value = decode_response(response, schema)
        validate_schema(value, schema)
        command = value['selection']['arguments']
        terminal(ctx.settings).validate_action(summary['assignment'], 'exec_command', command)
    except (ValueError, KeyError, TypeError, ValidationError, ContractError) as error:
        raise Rejected(rejection_feedback(error, category='selection'))
    return ToolCall('exec_command', {'assignment': summary['assignment'], 'command': command,
                                     'context_before': summary['context']})
