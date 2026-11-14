"""Root annotation-axis continuation and estimator settings."""
import hashlib

class RootYield:
    def yield_controller(self, path, initial_credit):
        from .library.record_values import canonical
        from .numerical import AnnotationAxisYieldController
        if len(path) != 1 or path[0][0] != 'annotation':
            raise ValueError('episode_owner_yield_binding_required:' + path[-1][0])
        epoch = hashlib.sha256(canonical(path).encode()).hexdigest()
        return AnnotationAxisYieldController(epoch, initial_credit,
            self.axis_yield_cutoffs, self.yield_parameters)

    def controller_record(self):
        return {'version': 'signed_root_axis_yield_v2',
            'cutoffs': dict(self.axis_yield_cutoffs),
            'parameters': self.yield_parameters.as_record(),
            'forecast_unit': 'another_whole_axis_invocation',
            'credit_aggregation': 'received_axis_progress_v1',
            'unresolved_execution': 'unidentifiable_yield_until_original_pending_result_is_received_or_fails',
            'continuation': 'each_annotation_axis_forecast_compared_with_own_cutoff'}
