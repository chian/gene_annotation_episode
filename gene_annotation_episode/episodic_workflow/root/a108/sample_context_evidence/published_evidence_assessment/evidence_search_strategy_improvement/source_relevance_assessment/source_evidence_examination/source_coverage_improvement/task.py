"""The task: read the assigned source in document order through the access tools, commit reasoning on what it says
together with its purpose-specific grading and saved subscoring sheet (one original action), populate sheets, and
for a verified-source-leads commission validate source leads.

The base investigation text and the reasoning-commit requirement are the library's A108
``literature_investigation_prompt`` texts (the old ``INSTRUCTIONS`` source).

Carried from the old task.py, task_decision.py, task_instructions.py, decision_inputs.py, source_operations.py,
source_references.py, source_contracts.py, grading/contextual_interpretation.py, grading/contextual_subscoring.py
and scoring/contextual_main_sheet.py. One unit is one model-selected tool call. The task always offers a unit and
never ends the Episode: only the yield controller does. The episode has no child and cannot search or fetch new
sources (the old ``_A108_ACQUISITION_TOOLS`` were never offered to it).

The grading is coupled to the interpretation inside the one ``reason`` action: ``literature_required_grading.execute``
(library) commits the reasoning and the purpose-specific grading and saves the subscoring sheet in one Store
transaction, and admits an interpretation without its sheet nowhere (AGENTS.md, required literature evidence
processing). The only outcome that omits grading is a source-grounded ``no_applicable_evidence`` declaration."""
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
    literature_required_grading)
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
# The A108 public acquisition clients (``PublicClients``, an object of the outside world, not a setting) are the
# declared service ``public_clients``; the tool registry's JSON settings (``job_limits``, executables) are the
# episode's setting ``tool_registry``.
SERVICES = ('public_clients',)

INTEGER = {'type': 'integer', 'minimum': 0}
POSITIVE = {'type': 'integer', 'minimum': 1}
TEXT = {'type': 'string', 'minLength': 1}

# The access tools of the old ``_ACCESS_TOOLS``; descriptions as the tool library states them.
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
}

# python tool name -> the library's tool name (a tool name here is lowercase letters, digits and underscores)
ACCESS_NAMES = {
    'state_query': 'state.query', 'source_read': 'source.read', 'source_locate': 'source.locate',
    'source_sequence_references': 'source.sequence.references', 'image_view': 'image.view',
    'source_archive_members': 'source.archive.members', 'source_archive_extract': 'source.archive.extract',
    'source_xlsx_sheets': 'source.xlsx.sheets', 'source_xlsx_rows': 'source.xlsx.rows',
    'source_pdf_info': 'source.pdf.info', 'source_pdf_text': 'source.pdf.text', 'source_pdf_page': 'source.pdf.page',
    'execution_estimate': 'execution.estimate'}
POPULATE_NAMES = {'literature_a108_grading_populate': 'literature.a108_grading.populate',
                  'literature_a108_aggregate': 'literature.a108.aggregate'}
LIBRARY_NAMES = {**ACCESS_NAMES, **POPULATE_NAMES}
# Tools whose source reads are bound to the records this episode holds (the old ``authorization``).
HELD_SOURCE_TOOLS = ('source.locate', 'source.sequence.references')
SOURCE_KEYS = {'source_ref', 'metadata_source_ref', 'sheet_ref', 'covariance_source_ref', 'model_source_ref'}

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

REASON_DESCRIPTION = ('Commit a typed scientific reasoning over the source and the records you hold: extracted terms, '
                      'source subjects, contexts, observations, hypotheses and assessments, each with its exact '
                      'source anchor. Interpreting evidence requires evidence_processing in the same action: the '
                      'purpose-specific grading (the host saves its subscoring sheet with the interpretation) or, '
                      'only when the examined material holds no applicable contextual observation, a '
                      'source-grounded no_applicable_evidence declaration. Every assessment carries its typed '
                      'investigation_finding (it stays in the assessment record; it is not returned). A commit with every '
                      'section empty is rejected.')

