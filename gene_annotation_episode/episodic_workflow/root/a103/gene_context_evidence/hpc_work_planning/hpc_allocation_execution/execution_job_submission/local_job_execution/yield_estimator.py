"""The commission is finite: the old controller was the practical completion estimator (a verified completion of the
assignment's endpoint). Its credit is the sum of the satisfied requirements and its target is the credit of the
assignment's completion keys, from the parent input."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    return CompletionYieldController('local_job_execution', initial_credit, settings['cost'],
                                     parent_input['completion_target'], settings['parameters'])
