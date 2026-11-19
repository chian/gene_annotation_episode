"""The plan and the scenarios done, from the loop's view."""


def internal_summary(view):
    return {**view.parent_input, 'outcomes': list(view.outcomes),
            'steps': min(len(view.outcomes), len(view.parent_input['plan']))}
