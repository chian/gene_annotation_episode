"""Private launch_api yield behavior for A106."""
from __future__ import annotations
from .execution_contracts import plain

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
        return self._launch_api_yield_controller(context, initial_credit, epoch)

    def _launch_api_yield_controller(self, context, initial_credit, epoch):
        from gene_annotation_episode.episodic_workflow.root.a106.numerical import YieldController, YieldParameters
        from gene_annotation_episode.episodic_workflow.root.a106.practical_yield import PracticalYieldEstimator
        request = self._validate_request(plain(context.assignment))
        profile = self._task_yield_profile('launch_api:' + self._request_yield_class(request))
        return YieldController(epoch, initial_credit, profile['cutoff'], YieldParameters(**profile['parameters']), estimate_with_context=PracticalYieldEstimator(lambda proof: self.verify_completion(context, proof)))

    def practical_estimator(self, context):
        from gene_annotation_episode.episodic_workflow.root.a106.practical_yield import PracticalYieldEstimator
        return PracticalYieldEstimator(lambda proof: self.verify_completion(context, proof))
