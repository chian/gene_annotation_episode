"""The task: investigate the assigned A106 question iteratively. The model looks up process options and tool
information (the process library, the tool library, the tool knowledge), prepares a revised process selection for a
new child (``process_revise``), calls the actual selected tools (``selected_tool``), commits typed scientific
reasoning (``reason``), writes its interpretation (``report``), and commissions children: published evidence
assessment (``literature``), the launch of a planned execution (``launch``), a progress check of a launched job
(``monitor``), the acquisition of its results (``results``) and a child of this same process
(``perturbation_evidence``). One unit is one model-selected tool call or one commissioned child. The task always
offers a unit and never ends the Episode: only the yield controller does.

Carried from the old ``task.py``, ``task_decision.py``, ``task_instructions.py``, ``task_state.py``,
``scientific_operations.py``, ``tool_selection.py``, ``alternate_process_selection.py``, ``execution_planning.py``,
``decision_inputs.py``, ``to_child_*.py`` and ``episode.py`` (the child roles and the permitted actions) at
97308b94c. The old ``wait`` and ``redeliver_report`` actions are not carried (a child completes inside the unit that
commissioned it), nor the decision exchange (``request_context``: a lookup is a tool), nor the checkpoint, the saved
request checks and the conversation state.

Files the episode reads outside the Store (the frozen process library, the frozen tool library, the tool knowledge
and launch instruction directories) are reached through the episode's settings (``ctx.settings``): the keys are
``process_library_directory``, ``tool_library_directory``, ``child_roles`` (the old ``child_roles`` configuration:
the slots offered), ``execution_handoff_unit`` (the credit one usable handoff earns, which the launch child takes as its
``handoff_unit``), ``monitoring_information_unit`` (the credit of one informative progress observation, the monitor's
``information_unit``), and the optional ``knowledge_library_directory``, ``launch_instruction_directory`` and
``tool_registry``. A missing required key fails.

Not carried, and the reason: the old common tools ``episode.history`` and ``episode.credit`` (the summary shows the
own outcomes and the credit), ``episode.annotation_score``, ``episode.monitoring_information``,
``episode.estimate_wait`` and the ``shared.*`` information board (they lived in the old shared runtime, which is not
read: no implementation outside it exists); ``services.authenticate_source_byte_operands`` (the authentication
step has no place: custody is the system's)."""
from copy import deepcopy

from jsonschema import ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.configuration.perturbation_evidence.process_options import (
    PerturbationEvidenceLibrary, catalog as process_catalog, evidence_axis_instruction_view)
