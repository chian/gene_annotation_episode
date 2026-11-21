"""The task: one model-selected unit per decision for the A110 evidence axis (biochemical feasibility and
chemical/resource accounting), over the tools, the reasoning commit and the six child commissions.

Carried from ``task.py`` (``ScientificTask.next``, ``apply_response``, ``execute``), ``decision_delivery.py``
(``call``, ``instructions``), ``task_instructions.py`` (``compose_instructions``), ``task_decision.py`` (the TASK
prompt sections), ``goal.py`` (the instruction text and ``scientific_guidance``), ``tool_selection.py`` (the catalogue
and ``process.revise``), ``scientific_operations.py`` (``execute``), ``initial_information.py`` and
``internal_summary.py`` (``initial_decision_context``: the received evidence). One unit is one model selection: a tool
(``TOOLS``) or the commission of one of the six children (``CHILD_SLOTS``: the old roles ``launch``, ``monitor``,
``results``, ``hpc``, ``literature`` and the recursive ``biochemical_feasibility_evidence``). The task always offers a
unit and never ends the Episode: only the yield controller does. Not carried: the ``wait`` and ``redeliver_report``
actions, the decision exchange (``request_context``), the running ``report_update`` of every decision (the model's
interpretation is the outcome of the tool ``write_interpretation``), checkpoint and restore, and the old common tool
catalogue entries that were services of the old runner (``process.search``, ``process.entry`` for lookups of the
parent library other than the selected entries, ``process.sources``, ``process.tools``, ``episode.history``,
``episode.credit``, ``episode.annotation_score``, ``episode.monitoring_information``, ``episode.estimate_wait``,
``shared.*``): the episode's own history and credit are in the context, the rest have no home.

Tool names are ``[a-z][a-z0-9_]*`` now (``process.revise`` is ``process_revise``, ``knowledge.search`` is
``knowledge_search``). The two initial lookups are the first part of the task, offered through its own tools:
``process_entry`` (the selected evidence axis and thought pattern entries and the selected tools, resolved from the
process library and the tool library) and ``received_evidence`` (the received component-axis evidence).

The settings of this binding (``ctx.settings``): ``child_roles`` (the slots offered, the old configured
``child_roles``; it names ``biochemical_feasibility_evidence`` itself), ``handoff_unit``, ``acquired_record_unit`` and
``information_unit`` (the credit units of the launch, results and monitor children, the old configuration of those
children), ``tool_registry`` (the keyword operands of the A110 ``ToolRegistry``), optionally ``knowledge_directory``
and ``launch_instruction_directory``, and ``yield_bindings`` (the old ``yield_bindings``, read by the yield
estimator)."""
import json

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.scientific_instruction_text import (
    REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_progress import FIELDS as JOB_PROGRESS_FIELDS
from gene_annotation_episode.episodic_workflow.episode_support.jobs.sequence_and_context_sources import (
    component_axis_native_hpc as native)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.domain import (
    ContractError, obj)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.biochemical_feasibility_evidence.tools import (
    ToolRegistry)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge, catalog as knowledge_catalog)

