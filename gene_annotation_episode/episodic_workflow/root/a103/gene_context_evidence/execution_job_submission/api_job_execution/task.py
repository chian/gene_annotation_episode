"""The task: one selected action per unit on the one assigned API service (carried from ``task.py``,
``instructions.py``, ``action_policy.py``, ``decision_inputs.py``, ``decision_state.py``, ``decision_presentation.py``,
``internal_summary.py``, ``operations.py`` and ``waiting.py``).

Each decision the model selects one of: ``service_operation`` (one operation of the API service's catalog),
``capabilities`` (the caller-bound resource configuration and recorded inventory), ``wait`` (only for a service job
that continues remotely: assignment version ``api_service_assignment_v1``, the old ``permitted_common_actions``),
and, when the settings name the libraries, ``launch_instructions`` and ``tool_knowledge`` lookups. This episode has
no ``reason`` action and no child. A selection that fails admission is rejected and creates no unit. The task offers
a unit at every decision and never ends the Episode: the yield controller does. The old goal text replaced the
default instructions (``replaces_default_instructions``); it is the instruction text here. The prompt is this
episode's own (old ``decision_presentation.render_api_launch_prompt``): the whole TASK repeated with the current
STEERING.

Settings read (the episode's own entry of the run's ``continuation`` collaborator): ``resources`` and
``initial_information`` (caller-bound resource configuration and inventory, by resource id), ``handoff_unit`` and
``acquired_record_unit`` (positive credit units passed to the service), ``task_yield_profiles`` (the controller's),
and optionally ``launch_instructions_directory`` and ``tool_knowledge_directory``.

BLOCKED-ON-JOB-SERVICE. The API service executor (old ``APIServiceExecution`` / ``api_execution``: its operation
catalog, its execution of one operation with the credit and facts it returns, its capabilities, the received BV-BRC
values and decision context it showed the model, and a wait on a service job) is the ``job_access`` service of
``LAUNCH_MONITOR_EXTRACT_MECHANICS.md``; no module of the library holds it and the system does not provide it yet.
This file names the service and the calls it wants (``read('api_catalog', ...)``, ``read('api_capabilities', ...)``,
``read('received_bvbrc_context', ...)``, ``read('api_decision_context', ...)``, ``api_execute(...)``,
``wait_for_job(...)``) and raises ``NotImplementedError('BLOCKED-ON-JOB-SERVICE: ...')`` where the service does not
offer them. The handoff record (a row of a declared job ledger work table) is not defined either:
``write_handoff_record`` raises.
"""
from collections.abc import Mapping
import copy
import json
import math

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.api_error_feedback import (
    is_api_error_return)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions, catalog as launch_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.gene_context_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge, catalog as knowledge_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

CHILD_SLOTS = {}
SERVICES = ('job_access',)
WAIT_VERSION = 'api_service_assignment_v1'
RESOURCE_KEYS = ('workspace', 'policy', 'account', 'python_executable', 'service', 'base_url')
ASSIGNMENT_KEYS = ('version', 'resource_id', 'service', 'endpoint', 'constraints', 'launch_instructions',
                   'subject_ref', 'algorithm', 'database', 'parameters', 'page_size', 'request')

GOAL_TEXT = (
    'Carry out the assigned work through {service} using one selected operation each turn. Keep the original '
    'inputs, request, resource and parent constraints fixed. Choose useful preparation, service requests, '
    'observations or repair from the actual available operations and received outcomes. Distinguish an immediate '
    'returned response from a service job that continues remotely. Preserve the actual request or job identity and '
    'submission uncertainty; a missing reply does not establish that no job was created. Establish the requested '
    'usable monitoring/results handoff from recorded service facts. The configured controller governs '
    'continuation; verified original handoff completion gives exact zero future credit.')
WAIT_TEXT = (
    '\nA wait is offered because this assignment is a service job that continues remotely: use it to give the '
    'job time to change state. Waiting reports only what the service then records; it does not establish the job '
    'state and earns no scientific credit.')
ACTION_TEXT = (
    '\nEach answer selects one action: tool=service_operation with the operation (a name of the callable '
    'operations) and its arguments; tool=capabilities to read the caller-bound resource configuration and recorded '
    'inventory (no discovery, no selection)')
