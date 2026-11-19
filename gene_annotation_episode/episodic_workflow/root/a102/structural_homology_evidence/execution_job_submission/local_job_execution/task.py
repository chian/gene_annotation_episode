"""The task: the execution agent for the assigned job on the local resource.

The model writes the shell command. The episode's one tool, ``exec_command``, runs it through the ``job_access``
service (on the assigned resource or in the coordinator workspace) and returns the saved receipt of the command: its
actual result and the validations of the original requirements it satisfied. A failed command is a returned outcome
like any other. The task always offers a unit and never ends the Episode: no stopping budget is added; the yield
controller stops it when the commissioned requirements are met or the forecast no longer pays for another command.

BLOCKED-ON-JOB-SERVICE: the ``job_access`` service has no implementation yet (LAUNCH_MONITOR_EXTRACT_MECHANICS.md,
section 5 and "Not provided yet" item 4). The tool names it and calls it; it raises where the call is made. The
practical receipt is published as a ``source`` record of provider ``episode.practical_receipt`` through
``ctx.store`` (the old ``PracticalReceiptInformation.publish`` reads ``store.db`` and the old runner's tables and
is not called: BLOCKED-ON-STORE-ACCESS, library not carried).

Settings (``ctx.settings``): ``resources`` (the configured resources by resource id), ``initial_information`` (the
recorded inventory by resource id), ``coordinator_workspace``, ``launch_instructions_directory`` and
``tool_knowledge_directory``."""
import inspect
import json

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.structural_homology_evidence.acquisition import (
    AcquisitionError)
from gene_annotation_episode.episodic_workflow.episode_support.findings.structural_homology_evidence.terminal_scientific_evidence import (
    finalize_scientific_command, terminal_artifact_paths)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.structural_homology_evidence.terminal_execution import (
    TerminalExecution)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.practical_execution_records import (
    assess_validations, canonical, digest, terminal_job_matches)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

CHILD_SLOTS = {}
SERVICES = ('job_access',)

TOOL = 'exec_command'
RECEIPT_PROVIDER = 'episode.practical_receipt'
RECEIPT_VERSION = 'practical_receipt_information_v1'
ASSIGNMENT_SNAPSHOT_VERSION = 'practical_receipt_assignment_v1'
ARGUMENT_TRANSPORT_ERROR = 'a102_local_job_execution_has_no_composed_tool_arguments'
# The one native job family A102 may bind to a configured resource (old ``configuration`` check).
ALLOWED_NATIVE = {'native_protein_structure'}
RESOURCE_KEYS = ('kind', 'policy', 'account', 'ssh_argv', 'python_executable', 'scheduler')

# The old ``terminal_contracts.operation_catalog('local')``: the one general capability.
EXEC_COMMAND = {
    'name': TOOL,
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

# The old ``terminal_goal.TerminalGoal.instructions`` text, unchanged.
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

_ENVIRONMENT_ITEM = {'type': 'object', 'additionalProperties': False, 'required': ['name', 'value'],
                     'properties': {'name': {'type': 'string', 'pattern': '^[A-Za-z_][A-Za-z0-9_]*$'},
                                    'value': {'type': 'string'}}}
ACTION_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['selection'], 'properties': {
    'selection': {'type': 'object', 'additionalProperties': False,
                  'required': ['tool', 'cmd', 'workdir', 'target', 'env'], 'properties': {
                      'tool': {'type': 'string', 'enum': [TOOL]},
                      'cmd': {'anyOf': [{'type': 'string', 'minLength': 1},
                                        {'type': 'array', 'minItems': 1,
                                         'items': {'type': 'string', 'minLength': 1}}],
                              'description': 'Shell code (a string) or an argv list.'},
                      'workdir': {'type': 'string', 'minLength': 1,
                                  'description': 'Absolute working directory inside the selected target workspace.'},
                      'target': {'type': 'string', 'enum': ['resource', 'coordinator'],
                                 'description': 'resource: the assigned execution resource workspace; coordinator: '
                                                'the local coordinator workspace for supplied-input work.'},
                      'env': {'type': 'array', 'items': _ENVIRONMENT_ITEM,
                              'description': 'Environment variables for this command only.'}}}}}


def _resource_configuration(settings, assignment):
    """The configured local resource of this assignment (the old ``configuration`` checks of one resource)."""
    configuration = settings['resources'][assignment['resource_id']]
    if configuration.get('kind') != 'local':
        raise ValueError('execution_resource_kind_conflict')
    if {name for name in configuration if name.startswith('native_') and name not in ALLOWED_NATIVE}:
        raise ValueError('a102_execution_resource_binding_conflict')
    return configuration


def _operations(settings, assignment):
    """The local transport's own validation of the assignment (old ``TerminalExecution``); a configuration or
    assignment it refuses raises and fails the run: it is not a model answer."""
    operations = TerminalExecution(_resource_configuration(settings, assignment),
                                   coordinator_workspace=settings['coordinator_workspace'],
                                   artifact_selector=terminal_artifact_paths)
    operations.validate_assignment(assignment)
    return operations


