"""The task: the execution agent for the assigned job on the assigned HPC resource.

The model writes the shell command; the episode's one tool, ``exec_command``, runs it (on the resource or, for
supplied-input and transport work, in the coordinator's run directory) through the ``job_access`` service. The tool
turns what the service returns into the receipt of the command: its actual result, the working context after it and
the validations of the original requirements it satisfied. The task always offers a unit and never ends the
Episode: no stopping budget is added; the yield controller stops it when the assignment's completion is verified or
the forecast no longer pays for another command.

BLOCKED-ON-JOB-SERVICE: the ``job_access`` service has no implementation yet (LAUNCH_MONITOR_EXTRACT_MECHANICS.md,
section 5 and "Not provided yet" items 4 and 5): the tool names it and calls it, and raises where the call is made.
The job record kind for the handoff (a ``job_ledger`` row) has no declaration in the library: the tool raises where
that row would be written."""
import inspect
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.evolutionary_history_evidence.acquisition import (
    AcquisitionError)
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.native_terminal_transport import (
    TerminalExecution)
from gene_annotation_episode.episodic_workflow.episode_support.findings.evolutionary_history_evidence.terminal_scientific_evidence import (
    finalize_scientific_command, terminal_artifact_paths)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import (
    ContractError, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.practical_execution_records import (
    RECEIPT_VERSION, assess_validations, canonical, digest, validate_receipt)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

CHILD_SLOTS = {}
SERVICES = ('job_access',)

# The old ``native_tool_contracts.operation_catalog('hpc')``: the one general capability.
EXEC_COMMAND = {
    'name': 'exec_command',
    'description': 'Execute the shell command you write on the assigned resource. Use normal shell/file tools to '
                   'inspect files, author scripts, prepare an environment, run software, or submit/observe the '
                   'actual job as needed. Returns its actual output and saved action receipt. workdir and env apply '
                   'to this command; select them explicitly on each action.',
    'input_schema': {'type': 'object', 'properties': {
        'cmd': {'anyOf': [{'type': 'string', 'minLength': 1},
                          {'type': 'array', 'minItems': 1, 'items': {'type': 'string', 'minLength': 1}}]},
        'workdir': {'type': 'string', 'minLength': 1},
        'target': {'type': 'string', 'enum': ['resource', 'coordinator'],
                   'description': 'Assigned resource (default), or local coordinator run directory for input-file '
                                  'work.'},
        'env': {'type': 'object', 'additionalProperties': {'type': 'string'}}},
        'required': ['cmd', 'workdir', 'env'], 'additionalProperties': False}}

# The old ``native_goal.HPCExecutionNativeGoal.instructions`` text, unchanged.
GOAL_INSTRUCTION = (
    "You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run "
    "the shell code needed for that job. Choose scripts, environment preparation, software invocation and recovery "
    "from the actual resource instructions and observed results. No sequence of setup or job-stage operations is "
    "prescribed. Preserve the caller's scientific inputs, desired outputs and acceptance criteria. Historical "
    "inventory is context, not proof of present usability. Each command is one ordinary episode action: its actual "
    "result and earned credit enter the iterator, including failure or zero progress. Host bookkeeping records "
    "command versions and actual native job identities; do not maintain a parallel receipt ledger. If a submission "
    "outcome is uncertain, investigate that original submission rather than create a duplicate. Use the provided "
    "resource-specific instructions, account, storage and existing authentication route. workdir and env apply to "
    "the selected command only. target=resource runs on the assigned resource; target=coordinator runs in the local "
    "run directory for supplied-input and transport work. Both are ordinary journaled actions; resource computation "
    "belongs on its actual allocation. For coordinator-side transfers, execution_resource.ssh_argv, when present, is "
    "the exact configured transport prefix. Append the remote shell command as its final argument and preserve "
    "stdin. The supplied configuration gives the existing connection details. target=resource uses that transport "
    "directly. The episode iterator decides continuation from credit; add no stopping budget.")
ANSWER_INSTRUCTION = (
    ' Answer with tool exec_command and its operands as one JSON object in arguments_json: cmd, workdir, env and, '
    'optionally, target.')
RESOURCE_KEYS = ('kind', 'policy', 'account', 'ssh_argv', 'python_executable', 'scheduler')


def _operations(settings, assignment):
    """The transport's own validation of the assignment and of an action (old ``TerminalExecution``, built by the
    old ``HPCExecutionNativeConfiguration._operations``); a configuration or assignment it refuses raises and fails
    the run: it is not a model answer. The configured resource of this episode is the PBS resource."""
    resource = settings['resource']
    if resource.get('kind') != 'pbs_ssh':
        raise ValueError('execution_resource_assignment_mismatch')
    operations = TerminalExecution(resource, coordinator_workspace=settings['coordinator_workspace'],
                                   artifact_selector=terminal_artifact_paths)
    operations.validate_assignment(assignment)
    return operations


def _failure(error):
    return {'facts': {}, 'native_outcome': {'failure': {
        'code': 'execution_action_failed', 'exception_type': type(error).__name__, 'detail': str(error)}}}


def _now():
    return datetime.now(timezone.utc).isoformat()


async def exec_command(arguments, ctx):
    """Run the selected command through ``job_access`` and keep its receipt as a record the Episode holds.

    The service executes once per ``ctx.operation_key`` and returns the raw outcome of the command. Here, as the old
    ``HPCExecutionNativeToolActions.execute`` did: a command that fails is still a completed action with its
    receipt (the failure is its outcome); the scientific command proof is finalized; the working context after the
    command is tracked; the validations of the original requirements are assessed; the receipt is built."""
    assignment, command, before = arguments['assignment'], arguments['arguments'], arguments['context_before']
    service = ctx.services['job_access']
    if not hasattr(service, 'exec_command'):
        raise NotImplementedError(
            'BLOCKED-ON-JOB-SERVICE: job_access.exec_command(assignment, arguments, *, run_id, episode_id, key); '
            'wanted call: await ctx.services["job_access"].exec_command(arguments["assignment"], '
            'arguments["arguments"], run_id=ctx.run_id, episode_id=ctx.episode_id, key=ctx.operation_key)')
    started_at = _now()
    try:
        reply = service.exec_command(assignment, command, run_id=ctx.run_id, episode_id=ctx.episode_id,
                                     key=ctx.operation_key)
        if inspect.isawaitable(reply):
            reply = await reply
        outcome = reply
    except (ValueError, TypeError, OSError, AcquisitionError) as error:
        outcome = _failure(error)
    outcome = finalize_scientific_command(assignment, command, outcome)
    after = deepcopy(before)
    if command.get('target', 'resource') == 'resource' and Path(command['workdir']).is_relative_to(
            assignment['workspace']):
        after.update({'cwd': command['workdir'], 'environment': command['env']})
    after['revision'] += int(any(after[name] != before[name] for name in ('cwd', 'environment')))
    validations = assess_validations(assignment, outcome, after, tool_name='exec_command')
    receipt = validate_receipt({
        'version': RECEIPT_VERSION, 'run_id': ctx.run_id, 'episode_id': ctx.episode_id,
        'assignment_sha256': digest(assignment), 'operation_key': ctx.operation_key, 'tool_name': 'exec_command',
        'arguments': command, 'context_before': before, 'context_after': after, 'outcome': outcome,
        'validations': validations, 'started_at': started_at, 'finished_at': _now()})
    receipt_ref = ctx.store.artifact(canonical(receipt), 'application/json')
    if receipt['outcome']['facts'].get('requested_job', {}).get('handoff') is not None:
        raise NotImplementedError(
            "BLOCKED-ON-JOB-SERVICE: job record kind (the handoff row of the job ledger, MECHANICS section 6); "
            "wanted call: ctx.store.table(JOB_LEDGER).put({'job': <native job identity>, 'event': 'handoff', "
            "'at': <submission time UTC>, 'detail': <job kind, how to find the job, launch estimates>, "
            "'source_ref': receipt_ref})")
    return {'status': 'completed', 'receipt': receipt, 'receipt_ref': receipt_ref,
            'operation_ref': digest(ctx.operation_key)}


TOOLS = {'exec_command': exec_command}


def _resource(settings):
    """The old ``_resource_information``: the configured resource and the recorded inventory (context only)."""
    resource = settings['resource']
    return {'resource_kind': 'hpc', 'workspace': resource['workspace'],
            **{name: resource[name] for name in RESOURCE_KEYS if name in resource},
            'inventory_snapshot': settings['initial_information'].get('hpc')}


def _instructions(settings):
    library = LaunchInstructions(settings['launch_instructions_directory'])
    text = GOAL_INSTRUCTION
    selected = library.for_resource(settings['resource'])
    if selected:
        text += '\nResource instructions supplied from the frozen library:\n' + '\n\n'.join(
            section['text'] for section in selected['sections'])
    return text + KNOWLEDGE_INSTRUCTIONS + LAUNCH_INSTRUCTIONS + ANSWER_INSTRUCTION, library


def _task_text(summary):
    """The old HPC prompt presentation, over this episode's own summary: the assignment, what the commands did so
    far and the verified completion."""
    parts = ['TASK', '', 'Execute the assigned job on the HPC resource.', '', 'Assignment', '',
             json.dumps(summary['assignment'], indent=1, sort_keys=True)]
    if summary['commands']:
        parts.extend(['', 'Commands run so far', '', json.dumps(summary['commands'], indent=1, sort_keys=True)])
    parts.extend(['', 'Progress', '', json.dumps({'execution_progress': summary['execution_progress'],
                                                  'execution_completion': summary['execution_completion']},
                                                 indent=1, sort_keys=True)])
    return '\n'.join(parts)


def _output_schema():
    return {'type': 'object', 'additionalProperties': False, 'required': ['tool', 'arguments_json'],
            'properties': {'tool': {'enum': ['exec_command']},
                           'arguments_json': {'type': 'string',
                                              'description': 'The exec_command operands as one JSON object: '
                                                             + json.dumps(EXEC_COMMAND['input_schema'],
                                                                          sort_keys=True)}}}


def decide(summary, feedback, ctx):
    """One command: the model chooses it from the assignment, the resource, the commands run and their credit."""
    settings = ctx.settings
    assignment = summary['assignment']
    instructions, library = _instructions(settings)
    selected = library.materialize(assignment.get('launch_instructions'))
    knowledge = ToolKnowledge(settings['tool_knowledge_directory'])
    context = {'task': _task_text(summary), 'feedback': feedback, 'execution_assignment': assignment,
               'execution_resource': _resource(settings),
               'execution_resource_information': settings['initial_information'],
               'coordinator_workspace': settings['coordinator_workspace'],
               'execution_progress': summary['execution_progress'],
               'execution_completion': summary['execution_completion'], 'commands': summary['commands'],
               'launch_instruction_library': library.context(), 'tool_knowledge': knowledge.context(),
               'selected_launch_instructions': selected, 'controller': summary['controller'],
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    return ModelRequest('REASONING', instructions, context, _output_schema())


def action(response, summary, records, ctx):
    """The one command the answer selects, or a rejection: it names exec_command and operands that fit its
    schema and the resource (a workdir inside the workspace, a command text, an environment)."""
    operations = _operations(ctx.settings, summary['assignment'])
    try:
        if response['tool'] != 'exec_command':
            raise ValueError('execution_tool_not_available')
        arguments = json.loads(response['arguments_json'])
        if not isinstance(arguments, dict):
            raise ValueError('arguments_json_must_be_a_JSON_object')
        validate_schema(arguments, EXEC_COMMAND['input_schema'])
        operations.validate_action(summary['assignment'], 'exec_command', arguments)
    except (KeyError, TypeError, ValueError, ContractError) as error:
        raise Rejected(rejection_feedback(error, category='arguments_or_reference'))
    return ToolCall('exec_command', {'arguments': arguments, 'assignment': summary['assignment'],
                                     'context_before': summary['context']})