TEXT = {'type': 'string', 'minLength': 1}
OPEN_RECORD = {'type': 'object'}


# -- the service, as this episode wants to call it ---------------------------------------------------------------

def job_read(ctx, member, *arguments):
    """A recorded read of the ``job_access`` service by a decision (the service offers it or the block is explicit)."""
    try:
        return ctx.services['job_access'].read(member, *arguments)
    except AttributeError as error:
        raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access.' + member) from error


def required_member(service, member):
    """The service's operation, or the explicit block when the system does not provide it yet."""
    call = getattr(service, member, None)
    if call is None:
        raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job_access.' + member)
    return call


def assignment_of(summary):
    """The original assignment (the old ``context.assignment``), from the parent input."""
    return {name: summary[name] for name in ASSIGNMENT_KEYS if name in summary}


def catalog_of(summary, ctx):
    """The API service executor's operation catalog for this assignment: ``{operation: contract}``."""
    catalog = job_read(ctx, 'api_catalog', summary['resource_id'], assignment_of(summary))
    if not isinstance(catalog, dict):
        raise TypeError('api_catalog_must_be_a_mapping_of_operation_to_contract')
    return catalog


def resource_information(settings, resource_id, entries):
    """Old ``_resource_information`` for the one bound API resource: its configuration, its operation names and the
    boolean configuration facts the service reports (no deployment or authentication probe)."""
    config = settings['resources'][resource_id]
    value = {'resource_id': resource_id, 'resource_kind': 'api', 'availability': 'unknown',
             'tool_names': [entry['name'] for entry in entries],
             **{key: copy.deepcopy(config[key]) for key in RESOURCE_KEYS if key in config},
             'inventory_snapshot': copy.deepcopy(settings['initial_information'].get(resource_id))}
    facts = {}
    for entry in entries:
        reported = entry.get('configuration', {})
        for name in ('ncbi_contact_configured', 'provider_rate_state_configured'):
            if name not in reported:
                continue
            actual = reported[name]
            if type(actual) is not bool:
                raise ValueError('api_configuration_fact_must_be_boolean')
            if name in facts and facts[name] != actual:
                raise ValueError('api_configuration_fact_conflict')
            facts[name] = actual
    if facts:
        value['api_configuration_facts'] = facts
    return value


def selected_execution_task(summary, resource):
    """Old ``_with_selected_execution_task``: the parent's scientific task, shown only for an ``ebi_hmmer`` request."""
    if summary['service'] != 'ebi_hmmer' or summary['scientific_question'] is None:
        return None
    return {'version': 'selected_execution_task_v1', 'scientific_question': summary['scientific_question'],
            'selected_tool_info': summary['selected_tool_info'],
            'requests': [{'resource_id': summary['resource_id'], 'resource_kind': 'api',
                          'endpoint': copy.deepcopy(summary.get('endpoint')),
                          'constraints': copy.deepcopy(summary.get('constraints', {})),
                          'job': assignment_of(summary), 'resource': resource}],
            'constraints': summary.get('constraints', {}), 'selector': None, 'result_description': None}


# -- instructions, offered actions, the output schema ---------------------------------------------------------------

def wait_permitted(summary):
    """Old ``permitted_common_actions``: ``tool`` always; ``wait`` only for ``api_service_assignment_v1``."""
    return summary['version'] == WAIT_VERSION


def offered_actions(summary, settings):
    names = ['service_operation', 'capabilities']
    if wait_permitted(summary):
        names.append('wait')
    if 'launch_instructions_directory' in settings:
        names.append('launch_instructions')
    if 'tool_knowledge_directory' in settings:
        names.append('tool_knowledge')
    return names


def instructions(summary, settings):
    """Old ``instructions`` for this role: the goal text replaces the default instructions; the lookup libraries add
    their text. The text of the old decision exchange, of pending child delivery and of the in-process child wait
    describes actions that no longer exist and is not carried."""
    offered = offered_actions(summary, settings)
    text = GOAL_TEXT.format(service=summary['service']) + ACTION_TEXT
    text += '; tool=wait with the condition, only when a wait is offered.' if 'wait' in offered else '.'
    if 'wait' in offered:
        text += WAIT_TEXT
    if 'tool_knowledge' in offered:
        text += KNOWLEDGE_INSTRUCTIONS
    if 'launch_instructions' in offered:
        text += LAUNCH_INSTRUCTIONS
    return text


