"""The continuation (carried from ``yield_estimator.py``, ``completion.py`` and ``configuration.py``).

The old controller was ``YieldController`` with ``PracticalYieldEstimator(verify_completion)``: a verified
original handoff completion gave exact zero future gain. That is README 7b: completion, with the credit the
verified completion earns as its target. The target is the commission's ``completion_target`` (``parent_input``);
the cost and parameters are this episode's settings. The old ``launch_api:<class>`` profile lookup is replaced by
this episode's own entry of the run's ``continuation`` collaborator.
"""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    return CompletionYieldController('api_job_execution', initial_credit, settings['cost'],
                                     parent_input['completion_target'], settings['parameters'])
