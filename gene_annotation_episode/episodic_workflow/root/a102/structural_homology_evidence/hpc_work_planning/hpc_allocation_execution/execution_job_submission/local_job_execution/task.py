"""The task: the execution agent for one assigned job on one local resource. Each unit is one shell command the
model writes (``exec_command``); its actual result, including a failure or no progress, enters the iterator with
the credit the saved receipts then earn. The task always offers a unit and never ends the Episode: its completion
controller stops it when the assignment's requirement credit is reached.

The command is run through the ``job_access`` service (see the BLOCKED-ON-JOB-SERVICE notes in ``exec_command``);
a decision reads what the model is shown about earlier estimates from the ``estimate_table`` service."""
from copy import deepcopy
import json
from pathlib import PurePosixPath

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.structural_homology_evidence.acquisition import (
    AcquisitionError)
from gene_annotation_episode.episodic_workflow.episode_support.findings.structural_homology_evidence.terminal_scientific_evidence import (
    finalize_scientific_command, terminal_artifact_paths)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.structural_homology_evidence.terminal_execution import (
    TerminalExecution)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.practical_execution_records import (
    assess_validations, canonical, digest)

CHILD_SLOTS = {}
SERVICES = ('job_access', 'estimate_table')
TOOL = 'exec_command'
MODEL_ROLE = 'REASONING'
RECEIPT_PROVIDER = 'episode.practical_receipt'
RECEIPT_VERSION = 'practical_receipt_information_v1'
ASSIGNMENT_SNAPSHOT_VERSION = 'practical_receipt_assignment_v1'

INSTRUCTIONS = (
    "You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run "
    "the shell code needed for that job. Choose scripts, environment preparation, software invocation and recovery "
    "from the actual resource instructions and observed results. No sequence of setup or job-stage operations is "
    "prescribed. Preserve the caller's scientific inputs, desired outputs and acceptance criteria. Historical "
    "inventory is context, not proof of present usability. Each command is one ordinary episode action: its actual "
    "result and earned credit enter the iterator, including failure or zero progress. Host bookkeeping records "
    "command versions and actual native job identities; do not maintain a parallel receipt ledger. If a "
    "submission outcome is uncertain, investigate that original submission rather than create a duplicate. Use "
    "the provided resource-specific instructions, account, storage and existing authentication route. workdir and "
    "env apply to the selected command only. target=resource runs on the assigned resource; target=coordinator "
    "runs in the local run directory for supplied-input and transport work. Both are ordinary journaled actions; "
    "resource computation belongs on its actual allocation. For coordinator-side transfers, "
    "execution_resource.ssh_argv, when present, is the exact configured transport prefix. Append the remote shell "
    "command as its final argument and preserve stdin. The supplied configuration gives the existing connection "
    "details. target=resource uses that transport directly. The episode iterator decides continuation from "
    "credit; add no stopping budget.")

_ENVIRONMENT_ITEM = {'type': 'object', 'additionalProperties': False, 'required': ['name', 'value'],
                     'properties': {'name': {'type': 'string', 'pattern': '^[A-Za-z_][A-Za-z0-9_]*$'},
                                    'value': {'type': 'string'}}}
OUTPUT_SCHEMA = {
    'type': 'object', 'additionalProperties': False, 'required': ['cmd', 'workdir', 'target', 'env'],
    'properties': {
        'cmd': {'anyOf': [{'type': 'string', 'minLength': 1},
                          {'type': 'array', 'minItems': 1, 'items': {'type': 'string', 'minLength': 1}}],
                'description': 'Shell code (a string) or an argv list.'},
        'workdir': {'type': 'string', 'minLength': 1,
                    'description': 'Absolute working directory inside the selected target workspace.'},
        'target': {'type': 'string', 'enum': ['resource', 'coordinator'],
                   'description': 'resource: the assigned execution resource; coordinator: the local coordinator '
                                  'run directory for supplied-input work.'},
        'env': {'type': 'array', 'items': _ENVIRONMENT_ITEM,
                'description': 'Environment variables for this command only.'}}}

STEERING = ('action_yields', 'last_local_outcome', 'feedback', 'resource_tool_estimates')
PROGRESS = ('credit', 'initial_credit', 'operational_credit', 'requirements', 'satisfied_keys')


