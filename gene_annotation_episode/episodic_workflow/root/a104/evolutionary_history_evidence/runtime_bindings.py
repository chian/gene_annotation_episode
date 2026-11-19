"""A104 bindings for the generic ``episode_runtime`` runner.

One binding per episode in the A104 subtree (docs/axis_restructure_20261117/BINDING_CONTRACT.md).
Identity and structure are this module's own table (``EPISODES``): each binding's path, its
role and the binding that commissions it. The head ``evolutionary_history_evidence`` is
commissioned by the root ``annotation`` binding and may commission itself recursively.

Construction (``a104_home``) reads ``services['store']``, the run's one shared
``gene_annotation_episode.state.Store`` (C4), and ``services['a104']``:

- ``head``: ``library`` (the frozen ``EvolutionaryHistoryEvidenceLibrary`` whose A104
  evidence-axis entry and thought patterns the head presents) and ``continuation`` (the
  head's continuation declaration for its own credit);
- ``tools``: the settings of the head's own ``ToolRegistry`` over the shared store;
- ``monitor``: the progress monitors' ``information_unit`` and ``yield_settings`` (they share
  the head's ``ToolRegistry``);
- ``hpc_job_execution``: the settings of the three ``launch_hpc`` bindings' own ``HpcJobTools`` over
  the shared store (``resource``, ``directory``, ``launch_instructions``;
  ``execution_job_submission/hpc_job_execution/runtime.construct``);
- ``api_job_execution``: ``resources`` and ``continuation`` of the three ``launch_api`` bindings, each
  over its own ``ToolRegistry`` (``execution_job_submission/api_job_execution/configuration.py``);
- ``local_job_execution``: ``resource``, ``coordinator_workspace``, ``state_directory``,
  ``launch_instruction_directory`` and ``continuation`` of the three ``launch_local`` bindings, each over
  its own ``TerminalExecution`` (``execution_job_submission/local_job_execution/runtime.construct``).

A missing service raises; nothing is defaulted.

The head's assignment carries the commissioning parent's choices (C3/C6): ``thought_pattern``
(one of its library's thought patterns) and ``tools`` (a subset of its own tools). Its
controller is its own continuation over its own credit, and its ``build_episode`` is its own
model-selected source (``runtime_source``). Each progress monitor is
``runtime_monitor.MonitorBinding``: its own model-selected progress units, received-information
credit and information-accumulation controller (``episode_support/jobs/service_calls/evolutionary_history_evidence/monitor_runtime.py``). Each of
the seven literature bindings is its home's explicit ``published_evidence_assessment/literature_binding.LiteratureBinding``
subclass: its own A104 ``ToolRegistry`` over the shared store (from ``tools``), the head's
``continuation`` declaration for the same evolutionary-history credit, its own model-selected source
(``literature_source``). Each launch, job-execution, results and HPC binding mixes its own
controller and ``build_episode`` in before ``DescendantBinding``. Credit is never clamped or rescaled.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from types import MappingProxyType

from episode_runtime import ChoiceField, Commission, DeclaredField, Field, RecordForm, SubsetField, grain_name_for
from method_loop import ClosedRecord, EpisodeGoal, EpisodeRequest, ReportContract

from gene_annotation_episode.domain import ContractError

from gene_annotation_episode.episodic_workflow.episode_support.records.episode_context import EpisodeContext
from .runtime_source import REPORT_CONTRACT

AXIS = 'A104'
HEAD = 'evolutionary_history_evidence'
_LAUNCH = ('execution_job_submission', 'launch')
_MONITOR = ('execution_progress_assessment', 'monitor')
_RESULTS = ('execution_result_acquisition', 'results')


def _jobs(parent):
    """The launch (with its three execution kinds), monitor and results children under ``parent``."""
    launch = parent + '/' + _LAUNCH[0]
    return ((launch, _LAUNCH[1], parent),
            (launch + '/api_job_execution', 'launch_api', launch),
            (launch + '/local_job_execution', 'launch_local', launch),
            (launch + '/hpc_job_execution', 'launch_hpc', launch),
            (parent + '/' + _MONITOR[0], _MONITOR[1], parent),
            (parent + '/' + _RESULTS[0], _RESULTS[1], parent))


_HPC = HEAD + '/hpc_work_planning'
_HPC_EXECUTION = _HPC + '/hpc_allocation_execution'
_LITERATURE = HEAD + '/published_evidence_assessment'
_STRATEGY = _LITERATURE + '/evidence_search_strategy_improvement'
_SEARCH = _STRATEGY + '/source_relevance_assessment'
_PAGE = _SEARCH + '/source_evidence_examination'
# (binding_path, role, commissioning binding) for every A104 episode, from the head down.
EPISODES = (
    (HEAD, HEAD, 'annotation'),
    *_jobs(HEAD),
    (_HPC, 'hpc', HEAD),
    (_HPC + '/hpc_resource_prediction', 'hpc_prediction', _HPC),
    *_jobs(_HPC),
    (_HPC_EXECUTION, 'hpc_execution', _HPC),
    *_jobs(_HPC_EXECUTION),
    (_LITERATURE, 'literature', HEAD),
    (_STRATEGY, 'literature_strategy', _LITERATURE),
    (_SEARCH, 'literature_search', _STRATEGY),
    (_PAGE, 'literature_page', _SEARCH),
    (_PAGE + '/passage_evidence_extraction', 'literature_targeted', _PAGE),
    (_PAGE + '/source_coverage_improvement', 'literature_ordered', _PAGE),
    (_PAGE + '/table_evidence_extraction', 'literature_table', _PAGE),
)

# What each role's iteration cycle improves, its repeated unit and its result.
ROLE_TEXT = {
    HEAD: ('The evolutionary-history evidence about what the supplied target does within the parent question',
           'One selected tool action, scientific interpretation or child commission',
           'Typed evolutionary-history findings with their sources, qualifications and unbounded credit'),
    'launch': ('Delivery of the selected execution work to an execution resource',
               'One launch action or execution-kind child commission', 'The launch handoff and its receipts'),
    'launch_api': ('Submission of the selected work to a remote API service', 'One API submission action',
                   'The API submission handoff'),
    'launch_local': ('Execution of the selected work as a local job', 'One local execution action',
                     'The local job handoff'),
    'launch_hpc': ('Submission of the selected work to the HPC scheduler', 'One HPC submission action',
                   'The HPC submission handoff'),
    'monitor': ('Information about the progress of submitted work', 'One progress observation or wait',
                'Progress observations of the monitored target'),
    'results': ('Acquisition of the actual results of completed work', 'One result acquisition or parsing action',
                'The acquired native results and their receipts'),
    'hpc': ('The original accomplishment under real elapsed time and resource demand',
            'One planning, prediction, allocation or monitoring action', 'The HPC report with accepted accomplishment'),
    'hpc_prediction': ('The resource-demand prediction model for planned work', 'One fit, measurement or comparison',
                       'The prediction report with validated model improvement'),
    'hpc_execution': ('Execution of the planned allocation portfolio', 'One preparation, launch, monitor or parse action',
                      'The allocation execution report'),
    'literature': ('The published evidence assessed for the parent question', 'One literature action or child commission',
                   'Assessed literature findings with the records they rest on'),
    'literature_strategy': ('The evidence search strategy', 'One search-strategy action or child commission',
                            'The search strategy report'),
    'literature_search': ('Assessment of source relevance', 'One relevance-assessment action or child commission',
                          'Relevance assessments of examined sources'),
    'literature_page': ('Examination of one source for applicable evidence', 'One examination action or child commission',
                        'Source examination findings'),
    'literature_targeted': ('Extraction of evidence from source passages', 'One passage-extraction action',
                            'Passage evidence extractions'),
    'literature_ordered': ('Coverage of the examined source', 'One coverage action', 'Source coverage findings'),
    'literature_table': ('Extraction of evidence from source tables', 'One table-extraction action',
                         'Table evidence extractions'),
}

# The seven literature bindings' explicit classes, one per home (published_evidence_assessment/literature_binding.py).
LITERATURE_ROLES = ('literature', 'literature_strategy', 'literature_search', 'literature_page',
                    'literature_targeted', 'literature_ordered', 'literature_table')

SCOPE = Field('record', 'The subject the commissioning parent holds for this episode')


@dataclass(frozen=True)
class UnitInput(ClosedRecord):
    """A closed A104 controller input or request message."""
    value: Mapping

    def as_record(self):
        return json.loads(json.dumps(dict(self.value), sort_keys=True, allow_nan=False))


class _Binding:
    """The hooks every A104 binding shares."""

    def __init__(self, binding_path, role, commissioning_parent, child_slots, roles_by_grain):
        self.binding_path, self.role, self.commissioning_parent = binding_path, role, commissioning_parent
        self.grain_name = grain_name_for(binding_path)
        self.goal, self.unit, self.result = ROLE_TEXT[role]
        self.child_slots = MappingProxyType(dict(child_slots))
        self.roles_by_grain = MappingProxyType(dict(roles_by_grain))

    def episode_context(self, bound, assignment):
        """The axis's own view of this bound episode (each A104 grain named by its role)."""
        path = tuple((self.roles_by_grain.get(grain, grain), key) for grain, key in bound.path)
        return EpisodeContext(bound.run_id, bound.episode_id, self.role, path, bound.assignment['scope'],
                              assignment, bound.request.as_record())

    def restore_controller_input(self, record):
        return UnitInput(record)