HISTORY_START = "A commissioned child returns ONLY the parent's typed form."
HISTORY_END = 'Do not execute native provider tools.'
HISTORY_GUIDANCE = ('Your own earlier read outcomes are shown to you as own_literature_outcomes; that page creates '
                    'no new action and does not execute or credit the historical work again. There is no separate report to write: what you return to '
                    'your parent is your credit and the counts code reads from the sheets you saved; your '
                    'assessments and their investigation_finding stay in your records. Selecting a tool never ends your work: only the numerical '
                    'controller does.\n')
LEAD_GUIDANCE = ('\nFor a verified_source_leads commission, a reason selection also carries source_lead: the '
                 'inspected source, its anchored reference subject, whether it is a useful lead for the original '
                 'question and the exact witnessed byte interval. A search hit or title alone verifies nothing.')


def instructions(*, knowledge, leads):
    """The old task_instructions.instructions: the investigation text, this episode's goal, the reasoning-commit
    requirement, the tool-knowledge text when it is offered. The decision-exchange paragraph, the pending-delivery
    paragraph and the redeliver_report text are not carried: no such action exists."""
    text = replace_span(INSTRUCTIONS, HISTORY_START, HISTORY_END, HISTORY_GUIDANCE)
    text += '\n' + GOAL
    text += '\n' + REASONING_COMMIT_REQUIREMENT
    text += GRADING_INSTRUCTIONS
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if leads:
        text += LEAD_GUIDANCE
    return text


def offered(settings):
    """The tools offered now: the access tools (execution_estimate only with timing statistics configured), the
    reasoning commit and the two sheet populations."""
    access = [name for name in ACCESS_NAMES
              if name != 'execution_estimate' or 'native_statistics' in settings['tool_registry']]
    return access + ['reason', *POPULATE_NAMES]


def lead_schema():
    """The old ``credit.lead_schema``: a source-lead disposition (a private copy; library candidate)."""
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
    """The old ``reasoning_action_schema`` as the arguments of the ``reason`` tool: the typed commit, the
    ``evidence_processing`` of the required grading logic (the library's action schema) and, for a
    verified_source_leads commission, a ``source_lead``."""
    action = literature_required_grading.action_schema(commit_schema, source_location_inputs(grading_population_schema()))
    properties = {name: action['properties'][name] for name in ('commit', 'evidence_processing')}
    if leads:
        properties['source_lead'] = lead_schema()
    return source_location_inputs(obj(properties, required=['commit']))


def catalog(names, commit_schema, leads):
    """The tools the model is shown: name, description and input schema (the old catalog; every input schema is
    projected through source_location_inputs)."""
    populations = {entry['name']: entry for entry in population_catalog()}
    entries = []
    for name in names:
        if name == 'reason':
            entries.append({'name': 'reason', 'description': REASON_DESCRIPTION,
                            'input_schema': reason_schema(commit_schema, leads)})
        elif name in POPULATE_NAMES:
            entry = populations[POPULATE_NAMES[name]]
            entries.append({'name': name, 'description': entry['description'],
                            'input_schema': source_location_inputs(entry['input_schema'])})
        else:
            entries.append({'name': name, 'description': DESCRIPTIONS[ACCESS_NAMES[name]],
                            'input_schema': source_location_inputs(INPUT_SCHEMAS[ACCESS_NAMES[name]])})
    return entries


def selection_schema(names, commit_schema, leads):
    """What the model answers with: one tool and its arguments (the old action schema)."""
    return obj({'selection': {'anyOf': [obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']},
                                             'arguments': entry['input_schema']})
                                        for entry in catalog(names, commit_schema, leads)]}})


