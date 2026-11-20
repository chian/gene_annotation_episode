"""Continuation: the accumulating controller (``AccumulationYieldController``). The credit of this episode is a sum of
units earned for what is newly established: an estimate held, a handoff, each status request that shows a fact the
earlier ones did not, the graded result. The number of informative status requests is not fixed by the commission (a
search can be queued, running, finished), so there is no finite target to complete and no maximum to bound; a
completion controller would raise when the credit passed its target. The controller stops the episode when the
forecast of the next unit's credit is at or below its cost. The cost is a setting of the run (``settings['cost']``),
with the estimator's ``settings['parameters']``. The value used: half of a credit unit, so a further unit is taken only
while it is forecast to earn at least half a unit; once the result is extracted every action is a repeat that earns
nothing, and the forecast falls with each such unit until the controller stops the episode (several no-gain units are
normal). A search still running when the controller stops the episode is returned as ``launched``: the parent would have
to come back for it (the later work on detaching); nothing here waits for it or works around that."""
from yield_control import AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('bvbrc_blast', initial_credit, settings['cost'], settings['parameters'])