# ---------------------------------------------------------------------------- the A110 axis guidance
# (the old ScientificGoal.instructions prefixed the text of the old component_axis_workflow module, which is not placed; the text is carried from the earlier port's copy)
VERSION = 'component_axis_investigation_v1'
NAMES = {'A110': 'Biochemical feasibility and chemical/resource accounting'}
TASKS = {
    'A110': ('reaction_identity', 'stoichiometric_accounting', 'electron_accounting',
        'cofactor_regeneration', 'resource_feasibility', 'conditional_energetics',
        'prediction_contrast', 'target_transfer', 'synthesis'),
}
_AXIS_INSTRUCTIONS = {
    'A110': 'Investigate whether a possible reaction or pathway is chemically sustainable '
        'under its declared conditions. Start from the supplied material and biological question; '
        'discover or obtain specific reaction leads through legitimate sources and parent exchange. '
        'For direct source inspection, include the actual source.read/source.locate '
        'capabilities when selecting the fixed child toolset. Native request and '
        'qualification operations do not implicitly grant source readers. '
        'Identify chemical entities, compartments, stoichiometric coefficients, reaction direction '
        'and alternatives before interpreting feasibility. Keep atom/charge bookkeeping, electron '
        'flow, cofactor and carrier regeneration, usable resource constraints and conditional '
        'energetics distinguishable. Rhea, ChEBI and KEGG source records retain their native '
        'direction, identity and qualification; a database equation does not establish physiological '
        'direction or activity. Use literature.reaction.populate or '
        'literature.reaction.source.populate through the configured literature '
        'child for the existing reaction-prediction/resource components; retain their exact '
        'measurement scale, source meanings, native uncertainty and missing reasons. '
        'Do not turn instrument signals into molar amounts, a product-pair ratio into substrate '
        'consumption, or steady-state FBA into thermodynamic feasibility. Repeated source views '
        'retain their original measurement identities. A regenerated carrier is not necessarily '
        'consumed once per turnover. Unknown formula, charge, resource, mapping or energetic '
        'prerequisite stays unknown. Use chemistry.request_accounting_hpc for an admitted '
        'declared chemical panel: exact equation residuals, explicit electron terms, declared '
        'pathway/carrier accounting and conditional chemical-standard-state Gibbs components. '
        'The declared weighted pathway energy is the sum of step energies at one matching '
        'physical condition, not evidence that each step is favorable or physically coupled. '
        'Unsupported formula/energetic conventions remain explicit; qualified chemical '
        'energetics requires the corresponding equation, identity and physical prerequisites. '
        'For received public Rhea and ChEBI records, chemistry.prepare_reference_accounting '
        'can assemble a source panel from exact participant identities and source fields '
        'for the existing HPC accounting operation. Missing source records remain specific '
        'parent needs; source balance assertions and the actual native calculation are '
        'different evidence. Source preparation supplies no physical conditions or activity. '
        'Use chemistry.reaction_evidence for a particular reaction-reference and molecular '
        'application; source interpretations and received sequence/region maps remain separate '
        'from the chemical calculation. For already saved experimental reaction-ratio, '
        'prediction or resource-model components, use chemistry.experimental_reaction_evidence '
        'with the actual sheet and selected component names. That independent path can retain '
        'source quantities and explicit unresolved application before obtaining a biological '
        'reaction reference, an accounting panel or a protein map. Qualify ratio/prediction '
        'and resource-model uses separately, retaining the source model definitions and '
        'actual assayed subject. Neither a sheet handle nor a protein map supplies unreceived '
        'cells or converts a resource model into a protein measurement. Original assay roles '
        'are not sequence operands: chemistry.source_identity_evidence can retain a received '
        'source declaration linking one original role to an actual protein and experiment. '
        'Select that saved identity for the particular molecular use; preserve unknown '
        'construct identity and share missing records with the parent. Protein features preserve their local coordinates '
        'and received parent-to-feature paths for a particular native correspondence. Keep '
        'missing parent frames and conflicting residue maps explicit and separate '
        'from chemical opposition. If a pinned remote FBA deployment is configured, '
        'chemistry.request_flux_balance_hpc uses the original driver, readers and calculations '
        'on the shared HPC service and returns only the selected projection. Do not count '
        'a remote worksheet path/digest as a receipt for other cells. Feasibility alone does '
        'not demonstrate molecular activity.',
}

_NATIVE_RETURN_GUIDANCE = (
    'When commissioning a biochemical_feasibility_evidence child whose child_tool_info includes '
    'chemistry.request_accounting_hpc or chemistry.request_flux_balance_hpc, '
    'its facts must include both component_axis_native_component_records '
    'and component_axis_native_execution_records (select them when commissioning it). '
    'Preparation or unavailable work can return empty component arrays and its saved '
    'execution findings. This custody requirement does not require a job to succeed.'
)

_SOURCE_COMMIT_GUIDANCE = (
    'Each text-derived source_content observation requires its own observations[].anchor. '
    'Select the actual source_ref, artifact_ref and zero-based half-open UTF-8 '
    'start/end from a received source.read window or source.locate match. The host '
    'retrieves and stores the exact quotation within the original reasoning action. '
    'For source.locate, use its artifact_ref together with the selected match '
    'witness source_ref/start/end. '
    'A source_subjects[].anchor does not populate observations[].anchor; retain the '
    'observation\'s own source and measured subjects. After a partial commit, reuse the '
    'successful aliases or saved record IDs and their actual witnesses when correcting '
    'rejected rows; successful rows remain committed. These source commitments are '
    'separate from the automatically projected numerical components.'
)
AXIS_GUIDANCE = {axis: instruction+' '+_NATIVE_RETURN_GUIDANCE+' '+_SOURCE_COMMIT_GUIDANCE
    for axis, instruction in _AXIS_INSTRUCTIONS.items()}


def scientific_guidance():
    """The A110 head's own investigation guidance: the axis question and the descendant relationship."""
    return AXIS_GUIDANCE['A110'] + '\n\nScientific descendants remain A110. Preserve named scientific components separately from controller progress.\n\n'


