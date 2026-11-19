"""The A103 home factory: construct every binding of the gene-context-evidence subtree.

``factory(services)`` is passed to ``episode_runtime.BindingRegistry.compose``. It
builds A103's own tool registry over the run's shared Store (contract ruling C4b:
tools are not a runtime collaborator) and constructs each of the 34 bindings with
its own constructor. Required keys, nothing defaulted:

- ``store``: the run's one shared ``gene_annotation_episode.state.Store``;
- ``a103_tools``: keyword operands of ``A103ToolRegistry`` (``a103_work_directory`` and
  ``target_genomic_sources``, both required);
- ``a103_head``: keyword operands of the head ``GeneContextEvidenceEpisode``
  (``library``, ``child_roles``, ``yield_bindings``);
- ``a103_monitor``: keyword operands of the three ``MonitorEpisode`` bindings
  (``information_unit``, ``yield_settings``);
- ``a103_local_job_execution``: keyword operands of the three local job execution
  bindings (``episode_support/jobs/local_execution/gene_context_evidence/local_job_runtime.A103LocalJobRuntime``: ``resource``,
  ``coordinator_workspace``, ``state_directory``, ``launch_instruction_directory``,
  ``continuation``);
- ``a103_hpc_job_execution``: the settings of the three HPC job execution bindings' own
  ``HpcJobTools`` over the shared store (``resource``, ``directory``, ``launch_instructions``;
  ``execution_job_submission/hpc_job_execution/runtime.construct``);
- ``a103_api_job_execution``: ``resources`` and ``continuation`` of the three API job execution
  bindings, each over its own ``A103ToolRegistry`` (``execution_job_submission/api_job_execution/configuration.py``);
- ``a103_hpc_resource_work_execution``, ``a103_api_resource_work_execution``: the HPC and API resource-work
  route bindings' own services, in the forms of ``a103_hpc_job_execution`` and ``a103_api_job_execution``;
- ``a103_local_resource_work_execution``, ``a103_resource_result_acquisition``: keyword operands of the local
  resource-work route binding and of resource result acquisition, each its own ``A103LocalJobRuntime``
  (the form of ``a103_local_job_execution``).
- The three ``execution_result_acquisition`` bindings each get their own ``A103ToolRegistry`` (``a103_tools``) and
  API services over ``a103_api_job_execution['resources']`` (``execution_result_acquisition/acquisition_source.py``).

The seven literature bindings each get their own ``A103ToolRegistry`` (``a103_tools``) and the
head's ``yield_bindings`` declaration for the measured-context credit
(``published_evidence_assessment/literature_binding.py``).

The three HPC bindings (``HPC_HOMES``: planning, resource prediction and allocation execution) take no
operands and run for real: their HPC services are the ``a103_hpc`` runtime collaborator
(``hpc_work_planning/hpc_runtime.py``, ``hpc_work_planning/hpc_allocation_execution/allocation_runtime.py``).

``resource_work_submission`` and the three ``execution_job_submission`` bindings take no operands (their route
children are commissioned through the runner).
"""
from __future__ import annotations

from collections.abc import Mapping
from importlib import import_module

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.'
KEYS = ('store', 'a103_tools', 'a103_head', 'a103_monitor', 'a103_local_job_execution', 'a103_hpc_job_execution',
        'a103_api_job_execution', 'a103_local_resource_work_execution', 'a103_hpc_resource_work_execution',
        'a103_api_resource_work_execution', 'a103_resource_result_acquisition')

_LEVELS = ('', 'hpc_work_planning/', 'hpc_work_planning/hpc_allocation_execution/')
EXECUTION_HOMES = tuple(level + home for level in _LEVELS
                        for home in ('execution_job_submission',))
RESULT_ACQUISITION_HOMES = tuple(level + 'execution_result_acquisition' for level in _LEVELS)
API_JOB_HOMES = tuple(level + 'execution_job_submission/api_job_execution' for level in _LEVELS)
HPC_JOB_HOMES = tuple(level + 'execution_job_submission/hpc_job_execution' for level in _LEVELS)
LOCAL_JOB_HOMES = tuple(level + 'execution_job_submission/local_job_execution' for level in _LEVELS)
MONITOR_HOMES = tuple(level + 'execution_progress_assessment' for level in _LEVELS)
HPC_HOMES = ('hpc_work_planning', 'hpc_work_planning/hpc_resource_prediction', 'hpc_work_planning/hpc_allocation_execution')
RESOURCE_HOMES = ('resource_work_submission', 'resource_work_submission/api_resource_work_execution',
                  'resource_work_submission/local_resource_work_execution',
                  'resource_work_submission/hpc_resource_work_execution', 'resource_result_acquisition')
_PAGE = ('published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/'
         'source_evidence_examination')
