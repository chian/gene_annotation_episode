"""The task: read the assigned source's passages, with their neighbouring context, through the access tools,
commit graded reasoning on what they say (the interpretation and its purpose-specific subscoring sheet in one unit;
for a verified-source-leads commission also validated source leads), optionally populate the subscoring or main
evidence sheets. There is no report tool: the return is the controlled features code reads from the saved sheets.

The base investigation text and the reasoning-commit requirement are the library's A108
``literature_investigation_prompt`` texts (the old ``INSTRUCTIONS`` source).

Carried from the old task.py, task_decision.py, task_instructions.py, decision_inputs.py, grading/*.py,
scoring/contextual_main_sheet.py, source_operations.py, source_contracts.py, source_references.py and goal.py
(``commissioned_task``, ``planning_context``). One unit is one model-selected tool call. The task always offers a
unit and never ends the Episode: only the yield controller does. The episode has no child and cannot search or
fetch new sources (no acquisition tools).

Required literature evidence processing (``AGENTS.md``): the ``reason`` tool is the old ``execute_reasoning`` path
(``literature_required_grading.execute``): an interpretation with scientific rows is committed only together with
its grading, whose sheet is saved in the same unit, and the only source-processing outcome without grading is the
source-grounded ``no_applicable_evidence`` declaration. A returned invalid or failed outcome is the unit's outcome
like any other.

The A108 repositories and the required-grading ``execute`` read a context value (``LibraryCallContext``); the public
acquisition clients are the declared service ``public_clients``, the ``ToolRegistry`` JSON settings the setting
``tool_registry``."""
from dataclasses import dataclass

from jsonschema import ValidationError