def task_context(task):
    if task not in TASKS['A110']:
        raise ContractError('component_axis_unknown_task')
    return {'version': VERSION, 'axis': 'A110', 'name': task, 'allowed_tasks': list(TASKS['A110']),
        'scientific_question': AXIS_GUIDANCE['A110'],
        'communication': 'Scientific descendants retain this evidence axis. Share acquired '
            'findings and specific missing-information needs through shared.*. The shared '
            'parent commissions complementary evidence axes as siblings; consume their '
            'actually delivered records, not their aggregate credit or private sheets.',
        'execution': 'The actual configured tool/resource catalog determines availability. '
            'Use the existing private execution/HPC parent and prediction/execution sisters '
            'for substantial computation; an availability notice, path or job ID is not a '
            'scientific result. Preserve original inputs, scope, software and result receipts. '
            'The original ordinary flux-balance adapter remains local-only. The new '
            'chemistry.request_flux_balance_hpc bridge is available only with caller-configured '
            'pinned remote software; availability is not an executed deployment check. These '
            'axis registries expose no local heavy FBA fallback. '
            'Publish missing execution capability to the shared parent. Read the actual '
            'whole-workflow CPU/RAM bounds and admission feedback.',
        'reporting': 'Return retained scientific findings and exact requested numerical cells '
            'with their source, biological scope, dependence and limitations. The receiver '
            'automatically projects its current scoring sheets from actual admitted cells, '
            'native graders and per-use qualifications. No synthesis child, finalize action '
            'or model-written conclusion is required to make an existing result count. Selected path '
            'evidence and correspondence references are interpretations, not automatic transfer '
            'proofs. Controller progress uses retained findings and remains separate from '
            'scientific component values. No new combined scientific scalar is defined.'}



# ------------------------------------------------------------------------------------------------ the slots

_PREFIX = 'biochemical_feasibility_evidence/'
CHILD_SLOTS = {'launch': _PREFIX + 'execution_job_submission',
               'monitor': _PREFIX + 'execution_progress_assessment',
               'results': _PREFIX + 'execution_result_acquisition',
               'hpc': _PREFIX + 'hpc_work_planning',
               'literature': _PREFIX + 'published_evidence_assessment',
               'biochemical_feasibility_evidence': 'biochemical_feasibility_evidence'}
SERVICES = ()
MODEL_ROLE = 'REASONING'

# The return fields each child declares as selectable, read from the children's ``final_to_parent.py`` (the parent
# selects among them, the child declares them).
SELECTABLE = {
    'launch': ('execution_completed', 'execution_result_refs', 'execution_file_source_refs',
               'execution_file_capture_outcomes'),
    'monitor': ('job_returncode', 'job_duration_seconds', 'job_elapsed_seconds', 'stdout_bytes', 'stderr_bytes',
                'log_window_refs', 'event_receipt_refs'),
    'results': ('execution_handoff_refs', 'execution_job_record_refs'),
    'hpc': ('hpc_credit', 'hpc_model_ref', 'hpc_accepted_obligations', 'hpc_result_refs'),
    'literature': (),
    'biochemical_feasibility_evidence': ('component_axis_native_component_records',
                                         'component_axis_native_execution_records'),
}

_TEXT = {'type': 'string', 'minLength': 1}
_REF = {'type': 'string', 'minLength': 1}
_REFS = {'type': 'array', 'items': _REF, 'uniqueItems': True}
_STRINGS = {'type': 'array', 'items': _TEXT, 'uniqueItems': True}

ACTION_ANSWER = (
    '\nAnswer with one selection from the offered actions and its arguments as JSON object text in arguments_json '
    '(the actions list gives the argument schema of each). A tool runs as one unit. A child commission is one unit '
    'whose child works to its own end and returns its typed result; the facts you list in a commission are the '
    'selectable return facts you want from it. The configured controller owns continuation. A lookup is a tool: its '
    'outcome is in the history at your next decision. Write your current interpretation with write_interpretation; '
    'it earns nothing by itself and does not end the investigation.')


# ----------------------------------------------------------------------------------------------- the tools

def _not_placed(what):
    """An old module of the shared root that has no placed home: the use raises where it is reached."""
    raise NotImplementedError('old_module_not_placed:' + what)


def process_entry(arguments, ctx):
    """The first lookup (the old ``decision_context``: ``library.resolve(selection[...])``, ``instruction_view``, the
    thought pattern fields and ``tool_library.resolve_tool_info``): the selected evidence axis entry, the thought
    pattern entry and the selected tools with their descriptions and instructions.

    BLOCKED, not placed: the old ``biochemical_feasibility_evidence_library`` (``library.resolve``,
    ``evidence_axis_instruction_view``), ``evidence_axis_instructions`` (``instruction_view``) and the tool library
    (``tool_library.resolve_tool_info``, ``resolve_invocations``) have no module (``module_of_that_name_now`` is
    ``none``). Wanted calls: ``library.resolve(selection['evidence_axis'])``, ``library.resolve(selection[
    'thought_pattern'])``, ``tool_library.resolve_invocations(selection['child_tool_info'], catalog)``."""
    _not_placed('biochemical_feasibility_evidence_library.resolve')


