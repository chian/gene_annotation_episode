"""The task: build the request of the assigned job, submit it once through the job service, end at handoff.

Each decision the model selects one tool: ``submit`` (the request it built, sent as one submission on the assigned
resource of the ``job_access`` service) or, when the settings name the libraries, one lookup in the run-frozen
launch-instruction or tool-knowledge library. The job continues at the service after the submission has returned:
this episode does not wait for it, ask its status or fetch its results (the monitor and result-acquisition
episodes do, from the handoff record). The task offers a unit at every decision and never ends the Episode: the
yield controller does, at the handoff.

What ties the request to the assigned job is code, not the model's care: the query is the held sequence record
the parent named and the ``submit`` tool stages it (the model never writes a sequence); ``action`` rejects a
request that is not of the service's request form, that changes a parameter the parent fixed, or whose program
does not take a query of the assigned molecule. A rejection creates no unit.

Carried from the episode's own files at ``97308b94c``: one selected operation per turn, the goal text's decisions
(keep the original inputs, request, resource and parent constraints fixed; a missing reply does not establish
that no job was created; the handoff completes the commission), the request bound to the parent's query and
database (``blast_request_custody.py``), and the two library lookups. Not carried, by the launch design
(``LAUNCH_MONITOR_EXTRACT_MECHANICS.md`` section 3: a launching child submits once, returns the handoff and never
waits): the ``wait`` action, the status and result operations of the old service catalog, and the capabilities
read (what a decision needs of the resource is read from the job service into every request). The model's
free-text ``report_update`` for the parent is not carried: nothing a model writes leaves this episode.

Settings read (the episode's own entry of the run's ``continuation`` collaborator): ``task_yield_profiles`` (read
by ``yield_estimator.py``) and, optionally, ``launch_instructions_directory`` and ``tool_knowledge_directory``.
"""
import json

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    LaunchInstructions, catalog as launch_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    ToolKnowledge, catalog as knowledge_catalog)

CHILD_SLOTS = {}
SERVICES = ('job_access',)
QUERY_FILE = 'query.fasta'
# The unit a program's query is counted in, for each molecule a held sequence subject can have.
MOLECULE_UNITS = {'protein': 'aa', 'dna': 'nt', 'rna': 'nt'}
# The lookups: the setting that names the library, the library, its operations offered here (reading only; a
# selection of sections is for an episode that commissions a child) and what the lookup is for.
LOOKUPS = {
    'launch_instructions': ('launch_instructions_directory', LaunchInstructions, launch_catalog,
                            ('launch.instructions.search', 'launch.instructions.entry', 'launch.instructions.read'),
                            'Read the run-frozen launch instruction library: notes on how a service or resource '
                            'is used.'),
    'tool_knowledge': ('tool_knowledge_directory', ToolKnowledge, knowledge_catalog,
                       ('knowledge.search', 'knowledge.entry', 'knowledge.read'),
                       'Read the run-frozen tool knowledge library: notes on tools and their parameters.')}

PURPOSE = (
    'You are the launch step of one job on the public web service {service}. Build the request of the assigned '
    'job, submit it once through the job service, and end at handoff. The handoff is the recorded identity of '
    'the accepted submission; other episodes monitor the job and fetch its results from that record. Do not wait '
    'for the job, ask its status or fetch anything here.')
ASSIGNED_JOB = (
    'Assigned job. It is assigned_job in the context. Its query is the held sequence record named there: the '
    'submit tool attaches it, you never write a sequence. Keep the original inputs, request, resource and parent '
    'constraints fixed: every parameter under assigned_job.fixed is the parent\'s decision and is copied exactly. '
    'You choose the parameters listed in assigned_job.open, within service.request_form.')
TOOL_TEXT = (
    'Tools. Each answer selects one tool; tools in the context says what each does. For submit give request with '
    'every parameter of service.request_form{null_lookup}.')
LOOKUP_TOOLS = (
    ' For a lookup give lookup (one operation of that library and its arguments as JSON text) and request null. '
    'A lookup is optional and earns nothing; use one only when the request cannot be built without it.')
OUTCOMES = (
    'Outcomes. progress in the context lists the submissions made so far. An accepted submission is the handoff. '
    'A failed submission says whether the request was sent: sent false means it was not sent and no job exists '
    '(retry_after_seconds, when given, is how long the service asks to be left alone); sent unknown means the '
    'reply was lost: a missing reply does not establish that no job was created, and another submission may '
    'create a second job; sent true means the service answered and refused the request.')
