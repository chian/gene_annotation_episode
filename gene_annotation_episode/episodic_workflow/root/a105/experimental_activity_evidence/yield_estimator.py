"""Continuation, carried from the old ``yield_estimator.py`` (``ExperimentalActivityEvidenceYield.yield_controller``;
README 7b): the head's only credit is accumulated distinct findings, whose projector declared
``yield_method = 'accumulation'`` for the task ``A105:whole_axis_findings``, so its controller is the accumulation
controller (old ``numerical.YieldController`` over ``declaration['cutoff']`` and ``declaration['parameters']``).

The cutoff is the controller's ``cost`` and the parameters are the old ``uncertainty_alpha``: both are this
episode's settings (``settings['cost']``, ``settings['parameters']``). The old configuration admitted accumulation, bounded_quality and completion, but this head's projector fixed
``yield_method = 'accumulation'``, so the accumulation controller is the one; the old declaration checks (``credit_definition`` digest against the projector record, ``yield_method``
against ``kind``) have nothing left to compare: the kind is fixed and the finding unit is the commission's own
(``parent_input['evidence_task']``, which ``credit.py`` projects with). A setting that does not make a controller
(a cost of zero never stops an accumulating Episode) is the controller's own error."""
from yield_control import AccumulationYieldController


def yield_controller(initial_credit, settings, parent_input):
    return AccumulationYieldController('experimental_activity_evidence', initial_credit, settings['cost'],
                                       settings['parameters'])
