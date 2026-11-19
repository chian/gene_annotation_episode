"""The task: investigate the supplied source-bound passages for the assigned question.

The episode has no children and no acquisition tools. Its tools are the access operations of the A103 tool
registry held to the assigned source, a first lookup of the tool catalog, and a ``report`` tool that carries the
model's controlled report (two fixed-vocabulary choices and the exact passages; no model text leaves the Episode).
The task always offers a unit and never ends the Episode: its yield controller does."""
from copy import deepcopy
import json
from urllib.parse import urlsplit

from episode_runtime import ModelRequest, Rejected, ToolCall
from method_loop import FormError

from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.gene_context_evidence import (
    literature_investigation_prompt)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import (
    ContractError, identity, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.received_records import reference_in_scope
from gene_annotation_episode.episodic_workflow.episode_support.tools.gene_context_evidence.tools import ToolRegistry

from .messages.final_to_parent import REPORT_FORM

CHILD_SLOTS = {}
SERVICES = ()

# The model's tool names carry no dots; each names one operation of the A103 tool registry.
ACCESS = {
    'state_query': 'state.query', 'source_read': 'source.read', 'source_locate': 'source.locate',
    'source_sequence_scan': 'source.sequence.scan', 'source_sequence_references': 'source.sequence.references',
    'source_experimental_records': 'source.experimental.records', 'image_view': 'image.view',
    'source_archive_members': 'source.archive.members', 'source_archive_extract': 'source.archive.extract',
    'source_xlsx_sheets': 'source.xlsx.sheets', 'source_xlsx_rows': 'source.xlsx.rows',
    'source_pdf_info': 'source.pdf.info', 'source_pdf_text': 'source.pdf.text', 'source_pdf_page': 'source.pdf.page',
    'execution_estimate': 'execution.estimate',
}
# Received record refs authorize these reads (the episode's held records).
AUTHORIZED = {'source.locate', 'source.sequence.scan', 'source.sequence.references', 'source.experimental.records'}
XLSX_ESTIMATES = {'source.xlsx.sheets', 'source.xlsx.rows'}

GOAL_INSTRUCTION = (
    'For A103, identify the actual locus and genome before using a source claim. Keep neighboring-gene identity, '
    'order, orientation, spacing, fusion, cooccurrence, and alternative explanations tied to their source and scope.'
    '\n\nInvestigate the supplied source-bound passages for the assigned question. Read neighboring context, '
    'qualifications or alternative passages as needed and revise the interpretation from actual outcomes. Separate '
    'spans remain separate; never concatenate them into a fabricated quotation.')
TOOL_INSTRUCTION = (
    'Select one operation per answer: give its name in tool and its operands as JSON text in arguments_json. '
    'Every operation that names a source must name the assigned source or a source derived from it. Reading is the '
    'work: record what the passages report by selecting the report tool with its controlled values: '
    'target_correspondence (established, unresolved or not_applicable), evidence_type (the kind of gene-context '
    'evidence the passages report, or none_applicable) and the separate passages (source_ref, representation, '
    'offset, limit). No text of yours is returned to your parent. '
    'Selecting report does not end the investigation; report again when new outcomes change it. Do not '
    'execute native provider tools. The host executes your selected action.')


def instructions():
    """The A103 literature investigation text without the actions this leaf does not have (reasoning commits,
    children, the report update, redelivery, the exchange), then this episode's own role text."""
    text = literature_investigation_prompt.INSTRUCTIONS
    text = replace_span(text, 'Select one ordinary tool, one typed reasoning commitment',
                        'Reasoning owns scientific interpretation', 'Select one ordinary tool at a time. ')
    text = replace_span(text, 'When annotation_score is supplied', 'Do not execute native provider tools.', '')
    return text + '\n\n' + GOAL_INSTRUCTION + '\n\n' + TOOL_INSTRUCTION


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
    """Whether ``reference`` is ``root`` or a source derived from it through ``parent_source_refs``."""
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


def _tool_arguments(store, entries, tool_name, arguments, scope, page_source):
    """The operands of one access operation, held to the assigned source (the old ``_tool_arguments``)."""
    if tool_name not in entries:
        raise ContractError('tool_not_available_to_a103_literature_role')
    validate_schema(arguments, entries[tool_name]['input_schema'])
    selected = arguments['arguments'] if tool_name == 'execution.estimate' else arguments
    source_ref = selected.get('source_ref')
    if tool_name == 'source.archive.extract':
        member = store.get(arguments['member_ref'])
        source_ref = member['source_ref']
    if source_ref is not None and not _within_source(store, source_ref, page_source, scope):
        raise ContractError('literature_reading_outside_assigned_source')
    return arguments


async def _access(tool_name, arguments, ctx):
    scope, page_source, selected = arguments['scope'], arguments['source_ref'], arguments['arguments']
    registry = ToolRegistry(ctx.store)
    entries = {entry['name']: entry for entry in _catalog(registry.catalog(scope))}
    try:
        selected = _tool_arguments(ctx.store, entries, tool_name, selected, scope, page_source)
    except ContractError as error:
        return {'status': 'invalid',
                'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': tool_name,
                                                        'arguments': selected}),
                'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': str(error),
                             **({'detail': error.detail} if error.detail else {})}}
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


