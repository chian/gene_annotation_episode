"""The A107 head binding (``partner_presence_evidence``) and the A107 home factory.

The head runs its own iteration cycle on the generic runner (``head_cycle``):
model-provider decisions over the shared store's reasoning view, its own A107
tools, reasoning commits and commissioned children, credited by the axis's
own finding-progress projection and continued by its accumulation yield
controller.

Construction (``home_factory``) gives the head its frozen A107 scientific
library and its own ``A107ToolRegistry`` over the run's one shared store
(ruling C4). Per commission the commissioning parent chooses one library
thought pattern (``ChoiceField``) and a subset of the head's tools
(``SubsetField``) (C3/C6); the head offers only the chosen tools and presents
the chosen thought pattern with every decision.
"""
from __future__ import annotations

from collections.abc import Mapping

from episode_runtime import ChoiceField, Commission, DeclaredField, Field, RecordForm, SubsetField, grain_name_for
from method_loop import EpisodeGoal, EpisodeRequest, ReportContract

from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import ContractError
from .head_cycle import (CycleRecord, STORE_METHODS, build_head_episode, collaborator,
                         head_settings, opening_credit)
from .runtime_binding import RETURN_FORM, UnitRecord, _contract

ROLE = 'partner_presence_evidence'
AXIS = 'A107'


def _thought_view(entry):
    """The thought-pattern fields presented with each decision (the original selection summary)."""
    return {name: entry[name] for name in ('id', 'name', 'description', 'use_when', 'live_alternatives',
                                           'decision_guidance', 'outcome_contingencies', 'boundary')
            if name in entry}


def _evidence_axis_view(library):
    """The library's A107 evidence-axis entry, in its own instruction view."""
    from gene_annotation_episode.episodic_workflow.episode_support.forms.partner_presence_evidence.evidence_axis_contracts import VERSION as EVIDENCE_AXIS_VERSION
    from gene_annotation_episode.episodic_workflow.episode_support.instructions.partner_presence_evidence.evidence_axis_instructions import VERSION as INSTRUCTION_VERSION, instruction_view
    from gene_annotation_episode.episodic_workflow.episode_support.configuration.partner_presence_evidence.process_options import evidence_axis_instruction_view
    entry = library.resolve(library.reference(AXIS))
    if entry.get('entry_version') == INSTRUCTION_VERSION:
        return instruction_view(entry)
    if entry.get('entry_version') == EVIDENCE_AXIS_VERSION:
        return evidence_axis_instruction_view(entry)
    raise ContractError('a107_evidence_axis_entry_invalid')


