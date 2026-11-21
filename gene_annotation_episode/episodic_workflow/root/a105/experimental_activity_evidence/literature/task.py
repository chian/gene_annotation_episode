"""The task: search for and read the published sources the assigned question needs through the access and
acquisition tools, commission the search-strategy investigation when that narrower question warrants iteration,
commit reasoning on what the sources say (the interpretation and its grading sheets in one unit, and for a
verified-source-leads commission validated source leads), populate the source-cell families when the settings turn
the population route on. The finding returned is the controlled features of the saved grading sheets.

Carried from the old task.py (``LiteratureOperations.catalog`` / ``execute``), source_operations.py
(``LiteratureSourceOperations._tool_arguments`` / ``_materialize_text_arguments``), task_decision.py,
task_instructions.py, source_contracts.py (``_ROLE_INSTRUCTIONS``, ``_CHILDREN``, ``_PAGE``, ``_WINDOW``,
``_TABLE``, ``_ACCESS_TOOLS``, ``_ACQUISITION_TOOLS``, ``_CATALOG_ORDER``),
grading/experimental_interpretation.py (``reasoning_action_schema``, ``reasoning_has_task_content``,
``execute_reasoning``), grading/assay_subscoring.py and the old credit.py lead functions (``lead_schema``,
``validate_lead``, private copies). One unit is one model-selected tool call or one commission of the child. The task
always offers a unit and never ends the Episode: only the yield controller does.

Child. The old ``_CHILDREN['literature']`` is ``('literature_strategy',)``: the slot below is that role under the
name of its folder. The model selects it with the child's objective and the sources the strategy investigation is to
build on (sources this episode holds: the sources it was given and the sources its own searches acquired);
``messages/msg_to_child.py`` builds the commission. A child is a unit like any other: what it earns in this episode is
this episode's own credit.

Tools offered. The access tools are the ones the A105 tool library implements (its ``A105ToolRegistry.catalog``
intersected with the old ``_ACCESS_TOOLS``): ``source.sequence.scan``, ``image.view``, ``source.xlsx.sheets``,
``source.xlsx.rows`` and ``execution.estimate`` have no A105 implementation and are not offered. The acquisition tools
are the old ``_ACQUISITION_TOOLS`` (literature search and read, sequence identity, NCBI search narrowed to ``pubmed``,
the three PMC operations and every experimental-database operation); this episode is offered them, as is its child.
The 35 ``literature.*`` population operations are offered when ``settings['rate_population']`` is true, each under
its flags (the old ``rate_population`` configuration, its other flags are settings of the same names, default
false). A literature assignment names no page, so the old containment of source reads inside a page
(``_within_source``) does not apply.

A105 evidence processing (AGENTS.md, "Required literature evidence processing"): the ``reason`` tool is the old
required-grading action. Its selection carries ``evidence_processing`` (graded gradings, or a source-grounded
``no_applicable_evidence``); the library's ``literature_required_grading.execute`` commits the interpretation and
saves its subscoring sheets together before any credit, and every assessment carries its typed
``investigation_finding`` (a record of this episode): ``literature_reasoning.reason`` on the custody-scoped store.
What returns to the parent is the controlled features code reads from the saved sheets (own and returned by the
child), never prose; the old ``report`` tool is gone. The owner's grading instructions are part of every decision's
instructions (``grading_section``)."""
import copy
import json