def _failure_outcome(error):
    return {'facts': {}, 'native_outcome': {'failure': {
        'code': 'execution_action_failed', 'exception_type': type(error).__name__, 'detail': str(error)}}}


def _publish_receipt(store, receipt, assignment, scope):
    """One command receipt as its ``source`` record in the run's Store, with the artifacts it names (written through
    ``ctx.store``; content-addressed, so publishing a recovered receipt again is idempotent)."""
    body = {'version': RECEIPT_VERSION, 'run_id': receipt['run_id'], 'episode_id': receipt['episode_id'],
            'assignment_sha256': digest(assignment), 'scope': scope, 'receipt': receipt}
    snapshot = {'version': ASSIGNMENT_SNAPSHOT_VERSION, 'run_id': receipt['run_id'],
                'episode_id': receipt['episode_id'], 'scope': scope, 'assignment': assignment}
    with store.transaction():
        artifact = store.artifact(canonical(body), 'application/json')
        request = store.artifact(canonical(snapshot), 'application/json')
        source = store.put('source', {
            'provider': RECEIPT_PROVIDER,
            'accession': 'practical_receipt_' + digest([receipt['run_id'], receipt['episode_id'],
                                                         receipt['operation_key']]),
            'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request,
            'version': RECEIPT_VERSION, 'retrieved_at': receipt['finished_at']}, origin='tool')
    return source['id'], [artifact, request]


async def exec_command(arguments, ctx):
    """Run one shell command on the assigned resource or the coordinator and save its receipt.

    BLOCKED-ON-JOB-SERVICE: ``job_access``. The service wraps the old ``PracticalState`` (durable command intent and
    receipt, idempotent on the operation key) and ``TerminalExecution.execute`` (the transport). Wanted calls:
    ``ctx.services['job_access'].begin_command(assignment, run_id, episode_id, key, tool, command)``,
    ``await ctx.services['job_access'].execute_command(assignment, run_id, episode_id, key, tool, command)`` and
    ``ctx.services['job_access'].finish_command(assignment, run_id, episode_id, key, outcome, validations,
    context_after)``. No such service exists: the run cannot be linked until the caller supplies it."""
    assignment, scope, command = arguments['assignment'], arguments['scope'], arguments['command']
    access = ctx.services['job_access']
    key = ctx.operation_key
    intent = access.begin_command(assignment, ctx.run_id, ctx.episode_id, key, TOOL, command)
    if intent['state'] == 'completed':
        receipt = intent['receipt']
    else:
        try:
            outcome = await access.execute_command(assignment, ctx.run_id, ctx.episode_id, key, TOOL, command)
        except (ValueError, TypeError, OSError, AcquisitionError) as error:
            outcome = _failure_outcome(error)
        outcome = finalize_scientific_command(assignment, command, outcome)
        before = intent['intent']['context_before']
        after = deepcopy(before)
        if command['target'] == 'resource' and PurePosixPath(command['workdir']).is_relative_to(
                assignment['workspace']):
            after.update(cwd=command['workdir'], environment=command['env'])
        after['revision'] += int(any(after[name] != before[name] for name in ('cwd', 'environment')))
        validations = assess_validations(assignment, outcome, after, tool_name=TOOL)
        receipt = access.finish_command(assignment, ctx.run_id, ctx.episode_id, key, outcome, validations, after)
    source_ref, artifact_refs = _publish_receipt(ctx.store, receipt, assignment, scope)
    failed = 'failure' in (receipt['outcome'].get('native_outcome') or {})
    return {'status': 'failed' if failed else 'completed', 'receipt': receipt, 'receipt_ref': source_ref,
            'artifact_refs': artifact_refs, 'receipt_sha256': digest(receipt)}


TOOLS = {TOOL: exec_command}


def _terminal(settings):
    return TerminalExecution(settings['resource'], coordinator_workspace=settings['coordinator_workspace'],
                             artifact_selector=terminal_artifact_paths)


def _resource_information(settings, assignment):
    resource = settings['resource']
    return {'resource_id': assignment['resource_id'], 'resource_kind': 'local', 'availability': 'unknown',
            'tool_names': [TOOL],
            **{name: deepcopy(resource[name]) for name in ('workspace', 'policy', 'account', 'python_executable',
                                                            'service', 'base_url') if name in resource},
            'inventory_snapshot': deepcopy(settings['initial_information'].get(assignment['resource_id']))}