from episode_runtime import CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.sample_context_evidence.literature_experimental_contracts import (
    ExperimentalContractError)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.sample_context_evidence.literature_population_catalog import (
    population_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.sample_context_evidence import (
    literature_required_grading as required_grading)
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.literature_grading_inputs import (
    grading_population_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.sample_context_evidence.literature_assay_inputs import (
    _Sources, _witness_schema, materialize_text_witness_inputs)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.sample_context_evidence.literature_investigation_prompt import (
    INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_sequence_discovery import (
    references_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    GRADING_INSTRUCTIONS)
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
from gene_annotation_episode.episodic_workflow.episode_support.records.received_records import read_record_in_scope
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import (
    RECORD_SCHEMAS, REF, REFS, identity, obj, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.tools.sample_context_evidence.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

from .goal import GOAL

CHILD_SLOTS = {}
SERVICES = ('public_clients',)

INTEGER = {'type': 'integer', 'minimum': 0}
POSITIVE = {'type': 'integer', 'minimum': 1}
TEXT = {'type': 'string', 'minLength': 1}

# The access tools of the old ``_A108_ACCESS_TOOLS`` that the A108 tool registry's catalog offers (the old catalog
# kept the intersection; ``material.*`` are not in this registry's catalog); descriptions as the registry states them.
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
    'execution_estimate': 'execution.estimate'}
# The two A108 population tools of the old ``_a108_population_catalog``: python name -> library name.
POPULATION_NAMES = {'grading_populate': 'literature.a108_grading.populate',
                    'aggregate_populate': 'literature.a108.aggregate'}
# Keys of a population argument that name a source; each must lie within the assigned source (old ``sources``).
POPULATION_SOURCE_KEYS = ('source_ref', 'metadata_source_ref', 'sheet_ref', 'covariance_source_ref',
                          'model_source_ref')

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
}
# ``execution.estimate`` is offered for the workbook tools only, and only when the run has timing statistics.
INPUT_SCHEMAS['execution.estimate'] = {'anyOf': [
    obj({'tool': {'const': name}, 'arguments': INPUT_SCHEMAS[name]}) for name in ('source.xlsx.sheets', 'source.xlsx.rows')]}

REASON_DESCRIPTION = ('Commit a typed scientific reasoning over the supplied passages and the records you hold: '
                      'extracted terms, source subjects, contexts, observations, hypotheses and assessments, each '
                      'with its exact source anchor, together with its required evidence_processing (the grading '
                      'whose subscoring sheet is saved in the same action, or the source-grounded no_applicable_'
                      'evidence declaration). A commit with every section empty is rejected.')
HISTORY_START = 'On a fresh provider conversation,'
HISTORY_END = 'Do not execute native provider tools.'
HISTORY_GUIDANCE = ('Your own earlier read outcomes are shown to you as own_literature_outcomes; that page creates '
                    'no new action and does not execute or credit the historical work again.\n')
RETURN_GUIDANCE = ('\nWhat returns to your parent is your credit and the counts code reads from the A108 sheets you saved, '
                   'with their references; nothing you write in prose is returned. Selecting a tool never ends your '
                   'work: only the numerical controller does.')
INPUT_LIST_GUIDANCE = ('\nYour input list (input_list) holds the commissioned passages still to be processed, in the '
                       'order assigned, as [start, end] byte offsets. A passage is consumed once a reasoning commit of '
                       'yours has dealt with it (a no-applicable-evidence declaration whose examined witnesses cover it, '
                       'or a record anchored within it; consumed_inputs lists them) and is no longer offered: a source '
                       'read lying wholly inside consumed passages is refused. Work through the input list.')
LEAD_GUIDANCE = ('\nFor a verified_source_leads commission, a reason selection also carries source_lead: the '
                 'inspected source, its anchored reference subject, whether it is a useful lead for the original '
                 'question and the exact witnessed byte interval. A search hit or title alone verifies nothing.')


@dataclass(frozen=True)
class LibraryCallContext:
    """The values the A108 library repositories and the required-grading ``execute`` read from their ``context``
    argument (``scope``, ``run_id``, ``episode_id``, ``received_record_refs``), named as they are
    read there. It is a plain value, not a binding context: it carries no behaviour and no recording."""
    scope: dict
    run_id: str
    episode_id: str
    received_record_refs: tuple
    assignment: dict


def instructions(*, knowledge, leads):
    """The old task_instructions.instructions: the investigation text, this episode's goal, the reasoning-commit
    requirement, the tool-knowledge text when it is offered. The decision-exchange paragraph, the pending-delivery
    paragraph, the wait paragraphs and the redeliver_report text are not carried: no such action exists."""
    text = replace_span(INSTRUCTIONS, HISTORY_START, HISTORY_END, HISTORY_GUIDANCE)
    text += '\n' + GOAL
    text += '\n' + REASONING_COMMIT_REQUIREMENT
    text += GRADING_INSTRUCTIONS
    text += INPUT_LIST_GUIDANCE
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if leads:
        text += LEAD_GUIDANCE
    return text + RETURN_GUIDANCE


def offered(settings):
    """The tools offered now: the access tools (``execution_estimate`` only with timing statistics configured), the
    two population tools, and the graded reasoning commit."""
    tools = [name for name in LIBRARY_NAMES
             if name != 'execution_estimate' or 'native_statistics' in settings['tool_registry']]
    return tools + list(POPULATION_NAMES) + ['reason']


def lead_schema():
    """The old ``lead_schema`` of the episode's credit: one source lead the model proposes."""
    return obj({'proposed_annotation_ref': {**REF, 'x-reference-namespace': 'hypothesis'},
                'source_ref': {**REF, 'x-reference-namespace': 'source'},
                'subject_ref': {**REF, 'x-reference-namespace': 'reference'},
                'disposition': {'enum': ['relevant', 'not_relevant'],
                                'description': 'Whether the inspected source is a useful lead for this commissioned question. This is not evidence supporting or opposing the proposed annotation.'},
                'relevance_rationale': {'type': 'string', 'minLength': 1,
                                        'description': 'Explain the specific connection between the witnessed source subject/result and the original question; a search hit or matching title alone is not verification.'},
                'witness': _witness_schema()})


def reason_schema(commit_schema, leads):
    """The old ``reasoning_action_schema``: the required-grading envelope over the typed commit and the grading
    population schema and, for a verified_source_leads commission, a source_lead."""
    schema = required_grading.action_schema(commit_schema, source_location_inputs(grading_population_schema()))
    if leads:
        schema['properties']['source_lead'] = lead_schema()
    return source_location_inputs(schema)


def catalog(names, commit_schema, leads):
    """The tools the model is shown: name, description and input schema (the old catalog; every input schema is
    projected through source_location_inputs)."""
    populations = {entry['name']: entry for entry in population_catalog()}
    entries = []
    for name in names:
        if name == 'reason':
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


def selection_schema(names, commit_schema, leads):
    """What the model answers with: one tool and its arguments (the old action schema)."""
    return obj({'selection': {'anyOf': [obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']},
                                             'arguments': entry['input_schema']})
                                        for entry in catalog(names, commit_schema, leads)]}})


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
    """The old ``_tool_arguments`` for an access tool: the arguments against the offered schema, and the source they
    name against the assigned page's source. A violation is a ``ContractError``."""
    validate_schema(arguments, source_location_inputs(INPUT_SCHEMAS[name]))
    selected = arguments['arguments'] if name == 'execution.estimate' else arguments
    source_ref = selected.get('source_ref')
    if name == 'source.archive.extract':
        source_ref = read_record_in_scope(store, arguments['member_ref'], scope, 'archive_member')['source_ref']
    if source_ref is not None and not within_source(store, source_ref, root, scope):
        raise ContractError('literature_reading_outside_assigned_source')


