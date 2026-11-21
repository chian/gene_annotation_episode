"""The task: acquire and read sources through the acquisition and access tools, or commission the relevance assessment
of returned sources by the search child, commit reasoning on what they say together with its
contextual grading sheets (and, for a verified-source-leads commission, validated source leads), populate the A108
sheets. There is no report tool: the return is the controlled features code reads from the saved sheets.

Carried from the old task.py, task_decision.py, task_instructions.py, source_operations.py, source_references.py,
source_contracts.py, scientific_records.py, scoring/contextual_main_sheet.py and grading/contextual_*.py of
``literature_strategy`` at 97308b94c (the old child role ``literature_search`` is the slot below). One unit is one
model-selected tool call or one child commission. The task always offers a unit and never ends the Episode: only the
yield controller does. The old permitted actions ``wait`` (``waiting.supports_wait`` was False) and
``redeliver_report`` do not exist. This episode has no assigned page, so the old page restriction of
``_tool_arguments`` (reads and population sources inside the page's source tree) does not apply.

A108 reasoning is the required-grading action of ``literature_required_grading``: the interpretation and the purpose-
specific contextual grader selected for it are committed in one tool call and the interpretation is refused unless its
subscoring sheet is saved (AGENTS.md, "Required literature evidence processing"). Only a source-grounded
``no_applicable_evidence`` declaration omits grading. The two population tools of the old catalogue
(``literature.a108_grading.populate`` and ``literature.a108.aggregate``) stay tools. The sheet repositories and the
required-grading logic work on the custody-scoped store.

Settings read (``ctx.settings``): ``tool_registry`` (the JSON keyword arguments of the library ``ToolRegistry``; its
``PublicClients`` are the declared service ``public_clients``) and ``knowledge_library_directory`` (optional). ``cost`` and ``parameters``
are read by ``yield_estimator.py``."""
from dataclasses import dataclass

