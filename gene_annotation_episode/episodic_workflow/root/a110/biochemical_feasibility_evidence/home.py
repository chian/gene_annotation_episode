"""The A110 home factory: construct every binding of the A110 subtree.

``home_factory(services)`` is the factory ``episode_runtime.BindingRegistry.compose``
calls. Nothing is defaulted:

- ``services['store']``: the run's shared Store (``gene_annotation_episode.state.Store``,
  ruling C4); the same object is the runtime ``store`` collaborator;
- ``services['a110']['tool_registry']``: the keyword operands of the A110
  ``ToolRegistry`` (clients, document executables, job limits, ...). Every
  model-driven A110 binding (the head and the seven literature bindings) gets its
  own registry built here over that Store;
- ``services['a110_local_job_execution']``: the keyword operands of the three local
  job execution bindings (``episode_support/jobs/local_execution/biochemical_feasibility_evidence/local_job_runtime.A110LocalJobRuntime``:
  ``resource``, ``coordinator_workspace``, ``state_directory``,
  ``launch_instruction_directory``);
- ``services['a110_hpc_job_execution']``: the settings of the three HPC job execution
  bindings' own ``HpcJobTools`` over that Store (``resource``, ``directory``,
  ``launch_instructions``; ``execution_job_submission/hpc_job_execution/runtime.construct``).

- ``services['a110_progress_monitor']``: the three progress monitors' ``information_unit``
  and ``yield_settings``; each monitor gets its own A110 ``ToolRegistry`` over that Store
  (``runtime_monitor``).

- the three job submissions (``execution_job_submission/submission_source``) and HPC work planning,
  resource prediction and allocation execution (``hpc_work_planning/hpc_runtime``,
  ``hpc_allocation_execution/allocation_runtime``) take no operand; they read their runtime
  collaborators (``a110_hpc`` for the HPC bindings).
"""
from __future__ import annotations

from collections.abc import Mapping

from gene_annotation_episode.state import Store

_PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence'
_LITERATURE = (
    ('published_evidence_assessment', 'PublishedEvidenceAssessmentEpisode'),
    ('published_evidence_assessment.evidence_search_strategy_improvement', 'EvidenceSearchStrategyImprovementEpisode'),
    ('published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment',
     'SourceRelevanceAssessmentEpisode'),
    ('published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.'
     'source_evidence_examination', 'SourceEvidenceExaminationEpisode'),
    ('published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.'
     'source_evidence_examination.table_evidence_extraction', 'TableEvidenceExtractionEpisode'),
    ('published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.'
     'source_evidence_examination.source_coverage_improvement', 'SourceCoverageImprovementEpisode'),
    ('published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.'
     'source_evidence_examination.passage_evidence_extraction', 'PassageEvidenceExtractionEpisode'),
)
_EXECUTION = (('execution_job_submission', 'ExecutionJobSubmissionEpisode'),)
# The three progress monitors (runtime_monitor.A110MonitorBinding).
_MONITORS = tuple((level + 'execution_progress_assessment', 'ExecutionProgressAssessmentEpisode')
                  for level in ('', 'hpc_work_planning.', 'hpc_work_planning.hpc_allocation_execution.'))
_NO_OPERAND = (
    *_EXECUTION,
    ('hpc_work_planning', 'HpcWorkPlanningEpisode'),
    ('hpc_work_planning.hpc_resource_prediction', 'HpcResourcePredictionEpisode'),
    ('hpc_work_planning.hpc_allocation_execution', 'HpcAllocationExecutionEpisode'),
    *(('hpc_work_planning.' + module, name) for module, name in _EXECUTION),
    *(('hpc_work_planning.hpc_allocation_execution.' + module, name) for module, name in _EXECUTION),
)
# The three local job executions (episode_support/jobs/local_execution/biochemical_feasibility_evidence/local_job_runtime.A110LocalJobRuntime).
_LOCAL_JOBS = tuple((level + 'execution_job_submission.local_job_execution', 'LocalJobExecutionEpisode')
                    for level in ('', 'hpc_work_planning.', 'hpc_work_planning.hpc_allocation_execution.'))