class HeadBinding(_Binding):
    """The A104 head: its own model-selected units over its own tool registry and the shared store."""

    required_collaborators = ('model_provider', 'store')

    def __init__(self, *, store, library, continuation, tool_registry, child_slots, roles_by_grain):
        super().__init__(HEAD, HEAD, 'annotation', child_slots, roles_by_grain)
        from .runtime_source import evidence_axis_view, thought_pattern_views
        if tool_registry.store is not store:
            raise ContractError('a104_tool_registry_is_not_over_the_run_store')
        self.store, self.tool_registry, self.library = store, tool_registry, library
        self.continuation = _head_continuation(continuation)
        self.evidence_axis = evidence_axis_view(library)
        self.thought_patterns = MappingProxyType(thought_pattern_views(library))
        self.selectable_tools = tuple(sorted(tool_registry.catalog(None)))
        if not self.thought_patterns or not self.selectable_tools:
            raise ContractError('a104_head_selection_options_required')
        self.report_contract = MappingProxyType(REPORT_CONTRACT)
        self.assignment_form = RecordForm({
            'scope': SCOPE,
            'evidence_task': DeclaredField('text', 'The evidence task this axis investigates', self.goal),
            'thought_pattern': ChoiceField('text', 'The library thought pattern this commission investigates with',
                                           tuple(sorted(self.thought_patterns))),
            'tools': SubsetField('text', 'The tools of this head this commission may use', self.selectable_tools),
        })
        self.return_form = RecordForm({
            'credit': Field('number', "The head's own unbounded evolutionary-history axis credit"),
            'finding': Field('record', 'The typed evolutionary-history findings report')})

    def entry_request(self, entry_input, collaborators, *, parent_goal):
        if not isinstance(entry_input, Mapping) or set(entry_input) != {'scope', 'thought_pattern', 'tools'}:
            raise ContractError('a104_head_entry_requires_scope_thought_pattern_and_tools')
        assignment = {name: entry_input[name] for name in ('scope', 'thought_pattern', 'tools')}
        assignment.update(self.assignment_form.declared)
        message = UnitInput({'scope': entry_input['scope']})
        if parent_goal is None:
            goal = EpisodeGoal.root(objective=self.goal, result_contract=dict(REPORT_CONTRACT),
                                    task_context={'evidence_axis': AXIS})
            return Commission(EpisodeRequest(goal, message), assignment)
        goal = EpisodeGoal.child(parent_goal, objective=self.goal, result_contract=dict(REPORT_CONTRACT))
        return Commission(EpisodeRequest(goal, message, ReportContract(**REPORT_CONTRACT)), assignment)

    def build_controller(self, bound, collaborators):
        """The head's own continuation over its own credit, opened at that credit over its scope's subjects."""
        from yield_control import (AccumulationYieldController, BoundedQualityYieldController,
                                   CompletionYieldController, YieldParameters)
        from .runtime_source import head_credit_projector, opening_record_refs, store_scope
        if bound.binding_path != self.binding_path:
            raise ValueError('a104_controller_opened_for_another_binding:' + bound.binding_path)
        store = collaborators['store']
        if store is not self.store:
            raise ContractError('a104_head_store_is_not_the_run_store')
        declaration, projector = self.continuation, head_credit_projector()
        scope = store_scope(store, bound.assignment['scope'])
        opening = projector(store, scope, known_record_refs=opening_record_refs(scope))['credit']
        parameters = YieldParameters(**declaration['parameters'])
        if declaration['kind'] == 'bounded_quality':
            return BoundedQualityYieldController(bound.episode_id, opening, declaration['cutoff'],
                                          projector.native_score_maximum, parameters)
        if declaration['kind'] == 'completion':
            return CompletionYieldController(bound.episode_id, opening, declaration['cutoff'],
                                             projector.as_record()['maximum_credit'], parameters)
        return AccumulationYieldController(bound.episode_id, opening, declaration['cutoff'], parameters)

    def build_episode(self, grain, bound, collaborators, child_builders):
        from method_loop import Episode
        from .runtime_source import EvolutionaryHistoryEvidenceSource
        source = EvolutionaryHistoryEvidenceSource(self, bound, collaborators, child_builders)
        return Episode(grain, bound.key, source, bound.request, source.result)


