"""The task: the execution agent for the assigned job on the local resource.

The model writes the shell command; the episode's tool ``exec_command`` runs it on the local resource through the
``job_access`` service and returns the receipt of the command (its actual result and the validations of the
original requirements it satisfied). Two read-only lookup tools stand where the old decision exchange served the
run-frozen instruction libraries (``knowledge.*`` and ``launch.instructions.*``). The task always offers a unit and
never ends the Episode: no stopping budget is added; the yield controller stops it when the assignment's
completion is verified or the forecast no longer pays for another action.

BLOCKED-ON-JOB-SERVICE: the ``job_access`` service has no implementation yet (LAUNCH_MONITOR_EXTRACT_MECHANICS.md,
section 5 and "Not provided yet" item 4). The tool names it and calls it; it raises where the call is made."""
import inspect
import json

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.findings.gene_context_evidence.terminal_scientific_evidence import (
    terminal_artifact_paths)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions, catalog as launch_instruction_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.gene_context_evidence.terminal_execution import (
    TerminalExecution)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import (
    ContractError, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.practical_execution_records import (
    canonical, digest)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge, catalog as knowledge_catalog)

CHILD_SLOTS = {}
SERVICES = ('job_access',)

# The old ``terminal_contracts.operation_catalog('local')``: the one general capability.
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

# The lookups into the run-frozen libraries: the read operations of each catalogue. ``launch.instructions.select``
# pins sections for a child assignment; this episode has no child, so it is not offered.
KNOWLEDGE_LOOKUPS = {entry['name']: entry for entry in knowledge_catalog()}
LAUNCH_LOOKUPS = {entry['name']: entry for entry in launch_instruction_catalog()
                  if entry['name'] != 'launch.instructions.select'}
LOOKUP_ANSWER = (' A lookup tool takes one JSON object in arguments_json: name (one of the listed operation names) '
                 'and arguments (that operation\'s operands).')

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
ANSWER_INSTRUCTION = (
    ' Answer with the tool you select and its operands as one JSON object in arguments_json. For exec_command the '
    'operands are cmd, workdir, env and, optionally, target.' + LOOKUP_ANSWER)
TOOL_NAMES = ('exec_command', 'knowledge_lookup', 'launch_instruction_lookup')
RESOURCE_KEYS = ('kind', 'policy', 'account', 'ssh_argv', 'python_executable', 'scheduler')


def _operations(settings, assignment):
    """The local transport's own validation of the assignment and of an action (old ``TerminalExecution``); a
    configuration or assignment it refuses raises and fails the run: it is not a model answer."""
    operations = TerminalExecution(settings['resource'], coordinator_workspace=settings['coordinator_workspace'],
                                   artifact_selector=terminal_artifact_paths)
    operations.validate_assignment(assignment)
    return operations


async def exec_command(arguments, ctx):
    """Run the selected command through ``job_access`` and keep its receipt as a record the Episode holds.

    The service executes once per ``ctx.operation_key`` and reports a failed command as a receipt, as the old
    ``TerminalOperations.execute`` did (begin the intent, run, finalize the scientific command proof, assess the
    validations of the original requirements, finish the receipt)."""
    service = ctx.services['job_access']
    if not hasattr(service, 'exec_command'):
        raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access.exec_command(assignment, arguments, *, key); '
                                  'wanted call: await ctx.services["job_access"].exec_command('
                                  'arguments["assignment"], arguments["arguments"], key=ctx.operation_key)')
    reply = service.exec_command(arguments['assignment'], arguments['arguments'], key=ctx.operation_key)
    if inspect.isawaitable(reply):
        reply = await reply
    receipt = reply['receipt']
    receipt_ref = ctx.store.artifact(canonical(receipt), 'application/json')
    return {'status': 'completed', 'receipt': receipt, 'receipt_ref': receipt_ref,
            'operation_ref': digest(ctx.operation_key), 'handoff': reply['handoff']}


def knowledge_lookup(arguments, ctx):
    """One read of the run-frozen tool-instruction library (``knowledge.search``, ``.entry``, ``.read``)."""
    return ToolKnowledge(ctx.settings['tool_knowledge_directory']).execute(arguments['name'], arguments['arguments'])


def launch_instruction_lookup(arguments, ctx):
    """One read of the run-frozen launch instruction library (``launch.instructions.search``, ``.entry``,
    ``.read``)."""
    return LaunchInstructions(ctx.settings['launch_instructions_directory']).execute(arguments['name'],
                                                                                      arguments['arguments'])


TOOLS = {'exec_command': exec_command, 'knowledge_lookup': knowledge_lookup,
         'launch_instruction_lookup': launch_instruction_lookup}


def _resource(settings, assignment):
    """The old ``_resource_information``: the configured resource and the recorded inventory (context only)."""
    resource = settings['resource']
    return {'resource_kind': 'local', 'workspace': resource['workspace'],
            **{name: resource[name] for name in RESOURCE_KEYS if name in resource},
            'inventory_snapshot': assignment['inventory_snapshot']}