def named_sources(value):
    """The sources a population argument names (the old ``sources`` generator)."""
    if isinstance(value, dict):
        for key, child in value.items():
            if key in POPULATION_SOURCE_KEYS and isinstance(child, str):
                yield child
            else:
                yield from named_sources(child)
    elif isinstance(value, list):
        for child in value:
            yield from named_sources(child)


def library_context(envelope, ctx):
    """The context the library repositories read, from the envelope ``action`` built and the unit."""
    return LibraryCallContext(scope=envelope['scope'], run_id=ctx.run_id, episode_id=ctx.episode_id,
                              received_record_refs=tuple(ctx.store.refs()), assignment={})


def repositories(ctx, context):
    """The old ``_a108_grading_repository`` and ``_a108_aggregation_repository`` (the old binding cached them on
    itself; the aggregation reads the cells of the grading repository)."""
    grading = LiteratureA108GradingRepository(ctx.store)
    aggregation = LiteratureA108AggregationRepository(
        ctx.store,
        read_cells=lambda call, sheet_ref, components: grading.fact_cells(call, [sheet_ref], components=components))
    return grading, aggregation


def authorize_source(store, repositories_, context, envelope, ref, representation, tool_name='source.read'):
    """The old ``_tool_arguments(context, 'source.read', ...)`` seen from a library call: the page-source
    restriction, then each repository's source access rule."""
    admitted(store, tool_name, {'source_ref': ref, 'representation': representation}, envelope['scope'],
             envelope['page_source_ref'])
    for repository in repositories_:
        repository.authorize_source_access(context, ref, representation, tool_name)


def invalid(ctx, name, arguments, error):
    detail = {'detail': error.detail} if getattr(error, 'detail', None) else {}
    return {'status': 'invalid',
            'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': name, 'arguments': arguments}),
            'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'category': 'arguments_or_reference', 'code': str(error), **detail}}