@dataclass(frozen=True)
class GradingContext:
    """What the library's A108 grading and sheet repositories read of their caller: the run and Episode, the scope,
    the assignment's requested components and the records received. The final form has no such object (the old
    ``BindingContext``); the library functions that take one are not carried yet, so this tool builds exactly what
    they read (misfit: library functions still take a context)."""
    run_id: str
    episode_id: str
    role: str
    scope: dict
    assignment: dict
    received_record_refs: tuple


def grading_context(envelope, ctx):
    return GradingContext(ctx.run_id, ctx.episode_id, 'literature_ordered', envelope['scope'],
                          envelope['requested'], tuple(ctx.store.refs()))


def grading_repository(store):
    """The old ``ContextualSubscoring._a108_grading_repository`` (it is the required grading repository)."""
    return LiteratureA108GradingRepository(store)


def aggregation_repository(store):
    """The old ``ContextualMainSheet._a108_aggregation_repository``."""
    grading = grading_repository(store)
    return LiteratureA108AggregationRepository(
        store,
        read_cells=lambda context, sheet_ref, components: grading.fact_cells(context, [sheet_ref], components=components))


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


def source_references(value):
    """The sources a population argument names (the old nested ``sources`` walk)."""
    if isinstance(value, dict):
        for key, child in value.items():
            if key in SOURCE_KEYS and isinstance(child, str):
                yield child
            else:
                yield from source_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from source_references(child)


def input_schema(name):
    if name in POPULATE_NAMES.values():
        return source_location_inputs({entry['name']: entry for entry in population_catalog()}[name]['input_schema'])
    return source_location_inputs(INPUT_SCHEMAS[name])


def admitted(store, name, arguments, envelope, ctx):
    """The old ``_tool_arguments``: the arguments against the offered schema, the source they name against the
    assigned page's source, and each A108 repository's authorization of the source or record read. A violation is
    a ``ContractError``."""
    scope, root = envelope['scope'], envelope['page_source_ref']
    validate_schema(arguments, input_schema(name))
    selected = arguments['arguments'] if name == 'execution.estimate' else arguments
    source_ref = selected.get('source_ref')
    if name == 'source.archive.extract':
        source_ref = read_record_in_scope(store, arguments['member_ref'], scope, 'archive_member')['source_ref']
    if source_ref is not None and not within_source(store, source_ref, root, scope):
        raise ContractError('literature_reading_outside_assigned_source')
    if name in POPULATE_NAMES.values():
        if any(not within_source(store, ref, root, scope) for ref in set(source_references(arguments))):
            raise ContractError('literature_reading_outside_assigned_source')
    context = grading_context(envelope, ctx)
    for repository in (grading_repository(store), aggregation_repository(store)):
        if isinstance(arguments.get('source_ref'), str) and (name.startswith('source.')
                                                             or name in {'image.view', 'material.from_source'}):
            representation = arguments.get('representation', 'original' if name == 'source.sequence.references'
                                           else 'text')
            repository.authorize_source_access(context, arguments['source_ref'], representation, name)
        elif name == 'state.query' and 'refs' in arguments:
            for ref in arguments['refs']:
                if not store.holds(ref):
                    raise ContractError('literature_reference_unavailable', detail={'reference': ref})
                repository.authorize_record_access(context, store.get(ref))


def invalid(ctx, name, arguments, error, *, category='arguments_or_reference'):
    """The old invalid outcome of ``execute``: it enters the iterator like any returned outcome."""
    detail = getattr(error, 'detail', None)
    return {'status': 'invalid',
            'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': name, 'arguments': arguments}),
            'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'category': category, 'code': str(error),
                         **({'field': error.field} if isinstance(error, ExperimentalContractError) else {}),
                         **({'detail': detail} if detail else {})}}


