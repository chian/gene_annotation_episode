"""Continuation, carried from the old ``yield_estimator.py`` (``ExperimentalActivityEvidenceYield.yield_controller``;
README 7b): the head's only credit is accumulated distinct findings, whose projector declared
``yield_method = 'accumulation'`` for the task ``A105:whole_axis_findings``, so its controller is the accumulation
controller, a port of nano-graphrag's EstimatorController, with the adaptive control (``ADAPTIVE_CONTROL``) and no
list of items (``items=None``). It takes no cost and no settings. After at least W=8 units attempted and m=4 observed
it fits nano-graphrag's yield model; a unit is flat when the upper bound of the expected next marginal (hypervolume)
credit is at or below gamma, the adaptive gamma = max(one-result resolution, 0.1 x median of the recent productive
credits), recomputed after every unit; it stops after 4 flat units in a row. With ``items=None`` no item count ends
it. The old
configuration admitted accumulation, bounded_quality and completion, but this head's projector fixed
``yield_method = 'accumulation'``, so the accumulation controller is the one; the old declaration checks
(``credit_definition`` digest against the projector record, ``yield_method`` against ``kind``) have nothing left to
compare: the kind is fixed and the finding unit is the commission's own (``parent_input['evidence_task']``, which
``credit.py`` projects with)."""
from yield_control import AccumulationYieldController, ADAPTIVE_CONTROL


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('experimental_activity_evidence', initial_credit, ADAPTIVE_CONTROL,
                                       items=None)
