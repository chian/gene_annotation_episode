"""The task: look up the process the selection names, use the tools of the selection (none of them searches for,
fetches or reads a paper's text: that is the literature chain's), commit reasoning on the records it holds together with
its contextual grading sheets, prepare a revised selection for a new child, or commission a child (a narrower A108
sample-context investigation by this binding itself, or the literature chain: the published evidence assessment, whose
one task is the verified source leads).

Carried from the old task.py, task_decision.py, task_instructions.py, scientific_operations.py,
scientific_contracts.py, library_operations.py, library_services.py, source_references.py and
execution_planning.py of ``sample_context_evidence`` at 97308b94c. One unit is one model-selected tool call or one child
commission. The task always offers a unit and never ends the Episode: only the yield controller does. The old actions
``wait`` and ``redeliver_report`` do not exist.

The initial lookups are the first part of the task and are offered through its own tool, ``process_selection``: when no
lookup has completed, ``decide`` returns it and it reads the evidence axis, the thought pattern and the tool information
the selection names (the old ``library.resolve`` of ``decision_context`` and ``tool_library.resolve_tool_info`` of
``materialize``). Its outcome tells which of the two old goal texts applies (the axis entry is an instruction entry, which
replaces the default instructions, or an evidence-axis entry, which is appended to them).

Tools: the process library (``process_search``, ``process_entry``, ``process_sources``), the tool retrieval
(``process_tools``), the tool knowledge when ``knowledge_library_directory`` is set, ``process_revise`` (the old
``process.revise``), the tools the selection names (the old direct tools, resolved from ``selection.child_tool_info``; a
selected tool may not reuse a common name), ``reason`` (the required-grading action of ``literature_required_grading``:
the interpretation and the purpose-specific contextual grader selected for it are committed in one tool call and the
interpretation is refused unless its subscoring sheet is saved; AGENTS.md, "Required literature evidence processing"). There is no report tool: the return is the controlled features code reads from the saved sheets. The old head's ``reason`` ran ``store.commit_reasoning``
without a grader (contract_misfits); this one is the copy of the sibling literature episode's coupling, with this
episode's role.

Not carried (see the blocked file of this episode): the common tools ``episode.history``, ``episode.credit``,
``episode.annotation_score``, ``episode.monitoring_information``, ``episode.estimate_wait`` and ``shared.*`` (the
history and credit are the summary now; the others are old-runner or old-shared-root modules that are not in
``episode_support/``), ``process.execution`` (``execution_planning.py``: needs the old ``workflow.resource_context`` and
the execution memory, and its ``maxItems: 8`` and ``history(limit=64)`` are count limits the current rules forbid), and the
``library`` operations of ``library_operations.py`` (``execute_scientific_library``: no module).

Settings read (``ctx.settings``): ``process_library_directory`` (the frozen A/P option library),
``tool_library_directory`` (the frozen tool library), ``tool_registry`` (the keyword arguments of the library
``ToolRegistry`` with the ``PublicClients`` of the acquisition tools) and ``knowledge_library_directory`` (optional).
``yield_estimator.py`` reads no setting: its accumulation controller (``ADAPTIVE_CONTROL``, ``items=None``) takes no
cost and stops after 4 flat units in a row (see ``yield_estimator.py``)."""
from dataclasses import dataclass

from jsonschema import ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.configuration.sample_context_evidence.process_options import (
    SampleContextEvidenceLibrary, catalog as process_catalog, evidence_axis_instruction_view)