LITERATURE_HOMES = ('published_evidence_assessment', 'published_evidence_assessment/evidence_search_strategy_improvement',
                    'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment',
                    _PAGE, _PAGE + '/passage_evidence_extraction', _PAGE + '/source_coverage_improvement',
                    _PAGE + '/table_evidence_extraction')


def _binding_type(home, name):
    module = 'episode' if not home else home.replace('/', '.') + '.episode'
    return getattr(import_module(PACKAGE + module), name)


def factory(services):
    if not isinstance(services, Mapping):
        raise TypeError('a103_home_services_must_be_a_mapping')
    missing = [key for key in KEYS if key not in services]
    if missing:
        raise LookupError('a103_home_service_required:' + ','.join(missing))
    from gene_annotation_episode.episodic_workflow.episode_support.tools.gene_context_evidence.evidence_operations import A103ToolRegistry
    tools = A103ToolRegistry(services['store'], **services['a103_tools'])
    head = _binding_type('', 'GeneContextEvidenceEpisode')(tool_registry=tools, **services['a103_head'])
    monitors = tuple(_binding_type(home, 'MonitorEpisode')(tool_registry=tools, **services['a103_monitor'])
                     for home in MONITOR_HOMES)
    local_jobs = tuple(_binding_type(home, 'ExecutionEpisode')(**services['a103_local_job_execution'])
                       for home in LOCAL_JOB_HOMES)
    from .execution_job_submission.hpc_job_execution.runtime import construct
    hpc_jobs = tuple(construct(_binding_type(home, 'ExecutionEpisode'), services['store'],
                               services['a103_hpc_job_execution']) for home in HPC_JOB_HOMES)
    # Each API job binding: its own API services over its own A103ToolRegistry on the shared store.
    api_jobs = tuple(_binding_type(home, 'ExecutionEpisode')(
        tool_registry=A103ToolRegistry(services['store'], **services['a103_tools']),
        configuration=services['a103_api_job_execution']) for home in API_JOB_HOMES)
    # Each literature binding: its own A103ToolRegistry on the shared store and the head's A103 continuation
    # declaration for the measured-context credit (published_evidence_assessment/literature_binding.py).
    literature = tuple(_binding_type(home, 'LiteratureEpisode')(
        tool_registry=A103ToolRegistry(services['store'], **services['a103_tools']),
        yield_bindings=services['a103_head']['yield_bindings']) for home in LITERATURE_HOMES)
    # The resource-work bindings: each its own route tools from its own construction service.
    resource_work = (
        _binding_type('resource_work_submission', 'ResourceEpisode')(),
        construct(_binding_type('resource_work_submission/hpc_resource_work_execution', 'ResourceEpisode'),
                  services['store'], services['a103_hpc_resource_work_execution']),
        _binding_type('resource_work_submission/api_resource_work_execution', 'ResourceEpisode')(
            tool_registry=A103ToolRegistry(services['store'], **services['a103_tools']),
            configuration=services['a103_api_resource_work_execution']),
        _binding_type('resource_work_submission/local_resource_work_execution', 'ResourceEpisode')(
            **services['a103_local_resource_work_execution']),
        _binding_type('resource_result_acquisition', 'ResourceEpisode')(**services['a103_resource_result_acquisition']))
    # Each result acquisition binding: its own A103ToolRegistry on the shared store and API services over the API
    # job route's resources (execution_result_acquisition/acquisition_source.py).
    acquisitions = tuple(_binding_type(home, 'ExecutionEpisode')(
        tool_registry=A103ToolRegistry(services['store'], **services['a103_tools']),
        api_resources=services['a103_api_job_execution']['resources']) for home in RESULT_ACQUISITION_HOMES)
    declared = tuple(_binding_type(home, name)() for homes, name in (
        (EXECUTION_HOMES, 'ExecutionEpisode'), (HPC_HOMES, 'HPCEpisode')) for home in homes)
    return (head, *monitors, *local_jobs, *hpc_jobs, *api_jobs, *literature, *resource_work, *acquisitions,
            *declared)


def a103_progress_provider(store, *, run_id):
    """The progress monitors' ``a103_progress_provider`` runtime collaborator for one run.

    A103's ``ProgressProvider`` over the run's shared Store, watching A103's own jobs: its job provider
    (``episode_support/jobs/service_calls/gene_context_evidence/job_provider.JobProvider``) reads the practical jobs this subtree's local and HPC job
    execution bindings recorded in that Store under ``run_id``.
    """
    from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.gene_context_evidence.job_provider import JobProvider
    from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.gene_context_evidence.progress_provider import ProgressProvider
    return ProgressProvider(store, run_id=run_id, job_provider=JobProvider(store, run_id=run_id))
