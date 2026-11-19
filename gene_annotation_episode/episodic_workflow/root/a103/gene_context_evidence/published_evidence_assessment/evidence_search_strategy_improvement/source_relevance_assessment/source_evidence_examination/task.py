"""The task: examine the assigned source through the access tools or commission one of three child
investigations of it (a selected table or sheet, an ordered reading, targeted passages), and write the finding
with the ``report`` tool as controlled values (two fixed-vocabulary choices and the exact readings; no model text
leaves the Episode).

Carried from the old ``task.py``, ``task_instructions.py``, ``task_presentation.py``, ``decision_state.py``,
``decision_inputs.py``, ``child_commissioning.py``, ``source_operations.py`` and ``source_references.py``. One unit
is one model-selected tool call or one child commission. The task always offers a unit and never ends the Episode:
only the yield controller does. The episode has no reasoning commit and cannot search or fetch new sources (no
acquisition tools). The first unit is a lookup of the tool catalog. This file is a private copy: it imports nothing
from another episode."""
from copy import deepcopy
import json
from urllib.parse import urlsplit

from method_loop import FormError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.gene_context_evidence import (
    literature_investigation_prompt)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import (
    identity, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.received_records import (
    read_record_in_scope)
from gene_annotation_episode.episodic_workflow.episode_support.tools.gene_context_evidence.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

from .goal import GOAL
from .messages.final_to_parent import REPORT_FORM

# The three children (the old ``_CHILDREN['literature_page']``: literature_table, literature_ordered,
# literature_targeted), by slot.
CHILD_SLOTS = {
    'table_evidence_extraction': 'gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction',
    'source_coverage_improvement': 'gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement',
    'passage_evidence_extraction': 'gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction',
}
SERVICES = ()

# What each child takes as its ``selection`` (the old ``_TABLE`` and ``_WINDOW`` schemas), as the prompt tells it.
CHILD_SELECTIONS = {
    'table_evidence_extraction': (
        'One selected table or sheet: either a workbook table selection {"source_ref", "sheet_key", "offset" '
        '(matching rows to skip, 0 or more), "limit" (rows to read, 0 or more), optional "header_row" (1 or more), '
        'optional "where" {"column" (letters, optional), "match" ("equals" or "contains"), "value", '
        '"case_sensitive"}} or one byte window {"source_ref", "representation", "offset", "limit"} to begin reading '
        'an article XML table at. The source is the assigned source and the representation the assigned one.'),
    'source_coverage_improvement': (
        'The one window where document-order reading starts: {"source_ref", "representation", "offset" (UTF-8 '
        'byte offset, 0 or more), "limit" (UTF-8 bytes, 1 or more)}, of the assigned source and representation.'),
    'passage_evidence_extraction': (
        'The separate passages to investigate: {"spans": [{"source_ref", "representation", "offset" (0 or more), '
        '"limit" (1 or more)}, ...]}, each of the assigned source and representation.'),
}

# The model's tool names carry no dots; each names one operation of the A103 tool registry (the old
# ``_ACCESS_TOOLS`` that the services catalogue also has).
ACCESS = {
    'state_query': 'state.query', 'source_read': 'source.read', 'source_locate': 'source.locate',
    'source_sequence_scan': 'source.sequence.scan', 'source_sequence_references': 'source.sequence.references',
    'source_experimental_records': 'source.experimental.records', 'image_view': 'image.view',
    'source_archive_members': 'source.archive.members', 'source_archive_extract': 'source.archive.extract',
    'source_xlsx_sheets': 'source.xlsx.sheets', 'source_xlsx_rows': 'source.xlsx.rows',
    'source_pdf_info': 'source.pdf.info', 'source_pdf_text': 'source.pdf.text', 'source_pdf_page': 'source.pdf.page',
    'execution_estimate': 'execution.estimate',
}
# Tools whose source reads are bound to the records this episode holds (the old ``authorization``).
HELD_SOURCE_TOOLS = ('source.locate', 'source.sequence.scan', 'source.sequence.references',
                     'source.experimental.records')
# ``execution.estimate`` is cut down to its workbook branches; with none it is not offered.
XLSX_ESTIMATES = ('source.xlsx.sheets', 'source.xlsx.rows')

REASONING_START = 'Select one ordinary tool, one typed reasoning commitment'
REASONING_END = 'Reasoning owns scientific interpretation'
TAIL_START = 'When annotation_score is supplied'
TAIL_END = 'Do not execute native provider tools.'
TOOL_INSTRUCTION = (
    'Select one operation per answer: give its name in operation and its operands as JSON text in arguments_json. '
    'An access operation takes its own operands; every one that names a source must name the assigned source or a '
    'source derived from it. A child operation (table_evidence_extraction, source_coverage_improvement, '
    'passage_evidence_extraction) takes {"objective": <what the child should investigate, as text>, "selection": '
    '<the selection that child takes, listed under Child investigations>}. Examining is the work: record what the '
    'source reports by selecting the report tool with its controlled values: target_correspondence (established, '
    'unresolved or not_applicable), evidence_type (the kind of gene-context evidence the source reports, or '
    'none_applicable) and the separate readings (source_ref, kind, offset, limit), including those of what '
    'the child investigations returned. No text of yours is returned to your parent. Selecting report does not end '
    'the investigation; report again when new '
    'outcomes change it. Only the numerical controller decides when your work ends. Do not execute native '
    'provider tools. The host executes your selected action.')


def instructions(*, knowledge, launch):
    """The old ``task_instructions.instructions``: the A103 literature investigation text without the actions this
    episode does not have (reasoning commits, the report update, redelivery, the exchange), this episode's goal,
    the tool-knowledge text and the launch-instruction text when they are offered."""
    text = literature_investigation_prompt.INSTRUCTIONS
    text = replace_span(text, REASONING_START, REASONING_END,
                        'Select one ordinary tool or one substantive child improvement. A tool lookup alone is not '
                        'a child Episode. There are no biological departments or compulsory stages.\n')
    text = replace_span(text, TAIL_START, TAIL_END, '')
    text += '\n\n' + GOAL
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if launch is not None:
        text += LAUNCH_INSTRUCTIONS
    return text + '\n\n' + TOOL_INSTRUCTION


def catalog(available):
    """The access operations of the registry catalog this episode offers (the old ``catalog``): only the access
    tools, ``execution.estimate`` cut to its workbook branches, every input schema projected through
    ``source_location_inputs``."""
    result = []
    for name, entry in available.items():
        if name not in ACCESS.values():
            continue
        entry = deepcopy({'name': name, **entry})
        if name == 'execution.estimate':
            branches = [branch for branch in entry['input_schema'].get('anyOf', ())
                        if branch.get('properties', {}).get('tool', {}).get('const') in XLSX_ESTIMATES]
            if not branches:
                continue
            entry['input_schema'] = {'anyOf': branches}
        entry['input_schema'] = source_location_inputs(entry['input_schema'])
        result.append(entry)
    return json.loads(json.dumps(result))


def within_source(store, reference, root, scope):
    """Whether ``reference`` is ``root`` or a source derived from it through ``parent_source_refs`` (the old
    ``_within_source``; each source on the way is read in scope)."""
    pending, seen = [reference], set()
    while pending:
        current = pending.pop()
        if current == root:
            return True
        if current in seen:
            continue
        seen.add(current)
        source = read_record_in_scope(store, current, scope, 'source')
        pending.extend(source.get('parent_source_refs', ()))
    return False


def admitted(store, entries, name, arguments, scope, root):
    """The old ``_tool_arguments``: the arguments against the offered schema and the source they name against the
    assigned page's source. A violation is a ``ContractError``."""
    if name not in entries:
        raise ContractError('tool_not_available_to_a103_literature_role')
    validate_schema(arguments, entries[name]['input_schema'])
    selected = arguments['arguments'] if name == 'execution.estimate' else arguments
    source_ref = selected.get('source_ref')
    if name == 'source.archive.extract':
        source_ref = read_record_in_scope(store, arguments['member_ref'], scope, 'archive_member')['source_ref']
    if source_ref is not None and not within_source(store, source_ref, root, scope):
        raise ContractError('literature_reading_outside_assigned_source')


async def run_access_tool(name, envelope, ctx):
    """Execute one access tool. A contract error is returned as an ``invalid`` outcome with ``arguments_or_reference``
    feedback, as the old ``execute`` did; the outcome is the unit's outcome like any other."""
    arguments, scope = envelope['arguments'], envelope['scope']
    registry = ToolRegistry(ctx.store, **ctx.settings.get('tool_registry', {}))
    entries = {entry['name']: entry for entry in catalog(registry.catalog(scope))}
    try:
        admitted(ctx.store, entries, name, arguments, scope, envelope['source_ref'])
    except (ContractError, ValueError) as error:
        detail = {'detail': error.detail} if getattr(error, 'detail', None) else {}
        return {'status': 'invalid',
                'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': name, 'arguments': arguments}),
                'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': str(error), **detail}}
    permitted = tuple(ctx.store.refs()) if name in HELD_SOURCE_TOOLS else None
    try:
        return await registry.execute_async(name, arguments, scope=scope, operation_key=ctx.operation_key,
                                            permitted_record_refs=permitted)
    except CustodyError:
        raise
    except Exception as error:   # the old record_execution_failure: a failed selected operation is an outcome
        return failure_outcome(ctx.store, error, category='episode_execution', cause_code='selected_operation_failed')