from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.evidence_axis_contracts import (
    VERSION as EVIDENCE_AXIS_VERSION, validate_evidence_axis_entry)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.instruction_spans import replace_span
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_progress import FIELDS as JOB_PROGRESS_FIELDS
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.perturbation_evidence.evidence_axis_instructions import (
    VERSION as INSTRUCTION_VERSION, instruction_view, validate_instruction_entry)
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.perturbation_evidence.literature_investigation_prompt import (
    INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.perturbation_evidence.action_transport import (
    decode_response, generation_schema)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.presentation import extend_context
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.construction_records import (
    CHILD_SELECTION_VERSION, OPTION_REF_VERSION, REVISION_ORIGIN_VERSION, SELECTION_VERSION, scientific_digest,
    selection_fields, selector_selection, validate_child_selection, validate_revision_origin, validate_selection)
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import (
    REF, identity, obj, source_location_inputs, validate_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.perturbation_evidence.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_catalog import (
    ScientificToolLibrary, catalog as tool_library_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge, catalog as knowledge_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome

from .goal import EVIDENCE_AXIS_GOAL, GOAL

# The roles of the old ``child_request_preparer_for_binding`` map, the recursive role and the binding paths.
CHILD_SLOTS = {
    'literature': 'perturbation_evidence/published_evidence_assessment',
    'launch': 'perturbation_evidence/execution_job_submission',
    'monitor': 'perturbation_evidence/execution_progress_assessment',
    'results': 'perturbation_evidence/execution_result_acquisition',
    'perturbation_evidence': 'perturbation_evidence',
}
SERVICES = ()
# What a monitor may be asked to observe of a job (the monitor's ``requested_fields``).
MONITOR_FIELDS = (*JOB_PROGRESS_FIELDS, 'log_windows')

TEXT = {'type': 'string', 'minLength': 1}
SHA256 = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
OPEN_RECORD = {'type': 'object'}   # travels as JSON text; an optional one may be null (the strict transport)
OPEN_RECORDS = {'type': 'array', 'items': OPEN_RECORD}   # an array schema names its items
UNIQUE_REFERENCES = {'type': 'array', 'items': REF, 'uniqueItems': True}
REFERENCES = {'type': 'array', 'items': REF, 'minItems': 1, 'uniqueItems': True}
RESOURCES = {'enum': ['api', 'local', 'hpc']}
# The old ``_REVISION_ARGUMENTS``, ``_THOUGHT_REF`` and ``_TOOL_SELECTOR``.
THOUGHT_REF = obj({'version': {'const': OPTION_REF_VERSION}, 'library_id': SHA256, 'slot': {'const': 'thought_pattern'},
                   'option_id': {'type': 'string', 'pattern': '^P[0-9]+$'}, 'entry_sha256': SHA256})
TOOL_SELECTOR = obj({'name': TEXT, 'resources': RESOURCES})
REVISION_ARGUMENTS = obj({'thought_pattern': THOUGHT_REF,
                          'child_tool_info': {'type': 'array', 'items': TOOL_SELECTOR, 'uniqueItems': True}})

# The fact sources each child declares as selectable (read as data from the child's ``RETURN_FORM``), under their
# old names; the model names the ones it wants and ``msg_to_child`` selects them.
FACTS = {
    'literature': ('literature_screening_answers', 'literature_source_lead_dispositions'),
    'launch': ('execution_handoff_refs', 'execution_result_refs', 'execution_completed',
               'bvbrc_appservice_support_refs', 'bvbrc_application_outcomes'),
    'monitor': ('job_returncode', 'job_duration_seconds', 'job_elapsed_seconds', 'stdout_bytes', 'stderr_bytes',
                'log_window_refs', 'event_receipt_refs'),
    'results': ('execution_handoff_refs', 'execution_completed', 'bvbrc_appservice_support_refs',
                'bvbrc_application_outcomes'),
    'perturbation_evidence': ('perturbation_evidence_results', 'committed_record_refs'),
}
# The sources the old ``required_return_sources`` of each child binding required (this parent's own copy): a launch
# returns the original handoff; a monitor always returns its check rows; a child of this process its committed records
# and, from the first level, its process results (the old rule of the path length is not carried).
REQUIRED_FACTS = {'literature': (), 'launch': ('execution_handoff_refs',), 'monitor': (),
                  'results': (), 'perturbation_evidence': ('perturbation_evidence_results', 'committed_record_refs')}
# No text passes to a child: its objective is fixed by its slot in msg_to_child (controlled messaging).
HEAD = {}


def facts_property(slot):
    return {'return_facts': {'type': 'array', 'items': {'enum': list(FACTS[slot])}, 'uniqueItems': True}}


# The literature task the model commissions (the old ``task_schema`` of the published evidence assessment): the
# credit unit is this episode's own, filled by ``msg_to_child``.
SPAN = obj({'source_ref': REF, 'artifact_ref': REF, 'start': {'type': 'integer', 'minimum': 0},
            'end': {'type': 'integer', 'minimum': 1}})
LITERATURE_TASK = {'anyOf': [
    obj({'evidence_axis': {'const': 'A106'}, 'kind': {'const': 'verified_source_leads'}}),
    obj({'evidence_axis': {'const': 'A106'}, 'kind': {'const': 'source_answer'},
         'answer_kind': {'const': 'assessment'}, 'source_refs': REFERENCES}),
    obj({'evidence_axis': {'const': 'A106'}, 'kind': {'const': 'source_answer'},
         'answer_kind': {'const': 'screening'}, 'examined': {'type': 'array', 'minItems': 1, 'items': SPAN}})]}

COMMISSION = {
    'literature': 'Commission an investigation of which published evidence bears on the assigned question: the '
                  'records that give the question context (question_context_refs), the sources assigned for reading '
                  '(source_refs, sources this episode holds, see source_custody) and the typed answer asked '
                  '(literature_task). It returns its interpretation, credit and, selected, its typed answers.',
    'launch': 'Commission the launch of permitted concrete execution requests on explicit resource ids: requests '
              '(resource_id -> request), the immutable input versions, the constraints, optionally a pinned '
              'launch-instruction selection and the records the job inputs name (record_refs). It returns the '
              'references of the usable handoffs.',
    'monitor': 'Commission one check of the progress of a job you hold as outstanding: handoff_ref (the handoff '
               'reference of one job of outstanding_jobs) and requested_fields (what the monitor may observe of it). '
               'It returns its credit, what it found of the job (its state, whether its results are available) and '
               'its check records; return_facts selects its measurements.',
    'results': 'Commission the acquisition of the original results of a launched job through its handoff '
               '(handoff_ref, a handoff this episode holds), a selector naming which results and the API service of '
               'the original job. It returns the retained result records.',
    'perturbation_evidence': 'Commission a child of this process: copy result.selection and revision_origin of a '
                             'process_revise preparation into it, with the records of evidence and the constraints '
                             'the child investigates under. It returns its credit, finding and, selected, its '
                             'process results and committed records.',
}


def commission_arguments(slot, jobs):
    """What the model supplies for a child; ``msg_to_child`` makes the child's assignment from it, the summary and
    the settings. ``jobs`` are the outstanding jobs of the summary: a monitor is commissioned on one of them, named
    by its held handoff reference."""
    if slot == 'literature':
        return obj({**HEAD, 'question_context_refs': UNIQUE_REFERENCES, 'source_refs': REFERENCES,
                    'literature_task': LITERATURE_TASK, **facts_property(slot)},
                   required=['question_context_refs', 'source_refs', 'literature_task'])
    if slot == 'launch':
        return obj({**HEAD, 'requests': OPEN_RECORD, 'immutable_input_versions': OPEN_RECORDS,
                    'constraints': OPEN_RECORD, 'launch_instructions': OPEN_RECORD,
                    'record_refs': UNIQUE_REFERENCES, **facts_property(slot)},
                   required=['requests', 'immutable_input_versions', 'constraints'])
    if slot == 'monitor':
        return obj({**HEAD, 'handoff_ref': {'enum': [job['handoff_ref'] for job in jobs]},
                    'requested_fields': {'type': 'array', 'items': {'enum': list(MONITOR_FIELDS)},
                                         'uniqueItems': True}, **facts_property(slot)},
                   required=['handoff_ref', 'requested_fields'])
    if slot == 'results':
        return obj({**HEAD, 'handoff_ref': REF, 'selector': OPEN_RECORD, 'service': TEXT, **facts_property(slot)},
                   required=['handoff_ref', 'selector', 'service'])
    return obj({**HEAD, 'selection': OPEN_RECORD, 'revision_origin': OPEN_RECORD, 'evidence_refs': UNIQUE_REFERENCES,
                'constraints': OPEN_RECORD, **facts_property(slot)},
               required=['selection', 'revision_origin'])


def named_references(slot, arguments):
    """The records a commission of ``slot`` names that this episode must hold."""
    if slot == 'literature':
        return [*arguments['question_context_refs'], *arguments['source_refs']]
    if slot == 'launch':
        return list(arguments.get('record_refs', []))
    if slot == 'results':
        return [arguments['handoff_ref']]
    if slot == 'perturbation_evidence':
        return list(arguments.get('evidence_refs', []))
    return []


# ---------------------------------------------------------------------------------------------------------------
# What the model is shown: the instructions and the tools.

REASON_DESCRIPTION = ('Commit a typed scientific reasoning over the examined sources and the records you hold: '
                      'extracted terms, source subjects, contexts, observations, hypotheses and assessments, each '
                      'with its exact source anchor. A commit with every section empty is rejected.')
REPORT_DESCRIPTION = ('Write your interpretation of what the evidence you examined and the work of your children '
                      'show for the assigned question: what each source itself shows, its own qualifications and '
                      'what stays unresolved. Sources stay separate. Writing it can be repeated and the latest one '
                      'is what is returned.')
REPORT_SCHEMA = obj({'interpretation': TEXT,
                     'sources': {'type': 'array', 'items': obj({'source_ref': TEXT, 'statement': TEXT,
                                                                 'qualification': TEXT})},
                     'qualification': TEXT})
REVISE_DESCRIPTION = (
    'Prepare a different thought pattern and/or selected actual tools for a new child investigating the same '
    'evidence axis. Return its selection for a separately selected child commission (perturbation_evidence) with '
    "the child's job, scope, constraints and typed return form. Copy result.selection and revision_origin into that "
    'commission. Changes no current process, starts no child and records no biological observation. Select the '
    'actual tool/resource choices returned by process.tools for the desired investigation.')
REVISE_DESCRIPTION_EVIDENCE_AXIS = (
    'Prepare a pinned thought pattern and selected actual tools for a new child using the original scientific '
    "support and library. Return its selection for a separately selected child commission with the child's job, "
    'scope, constraints and typed form. Copy result.selection and revision_origin into that commission; request '
    'perturbation_evidence_results in return_facts when process provenance and existing closed results are needed. '
    'Changes no current process, starts no child and records no biological observation. Supply the actual tool '
    'names returned by process.tools for the desired alternative investigation.')
EXECUTION_DESCRIPTION = (
    'Read execution instructions for an actual selected tool/resource pair, current local/Aurora planning context, '
    'available HPC commissions and shared age-weighted timing cases for explicit compatibility profiles. No job, '
    'probe or credit.')
HISTORY_START = 'On a fresh provider conversation,'
HISTORY_END = 'Do not execute native provider tools.'
HISTORY_GUIDANCE = ('Your own earlier outcomes are shown to you as own_outcomes; that page creates no new action '
                    'and does not execute or credit the historical work again.\n')
REPORT_GUIDANCE = ('\nSelect the report tool with your interpretation when the outcomes warrant it. The report is '
                   'returned to your parent in your finding. Selecting report does not end your work: only the '
                   'numerical controller does.')

PROCESS_TOOLS = {'process_search': 'process.search', 'process_entry': 'process.entry',
                 'process_sources': 'process.sources'}
KNOWLEDGE_TOOLS = {'knowledge_search': 'knowledge.search', 'knowledge_entry': 'knowledge.entry',
                   'knowledge_read': 'knowledge.read'}


def process_library(settings):
    """The frozen process library of the run (a snapshot directory the settings name)."""
    return PerturbationEvidenceLibrary(settings['process_library_directory'])


def tool_library(settings):
    """The frozen tool library of the run (a snapshot directory the settings name)."""
    return ScientificToolLibrary(settings['tool_library_directory'])


def entry_of(library, selection):
    """The selected evidence-axis entry and whether it is a published instruction entry."""
    entry = library.resolve(selection[selection_fields(selection)[0]])
    return entry, entry.get('entry_version') == INSTRUCTION_VERSION


def replaces_default_instructions(library):
    """The old ``replaces_default_instructions``: every evidence-axis option of the library is an instruction entry."""
    axes = [header['option_ref'] for header in library.headers() if header['option_ref']['slot'] == 'evidence_axis']
    return bool(axes) and all(library.resolve(reference).get('entry_version') == INSTRUCTION_VERSION
                              for reference in axes)


def instructions(*, goal, replaces, reasoning, knowledge, launch):
    """The old ``task_instructions.instructions``: the investigation text and this episode's goal (replacing the
    text when every axis entry is an instruction entry, appended otherwise), the reasoning-commit requirement, the
    tool-knowledge text and the launch-instruction text when they are offered. The pending-delivery, wait and native
    event paragraphs describe actions that no longer exist; the history paragraph is replaced as the old exchange
    protocol replaced it."""
    text = goal if replaces else replace_span(INSTRUCTIONS, HISTORY_START, HISTORY_END, HISTORY_GUIDANCE) + '\n' + goal
    if reasoning:
        text += '\n' + REASONING_COMMIT_REQUIREMENT
    if knowledge:
        text += KNOWLEDGE_INSTRUCTIONS
    if launch:
        text += LAUNCH_INSTRUCTIONS
    return text + REPORT_GUIDANCE


def selection_checked(library, tools, value):
    """The old ``_selection``: a selection of this library whose evidence axis is an instruction or evidence-axis
    entry and whose tools are the tool library's."""
    selection = validate_selection(value)
    fields = selection_fields(selection)
    for key in fields[:2]:
        reference = selection[key]
        if reference['library_id'] != library.as_record()['library_id']:
            raise ContractError('scientific_selection_library_mismatch')
        entry = library.resolve(reference)
        if key == fields[0]:
            if entry.get('entry_version') == INSTRUCTION_VERSION:
                validate_instruction_entry(entry)
            elif entry.get('entry_version') == EVIDENCE_AXIS_VERSION:
                validate_evidence_axis_entry(entry)
            else:
                raise ContractError('scientific_support_metadata_required')
    tools.resolve_tool_info(selection['child_tool_info'])
    return selection


def proposed_selection(library, tools, initial, arguments):
    """The old ``_proposed_selection``: the initial evidence axis with the new thought pattern and tools."""
    axis_field = selection_fields(initial)[0]
    validate_schema(arguments, REVISION_ARGUMENTS)
    return selection_checked(library, tools, {
        'version': SELECTION_VERSION, 'evidence_axis': initial[axis_field],
        'thought_pattern': arguments['thought_pattern'],
        'child_tool_info': tools.resolve_tool_info(arguments['child_tool_info'])})


def direct_tools(tools, selection):
    """The old ``catalog``: the contracts of the selected tools whose invocation route is direct, without their
    instructions and route."""
    rows = [row for row in tools.resolve_invocations(selection['child_tool_info'])
            if row.get('invocation_route', {'kind': 'direct'})['kind'] == 'direct']
    return [{key: deepcopy(value) for key, value in row.items() if key not in {'instructions', 'invocation_route'}}
            for row in rows]


def offered(settings):
    """The tools offered now, by their name here: the process lookups, the revision, the execution planning, the
    selected tools, the reasoning and the report; the tool knowledge when its library is configured."""
    names = [*PROCESS_TOOLS, 'process_tools', 'process_revise', 'process_execution', 'selected_tool']
    if settings.get('knowledge_library_directory') is not None:
        names.extend(KNOWLEDGE_TOOLS)
    return [*names, 'reason', 'report']


def offered_slots(settings):
    """The children offered: the old ``child_roles`` configuration."""
    slots = list(settings['child_roles'])
    if not slots or len(set(slots)) != len(slots) or not set(slots) <= set(CHILD_SLOTS):
        raise ContractError('scientific_child_roles_invalid')
    return slots


def commissionable(slots, jobs):
    """The offered children that can be commissioned now: the monitor only while a job is outstanding (its
    commission names one by its held handoff reference)."""
    return [slot for slot in slots if slot != 'monitor' or jobs]


def reason_schema(commit_schema):
    return source_location_inputs(obj({'commit': commit_schema}))


def catalog(settings, selection, summary, published):
    """The tools the model is shown: name, description and input schema (the old catalog)."""
    library_tools = {entry['name']: entry for entry in process_catalog()}
    entries = []
    for name in offered(settings):
        if name in PROCESS_TOOLS:
            entry = library_tools[PROCESS_TOOLS[name]]
            entries.append({'name': name, 'description': entry['description'], 'input_schema': entry['input_schema']})
        elif name == 'process_tools':
            entry = tool_library_catalog()[0]
            entries.append({'name': name, 'description': entry['description'], 'input_schema': entry['input_schema']})
        elif name in KNOWLEDGE_TOOLS:
            entry = next(item for item in knowledge_catalog() if item['name'] == KNOWLEDGE_TOOLS[name])
            entries.append({'name': name, 'description': entry['description'], 'input_schema': entry['input_schema']})
        elif name == 'process_revise':
            entries.append({'name': name, 'input_schema': deepcopy(REVISION_ARGUMENTS),
                            'description': REVISE_DESCRIPTION if published else REVISE_DESCRIPTION_EVIDENCE_AXIS})
        elif name == 'process_execution':
            text = {'type': 'string', 'minLength': 1}
            profile = obj({key: text for key in ('resource_id', 'tool', 'implementation', 'parameters', 'hardware')}
                          | {'backend': {'enum': ['local', 'hpc', 'api']}})
            entries.append({'name': name, 'description': EXECUTION_DESCRIPTION, 'input_schema': obj({
                'name': text, 'resources': RESOURCES,
                'profiles': {'type': 'array', 'maxItems': 8, 'items': profile}})})
        elif name == 'selected_tool':
            continue
        elif name == 'reason':
            entries.append({'name': name, 'description': REASON_DESCRIPTION,
                            'input_schema': reason_schema(summary['reasoning_schema'])})
        else:
            entries.append({'name': name, 'description': REPORT_DESCRIPTION, 'input_schema': REPORT_SCHEMA})
    return entries


def selected_catalog(tools, selection):
    """The actual selected tools, by their library name."""
    return [{'name': row['name'], 'description': row.get('description'), 'resources': row.get('resources'),
             'input_schema': source_location_inputs(row['input_schema'])} for row in direct_tools(tools, selection)]


def selection_schema(entries, selected, slots, jobs):
    """What the model answers with: one tool and its arguments, or one commissioned child (the old action schema).
    ``jobs`` are the outstanding jobs a monitor may be commissioned on."""
    return obj({'selection': {'anyOf': [
        *(obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']}, 'arguments': entry['input_schema']})
          for entry in entries),
        *(obj({'kind': {'const': 'tool'}, 'tool': {'const': 'selected_tool'},
               'arguments': obj({'name': {'const': row['name']}, 'arguments': row['input_schema']})})
          for row in selected),
        *(obj({'kind': {'const': 'child'}, 'slot': {'const': slot}, 'arguments': commission_arguments(slot, jobs)})
          for slot in slots)]}})


# ---------------------------------------------------------------------------------------------------------------
# Tools.

def lookup(library, name, arguments):
    """A lookup outcome: the library's own, returned as the unit's outcome (a failure is an outcome too)."""
    return library.execute(name, arguments)


def process_search(arguments, ctx):
    return lookup(process_library(ctx.settings), 'process.search', arguments)


def process_entry(arguments, ctx):
    return lookup(process_library(ctx.settings), 'process.entry', arguments)


def process_sources(arguments, ctx):
    return lookup(process_library(ctx.settings), 'process.sources', arguments)


def process_tools(arguments, ctx):
    """``process.tools``: the actual operation information for the desired child investigation (the old common tool;
    its retrieval is the tool library's literal test retrieval)."""
    try:
        result = tool_library(ctx.settings).retrieve_literal_test(arguments['investigation'])
    except ValueError as error:
        return {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'code': str(error), 'operation': 'process.tools'}}
    return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': result, 'feedback': None}


def knowledge_lookup(name, arguments, ctx):
    return ToolKnowledge(ctx.settings['knowledge_library_directory']).execute(name, arguments)


def knowledge_search(arguments, ctx):
    return knowledge_lookup('knowledge.search', arguments, ctx)


def knowledge_entry(arguments, ctx):
    return knowledge_lookup('knowledge.entry', arguments, ctx)


def knowledge_read(arguments, ctx):
    return knowledge_lookup('knowledge.read', arguments, ctx)


def process_revise(arguments, ctx):
    """``process.revise`` (the old ``ScientificOperations.execute`` branch): the child selection for a separately
    commissioned child and its revision origin. It changes no process and starts no child. An invalid proposal is an
    ``invalid`` outcome with the error as feedback, as the old ``execute`` returned it. The parent invocation is this
    Episode (run and episode), the old invocation reference of the run and the path."""
    envelope, initial = arguments, arguments['selection']
    arguments = envelope['arguments']
    operation_ref = identity('operation', {'key': ctx.operation_key, 'name': 'process.revise', 'arguments': arguments})
    try:
        library, tools = process_library(ctx.settings), tool_library(ctx.settings)
        proposed = proposed_selection(library, tools, initial, arguments)
        tools.resolve_invocations(proposed['child_tool_info'])
        child_selection = validate_child_selection({'version': CHILD_SELECTION_VERSION,
                                                    'parent_selection_sha256': scientific_digest(initial),
                                                    'selection': proposed})
        origin = validate_revision_origin({
            'version': REVISION_ORIGIN_VERSION, 'preparation_operation_ref': operation_ref,
            'parent_invocation_ref': identity('scientific_invocation', {'run_id': ctx.run_id,
                                                                        'episode_id': ctx.episode_id})})
    except (ValueError, ValidationError) as error:
        return {'status': 'invalid', 'operation_ref': operation_ref, 'record_refs': [], 'changed_record_refs': [],
                'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error),
                                             **({'detail': error.detail} if getattr(error, 'detail', None) else {})}}
    return {'status': 'completed', 'operation_ref': operation_ref, 'record_refs': [], 'changed_record_refs': [],
            'result': child_selection, 'revision_origin': origin, 'feedback': None}


def process_execution(arguments, ctx):
    """``process.execution`` (the old ``execution_planning.read``): the execution recipe of an actual selected
    tool/resource pair with the planning context, the age-weighted timing history per profile and the HPC
    commissions. The selected tool is resolved here; the rest read the old runner's ``execution_memory``,
    ``resource_context`` and ``episode_bindings`` through ``workflow``, which have no object any more (BLOCKED-ON-JOB-SERVICE:
    the run's job access and estimate table are services that are not built, README section 5 items 19 and 21)."""
    selected = tool_library(ctx.settings).resolve_tool_info([{key: arguments[key] for key in ('name', 'resources')}])
    raise NotImplementedError('BLOCKED-ON-JOB-SERVICE: process_execution for ' + selected[0]['name'] + ': wanted '
                              'calls ctx.services["job_access"].read("resource_context"), '
                              'ctx.services["estimate_table"].read("history", profile, 64) and '
                              'ctx.services["job_access"].read("hpc_commissions")')


async def selected_tool(arguments, ctx):
    """One actual selected tool (the old ``services.execute_tool``): a failed selected operation is an outcome, which
    enters the iterator like any other (the old ``record_execution_failure``)."""
    name, scope = arguments['arguments']['name'], arguments['scope']
    registry = ToolRegistry(ctx.store, **ctx.settings.get('tool_registry', {}))
    permitted = tuple(ctx.store.refs()) if name == 'source.locate' else None
    try:
        return await registry.execute_async(name, arguments['arguments']['arguments'], scope=scope,
                                            operation_key=ctx.operation_key, permitted_record_refs=permitted)
    except CustodyError:
        raise
    except Exception as error:
        return failure_outcome(ctx.store, error, category='episode_execution', cause_code='selected_operation_failed')


def reason(arguments, ctx):
    """Commit the model's typed reasoning (the old ``Store.commit_reasoning`` path of ``execute``; the owner of the
    interpretation accounts is named by the system). A commit that names a record this episode does not hold is an
    ``invalid`` outcome."""
    try:
        return ctx.store.commit_reasoning(arguments['arguments']['commit'], arguments['scope'], ctx.operation_key)
    except CustodyError as error:
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'reference', 'code': str(error)}}


