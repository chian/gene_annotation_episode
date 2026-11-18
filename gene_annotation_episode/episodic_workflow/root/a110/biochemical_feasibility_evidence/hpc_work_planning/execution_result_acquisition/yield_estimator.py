"""Private yield definitions retain their original callback provenance."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.library.execution_result_contract import RESULTS_SCHEMA
from .binding_roles import ROLE_KINDS
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import checked
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import digest
import json
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_records import validate_completion_proof

class ExecutionEpisodeYield:

    @staticmethod
    def _request_yield_class(request):
        """Classify the original execution request without generated IDs."""
        request = plain(request)
        version = request.get('version')
        if version != 'practical_assignment_v1':
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
        self.credit_kind('results')
        if not self.private_yield_binding:
            raise ValueError('execution_private_yield_binding_not_enabled')
        return self._results_yield_controller(context, initial_credit, epoch)

    def _launch_yield_controller(self, context, initial_credit, epoch):
        """Cap one next handoff by original request slots still uncredited."""
        from gene_annotation_episode.episodic_workflow.root.a110.numerical import BoundedYieldController, NumericBand, YieldController, YieldEstimate, YieldParameters
        assignment = plain(context.assignment)
        if 'requests' not in assignment:
            raise ValueError('launch_original_request_map_required')
        original = self._launch(assignment, scope=context.scope)
        eligible = {resource_id for resource_id in original['requests'] if self._permitted(original, resource_id)}
        selected, handoffs, _ = self._received(context)
        initial = set(selected['initial_known_record_refs'])
        already_received = {target['resource_id'] for reference, target in handoffs.items() if reference in initial and self.job_progress_provider.targets.usable_handoff(target)}
        remaining = len(eligible - already_received) * self.handoff_unit
        if remaining:
            classes = sorted((self._request_yield_class(original['requests'][resource_id]) for resource_id in eligible))
            profile = self._task_yield_profile('launch:' + '+'.join(classes))
            return BoundedYieldController(epoch, initial_credit, profile['cutoff'], remaining, YieldParameters(**profile['parameters']))
        if initial_credit != 0:
            raise ValueError('launch_no_uncredited_requests_but_nonzero_initial_credit')

        def no_remaining_requests(history, parameters, contexts):
            if any((value != 0 for value in history)):
                raise ValueError('launch_credit_without_original_uncredited_request')
            return YieldEstimate(len(history), NumericBand.exact(0), parameters, {'remaining_original_request_credit': 0.0, 'original_request_count': len(eligible)}, estimator_binding={'version': 'launch_original_request_exhaustion_v1', 'forecast': 'exact_zero_when_every_eligible_original_request_was_in_initial_handoffs'})
        return YieldController(epoch, initial_credit, 0.0, YieldParameters(), estimate_with_context=no_remaining_requests)

    def _launch_local_yield_controller(self, context, initial_credit, epoch):
        from gene_annotation_episode.episodic_workflow.root.a110.numerical import YieldController, YieldParameters
        from gene_annotation_episode.episodic_workflow.root.a110.practical_yield import PracticalYieldEstimator
        request = self._validate_request(plain(context.assignment))
        profile = self._task_yield_profile('launch_local:' + self._request_yield_class(request))
        return YieldController(epoch, initial_credit, profile['cutoff'], YieldParameters(**profile['parameters']), estimate_with_context=PracticalYieldEstimator(lambda proof: self.verify_completion(context, proof)))

    def _launch_hpc_yield_controller(self, context, initial_credit, epoch):
        from gene_annotation_episode.episodic_workflow.root.a110.numerical import YieldController, YieldParameters
        from gene_annotation_episode.episodic_workflow.root.a110.practical_yield import PracticalYieldEstimator
        request = self._validate_request(plain(context.assignment))
        profile = self._task_yield_profile('launch_hpc:' + self._request_yield_class(request))
        return YieldController(epoch, initial_credit, profile['cutoff'], YieldParameters(**profile['parameters']), estimate_with_context=PracticalYieldEstimator(lambda proof: self.verify_completion(context, proof)))

    def _results_yield_controller(self, context, initial_credit, epoch):
        from gene_annotation_episode.episodic_workflow.root.a110.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters, estimate_bounded_credit_yield
        from gene_annotation_episode.episodic_workflow.root.a110.practical_yield import PracticalYieldEstimator
        assignment = checked(context.assignment, RESULTS_SCHEMA, 'invalid_execution_results_assignment')
        target = self._target(context)
        selector = self._selector(assignment, target)
        if 'version' not in selector:
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
        key = 'results:typed_' + target['resource_kind'] + '_' + selector['version']
        profile = self._task_yield_profile(key)
        return YieldController(epoch, initial_credit, profile['cutoff'], YieldParameters(**profile['parameters']), estimate_with_context=PracticalYieldEstimator(lambda proof: self.verify_completion(context, proof)))

    def practical_estimator(self, context):
        from gene_annotation_episode.episodic_workflow.root.a110.practical_yield import PracticalYieldEstimator
        return PracticalYieldEstimator(lambda proof: self.verify_completion(context, proof))
