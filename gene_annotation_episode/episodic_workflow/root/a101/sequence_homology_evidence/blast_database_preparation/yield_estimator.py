"""Continuation: the Episode's one possible gain is the credit of one usable prepared-data record (one commission
names one input set and one set of options, hence one key), so the commission is finite and its target is
``prepared_unit``: the completion controller. At the target the forecast of further credit is exactly zero and the
episode ends; a usable record ends it after one unit. Before that, units that earn nothing (a failed build, a hold,
a repeat) are the evidence the controller reads.

The cost is a setting of the run (``settings['cost']``, ``settings['parameters']``) and must lie below the target.
The reason for the value this episode is run with: a further unit after a unit that earned nothing is worth its
cost only if it is likely to earn a real fraction of the one record at stake. The earlier real run of another tool
kept going for 22 units with no gain at cost 0.01 of a unit of 1; a cost of half the target (0.5 of the unit) is
used here, so a second unit that is forecast to earn less than half a record is not taken. The value is chosen from
the controller's observed behaviour on zero-credit units (see the design note), not from a count of units."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    return CompletionYieldController('blast_database_preparation', initial_credit, settings['cost'],
                                     parent_input['prepared_unit'], settings['parameters'])