class DescendantBinding(_Binding):
    """The descendant assignment, return form and entry request of an A104 descendant binding.

    Each subclass mixes in its own ``build_controller`` and ``build_episode`` before this base.
    """

    required_collaborators = ('model_provider', 'store')

    def __init__(self, binding_path, role, commissioning_parent, child_slots, roles_by_grain):
        super().__init__(binding_path, role, commissioning_parent, child_slots, roles_by_grain)
        self.assignment_form = RecordForm({
            'scope': SCOPE,
            'assignment': Field('record', f"The parent's {role} assignment")})
        self.return_form = RecordForm({
            'credit': Field('number', f'The unbounded credit of this {role} episode'),
            'report': Field('record', f"The {role} report in the parent's requested form")})

    def entry_request(self, entry_input, collaborators, *, parent_goal):
        if not isinstance(entry_input, Mapping) or set(entry_input) - {'objective', 'assignment', 'report_contract'}:
            raise ValueError('a104_entry_input_requires_objective_assignment_and_optional_report_contract')
        assignment = self.assignment_form.admit(entry_input['assignment'], 'a104_entry_assignment:' + self.binding_path)
        message = UnitInput({'scope': assignment['scope']})
        if parent_goal is None:
            goal = EpisodeGoal.root(objective=entry_input['objective'],
                                    result_contract={'role': self.role, 'result': self.result})
            return Commission(EpisodeRequest(goal, message), assignment)
        contract = entry_input['report_contract']
        goal = EpisodeGoal.child(parent_goal, objective=entry_input['objective'], result_contract=contract)
        return Commission(EpisodeRequest(goal, message, ReportContract(**contract)), assignment)


