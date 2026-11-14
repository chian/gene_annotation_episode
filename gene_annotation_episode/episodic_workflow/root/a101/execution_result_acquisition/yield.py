"""Private results yield behavior for A101."""
from __future__ import annotations
from .execution_contracts import RESULTS_SCHEMA, checked, plain

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
        return self._results_yield_controller(context, initial_credit, epoch)

    def _results_yield_controller(self, context, initial_credit, epoch):
        from gene_annotation_episode.episodic_workflow.root.a101.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters, estimate_bounded_credit_yield
        from gene_annotation_episode.episodic_workflow.root.a101.practical_yield import PracticalYieldEstimator
        assignment = checked(context.assignment, RESULTS_SCHEMA, 'invalid_execution_results_assignment')
        target = self._target(context)
        selector = self._selector(assignment, target)
        if target['resource_kind'] != 'api' and 'version' not in selector:
            requested = self._windows(selector)
            if not requested:
                raise ValueError('results_original_selector_has_no_requested_bytes')
            if any((length is None for _, length in requested.values())):
                key = 'native_unbounded_' + target['resource_kind']
                if key not in self.results_yield_profiles:
                    raise ValueError('results_original_task_yield_profile_required:' + key)
                profile = self.results_yield_profiles[key]
                return YieldController(epoch, initial_credit, profile['cutoff'], YieldParameters(**profile['parameters']))
            profile = self._task_yield_profile('results:native_finite_' + target['resource_kind'])
            selected, _, results = self._received(context)
            initial = set(selected['initial_known_record_refs'])
            baseline = {ref: body for ref, body in results.items() if ref in initial}
            original_fraction = self._generic_result_selector_progress(context, baseline, set())
            remaining = self.acquired_record_unit * (1.0 - original_fraction)
            if remaining == 0 and initial_credit != 0:
                raise ValueError('results_no_uncredited_bytes_but_nonzero_initial_credit')
            endpoint = PracticalYieldEstimator(lambda proof: self.verify_completion(context, proof))

            def finite_result_yield(history, parameters, contexts):
                if contexts and contexts[-1] and (contexts[-1].get('practical_completion') is not None):
                    completed = endpoint(history, parameters, contexts)
                    if completed.diagnostics.get('fitting_scope') == 'verified_assignment_endpoint':
                        return completed
                if remaining == 0:
                    if any((value != 0 for value in history)):
                        raise ValueError('results_credit_without_original_uncredited_bytes')
                    return YieldEstimate(len(history), NumericBand.exact(0), parameters, {'remaining_original_selector_credit': 0.0}, estimator_binding={'version': 'finite_result_selector_exhaustion_v1', 'forecast': 'exact_zero_after_all_requested_byte_positions_credited'})
                return estimate_bounded_credit_yield(history, parameters, contexts=contexts, initial_credit=initial_credit, maximum_credit=remaining)
            return YieldController(epoch, initial_credit, profile['cutoff'], YieldParameters(**profile['parameters']), estimate_with_context=finite_result_yield)
        if target['resource_kind'] == 'api':
            service = target.get('service') or target.get('assignment', {}).get('service')
            if not isinstance(service, str) or not service:
                raise ValueError('results_original_api_service_required_for_yield')
            key = 'results:api_' + service + ('_' + selector['version'] if 'version' in selector else '')
        else:
            key = 'results:typed_' + target['resource_kind'] + '_' + selector['version']
        profile = self._task_yield_profile(key)
        return YieldController(epoch, initial_credit, profile['cutoff'], YieldParameters(**profile['parameters']), estimate_with_context=PracticalYieldEstimator(lambda proof: self.verify_completion(context, proof)))

    def practical_estimator(self, context):
        if context.role in {'launch_local', 'launch_hpc'}:
            practical = self._practical_context(context)
            return self._delegate(context).practical_estimator(practical)
        from gene_annotation_episode.episodic_workflow.root.a101.practical_yield import PracticalYieldEstimator
        return PracticalYieldEstimator(lambda proof: self.verify_completion(context, proof))

    # The public practical_estimator above retains arbitrary direct-call compatibility.
    def _private_practical_estimator(self, context):
        context.role in {'launch_local', 'launch_hpc'}
        from gene_annotation_episode.episodic_workflow.root.a101.practical_yield import PracticalYieldEstimator
        return PracticalYieldEstimator(lambda proof: self.verify_completion(context, proof))