async def run_access_tool(name, envelope, ctx):
    """Execute one access tool. A contract error is returned as an ``invalid`` outcome with ``arguments_or_reference``
    feedback, as the old ``execute`` did; the outcome is the unit's outcome like any other."""
    arguments = envelope['arguments']
    try:
        admitted(ctx.store, name, arguments, envelope, ctx)
    except (ContractError, ValidationError) as error:
        return invalid(ctx, name, arguments, error)
    registry = ToolRegistry(ctx.store, clients=ctx.services['public_clients'], **ctx.settings['tool_registry'])
    permitted = tuple(ctx.store.refs()) if name in HELD_SOURCE_TOOLS else None
    try:
        outcome = await registry.execute_async(name, arguments, scope=envelope['scope'],
                                               operation_key=ctx.operation_key, permitted_record_refs=permitted)
    except CustodyError:
        raise
    except Exception as error:   # the old record_execution_failure: a failed selected operation is an outcome
        return failure_outcome(ctx.store, error, category='episode_execution', cause_code='selected_operation_failed')
    if name == 'state.query' and outcome.get('status') in {'completed', 'partial'}:
        context = grading_context(envelope, ctx)
        try:
            for record in outcome.get('result', {}).get('records', ()):
                for repository in (grading_repository(ctx.store),
                                   aggregation_repository(ctx.store)):
                    repository.authorize_record_access(context, record)
        except ContractError as error:
            return invalid(ctx, name, arguments, error)
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


def populate(name, repository, envelope, ctx):
    """The old population branch of ``execute``: the text witnesses of the arguments are materialized from their
    sources (each read admitted like ``source.read``) and the repository saves the sheet."""
    arguments, context, store = envelope['arguments'], grading_context(envelope, ctx), ctx.store
    try:
        admitted(store, name, arguments, envelope, ctx)

        def read_source(ref, representation):
            source = repository._native_source(context, ref)
            admitted(store, 'source.read', {'source_ref': ref, 'representation': representation}, envelope, ctx)
            artifact = source.get('artifact_ref' if representation == 'original' else 'text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            return {'artifact_ref': artifact, 'content': store.get_artifact(artifact)}
        materialized = materialize_text_witness_inputs(arguments, read_source=read_source)
        return repository.populate(context, materialized, ctx.operation_key)
    except (ContractError, ExperimentalContractError, ValidationError) as error:
        return invalid(ctx, name, arguments, error)


def literature_a108_grading_populate(arguments, ctx):
    return populate('literature.a108_grading.populate', grading_repository(ctx.store), arguments, ctx)


def literature_a108_aggregate(arguments, ctx):
    return populate('literature.a108.aggregate', aggregation_repository(ctx.store), arguments, ctx)


def validate_source_lead(store, lead, outcome, proposed):
    """The old ``credit.validate_lead`` re-expressed on custody (private copy; library candidate): the lead's
    identity and exact source witness against the records this episode holds. A violation is a ``ContractError``."""
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
    """The old ``credit._resolve``: original-action aliases in source-lead reference positions (private copy)."""
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
    """The old ``execute`` branch ``reason`` with ``contextual_interpretation.execute_reasoning``: the required
    grading logic commits the reasoning, grades it and saves the subscoring sheet in one action (the owner of
    interpretation accounts is named by the system). With a ``source_lead`` the commit, its grading and the
    validated lead are one transaction: a lead that does not hold returns an ``invalid`` outcome and nothing is
    committed."""
    envelope = arguments
    arguments, store = envelope['arguments'], ctx.store
    repository, context = grading_repository(store), grading_context(envelope, ctx)
    selection = {'kind': 'reason', **{name: value for name, value in arguments.items()
                                      if name != 'source_lead' and value is not None}}

    def authorize(ref, representation):
        admitted(store, 'source.read', {'source_ref': ref, 'representation': representation}, envelope, ctx)

    def execute():
        return literature_required_grading.execute(context, selection, ctx.operation_key, repository,
                                                   authorize_source_access=authorize)
    if arguments.get('source_lead') is None:
        return execute()
    try:
        witness = arguments['source_lead']['witness']
        admitted(store, 'source.read', {'source_ref': witness['source_ref'], 'representation': witness['representation'],
                                        'offset': witness['start'], 'limit': witness['end'] - witness['start']},
                 envelope, ctx)
        with store.transaction():
            result = execute()
            if result['status'] not in ('completed', 'partial'):
                return result
            lead = validate_source_lead(store, arguments['source_lead'], result, envelope['proposed_annotation_ref'])
            return {**result, 'literature_source_lead': lead}
    except (ContractError, ExperimentalContractError) as error:
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'source_lead', 'code': getattr(error, 'code', str(error))}}


