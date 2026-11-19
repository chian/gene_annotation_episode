"""The task: examine the assigned source through the access tools, commission a table, ordered-reading or
targeted-passage investigation of it, populate the source-cell families when the settings turn the population route
on, and commit reasoning on what it says together with its grading sheets (and, for a verified-source-leads
commission, a validated source lead).

Carried from the old task.py (``SourceTask.catalog`` / ``_tool_arguments`` / ``execute``), task_decision.py,
task_instructions.py, source_contracts.py (``_ROLE_INSTRUCTIONS``, ``_CHILDREN``, ``_TABLE``, ``_WINDOW``,
``_ACCESS_TOOLS``), source_references.py (``_within_source``), grading/experimental_interpretation.py and
grading/assay_subscoring.py of ``literature_page`` at ``97308b94c``. One unit is one model-selected tool call or one
commission of a child. The task always offers a unit and never ends the Episode: only the yield controller does.

Children. The old ``_CHILDREN['literature_page']`` is ``('literature_table', 'literature_ordered',
'literature_targeted')``: the slots below are those three roles under the names of their folders. The model selects
one slot with the child's objective, the page it reads and its selection; ``messages/msg_to_child.py`` builds the
commission. What a child returns is its credit and the controlled features of its sheets.

Tools offered: the access tools the A105 tool library implements; the population operations when
``settings['rate_population']`` is true, each under its flag (``literature_population_route``); ``reason``, the old
required-grading action (``literature_reasoning.reason``). The owner's grading instructions are part of every
decision's instructions. The old ``report`` tool is gone, and so are the copies of the owner's grader and reader
instructions that were parked in ``internal_summary.py``: the texts are in the library prompt files and reach the
model through ``grading_section``."""
from jsonschema import ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_experimental_contracts import (
    ExperimentalContractError)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_reasoning import (
    REASON_DESCRIPTION, empty_commit, reason as reasoning_unit, reason_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.experimental_activity_evidence.literature_grading_instructions import (
    grading_section)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.experimental_activity_evidence.literature_investigation_prompt import (
    INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_sequence_discovery import (
    references_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_population_route import (
    REPOSITORIES, population_entries, reader_cells, run_population as population_unit)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.experimental_activity_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import (
    identity, obj, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.experimental_database_records import (
    reader_schema as experimental_records_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.received_records import read_record_in_scope
from gene_annotation_episode.episodic_workflow.episode_support.tools.experimental_activity_evidence import (
    tools as access_library)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

from .goal import GOAL

CHILD_SLOTS = {
    'table_evidence_extraction': 'experimental_activity_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction',
    'source_coverage_improvement': 'experimental_activity_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement',
    'passage_evidence_extraction': 'experimental_activity_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction',
}
SERVICES = ()
INTEGER = {'type': 'integer', 'minimum': 0}
TEXT = {'type': 'string', 'minLength': 1}
REPRESENTATIONS = ['text', 'original', 'stdout', 'stderr']

# The access tools of the old ``_ACCESS_TOOLS`` that the A105 tool library implements; the descriptions and input
# schemas are the library's own (``A105ToolRegistry.catalog``).
ACCESS_NAMES = ('state.query', 'source.read', 'source.locate', 'source.sequence.references',
                'source.experimental.records', 'source.archive.members', 'source.archive.extract',
                'source.pdf.info', 'source.pdf.text', 'source.pdf.page')
ACCESS_DEFINITIONS = {
    **{name: access_library._DEFINITIONS[name] for name in ACCESS_NAMES
       if name not in ('source.sequence.references', 'source.experimental.records')},
    'source.sequence.references': (access_library._SEQUENCE_REFERENCES_DESCRIPTION, references_schema()),
    'source.experimental.records': (access_library._EXPERIMENT_RECORDS_DESCRIPTION, experimental_records_schema()),
}
# Tools whose source reads are bound to the records this episode holds (the old ``authorization``).
HELD_SOURCE_TOOLS = ('source.locate', 'source.sequence.references', 'source.experimental.records')
# Population operations whose argument tree names records that must lie inside the assigned source
# (the old ``_tool_arguments`` containment test of the population route).
SHEET_REF_TOOLS = ('literature.assay_grading.populate', 'literature.a105.aggregate',
                   'literature.measurement_validation.populate', 'literature.assay.components.populate',
                   'literature.ion_discrimination.populate')
SOURCE_REF_KEYS = ('source_ref', 'covariance_source_ref', 'activity_covariance_source_ref', 'model_source_ref',
                   'km_sheet_ref', 'data_source_ref', 'coordinate_source_ref', 'validation_source_ref')
# The population operations (library tool names): the reader families, the grader and the aggregation.
POPULATIONS = (*REPOSITORIES, 'literature.assay_grading.populate', 'literature.a105.aggregate')
TOOL_NAMES = {name: name.replace('.', '_') for name in (*ACCESS_NAMES, *POPULATIONS)}

HISTORY_START = 'On a fresh provider conversation,'
HISTORY_END = 'Do not execute native provider tools.'
HISTORY_GUIDANCE = ('Your own earlier read outcomes are shown to you as own_literature_outcomes; that page creates '
                    'no new action and does not execute or credit the historical work again.\n')
RETURN_GUIDANCE = ('\nWhat returns to your parent is your credit and the features code reads from the grading and '
                   'aggregation sheets saved (evidence type, quantity kind, measured effect, variance, log evidence '
                   'ratio, prediction model, criterion statuses); no prose of yours is returned. Selecting a tool '
                   'does not end your work: only the numerical controller does.')
LEAD_GUIDANCE = ('\nFor a verified_source_leads commission, a reason selection also carries source_lead: the '
                 'inspected source, its anchored reference subject, whether it is a useful lead for the original '
                 'question and the exact witnessed byte interval. A search hit or title alone verifies nothing.')

# The old ``_PAGE`` of a child (the page it reads), ``_WINDOW`` and ``_TABLE`` (what it reads of it).
PAGE_SCHEMA = obj({'source_ref': TEXT, 'representation': {'enum': REPRESENTATIONS}, 'artifact_ref': TEXT})
WINDOW_SCHEMA = obj({'source_ref': TEXT, 'representation': {'enum': REPRESENTATIONS}, 'offset': INTEGER,
                     'limit': {'type': 'integer', 'minimum': 1}})
WHERE_SCHEMA = obj({'column': {'type': 'string', 'pattern': '^[A-Z]+$'}, 'match': {'enum': ['equals', 'contains']},
                    'value': TEXT, 'case_sensitive': {'type': 'boolean'}}, required=['match', 'value'])
TABLE_SCHEMA = obj({'source_ref': TEXT, 'sheet_key': TEXT, 'offset': INTEGER, 'limit': INTEGER,
                    'header_row': {'type': 'integer', 'minimum': 1}, 'where': WHERE_SCHEMA},
                   required=['source_ref', 'sheet_key', 'offset', 'limit'])
OBJECTIVE = {'type': 'string', 'minLength': 1,
             'description': 'What the child should investigate in the selected part of the source and why'}
CHILD_ARGUMENTS = {
    'table_evidence_extraction': (
        'Investigate one selected table or sheet of a source of this assignment (a sheet with its rows, header and '
        'an optional literal row filter), or one byte window of it.',
        obj({'objective': OBJECTIVE, 'page': PAGE_SCHEMA, 'selection': {'anyOf': [TABLE_SCHEMA, WINDOW_SCHEMA]}})),
    'source_coverage_improvement': (
        'Read one source of this assignment in document order from one window, continuing, rereading or changing '
        'the window as the outcomes warrant.',
        obj({'objective': OBJECTIVE, 'page': PAGE_SCHEMA, 'selection': WINDOW_SCHEMA})),
    'passage_evidence_extraction': (
        'Investigate selected passages of a source of this assignment with their neighbouring context; separate '
        'spans stay separate.',
        obj({'objective': OBJECTIVE, 'page': PAGE_SCHEMA,
             'selection': obj({'spans': {'type': 'array', 'minItems': 1, 'items': WINDOW_SCHEMA}})})),
}

CHILD_GUIDANCE = ('\nSelect a child (a table, ordered-reading or targeted-passage investigation) with its objective, '
                  'the page it reads and its selection when that is the better way to examine the source; what it '
                  'returns is shown to you as child_returns. A child earns credit in this episode only through the '
                  'records it returns.')


def instructions(*, knowledge, leads, populations):
    """The old task_instructions.instructions: the investigation text, this episode's goal, the reasoning-commit
    requirement, the owner's grading section with the offered sheet families, the child text, the tool-knowledge
    text when it is offered. The decision-exchange, pending-delivery, wait and redeliver_report paragraphs are not
    carried: no such action exists."""
    text = replace_span(INSTRUCTIONS, HISTORY_START, HISTORY_END, HISTORY_GUIDANCE)
    text += '\n' + GOAL
    text += '\n' + REASONING_COMMIT_REQUIREMENT
    text += grading_section(populations)
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if leads:
        text += LEAD_GUIDANCE
    return text + CHILD_GUIDANCE + RETURN_GUIDANCE


def selection_schema(names, commit_schema, leads, settings):
    """What the model answers with: one tool and its arguments, or one child slot and its arguments (the old action
    schema: kinds ``tool`` and ``child``)."""
    tools = [obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']}, 'arguments': entry['input_schema']})
             for entry in catalog(names, commit_schema, leads, settings)]
    children = [obj({'kind': {'const': 'child'}, 'slot': {'const': slot}, 'arguments': CHILD_ARGUMENTS[slot][1]})
                for slot in CHILD_SLOTS]
    return obj({'selection': {'anyOf': [*tools, *children]}})


def offered(settings):
    """The tools offered now (library names): the access tools, the population operations under their flags,
    the reasoning commit."""
    return [*ACCESS_NAMES, *(entry['name'] for entry in population_entries(settings)), 'reason']


def catalog(names, commit_schema, leads, settings):
    """The tools the model is shown: python tool name, description and input schema (the old catalog; every input
    schema is projected through ``source_location_inputs``)."""
    population = {entry['name']: entry for entry in population_entries(settings)}
    entries = []
    for name in names:
        if name == 'reason':
            entries.append({'name': 'reason', 'description': REASON_DESCRIPTION,
                            'input_schema': reason_schema(commit_schema, leads)})
        elif name in population:
            entries.append({'name': TOOL_NAMES[name], 'description': population[name]['description'],
                            'input_schema': source_location_inputs(population[name]['input_schema'])})
        else:
            description, schema = ACCESS_DEFINITIONS[name]
            entries.append({'name': TOOL_NAMES[name], 'description': description,
                            'input_schema': source_location_inputs(schema)})
    return entries


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


def population_sources(name, arguments):
    """The records the argument tree of a population operation names (the old ``sources`` generator)."""
    if isinstance(arguments, dict):
        for key, child in arguments.items():
            if key == 'metadata_source_ref' and isinstance(child, str):
                yield child
                continue
            if ((key == 'sheet_ref' and name in SHEET_REF_TOOLS)
                    or (key == 'original_source_ref' and name == 'literature.binding.interaction.populate')
                    or key in SOURCE_REF_KEYS) and isinstance(child, str):
                yield child
            elif key == 'covariance_source_refs' and name == 'literature.measurement_comparison.populate':
                yield from child
            else:
                yield from population_sources(name, child)
    elif isinstance(arguments, list):
        for child in arguments:
            yield from population_sources(name, child)


def admitted(store, name, arguments, scope, root):
    """The old ``_tool_arguments``: the source the arguments name against the assigned page's source. A violation
    is a ``ContractError``. ``name`` is a library tool name."""
    if name in POPULATIONS:
        for reference in set(population_sources(name, arguments)):
            if not within_source(store, reference, root, scope):
                raise ContractError('literature_reading_outside_assigned_source', detail={'reference': reference})
        for key in ('visual_source_refs', 'covariance_source_refs'):
            for reference in arguments.get(key, ()):
                if not within_source(store, reference, root, scope):
                    raise ContractError('literature_reading_outside_assigned_source', detail={'reference': reference})
        return
    source_ref = arguments.get('source_ref')
    if name == 'source.archive.extract':
        source_ref = read_record_in_scope(store, arguments['member_ref'], scope, 'archive_member')['source_ref']
    if source_ref is not None and not within_source(store, source_ref, root, scope):
        raise ContractError('literature_reading_outside_assigned_source')


def invalid(name, arguments, ctx, error):
    """The old ``execute`` outcome for a contract error: an ``invalid`` outcome with feedback."""
    detail = {'detail': error.detail} if getattr(error, 'detail', None) else {}
    return {'status': 'invalid',
            'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': name, 'arguments': arguments}),
            'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'category': 'arguments_or_reference', 'code': str(error), **detail}}


async def run_access_tool(name, envelope, ctx):
    """Execute one access tool. A contract error is returned as an ``invalid`` outcome with ``arguments_or_reference``
    feedback, as the old ``execute`` did; the outcome is the unit's outcome like any other."""
    arguments, scope, root = envelope['arguments'], envelope['scope'], envelope['page_source_ref']
    try:
        validate_schema(arguments, source_location_inputs(ACCESS_DEFINITIONS[name][1]))
        admitted(ctx.store, name, arguments, scope, root)
    except (ContractError, ValidationError) as error:
        return invalid(name, arguments, ctx, error)
    registry = access_library.A105ToolRegistry(ctx.store, **ctx.settings['tool_registry'])
    permitted = tuple(ctx.store.refs()) if name in HELD_SOURCE_TOOLS else None
    try:
        return await registry.execute_async(name, arguments, scope=scope, operation_key=ctx.operation_key,
                                            permitted_record_refs=permitted)
    except CustodyError:
        raise
    except Exception as error:   # the old record_execution_failure: a failed selected operation is an outcome
        return failure_outcome(ctx.store, error, category='episode_execution', cause_code='selected_operation_failed')


def source_reader(ctx, scope, root):
    """The held bytes of a source below the assigned page (the old ``_materialize_text_arguments`` reader)."""
    def read_source(reference, representation):
        admitted(ctx.store, 'source.read', {'source_ref': reference, 'representation': representation}, scope, root)
        source = read_record_in_scope(ctx.store, reference, scope, 'source')
        artifact = source.get('artifact_ref' if representation == 'original' else 'text_ref')
        if artifact is None:
            raise ContractError('literature_source_representation_unavailable')
        return {'artifact_ref': artifact, 'content': ctx.store.get_artifact(artifact)}
    return read_source


def offered_populations(settings):
    return tuple(entry['name'] for entry in population_entries(settings))


async def run_population(name, envelope, ctx):
    """One population operation (the old ``execute`` population branch): the arguments are admitted against the
    offered schema and the assigned source, then the library's population route saves the sheet; a contract error
    is an ``invalid`` outcome that enters the iterator."""
    arguments, scope, root = envelope['arguments'], envelope['scope'], envelope['page_source_ref']
    try:
        validate_schema(arguments, source_location_inputs(
            {entry['name']: entry for entry in population_entries(ctx.settings)}[name]['input_schema']))
        admitted(ctx.store, name, arguments, scope, root)
        return population_unit(name, ctx.store, arguments, ctx.operation_key, scope=scope, page_source_ref=root,
                               assignment=envelope['assignment'], requested=envelope['requested'],
                               run_id=ctx.run_id, episode_id=ctx.episode_id, binding_path=ctx.binding_path,
                               offered=offered_populations(ctx.settings), read_source=source_reader(ctx, scope, root))
    except (ContractError, ExperimentalContractError, ValidationError) as error:
        return invalid(name, arguments, ctx, error)


def reason(arguments, ctx):
    """One reasoning unit: the interpretation, the grading sheets of its experiments and, for a
    verified-source-leads commission, the validated lead, committed together (``literature_reasoning.reason``).
    The grader reads the cells of a reader sheet this episode populated through that family's repository."""
    scope, root = arguments['scope'], arguments['page_source_ref']

    def authorize(reference, representation):
        admitted(ctx.store, 'source.read', {'source_ref': reference, 'representation': representation}, scope, root)
    read_cells = reader_cells(ctx.store, ctx.run_id, ctx.episode_id, ctx.binding_path, scope, arguments['assignment'],
                              offered_populations(ctx.settings))
    return reasoning_unit(ctx.store, scope, root, arguments['arguments'], ctx.operation_key,
                          arguments['proposed_annotation_ref'], authorize, read_cells)


async def state_query(arguments, ctx):
    return await run_access_tool('state.query', arguments, ctx)


async def source_read(arguments, ctx):
    return await run_access_tool('source.read', arguments, ctx)


async def source_locate(arguments, ctx):
    return await run_access_tool('source.locate', arguments, ctx)


async def source_sequence_references(arguments, ctx):
    return await run_access_tool('source.sequence.references', arguments, ctx)


async def source_experimental_records(arguments, ctx):
    return await run_access_tool('source.experimental.records', arguments, ctx)


async def source_archive_members(arguments, ctx):
    return await run_access_tool('source.archive.members', arguments, ctx)


async def source_archive_extract(arguments, ctx):
    return await run_access_tool('source.archive.extract', arguments, ctx)


async def source_pdf_info(arguments, ctx):
    return await run_access_tool('source.pdf.info', arguments, ctx)


async def source_pdf_text(arguments, ctx):
    return await run_access_tool('source.pdf.text', arguments, ctx)


async def source_pdf_page(arguments, ctx):
    return await run_access_tool('source.pdf.page', arguments, ctx)


async def literature_concentration_window_populate(arguments, ctx):
    return await run_population('literature.concentration_window.populate', arguments, ctx)


async def literature_measurement_comparison_populate(arguments, ctx):
    return await run_population('literature.measurement_comparison.populate', arguments, ctx)


async def literature_rate_populate(arguments, ctx):
    return await run_population('literature.rate.populate', arguments, ctx)


async def literature_rate_observations_populate(arguments, ctx):
    return await run_population('literature.rate.observations.populate', arguments, ctx)


async def literature_calibration_recovery_populate(arguments, ctx):
    return await run_population('literature.calibration.recovery.populate', arguments, ctx)


async def literature_product_coupling_populate(arguments, ctx):
    return await run_population('literature.product_coupling.populate', arguments, ctx)


async def literature_measurement_validation_populate(arguments, ctx):
    return await run_population('literature.measurement_validation.populate', arguments, ctx)


async def literature_rate_replicates_populate(arguments, ctx):
    return await run_population('literature.rate.replicates.populate', arguments, ctx)


async def literature_quantity_populate(arguments, ctx):
    return await run_population('literature.quantity.populate', arguments, ctx)


async def literature_assay_populate(arguments, ctx):
    return await run_population('literature.assay.populate', arguments, ctx)


async def literature_ratio_populate(arguments, ctx):
    return await run_population('literature.ratio.populate', arguments, ctx)


async def literature_binding_populate(arguments, ctx):
    return await run_population('literature.binding.populate', arguments, ctx)


async def literature_binding_model_populate(arguments, ctx):
    return await run_population('literature.binding.model.populate', arguments, ctx)


async def literature_transport_response_populate(arguments, ctx):
    return await run_population('literature.transport.response.populate', arguments, ctx)


async def literature_figure_populate(arguments, ctx):
    return await run_population('literature.figure.populate', arguments, ctx)


async def literature_rate_source_populate(arguments, ctx):
    return await run_population('literature.rate.source.populate', arguments, ctx)


async def literature_amount_populate(arguments, ctx):
    return await run_population('literature.amount.populate', arguments, ctx)


async def literature_optical_populate(arguments, ctx):
    return await run_population('literature.optical.populate', arguments, ctx)


async def literature_kinetic_populate(arguments, ctx):
    return await run_population('literature.kinetic.populate', arguments, ctx)


async def literature_kinetic_model_populate(arguments, ctx):
    return await run_population('literature.kinetic.model.populate', arguments, ctx)


async def literature_binding_interaction_populate(arguments, ctx):
    return await run_population('literature.binding.interaction.populate', arguments, ctx)


async def literature_binding_interaction_model_populate(arguments, ctx):
    return await run_population('literature.binding.interaction.model.populate', arguments, ctx)


async def literature_ion_discrimination_populate(arguments, ctx):
    return await run_population('literature.ion_discrimination.populate', arguments, ctx)


async def literature_channel_populate(arguments, ctx):
    return await run_population('literature.channel.populate', arguments, ctx)


async def literature_assay_components_populate(arguments, ctx):
    return await run_population('literature.assay.components.populate', arguments, ctx)


async def literature_assay_grading_populate(arguments, ctx):
    return await run_population('literature.assay_grading.populate', arguments, ctx)


async def literature_a105_aggregate(arguments, ctx):
    return await run_population('literature.a105.aggregate', arguments, ctx)


async def literature_product_partition_populate(arguments, ctx):
    return await run_population('literature.product_partition.populate', arguments, ctx)


async def literature_completion_time_populate(arguments, ctx):
    return await run_population('literature.completion_time.populate', arguments, ctx)


async def literature_active_site_populate(arguments, ctx):
    return await run_population('literature.active_site.populate', arguments, ctx)


async def literature_parent_depletion_populate(arguments, ctx):
    return await run_population('literature.parent_depletion.populate', arguments, ctx)


async def literature_stoichiometric_balance_populate(arguments, ctx):
    return await run_population('literature.stoichiometric_balance.populate', arguments, ctx)


async def literature_ratio_source_populate(arguments, ctx):
    return await run_population('literature.ratio.source.populate', arguments, ctx)


async def literature_controlled_response_source_v3_populate(arguments, ctx):
    return await run_population('literature.controlled_response.source_v3.populate', arguments, ctx)


async def literature_gel_populate(arguments, ctx):
    return await run_population('literature.gel.populate', arguments, ctx)


TOOLS = {
    'state_query': state_query, 'source_read': source_read, 'source_locate': source_locate,
    'source_sequence_references': source_sequence_references,
    'source_experimental_records': source_experimental_records, 'source_archive_members': source_archive_members,
    'source_archive_extract': source_archive_extract, 'source_pdf_info': source_pdf_info,
    'source_pdf_text': source_pdf_text, 'source_pdf_page': source_pdf_page,
    'literature_concentration_window_populate': literature_concentration_window_populate,
    'literature_measurement_comparison_populate': literature_measurement_comparison_populate,
    'literature_rate_populate': literature_rate_populate,
    'literature_rate_observations_populate': literature_rate_observations_populate,
    'literature_calibration_recovery_populate': literature_calibration_recovery_populate,
    'literature_product_coupling_populate': literature_product_coupling_populate,
    'literature_measurement_validation_populate': literature_measurement_validation_populate,
    'literature_rate_replicates_populate': literature_rate_replicates_populate,
    'literature_quantity_populate': literature_quantity_populate,
    'literature_assay_populate': literature_assay_populate,
    'literature_ratio_populate': literature_ratio_populate,
    'literature_binding_populate': literature_binding_populate,
    'literature_binding_model_populate': literature_binding_model_populate,
    'literature_transport_response_populate': literature_transport_response_populate,
    'literature_figure_populate': literature_figure_populate,
    'literature_rate_source_populate': literature_rate_source_populate,
    'literature_amount_populate': literature_amount_populate,
    'literature_optical_populate': literature_optical_populate,
    'literature_kinetic_populate': literature_kinetic_populate,
    'literature_kinetic_model_populate': literature_kinetic_model_populate,
    'literature_binding_interaction_populate': literature_binding_interaction_populate,
    'literature_binding_interaction_model_populate': literature_binding_interaction_model_populate,
    'literature_ion_discrimination_populate': literature_ion_discrimination_populate,
    'literature_channel_populate': literature_channel_populate,
    'literature_assay_components_populate': literature_assay_components_populate,
    'literature_assay_grading_populate': literature_assay_grading_populate,
    'literature_a105_aggregate': literature_a105_aggregate,
    'literature_product_partition_populate': literature_product_partition_populate,
    'literature_completion_time_populate': literature_completion_time_populate,
    'literature_active_site_populate': literature_active_site_populate,
    'literature_parent_depletion_populate': literature_parent_depletion_populate,
    'literature_stoichiometric_balance_populate': literature_stoichiometric_balance_populate,
    'literature_ratio_source_populate': literature_ratio_source_populate,
    'literature_controlled_response_source_v3_populate': literature_controlled_response_source_v3_populate,
    'literature_gel_populate': literature_gel_populate,
    'reason': reason}


def child_options():
    """The children the model may select: slot, description and the arguments it takes (the old
    ``child_option_information``, over this episode's own slots)."""
    return [{'slot': slot, 'description': CHILD_ARGUMENTS[slot][0], 'arguments': CHILD_ARGUMENTS[slot][1]}
            for slot in CHILD_SLOTS]



def decide(summary, feedback, ctx):
    """Ask the model for the next tool or child, shown the assignment, the custody of the source, its own read
    outcomes, the goal plan, the features of the sheets it saved and its children returned, the children's returns,
    the tools, the measured time and the yield table (the old decision state and inputs, over this episode's
    summary)."""
    names = offered(ctx.settings)
    leads = summary['task']['kind'] == 'verified_source_leads'
    knowledge_directory = ctx.settings['knowledge_library_directory']
    context = {'goal': GOAL, 'scope': summary['scope'], 'literature_assignment': summary['literature_assignment'],
               'literature_source_custody': summary['literature_source_custody'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_history_meaning': summary['literature_history_meaning'],
               'source_examination_goal': summary['source_examination_goal'],
               'credit_binding': summary['credit_binding'], 'last_local_outcome': summary['last_local_outcome'],
               'held_record_refs': summary['held_record_refs'], 'assay_sheets': summary['assay_sheets'],
               'aggregation_sheets': summary['aggregation_sheets'], 'child_returns': summary['child_returns'],
               'child_options': child_options(),
               'tools': catalog(names, summary['reasoning_schema'], leads, ctx.settings),
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    if ctx.settings['rate_population']:
        context['literature_experimental_work'] = {'version': 'literature_experimental_task_v1',
                                                    'aspect': 'source_experimental_evidence', 'evidence_axis': 'A105'}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['action_yields'],
        'tool_knowledge': None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(knowledge=context.get('tool_knowledge'), leads=leads,
                                                  populations=offered_populations(ctx.settings)), context,
                        generation_schema(selection_schema(names, summary['reasoning_schema'], leads, ctx.settings)))


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one child commission, or reject it (no unit). An answer that
    selects no offered tool or slot, arguments that do not fit its schema, or an empty reasoning commit without a
    source lead or a no-applicable-evidence declaration is invalid. What the child commission names is not checked
    here: a wrong commission fails where the child is built."""
    names = offered(ctx.settings)
    leads = summary['task']['kind'] == 'verified_source_leads'
    commit_schema = summary['reasoning_schema']
    schema = selection_schema(names, commit_schema, leads, ctx.settings)
    try:
        value = decode_response(response, schema)
        validate_schema(value, schema)
        selection = value['selection']
        if selection['kind'] == 'child':
            return ChildCall(selection['slot'], selection['arguments'])
        name, arguments = selection['tool'], selection['arguments']
        if name == 'reason' and empty_commit(arguments['commit'], commit_schema) and 'source_lead' not in arguments and (
                arguments.get('evidence_processing', {}).get('kind') != 'no_applicable_evidence'):
            raise ValueError('empty_reasoning_commit')
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(name, {'arguments': arguments, 'scope': summary['scope'],
                           'page_source_ref': summary['page']['source_ref'],
                           'assignment': summary['literature_assignment'], 'requested': summary['requested'],
                           'proposed_annotation_ref': summary['proposed_annotation_ref']})