def report(arguments, ctx):
    """The closing value the model writes: its interpretation. It is this unit's outcome; the summary holds the
    latest one and ``final_to_parent`` returns it in the finding."""
    return {'report': arguments}


TOOLS = {'process_search': process_search, 'process_entry': process_entry, 'process_sources': process_sources,
         'process_tools': process_tools, 'knowledge_search': knowledge_search, 'knowledge_entry': knowledge_entry,
         'knowledge_read': knowledge_read, 'process_revise': process_revise, 'process_execution': process_execution,
         'selected_tool': selected_tool, 'reason': reason, 'report': report}


# ---------------------------------------------------------------------------------------------------------------
# Deciding.

def decide(summary, feedback, ctx):
    """Ask the model for the next unit, shown the selected process, the credit and its progress, the own outcomes,
    the reports of the children, the tools and the children it may commission, the measured time and the yield
    table (the old decision state and inputs, over this episode's summary)."""
    settings = ctx.settings
    library, tools = process_library(settings), tool_library(settings)
    selection = summary['selection']
    entry, published = entry_of(library, selection)
    axis_view = instruction_view(entry) if published else evidence_axis_instruction_view(entry)
    if not published:
        # old: services.scientific_support_routes(context, observation_kinds=support_observation_kinds(entry))
        raise NotImplementedError('BLOCKED-ON-SUPPORT-ROUTES: annotation_support_routes of an evidence-axis entry '
                                  'need the bound annotation policy (scientific_support_metadata is not placed)')
    thought = library.resolve(selection['thought_pattern'])
    jobs = summary['outstanding_jobs']
    slots = commissionable(offered_slots(settings), jobs)
    entries = catalog(settings, selection, summary, published)
    selected = selected_catalog(tools, selection)
    knowledge_directory = settings.get('knowledge_library_directory')
    launch_directory = settings.get('launch_instruction_directory')
    launch_library = None if launch_directory is None else LaunchInstructions(launch_directory)
    context = {
        'goal': GOAL if published else EVIDENCE_AXIS_GOAL, 'scope': summary['scope'],
        'perturbation_evidence': {
            'selection': selector_selection(selection), 'initial_selection_sha256': scientific_digest(selection),
            'evidence_axis': axis_view,
            'thought_pattern': {name: deepcopy(thought[name]) for name in (
                'id', 'name', 'description', 'use_when', 'live_alternatives', 'decision_guidance',
                'outcome_contingencies', 'boundary') if name in thought},
            'child_tool_info': deepcopy(selection['child_tool_info']),
            'assignment': {key: summary[key] for key in ('proposed_annotation_ref', 'evidence_refs', 'constraints',
                                                          'context') if key in summary},
            'permitted_children': slots},
        'credit_binding': summary['credit_binding'], 'investigation_progress': summary['investigation_progress'],
        'own_outcomes': summary['own_outcomes'], 'visual_evidence': summary['visual_evidence'],
        'last_local_outcome': summary['last_local_outcome'],
        'held_record_refs': summary['held_record_refs'], 'current_report_update': summary['report'],
        'child_reports': summary['child_reports'], 'handoff_refs': summary['handoff_refs'],
        'outstanding_jobs': [{name: job[name] for name in ('handoff_ref', 'job', 'resource_id', 'kind',
                                                             'submitted_at', 'latest_check')} for job in jobs],
        'source_custody': sorted(summary['source_custody']),
        'tools': entries, 'selected_tools': selected,
        'child_options': [{'slot': slot, 'description': COMMISSION[slot],
                           'input_schema': commission_arguments(slot, jobs)} for slot in slots],
        'time_accounting': time_accounting(ctx.clock.progress_time)}
    context = extend_context(context, {
        'feedback': feedback, 'action_yields': summary['action_yields'],
        'tool_knowledge': None if knowledge_directory is None else ToolKnowledge(knowledge_directory).context(),
        'launch_instruction_library': None if launch_library is None else launch_library.context()},
        conflict='initial_binding_context_field_conflict')
    text = instructions(goal=context['goal'], replaces=replaces_default_instructions(library),
                        reasoning=True, knowledge=context.get('tool_knowledge') is not None,
                        launch=launch_library is not None)
    return ModelRequest('REASONING', text, context,
                        generation_schema(selection_schema(entries, selected, slots, jobs)))


