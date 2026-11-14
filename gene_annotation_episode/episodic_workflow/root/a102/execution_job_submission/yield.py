"""Private launch yield behavior for A102."""
from __future__ import annotations
from .execution_contracts import (RESULTS_SCHEMA, checked, plain)

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
        native = sorted(key for key in requested if key.startswith('native_'))
        parts = ['practical', request['resource_kind']]
        parts.extend(native)
        parts.append({'usable_handoff': 'handoff',
            'completed_job_outputs': 'outputs'}[request['endpoint']])
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
        return self._launch_yield_controller(context, initial_credit, epoch)

    def _launch_yield_controller(self, context, initial_credit, epoch):
        """Cap one next handoff by original request slots still uncredited."""
        from gene_annotation_episode.episodic_workflow.root.a102.numerical import (BoundedYieldController, NumericBand, YieldController,
            YieldEstimate, YieldParameters)
        assignment = plain(context.assignment)
        if 'requests' not in assignment:
            raise ValueError('launch_original_request_map_required')
        original = self._launch(assignment, scope=context.scope)
        eligible = {resource_id for resource_id in original['requests']
            if self._permitted(original, resource_id)}
        selected, handoffs, _ = self._received(context)
        initial = set(selected['initial_known_record_refs'])
        already_received = {target['resource_id'] for reference, target in handoffs.items()
            if reference in initial and self.job_progress_provider.targets.usable_handoff(target)}
        remaining = len(eligible - already_received) * self.handoff_unit
        if remaining:
            classes = sorted(self._request_yield_class(original['requests'][resource_id])
                for resource_id in eligible)
            profile = self._task_yield_profile('launch:' + '+'.join(classes))
            return BoundedYieldController(epoch, initial_credit, profile['cutoff'], remaining,
                YieldParameters(**profile['parameters']))
        if initial_credit != 0:
            raise ValueError('launch_no_uncredited_requests_but_nonzero_initial_credit')
        def no_remaining_requests(history, parameters, contexts):
            if any(value != 0 for value in history):
                raise ValueError('launch_credit_without_original_uncredited_request')
            return YieldEstimate(len(history), NumericBand.exact(0), parameters,
                {'remaining_original_request_credit': 0., 'original_request_count': len(eligible)},
                estimator_binding={'version': 'launch_original_request_exhaustion_v1',
                    'forecast': 'exact_zero_when_every_eligible_original_request_was_in_initial_handoffs'})
        return YieldController(epoch, initial_credit, 0., YieldParameters(),
            estimate_with_context=no_remaining_requests)

    def practical_estimator(self, context):
        from gene_annotation_episode.episodic_workflow.root.a102.practical_yield import PracticalYieldEstimator
        return PracticalYieldEstimator(lambda proof: self.verify_completion(context, proof))
