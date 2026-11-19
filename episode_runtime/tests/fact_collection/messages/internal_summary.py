"""Where the episode stands: what the commissioner gave, the facts its extractions returned and the facts it
has confirmed, from the loop's view."""


def internal_summary(view):
    facts, fact_refs, confirmed = [], [], []
    for outcome in view.outcomes:
        if outcome['kind'] == 'child':
            facts.append(outcome['report']['fact'])
            fact_refs.extend(outcome['result']['fact_refs'])
        else:
            confirmed.append(outcome['outcome']['fact_ref'])
    return {**view.parent_input, 'facts': facts, 'fact_refs': fact_refs, 'confirmed': confirmed}
