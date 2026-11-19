"""The task: the resource agent for the assigned job on the selected local resource.

The model chooses one tool per unit. ``exec_command`` runs the shell command the model writes through the
``job_access`` service (on the assigned resource or in the coordinator workspace) and returns the saved receipt of
the command: its actual result and the validations of the original requirements it satisfied. A failed command is a
returned outcome like any other. ``resource_capabilities`` and ``resource_inspect`` read the actual capability
availability and the configured resource information (they select and submit nothing). ``resource_check_handoff``
makes the receiving check of an execution handoff. ``reason`` commits a typed scientific reasoning. The task always
offers a unit and never ends the Episode: no stopping budget is added; the yield controller stops it when the
commissioned requirements are met or the forecast no longer pays for another unit.

Old tool names (``resource.capabilities``, ``resource.inspect``, ``resource.check_handoff``) are not valid tool names
now (``[a-z][a-z0-9_]*``): they are ``resource_capabilities``, ``resource_inspect``, ``resource_check_handoff``.

BLOCKED-ON-JOB-SERVICE: the ``job_access`` service has no implementation yet (LAUNCH_MONITOR_EXTRACT_MECHANICS.md,
section 5 and "Not provided yet" item 4). The tools name it and call it; each raises where the call is made. The
practical receipt is published as a ``source`` record of provider ``episode.practical_receipt`` through
``ctx.store`` (the old ``PracticalReceiptInformation.publish`` reads ``store.db`` and the old runner's tables and
is not called: BLOCKED-ON-STORE-ACCESS, library not carried).

Settings (``ctx.settings``): ``resources`` (the configured resources by resource id), ``resource_capabilities`` (the
declared capability of each resource, old ``services.capabilities()``), ``initial_information`` (the recorded
inventory by resource id), ``coordinator_workspace``, ``launch_instructions_directory``,
``tool_knowledge_directory`` and ``task_yield_profiles``."""
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
from gene_annotation_episode.episodic_workflow.episode_support.instructions.structural_homology_evidence.runtime_prompt import (
    REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.structural_homology_evidence.terminal_execution import (
    TerminalExecution)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.hpc.resource_records import (
    CAPABILITY_SCHEMA, HANDOFF_SCHEMA, _validate, obj)
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
# The one native job family A102 may bind to a configured resource (old ``configuration`` check).
ALLOWED_NATIVE = {'native_protein_structure'}
RESOURCE_KEYS = ('kind', 'policy', 'account', 'ssh_argv', 'python_executable', 'scheduler')
# The tools the selected resource owns (the old ``tool_not_owned_by_resource_role`` set).
RESOURCE_TOOLS = ('resource_capabilities', 'resource_inspect', 'resource_check_handoff', TOOL)

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
CAPABILITIES = {
    'name': 'resource_capabilities',
    'description': 'Read actual capability availability and configured resource information; this does not select '
                   'or submit work.',
    'input_schema': obj({})}
INSPECT = {
    'name': 'resource_inspect',
    'description': 'Read the actual declared capability and binding status of one resource.',
    'input_schema': obj({'resource_id': {'type': 'string', 'minLength': 1}})}
CHECK_HANDOFF = {
    'name': 'resource_check_handoff',
    'description': 'Make the receiving check of an execution handoff through the selected resource interface.',
    'input_schema': obj({'handoff': HANDOFF_SCHEMA})}
REASON_DESCRIPTION = ('Commit a typed scientific reasoning over the records you hold. A commit with every section '
                      'empty is rejected.')

# The old ``goal.ResourceGoal.instructions`` text for this role, unchanged (the contract-information discovery
# sentence applied only where a profile was configured: ``contract_information_profile`` was ``None`` here).
GOAL_INSTRUCTION = (
    'Investigate preparation, execution and receiving interfaces on the selected local resource. Revise later '
    'choices from actual outcomes. Ordinary operations are tools; iteration belongs to this shared Episode. '
    'Preserve the parent job, input versions, CPU, search and constraints. Capabilities and duration estimates '
    'inform your decisions, without selecting an approach or imposing an order. Unknown/authentication-required '
    'resources remain explicit. Return the original parent-defined typed form. Only the configured local '
    'controller governs continuation.')
EXEC_INSTRUCTION = (
    ' Use exec_command to write and run the shell code the job needs; choose scripts, environment preparation, '
    'software invocation and recovery from the actual resource instructions and observed results. Each command is '
    'one ordinary episode action: its actual result and earned credit enter the iterator, including failure or zero '
    'progress. If a submission outcome is uncertain, investigate that original submission rather than create a '
    'duplicate. workdir and env apply to the selected command only; target=resource runs on the assigned resource '
    'and target=coordinator in the local run directory for supplied-input and transport work. Selecting a tool '
    'never ends your work: only the numerical controller does.')

SELECTION_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['selection'], 'properties': {
    'selection': {'type': 'object', 'additionalProperties': False, 'required': ['tool', 'arguments'], 'properties': {
        'tool': {'type': 'string', 'enum': [*RESOURCE_TOOLS, 'reason']},
        'arguments': {'type': 'string',
                      'description': 'The JSON text of the arguments object of the selected tool, valid against '
                                     'that tool\'s input_schema in the offered tools.'}}}}}