def received_evidence(arguments, ctx):
    """The second lookup (the old ``initial_decision_context``): the current component scoring sheets, the received
    partner and chemical evidence, the received native components with the execution findings and the prepared HPC
    assignments, and the received A110 qualifications. The first step has no placed home (``component_axis_reports``,
    ``component_axis_execution_context`` and ``a110_qualification`` have no module): the use raises there; the
    native-component reads that follow are the library's (``component_axis_native_hpc``, still in its old form)."""
    store, references, scope = ctx.store, arguments['record_refs'], arguments['scope']
    sheets = _not_placed('component_axis_reports.current_scoring_sheets')
    reports = _not_placed('component_axis_reports.received_reports')
    components = native.received_components(store, references, scope)
    execution = native.execution_findings(store, references, scope)
    prepared = _not_placed('component_axis_execution_context.prepared_assignments')
    qualifications = _not_placed('a110_qualification.received')
    return {'status': 'completed', 'scoring_sheets': sheets, 'received_reports': reports,
            'native_components': components, 'execution_findings': execution,
            'prepared_hpc_assignments': prepared, 'qualifications': qualifications}


def tool_catalog(arguments, ctx):
    """The operand schemas of the selected tools (the old ``catalog`` over ``services.tool_catalog(scope)``)."""
    registry = ToolRegistry(ctx.store, **ctx.settings['tool_registry'])
    catalog = registry.catalog(arguments['scope'])
    wanted = set(arguments['names'])
    return {'status': 'completed', 'tools': {name: entry for name, entry in catalog.items() if name in wanted}}


async def scientific_tool(arguments, ctx):
    """One selected scientific tool (the old ``execute`` ending in ``services.execute_tool``): invalid arguments are
    returned as an invalid outcome with their feedback; the others go to the A110 ``ToolRegistry`` with the
    ``permitted_record_refs`` the action added for ``partner.*``, ``chemistry.*`` and ``source.locate``."""
    from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.domain import (
        identity, validate_schema)
    registry = ToolRegistry(ctx.store, **ctx.settings['tool_registry'])
    name, tool_arguments, scope = arguments['name'], arguments['arguments'], arguments['scope']
    try:
        entries = {key: value for key, value in registry.catalog(scope).items() if key in arguments['selected']}
        if name not in entries:
            raise ContractError('scientific_operation_unavailable')
        validate_schema(tool_arguments, entries[name]['input_schema'])
    except ContractError as error:
        return {'status': 'invalid', 'operation_ref': identity('operation', {'key': ctx.operation_key, 'name': name}),
                'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': str(error),
                             **({'detail': error.detail} if getattr(error, 'detail', None) else {})}}
    kwargs = {'permitted_record_refs': arguments['permitted_record_refs']} if 'permitted_record_refs' in arguments \
        else {}
    return await registry.execute_async(name, tool_arguments, scope=scope, operation_key=ctx.operation_key, **kwargs)


def process_revise(arguments, ctx):
    """The old ``process.revise`` (``ScientificScientificOperations.execute`` with ``_proposed_selection``): prepare a
    different thought pattern and selected tools for a new child; changes no current process and starts no child.

    BLOCKED, not placed: ``tool_library.resolve_tool_info``, ``validate_child_selection``, ``scientific_digest``,
    ``scientific_invocation_ref`` and ``validate_revision_origin`` (the old ``biochemical_feasibility_evidence_records``
    and the tool library: ``none``). Wanted calls: ``proposed = selection with arguments['thought_pattern'] and
    tool_library.resolve_tool_info(arguments['child_tool_info'], catalog)``; ``child_selection =
    validate_child_selection({'parent_selection_sha256': scientific_digest(selection), 'selection': proposed})``;
    ``origin = validate_revision_origin({'parent_invocation_ref': scientific_invocation_ref(run_id, path),
    'preparation_operation_ref': identity('operation', {...})})``."""
    _not_placed('tool_library.resolve_tool_info')


def process_execution(arguments, ctx):
    """The old ``process.execution`` read (``execution_planning.read``).

    BLOCKED, not placed: the old ``execution_planning`` module (``read`` and ``catalog``) has no module."""
    _not_placed('execution_planning.read')


def write_interpretation(arguments, ctx):
    """The model's interpretation of what the investigation has established so far (the old ``report_update`` of every
    decision, now the outcome of a tool unit: the summary holds the latest and ``final_to_parent`` returns it). The
    sources it names are asked of custody here; a source the episode does not hold makes this unit an invalid
    outcome (it still enters the iterator, and earns nothing by itself)."""
    held = {reference: ctx.store.holds(reference) for reference in arguments['source_refs']}
    status = 'completed' if all(held.values()) else 'invalid'
    return {'status': status, 'interpretation': arguments['interpretation'],
            'qualification': arguments['qualification'], 'source_refs': list(arguments['source_refs']),
            'source_held': held}


def reason(arguments, ctx):
    """One typed reasoning commit (the old ``reason`` action: ``store.commit_reasoning(payload, scope, key)``). The
    system owns the account owner; the operation key makes the commit idempotent. A payload that names a record the
    episode does not hold is returned as an invalid outcome."""
    try:
        result = ctx.store.commit_reasoning(arguments['commit'], arguments['scope'], ctx.operation_key)
    except CustodyError as error:
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'errors': [], 'notices': [],
                'conflicts': [], 'aliases': {}, 'error_code': 'record_not_held', 'feedback': {'detail': str(error)}}
    return result


