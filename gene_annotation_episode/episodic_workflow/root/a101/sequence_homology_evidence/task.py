"""The task of the A101 head: one model-selected unit per decision. The model investigates the assigned subject with
the selected tools of its commission (``execute_selected_tool``), commits scientific interpretations (``reason``),
prepares an alternative selection for a new child (``process_revise``), and commissions its children (launch,
monitor, results, published evidence, a recursive investigation). It never ends the Episode: only the yield
controller does. The old ``wait`` and ``redeliver_report`` actions are not carried (a child completes inside the
unit that commissioned it); the old ``request_context`` / ``select_action`` exchange is not carried (a lookup is a
tool, and own earlier attempts are ``own_outcomes`` of the context).

Carried from the old ``task.py``, ``task_decision.py``, ``task_instructions.py``, ``decision_inputs.py``,
``tool_selection.py``, ``scientific_operations.py``, ``alternate_process_selection.py``, ``execution_planning.py``
and the goal bodies of ``goal.py`` at 97308b94c.

Tools. ``reason`` is the old ``store.commit_reasoning`` path of ``execute``. ``execute_selected_tool`` is the old
dispatch of ``scientific_operations.execute`` to the services' tool executor for the tool the commission selected
(the old tool names are dotted and a tool name here has lowercase letters, digits and underscores, so the selected
name travels as an argument; the library's ``ToolRegistry`` is called with ``ctx.store``). ``process_revise`` is the
old ``process.revise``. ``process_execution`` (the old ``process.execution``) is declared and raises where its
inputs are not in the library; it is not offered to the model. The old common tools ``process.search``,
``process.entry``, ``process.sources``, ``process.tools``, ``knowledge.*``, ``episode.history``, ``episode.credit``,
``episode.annotation_score``, ``episode.monitoring_information``, ``episode.estimate_wait`` and ``shared.*`` were
callbacks of the old runner and are not in this episode's old files; ``episode.history`` and ``episode.credit``
are the context's ``own_outcomes`` and ``action_yields``.

Commissions. The model is the router: for a child it answers with the slot and the controlled fields of that
slot's commission (``commission_fields``: references of records this episode holds, a bound API resource, the
position of one of its own ``process_revise`` units, the handoff row of one of its outstanding jobs, the return
fields); it writes no assignment, objective or message. ``msg_to_child`` builds the child's assignment, in the
child's own form, from those choices and the summary. A slot is offered while this episode holds what its
commission is chosen from. The service ``job_access`` is read for the bound API resources a launch may name
(``launch_resources``). The two resource children are declared and not offered: their forms take open records
only a model could write (``BRANCH_FIX_BLOCKERS_head_a101.md``).

Settings (the old construction values): ``process_library_directory`` (the frozen process library),
``tool_library_directory`` (the frozen scientific tool library), ``tool_registry`` (the keyword settings of the
library's ``ToolRegistry``), ``yield_bindings`` (``yield_estimator.py``), and optionally
``knowledge_library_directory`` and ``launch_instruction_directory``."""
from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.configuration.sequence_homology_evidence.process_options import (
    SequenceHomologyEvidenceLibrary, evidence_axis_instruction_view)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.sequence_homology_evidence.evidence_axis_instructions import (
    VERSION as INSTRUCTION_VERSION, instruction_view)
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.evidence_axis_contracts import (
    VERSION as EVIDENCE_AXIS_VERSION)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.sequence_homology_evidence.literature_investigation_prompt import (
    INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.sequence_homology_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.construction_records import (
    CHILD_SELECTION_VERSION, REVISION_ORIGIN_VERSION, SELECTION_VERSION, scientific_digest, selection_fields,
    validate_child_selection, validate_revision_origin, validate_selection)
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import (
    identity, obj, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_homology_evidence.tools import (
    ToolRegistry)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_catalog import ScientificToolLibrary
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge)
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

from .goal import GOAL

# The old incoming-message routes (``incoming_message_owners``) are the slots; the two ``launch`` and the two
# ``results`` children of the old roles are told apart by their own slot.
HEAD = 'sequence_homology_evidence'
CHILD_SLOTS = {
    'execution_job_submission': HEAD + '/execution_job_submission',
    'execution_progress_assessment': HEAD + '/execution_progress_assessment',
    'execution_result_acquisition': HEAD + '/execution_result_acquisition',
    'literature': HEAD + '/literature',
    'resource_result_acquisition': HEAD + '/resource_result_acquisition',
    'resource_work_submission': HEAD + '/resource_work_submission',
    HEAD: HEAD,
}
# The monitor slot, and what a commission of it may ask the monitor to observe of a job (the monitor's own
# ``requested_fields`` options).
MONITOR = 'execution_progress_assessment'
MONITOR_FIELDS = ('execution_status', 'result_available', 'measurements', 'log_windows')
LAUNCH = 'execution_job_submission'
RESULTS = 'execution_result_acquisition'
LITERATURE = 'literature'
# The children whose forms take open records only a model could write (``job_request``,
# ``requested_data_selector``, an ``execution_handoff_v1`` record): no controlled commission exists for them, so
# they are never offered.
WITHOUT_COMMISSION = ('resource_result_acquisition', 'resource_work_submission')
# The API service whose jobs this episode launches (the BLAST database grader request) and acquires.
BLAST_SERVICE = 'ncbi_blast'
SERVICES = ('job_access',)

# The old common tool names and the tools this episode owns (``process.revise``, ``process.execution``).
COMMON_TOOLS = ('process.search', 'process.entry', 'process.sources', 'process.tools', 'knowledge.search',
                'knowledge.entry', 'knowledge.read', 'episode.history', 'episode.credit',
                'episode.annotation_score', 'episode.monitoring_information', 'episode.estimate_wait',
                'shared.request_information', 'shared.publish_information', 'shared.resolve_information_need',
                'shared.read_information', 'shared.list_information')
# The old ``scientific_operations``: these two tools were given the records this episode received.
RECEIVED_RECORD_READERS = ('result.blast.hsp', 'source.locate')
TEXT = {'type': 'string', 'minLength': 1}
OPEN = {'anyOf': [{'type': 'object'}]}   # an object the host validates; the provider carries it as JSON text
_SELECTOR = obj({'name': TEXT, 'resources': {'enum': ['api', 'local', 'hpc']}})
_THOUGHT_REF = obj({'version': {'const': 'sequence_homology_evidence_option_ref_v1'},
                    'library_id': {'type': 'string'}, 'slot': {'const': 'thought_pattern'},
                    'option_id': {'type': 'string', 'pattern': '^P[0-9]+$'}, 'entry_sha256': {'type': 'string'}})
REVISION_ARGUMENTS = obj({'thought_pattern': _THOUGHT_REF,
                          'child_tool_info': {'type': 'array', 'items': _SELECTOR, 'uniqueItems': True}})
THOUGHT_FIELDS = ('id', 'name', 'description', 'use_when', 'live_alternatives', 'decision_guidance',
                  'outcome_contingencies', 'boundary')
# The closed form ``Store.validate_scope`` admits (the old child scope of ``episode_child``).
_REF = {'type': 'string', 'minLength': 1}
SCOPE_SCHEMA = obj({
    'subject_refs': {'type': 'array', 'minItems': 1, 'items': _REF},
    'segments': {'type': 'array', 'minItems': 1,
                 'items': obj({'target_ref': _REF, 'start': {'type': 'integer', 'minimum': 0},
                               'end': {'type': 'integer', 'minimum': 0}, 'unit': _REF, 'member_ref': _REF},
                              required=['target_ref', 'start', 'end', 'unit'])},
    'read_selection_refs': {'type': 'array', 'minItems': 1, 'items': _REF},
}, required=['subject_refs'])
# References of records this episode holds, chosen by the model for a commission (``action`` rejects an answer that
# names a record it does not hold); and the name of a database of the BLAST service, as the service spells it.
REFERENCES = {'type': 'array', 'uniqueItems': True, 'items': _REF}
DATABASE_NAME = {'type': 'string', 'pattern': '^[A-Za-z0-9_./-]+$'}
# What this episode asks of the published evidence assessment: one value of that child's own fixed vocabulary
# (controlled messaging: the child's model is never shown text this episode's model wrote).
LITERATURE_OBJECTIVE = {
    'enum': ['evidence_in_supplied_sources', 'evidence_about_aligned_homolog', 'evidence_about_target_sequence'],
    'description': 'Where you expect the published evidence. evidence_in_supplied_sources: in the sources you pass '
                   'in source_refs. evidence_about_aligned_homolog: no source is passed for it; question_context_refs '
                   'names a homolog the target was aligned with (an alignment observation or its reference) and '
                   'published sources about that homolog have to be found. evidence_about_target_sequence: no '
                   'characterized homolog is known; published sources that characterize the target sequence itself '
                   'or a protein of its family have to be found.'}

# The selectable return fields each child declares (read from the child's own ``RETURN_FORM``); credit and finding
# are always returned. The recursive child is this episode's own kind.
SELECTABLE = {
    HEAD: ['committed_record_refs', 'execution_handoff_refs'],
    'execution_job_submission': """
        execution_handoff_refs execution_completed execution_result_refs execution_result_origin
        execution_blast_hsps execution_blast_pairwise_result_refs
    """.split(),
    'execution_progress_assessment': """
        job_returncode job_duration_seconds job_elapsed_seconds stdout_bytes stderr_bytes
        log_window_refs event_receipt_refs
    """.split(),
    'execution_result_acquisition': """
        execution_file_source_refs execution_handoff_refs execution_job_record_refs
        execution_result_refs execution_completed execution_blast_graded_refs
        execution_phmmer_graded_refs
    """.split(),
    'literature': """

    """.split(),
    'resource_result_acquisition': """
        execution_handoff execution_handoffs adapter_facts interpretation
    """.split(),
    'resource_work_submission': """
        execution_handoff execution_handoffs adapter_facts execution_handoff_refs
    """.split(),
}

# The two bodies the old ``ScientificGoal.instructions`` appended after the goal text, by the entry version of the
# selected evidence axis (instruction text, unchanged).
INSTRUCTION_ENTRY_BODY = "Determine what the supplied target does within the parent's assigned question, scope and constraints. Start with the supplied sequence, selected file contents or snippets, preserving their boundaries, completeness and known context. No initial candidate annotation or publicly searchable name is required. Possible functions can emerge from the evidence and be compared or revised. Apply the complete selected investigation instructions and thought-pattern guidance on every decision. Use actual outcomes and received child results to choose and revise your approach. Selected instructions describe how to investigate; they are not evidence about this target. Preserve the measured subject, conditions, controls, native measurements, uncertainty and limits of inference when interpreting evidence. Missing information remains unknown.\n\nChoose an available tool action, commit a scientific interpretation through the reasoning action, or commission one of the offered children (child_options) by choosing the controlled fields of its commission; code builds the child's assignment from your choices. Use only the selected actual tools and their supplied resource instructions; choose callable operands through the declared response contract. Preserve the parent's exact requested result meanings and allowed values. Recorded facts come from actual records. Keep inherited information distinct from new findings and completed work distinct from attempts. Return valid partial findings and specific failures through the requested form.\n\nKeep the assigned evidence axis, thought pattern and selected tools for this episode. process.revise prepares a different thought pattern and/or tool selection for a new child; it does not change this episode or start that child. To commission that alternative, select the child sequence_homology_evidence and name the process.revise unit by its position in own_outcomes (revision_position); code copies its selection and revision origin into the child's assignment. Children own their iterative choices. The configured controller owns continuation. Waiting and unchanged observations do not manufacture progress."
EVIDENCE_AXIS_BODY = "Investigate the parent's assigned scientific problem iteratively in the shared Episode loop. The selected scientific support proposition and operands define the support problem; the thought pattern supplies alternatives and outcome-sensitive guidance; the selected real tools supply their exact callable contracts. Choose your own actions using actual outcomes and received child forms. The selection is no prescribed sequence or automatic compatibility verdict. Library sources are instruction provenance, not scientific evidence about this target. Inspect actual source subjects, conditions and target applicability before interpreting evidence. annotation_support_routes describes the actual separately bound annotation policy's kind dispatch. An unmapped kind has no base-axis mapping in that known policy. Unavailable metadata means this reader cannot declare the bound policy; it is no verdict on evidence or the actual score. Metadata itself earns no credit and never replaces or filters the actual projectors, annotation formula or continuation rule. Keep the parent's objective, scope, constraints and exact typed form; support metadata never adds form fields or scoring axes. Use common reasoning to commit scientific interpretations. Keep the originally assigned scientific support, thought pattern and selected tool set throughout this episode. Explicit process.revise prepares a selection for a new child; a separately selected episode_child action commissions that child. Preparation changes no current process and starts no child. Name the process.revise unit by its position in own_outcomes (revision_position) in that commission; code copies its selection and revision origin into the child's assignment, which identifies it as an alternative approach. Only retrieved actual tools are available; their descriptions do not grant execution. The configured controller owns continuation."

HISTORY_START = 'On a fresh provider conversation,'
HISTORY_END = 'Do not execute native provider tools.'
HISTORY_GUIDANCE = ('Your own earlier outcomes are shown to you as own_outcomes, one row per completed unit, with '
                    'the records each produced; a failed or invalid outcome is shown with its feedback. Your '
                    'children\'s reports are in child_reports. Reading them creates no completed action or '
                    'observation and does not execute or credit the historical work again.\n')
DESCRIPTIONS = {
    'reason': REASONING_COMMIT_REQUIREMENT,
    'process_revise': ('Prepare a different thought pattern and/or selected actual tools for a new child '
                       'investigating the same evidence axis. Changes no current process, starts no child and '
                       'records no biological observation. Select the actual tool/resource choices of the tool '
                       'library for the desired investigation. To commission the alternative afterwards, select '
                       'the child sequence_homology_evidence and name this unit by its position in own_outcomes '
                       '(revision_position); code copies its selection and revision origin into the child\'s '
                       'assignment.'),
}
# What the model is told of each child it may commission: what the child does, the controlled fields of its
# commission (the model chooses values; code builds the child's assignment) and what comes back.
CHILD_DESCRIPTIONS = {
    'execution_job_submission': 'Launch one NCBI BLAST search of a subject of your scope on a bound API resource. '
                                'resource_id: one of launch_resources. query_subject_ref: the subject of your '
                                'scope to search with. database (optional): the name of one database of the '
                                'service, as the service spells it; leave it out to let the launch choose. The '
                                'search program is chosen by the launch. Returns the handoff row of the '
                                'submitted job (a job of outstanding_jobs afterwards); the handoff is '
                                'operational progress, not homology evidence.',
    'execution_progress_assessment': 'Check one outstanding job this episode holds (handoff_ref: one of '
                                     'outstanding_jobs), in one monitor visit. Returns its credit, the state of '
                                     'the job and whether its results are available, with its check records.',
    'execution_result_acquisition': 'Acquire and grade the BLAST return of one outstanding job this episode '
                                    'launched (handoff_ref: its handoff row). Code builds the request from the '
                                    'launch you made. Returns the graded BLAST sheet records your credit reads.',
    'literature': 'Assess the published evidence that bears on the assigned question. '
                                     'objective: where you expect that evidence, one value of the child\'s fixed '
                                     'vocabulary (evidence_in_supplied_sources, evidence_about_aligned_homolog, '
                                     'evidence_about_target_sequence). '
                                     'question_context_refs: the records you hold (visible_record_refs) that give '
                                     'the question its context, at least one. For '
                                     'evidence_about_aligned_homolog name the alignment observation or the '
                                     'homolog\'s subject there: code then puts the subjects those records name '
                                     'into the child\'s scope beside yours, so the child can read the homolog '
                                     '(a subject outside a scope is not readable in it). source_refs (offered while you '
                                     'hold a source record): the sources of held_source_refs the assessment '
                                     'starts from; it may be empty. Returns its credit and the counts of its '
                                     'report with the sources it chose.',
    HEAD: 'Commission a recursive sequence-homology investigation of your scope or of a scope within it. '
          'evidence_refs: the records you hold (visible_record_refs) the child starts from; it may be empty. '
          'revision_position (offered after a completed process.revise): the position in own_outcomes of the '
          'process.revise unit whose thought pattern and tools the child takes; without it the child takes your '
          'own selection. The proposed annotation, constraints and context are inherited. Returns its credit, '
          'its finding and the records it committed.',
}


def axis_entry(library, selection):
    """The old ``configuration._evidence_axis_view`` reading: the entry of the selected axis and its view."""
    entry = library.resolve(selection[selection_fields(selection)[0]])
    if entry.get('entry_version') == INSTRUCTION_VERSION:
        return entry, instruction_view(entry)
    if entry.get('entry_version') == EVIDENCE_AXIS_VERSION:
        return entry, evidence_axis_instruction_view(entry)
    raise ContractError('a101_evidence_axis_entry_invalid')


def replaces_default_instructions(library):
    """The old ``ScientificConfiguration.replaces_default_instructions``: every evidence axis of the library is a
    published instruction entry."""
    axes = [header['option_ref'] for header in library.headers() if header['option_ref']['slot'] == 'evidence_axis']
    return bool(axes) and all(library.resolve(ref).get('entry_version') == INSTRUCTION_VERSION for ref in axes)


def instructions(library, selection, *, knowledge, launch):
    """The old ``task_instructions.instructions``: the investigation text (replaced by the goal text when every
    axis is a published instruction entry), the reasoning-commit requirement, the tool-knowledge and the
    launch-instruction texts when those libraries are offered. The pending-delivery, wait, native-event and
    decision-exchange paragraphs describe actions that no longer exist and are not carried."""
    entry, _ = axis_entry(library, selection)
    body = INSTRUCTION_ENTRY_BODY if entry.get('entry_version') == INSTRUCTION_VERSION else EVIDENCE_AXIS_BODY
    specialized = GOAL + '\n\n' + body
    if replaces_default_instructions(library):
        text = specialized
    else:
        text = replace_span(INSTRUCTIONS, HISTORY_START, HISTORY_END, HISTORY_GUIDANCE) + '\n' + specialized
    text += '\n' + REASONING_COMMIT_REQUIREMENT
    if knowledge:
        text += KNOWLEDGE_INSTRUCTIONS
    if launch:
        text += LAUNCH_INSTRUCTIONS
    return text


def selected_tools(settings, selection):
    """The old ``tool_selection.catalog``: the direct-route tools of the selection, resolved from the tool library
    (a selected tool may not reuse a common tool name), without ``instructions`` and ``invocation_route``."""
    tools = ScientificToolLibrary(settings['tool_library_directory'])
    resolved = tools.resolve_invocations(selection['child_tool_info'])
    if any(row['name'] in {*COMMON_TOOLS, 'process.revise'} for row in resolved):
        raise ContractError('scientific_primitive_uses_common_tool_name')
    direct = [row for row in resolved if row.get('invocation_route', {'kind': 'direct'})['kind'] == 'direct']
    return [{key: value for key, value in row.items() if key not in ('instructions', 'invocation_route')}
            for row in direct]


def launch_resources(ctx):
    """The resources a launch may name: the API resources bound to the job service whose service is the BLAST
    service (read through the service's read handle, so the read is recorded with the decision)."""
    access = ctx.services['job_access']
    return [resource['resource_id'] for resource in access.read('resources')
            if resource['kind'] == 'api' and access.read('describe', resource['resource_id'])['service'] == BLAST_SERVICE]


def scope_schema(summary):
    """A scope within this episode's scope (the closed form ``Store.validate_scope`` admits): some of its subjects,
    optionally segments and read selections."""
    return obj({**SCOPE_SCHEMA['properties'],
                'subject_refs': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                                 'items': {'enum': list(summary['scope']['subject_refs'])}}},
               required=['subject_refs'])


