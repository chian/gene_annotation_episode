"""The task: improve the literature search strategy. Search and acquire sources and read them through the access
and acquisition tools, commission the assessment of which returned sources merit examination, and write the strategy
report with the ``report`` tool.

Carried from the old ``task.py``, ``task_instructions.py``, ``task_presentation.py``, ``decision_state.py``,
``decision_inputs.py``, ``child_commissioning.py``, ``source_operations.py`` and ``source_references.py``. One unit
is one model-selected tool call or one child commission. The task always offers a unit and never ends the Episode:
only the yield controller does. The episode has no reasoning commit. Any operation valid against the offered schema
runs. The first unit is a lookup of the tool catalog. This file is a private copy: it imports nothing from another
episode."""
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
from gene_annotation_episode.episodic_workflow.episode_support.tools.gene_context_evidence.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

from .goal import GOAL
from .messages.final_to_parent import REPORT_FORM

# The one child (the old ``_CHILDREN['literature_strategy']``: literature_search), by slot.
CHILD_SLOTS = {
    'source_relevance_assessment': 'gene_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment',
}
SERVICES = ()

# The model's tool names carry no dots; each names one operation of the A103 tool registry: the old
# ``_ACCESS_TOOLS`` and ``_ACQUISITION_TOOLS`` that the services catalogue also has.
ACCESS = {
    'state_query': 'state.query', 'source_read': 'source.read', 'source_locate': 'source.locate',
    'source_sequence_scan': 'source.sequence.scan', 'source_sequence_references': 'source.sequence.references',
    'source_experimental_records': 'source.experimental.records', 'image_view': 'image.view',
    'source_archive_members': 'source.archive.members', 'source_archive_extract': 'source.archive.extract',
    'source_xlsx_sheets': 'source.xlsx.sheets', 'source_xlsx_rows': 'source.xlsx.rows',
    'source_pdf_info': 'source.pdf.info', 'source_pdf_text': 'source.pdf.text', 'source_pdf_page': 'source.pdf.page',
    'execution_estimate': 'execution.estimate',
}
ACQUISITION = {
    'public_literature_search': 'public.literature.search', 'public_literature_read': 'public.literature.read',
    'public_literature_sequence_identity': 'public.literature.sequence_identity',
    'public_ncbi_search': 'public.ncbi.search', 'public_pmc_versions': 'public.pmc.versions',
    'public_pmc_files': 'public.pmc.files', 'public_pmc_asset': 'public.pmc.asset',
}
OPERATIONS = {**ACCESS, **ACQUISITION}
# Tools whose source reads are bound to the records this episode holds (the old ``authorization``).
HELD_SOURCE_TOOLS = ('source.locate', 'source.sequence.scan', 'source.sequence.references',
                     'source.experimental.records')
# ``execution.estimate`` is cut down to its workbook branches; with none it is not offered.
XLSX_ESTIMATES = ('source.xlsx.sheets', 'source.xlsx.rows')

REASONING_START = 'Select one ordinary tool, one typed reasoning commitment'
REASONING_END = 'Reasoning owns scientific interpretation'
TAIL_START = 'When annotation_score is supplied'
TAIL_END = 'Do not execute native provider tools.'
CHILD_OPERANDS = (
    '{"objective": <what the child should investigate, as text>, "search_result_refs": [<sources of the input '
    'list (held, not yet handed to a child) that the child should consider; a source handed out is consumed and '
    'no longer offered>]}')
TOOL_INSTRUCTION = (
    'Select one operation per answer: give its name in operation and its operands as JSON text in arguments_json. '
    'An access or acquisition operation takes its own operands. The child operation (source_relevance_assessment) '
    'takes ' + CHILD_OPERANDS + '. Improving the strategy is the work: record the relevant source candidates found '
    'by selecting the report tool with candidates: one entry per candidate, source_ref, target_correspondence '
    '(established, unresolved, not_applicable, or not_examined) and evidence_type (the kind of gene-context evidence '
    'it reports, or none_applicable). No text of yours is returned to your parent. Selecting report does not end the investigation; '
    'report again when new outcomes change the strategy. Only the numerical controller decides when your work ends. '
    'Do not execute native provider tools. The host executes your selected action.')


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
    """The operations of the registry catalog this episode offers (the old ``catalog``): the access and acquisition
    tools, ``public.ncbi.search`` limited to ``pubmed``, ``execution.estimate`` cut to its workbook branches, every
    input schema projected through ``source_location_inputs``."""
    result = []
    for name, entry in available.items():
        if name not in OPERATIONS.values():
            continue
        entry = deepcopy({'name': name, **entry})
        if name == 'public.ncbi.search':
            entry['input_schema']['properties']['database'] = {'enum': ['pubmed']}
        if name == 'execution.estimate':
            branches = [branch for branch in entry['input_schema'].get('anyOf', ())
                        if branch.get('properties', {}).get('tool', {}).get('const') in XLSX_ESTIMATES]
            if not branches:
                continue
            entry['input_schema'] = {'anyOf': branches}
        entry['input_schema'] = source_location_inputs(entry['input_schema'])
        result.append(entry)
    return json.loads(json.dumps(result))


