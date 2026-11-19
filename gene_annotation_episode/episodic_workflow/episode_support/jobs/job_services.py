"""The job services of a run, as the ``services`` collaborator wants them: a name and a factory for each.

A run's caller gives ``link`` and ``resume`` a mapping from each service name its episodes declare to a
zero-argument factory. ``job_services`` builds that mapping for the job services from the caller's configuration.
Each service is built on its first use in the run and again after a resume; what must outlast that (a job, the
estimate table, the native event ledger) is on disk under the directories named here.

| Name | Service | Module |
|---|---|---|
| ``job_access`` | ``JobAccess``: launch, check, fetch, cancel and ``run`` of jobs, their rows in custody | ``episode_runtime/job_access.py`` |
| ``estimate_table`` | ``EstimateTable``: expected and obtained outcomes of costly actions; observations | ``episode_runtime/estimate_table.py`` |
| ``native_events`` | ``NativeEvents``: the native event ledger; waits whose receipts come into custody | ``native_events.py`` |
| ``resource_adapter``, ``resources`` | ``ResourceAdapters``: one ``JobResourceAdapter`` per declared, bound resource | ``episode_runtime/resource_adapters.py``, ``job_resource_adapter.py`` |
| ``instruction_libraries`` | ``InstructionLibraries``: the frozen launch instructions and tool knowledge | ``instruction_libraries.py`` |

The job-access service and the resource adapters of a run share their routes: the adapters are built over the
run's one ``JobAccess``. The HPC ledger is not a service: it is the declared work table of ``hpc_ledger.py``.

The configuration names every part; nothing has a default:

- ``local``: ``{resource_id: {'workspace', 'policy' ({'memory_bytes', 'scratch_bytes'}), 'cpu_threads'}}``;
- ``pbs``: ``{resource_id: <the configuration of PbsSshRoute>}``;
- ``capabilities``: the declared capabilities, one per resource the run knows of;
- ``event_ledger_directory``, ``estimate_table_path``, ``launch_instructions_directory``,
  ``tool_knowledge_directory``.
"""
from __future__ import annotations

from episode_runtime.estimate_table import EstimateTable
from episode_runtime.job_access import JobAccess
from episode_runtime.resource_adapters import ResourceAdapters
from gene_annotation_episode.local_job_policy import LocalJobPolicy

from .instruction_libraries import InstructionLibraries
from .job_resource_adapter import JobResourceAdapter
from .local_job_route import LocalJobRoute
from .native_events import NativeEvents
from .pbs_job_route import PbsSshRoute

CONFIGURATION = ('local', 'pbs', 'capabilities', 'event_ledger_directory', 'estimate_table_path',
                 'launch_instructions_directory', 'tool_knowledge_directory')


def job_services(configuration):
    """``{service name: factory}`` for the job services of one run."""
    if not isinstance(configuration, dict) or set(configuration) != set(CONFIGURATION):
        raise ValueError('job_services_configuration_requires_exactly:' + ','.join(CONFIGURATION))
    shared = {}

    def job_access():
        # One JobAccess per run: the resource adapters act through the same object the episodes are handed.
        if 'job_access' not in shared:
            routes = {resource_id: LocalJobRoute(
                settings['workspace'], LocalJobPolicy.from_config(settings['policy']),
                configuration['event_ledger_directory'], resource_id=resource_id,
                cpu_threads=settings['cpu_threads']) for resource_id, settings in configuration['local'].items()}
            for resource_id, settings in configuration['pbs'].items():
                if resource_id in routes:
                    raise ValueError('job_resource_id_bound_twice:' + resource_id)
                routes[resource_id] = PbsSshRoute(settings, resource_id=resource_id)
            shared['job_access'] = JobAccess(routes)
        return shared['job_access']

    def resource_adapters():
        if 'resource_adapters' not in shared:
            jobs = job_access()
            bound = {item['resource_id'] for item in jobs.resources()}
            shared['resource_adapters'] = ResourceAdapters(configuration['capabilities'], {
                capability['resource_id']: JobResourceAdapter(jobs, capability)
                for capability in configuration['capabilities'] if capability['resource_id'] in bound})
        return shared['resource_adapters']

    return {
        'job_access': job_access,
        'estimate_table': lambda: EstimateTable(configuration['estimate_table_path']),
        'native_events': lambda: NativeEvents(configuration['event_ledger_directory']),
        'resource_adapter': resource_adapters,
        'resources': resource_adapters,
        'instruction_libraries': lambda: InstructionLibraries(configuration['launch_instructions_directory'],
                                                              configuration['tool_knowledge_directory']),
    }


__all__ = ['CONFIGURATION', 'job_services']