def acquirable_jobs(summary):
    """The outstanding BLAST jobs this episode launched itself: a results commission is built from the launch."""
    launched = {ref for launch in summary['launches'] for ref in launch['handoff_refs']}
    return [job['handoff_ref'] for job in summary['outstanding_jobs']
            if job['blast_status_target'] and job['handoff_ref'] in launched]


def commission_fields(slot, summary, resources):
    """What the model supplies to commission ``slot``, as ``(properties, required)``: controlled values only
    (references of records this episode holds, a bound resource, a handoff row of an outstanding job, the position
    of one of its own ``process_revise`` units, a database name, values of a fixed vocabulary). ``None`` while this
    episode holds nothing the commission could be chosen from, and for the children that have no controlled
    commission: the slot is then not offered. ``msg_to_child`` builds the child's assignment from these fields and
    the summary; the model writes no assignment, objective or message."""
    if slot == MONITOR and summary['outstanding_jobs']:
        return ({'handoff_ref': {'enum': [job['handoff_ref'] for job in summary['outstanding_jobs']]},
                 'requested_fields': {'type': 'array', 'uniqueItems': True, 'minItems': 1,
                                      'items': {'enum': list(MONITOR_FIELDS)}}},
                ['handoff_ref', 'requested_fields'])
    if slot == LAUNCH and resources:
        return ({'resource_id': {'enum': list(resources)},
                 'query_subject_ref': {'enum': list(summary['scope']['subject_refs'])},
                 'database': DATABASE_NAME}, ['resource_id', 'query_subject_ref'])
    if slot == RESULTS and acquirable_jobs(summary):
        return {'handoff_ref': {'enum': acquirable_jobs(summary)}}, ['handoff_ref']
    if slot == LITERATURE:
        properties = {'objective': LITERATURE_OBJECTIVE, 'question_context_refs': {**REFERENCES, 'minItems': 1},
                      'scope': scope_schema(summary)}
        if summary['held_source_refs']:
            properties['source_refs'] = REFERENCES
        return properties, ['objective', 'question_context_refs']
    if slot == HEAD:
        properties = {'evidence_refs': REFERENCES, 'scope': scope_schema(summary)}
        if summary['revisions']:
            properties['revision_position'] = {'enum': [item['position'] for item in summary['revisions']]}
        return properties, ['evidence_refs']
    return None