def _closed(properties):
    return {'type': 'object', 'additionalProperties': False, 'required': list(properties),
            'properties': properties}


def _branch(tool, arguments):
    return _closed({'kind': {'type': 'string', 'const': 'tool'}, 'tool': {'type': 'string', 'const': tool},
                    'arguments': arguments})


def output_schema(summary, settings, catalog):
    branches = [_branch('service_operation', _closed({'operation': {'type': 'string', 'const': name},
                                                      'arguments': copy.deepcopy(contract['input_schema'])}))
                for name, contract in sorted(catalog.items())]
    branches.append(_branch('capabilities', _closed({})))
    if wait_permitted(summary):
        branches.append(_branch('wait', _closed({'condition': OPEN_RECORD})))
    if 'launch_instructions_directory' in settings:
        branches.append(_branch('launch_instructions', _closed({
            'operation': {'type': 'string', 'enum': [item['name'] for item in launch_catalog()]},
            'arguments': OPEN_RECORD})))
    if 'tool_knowledge_directory' in settings:
        branches.append(_branch('tool_knowledge', _closed({
            'operation': {'type': 'string', 'enum': [item['name'] for item in knowledge_catalog()]},
            'arguments': OPEN_RECORD})))
    return _closed({'selection': {'anyOf': branches}})


# -- the prompt (old decision_presentation: the TASK repeated with the current STEERING) -------------------------------

def _scalar(value):
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)


def _values(value):
    if isinstance(value, (Mapping, list, tuple)):
        return '```json\n' + json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + '\n```'
    return 'Not supplied.' if value is None else _scalar(value)


def _table(headers, rows):
    lines = ['| ' + ' | '.join(headers) + ' |', '|' + '---|' * len(headers)]
    lines.extend('| ' + ' | '.join(_scalar(cell).replace('\n', ' ') for cell in row) + ' |' for row in rows)
    return '\n'.join(lines)


def _section(parts, title, body):
    parts.extend(['', title, body if isinstance(body, str) else _values(body)])


def _schema_text(schema, label):
    return label + ' (JSON Schema):\n' + _values(schema)


def _scope(scope):
    """Name the assigned set without exposing its opaque Store handles."""
    if not isinstance(scope, Mapping):
        return 'Not supplied.'
    subjects = scope.get('subject_refs', ())
    names = {reference: 'assigned subject ' + str(index + 1) for index, reference in enumerate(subjects)}
    rows = [('Subject', name) for name in names.values()]
    if 'segments' in scope:
        for index, segment in enumerate(scope['segments']):
            if not isinstance(segment, Mapping):
                continue
            subject = segment.get('target_ref', segment.get('subject_ref'))
            prefix = 'Region ' + str(index + 1)
            rows.append((prefix + ' subject', names.get(subject, 'assigned subject')))
            for field in ('start', 'end', 'unit', 'strand'):
                if field in segment:
                    rows.append((prefix + ' ' + field, segment[field]))
            if 'member_ref' in segment:
                rows.append((prefix + ' member', 'explicitly assigned original member'))
    else:
        rows.append(('Region', 'The assigned subject set; no narrower interval supplied.'))
    for index, _ in enumerate(scope.get('read_selection_refs', ())):
        rows.append(('Read selection', 'assigned original-read selection ' + str(index + 1)))
    return _table(('Scope item', 'Supplied value'), rows)


