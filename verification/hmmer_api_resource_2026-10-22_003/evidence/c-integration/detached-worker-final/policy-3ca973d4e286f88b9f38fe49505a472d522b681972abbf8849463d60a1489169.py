from gene_annotation_episode.case_execution import PolicyBindings
from gene_annotation_episode.numerical import YieldController, YieldEstimate, NumericBand

def create_policy(parameters):
    def task_credit(store, scope):
        return parameters['score']
    def scientific_child_credit(store, scope, **kwargs):
        return parameters['score']
    def job_credit(store, **kwargs):
        return parameters['score']
    def fixture_estimate(history, settings, contexts):
        return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= parameters.get('stop_after', 1) else 1), settings,
            {'kind':'fixture_only_not_production'})
    def controller(path, initial):
        return YieldController(str(path), initial, parameters['cost'], parameters['numerical'],
            estimate_with_context=fixture_estimate)
    return PolicyBindings(task_credit, scientific_child_credit, job_credit, job_credit, controller,
        {'kind':'fixture_constant','score':parameters['score']},
        {'kind':'fixture_constant','score':parameters['score']},
        {'kind':'fixture_constant','score':parameters['score']},
        {'kind':'fixture_constant','score':parameters['score']},
        {'kind':'fixture_estimator','cost':parameters['cost'],'numerical':parameters['numerical']})

from dataclasses import replace
from pathlib import Path
from gene_annotation_episode.assembled_service_setup import bind_assembled_services_with_public_search_timing
from gene_annotation_episode.resource_estimation import ResourceToolEstimator

_base_policy = create_policy

def create_policy(parameters):
    base = _base_policy(parameters)
    operands = parameters['api_services']
    def services(store, *, run_id, directory, job_episodes, resource_estimator,
                 tool_catalog, tool_registry):
        return bind_assembled_services_with_public_search_timing(store, run_id=run_id,
            api_timing=operands['api_timing'],
            directory=directory, job_episodes=job_episodes, resource_estimator=resource_estimator,
            source_directory=Path(operands['source_directory']), tool_catalog=tool_catalog,
            tool_retrieval=operands['tool_retrieval'],
            scientific_child_roles=tuple(operands['scientific_child_roles']),
            handoff_unit=3.25, acquired_record_unit=.375, monitoring_information_unit=.5,
            literature_outcome_page_size=7, monitor_outcome_page_size=13,
            log_window_bytes=123, log_roles=('native_stderr',),
            public_search_registry=operands['registry'], tool_registry=tool_registry)
    return replace(base, initial_known_record_refs=[], episode_record_receipts=True,
        annotation_child_roles=tuple(operands['scientific_child_roles']),
        execution_planning_roles=('annotation', 'scientific_process'),
        resource_estimator=ResourceToolEstimator.with_reported_results(),
        episode_service_factory=services, episode_service_binding=operands,
        episode_service_inputs='actual_tool_registry_v1')
