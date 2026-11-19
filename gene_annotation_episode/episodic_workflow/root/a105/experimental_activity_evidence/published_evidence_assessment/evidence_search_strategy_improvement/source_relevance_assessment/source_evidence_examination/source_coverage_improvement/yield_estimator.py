"""Continuation by the commissioned task. Verified source leads accumulate without a finite target. Every other
task is a finite commission (old kind ``remaining_commissioned_credit``): its credit counts toward the credit unit
of the task times the answers requested (the experiments of a105_experiments, otherwise one), which
``read_from_parent`` put into the parent input. The cost (the old cutoff) and the estimator parameters (the old
``uncertainty_alpha``) are this episode's settings."""
from yield_control import AccumulationYieldController, CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    if parent_input['literature_task']['kind'] == 'verified_source_leads':
        return AccumulationYieldController('source_coverage_improvement', initial_credit, settings['cost'],
                                           settings['parameters'])
    return CompletionYieldController('source_coverage_improvement', initial_credit, settings['cost'],
                                     parent_input['completion_target'], settings['parameters'])
