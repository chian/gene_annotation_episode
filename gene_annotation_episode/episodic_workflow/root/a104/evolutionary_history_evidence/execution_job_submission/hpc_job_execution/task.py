"""The task: the model writes one shell command per turn (``exec_command``) and the tool runs it on the assigned
resource, or on the coordinator for supplied-input and transport work, through the run's ``job_access`` service.

Every command that executes and returns is one unit, a failed one too; its receipt is written through ``ctx.store``
and enters the iterator with the credit measured after it. A model answer that fails admission creates no unit:
``action`` rejects it and ``decide`` is asked again with the feedback. The task always offers a unit and never ends
the Episode: only the yield controller does (a command may be offered after the endpoint is proven)."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import PurePosixPath

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.evolutionary_history_evidence.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.native_terminal_transport import TerminalExecution
from gene_annotation_episode.episodic_workflow.episode_support.findings.evolutionary_history_evidence.terminal_scientific_evidence import finalize_scientific_command, terminal_artifact_paths
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import rejection_feedback
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.practical_execution_records import RECEIPT_VERSION, assess_validations, canonical, digest, validate_receipt

CHILD_SLOTS = {}
TOOL = 'exec_command'
MODEL_ROLE = 'REASONING'
RECEIPT_PROVIDER = 'episode.practical_receipt'
RECEIPT_VERSION_INFORMATION = 'practical_receipt_information_v1'
RECEIPT_ASSIGNMENT_VERSION = 'practical_receipt_assignment_v1'

INSTRUCTIONS = (
    "You are the execution agent for the actual job and resource assigned below. Use exec_command to write and "
    "run the shell code needed for that job. Choose scripts, environment preparation, software invocation and "
    "recovery from the actual resource instructions and observed results. No sequence of setup or job-stage "
    "operations is prescribed. Preserve the caller's scientific inputs, desired outputs and acceptance criteria. "
    "Historical inventory is context, not proof of present usability. Each command is one ordinary episode "
    "action: its actual result and earned credit enter the iterator, including failure or zero progress. Host "
    "bookkeeping records command versions and actual native job identities; do not maintain a parallel receipt "
    "ledger. If a submission outcome is uncertain, investigate that original submission rather than create a "
    "duplicate. Use the provided resource-specific instructions, account, storage and existing authentication "
    "route. workdir and env apply to the selected command only. target=resource runs on the assigned resource; "
    "target=coordinator runs in the local run directory for supplied-input and transport work. Both are ordinary "
    "journaled actions; resource computation belongs on its actual allocation. For coordinator-side transfers, "
    "execution_resource.ssh_argv, when present, is the exact configured transport prefix. Append the remote "
    "shell command as its final argument and preserve stdin. The supplied configuration gives the existing "
    "connection details. target=resource uses that transport directly. The episode iterator decides continuation "
    "from credit; add no stopping budget. Return exactly one command: cmd is its argv (use "
    "[\"/bin/bash\", \"-c\", <script>] for shell code), env lists the environment variables it sets.")

ACTION_SCHEMA = {
    'type': 'object', 'additionalProperties': False, 'required': ['cmd', 'workdir', 'target', 'env'],
    'properties': {
        'cmd': {'type': 'array', 'minItems': 1, 'items': {'type': 'string', 'minLength': 1},
                'description': 'The argv of the one command to execute.'},
        'workdir': {'type': 'string', 'minLength': 1,
                    'description': 'Absolute working directory inside the target workspace.'},
        'target': {'enum': ['resource', 'coordinator'],
                   'description': 'resource: the assigned HPC resource; coordinator: the local run directory.'},
        'env': {'type': 'array', 'description': 'Environment variables this command sets.',
                'items': {'type': 'object', 'additionalProperties': False, 'required': ['name', 'value'],
                          'properties': {'name': {'type': 'string', 'minLength': 1},
                                         'value': {'type': 'string'}}}},
    },
}


def job_access(ctx, operation):
    """The run's ``job_access`` service, which must offer ``operation``."""
    service = ctx.services['job_access']
    if not hasattr(service, operation):
        raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access.' + operation)
    return service


def publish_receipt(store, run_id, episode_id, assignment, receipt):
    """The receipt's ``source`` record in the Store under custody (content-addressed, so republishing is
    idempotent)."""
    body = {'version': RECEIPT_VERSION_INFORMATION, 'run_id': run_id, 'episode_id': episode_id,
            'assignment_sha256': digest(assignment), 'receipt': receipt}
    snapshot = {'version': RECEIPT_ASSIGNMENT_VERSION, 'run_id': run_id, 'episode_id': episode_id,
                'assignment': assignment}
    with store.transaction():
        artifact = store.artifact(canonical(body), 'application/json')
        request = store.artifact(canonical(snapshot), 'application/json')
        source = store.put('source', {
            'provider': RECEIPT_PROVIDER,
            'accession': 'practical_receipt_' + digest([run_id, episode_id, receipt['operation_key']]),
            'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request,
            'version': RECEIPT_VERSION_INFORMATION, 'retrieved_at': receipt['finished_at']}, origin='tool')
    return source['id']