CREDIT = (
    'Credit. The established handoff earns {target} and completes the commission; after it further credit is '
    'exactly zero. A lookup or a failed submission earns nothing. The episode\'s controller ends the episode, at '
    'the handoff or when further units are not expected to earn.')


def offered_lookups(settings):
    return [name for name, (setting, *_rest) in LOOKUPS.items() if setting in settings]


def request_form(description):
    """The service's request form as the model is asked for it: each parameter with its type, its allowed values
    and its meaning. ``action`` validates the answer against the service's whole schema."""
    schema = description['request_schema']
    return {'type': 'object', 'additionalProperties': False, 'required': list(schema['properties']),
            'properties': {name: {key: value for key, value in parameter.items()
                                  if key in ('type', 'enum', 'description')}
                           for name, parameter in schema['properties'].items()}}


def lookup_form(names):
    operations = [operation for name in names for operation in LOOKUPS[name][3]]
    return {'type': 'object', 'additionalProperties': False, 'required': ['operation', 'arguments_json'],
            'properties': {'operation': {'type': 'string', 'enum': operations},
                           'arguments_json': {'type': 'string',
                                              'description': 'The arguments of the operation, as JSON text'}}}


def output_schema(description, settings):
    lookups = offered_lookups(settings)
    properties = {'action': {'type': 'string', 'enum': ['submit', *lookups]},
                  'request': {'anyOf': [request_form(description), {'type': 'null'}]}}
    if lookups:
        properties['lookup'] = {'anyOf': [lookup_form(lookups), {'type': 'null'}]}
    return {'type': 'object', 'additionalProperties': False, 'required': list(properties), 'properties': properties}


def instructions(summary, settings):
    lookups = offered_lookups(settings)
    tools = TOOL_TEXT.format(null_lookup=' and lookup null' if lookups else '') + (LOOKUP_TOOLS if lookups else '')
    return '\n\n'.join((PURPOSE.format(service=summary['service']), ASSIGNED_JOB, tools, OUTCOMES,
                        CREDIT.format(target=summary['completion_target'])))


def arguments_shown(schema):
    """An operation's arguments in one line each: the type, and ``optional`` for one that may be left out."""
    return {name: ' or '.join(map(str, [parameter['type']] if type(parameter['type']) is str else parameter['type']))
            + ('' if name in schema['required'] else ', optional')
            for name, parameter in schema['properties'].items()}


def tools_shown(settings):
    shown = [{'name': 'submit',
              'does': 'Sends the request you give, with the assigned query attached, to the service as one '
                      'submission. When the service accepts it, the handoff record is written and the commission '
                      'is complete. A failure is returned as the outcome of the submission.',
              'give': 'request'}]
    for name in offered_lookups(settings):
        _setting, _library, catalog, operations, does = LOOKUPS[name]
        shown.append({'name': name, 'does': does, 'give': 'lookup',
                      'operations': {entry['name']: arguments_shown(entry['input_schema'])
                                     for entry in catalog() if entry['name'] in operations}})
    return shown


def assigned_job(summary, description):
    """The job as the decision needs it: where it runs, the query, what the parent fixed and what is open. A
    fixed parameter that is not of the service's request form raises: the commission is wrong."""
    parameters = description['request_schema']['properties']
    units = description['query_unit_by_program']
    unit = MOLECULE_UNITS[summary['query']['molecule']]
    return {'service': summary['service'], 'resource_id': summary['resource_id'],
            'query': {'record': summary['query']['subject_ref'], 'molecule': summary['query']['molecule'],
                      'length': summary['query']['length'],
                      'programs_that_take_it': [name for name in sorted(units) if units[name] == unit]},
            'fixed': {name: {'value': value, 'parameter': parameters[name]['description']}
                      for name, value in summary['fixed_request'].items()},
            'open': [name for name in parameters if name not in summary['fixed_request']]}


