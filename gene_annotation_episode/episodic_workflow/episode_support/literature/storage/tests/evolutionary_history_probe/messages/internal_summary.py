"""The plan and what each library call returned, from the loop's view."""


def internal_summary(view):
    return {**view.parent_input, 'outcomes': [outcome['outcome'] for outcome in view.outcomes]}
