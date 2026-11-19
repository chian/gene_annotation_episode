"""The plan, the unit outcomes, how many plan steps are done, the child updates and what the held records say,
from the loop's view."""
import json


def internal_summary(view):
    names = [json.loads(view.records.get_artifact(ref))['name'] for ref in view.parent_input['subject_refs']]
    # A tool outcome may name a record for the summary to read (``summary_read``): the summary reads it through
    # the read-only reader, which refuses what the Episode does not hold.
    read = [json.loads(view.records.get_artifact(outcome['outcome']['summary_read']))['name']
            for outcome in view.outcomes
            if outcome['kind'] == 'tool' and isinstance(outcome['outcome'], dict)
            and outcome['outcome'].get('summary_read')]
    # Units after the plan's last step are ``idle`` units: they are not plan steps.
    return {**view.parent_input, 'outcomes': list(view.outcomes),
            'steps': min(len(view.outcomes), len(view.parent_input['plan'])), 'subject_names': names,
            'summary_read': read, 'n_updates': len(view.updates), 'n_reports': len(view.child_reports)}
