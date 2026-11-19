"""The task: investigate by the selected evidence axis, thought pattern and tools, commit reasoning on what the
evidence says (the interpretation and its subscoring sheets in one unit), look up the frozen evidence-axis and
thought-pattern library, prepare a revised selection for a new child, and commission a narrower A105 head or a
published-evidence assessment.

Carried from the old ``task.py`` (``ScientificTask.next/apply_response/execute``), ``task_decision.py``,
``task_instructions.py``, ``scientific_operations.py`` (``catalog``, ``execute``, ``_proposed_selection``),
``library_services.py`` / ``library_operations.py`` (``execute_scientific_library``: ``process.search``,
``process.entry``, ``process.sources``), ``goal.py`` (the two instruction texts) and ``decision_inputs.py`` /
``internal_summary.py`` (``decision_context``). One unit is one model-selected tool call or one commission of a
child. The task always offers a unit and never ends the Episode: only the yield controller does.

Children. The old ``child_roles`` were this head itself (``experimental_activity_evidence``) and ``literature``
(``published_evidence_assessment``); the slots below are those two, under the name of their folders.
``messages/msg_to_child.py`` builds each commission.

Tools offered. The registry tools are the A105 tool library's catalog (``A105ToolRegistry.catalog``); this episode
offers those the commissioner selected in ``selection['child_tool_info']`` (the old selected tools), and always the
library lookups (``process_search``, ``process_entry``, ``process_sources``), ``process_revise`` and ``reason``.
A selected tool this episode does not have raises (a wrong commission fails).

A105 evidence processing (AGENTS.md, "Required literature evidence processing"): the ``reason`` tool is the
required-grading action (the old head committed with a plain reasoning commit; the rule couples the grading with
it). Its selection carries ``evidence_processing`` (graded gradings, or a source-grounded
``no_applicable_evidence``); the library's ``literature_required_grading.execute`` commits the interpretation and
saves its subscoring sheets together before any credit, and every assessment carries its typed
``investigation_finding`` (a record of this episode): ``literature_reasoning.reason`` on the custody-scoped store.
What returns to the parent is the controlled features code reads from the saved sheets (own and returned by the
children), never prose. The owner's grading instructions are part of every decision's instructions
(``grading_section``)."""