def _failure(code, references=()):
    return {'code': code, 'affected_refs': list(references), 'diagnostic_ref': None, 'partial_record_refs': []}


def _outcome(value=None, failure=None, record_refs=()):
    return {'status': 'failed' if failure else 'completed', 'record_refs': list(record_refs),
            'changed_record_refs': [], 'result': value, 'feedback': failure}


def _availability_failure(capability):
    return {'unavailable': 'resource_unavailable', 'authentication_required': 'resource_authentication_required',
            'unknown': 'resource_availability_unknown'}.get(capability['availability'])


def _resource_configuration(settings, selection):
    """The configured local resource of this selection (the old ``configuration`` checks of one resource)."""
    configuration = settings['resources'][selection['resource_id']]
    if configuration.get('kind') != 'local':
        raise ValueError('execution_resource_kind_conflict')
    if {name for name in configuration if name.startswith('native_') and name not in ALLOWED_NATIVE}:
        raise ValueError('a102_execution_resource_binding_conflict')
    return configuration


def _operations(settings, assignment):
    """The local transport's own validation of the assignment (old ``TerminalExecution``); a configuration or
    assignment it refuses raises and fails the run: it is not a model answer."""
    operations = TerminalExecution(_resource_configuration(settings, {'resource_id': assignment['resource_id']}),
                                   coordinator_workspace=settings['coordinator_workspace'],
                                   artifact_selector=terminal_artifact_paths)
    operations.validate_assignment(assignment)
    return operations


def capabilities(settings, selection):
    """The old ``ResourceResourceSelection.capabilities``: the declared capabilities validated against the
    capability schema; a declaration with no configured resource is listed accurately but with no tools; the
    selected resource's capability must exist and its tools must be bound (library candidate)."""
    values = {}
    for declared in settings['resource_capabilities']:
        value = _validate(declared, CAPABILITY_SCHEMA)
        if value['resource_id'] not in settings['resources']:
            value['tool_names'] = []
        values[value['resource_id']] = value
    selected = values.get(selection['resource_id'])
    if selected is None:
        raise ValueError('resource_not_bound')
    if not set(selected['tool_names']) <= set(RESOURCE_TOOLS):
        raise ValueError('resource_capability_tool_not_bound')
    return list(values.values())


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


def _handoff(assignment, receipt):
    """Whether the command handed the requested job off and the receipt matches this assignment (the old returnable
    practical receipt)."""
    job = receipt['outcome'].get('facts', {}).get('requested_job')
    return bool(job is not None and job.get('handoff') is not None
                and terminal_job_matches(assignment, receipt['outcome']))


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
    """The old adapter ``execute`` of ``exec_command`` (``terminal_operations.execute``): begin the intent
    (idempotent by operation key: a completed intent reuses its receipt), run the command, finalize the scientific
    command artifacts, update the cwd/env context revision for resource commands inside the workspace, assess the
    validations, finish the receipt and publish it. An execution error becomes a ``failure`` native outcome, which
    is still a completed, observed action."""
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


