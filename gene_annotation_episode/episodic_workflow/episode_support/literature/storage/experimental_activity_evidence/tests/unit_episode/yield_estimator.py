"""A finite commission: one credit per function run."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    return CompletionYieldController('unit_episode', initial_credit, settings['cost'],
                                     float(parent_input['steps_planned']), settings['parameters'])
