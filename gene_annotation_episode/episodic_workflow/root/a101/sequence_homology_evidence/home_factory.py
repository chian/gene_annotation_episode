"""A101's home factory: construct every binding of the sequence-homology subtree.

``BindingRegistry.compose([a101_home_factory], services)`` calls this with the
construction-time services. Each binding is built through its own constructor;
a missing service raises (nothing is defaulted).

Construction services:
- ``store``: the run's one shared ``gene_annotation_episode.state.Store`` (C4); the head's own
  A101 ``ToolRegistry`` is built over it.
- ``a101``: A101's construction configuration: ``library`` (the frozen
  ``SequenceHomologyEvidenceLibrary``), ``tools`` (the keyword settings of the head's
  ``ToolRegistry``), ``yield_bindings`` (the head's continuation declaration) and
  ``monitor`` (the progress monitor's ``information_unit`` and ``yield_settings``; it
  shares the head's A101 ``ToolRegistry`` over the shared store); ``hpc_job_execution``
  (``resource``, ``directory``, ``launch_instructions``: the settings of the HPC job binding's
  own ``HpcJobTools`` over the shared store, ``execution_job_submission/hpc_job_execution/runtime.construct``);
  ``api_job_execution`` (``resources`` and ``continuation``: the API job binding's own API services over its
  own A101 ``ToolRegistry`` and its completion continuation,
  ``execution_job_submission/api_job_execution/configuration.py``); ``local_job_execution``
  (``resource``, ``coordinator_workspace``, ``state_directory``, ``launch_instruction_directory``,
  ``continuation``: the local job binding's own ``TerminalExecution`` and completion continuation,
  ``episode_support/jobs/local_execution/sequence_homology_evidence/local_job_runtime.py``); the resource-work route bindings' own services, in the same
  forms: ``hpc_resource_work_execution`` (as ``hpc_job_execution``), ``api_resource_work_execution`` (as
  ``api_job_execution``, over its own A101 ``ToolRegistry``), ``local_resource_work_execution`` and
  ``resource_result_acquisition`` (each as ``local_job_execution``: its own ``TerminalExecution`` and
  completion continuation).

The result acquisition binding gets its own A101 ``ToolRegistry`` over the shared store and API services over
``api_job_execution['resources']`` (``execution_result_acquisition/acquisition_source.py``).

The seven literature bindings each get their own A101 ``ToolRegistry`` over the shared store
and the head's ``yield_bindings`` declaration for their credit task
(``published_evidence_assessment/literature_binding.py``).
The progress monitor runs on ``episode_support/jobs/service_calls/sequence_homology_evidence/monitor_runtime.py``; its runtime collaborator
``a101_progress_provider`` is built per run by ``a101_progress_provider(store, run_id=...)`` below.
"""
from __future__ import annotations

from collections.abc import Mapping

from gene_annotation_episode.domain import ContractError

_CONFIGURATION = ('api_job_execution', 'api_resource_work_execution', 'hpc_job_execution',
                  'hpc_resource_work_execution', 'library', 'local_job_execution', 'local_resource_work_execution',
                  'monitor', 'resource_result_acquisition', 'tools', 'yield_bindings')


