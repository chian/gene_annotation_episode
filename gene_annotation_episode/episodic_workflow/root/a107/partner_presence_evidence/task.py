"""The task: the model investigates the supplied target under the pinned A107 evidence axis, thought pattern and
selected tools. It looks up library options and tool instructions, runs the selected tools, commits scientific
interpretations with the reasoning tool, prepares an alternative process for a new child, commissions a child
(itself, literature, launch, results, monitor or HPC). The prose report tool is not carried: the return is the controlled
finding code reads from the A107 scoring sheet. The task
always offers a unit and never ends the Episode: its yield controller does.

Old files carried here: ``task_instructions`` (``compose_instructions``) and ``goal.py`` (the instruction text),
``task_decision`` (the TASK prompt ``_task``) and ``presentation`` (which renderer), ``tool_selection`` (the tool
catalogue, ``process.revise``, ``_proposed_selection``), ``scientific_operations`` (``execute``: the lookups,
``process.revise``, the registry tools), ``decision_delivery`` / ``task.py`` (what a decision contains and the
admission of an answer), ``child_commissioning`` (the child roles and common actions) and
``scientific_assignment_contracts`` (``_COMMON_TOOLS`` and ``_REVISION_ARGUMENTS``).

Not carried (old runner): the ``request_context`` decision exchange and its history checks, the ``wait`` and
``redeliver_report`` actions, the saved-exchange checks, ``task_state`` (restore, checkpoint, ``record_effect``,
failure recording), ``validate_execution_context`` (a closed request permitted replay and never new dispatch: a
recorded commission), the source-byte operand authentication (a held record is custody), ``waiting`` and the
report-form machinery (``report_values``, ``report_update``). The old ``decision_exchange`` lookups
(``child_options``, composition information, own attempts) are the parent's own text below and ``view.outcomes`` in
the summary.

Not placed (no placement, so the use raises or is left out): ``component_axis_workflow.INSTRUCTIONS['A107']`` (the
A107 component text the old guidance began with; the axis instructions are in the library entry the model reads),
``execution_planning`` (``process.execution``: ``read`` and ``catalog``), the common tools ``process.tools``,
``episode.history``, ``episode.credit``, ``episode.annotation_score``, ``episode.monitoring_information``,
``episode.estimate_wait`` and ``shared.*`` (run by the old runner's ``execute``; ``episode.history`` and
``episode.credit`` are ``view.outcomes`` and the credit in the summary now), ``scientific_tool_retrieval``,
``composition_information`` (``episode.return_contract``: a child declares its return now) and the render helpers
of ``library.scientific_decision_presentation`` (private copies below)."""
import json

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.configuration.partner_presence_evidence.process_options import (
    catalog as process_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.partner_presence_evidence.evidence_axis_instructions import (
    instruction_view)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.scientific_instruction_text import (
    REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_progress import FIELDS as JOB_PROGRESS_FIELDS
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import rejection_feedback
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.construction_records import (
    CHILD_SELECTION_VERSION, REVISION_ORIGIN_VERSION, SELECTION_VERSION, scientific_digest, validate_child_selection,
    validate_revision_origin, validate_selection)
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import (
    ContractError, REF, identity, obj)
from gene_annotation_episode.episodic_workflow.episode_support.tools.partner_presence_evidence.evidence_operations import (
    A107ToolRegistry)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, catalog as knowledge_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

from .goal import GOAL
from .messages.msg_to_child import SELECTABLE
from .messages.read_from_parent import TOOL_SELECTOR

# The old child roles by slot (the old ``child_roles``): the head itself, literature, launch, results, monitor and
# HPC.
CHILD_SLOTS = {'partner_presence_evidence': 'partner_presence_evidence',
               'literature': 'partner_presence_evidence/published_evidence_assessment',
               'launch': 'partner_presence_evidence/execution_job_submission',
               'results': 'partner_presence_evidence/execution_result_acquisition',
               'monitor': 'partner_presence_evidence/execution_progress_assessment',
               'hpc': 'partner_presence_evidence/hpc_work_planning'}
# The library of options, the tool library and catalogue, the tool-instruction and launch-instruction libraries and
# the public clients of the registry: what the old head took as construction operands.
SERVICES = ('a107_library', 'tool_library', 'tool_catalog', 'tool_knowledge', 'launch_instructions',
            'public_clients')

# The old ``_COMMON_TOOLS`` that the library or the Store serve (the rest are not placed, see the module text).
COMMON_TOOLS = ('process.search', 'process.entry', 'process.sources', 'process.tools', 'knowledge.search',
                'knowledge.entry', 'knowledge.read', 'episode.history', 'episode.credit', 'episode.annotation_score',
                'episode.monitoring_information', 'episode.estimate_wait', 'shared.request_information',
                'shared.publish_information', 'shared.resolve_information_need', 'shared.read_information',
                'shared.list_information')
LIBRARY_TOOLS = ('process.search', 'process.entry', 'process.sources')
KNOWLEDGE_TOOLS = ('knowledge.search', 'knowledge.entry', 'knowledge.read')
THOUGHT_FIELDS = ('id', 'name', 'description', 'use_when', 'live_alternatives', 'decision_guidance',
                  'outcome_contingencies', 'boundary')
PROPOSAL_ERRORS = (ContractError, CustodyError, ValueError, KeyError, TypeError)
REVISION_ARGUMENTS = obj({'thought_pattern': obj({'version': {'const': 'partner_presence_evidence_option_ref_v1'},
                                                  'library_id': {'type': 'string', 'pattern': '^[a-f0-9]{64}$'},
                                                  'slot': {'const': 'thought_pattern'},
                                                  'option_id': {'type': 'string', 'pattern': '^P[0-9]+$'},
                                                  'entry_sha256': {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}}),
                          'child_tool_info': {'type': 'array', 'items': TOOL_SELECTOR, 'uniqueItems': True}})

# The old text of ``goal.scientific_guidance`` (without its ``INSTRUCTIONS['A107']`` prefix, which has no
# placement) and of ``ScientificGoal.instructions`` for an instruction-version axis. The spans about waiting for
# pending work are not carried (there is no wait action).
GUIDANCE = ('Scientific descendants remain A107. Use available shared operations for specific parent information '
            'needs or useful received findings. The immediate parent chooses within its own options or relays the '
            'need upward; publication does not commission work or promise a reply. Preserve named scientific '
            'components separately from controller progress.\n\n')
INSTRUCTION_VERSION_TEXT = (
    "Determine what the supplied target does within the parent's assigned question, scope and constraints. Start "
    'with the supplied sequence, selected file contents or snippets, preserving their boundaries, completeness and '
    'known context. No initial candidate annotation or publicly searchable name is required. Possible functions can '
    'emerge from the evidence and be compared or revised. Apply the complete selected investigation instructions and '
    'thought-pattern guidance on every decision. Use actual outcomes and received child results to choose and '
    'revise your approach. Selected instructions describe how to investigate; they are not evidence about this '
    'target. Preserve the measured subject, conditions, controls, native measurements, uncertainty and limits of '
    'inference when interpreting evidence. Missing information remains unknown.\n\n'
    'Choose an available tool, commit a scientific interpretation through the reasoning tool, or commission a '
    'scoped child, each as one unit; the child declares its own typed return and you select the fields you want. '
    'Use only the selected actual tools and their supplied resource instructions; choose callable operands through '
    'the declared response contract. Preserve the parent\'s exact requested result meanings and allowed values. '
    'Recorded facts come from actual records. Keep inherited information distinct from new findings and completed '
    'work distinct from attempts.\n\n'
    'Keep the assigned evidence axis, thought pattern and selected tools for this episode. process.revise prepares a '
    'different thought pattern and/or tool selection for a new child; it does not change this episode or start '
    'that child. To commission that alternative, copy its selection and revision_origin into the process_selection '
    "and revision_origin arguments of a separately selected partner_presence_evidence child commission with the "
    "child's objective, evidence, constraints and context. Children own their iterative choices. The configured "
    'controller owns continuation. Unchanged observations do not manufacture progress.')
RETURN_GUIDANCE = ('\nWhat returns to your parent is your credit and controlled features code reads from the A107 scoring '
                   'sheet: the literature partner sheets your literature children graded, side by side with the native '
                   'components and per-use qualifications you hold; no prose of yours is returned. Selecting a tool or a '
                   'child does not end your work: only the numerical controller does.')
EVIDENCE_THROUGH_CHILDREN = (
    "Choose each child's return fields to carry the evidence needed for your question. committed_record_refs carries "
    "the acquired scientific record references; select the provider's coverage/completeness fields when interpreting "
    'acquired rows or an empty result. A job handle, usable handoff or null failure field alone does not return the '
    'search data. Keep a completed empty acquisition distinct from partial or unavailable acquisition, and keep those '
    'acquisition facts separate from evidence for a biological function. Reporting does not require another '
    "supported/contradicted, function, path or scope verdict: use the grading sheet's existing criteria and status, "
    "without inventing a score threshold or asking a child to judge the same result again.")
PROCESS_REVISE_DESCRIPTION = (
    'Prepare a different thought pattern and/or selected actual tools for a new child investigating the same '
    "evidence axis. Return its selection for a separately selected partner_presence_evidence child commission with "
    "the child's objective, evidence, constraints and context. Copy result.selection and revision_origin into that "
    'commission. Changes no current process, starts no child and records no biological observation. Select the '
    'actual tool/resource choices of the pinned selection for the desired investigation.')
# The parent's own description of what each child is for (the old ``child_option_information`` text), from the
# children's own goals.
CHILD_OPTIONS = {
    'partner_presence_evidence': 'A new A107 investigation with a prepared alternative process (process.revise): its '
                                 'own thought pattern and tools, over the evidence and constraints you name.',
    'literature': 'Investigate which published evidence bears on the partner question: reported partner removal, '
                  'addback and coexpression evidence from named sources; returns its typed finding and, when '
                  'selected, the partner cells of its committed sheets.',
    'launch': 'Choose and commission the permitted concrete execution requests on an explicit resource_id (API, '
              'local or HPC); returns the original handoff records of the launched jobs.',
    'results': 'Acquire the selected execution results of a handed-off job (bounded status or file/page reads); '
               'returns the retained result acquisitions and the selected native result family facts.',
    'monitor': 'Check the progress of one job you hold as outstanding: handoff_ref (the handoff reference of one of '
               'the outstanding jobs) and requested_fields (what the monitor may observe of it). This parent '
               'requests information and never polls here. Returns its credit, what it found of the job (its '
               'state, whether its results are available) and its check records; return_fields selects its '
               'measurements.',
    'hpc': 'Plan, predict, allocate, launch, monitor and accept HPC work for the assigned computation; returns the '
           'plan, the allocation outcome and the execution handoffs.'}

# What a monitor may be asked to observe of a job (the monitor's ``requested_fields``).
MONITOR_FIELDS = (*JOB_PROGRESS_FIELDS, 'log_windows')
TEXT = {'type': 'string', 'minLength': 1}
REFS = {'type': 'array', 'items': REF, 'uniqueItems': True}
OBJECT = {'type': 'object'}
# What the model supplies to commission each child (the old assignment fields the model chose; every other field of
# the child's form is filled by ``msg_to_child`` from this episode's own parent input): (properties, required).
CHILD_FIELDS = {
    'partner_presence_evidence': ({'process_selection': OBJECT, 'revision_origin': OBJECT, 'evidence_refs': REFS,
                                   'constraints': OBJECT, 'context': OBJECT},
                                  ['process_selection', 'evidence_refs', 'constraints', 'context']),
    'literature': ({'question_context_refs': REFS, 'source_refs': REFS,
                    'partner_components': {'type': 'array', 'items': TEXT, 'uniqueItems': True}},
                   ['question_context_refs', 'source_refs']),
    'launch': ({'requests': OBJECT, 'immutable_input_versions': {'type': 'array', 'items': OBJECT},
                'constraints': OBJECT, 'launch_instructions': OBJECT, 'record_refs': REFS,
                'received_handoff_resources': {'type': 'array', 'items': TEXT, 'uniqueItems': True}},
               ['requests', 'immutable_input_versions', 'constraints']),
    'results': ({'handoff_ref': TEXT, 'selector': OBJECT, 'target': OBJECT, 'record_refs': REFS,
                 'initial_result_refs': REFS}, ['handoff_ref', 'selector', 'target']),
    'monitor': ({'requested_fields': {'type': 'array', 'items': {'enum': list(MONITOR_FIELDS)},
                                      'uniqueItems': True}}, ['requested_fields']),
    'hpc': ({'commission_id': TEXT, 'commission_source_ref': REFS, 'tool_request': OBJECT,
             'received_record_refs': REFS, 'input_refs': REFS}, []),
}
# The arguments of each slot that name Store records the head must hold (an answer naming an unheld record is an
# invalid answer: the provisional held-record check of ``action``, never a check of a commission).
RECORD_ARGUMENTS = {'partner_presence_evidence': ('evidence_refs',),
                    'literature': ('question_context_refs', 'source_refs'), 'launch': ('record_refs',),
                    'results': ('record_refs', 'initial_result_refs'), 'monitor': (),
                    'hpc': ('commission_source_ref', 'received_record_refs', 'input_refs')}


def instructions():
    """The old composed instructions: the guidance and the instruction-version text (this binding replaced the default
    instructions), the reasoning-commit requirement and the tool-knowledge and launch-instruction texts (the old
    contexts always held both libraries). The old pending-child, ``wait``, native-event and exchange-protocol
    paragraphs describe actions that no longer exist."""
    return (GUIDANCE + INSTRUCTION_VERSION_TEXT + '\n' + REASONING_COMMIT_REQUIREMENT + KNOWLEDGE_INSTRUCTIONS
            + LAUNCH_INSTRUCTIONS + RETURN_GUIDANCE)


def selected_entries(summary, ctx):
    """The old ``catalog``: the selected actual tools (direct invocations only, without their instructions), then
    ``process.revise``. The library lookups are offered beside them (the old common tools)."""
    available = ctx.services['tool_catalog'].read('entries')
    resolved = ctx.services['tool_library'].read('resolve_invocations', summary['selection']['child_tool_info'],
                                                 available)
    direct = [row for row in resolved if row.get('invocation_route', {'kind': 'direct'})['kind'] == 'direct']
    entries = [{key: value for key, value in row.items() if key not in ('instructions', 'invocation_route')}
               for row in direct]
    if any(entry['name'] in (*COMMON_TOOLS, 'process.revise') for entry in entries):
        raise ContractError('scientific_primitive_uses_common_tool_name')
    return entries


def offered_catalog(summary, ctx):
    """Every operation the model may select, by its dotted name: the selected tools, ``process.revise``, the library
    options lookups and the tool-knowledge lookups."""
    entries = selected_entries(summary, ctx)
    entries.append({'name': 'process.revise', 'description': PROCESS_REVISE_DESCRIPTION,
                    'input_schema': REVISION_ARGUMENTS})
    entries.extend(process_catalog())
    entries.extend(knowledge_catalog())
    return entries


def commissionable(jobs):
    """The children that can be commissioned now: the monitor only while a job is outstanding."""
    return [slot for slot in CHILD_SLOTS if slot != 'monitor' or jobs]


def child_arguments(slot, jobs):
    """What the model supplies to commission a child. ``return_fields`` is the selectable fields it wants of what
    the child declares; a child that declares none has no ``return_fields`` (an array schema needs its ``items``,
    and an ``enum`` of no names admits nothing). A monitor is commissioned on one of ``jobs`` (the outstanding jobs
    of the summary), named by its held handoff reference; no text of the model passes to it."""
    properties, required = CHILD_FIELDS[slot]
    names = sorted(SELECTABLE[slot])
    head = ({'handoff_ref': {'enum': [job['handoff_ref'] for job in jobs]}} if slot == 'monitor'
            else {'objective': TEXT, 'purpose': TEXT})
    fields = {**head, **properties}
    if names:
        fields['return_fields'] = {'type': 'array', 'items': {'enum': names}, 'uniqueItems': True}
    return obj(fields, [*head, *(['return_fields'] if names else []), *required])


def action_schema(catalog, summary):
    """What the model answers with: one tool (the selected tools, the lookups, ``process.revise``, the reasoning
    commit), or one child commission with the return fields it wants. The reasoning commit is the tool ``reason``:
    the arguments of a tool whose schema is composed travel as JSON text, and the Store's reasoning schema sent as
    output schema itself has more enum values than the model endpoint takes in one schema."""
    reason_entry = {'name': 'reason', 'input_schema': obj({'commit': summary['reasoning_schema']})}
    branches = [{'type': 'object', 'additionalProperties': False, 'required': ['kind', 'tool', 'arguments'],
                 'properties': {'kind': {'const': 'tool'}, 'tool': {'const': entry['name']},
                                'arguments': entry['input_schema']}} for entry in (*catalog, reason_entry)]
    jobs = summary['outstanding_jobs']
    branches.extend({'type': 'object', 'additionalProperties': False, 'required': ['kind', 'slot', 'arguments'],
                     'properties': {'kind': {'const': 'child'}, 'slot': {'const': slot},
                                    'arguments': child_arguments(slot, jobs)}} for slot in commissionable(jobs))
    return {'type': 'object', 'additionalProperties': False, 'required': ['selection'],
            'properties': {'selection': {'anyOf': branches}}}


# How the action schema travels to the model: the model endpoint takes no open object, so a record whose fields the
# schema leaves open (the ``OBJECT`` arguments of a commission) travels as JSON text and is decoded in ``action``.
TRANSPORT = {'open_records_as_text': True, 'argument_transport_error': 'a107_argument_transport_not_carried'}


def transport(schema):
    return strict_output_schema(schema, **TRANSPORT)


# The private copies of the old presentation helpers (``_section``, ``_values``, ``_scalar``, ``_table``): a section
# is its title and the value as JSON text.
def section(parts, title, value):
    if value not in (None, [], {}, ()):
        parts.extend(('', title, value if isinstance(value, str) else json.dumps(value, sort_keys=True,
                                                                                  allow_nan=False)))


def table(headers, rows):
    return '\n'.join([' | '.join(headers), *(' | '.join(str(cell) for cell in row) for row in rows)])


def render_prompt(summary, axis, thought, catalog, ctx, feedback):
    """The old TASK (``task_decision._task``) and STEERING (``render_episode_steering``) layout. Not carried: the
    working-state sections (subjects, materials, collections, links: ``working_state``), the parent-written return
    form and the meaning of requested facts (the child declares its return; this episode's own return fields are in
    ``messages/final_to_parent.py``) and the report timing note."""
    parts = ['TASK', '', GOAL]
    section(parts, 'Assigned work', {'objective': summary['objective']})
    section(parts, 'Fixed scope', summary['scope'])
    section(parts, 'Parent constraints', summary['constraints'])
    section(parts, 'Parent-supplied context', summary['context'])
    section(parts, 'Parent-selected evidence operands', summary['evidence_refs'])
    section(parts, 'Proposed annotation', summary['proposed_annotation_ref'])
    section(parts, 'Records held', summary['held_record_refs'])
    section(parts, 'Investigate the supplied target: ' + axis.get('name', ''), axis['investigation_instructions'])
    section(parts, 'Reason about the evidence: ' + thought.get('name', ''),
            '\n\n'.join(str(thought[name]) for name in ('description', 'use_when') if name in thought))
    for field, label in (('live_alternatives', 'Alternatives to distinguish'),
                         ('decision_guidance', 'How to choose and revise the investigation')):
        if thought.get(field):
            section(parts, label, '\n'.join('- ' + item for item in thought[field]))
    if thought.get('outcome_contingencies'):
        section(parts, 'How outcomes affect the next choice',
                table(('If observed', 'Then consider'),
                      ((row['if_observed'], row['then_consider']) for row in thought['outcome_contingencies'])))
    section(parts, 'Limits of this reasoning approach', thought.get('boundary'))
    section(parts, 'Callable operations', table(('Operation', 'Meaning'),
                                               ((entry['name'], entry.get('description', '')) for entry in catalog)))
    for entry in catalog:
        section(parts, 'Operands for ' + entry['name'], entry['input_schema'])
    slots = commissionable(summary['outstanding_jobs'])
    section(parts, 'Permitted child roles', sorted(slots))
    section(parts, 'Child construction and requested facts', {slot: CHILD_OPTIONS[slot] for slot in slots})
    section(parts, 'Return fields each child can be asked for', {slot: SELECTABLE[slot] for slot in slots})
    section(parts, 'Evidence through child returns', EVIDENCE_THROUGH_CHILDREN)
    section(parts, 'Tool knowledge', ctx.services['tool_knowledge'].read('context'))
    section(parts, 'Launch instruction library', ctx.services['launch_instructions'].read('context'))
    steering = ['STEERING']
    section(steering, 'Own action yields', summary.get('yield_table'))
    section(steering, 'Current A107 scoring sheet', {'scoring_sheet': summary['scoring_sheet'],
                                                     'committed_record_refs': summary['committed_record_refs']})
    section(steering, 'Prepared alternative processes', summary['revisions'])
    section(steering, 'Received A107 evidence', summary['received'])
    section(steering, 'Received child reports', summary['child_reports'])
    section(steering, 'Outstanding jobs (a monitor is commissioned on one by its handoff_ref)',
            [{name: job[name] for name in ('handoff_ref', 'job', 'resource_id', 'kind', 'submitted_at',
                                           'latest_check')} for job in summary['outstanding_jobs']])
    section(steering, 'Own earlier outcomes', {'meaning': summary['history_meaning'], 'page': summary['own_outcomes']})
    section(steering, 'Feedback on your last answer', feedback)
    return '\n'.join(parts) + '\n\n' + '\n'.join(steering)


def decide(summary, feedback, ctx):
    library = ctx.services['a107_library']
    axis = instruction_view(library.read('resolve', summary['selection']['evidence_axis']))
    entry = library.read('resolve', summary['selection']['thought_pattern'])
    thought = {name: entry[name] for name in THOUGHT_FIELDS if name in entry}
    catalog = offered_catalog(summary, ctx)
    return ModelRequest('REASONING', instructions(),
                        {'prompt': render_prompt(summary, axis, thought, catalog, ctx, feedback)},
                        transport(action_schema(catalog, summary)))


def named_references(value):
    """Every record a model-written value names: a value under a key ``ref`` or ``..._ref``, or in a list under
    ``..._refs``."""
    if isinstance(value, dict):
        for key, child in value.items():
            if (key == 'ref' or key.endswith('_ref')) and isinstance(child, str):
                yield child
            elif key.endswith('_refs') and isinstance(child, list):
                yield from (item for item in child if isinstance(item, str))
            else:
                yield from named_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from named_references(child)


def check_held(records, references):
    for reference in references:
        if not records.holds(reference):
            raise ContractError('scientific_evidence_reference_unavailable', detail={'reference': reference})


def empty_commit(commit, schema):
    """The old ``reasoning_has_task_content`` test: every row list of the commit is empty."""
    return (set(schema.get('required', schema['properties'])) <= set(commit) <= set(schema['properties'])
            and all(value == [] for value in commit.values()))


def action(response, summary, records, ctx):
    catalog = offered_catalog(summary, ctx)
    schema = action_schema(catalog, summary)
    try:
        decoded = decode_strict_output(response, schema, **TRANSPORT)
        Draft202012Validator(schema).validate(decoded)
    except (ValidationError, ValueError) as error:   # an answer that does not fit, or JSON text that does not parse
        raise Rejected(rejection_feedback(error, category='action_contract'))
    selection = decoded['selection']
    try:
        if selection['kind'] == 'child':
            slot, arguments = selection['slot'], selection['arguments']
            for name in RECORD_ARGUMENTS[slot]:
                check_held(records, arguments.get(name) or ())
            return ChildCall(slot, arguments)
        tool, arguments = selection['tool'], selection['arguments']
        if tool == 'reason':
            if empty_commit(arguments['commit'], records.reasoning_schema()):
                raise ValueError('empty_reasoning_commit')
            return ToolCall('reason', {'commit': arguments['commit'], 'scope': summary['scope']})
        if tool == 'process.revise':
            return ToolCall('process_revise', {'revision': arguments, 'selection': summary['selection']})
        if tool in (*LIBRARY_TOOLS, *KNOWLEDGE_TOOLS):
            return ToolCall(tool.replace('.', '_'), arguments)
        check_held(records, named_references(arguments))
    except PROPOSAL_ERRORS as error:
        raise Rejected(rejection_feedback(error, category='arguments_or_reference'))
    permitted = (list(records.refs()) if tool.startswith(('context.', 'partner.'))
                 or tool in ('reference.neighborhood', 'result.blast.hsp', 'source.locate') else None)
    return ToolCall('selected_tool', {'tool': tool, 'arguments': arguments, 'scope': summary['scope'],
                                      'permitted_record_refs': permitted})


async def selected_tool(arguments, ctx):
    """One selected actual tool, run by the axis registry handed ``ctx.store`` (old ``services.execute_tool(tool_name,
    arguments, scope=..., operation_key=..., permitted_record_refs=...)``). The registry is the library's old
    ``A107ToolRegistry(store, ...)`` (raw Store: ``store.db``, the ``a107_operations`` table): called as written."""
    registry = A107ToolRegistry(ctx.store, clients=ctx.services['public_clients'], **ctx.settings['tool_registry'])
    try:
        return await registry.execute_async(arguments['tool'], arguments['arguments'], scope=arguments['scope'],
                                            operation_key=ctx.operation_key,
                                            permitted_record_refs=arguments['permitted_record_refs'])
    except (ContractError, CustodyError) as error:
        return failure_outcome(ctx.store, error, category='arguments_or_reference', cause_code=str(error))


def library_lookup(name, arguments, ctx):
    return ctx.services['a107_library'].execute(name, arguments)


def process_search(arguments, ctx):
    return library_lookup('process.search', arguments, ctx)


def process_entry(arguments, ctx):
    return library_lookup('process.entry', arguments, ctx)


def process_sources(arguments, ctx):
    return library_lookup('process.sources', arguments, ctx)


def knowledge_lookup(name, arguments, ctx):
    return ctx.services['tool_knowledge'].execute(name, arguments)


def knowledge_search(arguments, ctx):
    return knowledge_lookup('knowledge.search', arguments, ctx)


def knowledge_entry(arguments, ctx):
    return knowledge_lookup('knowledge.entry', arguments, ctx)


def knowledge_read(arguments, ctx):
    return knowledge_lookup('knowledge.read', arguments, ctx)


def process_revise(arguments, ctx):
    """The old ``process.revise``: prepare a different thought pattern and tool selection for a new child (old
    ``_proposed_selection``, ``_tool_resolution``, ``validate_child_selection``, the operation reference and the
    revision origin). It changes nothing and starts nothing. The parent invocation is identified by this run and
    Episode (the old ``scientific_invocation_ref(run_id, path)`` took the old runner's path)."""
    revision, parent = arguments['revision'], arguments['selection']
    try:
        available = ctx.services['tool_catalog'].entries
        tools = ctx.services['tool_library']
        initial = validate_selection({**parent, 'child_tool_info': tools.resolve_tool_info(parent['child_tool_info'],
                                                                                           available)})
        proposed = validate_selection({'version': SELECTION_VERSION, 'evidence_axis': initial['evidence_axis'],
                                       'thought_pattern': revision['thought_pattern'],
                                       'child_tool_info': tools.resolve_tool_info(revision['child_tool_info'],
                                                                                 available)})
        ctx.services['a107_library'].resolve(proposed['thought_pattern'])
        resolved = tools.resolve_invocations(proposed['child_tool_info'], available)
        if any(entry['name'] in (*COMMON_TOOLS, 'process.revise') for entry in resolved):
            raise ContractError('scientific_primitive_uses_common_tool_name')
        child = validate_child_selection({'version': CHILD_SELECTION_VERSION,
                                          'parent_selection_sha256': scientific_digest(initial),
                                          'selection': proposed})
        operation_ref = identity('operation', {'key': ctx.operation_key, 'name': 'process.revise',
                                               'arguments': revision})
        origin = validate_revision_origin({
            'version': REVISION_ORIGIN_VERSION,
            'parent_invocation_ref': identity('scientific_invocation', {'run_id': ctx.run_id,
                                                                        'episode_id': ctx.episode_id}),
            'preparation_operation_ref': operation_ref})
    except ValueError as error:
        return {'status': 'invalid', 'operation_ref': identity('operation', {'key': ctx.operation_key,
                                                                             'name': 'process.revise'}),
                'record_refs': [], 'changed_record_refs': [], 'result': None, 'revision_origin': None,
                'feedback': {'category': 'arguments_or_reference', 'code': str(error),
                             **({'detail': error.detail} if getattr(error, 'detail', None) else {})}}
    return {'status': 'completed', 'operation_ref': operation_ref, 'record_refs': [], 'changed_record_refs': [],
            'result': child, 'revision_origin': origin, 'feedback': None}


def process_execution(arguments, ctx):
    """Old: ``execution_planning.read(binding, context, arguments)`` (``process.execution``), which has no placement."""
    raise NotImplementedError('unplaced:execution_planning.read')


def reason(arguments, ctx):
    """The old ``reason`` action: commit the reasoning payload in the commissioned scope (old
    ``store.commit_reasoning(payload, scope, key)``). A payload that names a record this Episode does not hold is
    refused by custody and is this unit's failed outcome."""
    try:
        return ctx.store.commit_reasoning(arguments['commit'], arguments['scope'], ctx.operation_key)
    except CustodyError as error:
        return failure_outcome(ctx.store, error, category='arguments_or_reference', cause_code=str(error))


TOOLS = {'selected_tool': selected_tool, 'process_search': process_search, 'process_entry': process_entry,
         'process_sources': process_sources, 'knowledge_search': knowledge_search,
         'knowledge_entry': knowledge_entry, 'knowledge_read': knowledge_read, 'process_revise': process_revise,
         'process_execution': process_execution, 'reason': reason}