def admitted(entries, name, arguments):
    """The old ``_tool_arguments``: the operation is one offered and its arguments fit the offered schema. A
    violation is a ``ContractError``. This episode is not held to a source."""
    if name not in entries:
        raise ContractError('tool_not_available_to_a103_literature_role')
    validate_schema(arguments, entries[name]['input_schema'])


async def run_operation(tool_name, envelope, ctx):
    """Execute one access or acquisition operation. A contract error is returned as an ``invalid`` outcome with
    ``arguments_or_reference`` feedback, as the old ``execute`` did; the outcome is the unit's outcome like any
    other."""
    name = OPERATIONS[tool_name]
    arguments, scope = envelope['arguments'], envelope['scope']
    registry = ToolRegistry(ctx.store, **ctx.settings.get('tool_registry', {}))
    entries = {entry['name']: entry for entry in catalog(registry.catalog(scope))}
    try:
        admitted(entries, name, arguments)
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
    """The first lookup: the operations the registry offers for the scope."""
    return {'catalog': catalog(ToolRegistry(ctx.store, **ctx.settings.get('tool_registry', {})).catalog(
        arguments['scope']))}


async def state_query(arguments, ctx):
    return await run_operation('state_query', arguments, ctx)


async def source_read(arguments, ctx):
    return await run_operation('source_read', arguments, ctx)


async def source_locate(arguments, ctx):
    return await run_operation('source_locate', arguments, ctx)


async def source_sequence_scan(arguments, ctx):
    return await run_operation('source_sequence_scan', arguments, ctx)


async def source_sequence_references(arguments, ctx):
    return await run_operation('source_sequence_references', arguments, ctx)


async def source_experimental_records(arguments, ctx):
    return await run_operation('source_experimental_records', arguments, ctx)


async def image_view(arguments, ctx):
    return await run_operation('image_view', arguments, ctx)


async def source_archive_members(arguments, ctx):
    return await run_operation('source_archive_members', arguments, ctx)


async def source_archive_extract(arguments, ctx):
    return await run_operation('source_archive_extract', arguments, ctx)


async def source_xlsx_sheets(arguments, ctx):
    return await run_operation('source_xlsx_sheets', arguments, ctx)


async def source_xlsx_rows(arguments, ctx):
    return await run_operation('source_xlsx_rows', arguments, ctx)


async def source_pdf_info(arguments, ctx):
    return await run_operation('source_pdf_info', arguments, ctx)


async def source_pdf_text(arguments, ctx):
    return await run_operation('source_pdf_text', arguments, ctx)


async def source_pdf_page(arguments, ctx):
    return await run_operation('source_pdf_page', arguments, ctx)


async def execution_estimate(arguments, ctx):
    return await run_operation('execution_estimate', arguments, ctx)


async def public_literature_search(arguments, ctx):
    return await run_operation('public_literature_search', arguments, ctx)


async def public_literature_read(arguments, ctx):
    return await run_operation('public_literature_read', arguments, ctx)


async def public_literature_sequence_identity(arguments, ctx):
    return await run_operation('public_literature_sequence_identity', arguments, ctx)


async def public_ncbi_search(arguments, ctx):
    return await run_operation('public_ncbi_search', arguments, ctx)


async def public_pmc_versions(arguments, ctx):
    return await run_operation('public_pmc_versions', arguments, ctx)


async def public_pmc_files(arguments, ctx):
    return await run_operation('public_pmc_files', arguments, ctx)


async def public_pmc_asset(arguments, ctx):
    return await run_operation('public_pmc_asset', arguments, ctx)


def report(arguments, ctx):
    """The model's controlled report as this unit's outcome; the summary holds the latest and code reads the finding
    from it. A report that is not of the declared form, or that names a source this episode does not hold, is an
    invalid outcome."""
    try:
        value = REPORT_FORM.admit(arguments['report'], 'report')
    except FormError as error:
        return {'status': 'invalid', 'feedback': {'category': 'report_format', 'detail': str(error)}}
    unheld = [item['source_ref'] for item in value['candidates'] if not ctx.store.holds(item['source_ref'])]
    if unheld:
        return {'status': 'invalid', 'feedback': {'category': 'arguments_or_reference',
                                                  'detail': 'candidate sources not held: ' + ', '.join(unheld)}}
    return {'status': 'reported', 'report': value}


