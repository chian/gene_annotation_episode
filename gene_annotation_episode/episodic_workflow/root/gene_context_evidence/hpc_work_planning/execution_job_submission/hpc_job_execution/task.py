"""The task: the model writes the shell commands that run the commissioned HPC job; each command is one unit.

The one tool, ``exec_command``, runs the command on the assigned resource (or on the local coordinator, for
supplied-input and transport work) through the run's ``job_access`` service, qualifies its facts against the
original assignment and returns the command's receipt, which it also writes to the Store as an artifact held as
produced. Every command that runs is a unit with its actual outcome, a failure or zero progress included. The
task always offers a unit and never ends the Episode: when the endpoint is validated or nothing more is earned its
yield controller stops it."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import PurePosixPath

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.gene_context_evidence.acquisition import (
    AcquisitionError)
from gene_annotation_episode.episodic_workflow.episode_support.findings.gene_context_evidence.terminal_scientific_evidence import (
    finalize_scientific_command, terminal_artifact_paths)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.gene_context_evidence.terminal_execution import (
    TerminalExecution)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.gene_context_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
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
    "the selected command only. target=resource runs on the assigned resource; target=coordinator runs in the local "
    "run directory for supplied-input and transport work. Both are ordinary journaled actions; resource computation "
    "belongs on its actual allocation. For coordinator-side transfers, execution_resource.ssh_argv, when present, is "
    "the exact configured transport prefix. Append the remote shell command as its final argument and preserve "
    "stdin. The supplied configuration gives the existing connection details. target=resource uses that transport "
    "directly. The episode iterator decides continuation from credit; add no stopping budget.")

EXEC_COMMAND = {
    'name': 'exec_command',
    'description': ('Execute the shell command you write on the assigned resource. Use normal shell/file tools to '
                    'inspect files, author scripts, prepare an environment, run software, or submit/observe the '
                    'actual job as needed. Returns its actual output and saved action receipt. workdir and env '
                    'apply to this command; select them explicitly on each action.'),
    'input_schema': {
        'type': 'object',
        'properties': {
            'cmd': {'anyOf': [{'type': 'string', 'minLength': 1},
                              {'type': 'array', 'minItems': 1, 'items': {'type': 'string', 'minLength': 1}}]},
            'workdir': {'type': 'string', 'minLength': 1},
            'target': {'type': 'string', 'enum': ['resource', 'coordinator'],
                       'description': 'Assigned resource (default), or local coordinator run directory for '
                                      'input-file work.'},
            'env': {'type': 'object', 'additionalProperties': {'type': 'string'}}},
        'required': ['cmd', 'workdir', 'env'], 'additionalProperties': False}}
SELECTION_SCHEMA = {
    'type': 'object',
    'properties': {'selection': {
        'type': 'object',
        'properties': {'kind': {'const': 'tool'}, 'tool': {'const': 'exec_command'},
                       'arguments': EXEC_COMMAND['input_schema']},
        'required': ['kind', 'tool', 'arguments'], 'additionalProperties': False}},
    'required': ['selection'], 'additionalProperties': False}


def _now():
    return datetime.now(timezone.utc).isoformat()


async def exec_command(arguments, ctx):
    """Run one command through the job-access service and return its receipt.

    ``arguments`` are the model's command (``cmd``, ``workdir``, ``env``, optional ``target``) with the original
    ``assignment`` and the working ``context_before`` that ``action`` added from the summary. The job-access call
    is idempotent on ``ctx.operation_key``: a rerun of an unfinished unit does not run the command again."""
    assignment, before = arguments['assignment'], arguments['context_before']
    call = {name: arguments[name] for name in ('cmd', 'workdir', 'env', 'target') if name in arguments}
    target = call.get('target', 'resource')
    started_at = _now()
    paths = None if target == 'coordinator' else terminal_artifact_paths(assignment, call)
    try:
        outcome = await ctx.services['job_access'].exec_command(
            assignment, call, artifact_paths=paths, run_id=ctx.run_id, episode_id=ctx.episode_id,
            key=ctx.operation_key)
    except (ValueError, TypeError, OSError, AcquisitionError) as error:
        outcome = {'facts': {}, 'native_outcome': {'failure': {
            'code': 'execution_action_failed', 'exception_type': type(error).__name__, 'detail': str(error)}}}
    outcome = finalize_scientific_command(assignment, call, outcome)
    after = deepcopy(before)
    if target == 'resource' and PurePosixPath(call['workdir']).is_relative_to(assignment['workspace']):
        after.update({'cwd': call['workdir'], 'environment': call['env']})
    after['revision'] += int(any(after[name] != before[name] for name in ('cwd', 'environment')))
    validations = assess_validations(assignment, outcome, after, tool_name='exec_command')
    receipt = validate_receipt({
        'version': RECEIPT_VERSION, 'run_id': ctx.run_id, 'episode_id': ctx.episode_id,
        'assignment_sha256': digest(assignment), 'operation_key': ctx.operation_key, 'tool_name': 'exec_command',
        'arguments': call, 'context_before': before, 'context_after': after, 'outcome': outcome,
        'validations': validations, 'started_at': started_at, 'finished_at': _now()})
    reference = ctx.store.artifact(canonical(receipt), 'application/json')
    return {'status': 'completed', 'receipt': receipt, 'receipt_ref': reference,
            'operation_ref': digest(ctx.operation_key)}


TOOLS = {'exec_command': exec_command}


def _resource_information(settings, assignment):
    resource = settings['resource']
    return {'resource_kind': assignment['resource_kind'], 'workspace': resource['workspace'],
            **{name: deepcopy(resource[name]) for name in ('kind', 'policy', 'account', 'ssh_argv',
                                                           'python_executable', 'scheduler') if name in resource},
            'inventory_snapshot': deepcopy(settings['initial_information'])}


def _history(receipts):
    return [{'index': index, 'cmd': receipt['arguments']['cmd'], 'workdir': receipt['arguments']['workdir'],
             'target': receipt['arguments'].get('target', 'resource'),
             'returncode': receipt['outcome'].get('facts', {}).get('command', {}).get('returncode'),
             'failure': (receipt['outcome'].get('native_outcome') or {}).get('failure'),
             'satisfied_keys': [item['key'] for item in receipt['validations'] if item['satisfied']]}
            for index, receipt in enumerate(receipts)]


def decide(summary, feedback, ctx):
    assignment = summary['assignment']
    instructions = INSTRUCTIONS
    directory = ctx.settings.get('launch_instruction_directory')
    if directory is not None:
        selected = LaunchInstructions(directory).for_resource(ctx.settings['resource'])
        if selected:
            instructions += ('\nResource instructions supplied from the frozen library:\n'
                             + '\n\n'.join(section['text'] for section in selected['sections']))
    context = {'execution_assignment': assignment,
               'execution_resource': _resource_information(ctx.settings, assignment),
               'coordinator_workspace': ctx.settings['coordinator_workspace'],
               'execution_context': summary['context'],
               'execution_progress': summary['execution_progress'],
               'execution_completion': summary['execution_completion'],
               'requested_action_history': _history(summary['receipts']),
               'feedback': feedback, 'tools': [EXEC_COMMAND]}
    if summary['receipts']:
        context['last_local_outcome'] = summary['receipts'][-1]
    if 'controller' in summary:
        context['controller'] = summary['controller']
    return ModelRequest('REASONING', instructions, context, generation_schema(SELECTION_SCHEMA))


def action(response, summary, records, ctx):
    """The model's answer becomes one ``exec_command`` unit, or is rejected as an invalid answer."""
    try:
        decoded = decode_response(response, SELECTION_SCHEMA)
        Draft202012Validator(SELECTION_SCHEMA).validate(decoded)
        call = decoded['selection']['arguments']
        TerminalExecution(ctx.settings['resource'], coordinator_workspace=ctx.settings['coordinator_workspace']
                          ).validate_action(summary['assignment'], 'exec_command', call)
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='arguments_or_reference'))
    return ToolCall('exec_command', {**call, 'assignment': summary['assignment'],
                                     'context_before': summary['context']})
