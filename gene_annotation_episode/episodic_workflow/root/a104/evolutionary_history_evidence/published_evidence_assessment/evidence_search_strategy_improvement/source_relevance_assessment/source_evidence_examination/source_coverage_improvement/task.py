"""The task: investigate the source in document order, from the assigned starting window, for the assigned question.

The episode has no children and no acquisition tools. Its tools are the access operations of the A104 tool registry
held to the assigned source, a first lookup of the tool catalog, the common reasoning commit (``reason``) and a
no prose report tool: the return is read by code from the assessments it commits. The task always offers a unit
and never ends the Episode: its
yield controller does.

Carried from the old ``task.py``, ``task_decision.py``, ``task_action.py``, ``task_instructions.py``,
``task_presentation.py``, ``source_catalog.py``, ``source_admission.py``, ``source_custody.py``,
``source_operations.py`` and ``scientific_interpretation.py``. The old ``rate_population`` routes (population tools,
text-witness materialization, population admission) exist only under a configuration that is off by default and are
not built here."""
from copy import deepcopy
import json
from urllib.parse import urlsplit

from episode_runtime import CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.evolutionary_history_evidence import (
    runtime_prompt)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_task_credit import (
    lead_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import (
    ContractError, identity, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.received_records import (
    read_record_in_scope, reference_in_scope)
from gene_annotation_episode.episodic_workflow.episode_support.tools.evolutionary_history_evidence.tools import (
    ToolRegistry)


CHILD_SLOTS = {}
SERVICES = ()

# The model's tool names carry no dots; each names one operation of the A104 tool registry (the old
# ``_ACCESS_TOOLS``: this role gets no acquisition tools).
ACCESS = {
    'state_query': 'state.query', 'source_read': 'source.read', 'source_locate': 'source.locate',
    'source_sequence_scan': 'source.sequence.scan', 'source_sequence_references': 'source.sequence.references',
    'source_experimental_records': 'source.experimental.records', 'image_view': 'image.view',
    'source_archive_members': 'source.archive.members', 'source_archive_extract': 'source.archive.extract',
    'source_xlsx_sheets': 'source.xlsx.sheets', 'source_xlsx_rows': 'source.xlsx.rows',
    'source_pdf_info': 'source.pdf.info', 'source_pdf_text': 'source.pdf.text', 'source_pdf_page': 'source.pdf.page',
    'execution_estimate': 'execution.estimate',
}
# The passed records authorize these reads (the old ``context.received_record_refs``).
AUTHORIZED = {'source.locate', 'source.sequence.scan', 'source.sequence.references', 'source.experimental.records'}
XLSX_ESTIMATES = {'source.xlsx.sheets', 'source.xlsx.rows'}

GOAL_INSTRUCTION = (
    'Investigate the source in document order as useful for the assigned question. Use returned UTF-8 byte '
    'continuations and retain representation identity. Decide whether to continue, reread, change the examined '
    'window or interpret obtained evidence from actual outcomes.\n'
    'This is an iterative scientific investigation in the shared Episode loop. Earlier outcomes inform later '
    'choices; no reading quota or complete-document requirement is prescribed. A one-off search/read is an '
    "ordinary tool. A supplied reading selector is context, not an automatically executed action. Preserve the "
    "source's actual subject, experimental conditions, representation, version and UTF-8 byte anchors. "
    'Distinguish source claims from their applicability to the fixed target. Negative findings and qualifications '
    'can advance the investigation. Commit interpretations with the common reasoning action. Navigation, byte '
    "coverage and repeated reading earn no scientific credit by themselves. The commissioned task's own yield "
    'settings guide continuation.')
TOOL_INSTRUCTION = (
    'Select one operation per answer: give its name in tool and its operands as JSON text in arguments_json. '
    'Every operation that names a source must name the assigned source or a source derived from it. The reason '
    'operation commits an interpretation: its operands are {"commit": <the reasoning commit>} and, for a '
    'verified_source_leads task, {"source_lead": <the lead>} beside it. What returns to your parent is your credit '
    'and the features code reads from the assessments you commit (relation, applicability, the fixed kind of the '
    'finding\'s qualification, its status and counts), never prose of yours. Do not execute native provider '
    'tools. The host executes your selected action.')


def instructions():
    """The A104 investigation text without the actions this leaf does not have (children, annotation scores,
    resource estimates, the report update, redelivery, history reading), then the commit requirement and this
    episode's own role text (the old ``instructions(source, context)`` composer)."""
    text = runtime_prompt.INSTRUCTIONS
    text = replace_span(text, 'Select one ordinary tool, one typed reasoning commitment',
                        'Reasoning owns scientific interpretation',
                        'Select one ordinary tool or one typed reasoning commitment based on available existing '
                        'evidence. There are no biological departments or compulsory stages.\n')
    text = replace_span(text, 'When annotation_score is supplied', 'Define local rows',
                        "The recorded task credit supplies this episode's numerical yield observations.\n")
    text = replace_span(text, "A commissioned child returns ONLY", 'Do not execute native provider tools.', '')
    return (text + '\n' + GOAL_INSTRUCTION + '\n' + runtime_prompt.REASONING_COMMIT_REQUIREMENT + '\n\n'
            + TOOL_INSTRUCTION)


def _catalog(available):
    """The access operations of the registry catalog this episode offers (the old ``catalog``)."""
    entries = [{'name': name, **entry} for name, entry in available.items()]
    result = []
    for entry in entries:
        if entry['name'] not in ACCESS.values():
            continue
        entry = deepcopy(entry)
        if entry['name'] == 'execution.estimate':
            branches = [branch for branch in entry['input_schema'].get('anyOf', ())
                        if branch.get('properties', {}).get('tool', {}).get('const') in XLSX_ESTIMATES]
            if not branches:
                continue
            entry['input_schema'] = {'anyOf': branches}
        result.append(entry)
    return json.loads(json.dumps([{**entry, 'input_schema': source_location_inputs(entry['input_schema'])}
                                  for entry in result]))


def _within_source(store, reference, root, scope):
    """The old ``_within_source``: whether ``reference`` is ``root`` or a source derived from it through
    ``parent_source_refs``."""
    pending, seen = [reference], set()
    while pending:
        current = pending.pop()
        if current == root:
            return True
        if current in seen:
            continue
        seen.add(current)
        if not reference_in_scope(store, current, scope, 'source'):
            raise ContractError('literature_reference_unavailable', detail={'reference': current, 'namespace': 'source'})
        pending.extend(store.get(current).get('parent_source_refs', ()))
    return False


def _admit(store, entries, tool_name, arguments, scope, page_source):
    """The operands of one access operation, held to the assigned source (the old ``_tool_arguments``)."""
    if tool_name not in entries:
        raise ContractError('tool_not_available_to_literature_role')
    validate_schema(arguments, entries[tool_name]['input_schema'])
    selected = arguments['arguments'] if tool_name == 'execution.estimate' else arguments
    source_ref = selected.get('source_ref')
    if tool_name == 'source.archive.extract':
        source_ref = read_record_in_scope(store, arguments['member_ref'], scope, 'archive_member')['source_ref']
    if source_ref is not None and not _within_source(store, source_ref, page_source, scope):
        raise ContractError('literature_reading_outside_assigned_source')
    return arguments


def _invalid(ctx, name, arguments, error):
    """A returned invalid outcome: the unit entered the iterator with its own identity (the old ``execute``)."""
    return {'status': 'invalid',
            'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': name, 'arguments': arguments}),
            'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'category': 'arguments_or_reference', 'code': str(error),
                         **({'detail': error.detail} if getattr(error, 'detail', None) else {})}}