def _knowledge(name, arguments, ctx):
    return ToolKnowledge(ctx.settings['knowledge_directory']).execute(name, arguments)


def knowledge_search(arguments, ctx):
    return _knowledge('knowledge.search', arguments, ctx)


def knowledge_entry(arguments, ctx):
    return _knowledge('knowledge.entry', arguments, ctx)


def knowledge_read(arguments, ctx):
    return _knowledge('knowledge.read', arguments, ctx)


TOOLS = {'process_entry': process_entry, 'received_evidence': received_evidence, 'tool_catalog': tool_catalog,
         'scientific_tool': scientific_tool, 'process_revise': process_revise,
         'process_execution': process_execution, 'write_interpretation': write_interpretation,
         'reason': reason, 'knowledge_search': knowledge_search, 'knowledge_entry': knowledge_entry,
         'knowledge_read': knowledge_read}


# ------------------------------------------------------------------------- what the model may select

_THOUGHT_REF = obj({'version': {'const': 'biochemical_feasibility_evidence_option_ref_v1'},
                    'library_id': {'type': 'string', 'pattern': '^[a-f0-9]{64}$'},
                    'slot': {'const': 'thought_pattern'},
                    'option_id': {'type': 'string', 'pattern': '^P[0-9]+$'},
                    'entry_sha256': {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}})
_TOOL_SELECTOR = obj({'name': _TEXT, 'resources': {'enum': ['api', 'local', 'hpc']}})
# The old ``_REVISION_ARGUMENTS``.
REVISION_ARGUMENTS = obj({'thought_pattern': _THOUGHT_REF,
                          'child_tool_info': {'type': 'array', 'items': _TOOL_SELECTOR, 'uniqueItems': True}})
SOURCE_REFS = {'type': 'array', 'items': _REF, 'uniqueItems': True}

TOOL_DEFINITIONS = {
    'process_entry': ('The selected evidence axis entry, thought pattern entry and selected tools, resolved.',
                      obj({})),
    'received_evidence': ('The received component-axis evidence: scoring sheets, received reports, native '
                          'components with their execution findings, prepared HPC assignments, qualifications.',
                          obj({})),
    'tool_catalog': ('The operand schemas of the selected scientific tools. Read them before calling a tool.',
                     obj({})),
    'scientific_tool': ('Run one selected scientific tool with the exact arguments of its operand schema '
                        '(arguments is a JSON object).', obj({'name': _TEXT, 'arguments': {'type': 'object'}})),
    'process_revise': ("Prepare a different thought pattern and/or selected actual tools for a new child "
                       "investigating the same evidence axis. Returns its selection for a separately selected "
                       "child commission; copy result.selection and revision_origin into that child's "
                       "assignment. Changes no current process, starts no child and records no biological "
                       "observation. Select the actual tool/resource choices from the selected entries.",
                       REVISION_ARGUMENTS),
    'process_execution': ('Read the execution planning information of the process.', {'type': 'object'}),
    'write_interpretation': ('Write your current interpretation of what the investigation has established, the '
                             'qualification of what it leaves unresolved, and the sources it rests on. Keep the '
                             'evidence, conditions, uncertainty and unknowns explicit.',
                             obj({'interpretation': _TEXT, 'qualification': _TEXT, 'source_refs': SOURCE_REFS})),
    'reason': ('Commit one typed scientific interpretation (a reasoning commit): commit matches '
               'reasoning_commit_schema. A request with every list empty is refused unless evidence_processing '
               'says no_applicable_evidence.',
               obj({'commit': {'type': 'object'}, 'evidence_processing': {'type': 'object'}}, required=['commit'])),
}


def _facts(slot):
    return {'type': 'array', 'items': {'type': 'string', 'enum': list(SELECTABLE[slot])}, 'uniqueItems': True}


def _child(slot, properties, required, description):
    schema = obj({'objective': _TEXT, 'purpose': _TEXT, **properties, 'facts': _facts(slot)},
                 required=['objective', 'purpose', *required])
    return (description, schema)


# The monitor is commissioned on a job this episode holds as outstanding: the model names the job by its held handoff
# reference and says what the monitor may observe of it; no text of the model passes to the monitor.
MONITOR_FIELDS = (*JOB_PROGRESS_FIELDS, 'log_windows')
MONITOR_DESCRIPTION = (
    'Commission one check of the progress of a job you hold as outstanding: handoff_ref (the handoff reference of '
    'one job of outstanding_jobs) and requested_fields (what the monitor may observe of it). This parent requests '
    'information; it never polls here. It returns its credit, what it found of the job (its state, whether its '
    'results are available) and its check records; facts selects its measurements.')


def monitor_arguments(jobs):
    return obj({'handoff_ref': {'enum': [job['handoff_ref'] for job in jobs]},
                'requested_fields': {'type': 'array', 'items': {'enum': list(MONITOR_FIELDS)}, 'uniqueItems': True},
                'facts': _facts('monitor')}, required=['handoff_ref', 'requested_fields'])


