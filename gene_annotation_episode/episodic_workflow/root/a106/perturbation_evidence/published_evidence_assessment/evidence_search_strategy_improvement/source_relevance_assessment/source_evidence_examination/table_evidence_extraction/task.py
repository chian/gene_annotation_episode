"""The task: read the selected table or sheet of the assigned source, with its headers, conditions and footnotes,
through the access tools, commit reasoning on what they say (and, for a verified-source-leads
commission, validated source leads), and grade what it reads on the A106 sheets: the perturbation sheet and the other
operand sheets, the intervention grading sheet G1 (``literature_intervention_grading_populate``), the A106 final
subscore G2 (``literature_a106_finalize``) and the automatic source-bound score judgment that also writes G2
(``literature_a106_score_judgment``).

The base investigation text and the reasoning-commit requirement are the library's A106
``literature_investigation_prompt`` texts (the old ``INSTRUCTIONS`` source); the grader instructions (what each grader
grades, its criteria and how the owner fills the sheets) are part of the instructions of every decision.

Carried from the old task.py, task_decision.py, task_action.py, task_instructions.py,
scientific_interpretation.py, source_operations.py, source_catalog.py, source_admission.py, source_custody.py,
``grading/intervention_assessment.py`` and ``scoring/intervention_main_sheet.py``. One unit is one model-selected
tool call. The task always offers a unit and never ends the Episode: only the yield controller does. The episode has
no child and cannot search or fetch new sources (no acquisition tools). The old ``report`` tool is gone: what returns
to the parent is the credit and the controlled features code reads from the saved G1 and G2 sheets, not prose.

The A106 population route of the old episode is carried: the population operations of the old catalogue
(``literature.*.populate`` and ``literature.a106.finalize``) stay tools, named as the library names them with the dots
replaced by underscores. Which optional populations are offered is this episode's explicit setting
``literature_populations`` (a list of the library's ``OPTIONAL_POPULATIONS`` names, none by default, as the old
configuration defaulted every flag to False) with ``literature_evidence_origins`` (the evidence origin of each of
``ratio_source``, ``controlled_response`` and ``gel`` when offered). The library's sheet repositories
(``LiteratureRepositories``) run over the custody-scoped store of the unit (``ctx.store``)."""
from jsonschema import ValidationError