def report(arguments, ctx):
    """The model's controlled report as the outcome of a unit (the two choices and the exact passages); the summary
    holds the latest and code reads the finding from it. A report that is not of the declared form, or that names a
    source this episode does not hold, is an invalid outcome."""
    try:
        value = REPORT_FORM.admit(arguments['report'], 'report')
    except FormError as error:
        return {'status': 'invalid', 'feedback': {'category': 'report_format', 'detail': str(error)}}
    unheld = [passage['source_ref'] for passage in value['passages'] if not ctx.store.holds(passage['source_ref'])]
    if unheld:
        return {'status': 'invalid', 'feedback': {'category': 'arguments_or_reference',
                                                  'detail': 'passage sources not held: ' + ', '.join(unheld)}}
    return {'status': 'reported', 'report': value}


TOOLS = {'tool_catalog': tool_catalog, 'state_query': state_query, 'source_read': source_read,
         'source_locate': source_locate, 'source_sequence_scan': source_sequence_scan,
         'source_sequence_references': source_sequence_references,
         'source_experimental_records': source_experimental_records, 'image_view': image_view,
         'source_archive_members': source_archive_members, 'source_archive_extract': source_archive_extract,
         'source_xlsx_sheets': source_xlsx_sheets, 'source_xlsx_rows': source_xlsx_rows,
         'source_pdf_info': source_pdf_info, 'source_pdf_text': source_pdf_text, 'source_pdf_page': source_pdf_page,
         'execution_estimate': execution_estimate, 'report': report}


def _offered(summary):
    """The model's tool names: the catalog's operations (dots out) and ``report``."""
    named = {operation: name for name, operation in ACCESS.items()}
    return [named[entry['name']] for entry in summary['catalog']] + ['report']


def _output_schema(offered):
    return {'type': 'object', 'additionalProperties': False, 'required': ['tool', 'arguments_json'],
            'properties': {'tool': {'enum': offered},
                           'arguments_json': {'type': 'string', 'description': 'The operands as one JSON object'}}}


# Presentation of the task as text (the old receiver task prompt, over this episode's own summary).
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
                         'accession': source.get('accession'), 'version': source.get('version'),
                         'uri': web_uri})
    return rows


def _task(summary, text):
    assignment = summary['assignment']
    parts = ['TASK', '', text]
    _section(parts, 'Assigned work', {'goal': GOAL_INSTRUCTION.split('\n\n')[1], 'page': assignment['page'],
                                      'spans': assignment['selection']['spans']})
    _section(parts, 'Fixed scope', assignment['scope'])
    context = assignment.get('gene_context_evidence', {}).get('assignment', {})
    _section(parts, 'Parent constraints', context.get('constraints'))
    _section(parts, 'Parent-supplied context', context.get('context'))
    _section(parts, 'Parent-selected evidence operands', context.get('evidence_refs'))
    _section(parts, 'Callable supplied Sources', _source_operands(summary['source_custody']))
    named = {operation: name for name, operation in ACCESS.items()}
    _section(parts, 'Callable operations', [{'tool': named[entry['name']], 'operation': entry['name'],
                                             'meaning': entry.get('description', ''),
                                             'operands': entry['input_schema']} for entry in summary['catalog']])
    _section(parts, 'Current gene-context scoring sheet', summary['completed_work_axis_results'])
    _section(parts, 'Return', 'Report with the report tool: ' + json.dumps(REPORT_FORM.as_record(), sort_keys=True))
    return '\n'.join(parts)


def decide(summary, feedback, ctx):
    """The tool catalog first (a lookup, one unit); then the model chooses one operation or the report."""
    if summary['catalog'] is None:
        return ToolCall('tool_catalog', {'scope': summary['assignment']['scope']})
    offered = _offered(summary)
    context = {'task': _task(summary, instructions()), 'feedback': feedback,
               'own_outcomes': summary['own_outcomes'], 'current_report': summary['report'],
               'completed_work_axis_results': summary['completed_work_axis_results'],
               'source_custody': summary['source_custody'], 'history_meaning': summary['history_meaning'],
               'controller': summary['controller'], 'time_accounting': time_accounting(ctx.clock.progress_time)}
    return ModelRequest('REASONING', instructions(), context, _output_schema(offered))


def action(response, summary, records, ctx):
    """One selected operation, or a rejection: the answer names an offered tool and closed JSON operands."""
    try:
        name = response['tool']
        if name not in _offered(summary):
            raise ValueError('tool_not_offered:' + repr(name))
        arguments = json.loads(response['arguments_json'])
        if not isinstance(arguments, dict):
            raise ValueError('arguments_json_must_be_a_JSON_object')
    except (KeyError, TypeError, ValueError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    if name == 'report':
        return ToolCall('report', {'report': arguments})
    return ToolCall(name, {'arguments': arguments, 'scope': summary['assignment']['scope'],
                           'source_ref': summary['assignment']['page']['source_ref']})
