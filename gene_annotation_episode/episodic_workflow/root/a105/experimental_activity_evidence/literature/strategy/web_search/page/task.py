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
decision's instructions. ``update_sheet`` (A105 scoring paradigm, OWNER_DECISION 10) is the page's own unit: it groups the
leaf records the ``chunk`` children returned into graders and updates the persistent subscoring sheet, the credit and the
per-annotation scores (``update_sheet``, ``literature_page_update.page_update``). The old ``report`` tool is gone, and so are the copies of the owner's grader and reader
instructions that were parked in ``internal_summary.py``: the texts are in the library prompt files and reach the
model through ``grading_section``."""
import json

from jsonschema import ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_experimental_contracts import (
    ExperimentalContractError)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_claim import (
    PARTNER_VALUE_TYPES, claim_of_hypothesis)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_identity import (
    finalize_grader, group_leaf_records)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_page_update import (
    page_update)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_reasoning import (
    REASON_DESCRIPTION, empty_commit, reason as reasoning_unit, reason_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    AXIS_CREDIT_CHANNEL, EXPERIMENT_TYPES)
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
    canonical, identity, obj, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.experimental_database_records import (
    reader_schema as experimental_records_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.received_records import read_record_in_scope
from gene_annotation_episode.episodic_workflow.episode_support.tools.experimental_activity_evidence import (
    tools as access_library)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

from .credit import classify_unknowns
from .goal import GOAL

CHILD_SLOTS = {
    'table': 'experimental_activity_evidence/literature/strategy/web_search/page/table',
    'report': 'experimental_activity_evidence/literature/strategy/web_search/page/report',
    'chunk': 'experimental_activity_evidence/literature/strategy/web_search/page/chunk',
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

# The span of the library text that describes actions this episode does not have (the report_update form, the
# redeliver_report action, episode.history) is replaced by what the episode has instead.
HISTORY_START = 'A commissioned child returns ONLY the parent\'s typed form.'
HISTORY_END = 'Do not execute native provider tools.'
HISTORY_GUIDANCE = ('Your own earlier read outcomes are shown to you as own_literature_outcomes; that page creates '
                    'no new action and does not execute or credit the historical work again.\n')
# The first thing the model reads: what this episode is for, what the commissioner asked, which tools and children
# exist and when each is the right choice, and what earns credit. The objective values are the vocabulary of
# ``messages/read_from_parent.py`` (``OBJECTIVES``); the value of this commission is shown in ``context.commission``.
# Holding the ordinary tools is this episode's design (goal: "Choose ordinary source operations or selected table,
# ordered-reading or targeted-passage investigations as useful"): the text says when delegating is the right choice
# and prescribes no child.
BRIEF = (
    'THIS EPISODE: page (A105 experimental evidence). You examine ONE assigned source '
    '(context.literature_assignment: source_ref, representation, artifact_ref) for ONE commissioned literature task '
    '(context.literature_assignment.literature_task) about ONE proposed annotation '
    '(context.commission.proposed_annotation_ref). Your work is to find the parts of this source that hold evidence '
    'for that task and to have each read and graded, with your own tools or by a child.\n'
    'WHAT THE COMMISSIONER ASKED: context.commission.objective is the commissioner\'s objective. It is one value of a '
    'fixed vocabulary and context.commission.objective_meaning states it: where the commissioner expects the '
    'evidence in this source (evidence_in_table, evidence_in_passages) or that it does not know '
    '(evidence_location_unknown). It tells you where to look first; it prescribes no tool and no child.\n'
    'YOUR OWN TOOLS (context.tools) do ordinary one-off work directly:\n'
    '- state_query reads records you hold, for example a commissioned experiment reference whose anchor (start, end) '
    'is the byte interval where the source states that experiment.\n'
    '- source_read and source_locate read a byte window of the source and locate a literal phrase in it; the pdf, '
    'archive, sequence-reference and experimental-record tools read a source held in that representation.\n'
    '- reason commits your own interpretation together with its grading sheet (or a source-grounded '
    'no_applicable_evidence, or the source_lead of a verified_source_leads task), for evidence you have read '
    'yourself.\n'
    'THE CHILDREN (context.child_options gives the arguments of each): a child is a narrower investigation that needs '
    'iteration of its own and passes back only a summary (its credit, the counts of its finding and the features of '
    'the sheets it saved). No child is compulsory and no order is prescribed. Delegating is the right choice when the '
    'part to examine is a job of several steps in itself:\n'
    '- table: a whole table or sheet to work through (many rows, headers, footnotes, row '
    'selections, or several experiments in one table). Its selection is a sheet (sheet_key, offset, limit, '
    'header_row, optional where) or one byte window of the page (representation, offset, limit).\n'
    '- chunk: a leaf extractor of ONE byte window for ONE experiment_type; it returns only its leaf record. Its '
    'records earn credit only through update_sheet (below).\n'
    '- report: a long document to be read in order, window after window, when where the '
    'evidence stands is not known. Its selection is the window the reading starts at.\n'
    'When one read shows you the evidence in full (a short source, one small block of numbers), reading and grading '
    'it yourself is ordinary work and needs no child. A commission carries an objective of the child\'s own fixed '
    'vocabulary: grade_reported_experiment when the selection is known to report a commissioned experiment with its '
    'measurements; find_applicable_evidence when whether the selection holds applicable evidence is still open.\n'
    'UPDATE_SHEET (a105_experiments tasks): the tool update_sheet takes no argument. Code groups every leaf record your '
    'chunk children returned into graders (one experiment = one grader; same document and experiment type merge unless '
    'a stated identity feature conflicts), converts each grader, scores it against the commissioned annotation and '
    'updates the persistent subscoring sheet, the main scoring sheet, the credit and the per-annotation scores. For an '
    'a105_experiments task the credit of this episode is credit_unit times the credit of the latest update_sheet '
    '(context.sheet_update); nothing is earned before it runs.\n'
    'CREDIT (context.credit_binding, context.action_yields): one credit_unit for each answer to the commissioned '
    'task. For an a105_experiments task the answer is the current grading sheet of each commissioned experiment (the '
    'experiment_ref and assay_type of literature_task.experiments), saved by your reason or returned by a child. '
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
    'support is a wrong grading. Reading, locating, navigation and repeated work earn nothing by themselves. A '
    'child\'s credit is in context.child_returns; the sheets it returned are answers of this episode and earn by '
    'the same counts. Only the numerical controller ends the episode.\n\n')
RETURN_GUIDANCE = ('\nWhat returns to your parent is your credit, the per-annotation scores and the features code reads '
                   'from the subscoring rows of your latest update_sheet (evidence type, number of assays, '
                   'independent groups, relative deviation, support, opposition, net, status) and the references of '
                   'the persisted sheet states; no prose of yours and no raw record is returned. Selecting a tool '
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
# What this episode asks of a child: one value of the child's fixed vocabulary (controlled messaging: the child's
# model is never shown text this episode's model wrote). The three children take the same two values.
OBJECTIVE = {'enum': ['grade_reported_experiment', 'find_applicable_evidence'],
             'description': 'What the child is to do with its selection. grade_reported_experiment: the selection is '
                            'known to report a commissioned experiment with its measurements; the child reads it and '
                            'grades that experiment, entering every quantity the selection states. '
                            'find_applicable_evidence: whether the selection holds an experiment or result '
                            'applicable to the proposed annotation is still open; the child reads it, grades what '
                            'is applicable and otherwise declares that it holds no applicable evidence.'}
CHILD_ARGUMENTS = {
    'table': (
        'Reads ONE table, sheet or tabular block of numbers of a source of this assignment and grades the '
        'experiments it reports. Selection: a sheet (sheet_key with its rows, header and an optional literal row '
        'filter) or one byte window of the page that holds the table. The right choice when a whole table is a job '
        'of several steps in itself: many rows, headers and footnotes to work through, row selections to revise, or '
        'several experiments reported in one table.',
        obj({'objective': OBJECTIVE, 'page': PAGE_SCHEMA, 'selection': {'anyOf': [TABLE_SCHEMA, WINDOW_SCHEMA]}})),
    'report': (
        'Reads one source of this assignment in document order from one window, continuing, rereading or changing '
        'the window as its outcomes warrant, and grades the experiments it meets. The right choice when a long '
        'document has to be read in order, window after window, because where the evidence stands is not known.',
        obj({'objective': OBJECTIVE, 'page': PAGE_SCHEMA, 'selection': WINDOW_SCHEMA})),
    'chunk': (
        'A leaf extractor: reads ONE byte window of a source of this assignment and extracts, for ONE kind of '
        'experiment (experiment_type), exactly the inputs that experiment\'s grader needs, each with its quote. It '
        'grades and judges nothing and returns only the immutable leaf record. Commission it once per window and kind. '
        'The right choice when a passage of the running text reports an experiment of a known kind. This episode '
        'groups the leaf records of its chunks into graders and updates the subscoring sheet itself (update_sheet).',
        obj({'objective': OBJECTIVE, 'page': PAGE_SCHEMA, 'selection': WINDOW_SCHEMA,
             'experiment_type': {'enum': list(EXPERIMENT_TYPES),
                                 'description': 'The kind of experiment whose grader inputs are extracted'}})),
}

CHILD_GUIDANCE = ('\nA child, when you select one, is selected with its objective (a value of its vocabulary), the '
                  'page it reads and its selection. What it returns is shown to you as child_returns (its credit and '
                  'the counts of its finding) and, for table and report, assay_sheets (the features of the sheets it '
                  'saved). A chunk child returns only its leaf records (context.leaf_record_refs): it earns this '
                  'episode credit only through update_sheet, which groups every leaf record held into graders (one '
                  'experiment, one grader), scores them against the commissioned annotation and updates the '
                  'subscoring sheet; its result is context.sheet_update (scores, features and credit). Run '
                  'update_sheet when the leaf records you want are held; it can be run again after more chunks '
                  'return and always starts from the sheet you were given.')
UPDATE_SHEET_DESCRIPTION = (
    'Group all the leaf records returned by chunk children into graders, update the persistent subscoring sheet with '
    'them, and so update the main scoring sheet, the credit and the per-annotation scores of the commissioned '
    'annotation (context.sheet_update). It takes no argument: code derives everything from the records held. It '
    'earns credit only for resolution newly gained; repeating a held fact earns nothing.')


def instructions(*, knowledge, leads, populations):
    """This episode's brief first (what it is for, what the commissioner asked, the children and tools and when each
    is the right choice, what earns credit), then the old task_instructions.instructions: the investigation text,
    this episode's goal, the reasoning-commit requirement, the owner's grading section with the offered sheet
    families, the child text, the tool-knowledge text when it is offered. The report_update, redeliver_report,
    decision-exchange, pending-delivery and wait paragraphs are not carried: no such action exists."""
    text = BRIEF + replace_span(INSTRUCTIONS, HISTORY_START, HISTORY_END, HISTORY_GUIDANCE)
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
    return [*ACCESS_NAMES, *(entry['name'] for entry in population_entries(settings)), 'reason', 'update_sheet']


def offered_actions(summary, ctx):
    """The action types offered at this decision, by the names the runner records: each tool offered by ``offered``
    (the list ``decide`` and ``action`` use) under its python name, then each child slot of ``selection_schema``."""
    return [*(TOOL_NAMES.get(name, name) for name in offered(ctx.settings)), *CHILD_SLOTS]


def catalog(names, commit_schema, leads, settings):
    """The tools the model is shown: python tool name, description and input schema (the old catalog; every input
    schema is projected through ``source_location_inputs``)."""
    population = {entry['name']: entry for entry in population_entries(settings)}
    entries = []
    for name in names:
        if name == 'reason':
            entries.append({'name': 'reason', 'description': REASON_DESCRIPTION,
                            'input_schema': reason_schema(commit_schema, leads)})
        elif name == 'update_sheet':
            entries.append({'name': 'update_sheet', 'description': UPDATE_SHEET_DESCRIPTION, 'input_schema': obj({})})
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


def hypothesis_claim(store, hypothesis_ref):
    """The claim (predicate, subject, partner) of the commissioned hypothesis record, with the names read from the
    records it points at (term and reference records carry their ``label``). A hypothesis that is no claim
    (``literature_claim``) raises: the commission is wrong."""
    hypothesis = store.get(hypothesis_ref)
    refs = list(hypothesis['subject_refs'])
    if hypothesis['value']['type'] in PARTNER_VALUE_TYPES:
        refs.append(hypothesis['value']['ref'])
    return claim_of_hypothesis(hypothesis, {ref: store.get(ref)['label'] for ref in refs})


def prior_sheet_state(store, state_refs):
    """The persistent subscoring sheet this page was given: {(sheet, assertion_ref): state}, one state per row."""
    prior = {}
    for ref in state_refs:
        held = json.loads(store.get_artifact(ref))
        key = (held['row']['sheet'], held['row']['assertion_ref'])
        if key in prior:
            raise ValueError(f'the sheet states passed to this page hold the row {key!r} twice')
        prior[key] = held
    return prior


def update_sheet(arguments, ctx):
    """The page's update of the persistent subscoring sheet (OWNER_DECISION 10). Reads the immutable leaf records the chunk
    children returned and the sheet states passed in, groups the leaf records into graders (``group_leaf_records``: one
    experiment = one grader, default merge, split on a positive identity conflict), finalizes every grader
    (``finalize_grader``), and runs ``page_update`` (merged record, grade, convert, bearing and direction against the claim of
    the commissioned hypothesis, subscoring rows, main sheet, axis, credit, scores, features). Every call regroups ALL the leaf
    records from the states passed in, so a grader whose members grow is re-derived and never counted twice; the latest call
    is the page's whole result. The library functions are pure: this unit alone writes, through the custody store, each row
    state as an artifact (content-addressed; the row inside it carries its content-addressed ``row_ref``). The outcome holds
    controlled data only: the state references, the scores, the credit channel and the features."""
    store = ctx.store
    leaf_records = [json.loads(store.get_artifact(ref)) for ref in arguments['leaf_record_refs']]
    graders = [finalize_grader(grader) for grader in group_leaf_records(leaf_records)]
    by_ref = {record['experiment_ref']: record for record in leaf_records}
    items = [{'grader': grader, 'member_records': [by_ref[ref] for ref in grader['member_record_refs']]}
             for grader in graders]
    proposed = arguments['proposed_annotation_ref']
    update = page_update(prior_sheet_state(store, arguments['base_state_refs']), items,
                         {proposed: hypothesis_claim(store, proposed)})
    state = update['sheet_state']
    refs = [store.artifact(canonical(state[key]), 'application/json') for key in sorted(state)]
    return {'status': 'completed',
            'sheet_update': {'sheet_state_refs': refs, 'grader_count': len(graders),
                             'scores': [update['scores'][name] for name in sorted(update['scores'])],
                             'credit': [{name: axis[name] for name in AXIS_CREDIT_CHANNEL} for axis in update['axis']],
                             'features': update['features']}}


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
    'reason': reason, 'update_sheet': update_sheet}


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
    context = {'commission': summary['commission'], 'goal': GOAL, 'scope': summary['scope'],
               'literature_assignment': summary['literature_assignment'],
               'literature_source_custody': summary['literature_source_custody'],
               'own_literature_outcomes': summary['own_literature_outcomes'],
               'literature_history_meaning': summary['literature_history_meaning'],
               'source_examination_goal': summary['source_examination_goal'],
               'credit_binding': summary['credit_binding'], 'last_local_outcome': summary['last_local_outcome'],
               'held_record_refs': summary['held_record_refs'], 'assay_sheets': summary['assay_sheets'],
               'aggregation_sheets': summary['aggregation_sheets'], 'child_returns': summary['child_returns'],
               'leaf_record_refs': summary['leaf_record_refs'], 'sheet_update': summary['sheet_update'],
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
    if name == 'update_sheet':
        return ToolCall(name, {'leaf_record_refs': summary['leaf_record_refs'],
                               'base_state_refs': summary['base_state_refs'],
                               'proposed_annotation_ref': summary['proposed_annotation_ref']})
    return ToolCall(name, {'arguments': arguments, 'scope': summary['scope'],
                           'page_source_ref': summary['page']['source_ref'],
                           'assignment': summary['literature_assignment'], 'requested': summary['requested'],
                           'proposed_annotation_ref': summary['proposed_annotation_ref'],
                           'examined_windows': summary['examined_windows']})