def offered_children(summary, resources):
    """The children this decision offers: those whose commission this episode can state now. The monitor is
    offered while it holds an outstanding job, the results acquisition while it holds an outstanding BLAST job it
    launched, the launch while an API resource of the BLAST service is bound; the published evidence assessment
    and the recursive investigation always."""
    return [slot for slot in CHILD_SLOTS if commission_fields(slot, summary, resources) is not None]


def child_option(slot, summary, resources):
    """One child the model may commission: the slot, the controlled fields of its commission
    (``commission_fields``) and ``selection``, the optional return fields the commission may select from what the
    child declares; a child that declares none has no ``selection`` (an array schema needs its ``items``, and an
    ``enum`` of no names admits nothing)."""
    properties, required = commission_fields(slot, summary, resources)
    properties = {'kind': {'const': 'episode_child'}, 'slot': {'const': slot}, **properties}
    if SELECTABLE[slot]:
        properties['selection'] = {'type': 'array', 'uniqueItems': True, 'items': {'enum': SELECTABLE[slot]}}
    return obj(properties, required=['kind', 'slot', *required])


def unheld_references(arguments, summary):
    """The references of a commission the model wrote that name no record this episode holds (a source reference:
    no source it holds)."""
    held = set(summary['held_record_refs'])
    named = [*arguments.get('question_context_refs', []), *arguments.get('evidence_refs', []),
             *arguments.get('scope', {}).get('read_selection_refs', [])]
    return [*(ref for ref in named if ref not in held),
            *(ref for ref in arguments.get('source_refs', []) if ref not in summary['held_source_refs'])]


