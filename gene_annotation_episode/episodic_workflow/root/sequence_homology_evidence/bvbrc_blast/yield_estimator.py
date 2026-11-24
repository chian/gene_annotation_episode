"""Continuation: the completion controller (``CompletionYieldController``): continue until the credit reaches the commission's
finite target. The credit of this episode is bounded (``credit.py``): four things, each worth its unit once and counted only
when new in this commission: an estimate held, the search launched, the search known ended and the graded result. The
target (``read_from_parent``) is the sum of the units still obtainable under the commission's ``until``: ``launched`` ->
the estimate and the launch; ``extracted`` -> all four, less what the passed-back records already hold. At the target the
remaining credit is exactly zero and the controller stops the episode at once: a parking commission ends the moment the
launch completes, a resuming or one-loop commission the moment the result is extracted, with no wind-down units. The credit
never exceeds the target (it raises if it did): ``credit`` counts each unit only where ``read_from_parent`` put it into the
target. A search that failed at the service, or a monitor that keeps showing running, leaves the target unreached: the
controller then winds the episode down by units that earn nothing, as the forecast falls to the cost.

The cost is a setting of the run, ``settings['cost']``, taken as a fraction of the smallest credit unit of the commission
(``0.5``: half a unit), so it is always below the target (the controller requires that) and below the credit left before the
target, which is at least one unit; ``settings['parameters']`` are the estimator's."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    cost = settings['cost'] * min(parent_input['units'].values())
    return CompletionYieldController('bvbrc_blast', initial_credit, cost, parent_input['target'], settings['parameters'])