from jsonschema import ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.forms.sample_context_evidence.communication import (
    plain)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.sample_context_evidence.literature_experimental_contracts import (
    ExperimentalContractError)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.sample_context_evidence.literature_population_catalog import (
    population_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.sample_context_evidence.literature_required_grading import (
    action_schema as required_grading_schema, execute as execute_required_grading)
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.literature_grading_inputs import (
    grading_population_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.sample_context_evidence.literature_assay_inputs import (
    _Sources, _witness_schema, materialize_text_witness_inputs)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.sample_context_evidence.literature_investigation_prompt import (
    INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_sequence_discovery import (
    identity_schema, references_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_grading_storage import (
    LiteratureA108GradingRepository)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.sample_context_evidence.literature_aggregation_storage import (
    LiteratureA108AggregationRepository)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.sample_context_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sample_context_evidence.source_locations import (
    locate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import (
    ContractError, RECORD_SCHEMAS, REF, REFS, identity, obj, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.tools.sample_context_evidence.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

from .goal import GOAL

# The one child (the old ``_CHILDREN['literature_strategy']``: literature_search), by slot.
CHILD_SLOTS = {
    'source_relevance_assessment': 'sample_context_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment',
}
SERVICES = ('public_clients',)

INTEGER = {'type': 'integer', 'minimum': 0}
POSITIVE = {'type': 'integer', 'minimum': 1}
TEXT = {'type': 'string', 'minLength': 1}

# The access tools of the old ``_A108_ACCESS_TOOLS`` that the A108 tool library implements (the old catalogue
# skipped a name the library does not offer: ``material.annotations``, ``material.parse`` and ``material.from_source``
# are not in it); descriptions as the tool library states them.
DESCRIPTIONS = {
    'state.query':
        'Read an exact page of typed scientific records, current revisions, or records referring to actual references. Follow the returned next_query for the same selection and order. Exact refs is a separate mode and cannot be combined with page selectors.',
    'source.read':
        'Read a bounded UTF-8 byte window from an actual source. Choose original for retained source bytes, including XML tables/headings omitted by a paragraph projection; text selects that projection when available. Explicit stdout/stderr select retained native stream bytes when present, without falling back to another representation. Returned artifact/offsets support exact anchors.',
    'source.locate':
        'Locate an exact supplied literal quote in an explicitly received original or text source representation. Return UTF-8 byte witnesses, unchanged neighboring context and bounded match continuation. Multiple occurrences remain separate. No normalization, scientific interpretation, measurement parsing or evidence credit is performed; no literal match means only no match in the examined bytes.',
    'source.sequence.references':
        'Read a page of publication identifiers, titles and reported citation scopes from a received sequence-identity response. Reverify full sequence equality for the selected record. Citation metadata supplies leads; it does not establish experimental results.',
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
    'public.literature.search':
        'Acquire one literature search page. Read the actual source before extracting biological evidence.',
    'public.literature.read':
        'Acquire an actual open article, an ordered paragraph projection and separate cited-publication metadata. Bibliography identifiers and paragraph links support further source discovery; they do not identify the acquired article or establish a cited experiment\'s result. Read the retained original XML with source.read representation=original for tables, headings and other omitted elements.',
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
    'public.taxonomy':
        "Retrieve a taxon's source lineage record; it does not assign that taxon to the target.",
    'public.ncbi.sequence':
        'Acquire an external GenBank/GenPept sequence and its original feature context; optional nucleotide interval uses zero-based half-open coordinates.',
    'execution.estimate':
        'Obtain recorded duration expectations before a proposed workbook selection. Uses the same operands, actual settings and caller resource as execution. Creates no native job or scientific evidence; missing history stays unknown. This is an optional information tool, not a scheduling or continuation decision.',
}

# python tool name -> the library's tool name (a tool name here is lowercase letters, digits and underscores)
LIBRARY_NAMES = {
    'state_query': 'state.query', 'source_read': 'source.read', 'source_locate': 'source.locate',
    'source_sequence_references': 'source.sequence.references', 'image_view': 'image.view',
    'source_archive_members': 'source.archive.members', 'source_archive_extract': 'source.archive.extract',
    'source_xlsx_sheets': 'source.xlsx.sheets', 'source_xlsx_rows': 'source.xlsx.rows',
    'source_pdf_info': 'source.pdf.info', 'source_pdf_text': 'source.pdf.text', 'source_pdf_page': 'source.pdf.page',
    'public_literature_search': 'public.literature.search', 'public_literature_read': 'public.literature.read',
    'public_literature_sequence_identity': 'public.literature.sequence_identity',
    'public_ncbi_search': 'public.ncbi.search', 'public_pmc_versions': 'public.pmc.versions',
    'public_pmc_files': 'public.pmc.files', 'public_pmc_asset': 'public.pmc.asset',
    'public_taxonomy': 'public.taxonomy', 'public_ncbi_sequence': 'public.ncbi.sequence',
    'execution_estimate': 'execution.estimate'}
# The two population operations of the old catalogue (``population_catalog``), by tool name.
POPULATION_NAMES = {'literature_a108_grading_populate': 'literature.a108_grading.populate',
                    'literature_a108_aggregate': 'literature.a108.aggregate'}
# Tools whose source reads are bound to the records this episode holds (the old ``authorization``).
HELD_SOURCE_TOOLS = ('source.locate', 'source.sequence.references')

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
    'source.sequence.references': references_schema(),
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
    # the old catalogue restricted the database of public.ncbi.search to this set
    'public.ncbi.search': obj({'database': {'enum': ['pubmed', 'protein', 'nuccore', 'taxonomy', 'biosample',
                                                     'bioproject']},
                               'term': TEXT, 'size': POSITIVE, 'offset': INTEGER}, ['database', 'term']),
    'public.pmc.versions': obj({'pmcid': {'type': 'string', 'pattern': '^PMC[0-9]+$'}, 'continuation_token': TEXT},
                               ['pmcid']),
    'public.pmc.files': obj({'version_ref': REF, 'continuation_token': TEXT}, ['version_ref']),
    'public.pmc.asset': obj({'asset_ref': REF}),
    'public.taxonomy': obj({'taxon_id': POSITIVE}),
    'public.ncbi.sequence': obj({'accession': TEXT, 'database': {'enum': ['protein', 'nuccore']},
                                 'start': INTEGER, 'end': POSITIVE}, ['accession', 'database']),
}
# ``execution.estimate`` is offered for the workbook tools only, and only when the run has timing statistics.
INPUT_SCHEMAS['execution.estimate'] = {'anyOf': [
    obj({'tool': {'const': name}, 'arguments': INPUT_SCHEMAS[name]}) for name in ('source.xlsx.sheets', 'source.xlsx.rows')]}

# What the one child takes as the model's selection: the returned sources whose relevance is assessed and the records
# giving the question its context (the old child assignment's ``search_result_refs`` and ``question_context_refs``;
# its version is fixed by ``msg_to_child``).
CONTEXT_REFS = {'type': 'array', 'items': REF, 'uniqueItems': True}


def child_arguments(input_list):
    """The child commission's arguments (nano-graphrag input list): ``search_result_refs`` names sources of the
    input list only, so a source already handed to the child (consumed) cannot be selected."""
    sources = {'type': 'array', 'items': {**REF, 'enum': list(input_list)}, 'minItems': 1, 'uniqueItems': True}
    return obj({'objective': TEXT, 'search_result_refs': sources, 'question_context_refs': CONTEXT_REFS})


CHILD_DESCRIPTIONS = {
    'source_relevance_assessment': 'Commission an investigation of which of the returned sources merit examination '
                                   'for the assigned question. search_result_refs names UNCONSUMED sources of the '
                                   'input list (search results you hold that no earlier commission took); a source '
                                   'handed out is consumed and not offered again. question_context_refs names the '
                                   'records giving the question its context.',
}

REASON_DESCRIPTION = ('Commit a typed scientific reasoning over the selected table or sheet and the records you hold: '
                      'extracted terms, source subjects, contexts, observations, hypotheses and assessments, each '
                      'with its exact source anchor, together with the contextual grader selected for the '
                      'interpretation (evidence_processing) in this one call. An interpretation is not saved '
                      'without its subscoring sheet; only a source-grounded finding that the examined material has '
                      'no applicable contextual observation omits grading. A commit with every section empty is '
                      'rejected.')
HISTORY_START = 'On a fresh provider conversation,'
HISTORY_END = 'Do not execute native provider tools.'
HISTORY_GUIDANCE = ('Your own earlier acquisition and read outcomes are shown to you as own_literature_outcomes; that page creates '
                    'no new action and does not execute or credit the historical work again.\n')
RETURN_GUIDANCE = ('\nWhat returns to your parent is your credit and the counts code reads from the A108 sheets you and your '
                   'children saved, with their references; nothing you write in prose is returned. Selecting a tool '
                   'never ends your work: only the numerical controller does.')
LEAD_GUIDANCE = ('\nFor a verified_source_leads commission, a reason selection also carries source_lead: the '
                 'inspected source, its anchored reference subject, whether it is a useful lead for the original '
                 'question and the exact witnessed byte interval. A search hit or title alone verifies nothing.')


@dataclass(frozen=True)
class LiteratureContext:
    """The old episode context the A108 sheet repositories and the required-grading logic read: one literature
    episode's identity, commission and the records it holds (private copy; library candidate)."""
    run_id: str
    episode_id: str
    role: str
    path: tuple
    scope: dict
    assignment: dict
    request: dict
    received_record_refs: tuple


def instructions(*, knowledge, leads):
    """The old task_instructions.instructions: the investigation text, this episode's goal, the reasoning-commit
    requirement, the tool-knowledge text when it is offered. The decision-exchange paragraph, the pending-delivery
    paragraph, the wait paragraphs and the redeliver_report text are not carried: no such action exists."""
    text = replace_span(INSTRUCTIONS, HISTORY_START, HISTORY_END, HISTORY_GUIDANCE)
    text += '\n' + GOAL
    text += '\n' + REASONING_COMMIT_REQUIREMENT
    text += GRADING_INSTRUCTIONS
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if leads:
        text += LEAD_GUIDANCE
    return text + RETURN_GUIDANCE


def offered(settings, input_list):
    """The tools offered now: the access tools (``execution_estimate`` only with timing statistics configured), the
    two population operations, the reasoning commit and, while the input list holds an unconsumed source, the child
    commission."""
    access = [name for name in LIBRARY_NAMES
              if name != 'execution_estimate' or 'native_statistics' in settings['tool_registry']]
    return access + list(POPULATION_NAMES) + ['reason', *(CHILD_SLOTS if input_list else ())]


def lead_schema():
    """The old credit.py ``lead_schema``: the source lead a verified_source_leads reasoning also carries."""
    return obj({'proposed_annotation_ref': {**REF, 'x-reference-namespace': 'hypothesis'},
                'source_ref': {**REF, 'x-reference-namespace': 'source'},
                'subject_ref': {**REF, 'x-reference-namespace': 'reference'},
                'disposition': {'enum': ['relevant', 'not_relevant'],
                                'description': 'Whether the inspected source is a useful lead for this commissioned '
                                               'question. This is not evidence supporting or opposing the proposed '
                                               'annotation.'},
                'relevance_rationale': {'type': 'string', 'minLength': 1,
                                        'description': 'Explain the specific connection between the witnessed source '
                                                       'subject/result and the original question; a search hit or '
                                                       'matching title alone is not verification.'},
                'witness': _witness_schema()})


def reason_schema(commit_schema, leads):
    """The old ``contextual_interpretation.reasoning_action_schema``: the required-grading action (the typed commit
    with its ``evidence_processing``: the contextual grader selected for the interpretation, or the source-grounded
    no-applicable-evidence declaration) and, for a verified_source_leads commission, a source_lead."""
    schema = required_grading_schema(commit_schema, source_location_inputs(grading_population_schema()))
    if leads:
        schema['properties']['source_lead'] = lead_schema()
    return source_location_inputs(schema)


def catalog(names, commit_schema, leads, input_list):
    """The tools the model is shown: name, description and input schema (the old catalog; every input schema
    is projected through source_location_inputs; the child accepts only unconsumed sources of ``input_list``)."""
    populations = {entry['name']: entry for entry in population_catalog()}
    entries = []
    for name in names:
        if name in CHILD_SLOTS:
            entries.append({'name': name, 'description': CHILD_DESCRIPTIONS[name],
                            'input_schema': child_arguments(input_list)})
        elif name == 'reason':
            entries.append({'name': 'reason', 'description': REASON_DESCRIPTION,
                            'input_schema': reason_schema(commit_schema, leads)})
        elif name in POPULATION_NAMES:
            entry = populations[POPULATION_NAMES[name]]
            entries.append({'name': name, 'description': entry['description'],
                            'input_schema': source_location_inputs(entry['input_schema'])})
        else:
            entries.append({'name': name, 'description': DESCRIPTIONS[LIBRARY_NAMES[name]],
                            'input_schema': source_location_inputs(INPUT_SCHEMAS[LIBRARY_NAMES[name]])})
    return entries


def selection_schema(names, commit_schema, leads, input_list):
    """What the model answers with: one tool and its arguments (the old action schema)."""
    return obj({'selection': {'anyOf': [obj({'kind': {'const': 'child' if entry['name'] in CHILD_SLOTS else 'tool'},
                                             'tool': {'const': entry['name']}, 'arguments': entry['input_schema']})
                                        for entry in catalog(names, commit_schema, leads, input_list)]}})


def admitted(name, arguments):
    """The old ``_tool_arguments`` (its Store-free part): the arguments against the offered schema. This episode has
    no assigned page, so the old restriction of reads and population sources to the page's source tree does not
    apply. A violation is a ``ContractError`` or a ``ValidationError``."""
    if name in POPULATION_NAMES.values():
        entry = {entry['name']: entry for entry in population_catalog()}[name]
        validate_schema(arguments, source_location_inputs(entry['input_schema']))
        return
    validate_schema(arguments, source_location_inputs(INPUT_SCHEMAS[name]))


def literature_context(ctx, envelope):
    """The context the library repositories and the required-grading logic read (the old binding context): the
    episode's identity, its commission and the records it holds now."""
    return LiteratureContext(
        run_id=ctx.run_id, episode_id=ctx.episode_id, role='literature_strategy',
        path=tuple(ctx.binding_path.split('/')), scope=envelope['scope'], assignment=envelope['assignment'],
        request={'goal': GOAL, 'scope': envelope['scope']}, received_record_refs=tuple(ctx.store.refs()))


def repositories(store):
    """The old ``_a108_grading_repository`` and ``_a108_aggregation_repository``: the aggregation reads the grading
    cells of a sheet through the grading repository."""
    grading = LiteratureA108GradingRepository(store)
    aggregation = LiteratureA108AggregationRepository(
        store,
        read_cells=lambda context, sheet_ref, components: grading.fact_cells(context, [sheet_ref],
                                                                              components=components))
    return grading, aggregation


def invalid_outcome(ctx, name, arguments, error):
    """The old invalid outcome of ``execute``: a contract error is returned as ``arguments_or_reference`` feedback."""
    detail = getattr(error, 'detail', None)
    field = getattr(error, 'field', None)
    return {'status': 'invalid',
            'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': name, 'arguments': arguments}),
            'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'category': 'arguments_or_reference', 'code': getattr(error, 'code', str(error)),
                         **({'field': field} if field is not None else {}),
                         **({'detail': detail} if detail else {})}}


def authorize_source(store, context, name, arguments):
    """The old repository authorization of ``_tool_arguments``: a source read, or a state.query by reference, may not
    reach another episode's private sheet (``a108_selected_components_required_for_nonowner``)."""
    for repository in repositories(store):
        if isinstance(arguments.get('source_ref'), str) and (name.startswith('source.')
                                                             or name in {'image.view', 'material.from_source'}):
            representation = arguments.get('representation',
                                           'original' if name == 'source.sequence.references' else 'text')
            repository.authorize_source_access(context, arguments['source_ref'], representation, name)
        elif name == 'state.query' and 'refs' in arguments:
            for ref in arguments['refs']:
                repository.authorize_record_access(context, store.get(ref))


async def run_access_tool(name, envelope, ctx):
    """Execute one access tool: the old ``execute`` of ``LiteratureOperations``. A contract error is returned as an
    ``invalid`` outcome, as the old ``execute`` did; the outcome is the unit's outcome like any other."""
    arguments, scope = envelope['arguments'], envelope['scope']
    context = literature_context(ctx, envelope)
    try:
        admitted(name, arguments)
        authorize_source(ctx.store, context, name, arguments)
    except (ContractError, ValidationError) as error:
        return invalid_outcome(ctx, name, arguments, error)
    registry = ToolRegistry(ctx.store, clients=ctx.services['public_clients'], **ctx.settings['tool_registry'])
    permitted = tuple(ctx.store.refs()) if name in HELD_SOURCE_TOOLS else None
    try:
        outcome = await registry.execute_async(name, arguments, scope=scope, operation_key=ctx.operation_key,
                                               permitted_record_refs=permitted)
    except CustodyError:
        raise
    except Exception as error:   # the old record_execution_failure: a failed selected operation is an outcome
        return failure_outcome(ctx.store, error, category='episode_execution', cause_code='selected_operation_failed')
    if name == 'state.query' and outcome.get('status') in {'completed', 'partial'}:
        repositories_ = repositories(ctx.store)
        try:
            for record in outcome.get('result', {}).get('records', ()):
                for repository in repositories_:
                    repository.authorize_record_access(context, record)
        except ContractError as error:
            return {'status': 'invalid',
                    'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': name,
                                                            'arguments': arguments}),
                    'record_refs': [], 'changed_record_refs': [], 'result': None,
                    'feedback': {'category': 'arguments_or_reference', 'code': str(error)}}
    return outcome