def _task(state, text):
    assignment = state['execution_assignment']
    selected_task = state.get('selected_execution_task')
    question = state['scientific_question']
    if selected_task is not None:
        question = selected_task['scientific_question']
    parts = ['TASK']
    _section(parts, 'Scientific QUESTION', question if isinstance(question, str) and question else
             'Not supplied in this recorded input.')
    _section(parts, 'Assigned job', state['assigned_job'] if state['assigned_job'] is not None else 'Not supplied.')
    _section(parts, 'Assigned scope', _scope(state['scope']))
    _section(parts, 'Selected API work', {key: assignment[key] for key in ('resource_id', 'service', 'endpoint')
                                          if key in assignment})
    _section(parts, 'Parent constraints', assignment.get('constraints', {}))
    if selected_task is not None:
        for tool in selected_task['selected_tool_info'] or ():
            _section(parts, 'Parent-selected tool guidance: ' + tool['name'] + ' (' + tool['resources'] + ')',
                     tool['description'] + '\n\n' + tool['instructions'])
    resource = state['execution_resource']
    _section(parts, 'Configured resource', {key: resource[key] for key in (
        'resource_id', 'resource_kind', 'service', 'base_url', 'availability', 'api_configuration_facts')
        if key in resource})
    _section(parts, 'Exact assigned scientific request',
             assignment['request'] if 'request' in assignment else
             {key: assignment[key] for key in ('subject_ref', 'algorithm', 'database', 'parameters', 'page_size')
              if key in assignment})
    _section(parts, 'Execution method and decision rules', text)
    for name, tool in sorted(state['tools'].items()):
        _section(parts, 'Callable operation: ' + name, tool.get('description', ''))
        if 'instructions' in tool:
            _section(parts, 'Supplied instructions for ' + name, tool['instructions'])
        if 'input_schema' in tool:
            _section(parts, 'Arguments for ' + name, _schema_text(tool['input_schema'], 'arguments'))
    manuals = state['selected_launch_instructions'] or {}
    for section in manuals.get('sections', ()):
        _section(parts, 'Selected resource instructions: ' + section['entry_id'] + ' / ' + section['section_id'],
                 section['text'])
    return '\n'.join(parts)


def _band(value):
    """Display a recorded forecast: the value, never its unavailable code coordinates."""
    if value is None:
        return 'unavailable'
    return _scalar(value)


