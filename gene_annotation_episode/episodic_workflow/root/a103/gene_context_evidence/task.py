"""The task: the A103 head's investigation. Look up the selected process (the evidence axis and thought pattern
entries) and the callable tool catalog, then choose one operation per unit: a lookup, a tool operation of the selected
tools (the A103 context measurements among them), the grading of held measurements (``context.grade``), a reasoning
commit, the preparation of a revised selection, or a child commission.

Carried from the old ``task.py``, ``task_state.py``, ``decision_delivery.py``, ``decision_presentation.py``,
``operations.py``, ``instructions.py``, ``tool_policy.py``, ``child_policy.py`` and ``internal_summary.py``. One unit is
one model-selected operation or one child commission. The task always offers a unit and never ends the Episode: only
the yield controller does (the old ``wait`` and ``redeliver_report`` actions, the decision exchange, the saved
exchanges and the checkpoints are the old runner's and are not carried). A reasoning commit that carries no proposed
row is rejected as it was (``empty_reasoning_commit``). This file is a private copy: it imports nothing from another
episode.

Grading. The old runner graded every received or published A103 measurement automatically after each outcome
(``automatic_score_updates``: the attachment refresh of the A103 registry). Here that is the ``context_grade`` tool
(``context.grade``): ``attachments.refresh`` over the records this Episode holds writes one attachment sheet
(``a103_tool_attachment_v1``) per held measurement and policy, and the context observation of each scored sheet. It
runs without a model decision as the next unit whenever a held measurement has no sheet yet (the old automatic
grading), and the model may select it. The old prose ``report`` tool is gone: the finding is the controlled features
code reads from the sheets (``findings.gene_context_evidence.investigation_finding``), built in ``internal_summary``.

The old model-facing operation names are kept (``process.search``, ``knowledge.read``, ``process.revise``, ``reason``,
and the registry's own dotted tool names); a tool of ``TOOLS`` has no dot in its name, so ``action`` maps one to the
other. The old common tools of the old runner (``episode.history``, ``episode.credit``, ``episode.annotation_score``,
``episode.monitoring_information``, ``episode.estimate_wait`` and the ``shared.*`` information exchange) are system
machinery (the episode's own history is ``view.outcomes``; credit and progress are the system's; the shared exchange had
no owner in the episode) and are not offered; ``process.execution`` (``execution_planning``) and the ``process.tools``
retrieval of ``scientific_tool_retrieval`` have no module in the library: ``process_tools`` lists the configured tool
library instead (its ``parent_tool_info``).

Settings the episode reads (``ctx.settings``): ``library_directory`` (the frozen A/P option library),
``tool_library_directory`` (the frozen tool library), ``knowledge_library_directory`` and ``launch_instruction_directory``
(optional, shown to the model when set), ``tool_registry`` (the keyword values of the ``A103ToolRegistry``, with its
``a103_work_directory`` under ``runs/`` and the caller's ``target_genomic_sources``), ``child_values`` (per child slot
the values its form needs and the old configuration held) and ``yield_bindings`` (``yield_estimator.py``)."""
import json

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.configuration.gene_context_evidence.process_options import (
    GeneContextEvidenceLibrary, catalog as process_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.gene_context_evidence.evidence_axis_instructions import (
    instruction_view)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.gene_context_evidence import (
    literature_investigation_prompt)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.construction_records import (
    CHILD_SELECTION_VERSION, REVISION_ORIGIN_VERSION, SELECTION_VERSION, scientific_digest,
    scientific_invocation_ref, selector_selection, validate_child_selection, validate_revision_origin)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import (
    identity, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.records.read_mapping_values import (
    parameter_schema_failure)
from gene_annotation_episode.episodic_workflow.episode_support.findings.gene_context_evidence.investigation_finding import (
    EVIDENCE_TYPES)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.attachments import refresh
from gene_annotation_episode.episodic_workflow.episode_support.tools.gene_context_evidence.evidence_operations import (
    A103ToolRegistry)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_catalog import ScientificToolLibrary
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge, catalog as knowledge_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

from .goal import GOAL

# The head's seven slots: the recursive head (the old role ``gene_context_evidence``), the monitor (the old role
# ``monitor``) and the execution, HPC and resource children the old ``episode.py`` factories built. A103 has no
# literature child.
CHILD_SLOTS = {
    'gene_context_evidence': 'gene_context_evidence',
    'execution_job_submission': 'gene_context_evidence/execution_job_submission',
    'execution_progress_assessment': 'gene_context_evidence/execution_progress_assessment',
    'execution_result_acquisition': 'gene_context_evidence/execution_result_acquisition',
    'hpc_work_planning': 'gene_context_evidence/hpc_work_planning',
    'resource_work_submission': 'gene_context_evidence/resource_work_submission',
    'resource_result_acquisition': 'gene_context_evidence/resource_result_acquisition',
}
SERVICES = ()
# The monitor slot. Its commission is controlled values only: the handoff record of one outstanding job this episode
# holds, what the monitor may observe of it (the monitor's own ``requested_fields`` options) and the measurements to
# return (the monitor's selectable fields; its credit, finding and check rows are always returned).
MONITOR = 'execution_progress_assessment'
MONITOR_FIELDS = ('execution_status', 'result_available', 'measurements', 'log_windows')
MONITOR_RETURN_FIELDS = ('job_returncode', 'job_duration_seconds', 'job_elapsed_seconds', 'stdout_bytes',
                         'stderr_bytes', 'log_window_refs', 'event_receipt_refs')

# The old ``_COMMON_TOOLS`` and ``process.revise``: a selected tool of the tool library may not reuse one of these
# names (the old ``scientific_primitive_uses_common_tool_name``).
RESERVED_NAMES = ('process.search', 'process.entry', 'process.sources', 'process.tools', 'knowledge.search',
                  'knowledge.entry', 'knowledge.read', 'episode.history', 'episode.credit',
                  'episode.annotation_score', 'episode.monitoring_information', 'episode.estimate_wait',
                  'shared.request_information', 'shared.publish_information', 'shared.resolve_information_need',
                  'shared.read_information', 'shared.list_information', 'process.revise')
LOOKUPS = {'process.search': 'process_search', 'process.entry': 'process_entry', 'process.sources': 'process_sources',
           'process.tools': 'process_tools', 'knowledge.search': 'knowledge_search',
           'knowledge.entry': 'knowledge_entry', 'knowledge.read': 'knowledge_read'}
KNOWLEDGE = ('knowledge.search', 'knowledge.entry', 'knowledge.read')
THOUGHT_FIELDS = ('id', 'name', 'description', 'use_when', 'live_alternatives', 'decision_guidance',
                  'outcome_contingencies', 'boundary')
# The fields of each child's assignment that are ``record_refs`` fields of the child's form: the parent names them, and
# the model's answer may only name records this episode holds (the provisional held-record check of ``action``).
RECORD_REFS = {
    'gene_context_evidence': ('evidence_refs', 'scope_refs'),
    'execution_job_submission': ('record_refs',),
    'execution_progress_assessment': (),
    'execution_result_acquisition': ('handoff_ref', 'initial_result_refs', 'initial_result_artifact_refs'),
    'hpc_work_planning': ('commission_source_ref', 'input_refs'),
    'resource_work_submission': ('scope_refs', 'input_refs'),
    'resource_result_acquisition': (),
}
# What the model writes in ``assignment`` for each child (the parent's own text; the child's form admits or refuses it).
CHILD_ASSIGNMENTS = {
    'gene_context_evidence': 'a narrower A103 investigation: {"selection": <gene_context_evidence_selection_v3 record: '
                             'the result.selection of process.revise, or the text "own" for your own selection>, "evidence_refs": [<records you '
                             'hold and hand on, with every record they name that the child reads>], "constraints": '
                             '{...}, "context": {...optional evidence_task and a103_task...}, "scope": <a scope '
                             'within yours>, "scope_refs": [<the records the scope names>], "revision_origin": '
                             '<revision_origin of process.revise, optional>}; your proposed annotation is inherited',
    'execution_job_submission': 'the launch of execution work: {"version": "execution_launch_assignment_v1", '
                                '"requests": {<resource_id>: <closed concrete request>}, '
                                '"immutable_input_versions": [...], "constraints": {allowed_resource_ids, '
                                'allowed_kinds, resource_id, kind}, "launch_instructions": {...optional...}, '
                                '"record_refs": [<every record the job inputs name>], "scope": {...optional...}, '
                                '"scientific_task": {...optional...}, "received_handoff_resources": [...optional...]}',
    'execution_progress_assessment': 'one check of an outstanding job you hold (one monitor visit). Its operands are '
                                     'not those of the other children: exactly {"handoff_ref": <the handoff_ref of '
                                     'one of the outstanding jobs>, "requested_fields": [<what the monitor may '
                                     'observe: execution_status, result_available, measurements, log_windows>], '
                                     '"select": [<the measurements you want returned: job_returncode, '
                                     'job_duration_seconds, job_elapsed_seconds, stdout_bytes, stderr_bytes, '
                                     'log_window_refs, event_receipt_refs>]}; no objective, purpose or assignment. '
                                     'It returns its credit, the state of the job and whether its results are '
                                     'available, with its check records',
    'execution_result_acquisition': 'the acquisition of results: {"version": <the results assignment version>, '
                                    '"handoff_ref": [<the one original handoff record>], "selector": {...}, '
                                    '"resource_kind": "local"|"hpc"|"api", "workspace": <absolute path>, '
                                    '"initial_result_refs": [...optional...], "initial_result_artifact_refs": '
                                    '[...optional...]}',
    'hpc_work_planning': 'the planning and execution of HPC work: {"commission_id": <a configured commission> or '
                         '"commission_source_ref": [<one held source>] (exactly one of the two), "tool_request": '
                         '{name, resources, arguments_json, result_reader, objective} (optional), "scope": {...}, '
                         '"input_refs": [...optional...]}',
    'resource_work_submission': 'the submission of resource work: {"version": "resource_launch_assignment_v1", '
                                '"job_request": {...}, "immutable_input_versions": [...], "constraints": {...}, '
                                '"resource_selection": {...optional...}, "software_knowledge_refs": [...], '
                                '"resource_knowledge_refs": [...], "launch_instructions": {...optional...}, '
                                '"scope": {...}, "scope_refs": [...], "input_refs": [...]}',
    'resource_result_acquisition': 'the acquisition of resource work results: {"version": <the results assignment '
                                   'version>, "handoff": <the execution_handoff_v1 record>, '
                                   '"requested_data_selector": {...}}',
}
TOOL_INSTRUCTION = (
    'Select one operation per answer: give its name in operation and its operands as JSON text in arguments_json. '
    'A lookup or a tool operation takes the operands of its entry in the callable operations. Commit a scientific '
    'interpretation with reason, whose operands are {"commit": <the reasoning payload>} (with '
    '"evidence_processing": {"kind": "no_applicable_evidence", ...} only where a source-grounded declaration of no '
    'applicable evidence is the finding). process.revise takes {"thought_pattern": <option ref>, "child_tool_info": '
    '[{"name": ..., "resources": ...}]}: it prepares a selection for a new child and changes no current process. A '
    'child operation takes {"objective": <what the child should do, as text>, "purpose": <what you use its return '
    'for>, "assignment": <the typed assignment of that child, below>, "select": [<the optional fact sources you want '
    'returned>]}. Name every record a child will read in its assignment: a passed record does not bring the records '
    'it names. execution_progress_assessment, offered while you hold an outstanding job, takes its own operands, '
    'given with it. Only the numerical controller decides when your work ends. The host executes your selected '
    'action.')

# The A103 grader: what the attachment sheet is, how it is filled, and what the credit reads from it (the sheet's
# meaning comes from the library: the attachment policies, the credit projector's own record).
# Owner (gene_context_evidence_prompt.py at 97308b94c, lines 257-260): "return their actual saved grading results,
# numerical status, qualifications and missing inputs. Reporting does not require another supported/contradicted,
# function, path or scope verdict: use the grading sheet's existing criteria and status, without inventing a score
# threshold or asking a child to judge the same result again."
GRADING_SECTION = (
    '\n\nA103 grading (operation context.grade, sheet a103_tool_attachment_v1). Every native context measurement '
    '(context.bind_locus, reference.neighborhood, context.compare_neighborhoods, context.fusion, '
    'context.cooccurrence, context.association_channels, context.contrast, context.detection_inventory) is graded '
    'when it is published or received: context.grade writes one attachment sheet per held measurement, attributing '
    'it to the target through the actual locus binding, the specific components and the sampling panel; a scored '
    'sheet also publishes a context observation (measurement context_association_index) of the target. The sheet '
    'policies, each its own evidence type: ' + ', '.join(sorted(EVIDENCE_TYPES)) + '. A locus binding or a single '
    'measured neighborhood earns no association score; a functional contrast adds no second copy of context credit. '
    'Missing operands stay listed on the sheet as missing; an unknown flank or an unevaluated detection is not '
    'absence. The credit is the maximum attached score per region cell of the assigned scope, length-weighted, '
    'counted only for sheets whose context observation a current assessment of yours links to the proposed '
    'annotation (commit it with reason: hypothesis_ref the proposed annotation, observation_ref the context '
    'observation; a whole commit is {"commit": {"structural_proposals": [], "terms": [], "source_subjects": [], '
    '"observations": [], "hypotheses": [], "annotation_updates": [], "assessments": [{"alias": "context_link", '
    '"expected_revision": 0, "hypothesis_ref": <the proposed annotation>, "observation_ref": <the context '
    'observation>, "relation": "strengthens" or "weakens", "applicability": "direct", "extent_basis": '
    '"observed_extent", "condition_refs": [], "assumption_refs": []}]}}). Use the grading sheet\'s existing criteria and status, without inventing a score threshold or '
    'asking a child to judge the same result again. What returns to your parent is your credit and the features '
    'code reads from the sheets you hold (evidence type, attachment state, score bounds, missing operand count, '
    'target link) with the sheets\' references; no text of yours is returned.')


GRADE_ENTRY = {'name': 'context.grade', 'description': 'Grade every held A103 context measurement of the assigned '
               'targets into its attachment sheet (a103_tool_attachment_v1); operands {}',
               'input_schema': {'type': 'object', 'properties': {}, 'additionalProperties': False}}


def instructions(*, knowledge, launch):
    """The old ``instructions.instructions`` for a published-instruction axis: this episode's goal replaces the default
    text (``replaces_default_instructions``), then the reasoning-commit requirement, the A103 grading section, the
    tool-knowledge text and the launch-instruction text when they are offered. The old paragraphs about
    ``redeliver_report``, the in-process wait, the native event targets and the exchange protocol described actions
    that no longer exist."""
    text = GOAL + '\n' + literature_investigation_prompt.REASONING_COMMIT_REQUIREMENT + GRADING_SECTION
    if knowledge is not None:
        text += KNOWLEDGE_INSTRUCTIONS
    if launch is not None:
        text += LAUNCH_INSTRUCTIONS
    return text + '\n\n' + TOOL_INSTRUCTION


# -- tools -----------------------------------------------------------------------------------------------------

def process_library(arguments, ctx):
    """The first lookup: the evidence axis and thought pattern entries the selection pins, resolved against the frozen
    option library (the old ``_selection`` resolution; a legacy support-metadata axis entry is not an instruction entry
    and ``instruction_view`` raises). The selected tools' information comes with the selection."""
    selection = arguments['selection']
    library = GeneContextEvidenceLibrary(ctx.settings['library_directory'])
    axis, thought = library.resolve(selection['evidence_axis']), library.resolve(selection['thought_pattern'])
    return {'status': 'completed', 'library': library.as_record(), 'selection': selector_selection(selection),
            'evidence_axis': instruction_view(axis),
            'thought_pattern': {name: thought[name] for name in THOUGHT_FIELDS if name in thought},
            'child_tool_info': selection['child_tool_info']}


def _library_lookup(name, arguments, ctx):
    return GeneContextEvidenceLibrary(ctx.settings['library_directory']).execute(name, arguments['arguments'])


def process_search(arguments, ctx):
    return _library_lookup('process.search', arguments, ctx)


def process_entry(arguments, ctx):
    return _library_lookup('process.entry', arguments, ctx)


def process_sources(arguments, ctx):
    return _library_lookup('process.sources', arguments, ctx)


def _knowledge_lookup(name, arguments, ctx):
    return ToolKnowledge(ctx.settings['knowledge_library_directory']).execute(name, arguments['arguments'])


def knowledge_search(arguments, ctx):
    return _knowledge_lookup('knowledge.search', arguments, ctx)


def knowledge_entry(arguments, ctx):
    return _knowledge_lookup('knowledge.entry', arguments, ctx)


def knowledge_read(arguments, ctx):
    return _knowledge_lookup('knowledge.read', arguments, ctx)


def _available(registry, scope):
    """The registry's catalog as the list the tool library compares selections with (the old
    ``services.tool_catalog(scope)``)."""
    return [{'name': name, **entry} for name, entry in registry.catalog(scope).items()]


def tool_catalog(arguments, ctx):
    """The second lookup: the operations of the selected tools with a direct route, resolved through the frozen tool
    library against what the registry offers for the scope (the old ``catalog``/``_tool_resolution``)."""
    registry = A103ToolRegistry(ctx.store, **ctx.settings['tool_registry'])
    library = ScientificToolLibrary(ctx.settings['tool_library_directory'])
    resolved = library.resolve_invocations(arguments['selection']['child_tool_info'],
                                           _available(registry, arguments['scope']))
    if any(entry['name'] in RESERVED_NAMES for entry in resolved):
        raise ContractError('scientific_primitive_uses_common_tool_name')
    direct = [row for row in resolved if row.get('invocation_route', {'kind': 'direct'})['kind'] == 'direct']
    return {'catalog': [{key: value for key, value in row.items() if key not in {'instructions', 'invocation_route'}}
                        for row in direct]}


def process_tools(arguments, ctx):
    """The tools the frozen tool library offers for a new child's selection (what ``process.revise`` takes)."""
    registry = A103ToolRegistry(ctx.store, **ctx.settings['tool_registry'])
    library = ScientificToolLibrary(ctx.settings['tool_library_directory'])
    return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'feedback': None,
            'result': {'child_tool_info': library.parent_tool_info(_available(registry, arguments['scope']))}}


def process_revise(arguments, ctx):
    """The old ``process.revise``: prepare a different thought pattern and/or tool selection for a new child. It
    returns the child selection and its ``revision_origin`` and starts nothing; the model copies both into a child
    assignment. An invalid proposal is an ``invalid`` outcome."""
    selection, revision, scope = arguments['selection'], arguments['revision'], arguments['scope']
    try:
        registry = A103ToolRegistry(ctx.store, **ctx.settings['tool_registry'])
        library = ScientificToolLibrary(ctx.settings['tool_library_directory'])
        proposed = {'version': SELECTION_VERSION, 'evidence_axis': selection['evidence_axis'],
                    'thought_pattern': revision['thought_pattern'],
                    'child_tool_info': library.resolve_tool_info(revision['child_tool_info'],
                                                                 _available(registry, scope))}
        child_selection = validate_child_selection({'version': CHILD_SELECTION_VERSION,
                                                    'parent_selection_sha256': scientific_digest(selection),
                                                    'selection': proposed})
        operation_ref = identity('operation', {'key': ctx.operation_key, 'name': 'process.revise',
                                               'arguments': revision})
        origin = validate_revision_origin({
            'version': REVISION_ORIGIN_VERSION,
            'parent_invocation_ref': scientific_invocation_ref(ctx.run_id, [[ctx.binding_path, ctx.episode_id]]),
            'preparation_operation_ref': operation_ref})
    except ValueError as error:
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': str(error),
                             **({'detail': error.detail} if getattr(error, 'detail', None) else {})}}
    return {'status': 'completed', 'operation_ref': operation_ref, 'record_refs': [], 'changed_record_refs': [],
            'result': child_selection, 'revision_origin': origin, 'feedback': None}