async def run_access_tool(name, envelope, ctx):
    """Execute one access tool. A contract error is returned as an ``invalid`` outcome with ``arguments_or_reference``
    feedback, as the old ``execute`` did; the outcome is the unit's outcome like any other. The A108 repositories'
    source and record access rules (the old tail of ``_tool_arguments`` and of ``execute``) apply to reads of
    sources and of records."""
    arguments, scope, root = envelope['arguments'], envelope['scope'], envelope['page_source_ref']
    context = library_context(envelope, ctx)
    guards = repositories(ctx, context)
    try:
        admitted(ctx.store, name, arguments, scope, root)
        if isinstance(arguments.get('source_ref'), str) and (name.startswith('source.') or name == 'image.view'):
            representation = arguments.get('representation', 'original' if name == 'source.sequence.references'
                                           else 'text')
            for repository in guards:
                repository.authorize_source_access(context, arguments['source_ref'], representation, name)
        elif name == 'state.query' and 'refs' in arguments:
            for ref in arguments['refs']:
                for repository in guards:
                    repository.authorize_record_access(context, ctx.store.get(ref))
    except (ContractError, ValidationError) as error:
        return invalid(ctx, name, arguments, error)
    registry = ToolRegistry(ctx.store, clients=ctx.services['public_clients'], **ctx.settings['tool_registry'])
    permitted = tuple(ctx.store.refs()) if name in ('source.locate', 'source.sequence.references') else None
    try:
        outcome = await registry.execute_async(name, arguments, scope=scope, operation_key=ctx.operation_key,
                                               permitted_record_refs=permitted)
    except CustodyError:
        raise
    except Exception as error:   # the old record_execution_failure: a failed selected operation is an outcome
        return failure_outcome(ctx.store, error, category='episode_execution', cause_code='selected_operation_failed')
    if name == 'state.query' and outcome.get('status') in ('completed', 'partial'):
        try:
            for record in outcome.get('result', {}).get('records', ()):
                for repository in guards:
                    repository.authorize_record_access(context, record)
        except ContractError as error:
            return {'status': 'invalid', 'operation_ref': identity('operation', {
                'key': ctx.operation_key, 'name': name, 'arguments': arguments}), 'record_refs': [],
                'changed_record_refs': [], 'result': None,
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


def populate(library_name, which, envelope, ctx):
    """The old ``execute`` branch for ``literature.a108_grading.populate`` and ``literature.a108.aggregate``: the
    arguments against the population schema and the page source, the text witnesses materialized from authorized
    bytes, then the repository populates and saves its sheet. A contract error is an ``invalid`` outcome."""
    arguments, scope, root = envelope['arguments'], envelope['scope'], envelope['page_source_ref']
    store = ctx.store
    context = library_context(envelope, ctx)
    guards = repositories(ctx, context)
    repository = guards[which]
    try:
        entry = {row['name']: row for row in population_catalog()}[library_name]
        validate_schema(arguments, source_location_inputs(entry['input_schema']))
        for reference in set(named_sources(arguments)):
            if not within_source(store, reference, root, scope):
                raise ContractError('literature_reading_outside_assigned_source')

        def read_source(ref, representation):
            source = repository._native_source(context, ref)
            authorize_source(store, guards, context, envelope, ref, representation)
            artifact = source.get('artifact_ref' if representation == 'original' else 'text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            return {'artifact_ref': artifact, 'content': store.get_artifact(artifact)}
        materialized = materialize_text_witness_inputs(arguments, read_source=read_source)
        return repository.populate(context, materialized, ctx.operation_key)
    except (ContractError, ExperimentalContractError, ValidationError) as error:
        return {'status': 'invalid', 'operation_ref': identity('operation', {
            'key': ctx.operation_key, 'name': library_name, 'arguments': arguments}), 'record_refs': [],
            'changed_record_refs': [], 'result': None,
            'feedback': {'category': 'arguments_or_reference', 'code': str(error),
                         'field': getattr(error, 'field', None),
                         **({'detail': error.detail} if getattr(error, 'detail', None) is not None else {})}}


def grading_populate(arguments, ctx):
    return populate('literature.a108_grading.populate', 0, arguments, ctx)


def aggregate_populate(arguments, ctx):
    return populate('literature.a108.aggregate', 1, arguments, ctx)


def validate_source_lead(store, lead, outcome, proposed):
    """The old ``validate_lead`` re-expressed on custody (private copy; library candidate): the lead's identity and
    exact source witness against the records this episode holds. A violation is a ``ContractError``."""
    value = resolve_aliases(lead, outcome.get('aliases', {}))
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
    if anchor['artifact_ref'] != witness['artifact_ref'] or not witness['start'] <= anchor['start'] < anchor['end'] <= witness['end']:
        raise ContractError('literature_lead_subject_outside_witness')
    return {**value, 'witness': {**value['witness'], 'quote': witness['quote']}}


def resolve_aliases(value, aliases, reference_position=False):
    """The old ``_resolve``: original-action aliases in source-lead reference positions (private copy)."""
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
    """The old ``execute_reasoning`` of ``grading/contextual_interpretation.py``: the interpretation and its
    grader in one action (``required_grading.execute``, which saves the subscoring sheet before any credit
    projection). With a ``source_lead`` the commit, its grading and the validated lead are one transaction: a lead
    that does not hold returns an ``invalid`` outcome and nothing is committed."""
    envelope = arguments
    selection, scope, root = envelope['arguments'], envelope['scope'], envelope['page_source_ref']
    store = ctx.store
    context = library_context(envelope, ctx)
    guards = repositories(ctx, context)

    def authorize(ref, representation):
        authorize_source(store, guards, context, envelope, ref, representation)
    if 'source_lead' not in selection:
        return required_grading.execute(context, selection, ctx.operation_key, guards[0],
                                        authorize_source_access=authorize)
    try:
        witness = selection['source_lead']['witness']
        authorize(witness['source_ref'], witness['representation'])
        with store.transaction():
            native = {key: value for key, value in selection.items() if key != 'source_lead'}
            result = required_grading.execute(context, native, ctx.operation_key, guards[0],
                                              authorize_source_access=authorize)
            if result['status'] not in ('completed', 'partial'):
                return result
            lead = validate_source_lead(store, selection['source_lead'], result, envelope['proposed_annotation_ref'])
            return {**result, 'literature_source_lead': lead}
    except (ContractError, ExperimentalContractError, ValidationError) as error:
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'source_lead', 'code': getattr(error, 'code', str(error))}}