# The three result acquisitions (execution_result_acquisition/acquisition_source.ResultAcquisitionBinding).
_RESULT_ACQUISITIONS = tuple((level + 'execution_result_acquisition', 'ExecutionResultAcquisitionEpisode')
                             for level in ('', 'hpc_work_planning.', 'hpc_work_planning.hpc_allocation_execution.'))
# The three HPC job executions (execution_job_submission/hpc_job_execution/runtime.HpcJobExecutionRuntime).
_HPC_JOBS = tuple((level + 'execution_job_submission.hpc_job_execution', 'HpcJobExecutionEpisode')
                  for level in ('', 'hpc_work_planning.', 'hpc_work_planning.hpc_allocation_execution.'))


def _binding_class(module, name):
    from importlib import import_module
    return getattr(import_module(_PACKAGE + '.' + module + '.episode'), name)


def home_factory(services):
    if 'store' not in services:
        raise KeyError('a110_home_store_required')
    store = services['store']
    if not isinstance(store, Store):
        raise TypeError('a110_home_store_must_be_the_shared_store')
    if 'a110' not in services:
        raise KeyError('a110_home_operands_required')
    operands = services['a110']
    if not isinstance(operands, Mapping) or set(operands) != {'tool_registry'}:
        raise KeyError('a110_home_operands_must_be_exactly_tool_registry')
    if 'a110_local_job_execution' not in services:
        raise KeyError('a110_home_local_job_execution_operands_required')
    local_jobs = services['a110_local_job_execution']
    if not isinstance(local_jobs, Mapping):
        raise TypeError('a110_home_local_job_execution_operands_must_be_a_mapping')
    if 'a110_hpc_job_execution' not in services:
        raise KeyError('a110_home_hpc_job_execution_settings_required')
    if 'a110_progress_monitor' not in services:
        raise KeyError('a110_home_progress_monitor_settings_required')
    monitor = services['a110_progress_monitor']
    if not isinstance(monitor, Mapping) or set(monitor) != {'information_unit', 'yield_settings'}:
        raise KeyError('a110_home_progress_monitor_settings_must_be_exactly_information_unit_and_yield_settings')
    from gene_annotation_episode.episodic_workflow.episode_support.tools.biochemical_feasibility_evidence.tools import ToolRegistry
    from .episode import BiochemicalFeasibilityEvidenceEpisode
    from .execution_job_submission.hpc_job_execution.runtime import construct as construct_hpc_job

    def registry():
        return ToolRegistry(store, **dict(operands['tool_registry']))
    return (BiochemicalFeasibilityEvidenceEpisode(registry()),
            *(_binding_class(module, name)(registry()) for module, name in _LITERATURE),
            *(_binding_class(module, name)(**local_jobs) for module, name in _LOCAL_JOBS),
            *(construct_hpc_job(_binding_class(module, name), store, services['a110_hpc_job_execution'])
              for module, name in _HPC_JOBS),
            *(_binding_class(module, name)(tool_registry=registry(), **dict(monitor)) for module, name in _MONITORS),
            # Each result acquisition: its own A110 ToolRegistry over the shared store; A110 has no API job route,
            # so it is given no API resource.
            *(_binding_class(module, name)(tool_registry=registry(), api_resources={})
              for module, name in _RESULT_ACQUISITIONS),
            *(_binding_class(module, name)() for module, name in _NO_OPERAND))


def a110_progress_provider(store, *, run_id):
    """The progress monitors' ``a110_progress_provider`` runtime collaborator for one run.

    A110's ``ProgressProvider`` over the run's shared Store, watching A110's own jobs: its job provider
    (``episode_support/jobs/service_calls/biochemical_feasibility_evidence/job_provider.JobProvider``) reads the practical jobs this subtree's local and HPC job
    execution bindings recorded in that Store under ``run_id``.
    """
    from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.biochemical_feasibility_evidence.job_provider import JobProvider
    from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.biochemical_feasibility_evidence.progress_provider import ProgressProvider
    return ProgressProvider(store, run_id=run_id, job_provider=JobProvider(store, run_id=run_id))