async def _access(tool_name, arguments, ctx):
    scope, page_source, selected = arguments['scope'], arguments['source_ref'], arguments['arguments']
    registry = ToolRegistry(ctx.store)
    entries = {entry['name']: entry for entry in _catalog(registry.catalog(scope))}
    try:
        selected = _admit(ctx.store, entries, tool_name, selected, scope, page_source)
    except ContractError as error:
        return _invalid(ctx, tool_name, selected, error)
    authorization = {'permitted_record_refs': tuple(ctx.store.refs())} if tool_name in AUTHORIZED else {}
    return await registry.execute_async(tool_name, selected, scope=scope, operation_key=ctx.operation_key,
                                        **authorization)


def tool_catalog(arguments, ctx):
    """The first lookup: the access operations the registry offers for the scope."""
    return {'catalog': _catalog(ToolRegistry(ctx.store).catalog(arguments['scope']))}


async def state_query(arguments, ctx):
    return await _access('state.query', arguments, ctx)


async def source_read(arguments, ctx):
    return await _access('source.read', arguments, ctx)


async def source_locate(arguments, ctx):
    return await _access('source.locate', arguments, ctx)


async def source_sequence_scan(arguments, ctx):
    return await _access('source.sequence.scan', arguments, ctx)


async def source_sequence_references(arguments, ctx):
    return await _access('source.sequence.references', arguments, ctx)


async def source_experimental_records(arguments, ctx):
    return await _access('source.experimental.records', arguments, ctx)