def _handoff(assignment, receipt):
    """Whether the command handed the requested job off and the receipt matches this assignment (the old returnable
    practical receipt)."""
    job = receipt['outcome'].get('facts', {}).get('requested_job')
    return bool(job is not None and job.get('handoff') is not None
                and terminal_job_matches(assignment, receipt['outcome']))


def _job_access(ctx, method, wanted):
    service = ctx.services['job_access']
    if not hasattr(service, method):
        raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access.' + method + '; wanted call: ' + wanted)
    return service


async def _call(service, method, *arguments, **keywords):
    reply = getattr(service, method)(*arguments, **keywords)
    if inspect.isawaitable(reply):
        reply = await reply
    return reply


def publish_receipt(store, run_id, episode_id, assignment, receipt):
    """One command receipt as its ``source`` record, in the form the HPC job route publishes (content-addressed:
    publishing a recovered receipt again is idempotent). Library candidate (the old ``publish_receipt`` /
    ``PracticalReceiptInformation.publish``)."""
    body = {'version': RECEIPT_VERSION, 'run_id': run_id, 'episode_id': episode_id,
            'assignment_sha256': digest(assignment), 'receipt': receipt}
    snapshot = {'version': ASSIGNMENT_SNAPSHOT_VERSION, 'run_id': run_id, 'episode_id': episode_id,
                'assignment': assignment}
    with store.transaction():
        artifact = store.artifact(canonical(body), 'application/json')
        request = store.artifact(canonical(snapshot), 'application/json')
        source = store.put('source', {
            'provider': RECEIPT_PROVIDER,
            'accession': 'practical_receipt_' + digest([run_id, episode_id, receipt['operation_key']]),
            'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': request,
            'version': RECEIPT_VERSION, 'retrieved_at': receipt['finished_at']}, origin='tool')
    return source['id']


async def exec_command(arguments, ctx):
    """The old ``terminal_operations.execute``: begin the intent (idempotent by operation key: a completed intent
    reuses its receipt), run the command, finalize the scientific command artifacts, update the cwd/env context
    revision for resource commands inside the workspace, assess the validations, finish the receipt and publish it.
    An execution error becomes a ``failure`` native outcome, which is still a completed, observed action."""
    assignment, command = arguments['assignment'], arguments['arguments']
    key, identity = ctx.operation_key, {'run_id': ctx.run_id, 'episode_id': ctx.episode_id}
    service = _job_access(ctx, 'begin_command', 'await ctx.services["job_access"].begin_command(assignment, '
                          '"exec_command", arguments, key=ctx.operation_key, run_id=ctx.run_id, '
                          'episode_id=ctx.episode_id)')
    intent = await _call(service, 'begin_command', assignment, TOOL, command, key=key, **identity)
    if intent['state'] == 'completed':
        receipt = intent['receipt']
    else:
        service = _job_access(ctx, 'run_command', 'await ctx.services["job_access"].run_command(assignment, '
                              'arguments, key=ctx.operation_key, run_id=ctx.run_id, episode_id=ctx.episode_id)')
        try:
            outcome = await _call(service, 'run_command', assignment, command, key=key, **identity)
        except (ValueError, TypeError, OSError, AcquisitionError) as error:
            outcome = {'facts': {}, 'native_outcome': {'failure': {
                'code': 'execution_action_failed', 'exception_type': type(error).__name__, 'detail': str(error)}}}
        outcome = finalize_scientific_command(assignment, command, outcome)
        before = intent['intent']['context_before']
        after = json.loads(canonical(before))
        if command.get('target', 'resource') == 'resource' and (
                command['workdir'] == assignment['workspace']
                or command['workdir'].startswith(assignment['workspace'].rstrip('/') + '/')):
            after.update(cwd=command['workdir'], environment=command['env'])
        after['revision'] += int(any(after[name] != before[name] for name in ('cwd', 'environment')))
        validations = assess_validations(assignment, outcome, after, tool_name=TOOL)
        service = _job_access(ctx, 'finish_command', 'await ctx.services["job_access"].finish_command('
                              'key, outcome, validations, context_after=after)')
        receipt = await _call(service, 'finish_command', key, outcome, validations, context_after=after)
    reference = publish_receipt(ctx.store, ctx.run_id, ctx.episode_id, assignment, receipt)
    failed = 'failure' in (receipt['outcome'].get('native_outcome') or {})
    return {'status': 'failed' if failed else 'completed', 'receipt': receipt, 'receipt_ref': reference,
            'operation_ref': digest(key), 'handoff': _handoff(assignment, receipt)}


TOOLS = {TOOL: exec_command}


def _resource(settings, assignment):
    """The old ``_resource_information``: the configured resource and the recorded inventory (context only)."""
    configuration = _resource_configuration(settings, assignment)
    return {'resource_kind': 'local', 'workspace': configuration['workspace'],
            **{name: configuration[name] for name in RESOURCE_KEYS if name in configuration},
            'inventory_snapshot': settings['initial_information'].get(assignment['resource_id'])}