def _error_text(value):
    """The entire recorded error, outside operational-summary masking."""
    return '```json\n' + json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n```'


def _lookup(value):
    """One requested lookup result (old ``_lookup``: errors whole, instruction windows as text)."""
    if not isinstance(value, Mapping):
        return _values(value)
    if is_api_error_return(value) or is_api_error_return(value.get('result')):
        return _error_text(value)
    content = value.get('result', value)
    if isinstance(content, Mapping) and 'text' in content:
        parts = [str(content['text'])]
        page = {key: content[key] for key in ('entry_id', 'section_id', 'coordinate_unit', 'offset',
                                              'returned_lines', 'total_lines', 'next_query') if key in content}
        if page:
            _section(parts, 'Selected instruction window', page)
        return '\n'.join(parts)
    return _error_text(value) if value.get('feedback') is not None else _values(content)


def _steering(state, summary):
    parts = ['STEERING']
    table = summary['yield_table']
    if table is not None or 'current_credit' in state:
        _section(parts, 'Current operational continuation', _table(
            ('Completed own actions', 'Current operational credit', 'Expected next gain', 'Continuation cost',
             'Controller decision'),
            [(None if table is None else table['completed_units'], state['current_credit'],
              _band(None if table is None else table['expected_next_gain']),
              None if table is None else table['continuation_cost'],
              'not supplied' if table is None else 'stop' if table['stop_requested'] else 'continue')]))
    _section(parts, 'Original handoff completion', _scalar(summary['completed']))
    ordinary = {}
    for operation, returned in summary['api_progress'].items():
        if is_api_error_return(returned) or is_api_error_return(returned.get('facts')):
            _section(parts, 'Complete recorded API error from ' + operation, _error_text(returned))
        else:
            ordinary[operation] = returned
    if ordinary:
        _section(parts, 'Recorded own API outcomes', ordinary)
    outcome = summary['last_outcome']
    if isinstance(outcome, Mapping):
        error = is_api_error_return(outcome) or is_api_error_return(outcome.get('result')) \
            or outcome.get('feedback') is not None
        _section(parts, 'Latest own action — complete returned error' if error else 'Latest own action',
                 _error_text(outcome) if error else outcome)
    feedback = state['feedback']
    if feedback is not None and (not isinstance(outcome, Mapping) or feedback != outcome.get('feedback')):
        _section(parts, 'Complete returned feedback', _error_text(feedback))
    for value in summary['lookups']:
        _section(parts, 'Requested information; continue the same decision', _lookup(value))
    return '\n'.join(parts)


def render_api_launch_prompt(state, summary, text):
    """Repeat the complete assigned TASK with the supplied current own STEERING (old ``render_api_launch_prompt``)."""
    return _task(state, text) + '\n\n' + _steering(state, summary)


# -- deciding ---------------------------------------------------------------------------------------------------------

def decide(summary, feedback, ctx):
    settings = ctx.settings
    catalog = catalog_of(summary, ctx)
    entries = job_read(ctx, 'api_capabilities', summary['resource_id'])
    resource = resource_information(settings, summary['resource_id'], entries)
    state = {'assigned_job': summary['message'], 'scientific_question': summary['scientific_question'],
             'scope': summary['scope'], 'execution_assignment': assignment_of(summary),
             'execution_resource': resource, 'tools': catalog, 'selected_launch_instructions': None,
             'selected_execution_task': selected_execution_task(summary, resource),
             'current_credit': summary['credit'], 'feedback': feedback}
    if 'launch_instructions_directory' in settings:
        state['selected_launch_instructions'] = LaunchInstructions(
            settings['launch_instructions_directory']).materialize(summary.get('launch_instructions'))
    elif summary.get('launch_instructions') is not None:
        raise ValueError('selected_launch_instructions_require_the_launch_instructions_directory_setting')
    text = instructions(summary, settings)
    context = {'prompt': render_api_launch_prompt(state, summary, text),
               'received_bvbrc_values': job_read(ctx, 'received_bvbrc_context', summary['resource_id']),
               'api_decision_context': job_read(ctx, 'api_decision_context', summary['resource_id'],
                                                assignment_of(summary)),
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    if 'launch_instructions_directory' in settings:
        context['launch_instruction_library'] = LaunchInstructions(settings['launch_instructions_directory']).context()
    if 'tool_knowledge_directory' in settings:
        context['tool_knowledge'] = ToolKnowledge(settings['tool_knowledge_directory']).context()
    return ModelRequest('REASONING', text, context,
                        generation_schema(output_schema(summary, settings, catalog)))


def _named_refs(value):
    """The record references a model-built value names: values under ``ref``, ``..._ref`` and ``..._refs``."""
    found = []
    if isinstance(value, dict):
        for name, child in value.items():
            if name == 'ref' or name.endswith('_ref'):
                found.append(child)
            elif name.endswith('_refs'):
                found.extend(child)
            else:
                found.extend(_named_refs(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_named_refs(child))
    return found


def action(response, summary, records, ctx):
    """Admit the model's selection (old ``apply_response`` for a tool or wait): a rejection creates no unit."""
    schema = output_schema(summary, ctx.settings, catalog_of(summary, ctx))
    try:
        decoded = decode_response(response, schema)
        Draft202012Validator(schema).validate(decoded)
        selection = decoded['selection']
        unheld = [ref for ref in _named_refs(selection['arguments']) if not records.holds(ref)]
        if unheld:
            raise ValueError('record_not_held:' + ','.join(unheld))
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    tool, given = selection['tool'], selection['arguments']
    # A tool is handed no summary: the original assignment and the passed records ride in its arguments.
    assignment = assignment_of(summary)
    if tool == 'service_operation':
        return ToolCall('service_operation', {
            'operation': given['operation'], 'arguments': given['arguments'], 'assignment': assignment,
            'resource_id': summary['resource_id'], 'scope': summary['scope'], 'input_refs': summary['input_refs'],
            'immutable_input_versions': summary['immutable_input_versions']})
    if tool == 'capabilities':
        return ToolCall('capabilities', {'resource_id': summary['resource_id']})
    if tool == 'wait':
        return ToolCall('wait', {'resource_id': summary['resource_id'], 'assignment': assignment,
                                 'condition': given['condition'], 'handoff_refs': summary['handoff_refs']})
    return ToolCall(tool, given)


# -- the tools --------------------------------------------------------------------------------------------------------

def write_handoff_record(store, reply, operation_key):
    """The handoff record of the job: a row of a declared job ledger work table, written through ``store``.

    Wanted call: ``store.table(JOB_LEDGER).put({'job': ..., 'event': 'handoff', 'at': ..., 'detail': ...,
    'source_ref': ...})`` and, for the retained response, the receipts of
    ``records/service_calls/gene_context_evidence/api_job_receipts.py`` (``ApiJobReceipts``, still taking the old
    ``bound``). Neither the job record kind nor a custody-aware receipts library exists yet.
    """
    raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: job record kind (the handoff row of a declared job ledger '
                              'work table)')


def failed(operation, store, error):
    """A returned failure of one operation: it enters the iterator like any other outcome and earns what it earns."""
    return {**failure_outcome(store, error, category='service_operation', cause_code='api_operation_raised'),
            'operation': operation, 'event': None, 'credit': None, 'completed': False, 'handoff_refs': [],
            'result_refs': [], 'facts': {}}


def service_operation(arguments, ctx):
    """One operation of the API service, through the ``job_access`` service, idempotent on the operation key."""
    execute = required_member(ctx.services['job_access'], 'api_execute')
    held = {ref: ctx.store.get(ref) for ref in dict.fromkeys([*arguments['input_refs'],
                                                              *_named_refs(arguments['arguments'])])}
    try:
        reply = execute(resource_id=arguments['resource_id'], assignment=arguments['assignment'],
                        operation=arguments['operation'], arguments=arguments['arguments'],
                        scope=arguments['scope'], held_inputs=held,
                        immutable_input_versions=arguments['immutable_input_versions'],
                        handoff_unit=ctx.settings['handoff_unit'],
                        acquired_record_unit=ctx.settings['acquired_record_unit'], key=ctx.operation_key)
    except NotImplementedError:
        raise
    except Exception as error:      # noqa: BLE001 - an operation that raised is a failed outcome that still earns
        return failed(arguments['operation'], ctx.store, error)
    event = reply['event']
    handoff_refs = write_handoff_record(ctx.store, reply, ctx.operation_key) \
        if event is not None and (event['handoff_ready'] or event['native_handle'] is not None) else []
    result_refs = [ctx.store.artifact(item['content'], item['media_type']) for item in reply['artifacts']]
    return {'operation': arguments['operation'], 'status': reply['status'], 'event': event,
            'feedback': reply['feedback'], 'credit': reply['credit'],
            'completed': reply['facts']['execution_completed'], 'handoff_refs': handoff_refs,
            'result_refs': result_refs, 'facts': reply['facts']}


def capabilities(arguments, ctx):
    """The old ``execution.capabilities`` operation: the resource configuration and recorded inventory."""
    entries = required_member(ctx.services['job_access'], 'api_capabilities')(arguments['resource_id'])
    return {'operation': 'execution.capabilities', 'status': 'completed', 'event': None, 'feedback': None,
            'credit': None, 'completed': False,
            'capabilities': resource_information(ctx.settings, arguments['resource_id'], entries)}


async def wait(arguments, ctx):
    """Wait on the service job (old ``waiting.py`` and the ``wait`` action), through the ``job_access`` service."""
    wait_for_job = required_member(ctx.services['job_access'], 'wait_for_job')
    reply = await wait_for_job(resource_id=arguments['resource_id'], assignment=arguments['assignment'],
                               condition=arguments['condition'], handoff_refs=arguments['handoff_refs'],
                               key=ctx.operation_key)
    return {'operation': 'wait', 'status': reply['status'], 'event': reply['event'], 'feedback': None,
            'credit': None, 'completed': False}


def launch_instructions(arguments, ctx):
    """A lookup in the run-frozen launch instruction library (old ``launch.instructions.*`` operations)."""
    result = LaunchInstructions(ctx.settings['launch_instructions_directory']).execute(arguments['operation'],
                                                                                       arguments['arguments'])
    return {'operation': arguments['operation'], 'status': 'completed', 'event': None, 'feedback': None,
            'credit': None, 'completed': False, 'result': result}


def tool_knowledge(arguments, ctx):
    """A lookup in the run-frozen tool knowledge library (old ``knowledge.*`` operations)."""
    result = ToolKnowledge(ctx.settings['tool_knowledge_directory']).execute(arguments['operation'],
                                                                             arguments['arguments'])
    return {'operation': arguments['operation'], 'status': 'completed', 'event': None, 'feedback': None,
            'credit': None, 'completed': False, 'result': result}


TOOLS = {'service_operation': service_operation, 'capabilities': capabilities, 'wait': wait,
         'launch_instructions': launch_instructions, 'tool_knowledge': tool_knowledge}