async def image_view(arguments, ctx):
    return await _access('image.view', arguments, ctx)


async def source_archive_members(arguments, ctx):
    return await _access('source.archive.members', arguments, ctx)


async def source_archive_extract(arguments, ctx):
    return await _access('source.archive.extract', arguments, ctx)


async def source_xlsx_sheets(arguments, ctx):
    return await _access('source.xlsx.sheets', arguments, ctx)


async def source_xlsx_rows(arguments, ctx):
    return await _access('source.xlsx.rows', arguments, ctx)


async def source_pdf_info(arguments, ctx):
    return await _access('source.pdf.info', arguments, ctx)


async def source_pdf_text(arguments, ctx):
    return await _access('source.pdf.text', arguments, ctx)


async def source_pdf_page(arguments, ctx):
    return await _access('source.pdf.page', arguments, ctx)


async def execution_estimate(arguments, ctx):
    return await _access('execution.estimate', arguments, ctx)


def _validated_lead(store, arguments, lead, outcome):
    """The old ``validate_lead(store, context, lead, outcome)``: the lead's identity and exact source witness.

    The library function (``literature/grading/literature_task_credit.py``) still takes the old binding context
    (``assignment``, ``request``, ``role``, ``received_record_refs``) and reads ``store._require``, so it cannot be
    called in the final form. The intended call is
    ``validate_lead(store, task, proposed, store.refs(), lead, outcome)`` over the custody-scoped store."""
    raise NotImplementedError('library_not_carried:literature_task_credit.validate_lead')


def reason(arguments, ctx):
    """The common reasoning commit (the old ``execute_reasoning`` without a grading repository): the commit goes to
    ``Store.commit_reasoning`` through custody; a ``verified_source_leads`` task's ``source_lead`` is validated in
    the same transaction and enters the outcome. A commit that names a record the Episode does not hold, or a lead
    outside the assigned source, is a returned invalid outcome."""
    scope, page_source, lead = arguments['scope'], arguments['source_ref'], arguments.get('source_lead')
    try:
        with ctx.store.transaction():
            if lead is not None:
                witness = lead['witness']
                entries = {entry['name']: entry for entry in _catalog(ToolRegistry(ctx.store).catalog(scope))}
                _admit(ctx.store, entries, 'source.read',
                       {'source_ref': witness['source_ref'], 'representation': witness['representation'],
                        'offset': witness['start'], 'limit': witness['end'] - witness['start']}, scope, page_source)
            result = ctx.store.commit_reasoning(arguments['commit'], scope, ctx.operation_key)
            if result['status'] not in ('completed', 'partial') or lead is None:
                return result
            return {**result, 'literature_source_lead': _validated_lead(ctx.store, arguments, lead, result)}
    except ContractError as error:
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'source_lead' if lead is not None else 'arguments_or_reference',
                             'code': getattr(error, 'code', str(error))}}
    except CustodyError as error:
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': 'record_not_held', 'detail': str(error)}}




TOOLS = {'tool_catalog': tool_catalog, 'state_query': state_query, 'source_read': source_read,
         'source_locate': source_locate, 'source_sequence_scan': source_sequence_scan,
         'source_sequence_references': source_sequence_references,
         'source_experimental_records': source_experimental_records, 'image_view': image_view,
         'source_archive_members': source_archive_members, 'source_archive_extract': source_archive_extract,
         'source_xlsx_sheets': source_xlsx_sheets, 'source_xlsx_rows': source_xlsx_rows,
         'source_pdf_info': source_pdf_info, 'source_pdf_text': source_pdf_text, 'source_pdf_page': source_pdf_page,
         'execution_estimate': execution_estimate, 'reason': reason}


def _offered(summary):
    """The model's tool names: the catalog's operations (dots out) and ``reason``."""
    named = {operation: name for name, operation in ACCESS.items()}
    return [named[entry['name']] for entry in summary['catalog']] + ['reason']


def _output_schema(offered):
    return {'type': 'object', 'additionalProperties': False, 'required': ['tool', 'arguments_json'],
            'properties': {'tool': {'enum': offered},
                           'arguments_json': {'type': 'string', 'description': 'The operands as one JSON object'}}}


# Presentation of the task as text (the old published-scientific task prompt, over this episode's own summary).
def _section(parts, title, body):
    if body not in (None, '', [], {}):
        parts.extend(['', title, '', body if isinstance(body, str) else json.dumps(body, indent=1, sort_keys=True)])