TOOLS = {'state_query': state_query, 'source_read': source_read, 'source_locate': source_locate,
         'source_sequence_references': source_sequence_references, 'image_view': image_view,
         'source_archive_members': source_archive_members, 'source_archive_extract': source_archive_extract,
         'source_xlsx_sheets': source_xlsx_sheets, 'source_xlsx_rows': source_xlsx_rows,
         'source_pdf_info': source_pdf_info, 'source_pdf_text': source_pdf_text, 'source_pdf_page': source_pdf_page,
         'execution_estimate': execution_estimate, 'grading_populate': grading_populate,
         'aggregate_populate': aggregate_populate, 'reason': reason}


def decide(summary, feedback, ctx):
    """Ask the model for the next tool, shown the assignment, the custody of the source, its own read outcomes,
    the saved-sheet display, the tools, the measured time and the yield table (the old decision state and inputs,
    over this episode's summary)."""
    names = offered(ctx.settings)
    leads = summary['task']['kind'] == 'verified_source_leads'
    knowledge_directory = ctx.settings.get('knowledge_library_directory')
    context = {'goal': GOAL, 'scope': summary['scope'], 'literature_assignment': summary['literature_assignment'],
               'literature_source_custody': summary['literature_source_custody'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_history_meaning': summary['literature_history_meaning'],
               'input_list': summary['input_list'], 'consumed_inputs': summary['consumed_inputs'],
               'literature_experimental_work': summary['literature_experimental_work'],
               'literature_received_fact_display': summary['literature_received_fact_display'],
               'literature_goal_plan': {
                   'objective': GOAL, 'proposed_annotation_ref': summary['proposed_annotation_ref'],
                   'commissioned_result': summary['task'], 'progress_definition': summary['credit_binding'],
                   'planning_question': instructions(knowledge=None, leads=leads)},
               'credit_binding': summary['credit_binding'], 'visual_evidence': summary['visual_evidence'],
               'last_local_outcome': summary['last_local_outcome'], 'held_record_refs': summary['held_record_refs'],
               'current_findings': summary['finding'],
               'source_lead_dispositions': summary['source_lead_dispositions'],
               'tools': catalog(names, summary['reasoning_schema'], leads),
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['action_yields'],
        'literature_selected_population_attempt': summary['literature_selected_population_attempt'],
        'tool_knowledge': None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(knowledge=context.get('tool_knowledge'), leads=leads), context,
                        generation_schema(selection_schema(names, summary['reasoning_schema'], leads)))


def empty_commit(commit, commit_schema):
    """The old empty-reasoning test: every section the schema names is present or absent and none has a row."""
    return (set(commit_schema.get('required', commit_schema['properties'])) <= set(commit)
            <= set(commit_schema['properties']) and all(value == [] for value in commit.values()))


def validate_selection(value, schema):
    validate_schema(value, schema)
    return value['selection']


def consumed_read(arguments, summary):
    """Whether a ``source_read`` window of the assigned source lies wholly inside a consumed passage (a re-read of
    consumed input)."""
    page = summary['literature_assignment']['page']
    if arguments.get('source_ref') != page['source_ref']:
        return False
    start = arguments.get('offset', 0)
    end = start + arguments.get('limit', 12000)
    if arguments.get('representation', 'text') != page['representation']:
        return False
    return any(first <= start and end <= last for first, last in summary['consumed_inputs'])


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call, or reject it (no unit). An answer that selects no offered tool,
    arguments that do not fit its schema, or an empty reasoning commit that has neither the no-applicable-evidence
    declaration nor a source lead is invalid."""
    names = offered(ctx.settings)
    leads = summary['task']['kind'] == 'verified_source_leads'
    commit_schema = summary['reasoning_schema']
    schema = selection_schema(names, commit_schema, leads)
    try:
        selection = validate_selection(decode_response(response, schema), schema)
        name, arguments = selection['tool'], selection['arguments']
        if (name == 'reason' and empty_commit(arguments['commit'], commit_schema)
                and arguments.get('evidence_processing', {}).get('kind') != 'no_applicable_evidence'
                and 'source_lead' not in arguments):
            raise ValueError('empty_reasoning_commit')
        if name == 'source_read' and consumed_read(arguments, summary):
            raise ValueError('input_already_consumed')   # a read wholly inside consumed passages: not offered again
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(name, {'arguments': arguments, 'scope': summary['scope'],
                           'page_source_ref': summary['literature_assignment']['page']['source_ref'],
                           'proposed_annotation_ref': summary['proposed_annotation_ref']})
