"""The A105 reading leaves' (chunk, table, report) yield estimator: the completion controller plus the owner's one more
stopping condition of an episode with an input list: when the number of items on its list is zero, stop.

``ListBoundCompletionYieldController`` is a ``CompletionYieldController`` (the runner admits only the ``yield_control``
controllers, by type, and describes this one to the model as the completion controller it is): its estimator, cost,
target, estimate and stop rule are the completion controller's own, unchanged. It adds only the list: ``items`` is the
number of items on the leaf's input list when the leaf starts (from what ``read_from_parent`` produced), every completed
unit consumes one item (a leaf's one action is ``extract``, which consumes the item it reads), and once no item remains
the step and the state say stop. While an item remains, every step and state is the completion controller's own, as it
made it. With no item left the decision is the completion controller's decision with ``stop`` set and the list in its
record (``items``, ``items_remaining``, ``stopped_by``). A resumed leaf replays its recorded units through ``observe``,
so its list is consumed again unit by unit and its state stops where the run stopped."""
from dataclasses import dataclass, replace

from yield_control import CompletionYieldController, ContinuationDecision


@dataclass(frozen=True)
class ListStopDecision(ContinuationDecision):
    """The completion controller's decision once the list is empty: ``stop`` is True; ``stopped_by`` names the
    conditions that hold (``'estimator'`` when the completion rule also stopped, and ``'items'``)."""
    items: int
    items_remaining: int
    stopped_by: tuple

    def as_record(self):
        return {**super().as_record(),
                'decision_basis': 'current_estimator_marginal_credit_upper_bound_or_no_item_left',
                'items': self.items, 'items_remaining': self.items_remaining, 'stopped_by': list(self.stopped_by)}


class ListBoundCompletionYieldController(CompletionYieldController):
    """``CompletionYieldController(epoch, initial_credit, cost, target, settings)`` that also stops when no item of the
    episode's input list remains. ``items``: the number of items on the list at the start (a positive integer: the
    loop runs at least one unit)."""

    def __init__(self, epoch, initial_credit, cost, target, settings=None, *, items):
        super().__init__(epoch, initial_credit, cost, target, settings)
        if type(items) is not int or items < 1:
            raise ValueError('leaf_list_items_must_be_a_positive_integer')
        self.items = items
        self._items_remaining = items

    def _with_list(self, decision):
        if self._items_remaining:
            return decision
        return ListStopDecision(True, decision.projected_gain, decision.continuation_cost, self.items, 0,
                                (('estimator',) if decision.stop else ()) + ('items',))

    def observe(self, unit_label, value, is_root=False):
        if self._items_remaining == 0:
            raise RuntimeError(f'leaf_list_no_item_left_for_unit:{unit_label}')
        step = super().observe(unit_label, value, is_root)
        self._items_remaining -= 1
        return replace(step, decision=self._with_list(step.decision))

    def state(self):
        state = super().state()
        return replace(state, decision=self._with_list(state.decision))


__all__ = ['ListBoundCompletionYieldController', 'ListStopDecision']