CHILD_DEFINITIONS = {
    'launch': _child('launch', {
        'assignment': obj({'requests': {'type': 'object'}, 'immutable_input_versions': {'type': 'array'},
                           'constraints': {'type': 'object'}, 'launch_instructions': {'type': 'object'},
                           'received_handoff_resources': _STRINGS},
                          required=['requests', 'immutable_input_versions', 'constraints']),
        'input_refs': _REFS}, ['assignment'],
        'Commission the launch of concrete execution requests on explicit resource ids; it returns the original '
        'handoff records. input_refs are the records the job inputs name, held by this episode.'),
    'results': _child('results', {
        'handoff_ref': _REF, 'selector': {'type': 'object'},
        'resource_kind': {'enum': ['local', 'hpc']}}, ['handoff_ref', 'selector', 'resource_kind'],
        'Commission the acquisition of the original selected execution results through the original handoff '
        'record this episode holds.'),
    'hpc': _child('hpc', {
        'commission_id': _TEXT, 'commission_source_ref': _REF, 'tool_request': {'type': 'object'},
        'input_refs': _REFS}, ['input_refs'],
        'Commission HPC work planning for a commission (exactly one of commission_id and commission_source_ref); '
        'input_refs are the records the planned jobs read.'),
    'literature': _child('literature', {
        'question_context_refs': _REFS, 'source_refs': _REFS, 'received_record_refs': _REFS},
        ['question_context_refs', 'source_refs', 'received_record_refs'],
        'Commission a published-evidence assessment of source records this episode holds; received_record_refs '
        'name every record its code reads (the sources, their artifacts, the sources they derive from and the '
        'records giving the question context).'),
    'biochemical_feasibility_evidence': _child('biochemical_feasibility_evidence', {
        'assignment': obj({'selection': {'type': 'object'}, 'evidence_refs': _REFS, 'constraints': {'type': 'object'},
                           'context': {'type': 'object'}, 'revision_origin': {'type': 'object'}},
                          required=['selection', 'evidence_refs', 'constraints']),
        'received_record_refs': _REFS}, ['assignment'],
        'Commission a recursive A110 investigation with its own thought pattern and tool selection (copy the '
        'selection and revision_origin that process_revise returned). The proposed annotation, scope and context '
        'are inherited.'),
}


def offered(ctx):
    """The actions this decision offers: every tool (the knowledge lookups when a knowledge directory is set) and the
    child slots the settings configure."""
    settings = ctx.settings
    slots = list(settings['child_roles'])
    if 'biochemical_feasibility_evidence' not in slots or any(slot not in CHILD_SLOTS for slot in slots):
        raise ContractError('scientific_child_roles_invalid')
    tools = [name for name in TOOL_DEFINITIONS]
    if 'knowledge_directory' in settings:
        tools.extend(definition['name'].replace('.', '_') for definition in knowledge_catalog())
    return tools + slots


def commissionable(names, jobs):
    """The offered actions that can be selected now: the monitor only while a job is outstanding (its commission
    names one by its held handoff reference)."""
    return [name for name in names if name != 'monitor' or jobs]


def argument_schema(name, jobs):
    if name == 'monitor':
        return monitor_arguments(jobs)
    if name in TOOL_DEFINITIONS:
        return TOOL_DEFINITIONS[name][1]
    if name in CHILD_DEFINITIONS:
        return CHILD_DEFINITIONS[name][1]
    for definition in knowledge_catalog():
        if definition['name'].replace('.', '_') == name:
            return definition['input_schema']
    raise LookupError('unknown_action:' + name)


def describe(name):
    if name == 'monitor':
        return MONITOR_DESCRIPTION
    if name in TOOL_DEFINITIONS:
        return TOOL_DEFINITIONS[name][0]
    if name in CHILD_DEFINITIONS:
        return CHILD_DEFINITIONS[name][0]
    return next(definition['description'] for definition in knowledge_catalog()
                if definition['name'].replace('.', '_') == name)


def output_schema(names):
    return {'type': 'object', 'additionalProperties': False, 'required': ['selection', 'arguments_json'],
            'properties': {'selection': {'type': 'string', 'enum': list(names),
                                         'description': 'The one action of this decision.'},
                           'arguments_json': {'type': 'string',
                                              'description': 'The arguments of the action as a JSON object text.'}}}


# ----------------------------------------------------------------------------------------------- deciding

def compose_instructions(ctx):
    """The old ``compose_instructions`` for an instruction-version axis: the specialist text replaces the default
    runtime instructions (``replaces_default_instructions``), then the reasoning commit requirement, the tool
    knowledge instructions and the launch library instructions. The pending-child redelivery, wait, native-event and
    decision-exchange paragraphs describe actions that no longer exist and are not carried."""
    instructions = (scientific_guidance() + _TASK_TEXT)
    instructions += '\n' + REASONING_COMMIT_REQUIREMENT
    if 'knowledge_directory' in ctx.settings:
        instructions += KNOWLEDGE_INSTRUCTIONS
    if 'launch_instruction_directory' in ctx.settings:
        instructions += LAUNCH_INSTRUCTIONS
    return instructions + ACTION_ANSWER


