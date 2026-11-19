"""The task: the model writes one shell command per unit, the episode runs it on the assigned resource (or the
coordinator) through the ``job_access`` service and keeps the receipt of what it did.

The task always offers a unit and never ends the Episode: the Episode ends when its yield controller stops it, which
is when the credit of the commissioned requirements reaches the target of its completion keys. No sequence of setup
or job-stage operations is prescribed; a failed or zero-progress command is an ordinary unit that enters the
iterator with its credit.

Wanted of the ``job_access`` service, which the system does not provide yet (BLOCKED-ON-JOB-SERVICE):
reads for ``decide``: ``resource_information(resource_id)``, ``resource_instructions(resource_id)``,
``coordinator_workspace()``, ``launch_instruction_sections(selection)``; calls for the tool:
``validate_action(assignment, tool_name, arguments)`` and ``exec_command(assignment, arguments, key=...)``, the
latter idempotent on the operation key."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.gene_context_evidence.acquisition import (
    AcquisitionError)
from gene_annotation_episode.episodic_workflow.episode_support.findings.gene_context_evidence.terminal_scientific_evidence import (
    finalize_scientific_command)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.gene_context_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import (
    validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.practical_execution_records import (
    RECEIPT_VERSION, assess_validations, canonical, digest, validate_receipt)

CHILD_SLOTS = {}
SERVICES = ('job_access',)

INSTRUCTIONS = (
    "You are the execution agent for the actual job and resource assigned below. Use exec_command to write and run "
    "the shell code needed for that job. Choose scripts, environment preparation, software invocation and recovery "
    "from the actual resource instructions and observed results. No sequence of setup or job-stage operations is "
    "prescribed. Preserve the caller's scientific inputs, desired outputs and acceptance criteria. Historical "
    "inventory is context, not proof of present usability. Each command is one ordinary episode action: its actual "
    "result and earned credit enter the iterator, including failure or zero progress. Host bookkeeping records "
    "command versions and actual native job identities; do not maintain a parallel receipt ledger. If a submission "
    "outcome is uncertain, investigate that original submission rather than create a duplicate. Use the provided "
    "resource-specific instructions, account, storage and existing authentication route. workdir and env apply to "
    "the selected command only. target=resource runs on the assigned resource; target=coordinator runs in the "
    "local run directory for supplied-input and transport work. Both are ordinary journaled actions; resource "
    "computation belongs on its actual allocation. For coordinator-side transfers, execution_resource.ssh_argv, "
    "when present, is the exact configured transport prefix. Append the remote shell command as its final argument "
    "and preserve stdin. The supplied configuration gives the existing connection details. target=resource uses "
    "that transport directly. The episode iterator decides continuation from credit; add no stopping budget.")

EXEC_COMMAND_SCHEMA = {
    'type': 'object',
    'properties': {
        'cmd': {'anyOf': [{'type': 'string', 'minLength': 1},
                          {'type': 'array', 'minItems': 1, 'items': {'type': 'string', 'minLength': 1}}]},
        'workdir': {'type': 'string', 'minLength': 1},
        'target': {'type': 'string', 'enum': ['resource', 'coordinator'],
                   'description': 'Assigned resource (default), or local coordinator run directory for input-file '
                                  'work.'},
        'env': {'type': 'object', 'additionalProperties': {'type': 'string'}}},
    'required': ['cmd', 'workdir', 'env'], 'additionalProperties': False}
EXEC_COMMAND = {
    'name': 'exec_command',
    'description': ('Execute the shell command you write on the assigned resource. Use normal shell/file tools to '
                    'inspect files, author scripts, prepare an environment, run software, or submit/observe the '
                    'actual job as needed. Returns its actual output and saved action receipt. workdir and env '
                    'apply to this command; select them explicitly on each action.'),
    'input_schema': EXEC_COMMAND_SCHEMA}
# What the model answers: the one tool, with its arguments.
SELECTION_SCHEMA = {
    'type': 'object',
    'properties': {'kind': {'type': 'string', 'const': 'tool'}, 'tool': {'type': 'string', 'const': 'exec_command'},
                   'arguments': EXEC_COMMAND_SCHEMA},
    'required': ['kind', 'tool', 'arguments'], 'additionalProperties': False}
ACTION_SCHEMA = {'type': 'object', 'properties': {'selection': SELECTION_SCHEMA}, 'required': ['selection'],
                 'additionalProperties': False}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _outcome(result=None, *, references=(), code=None):
    return {'status': 'invalid' if code else 'completed', 'record_refs': list(references),
            'changed_record_refs': list(references), 'result': result,
            'feedback': None if code is None else {'category': 'arguments_or_reference', 'code': code}}


def exec_command(arguments, ctx):
    """Run one command; keep the receipt of what it did as a record the Episode produced."""
    command, assignment, before = arguments['command'], arguments['assignment'], arguments['context_before']
    access = ctx.services['job_access']
    started_at = _now()
    try:
        validate_schema(command, EXEC_COMMAND_SCHEMA)
        access.validate_action(assignment, 'exec_command', command)
    except (ValueError, TypeError) as error:
        return _outcome(code=str(error))
    try:
        outcome = access.exec_command(assignment, command, key=ctx.operation_key)
    except (ValueError, TypeError, OSError, AcquisitionError) as error:
        outcome = {'facts': {}, 'native_outcome': {'failure': {
            'code': 'execution_action_failed', 'exception_type': type(error).__name__, 'detail': str(error)}}}
    outcome = finalize_scientific_command(assignment, command, outcome)
    after = deepcopy(before)
    if command.get('target', 'resource') == 'resource' and Path(command['workdir']).is_relative_to(
            assignment['workspace']):
        after.update({'cwd': command['workdir'], 'environment': command['env']})
    after['revision'] += int(any(after[name] != before[name] for name in ('cwd', 'environment')))
    finished_at = _now()
    validations = assess_validations(assignment, outcome, after, checked_at=finished_at, tool_name='exec_command')
    receipt = validate_receipt({
        'version': RECEIPT_VERSION, 'run_id': ctx.run_id, 'episode_id': ctx.episode_id,
        'assignment_sha256': digest(assignment), 'operation_key': ctx.operation_key, 'tool_name': 'exec_command',
        'arguments': command, 'context_before': before, 'context_after': after, 'outcome': outcome,
        'validations': validations, 'started_at': started_at, 'finished_at': finished_at})
    reference = ctx.store.artifact(canonical(receipt).encode('utf-8'), 'application/json')
    return _outcome(receipt, references=[reference]) | {'operation_ref': digest(ctx.operation_key)}


TOOLS = {'exec_command': exec_command}


def decide(summary, feedback, ctx):
    """Ask the model for the next command, with the assignment, the resource, the progress and the last receipt."""
    access = ctx.services['job_access']
    assignment = summary['assignment']
    instructions = INSTRUCTIONS
    selected = access.read('resource_instructions', assignment['resource_id'])
    if selected:
        instructions += '\nResource instructions supplied from the frozen library:\n' + '\n\n'.join(
            section['text'] for section in selected['sections'])
    context = {
        'execution_assignment': assignment,
        'execution_resource': access.read('resource_information', assignment['resource_id']),
        'coordinator_workspace': access.read('coordinator_workspace'),
        'execution_progress': summary['progress'], 'execution_completion': summary['completion'],
        'current_credit': summary['credit'], 'working_context': summary['context'],
        'actions': summary['actions'], 'last_receipt': summary['last_receipt'], 'feedback': feedback,
        'tools': [EXEC_COMMAND]}
    if 'launch_instructions' in assignment:
        context['selected_launch_instructions'] = access.read('launch_instruction_sections',
                                                              assignment['launch_instructions'])
    if 'controller' in summary:
        context['controller'] = summary['controller']
    return ModelRequest('REASONING', instructions, context, generation_schema(ACTION_SCHEMA))


def action(response, summary, records, ctx):
    """The one command the model chose; an answer that does not fit the schema is rejected with its diagnostic."""
    try:
        selection = decode_response(response, ACTION_SCHEMA)['selection']
        Draft202012Validator(SELECTION_SCHEMA).validate(selection)
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall('exec_command', {'command': selection['arguments'], 'assignment': summary['assignment'],
                                     'context_before': summary['context']})
