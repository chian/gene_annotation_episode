"""The task: read the assigned source in document order from the starting window through the access tools (continue,
reread, change the examined window), populate the result sheets the commission asks for when the settings turn the
population route on, and commit interpretations together with their grading sheets (and, for a
verified-source-leads commission, a validated source lead).

Carried from the old ``task.py``, ``task_decision.py``, ``task_instructions.py``, ``decision_presentation.py``,
``source_operations.py``, ``source_references.py``, ``source_contracts.py``, ``grading/experimental_interpretation.py``
and ``grading/assay_subscoring.py`` of ``literature_ordered`` at ``97308b94c``. One unit is one model-selected tool
call. The task always offers a unit and never ends the Episode: only the yield controller does. The episode has no
child and cannot search or fetch new sources.

Tools offered: the access tools the A105 tool library implements; the population operations when
``settings['rate_population']`` is true, each under its flag (``literature_population_route``); ``reason``, the old
required-grading action (``literature_reasoning.reason``). The owner's grading instructions are part of every
decision's instructions, with the filling instruction of each offered sheet family. What returns to the parent is
the controlled features code reads from the saved sheets.

Settings read here (``ctx.settings``): ``tool_registry``, ``rate_population`` and the family flags,
``knowledge_library_directory`` and ``launch_instruction_directory``."""
from jsonschema import ValidationError

from episode_runtime import CustodyError, ModelRequest, Rejected, ToolCall

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
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)

from .credit import classify_unknowns
from .goal import GOAL

CHILD_SLOTS = {}
SERVICES = ()
ROLE_INSTRUCTION = ('Investigate the source in document order as useful for the assigned question. Use returned UTF-8 '
                    'byte continuations and retain representation identity. Decide whether to continue, reread, '
                    'change the examined window or interpret obtained evidence from actual outcomes.')
GOAL_INSTRUCTIONS = (ROLE_INSTRUCTION
                     + "\nThis is an iterative scientific investigation in the shared Episode loop. Earlier outcomes "
                       "and admitted child forms inform later choices; no child order, reading quota or "
                       "complete-document requirement is prescribed. A one-off search/read is an ordinary tool. A "
                       "supplied reading selector is context, not an automatically executed action. Preserve the "
                       "source's actual subject, experimental conditions, representation, version and UTF-8 byte "
                       "anchors. Distinguish source claims from their applicability to the fixed target. Negative "
                       "findings and qualifications can advance the investigation. Commit interpretations with the "
                       "common reasoning action and update only the parent's declared typed form in that same work "
                       "call. Navigation, byte coverage and repeated reading earn no scientific credit by themselves. "
                       "The commissioned task's own yield settings guide continuation.")

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

# The span of the library text that describes actions this episode does not have (the report_update form, the
# redeliver_report action, episode.history) is replaced by what the episode has instead.
HISTORY_START = 'A commissioned child returns ONLY the parent\'s typed form.'
HISTORY_END = 'Do not execute native provider tools.'
HISTORY_GUIDANCE = ('Your own earlier read outcomes are shown to you as own_literature_outcomes; that page creates '
                    'no new action and does not execute or credit the historical work again.\n')