# The old ``ScientificGoal.instructions`` (instruction-version branch), second and third paragraphs; the wait and
# the report-form sentences of the old text are not carried.
_TASK_TEXT = (
    'Choose an available tool action, commit a scientific interpretation through the reasoning action, or '
    'commission a scoped child with its own typed return. Use only the selected actual tools and their supplied '
    "resource instructions; choose callable operands through the declared response contract. Preserve the parent's "
    'exact requested result meanings and allowed values. Recorded facts come from actual records. Keep inherited '
    'information distinct from new findings and completed work distinct from attempts. Return valid partial '
    'findings and specific failures.\n\n'
    'Keep the assigned evidence axis, thought pattern and selected tools for this episode. process_revise prepares '
    'a different thought pattern and/or tool selection for a new child; it does not change this episode or start '
    'that child. To commission that alternative, copy its selection and revision_origin into a separately selected '
    "child assignment with the child's job, scope, constraints and typed return. Children own their iterative "
    'choices. The configured controller owns continuation.')

_CHILD_RETURNS = (
    "Choose each child's return facts to carry the evidence needed for your question. committed_record_refs "
    'carries the acquired scientific record references; select the provider\'s coverage/completeness facts when '
    'interpreting acquired rows or an empty result. A job handle, usable handoff or null failure field alone does '
    'not return the search data. Keep a completed empty acquisition distinct from partial or unavailable '
    'acquisition, and keep those acquisition facts separate from evidence for a biological function.'
    # Owner's grading decision (R19, ``task_decision._task`` at 97308b94c): a grading sheet's own criteria and status
    # are the result; no episode re-judges or re-thresholds a sheet that is already graded.
    ' Reporting does not require another supported/contradicted, function, path or scope verdict: use the grading '
    "sheet's existing criteria and status, without inventing a score threshold or asking a child to judge the same "
    'result again.')


def prompt_sections(summary, names):
    """The old TASK prompt (``task_decision._task``): the same sections in the same order, as structured values (the
    text helpers of the old shared presentation library are not placed). Nothing is shown that the episode does not
    have: an empty section is left out."""
    entry = summary['entry']
    axis, thought = entry['evidence_axis'], entry['thought_pattern']
    sections = [('Assigned work', summary['goal']), ('Fixed scope', summary['scope']),
                ('Parent constraints', summary['constraints']), ('Parent-supplied context', summary['context'])]
    if summary['evidence_refs']:
        sections.append(('Parent-selected evidence operands', summary['evidence_refs']))
    sections.append(('Investigate the supplied target: ' + axis.get('name', ''),
                     axis['investigation_instructions']))
    sections.append(('Reason about the evidence: ' + thought.get('name', ''),
                     {name: thought[name] for name in ('description', 'use_when') if name in thought}))
    for field, label in (('live_alternatives', 'Alternatives to distinguish'),
                         ('decision_guidance', 'How to choose and revise the investigation'),
                         ('outcome_contingencies', 'How outcomes affect the next choice'),
                         ('boundary', 'Limits of this reasoning approach')):
        if thought.get(field):
            sections.append((label, thought[field]))
    for tool in entry['child_tool_info']:
        sections.append(('Selected tool: ' + tool['name'] + ' (' + tool['resources'] + ')',
                         {'description': tool['description'], 'instructions': tool['instructions']}))
    sections.append(('Permitted child roles', [name for name in names if name in CHILD_SLOTS]))
    sections.append(('Evidence through child returns', _CHILD_RETURNS))
    sections.append(('Callable selection operands for child assignment (copy exact values)',
                     summary['selection']))
    return [{'title': title, 'content': content} for title, content in sections]


def decide(summary, feedback, ctx):
    if summary['entry'] is None:
        # The first part of the task: the selected entries, through the episode's own lookup.
        return ToolCall('process_entry', {})
    if summary['received'] is None:
        return ToolCall('received_evidence', {'record_refs': summary['record_refs'], 'scope': summary['scope']})
    jobs = summary['outstanding_jobs']
    names = commissionable(offered(ctx), jobs)
    progress = summary['investigation_progress']
    context = {
        'sections': prompt_sections(summary, names),
        'actions': [{'selection': name, 'description': describe(name), 'input_schema': argument_schema(name, jobs)}
                    for name in names],
        'requested_action_history': summary['actions'], 'last_local_outcome': summary['last_outcome'],
        'current_credit': progress['credit'],
        'investigation_progress': {key: progress[key] for key in
                                   ('retained_finding_count', 'inactive_dependencies', 'detail_pages')},
        'received_evidence': summary['received'], 'child_reports': summary['children'],
        'outstanding_jobs': [{name: job[name] for name in ('handoff_ref', 'job', 'resource_id', 'kind',
                                                             'submitted_at', 'latest_check')} for job in jobs],
        'interpretation': summary['interpretation'], 'reasoning_commit_schema': summary['reasoning_schema'],
        'time_accounting': time_accounting(ctx.clock.progress_time), 'feedback': feedback}
    if summary['action_yields'] is not None:
        context['action_yields'] = summary['action_yields']
    if 'knowledge_directory' in ctx.settings:
        context['tool_knowledge'] = ToolKnowledge(ctx.settings['knowledge_directory']).context()
    if 'launch_instruction_directory' in ctx.settings:
        library = LaunchInstructions(ctx.settings['launch_instruction_directory'])
        context['launch_instruction_library'] = library.context()
        # The sections the commissioner selected for this episode (the old ``episode_assignment`` of the request).
        selected = library.materialize(summary['message'].get('launch_instructions'))
        if selected is not None:
            context['selected_launch_instructions'] = selected
    return ModelRequest(MODEL_ROLE, compose_instructions(ctx), context, output_schema(names))