async def state_query(arguments, ctx):
    return await run_access_tool('state.query', arguments, ctx)


async def source_read(arguments, ctx):
    return await run_access_tool('source.read', arguments, ctx)


async def source_locate(arguments, ctx):
    return await run_access_tool('source.locate', arguments, ctx)


async def source_sequence_references(arguments, ctx):
    return await run_access_tool('source.sequence.references', arguments, ctx)


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


async def public_literature_search(arguments, ctx):
    return await run_access_tool('public.literature.search', arguments, ctx)


async def public_literature_read(arguments, ctx):
    return await run_access_tool('public.literature.read', arguments, ctx)


async def public_literature_sequence_identity(arguments, ctx):
    return await run_access_tool('public.literature.sequence_identity', arguments, ctx)


async def public_ncbi_search(arguments, ctx):
    return await run_access_tool('public.ncbi.search', arguments, ctx)


async def public_pmc_versions(arguments, ctx):
    return await run_access_tool('public.pmc.versions', arguments, ctx)


async def public_pmc_files(arguments, ctx):
    return await run_access_tool('public.pmc.files', arguments, ctx)


async def public_pmc_asset(arguments, ctx):
    return await run_access_tool('public.pmc.asset', arguments, ctx)


async def public_taxonomy(arguments, ctx):
    return await run_access_tool('public.taxonomy', arguments, ctx)


