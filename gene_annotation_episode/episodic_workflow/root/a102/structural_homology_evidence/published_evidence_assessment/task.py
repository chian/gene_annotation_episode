"""The task: search and read the literature and examine sources through the access tools, commit reasoning (with
the commissioned task's typed answer), grade a deposited structure with ``structure_populate``, or commission a strategy
child to investigate which search approach is productive.

Carried from the old ``task.py``, ``decision_delivery.py``, ``decision_presentation.py``, ``task_instructions.py``,
``child_commissioning.py``, ``source_operations.py``, ``source_interpretation.py``, ``source_references.py`` and
``source_contracts.py`` of ``literature``. One unit is one model-selected tool call or one child commission. The
task always offers a unit and never ends the Episode: only the yield controller does. This episode has the
acquisition tools (literature search and read, NCBI restricted to ``pubmed``, PMC, the experimental databases) and
no page boundary on tool arguments (its assignment has no ``page``)."""
import json

from jsonschema import ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.structural_homology_evidence.experimental_database_acquisition import (
    catalog as experimental_database_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.instructions.structural_homology_evidence.runtime_prompt import (
    INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_task_credit import (
    lead_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.evolutionary_history_evidence.literature_assay_inputs import (
    _Sources)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.structural_homology_evidence.literature_sequence_discovery import (
    identity_schema, references_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_operations.structural_homology_evidence.source_sequences import (
    scan_schema)
from gene_annotation_episode.episodic_workflow.episode_support.readers.structural_homology_evidence.source_locations import (
    locate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import (
    RECORD_SCHEMAS, REF, REFS, identity, obj, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.experimental_database_records import (
    reader_schema as experimental_records_schema)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structural_homology_evidence.tools import (
    ToolRegistry)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.literature_contract_error import (
    ExperimentalContractError)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.structural_homology_evidence.literature_structure_types import (
    EXPERIMENT_TYPES)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.literature_structure_prompt import (
    STRUCTURE_TASK)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.structural_homology_evidence.literature_structure_storage import (
    TOOL_DESCRIPTION as STRUCTURE_TOOL_DESCRIPTION, populate_structure_sheet, population_input_schema)
from .goal import BINDING_PATH, GOAL

CHILD_SLOTS = {'literature_strategy': BINDING_PATH + '/evidence_search_strategy_improvement'}
SERVICES = ()

INTEGER = {'type': 'integer', 'minimum': 0}
POSITIVE = {'type': 'integer', 'minimum': 1}
TEXT = {'type': 'string', 'minLength': 1}
TRANSPORT_ERROR = 'a102_literature_selection_has_no_argument_transport'
EXPERIMENT_DATABASES = experimental_database_catalog()

# The access tools of the old ``_ACCESS_TOOLS`` and the acquisition tools of the old ``_ACQUISITION_TOOLS``;
# descriptions as the tool library states them.
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
        'Inspect one page of a received experimental database response. Return native assay records, source measurement selectors and literal record links. Optional contains and contains_all filter retained rows by one or several literal terms, including their native headers and section labels. Record and whole-page link continuations are separate. These records locate the characterized homolog and its source evidence; metadata and deposited scores retain their native meanings.',
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
        'Obtain recorded duration expectations before a proposed native alignment or workbook selection. Uses the same operands, actual settings and caller resource as execution. Creates no native job or scientific evidence; missing history stays unknown. This is an optional information tool, not a scheduling or continuation decision.',
    'public.literature.search':
        'Acquire one literature search page. Read the actual source before extracting biological evidence.',
    'public.literature.read':
        "Acquire an actual open article, an ordered paragraph projection and separate cited-publication metadata. Bibliography identifiers and paragraph links support further source discovery; they do not identify the acquired article or establish a cited experiment's result. Read the retained original XML with source.read representation=original for tables, headings and other omitted elements.",
    'public.literature.sequence_identity':
        'Find publication leads from a supplied protein sequence: retrieve one UniProtKB checksum-search page and verify each complete residue string. Return all equal records on the page, names, organisms, citation counts and explicit continuation. The optional reviewed filter selects database curation status. These are source identities and discovery metadata; experimental evidence is not established by them.',
    'public.ncbi.search':
        'Search one page of a named NCBI collection for selected references, taxa or sample context. This episode searches pubmed only.',
    'public.pmc.versions':
        'List one actual public PMC cloud version page. No version is chosen as latest/preferred; source versions can differ in manuscript status and can change in place.',
    'public.pmc.files':
        "Read the selected advertised version's actual file inventory and its listed JSON metadata. Returns reusable listed-object/advertised-asset IDs; optional metadata failure preserves listed files. Choose a version ID, not a URL or guessed filename.",
    'public.pmc.asset':
        'Acquire exactly one selected advertised/listed PMC asset ID. Preserve actual HTTP bytes, original advertisement and checksums; source content is evidence, not target annotation.',
    **{name: entry['description'] for name, entry in EXPERIMENT_DATABASES.items()},
}

# python tool name -> the library's tool name (a tool name here is lowercase letters, digits and underscores)
ACCESS_NAMES = ('state.query', 'source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references',
                'source.experimental.records', 'image.view', 'source.archive.members', 'source.archive.extract',
                'source.xlsx.sheets', 'source.xlsx.rows', 'source.pdf.info', 'source.pdf.text', 'source.pdf.page',
                'execution.estimate')
ACQUISITION_NAMES = ('public.literature.search', 'public.literature.read', 'public.literature.sequence_identity',
                     'public.ncbi.search', 'public.pmc.versions', 'public.pmc.files', 'public.pmc.asset',
                     *EXPERIMENT_DATABASES)
LIBRARY_NAMES = {name.replace('.', '_'): name for name in (*ACCESS_NAMES, *ACQUISITION_NAMES)}
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
    'public.literature.search': obj({'query': TEXT, 'size': POSITIVE, 'cursor': TEXT}, ['query']),
    'public.literature.read': obj({'pmcid': TEXT}),
    'public.literature.sequence_identity': identity_schema(),
    # The old catalog restricted this operation's database to pubmed.
    'public.ncbi.search': obj({'database': {'enum': ['pubmed']}, 'term': TEXT, 'size': POSITIVE,
                               'offset': INTEGER}, ['database', 'term']),
    'public.pmc.versions': obj({'pmcid': {'type': 'string', 'pattern': '^PMC[0-9]+$'}, 'continuation_token': TEXT},
                               ['pmcid']),
    'public.pmc.files': obj({'version_ref': REF, 'continuation_token': TEXT}, ['version_ref']),
    'public.pmc.asset': obj({'asset_ref': REF}),
    **{name: entry['input_schema'] for name, entry in EXPERIMENT_DATABASES.items()},
}
# ``execution.estimate`` is offered for the workbook tools only, and only when the run has timing statistics.
INPUT_SCHEMAS['execution.estimate'] = {'anyOf': [
    obj({'tool': {'const': name}, 'arguments': INPUT_SCHEMAS[name]}) for name in ('source.xlsx.sheets', 'source.xlsx.rows')]}


# The empty-commit rule of the old ``task.py apply_response`` (``empty_reasoning_commit``) and the evidence
# processing a screening answer rests on.
NO_APPLICABLE_EVIDENCE = 'no_applicable_evidence'
EVIDENCE_PROCESSING = obj({
    'kind': {'const': NO_APPLICABLE_EVIDENCE},
    'reason': TEXT,
    'examined': {'type': 'array', 'minItems': 1, 'items': obj({
        'source_ref': REF, 'representation': {'enum': ['original', 'text']},
        'start': INTEGER, 'end': POSITIVE})}})

REASON_DESCRIPTION = ('Commit one typed scientific reasoning payload about the examined sources, using the '
                      'common reasoning commit schema. A payload with every section empty is rejected before '
                      'it runs and creates no unit. For a verified_source_leads task the commit carries the '
                      'source_lead the commissioned question asks for. For a screening answer, '
                      'evidence_processing no_applicable_evidence declares, with its reason and the exact '
                      'examined byte spans, that the examined passages contain no applicable evidence; '
                      'missing access is not absence.')
CHILD_DESCRIPTIONS = {
    'literature_strategy': ('Commission an investigation of which search approach is productive for the assigned '
                            'question: its strategy names the records giving the question context and the prior '
                            'search sources (sources this episode holds) it starts from. The child can search and '
                            'read itself or commission an assessment of which returned sources merit examination. '
                            'The prior search sources are chosen only among input_list (the held sources not yet '
                            'handed to a strategy child); a source handed to a child is consumed and no longer '
                            'offered, and no strategy child is offered when input_list is empty.'),
}
REFERENCES = {'type': 'array', 'items': REF, 'uniqueItems': True}


def child_arguments(slot, summary):
    """The arguments a child takes now: the prior search sources are chosen among the input list only (the held
    sources no strategy child has been handed); a handed-out source is consumed and offered no more."""
    if slot != 'literature_strategy':
        raise KeyError(slot)
    strategy = obj({'question_context_refs': REFERENCES,
                    'prior_search_refs': {'type': 'array', 'items': {'enum': list(summary['input_list'])},
                                          'uniqueItems': True, 'minItems': 1,
                                          'description': 'Unconsumed sources of input_list only'}})
    return obj({'strategy': strategy})


def available_slots(summary):
    """The child slots valid now: the strategy child while the input list is not empty."""
    return [slot for slot in CHILD_SLOTS if summary['input_list']]

HISTORY_START = 'On a fresh provider conversation,'
HISTORY_END = 'Do not execute native provider tools.'
HISTORY_GUIDANCE = ('Your own earlier acquisition and read outcomes are shown to you as own_literature_outcomes; '
                    'that page creates no new action and does not execute or credit the historical work again.\n')
REPORT_START = "A commissioned child returns ONLY the parent's typed form."
REPORT_END = 'A report_delivery_failure is operational feedback'
RETURN_GUIDANCE = ('What returns to your parent is your credit and the features code reads from the structure '
                   'sheets you saved with structure_populate and the sheets your children returned (bounds, status '
                   'and reason of each cell, the panel sizes, the validation binding); each sheet stays its own '
                   'entry and no prose is returned. A commissioned child returns its credit, its sheets and the '
                   'typed answers the commission selects; they are shown to you as child_reports. Selecting a tool '
                   'or a child does not end your work: only the numerical controller does. Later tool outcomes are '
                   'facts, not a new judgment.\n')
TAIL_GUIDANCE = ('\nSelect structure_populate when a held source supplies the coordinates and the fixed feature '
                 'panel of the assigned question.')

# The A102 literature grader (``structural_feature_geometry``, sheet ``literature_structure_cells``): the owner's
# question, what the grading keeps apart, its cells and their combination, and the recurring structural questions
# of ``STRUCTURE_TASK``; part of the instructions of every decision.
GRADER = EXPERIMENT_TYPES['structural_feature_geometry']
STRUCTURE_SECTION = ('\nLiterature structure grading (tool structure_populate, grader structural_feature_geometry, '
                     'sheet literature_structure_cells). Question: ' + GRADER['question'] + ' Keep apart: '
                     + '; '.join(GRADER['considerations']) + '. Cells: ' + ', '.join(GRADER['components'])
                     + '. Combination: ' + GRADER['combination'] + '\n' + STRUCTURE_TASK + '\n')


def instructions(*, knowledge):
    """The old ``task_instructions.compose_instructions``: the A102 investigation text (with the span about the
    parent-written report form, the span about redelivery and the span about the decision-exchange history
    replaced: those actions no longer exist), this episode's goal, the reasoning-commit requirement, and the
    tool-knowledge text when it is offered. The pending-delivery paragraph, the wait paragraphs and the
    native-event paragraph are not carried: there is no such action. The launch-instruction library is not
    offered by this episode."""
    text = replace_span(INSTRUCTIONS, REPORT_START, REPORT_END, RETURN_GUIDANCE)
    text = replace_span(text, REPORT_END, HISTORY_START, '')
    text = replace_span(text, HISTORY_START, HISTORY_END, HISTORY_GUIDANCE)
    text += '\n' + GOAL
    text += '\n' + REASONING_COMMIT_REQUIREMENT
    text += STRUCTURE_SECTION
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    return text + TAIL_GUIDANCE


def offered(settings):
    """The tools offered now: ``execution_estimate`` only with timing statistics configured."""
    names = [name for name in LIBRARY_NAMES
             if name != 'execution_estimate' or settings.get('tool_registry', {}).get('native_statistics') is not None]
    names += ['structure_populate', 'reason']
    return names


def reason_schema(summary):
    """The reason tool's arguments: the common commit, plus the commissioned task's own typed content (the old
    ``reasoning_action_schema``: a ``source_lead`` for ``verified_source_leads``)."""
    properties = {'commit': summary['reasoning_schema']}
    required = ['commit']
    task = summary['task']
    if task['kind'] == 'verified_source_leads':
        properties['source_lead'] = lead_schema()
        required.append('source_lead')
    elif task['kind'] == 'source_answer' and task['answer_kind'] == 'screening':
        properties['evidence_processing'] = EVIDENCE_PROCESSING
    return source_location_inputs(obj(properties, required))


def catalog(names, summary):
    """The tools the model is shown: name, description and input schema (the old ``catalog``; every input schema
    is projected through ``source_location_inputs``)."""
    entries = []
    for name in names:
        if name == 'structure_populate':
            entries.append({'name': name, 'description': STRUCTURE_TOOL_DESCRIPTION,
                            'input_schema': population_input_schema()})
        elif name == 'reason':
            entries.append({'name': name, 'description': REASON_DESCRIPTION, 'input_schema': reason_schema(summary)})
        else:
            entries.append({'name': name, 'description': DESCRIPTIONS[LIBRARY_NAMES[name]],
                            'input_schema': source_location_inputs(INPUT_SCHEMAS[LIBRARY_NAMES[name]])})
    return entries


def selection_schema(names, summary):
    """What the model answers with: one tool and its arguments, or one child and its strategy (the old action
    schema: kinds ``tool`` and ``child``)."""
    tools = [obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']}, 'arguments': entry['input_schema']})
             for entry in catalog(names, summary)]
    children = [obj({'kind': {'const': 'child'}, 'slot': {'const': slot}, 'arguments': child_arguments(slot, summary)})
                for slot in available_slots(summary)]
    return obj({'selection': {'anyOf': tools + children}})


def artifact_of(source, representation):
    """The old ``_artifact``: the artifact of the source's representation."""
    if representation == 'original':
        return source['artifact_ref']
    if representation == 'text':
        return source.get('text_ref') or source['artifact_ref']
    return source.get(representation + '_ref')


def checked_strategy(strategy, records, summary):
    """The commission the model chose, over the held records: every prior search source is a source this episode
    holds and every question-context record is held. A violation is a wrong commission: it raises and fails the
    run (no rejection, no feedback)."""
    for reference in strategy['prior_search_refs']:
        if reference not in summary['input_list']:
            raise ContractError('literature_reference_unavailable', detail={'reference': reference,
                                                                            'namespace': 'input_list'})
        if not records.holds(reference) or records.get(reference).get('record_type') != 'source':
            raise ContractError('literature_reference_unavailable', detail={'reference': reference,
                                                                            'namespace': 'source'})
    for reference in strategy['question_context_refs']:
        if not records.holds(reference):
            raise ContractError('literature_reference_unavailable', detail={'reference': reference})


def invalid(operation_ref, error):
    detail = {'detail': error.detail} if getattr(error, 'detail', None) else {}
    return {'status': 'invalid', 'operation_ref': operation_ref, 'record_refs': [], 'changed_record_refs': [],
            'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error), **detail}}


async def run_tool(name, envelope, ctx):
    """Execute one access or acquisition tool. A contract error is returned as an ``invalid`` outcome with
    ``arguments_or_reference`` feedback, as the old ``execute`` did; the outcome is the unit's outcome like any
    other. This assignment has no page, so there is no boundary on the sources the arguments name."""
    arguments, scope = envelope['arguments'], envelope['scope']
    try:
        validate_schema(arguments, source_location_inputs(INPUT_SCHEMAS[name]))
    except (ContractError, ValidationError) as error:
        return invalid(identity('operation', {'key': ctx.operation_key, 'name': name, 'arguments': arguments}), error)
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
    return await run_tool(LIBRARY_NAMES['state_query'], arguments, ctx)


async def source_read(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['source_read'], arguments, ctx)


async def source_locate(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['source_locate'], arguments, ctx)


async def source_sequence_scan(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['source_sequence_scan'], arguments, ctx)


async def source_sequence_references(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['source_sequence_references'], arguments, ctx)


async def source_experimental_records(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['source_experimental_records'], arguments, ctx)


async def image_view(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['image_view'], arguments, ctx)


async def source_archive_members(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['source_archive_members'], arguments, ctx)


async def source_archive_extract(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['source_archive_extract'], arguments, ctx)


async def source_xlsx_sheets(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['source_xlsx_sheets'], arguments, ctx)


async def source_xlsx_rows(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['source_xlsx_rows'], arguments, ctx)


async def source_pdf_info(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['source_pdf_info'], arguments, ctx)


async def source_pdf_text(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['source_pdf_text'], arguments, ctx)


async def source_pdf_page(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['source_pdf_page'], arguments, ctx)


async def execution_estimate(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['execution_estimate'], arguments, ctx)


async def public_literature_search(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['public_literature_search'], arguments, ctx)


async def public_literature_read(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['public_literature_read'], arguments, ctx)


async def public_literature_sequence_identity(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['public_literature_sequence_identity'], arguments, ctx)


async def public_ncbi_search(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['public_ncbi_search'], arguments, ctx)


async def public_pmc_versions(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['public_pmc_versions'], arguments, ctx)


async def public_pmc_files(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['public_pmc_files'], arguments, ctx)


async def public_pmc_asset(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['public_pmc_asset'], arguments, ctx)


async def public_sabiork_search(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['public_sabiork_search'], arguments, ctx)


async def public_sabiork_read(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['public_sabiork_read'], arguments, ctx)


async def public_brenda_search(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['public_brenda_search'], arguments, ctx)


async def public_brenda_read(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['public_brenda_read'], arguments, ctx)


async def public_brenda_graph_search(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['public_brenda_graph_search'], arguments, ctx)


async def public_bioassay_search(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['public_bioassay_search'], arguments, ctx)


async def public_bioassay_read(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['public_bioassay_read'], arguments, ctx)


async def public_chembl_search(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['public_chembl_search'], arguments, ctx)


async def public_chembl_read(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['public_chembl_read'], arguments, ctx)


async def public_mavedb_search(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['public_mavedb_search'], arguments, ctx)


async def public_mavedb_read(arguments, ctx):
    return await run_tool(LIBRARY_NAMES['public_mavedb_read'], arguments, ctx)


def _plain(value):
    return json.loads(json.dumps(value, allow_nan=False))


def _resolve(value, aliases, reference_position=False):
    """Resolve original-action aliases in source-lead reference positions (the library's private ``_resolve``)."""
    if reference_position and isinstance(value, str) and value.startswith('@'):
        if value[1:] not in aliases:
            raise ContractError('required_grading_unresolved_alias', detail={'reference': value})
        return aliases[value[1:]]
    if isinstance(value, dict):
        return {key: _resolve(child, aliases, key in ('ref', 'dependencies') or key.endswith('_ref')
                              or key.endswith('_refs')) for key, child in value.items()}
    if isinstance(value, list):
        return [_resolve(child, aliases, reference_position) for child in value]
    return value


def validate_source_lead(store, proposed, lead, outcome):
    """The old ``validate_lead`` (library: ``literature_task_credit.validate_lead``, which takes the old binding
    context): the lead's identity and exact source witness, over the held records. Library candidate."""
    value = _resolve(_plain(lead), outcome.get('aliases', {}))
    validate_schema(value, source_location_inputs(lead_schema()))
    if value['proposed_annotation_ref'] != proposed or value['witness']['source_ref'] != value['source_ref']:
        raise ContractError('literature_lead_question_or_source_mismatch')
    if not value['relevance_rationale'].strip():
        raise ContractError('literature_lead_relevance_rationale_required')
    if not all(store.holds(ref) for ref in (value['source_ref'], value['subject_ref'], proposed)):
        raise ContractError('literature_lead_original_inputs_not_received')
    source = store.require(value['source_ref'], {'source'})
    subject = store.require(value['subject_ref'], {'reference'})
    if subject['source_ref'] != value['source_ref'] or not subject.get('anchor'):
        raise ContractError('literature_lead_subject_not_anchored_in_source')
    uri = (source.get('uri') or '').split('?', 1)[0].rstrip('/')
    if uri.endswith(('/search', '/esearch.fcgi')):
        raise ContractError('literature_lead_requires_acquired_source_not_search_page')

    def read_source(ref, representation):
        if ref != value['source_ref']:
            raise ContractError('literature_lead_source_mismatch')
        artifact = source.get('artifact_ref' if representation == 'original' else 'text_ref')
        if artifact is None:
            raise ContractError('literature_lead_source_representation_unavailable')
        return {'artifact_ref': artifact, 'content': store.get_artifact(artifact)}
    witness = _Sources(read_source).witness(value['witness'], 'source_lead.witness')
    anchor = subject['anchor']
    if anchor['artifact_ref'] != witness['artifact_ref'] or not witness['start'] <= anchor['start'] < anchor['end'] <= witness['end']:
        raise ContractError('literature_lead_subject_outside_witness')
    return {**value, 'witness': {**value['witness'], 'quote': witness['quote']}}


def examined_spans(store, processing):
    """The spans a ``no_applicable_evidence`` declaration examined, with the artifact of the representation read
    (the old ``screening_answers`` read each source's artifact the same way)."""
    spans = []
    for witness in processing['examined']:
        validate_schema({'source_ref': witness['source_ref'], 'representation': witness['representation'],
                         'offset': witness['start'], 'limit': witness['end'] - witness['start']},
                        source_location_inputs(INPUT_SCHEMAS['source.read']))
        source = store.get(witness['source_ref'])
        spans.append({**witness, 'artifact_ref': source.get('artifact_ref' if witness['representation'] == 'original'
                                                            else 'text_ref')})
    return spans


def reason(arguments, ctx):
    """One typed reasoning commit (the old ``reason`` action and ``execute_reasoning``). The commit, the lead
    validation and the evidence processing are one transaction: an invalid lead leaves nothing. An invalid
    request is returned as an ``invalid`` outcome that enters the iterator, as the old ``execute`` did."""
    store, scope = ctx.store, arguments['scope']
    lead, processing = arguments.get('source_lead'), arguments.get('evidence_processing')
    try:
        if lead is not None:      # the old ``_tool_arguments(context, 'source.read', witness window)``
            witness = lead['witness']
            validate_schema({'source_ref': witness['source_ref'], 'representation': witness['representation'],
                             'offset': witness['start'], 'limit': witness['end'] - witness['start']},
                            source_location_inputs(INPUT_SCHEMAS['source.read']))
        with store.transaction():
            result = store.commit_reasoning(arguments['commit'], scope, ctx.operation_key)
            if result['status'] not in ('completed', 'partial'):
                return result
            outcome = dict(result)
            if lead is not None:
                outcome['literature_source_lead'] = validate_source_lead(store, arguments['proposed_annotation_ref'],
                                                                         lead, result)
            if processing is not None:
                outcome['evidence_processing'] = {**processing, 'examined': examined_spans(store, processing)}
            return outcome
    except (ContractError, ValidationError) as error:
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'source_lead' if lead is not None else 'arguments_or_reference',
                             'code': getattr(error, 'code', str(error))}}


def structure_populate(arguments, ctx):
    """``literature.structure.populate``: read the selected coordinates, validation and literal witnesses of held
    sources (this episode reads no assigned page), calculate the six source-geometry cells and save the sheet, its
    cell rows, its revision family and its experiment assessment through ``ctx.store``. Arguments the library
    refuses are returned as an ``invalid`` outcome with their code, as the old ``execute`` did; the outcome enters
    the iterator like any other."""
    try:
        return populate_structure_sheet(ctx.store, arguments['scope'], None, arguments['arguments'],
                                        ctx.operation_key)
    except (ContractError, ExperimentalContractError) as error:
        return invalid(identity('operation', {'key': ctx.operation_key, 'name': 'literature.structure.populate',
                                              'arguments': arguments['arguments']}), error)


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
         'public_brenda_graph_search': public_brenda_graph_search,
         'public_bioassay_search': public_bioassay_search,
         'public_bioassay_read': public_bioassay_read,
         'public_chembl_search': public_chembl_search,
         'public_chembl_read': public_chembl_read,
         'public_mavedb_search': public_mavedb_search,
         'public_mavedb_read': public_mavedb_read,
         'structure_populate': structure_populate, 'reason': reason}


def generation_schema(schema):
    return strict_output_schema(schema, open_records_as_text=False, argument_transport_error=TRANSPORT_ERROR)


def decode_response(value, schema):
    return decode_strict_output(value, schema, open_records_as_text=False, argument_transport_error=TRANSPORT_ERROR)


def decide(summary, feedback, ctx):
    """Ask the model for the next tool or child, shown the assignment, the custody of the sources, its own
    acquisition and read outcomes, the children's reports, the structure sheets (own and returned), the tools and children, the
    measured time, the credit definition and the yield table (the old decision state and inputs, over this
    episode's summary)."""
    names = offered(ctx.settings)
    knowledge_directory = ctx.settings.get('knowledge_library_directory')
    context = {'goal': GOAL, 'scope': summary['scope'], 'literature_assignment': summary['literature_assignment'],
               'input_list': summary['input_list'], 'consumed_source_refs': summary['consumed_source_refs'],
               'literature_source_custody': summary['literature_source_custody'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_history_meaning': summary['literature_history_meaning'],
               'child_reports': summary['child_reports'],
               'children': [{'slot': slot, 'description': CHILD_DESCRIPTIONS[slot]}
                            for slot in available_slots(summary)],
               'credit_binding': summary['credit_binding'],
               'structure_sheets': summary['structure_sheets'],
               'tools': catalog(names, summary), 'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['action_yields'],
        'tool_knowledge': None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(knowledge=context.get('tool_knowledge')), context,
                        generation_schema(selection_schema(names, summary)))


def empty_commit(commit, schema, processing):
    """The old test of ``apply_response``: every section of the commit is empty and the answer is not the
    ``no_applicable_evidence`` declaration."""
    required = set(schema.get('required', schema['properties']))
    return (required <= set(commit) <= set(schema['properties']) and all(value == [] for value in commit.values())
            and (processing or {}).get('kind') != NO_APPLICABLE_EVIDENCE)


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one child commission, or reject it (no unit). An answer that
    selects no offered tool or child, arguments that do not fit its schema, an empty reasoning commit without task
    content is invalid. A child commission that names a
    source or record this episode does not hold is a wrong commission: it raises and fails the run."""
    names = offered(ctx.settings)
    schema = selection_schema(names, summary)
    try:
        value = decode_response(response, schema)
        validate_schema(value, schema)
        selection = value['selection']
        arguments = selection['arguments']
        if selection['kind'] == 'child':
            commission = ChildCall(selection['slot'], arguments)
        else:
            commission = None
            name = selection['tool']
        if commission is not None:
            pass
        elif name == 'reason':
            if 'source_lead' not in arguments and empty_commit(arguments['commit'], summary['reasoning_schema'],
                                                               arguments.get('evidence_processing')):
                raise ValueError('empty_reasoning_commit')
            return ToolCall(name, {**arguments, 'scope': summary['scope'],
                                   'proposed_annotation_ref': summary['proposed_annotation_ref']})
    except (ValueError, KeyError, TypeError, ValidationError, ContractError) as error:
        raise Rejected(rejection_feedback(error, category='selection'))
    if commission is not None:
        checked_strategy(commission.arguments['strategy'], records, summary)
        return commission
    return ToolCall(name, {'arguments': arguments, 'scope': summary['scope']})
