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
    'published_evidence_assessment': HEAD + '/published_evidence_assessment',
    'resource_result_acquisition': HEAD + '/resource_result_acquisition',
    'resource_work_submission': HEAD + '/resource_work_submission',
    HEAD: HEAD,
}
SERVICES = ()

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

# The selectable return fields each child declares (read from the child's own ``RETURN_FORM``); credit and finding
# are always returned. The recursive child is this episode's own kind.
SELECTABLE = {
    HEAD: ['committed_record_refs', 'execution_handoff_refs'],
    'execution_job_submission': """
        execution_handoff_refs execution_completed execution_result_refs execution_result_origin
        execution_blast_hsps execution_blast_pairwise_result_refs
    """.split(),
    'execution_progress_assessment': """
        monitoring_progress_refs monitoring_target_handle monitoring_execution_state
        monitoring_result_available monitoring_observed_at_unix_seconds monitoring_committed_record_refs
        monitoring_dependency_handles monitoring_progress_snapshots
    """.split(),
    'execution_result_acquisition': """
        execution_file_source_refs execution_file_capture_outcomes execution_handoff_refs
        execution_result_refs execution_completed execution_result_origin execution_blast_graded_refs
        execution_phmmer_graded_refs
    """.split(),
    'published_evidence_assessment': """

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
INSTRUCTION_ENTRY_BODY = "Determine what the supplied target does within the parent's assigned question, scope and constraints. Start with the supplied sequence, selected file contents or snippets, preserving their boundaries, completeness and known context. No initial candidate annotation or publicly searchable name is required. Possible functions can emerge from the evidence and be compared or revised. Apply the complete selected investigation instructions and thought-pattern guidance on every decision. Use actual outcomes and received child results to choose and revise your approach. Selected instructions describe how to investigate; they are not evidence about this target. Preserve the measured subject, conditions, controls, native measurements, uncertainty and limits of inference when interpreting evidence. Missing information remains unknown.\n\nChoose an available tool action, commit a scientific interpretation through the reasoning action, commission a scoped child with its own typed return form, or wait for selected pending work when that informs the investigation. Use only the selected actual tools and their supplied resource instructions; choose callable operands through the declared response contract. Preserve the parent's exact requested result meanings and allowed values. Recorded facts come from actual records. Keep inherited information distinct from new findings and completed work distinct from attempts. Return valid partial findings and specific failures through the requested form.\n\nKeep the assigned evidence axis, thought pattern and selected tools for this episode. process.revise prepares a different thought pattern and/or tool selection for a new child; it does not change this episode or start that child. To commission that alternative, copy its selection and revision_origin into a separately selected child assignment with the child's job, scope, constraints and typed return. Children own their iterative choices. The configured controller owns continuation. Waiting and unchanged observations do not manufacture progress."
EVIDENCE_AXIS_BODY = "Investigate the parent's assigned scientific problem iteratively in the shared Episode loop. The selected scientific support proposition and operands define the support problem; the thought pattern supplies alternatives and outcome-sensitive guidance; the selected real tools supply their exact callable contracts. Choose your own actions using actual outcomes and received child forms. The selection is no prescribed sequence or automatic compatibility verdict. Library sources are instruction provenance, not scientific evidence about this target. Inspect actual source subjects, conditions and target applicability before interpreting evidence. annotation_support_routes describes the actual separately bound annotation policy's kind dispatch. An unmapped kind has no base-axis mapping in that known policy. Unavailable metadata means this reader cannot declare the bound policy; it is no verdict on evidence or the actual score. Metadata itself earns no credit and never replaces or filters the actual projectors, annotation formula or continuation rule. Keep the parent's objective, scope, constraints and exact typed form; support metadata never adds form fields or scoring axes. Use common reasoning to commit scientific interpretations. Keep the originally assigned scientific support, thought pattern and selected tool set throughout this episode. Explicit process.revise prepares a selection for a new child; a separately selected episode_child action commissions that child with its own job, scope, constraints and typed return form. Preparation changes no current process and starts no child. Copy both result.selection and revision_origin into that child's assignment to identify it as an alternative approach. Request the recorded sequence_homology_evidence_results source in child forms when their process relationships and existing closed credit/yield are needed for steering. Only retrieved actual tools are available; their descriptions do not grant execution. The configured controller owns continuation."

HISTORY_START = 'On a fresh provider conversation,'
HISTORY_END = 'Do not execute native provider tools.'
HISTORY_GUIDANCE = ('Your own earlier outcomes are shown to you as own_outcomes, one row per completed unit, with '
                    'the records each produced; a failed or invalid outcome is shown with its feedback. Your '
                    'children\'s reports are in child_reports. Reading them creates no completed action or '
                    'observation and does not execute or credit the historical work again.\n')
DESCRIPTIONS = {
    'reason': REASONING_COMMIT_REQUIREMENT,
    'process_revise': ('Prepare a different thought pattern and/or selected actual tools for a new child '
                       'investigating the same evidence axis. Return its selection for a separately selected '
                       'episode_child commission with the child\'s job, scope, constraints and typed return form. '
                       'Copy result.selection and revision_origin into that assignment. Changes no current process, '
                       'starts no child and records no biological observation. Select the actual tool/resource '
                       'choices of the tool library for the desired investigation.'),
}
CHILD_DESCRIPTIONS = {
    'execution_job_submission': 'Launch a planned execution on an explicit resource; returns its handoff records.',
    'execution_progress_assessment': 'Check the progress of one execution handle; returns progress snapshots.',
    'execution_result_acquisition': 'Acquire the requested results of an original handoff.',
    'published_evidence_assessment': 'Assess the published evidence that bears on the assigned question.',
    'resource_result_acquisition': 'Acquire the requested results of a resource work handoff.',
    'resource_work_submission': 'Submit work on a declared resource; returns its handoff records.',
    HEAD: 'Commission a recursive sequence-homology investigation of a scope within this scope, with its own '
          'thought pattern and tools (copy process_revise\'s selection and revision_origin for an alternative).',
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


def selectable_schema(slot):
    """The optional return fields this commission may select from what the child declares."""
    names = SELECTABLE[slot]
    if not names:
        return {'type': 'array', 'maxItems': 0}
    return {'type': 'array', 'uniqueItems': True, 'items': {'enum': names}}


def selection_schema(summary, tools):
    """What the model answers with: one reasoning commit, one selected tool, a process revision, or one child."""
    options = [obj({'kind': {'const': 'reason'}, 'commit': summary['reasoning_schema']}),
               obj({'kind': {'const': 'tool'}, 'tool': {'const': 'process.revise'}, 'arguments': REVISION_ARGUMENTS})]
    options.extend(obj({'kind': {'const': 'tool'}, 'tool': {'const': row['name']},
                        'arguments': row.get('input_schema', OPEN)}) for row in tools)
    options.extend(obj({'kind': {'const': 'episode_child'}, 'slot': {'const': slot}, 'objective': TEXT,
                        'message': {'type': 'string'}, 'assignment': OPEN, 'selection': selectable_schema(slot),
                        'scope': SCOPE_SCHEMA}, required=['kind', 'slot', 'objective', 'message', 'assignment'])
                   for slot in CHILD_SLOTS)
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
            'permitted_children': summary['permitted_children']},
        'working_state': summary['working_state'], 'visible_record_refs': summary['held_record_refs'],
        'credit_binding': summary['credit_binding'], 'own_outcomes': summary['units'],
        'last_local_outcome': summary['last_local_outcome'], 'child_reports': summary['child_reports'],
        'handoff_refs': summary['handoff_refs'],
        'tools': [{'name': 'reason', 'description': DESCRIPTIONS['reason']},
                  {'name': 'process.revise', 'description': DESCRIPTIONS['process_revise'],
                   'input_schema': REVISION_ARGUMENTS}, *tools],
        'child_options': [{'slot': slot, 'binding_path': path, 'description': CHILD_DESCRIPTIONS[slot],
                           'selectable_return_fields': SELECTABLE[slot]}
                          for slot, path in CHILD_SLOTS.items()],
        'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['action_yields'],
        'revision_origin': summary.get('revision_origin'), 'tool_knowledge': knowledge,
        'launch_instruction_library': None if launch_library is None else launch_library.context()},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(library, selection, knowledge=knowledge, launch=launch_library),
                        context, generation_schema(selection_schema(summary, tools)))


def empty_commit(commit):
    """The old ``reasoning_has_task_content`` test: every section of the commit is empty."""
    return all(rows == [] for rows in commit.values())


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one commission, or reject it (no unit): an answer that does not
    fit the schema, or a reasoning commit with every section empty (rejected before acquisition)."""
    tools = selected_tools(ctx.settings, summary['selection'])
    schema = selection_schema(summary, tools)
    try:
        if not isinstance(response, dict) or set(response) != {'selection'}:
            raise ValueError('a101_decision_response_must_be_exactly_selection')
        selection = decode_response(response, schema)['selection']
        Draft202012Validator(schema['properties']['selection']).validate(selection)
        if selection['kind'] == 'reason' and empty_commit(selection['commit']):
            raise ValueError('empty_reasoning_commit')
    except (ValueError, KeyError, TypeError, ContractError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    if selection['kind'] == 'episode_child':
        arguments = {key: value for key, value in selection.items() if key not in ('kind', 'slot')}
        return ChildCall(selection['slot'], arguments)
    scope = summary['scope']
    if selection['kind'] == 'reason':
        return ToolCall('reason', {'commit': selection['commit'], 'scope': scope})
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