# The first thing the model reads: what this episode is for, what the commissioner asked, which tools exist and when
# each is the right choice, and what earns credit. The objective values are the vocabulary of
# ``messages/read_from_parent.py`` (``OBJECTIVES``); the value of this commission is shown in ``context.commission``.
BRIEF = (
    'THIS EPISODE: report (A105 experimental evidence). You read ONE source in document order, '
    'starting at the window context.commission.selection (offset/limit of the page '
    'context.literature_assignment.page), and grade the experiments you meet, for ONE commissioned literature task '
    '(context.literature_assignment.literature_task) about ONE proposed annotation '
    '(context.commission.proposed_annotation_ref). You have no children and cannot search for or fetch other '
    'sources.\n'
    'WHAT THE COMMISSIONER ASKED: context.commission.objective is the commissioner\'s objective. It is one value of a '
    'fixed vocabulary; context.commission.objective_meaning states it.\n'
    '- grade_reported_experiment: the source reports a commissioned experiment with its measurements from the '
    'starting window on. Read in order until you have it, then commit one reason that grades each commissioned '
    'experiment read, with every quantity the source states for it entered in the grading.\n'
    '- find_applicable_evidence: whether the source holds applicable evidence is open. Read in order from the '
    'starting window; grade each applicable experiment or result in a reason as you meet it, and commit a reason '
    'with evidence_processing.kind=no_applicable_evidence and the exact examined spans for what holds none.\n'
    'YOUR TOOLS (context.tools):\n'
    '- source_read reads a byte window of the source. Start at the selection; continue with the next_query a read '
    'returns, reread or change the window as the outcomes warrant.\n'
    '- source_locate returns the exact byte interval of a literal phrase you have read. Use it for the byte offsets a '
    'grading operand or an anchor needs.\n'
    '- state_query reads records you hold, for example the commissioned experiment reference and its anchor.\n'
    '- source_pdf_info, source_pdf_text, source_pdf_page, source_archive_members, source_archive_extract, '
    'source_sequence_references and source_experimental_records apply when the source is held in that '
    'representation.\n'
    '- the literature_*_populate tools and literature_a105_aggregate, when context.tools lists them, save a reader, '
    'grading or aggregation sheet of their family.\n'
    '- reason commits your interpretation (the observation and the assessment of each experiment) together with its '
    'grading sheet; an interpretation is not saved without its sheet.\n'
    'CREDIT (context.credit_binding, context.action_yields): one credit_unit for each answer to the commissioned '
    'task. For an a105_experiments task the answer is the current grading sheet of each commissioned experiment (the '
    'experiment_ref and assay_type of literature_task.experiments), saved together with the assessment it grades. '
    'It earns the share of the unit that its fields earn: the nine quantities, the prediction model and the criteria '
    'of its assay type. A field that was entered earns its share. A field left null or unknown is classified when '
    'the sheet is saved, automatically and with no action of yours, against the source windows read: justified when '
    'those windows do not state it, which is a correct partial grading and earns its share; unjustified when they '
    'state it, which earns nothing. A field left unknown with no window read earns nothing. context.assay_sheets '
    'shows the counts of each sheet (graded_field_count, unknown_field_count, justified_unknown_count, '
    'unjustified_unknown_count) and the outcome of a reason lists the classified fields; a later reason that grades '
    'the experiment again with the unjustified fields entered earns the rest. So enter every quantity the source '
    'states for an experiment (see "Entering the quantities of a grading" below) and resolve every criterion it '
    'settles; leave null or unknown only what it does not state. Do not write a value or a support the source does '
    'not give to make a sheet look complete: an honest unknown is a correct grading and earns its share, an invented '
    'support is a wrong grading. Reading, byte coverage and locating earn nothing by themselves. Only the numerical '
    'controller ends the episode.\n\n')
RETURN_GUIDANCE = ('\nWhat returns to your parent is your credit and the features code reads from the grading and '
                   'aggregation sheets saved (evidence type, quantity kind, measured effect, variance, log evidence '
                   'ratio, prediction model, criterion statuses); no prose of yours is returned. Selecting a tool '
                   'does not end your work: only the numerical controller does.')
LEAD_GUIDANCE = ('\nFor a verified_source_leads commission, a reason selection also carries source_lead: the '
                 'inspected source, its anchored reference subject, whether it is a useful lead for the original '
                 'question and the exact witnessed byte interval. A search hit or title alone verifies nothing.')


def instructions(*, knowledge, launch, leads, populations):
    """This episode's brief first (what it is for, what the commissioner asked, the tools and when each is the right
    choice, what earns credit), then the old ``task_instructions.instructions``: the literature investigation text,
    this episode's goal, the reasoning-commit requirement, the owner's grading section with the offered sheet
    families, the tool-knowledge and launch-instruction texts when they are offered. The report_update, redelivery
    and ``episode.history`` paragraphs describe actions that no longer exist and are replaced."""
    text = BRIEF + replace_span(INSTRUCTIONS, HISTORY_START, HISTORY_END, HISTORY_GUIDANCE)
    text += '\n' + GOAL_INSTRUCTIONS
    text += '\n' + REASONING_COMMIT_REQUIREMENT
    text += grading_section(populations)
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if launch is not None:
        text += LAUNCH_INSTRUCTIONS
    if leads:
        text += LEAD_GUIDANCE
    return text + RETURN_GUIDANCE


def selection_schema(names, commit_schema, leads, settings):
    """What the model answers with: one tool and its arguments (the old action schema)."""
    return obj({'selection': {'anyOf': [obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']},
                                             'arguments': entry['input_schema']})
                                        for entry in catalog(names, commit_schema, leads, settings)]}})


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