def _instructions(settings):
    library = LaunchInstructions(settings['launch_instructions_directory'])
    text = GOAL_INSTRUCTION
    selected = library.for_resource(settings['resource'])
    if selected:
        text += '\nResource instructions supplied from the frozen library:\n' + '\n\n'.join(
            section['text'] for section in selected['sections'])
    return text + KNOWLEDGE_INSTRUCTIONS + LAUNCH_INSTRUCTIONS + ANSWER_INSTRUCTION, library


def _task_text(summary):
    """The old selected-execution presentation (``present_native_task``), over this episode's own summary: the
    assignment, what the commands did so far and the verified completion."""
    parts = ['TASK', '', 'Execute the assigned job on the local resource.', '', 'Assignment', '',
             json.dumps(summary['assignment'], indent=1, sort_keys=True)]
    if summary['selected_execution_task'] is not None:
        parts.extend(['', 'Selected execution task', '',
                      json.dumps(summary['selected_execution_task'], indent=1, sort_keys=True)])
    if summary['commands']:
        parts.extend(['', 'Commands run so far', '', json.dumps(summary['commands'], indent=1, sort_keys=True)])
    if summary['lookups']:
        parts.extend(['', 'Lookups made so far', '', json.dumps(summary['lookups'], indent=1, sort_keys=True)])
    parts.extend(['', 'Progress', '', json.dumps({'execution_progress': summary['execution_progress'],
                                                  'execution_completion': summary['execution_completion']},
                                                 indent=1, sort_keys=True)])
    return '\n'.join(parts)


def _output_schema():
    return {'type': 'object', 'additionalProperties': False, 'required': ['tool', 'arguments_json'],
            'properties': {'tool': {'enum': list(TOOL_NAMES)},
                           'arguments_json': {'type': 'string', 'description': (
                               'exec_command operands as one JSON object: '
                               + json.dumps(EXEC_COMMAND['input_schema'], sort_keys=True)
                               + '. knowledge_lookup operands: {"name": one of '
                               + json.dumps(sorted(KNOWLEDGE_LOOKUPS)) + ', "arguments": ...}. '
                               'launch_instruction_lookup operands: {"name": one of '
                               + json.dumps(sorted(LAUNCH_LOOKUPS)) + ', "arguments": ...}.')}}}


def decide(summary, feedback, ctx):
    """One action: the model chooses it from the assignment, the resource, the commands run and their credit."""
    settings = ctx.settings
    assignment = summary['assignment']
    instructions, library = _instructions(settings)
    selected = library.materialize(assignment.get('launch_instructions'))
    knowledge = ToolKnowledge(settings['tool_knowledge_directory'])
    context = {'task': _task_text(summary), 'feedback': feedback, 'execution_assignment': assignment,
               'execution_resource': _resource(settings, assignment),
               'coordinator_workspace': settings['coordinator_workspace'],
               'execution_progress': summary['execution_progress'],
               'execution_completion': summary['execution_completion'], 'commands': summary['commands'],
               'lookups': summary['lookups'], 'launch_instruction_library': library.context(),
               'tool_knowledge': knowledge.context(), 'selected_launch_instructions': selected,
               'controller': summary['controller'], 'time_accounting': time_accounting(ctx.clock.progress_time)}
    if summary['selected_execution_task'] is not None:
        context['selected_execution_task'] = summary['selected_execution_task']
    return ModelRequest('REASONING', instructions, context, _output_schema())


def _lookup_arguments(tool, arguments):
    """A lookup names one operation of its library and that operation's operands, which fit its schema."""
    lookups = KNOWLEDGE_LOOKUPS if tool == 'knowledge_lookup' else LAUNCH_LOOKUPS
    if set(arguments) != {'name', 'arguments'} or arguments['name'] not in lookups:
        raise ValueError('lookup_name_and_arguments_required')
    validate_schema(arguments['arguments'], lookups[arguments['name']]['input_schema'])
    return {'name': arguments['name'], 'arguments': arguments['arguments']}


def action(response, summary, records, ctx):
    """The one action the answer selects, or a rejection: it names a tool of this episode and operands that fit its
    schema and, for a command, the resource (a workdir inside the workspace, a command text, an environment)."""
    operations = _operations(ctx.settings, summary['assignment'])
    try:
        tool = response['tool']
        if tool not in TOOL_NAMES:
            raise ValueError('execution_tool_not_available')
        arguments = json.loads(response['arguments_json'])
        if not isinstance(arguments, dict):
            raise ValueError('arguments_json_must_be_a_JSON_object')
        if tool == 'exec_command':
            validate_schema(arguments, EXEC_COMMAND['input_schema'])
            operations.validate_action(summary['assignment'], 'exec_command', arguments)
            return ToolCall('exec_command', {'arguments': arguments, 'assignment': summary['assignment']})
        return ToolCall(tool, _lookup_arguments(tool, arguments))
    except (KeyError, TypeError, ValueError, ContractError) as error:
        raise Rejected(rejection_feedback(error, category='arguments_or_reference'))