def decide(summary, feedback, ctx):
    description = ctx.services['job_access'].read('describe', summary['resource_id'])
    context = {'assigned_job': assigned_job(summary, description),
               'service': {'name': description['service'], 'protocol': description['protocol'],
                           'request_form': request_form(description),
                           'seconds_between_contacts': description['request_spacing_seconds']},
               'tools': tools_shown(ctx.settings),
               'progress': {'handoff_established': bool(summary['handoff_refs']),
                            'submissions': summary['submissions'], 'lookups': summary['lookups']},
               'credit': {'now': summary['credit'], 'the_handoff_earns': summary['completion_target']},
               'feedback': feedback}
    if summary['launch_instructions'] is not None:
        context['launch_instructions_selected_by_the_parent'] = LaunchInstructions(
            ctx.settings['launch_instructions_directory']).materialize(summary['launch_instructions'])
    return ModelRequest('REASONING', instructions(summary, ctx.settings), context,
                        output_schema(description, ctx.settings))


def action(response, summary, records, ctx):
    """The one unit the answer selects, or a rejection. A submission is admitted only as the request of the
    assigned job; ``submit`` is always acceptable with such a request, so a unit is always offered."""
    description = ctx.services['job_access'].read('describe', summary['resource_id'])
    try:
        Draft202012Validator(output_schema(description, ctx.settings)).validate(response)
        if response['action'] == 'submit':
            request = response['request']
            Draft202012Validator(description['request_schema']).validate(request)
            for name, value in summary['fixed_request'].items():
                if request[name] != value:
                    raise ValueError('request_changes_a_parameter_the_parent_fixed:' + name + ':assigned:'
                                     + json.dumps(value) + ':given:' + json.dumps(request[name]))
            unit = MOLECULE_UNITS[summary['query']['molecule']]
            if description['query_unit_by_program'][request['program']] != unit:
                raise ValueError('program_does_not_take_the_assigned_query:' + request['program'] + ':query_is:'
                                 + summary['query']['molecule'])
            return ToolCall('submit', {'resource_id': summary['resource_id'], 'request': request,
                                       'query_sequence_ref': summary['query']['sequence_ref']})
        lookup = response['lookup']
        if lookup is None:
            raise ValueError('a_lookup_requires_the_lookup_member:' + response['action'])
        if lookup['operation'] not in LOOKUPS[response['action']][3]:
            raise ValueError('operation_is_not_of_the_selected_library:' + lookup['operation'])
        return ToolCall(response['action'], {'operation': lookup['operation'],
                                             'arguments': json.loads(lookup['arguments_json'])})
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='selection'))


def submit(arguments, ctx):
    """One submission of the built request on the assigned resource, through the ``job_access`` service: the
    query is staged from the held sequence record, the job's handle comes from this unit's operation key (a unit
    that runs again does not submit again) and the handoff row is written through ``ctx.store`` with the
    service's reply as an artifact. A request that failed is the returned outcome, with whether it was sent."""
    launched = ctx.services['job_access'].launch(
        ctx, arguments['resource_id'], {**arguments['request'], 'query_file': QUERY_FILE},
        inputs={QUERY_FILE: arguments['query_sequence_ref']})
    if launched['status'] != 'completed':
        failure = launched['failure']
        return {'status': 'failed', 'job': launched['job'], 'handoff_refs': [], 'failure_code': failure['code'],
                'sent': failure['detail']['sent'],
                'retry_after_seconds': failure['detail'].get('retry_after_seconds'), 'failure': failure}
    return {'status': 'completed', 'job': launched['job'], 'handoff_refs': [launched['handoff_ref']],
            'failure_code': None, 'sent': True, 'retry_after_seconds': None, 'failure': None,
            'submitted_at': launched['submitted_at'], 'reply_ref': launched['reply_ref'],
            'adopted': launched['adopted'], 'replayed': launched['replayed']}


def _lookup(name, arguments, ctx):
    setting, library, _catalog, _operations, _does = LOOKUPS[name]
    found = library(ctx.settings[setting]).execute(arguments['operation'], arguments['arguments'])
    return {'status': found['status'], 'result': found['result'], 'feedback': found['feedback']}


def launch_instructions(arguments, ctx):
    """One reading operation of the run-frozen launch instruction library."""
    return _lookup('launch_instructions', arguments, ctx)


def tool_knowledge(arguments, ctx):
    """One reading operation of the run-frozen tool knowledge library."""
    return _lookup('tool_knowledge', arguments, ctx)


TOOLS = {'submit': submit, 'launch_instructions': launch_instructions, 'tool_knowledge': tool_knowledge}
