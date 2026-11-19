"""The number of functions planned and the outcome of each unit so far."""


def internal_summary(view):
    return {**view.parent_input, 'outcomes': list(view.outcomes)}