TOOLS = {'state_query': state_query, 'source_read': source_read, 'source_locate': source_locate,
         'source_sequence_references': source_sequence_references, 'image_view': image_view,
         'source_archive_members': source_archive_members, 'source_archive_extract': source_archive_extract,
         'source_xlsx_sheets': source_xlsx_sheets, 'source_xlsx_rows': source_xlsx_rows,
         'source_pdf_info': source_pdf_info, 'source_pdf_text': source_pdf_text, 'source_pdf_page': source_pdf_page,
         'execution_estimate': execution_estimate, 'reason': reason,
         'literature_a108_grading_populate': literature_a108_grading_populate,
         'literature_a108_aggregate': literature_a108_aggregate}


def decide(summary, feedback, ctx):
    """Ask the model for the next tool, shown the assignment, the custody of the source, its own read outcomes, the
    typed findings and saved sheets so far, the latest image it looked at, the tools, the measured time and the yield
    table (the old decision state and inputs, over this episode's summary)."""
    names = offered(ctx.settings)
    leads = summary['task']['kind'] == 'verified_source_leads'
    knowledge_directory = ctx.settings.get('knowledge_library_directory')
    context = {'goal': GOAL, 'scope': summary['scope'], 'literature_assignment': summary['literature_assignment'],
               'literature_source_custody': summary['literature_source_custody'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_history_meaning': summary['literature_history_meaning'],
               'literature_experimental_work': summary['literature_experimental_work'],
               'literature_owned_population_sources': summary['literature_owned_population_sources'],
               'literature_received_fact_display': summary['literature_received_fact_display'],
               'credit_binding': summary['credit_binding'], 'visual_evidence': summary['visual_evidence'],
               'last_local_outcome': summary['last_local_outcome'], 'held_record_refs': summary['held_record_refs'],
               'current_findings': summary['finding'],
               'current_scoring_cells': {'grading': summary['grading_cells'],
                                         'aggregation': summary['aggregation_cells']},
               'source_lead_dispositions': summary['source_lead_dispositions'],
               'literature_goal_plan': summary['literature_goal_plan'],
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


def has_task_content(arguments, leads):
    """The old ``reasoning_has_task_content``: a ``source_lead`` of a verified_source_leads commission; and the
    source-grounded ``no_applicable_evidence`` declaration, which the old action check also let through."""
    if (arguments.get('evidence_processing') or {}).get('kind') == 'no_applicable_evidence':
        return True
    return leads and arguments.get('source_lead') is not None


def validate_selection(value, schema):
    validate_schema(value, schema)
    return value['selection']


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call, or reject it (no unit). An answer that selects no offered tool,
    arguments that do not fit its schema, or an empty reasoning commit without task content is invalid."""
    names = offered(ctx.settings)
    leads = summary['task']['kind'] == 'verified_source_leads'
    commit_schema = summary['reasoning_schema']
    schema = selection_schema(names, commit_schema, leads)
    try:
        selection = validate_selection(decode_response(response, schema), schema)
        name, arguments = selection['tool'], selection['arguments']
        if name == 'reason' and empty_commit(arguments['commit'], commit_schema) \
                and not has_task_content(arguments, leads):
            raise ValueError('empty_reasoning_commit')
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(name, {'arguments': arguments, 'scope': summary['scope'],
                           'page_source_ref': summary['literature_assignment']['page']['source_ref'],
                           'proposed_annotation_ref': summary['proposed_annotation_ref'],
                           'requested': summary['requested']})