def _invalid(name, key, arguments, error):
    detail = {'detail': error.detail} if getattr(error, 'detail', None) else {}
    return {'status': 'invalid', 'operation_ref': identity('operation', {'key': key, 'name': name,
                                                                         'arguments': arguments}),
            'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'category': 'arguments_or_reference', 'code': str(error), **detail}}


async def operation(arguments, ctx):
    """One operation of a selected tool of the A103 registry (the old ``execute``): the tool is one the catalog
    offered, ``sequence.align`` is refused (the old ``tool_policy``: a new sequence comparison goes through the shared
    parent), the operands fit the offered schema. A violation, or a failed operation, is the unit's own outcome."""
    name, operands, scope = arguments['name'], arguments['operands'], arguments['scope']
    try:
        if name == 'sequence.align':
            raise ContractError('a103_new_sequence_comparison_requires_shared_parent')
        validate_schema(operands, arguments['input_schema'])
    except (ContractError, ValueError) as error:
        failure = None
        if name == 'reads.map':
            for schema_error in Draft202012Validator(arguments['input_schema']).iter_errors(operands):
                failure = parameter_schema_failure(schema_error)
                if failure is not None:
                    break
        outcome = _invalid(name, ctx.operation_key, operands, error)
        if failure is not None:
            outcome['feedback'].update(failure)
        return outcome
    registry = A103ToolRegistry(ctx.store, **ctx.settings['tool_registry'])
    # The records the source readers are bound to are the ones this episode holds (the old ``received_record_refs``).
    held = name.startswith('context.') or name in {'reference.neighborhood', 'result.blast.hsp', 'source.locate'}
    permitted = tuple(ctx.store.refs()) if held else None
    try:
        return await registry.execute_async(name, operands, scope=scope, operation_key=ctx.operation_key,
                                            permitted_record_refs=permitted)
    except CustodyError:
        raise
    except Exception as error:   # the old record_execution_failure: a failed selected operation is an outcome
        return failure_outcome(ctx.store, error, category='episode_execution', cause_code='selected_operation_failed')


def reason(arguments, ctx):
    """The old ``reason`` action: commit the reasoning payload into the Store under the commission's scope (every
    record the payload names must be held, or ``commit_reasoning`` raises ``CustodyError``). The Store's commit is
    idempotent on the operation key."""
    result = ctx.store.commit_reasoning(arguments['commit'], arguments['scope'], ctx.operation_key)
    return {'status': result['status'], 'errors': result['errors'], 'record_refs': result['record_refs'],
            **({'evidence_processing': arguments['evidence_processing']} if 'evidence_processing' in arguments
               else {})}


def context_grade(arguments, ctx):
    """``context.grade``: grade every held native A103 measurement of the commission's targets (the old automatic
    attachment refresh at publication and receipt): one attachment sheet per measurement and policy, and the context
    observation of each scored sheet, written through ``ctx.store``. The outcome names what was written and how many
    sheets still list missing operands; the sheets themselves are read by ``internal_summary``."""
    generated, needs = refresh(ctx.store, set(ctx.store.refs()), arguments['scope'])
    return {'status': 'completed', 'record_refs': generated, 'changed_record_refs': [],
            'result': {'graded_record_count': len(generated), 'sheets_with_missing_operands': len(needs)},
            'feedback': None}


TOOLS = {'process_library': process_library, 'tool_catalog': tool_catalog, 'process_search': process_search,
         'process_entry': process_entry, 'process_sources': process_sources, 'process_tools': process_tools,
         'knowledge_search': knowledge_search, 'knowledge_entry': knowledge_entry, 'knowledge_read': knowledge_read,
         'process_revise': process_revise, 'operation': operation, 'reason': reason,
         'context_grade': context_grade}


# -- deciding ------------------------------------------------------------------------------------------------------

def offered(summary, settings):
    """The model's operation names: the lookups (knowledge only when its library is configured), the registry
    operations of the catalog, ``context.grade``, ``process.revise``, ``reason`` and the child slots."""
    lookups = [name for name in LOOKUPS if name not in KNOWLEDGE or 'knowledge_library_directory' in settings]
    return [*lookups, *(entry['name'] for entry in summary['catalog']), 'context.grade', 'process.revise', 'reason',
            *offered_children(summary)]


def offered_children(summary):
    """The children this decision offers. The monitor is offered while this episode holds an outstanding job (a job
    ledger handoff row without its closure row): its commission names one of them."""
    return [slot for slot in CHILD_SLOTS if slot != MONITOR or summary['outstanding_jobs']]


def output_schema(names):
    return {'type': 'object', 'additionalProperties': False, 'required': ['operation', 'arguments_json'],
            'properties': {'operation': {'enum': names},
                           'arguments_json': {'type': 'string', 'description': 'The operands as one JSON object'}}}


def section(parts, title, body):
    if body not in (None, '', [], {}):
        parts.extend(['', title, '', body if isinstance(body, str) else json.dumps(body, indent=1, sort_keys=True)])


def present(summary, text, settings):
    """The old ``render_gene_context_evidence_prompt`` over this episode's summary: the assigned work, the fixed scope,
    the constraints and context, the selected process, the callable operations with their operands, the child
    investigations and what they returned, the credit and the return."""
    assignment = summary['assignment']
    library = summary['library']
    parts = ['TASK', '', text]
    section(parts, 'Fixed scope', assignment['scope'])
    section(parts, 'Proposed annotation', assignment['proposed_annotation_ref'])
    section(parts, 'Parent constraints', assignment['constraints'])
    section(parts, 'Parent-supplied context', assignment['context'])
    section(parts, 'Parent-selected evidence operands', assignment['evidence_refs'])
    section(parts, 'Parent message', assignment['message'])
    section(parts, 'Evidence axis', library['evidence_axis'])
    section(parts, 'Thought pattern', library['thought_pattern'])
    section(parts, 'Selected tools', library['child_tool_info'])
    lookups = [entry for entry in [*process_catalog(), *(knowledge_catalog() if 'knowledge_library_directory'
                                                         in settings else [])]]
    section(parts, 'Callable operations', [{'operation': entry['name'], 'meaning': entry.get('description', ''),
                                            'operands': entry['input_schema']}
                                           for entry in [*lookups, *summary['catalog'], GRADE_ENTRY]])
    section(parts, 'Child investigations', {slot: CHILD_ASSIGNMENTS[slot] for slot in offered_children(summary)})
    section(parts, 'Outstanding jobs (each is named by its handoff_ref)',
            [{name: job[name] for name in ('job', 'kind', 'submitted_at', 'handoff_ref', 'latest_check')}
             for job in summary['outstanding_jobs']])
    section(parts, 'Returned by the child investigations', summary['child_reports'])
    section(parts, 'Current credit', summary['credit_view'])
    section(parts, 'Current A103 grading sheets (the controlled features code reads from them)', summary['finding'])
    return '\n'.join(parts)


def decide(summary, feedback, ctx):
    """The two lookups first (the selected process, then the tool catalog: one unit each); then ask the model for the
    next operation, shown the assignment, the selected process, its credit view, its own outcomes, what its children
    returned, the finding so far, the pixels of a completed image view, the measured time and the yield table (the old
    decision state and inputs, over this episode's summary). A held measurement without a sheet is graded first
    (``context_grade``, the old automatic grading at publication and receipt), unless the last unit was that grading:
    a measurement it could not attach (a contrast whose operands are not held) waits for the model."""
    assignment = summary['assignment']
    if summary['library'] is None:
        return ToolCall('process_library', {'selection': assignment['selection']})
    if summary['catalog'] is None:
        return ToolCall('tool_catalog', {'selection': assignment['selection'], 'scope': assignment['scope']})
    last = summary['last_outcome']
    if summary['ungraded_measurement_refs'] and not (last is not None and last['kind'] == 'tool'
                                                     and last['tool'] == 'context_grade'):
        return ToolCall('context_grade', {'scope': assignment['scope']})
    knowledge_directory = ctx.settings.get('knowledge_library_directory')
    launch_directory = ctx.settings.get('launch_instruction_directory')
    knowledge = None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context()
    launch = None if launch_directory is None else LaunchInstructions(launch_directory).context()
    text = instructions(knowledge=knowledge, launch=launch)
    context = {'task': present(summary, text, ctx.settings), 'goal': GOAL, 'scope': assignment['scope'],
               'working_state': {'held_record_refs': summary['held_record_refs'],
                                 'committed_record_refs': summary['committed_record_refs']},
               'current_credit': summary['credit_view']['credit'],
               'current_evidence_vector': summary['credit_view'].get('axis_components'),
               'own_outcomes': summary['own_outcomes'], 'last_outcome': summary['last_outcome'],
               'child_reports': summary['child_reports'], 'revisions': summary['revisions'],
               'current_finding': summary['finding'],
               'visual_evidence': summary['visual_evidence'],
               'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['action_yields'],
        'tool_knowledge': knowledge, 'launch_instruction_library': launch},
        conflict='initial_binding_context_field_conflict')
    return ModelRequest('REASONING', text, context, output_schema(offered(summary, ctx.settings)))