def _head_continuation(declaration):
    """The head's continuation declaration for its own credit: exactly kind, cutoff, parameters, credit_definition.

    The definition must be the head's own projector and the kind its projector's yield method.
    """
    from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import canonical
    from yield_control import (AccumulationYieldController, BoundedQualityYieldController,
                                   CompletionYieldController, YieldParameters)
    from .runtime_source import head_credit_projector
    declaration = json.loads(json.dumps(declaration, allow_nan=False))
    projector = head_credit_projector()
    task = AXIS + ':' + projector.as_record()['kind']
    if (not isinstance(declaration, dict) or set(declaration) != {'kind', 'cutoff', 'parameters', 'credit_definition'}
            or not isinstance(declaration['parameters'], dict) or set(declaration['parameters']) != {'uncertainty_alpha'}):
        raise ValueError('scientific_yield_task_binding_invalid:' + task)
    if canonical(declaration['credit_definition']) != canonical(projector.as_record()):
        raise ValueError('scientific_yield_credit_definition_mismatch:' + task)
    if declaration['kind'] != projector.yield_method:
        raise ValueError('scientific_yield_method_credit_mismatch:' + task)
    parameters = YieldParameters(**declaration['parameters'])
    if declaration['kind'] == 'bounded_quality':
        BoundedQualityYieldController('configuration', 0, declaration['cutoff'], projector.native_score_maximum, parameters)
    elif declaration['kind'] == 'completion':
        CompletionYieldController('configuration', 0, declaration['cutoff'],
                                  projector.as_record()['maximum_credit'], parameters)
    else:
        AccumulationYieldController('configuration', 0, declaration['cutoff'], parameters)
    return MappingProxyType(declaration)


