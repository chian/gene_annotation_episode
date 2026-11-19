"""Credit: the assignment's own practical requirement credit, from the summary.

The summary projects the assignment's progress requirements over the receipts of this Episode's commands (the
sum of the credits of the original requirement keys currently satisfied). It is cumulative and signed: losing a
previously established fact lowers it. It is never bounded, clamped or rescaled."""


def credit(summary, records):
    return summary['progress']['credit']
