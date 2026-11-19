"""A102 episode bindings under the generic ``episode_runtime`` contract.

Every binding class in the A102 head subtree mixes in ``A102ContractBinding``
(docs/axis_restructure_20261117/BINDING_CONTRACT.md). The binding's identity is
its ``binding_path``; its ``grain_name``, ``goal``, ``unit``, ``result`` and
``child_slots`` are declared in this axis's own tables below.

- The head (``episode.StructuralHomologyEvidenceEpisode``) runs for real: its own
  model-selected decisions over its own tool registry, its per-task credit and its
  per-task yield controller (``runtime_head``).
- The three progress monitors run for real: each mixes in
  ``runtime_monitor.A102MonitorBinding`` (the A102 monitor runtime in
  ``episode_support/jobs/service_calls/structural_homology_evidence/monitor_runtime.py``) before ``A102ContractBinding``.
- The three HPC job bindings (``.../execution_job_submission/hpc_job_execution``) run
  for real: each mixes in ``execution_job_submission/hpc_job_execution/runtime.HpcJobExecutionRuntime``
  before ``A102ContractBinding`` and is constructed with its own ``HpcJobTools``.
- The three API job bindings (``.../execution_job_submission/api_job_execution``) run
  for real: each mixes in ``execution_job_submission/api_job_execution/runtime_binding.ApiJobExecutionBinding``
  before ``A102ContractBinding`` and is constructed with its own API services.
- The three execution job submission bindings (``.../execution_job_submission``) run for
  real: each mixes in ``execution_job_submission/submission_source.JobSubmissionBinding``
  before ``A102ContractBinding``.
- The five resource-work bindings run for real on the same runtimes: ``resource_work_submission`` on
  ``JobSubmissionBinding``, its HPC/API/local route children on ``HpcJobExecutionRuntime``,
  ``ApiJobExecutionBinding`` and ``A102LocalJobRuntime``, and ``resource_result_acquisition`` on
  ``A102LocalJobRuntime``, each constructed with its own resource-work construction service.
- The seven literature bindings (``published_evidence_assessment`` and the six below it) run
  for real: each subclasses ``published_evidence_assessment/literature_binding.LiteratureBinding``
  and is constructed with its own A102 ``ToolRegistry`` over the shared store and the literature
  continuation declaration ``services['a102']['literature']``.
- HPC allocation execution (``hpc_work_planning/hpc_allocation_execution``) runs for real: it mixes in
  ``hpc_allocation_execution/allocation_runtime.AllocationRuntime`` before ``A102ContractBinding`` and reads
  its HPC services from the ``a102_hpc`` runtime collaborator.
- HPC work planning and resource prediction (``hpc_work_planning``, ``hpc_work_planning/hpc_resource_prediction``)
  run for real: each mixes in ``hpc_work_planning/hpc_runtime.HPCRuntime`` before ``A102ContractBinding``.
- The three result acquisition bindings (``.../execution_result_acquisition``) run for real: each mixes in
  ``execution_result_acquisition/acquisition_source.ResultAcquisitionBinding`` before ``A102ContractBinding``.

``A102ContractBinding`` supplies only the declared identity, slots, forms and entry request; every binding's
``build_controller`` and ``build_episode`` come from its own runtime.

Credits are each binding's own projection, never bounded, clamped or rescaled.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from episode_runtime import Commission, DeclaredField, Field, RecordForm
from method_loop import ClosedRecord, EpisodeGoal, EpisodeRequest, ReportContract

HEAD = 'structural_homology_evidence'

REPORT = MappingProxyType({
    'decision': 'Use the child finding in the parent cycle',
    'measurements': {},
    'information': {'finding': 'What the child established, with its record references'},
})

# (goal, unit, result) per episode kind, keyed by the last binding-path segment.
DECLARATIONS = MappingProxyType({
    HEAD: ('Improve the structural-homology evidence for the assigned target: native structural '
           'correspondence between the target and reference models, graded per comparison',
           'One selected structural tool action, reasoning commit or child investigation',
           'The structural correspondence evidence with its graded comparison records'),
    'published_evidence_assessment': (
        'Improve the published structural evidence received for the assigned question',
        'One literature action or literature child investigation',
        'Graded literature findings with their source records'),
    'evidence_search_strategy_improvement': (
        'Improve the search strategy that finds applicable published structural evidence',
        'One search-strategy action or source-relevance child',
        'Verified source leads and their screening'),
    'source_relevance_assessment': (
        'Improve the relevance assessment of candidate sources',
        'One source-relevance action or examination child',
        'Assessed relevant sources'),
    'source_evidence_examination': (
        'Improve the examination of one source for applicable structural evidence',
        'One source-examination action or extraction child',
        'Graded source evidence with anchors'),
    'table_evidence_extraction': (
        'Improve the extraction of structural evidence from source tables',
        'One table-extraction action', 'Extracted table evidence with anchors'),
    'source_coverage_improvement': (
        'Improve coverage of the examined source', 'One coverage action', 'Covered source passages'),
    'passage_evidence_extraction': (
        'Improve the extraction of structural evidence from targeted passages',
        'One passage-extraction action', 'Extracted passage evidence with anchors'),
    'resource_work_submission': (
        'Improve the submitted resource work for the assigned structural computation',
        'One resource-submission action or execution child', 'Submitted resource work handles'),
    'api_resource_work_execution': (
        'Improve the API execution of assigned resource work', 'One API resource action',
        'API resource outcomes'),
    'local_resource_work_execution': (
        'Improve the local execution of assigned resource work', 'One local resource action',
        'Local resource outcomes'),
    'hpc_resource_work_execution': (
        'Improve the HPC execution of assigned resource work', 'One HPC resource action',
        'HPC resource outcomes'),
    'resource_result_acquisition': (
        'Improve the acquisition of results of submitted resource work', 'One result-acquisition action',
        'Acquired resource results'),
    'execution_job_submission': (
        'Improve the submission of the assigned execution job', 'One launch action or execution child',
        'Launched job handles and handoff records'),
    'api_job_execution': (
        'Improve the API execution of the assigned job', 'One API job action', 'API job outcomes'),
    'local_job_execution': (
        'Improve the local native execution of the assigned job', 'One native job action',
        'Native job outcomes and retained files'),
    'hpc_job_execution': (
        'Improve the HPC native execution of the assigned job', 'One HPC job action',
        'HPC job outcomes and retained files'),
    'execution_progress_assessment': (
        'Improve the assessment of progress of running work', 'One progress observation',
        'Observed progress of the assigned work'),
    'execution_result_acquisition': (
        'Improve the acquisition of results of executed jobs', 'One result-acquisition action',
        'Acquired job results'),
    'hpc_work_planning': (
        'Improve the HPC work plan for the assigned structural computation',
        'One planning action or HPC child', 'An HPC portfolio plan and its launches'),
    'hpc_allocation_execution': (
        'Improve the execution of work inside one HPC allocation', 'One allocation action or child',
        'Allocation work outcomes'),
    'hpc_resource_prediction': (
        'Improve the resource prediction for the assigned HPC work', 'One prediction action',
        'Resource predictions with their basis'),
})

# The A102 subtree's binding paths; child slots are its direct declared children.
PATHS = (
    HEAD,
    HEAD + '/published_evidence_assessment',
    HEAD + '/published_evidence_assessment/evidence_search_strategy_improvement',
    HEAD + '/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment',
    HEAD + '/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination',
    *(HEAD + '/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/' + leaf
      for leaf in ('table_evidence_extraction', 'source_coverage_improvement', 'passage_evidence_extraction')),
    HEAD + '/resource_work_submission',
    *(HEAD + '/resource_work_submission/' + leaf
      for leaf in ('api_resource_work_execution', 'local_resource_work_execution', 'hpc_resource_work_execution')),
    HEAD + '/resource_result_acquisition',
    *(prefix + suffix
      for prefix in (HEAD, HEAD + '/hpc_work_planning', HEAD + '/hpc_work_planning/hpc_allocation_execution')
      for suffix in ('/execution_job_submission', '/execution_job_submission/api_job_execution',
                     '/execution_job_submission/local_job_execution', '/execution_job_submission/hpc_job_execution',
                     '/execution_progress_assessment', '/execution_result_acquisition')),
    HEAD + '/hpc_work_planning',
    HEAD + '/hpc_work_planning/hpc_allocation_execution',
    HEAD + '/hpc_work_planning/hpc_resource_prediction',
)


MONITOR = 'execution_progress_assessment'
HPC_JOB_EXECUTION = 'hpc_job_execution'


def _slots(path):
    slots = {child.rsplit('/', 1)[1]: child for child in PATHS
             if child.rsplit('/', 1)[0] == path and '/' in child}
    if path == HEAD:
        # The head may commission a further structural-homology investigation of its own kind.
        slots[HEAD] = HEAD
    if path.rsplit('/', 1)[-1] == MONITOR:
        # A monitor commissions a monitor of its own kind for a target's dependency (child_roles: monitor).
        slots[MONITOR] = path
    return MappingProxyType(slots)


CHILD_SLOTS = MappingProxyType({path: _slots(path) for path in PATHS})


# The seven literature kinds (published_evidence_assessment/literature_binding.py).
LITERATURE_KINDS = frozenset({
    'published_evidence_assessment', 'evidence_search_strategy_improvement', 'source_relevance_assessment',
    'source_evidence_examination', 'table_evidence_extraction', 'source_coverage_improvement',
    'passage_evidence_extraction'})


@dataclass(frozen=True)
class ContractRecord(ClosedRecord):
    value: Mapping

    def as_record(self):
        return dict(self.value)


CHILD_ASSIGNMENT = RecordForm({
    'scope': Field('record', 'The subject scope fixed by the commissioning A102 parent'),
})
# Every A102 episode returns its own credit (never bounded or rescaled) and its finding.
RETURN = RecordForm({
    'credit': Field('number', "This episode's credit on its own unbounded scale"),
    'finding': Field('record', 'What this episode established, with its record references'),
})


class A102ContractBinding:
    """Contract hooks shared by A102 bindings; values come from this axis's tables."""
    report_contract = REPORT

    def _declared(self):
        if self.binding_path not in CHILD_SLOTS:
            raise LookupError('a102_binding_path_not_declared:' + self.binding_path)
        return DECLARATIONS[self.binding_path.rsplit('/', 1)[-1]]

    @property
    def grain_name(self):
        self._declared()
        return self.binding_path.replace('/', '__')

    @property
    def goal(self):
        return self._declared()[0]

    @property
    def unit(self):
        return self._declared()[1]

    @property
    def result(self):
        return self._declared()[2]

    @property
    def child_slots(self):
        self._declared()
        return CHILD_SLOTS[self.binding_path]

    @staticmethod
    def child_purpose(path):
        """What a parent commissions when it commissions the binding at ``path`` (its declared goal and result)."""
        goal, _, result = DECLARATIONS[path.rsplit('/', 1)[-1]]
        return goal + '; it returns ' + result[0].lower() + result[1:] + ', with its credit.'

    def _kind(self):
        self._declared()
        return self.binding_path.rsplit('/', 1)[-1]

    @property
    def required_collaborators(self):
        return ()

    @property
    def assignment_form(self):
        return CHILD_ASSIGNMENT

    @property
    def return_form(self):
        self._declared()
        return RETURN

    def entry_request(self, entry_input, collaborators, *, parent_goal):
        form = self.assignment_form
        supplied = {name for name, spec in form.fields.items() if not isinstance(spec, DeclaredField)}
        if not isinstance(entry_input, Mapping) or set(entry_input) != supplied:
            raise ValueError('a102_entry_input_requires_exactly:' + self.binding_path + ':' + ','.join(sorted(supplied)))
        assignment = {**{name: entry_input[name] for name in supplied}, **form.declared}
        message = ContractRecord(dict(assignment))
        if parent_goal is None:
            goal = EpisodeGoal.root(objective=self.goal, result_contract=self.return_form.as_record())
            return Commission(EpisodeRequest(goal, message), assignment)
        goal = EpisodeGoal.child(parent_goal, objective=self.goal, result_contract=dict(REPORT))
        return Commission(EpisodeRequest(goal, message, ReportContract(**REPORT)), assignment)

    def restore_controller_input(self, record):
        from .runtime_continuation import A102UnitInput
        return A102UnitInput.from_record(record)


