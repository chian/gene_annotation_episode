"""Private launch_hpc yield behavior for A102."""
from __future__ import annotations
from .contracts import RESULTS_SCHEMA, checked, plain

class ExecutionEpisodeYield:

    @staticmethod
    def _request_yield_class(request):
        """Classify the original execution request without generated IDs."""
        request = plain(request)
        version = request.get('version')
        if version != 'practical_assignment_v1':
            if version in ('api_execution_assignment_v1', 'api_service_assignment_v1'):
                parts = ['api', request.get('service', 'unknown')]
                for field in ('algorithm', 'database'):
                    if field in request:
                        parts.append(request[field])
                return '_'.join(parts) + '_handoff'
            return 'compact_' + str(version)
        requested = request['requested_job']
        native = sorted((key for key in requested if key.startswith('native_')))
        parts = ['practical', request['resource_kind']]
        parts.extend(native)
        parts.append({'usable_handoff': 'handoff', 'completed_job_outputs': 'outputs'}[request['endpoint']])
        return '_'.join(parts)

    def _task_yield_profile(self, key):
        binding = self.task_yield_profiles.get(key)
        if binding is None:
            raise ValueError('execution_original_task_yield_profile_required:' + key)
        return binding

    def yield_controller(self, context, initial_credit, epoch):
        """Choose only this admitted execution task's own yield binding."""
        self.credit_kind(context.role)
        if not self.private_yield_binding:
            raise ValueError('execution_private_yield_binding_not_enabled')
        return self._launch_hpc_yield_controller(context, initial_credit, epoch)

    def _launch_hpc_yield_controller(self, context, initial_credit, epoch):
        from gene_annotation_episode.episodic_workflow.root.a102.numerical import YieldController, YieldParameters
        from gene_annotation_episode.episodic_workflow.root.a102.practical_yield import PracticalYieldEstimator
        request = self._validate_request(plain(context.assignment))
        profile = self._task_yield_profile('launch_hpc:' + self._request_yield_class(request))
        return YieldController(epoch, initial_credit, profile['cutoff'], YieldParameters(**profile['parameters']), estimate_with_context=PracticalYieldEstimator(lambda proof: self.verify_completion(context, proof)))

    def practical_estimator(self, context):
        return self._delegate(context).practical_estimator(context)
