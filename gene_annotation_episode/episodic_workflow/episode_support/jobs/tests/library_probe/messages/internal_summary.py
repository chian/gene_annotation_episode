"""The plan, the unit outcomes and how many plan steps are done, with what the read-only reader finds of the rows
the plan steps wrote."""
from ..task import read_progress, read_timing


def internal_summary(view):
    outcomes = [item['outcome'] for item in view.outcomes]
    return {**view.parent_input, 'outcomes': list(view.outcomes),
            'steps': min(len(view.outcomes), len(view.parent_input['plan'])),
            'reread': [read_timing(done['axis'], view.records, done['scope'], done['refs'])
                       == done['details'] if 'refs' in done else read_progress(view.records, done)
                       for done in outcomes if 'refs' in done or 'first' in done]}
