"""The task of the A101 head: one model-selected unit per decision. The model investigates the assigned subject with
the selected tools of its commission (``execute_selected_tool``), commits scientific interpretations (``reason``) and
commissions its children. It never ends the Episode: only the yield controller does.

Tools. ``reason`` is the ``Store.commit_reasoning`` path. ``execute_selected_tool`` dispatches a tool the commission
selected to the library's ``ToolRegistry``, called with ``ctx.store`` (a tool name here has lowercase letters, digits
and underscores, so the selected name travels as an argument). ``pairwise_blast`` is this episode's own defined tool:
the model chooses the program, the query (a subject of the scope), the subject record to compare it with and a bound
local resource, all from fixed sets; code runs the comparison, fetches its report and grades it in the same unit
(``pairwise_blast_comparison``), and the graded sheet is what this episode's credit reads. It is offered while this
episode holds a second subject record and a local resource is bound.

Children. The head's child episodes in the A101 tree are ``blast_database_preparation``, ``database_blast`` and
``all_vs_all_blast`` (HMMER later). A child is declared in ``CHILD_SLOTS`` when its episode is built (the runner
refuses a declared slot with no episode behind it), together with its commission in ``COMMISSIONS``. The model is the
router: for a child it answers with the slot and the controlled fields of that slot's commission
(``commission_fields``); it writes no assignment, objective or message. ``msg_to_child`` builds the child's
assignment, in the child's own form, from those choices and the summary. A slot is offered while its commission can
be stated from what this episode holds. The service ``job_access`` is read for the bound resources a commission or a
tool may name (``local_resources``).

Settings: ``process_library_directory`` (the frozen process library), ``tool_library_directory`` (the frozen
scientific tool library), ``tool_registry`` (the keyword settings of the library's ``ToolRegistry``),
``blast_executable_directory`` (the directory that holds the BLAST programs) and ``yield_bindings``
(``yield_estimator.py``)."""
from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.configuration.sequence_homology_evidence.process_options import (
    SequenceHomologyEvidenceLibrary, evidence_axis_instruction_view)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.instructions.sequence_homology_evidence.evidence_axis_instructions import (
    VERSION as INSTRUCTION_VERSION, instruction_view)
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.evidence_axis_contracts import (
    VERSION as EVIDENCE_AXIS_VERSION)
