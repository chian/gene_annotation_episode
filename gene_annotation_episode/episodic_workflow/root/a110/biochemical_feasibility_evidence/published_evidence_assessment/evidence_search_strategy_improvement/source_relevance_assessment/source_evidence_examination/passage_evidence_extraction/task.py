"""The task: read the assigned source's passages, with their neighbouring context, through the access tools, grade
the reaction or resource evidence they supply with ``literature_reaction_populate`` or
``literature_reaction_source_populate`` (the A110 literature reaction grader, sheet ``literature_reaction_cells``),
and commit reasoning on what they say.

Carried from the old ``task.py``, ``task_decision.py``, ``task_action.py``, ``task_instructions.py``,
``source_operations.py``, ``reaction_records.py`` and ``source_custody.py``. The old ``report`` tool is gone: the
return is controlled features read by code from the saved sheets and the committed assessments, not the model's
prose. One unit is one model-selected tool call. The task always offers a unit and never ends the Episode: only the
yield controller does. The episode has no child and cannot search or fetch new sources (no acquisition tools)."""
from jsonschema import ValidationError

from episode_runtime import CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.instructions.scientific_instruction_text import (
    INSTRUCTIONS as DEFAULT_INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.literature_contract_error import (
    ExperimentalContractError)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.biochemical_feasibility_evidence.literature_reaction_grader import (
    grader_instructions)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.biochemical_feasibility_evidence.literature_sequence_discovery import (
    references_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.biochemical_feasibility_evidence.literature_reaction_storage import (
    POPULATE_DESCRIPTION, SOURCE_POPULATE_DESCRIPTION, population_input_schema, populate_reaction_sheet,
    populate_reaction_source_sheet, source_population_input_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.readers.biochemical_feasibility_evidence.source_locations import (
    locate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_operations.biochemical_feasibility_evidence.source_sequences import (
    scan_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.domain import (
    RECORD_SCHEMAS, REF, REFS, identity, obj, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.experimental_database_records import (
    reader_schema as experimental_records_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.received_records import read_record_in_scope
from gene_annotation_episode.episodic_workflow.episode_support.tools.biochemical_feasibility_evidence.tools import (
    ToolRegistry)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

from .goal import GOAL

CHILD_SLOTS = {}
SERVICES = ()

INTEGER = {'type': 'integer', 'minimum': 0}
POSITIVE = {'type': 'integer', 'minimum': 1}
TEXT = {'type': 'string', 'minLength': 1}
ARGUMENT_TRANSPORT_ERROR = 'a110_argument_transport_not_carried'

# The access tools of the old ``_ACCESS_TOOLS``; descriptions as the A110 tool library's ``ToolRegistry.catalog``
# states them (a private copy: the registry cannot be built without a Store).
DESCRIPTIONS = {
    'state.query':
        'Read an exact page of typed scientific records, current revisions, or records referring to actual references. Follow the returned next_query for the same selection and order. Exact refs is a separate mode and cannot be combined with page selectors.',
    'source.read':
        'Read a bounded UTF-8 byte window from an actual source. Choose original for retained source bytes, including XML tables/headings omitted by a paragraph projection; text selects that projection when available. Explicit stdout/stderr select retained native stream bytes when present, without falling back to another representation. Returned artifact/offsets support exact anchors.',
    'source.locate':
        'Locate an exact supplied literal quote in an explicitly received original or text source representation. Return UTF-8 byte witnesses, unchanged neighboring context and bounded match continuation. Multiple occurrences remain separate. No normalization, scientific interpretation, measurement parsing or evidence credit is performed; no literal match means only no match in the examined bytes.',
    'source.sequence.scan':
        'Recognize candidate protein sequence blocks in received source text/XML/HTML, preserving original UTF-8 positions. Normalize case, whitespace, numbering and soft hyphens; report exact containment, extra residues and literal differences. For numbered GenBank/GenPept blocks, include the ORIGIN marker and contiguous residue rows in the selected window. Hard hyphens remain explicit, with conditional correspondence, until their byte offsets are selected as formatting_hyphen_offsets after inspecting the layout. A document boundary may require an overlapping window. No biological gaps, tags or substitutions are silently removed.',
    'source.sequence.references':
        'Read a page of publication identifiers, titles and reported citation scopes from a received sequence-identity response. Reverify full sequence equality for the selected record. Citation metadata supplies leads; it does not establish experimental results.',
    'source.experimental.records':
        'Inspect one page of a received experimental database response. Return native assay records, source measurement selectors and literal record links. Optional contains and contains_all filter retained rows by one or several literal terms, including their native headers and section labels. Record and whole-page link continuations are separate. These records locate the chemical or reaction source evidence; metadata and deposited scores retain their native meanings.',
    'image.view':
        'Inspect one explicitly selected frame of a registered scientific image. The next reasoning call receives its actual pixels and exact source/frame metadata. Stored axes are preserved; no contrast adjustment, resizing, interpretation or annotation is performed. An optional RGB conversion is explicit and recorded; original bytes remain intact.',
    'source.archive.members':
        'Inventory one page of an actual ZIP/TAR source. Member IDs preserve ordinal identity, including duplicate names; no members are extracted or selected for you.',
    'source.archive.extract':
        "Extract exactly one inventoried regular member to a source artifact; never follow a member's host path or link. Original archive and member identity remain attached.",
    'source.xlsx.sheets':
        'Read the actual sheet names, relationship keys and package parts of a retained XLSX source. No sheet or biological interpretation is selected for you.',
    'source.xlsx.rows':
        'Read a selected page of actual XLSX rows, optionally matching literal cell values. Select sheet_key from source.xlsx.sheets; row offsets count matching rows, while returned row numbers/cell addresses retain native identity. Header row is caller-selected or null. Original numeric/date lexical values, styles, formulas and caches remain distinct; no formula is recalculated or biology inferred.',
    'source.pdf.info':
        'Read native PDF information and physical page count for a selected actual source; no biological interpretation.',
    'source.pdf.text':
        'Extract a selected physical PDF page or contiguous page range as a reusable UTF-8 text derivative. page is the first page; optional last_page is inclusive and defaults to page. Use source.pdf.info for the physical page count, then source.locate on the extracted text to find a section without guessing pages. Native page breaks and the selected range are retained. Byte offsets refer to this text derivative, not the PDF. No OCR or interpretation is performed.',
    'source.pdf.page':
        'Render one explicitly selected physical PDF page as a reusable PNG source. Rendering does not by itself supply image input to a model or interpret a figure.',
    'execution.estimate':
        'Obtain recorded duration expectations before a proposed workbook selection. Uses the same operands, actual settings and caller resource as execution. Creates no native job or scientific evidence; missing history stays unknown. This is an optional information tool, not a scheduling or continuation decision.',
}

# python tool name -> the library's tool name (a tool name here is lowercase letters, digits and underscores)
LIBRARY_NAMES = {
    'state_query': 'state.query', 'source_read': 'source.read', 'source_locate': 'source.locate',
    'source_sequence_scan': 'source.sequence.scan', 'source_sequence_references': 'source.sequence.references',
    'source_experimental_records': 'source.experimental.records', 'image_view': 'image.view',
    'source_archive_members': 'source.archive.members', 'source_archive_extract': 'source.archive.extract',
    'source_xlsx_sheets': 'source.xlsx.sheets', 'source_xlsx_rows': 'source.xlsx.rows',
    'source_pdf_info': 'source.pdf.info', 'source_pdf_text': 'source.pdf.text', 'source_pdf_page': 'source.pdf.page',
    'execution_estimate': 'execution.estimate'}
# Tools whose source reads are bound to the records this episode holds (the old ``authorization``).
HELD_SOURCE_TOOLS = ('source.locate', 'source.sequence.scan', 'source.sequence.references',
                     'source.experimental.records')

INPUT_SCHEMAS = {
    'state.query': obj({
        'kind': {'enum': list(RECORD_SCHEMAS) + ['subject']}, 'offset': INTEGER, 'limit': POSITIVE,
        'refs': {**REFS,
                 'description': 'Exact reference mode: supply refs alone, including an empty array for no records. '
                                'Omit kind, offset, limit, current_only and references in this mode.'},
        'current_only': {'type': 'boolean'},
        'references': {'type': 'array', 'items': REF, 'minItems': 1,
                       'description': "Select records that refer to any supplied ID through reference fields or "
                                      "provenance anchors. This does not match a record's own ID; to read known "
                                      "records themselves, supply refs alone instead."}}, required=[]),
    'source.read': obj({'source_ref': REF, 'offset': INTEGER, 'limit': POSITIVE,
                        'representation': {'enum': ['text', 'original', 'stdout', 'stderr']}}, ['source_ref']),
    'source.locate': locate_schema(),
    'source.sequence.scan': scan_schema(),
    'source.sequence.references': references_schema(),
    'source.experimental.records': experimental_records_schema(),
    'image.view': obj({'source_ref': REF, 'frame': INTEGER, 'colour_conversion': {'enum': ['preserve', 'rgb']}},
                      ['source_ref']),
    'source.archive.members': obj({'source_ref': REF, 'offset': INTEGER, 'limit': POSITIVE}, ['source_ref']),
    'source.archive.extract': obj({'member_ref': REF}),
    'source.xlsx.sheets': obj({'source_ref': REF}),
    'source.xlsx.rows': obj({
        'source_ref': REF, 'sheet_key': TEXT, 'offset': INTEGER, 'limit': INTEGER,
        'header_row': {'type': ['integer', 'null'], 'minimum': 1},
        'where': {**obj({'column': {'type': ['string', 'null'], 'pattern': '^[A-Z]+$'},
                         'match': {'enum': ['equals', 'contains']}, 'value': TEXT,
                         'case_sensitive': {'type': 'boolean'}}), 'type': ['object', 'null']}}),
    'source.pdf.info': obj({'source_ref': REF}),
    'source.pdf.text': obj({'source_ref': REF, 'page': POSITIVE, 'last_page': POSITIVE,
                            'layout': {'enum': ['reading_order', 'layout', 'raw']}}, ['source_ref', 'page']),
    'source.pdf.page': obj({'source_ref': REF, 'page': POSITIVE, 'dpi': {'type': 'number', 'exclusiveMinimum': 0}},
                           ['source_ref', 'page']),
}
# ``execution.estimate`` is offered for the workbook tools only, and only when the run has timing statistics.
INPUT_SCHEMAS['execution.estimate'] = {'anyOf': [
    obj({'tool': {'const': name}, 'arguments': INPUT_SCHEMAS[name]}) for name in ('source.xlsx.sheets', 'source.xlsx.rows')]}


REASON_DESCRIPTION = ('Commit a typed scientific reasoning over the supplied passages and the records you hold: '
                      'extracted terms, source subjects, contexts, observations, hypotheses and assessments, each '
                      'with its exact source anchor. A commit with every section empty is rejected.')
POPULATE_NAMES = {'literature_reaction_populate': 'literature.reaction.populate',
                  'literature_reaction_source_populate': 'literature.reaction.source.populate'}

HISTORY_START = 'On a fresh provider conversation,'
HISTORY_END = 'Do not execute native provider tools.'
HISTORY_GUIDANCE = ('Your own earlier read outcomes are shown to you as own_literature_outcomes; that page creates '
                    'no new action and does not execute or credit the historical work again.\n')
REPORT_START = "A commissioned child returns ONLY the parent's typed form."
REPORT_END = 'A report_delivery_failure is operational feedback'
RETURN_GUIDANCE = ('What returns to your parent is your credit and the features code reads from the reaction sheets '
                   'you saved and from the typed assessments you committed (cell values, statuses and missing '
                   'reasons, counts, fixed values and record references); no prose of yours is returned. Selecting '
                   'a tool does not end your work: only the numerical controller does. Later tool outcomes are '
                   'facts, not a new judgment.\n')
TAIL_GUIDANCE = ('\nSelect literature_reaction_populate or literature_reaction_source_populate when the examined '
                 'source supplies the measured ratios, predictions or resource quantities of the assigned question.')


def instructions(*, knowledge, family):
    """The old task_instructions.instructions: the default investigation text (the span about the parent-written
    report form, the span about redelivery and the span about the decision-exchange history replaced: those actions
    no longer exist), this episode's goal, the reasoning-commit requirement, the reaction grader of the selected
    family (the old ``literature_reaction_instructions.lead`` and ``selected_literature_task_sections``) and the
    tool-knowledge text when it is offered."""
    text = replace_span(DEFAULT_INSTRUCTIONS, REPORT_START, REPORT_END, RETURN_GUIDANCE)
    text = replace_span(text, REPORT_END, HISTORY_START, '')
    text = replace_span(text, HISTORY_START, HISTORY_END, HISTORY_GUIDANCE)
    text += '\n' + GOAL + '\n' + REASONING_COMMIT_REQUIREMENT
    text += grader_instructions(family)
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    return text + TAIL_GUIDANCE


def offered(settings):
    """The access tools offered now: execution_estimate only with timing statistics configured; then the two
    reaction graders and the reasoning commit."""
    tools = [name for name in LIBRARY_NAMES
             if name != 'execution_estimate' or settings.get('tool_registry', {}).get('native_statistics') is not None]
    return tools + ['literature_reaction_populate', 'literature_reaction_source_populate', 'reason']


def reason_schema(commit_schema):
    """The old reasoning_action_schema is None for this episode (the common reason selection): the typed commit."""
    return source_location_inputs(obj({'commit': commit_schema}))


def catalog(names, commit_schema):
    """The tools the model is shown: name, description and input schema (the old catalog with the old
    ``_population_catalog`` entries; every input schema is projected through source_location_inputs)."""
    entries = []
    for name in names:
        if name == 'literature_reaction_populate':
            entries.append({'name': name, 'description': POPULATE_DESCRIPTION,
                            'input_schema': population_input_schema()})
        elif name == 'literature_reaction_source_populate':
            entries.append({'name': name, 'description': SOURCE_POPULATE_DESCRIPTION,
                            'input_schema': source_population_input_schema()})
        elif name == 'reason':
            entries.append({'name': 'reason', 'description': REASON_DESCRIPTION,
                            'input_schema': reason_schema(commit_schema)})
        else:
            entries.append({'name': name, 'description': DESCRIPTIONS[LIBRARY_NAMES[name]],
                            'input_schema': source_location_inputs(INPUT_SCHEMAS[LIBRARY_NAMES[name]])})
    return entries


def selection_schema(names, commit_schema):
    """What the model answers with: one tool and its arguments (the old action schema)."""
    return obj({'selection': {'anyOf': [obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']},
                                             'arguments': entry['input_schema']})
                                        for entry in catalog(names, commit_schema)]}})


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


def admitted(store, name, arguments, scope, root):
    """The old ``_tool_arguments``: the arguments against the offered schema, and the source they name against the
    assigned page's source. A violation is a ``ContractError``."""
    validate_schema(arguments, source_location_inputs(INPUT_SCHEMAS[name]))
    selected = arguments['arguments'] if name == 'execution.estimate' else arguments
    source_ref = selected.get('source_ref')
    if name == 'source.archive.extract':
        source_ref = read_record_in_scope(store, arguments['member_ref'], scope, 'archive_member')['source_ref']
    if source_ref is not None and not within_source(store, source_ref, root, scope):
        raise ContractError('literature_reading_outside_assigned_source')


async def run_access_tool(name, envelope, ctx):
    """Execute one access tool. A contract error is returned as an ``invalid`` outcome with ``arguments_or_reference``
    feedback, as the old ``execute`` did; the outcome is the unit's outcome like any other."""
    arguments, scope, root = envelope['arguments'], envelope['scope'], envelope['page_source_ref']
    try:
        admitted(ctx.store, name, arguments, scope, root)
    except (ContractError, ValidationError) as error:
        detail = {'detail': error.detail} if getattr(error, 'detail', None) else {}
        return {'status': 'invalid',
                'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': name, 'arguments': arguments}),
                'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': str(error), **detail}}
    registry = ToolRegistry(ctx.store, **ctx.settings.get('tool_registry', {}))
    permitted = tuple(ctx.store.refs()) if name in HELD_SOURCE_TOOLS else None
    try:
        return await registry.execute_async(name, arguments, scope=scope, operation_key=ctx.operation_key,
                                            permitted_record_refs=permitted)
    except CustodyError:
        raise
    except Exception as error:   # the old record_execution_failure: a failed selected operation is an outcome
        return failure_outcome(ctx.store, error, category='episode_execution', cause_code='selected_operation_failed')


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



def invalid(name, arguments, operation_key, error):
    return {'status': 'invalid',
            'operation_ref': identity('operation', {'key': operation_key, 'name': name, 'arguments': arguments}),
            'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'category': 'arguments_or_reference', 'code': str(error),
                         'field': getattr(error, 'field', None),
                         **({'detail': error.detail} if getattr(error, 'detail', None) is not None else {})}}


def literature_reaction_populate(arguments, ctx):
    """``literature.reaction.populate``: read the selected retained dataset (or none) and the literal witnesses of
    held sources below the assigned page, calculate the fifteen reaction and resource cells and save the sheet, its
    bindings, its cell rows, its revision family and its experiment assessment through ``ctx.store``. Arguments the
    library refuses are returned as an ``invalid`` outcome with their code, as the old ``execute`` did; the outcome
    enters the iterator like any other."""
    try:
        return populate_reaction_sheet(ctx.store, arguments['scope'], arguments['page_source_ref'],
                                       arguments['arguments'], ctx.operation_key)
    except (ContractError, ExperimentalContractError) as error:
        return invalid(POPULATE_NAMES['literature_reaction_populate'], arguments['arguments'], ctx.operation_key,
                       error)


def literature_reaction_source_populate(arguments, ctx):
    """``literature.reaction.source.populate``: save the model's exact source selectors as a selection source, then
    populate the sheet from it through the native reader (the old ``reaction_source_selection.populate_source``)."""
    try:
        return populate_reaction_source_sheet(ctx.store, arguments['scope'], arguments['page_source_ref'],
                                              arguments['arguments'], ctx.operation_key)
    except (ContractError, ExperimentalContractError) as error:
        return invalid(POPULATE_NAMES['literature_reaction_source_populate'], arguments['arguments'],
                       ctx.operation_key, error)


def reason(arguments, ctx):
    """Commit the model's typed reasoning (the old ``Store.commit_reasoning`` path of ``execute``; the owner of
    interpretation accounts is named by the system). The old episode had no reasoning action of its own, so the
    commit is not wrapped."""
    return ctx.store.commit_reasoning(arguments['arguments']['commit'], arguments['scope'], ctx.operation_key)


TOOLS = {'state_query': state_query, 'source_read': source_read, 'source_locate': source_locate,
         'source_sequence_scan': source_sequence_scan, 'source_sequence_references': source_sequence_references,
         'source_experimental_records': source_experimental_records, 'image_view': image_view,
         'source_archive_members': source_archive_members, 'source_archive_extract': source_archive_extract,
         'source_xlsx_sheets': source_xlsx_sheets, 'source_xlsx_rows': source_xlsx_rows,
         'source_pdf_info': source_pdf_info, 'source_pdf_text': source_pdf_text, 'source_pdf_page': source_pdf_page,
         'execution_estimate': execution_estimate, 'literature_reaction_populate': literature_reaction_populate,
         'literature_reaction_source_populate': literature_reaction_source_populate, 'reason': reason}


def decide(summary, feedback, ctx):
    """Ask the model for the next tool, shown the assignment, the custody of the source, its own read outcomes, the
    controlled features of the reaction sheets it saved and of the assessments it committed, the latest image it
    looked at, the tools, the measured time and the yield table (the old decision state and inputs, over this
    episode's summary). The instructions carry the reaction grader of the family the assignment selects."""
    names = offered(ctx.settings)
    knowledge_directory = ctx.settings.get('knowledge_library_directory')
    context = {'goal': GOAL, 'scope': summary['scope'], 'literature_assignment': summary['literature_assignment'],
               'literature_source_custody': summary['literature_source_custody'],
               'input_list': summary['input_list'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_history_meaning': summary['literature_history_meaning'],
               'visual_evidence': summary['visual_evidence'], 'last_local_outcome': summary['last_local_outcome'],
               'held_record_refs': summary['held_record_refs'], 'reaction_sheets': summary['reaction_sheets'],
               'investigation_finding': summary['investigation_finding'],
               'tools': catalog(names, summary['reasoning_schema']),
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['action_yields'],
        'tool_knowledge': None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(knowledge=context.get('tool_knowledge'), family=summary['family']),
                        context, strict_output_schema(selection_schema(names, summary['reasoning_schema']),
                                                      open_records_as_text=False,
                                                      argument_transport_error=ARGUMENT_TRANSPORT_ERROR))


def empty_commit(commit, commit_schema):
    """The old empty-reasoning test: every section the schema names is present or absent and none has a row."""
    return (set(commit_schema.get('required', commit_schema['properties'])) <= set(commit)
            <= set(commit_schema['properties']) and all(value == [] for value in commit.values()))


def validate_selection(value, schema):
    validate_schema(value, schema)
    return value['selection']


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call, or reject it (no unit). An answer that selects no offered tool,
    arguments that do not fit its schema, or an empty reasoning commit is invalid."""
    names = offered(ctx.settings)
    commit_schema = summary['reasoning_schema']
    schema = selection_schema(names, commit_schema)
    try:
        decoded = decode_strict_output(response, schema, open_records_as_text=False,
                                       argument_transport_error=ARGUMENT_TRANSPORT_ERROR)
        selection = validate_selection(decoded, schema)
        name, arguments = selection['tool'], selection['arguments']
        if name == 'reason' and empty_commit(arguments['commit'], commit_schema):
            raise ValueError('empty_reasoning_commit')
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(name, {'arguments': arguments, 'scope': summary['scope'],
                           'page_source_ref': summary['literature_assignment']['page']['source_ref']})