from jsonschema import ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.experimental_activity_evidence.experimental_database_acquisition import (
    OPERATIONS as EXPERIMENT_DATABASE_TOOLS, catalog as experimental_database_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_experimental_contracts import (
    ExperimentalContractError)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.experimental_activity_evidence.literature_investigation_prompt import (
    INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_sequence_discovery import (
    identity_schema, references_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.experimental_activity_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import (
    REF, obj, identity, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.experimental_database_records import (
    reader_schema as experimental_records_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.experimental_activity_evidence import (
    tools as access_library)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_reasoning import (
    REASON_DESCRIPTION, empty_commit, reason as reasoning_unit, reason_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.experimental_activity_evidence.literature_grading_instructions import (
    grading_section)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_population_route import (
    REPOSITORIES, authorize_record_access, authorize_source_access, population_entries, reader_cells,
    run_population as population_unit)
from .goal import GOAL

CHILD_SLOTS = {
    'strategy': 'experimental_activity_evidence/literature/strategy',
}
SERVICES = ()

# The access tools of the old ``_ACCESS_TOOLS`` that the A105 tool library implements; the descriptions and input
# schemas are the library's own (``A105ToolRegistry.catalog``).
ACCESS_NAMES = ('state.query', 'source.read', 'source.locate', 'source.sequence.references',
                'source.experimental.records', 'source.archive.members', 'source.archive.extract',
                'source.pdf.info', 'source.pdf.text', 'source.pdf.page')
# The old ``_ACQUISITION_TOOLS``: the public literature, NCBI and PMC operations and the experimental databases.
ACQUISITION_NAMES = ('public.literature.search', 'public.literature.read', 'public.literature.sequence_identity',
                     'public.ncbi.search', 'public.pmc.versions', 'public.pmc.files', 'public.pmc.asset',
                     *EXPERIMENT_DATABASE_TOOLS)
LIBRARY_NAMES = (*ACCESS_NAMES, *ACQUISITION_NAMES)


def definitions():
    """The description and input schema of every library tool this episode offers: the registry's own
    ``_DEFINITIONS`` and readers, the sequence-identity and experimental-database catalogs; ``public.ncbi.search`` is
    narrowed to ``pubmed`` (the old ``catalog``)."""
    result = {name: access_library._DEFINITIONS[name] for name in LIBRARY_NAMES
              if name in access_library._DEFINITIONS and name not in ('source.sequence.references',
                                                                      'source.experimental.records')}
    result['source.sequence.references'] = (access_library._SEQUENCE_REFERENCES_DESCRIPTION, references_schema())
    result['source.experimental.records'] = (access_library._EXPERIMENT_RECORDS_DESCRIPTION,
                                             experimental_records_schema())
    result['public.literature.sequence_identity'] = (access_library._SEQUENCE_IDENTITY_DESCRIPTION,
                                                      identity_schema())
    for name, entry in experimental_database_catalog().items():
        result[name] = (entry['description'], entry['input_schema'])
    ncbi = copy.deepcopy(result['public.ncbi.search'])
    ncbi[1]['properties']['database'] = {'enum': ['pubmed']}
    result['public.ncbi.search'] = ncbi
    return {name: result[name] for name in LIBRARY_NAMES}


LIBRARY_DEFINITIONS = definitions()
HELD_SOURCE_TOOLS = ('source.locate', 'source.sequence.references', 'source.experimental.records')
# The repository families the old ``rate_population`` source access authorized (``authorize_source_access`` /
# ``authorize_record_access``), asked before every source read and record query while the population route is on.
SOURCE_READ_TOOLS = ('source.read', 'source.locate', 'source.sequence.references', 'source.experimental.records')




INTEGER = {'type': 'integer', 'minimum': 0}
TEXT = {'type': 'string', 'minLength': 1}
REPRESENTATIONS = ['text', 'original', 'stdout', 'stderr']


OBJECTIVE = {'type': 'string', 'minLength': 1,
             'description': 'What the child should investigate about the search approach and why'}
CHILD_DESCRIPTION = (
    'Investigate which search approach is productive. Keep the information objective and evidence context '
    'separate from a literal provider query; the child revises terms or source choices in light of actual '
    'search/read outcomes and can commission an investigation of which returned sources deserve examination. The '
    'sources handed to it are taken from the input list (the sources not yet consumed) and are consumed: they are '
    'not offered again.')


def strategy_schema(input_list):
    """The sources the model may hand the child: one or more of the unconsumed sources (the input list), so a
    consumed source cannot be handed out."""
    return obj({'prior_search_refs': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                                      'items': {'enum': list(input_list)}}})


def child_arguments(slot, input_list):
    """The description and arguments schema of a child, over the input list now."""
    return CHILD_DESCRIPTION, obj({'objective': OBJECTIVE, 'strategy': strategy_schema(input_list)})


def valid_slots(input_list):
    """The child slots valid now: the strategy child while an unconsumed source remains."""
    return list(CHILD_SLOTS) if input_list else []


# Static form (the declared shape of each child's arguments, without the input list), kept for the binding test.
CHILD_ARGUMENTS = {slot: child_arguments(slot, ['<unconsumed source>']) for slot in CHILD_SLOTS}

HISTORY_START = 'On a fresh provider conversation,'
HISTORY_END = 'Do not execute native provider tools.'
HISTORY_GUIDANCE = ('Your own earlier read outcomes are shown to you as own_literature_outcomes; that page creates '
                    'no new action and does not execute or credit the historical work again.\n')
CHILD_GUIDANCE = ('\nSelect the strategy child (the investigation of which search approach is productive) with its '
                  'objective and the sources you hold that it is to build on when a narrower question warrants '
                  'iteration; what it returns is shown to you as child_returns. A child earns credit in this '
                  'episode only through the records it returns. Your input list (input_list) is the sources not yet '
                  'consumed: a source handed to the child, or read or processed by one of your units, is consumed '
                  'and is not offered again; the child takes only sources of the input list.')


LEAD_GUIDANCE = ('\nFor a verified_source_leads commission, a reason selection also carries source_lead: the '
                 'inspected source, its anchored reference subject, whether it is a useful lead for the original '
                 'question and the exact witnessed byte interval. A search hit or title alone verifies nothing.')


def instructions(*, knowledge, leads, populations):
    """The old task_instructions.instructions: the investigation text, this episode's goal (the old role
    instruction and the shared investigation paragraph), the reasoning-commit requirement, the child text, the
    tool-knowledge text when it is offered. The decision-exchange paragraph, the pending-delivery paragraph, the
    wait paragraphs and the redeliver_report text are not carried: no such action exists."""
    text = replace_span(INSTRUCTIONS, HISTORY_START, HISTORY_END, HISTORY_GUIDANCE)
    text += '\n' + GOAL
    text += '\n' + REASONING_COMMIT_REQUIREMENT
    text += grading_section(populations)
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if leads:
        text += LEAD_GUIDANCE
    return text + CHILD_GUIDANCE + RETURN_GUIDANCE


def offered(settings):
    """The tools offered now (library names): the access and acquisition tools, the population operations under
    their flags and the reasoning commit."""
    return [*LIBRARY_NAMES, *(entry['name'] for entry in population_entries(settings)), 'reason']


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
            description, schema = LIBRARY_DEFINITIONS[name]
            entries.append({'name': TOOL_NAMES[name], 'description': description,
                            'input_schema': source_location_inputs(schema)})
    return entries


def selection_schema(names, commit_schema, leads, settings, input_list):
    """What the model answers with: one tool and its arguments, or one child slot and its arguments (the old action
    schema: kinds ``tool`` and ``child``). A child is offered only for unconsumed sources (``input_list``)."""
    tools = [obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']}, 'arguments': entry['input_schema']})
             for entry in catalog(names, commit_schema, leads, settings)]
    children = [obj({'kind': {'const': 'child'}, 'slot': {'const': slot},
                     'arguments': child_arguments(slot, input_list)[1]})
                for slot in valid_slots(input_list)]
    return obj({'selection': {'anyOf': [*tools, *children]}})


def admitted(ctx, name, arguments, assignment):
    """The old ``_tool_arguments``: the source authorization of the population route. A violation is a
    ``ContractError``. ``name`` is a library tool name."""
    if name in POPULATIONS:
        return
    authorize_source_read(ctx, name, arguments, assignment)


def invalid(name, arguments, ctx, error):
    """The old ``execute`` outcome for a contract error: an ``invalid`` outcome with feedback."""
    detail = {'detail': error.detail} if getattr(error, 'detail', None) else {}
    return {'status': 'invalid',
            'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': name, 'arguments': arguments}),
            'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'category': 'arguments_or_reference', 'code': str(error), **detail}}


async def run_access_tool(name, envelope, ctx):
    """Execute one access or acquisition tool. A contract error is returned as an ``invalid`` outcome with ``arguments_or_reference``
    feedback, as the old ``execute`` did; the outcome is the unit's outcome like any other."""
    arguments, scope = envelope['arguments'], envelope['scope']
    try:
        validate_schema(arguments, source_location_inputs(LIBRARY_DEFINITIONS[name][1]))
        admitted(ctx, name, arguments, envelope['assignment'])
    except (ContractError, ValidationError) as error:
        return invalid(name, arguments, ctx, error)
    registry = access_library.A105ToolRegistry(ctx.store, **ctx.settings['tool_registry'])
    permitted = tuple(ctx.store.refs()) if name in HELD_SOURCE_TOOLS else None
    try:
        outcome = await registry.execute_async(name, arguments, scope=scope, operation_key=ctx.operation_key,
                                               permitted_record_refs=permitted)
    except CustodyError:
        raise
    except Exception as error:   # the old record_execution_failure: a failed selected operation is an outcome
        return failure_outcome(ctx.store, error, category='episode_execution', cause_code='selected_operation_failed')
    if ctx.settings['rate_population'] and name == 'state.query' and outcome['status'] in ('completed', 'partial'):
        for record in outcome['result']['records']:
            authorize_record_access(ctx.store, ctx.run_id, ctx.episode_id, ctx.binding_path, scope,
                                    envelope['assignment'], record)
    return outcome


# The population operations (library tool names): the reader families, the grader and the aggregation.
POPULATIONS = (*REPOSITORIES, 'literature.assay_grading.populate', 'literature.a105.aggregate')
TOOL_NAMES = {name: name.replace('.', '_') for name in (*LIBRARY_NAMES, *POPULATIONS)}
RETURN_GUIDANCE = ('\nWhat returns to your parent is your credit and the features code reads from the grading and '
                   'aggregation sheets saved here or returned by your child (evidence type, quantity kind, measured '
                   'effect, variance, log evidence ratio, prediction model, criterion statuses); no prose of yours is '
                   'returned. Selecting a tool does not end your work: only the numerical controller does.')


def offered_populations(settings):
    return tuple(entry['name'] for entry in population_entries(settings))


def authorize_source_read(ctx, name, arguments, assignment):
    """The old ``_tool_arguments`` source authorization of the population route: while ``rate_population`` is on,
    each source read and each exact-reference record query is first authorized by the access authorities of the
    population route (``literature_population_route.authorize_source_access`` / ``authorize_record_access``). This
    assignment names no page, so the old containment of a read inside an assigned page does not apply."""
    if not ctx.settings['rate_population']:
        return
    if name in SOURCE_READ_TOOLS:
        representation = ('original' if name in ('source.sequence.references', 'source.experimental.records')
                          else arguments.get('representation', 'text'))
        authorize_source_access(ctx.store, ctx.run_id, ctx.episode_id, ctx.binding_path, assignment['scope'],
                                assignment, arguments['source_ref'], representation, name)
    elif name == 'state.query' and 'refs' in arguments:
        for reference in arguments['refs']:
            authorize_record_access(ctx.store, ctx.run_id, ctx.episode_id, ctx.binding_path, assignment['scope'],
                                    assignment, ctx.store.get(reference))


def source_reader(ctx, scope, assignment):
    """The held bytes of a source (the old ``_materialize_text_arguments`` reader), each read authorized."""
    def read_source(reference, representation):
        authorize_source_read(ctx, 'source.read', {'source_ref': reference, 'representation': representation},
                              assignment)
        source = ctx.store.require(reference, {'source'})
        if not ctx.store.reference_subset([reference], scope):
            raise ContractError('literature_source_outside_scope')
        artifact = source.get('artifact_ref' if representation == 'original' else 'text_ref')
        if artifact is None:
            raise ContractError('literature_source_representation_unavailable')
        return {'artifact_ref': artifact, 'content': ctx.store.get_artifact(artifact)}
    return read_source


async def run_population(name, envelope, ctx):
    """One population operation (the old ``execute`` population branch): the arguments are admitted against the
    offered schema, then the library's population route saves the sheet; a contract error is an ``invalid``
    outcome that enters the iterator."""
    arguments, scope = envelope['arguments'], envelope['scope']
    try:
        validate_schema(arguments, source_location_inputs(
            {entry['name']: entry for entry in population_entries(ctx.settings)}[name]['input_schema']))
        return population_unit(name, ctx.store, arguments, ctx.operation_key, scope=scope, page_source_ref=None,
                               assignment=envelope['assignment'], requested=envelope['requested'],
                               run_id=ctx.run_id, episode_id=ctx.episode_id, binding_path=ctx.binding_path,
                               offered=offered_populations(ctx.settings),
                               read_source=source_reader(ctx, scope, envelope['assignment']))
    except (ContractError, ExperimentalContractError, ValidationError) as error:
        return invalid(name, arguments, ctx, error)


def reason(arguments, ctx):
    """One reasoning unit: the interpretation, the grading sheets of its experiments and, for a
    verified-source-leads commission, the validated lead, committed together (``literature_reasoning.reason``).
    The grader reads the cells of a reader sheet this episode populated through that family's repository."""
    scope, assignment = arguments['scope'], arguments['assignment']

    def authorize(reference, representation):
        read = {'source_ref': reference, 'representation': representation}
        validate_schema(read, source_location_inputs(LIBRARY_DEFINITIONS['source.read'][1]))
        authorize_source_read(ctx, 'source.read', read, assignment)
    read_cells = reader_cells(ctx.store, ctx.run_id, ctx.episode_id, ctx.binding_path, scope, assignment,
                              offered_populations(ctx.settings))
    return reasoning_unit(ctx.store, scope, None, arguments['arguments'], ctx.operation_key,
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


async def public_sabiork_search(arguments, ctx):
    return await run_access_tool('public.sabiork.search', arguments, ctx)


async def public_sabiork_read(arguments, ctx):
    return await run_access_tool('public.sabiork.read', arguments, ctx)


async def public_brenda_search(arguments, ctx):
    return await run_access_tool('public.brenda.search', arguments, ctx)


async def public_brenda_read(arguments, ctx):
    return await run_access_tool('public.brenda.read', arguments, ctx)


async def public_bioassay_search(arguments, ctx):
    return await run_access_tool('public.bioassay.search', arguments, ctx)


async def public_bioassay_read(arguments, ctx):
    return await run_access_tool('public.bioassay.read', arguments, ctx)


async def public_chembl_search(arguments, ctx):
    return await run_access_tool('public.chembl.search', arguments, ctx)


async def public_chembl_read(arguments, ctx):
    return await run_access_tool('public.chembl.read', arguments, ctx)


async def public_mavedb_search(arguments, ctx):
    return await run_access_tool('public.mavedb.search', arguments, ctx)


async def public_mavedb_read(arguments, ctx):
    return await run_access_tool('public.mavedb.read', arguments, ctx)


async def public_brenda_graph_search(arguments, ctx):
    return await run_access_tool('public.brenda.graph_search', arguments, ctx)


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
    'state_query': state_query,
    'source_read': source_read,
    'source_locate': source_locate,
    'source_sequence_references': source_sequence_references,
    'source_experimental_records': source_experimental_records,
    'source_archive_members': source_archive_members,
    'source_archive_extract': source_archive_extract,
    'source_pdf_info': source_pdf_info,
    'source_pdf_text': source_pdf_text,
    'source_pdf_page': source_pdf_page,
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


def child_options(input_list):
    """The children the model may select now: slot, description and the arguments it takes (the old
    ``child_option_information``), only while an unconsumed source remains in the input list."""
    return [{'slot': slot, 'description': child_arguments(slot, input_list)[0],
             'arguments': child_arguments(slot, input_list)[1]} for slot in valid_slots(input_list)]


def decide(summary, feedback, ctx):
    """Ask the model for the next tool or child, shown the assignment, the custody of the sources, its own read
    and acquisition outcomes, the goal plan, the interpretation so far, the children's returns, the tools, the measured time and the
    yield table (the old decision state and inputs, over this episode's summary).

    The population display contexts of the old ``internal_summary.py`` (the possessed rate, domain, meaning,
    gel, controlled-response, endpoint, precision, comparison and window rows, the owned population sources and
    the failed population attempt) read the family repositories through the Store and are not carried (see the
    "Carried over" table)."""
    names = offered(ctx.settings)
    leads = summary['task']['kind'] == 'verified_source_leads'
    knowledge_directory = ctx.settings['knowledge_library_directory']
    context = {'goal': GOAL, 'scope': summary['scope'], 'literature_assignment': summary['literature_assignment'],
               'literature_source_custody': summary['literature_source_custody'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_history_meaning': summary['literature_history_meaning'],
               'literature_goal_plan': summary['literature_goal_plan'],
               'credit_binding': summary['credit_binding'], 'last_local_outcome': summary['last_local_outcome'],
               'held_record_refs': summary['held_record_refs'], 'assay_sheets': summary['assay_sheets'],
               'aggregation_sheets': summary['aggregation_sheets'],
               'child_returns': summary['child_returns'], 'input_list': summary['input_list'],
               'consumed_inputs': summary['consumed_inputs'], 'child_options': child_options(summary['input_list']),
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
                        generation_schema(selection_schema(names, summary['reasoning_schema'], leads, ctx.settings,
                                                           summary['input_list'])))


def validate_selection(value, schema):
    validate_schema(value, schema)
    return value['selection']


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one child commission, or reject it (no unit). An answer that
    selects no offered tool or slot, arguments that do not fit its schema, an empty reasoning commit without a
    source lead or a no-applicable-evidence declaration, or a child commission naming a source this episode does
    not hold is invalid (validation of the model's own answer). What ``msg_to_child`` builds is not checked here: a
    wrong commission fails where the child is built."""
    names = offered(ctx.settings)
    leads = summary['task']['kind'] == 'verified_source_leads'
    commit_schema = summary['reasoning_schema']
    schema = selection_schema(names, commit_schema, leads, ctx.settings, summary['input_list'])
    try:
        selection = validate_selection(decode_response(response, schema), schema)
        if selection['kind'] == 'child':
            for reference in selection['arguments']['strategy']['prior_search_refs']:
                if not records.holds(reference):
                    raise ContractError('literature_reference_unavailable', detail={'reference': reference})
            return ChildCall(selection['slot'], selection['arguments'])
        name, arguments = selection['tool'], selection['arguments']
        if name == 'reason' and empty_commit(arguments['commit'], commit_schema) and 'source_lead' not in arguments and (
                arguments.get('evidence_processing', {}).get('kind') != 'no_applicable_evidence'):
            raise ValueError('empty_reasoning_commit')
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(name, {'arguments': arguments, 'scope': summary['scope'],
                           'assignment': summary['literature_assignment'], 'requested': summary['requested'],
                           'proposed_annotation_ref': summary['proposed_annotation_ref']})


def offered_actions(summary, ctx):
    """The action types offered at this decision, from the same ``offered`` and ``CHILD_SLOTS`` that ``decide`` builds
    its selection schema from: the tool names (as the runner records them), ``reason``, and the child slot while an
    unconsumed source remains in the input list."""
    return [TOOL_NAMES.get(name, name) for name in offered(ctx.settings)] + valid_slots(summary['input_list'])