def resource_capabilities(arguments, ctx):
    """The old ``resource.capabilities``."""
    return _outcome({'capabilities': capabilities(ctx.settings, arguments['selection'])})


def resource_inspect(arguments, ctx):
    """The old ``ResourceInspection.inspect_resource``: the declared capability of the named resource, with a
    ``resource_not_bound`` or availability failure as its outcome."""
    reference = arguments['arguments']['resource_id']
    capability = next((value for value in capabilities(ctx.settings, arguments['selection'])
                       if value['resource_id'] == reference), None)
    if capability is None:
        return _outcome(failure=_failure('resource_not_bound', [reference]))
    code = _availability_failure(capability)
    if code is None and reference not in ctx.settings['resources']:
        code = 'resource_not_bound'
    return _outcome({'capability': capability}, _failure(code, [reference]) if code else None)


async def resource_check_handoff(arguments, ctx):
    """The old ``ResourceHandoffCheck.check_selected_handoff``: the receiving check of the handoff through the
    resource interface (the ``job_access`` service now), with the old failure for an invalid handoff. The service
    replies with the outcome in the shape of ``_outcome`` whose ``result`` is the checked
    ``execution_handoff_v1``."""
    handoff = arguments['arguments']['handoff']
    try:
        if handoff['resource_selection']['resource_id'] not in ctx.settings['resources']:
            raise ValueError('resource_not_bound')
        service = _job_access(ctx, 'check_handoff', 'await ctx.services["job_access"].check_handoff(handoff, '
                              'key=ctx.operation_key, run_id=ctx.run_id, episode_id=ctx.episode_id)')
        return await _call(service, 'check_handoff', handoff, key=ctx.operation_key, run_id=ctx.run_id,
                           episode_id=ctx.episode_id)
    except (ValueError, KeyError, OSError) as error:
        if str(error) == 'resource_information_identity_conflict':
            raise
        return _outcome(failure=_failure('invalid_resource_handoff', [handoff['execution_handle']]))


def reason(arguments, ctx):
    """Commit the model's typed reasoning (the old ``Store.commit_reasoning`` path of the ``reason`` action; the
    owner of interpretation accounts is named by the system)."""
    result = ctx.store.commit_reasoning(arguments['arguments']['commit'], arguments['scope'], ctx.operation_key)
    return _outcome(result)


TOOLS = {TOOL: exec_command, 'resource_capabilities': resource_capabilities, 'resource_inspect': resource_inspect,
         'resource_check_handoff': resource_check_handoff, 'reason': reason}


def _catalog(commit_schema):
    """The tools the model is offered (the old ``catalog``: ``resource.capabilities`` plus the adapter's tools,
    here the resource's own four)."""
    return [CAPABILITIES, INSPECT, CHECK_HANDOFF, EXEC_COMMAND,
            {'name': 'reason', 'description': REASON_DESCRIPTION,
             'input_schema': obj({'commit': commit_schema})}]


def _resource(settings, selection):
    """The old ``_resource_information``: the configured resource and the recorded inventory (context only)."""
    configuration = _resource_configuration(settings, selection)
    return {'resource_kind': 'local', 'workspace': configuration['workspace'],
            **{name: configuration[name] for name in RESOURCE_KEYS if name in configuration},
            'inventory_snapshot': settings['initial_information'].get(selection['resource_id'])}


def _instructions(settings, selection):
    """The goal text, the resource instructions of the frozen launch library, and the library, reasoning and
    knowledge paragraphs (the old ``instructions`` composer: the redelivery, pending-child wait and
    request_context paragraphs describe actions that no longer exist and are not carried)."""
    library = LaunchInstructions(settings['launch_instructions_directory'])
    text = GOAL_INSTRUCTION + EXEC_INSTRUCTION + ' ' + REASONING_COMMIT_REQUIREMENT
    selected = library.for_resource(_resource_configuration(settings, selection))
    if selected:
        text += '\nResource instructions supplied from the frozen library:\n' + '\n\n'.join(
            section['text'] for section in selected['sections'])
    return text + KNOWLEDGE_INSTRUCTIONS + LAUNCH_INSTRUCTIONS, library


