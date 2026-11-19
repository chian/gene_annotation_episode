"""The task: the launch of the computations the A107 head selected. The first unit is the lookup of the configured
resource capabilities (the old ``execution.capabilities``, the one operation of ``work_operations.py``:
``execution_capabilities`` here, a tool name cannot contain a dot); after it the model chooses a lookup in the
run-frozen tool-knowledge or launch-instruction library (the old decision-exchange lookups, which are tools now), a
reasoning commit (the old ``reason`` action), or which permitted concrete request to commission on an explicit
``resource_id``. A commission is a ``ChildCall`` on the launch child that owns the resource's kind (``launch_api``,
``launch_local`` or ``launch_hpc``). The task always offers a unit and never ends the Episode: no stopping budget is
added, and the yield controller (``yield_estimator.py``) alone stops it.

The old decision machine (``LaunchTask.next``, ``apply_response``, ``execute``, ``LaunchTaskDecision.call``,
``exchange_decision`` and its saved-request checks, the ``wait`` and ``redeliver_report`` actions, the conversation
state) is the system's loop now. The old ``permitted_common_actions`` offered ``tool``, ``reason``, ``child``,
``wait`` and ``redeliver_report`` (this episode has no ``hpc`` ancestor); ``wait`` and ``redeliver_report`` have no
replacement (a child completes inside the unit that commissions it), ``reason`` is the tool ``reason`` (a
``commit_reasoning`` through ``ctx.store``). What stays of ``task_instructions.instructions`` is the goal text (it
replaced the default instructions), the reasoning-commit requirement, the tool-knowledge text and the
launch-instruction text; the ``pending_child_delivery``, wait, native-event and decision-exchange paragraphs
described actions that no longer exist.

BLOCKED-ON-JOB-SERVICE: the ``job_access`` service has no implementation yet (LAUNCH_MONITOR_EXTRACT_MECHANICS.md,
section 5 and "Not provided yet" item 4). This episode names it for the two things the old ``api_execution`` did for
an API resource: the operations and configuration facts of the resource (``capabilities(resource_id)``) and the
service's own validation of an API request (``validate_assignment(request)``); each raises where it is called.

Not carried into the model's context (their sources are old-runner services, not episode functions): the old
``resource_context``, ``shared_information_context``, ``execution_expectations``, ``resource_tool_estimates`` and
``native_execution_expectations`` of ``task_decision.call``; the old prompt renderers of ``presentation.py``
(``present_context``: the HPC, A107 head, API launch, RNA, selected-execution and monitor prompts) are not in the
library: the model's context carries a text task of this episode's own.

Settings (``ctx.settings``, the old ``configuration.py`` values): ``resources`` (the configured resources by resource
id, each with ``kind`` ``local``, ``pbs_ssh``, ``hmmer_api`` or ``api``), ``initial_information`` (the recorded
inventory by resource id), ``coordinator_workspace`` (the run directory the resource validators work in),
``launch_instructions_directory`` and ``tool_knowledge_directory`` (the old ``directory`` of the two libraries) and
``task_yield_profiles`` (read by ``yield_estimator.py``)."""
from copy import deepcopy
import inspect
import json

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChildCall, CustodyError, ModelRequest, Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.findings.partner_presence_evidence.terminal_scientific_evidence import (
    terminal_artifact_paths)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS, LaunchInstructions, catalog as launch_catalog)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.partner_presence_evidence.terminal_execution import (
    TerminalExecution)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.rejection_feedback import (
    rejection_feedback)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.strict_output import (
    decode_strict_output, strict_output_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import time_accounting
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_knowledge import (
    INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS, ToolKnowledge, catalog as knowledge_catalog)

from .goal import BINDING_PATH, GOAL

CHILD_SLOTS = {'launch_api': BINDING_PATH + '/api_job_execution', 'launch_hpc': BINDING_PATH + '/hpc_job_execution',
               'launch_local': BINDING_PATH + '/local_job_execution'}
SERVICES = ('job_access',)

# The old ``binding_roles.KINDS``: the kind of each configured resource.
KINDS = {'local': 'local', 'pbs_ssh': 'hpc', 'hmmer_api': 'api', 'api': 'api'}
# The old ``resource_information._resource_information`` keys copied from the configured resource.
RESOURCE_KEYS = ('workspace', 'policy', 'account', 'python_executable', 'service', 'base_url')
# The old ``terminal_validation.operation_catalog``: the one general capability of a local or HPC resource.
PRACTICAL_TOOL_NAMES = ['exec_command']
# The old ``LaunchInternalSummary._with_selected_execution_task``: the native job families whose scientific view it
# presented.
SUPPORTED_NATIVE_JOBS = ('native_blast', 'native_blast_masking', 'native_blast_utility', 'native_blast_database',
                         'native_blast_standard_database', 'native_hmmer', 'native_hmmer_preparation',
                         'native_expression_nmf')
# The old ``LaunchConfiguration.__init__`` allowance of ``native_*`` bindings on a configured resource.
ALLOWED_NATIVE = {'native_blast', 'native_blast_masking', 'native_blast_utility', 'native_blast_database',
                  'native_blast_standard_database', 'native_hmmer', 'native_hmmer_preparation', 'native_infernal',
                  'native_infernal_preparation', 'native_rna_structure', 'native_expression_nmf'}
REASONING_COMMIT_REQUIREMENT = 'A common scientific reason action needs at least one proposed commit row. A request with every commit section empty is rejected before acquisition and creates no completed-action observation. A return-form update alone does not make that request executable. Where the supplied action schema explicitly permits evidence_processing.kind=no_applicable_evidence, its source-grounded declaration is the existing exception. Keep current report references when the interpretation is unchanged; existing saved results require no empty reasoning action.'
ACTION_BOUNDARY = ('Do not emit a stop action or invent a turn budget, approval review, quality gate, experiment, '
                   'term or observation.\n')
HOST_EXECUTION_GUIDANCE = 'Do not execute native provider tools. The host executes your selected action.\n'
ANSWER_INSTRUCTION = (' Answer with one selection: commission one permitted request on its explicit resource_id '
                      '(kind child, with the launch child slot that owns the resource), look into a library '
                      '(kind tool, one operation of the library), or commit a reasoning payload (kind reason).')
LIBRARIES = {'knowledge_lookup': ('Look into the run-frozen tool-instruction library: ', knowledge_catalog),
             'launch_instruction_lookup': ('Look into the run-frozen launch instruction library: ', launch_catalog)}
# The old ``launch_operation_catalog``: the one operation of this episode's own tool.
CAPABILITIES_DESCRIPTION = ('Read the actual caller-bound resource configuration and already recorded inventory; no '
                            'discovery or selection.')
_TRANSPORT = {'open_records_as_text': False, 'argument_transport_error': 'execution_launch_argument_transport'}


def _resources(settings):
    """The old ``LaunchConfiguration.__init__`` checks of the configured resources."""
    resources, information = settings['resources'], settings['initial_information']
    if (not isinstance(resources, dict) or not resources or any(
            not isinstance(key, str) or not key or not isinstance(value, dict) or value.get('kind') not in KINDS
            for key, value in resources.items())):
        raise ValueError('explicit_execution_resources_required')
    if not isinstance(information, dict) or not set(information) <= set(resources):
        raise ValueError('initial_inventory_resource_not_bound')
    for configuration in resources.values():
        if {name for name in configuration if name.startswith('native_') and name not in ALLOWED_NATIVE}:
            raise ValueError('a107_execution_resource_binding_conflict')
    return resources


def _bound(summary, ctx):
    """The old ``_validate_request`` against the configured resources: each request names a bound resource of its
    kind, and the transport (or the API service) accepts the request. A configuration or request it refuses raises
    and fails the run: it is not a model answer. (The old ``validate_primary_resource_bindings``,
    ``validate_preparation_resource_binding`` and the native NMF, RNA structure and Infernal binding validators have
    no module in the library.)"""
    settings = ctx.settings
    _resources(settings)
    for resource_id, request in summary['assignment']['requests'].items():
        config = settings['resources'].get(resource_id)
        if config is None:
            raise ValueError('execution_resource_not_bound')
        kind = 'api' if request['version'] != 'practical_assignment_v1' else request['resource_kind']
        if KINDS[config['kind']] != kind:
            raise ValueError('execution_resource_kind_conflict')
        if kind == 'api':
            try:
                ctx.services['job_access'].read('validate_assignment', request)
            except AttributeError:
                raise NotImplementedError(
                    'BLOCKED-ON-JOB-SERVICE: job_access.validate_assignment(request); wanted call: '
                    'ctx.services["job_access"].read("validate_assignment", request)') from None
        else:
            TerminalExecution(config, coordinator_workspace=settings['coordinator_workspace'],
                              artifact_selector=terminal_artifact_paths).validate_assignment(request)


async def execution_capabilities(arguments, ctx):
    """The old ``execution.capabilities`` (``work_operations.execute`` over ``execution_capability_information``): the
    caller-bound resource configuration and the already recorded inventory, with no discovery, authentication probe
    or selection. A resource of the API kind also lists its configured operations and configuration facts, which only
    the job-access service knows."""
    settings = ctx.settings
    information = []
    for resource_id, config in settings['resources'].items():
        kind = KINDS[config['kind']]
        value = {'resource_id': resource_id, 'resource_kind': kind, 'availability': 'unknown',
                 'observed_at': 'caller_configuration', 'provenance_refs': [], 'knowledge_entry_ids': [],
                 **{key: deepcopy(config[key]) for key in RESOURCE_KEYS if key in config},
                 'inventory_snapshot': deepcopy(settings['initial_information'].get(resource_id))}
        if kind == 'api':
            service = ctx.services['job_access']
            if not hasattr(service, 'capabilities'):
                raise NotImplementedError(
                    'BLOCKED-ON-JOB-SERVICE: job_access.capabilities(resource_id); wanted call: '
                    'await ctx.services["job_access"].capabilities(resource_id)')
            entries = service.capabilities(resource_id)
            if inspect.isawaitable(entries):
                entries = await entries
            value['tool_names'] = [entry['name'] for entry in entries]
            facts = {}
            for entry in entries:
                reported = entry.get('configuration', {})
                for name in ('ncbi_contact_configured', 'provider_rate_state_configured'):
                    if name not in reported:
                        continue
                    actual = reported[name]
                    if type(actual) is not bool:
                        raise ValueError('api_configuration_fact_must_be_boolean')
                    if name in facts and facts[name] != actual:
                        raise ValueError('api_configuration_fact_conflict')
                    facts[name] = actual
            if facts:
                value['api_configuration_facts'] = facts
        else:
            value['tool_names'] = list(PRACTICAL_TOOL_NAMES)
        information.append(value)
    return {'execution_resource_capabilities': information,
            'execution_initial_information': deepcopy(settings['initial_information'])}


def knowledge_lookup(arguments, ctx):
    """One operation of the run-frozen tool-instruction library (the old ``knowledge.*`` exchange lookups)."""
    return ToolKnowledge(ctx.settings['tool_knowledge_directory']).execute(arguments['operation'],
                                                                           arguments['arguments'])


def launch_instruction_lookup(arguments, ctx):
    """One operation of the run-frozen launch-instruction library (the old ``launch.instructions.*`` lookups)."""
    return LaunchInstructions(ctx.settings['launch_instructions_directory']).execute(arguments['operation'],
                                                                                    arguments['arguments'])


def reason(arguments, ctx):
    """The old ``reason`` action (``LaunchTask.execute``: ``store.commit_reasoning(payload, scope, key)``): commit the
    model's reasoning payload in the commissioned scope. The old ``specialist.execute_reasoning`` hook was this
    episode's none. A payload that names a record the Episode does not hold is a failure outcome, not a crash."""
    try:
        return {'status': 'completed', 'result': ctx.store.commit_reasoning(arguments['commit'], arguments['scope'],
                                                                           ctx.operation_key)}
    except CustodyError as error:
        return {'status': 'failed', 'category': 'custody', 'detail': str(error)}


TOOLS = {'execution_capabilities': execution_capabilities, 'knowledge_lookup': knowledge_lookup,
         'launch_instruction_lookup': launch_instruction_lookup, 'reason': reason}


def _selected_execution_task(summary, resources):
    """The old ``LaunchInternalSummary._with_selected_execution_task``: the scientific question and tool information
    of the parent task, and each request with its resource information, constraints and job. It presented nothing
    when the request of some resource was not an EBI HMMER API request or exactly one supported native job
    family."""
    task = summary['scientific_task']
    if task is None:
        return None
    selected = []
    for resource_id, request in summary['assignment']['requests'].items():
        if resource_id not in resources:
            return None
        if request['version'] != 'practical_assignment_v1':
            if request.get('service') != 'ebi_hmmer':
                return None
            kind, job = 'api', deepcopy(request)
        else:
            jobs = request['requested_job']
            chosen = [name for name in SUPPORTED_NATIVE_JOBS if isinstance(jobs.get(name), dict)]
            if len(chosen) != 1:
                return None
            kind, job = request['resource_kind'], deepcopy(jobs[chosen[0]])
            if chosen[0] == 'native_expression_nmf':
                # old: expression_nmf_presentation.expression_nmf_scientific_job_view(job), in no place now
                raise NotImplementedError('unplaced:expression_nmf_scientific_job_view')
            if chosen[0] in ('native_hmmer', 'native_hmmer_preparation'):
                # old: native_profile_presentation.native_profile_scientific_job_view(job), in no place now
                raise NotImplementedError('unplaced:native_profile_scientific_job_view')
        selected.append({'resource_id': resource_id, 'resource_kind': kind,
                         'endpoint': deepcopy(request.get('endpoint')),
                         'constraints': deepcopy(request.get('constraints', {})), 'job': job,
                         'resource': resources[resource_id]})
    return {'version': 'selected_execution_task_v1', 'scientific_question': task['scientific_question'],
            'selected_tool_info': task['selected_tool_info'], 'requests': selected,
            'constraints': deepcopy(summary['assignment']['constraints']), 'selector': None,
            'result_description': None}


def _task_text(summary, selected):
    parts = ['TASK', '', 'Choose which permitted concrete execution request to commission on an explicit resource_id.']
    if selected is not None:
        parts.extend(['', 'Selected execution task', '', json.dumps(selected, indent=1, sort_keys=True)])
    parts.extend(['', 'Permitted requests', '', json.dumps(summary['permitted'], indent=1, sort_keys=True),
                  '', 'Launches so far', '', json.dumps(summary['launches'], indent=1, sort_keys=True)])
    return '\n'.join(parts)


def _schema(summary):
    """What the model answers with: the commission of one permitted request, one operation of a library, or a
    reasoning commit."""
    commissions = [{'type': 'object', 'additionalProperties': False, 'required': ['kind', 'slot', 'resource_id'],
                    'properties': {'kind': {'type': 'string', 'const': 'child'},
                                   'slot': {'type': 'string', 'const': entry['slot']},
                                   'resource_id': {'type': 'string', 'const': resource_id}}}
                   for resource_id, entry in sorted(summary['permitted'].items())]
    lookups = [{'type': 'object', 'additionalProperties': False,
                'required': ['kind', 'tool', 'operation', 'arguments'],
                'properties': {'kind': {'type': 'string', 'const': 'tool'},
                               'tool': {'type': 'string', 'const': name},
                               'operation': {'type': 'string', 'const': operation['name']},
                               'arguments': deepcopy(operation['input_schema'])}}
               for name, (_, catalog) in sorted(LIBRARIES.items()) for operation in catalog()]
    # The old ``reason`` action; its commit is the Store's reasoning payload, checked in ``action`` against
    # ``records.reasoning_schema()`` (a decision has no Store). Committed in the scope the commissioner fixed.
    reasons = [] if summary['scope'] is None else [
        {'type': 'object', 'additionalProperties': False, 'required': ['kind', 'commit'],
         'properties': {'kind': {'type': 'string', 'const': 'reason'}, 'commit': {'type': 'object'}}}]
    return {'type': 'object', 'additionalProperties': False, 'required': ['selection'],
            'properties': {'selection': {'anyOf': commissions + lookups + reasons}}}


def _context(summary, feedback, ctx, selected):
    settings = ctx.settings
    library = LaunchInstructions(settings['launch_instructions_directory'])
    knowledge = ToolKnowledge(settings['tool_knowledge_directory'])
    context = {'task': _task_text(summary, selected), 'feedback': feedback,
               'execution_assignment': summary['assignment'], 'execution_progress': summary['progress'],
               'execution_resource_capabilities': summary['capabilities']['execution_resource_capabilities'],
               'execution_initial_information': summary['capabilities']['execution_initial_information'],
               'callable_lookups': [{'name': name, 'description': description + ', '.join(
                   operation['name'] for operation in catalog())} for name, (description, catalog) in
                   sorted(LIBRARIES.items())],
               'requested_information': summary['lookups'], 'completed_action_reports': summary['launches'],
               'launch_instruction_library': library.context(), 'tool_knowledge': knowledge.context(),
               'selected_launch_instructions': library.materialize(summary['assignment'].get('launch_instructions')),
               'tools': [{'name': 'execution_capabilities', 'description': CAPABILITIES_DESCRIPTION}],
               'controller': summary['controller'], 'time_accounting': time_accounting(ctx.clock.progress_time)}
    if selected is not None:
        context['selected_execution_task'] = selected
    return context


def decide(summary, feedback, ctx):
    """The lookup of the capabilities first (after the configured resources accepted the requests); then one
    selection: a library lookup, a reasoning commit or the commission of one permitted request, chosen from the
    capabilities, the inventory, the handoffs received so far and their credit."""
    if summary['capabilities'] is None:
        _bound(summary, ctx)
        return ToolCall('execution_capabilities', {})
    resources = {value['resource_id']: value for value in summary['capabilities']['execution_resource_capabilities']}
    selected = _selected_execution_task(summary, resources)
    instructions = (GOAL + '\n' + REASONING_COMMIT_REQUIREMENT + '\n' + ACTION_BOUNDARY + HOST_EXECUTION_GUIDANCE + KNOWLEDGE_INSTRUCTIONS
                    + LAUNCH_INSTRUCTIONS + ANSWER_INSTRUCTION)
    return ModelRequest('REASONING', instructions, _context(summary, feedback, ctx, selected),
                        strict_output_schema(_schema(summary), **_TRANSPORT))


def action(response, summary, records, ctx):
    """The one unit the answer selects, or a rejection: a lookup of a library, a reasoning commit, or the commission
    of a permitted request on the launch child that owns the resource's kind. The lookups are always acceptable,
    so a unit is always offered."""
    schema = _schema(summary)
    try:
        decoded = decode_strict_output(response, schema, **_TRANSPORT)
        Draft202012Validator(schema).validate(decoded)
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise Rejected(rejection_feedback(error, category='action_contract'))
    selection = decoded['selection']
    if selection['kind'] == 'child':
        return ChildCall(selection['slot'], {'resource_id': selection['resource_id']})
    if selection['kind'] == 'reason':
        payload = selection['commit']
        commit_schema = records.reasoning_schema()
        try:
            Draft202012Validator(commit_schema).validate(payload)
        except ValidationError as error:
            raise Rejected(rejection_feedback(error, category='action_contract'))
        # The old ``empty_reasoning_commit``: a reason answer with every commit section empty is rejected (this
        # episode has no ``reasoning_has_task_content`` of its own, and a launch has no evidence processing).
        if (set(commit_schema.get('required', commit_schema['properties'])) <= set(payload)
                <= set(commit_schema['properties']) and all(value == [] for value in payload.values())):
            raise Rejected(rejection_feedback(ValueError('empty_reasoning_commit'), category='action_contract'))
        return ToolCall('reason', {'commit': payload, 'scope': summary['scope']})
    return ToolCall(selection['tool'], {'operation': selection['operation'], 'arguments': selection['arguments']})