from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.native_blast_contracts import (
    PROGRAMS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.sequence_homology_evidence.literature_investigation_prompt import (
    INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.sequence_homology_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.construction_records import (
    selection_fields)
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import obj
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_homology_evidence.tools import (
    ToolRegistry)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.pairwise_blast_comparison import (
    pairwise_blast_comparison)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_catalog import ScientificToolLibrary
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

from .goal import GOAL

HEAD = 'sequence_homology_evidence'
# The child episodes that are built, by slot. A child is added here with its entries in ``COMMISSIONS``,
# ``CHILD_DESCRIPTIONS`` and ``SELECTABLE`` and its builder in ``messages/msg_to_child.py``.
CHILD_SLOTS = {}
# What the model supplies to commission each slot: a function of (summary, resources) that returns
# ``(properties, required)`` of controlled values, or ``None`` while the commission cannot be stated.
COMMISSIONS = {}
SERVICES = ('job_access',)

# The common tool names a selected tool may not reuse.
COMMON_TOOLS = ('process.search', 'process.entry', 'process.sources', 'process.tools', 'knowledge.search',
                'knowledge.entry', 'knowledge.read', 'episode.history', 'episode.credit',
                'episode.annotation_score', 'episode.monitoring_information', 'episode.estimate_wait',
                'shared.request_information', 'shared.publish_information', 'shared.resolve_information_need',
                'shared.read_information', 'shared.list_information')
# The old ``scientific_operations``: these two tools were given the records this episode received.
RECEIVED_RECORD_READERS = ('result.blast.hsp', 'source.locate')
TEXT = {'type': 'string', 'minLength': 1}
OPEN = {'anyOf': [{'type': 'object'}]}   # an object the host validates; the provider carries it as JSON text
THOUGHT_FIELDS = ('id', 'name', 'description', 'use_when', 'live_alternatives', 'decision_guidance',
                  'outcome_contingencies', 'boundary')
# The optional return fields a commission may select from what the child declares (read from the child's own
# ``RETURN_FORM``); credit and finding are always returned. A child's entry is added with its commission.
SELECTABLE = {}

# The two bodies the old ``ScientificGoal.instructions`` appended after the goal text, by the entry version of the
# selected evidence axis (instruction text, unchanged).
INSTRUCTION_ENTRY_BODY = "Determine what the supplied target does within the parent's assigned question, scope and constraints. Start with the supplied sequence, selected file contents or snippets, preserving their boundaries, completeness and known context. No initial candidate annotation or publicly searchable name is required. Possible functions can emerge from the evidence and be compared or revised. Apply the complete selected investigation instructions and thought-pattern guidance on every decision. Use actual outcomes and received child results to choose and revise your approach. Selected instructions describe how to investigate; they are not evidence about this target. Preserve the measured subject, conditions, controls, native measurements, uncertainty and limits of inference when interpreting evidence. Missing information remains unknown.\n\nChoose an available tool action, commit a scientific interpretation through the reasoning action, or commission one of the offered children (child_options) by choosing the controlled fields of its commission; code builds the child's assignment from your choices. Use only the selected actual tools and their supplied resource instructions; choose callable operands through the declared response contract. Preserve the parent's exact requested result meanings and allowed values. Recorded facts come from actual records. Keep inherited information distinct from new findings and completed work distinct from attempts. Return valid partial findings and specific failures through the requested form.\n\nKeep the assigned evidence axis, thought pattern and selected tools for this episode. Children own their iterative choices. The configured controller owns continuation. Waiting and unchanged observations do not manufacture progress."
EVIDENCE_AXIS_BODY = "Investigate the parent's assigned scientific problem iteratively in the shared Episode loop. The selected scientific support proposition and operands define the support problem; the thought pattern supplies alternatives and outcome-sensitive guidance; the selected real tools supply their exact callable contracts. Choose your own actions using actual outcomes and received child forms. The selection is no prescribed sequence or automatic compatibility verdict. Library sources are instruction provenance, not scientific evidence about this target. Inspect actual source subjects, conditions and target applicability before interpreting evidence. annotation_support_routes describes the actual separately bound annotation policy's kind dispatch. An unmapped kind has no base-axis mapping in that known policy. Unavailable metadata means this reader cannot declare the bound policy; it is no verdict on evidence or the actual score. Metadata itself earns no credit and never replaces or filters the actual projectors, annotation formula or continuation rule. Keep the parent's objective, scope, constraints and exact typed form; support metadata never adds form fields or scoring axes. Use common reasoning to commit scientific interpretations. Keep the originally assigned scientific support, thought pattern and selected tool set throughout this episode. Only retrieved actual tools are available; their descriptions do not grant execution. The configured controller owns continuation."

HISTORY_START = 'On a fresh provider conversation,'
HISTORY_END = 'Do not execute native provider tools.'
HISTORY_GUIDANCE = ('Your own earlier outcomes are shown to you as own_outcomes, one row per completed unit, with '
                    'the records each produced; a failed or invalid outcome is shown with its feedback. Your '
                    'children\'s reports are in child_reports. Reading them creates no completed action or '
                    'observation and does not execute or credit the historical work again.\n')
PAIRWISE_TOOL = 'pairwise_blast'
DESCRIPTIONS = {
    'reason': REASONING_COMMIT_REQUIREMENT,
    PAIRWISE_TOOL: ('Compare one query sequence with one subject sequence by a pairwise BLAST on a bound local '
                    'resource. You choose four values from the offered sets: program (blastp for two proteins, '
                    'blastn for two nucleotide sequences, blastx for a nucleotide query against a protein subject, '
                    'tblastn for a protein query against a nucleotide subject, tblastx for two nucleotide sequences '
                    'compared in translation), query_ref (a subject of your scope), subject_ref (another subject '
                    'record you hold) and resource_id (one of local_resources). Code runs the search, fetches its '
                    'report and grades it in this one unit; you do not grade. The outcome shows the controlled '
                    'features of the saved pairwise sheet: counts and fractions of paired and identical residues, '
                    'the two lengths and the native E-value with the search-space context the report gives, and '
                    'observation_refs: one comparison observation per reported alignment, which you now hold. '
                    'The comparison itself is a measurement, not yet evidence about the proposed annotation: your '
                    'credit measures the graded correspondence of the observations that an assessment of yours '
                    'relates to the proposed annotation (a reasoning commit with an assessment of the proposed '
                    'annotation against the observation, its relation, applicability and extent). Repeating a '
                    'comparison you already hold adds no correspondence and earns nothing. A program that does '
                    'not take the two molecules is an invalid outcome.'),
}
# What the model is told of each child it may commission: what the child does, the controlled fields of its
# commission (the model chooses values; code builds the child's assignment) and what comes back. A child's entry is
# added with its commission.
CHILD_DESCRIPTIONS = {}


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


def instructions(library, selection):
    """The investigation text (replaced by the goal text when every axis is a published instruction entry) and the
    reasoning-commit requirement. The text lives in this episode's own files: no knowledge or launch instruction
    library is assembled into it."""
    entry, _ = axis_entry(library, selection)
    body = INSTRUCTION_ENTRY_BODY if entry.get('entry_version') == INSTRUCTION_VERSION else EVIDENCE_AXIS_BODY
    specialized = GOAL + '\n\n' + body
    if replaces_default_instructions(library):
        text = specialized
    else:
        text = replace_span(INSTRUCTIONS, HISTORY_START, HISTORY_END, HISTORY_GUIDANCE) + '\n' + specialized
    return text + '\n' + REASONING_COMMIT_REQUIREMENT


def selected_tools(settings, selection):
    """The old ``tool_selection.catalog``: the direct-route tools of the selection, resolved from the tool library
    (a selected tool may not reuse a common tool name), without ``instructions`` and ``invocation_route``."""
    tools = ScientificToolLibrary(settings['tool_library_directory'])
    resolved = tools.resolve_invocations(selection['child_tool_info'])
    if any(row['name'] in COMMON_TOOLS for row in resolved):
        raise ContractError('scientific_primitive_uses_common_tool_name')
    direct = [row for row in resolved if row.get('invocation_route', {'kind': 'direct'})['kind'] == 'direct']
    return [{key: value for key, value in row.items() if key not in ('instructions', 'invocation_route')}
            for row in direct]


def local_resources(ctx):
    """The local resources bound to the job service, which a commission or a tool may name (read through the
    service's read handle, so the read is recorded with the decision)."""
    access = ctx.services['job_access']
    return [resource['resource_id'] for resource in access.read('resources') if resource['kind'] == 'local']


def held_subjects(summary):
    """The subject records this episode holds: what a comparison's two sequences are chosen from."""
    return [ref for ref in summary['held_record_refs'] if ref.startswith('subject_')]


def pairwise_options(summary, resources):
    """The ``pairwise_blast`` choices this decision offers, one per query: the query is a held subject of the scope
    and the subject is any other held subject record; every value is from a fixed set. None while no local resource
    is bound or no second subject record is held."""
    held, options = held_subjects(summary), []
    for query in summary['scope']['subject_refs']:
        subjects = [ref for ref in held if ref != query]
        if query in held and subjects and resources:
            options.append(obj({'kind': {'const': 'tool'}, 'tool': {'const': PAIRWISE_TOOL},
                                'arguments': obj({'program': {'enum': list(PROGRAMS)}, 'query_ref': {'enum': [query]},
                                                  'subject_ref': {'enum': subjects},
                                                  'resource_id': {'enum': list(resources)}})}))
    return options


def commission_fields(slot, summary, resources):
    """What the model supplies to commission ``slot``, as ``(properties, required)``: controlled values only.
    ``None`` while this episode holds nothing the commission could be chosen from: the slot is then not offered.
    ``msg_to_child`` builds the child's assignment from these fields and the summary; the model writes no
    assignment, objective or message."""
    return COMMISSIONS[slot](summary, resources)


def offered_children(summary, resources):
    """The children this decision offers: those whose commission this episode can state now."""
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


def selection_schema(summary, tools, resources):
    """What the model answers with: one reasoning commit, one selected tool, one pairwise comparison, or one child.
    The reasoning commit is the tool ``reason``, as the model is shown it: the arguments of a tool whose schema is
    composed travel as JSON text, and the Store's reasoning schema sent as output schema itself has more enum
    values than the model endpoint takes in one schema."""
    options = [obj({'kind': {'const': 'tool'}, 'tool': {'const': 'reason'},
                    'arguments': obj({'commit': summary['reasoning_schema']})})]
    options.extend(obj({'kind': {'const': 'tool'}, 'tool': {'const': row['name']},
                        'arguments': row.get('input_schema', OPEN)}) for row in tools)
    options.extend(pairwise_options(summary, resources))
    options.extend(child_option(slot, summary, resources) for slot in offered_children(summary, resources))
    return obj({'selection': {'anyOf': options}})


def decide(summary, feedback, ctx):
    """Ask the model for the next unit, shown the commission, the selected process library entries, the working
    state of the scope, its own outcomes and its children's reports, the tools and children it may use, the
    measured time and the yield table."""
    settings = ctx.settings
    library = SequenceHomologyEvidenceLibrary(settings['process_library_directory'])
    selection = summary['selection']
    _, axis_view = axis_entry(library, selection)
    thought = library.resolve(selection[selection_fields(selection)[1]])
    tools = selected_tools(settings, selection)
    resources = local_resources(ctx)
    offered = offered_children(summary, resources)
    own = ([{'name': PAIRWISE_TOOL, 'description': DESCRIPTIONS[PAIRWISE_TOOL]}]
           if pairwise_options(summary, resources) else [])
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
        'handoff_refs': summary['handoff_refs'], 'local_resources': resources,
        'tools': [{'name': 'reason', 'description': DESCRIPTIONS['reason']}, *own, *tools],
        'child_options': [{'slot': slot, 'binding_path': CHILD_SLOTS[slot], 'description': CHILD_DESCRIPTIONS[slot],
                           'selectable_return_fields': SELECTABLE[slot]} for slot in offered],
        'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['action_yields'],
        'revision_origin': summary.get('revision_origin')}, conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', instructions(library, selection), context,
                        generation_schema(selection_schema(summary, tools, resources)))


