"""Where the extraction stands: the records read so far and the fact, when found, from the loop's view."""


def internal_summary(view):
    summary = {**view.parent_input, 'read': [], 'value': None, 'fact_ref': None}
    for outcome in view.outcomes:
        found = outcome['outcome']
        summary['read'].append(found['source_ref'])
        if found['found']:
            summary.update(value=found['value'], fact_ref=found['fact_ref'])
    return summary