# ---------------------------------------------------------------------------------------------- choosing

_PERMITTED_RECORD_TOOLS = ('partner.', 'chemistry.')
_PERMITTED_RECORD_TOOL_NAMES = frozenset({'source.locate'})
_UNITS = {'launch': ('handoff_unit', 'acquired_record_unit'), 'monitor': ('information_unit',),
          'results': ('acquired_record_unit',)}
_NAMED = {'launch': ('input_refs',), 'results': ('handoff_ref',), 'hpc': ('input_refs',),
          'literature': ('question_context_refs', 'source_refs', 'received_record_refs')}


def _named_records(selection, arguments):
    """The records the model's arguments name, which this episode must hold."""
    named = []
    if selection == 'write_interpretation':
        named.extend(arguments['source_refs'])
    elif selection == 'biochemical_feasibility_evidence':
        named.extend(arguments['assignment']['evidence_refs'])
        named.extend(arguments.get('received_record_refs', []))
    elif selection == 'hpc':
        named.extend(arguments['input_refs'])
        if 'commission_source_ref' in arguments:
            named.append(arguments['commission_source_ref'])
    elif selection in _NAMED:
        for key in _NAMED[selection]:
            value = arguments.get(key, [])
            named.extend([value] if isinstance(value, str) else value)
    return named


def _check_commit(arguments, records):
    """The old ``reasoning_has_task_content`` path of ``apply_response``: a commit with every row list empty is
    refused unless it says there was no applicable evidence."""
    payload = arguments['commit']
    schema = records.reasoning_schema()
    if (set(schema.get('required', schema['properties'])) <= set(payload) <= set(schema['properties'])
            and all(value == [] for value in payload.values())
            and arguments.get('evidence_processing', {}).get('kind') != 'no_applicable_evidence'):
        raise ValueError('empty_reasoning_commit')


def action(response, summary, records, ctx):
    """Admit the model's selection. An invalid answer creates no unit: the model decides again with the feedback.
    A tool is called with its arguments and the scope (and, where the old runner supplied it, the permitted records
    and the selected tool names); a commission is called with the model's arguments and, for the three job
    children, the credit unit of that child from the settings."""
    names = commissionable(offered(ctx), summary['outstanding_jobs'])
    try:
        Draft202012Validator(output_schema(names)).validate(response)
        selection = response['selection']
        arguments = json.loads(response['arguments_json'])
        if not isinstance(arguments, dict):
            raise ValueError('arguments_json_must_encode_an_object')
        Draft202012Validator(argument_schema(selection, summary['outstanding_jobs'])).validate(arguments)
        if selection == 'reason':
            _check_commit(arguments, records)
        for reference in _named_records(selection, arguments):
            if not records.holds(reference):
                raise ValueError('record_not_held:' + reference)
    except (ValidationError, ValueError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    if selection == 'reason' or selection == 'process_revise':
        injected = {'scope': summary['scope']}
        if selection == 'process_revise':
            injected['selection'] = summary['selection']
        return ToolCall(selection, {**arguments, **injected})
    if selection == 'received_evidence':
        return ToolCall(selection, {'record_refs': summary['record_refs'], 'scope': summary['scope']})
    if selection == 'tool_catalog':
        return ToolCall(selection, {'scope': summary['scope'], 'names': _selected_tool_names(summary)})
    if selection == 'scientific_tool':
        injected = {'scope': summary['scope'], 'selected': _selected_tool_names(summary)}
        if arguments['name'].startswith(_PERMITTED_RECORD_TOOLS) or arguments['name'] in _PERMITTED_RECORD_TOOL_NAMES:
            injected['permitted_record_refs'] = list(summary['record_refs'])
        return ToolCall(selection, {**arguments, **injected})
    if selection in TOOLS:
        return ToolCall(selection, arguments)
    units = {unit: ctx.settings[unit] for unit in _UNITS.get(selection, ())}
    return ChildCall(selection, {**arguments, **units})


def _selected_tool_names(summary):
    return [tool['name'] for tool in summary['selection']['child_tool_info']]