class PartnerPresenceEvidenceEpisode:
    """The A107 evidence-axis head: its own decisions, tools, credit and continuation."""
    binding_path = ROLE
    commissioning_parent = 'annotation'
    goal = ('Improve the retained, source-grounded evidence on which components a possible function '
            'requires and whether they are present and expressed in the relevant genome, organism '
            'and conditions')
    unit = 'One scientific action of its own or one commissioned partner, literature, execution or HPC child'
    result = 'Retained typed A107 findings with their source, subject, scope and unresolved correspondence'
    # slot -> child binding_path: itself (recursive), literature, and the
    # execution, results, monitor and HPC subtrees below it.
    child_slots = {
        'partner_presence_evidence': 'partner_presence_evidence',
        'literature': 'partner_presence_evidence/published_evidence_assessment',
        'launch': 'partner_presence_evidence/execution_job_submission',
        'results': 'partner_presence_evidence/execution_result_acquisition',
        'monitor': 'partner_presence_evidence/execution_progress_assessment',
        'hpc': 'partner_presence_evidence/hpc_work_planning',
    }
    required_collaborators = ('store', 'model_provider', 'continuation')
    return_form = RETURN_FORM

    def __init__(self, *, library, tool_registry):
        from gene_annotation_episode.episodic_workflow.episode_support.tools.partner_presence_evidence.evidence_operations import A107ToolRegistry
        if type(tool_registry) is not A107ToolRegistry:
            raise ContractError('a107_head_requires_its_own_a107_tool_registry')
        self.library, self.tool_registry = library, tool_registry
        self.evidence_axis = _evidence_axis_view(library)
        self.thought_patterns = {header['option_ref']['option_id']: _thought_view(library.resolve(header['option_ref']))
                                 for header in library.headers() if header['option_ref']['slot'] == 'thought_pattern'}
        self.selectable_tools = tuple(sorted(tool_registry.catalog(None)))
        if not self.thought_patterns or not self.selectable_tools:
            raise ContractError('a107_head_selection_options_required')

    @property
    def grain_name(self):
        return grain_name_for(self.binding_path)

    @property
    def assignment_form(self):
        """``scope`` is held by the commissioner; the thought pattern and tools are its choice per commission."""
        return RecordForm({
            'scope': Field('record', 'The subject the commissioner holds (a Store scope)'),
            'evidence_axis': DeclaredField('text', 'The evidence axis this head investigates', AXIS),
            'thought_pattern': ChoiceField('text', 'The library thought pattern this commission investigates with',
                                           tuple(sorted(self.thought_patterns))),
            'tools': SubsetField('text', 'The tools of this head this commission may use', self.selectable_tools),
        })

    def entry_request(self, entry_input, collaborators, *, parent_goal):
        fields = {'objective', 'scope', 'thought_pattern', 'tools'} | ({'report_contract'} if parent_goal else set())
        if not isinstance(entry_input, Mapping) or set(entry_input) != fields \
                or type(entry_input['objective']) is not str or not entry_input['objective'].strip():
            raise ContractError('a107_head_entry_requires_' + '_'.join(sorted(fields)))
        assignment = self.assignment_form.admit(
            {'scope': entry_input['scope'], 'thought_pattern': entry_input['thought_pattern'],
             'tools': entry_input['tools'], **self.assignment_form.declared}, self.binding_path)
        message = UnitRecord({'objective': entry_input['objective']})
        if parent_goal is None:
            goal = EpisodeGoal.root(objective=entry_input['objective'],
                                    result_contract={'binding_path': self.binding_path, 'result': self.result},
                                    task_context={'evidence_axis': AXIS})
            return Commission(EpisodeRequest(goal, message), assignment)
        contract = _contract(entry_input['report_contract'], self.binding_path)
        goal = EpisodeGoal.child(parent_goal, objective=entry_input['objective'], result_contract=contract)
        return Commission(EpisodeRequest(goal, message, ReportContract(**contract)), assignment)

    def build_controller(self, bound, collaborators):
        """The A107 accumulation yield controller, opened at the commission's finding-progress baseline."""
        from yield_control import AccumulationYieldController, YieldParameters
        settings = head_settings(collaborators, self.binding_path)
        store = collaborator(collaborators, 'store', STORE_METHODS)
        return AccumulationYieldController(bound.episode_id, opening_credit(bound, store, settings), settings['cutoff'],
                               YieldParameters(**settings['parameters']))

    def build_episode(self, grain, bound, collaborators, child_builders):
        return build_head_episode(self, grain, bound, collaborators, child_builders)

    def restore_controller_input(self, record):
        if not isinstance(record, Mapping) or 'credit' not in record:
            raise ContractError('a107_recorded_unit_requires_credit:' + self.binding_path)
        return CycleRecord(dict(record))