def _capabilities(settings, assignment):
    """The old ``capabilities`` / ``initial_decision_context`` for this resource: configured operation
    availability, with no deployment or authentication probe."""
    configuration = _resource_configuration(settings, assignment)
    return {'resource_id': assignment['resource_id'], 'resource_kind': 'local', 'availability': 'unknown',
            'tool_names': [EXEC_COMMAND['name']],
            **{name: configuration[name] for name in ('workspace', 'policy', 'account', 'python_executable')
               if name in configuration},
            'inventory_snapshot': settings['initial_information'].get(assignment['resource_id'])}


def _instructions(settings, assignment):
    """The goal text, the resource instructions of the frozen launch library, and the library and knowledge
    paragraphs (the old ``instructions`` composer: with only ``tool`` permitted the reasoning and wait paragraphs
    never apply)."""
    library = LaunchInstructions(settings['launch_instructions_directory'])
    text = GOAL_INSTRUCTION
    selected = library.for_resource(_resource_configuration(settings, assignment))
    if selected:
        text += '\nResource instructions supplied from the frozen library:\n' + '\n\n'.join(
            section['text'] for section in selected['sections'])
    return text + KNOWLEDGE_INSTRUCTIONS + LAUNCH_INSTRUCTIONS, library


def _task_text(summary):
    """The old ``present_native_task`` renderer, over this episode's own summary: the task, the commands run so far
    and the practical progress and completion."""
    parts = ['TASK', '', 'Execute the assigned job on the local resource.', '', 'Assignment', '',
             json.dumps(summary['assignment'], indent=1, sort_keys=True)]
    if summary['selected_execution_task'] is not None:
        parts.extend(['', 'Selected execution task', '',
                      json.dumps(summary['selected_execution_task'], indent=1, sort_keys=True)])
    if summary['commands']:
        parts.extend(['', 'Commands run so far', '', json.dumps(summary['commands'], indent=1, sort_keys=True)])
    parts.extend(['', 'Current execution information', '',
                  json.dumps({'execution_completed': summary['execution_completion'] is not None,
                              'execution_progress': summary['execution_progress'],
                              'execution_completion': summary['execution_completion']}, indent=1, sort_keys=True)])
    return '\n'.join(parts)


def decide(summary, feedback, ctx):
    """One command: the model chooses it from the assignment, the resource, the commands run and their credit."""
    settings = ctx.settings
    assignment = summary['assignment']
    instructions, library = _instructions(settings, assignment)
    knowledge = ToolKnowledge(settings['tool_knowledge_directory'])
    context = {'task': _task_text(summary), 'feedback': feedback, 'execution_assignment': assignment,
               'execution_resource': _resource(settings, assignment),
               'execution_resource_capabilities': [_capabilities(settings, assignment)],
               'execution_initial_information': settings['initial_information'],
               'coordinator_workspace': settings['coordinator_workspace'],
               'execution_context': summary['execution_context'],
               'execution_progress': summary['execution_progress'],
               'execution_completion': summary['execution_completion'], 'commands': summary['commands'],
               'launch_instruction_library': library.context(), 'tool_knowledge': knowledge.context(),
               'selected_launch_instructions': library.materialize(assignment.get('launch_instructions')),
               'controller': summary['controller'], 'time_accounting': time_accounting(ctx.clock.progress_time)}
    if summary['selected_execution_task'] is not None:
        context['selected_execution_task'] = summary['selected_execution_task']
    schema = strict_output_schema(ACTION_SCHEMA, open_records_as_text=False,
                                  argument_transport_error=ARGUMENT_TRANSPORT_ERROR)
    return ModelRequest('REASONING', instructions, context, schema)


def action(response, summary, records, ctx):
    """The one command the answer selects, or a rejection: it names exec_command and operands that fit its schema
    and the resource (a workdir inside the workspace, a command text, an environment). A selection that fails here
    creates no unit; the model decides again with the feedback."""
    operations = _operations(ctx.settings, summary['assignment'])
    try:
        decoded = decode_strict_output(response, ACTION_SCHEMA, open_records_as_text=False,
                                       argument_transport_error=ARGUMENT_TRANSPORT_ERROR)
        Draft202012Validator(ACTION_SCHEMA).validate(decoded)
        selection = decoded['selection']
        names = [item['name'] for item in selection['env']]
        if len(set(names)) != len(names):
            raise ValueError('exec_command_environment_name_repeated')
        arguments = {'cmd': selection['cmd'], 'workdir': selection['workdir'], 'target': selection['target'],
                     'env': {item['name']: item['value'] for item in selection['env']}}
        operations.validate_action(summary['assignment'], TOOL, arguments)
    except (KeyError, TypeError, ValueError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(TOOL, {'arguments': arguments, 'assignment': summary['assignment']})