def _source_operands(custody):
    """Callable source metadata only: sources with an id, a provider and, when plain http(s), a resource URI."""
    rows = []
    for source in custody:
        uri, web_uri = source.get('uri'), None
        if isinstance(uri, str) and not any(character.isspace() or ord(character) < 32 for character in uri):
            try:
                parsed = urlsplit(uri)
                parsed.port
                if parsed.scheme.lower() in {'http', 'https'} and parsed.hostname and parsed.username is None \
                        and parsed.password is None:
                    web_uri = uri
            except ValueError:
                pass
        if isinstance(source.get('provider'), str):
            rows.append({'source': source['source_ref'], 'provider': source['provider'],
                         'accession': source.get('accession'), 'version': source.get('version'), 'uri': web_uri})
    return rows


def _task(summary, text):
    assignment = summary['literature_assignment']
    parts = ['TASK', '', text]
    _section(parts, 'Assigned work', {'goal': GOAL_INSTRUCTION.split('\n')[0], 'page': assignment['page'],
                                      'starting_window': assignment['selection']})
    _section(parts, 'Fixed scope', summary['scope'])
    _section(parts, 'Commissioned task', summary['task'])
    _section(parts, 'Proposed annotation', summary['proposed_annotation_ref'])
    _section(parts, 'Credit binding', summary['credit_binding'])
    _section(parts, 'Callable supplied Sources', _source_operands(summary['literature_source_custody']))
    named = {operation: name for name, operation in ACCESS.items()}
    _section(parts, 'Callable operations', [{'tool': named[entry['name']], 'operation': entry['name'],
                                             'meaning': entry.get('description', ''),
                                             'operands': entry['input_schema']} for entry in summary['catalog']])
    _section(parts, 'Reasoning commit schema (operands of reason: {"commit": ...})', summary['reasoning_schema'])
    _section(parts, 'Return', 'Your credit and the features code reads from the assessments you commit.')
    return '\n'.join(parts)


def decide(summary, feedback, ctx):
    """The tool catalog first (a lookup, one unit); then the model chooses one operation, a reasoning commit or the
    nothing else (no report)."""
    if summary['catalog'] is None:
        return ToolCall('tool_catalog', {'scope': summary['scope']})
    offered = _offered(summary)
    context = {'task': _task(summary, instructions()), 'feedback': feedback,
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'last_local_outcome': summary['last_local_outcome'], 'visual_evidence': summary['visual_evidence'],
               'assessments': summary['assessments'], 'literature_source_custody': summary['literature_source_custody'],
               'literature_history_meaning': summary['literature_history_meaning'],
               'action_yields': summary['action_yields'], 'time_accounting': time_accounting(ctx.clock.progress_time)}
    return ModelRequest('REASONING', instructions(), context, _output_schema(offered))


def _empty_commit(commit, schema):
    """The old empty-reasoning test: every section of the commit is present-or-absent and empty."""
    required = schema.get('required', schema['properties'])
    return set(required) <= set(commit) <= set(schema['properties']) and all(value == [] for value in commit.values())


def action(response, summary, records, ctx):
    """One selected operation, or a rejection: the answer names an offered tool and closed JSON operands. A reason
    answer needs a valid commit with at least one proposed row (or, for a ``verified_source_leads`` task, a valid
    ``source_lead``)."""
    try:
        name = response['tool']
        if name not in _offered(summary):
            raise ValueError('tool_not_offered:' + repr(name))
        arguments = json.loads(response['arguments_json'])
        if not isinstance(arguments, dict):
            raise ValueError('arguments_json_must_be_a_JSON_object')
        if name == 'reason':
            if set(arguments) - {'commit', 'source_lead'} or not isinstance(arguments.get('commit'), dict):
                raise ValueError('reason_operands_are_commit_and_optionally_source_lead')
            validate_schema(arguments['commit'], summary['reasoning_schema'])
            lead = arguments.get('source_lead')
            content = False
            if lead is not None:
                if summary['task']['kind'] != 'verified_source_leads':
                    raise ValueError('source_lead_is_only_for_a_verified_source_leads_task')
                validate_schema(lead, source_location_inputs(lead_schema()))
                content = True
            if not content and _empty_commit(arguments['commit'], summary['reasoning_schema']):
                raise ValueError('empty_reasoning_commit')
    except (KeyError, TypeError, ValueError, ContractError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    scope, source_ref = summary['scope'], summary['literature_assignment']['page']['source_ref']
    if name == 'reason':
        return ToolCall('reason', {**arguments, 'scope': scope, 'source_ref': source_ref})
    return ToolCall(name, {'arguments': arguments, 'scope': scope, 'source_ref': source_ref})