from gene_annotation_episode.episodic_workflow.episode_support.forms.sample_context_evidence.evidence_axis_contracts import (
    VERSION as EVIDENCE_AXIS_VERSION)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.instructions.sample_context_evidence.evidence_axis_instructions import (
    VERSION as INSTRUCTION_VERSION, instruction_view)
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.sample_context_evidence.literature_required_grading import (
    action_schema as required_grading_schema, execute as execute_required_grading)
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.literature_grading_inputs import (
    grading_population_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_context_findings import (
    GRADING_INSTRUCTIONS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.sample_context_evidence.literature_investigation_prompt import (
    INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_sequence_discovery import (
    references_schema)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_grading_storage import (
    COMPONENTS as GRADING_COMPONENTS, LiteratureA108GradingRepository)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_aggregation import (
    COMPONENTS as AGGREGATION_COMPONENTS)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.sample_context_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sample_context_evidence.source_locations import (
    locate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_operations.sample_context_evidence.source_sequences import (
    scan_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.construction_records import (
    CHILD_SELECTION_VERSION, REVISION_ORIGIN_VERSION, SELECTION_VERSION, scientific_digest,
    scientific_invocation_ref, validate_child_selection, validate_revision_origin, validate_selection)
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import (
    ContractError, RECORD_SCHEMAS, REF, REFS, identity, obj, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.tools.sample_context_evidence.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_and_context_sources.sample_context_evidence.ncbi_entrez_tools import (
    ncbi_entrez_tool_contract)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_catalog import (
    ScientificToolLibrary, catalog as tool_retrieval_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge, catalog as knowledge_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

from .goal import GOAL

# The two children (the old ``child_roles``: ``sample_context_evidence`` and ``literature``), by slot.
CHILD_SLOTS = {
    'sample_context_evidence': 'sample_context_evidence',
    'published_evidence_assessment': 'sample_context_evidence/published_evidence_assessment',
}
# The public acquisition clients (``PublicClients``) are the declared service ``public_clients``; the tool registry's JSON
# settings are the setting ``tool_registry``.
SERVICES = ('public_clients',)

INTEGER = {'type': 'integer', 'minimum': 0}
POSITIVE = {'type': 'integer', 'minimum': 1}
TEXT = {'type': 'string', 'minLength': 1}
SHA256 = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
THOUGHT_FIELDS = ('id', 'name', 'description', 'use_when', 'live_alternatives', 'decision_guidance',
                  'outcome_contingencies', 'boundary')
RESOURCES = ['api', 'local', 'hpc']

# The old ``_COMMON_TOOLS`` this episode carries (library name -> tool name), and the one it prepares with.
COMMON = {'process.search': 'process_search', 'process.entry': 'process_entry', 'process.sources': 'process_sources',
          'process.tools': 'process_tools', 'knowledge.search': 'knowledge_search',
          'knowledge.entry': 'knowledge_entry', 'knowledge.read': 'knowledge_read'}
REVISE = 'process.revise'
# Tools whose source reads are bound to the records this episode holds (the old ``source.locate`` limit).
HELD_SOURCE_TOOLS = ('source.locate', 'source.sequence.references', 'source.sequence.scan')

# The old goal text of an axis entry that is an evidence-axis entry (appended to the default instructions).
EVIDENCE_AXIS_INSTRUCTIONS = (
    "Investigate the parent's assigned scientific problem iteratively in the shared Episode loop. The selected "
    "scientific support proposition and operands define the support problem; the thought pattern supplies "
    "alternatives and outcome-sensitive guidance; the selected real tools supply their exact callable contracts. "
    "Choose your own actions using actual outcomes and received child forms. The selection is no prescribed sequence "
    "or automatic compatibility verdict. Library sources are instruction provenance, not scientific evidence about "
    "this target. Inspect actual source subjects, conditions and target applicability before interpreting evidence. "
    "annotation_support_routes describes the actual separately bound annotation policy's kind dispatch. An unmapped "
    "kind has no base-axis mapping in that known policy. Unavailable metadata means this reader cannot declare the "
    "bound policy; it is no verdict on evidence or the actual score. Metadata itself earns no credit and never "
    "replaces or filters the actual projectors, annotation formula or continuation rule. Keep the parent's "
    "objective, scope, constraints and exact return fields; support metadata never adds fields or scoring axes. Use "
    "common reasoning to commit scientific interpretations. Keep the originally assigned scientific support, thought "
    "pattern and selected tool set throughout this episode. Explicit process_revise prepares a selection for a new "
    "child; a separately selected child commission starts that child with its own job, scope and return fields. "
    "Preparation changes no current process and starts no child. Copy both result.selection and revision_origin into "
    "that child's commission to identify it as an alternative approach. Only retrieved actual tools are available; "
    "their descriptions do not grant execution. The configured controller owns continuation.")
HISTORY_START = 'On a fresh provider conversation,'
HISTORY_END = 'Do not execute native provider tools.'
HISTORY_GUIDANCE = ('Your own earlier outcomes are shown to you as own_outcomes; that page creates no new action and '
                    'does not execute or credit the historical work again.\n')
LITERATURE_GUIDANCE = ('\nYou run no literature search, fetch no paper and read no paper text yourself. The literature '
                       'chain does that: commission the published evidence assessment child for the proposed '
                       'annotation (its strategy writes the searches, its search picks a paper, its page examines it, '
                       'and what is found is graded there automatically). It takes one task, the verified source '
                       'leads.')
RETURN_GUIDANCE = ('\nWhat returns to your parent is your credit and the counts code reads from the A108 sheets you and your '
                   'children saved, with their references and the assessments committed with grading; nothing you '
                   'write in prose is returned. Selecting a tool never ends your work: only the numerical controller '
                   'does.')

# The input schemas of the tools a selection can name (the registry's own definitions, ``ToolRegistry.catalog``); the
# descriptions come from the selection's own tool information.
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
    'source.locate': locate_schema(),
    'source.sequence.references': references_schema(),
    'source.sequence.scan': scan_schema(),
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
    'public.ncbi.search': obj({'database': {'enum': ['protein', 'nuccore', 'assembly', 'taxonomy', 'biosample',
                                                     'bioproject']},
                               'term': TEXT, 'size': POSITIVE, 'offset': INTEGER}, ['database', 'term']),
    'public.ncbi.sequence': obj({'accession': TEXT, 'database': {'enum': ['protein', 'nuccore']},
                                 'start': INTEGER, 'end': POSITIVE}, ['accession', 'database']),
    'public.ncbi.entrez': ncbi_entrez_tool_contract()['input_schema'],
    'public.taxonomy': obj({'taxon_id': POSITIVE}),
}
INPUT_SCHEMAS['execution.estimate'] = {'anyOf': [
    obj({'tool': {'const': name}, 'arguments': INPUT_SCHEMAS[name]}) for name in ('source.xlsx.sheets', 'source.xlsx.rows')]}
ACCESS = {name: name.replace('.', '_') for name in INPUT_SCHEMAS}
# The reading authorization the grading repository asks before it reads a source the head holds (the head offers no
# tool that reads a paper's text: this is the schema of the authorization, not an offered tool).
SOURCE_READ = obj({'source_ref': REF, 'offset': INTEGER, 'limit': POSITIVE,
                   'representation': {'enum': ['text', 'original', 'stdout', 'stderr']}}, ['source_ref'])

# A Store scope within this scope, in the closed form ``Store.validate_scope`` admits (BINDING_CONTRACT.md, C1).
SCOPE_SCHEMA = {**obj({
    'subject_refs': {'type': 'array', 'minItems': 1, 'items': REF,
                     'description': 'Subject references of this scope the child investigates.'},
    'segments': {'type': 'array', 'minItems': 1,
                 'description': 'Optional original-coordinate intervals; one or more per subject.',
                 'items': obj({'target_ref': REF, 'start': INTEGER, 'end': POSITIVE, 'unit': REF, 'member_ref': REF},
                              required=['target_ref', 'start', 'end', 'unit'])},
    'read_selection_refs': {'type': 'array', 'minItems': 1, 'items': REF,
                            'description': 'Optional read selections of library subjects in this scope.'},
}, required=['subject_refs']), 'description': 'A Store scope within this scope.'}


def option_schema(slot, prefix):
    """The old ``_ref_schema``: a pinned option reference."""
    return obj({'version': {'const': 'sample_context_evidence_option_ref_v1'}, 'library_id': SHA256,
                'slot': {'const': slot}, 'option_id': {'type': 'string', 'pattern': '^' + prefix + '[0-9]+$'},
                'entry_sha256': SHA256})


AXIS_REF = option_schema('evidence_axis', 'A')
AXIS_REF['properties']['option_id'] = {'const': 'A108'}
THOUGHT_REF = option_schema('thought_pattern', 'P')
TOOL_SELECTOR = obj({'name': TEXT, 'resources': {'enum': RESOURCES}})
TOOL_INFO = obj({**TOOL_SELECTOR['properties'], 'description': TEXT, 'instructions': TEXT})
REVISION_ARGUMENTS = obj({'thought_pattern': THOUGHT_REF,
                          'child_tool_info': {'type': 'array', 'items': TOOL_SELECTOR, 'uniqueItems': True}})
CHILD_SELECTION = obj({'version': {'const': SELECTION_VERSION}, 'evidence_axis': AXIS_REF,
                       'thought_pattern': THOUGHT_REF,
                       'child_tool_info': {'type': 'array', 'items': TOOL_INFO, 'uniqueItems': True}})
REVISION_ORIGIN = obj({'version': {'const': REVISION_ORIGIN_VERSION},
                       'parent_invocation_ref': {'type': 'string', 'pattern': '^scientific_invocation_[a-f0-9]{24}$'},
                       'preparation_operation_ref': {'type': 'string', 'pattern': '^operation_[a-f0-9]{24}$'}})
HELD_REFS = {'type': 'array', 'items': REF, 'uniqueItems': True}
COMMITTED = 'committed_record_refs'
LITERATURE_FIELDS = ['literature_source_lead_dispositions',
                     'literature_a108_grading_cells', 'literature_a108_aggregation_cells']
LITERATURE_VERSION = 'literature_local_task_v1'


def literature_task_schema():
    """The commissioned A108 literature task (private copy of the old ``goal.task_schema`` of ``literature``)."""
    return obj({'version': {'const': LITERATURE_VERSION}, 'evidence_axis': {'const': 'A108'},
                'credit_unit': {'type': 'number', 'exclusiveMinimum': 0}, 'kind': {'const': 'verified_source_leads'}})


SELF_ARGUMENTS = obj({
    'objective': TEXT, 'purpose': TEXT, 'scope': SCOPE_SCHEMA,
    'selection': CHILD_SELECTION, 'evidence_refs': HELD_REFS,
    'revision_origin': {'anyOf': [REVISION_ORIGIN, {'type': 'null'}]},
    'return_fields': {'type': 'array', 'uniqueItems': True, 'items': {'enum': [COMMITTED]}}})
LITERATURE_ARGUMENTS = obj({
    'objective': TEXT, 'purpose': TEXT, 'scope': SCOPE_SCHEMA,
    'assignment': obj({
        'question_context_refs': HELD_REFS, 'literature_task': literature_task_schema(),
        'requested_a108_grading_components': {'type': 'array', 'uniqueItems': True,
                                              'items': {'enum': list(GRADING_COMPONENTS)}},
        'requested_a108_aggregation_components': {'type': 'array', 'uniqueItems': True,
                                                  'items': {'enum': list(AGGREGATION_COMPONENTS)}}}),
    'return_fields': {'type': 'array', 'uniqueItems': True, 'items': {'enum': LITERATURE_FIELDS}}})
CHILD_ARGUMENTS = {'sample_context_evidence': SELF_ARGUMENTS, 'published_evidence_assessment': LITERATURE_ARGUMENTS}
CHILD_DESCRIPTIONS = {
    'sample_context_evidence': 'Commission a narrower A108 sample-context investigation over a sub-scope of this '
                               'scope; it returns its credit and the findings it retained. For an alternative '
                               'approach copy selection and revision_origin from process_revise.',
    'published_evidence_assessment': 'Commission the A108 literature chain for the proposed annotation: its strategy '
                                     'writes the searches, its search runs each one and picks a paper, its page '
                                     'examines the paper and the findings are graded there. You search for, fetch '
                                     'and read no paper yourself; it returns its credit and the findings it '
                                     'retained.',
}
REASON_DESCRIPTION = ('Commit a typed scientific reasoning over the selected table or sheet and the records you hold: '
                      'extracted terms, source subjects, contexts, observations, hypotheses and assessments, each '
                      'with its exact source anchor, together with the contextual grader selected for the '
                      'interpretation (evidence_processing) in this one call. An interpretation is not saved '
                      'without its subscoring sheet; only a source-grounded finding that the examined material has '
                      'no applicable contextual observation omits grading. A commit with every section empty is '
                      'rejected.')
REVISE_DESCRIPTION = (
    "Prepare a different thought pattern and/or selected actual tools for a new child investigating the same "
    "evidence axis. Return its selection for a separately selected child commission with the child's job, scope and "
    "return fields. Copy result.selection and revision_origin into that commission. Changes no current process, "
    "starts no child and records no biological observation. Select the actual tool/resource choices returned by "
    "process_tools for the desired investigation.")


@dataclass(frozen=True)
class GradingContext:
    """The context the A108 sheet repository and the required-grading logic read (the old binding context): this
    episode's identity, its commission and the records it holds now (private copy; library candidate)."""
    run_id: str
    episode_id: str
    role: str
    path: tuple
    scope: dict
    assignment: dict
    request: dict
    received_record_refs: tuple


def python_name(name):
    return name.replace('.', '_')


def selected_tools(process):
    """The selection's own tools, by library name: never a common name or ``process.revise``, always callable here."""
    names = [row['name'] for row in process['child_tool_info']]
    for name in names:
        if name in COMMON or name == REVISE:
            raise ContractError('scientific_primitive_uses_common_tool_name')
        if name not in ACCESS:
            raise ContractError('scientific_selected_tool_not_callable:' + name)
    return names


def offered(summary, settings):
    """The tools and slots offered now: the common tools this episode carries, ``process_revise``, the selection's
    tools, the reasoning commit and the two children."""
    common = [name for name in COMMON if not name.startswith('knowledge.') or settings.get('knowledge_library_directory')]
    return [*(COMMON[name] for name in common), 'process_revise',
            *(ACCESS[name] for name in selected_tools(summary['process'])), 'reason', *CHILD_SLOTS]


def reason_schema(commit_schema):
    """The old ``execute_reasoning`` action: the required-grading action (the typed commit with its
    ``evidence_processing``: the contextual grader selected for the interpretation, or the source-grounded
    no-applicable-evidence declaration)."""
    return source_location_inputs(
        required_grading_schema(commit_schema, source_location_inputs(grading_population_schema())))


def catalog(summary, names):
    """The tools the model is shown: name, description and input schema."""
    process = summary['process']
    rows = {python_name(row['name']): row for row in process['child_tool_info']}
    library = {python_name(entry['name']): entry for entry in [*process_catalog(), *tool_retrieval_catalog(),
                                                               *knowledge_catalog()]}
    entries = []
    for name in names:
        if name in CHILD_SLOTS:
            entries.append({'name': name, 'description': CHILD_DESCRIPTIONS[name],
                            'input_schema': CHILD_ARGUMENTS[name]})
        elif name == 'reason':
            entries.append({'name': 'reason', 'description': REASON_DESCRIPTION,
                            'input_schema': reason_schema(summary['reasoning_schema'])})
        elif name == 'process_revise':
            entries.append({'name': name, 'description': REVISE_DESCRIPTION, 'input_schema': REVISION_ARGUMENTS})
        elif name in library:
            entries.append({'name': name, 'description': library[name]['description'],
                            'input_schema': library[name]['input_schema']})
        else:
            row = rows[name]
            entries.append({'name': name, 'library_name': row['name'], 'resources': row['resources'],
                            'description': row['description'],
                            'input_schema': source_location_inputs(INPUT_SCHEMAS[row['name']])})
    return entries


def selection_schema(summary, names):
    """What the model answers with: one tool or child and its arguments (the old action schema)."""
    return obj({'selection': {'anyOf': [obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']},
                                             'arguments': entry['input_schema']})
                                        for entry in catalog(summary, names)]}})


def instructions(process, knowledge):
    """The old ``task_instructions.instructions``: the goal text of an instruction-entry axis replaces the default
    instructions; otherwise the evidence-axis text is appended to them. Then the reasoning-commit requirement, the
    tool-knowledge text when offered, the A108 grading instructions and the return guidance. The decision-exchange,
    pending-delivery, wait and
    native-event paragraphs are not carried: no such action exists."""
    if process['evidence_axis_entry_version'] == INSTRUCTION_VERSION:
        text = GOAL
    else:
        text = replace_span(INSTRUCTIONS, HISTORY_START, HISTORY_END, HISTORY_GUIDANCE) + '\n' + EVIDENCE_AXIS_INSTRUCTIONS
    text += '\n' + REASONING_COMMIT_REQUIREMENT
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    text += GRADING_INSTRUCTIONS
    return text + LITERATURE_GUIDANCE + RETURN_GUIDANCE


def outcome_of(result):
    """A lookup's outcome in the shape of a tool outcome."""
    return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': result, 'feedback': None}


def invalid_outcome(ctx, name, arguments, error):
    """The old invalid outcome of ``execute``: a contract error is returned as ``arguments_or_reference`` feedback."""
    detail = getattr(error, 'detail', None)
    return {'status': 'invalid',
            'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': name, 'arguments': arguments}),
            'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'category': 'arguments_or_reference', 'code': getattr(error, 'code', str(error)),
                         **({'detail': detail} if detail else {})}}


def process_selection(arguments, ctx):
    """The initial lookups: the evidence axis, the thought pattern and the tool information the selection names (the
    old ``library.resolve`` of the decision context and ``tool_library.resolve_tool_info`` of ``materialize``). An axis
    entry that is neither an instruction nor an evidence-axis entry raises (old ``scientific_support_metadata_required``)."""
    selection = arguments['selection']
    library = SampleContextEvidenceLibrary(ctx.settings['process_library_directory'])
    axis = library.resolve(selection['evidence_axis'])
    if axis.get('entry_version') == INSTRUCTION_VERSION:
        view = instruction_view(axis)
    elif axis.get('entry_version') == EVIDENCE_AXIS_VERSION:
        view = evidence_axis_instruction_view(axis)
    else:
        raise ContractError('scientific_support_metadata_required')
    thought = library.resolve(selection['thought_pattern'])
    information = ScientificToolLibrary(ctx.settings['tool_library_directory']).resolve_tool_info(
        selection['child_tool_info'])
    return outcome_of({'evidence_axis': view, 'evidence_axis_entry_version': axis['entry_version'],
                       'thought_pattern': {name: thought[name] for name in THOUGHT_FIELDS if name in thought},
                       'child_tool_info': information,
                       'initial_selection_sha256': scientific_digest(selection)})


def process_search(arguments, ctx):
    return SampleContextEvidenceLibrary(ctx.settings['process_library_directory']).execute(
        'process.search', arguments['arguments'])


def process_entry(arguments, ctx):
    return SampleContextEvidenceLibrary(ctx.settings['process_library_directory']).execute(
        'process.entry', arguments['arguments'])


def process_sources(arguments, ctx):
    return SampleContextEvidenceLibrary(ctx.settings['process_library_directory']).execute(
        'process.sources', arguments['arguments'])


def process_tools(arguments, ctx):
    """The old ``process.tools``: the test retrieval of the tool library for an investigation."""
    library = ScientificToolLibrary(ctx.settings['tool_library_directory'])
    return outcome_of(library.retrieve_literal_test(arguments['arguments']['investigation']))


def knowledge_search(arguments, ctx):
    return ToolKnowledge(ctx.settings['knowledge_library_directory']).execute('knowledge.search',
                                                                              arguments['arguments'])


def knowledge_entry(arguments, ctx):
    return ToolKnowledge(ctx.settings['knowledge_library_directory']).execute('knowledge.entry',
                                                                              arguments['arguments'])


def knowledge_read(arguments, ctx):
    return ToolKnowledge(ctx.settings['knowledge_library_directory']).execute('knowledge.read',
                                                                              arguments['arguments'])


def process_revise(arguments, ctx):
    """The old ``process.revise``: prepare a different thought pattern and/or tool selection for a new child on the same
    axis. It returns ``sample_context_evidence_child_selection_v1`` and a ``revision_origin``, changes nothing now and
    starts no child. The proposal is the initial selection with the new thought pattern and the tool information the
    tool library resolves for the named tools (the old ``_proposed_selection``)."""
    revised, initial = arguments['arguments'], arguments['selection']
    try:
        validate_schema(revised, REVISION_ARGUMENTS)
        library = ScientificToolLibrary(ctx.settings['tool_library_directory'])
        proposed = validate_selection({'version': SELECTION_VERSION, 'evidence_axis': initial['evidence_axis'],
                                       'thought_pattern': revised['thought_pattern'],
                                       'child_tool_info': library.resolve_tool_info(revised['child_tool_info'])})
        child_selection = validate_child_selection({'version': CHILD_SELECTION_VERSION,
                                                    'parent_selection_sha256': scientific_digest(initial),
                                                    'selection': proposed})
        operation_ref = identity('operation', {'key': ctx.operation_key, 'name': REVISE, 'arguments': revised})
        origin = validate_revision_origin({
            'version': REVISION_ORIGIN_VERSION,
            'parent_invocation_ref': scientific_invocation_ref(ctx.run_id, [[ctx.binding_path, ctx.episode_id]]),
            'preparation_operation_ref': operation_ref})
    except (ContractError, ValidationError, ValueError) as error:
        return invalid_outcome(ctx, REVISE, revised, error)
    return {'status': 'completed', 'operation_ref': operation_ref, 'record_refs': [], 'changed_record_refs': [],
            'result': child_selection, 'revision_origin': origin, 'feedback': None}


async def run_access_tool(name, envelope, ctx):
    """Execute one tool of the selection: the old ``execute`` of ``ScientificOperations``. A contract error is
    returned as an ``invalid`` outcome, as the old ``execute`` did; the outcome is the unit's outcome like any other."""
    arguments, scope = envelope['arguments'], envelope['scope']
    try:
        validate_schema(arguments, source_location_inputs(INPUT_SCHEMAS[name]))
    except (ContractError, ValidationError) as error:
        return invalid_outcome(ctx, name, arguments, error)
    registry = ToolRegistry(ctx.store, clients=ctx.services['public_clients'], **ctx.settings['tool_registry'])
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


async def source_locate(arguments, ctx):
    return await run_access_tool('source.locate', arguments, ctx)


async def source_sequence_references(arguments, ctx):
    return await run_access_tool('source.sequence.references', arguments, ctx)


async def source_sequence_scan(arguments, ctx):
    return await run_access_tool('source.sequence.scan', arguments, ctx)


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


async def execution_estimate(arguments, ctx):
    return await run_access_tool('execution.estimate', arguments, ctx)


async def public_ncbi_search(arguments, ctx):
    return await run_access_tool('public.ncbi.search', arguments, ctx)


async def public_ncbi_sequence(arguments, ctx):
    return await run_access_tool('public.ncbi.sequence', arguments, ctx)


async def public_ncbi_entrez(arguments, ctx):
    return await run_access_tool('public.ncbi.entrez', arguments, ctx)


async def public_taxonomy(arguments, ctx):
    return await run_access_tool('public.taxonomy', arguments, ctx)


def grading_context(ctx, envelope):
    """The context the grading repository and the required-grading logic read (the old binding context)."""
    return GradingContext(
        run_id=ctx.run_id, episode_id=ctx.episode_id, role='sample_context_evidence',
        path=tuple(ctx.binding_path.split('/')), scope=envelope['scope'], assignment=envelope['assignment'],
        request={'goal': GOAL, 'scope': envelope['scope']}, received_record_refs=tuple(ctx.store.refs()))


def reason(arguments, ctx):
    """Commit the model's typed reasoning with its contextual grader: the required-grading action of the library
    (``literature_required_grading.execute``: the commit and the sheet are saved together, or nothing). The old head ran
    ``store.commit_reasoning`` alone; the coupling is AGENTS.md, "Required literature evidence processing" (this is the
    sibling literature episode's ``reason`` without the source lead)."""
    selection = arguments['arguments']
    store = ctx.store
    context = grading_context(ctx, arguments)
    repository = LiteratureA108GradingRepository(store)

    def authorize_source_access(reference, representation):
        reading = {'source_ref': reference, 'representation': representation}
        validate_schema(reading, source_location_inputs(SOURCE_READ))
        repository.authorize_source_access(context, reference, representation, 'source.read')
    return execute_required_grading(context, selection, ctx.operation_key, repository,
                                    authorize_source_access=authorize_source_access)


TOOLS = {'process_selection': process_selection, 'process_search': process_search, 'process_entry': process_entry,
         'process_sources': process_sources, 'process_tools': process_tools, 'process_revise': process_revise,
         'knowledge_search': knowledge_search, 'knowledge_entry': knowledge_entry, 'knowledge_read': knowledge_read,
         'state_query': state_query, 'source_locate': source_locate,
         'source_sequence_references': source_sequence_references, 'source_sequence_scan': source_sequence_scan,
         'image_view': image_view, 'source_archive_members': source_archive_members,
         'source_archive_extract': source_archive_extract, 'source_xlsx_sheets': source_xlsx_sheets,
         'source_xlsx_rows': source_xlsx_rows, 'execution_estimate': execution_estimate,
         'public_ncbi_search': public_ncbi_search, 'public_ncbi_sequence': public_ncbi_sequence,
         'public_ncbi_entrez': public_ncbi_entrez,
         'public_taxonomy': public_taxonomy, 'reason': reason}


def decide(summary, feedback, ctx):
    """Ask the model for the next tool or child commission, shown the selection and what it names (the evidence axis,
    the thought pattern, the tools), the scope, the finding progress, the working state, its own outcomes, what its
    children returned, the controlled features of the saved sheets, the latest image it looked at, the preparations of revised
    selections, the measured time and the yield table (the old decision state and inputs, over this episode's
    summary). Until the first lookup completed the first unit is the lookup itself."""
    process = summary['process']
    if process is None:
        return ToolCall('process_selection', {'selection': summary['selection']})
    names = offered(summary, ctx.settings)
    directory = ctx.settings.get('knowledge_library_directory')
    knowledge = None if directory is None else ToolKnowledge(directory).context()
    context = {
        'goal': GOAL, 'scope': summary['scope'], 'evidence_task': summary['evidence_task'],
        'sample_context_evidence': {
            'selection': summary['selection'], 'initial_selection_sha256': process['initial_selection_sha256'],
            'evidence_axis': process['evidence_axis'], 'thought_pattern': process['thought_pattern'],
            'child_tool_info': process['child_tool_info'], 'assignment': summary['assignment'],
            'permitted_children': list(CHILD_SLOTS)},
        'proposed_annotation_ref': summary['proposed_annotation_ref'],
        'initial_references': summary['initial_references'],
        'working_state': summary['working_state'], 'visible_record_refs': summary['held_record_refs'],
        'known_assessment_refs': summary['known_assessment_refs'],
        'current_credit': summary['current_credit'], 'credit_binding': summary['credit_binding'],
        'investigation_progress': summary['investigation_progress'],
        'time_accounting': time_accounting(ctx.clock.progress_time), 'action_yields': summary['action_yields'],
        'own_outcomes': summary['own_outcomes'], 'last_local_outcome': summary['last_local_outcome'],
        'visual_evidence': summary['visual_evidence'], 'revision_proposals': summary['revision_proposals'],
        'current_findings': summary['finding'], 'child_reports': summary['child_reports'],
        'tools': catalog(summary, names), 'feedback': feedback, 'tool_knowledge': knowledge,
    }
    return ModelRequest('REASONING', instructions(process, knowledge), context,
                        generation_schema(selection_schema(summary, names)))


def empty_commit(commit, commit_schema):
    """The old empty-reasoning test: every section the schema names is present or absent and none has a row."""
    return (set(commit_schema.get('required', commit_schema['properties'])) <= set(commit)
            <= set(commit_schema['properties']) and all(value == [] for value in commit.values()))


def held(records, references):
    """The old ``reference_in_context`` of the references a model names: each is a record this episode holds."""
    for reference in references:
        if not records.holds(reference):
            raise ContractError('scientific_reference_unavailable', detail={'reference': reference})


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one child commission, or reject it (no unit). An answer that
    selects no offered tool or child, arguments that do not fit its schema, an empty reasoning commit (except a
    no-applicable-evidence declaration) or a model-named reference this episode does not hold is invalid."""
    names = offered(summary, ctx.settings)
    schema = selection_schema(summary, names)
    try:
        value = decode_response(response, schema)
        validate_schema(value, schema)
        name, arguments = value['selection']['tool'], value['selection']['arguments']
        if name == 'sample_context_evidence':
            held(records, arguments['evidence_refs'])
            return ChildCall(name, arguments)
        if name == 'published_evidence_assessment':
            held(records, arguments['assignment']['question_context_refs'])
            return ChildCall(name, arguments)
        if (name == 'reason' and empty_commit(arguments['commit'], summary['reasoning_schema'])
                and arguments.get('evidence_processing', {}).get('kind') != 'no_applicable_evidence'):
            raise ValueError('empty_reasoning_commit')
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    return ToolCall(name, {'arguments': arguments, 'scope': summary['scope'], 'selection': summary['selection'],
                           'assignment': summary['assignment']})