def now():
    return datetime.now(timezone.utc).isoformat()


async def exec_command(arguments, ctx):
    """Run one admitted command (once per operation key) and write its receipt.

    ``arguments``: ``command`` (cmd, workdir, target, env), the ``assignment`` and the working ``context_before``,
    which ``action`` took from the summary."""
    assignment, command, before = arguments['assignment'], arguments['command'], arguments['context_before']
    service = job_access(ctx, 'exec_command')
    started_at = now()
    try:
        outcome = await service.exec_command(assignment=assignment, command=command, run_id=ctx.run_id,
                                             episode_id=ctx.episode_id, operation_key=ctx.operation_key,
                                             resumed=ctx.resumed)
    except (ValueError, TypeError, OSError, AcquisitionError) as error:
        outcome = {'facts': {}, 'native_outcome': {'failure': {
            'code': 'execution_action_failed', 'exception_type': type(error).__name__, 'detail': str(error)}}}
    outcome = finalize_scientific_command(assignment, command, outcome)
    after = deepcopy(before)
    if (command['target'] == 'resource'
            and PurePosixPath(command['workdir']).is_relative_to(assignment['workspace'])):
        after.update({'cwd': command['workdir'], 'environment': command['env']})
    after['revision'] += int(any(after[name] != before[name] for name in ('cwd', 'environment')))
    validations = assess_validations(assignment, outcome, after, tool_name=TOOL)
    receipt = validate_receipt({
        'version': RECEIPT_VERSION, 'run_id': ctx.run_id, 'episode_id': ctx.episode_id,
        'assignment_sha256': digest(assignment), 'operation_key': ctx.operation_key, 'tool_name': TOOL,
        'arguments': command, 'context_before': before, 'context_after': after, 'outcome': outcome,
        'validations': validations, 'started_at': started_at, 'finished_at': now()})
    reference = publish_receipt(ctx.store, ctx.run_id, ctx.episode_id, assignment, receipt)
    handoff = any(item['satisfied'] and item['predicate']['kind'] == 'requested_job_handoff'
                  for item in receipt['validations'])
    failure = receipt['outcome'].get('native_outcome', {}).get('failure')
    return {'status': 'failed' if failure else 'completed', 'receipt': receipt, 'receipt_ref': reference,
            'receipt_sha256': digest(receipt), 'handoff': handoff}


TOOLS = {TOOL: exec_command}
SERVICES = ('job_access', 'launch_instructions')


def resource_information(resource, initial_information):
    """What the model may know about the configured resource."""
    return {'resource_kind': 'hpc', 'workspace': resource['workspace'],
            **{name: deepcopy(resource[name])
               for name in ('kind', 'policy', 'account', 'ssh_argv', 'python_executable', 'scheduler')
               if name in resource},
            'inventory_snapshot': deepcopy(initial_information.get('hpc'))}


def decide(summary, feedback, ctx):
    resource = ctx.settings['resource']
    initial = ctx.settings['initial_information']
    selected = ctx.services['launch_instructions'].read('for_resource', resource)
    instructions = INSTRUCTIONS
    if selected:
        instructions += ('\nResource instructions supplied from the frozen library:\n'
                         + '\n\n'.join(section['text'] for section in selected['sections']))
    context = {
        'execution_resource_information': deepcopy(initial),
        'execution_assignment': summary['assignment'],
        'execution_resource': resource_information(resource, initial),
        'coordinator_workspace': ctx.settings['coordinator_workspace'],
        'execution_progress': summary['progress'],
        'execution_completion': summary['completion'],
        'receipts': [{key: receipt[key] for key in ('operation_key', 'arguments', 'outcome', 'validations',
                                                   'context_after', 'finished_at')}
                     for receipt in summary['receipts']],
        'action_yields': summary['yield_table'],
        'feedback': feedback,
    }
    return ModelRequest(MODEL_ROLE, instructions, context, deepcopy(ACTION_SCHEMA))


def action(response, summary, records, ctx):
    transport = TerminalExecution(ctx.settings['resource'], coordinator_workspace=ctx.settings['coordinator_workspace'],
                                  artifact_selector=terminal_artifact_paths)
    try:
        Draft202012Validator(ACTION_SCHEMA).validate(response)
        env = {}
        for item in response['env']:
            if item['name'] in env:
                raise ValueError('exec_command_environment_name_repeats:' + item['name'])
            env[item['name']] = item['value']
        command = {'cmd': list(response['cmd']), 'workdir': response['workdir'], 'env': env,
                   'target': response['target']}
        transport.validate_action(summary['assignment'], TOOL, command)
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(TOOL, {'command': command, 'assignment': summary['assignment'],
                           'context_before': summary['context']})
