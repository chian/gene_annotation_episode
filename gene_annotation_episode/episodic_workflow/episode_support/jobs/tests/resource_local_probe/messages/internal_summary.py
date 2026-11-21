"""The plan, the unit outcomes and how many plan steps are done."""


def internal_summary(view):
    return {**view.parent_input, 'outcomes': list(view.outcomes),
            'steps': min(len(view.outcomes), len(view.parent_input['plan']))}
