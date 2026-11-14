"""Private results yield behavior for A106."""
from __future__ import annotations
from .execution_contracts import RESULTS_SCHEMA, checked, plain

class ExecutionEpisodeYield:

    @staticmethod
    def _request_yield_class(request):
        request = plain(request)
        parts = ['api', request.get('service', 'unknown')]
        for field in ('algorithm', 'database'):
            if field in request:
                parts.append(request[field])
        return '_'.join(parts) + '_handoff'

    def _task_yield_profile(self, key):
        binding = self.task_yield_profiles.get(key)
        if binding is None:
            raise ValueError('execution_original_task_yield_profile_required:' + key)
        return binding

    def yield_controller(self, context, initial_credit, epoch):
        self.credit_kind(context.role)
        if not self.private_yield_binding:
            raise ValueError('execution_private_yield_binding_not_enabled')
        return self._results_yield_controller(context, initial_credit, epoch)

    def _results_yield_controller(self, context, initial_credit, epoch):
        from gene_annotation_episode.episodic_workflow.root.a106.numerical import YieldController, YieldParameters
        from gene_annotation_episode.episodic_workflow.root.a106.practical_yield import PracticalYieldEstimator
        assignment = checked(context.assignment, RESULTS_SCHEMA, 'invalid_execution_results_assignment')
        target = self._target(context)
        selector = self._selector(assignment, target)
        service = target.get('service') or target.get('assignment', {}).get('service')
        if not isinstance(service, str) or not service:
            raise ValueError('results_original_api_service_required_for_yield')
        key = 'results:api_' + service + ('_' + selector['version'] if 'version' in selector else '')
        profile = self._task_yield_profile(key)
        return YieldController(epoch, initial_credit, profile['cutoff'], YieldParameters(**profile['parameters']), estimate_with_context=PracticalYieldEstimator(lambda proof: self.verify_completion(context, proof)))

    def practical_estimator(self, context):
        from gene_annotation_episode.episodic_workflow.root.a106.practical_yield import PracticalYieldEstimator
        return PracticalYieldEstimator(lambda proof: self.verify_completion(context, proof))