def tool_catalog(arguments, ctx):
    """The first lookup: the access operations the registry offers for the scope."""
    return {'catalog': catalog(ToolRegistry(ctx.store, **ctx.settings.get('tool_registry', {})).catalog(
        arguments['scope']))}


async def state_query(arguments, ctx):
    return await run_access_tool('state.query', arguments, ctx)


async def source_read(arguments, ctx):
    return await run_access_tool('source.read', arguments, ctx)


async def source_locate(arguments, ctx):
    return await run_access_tool('source.locate', arguments, ctx)


async def source_sequence_scan(arguments, ctx):
    return await run_access_tool('source.sequence.scan', arguments, ctx)


async def source_sequence_references(arguments, ctx):
    return await run_access_tool('source.sequence.references', arguments, ctx)


async def source_experimental_records(arguments, ctx):
    return await run_access_tool('source.experimental.records', arguments, ctx)


async def image_view(arguments, ctx):
    return await run_access_tool('image.view', arguments, ctx)


async def source_archive_members(arguments, ctx):
    return await run_access_tool('source.archive.members', arguments, ctx)


async def source_archive_extract(arguments, ctx):
    return await run_access_tool('source.archive.extract', arguments, ctx)


async def source_xlsx_sheets(arguments, ctx):
    return await run_access_tool('source.xlsx.sheets', arguments, ctx)