async def public_ncbi_sequence(arguments, ctx):
    return await run_access_tool('public.ncbi.sequence', arguments, ctx)


def populate(name, envelope, ctx):
    """The old population branch of ``execute`` (``literature.a108_grading.populate`` and ``literature.a108.aggregate``):
    the arguments admitted, their text witnesses materialized from the actual source bytes, then the repository
    populates its sheet. A contract error is an ``invalid`` outcome."""
    arguments = envelope['arguments']
    store = ctx.store
    context = literature_context(ctx, envelope)
    grading, aggregation = repositories(store)
    repository = grading if name == 'literature.a108_grading.populate' else aggregation

    def read_source(ref, representation):
        source = repository._native_source(context, ref)
        reading = {'source_ref': ref, 'representation': representation}
        admitted('source.read', reading)
        authorize_source(store, context, 'source.read', reading)
        artifact = source.get('artifact_ref' if representation == 'original' else 'text_ref')
        if artifact is None:
            raise ContractError('literature_source_representation_unavailable')
        return {'artifact_ref': artifact, 'content': store.get_artifact(artifact)}
    try:
        admitted(name, arguments)
        materialized = materialize_text_witness_inputs(arguments, read_source=read_source)
        return repository.populate(context, materialized, ctx.operation_key)
    except (ContractError, ExperimentalContractError) as error:
        return invalid_outcome(ctx, name, arguments, error)