def _execution_resource(settings, assignment):
    resource = settings['resource']
    return {'resource_kind': 'local', 'workspace': resource['workspace'],
            **{name: deepcopy(resource[name]) for name in ('kind', 'policy', 'account', 'ssh_argv',
                                                            'python_executable', 'scheduler') if name in resource},
            'inventory_snapshot': deepcopy(settings['initial_information'].get(assignment['resource_id']))}


def present_native_task(state, instructions):
    """The selected execution TASK, then its STEERING, then the current execution information (this episode's
    own prompt; the old renderer's helpers lived in the shared root and are not carried)."""
    def render(value):
        return json.dumps(value, indent=2, sort_keys=True, allow_nan=False)

    steering = {name: state[name] for name in STEERING if state.get(name) is not None}
    progress = {'practical_progress': {name: state['execution_progress'][name] for name in PROGRESS},
                'practical_completion': state['execution_completion'],
                'execution_completed': state['execution_completion'] is not None}
    return '\n\n'.join(['TASK\n' + instructions + '\n' + render(state['selected_execution_task']),
                        'STEERING\n' + render(steering),
                        'Current execution information\n' + render(progress)])


def decide(summary, feedback, ctx):
    settings = ctx.settings
    assignment = summary['assignment']
    library = LaunchInstructions(settings['launch_instruction_directory'])
    instructions = INSTRUCTIONS
    resource_instructions = library.for_resource(settings['resource'])
    if resource_instructions:
        instructions += '\nResource instructions supplied from the frozen library:\n' + '\n\n'.join(
            section['text'] for section in resource_instructions['sections'])
    state = {
        'goal': summary['objective'], 'scope': summary['scope'],
        'execution_assignment': assignment,
        'execution_resource': _execution_resource(settings, assignment),
        'coordinator_workspace': settings['coordinator_workspace'],
        'execution_context': summary['execution_context'],
        'execution_progress': summary['execution_progress'],
        'execution_completion': summary['execution_completion'],
        'completion_target': summary['completion_target'],
        'last_local_outcome': summary['last_local_outcome'],
        'feedback': feedback,
        'action_yields': summary['action_yields'],
        'time_accounting': time_accounting(ctx.clock.progress_time),
        'launch_instruction_library': library.context(),
        'selected_launch_instructions': library.materialize(assignment.get('launch_instructions')),
        # BLOCKED-ON-JOB-SERVICE: estimate_table; wanted call: the read below. No such service exists.
        'resource_tool_estimates': ctx.services['estimate_table'].read('resource_tool_estimates', 'launch_local'),
        'tools': [{'name': TOOL, 'input_schema': OUTPUT_SCHEMA}],
    }
    if summary['units_consumed'] == 0:
        state['execution_resource_capabilities'] = [_resource_information(settings, assignment)]
        state['execution_initial_information'] = deepcopy(settings['initial_information'])
    task = summary['selected_execution_task']
    if task is not None:
        state['selected_execution_task'] = {**task, 'requests': [
            {**request, 'resource': _resource_information(settings, assignment)} for request in task['requests']]}
        return ModelRequest(MODEL_ROLE, instructions, {'presentation': present_native_task(state, instructions)},
                            OUTPUT_SCHEMA)
    return ModelRequest(MODEL_ROLE, instructions, state, OUTPUT_SCHEMA)


def action(response, summary, records, ctx):
    """Admit the model's command. A selection that fails admission creates no unit: the model decides again with
    the feedback."""
    terminal = _terminal(ctx.settings)
    try:
        Draft202012Validator(OUTPUT_SCHEMA).validate(response)
        names = [item['name'] for item in response['env']]
        if len(set(names)) != len(names):
            raise ValueError('exec_command_environment_name_repeated')
        command = {'cmd': response['cmd'], 'workdir': response['workdir'], 'target': response['target'],
                   'env': {item['name']: item['value'] for item in response['env']}}
        terminal.validate_action(summary['assignment'], TOOL, command)
    except (ValidationError, ValueError, TypeError, KeyError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(TOOL, {'assignment': summary['assignment'], 'scope': summary['scope'], 'command': command})