async def source_xlsx_rows(arguments, ctx):
    return await run_access_tool('source.xlsx.rows', arguments, ctx)


async def source_pdf_info(arguments, ctx):
    return await run_access_tool('source.pdf.info', arguments, ctx)


async def source_pdf_text(arguments, ctx):
    return await run_access_tool('source.pdf.text', arguments, ctx)


async def source_pdf_page(arguments, ctx):
    return await run_access_tool('source.pdf.page', arguments, ctx)


async def execution_estimate(arguments, ctx):
    return await run_access_tool('execution.estimate', arguments, ctx)


def report(arguments, ctx):
    """The model's controlled report as the outcome of a unit (the two choices and the exact readings); the summary
    holds the latest and code reads the finding from it. A report that is not of the declared form, or that names a
    source this episode does not hold, is an invalid outcome."""
    try:
        value = REPORT_FORM.admit(arguments['report'], 'report')
    except FormError as error:
        return {'status': 'invalid', 'feedback': {'category': 'report_format', 'detail': str(error)}}
    unheld = [reading['source_ref'] for reading in value['readings'] if not ctx.store.holds(reading['source_ref'])]
    if unheld:
        return {'status': 'invalid', 'feedback': {'category': 'arguments_or_reference',
                                                  'detail': 'reading sources not held: ' + ', '.join(unheld)}}
    return {'status': 'reported', 'report': value}


TOOLS = {'tool_catalog': tool_catalog, 'state_query': state_query, 'source_read': source_read,
         'source_locate': source_locate, 'source_sequence_scan': source_sequence_scan,
         'source_sequence_references': source_sequence_references,
         'source_experimental_records': source_experimental_records, 'image_view': image_view,
         'source_archive_members': source_archive_members, 'source_archive_extract': source_archive_extract,
         'source_xlsx_sheets': source_xlsx_sheets, 'source_xlsx_rows': source_xlsx_rows,
         'source_pdf_info': source_pdf_info, 'source_pdf_text': source_pdf_text, 'source_pdf_page': source_pdf_page,
         'execution_estimate': execution_estimate, 'report': report}


def offered(summary):
    """The model's operation names: the catalog's operations (dots out), ``report`` and the three child slots."""
    named = {operation: name for name, operation in ACCESS.items()}
    return [named[entry['name']] for entry in summary['catalog']] + ['report', *CHILD_SLOTS]


def output_schema(names):
    return {'type': 'object', 'additionalProperties': False, 'required': ['operation', 'arguments_json'],
            'properties': {'operation': {'enum': names},
                           'arguments_json': {'type': 'string', 'description': 'The operands as one JSON object'}}}


