"""The task of the A101 head: one model-selected unit per decision. The model investigates the assigned subject with
the selected tools of its commission (``execute_selected_tool``), commits scientific interpretations (``reason``) and
commissions its children. It never ends the Episode: only the yield controller does.

Tools. ``reason`` is the ``Store.commit_reasoning`` path. ``execute_selected_tool`` dispatches a tool the commission
selected to the library's ``ToolRegistry``, called with ``ctx.store`` (a tool name here has lowercase letters, digits
and underscores, so the selected name travels as an argument). ``pairwise_blast`` is this episode's own defined tool:
the model fills out one request (the query, the reference sequence record, the program and a bound resource, each
from a fixed set). ``action`` runs the library's one deterministic check of that request against what the episode
holds and the bound resources (``check_pairwise_request``): a request with problems is rejected with the things to
fix and no unit is made; a request that passes runs as one unit (``pairwise_blast_comparison``: the search, the
fetch of its report and the grading). The credit counts the graded comparison as soon as its sheet is saved; no
reasoning commit is needed for it.

Children. The head's child episodes in the A101 tree are ``blast_database_preparation``, ``database_blast`` and
``all_vs_all_blast`` (HMMER later). A child is declared in ``CHILD_SLOTS`` when its episode is built (the runner
refuses a declared slot with no episode behind it), together with its commission in ``COMMISSIONS``. The model is the
router: for a child it answers with the slot and the controlled fields of that slot's commission
(``commission_fields``); it writes no assignment, objective or message. ``msg_to_child`` builds the child's
assignment, in the child's own form, from those choices and the summary. A slot is offered while its commission can
be stated from what this episode holds. The service ``job_access`` is read for the bound resources a commission or a
tool may name (``bound_resources``).

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
    PROGRAM_MOLECULES, check_pairwise_request, pairwise_blast_comparison)
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
    PAIRWISE_TOOL: ('Compare one query sequence with one reference sequence by a pairwise BLAST on a local resource. Fill '
                    'out the four fields of its request: query_ref (a sequence of your scope), reference_ref (another '
                    'sequence record you hold; held_sequences gives each record with its molecule), program (blastp '
                    'compares a protein query with a protein reference, blastn nucleotide with nucleotide, blastx a '
                    'nucleotide query with a protein reference, tblastn a protein query with a nucleotide '
                    'reference, tblastx two nucleotide sequences in translation) and resource_id (a local resource '
                    'of bound_resources). Code checks the request before anything runs. If something is wrong the '
                    'request comes back in feedback with the things to fix (each names the field, a code and what to '
                    'choose from) and nothing has run: correct those fields. A request that passes the check runs '
                    'as one unit, with no second call: code runs the search, fetches its report and grades it. The '
                    'completed outcome shows the controlled features of the saved pairwise sheet (counts and '
                    'fractions of paired and identical residues, the two lengths, the native E-value with the '
                    'search-space context the report gives) and observation_refs: one alignment observation per '
                    'reported alignment, which you now hold. A comparison you already hold is not run again. The '
                    'grading is automatic and your credit counts the graded correspondence as soon as the unit '
                    'completes: no reasoning commit is needed for it and none changes it. A failed outcome is a fault of '
                    'the environment, not of your request: it is reported once and the same request is not made '
                    'again.'),
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


def bound_resources(ctx):
    """The resources bound to the job service, each with its kind, which a commission or a tool may name (read
    through the service's read handle, so the read is recorded with the decision)."""
    access = ctx.services['job_access']
    return {resource['resource_id']: resource['kind'] for resource in access.read('resources')}


def pairwise_options(summary, resources):
    """The request of the ``pairwise_blast`` tool, as the model fills it out: each field from a fixed set (the held
    sequence records, the programs, the bound resources). Whether the filled request can run is decided by
    ``check_pairwise_request`` in ``action``. Not offered while fewer than two sequence records are held or no
    resource is bound."""
    held = list(summary['held_sequences'])
    if len(held) < 2 or not resources:
        return []
    return [obj({'kind': {'const': 'tool'}, 'tool': {'const': PAIRWISE_TOOL},
                 'arguments': obj({'query_ref': {'enum': held}, 'reference_ref': {'enum': held},
                                   'program': {'enum': list(PROGRAM_MOLECULES)},
                                   'resource_id': {'enum': list(resources)}})})]


def comparisons_made(summary):
    """The comparisons this episode holds (``completed``) or saw fail (``failed``), by query, reference and
    program: what ``check_pairwise_request`` refuses to run again."""
    made = {(row['comparison']['query_ref'], row['comparison']['reference_ref'], row['comparison']['program']): 'failed'
            for row in summary['units'] if row['kind'] == 'tool' and row['tool'] == PAIRWISE_TOOL
            and row['status'] != 'completed'}
    made.update({(row['query_ref'], row['reference_ref'], row['program']): 'completed'
                 for row in summary['held_comparisons']})
    return made


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
    resources = bound_resources(ctx)
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
        'handoff_refs': summary['handoff_refs'], 'bound_resources': resources,
        'held_sequences': summary['held_sequences'], 'held_comparisons': summary['held_comparisons'],
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
    fit the schema, a reasoning commit with every section empty (rejected before acquisition), or a pairwise request
    the check finds something to fix in (rejected with the things to fix)."""
    tools = selected_tools(ctx.settings, summary['selection'])
    resources = bound_resources(ctx)
    schema = selection_schema(summary, tools, resources)
    try:
        if not isinstance(response, dict) or set(response) != {'selection'}:
            raise ValueError('a101_decision_response_must_be_exactly_selection')
        selection = decode_response(response, schema)['selection']
        Draft202012Validator(schema['properties']['selection']).validate(selection)
        if selection['kind'] == 'tool' and selection['tool'] == 'reason' and empty_commit(
                selection['arguments']['commit']):
            raise ValueError('empty_reasoning_commit')
        if selection['kind'] == 'tool' and selection['tool'] == PAIRWISE_TOOL:
            problems = check_pairwise_request(
                selection['arguments'], sequences=summary['held_sequences'],
                scope_subjects=summary['scope']['subject_refs'], resources=resources, made=comparisons_made(summary))
            if problems:
                raise Rejected({'status': 'invalid', 'category': 'pairwise_blast_request',
                                'detail': {'request': selection['arguments'], 'fix': problems}})
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
        ctx, program=arguments['program'], query_ref=arguments['query_ref'], reference_ref=arguments['reference_ref'],
        resource_id=arguments['resource_id'], executable_directory=ctx.settings['blast_executable_directory'])


TOOLS = {'reason': reason, 'execute_selected_tool': execute_selected_tool, PAIRWISE_TOOL: pairwise_blast}