def literature_a108_grading_populate(arguments, ctx):
    return populate('literature.a108_grading.populate', arguments, ctx)


def literature_a108_aggregate(arguments, ctx):
    return populate('literature.a108.aggregate', arguments, ctx)


def validate_lead(store, value, outcome, proposed, task):
    """The old credit.py ``validate_lead`` re-expressed on custody (private copy; library candidate): the lead's
    identity and exact source witness against the records this episode holds. A violation is a ``ContractError``."""
    if task['kind'] != 'verified_source_leads':
        raise ContractError('literature_lead_outside_original_search_task')
    value = plain(resolve_aliases(plain(value), outcome.get('aliases', {})))
    validate_schema(value, source_location_inputs(lead_schema()))
    if value['proposed_annotation_ref'] != proposed or value['witness']['source_ref'] != value['source_ref']:
        raise ContractError('literature_lead_question_or_source_mismatch')
    if not value['relevance_rationale'].strip():
        raise ContractError('literature_lead_relevance_rationale_required')
    known = {*store.refs(), *outcome.get('record_refs', [])}
    if not {value['source_ref'], value['subject_ref'], proposed} <= known:
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
    if (anchor['artifact_ref'] != witness['artifact_ref']
            or not witness['start'] <= anchor['start'] < anchor['end'] <= witness['end']):
        raise ContractError('literature_lead_subject_outside_witness')
    return {**value, 'witness': {**value['witness'], 'quote': witness['quote']}}


