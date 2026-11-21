"""The A108 page's information needs and Jev goal, after nano-graphrag's ``PageBinding._page_information_needs``.

nano-graphrag's page has Jev measure every table region and prose chunk of its paper once against the information
needs of its Goal (``assess_page_content``) before the page plans. The candidates, Jev's windowed measurement and the
planner's view of it do not depend on the axis: they are the functions of
``readers/experimental_activity_evidence/literature_page_content.py`` (``page_candidates``, ``assess_page_content``,
``planner_context``, ``report_windows``), which the A108 page calls with its own needs. This module is the A108 part:
what the page needs to find in a paper for the claim.

The A108 claim is the proposed function (the hypothesis record: its predicate and what its value names) for the organism
context the caller supplied. The needs follow the four kinds of outside context the A108 task names (physiology,
environment, availability, localization): per kind one need for the observation itself and one for the identity link that
ties the observation to the supplied organism, strain or sample (the analogue of a result table's slots and its identity
key columns). Pure: nothing here reads or writes the Store; the caller hands in the names it read through custody."""

DOMAINS = {
    'physiology': 'what the organism is observed to do (growth, uptake, metabolism, response)',
    'environment': 'the habitat, temperature, pH, oxygen and growth conditions of the organism or sample',
    'availability': 'the substrates and cofactors the proposed function needs, and whether they are present',
    'localization': 'whether the protein and the molecules it needs can occur in compatible cellular locations',
}
NAME_FIELD = {'context': 'name', 'term': 'label', 'reference': 'label', 'input': 'name'}


def record_name(record):
    """The name a record carries: a context's ``name``, a term's or reference's ``label``, an input's ``name``."""
    return record[NAME_FIELD[record['record_type']]]


def claim_of(hypothesis, value_name, organism_names):
    """The claim the page serves: the hypothesis's predicate, the name its value points at (None when the value is not a
    record) and the names of the organism contexts the caller supplied."""
    return {'predicate': hypothesis['predicate'], 'value_name': value_name, 'organism_names': list(organism_names)}


def information_needs(claim):
    """The needs Jev measures: for each domain one ``observation`` need and one ``subject_identity`` need (its 'table' is
    the domain)."""
    organisms = ', '.join(claim['organism_names'])
    function = f"'{claim['predicate']}' " + (f"{claim['value_name']}" if claim['value_name'] else 'the supplied value')
    observations, identities = [], []
    for domain, meaning in DOMAINS.items():
        observations.append({
            'need_id': 'observation:' + domain, 'table': domain, 'kind': 'observation',
            'label': 'contextual observation: ' + domain, 'columns': ['observation', 'organism', 'condition'],
            'description': (f"A reported observation of the {domain} of the organism context ({organisms}): {meaning}; "
                            f"bearing on the proposed function ({function}), whether it supports, conflicts with or "
                            'leaves open the fit.')})
        identities.append({
            'need_id': 'identity:' + domain, 'table': domain, 'kind': 'subject_identity',
            'label': 'identity context for ' + domain, 'columns': ['organism', 'strain', 'sample'],
            'description': ('Information needed to link an observation of this kind to the supplied organism context '
                            f"({organisms}): its organism, strain, sample, host or community, at the resolution the "
                            'source states.')})
    return observations + identities


__all__ = ['DOMAINS', 'NAME_FIELD', 'claim_of', 'information_needs', 'record_name']