def a102_home_factory(services):
    """Construct every A102 binding (the head subtree's 34) with its own constructor.

    ``services['store']`` is the run's one shared ``gene_annotation_episode.state.Store``.
    ``services['a102']`` supplies A102's construction-time services: ``library`` (the
    head's frozen ``StructuralHomologyEvidenceLibrary``), ``tools`` (the settings of the
    head's own ``a102.tools.ToolRegistry`` over the shared store), ``yield_bindings`` (the
    head's per-task declarations ``A102:<task>``) and ``monitor`` (each monitor's
    ``information_unit`` and ``yield_settings``; the monitors share the head's registry) and
    ``hpc_job_execution`` (``resource``, ``directory``, ``launch_instructions``: the settings of each
    HPC job binding's own ``HpcJobTools``, ``execution_job_submission/hpc_job_execution/runtime.construct``) and
    ``api_job_execution`` (``resources`` and ``continuation`` of the three API job bindings,
    ``execution_job_submission/api_job_execution/configuration.py``) and ``local_job_execution``
    (``resource``, ``coordinator_workspace``, ``state_directory``, ``launch_instruction_directory``,
    ``continuation`` of the three local job bindings, ``episode_support/jobs/local_execution/structural_homology_evidence/local_job_runtime.py``) and the resource-work
    bindings' own services in the same forms: ``hpc_resource_work_execution`` (as ``hpc_job_execution``),
    ``api_resource_work_execution`` (as ``api_job_execution``), ``local_resource_work_execution`` and
    ``resource_result_acquisition`` (each as ``local_job_execution``) and ``literature`` (the seven literature
    bindings' continuation declaration ``{kind, cutoff, parameters, credit_definition}`` for their native
    structural correspondence credit; each literature binding gets its own A102 ``ToolRegistry`` over the
    shared store from ``tools``, ``published_evidence_assessment/literature_binding.py``). A missing one raises.
    Each ``execution_result_acquisition`` binding gets its own A102 ``ToolRegistry`` over the shared store and API
    services over ``api_job_execution['resources']`` (``execution_result_acquisition/acquisition_source.py``).
    """
    from importlib import import_module
    from gene_annotation_episode.episodic_workflow.episode_support.tools.structural_homology_evidence.tools import ToolRegistry
    from .episode import StructuralHomologyEvidenceEpisode
    try:
        store, configuration = services['store'], services['a102']
        library, tools, yield_bindings, monitor = (configuration[name]
                                                   for name in ('library', 'tools', 'yield_bindings', 'monitor'))
    except KeyError as error:
        raise LookupError('a102_home_factory_requires_service:' + str(error.args[0])) from error
    package = __package__.rsplit('.', 1)[0]
    registry = ToolRegistry(store, **tools)
    bindings = [StructuralHomologyEvidenceEpisode(library=library, tool_registry=registry,
                                                  yield_bindings=yield_bindings)]
    for path in PATHS[1:]:
        module = import_module(package + '.' + path.replace('/', '.') + '.episode')
        if path.rsplit('/', 1)[-1] == MONITOR:
            # A monitor's progress.log reads its received log windows through the A102 registry over the store.
            bindings.append(module.MonitorEpisode(tool_registry=registry, **monitor))
        elif path.rsplit('/', 1)[-1] == 'api_job_execution':
            # Each API job binding: its own API services over its own A102 registry on the shared store.
            bindings.append(module.ExecutionEpisode(tool_registry=ToolRegistry(store, **tools),
                                                    configuration=configuration['api_job_execution']))
        else:
            classes = [value for name, value in vars(module).items() if name.endswith('Episode') and isinstance(value, type)
                       and issubclass(value, A102ContractBinding) and value is not A102ContractBinding
                       and getattr(value, 'binding_path', None) == path]
            if len(classes) != 1:
                raise LookupError('a102_binding_class_required:' + path)
            if path.rsplit('/', 1)[-1] == HPC_JOB_EXECUTION:
                # Each HPC job binding gets its own HpcJobTools over the shared store.
                from .execution_job_submission.hpc_job_execution.runtime import construct
                bindings.append(construct(classes[0], store, configuration[HPC_JOB_EXECUTION]))
            elif path.rsplit('/', 1)[-1] in LITERATURE_KINDS:
                # Each literature binding: its own A102 ToolRegistry on the shared store and the literature
                # continuation declaration (published_evidence_assessment/literature_binding.py).
                bindings.append(classes[0](tool_registry=ToolRegistry(store, **tools),
                                           continuation=configuration['literature']))
            elif path.rsplit('/', 1)[-1] == 'local_job_execution':
                # Each local job binding: its own TerminalExecution over the configured local resource
                # (episode_support/jobs/local_execution/structural_homology_evidence/local_job_runtime.A102LocalJobRuntime).
                bindings.append(classes[0](**configuration['local_job_execution']))
            elif path.rsplit('/', 1)[-1] == 'hpc_resource_work_execution':
                # The HPC resource-work binding: its own HpcJobTools over the shared store.
                from .execution_job_submission.hpc_job_execution.runtime import construct
                bindings.append(construct(classes[0], store, configuration['hpc_resource_work_execution']))
            elif path.rsplit('/', 1)[-1] == 'api_resource_work_execution':
                # The API resource-work binding: its own API services over its own A102 registry.
                bindings.append(classes[0](tool_registry=ToolRegistry(store, **tools),
                                           configuration=configuration['api_resource_work_execution']))
            elif path.rsplit('/', 1)[-1] == 'execution_result_acquisition':
                # Each result acquisition binding: its own A102 registry over the shared store and API services
                # over the API job route's resources (execution_result_acquisition/acquisition_source.py).
                bindings.append(classes[0](tool_registry=ToolRegistry(store, **tools),
                                           api_resources=configuration['api_job_execution']['resources']))
            elif path.rsplit('/', 1)[-1] in ('local_resource_work_execution', 'resource_result_acquisition'):
                # Its own TerminalExecution over its configured local resource (A102LocalJobRuntime).
                bindings.append(classes[0](**configuration[path.rsplit('/', 1)[-1]]))
            else:
                bindings.append(classes[0]())
    built = sorted(binding.binding_path for binding in bindings)
    if built != sorted(PATHS):
        raise ValueError('a102_home_factory_bindings_differ_from_declared_paths')
    return tuple(bindings)


def a102_progress_provider(store, *, run_id):
    """The progress monitors' ``a102_progress_provider`` runtime collaborator for one run.

    A102's ``ProgressProvider`` over the run's shared Store, watching A102's own jobs: its job provider
    (``episode_support/jobs/service_calls/structural_homology_evidence/job_provider.JobProvider``) reads the practical jobs this subtree's local and HPC job
    execution bindings recorded in that Store under ``run_id``.
    """
    from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.structural_homology_evidence.job_provider import JobProvider
    from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.structural_homology_evidence.progress_provider import ProgressProvider
    return ProgressProvider(store, run_id=run_id, job_provider=JobProvider(store, run_id=run_id))