TOOLS = {'tool_catalog': tool_catalog, 'state_query': state_query, 'source_read': source_read, 'source_locate':
         source_locate, 'source_sequence_scan': source_sequence_scan, 'source_sequence_references':
         source_sequence_references, 'source_experimental_records': source_experimental_records, 'image_view':
         image_view, 'source_archive_members': source_archive_members, 'source_archive_extract':
         source_archive_extract, 'source_xlsx_sheets': source_xlsx_sheets, 'source_xlsx_rows': source_xlsx_rows,
         'source_pdf_info': source_pdf_info, 'source_pdf_text': source_pdf_text, 'source_pdf_page':
         source_pdf_page, 'execution_estimate': execution_estimate, 'public_literature_search':
         public_literature_search, 'public_literature_read': public_literature_read,
         'public_literature_sequence_identity': public_literature_sequence_identity, 'public_ncbi_search':
         public_ncbi_search, 'public_pmc_versions': public_pmc_versions, 'public_pmc_files': public_pmc_files,
         'public_pmc_asset': public_pmc_asset, 'report': report}


def offered(summary):
    """The model's operation names: the catalog's operations (dots out), ``report`` and the child slot."""
    named = {operation: name for name, operation in OPERATIONS.items()}
    # The child is offered only while the input list holds an unconsumed candidate source.
    return [named[entry['name']] for entry in summary['catalog']] + ['report', *(CHILD_SLOTS if summary['input_list'] else ())]


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
    operands, the child investigation and what it returned, and the return form."""
    assignment = summary['assignment']
    parts = ['TASK', '', text]
    section(parts, 'Assigned work', {'goal': GOAL.split('\n\n')[1],
                                     'question_context_refs': assignment['question_context_refs'],
                                     'prior_search_refs': assignment['prior_search_refs']})
    section(parts, 'Fixed scope', assignment['scope'])
    section(parts, 'Parent message', assignment['message'])
    context = assignment.get('gene_context_evidence', {}).get('assignment', {})
    section(parts, 'Parent constraints', context.get('constraints'))
    section(parts, 'Parent-supplied context', context.get('context'))
    section(parts, 'Parent-selected evidence operands', context.get('evidence_refs'))
    section(parts, 'Callable sources of the prior searches', source_operands(summary['source_custody']))
    named = {operation: name for name, operation in OPERATIONS.items()}
    section(parts, 'Callable operations', [{'tool': named[entry['name']], 'operation': entry['name'],
                                            'meaning': entry.get('description', ''),
                                            'operands': entry['input_schema']} for entry in summary['catalog']])
    section(parts, 'Child investigation', {'source_relevance_assessment': CHILD_OPERANDS})
    section(parts, 'Input list: candidate sources not yet handed to the child (a source handed out is consumed and '
                   'is no longer offered)', summary['input_list'])
    section(parts, 'Returned by the child investigation', summary['child_reports'])
    section(parts, 'Return', 'Report the strategy with the report tool: ' + json.dumps(REPORT_FORM.as_record(), sort_keys=True))
    return '\n'.join(parts)


def decide(summary, feedback, ctx):
    """The tool catalog first (a lookup, one unit); then ask the model for the next operation, shown the
    assignment, the custody of the sources, its own acquisition and read outcomes, what its child returned, the
    judgements so far, the pixels of a completed image view, the measured time and the yield table (the old
    decision state and inputs, over this episode's summary)."""
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
               'input_list': summary['input_list'],
               'consumed_search_result_refs': summary['consumed_search_result_refs'],
               'current_report': summary['report'], 'report_lifecycle': summary['report_lifecycle'],
               'visual_evidence': summary['visual_evidence'],
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['action_yields'],
        'tool_knowledge': knowledge, 'launch_instruction_library': launch},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', text, context, output_schema(offered(summary)))


def child_operands(arguments, records, input_list):
    """The model's operands of the child commission: an objective text and sources of the input list (held and not
    yet consumed by an earlier commission)."""
    if type(arguments.get('objective')) is not str or not arguments['objective'].strip():
        raise ValueError('child_operands_need_an_objective_text')
    sources = arguments.get('search_result_refs')
    if not isinstance(sources, list) or not sources:
        raise ValueError('child_search_result_refs_must_be_a_non_empty_list')
    for reference in sources:
        if type(reference) is not str or not records.holds(reference):
            raise ValueError('child_record_not_held:' + repr(reference))
        if reference not in input_list:
            raise ValueError('child_source_not_in_input_list_or_already_consumed:' + repr(reference))
    return {'objective': arguments['objective'], 'search_result_refs': sources}


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one child commission, or reject it (no unit): the answer
    names an offered operation and closed JSON operands (the ``report`` tool itself checks its judgements and the
    sources they name; the child commission names only records this episode holds)."""
    try:
        name = response['operation']
        if name not in offered(summary):
            raise ValueError('operation_not_offered:' + repr(name))
        arguments = json.loads(response['arguments_json'])
        if not isinstance(arguments, dict):
            raise ValueError('arguments_json_must_be_a_JSON_object')
        if name in CHILD_SLOTS:
            arguments = child_operands(arguments, records, summary['input_list'])
    except (KeyError, TypeError, ValueError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    if name in CHILD_SLOTS:
        return ChildCall(name, arguments)
    if name == 'report':
        return ToolCall('report', {'report': arguments})
    return ToolCall(name, {'arguments': arguments, 'scope': summary['assignment']['scope']})