def selection_schema(summary, tools, resources):
    """What the model answers with: one reasoning commit, one selected tool, a process revision, or one child.
    The reasoning commit is the tool ``reason``, as the model is shown it: the arguments of a tool whose schema is
    composed travel as JSON text, and the Store's reasoning schema sent as output schema itself has more enum
    values than the model endpoint takes in one schema."""
    options = [obj({'kind': {'const': 'tool'}, 'tool': {'const': 'reason'},
                    'arguments': obj({'commit': summary['reasoning_schema']})}),
               obj({'kind': {'const': 'tool'}, 'tool': {'const': 'process.revise'}, 'arguments': REVISION_ARGUMENTS})]
    options.extend(obj({'kind': {'const': 'tool'}, 'tool': {'const': row['name']},
                        'arguments': row.get('input_schema', OPEN)}) for row in tools)
    options.extend(child_option(slot, summary, resources) for slot in offered_children(summary, resources))
    return obj({'selection': {'anyOf': options}})


def decide(summary, feedback, ctx):
    """Ask the model for the next unit, shown the commission, the selected process library entries, the working
    state of the scope, its own outcomes and its children's reports, the tools and children it may use, the
    measured time and the yield table (the old decision state and inputs, over this episode's summary)."""
    settings = ctx.settings
    library = SequenceHomologyEvidenceLibrary(settings['process_library_directory'])
    selection = summary['selection']
    _, axis_view = axis_entry(library, selection)
    thought = library.resolve(selection[selection_fields(selection)[1]])
    tools = selected_tools(settings, selection)
    resources = launch_resources(ctx)
    offered = offered_children(summary, resources)
    knowledge_directory = settings.get('knowledge_library_directory')
    launch_directory = settings.get('launch_instruction_directory')
    launch_library = None if launch_directory is None else LaunchInstructions(launch_directory)
    knowledge = None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()
    context = {
        'goal': GOAL, 'scope': summary['scope'],
        'sequence_homology_evidence': {
            'selection': selection, 'initial_selection_sha256': summary['initial_selection_sha256'],
            'evidence_axis': axis_view,
            'thought_pattern': {name: thought[name] for name in THOUGHT_FIELDS if name in thought},
            'child_tool_info': selection['child_tool_info'],
            'assignment': {'proposed_annotation_ref': summary['proposed_annotation_ref'],
                           'evidence_refs': summary['evidence_refs'], 'constraints': summary['constraints'],
                           'context': summary['context']},
            'permitted_children': offered},
        'working_state': summary['working_state'], 'visible_record_refs': summary['held_record_refs'],
        'held_source_refs': summary['held_source_refs'],
        'credit_binding': summary['credit_binding'], 'own_outcomes': summary['units'],
        'last_local_outcome': summary['last_local_outcome'], 'child_reports': summary['child_reports'],
        'handoff_refs': summary['handoff_refs'],
        'outstanding_jobs': [{name: job[name] for name in ('job', 'kind', 'submitted_at', 'handoff_ref',
                                                           'latest_check')}
                             for job in summary['outstanding_jobs']],
        'launch_resources': resources,
        'tools': [{'name': 'reason', 'description': DESCRIPTIONS['reason']},
                  {'name': 'process.revise', 'description': DESCRIPTIONS['process_revise'],
                   'input_schema': REVISION_ARGUMENTS}, *tools],
        'child_options': [{'slot': slot, 'binding_path': CHILD_SLOTS[slot], 'description': CHILD_DESCRIPTIONS[slot],
                           'selectable_return_fields': SELECTABLE[slot]} for slot in offered],
        'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['action_yields'],
        'revision_origin': summary.get('revision_origin'), 'tool_knowledge': knowledge,
        'launch_instruction_library': None if launch_library is None else launch_library.context()},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(library, selection, knowledge=knowledge, launch=launch_library),
                        context, generation_schema(selection_schema(summary, tools, resources)))


