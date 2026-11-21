"""The task: assess which returned sources merit examination. The model searches and reads through the access and
acquisition tools, commissions the examination of one selected source, and grades the reaction or resource evidence a held source
supplies with ``literature_reaction_populate`` or ``literature_reaction_source_populate`` (the A110 literature
reaction grader).

Carried from the old ``task.py``, ``task_decision.py``, ``task_action.py``, ``task_instructions.py``,
``source_operations.py``, ``source_custody.py`` and ``contracts.py``. One unit is one model-selected tool call or one
commission of the child. The old permitted common actions were tool, child and redeliver_report (no reasoning
action, so there is no reasoning tool here). The task always offers a unit and never ends the Episode: only the
yield controller does. Unlike the examination child this episode is not bound to one source (its assignment has no
page): it may search for and fetch new sources (the old ``_ACQUISITION_TOOLS``) and read any it holds. The old
``report`` tool is gone: the return is controlled features read by code from the saved sheets, the held assessments
and the child's controlled return, not the model's prose."""
from jsonschema import ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.biochemical_feasibility_evidence.experimental_database_acquisition import (
    OPERATIONS as EXPERIMENT_DATABASE_TOOLS, catalog as experimental_database_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.instructions.scientific_instruction_text import (
    INSTRUCTIONS as DEFAULT_INSTRUCTIONS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.literature_contract_error import (
    ExperimentalContractError)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.biochemical_feasibility_evidence.literature_reaction_grader import (
    grader_instructions)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.biochemical_feasibility_evidence.literature_reaction_storage import (
    POPULATE_DESCRIPTION, SOURCE_POPULATE_DESCRIPTION, population_input_schema, populate_reaction_sheet,
    populate_reaction_source_sheet, source_population_input_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.biochemical_feasibility_evidence.literature_sequence_discovery import (
    identity_schema, references_schema)
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
from gene_annotation_episode.episodic_workflow.episode_support.tools.biochemical_feasibility_evidence.tools import (
    ToolRegistry)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

from .goal import GOAL

CHILD_SLOTS = {
    'source_evidence_examination': 'biochemical_feasibility_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination',
}
SERVICES = ()

INTEGER = {'type': 'integer', 'minimum': 0}
POSITIVE = {'type': 'integer', 'minimum': 1}
TEXT = {'type': 'string', 'minLength': 1}
ARGUMENT_TRANSPORT_ERROR = 'a110_argument_transport_not_carried'

# The access tools of the old ``_ACCESS_TOOLS`` and the acquisition tools of ``_ACQUISITION_TOOLS`` (public
# literature/NCBI/PMC search and read, then the experimental-database operations), by the library's tool names.
ACCESS_TOOLS = ('state.query', 'source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references',
                'source.experimental.records', 'image.view', 'source.archive.members', 'source.archive.extract',
                'source.xlsx.sheets', 'source.xlsx.rows', 'source.pdf.info', 'source.pdf.text', 'source.pdf.page',
                'execution.estimate')
ACQUISITION_TOOLS = ('public.literature.search', 'public.literature.read', 'public.literature.sequence_identity',
                     'public.ncbi.search', 'public.pmc.versions', 'public.pmc.files', 'public.pmc.asset',
                     *EXPERIMENT_DATABASE_TOOLS)
# python tool name -> the library's tool name (a tool name here is lowercase letters, digits and underscores)
LIBRARY_NAMES = {name.replace('.', '_'): name for name in (*ACCESS_TOOLS, *ACQUISITION_TOOLS)}
# Tools whose source reads are bound to the records this episode holds (the old ``authorization``).
HELD_SOURCE_TOOLS = ('source.locate', 'source.sequence.scan', 'source.sequence.references',
                     'source.experimental.records')

# Descriptions as the A110 tool library's ``ToolRegistry.catalog`` states them (a private copy: the registry
# cannot be built without a Store).
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
# The acquisition tools of the A110 tool library (the same private copy); ``public.ncbi.search`` is restricted to
# pubmed as the old ``catalog`` did. The experimental-database operations are the acquisition library's own catalog.
DESCRIPTIONS.update({
    'public.literature.search':
        'Acquire one literature search page. Read the actual source before extracting biological evidence.',
    'public.literature.read':
        "Acquire an actual open article, an ordered paragraph projection and separate cited-publication metadata. Bibliography identifiers and paragraph links support further source discovery; they do not identify the acquired article or establish a cited experiment's result. Read the retained original XML with source.read representation=original for tables, headings and other omitted elements.",
    'public.literature.sequence_identity':
        'Find publication leads from a supplied protein sequence: retrieve one UniProtKB checksum-search page and verify each complete residue string. Return all equal records on the page, names, organisms, citation counts and explicit continuation. The optional reviewed filter selects database curation status. These are source identities and discovery metadata; experimental evidence requires reading the actual publications.',
    'public.ncbi.search':
        'Search one page of a named NCBI collection for selected references, taxa or sample context.',
    'public.pmc.versions':
        'List one actual public PMC cloud version page. No version is chosen as latest/preferred; source versions can differ in manuscript status and can change in place.',
    'public.pmc.files':
        "Read the selected advertised version's actual file inventory and its listed JSON metadata. Returns reusable listed-object/advertised-asset IDs; optional metadata failure preserves listed files. Choose a version ID, not a URL or guessed filename.",
    'public.pmc.asset':
        'Acquire exactly one selected advertised/listed PMC asset ID. Preserve actual HTTP bytes, original advertisement and checksums; source content is evidence, not target annotation.',
})
EXPERIMENT_DATABASE = experimental_database_catalog()
DESCRIPTIONS.update({name: EXPERIMENT_DATABASE[name]['description'] for name in EXPERIMENT_DATABASE_TOOLS})

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


INPUT_SCHEMAS.update({
    'public.literature.search': obj({'query': TEXT, 'size': POSITIVE, 'cursor': TEXT}, ['query']),
    'public.literature.read': obj({'pmcid': TEXT}),
    'public.literature.sequence_identity': identity_schema(),
    'public.ncbi.search': obj({'database': {'enum': ['pubmed']}, 'term': TEXT, 'size': POSITIVE,
                               'offset': INTEGER}, ['database', 'term']),
    'public.pmc.versions': obj({'pmcid': {'type': 'string', 'pattern': '^PMC[0-9]+$'}, 'continuation_token': TEXT},
                               ['pmcid']),
    'public.pmc.files': obj({'version_ref': REF, 'continuation_token': TEXT}, ['version_ref']),
    'public.pmc.asset': obj({'asset_ref': REF}),
})
INPUT_SCHEMAS.update({name: EXPERIMENT_DATABASE[name]['input_schema'] for name in EXPERIMENT_DATABASE_TOOLS})


POPULATE_NAMES = {'literature_reaction_populate': 'literature.reaction.populate',
                  'literature_reaction_source_populate': 'literature.reaction.source.populate'}

REPRESENTATIONS = ['text', 'original', 'stdout', 'stderr']
REFERENCES = {'type': 'array', 'items': REF, 'uniqueItems': True}
# The old ``_PAGE`` of ``contracts.py`` without its constant ``version`` (``msg_to_child`` adds it).
PAGE = obj({'source_ref': REF, 'representation': {'enum': REPRESENTATIONS}, 'artifact_ref': REF,
            'question_context_refs': REFERENCES, 'prior_delivery_refs': REFERENCES})
CHILD_ARGUMENTS = {'source_evidence_examination': PAGE}
# What the parent says to the model about each child (the old child option information).
CHILD_DESCRIPTIONS = {
    'source_evidence_examination':
        'Commission an examination of one selected source: its representation and artifact, the records that give '
        'the question its context and the records earlier readings delivered. The examiner investigates where and '
        'how that source is to be examined and returns its credit and the controlled features of '
        'the reaction sheets and findings it and its investigations hold.',
}

HISTORY_START = 'On a fresh provider conversation,'
HISTORY_END = 'Do not execute native provider tools.'
HISTORY_GUIDANCE = ('Your own earlier search, acquisition and read outcomes are shown to you as '
                    'own_literature_outcomes; that page creates no new action and does not execute or credit the '
                    'historical work again.\n')
REPORT_START = "A commissioned child returns ONLY the parent's typed form."
REPORT_END = 'A report_delivery_failure is operational feedback'
RETURN_GUIDANCE = ('What returns to your parent is your credit and the features code reads from the reaction sheets '
                   'you and the investigations you commissioned saved and from the typed assessments you hold (cell '
                   'values, statuses and missing reasons, counts, fixed values and record references); no prose is '
                   'returned. Selecting a tool or a child does not end your work: only the numerical controller '
                   'does.\n')
TAIL_GUIDANCE = ('\nYour input list (input_list) is the returned sources not yet examined; a source handed to an '
                 'examination is consumed and no longer offered. Select a source examination as a child when a '
                 'source of the input list may merit one; what it returns '
                 '(its credit and the controlled features of its findings) is shown to you as examinations. Select '
                 'literature_reaction_populate or '
                 'literature_reaction_source_populate when a source you hold supplies the measured ratios, '
                 'predictions or resource quantities of the assigned question.')


def instructions(*, knowledge, family):
    """The old task_instructions.instructions: the default investigation text (the span about the parent-written
    report form, the span about redelivery and the span about the decision-exchange history replaced: those actions
    no longer exist), this episode's goal, the reaction grader of the selected family and the tool-knowledge text
    when it is offered."""
    text = replace_span(DEFAULT_INSTRUCTIONS, REPORT_START, REPORT_END, RETURN_GUIDANCE)
    text = replace_span(text, REPORT_END, HISTORY_START, '')
    text = replace_span(text, HISTORY_START, HISTORY_END, HISTORY_GUIDANCE)
    text += '\n' + GOAL
    text += grader_instructions(family)
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    return text + TAIL_GUIDANCE


def offered(settings):
    """The tools offered now: the access tools (execution_estimate only with timing statistics configured), the
    acquisition tools, then the two reaction graders."""
    tools = [name for name, library in LIBRARY_NAMES.items()
             if name != 'execution_estimate' or settings.get('tool_registry', {}).get('native_statistics') is not None]
    return tools + ['literature_reaction_populate', 'literature_reaction_source_populate']


def catalog(names):
    """The tools the model is shown: name, description and input schema (the old catalog; every input schema is
    projected through source_location_inputs)."""
    entries = []
    for name in names:
        if name == 'literature_reaction_populate':
            entries.append({'name': name, 'description': POPULATE_DESCRIPTION,
                            'input_schema': population_input_schema()})
        elif name == 'literature_reaction_source_populate':
            entries.append({'name': name, 'description': SOURCE_POPULATE_DESCRIPTION,
                            'input_schema': source_population_input_schema()})
        else:
            entries.append({'name': name, 'description': DESCRIPTIONS[LIBRARY_NAMES[name]],
                            'input_schema': source_location_inputs(INPUT_SCHEMAS[LIBRARY_NAMES[name]])})
    return entries


def child_catalog(summary):
    """The children offered now: an examination takes ONE unconsumed item of the input list (``source_ref`` is an enum
    of ``summary['input_list']``, so a consumed search result cannot be selected), and none is offered once the
    list is empty (nano-graphrag ``PageChildProposer``: child options only for unconsumed inputs)."""
    if not summary['input_list']:
        return []
    schema = {**PAGE, 'properties': {**PAGE['properties'], 'source_ref': {'enum': list(summary['input_list'])}}}
    return [{'slot': slot, 'description': CHILD_DESCRIPTIONS[slot], 'input_schema': schema} for slot in CHILD_SLOTS]


def selection_schema(names, summary):
    """What the model answers with: one tool or one child and its arguments (the old action schema)."""
    options = [obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']}, 'arguments': entry['input_schema']})
               for entry in catalog(names)]
    options += [obj({'kind': {'const': 'child'}, 'slot': {'const': entry['slot']},
                     'arguments': entry['input_schema']}) for entry in child_catalog(summary)]
    return obj({'selection': {'anyOf': options}})


def admitted(name, arguments):
    """The old ``_tool_arguments``: the arguments against the offered schema. This assignment has no page, so no
    source boundary applies. A violation is a ``ValidationError`` (the old ``validate_schema`` error)."""
    validate_schema(arguments, source_location_inputs(INPUT_SCHEMAS[name]))


async def run_library_tool(name, envelope, ctx):
    """Execute one access or acquisition tool. A schema violation is returned as an ``invalid`` outcome with
    ``arguments_or_reference`` feedback, as the old ``execute`` did; the outcome is the unit's outcome like any
    other."""
    arguments, scope = envelope['arguments'], envelope['scope']
    try:
        admitted(name, arguments)
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
    return await run_library_tool('state.query', arguments, ctx)

async def source_read(arguments, ctx):
    return await run_library_tool('source.read', arguments, ctx)

async def source_locate(arguments, ctx):
    return await run_library_tool('source.locate', arguments, ctx)

async def source_sequence_scan(arguments, ctx):
    return await run_library_tool('source.sequence.scan', arguments, ctx)

async def source_sequence_references(arguments, ctx):
    return await run_library_tool('source.sequence.references', arguments, ctx)

async def source_experimental_records(arguments, ctx):
    return await run_library_tool('source.experimental.records', arguments, ctx)

async def image_view(arguments, ctx):
    return await run_library_tool('image.view', arguments, ctx)

async def source_archive_members(arguments, ctx):
    return await run_library_tool('source.archive.members', arguments, ctx)

async def source_archive_extract(arguments, ctx):
    return await run_library_tool('source.archive.extract', arguments, ctx)

async def source_xlsx_sheets(arguments, ctx):
    return await run_library_tool('source.xlsx.sheets', arguments, ctx)

async def source_xlsx_rows(arguments, ctx):
    return await run_library_tool('source.xlsx.rows', arguments, ctx)

async def source_pdf_info(arguments, ctx):
    return await run_library_tool('source.pdf.info', arguments, ctx)

async def source_pdf_text(arguments, ctx):
    return await run_library_tool('source.pdf.text', arguments, ctx)

async def source_pdf_page(arguments, ctx):
    return await run_library_tool('source.pdf.page', arguments, ctx)

async def execution_estimate(arguments, ctx):
    return await run_library_tool('execution.estimate', arguments, ctx)

async def public_literature_search(arguments, ctx):
    return await run_library_tool('public.literature.search', arguments, ctx)

async def public_literature_read(arguments, ctx):
    return await run_library_tool('public.literature.read', arguments, ctx)

async def public_literature_sequence_identity(arguments, ctx):
    return await run_library_tool('public.literature.sequence_identity', arguments, ctx)

async def public_ncbi_search(arguments, ctx):
    return await run_library_tool('public.ncbi.search', arguments, ctx)

async def public_pmc_versions(arguments, ctx):
    return await run_library_tool('public.pmc.versions', arguments, ctx)

async def public_pmc_files(arguments, ctx):
    return await run_library_tool('public.pmc.files', arguments, ctx)

async def public_pmc_asset(arguments, ctx):
    return await run_library_tool('public.pmc.asset', arguments, ctx)

async def public_sabiork_search(arguments, ctx):
    return await run_library_tool('public.sabiork.search', arguments, ctx)

async def public_sabiork_read(arguments, ctx):
    return await run_library_tool('public.sabiork.read', arguments, ctx)

async def public_brenda_search(arguments, ctx):
    return await run_library_tool('public.brenda.search', arguments, ctx)

async def public_brenda_read(arguments, ctx):
    return await run_library_tool('public.brenda.read', arguments, ctx)

async def public_bioassay_search(arguments, ctx):
    return await run_library_tool('public.bioassay.search', arguments, ctx)

async def public_bioassay_read(arguments, ctx):
    return await run_library_tool('public.bioassay.read', arguments, ctx)

async def public_chembl_search(arguments, ctx):
    return await run_library_tool('public.chembl.search', arguments, ctx)

async def public_chembl_read(arguments, ctx):
    return await run_library_tool('public.chembl.read', arguments, ctx)

async def public_mavedb_search(arguments, ctx):
    return await run_library_tool('public.mavedb.search', arguments, ctx)

async def public_mavedb_read(arguments, ctx):
    return await run_library_tool('public.mavedb.read', arguments, ctx)

async def public_brenda_graph_search(arguments, ctx):
    return await run_library_tool('public.brenda.graph_search', arguments, ctx)


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


TOOLS = {'state_query': state_query,
         'source_read': source_read,
         'source_locate': source_locate,
         'source_sequence_scan': source_sequence_scan,
         'source_sequence_references': source_sequence_references,
         'source_experimental_records': source_experimental_records,
         'image_view': image_view,
         'source_archive_members': source_archive_members,
         'source_archive_extract': source_archive_extract,
         'source_xlsx_sheets': source_xlsx_sheets,
         'source_xlsx_rows': source_xlsx_rows,
         'source_pdf_info': source_pdf_info,
         'source_pdf_text': source_pdf_text,
         'source_pdf_page': source_pdf_page,
         'execution_estimate': execution_estimate,
         'public_literature_search': public_literature_search,
         'public_literature_read': public_literature_read,
         'public_literature_sequence_identity': public_literature_sequence_identity,
         'public_ncbi_search': public_ncbi_search,
         'public_pmc_versions': public_pmc_versions,
         'public_pmc_files': public_pmc_files,
         'public_pmc_asset': public_pmc_asset,
         'public_sabiork_search': public_sabiork_search,
         'public_sabiork_read': public_sabiork_read,
         'public_brenda_search': public_brenda_search,
         'public_brenda_read': public_brenda_read,
         'public_bioassay_search': public_bioassay_search,
         'public_bioassay_read': public_bioassay_read,
         'public_chembl_search': public_chembl_search,
         'public_chembl_read': public_chembl_read,
         'public_mavedb_search': public_mavedb_search,
         'public_mavedb_read': public_mavedb_read,
         'public_brenda_graph_search': public_brenda_graph_search,
         'literature_reaction_populate': literature_reaction_populate,
         'literature_reaction_source_populate': literature_reaction_source_populate}


def decide(summary, feedback, ctx):
    """Ask the model for the next tool or child, shown the assignment, custody of the sources it hands over, its own
    search and read outcomes, the controlled returns of its examinations, the controlled features of the reaction sheets and of the held
    assessments, the latest image it looked at, the tools and the child, the measured time and the yield table (the old decision state and inputs, over
    this episode's summary)."""
    names = offered(ctx.settings)
    knowledge_directory = ctx.settings.get('knowledge_library_directory')
    context = {'goal': GOAL, 'scope': summary['scope'], 'literature_assignment': summary['literature_assignment'],
               'literature_source_custody': summary['literature_source_custody'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_history_meaning': summary['literature_history_meaning'],
               'literature_experimental_work': summary['literature_experimental_work'],
               'examinations': summary['examinations'],
               'visual_evidence': summary['visual_evidence'], 'last_local_outcome': summary['last_local_outcome'],
               'held_record_refs': summary['held_record_refs'], 'reaction_sheets': summary['reaction_sheets'],
               'investigation_finding': summary['investigation_finding'],
               'input_list': summary['input_list'], 'consumed_input_ids': summary['consumed_input_ids'],
               'tools': catalog(names), 'children': child_catalog(summary),
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['action_yields'],
        'tool_knowledge': None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(knowledge=context.get('tool_knowledge'), family=summary['family']), context,
                        strict_output_schema(selection_schema(names, summary), open_records_as_text=False,
                                             argument_transport_error=ARGUMENT_TRANSPORT_ERROR))


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one commission, or reject it (no unit). An answer that
    selects no offered tool or child, or arguments that do not fit its schema, is invalid. A commission naming a record this episode does not hold, or one the child does not
    admit, is not checked here: it fails with its own error."""
    names = offered(ctx.settings)
    schema = selection_schema(names, summary)
    try:
        decoded = decode_strict_output(response, schema, open_records_as_text=False,
                                       argument_transport_error=ARGUMENT_TRANSPORT_ERROR)
        validate_schema(decoded, schema)
        selection = decoded['selection']
        arguments = selection['arguments']
        if selection['kind'] == 'child':
            return ChildCall(selection['slot'], arguments)
        name = selection['tool']
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    call = {'arguments': arguments, 'scope': summary['scope']}
    if name in POPULATE_NAMES:
        call['page_source_ref'] = None      # this assignment has no page: no page boundary applies
    return ToolCall(name, call)
