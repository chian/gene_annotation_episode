from dataclasses import replace
from gene_annotation_episode.assembled_case_policy import create_policy as assembled_policy
from gene_annotation_episode.numerical import YieldController, YieldEstimate, NumericBand

def create_policy(parameters):
    original = assembled_policy(parameters)
    def fixture_estimate(history, settings, contexts):
        return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= 2 else 1), settings,
            {'kind':'assembled_engineering_fixture_only'})
    # The caller's policy retains its explicit controller parameters below;
    # the fixture extracts only the existing YieldParameters fields.
    def controller(path, initial):
        settings = {name: parameters['policy']['controller'][name]
            for name in ('window_size','subsample_size','uncertainty_alpha')}
        return YieldController(str(path), initial, 0, settings,
            estimate_with_context=fixture_estimate)
    return replace(original, controller_factory=controller,
        controller_definition={'version':'assembled_engineering_fixture_controller_v1',
            'stop_after_completed_actions':2,'cost':0,
            'scientific_policy_unchanged':True})
