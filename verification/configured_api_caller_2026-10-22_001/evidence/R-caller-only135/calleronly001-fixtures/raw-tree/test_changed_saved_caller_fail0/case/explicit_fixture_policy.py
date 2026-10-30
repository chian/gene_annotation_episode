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
