"""The task: the execution agent of one actual HPC job.

The model writes the shell code (``exec_command``); each command is one unit whose actual result, receipt and
earned credit enter the iterator, a failed or invalid command too. The task always offers a unit and never ends
the Episode: only the yield controller does.

The command itself runs through the ``job_access`` service (transport, SSH, the scheduler's shell). The service
does not exist yet: BLOCKED-ON-JOB-SERVICE (the tool raises where it would call it)."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import PurePosixPath

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from .goal import GOAL

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.biochemical_feasibility_evidence.acquisition import (
    AcquisitionError)
from gene_annotation_episode.episodic_workflow.episode_support.findings.biochemical_feasibility_evidence.terminal_scientific_evidence import (
    finalize_scientific_command, terminal_artifact_paths)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.biochemical_feasibility_evidence.terminal_execution import (
    TerminalExecution)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.practical_execution_records import (
    RECEIPT_VERSION, assess_validations, canonical, digest, validate_receipt)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import (
    time_accounting, yield_table)

CHILD_SLOTS = {}
SERVICES = ('job_access',)

INSTRUCTIONS = (
    'You are the execution agent for the actual job and resource assigned below. '
    'Use exec_command to write and run the shell code needed for that job. '
    'Choose scripts, environment preparation, software invocation and recovery from '
    'the actual resource instructions and observed results. No sequence of setup or '
    'job-stage operations is prescribed. Preserve the caller\'s scientific inputs, '
    'desired outputs and acceptance criteria. Historical inventory is context, not '
    'proof of present usability. Each command is one ordinary episode action: its '
    'actual result and earned credit enter the iterator, including failure or zero '
    'progress. Host bookkeeping records command versions and actual native job '
    'identities; do not maintain a parallel receipt ledger. If a submission outcome '
    'is uncertain, investigate that original submission rather than create a duplicate. '
    'Use the provided resource-specific instructions, account, storage and existing '
    'authentication route. workdir and env apply to the selected command only. '
    'target=resource runs on the assigned resource; target=coordinator runs in the '
    'local run directory for supplied-input and transport work. Both are ordinary '
    'journaled actions; resource computation belongs on its actual allocation. '
    'For coordinator-side transfers, execution_resource.ssh_argv, when present, '
    'is the exact configured transport prefix. Append the remote shell command '
    'as its final argument and preserve stdin. The supplied configuration gives '
    'the existing connection details. target=resource uses that transport directly. '
    'The episode iterator decides continuation from credit; add no stopping budget.')

COMMAND_SCHEMA = {
    'type': 'object',
    'properties': {
        'cmd': {'anyOf': [{'type': 'string', 'minLength': 1},
                          {'type': 'array', 'minItems': 1, 'items': {'type': 'string', 'minLength': 1}}]},
        'workdir': {'type': 'string', 'minLength': 1},
        'env': {'type': 'object', 'additionalProperties': {'type': 'string'}},
        'target': {'enum': ['resource', 'coordinator']},
    },
    'required': ['cmd', 'workdir', 'env'], 'additionalProperties': False}
TOOL_DESCRIPTION = {
    'name': 'exec_command',
    'description': 'Run one shell command on the assigned resource (target=resource, the default) or in the '
                   'coordinator run directory (target=coordinator). workdir and env apply to this command only.',
    'input_schema': COMMAND_SCHEMA}
ACTION_SCHEMA = {
    'type': 'object',
    'properties': {'tool': {'const': 'exec_command'}, 'arguments': COMMAND_SCHEMA},
    'required': ['tool', 'arguments'], 'additionalProperties': False}
TRANSPORT = {'open_records_as_text': True, 'argument_transport_error': 'hpc_job_execution_argument_transport_unsupported'}
RESOURCE_FIELDS = ('kind', 'policy', 'account', 'ssh_argv', 'python_executable', 'scheduler')


def _now():
    return datetime.now(timezone.utc).isoformat()


def _operations(settings):
    """The old ``TerminalExecutionBehavior._operations``: the command validator of the configured resource."""
    return TerminalExecution(settings['resource'], coordinator_workspace=settings['coordinator_workspace'],
                             artifact_selector=terminal_artifact_paths)


def _resource_information(settings, assignment):
    """The old ``_resource_information``: the configured resource and the inventory the assignment froze."""
    configuration = settings['resource']
    return {'resource_kind': 'hpc', 'workspace': configuration['workspace'],
            **{name: deepcopy(configuration[name]) for name in RESOURCE_FIELDS if name in configuration},
            'inventory_snapshot': deepcopy(assignment['inventory_snapshot'])}


def _launch_instructions(settings, assignment):
    """The run-frozen launch instruction library, when one is configured: its identity, the sections the
    launching parent selected and the sections of this resource's configured prompt."""
    directory = settings.get('launch_instructions_directory')
    if directory is None:
        return None, {}, ''
    library = LaunchInstructions(directory)
    context = {'launch_instruction_library': library.context()}
    selected = library.materialize(assignment.get('launch_instructions'))
    if selected is not None:
        context['selected_launch_instructions'] = selected
    resource = library.for_resource(settings['resource'])
    text = ''
    if resource:
        text = '\nResource instructions supplied from the frozen library:\n' + '\n\n'.join(
            section['text'] for section in resource['sections'])
    return library, context, text