def empty_commit(commit):
    """The old ``reasoning_has_task_content`` test: every section of the commit is empty."""
    return all(rows == [] for rows in commit.values())


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one commission, or reject it (no unit): an answer that does not
    fit the schema, or a reasoning commit with every section empty (rejected before acquisition)."""
    tools = selected_tools(ctx.settings, summary['selection'])
    schema = selection_schema(summary, tools, local_resources(ctx))
    try:
        if not isinstance(response, dict) or set(response) != {'selection'}:
            raise ValueError('a101_decision_response_must_be_exactly_selection')
        selection = decode_response(response, schema)['selection']
        Draft202012Validator(schema['properties']['selection']).validate(selection)
        if selection['kind'] == 'tool' and selection['tool'] == 'reason' and empty_commit(
                selection['arguments']['commit']):
            raise ValueError('empty_reasoning_commit')
    except (ValueError, KeyError, TypeError, ContractError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract')) from error
    if selection['kind'] == 'episode_child':
        arguments = {key: value for key, value in selection.items() if key not in ('kind', 'slot')}
        return ChildCall(selection['slot'], arguments)
    scope = summary['scope']
    if selection['tool'] == 'reason':
        return ToolCall('reason', {'commit': selection['arguments']['commit'], 'scope': scope})
    if selection['tool'] == PAIRWISE_TOOL:
        return ToolCall(PAIRWISE_TOOL, dict(selection['arguments']))
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


async def pairwise_blast(arguments, ctx):
    """One pairwise comparison as one unit: run, fetch and grade, by the library's one function. The arguments are
    the model's four controlled choices."""
    return await pairwise_blast_comparison(
        ctx, program=arguments['program'], query_ref=arguments['query_ref'], subject_ref=arguments['subject_ref'],
        resource_id=arguments['resource_id'], executable_directory=ctx.settings['blast_executable_directory'])


TOOLS = {'reason': reason, 'execute_selected_tool': execute_selected_tool, PAIRWISE_TOOL: pairwise_blast}