async def reason(arguments, ctx):
    """One reasoning unit: the interpretation, the grading sheets of its experiments and, for a
    verified-source-leads commission, the validated lead, committed together (``literature_reasoning.reason``);
    then, as the tail of the same unit, the classification of the fields each saved sheet leaves unknown against
    the source windows this episode read (``credit.classify_unknowns``: credit assignment, automatic, no tool).
    The grader reads the cells of a reader sheet this episode populated through that family's repository."""
    scope, root = arguments['scope'], arguments['page_source_ref']

    def authorize(reference, representation):
        admitted(ctx.store, 'source.read', {'source_ref': reference, 'representation': representation}, scope, root)
    read_cells = reader_cells(ctx.store, ctx.run_id, ctx.episode_id, ctx.binding_path, scope, arguments['assignment'],
                              offered_populations(ctx.settings))
    outcome = reasoning_unit(ctx.store, scope, root, arguments['arguments'], ctx.operation_key,
                             arguments['proposed_annotation_ref'], authorize, read_cells)
    return await classify_unknowns(outcome, scope, arguments['examined_windows'], ctx)


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


def offered_actions(summary, ctx):
    """The action types offered at this decision, from the same ``offered`` that ``decide`` and ``action`` use, under
    the names the runner records (the tool's python name; ``reason``)."""
    return [TOOL_NAMES.get(name, name) for name in offered(ctx.settings)]


def decide(summary, feedback, ctx):
    """Ask the model for the next tool, shown the assignment, the custody of the source, its own read outcomes,
    the goal plan, the features of the sheets it saved, the tools, the measured time and the yield table (the old
    decision state and inputs, over this episode's summary)."""
    names = offered(ctx.settings)
    leads = summary['task']['kind'] == 'verified_source_leads'
    knowledge_directory = ctx.settings['knowledge_library_directory']
    launch_directory = ctx.settings['launch_instruction_directory']
    context = {'commission': summary['commission'], 'goal': GOAL, 'scope': summary['scope'],
               'literature_assignment': summary['literature_assignment'],
               'literature_source_custody': summary['literature_source_custody'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_history_meaning': summary['literature_history_meaning'],
               'literature_goal_plan': summary['literature_goal_plan'],
               'credit_binding': summary['credit_binding'], 'last_local_outcome': summary['last_local_outcome'],
               'held_record_refs': summary['held_record_refs'], 'assay_sheets': summary['assay_sheets'],
               'aggregation_sheets': summary['aggregation_sheets'],
               'tools': catalog(names, summary['reasoning_schema'], leads, ctx.settings),
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['action_yields'],
        'tool_knowledge': None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context(),
        'launch_instruction_library': (None if launch_directory is None
                                       else LaunchInstructions(launch_directory).context())},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(knowledge=context.get('tool_knowledge'),
                                                  launch=context.get('launch_instruction_library'), leads=leads,
                                                  populations=offered_populations(ctx.settings)), context,
                        generation_schema(selection_schema(names, summary['reasoning_schema'], leads, ctx.settings)))


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call, or reject it (no unit). An answer that selects no offered tool,
    arguments that do not fit its schema, or an empty reasoning commit without a source lead or a
    no-applicable-evidence declaration is invalid."""
    names = offered(ctx.settings)
    leads = summary['task']['kind'] == 'verified_source_leads'
    commit_schema = summary['reasoning_schema']
    schema = selection_schema(names, commit_schema, leads, ctx.settings)
    try:
        value = decode_response(response, schema)
        validate_schema(value, schema)
        name, arguments = value['selection']['tool'], value['selection']['arguments']
        if name == 'reason' and empty_commit(arguments['commit'], commit_schema) and 'source_lead' not in arguments and (
                arguments.get('evidence_processing', {}).get('kind') != 'no_applicable_evidence'):
            raise ValueError('empty_reasoning_commit')
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(name, {'arguments': arguments, 'scope': summary['scope'],
                           'page_source_ref': summary['literature_assignment']['page']['source_ref'],
                           'assignment': summary['literature_assignment'], 'requested': summary['requested'],
                           'proposed_annotation_ref': summary['proposed_annotation_ref'],
                           'examined_windows': summary['examined_windows']})