def home_factory(services):
    """The A107 home factory for ``BindingRegistry.compose``: the head and its 28 descendants.

    ``services['store']`` is the run's one shared ``gene_annotation_episode.state.Store``.
    ``services['partner_presence_evidence']`` holds A107's construction-time services,
    each required (nothing is defaulted):

    - ``library``: the frozen A107 scientific library (``PartnerPresenceEvidenceLibrary``);
    - ``tools``: the keyword settings of the head's own ``A107ToolRegistry`` over the shared
      store (``a107_work_directory``, ``a107_detection_bindings`` and the ``ToolRegistry`` settings, of which
      ``clients``, ``minimap2_cache_dir`` and the five executables are required).

    ``services['a107_local_job_execution']`` holds the keyword operands of the three local job
    execution bindings (``episode_support/jobs/local_execution/partner_presence_evidence/local_job_runtime.A107LocalJobRuntime``: ``resource``,
    ``coordinator_workspace``, ``state_directory``, ``launch_instruction_directory``).

    ``services['a107_hpc_job_execution']`` holds the settings of the three HPC job execution
    bindings' own ``HpcJobTools`` over the shared store (``resource``, ``directory``,
    ``launch_instructions``; ``execution_job_submission/hpc_job_execution/runtime.construct``).

    ``services['a107_progress_monitor']`` holds the three progress monitors' ``information_unit``,
    ``yield_settings`` and ``tools`` (the settings of each monitor's own base A107 ``ToolRegistry``
    over the shared store; ``runtime_monitor``).

    ``services['a107_api_job_execution']`` holds the three API job execution bindings' ``resources``
    (each binding's own API services over its own ``A107ToolRegistry``;
    ``execution_job_submission/api_job_execution/configuration.py``).
    The three ``execution_result_acquisition`` bindings each get their own ``A107ToolRegistry`` and API
    services over the same ``resources`` (``execution_result_acquisition/acquisition_source.py``).

    The seven literature bindings each get their own ``A107ToolRegistry`` over the shared store
    from the same ``tools`` settings (``published_evidence_assessment/literature_binding.py``).

    The remaining descendants (the three job submission bindings and HPC planning, prediction and
    allocation) take no construction-time services: they read their runtime collaborators.
    """
    from importlib import import_module
    from gene_annotation_episode.episodic_workflow.episode_support.tools.partner_presence_evidence.evidence_operations import A107ToolRegistry
    try:
        store, own = services['store'], services[ROLE]
        library, tools = own['library'], own['tools']
        local_jobs = services['a107_local_job_execution']
        hpc_jobs = services['a107_hpc_job_execution']
    except (KeyError, TypeError) as error:
        raise ContractError('a107_home_factory_requires_service:' + str(error)) from error
    if set(own) != {'library', 'tools'} or not isinstance(tools, Mapping):
        raise ContractError('a107_home_factory_services_must_be_exactly_library_and_tools')
    if not isinstance(local_jobs, Mapping):
        raise ContractError('a107_home_factory_local_job_execution_operands_must_be_a_mapping')
    head = PartnerPresenceEvidenceEpisode(library=library, tool_registry=A107ToolRegistry(store, **tools))
    base = 'gene_annotation_episode.episodic_workflow.root.a107.'
    descendants = [import_module(base + path.replace('/', '.') + '.episode') for path in DESCENDANT_PATHS]
    from .execution_job_submission.hpc_job_execution.runtime import construct as construct_hpc_job
    return (head, *(_descendant(module)(**local_jobs) if path.endswith('/local_job_execution')
                    # Each HPC job binding: its own HpcJobTools over the shared store.
                    else construct_hpc_job(_descendant(module), store, hpc_jobs)
                    if path.endswith('/hpc_job_execution')
                    # Each literature binding: its own A107ToolRegistry over the shared store.
                    else _descendant(module)(tool_registry=A107ToolRegistry(store, **tools))
                    if path.startswith(LITERATURE_PATH)
                    else _progress_monitor(_descendant(module), store, services)
                    if path.endswith('/execution_progress_assessment')
                    # Each API job binding: its own API services over its own A107ToolRegistry on the shared store.
                    else _api_job(_descendant(module), store, tools, services)
                    if path.endswith('/api_job_execution')
                    # Each result acquisition binding: its own A107ToolRegistry and API services over the API job
                    # route's resources (execution_result_acquisition/acquisition_source.py).
                    else _result_acquisition(_descendant(module), store, tools, services)
                    if path.endswith('/execution_result_acquisition')
                    else _descendant(module)() for path, module in zip(DESCENDANT_PATHS, descendants)))