def child_operands(name, arguments, records, settings):
    """The model's operands of a child commission: the objective and purpose texts, the typed assignment, the optional
    fact sources it selects and, for each record the assignment names, a record this episode holds. The child's own
    values come from the settings."""
    for key in ('objective', 'purpose'):
        if type(arguments.get(key)) is not str or not arguments[key].strip():
            raise ValueError('child_operands_need_a_' + key + '_text')
    assignment, select = arguments.get('assignment'), arguments.get('select', [])
    if not isinstance(assignment, dict):
        raise ValueError('child_operands_need_an_assignment_record')
    if not isinstance(select, list) or any(type(item) is not str for item in select):
        raise ValueError('child_select_must_be_a_list_of_field_names')
    for field in RECORD_REFS[name]:
        if field in assignment:
            value = assignment[field]
            for reference in value if isinstance(value, list) else [value]:
                if type(reference) is not str or not records.holds(reference):
                    raise ValueError('child_record_not_held:' + field + ':' + repr(reference))
    return {'objective': arguments['objective'], 'purpose': arguments['purpose'], 'assignment': assignment,
            'select': select, 'child_values': dict(settings.get('child_values', {}).get(name, {}))}


def monitor_operands(arguments, summary, settings):
    """The model's operands of a monitor commission, controlled values only: the handoff record of one outstanding
    job this episode holds (the only way to name the job), what the monitor may observe of it and the measurements
    to return. ``msg_to_child`` builds the monitor's assignment from the rows this episode holds of that job; the
    monitor's own values come from the settings."""
    fields = {'handoff_ref': {'enum': [job['handoff_ref'] for job in summary['outstanding_jobs']]},
              'requested_fields': {'type': 'array', 'uniqueItems': True, 'minItems': 1,
                                   'items': {'enum': list(MONITOR_FIELDS)}},
              'select': {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(MONITOR_RETURN_FIELDS)}}}
    Draft202012Validator({'type': 'object', 'additionalProperties': False, 'properties': fields,
                          'required': ['handoff_ref', 'requested_fields']}).validate(arguments)
    return {'handoff_ref': arguments['handoff_ref'], 'requested_fields': arguments['requested_fields'],
            'select': arguments.get('select', []),
            'child_values': dict(settings.get('child_values', {}).get(MONITOR, {}))}


