"""The commission is finite: its credit counts the plan steps and the target is the whole plan."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    return CompletionYieldController('partner_sheet_probe', initial_credit, settings['cost'],
                                     float(len(parent_input['plan'])), settings['parameters'])