def a101_home_factory(services):
    from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_homology_evidence.tools import ToolRegistry
    from .episode import SequenceHomologyEvidenceEpisode
    from .execution_job_submission.episode import ExecutionJobSubmissionEpisode
    from .execution_job_submission.api_job_execution.episode import ApiJobExecutionEpisode
    from .execution_job_submission.hpc_job_execution.episode import HpcJobExecutionEpisode
    from .execution_job_submission.hpc_job_execution.runtime import construct as construct_hpc_job_execution
    from .execution_job_submission.local_job_execution.episode import LocalJobExecutionEpisode
    from .execution_progress_assessment.episode import ExecutionProgressAssessmentEpisode
    from .execution_result_acquisition.episode import ExecutionResultAcquisitionEpisode
    from .resource_work_submission.episode import ResourceWorkSubmissionEpisode
    from .resource_work_submission.api_resource_work_execution.episode import ApiResourceWorkExecutionEpisode
    from .resource_work_submission.hpc_resource_work_execution.episode import HpcResourceWorkExecutionEpisode
    from .resource_work_submission.local_resource_work_execution.episode import LocalResourceWorkExecutionEpisode
    from .resource_result_acquisition.episode import ResourceResultAcquisitionEpisode
    from .published_evidence_assessment.episode import PublishedEvidenceAssessmentEpisode
    from .published_evidence_assessment.evidence_search_strategy_improvement.episode import (
        EvidenceSearchStrategyImprovementEpisode)
    from .published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.episode \
        import SourceRelevanceAssessmentEpisode
    from .published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.\
        source_evidence_examination.episode import SourceEvidenceExaminationEpisode
    from .published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.\
        source_evidence_examination.passage_evidence_extraction.episode import PassageEvidenceExtractionEpisode
    from .published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.\
        source_evidence_examination.source_coverage_improvement.episode import SourceCoverageImprovementEpisode
    from .published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.\
        source_evidence_examination.table_evidence_extraction.episode import TableEvidenceExtractionEpisode
    try:
        store, configuration = services['store'], services['a101']
    except KeyError as error:
        raise ContractError('a101_home_factory_requires_service:' + str(error.args[0])) from error
    if not isinstance(configuration, Mapping) or set(configuration) != set(_CONFIGURATION):
        raise ContractError('a101_home_factory_configuration_requires_exactly:' + ','.join(_CONFIGURATION))
    tools = configuration['tools']
    if not isinstance(tools, Mapping):
        raise ContractError('a101_home_factory_tool_settings_must_be_a_mapping')
    monitor = configuration['monitor']
    if not isinstance(monitor, Mapping) or set(monitor) != {'information_unit', 'yield_settings'}:
        raise ContractError('a101_home_factory_monitor_requires_exactly:information_unit,yield_settings')
    registry = ToolRegistry(store, **tools)
    head = SequenceHomologyEvidenceEpisode(library=configuration['library'], tool_registry=registry,
                                           yield_bindings=configuration['yield_bindings'])
    # The monitor's own progress.log reads its received log windows through the A101 registry over the shared store.
    progress = ExecutionProgressAssessmentEpisode(tool_registry=registry, **monitor)
    hpc_job_execution = construct_hpc_job_execution(HpcJobExecutionEpisode, store,
                                                    configuration['hpc_job_execution'])
    # The API job binding's own API services over its own A101 ToolRegistry on the shared store.
    api_job_execution = ApiJobExecutionEpisode(tool_registry=ToolRegistry(store, **tools),
                                               configuration=configuration['api_job_execution'])
    # The local job binding's own TerminalExecution over the configured local resource
    # (episode_support/jobs/local_execution/sequence_homology_evidence/local_job_runtime.A101LocalJobRuntime).
    local_job_execution = LocalJobExecutionEpisode(**configuration['local_job_execution'])
    # The resource-work bindings: each its own route tools from its own construction service.
    resource_work = (
        construct_hpc_job_execution(HpcResourceWorkExecutionEpisode, store,
                                    configuration['hpc_resource_work_execution']),
        ApiResourceWorkExecutionEpisode(tool_registry=ToolRegistry(store, **tools),
                                        configuration=configuration['api_resource_work_execution']),
        LocalResourceWorkExecutionEpisode(**configuration['local_resource_work_execution']),
        ResourceResultAcquisitionEpisode(**configuration['resource_result_acquisition']))
    # Result acquisition: its own A101 ToolRegistry over the shared store and API services over the same
    # resources as the API job route, so each API handoff's resource_id names one of its own services
    # (execution_result_acquisition/acquisition_source.py).
    result_acquisition = ExecutionResultAcquisitionEpisode(
        tool_registry=ToolRegistry(store, **tools),
        api_resources=configuration['api_job_execution']['resources'])
    children = (ExecutionJobSubmissionEpisode, ResourceWorkSubmissionEpisode)
    # Each literature binding: its own A101 ToolRegistry over the shared store and the A101 continuation
    # declaration for its credit task (published_evidence_assessment/literature_binding.py).
    literature = (PublishedEvidenceAssessmentEpisode, EvidenceSearchStrategyImprovementEpisode,
                  SourceRelevanceAssessmentEpisode, SourceEvidenceExaminationEpisode, PassageEvidenceExtractionEpisode,
                  SourceCoverageImprovementEpisode, TableEvidenceExtractionEpisode)
    return (head, progress, hpc_job_execution, api_job_execution, local_job_execution, *resource_work,
            result_acquisition, *(child() for child in children),
            *(binding(tool_registry=ToolRegistry(store, **tools), yield_bindings=configuration['yield_bindings'])
              for binding in literature))


def a101_progress_provider(store, *, run_id):
    """The progress monitor's ``a101_progress_provider`` runtime collaborator for one run.

    A101's ``ProgressProvider`` over the run's shared Store, watching A101's own jobs: its job provider
    (``episode_support/jobs/service_calls/sequence_homology_evidence/job_provider.JobProvider``) reads the practical jobs this subtree's local and HPC job
    execution bindings recorded in that Store under ``run_id``.
    """
    from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.sequence_homology_evidence.job_provider import JobProvider
    from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.sequence_homology_evidence.progress_provider import ProgressProvider
    return ProgressProvider(store, run_id=run_id, job_provider=JobProvider(store, run_id=run_id))