def reasoning_payload(arguments, records):
    """The old admission of a ``reason`` selection: the payload fits the Store's reasoning schema, and a commit with
    every section empty is rejected before acquisition unless the selection declares ``no_applicable_evidence`` (the
    old ``empty_reasoning_commit``; the binding had no ``reasoning_has_task_content``)."""
    payload = arguments['commit']
    schema = records.reasoning_schema()
    Draft202012Validator(schema).validate(payload)
    if (set(schema.get('required', schema['properties'])) <= set(payload) <= set(schema['properties'])
            and all(value == [] for value in payload.values())
            and arguments.get('evidence_processing', {}).get('kind') != 'no_applicable_evidence'):
        raise ValueError('empty_reasoning_commit')
    return payload


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one child commission, or reject it (no unit): the answer names
    an offered operation and closed JSON operands; a reasoning payload fits the Store's schema and is not empty; a
    child commission names only records this episode holds."""
    assignment = summary['assignment']
    try:
        name = response['operation']
        if name not in offered(summary, ctx.settings):
            raise ValueError('operation_not_offered:' + repr(name))
        arguments = json.loads(response['arguments_json'])
        if not isinstance(arguments, dict):
            raise ValueError('arguments_json_must_be_a_JSON_object')
        if name == 'reason':
            payload = reasoning_payload(arguments, records)
        elif name == MONITOR:
            arguments = monitor_operands(arguments, summary, ctx.settings)
        elif name in CHILD_SLOTS:
            arguments = child_operands(name, arguments, records, ctx.settings)
    except (KeyError, TypeError, ValueError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    if name in CHILD_SLOTS:
        return ChildCall(name, arguments)
    if name in LOOKUPS:
        operands = {'arguments': arguments}
        if name == 'process.tools':
            operands['scope'] = assignment['scope']
        return ToolCall(LOOKUPS[name], operands)
    if name == 'process.revise':
        return ToolCall('process_revise', {'selection': assignment['selection'], 'revision': arguments,
                                           'scope': assignment['scope']})
    if name == 'reason':
        return ToolCall('reason', {'commit': payload, 'scope': assignment['scope'],
                                   **({'evidence_processing': arguments['evidence_processing']}
                                      if 'evidence_processing' in arguments else {})})
    if name == 'context.grade':
        return ToolCall('context_grade', {'scope': assignment['scope']})
    entry = next(entry for entry in summary['catalog'] if entry['name'] == name)
    return ToolCall('operation', {'name': name, 'operands': arguments, 'scope': assignment['scope'],
                                  'input_schema': entry['input_schema']})