from episode_runtime import CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.perturbation_evidence.literature_experimental_contracts import (
    ExperimentalContractError)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_task_credit import (
    _resolve, lead_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.perturbation_evidence.literature_assay_inputs import (
    _Sources)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.perturbation_evidence.literature_input_spans import (
    is_consumed_read)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage import literature_population_route as route
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.perturbation_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.perturbation_evidence.literature_investigation_prompt import (
    INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.readers.perturbation_evidence.source_locations import (
    locate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_operations.perturbation_evidence.source_sequences import (
    scan_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.received_records import read_record_in_scope
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_discovery_values import (
    references_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import (
    RECORD_SCHEMAS, REF, REFS, identity, obj, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.experimental_database_records import (
    reader_schema as experimental_records_schema)
from gene_annotation_episode.episodic_workflow.episode_support.tools.perturbation_evidence.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)

from .goal import GOAL

CHILD_SLOTS = {}
SERVICES = ()
ROLE = 'literature_table'      # the old role of this reading (the library repositories read it)

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

REASON_DESCRIPTION = ('Commit a typed scientific reasoning over the selected table or sheet and the records you hold: '
                      'extracted terms, source subjects, contexts, observations, hypotheses and assessments, each '
                      'with its exact source anchor. A commit with every section empty is rejected.')
HISTORY_START = 'On a fresh provider conversation,'
HISTORY_END = 'Do not execute native provider tools.'
HISTORY_GUIDANCE = ('Your own earlier read outcomes are shown to you as own_literature_outcomes; that page creates '
                    'no new action and does not execute or credit the historical work again.\n')
INPUT_LIST_GUIDANCE = ('\nYour input list (input_list) holds the spans of the selected region still to be processed, in '
                       'document order: [start, end] byte offsets of the selected window, or row offsets (counting '
                       'matching rows) of the selected table. A span is consumed once you have read it and committed '
                       'your reasoning after the read (consumed_inputs lists the consumed spans); a read that only '
                       'repeats consumed spans is not offered again.')
LEAD_GUIDANCE = ('\nFor a verified_source_leads commission, a reason selection also carries source_lead: the '
                 'inspected source, its anchored reference subject, whether it is a useful lead for the original '
                 'question and the exact witnessed byte interval. A search hit or title alone verifies nothing.')



def instructions(*, knowledge, leads):
    """The old task_instructions.instructions: the investigation text, the reasoning-commit requirement, this
    episode's goal, the tool-knowledge text when it is offered. The decision-exchange paragraph, the
    pending-delivery paragraph, the wait paragraphs and the redeliver_report text are not carried: no such
    action exists."""
    text = replace_span(INSTRUCTIONS, HISTORY_START, HISTORY_END, HISTORY_GUIDANCE)
    text += '\n' + GOAL
    text += '\n' + REASONING_COMMIT_REQUIREMENT
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if leads:
        text += LEAD_GUIDANCE
    return text + INPUT_LIST_GUIDANCE + route.GRADER_SECTION + route.RETURN_GUIDANCE


def offered(settings, opened):
    """The access tools offered now: execution_estimate only with timing statistics configured; then the population
    tools (``open_population``, the opened population operation, the automatic score judgment) and the reasoning
    commit."""
    tools = [name for name in LIBRARY_NAMES
             if name != 'execution_estimate' or settings.get('tool_registry', {}).get('native_statistics') is not None]
    return tools + route.offered_population_tools(opened) + ['reason']


def reason_schema(commit_schema, leads):
    """The old reasoning_action_schema (the reason selection without the assay-grading logic of the
    population route): the typed commit and, for a verified_source_leads commission, a source_lead."""
    properties = {'commit': commit_schema}
    if leads:
        properties['source_lead'] = lead_schema()
    return source_location_inputs(obj(properties, required=['commit']))


def catalog(names, commit_schema, leads, settings):
    """The tools the model is shown: name, description and input schema (the old catalog; every input schema
    is projected through source_location_inputs)."""
    entries = []
    population_tools = {route.OPEN, route.JUDGMENT, *route.POPULATION_NAMES}
    for name in names:
        if name in population_tools:
            entries.append(route.population_tool_entry(name, settings))
        elif name == 'reason':
            entries.append({'name': 'reason', 'description': REASON_DESCRIPTION,
                            'input_schema': reason_schema(commit_schema, leads)})
        else:
            entries.append({'name': name, 'description': DESCRIPTIONS[LIBRARY_NAMES[name]],
                            'input_schema': source_location_inputs(INPUT_SCHEMAS[LIBRARY_NAMES[name]])})
    return entries


def selection_schema(names, commit_schema, leads, settings):
    """What the model answers with: one tool and its arguments (the old action schema)."""
    return obj({'selection': {'anyOf': [obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']},
                                             'arguments': entry['input_schema']})
                                        for entry in catalog(names, commit_schema, leads, settings)]}})


def admitted(store, name, arguments, scope, root, selection=None):
    """The old ``_tool_arguments`` of an access tool: the arguments against the offered schema, the source they name
    against the assigned page's source and, when the selection is a table (it has a ``sheet_key``),
    ``source.xlsx.rows`` against that sheet (this episode's own rule). A violation is a ``ContractError``."""
    if name == 'source.xlsx.rows' and selection is not None and 'sheet_key' in selection:
        if arguments['sheet_key'] != selection['sheet_key']:
            raise ContractError('literature_table_sheet_mismatch')
    validate_schema(arguments, source_location_inputs(INPUT_SCHEMAS[name]))
    selected = arguments['arguments'] if name == 'execution.estimate' else arguments
    source_ref = selected.get('source_ref')
    if name == 'source.archive.extract':
        source_ref = read_record_in_scope(store, arguments['member_ref'], scope, 'archive_member')['source_ref']
    if source_ref is not None and not route.within_source(store, source_ref, root, scope):
        raise ContractError('literature_reading_outside_assigned_source')


async def run_access_tool(name, envelope, ctx):
    """Execute one access tool. A contract error is returned as an ``invalid`` outcome with ``arguments_or_reference``
    feedback, as the old ``execute`` did; the outcome is the unit's outcome like any other."""
    arguments, scope, root = envelope['arguments'], envelope['scope'], envelope['page_source_ref']
    try:
        admitted(ctx.store, name, arguments, scope, root, envelope['selection'])
    except (ContractError, ValidationError) as error:
        return route.invalid_outcome(ctx, name, arguments, error)
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


def literature_concentration_window_populate(arguments, ctx):
    return route.populate('literature.concentration_window.populate', arguments, ctx, ROLE, GOAL)


def literature_measurement_comparison_populate(arguments, ctx):
    return route.populate('literature.measurement_comparison.populate', arguments, ctx, ROLE, GOAL)


def literature_product_coupling_populate(arguments, ctx):
    return route.populate('literature.product_coupling.populate', arguments, ctx, ROLE, GOAL)


def literature_measurement_validation_populate(arguments, ctx):
    return route.populate('literature.measurement_validation.populate', arguments, ctx, ROLE, GOAL)


def literature_ion_discrimination_populate(arguments, ctx):
    return route.populate('literature.ion_discrimination.populate', arguments, ctx, ROLE, GOAL)


def literature_channel_populate(arguments, ctx):
    return route.populate('literature.channel.populate', arguments, ctx, ROLE, GOAL)


def literature_assay_components_populate(arguments, ctx):
    return route.populate('literature.assay.components.populate', arguments, ctx, ROLE, GOAL)


def literature_rate_populate(arguments, ctx):
    return route.populate('literature.rate.populate', arguments, ctx, ROLE, GOAL)


def literature_calibration_recovery_populate(arguments, ctx):
    return route.populate('literature.calibration.recovery.populate', arguments, ctx, ROLE, GOAL)


def literature_rate_observations_populate(arguments, ctx):
    return route.populate('literature.rate.observations.populate', arguments, ctx, ROLE, GOAL)


def literature_rate_replicates_populate(arguments, ctx):
    return route.populate('literature.rate.replicates.populate', arguments, ctx, ROLE, GOAL)


def literature_rate_source_populate(arguments, ctx):
    return route.populate('literature.rate.source.populate', arguments, ctx, ROLE, GOAL)


def literature_quantity_populate(arguments, ctx):
    return route.populate('literature.quantity.populate', arguments, ctx, ROLE, GOAL)


def literature_assay_populate(arguments, ctx):
    return route.populate('literature.assay.populate', arguments, ctx, ROLE, GOAL)


def literature_amount_populate(arguments, ctx):
    return route.populate('literature.amount.populate', arguments, ctx, ROLE, GOAL)


def literature_completion_time_populate(arguments, ctx):
    return route.populate('literature.completion_time.populate', arguments, ctx, ROLE, GOAL)


def literature_active_site_populate(arguments, ctx):
    return route.populate('literature.active_site.populate', arguments, ctx, ROLE, GOAL)


def literature_parent_depletion_populate(arguments, ctx):
    return route.populate('literature.parent_depletion.populate', arguments, ctx, ROLE, GOAL)


def literature_stoichiometric_balance_populate(arguments, ctx):
    return route.populate('literature.stoichiometric_balance.populate', arguments, ctx, ROLE, GOAL)


def literature_intervention_grading_populate(arguments, ctx):
    return route.populate('literature.intervention_grading.populate', arguments, ctx, ROLE, GOAL)


def literature_a106_finalize(arguments, ctx):
    return route.populate('literature.a106.finalize', arguments, ctx, ROLE, GOAL)


def literature_product_partition_populate(arguments, ctx):
    return route.populate('literature.product_partition.populate', arguments, ctx, ROLE, GOAL)


def literature_optical_populate(arguments, ctx):
    return route.populate('literature.optical.populate', arguments, ctx, ROLE, GOAL)


def literature_kinetic_populate(arguments, ctx):
    return route.populate('literature.kinetic.populate', arguments, ctx, ROLE, GOAL)


def literature_kinetic_model_populate(arguments, ctx):
    return route.populate('literature.kinetic.model.populate', arguments, ctx, ROLE, GOAL)


def literature_binding_interaction_populate(arguments, ctx):
    return route.populate('literature.binding.interaction.populate', arguments, ctx, ROLE, GOAL)


def literature_binding_interaction_model_populate(arguments, ctx):
    return route.populate('literature.binding.interaction.model.populate', arguments, ctx, ROLE, GOAL)


def literature_ratio_populate(arguments, ctx):
    return route.populate('literature.ratio.populate', arguments, ctx, ROLE, GOAL)


def literature_ratio_source_populate(arguments, ctx):
    return route.populate('literature.ratio.source.populate', arguments, ctx, ROLE, GOAL)


def literature_controlled_response_source_v3_populate(arguments, ctx):
    return route.populate('literature.controlled_response.source_v3.populate', arguments, ctx, ROLE, GOAL)


def literature_gel_populate(arguments, ctx):
    return route.populate('literature.gel.populate', arguments, ctx, ROLE, GOAL)


def literature_binding_populate(arguments, ctx):
    return route.populate('literature.binding.populate', arguments, ctx, ROLE, GOAL)


def literature_binding_model_populate(arguments, ctx):
    return route.populate('literature.binding.model.populate', arguments, ctx, ROLE, GOAL)


def literature_transport_response_populate(arguments, ctx):
    return route.populate('literature.transport.response.populate', arguments, ctx, ROLE, GOAL)


def literature_perturbation_populate(arguments, ctx):
    return route.populate('literature.perturbation.populate', arguments, ctx, ROLE, GOAL)


def literature_figure_populate(arguments, ctx):
    return route.populate('literature.figure.populate', arguments, ctx, ROLE, GOAL)


def validate_source_lead(store, lead, outcome, proposed):
    """The old library ``validate_lead`` re-expressed on custody (private copy; library candidate): the lead's
    identity and exact source witness against the records this episode holds. A violation is a ``ContractError``."""
    value = _resolve(lead, outcome.get('aliases', {}))
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


def reason(arguments, ctx):
    """Commit the model's typed reasoning (the old ``Store.commit_reasoning`` path of ``execute``; the owner of
    interpretation accounts is named by the system). With a ``source_lead`` the commit and the validated lead are
    one transaction (the old ``execute_reasoning``): a lead that does not hold returns an ``invalid`` outcome and
    nothing is committed."""
    envelope = arguments
    arguments, scope, root = envelope['arguments'], envelope['scope'], envelope['page_source_ref']
    store = ctx.store
    if 'source_lead' not in arguments:
        return store.commit_reasoning(arguments['commit'], scope, ctx.operation_key)
    try:
        witness = arguments['source_lead']['witness']
        admitted(store, 'source.read', {'source_ref': witness['source_ref'], 'representation': witness['representation'],
                                        'offset': witness['start'], 'limit': witness['end'] - witness['start']},
                 scope, root)
        with store.transaction():
            result = store.commit_reasoning(arguments['commit'], scope, ctx.operation_key)
            if result['status'] not in ('completed', 'partial'):
                return result
            lead = validate_source_lead(store, arguments['source_lead'], result, envelope['proposed_annotation_ref'])
            return {**result, 'literature_source_lead': lead}
    except (ContractError, ExperimentalContractError) as error:
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'source_lead', 'code': getattr(error, 'code', str(error))}}


def open_population(arguments, ctx):
    return route.open_population(arguments)


async def literature_a106_score_judgment(arguments, ctx):
    return await route.score_judgment(arguments, ctx, ROLE, GOAL)


TOOLS = {'state_query': state_query, 'source_read': source_read, 'source_locate': source_locate,
         'source_sequence_scan': source_sequence_scan, 'source_sequence_references': source_sequence_references,
         'source_experimental_records': source_experimental_records, 'image_view': image_view,
         'source_archive_members': source_archive_members, 'source_archive_extract': source_archive_extract,
         'source_xlsx_sheets': source_xlsx_sheets, 'source_xlsx_rows': source_xlsx_rows,
         'source_pdf_info': source_pdf_info, 'source_pdf_text': source_pdf_text, 'source_pdf_page': source_pdf_page,
         'execution_estimate': execution_estimate, 'reason': reason,
         'literature_a106_score_judgment': literature_a106_score_judgment, 'open_population': open_population,
         **{name: globals()[name] for name in route.POPULATION_NAMES}}


def decide(summary, feedback, ctx):
    """Ask the model for the next tool, shown the assignment, the custody of the source, its own read outcomes,
    the controlled features of the A106 sheets it saved, the latest image it looked at, the tools, the measured time and the yield table
    (the old decision state and inputs, over this episode's summary)."""
    names = offered(ctx.settings, summary['opened_population'])
    leads = summary['task']['kind'] == 'verified_source_leads'
    knowledge_directory = ctx.settings.get('knowledge_library_directory')
    context = {'goal': GOAL, 'scope': summary['scope'], 'literature_assignment': summary['literature_assignment'],
               'literature_source_custody': summary['literature_source_custody'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_history_meaning': summary['literature_history_meaning'],
               'input_list': summary['input_list'], 'consumed_inputs': summary['consumed_inputs'],
               'credit_binding': summary['credit_binding'], 'visual_evidence': summary['visual_evidence'],
               'last_local_outcome': summary['last_local_outcome'], 'held_record_refs': summary['held_record_refs'],
               'a106_findings': summary['a106_findings'],
               'source_lead_dispositions': summary['source_lead_dispositions'],
               'tools': catalog(names, summary['reasoning_schema'], leads, ctx.settings),
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['action_yields'],
        'tool_knowledge': None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(knowledge=context.get('tool_knowledge'), leads=leads), context,
                        generation_schema(selection_schema(names, summary['reasoning_schema'], leads, ctx.settings)))


def empty_commit(commit, commit_schema):
    """The old empty-reasoning test: every section the schema names is present or absent and none has a row."""
    return (set(commit_schema.get('required', commit_schema['properties'])) <= set(commit)
            <= set(commit_schema['properties']) and all(value == [] for value in commit.values()))


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call, or reject it (no unit). An answer that selects no offered tool,
    arguments that do not fit its schema, or an empty reasoning commit without a source lead is invalid."""
    names = offered(ctx.settings, summary['opened_population'])
    leads = summary['task']['kind'] == 'verified_source_leads'
    commit_schema = summary['reasoning_schema']
    schema = selection_schema(names, commit_schema, leads, ctx.settings)
    try:
        selection = validate_selection(decode_response(response, schema), schema)
        name, arguments = selection['tool'], selection['arguments']
        if name == 'reason' and empty_commit(arguments['commit'], commit_schema) and 'source_lead' not in arguments:
            raise ValueError('empty_reasoning_commit')
        if is_consumed_read(summary['literature_assignment']['selection'], name, arguments, summary['consumed_inputs']):
            raise ValueError('input_already_consumed')   # the selected span was read and committed: not offered again
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(name, {'arguments': arguments, 'scope': summary['scope'],
                           'page_source_ref': summary['literature_assignment']['page']['source_ref'],
                           'assignment': summary['literature_assignment'],
                           'selection': summary['literature_assignment']['selection'],
                           'proposed_annotation_ref': summary['proposed_annotation_ref']})


def validate_selection(value, schema):
    validate_schema(value, schema)
    return value['selection']