def decide(summary, feedback, ctx):
    assignment = summary['assignment']
    _, library_context, resource_text = _launch_instructions(ctx.settings, assignment)
    context = {'goal': GOAL,
               'execution_assignment': assignment,
               'execution_resource': _resource_information(ctx.settings, assignment),
               'coordinator_workspace': ctx.settings['coordinator_workspace'],
               'execution_progress': summary['progress'],
               'execution_completion': summary['completion'],
               'current_credit': summary['progress']['credit'],
               'working_context': summary['context'],
               'completed_action_reports': [{'operation_key': receipt['operation_key'],
                                             'tool_name': receipt['tool_name'], 'arguments': receipt['arguments'],
                                             'outcome': receipt['outcome'],
                                             'satisfied_keys': [item['key'] for item in receipt['validations']
                                                                if item['satisfied']],
                                             'started_at': receipt['started_at'],
                                             'finished_at': receipt['finished_at']}
                                            for receipt in summary['receipts']],
               'last_local_outcome': summary['last_outcome'],
               'feedback': feedback,
               'controller': summary['controller'],
               'time_accounting': time_accounting(ctx.clock.progress_time),
               'tools': [TOOL_DESCRIPTION],
               **library_context}
    return ModelRequest('REASONING', INSTRUCTIONS + resource_text, context,
                        strict_output_schema(ACTION_SCHEMA, **TRANSPORT))


def action(response, summary, records, ctx):
    """The model's answer is one ``exec_command``; an answer that is not one is rejected."""
    try:
        selected = decode_strict_output(response, ACTION_SCHEMA, **TRANSPORT)
        Draft202012Validator(ACTION_SCHEMA).validate(selected)
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='invalid_action'))
    return ToolCall('exec_command', {'command': selected['arguments'], 'assignment': summary['assignment'],
                                     'context_before': summary['context']})


def _publish_receipt(store, run_id, episode_id, assignment, receipt):
    """Publish the receipt as a Store record held by this Episode.

    BLOCKED-ON-STORE-ACCESS. Intended call: ``PracticalReceiptInformation(store, run_id).publish(context,
    receipt)`` (``episode_support/records/practical_receipt_information.py``). The library is not carried: it
    requires the old ``BindingContext``, reads ``runtime_actions`` and ``runtime_episodes`` and ``store.db``."""
    raise NotImplementedError('BLOCKED-ON-STORE-ACCESS: PracticalReceiptInformation(ctx.store, ctx.run_id)'
                              '.publish(context, receipt): library not carried')


async def exec_command(arguments, ctx):
    """Run one command and keep its receipt: the old ``TerminalExecutionBehavior.execute``."""
    assignment, command, before = arguments['assignment'], arguments['command'], arguments['context_before']
    operations = _operations(ctx.settings)
    try:
        operations.validate_action(assignment, 'exec_command', command)
    except (ValueError, TypeError) as error:
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': str(error)}}
    job_access = ctx.services['job_access']
    if not hasattr(job_access, 'exec_command'):
        raise NotImplementedError(
            'BLOCKED-ON-JOB-SERVICE: job_access.exec_command(configuration, coordinator_workspace, assignment, '
            'command, run_id, episode_id, key): the transport run of one command, idempotent on the operation key')
    started = _now()
    try:
        outcome = await job_access.exec_command(
            configuration=ctx.settings['resource'], coordinator_workspace=ctx.settings['coordinator_workspace'],
            assignment=assignment, command=command, run_id=ctx.run_id, episode_id=ctx.episode_id,
            key=ctx.operation_key)
    except (ValueError, TypeError, OSError, AcquisitionError) as error:
        outcome = {'facts': {}, 'native_outcome': {'failure': {
            'code': 'execution_action_failed', 'exception_type': type(error).__name__, 'detail': str(error)}}}
    outcome = finalize_scientific_command(assignment, command, outcome)
    after = deepcopy(before)
    if command.get('target', 'resource') == 'resource' and (
            PurePosixPath(command['workdir']).is_relative_to(assignment['workspace'])):
        after.update({'cwd': command['workdir'], 'environment': command['env']})
    after['revision'] += int(any(after[name] != before[name] for name in ('cwd', 'environment')))
    validations = assess_validations(assignment, outcome, after, tool_name='exec_command')
    receipt = validate_receipt({
        'version': RECEIPT_VERSION, 'run_id': ctx.run_id, 'episode_id': ctx.episode_id,
        'assignment_sha256': digest(assignment), 'operation_key': ctx.operation_key, 'tool_name': 'exec_command',
        'arguments': command, 'context_before': before, 'context_after': after, 'outcome': outcome,
        'validations': validations, 'started_at': started, 'finished_at': _now()})
    reference = _publish_receipt(ctx.store, ctx.run_id, ctx.episode_id, assignment, receipt)
    return {'status': 'completed', 'record_refs': [reference], 'changed_record_refs': [reference],
            'operation_ref': digest(ctx.operation_key), 'result': json.loads(canonical(receipt))}


TOOLS = {'exec_command': exec_command}