def source_operands(custody):
    """Callable source metadata only (the old ``_source_operands``): sources with an id, a provider and, when plain
    http(s), a resource URI."""
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


def section(parts, title, body):
    if body not in (None, '', [], {}):
        parts.extend(['', title, '', body if isinstance(body, str) else json.dumps(body, indent=1, sort_keys=True)])


def present(summary, text):
    """The old ``render_receiver_prompt`` over this episode's summary: the assigned work, the fixed scope, the
    parent's constraints, context and evidence operands, the callable sources, the callable operations with their
    operands, the child investigations and what they returned, and the return form."""
    assignment = summary['assignment']
    parts = ['TASK', '', text]
    section(parts, 'Assigned work', {'goal': GOAL.split('\n\n')[1],
                                     'page': {name: assignment[name] for name in (
                                         'source_ref', 'representation', 'artifact_ref', 'question_context_refs',
                                         'prior_delivery_refs')}})
    section(parts, 'Fixed scope', assignment['scope'])
    section(parts, 'Parent message', assignment['message'])
    context = assignment.get('gene_context_evidence', {}).get('assignment', {})
    section(parts, 'Parent constraints', context.get('constraints'))
    section(parts, 'Parent-supplied context', context.get('context'))
    section(parts, 'Parent-selected evidence operands', context.get('evidence_refs'))
    section(parts, 'Callable supplied Sources', source_operands(summary['source_custody']))
    named = {operation: name for name, operation in ACCESS.items()}
    section(parts, 'Callable operations', [{'tool': named[entry['name']], 'operation': entry['name'],
                                            'meaning': entry.get('description', ''),
                                            'operands': entry['input_schema']} for entry in summary['catalog']])
    section(parts, 'Child investigations', CHILD_SELECTIONS)
    section(parts, 'Returned by child investigations', summary['child_reports'])
    section(parts, 'Current gene-context scoring sheet', summary['completed_work_axis_results'])
    section(parts, 'Return', 'Report with the report tool: ' + json.dumps(REPORT_FORM.as_record(), sort_keys=True))
    return '\n'.join(parts)


def decide(summary, feedback, ctx):
    """The tool catalog first (a lookup, one unit); then ask the model for the next operation, shown the
    assignment, the custody of the source, its own read outcomes, what its children returned, the finding so far,
    the pixels of a completed image view, the measured time and the yield table (the old decision state and
    inputs, over this episode's summary)."""
    if summary['catalog'] is None:
        return ToolCall('tool_catalog', {'scope': summary['assignment']['scope']})
    knowledge_directory = ctx.settings.get('knowledge_library_directory')
    launch_directory = ctx.settings.get('launch_instruction_directory')
    knowledge = None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()
    launch = None if launch_directory is None else LaunchInstructions(launch_directory).context()
    text = instructions(knowledge=knowledge, launch=launch)
    context = {'task': present(summary, text), 'goal': GOAL, 'scope': summary['assignment']['scope'],
               'literature_source_custody': summary['source_custody'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_history_meaning': summary['literature_history_meaning'],
               'child_reports': summary['child_reports'],
               'current_report': summary['report'], 'report_lifecycle': summary['report_lifecycle'],
               'completed_work_axis_results': summary['completed_work_axis_results'],
               'visual_evidence': summary['visual_evidence'],
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['action_yields'],
        'tool_knowledge': knowledge, 'launch_instruction_library': launch},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', text, context, output_schema(offered(summary)))


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one child commission, or reject it (no unit): the answer
    names an offered operation and closed JSON operands (the ``report`` tool itself checks its finding and the
    sources it cites; a child's form checks the selection it is commissioned with)."""
    try:
        name = response['operation']
        if name not in offered(summary):
            raise ValueError('operation_not_offered:' + repr(name))
        arguments = json.loads(response['arguments_json'])
        if not isinstance(arguments, dict):
            raise ValueError('arguments_json_must_be_a_JSON_object')
        if name in CHILD_SLOTS:
            if type(arguments.get('objective')) is not str or not arguments['objective'].strip() \
                    or not isinstance(arguments.get('selection'), dict):
                raise ValueError('child_operands_need_an_objective_text_and_a_selection_object')
    except (KeyError, TypeError, ValueError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    if name in CHILD_SLOTS:
        return ChildCall(name, {'objective': arguments['objective'], 'selection': arguments['selection']})
    if name == 'report':
        return ToolCall('report', {'report': arguments})
    assignment = summary['assignment']
    return ToolCall(name, {'arguments': arguments, 'scope': assignment['scope'],
                           'source_ref': assignment['source_ref']})