def resolve_aliases(value, aliases, reference_position=False):
    """The old credit.py ``_resolve``: original-action aliases in reference positions of a source lead."""
    if reference_position and isinstance(value, str) and value.startswith('@'):
        if value[1:] not in aliases:
            raise ContractError('required_grading_unresolved_alias', detail={'reference': value})
        return aliases[value[1:]]
    if isinstance(value, dict):
        return {key: resolve_aliases(child, aliases, key in ('ref', 'dependencies') or key.endswith('_ref')
                                     or key.endswith('_refs')) for key, child in value.items()}
    if isinstance(value, list):
        return [resolve_aliases(child, aliases, reference_position) for child in value]
    return value


def reason(arguments, ctx):
    """Commit the model's typed reasoning with its contextual grader: the old ``execute_reasoning`` of
    ``ContextualInterpretation``. Without a ``source_lead`` this is the required-grading action of the library
    (``literature_required_grading.execute``: the commit and the sheet are saved together, or nothing). With a
    ``source_lead`` the same action and the validated lead are one transaction: a lead that does not hold returns an
    ``invalid`` outcome."""
    envelope = arguments
    selection = envelope['arguments']
    store = ctx.store
    context = literature_context(ctx, envelope)
    repository = repositories(store)[0]

    def authorize_source_access(reference, representation):
        reading = {'source_ref': reference, 'representation': representation}
        admitted('source.read', reading)
        authorize_source(store, context, 'source.read', reading)
    if 'source_lead' in selection:
        try:
            witness = selection['source_lead']['witness']
            reading = {'source_ref': witness['source_ref'], 'representation': witness['representation'],
                       'offset': witness['start'], 'limit': witness['end'] - witness['start']}
            admitted('source.read', reading)
            authorize_source(store, context, 'source.read', reading)
            with store.transaction():
                native = {key: value for key, value in plain(selection).items() if key != 'source_lead'}
                result = execute_required_grading(context, native, ctx.operation_key, repository,
                                                  authorize_source_access=authorize_source_access)
                if result['status'] not in ('completed', 'partial'):
                    return result
                lead = validate_lead(store, selection['source_lead'], result, envelope['proposed_annotation_ref'],
                                     envelope['task'])
                return {**result, 'literature_source_lead': lead}
        except (ContractError, ExperimentalContractError) as error:
            return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                    'feedback': {'category': 'source_lead', 'code': getattr(error, 'code', str(error))}}
    return execute_required_grading(context, selection, ctx.operation_key, repository,
                                    authorize_source_access=authorize_source_access)