def empty_commit(commit):
    """The old ``reasoning_has_task_content`` test: every section of the commit is empty."""
    return all(rows == [] for rows in commit.values())


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one commission, or reject it (no unit): an answer that does not
    fit the schema, a reasoning commit with every section empty (rejected before acquisition), or a commission
    that names a record this episode does not hold (an invalid answer of the model, never a check of what
    ``msg_to_child`` builds)."""
    tools = selected_tools(ctx.settings, summary['selection'])
    schema = selection_schema(summary, tools, launch_resources(ctx))
    try:
        if not isinstance(response, dict) or set(response) != {'selection'}:
            raise ValueError('a101_decision_response_must_be_exactly_selection')
        selection = decode_response(response, schema)['selection']
        Draft202012Validator(schema['properties']['selection']).validate(selection)
        if selection['kind'] == 'tool' and selection['tool'] == 'reason' and empty_commit(
                selection['arguments']['commit']):
            raise ValueError('empty_reasoning_commit')
        if selection['kind'] == 'episode_child' and unheld_references(selection, summary):
            raise ValueError('commission_names_records_not_held:' + ','.join(unheld_references(selection, summary)))
    except (ValueError, KeyError, TypeError, ContractError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    if selection['kind'] == 'episode_child':
        arguments = {key: value for key, value in selection.items() if key not in ('kind', 'slot')}
        return ChildCall(selection['slot'], arguments)
    scope = summary['scope']
    if selection['tool'] == 'reason':
        return ToolCall('reason', {'commit': selection['arguments']['commit'], 'scope': scope})
    if selection['tool'] == 'process.revise':
        return ToolCall('process_revise', {'arguments': selection['arguments'], 'selection': summary['selection']})
    return ToolCall('execute_selected_tool', {'tool': selection['tool'], 'arguments': selection['arguments'],
                                              'scope': scope,
                                              'permitted_record_refs': (summary['held_record_refs']
                                                                        if selection['tool'] in RECEIVED_RECORD_READERS
                                                                        else None)})


def reason(arguments, ctx):
    """Commit the model's typed reasoning (the old ``Store.commit_reasoning`` path of ``execute``; the owner of
    interpretation accounts is named by the system). Every reference the payload names is held, else
    ``CustodyError``."""
    return ctx.store.commit_reasoning(arguments['commit'], arguments['scope'], ctx.operation_key)


async def execute_selected_tool(arguments, ctx):
    """The old ``scientific_operations.execute`` dispatch of a selected tool to the services' tool executor, over
    the library's ``ToolRegistry`` handed ``ctx.store``. An argument or reference error is an ``invalid`` outcome
    and a failed operation a ``failed`` one; both are outcomes that enter the iterator, as before. The old
    ``authenticate_source_byte_operands`` of the material and source tools was a callback of the old runner and is
    not in this episode's files."""
    registry = ToolRegistry(ctx.store, **ctx.settings['tool_registry'])
    permitted = arguments['permitted_record_refs']
    try:
        return await registry.execute_async(arguments['tool'], arguments['arguments'], scope=arguments['scope'],
                                            operation_key=ctx.operation_key,
                                            permitted_record_refs=None if permitted is None else tuple(permitted))
    except CustodyError:
        raise
    except (ContractError, ValueError, ValidationError) as error:
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': str(error),
                             **({'detail': error.detail} if getattr(error, 'detail', None) else {})}}
    except Exception as error:   # the old record_execution_failure: a failed selected operation is an outcome
        return failure_outcome(ctx.store, error, category='episode_execution', cause_code='selected_operation_failed')