def _api_job(binding, store, tools, services):
    """One API job binding over its own A107ToolRegistry (``execution_job_submission/api_job_execution``)."""
    from gene_annotation_episode.episodic_workflow.episode_support.tools.partner_presence_evidence.evidence_operations import A107ToolRegistry
    try:
        configuration = services['a107_api_job_execution']
    except KeyError as error:
        raise ContractError('a107_home_factory_requires_service:' + str(error)) from error
    return binding(tool_registry=A107ToolRegistry(store, **tools), configuration=configuration)


def _result_acquisition(binding, store, tools, services):
    """One result acquisition binding over its own A107ToolRegistry, with API services over the API job route's
    ``resources`` (``execution_result_acquisition/acquisition_source.py``)."""
    from gene_annotation_episode.episodic_workflow.episode_support.tools.partner_presence_evidence.evidence_operations import A107ToolRegistry
    try:
        resources = services['a107_api_job_execution']['resources']
    except KeyError as error:
        raise ContractError('a107_home_factory_requires_service:' + str(error)) from error
    return binding(tool_registry=A107ToolRegistry(store, **tools), api_resources=resources)


def _progress_monitor(binding, store, services):
    """One progress monitor over its own base A107 ``ToolRegistry`` on the shared store (``runtime_monitor``)."""
    from gene_annotation_episode.episodic_workflow.episode_support.tools.partner_presence_evidence.tools import ToolRegistry
    try:
        settings = services['a107_progress_monitor']
    except KeyError as error:
        raise ContractError('a107_home_factory_requires_service:' + str(error)) from error
    if not isinstance(settings, Mapping) or set(settings) != {'information_unit', 'yield_settings', 'tools'} \
            or not isinstance(settings['tools'], Mapping):
        raise ContractError('a107_progress_monitor_requires_exactly:information_unit,yield_settings,tools')
    return binding(information_unit=settings['information_unit'], yield_settings=settings['yield_settings'],
                   tool_registry=ToolRegistry(store, **settings['tools']))


def _descendant(module):
    from .runtime_binding import DescendantBinding
    classes = [value for value in vars(module).values()
               if isinstance(value, type) and issubclass(value, DescendantBinding) and value is not DescendantBinding]
    if len(classes) != 1:
        raise ContractError('a107_descendant_home_must_declare_one_binding:' + module.__name__)
    return classes[0]


_EXECUTION = ('execution_job_submission', 'execution_job_submission/api_job_execution',
              'execution_job_submission/hpc_job_execution', 'execution_job_submission/local_job_execution',
              'execution_progress_assessment', 'execution_result_acquisition')
_LITERATURE = ('published_evidence_assessment', 'published_evidence_assessment/evidence_search_strategy_improvement',
               'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment')
_PAGE = _LITERATURE[-1] + '/source_evidence_examination'
LITERATURE_PATH = ROLE + '/' + _LITERATURE[0]
DESCENDANT_PATHS = tuple(ROLE + '/' + path for path in (
    *_LITERATURE, _PAGE, _PAGE + '/passage_evidence_extraction', _PAGE + '/source_coverage_improvement',
    _PAGE + '/table_evidence_extraction',
    *_EXECUTION,
    'hpc_work_planning', *('hpc_work_planning/' + path for path in _EXECUTION),
    'hpc_work_planning/hpc_resource_prediction',
    'hpc_work_planning/hpc_allocation_execution',
    *('hpc_work_planning/hpc_allocation_execution/' + path for path in _EXECUTION)))


def a107_progress_provider(store, *, run_id):
    """The progress monitors' ``a107_progress_provider`` runtime collaborator for one run.

    A107's ``ProgressProvider`` over the run's shared Store, watching A107's own jobs: its job provider
    (``episode_support/jobs/service_calls/partner_presence_evidence/job_provider.JobProvider``) reads the practical jobs this subtree's local and HPC job
    execution bindings recorded in that Store under ``run_id``.
    """
    from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.partner_presence_evidence.job_provider import JobProvider
    from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.partner_presence_evidence.progress_provider import ProgressProvider
    return ProgressProvider(store, run_id=run_id, job_provider=JobProvider(store, run_id=run_id))


__all__ = ['DESCENDANT_PATHS', 'PartnerPresenceEvidenceEpisode', 'a107_progress_provider', 'home_factory']