def _task_text(summary):
    """The task, the commands run so far, the receiving checks and the practical progress and completion."""
    parts = ['TASK', '', 'Carry the assigned job through the selected local resource.', '', 'Job assignment', '',
             json.dumps(summary['assignment'], indent=1, sort_keys=True)]
    if summary['commands']:
        parts.extend(['', 'Commands run so far', '', json.dumps(summary['commands'], indent=1, sort_keys=True)])
    if summary['checks']:
        parts.extend(['', 'Receiving checks so far', '', json.dumps(summary['checks'], indent=1, sort_keys=True)])
    parts.extend(['', 'Current execution information', '',
                  json.dumps({'execution_completed': summary['execution_completion'] is not None,
                              'execution_progress': summary['execution_progress'],
                              'execution_completion': summary['execution_completion'],
                              'execution_handoffs': summary['handoffs']}, indent=1, sort_keys=True)])
    return '\n'.join(parts)


def decide(summary, feedback, ctx):
    """One unit: the model chooses a tool from the assignment, the resource, the commands run and their credit."""
    settings = ctx.settings
    launch = summary['launch']
    selection = launch['resource_selection']
    instructions, library = _instructions(settings, selection)
    knowledge = ToolKnowledge(settings['tool_knowledge_directory'])
    context = {'task': _task_text(summary), 'feedback': feedback, 'launch_assignment': launch,
               'execution_assignment': summary['assignment'],
               'resource_context': _resource(settings, selection),
               'resource_capabilities': capabilities(settings, selection),
               'execution_initial_information': settings['initial_information'],
               'coordinator_workspace': settings['coordinator_workspace'],
               'execution_context': summary['execution_context'],
               'execution_progress': summary['execution_progress'],
               'execution_completion': summary['execution_completion'], 'commands': summary['commands'],
               'handoff_checks': summary['checks'], 'execution_handoffs': summary['handoffs'],
               'reasonings': summary['reasonings'], 'tools': _catalog(summary['reasoning_schema']),
               'launch_instruction_library': library.context(), 'tool_knowledge': knowledge.context(),
               'selected_launch_instructions': library.materialize(launch.get('launch_instructions')),
               'controller': summary['controller'], 'time_accounting': time_accounting(ctx.clock.progress_time)}
    return ModelRequest('REASONING', instructions, context, SELECTION_SCHEMA)


def _empty_commit(commit):
    """The old empty-reasoning test: every section of the commit is present and none has a row."""
    return all(value == [] for value in commit.values())


def action(response, summary, records, ctx):
    """The one tool call the answer selects, or a rejection: it names an offered tool and arguments that fit that
    tool's input schema and the resource (for a command: a workdir inside the workspace, a command text, an
    environment; for a reasoning: a commit with at least one row). A selection that fails here creates no unit; the
    model decides again with the feedback."""
    assignment = summary['assignment']
    operations = _operations(ctx.settings, assignment)
    catalog = {item['name']: item for item in _catalog(summary['reasoning_schema'])}
    try:
        Draft202012Validator(SELECTION_SCHEMA).validate(response)
        selection = response['selection']
        name = selection['tool']
        arguments = json.loads(selection['arguments'])
        Draft202012Validator(catalog[name]['input_schema']).validate(arguments)
        if name == TOOL:
            operations.validate_action(assignment, TOOL, arguments)
        if name == 'reason' and _empty_commit(arguments['commit']):
            raise ValueError('empty_reasoning_commit')
    except (KeyError, TypeError, ValueError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(name, {'arguments': arguments, 'assignment': assignment,
                           'selection': summary['launch']['resource_selection'], 'scope': summary['scope']})