def _literature_class(path, role, parent):
    """The one literature binding class its home's ``episode.py`` declares for ``path``."""
    from importlib import import_module
    from .published_evidence_assessment.literature_binding import LiteratureBinding
    module = import_module(__package__ + path[len(HEAD):].replace('/', '.') + '.episode')
    classes = [value for value in vars(module).values() if isinstance(value, type)
               and issubclass(value, LiteratureBinding) and value is not LiteratureBinding]
    if len(classes) != 1 or (classes[0].binding_path, classes[0].role, classes[0].commissioning_parent) != (
            path, role, parent):
        raise ContractError('a104_literature_binding_class_required:' + path)
    return classes[0]


def a104_home(services):
    """The A104 home factory: every A104 binding, the head's tool registry over the run's shared store."""
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.episodic_workflow.episode_support.tools.evolutionary_history_evidence.tools import ToolRegistry
    if not isinstance(services, Mapping):
        raise TypeError('a104_construction_services_must_be_a_mapping')
    try:
        store, configuration = services['store'], services['a104']
        head, tools, monitor = (configuration[name] for name in ('head', 'tools', 'monitor'))
        hpc_job_execution = configuration['hpc_job_execution']
        api_job_execution = configuration['api_job_execution']
        local_job_execution = configuration['local_job_execution']
        library, continuation = head['library'], head['continuation']
    except KeyError as error:
        raise ContractError('a104_home_requires_service:' + str(error.args[0])) from error
    if type(store) is not Store:
        raise ContractError('a104_home_store_must_be_the_shared_store')
    if not isinstance(tools, Mapping) or not isinstance(monitor, Mapping):
        raise ContractError('a104_home_tool_and_monitor_settings_must_be_mappings')
    children = {path: {} for path, _, _ in EPISODES}
    for path, role, parent in EPISODES:
        if path != HEAD:
            children[parent][role] = path
    children[HEAD][HEAD] = HEAD  # the head commissions itself recursively
    roles_by_grain = {grain_name_for(path): role for path, role, _ in EPISODES}
    from .runtime_monitor import MonitorBinding
    registry = ToolRegistry(store, **dict(tools))
    bindings = [HeadBinding(store=store, library=library, continuation=continuation, tool_registry=registry,
                            child_slots=children[HEAD], roles_by_grain=roles_by_grain)]
    for path, role, parent in EPISODES[1:]:
        if role == 'monitor':
            # A monitor's progress.log reads its received log windows through the A104 registry over the store.
            bindings.append(MonitorBinding(path, parent, children[path], roles_by_grain, tool_registry=registry,
                                           **dict(monitor)))
        elif role == 'launch':
            # A launch hands each commissioned execution request to its route children (submission_source).
            from .execution_job_submission.submission_source import LaunchBinding
            bindings.append(LaunchBinding(path, parent, children[path], roles_by_grain))
        elif role == 'launch_local':
            # Each local job binding: its own TerminalExecution over the configured local resource
            # (execution_job_submission/local_job_execution/runtime, episode_support/jobs/local_execution/evolutionary_history_evidence/local_job_runtime).
            from .execution_job_submission.local_job_execution.runtime import construct as construct_local_job
            bindings.append(construct_local_job(local_job_execution, path, role, parent, children[path],
                                                roles_by_grain))
        elif role == 'launch_hpc':
            # Each HPC job binding: its own HpcJobTools over the shared store (execution_job_submission/
            # hpc_job_execution/runtime).
            from .execution_job_submission.hpc_job_execution.runtime import construct as construct_hpc_job
            bindings.append(construct_hpc_job(store, hpc_job_execution, path, role, parent, children[path],
                                              roles_by_grain))
        elif role == 'launch_api':
            # Each API job binding: its own API services over its own A104 ToolRegistry on the shared store
            # (execution_job_submission/api_job_execution).
            from .execution_job_submission.api_job_execution.api_job_binding import ApiJobExecutionBinding
            bindings.append(ApiJobExecutionBinding(path, role, parent, children[path], roles_by_grain,
                                                   tool_registry=ToolRegistry(store, **dict(tools)),
                                                   configuration=api_job_execution))
        elif role == 'results':
            # Each results binding: its own A104 ToolRegistry on the shared store and API services over the API
            # job route's resources (execution_result_acquisition/acquisition_source.py).
            from .execution_result_acquisition.acquisition_source import ResultsBinding
            bindings.append(ResultsBinding(path, parent, children[path], roles_by_grain,
                                           tool_registry=ToolRegistry(store, **dict(tools)),
                                           api_resources=api_job_execution['resources']))
        elif role in ('hpc', 'hpc_prediction'):
            # HPC planning and its prediction sister run over the commission's own ledger (hpc_runtime).
            from .hpc_work_planning.binding import HPCBinding
            bindings.append(HPCBinding(path, role, parent, children[path], roles_by_grain))
        elif role == 'hpc_execution':
            # HPC allocation execution runs one frozen plan of its owner's ledger (allocation_runtime).
            from .hpc_work_planning.hpc_allocation_execution.binding import AllocationBinding
            bindings.append(AllocationBinding(path, role, parent, children[path], roles_by_grain))
        elif role in LITERATURE_ROLES:
            # Each literature binding: its home's own class, its own A104 ToolRegistry on the shared store and
            # the head's continuation declaration for the same credit (published_evidence_assessment).
            bindings.append(_literature_class(path, role, parent)(
                child_slots=children[path], roles_by_grain=roles_by_grain, store=store,
                tool_registry=ToolRegistry(store, **dict(tools)), continuation=continuation))
        else:
            raise ContractError('a104_role_has_no_binding:' + role)
    return tuple(bindings)


def a104_progress_provider(store, *, run_id):
    """The progress monitors' ``a104_progress_provider`` runtime collaborator for one run.

    A104's ``ProgressProvider`` over the run's shared Store, watching A104's own jobs: its job provider
    (``episode_support/jobs/service_calls/evolutionary_history_evidence/job_provider.JobProvider``) reads the practical jobs this subtree's local and HPC job
    execution bindings recorded in that Store under ``run_id``.
    """
    from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.evolutionary_history_evidence.job_provider import JobProvider
    from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.evolutionary_history_evidence.progress_provider import ProgressProvider
    return ProgressProvider(store, run_id=run_id, job_provider=JobProvider(store, run_id=run_id))


__all__ = ['AXIS', 'DescendantBinding', 'EPISODES', 'HEAD', 'HeadBinding',
           'REPORT_CONTRACT', 'UnitInput', 'a104_home', 'a104_progress_provider']