def process_revise(arguments, ctx):
    """The old ``process.revise`` (``scientific_operations`` and ``alternate_process_selection``): the same evidence
    axis with a different thought pattern and/or tools, as a detached child selection and its revision origin. It
    changes no current process and starts no child."""
    try:
        initial = validate_selection(arguments['selection'])
        validate_schema(arguments['arguments'], REVISION_ARGUMENTS)
        tools = ScientificToolLibrary(ctx.settings['tool_library_directory'])
        proposed = validate_selection({
            'version': SELECTION_VERSION, 'evidence_axis': initial[selection_fields(initial)[0]],
            'thought_pattern': arguments['arguments']['thought_pattern'],
            'child_tool_info': tools.resolve_tool_info(arguments['arguments']['child_tool_info'])})
        child_selection = validate_child_selection({
            'version': CHILD_SELECTION_VERSION, 'parent_selection_sha256': scientific_digest(initial),
            'selection': proposed})
        operation = identity('operation', {'key': ctx.operation_key, 'name': 'process.revise',
                                           'arguments': arguments['arguments']})
        origin = validate_revision_origin({
            'version': REVISION_ORIGIN_VERSION,
            'parent_invocation_ref': identity('scientific_invocation',
                                              {'run_id': ctx.run_id, 'episode_id': ctx.episode_id}),
            'preparation_operation_ref': operation})
    except (ContractError, ValueError, ValidationError) as error:
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': str(error)}}
    return {'status': 'completed', 'operation_ref': operation, 'record_refs': [], 'changed_record_refs': [],
            'result': child_selection, 'revision_origin': origin, 'feedback': None}


def process_execution(arguments, ctx):
    """The old ``process.execution`` (``execution_planning.read``): operational planning only, credit 0. Its inputs
    (the execution memory of ``memory_for(workflow)``, ``workflow.resource_context`` and the HPC commissions of
    ``workflow.episode_bindings``) were the old runner's and have no place in the library or the system today. It
    is not offered to the model (``decide``)."""
    raise NotImplementedError('unplaced:execution_planning.memory_for:resource_context:hpc_commissions')


TOOLS = {'reason': reason, 'execute_selected_tool': execute_selected_tool, 'process_revise': process_revise,
         'process_execution': process_execution}