def empty_commit(commit, commit_schema):
    """The old empty-reasoning test: every section the schema names is present or absent and none has a row."""
    return (set(commit_schema.get('required', commit_schema['properties'])) <= set(commit)
            <= set(commit_schema['properties']) and all(value == [] for value in commit.values()))


def validate_selection_answer(value, schema):
    validate_schema(value, schema)
    return value['selection']


def action(response, summary, records, ctx):
    """Turn the model's answer into one tool call or one commission, or reject it (no unit). An answer that selects
    no offered tool or child, arguments that do not fit the schema, an empty reasoning commit, a report naming a
    source this episode does not hold, or a commission naming a record this episode does not hold is invalid. A launch
    commission carries the credit one handoff earns and a monitor commission the credit of one informative
    observation: the episode's settings (``execution_handoff_unit``, ``monitoring_information_unit``), which the
    old child bindings held as configuration; a missing setting fails."""
    settings = ctx.settings
    selection = summary['selection']
    tools = tool_library(settings)
    published = entry_of(process_library(settings), selection)[1]
    slots = commissionable(offered_slots(settings), summary['outstanding_jobs'])
    entries = catalog(settings, selection, summary, published)
    selected = selected_catalog(tools, selection)
    schema = selection_schema(entries, selected, slots, summary['outstanding_jobs'])
    try:
        chosen = validate_selection_answer(decode_response(response, schema), schema)
        if chosen['kind'] == 'child':
            slot, arguments = chosen['slot'], chosen['arguments']
            for reference in named_references(slot, arguments):
                if not records.holds(reference):
                    raise ContractError('reference_not_held', detail={'reference': reference})
        else:
            name, arguments = chosen['tool'], chosen['arguments']
            if name == 'report':
                for item in arguments['sources']:
                    if not records.holds(item['source_ref']):
                        raise ContractError('reference_not_held', detail={'reference': item['source_ref']})
            if name == 'reason' and empty_commit(arguments['commit'], summary['reasoning_schema']):
                raise ValueError('empty_reasoning_commit')
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    if chosen['kind'] == 'child':
        if slot == 'launch':
            arguments = {**arguments, 'handoff_unit': settings['execution_handoff_unit']}
        if slot == 'monitor':
            arguments = {**arguments, 'information_unit': settings['monitoring_information_unit']}
        return ChildCall(slot, arguments)
    if name in ('reason', 'selected_tool'):
        return ToolCall(name, {'arguments': arguments, 'scope': summary['scope']})
    if name == 'process_revise':
        return ToolCall(name, {'arguments': arguments, 'selection': selection})
    return ToolCall(name, arguments)