TOOLS = {'state_query': state_query, 'source_read': source_read, 'source_locate': source_locate,
         'source_sequence_references': source_sequence_references, 'image_view': image_view,
         'source_archive_members': source_archive_members, 'source_archive_extract': source_archive_extract,
         'source_xlsx_sheets': source_xlsx_sheets, 'source_xlsx_rows': source_xlsx_rows,
         'source_pdf_info': source_pdf_info, 'source_pdf_text': source_pdf_text, 'source_pdf_page': source_pdf_page,
         'execution_estimate': execution_estimate,
         'public_literature_search': public_literature_search, 'public_literature_read': public_literature_read,
         'public_literature_sequence_identity': public_literature_sequence_identity,
         'public_ncbi_search': public_ncbi_search, 'public_pmc_versions': public_pmc_versions,
         'public_pmc_files': public_pmc_files, 'public_pmc_asset': public_pmc_asset,
         'public_taxonomy': public_taxonomy, 'public_ncbi_sequence': public_ncbi_sequence,
         'literature_a108_grading_populate': literature_a108_grading_populate,
         'literature_a108_aggregate': literature_a108_aggregate, 'reason': reason}


def decide(summary, feedback, ctx):
    """Ask the model for the next tool or child commission, shown the assignment, the custody of the source, its own
    read outcomes, what its children returned, the interpretation so far, the latest image it looked at, the saved sheets, the commissioned goal plan, the tools, the
    measured time and the yield table (the old decision state and inputs, over this episode's summary)."""
    names = offered(ctx.settings, summary['input_list'])
    leads = summary['task']['kind'] == 'verified_source_leads'
    knowledge_directory = ctx.settings.get('knowledge_library_directory')
    context = {'goal': GOAL, 'scope': summary['scope'], 'literature_assignment': summary['literature_assignment'],
               'literature_source_custody': summary['literature_source_custody'],
               'held_source_custody': summary['held_source_custody'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_history_meaning': summary['literature_history_meaning'],
               'literature_experimental_work': summary['literature_experimental_work'],
               'literature_received_fact_display': summary['literature_received_fact_display'],
               'literature_owned_population_sources': summary['literature_owned_population_sources'],
               'literature_goal_plan': summary['literature_goal_plan'],
               'credit_binding': summary['credit_binding'], 'visual_evidence': summary['visual_evidence'],
               'last_local_outcome': summary['last_local_outcome'], 'held_record_refs': summary['held_record_refs'],
               'current_findings': summary['finding'], 'child_reports': summary['child_reports'],
               'source_lead_dispositions': summary['source_lead_dispositions'],
               'input_list': summary['input_list'],
               'consumed_search_result_refs': summary['consumed_search_result_refs'],
               'tools': catalog(names, summary['reasoning_schema'], leads, summary['input_list']),
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'literature_selected_population_attempt': summary['literature_selected_population_attempt'],
        'feedback': feedback, 'action_yields': summary['action_yields'],
        'tool_knowledge': None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(knowledge=context.get('tool_knowledge'), leads=leads), context,
                        generation_schema(selection_schema(names, summary['reasoning_schema'], leads,
                                                            summary['input_list'])))


def empty_commit(commit, commit_schema):
    """The old empty-reasoning test: every section the schema names is present or absent and none has a row."""
    return (set(commit_schema.get('required', commit_schema['properties'])) <= set(commit)
            <= set(commit_schema['properties']) and all(value == [] for value in commit.values()))


def reasoning_has_task_content(task, arguments):
    """The old ``ContextualInterpretation.reasoning_has_task_content``: an otherwise empty commit is executable only
    as a valid source lead of a verified_source_leads commission."""
    if 'source_lead' not in arguments or task['kind'] != 'verified_source_leads':
        return False
    validate_schema(plain(arguments['source_lead']), source_location_inputs(lead_schema()))
    return True


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one child commission, or reject it (no unit). An answer that
    selects no offered tool or child,
    arguments that do not fit its schema, an empty reasoning commit (except a no-applicable-evidence declaration or a
    source lead) is invalid."""
    names = offered(ctx.settings, summary['input_list'])
    leads = summary['task']['kind'] == 'verified_source_leads'
    commit_schema = summary['reasoning_schema']
    schema = selection_schema(names, commit_schema, leads, summary['input_list'])
    try:
        selection = validate_selection(decode_response(response, schema), schema)
        name, arguments = selection['tool'], selection['arguments']
        if name in CHILD_SLOTS:
            for reference in arguments['search_result_refs']:
                if reference not in summary['input_list']:
                    raise ContractError('literature_source_not_in_input_list_or_consumed',
                                        detail={'reference': reference})
            for reference in (*arguments['search_result_refs'], *arguments['question_context_refs']):
                if not records.holds(reference):
                    raise ContractError('literature_reference_unavailable', detail={'reference': reference})
            return ChildCall(name, {'objective': arguments['objective'],
                                    'search_result_refs': arguments['search_result_refs'],
                                    'question_context_refs': arguments['question_context_refs']})
        if (name == 'reason' and empty_commit(arguments['commit'], commit_schema)
                and arguments.get('evidence_processing', {}).get('kind') != 'no_applicable_evidence'
                and not reasoning_has_task_content(summary['task'], arguments)):
            raise ValueError('empty_reasoning_commit')
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(name, {'arguments': arguments, 'scope': summary['scope'],
                           'assignment': summary['literature_assignment'], 'task': summary['task'],
                           'proposed_annotation_ref': summary['proposed_annotation_ref']})


def validate_selection(value, schema):
    validate_schema(value, schema)
    return value['selection']