from jsonschema import ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.experimental_activity_evidence.experimental_database_acquisition import (
    OPERATIONS as EXPERIMENT_DATABASE_TOOLS, catalog as experimental_database_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.configuration.experimental_activity_evidence.process_options import (
    ExperimentalActivityEvidenceLibrary, catalog as process_catalog, evidence_axis_instruction_view)
from gene_annotation_episode.episodic_workflow.episode_support.forms.experimental_activity_evidence.evidence_axis_contracts import (
    VERSION as EVIDENCE_AXIS_VERSION)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.experimental_activity_evidence.evidence_axis_instructions import (
    VERSION as INSTRUCTION_VERSION, instruction_view)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import (
    ASSAY_TYPES, COMPONENTS as ASSAY_GRADING_COMPONENTS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_reasoning import (
    REASON_DESCRIPTION, empty_commit, reason as reasoning_unit, reason_schema as reasoning_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.experimental_activity_evidence.literature_grading_instructions import (
    grading_section)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.experimental_activity_evidence.literature_investigation_prompt import (
    INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_aggregation import (
    COMPONENTS as AGGREGATION_COMPONENTS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_sequence_discovery import (
    identity_schema, references_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_quantity_storage import (
    COMPONENTS as QUANTITY_COMPONENTS, quantity_population_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.experimental_activity_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import (
    REF, REFS, identity, obj, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.experimental_database_records import (
    reader_schema as experimental_records_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.option_records import scientific_digest
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.experimental_activity_evidence import (
    tools as access_library)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

CHILD_SLOTS = {
    'experimental_activity_evidence': 'experimental_activity_evidence',
    'published_evidence_assessment': 'experimental_activity_evidence/published_evidence_assessment',
}
SERVICES = ()

REVISION_ORIGIN_VERSION = 'experimental_activity_evidence_revision_origin_v1'
CHILD_SELECTION_VERSION = 'experimental_activity_evidence_child_selection_v1'

# The tools of the A105 tool library (``A105ToolRegistry.catalog``) a commissioner can select for this head.
REGISTRY_NAMES = ('state.query', 'source.read', 'source.locate', 'source.sequence.references',
                  'source.experimental.records', 'source.archive.members', 'source.archive.extract',
                  'source.pdf.info', 'source.pdf.text', 'source.pdf.page',
                  'public.literature.search', 'public.literature.read', 'public.literature.sequence_identity',
                  'public.ncbi.search', 'public.ncbi.sequence', 'public.taxonomy',
                  'public.pmc.versions', 'public.pmc.files', 'public.pmc.asset', *EXPERIMENT_DATABASE_TOOLS)
# The old ``_RECEIVED_SOURCE_READERS``: the source locator reads only records this episode received.
HELD_SOURCE_TOOLS = ('source.locate',)
LIBRARY_LOOKUPS = ('process.search', 'process.entry', 'process.sources')
TOOL_NAMES = {name: name.replace('.', '_') for name in (*REGISTRY_NAMES, *LIBRARY_LOOKUPS, 'process.revise')}


def definitions():
    """The description and input schema of every registry tool: the registry's own ``_DEFINITIONS``, its readers,
    the sequence-identity and experimental-database catalogs (the old ``A105ToolRegistry.catalog``)."""
    result = {name: access_library._DEFINITIONS[name] for name in REGISTRY_NAMES
              if name in access_library._DEFINITIONS}
    result['source.sequence.references'] = (access_library._SEQUENCE_REFERENCES_DESCRIPTION, references_schema())
    result['source.experimental.records'] = (access_library._EXPERIMENT_RECORDS_DESCRIPTION,
                                             experimental_records_schema())
    result['public.literature.sequence_identity'] = (access_library._SEQUENCE_IDENTITY_DESCRIPTION,
                                                      identity_schema())
    for name, entry in experimental_database_catalog().items():
        result[name] = (entry['description'], entry['input_schema'])
    return {name: result[name] for name in REGISTRY_NAMES}


REGISTRY_DEFINITIONS = definitions()
LOOKUP_DEFINITIONS = {entry['name']: (entry['description'], entry['input_schema']) for entry in process_catalog()}

TEXT = {'type': 'string', 'minLength': 1}
SHA256 = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}

# The old ``scientific_contracts`` option references, tool selectors and assignment, as the model writes them.
OPTION_REF = obj({'version': {'const': 'experimental_activity_evidence_option_ref_v1'}, 'library_id': SHA256,
                  'slot': {'enum': ['evidence_axis', 'thought_pattern']}, 'option_id': TEXT, 'entry_sha256': SHA256})
TOOL_SELECTOR = obj({'name': TEXT, 'resources': {'enum': ['api', 'local', 'hpc']}})
SELECTION = obj({'version': TEXT, 'evidence_axis': OPTION_REF, 'thought_pattern': OPTION_REF,
                 'child_tool_info': {'type': 'array', 'items': TOOL_SELECTOR, 'uniqueItems': True}})
EVIDENCE_TASK = obj({'version': {'const': 'evidence_axis_task_v1'}, 'kind': {'const': 'whole_axis_findings'},
                     'evidence_axis': {'const': 'A105'},
                     'credit_unit': {'type': 'number', 'exclusiveMinimum': 0,
                                     'description': 'Use the finding unit of the explicitly configured credit '
                                                    'definition for this exact task; do not select or change its '
                                                    'cost.'}})
REVISION_ORIGIN = obj({'version': {'const': REVISION_ORIGIN_VERSION}, 'parent_invocation_ref': TEXT,
                       'preparation_operation_ref': TEXT})
HEAD_ASSIGNMENT = obj({'selection': SELECTION, 'proposed_annotation_ref': REF, 'evidence_refs': REFS,
                       'constraints': {'type': 'object'}, 'context': obj({'evidence_task': EVIDENCE_TASK}),
                       'revision_origin': REVISION_ORIGIN},
                      required=['selection', 'evidence_refs', 'constraints', 'context'])
REVISION_ARGUMENTS = obj({'thought_pattern': OPTION_REF,
                          'child_tool_info': {'type': 'array', 'items': TOOL_SELECTOR, 'uniqueItems': True}})

# The literature assignment (private copy of what the published-evidence assessment takes; the head states it in its
# own text and schema and sends it by name, rule 5).
OTHER_REQUESTED = (
    'requested_concentration_window_components', 'requested_measurement_comparison_components',
    'requested_kinetic_summary_precision_components', 'requested_rate_grid_components',
    'requested_rate_observation_components', 'requested_calibration_recovery_components',
    'requested_product_coupling_components', 'requested_measurement_validation_components',
    'requested_rate_replicate_components', 'requested_rate_components', 'requested_assay_components',
    'requested_ratio_components', 'requested_binding_components', 'requested_binding_model_components',
    'requested_transport_components', 'requested_endpoint_signal_components', 'requested_figure_components',
    'requested_amount_components', 'requested_optical_components', 'requested_kinetic_components',
    'requested_kinetic_model_components', 'requested_binding_interaction_model_components',
    'requested_binding_interaction_components', 'requested_ion_discrimination_components',
    'requested_channel_components', 'requested_compiled_assay_components',
    'requested_compiled_assay_components_v2', 'requested_compiled_assay_components_v3',
    'requested_parent_depletion_components', 'requested_stoichiometric_balance_components',
    'requested_product_partition_components', 'requested_completion_time_components',
    'requested_active_site_components', 'requested_ratio_source_components',
    'requested_controlled_response_components', 'requested_controlled_response_views',
    'requested_controlled_response_component_keys', 'requested_gel_components', 'requested_gel_views',
    'requested_gel_component_keys')


def literature_task_schema():
    """The commissioned literature result and its explicit local credit unit (the old ``goal.task_schema``)."""
    yield_settings = obj({'kind': {'enum': ['accumulation', 'remaining_commissioned_credit']},
                          'cutoff': {'type': 'number', 'minimum': 0},
                          'uncertainty_alpha': {'type': 'number', 'exclusiveMinimum': 0, 'exclusiveMaximum': 1}})
    base = {'version': {'const': 'literature_local_task_v1'}, 'evidence_axis': {'const': 'A105'},
            'credit_unit': {'type': 'number', 'exclusiveMinimum': 0}, 'yield_settings': yield_settings}

    def task_object(properties):
        return obj(properties, required=[key for key in properties if key != 'yield_settings'])
    refs = {'type': 'array', 'items': REF, 'minItems': 1, 'uniqueItems': True}
    span = obj({'source_ref': REF, 'artifact_ref': REF, 'start': {'type': 'integer', 'minimum': 0},
                'end': {'type': 'integer', 'minimum': 1}})
    return {'anyOf': [
        task_object({**base, 'kind': {'const': 'verified_source_leads'}}),
        task_object({**base, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'assessment'},
                     'source_refs': refs}),
        task_object({**base, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'screening'},
                     'examined': {'type': 'array', 'minItems': 1, 'items': span}}),
        task_object({**base, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'measurement'},
                     'selection': quantity_population_schema(),
                     'components': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                                    'items': {'enum': ['reported_value', 'reported_spread',
                                                       'relative_reported_spread']}}}),
        task_object({**base, 'kind': {'const': 'a105_experiments'},
                     'experiments': {'type': 'array', 'minItems': 1,
                                     'items': obj({'experiment_ref': REF, 'assay_type': {'enum': list(ASSAY_TYPES)}})}}),
        task_object({**base, 'kind': {'const': 'a105_assembly'}, 'experiment_refs': refs,
                     'metrics': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                                 'items': {'enum': ['reliability', 'validity', 'relevance', 'attribution',
                                                    'overall']}}})]}


def literature_assignment_schema():
    requested = {'requested_assay_grading_components': {'type': 'array', 'items': {'enum': list(ASSAY_GRADING_COMPONENTS)}},
                 'requested_a105_aggregation_components': {'type': 'array', 'items': {'enum': list(AGGREGATION_COMPONENTS)}},
                 'requested_quantity_components': {'type': 'array', 'items': {'enum': list(QUANTITY_COMPONENTS)}},
                 **{name: {'type': 'array', 'items': TEXT} for name in OTHER_REQUESTED}}
    properties = {'version': {'const': 'literature_assignment_v1'}, 'question_context_refs': REFS,
                  'source_refs': REFS, 'literature_task': literature_task_schema(),
                  'proposed_annotation_ref': REF, **requested}
    return obj(properties, required=['version', 'question_context_refs', 'source_refs', 'literature_task',
                                     'proposed_annotation_ref'])


OBJECTIVE = {'type': 'string', 'minLength': 1, 'description': 'The child episode objective.'}
SCOPE = {'type': 'object', 'description': 'A Store scope within this scope.'}
CHILD_ARGUMENTS = {
    'experimental_activity_evidence': (
        'Commission a narrower A105 experimental-activity investigation over a sub-scope of this scope with its own '
        'selection (the evidence axis, a thought pattern and tools) and its own typed return; it returns its credit '
        'and the typed findings it retained. Name every record it needs in evidence_refs: the records of the '
        "sub-scope's subjects and the evidence. request_results asks for its recorded process result.",
        obj({'objective': OBJECTIVE, 'scope': SCOPE, 'assignment': HEAD_ASSIGNMENT,
             'request_results': {'type': 'boolean'}}, required=['objective', 'scope', 'assignment'])),
    'published_evidence_assessment': (
        'Commission an A105 published-evidence assessment of one proposed annotation: it searches and reads the '
        'sources, grades each applicable experiment with its purpose-specific subscoring sheet and returns its '
        'credit, its typed findings and the typed answer its task requires. Name the sources and the question '
        'context it starts from.',
        obj({'objective': OBJECTIVE, 'scope': SCOPE, 'assignment': literature_assignment_schema()})),
}

HISTORY_START = 'On a fresh provider conversation,'
HISTORY_END = 'Do not execute native provider tools.'
HISTORY_GUIDANCE = ('Your own earlier outcomes are shown to you as own_outcomes; that page creates no new action '
                    'and does not execute or credit the historical work again.\n')
# The old ``goal.py`` ``ScientificGoal.instructions``: the text of the published-instruction axis entry and the text
# of the evidence-axis entry. The wait and redelivery sentences describe actions that no longer exist.
INSTRUCTION_ENTRY_GOAL = (
    "Determine what the supplied target does within the parent's assigned question, scope and constraints. Start "
    "with the supplied sequence, selected file contents or snippets, preserving their boundaries, completeness and "
    "known context. No initial candidate annotation or publicly searchable name is required. Possible functions can "
    "emerge from the evidence and be compared or revised. Apply the complete selected investigation instructions and "
    "thought-pattern guidance on every decision. Use actual outcomes and received child results to choose and "
    "revise your approach. Selected instructions describe how to investigate; they are not evidence about this "
    "target. Preserve the measured subject, conditions, controls, native measurements, uncertainty and limits of "
    "inference when interpreting evidence. Missing information remains unknown.\n\n"
    "Choose an available tool action, commit a scientific interpretation through the reasoning action, or "
    "commission a scoped child with its own typed return form. Use only the selected actual tools and their "
    "supplied resource instructions; choose callable operands through the declared response contract. Preserve the "
    "parent's exact requested result meanings and allowed values. Recorded facts come from actual records. Keep "
    "inherited information distinct from new findings and completed work distinct from attempts. Return valid "
    "partial findings and specific failures through the requested form.\n\n"
    "Keep the assigned evidence axis, thought pattern and selected tools for this episode. process_revise prepares "
    "a different thought pattern and/or tool selection for a new child; it does not change this episode or start "
    "that child. To commission that alternative, copy its selection and revision_origin into a separately selected "
    "child assignment with the child's scope, constraints and typed return. Children own their iterative choices. "
    "The configured controller owns continuation. Unchanged observations do not manufacture progress.")
EVIDENCE_AXIS_ENTRY_GOAL = (
    "Investigate the parent's assigned scientific problem iteratively in the shared Episode loop. The selected "
    "scientific support proposition and operands define the support problem; the thought pattern supplies "
    "alternatives and outcome-sensitive guidance; the selected real tools supply their exact callable contracts. "
    "Choose your own actions using actual outcomes and received child forms. The selection is no prescribed "
    "sequence or automatic compatibility verdict. Library sources are instruction provenance, not scientific "
    "evidence about this target. Inspect actual source subjects, conditions and target applicability before "
    "interpreting evidence. annotation_support_routes describes the actual separately bound annotation policy's "
    "kind dispatch. An unmapped kind has no base-axis mapping in that known policy. Unavailable metadata means this "
    "reader cannot declare the bound policy; it is no verdict on evidence or the actual score. Metadata itself "
    "earns no credit and never replaces or filters the actual projectors, annotation formula or continuation rule. "
    "Keep the parent's objective, scope, constraints and exact typed form; support metadata never adds form fields "
    "or scoring axes. Use common reasoning to commit scientific interpretations. Keep the originally assigned "
    "scientific support, thought pattern and selected tool set throughout this episode. Explicit process_revise "
    "prepares a selection for a new child; a separately selected child commission commissions that child with its "
    "own scope, constraints and typed return form. Preparation changes no current process and starts no child. Copy "
    "both result.selection and revision_origin into that child's assignment to identify it as an alternative "
    "approach. Only retrieved actual tools "
    "are available; their descriptions do not grant execution. The configured controller owns continuation.")
CHILD_GUIDANCE = ('\nSelect a child with its objective, scope and assignment when a narrower question warrants '
                  'iteration; what it returns is shown to you as child_returns. A child earns credit in this '
                  'episode only through the records it returns.')
REVISE_DESCRIPTION = ('Prepare a different thought pattern and/or selected actual tools for a new child investigating '
                      'the same evidence axis. Return its selection for a separately selected child commission with '
                      "the child's scope, constraints and typed return. Copy result.selection and revision_origin "
                      'into that assignment. Changes no current process, starts no child and records no '
                      'biological observation. Select the actual tools from those offered for the desired '
                      'investigation.')


def open_library(settings):
    """The frozen experimental-activity library (the old ``self.library``), at the settings' directory."""
    return ExperimentalActivityEvidenceLibrary(settings['library_directory'])


def axis_entry(library, selection):
    """The selected evidence-axis entry in its own view and the goal text of its version (the old
    ``ScientificGoal.instructions`` branch and ``decision_context``)."""
    entry = library.resolve(selection['evidence_axis'])
    version = entry.get('entry_version')
    if version == INSTRUCTION_VERSION:
        return instruction_view(entry), INSTRUCTION_ENTRY_GOAL
    if version == EVIDENCE_AXIS_VERSION:
        return evidence_axis_instruction_view(entry), EVIDENCE_AXIS_ENTRY_GOAL
    raise ValueError('scientific_support_entry_invalid')


def offered(summary):
    """The tools offered now (library names): the registry tools the commissioner selected, the library lookups,
    the revision preparation and the reasoning commit. A selected tool this episode does not have raises."""
    selected = [item['name'] for item in summary['selection']['child_tool_info']]
    unknown = sorted(set(selected) - set(REGISTRY_NAMES))
    if unknown:
        raise ValueError('a105_selected_tools_not_in_the_tool_library:' + ','.join(unknown))
    return [*[name for name in REGISTRY_NAMES if name in selected], *LIBRARY_LOOKUPS, 'process.revise', 'reason']


def catalog(names, commit_schema):
    """The tools the model is shown: python tool name, description and input schema (the old catalog; every input
    schema is projected through ``source_location_inputs``)."""
    entries = []
    for name in names:
        if name == 'reason':
            entries.append({'name': 'reason', 'description': REASON_DESCRIPTION,
                            'input_schema': reason_schema(commit_schema)})
        elif name == 'process.revise':
            entries.append({'name': 'process_revise', 'description': REVISE_DESCRIPTION,
                            'input_schema': REVISION_ARGUMENTS})
        else:
            description, schema = {**REGISTRY_DEFINITIONS, **LOOKUP_DEFINITIONS}[name]
            entries.append({'name': TOOL_NAMES[name], 'description': description,
                            'input_schema': source_location_inputs(schema)})
    return entries


def selection_schema(names, commit_schema):
    """What the model answers with: one tool and its arguments, or one child slot and its arguments (the old action
    schema: kinds ``tool`` and ``child``)."""
    tools = [obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']}, 'arguments': entry['input_schema']})
             for entry in catalog(names, commit_schema)]
    children = [obj({'kind': {'const': 'child'}, 'slot': {'const': slot}, 'arguments': CHILD_ARGUMENTS[slot][1]})
                for slot in CHILD_SLOTS]
    return obj({'selection': {'anyOf': [*tools, *children]}})


def invalid(name, arguments, ctx, error):
    """The old ``execute`` outcome for a contract error: an ``invalid`` outcome with feedback."""
    detail = {'detail': error.detail} if getattr(error, 'detail', None) else {}
    return {'status': 'invalid',
            'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': name, 'arguments': arguments}),
            'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'category': 'arguments_or_reference', 'code': str(error), **detail}}


async def run_registry_tool(name, envelope, ctx):
    """Execute one registry tool. A contract error is returned as an ``invalid`` outcome with
    ``arguments_or_reference`` feedback, as the old ``execute`` did; the outcome is the unit's outcome like any
    other."""
    arguments, scope = envelope['arguments'], envelope['scope']
    try:
        validate_schema(arguments, source_location_inputs(REGISTRY_DEFINITIONS[name][1]))
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


def run_lookup(name, envelope, ctx):
    """One lookup of the frozen library (the old ``execute_scientific_library``): ``process.search``,
    ``process.entry`` or ``process.sources``. The library reports its own failure in its outcome."""
    arguments = envelope['arguments']
    try:
        validate_schema(arguments, LOOKUP_DEFINITIONS[name][1])
    except (ContractError, ValidationError) as error:
        return invalid(name, arguments, ctx, error)
    return open_library(ctx.settings).execute(name, arguments)


def process_revise(arguments, ctx):
    """The old ``process.revise``: prepare a pinned thought pattern and selected tools for a new child. It returns
    the child selection and the revision origin for a separately selected child commission; it changes no current
    process, starts no child and is no observation (it earns nothing).

    The thought pattern is resolved against the frozen library (a reference that does not resolve is an
    ``invalid`` outcome); the old retrieval of the tool info against the tool library is the offered tool names
    here. ``parent_invocation_ref`` is this Episode's id (the old ``scientific_invocation_ref`` has no module in
    the library)."""
    envelope = arguments
    arguments, selection = envelope['arguments'], envelope['selection']
    try:
        validate_schema(arguments, REVISION_ARGUMENTS)
        open_library(ctx.settings).resolve(arguments['thought_pattern'])
        unknown = sorted({item['name'] for item in arguments['child_tool_info']} - set(REGISTRY_NAMES))
        if unknown:
            raise ValueError('scientific_tool_selection_unavailable:' + ','.join(unknown))
    except (ContractError, ValidationError, ValueError) as error:
        return invalid('process.revise', arguments, ctx, error)
    proposed = {'version': selection['version'], 'evidence_axis': selection['evidence_axis'],
                'thought_pattern': arguments['thought_pattern'], 'child_tool_info': arguments['child_tool_info']}
    operation_ref = identity('operation', {'key': ctx.operation_key, 'name': 'process.revise',
                                           'arguments': arguments})
    return {'status': 'completed', 'operation_ref': operation_ref, 'record_refs': [], 'changed_record_refs': [],
            'result': {'version': CHILD_SELECTION_VERSION, 'parent_selection_sha256': scientific_digest(selection),
                       'selection': proposed},
            'revision_origin': {'version': REVISION_ORIGIN_VERSION, 'parent_invocation_ref': ctx.episode_id,
                                'preparation_operation_ref': operation_ref},
            'feedback': None}


def reason_schema(commit_schema):
    """The ``reason`` tool's arguments: the required-grading action (the typed commit and ``evidence_processing``)."""
    return reasoning_schema(commit_schema, False)


def no_page(reference, representation):
    """The head reads no assigned page: a source read the grader makes is not contained in one (the old head passed
    no source authorization to the required grading)."""


def reason(arguments, ctx):
    """One reasoning unit: the interpretation and the grading sheets of its experiments committed together
    (``literature_reasoning.reason``, the required-grading action of AGENTS.md, "Required literature evidence
    processing"). The head populates no reader sheet, so a ``received_component`` route of the grader is refused
    with ``assay_grading_reader_namespace_unbound``."""
    return reasoning_unit(ctx.store, arguments['scope'], None, arguments['arguments'], ctx.operation_key,
                          arguments['proposed_annotation_ref'], no_page)


async def state_query(arguments, ctx):
    return await run_registry_tool('state.query', arguments, ctx)


async def source_read(arguments, ctx):
    return await run_registry_tool('source.read', arguments, ctx)


async def source_locate(arguments, ctx):
    return await run_registry_tool('source.locate', arguments, ctx)


async def source_sequence_references(arguments, ctx):
    return await run_registry_tool('source.sequence.references', arguments, ctx)


async def source_experimental_records(arguments, ctx):
    return await run_registry_tool('source.experimental.records', arguments, ctx)


async def source_archive_members(arguments, ctx):
    return await run_registry_tool('source.archive.members', arguments, ctx)


async def source_archive_extract(arguments, ctx):
    return await run_registry_tool('source.archive.extract', arguments, ctx)


async def source_pdf_info(arguments, ctx):
    return await run_registry_tool('source.pdf.info', arguments, ctx)


async def source_pdf_text(arguments, ctx):
    return await run_registry_tool('source.pdf.text', arguments, ctx)


async def source_pdf_page(arguments, ctx):
    return await run_registry_tool('source.pdf.page', arguments, ctx)


async def public_literature_search(arguments, ctx):
    return await run_registry_tool('public.literature.search', arguments, ctx)


async def public_literature_read(arguments, ctx):
    return await run_registry_tool('public.literature.read', arguments, ctx)


async def public_literature_sequence_identity(arguments, ctx):
    return await run_registry_tool('public.literature.sequence_identity', arguments, ctx)


async def public_ncbi_search(arguments, ctx):
    return await run_registry_tool('public.ncbi.search', arguments, ctx)


async def public_ncbi_sequence(arguments, ctx):
    return await run_registry_tool('public.ncbi.sequence', arguments, ctx)


async def public_taxonomy(arguments, ctx):
    return await run_registry_tool('public.taxonomy', arguments, ctx)


async def public_pmc_versions(arguments, ctx):
    return await run_registry_tool('public.pmc.versions', arguments, ctx)


async def public_pmc_files(arguments, ctx):
    return await run_registry_tool('public.pmc.files', arguments, ctx)


async def public_pmc_asset(arguments, ctx):
    return await run_registry_tool('public.pmc.asset', arguments, ctx)


async def public_sabiork_search(arguments, ctx):
    return await run_registry_tool('public.sabiork.search', arguments, ctx)


async def public_sabiork_read(arguments, ctx):
    return await run_registry_tool('public.sabiork.read', arguments, ctx)


async def public_brenda_search(arguments, ctx):
    return await run_registry_tool('public.brenda.search', arguments, ctx)


async def public_brenda_read(arguments, ctx):
    return await run_registry_tool('public.brenda.read', arguments, ctx)


async def public_bioassay_search(arguments, ctx):
    return await run_registry_tool('public.bioassay.search', arguments, ctx)


async def public_bioassay_read(arguments, ctx):
    return await run_registry_tool('public.bioassay.read', arguments, ctx)


async def public_chembl_search(arguments, ctx):
    return await run_registry_tool('public.chembl.search', arguments, ctx)


async def public_chembl_read(arguments, ctx):
    return await run_registry_tool('public.chembl.read', arguments, ctx)


async def public_mavedb_search(arguments, ctx):
    return await run_registry_tool('public.mavedb.search', arguments, ctx)


async def public_mavedb_read(arguments, ctx):
    return await run_registry_tool('public.mavedb.read', arguments, ctx)


async def public_brenda_graph_search(arguments, ctx):
    return await run_registry_tool('public.brenda.graph_search', arguments, ctx)


def process_search(arguments, ctx):
    return run_lookup('process.search', arguments, ctx)


def process_entry(arguments, ctx):
    return run_lookup('process.entry', arguments, ctx)


def process_sources(arguments, ctx):
    return run_lookup('process.sources', arguments, ctx)


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
    'public_ncbi_sequence': public_ncbi_sequence,
    'public_taxonomy': public_taxonomy,
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
    'process_search': process_search,
    'process_entry': process_entry,
    'process_sources': process_sources,
    'process_revise': process_revise, 'reason': reason}


THOUGHT_FIELDS = ('id', 'name', 'description', 'use_when', 'live_alternatives', 'decision_guidance',
                  'outcome_contingencies', 'boundary')


def child_options():
    """The children the model may select: slot, description and the arguments it takes (the old
    ``child_option_information``, over this episode's own slots)."""
    return [{'slot': slot, 'description': CHILD_ARGUMENTS[slot][0], 'arguments': CHILD_ARGUMENTS[slot][1]}
            for slot in CHILD_SLOTS]


def instructions(goal_text, *, knowledge):
    """The old task_instructions.instructions: the investigation text, the selected axis entry's goal text, the
    reasoning-commit requirement, the tool-knowledge text when it is offered, the child text. The decision-exchange
    paragraph, the pending-delivery paragraph, the wait paragraphs and the redeliver_report text are not carried:
    no such action exists."""
    text = replace_span(INSTRUCTIONS, HISTORY_START, HISTORY_END, HISTORY_GUIDANCE)
    text += '\n' + goal_text
    text += '\n' + REASONING_COMMIT_REQUIREMENT
    text += grading_section()
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    return text + CHILD_GUIDANCE


def decide(summary, feedback, ctx):
    """Ask the model for the next tool or child, shown the commission, the evidence-axis and thought-pattern
    guidance, the working state, the records it holds, the finding progress and its credit definition, its own
    outcomes, the children's returns, the tools, the measured time and the yield table (the old decision inputs
    and the head's ``decision_context``, over this episode's summary).

    Not carried: ``pending_work``, ``report_deliveries``, the visual evidence of ``image.view``,
    ``job_episode_options``, the resource and execution contexts and the native-event contexts (their sources are
    old-runner or job machinery with no module in the library)."""
    library = open_library(ctx.settings)
    axis_view, goal_text = axis_entry(library, summary['selection'])
    thought = library.resolve(summary['selection']['thought_pattern'])
    names = offered(summary)
    commit_schema = summary['reasoning_schema']
    progress = summary['progress']
    knowledge_directory = ctx.settings['knowledge_library_directory']
    context = {'goal': GOAL, 'scope': summary['scope'], 'proposed_annotation_ref': summary['proposed_annotation_ref'],
               'evidence_task': summary['evidence_task'], 'constraints': summary['constraints'],
               'revision_origin': summary['revision_origin'],
               'experimental_activity_evidence': {
                   'selection': summary['selection'], 'evidence_axis': axis_view,
                   'thought_pattern': {name: thought[name] for name in THOUGHT_FIELDS if name in thought},
                   'tools': [item['name'] for item in summary['selection']['child_tool_info']],
                   'permitted_children': list(CHILD_SLOTS)},
               'working_state': summary['working_state'], 'visible_record_refs': summary['held_record_refs'],
               'current_credit': progress['credit'],
               'investigation_progress': {key: progress[key] for key in
                                          ('retained_finding_count', 'inactive_dependencies', 'detail_pages')},
               'credit_binding': summary['credit_binding'], 'own_outcomes': summary['own_outcomes'],
               'last_local_outcome': summary['last_local_outcome'], 'child_returns': summary['child_returns'],
               'child_options': child_options(), 'tools': catalog(names, commit_schema),
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['action_yields'],
        'tool_knowledge': None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(goal_text, knowledge=context.get('tool_knowledge')), context,
                        generation_schema(selection_schema(names, commit_schema)))


def validate_selection(value, schema):
    validate_schema(value, schema)
    return value['selection']


def named_records(slot, arguments):
    """The records the model's own commission names (the old ``evidence_refs`` and the literature sources)."""
    assignment = arguments['assignment']
    if slot == 'experimental_activity_evidence':
        return [*assignment['evidence_refs'], *([assignment['proposed_annotation_ref']]
                                                  if 'proposed_annotation_ref' in assignment else [])]
    return [*assignment['question_context_refs'], *assignment['source_refs'], assignment['proposed_annotation_ref']]


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one child commission, or reject it (no unit). An answer that
    selects no offered tool or slot, arguments that do not fit their schema, an empty reasoning commit, or a
    commission naming a record this episode does not hold is invalid (validation of the model's own answer).
    What ``msg_to_child`` builds is not checked here: a wrong commission fails where the child is built."""
    names = offered(summary)
    commit_schema = summary['reasoning_schema']
    schema = selection_schema(names, commit_schema)
    try:
        selection = validate_selection(decode_response(response, schema), schema)
        if selection['kind'] == 'child':
            for reference in named_records(selection['slot'], selection['arguments']):
                if not records.holds(reference):
                    raise ContractError('reference_unavailable', detail={'reference': reference})
            return ChildCall(selection['slot'], selection['arguments'])
        name, arguments = selection['tool'], selection['arguments']
        if name == 'reason' and empty_commit(arguments['commit'], commit_schema) and (
                arguments.get('evidence_processing', {}).get('kind') != 'no_applicable_evidence'):
            raise ValueError('empty_reasoning_commit')
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(name, {'arguments': arguments, 'scope': summary['scope'], 'selection': summary['selection'],
                           'proposed_annotation_ref': summary['proposed_annotation_ref']})
