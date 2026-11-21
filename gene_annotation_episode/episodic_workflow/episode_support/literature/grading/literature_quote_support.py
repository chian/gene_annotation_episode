"""How well the quote of a stated field supports it: the sheet side's use of the extraction's 'support' fact.

The extraction records, per stated field, a fixed-vocabulary fact ('direct', 'implied', 'about_something_else'); the
grader keeps it in the record and only reads it out (``criterion_supports``); the converter (the sheet side) judges it
(``apply_support``): it never changes a status, it only gives or lowers the degree of a supported criterion.
"""

SUPPORTS = ('direct', 'implied', 'about_something_else')
SUPPORT_DEGREE = {
    'direct': 1.0,                # EXPERT_REVIEW: the quote itself states the value or fact: full credit, degree unchanged.
    'implied': 0.7,               # EXPERT_REVIEW: the quote states it only by implication: a reader would probably accept it, but it is not what the source says in so many words.
    'about_something_else': 0.3,  # EXPERT_REVIEW: the quote is on the topic but is really about another measurement or condition: the value is more likely borrowed than reported, so little credit.
}


def field_support(record, path):
    """The support of the stated field at ``path`` ('quantities.x', 'facts.x', 'concentration_series' or the name of a
    plain choice field kept in record['choice_support']); None when the field is not stated."""
    kind, _, name = path.partition('.')
    if kind == 'quantities':
        return record['quantities'][name].get('support')
    if kind == 'facts':
        return record['facts'][name].get('support')
    if not name and kind in record and isinstance(record[kind], dict):
        return record[kind].get('support')
    return record['choice_support'].get(kind)


def criterion_supports(record, criteria):
    """criterion id -> the supports of the stated fields that criterion reads (from its declared 'reads')."""
    result = {}
    for criterion in criteria:
        found = (field_support(record, path) for path in criterion['reads'])
        result[criterion['id']] = [support for support in found if support is not None]
    return result


def apply_support(verdict, supports):
    """``verdict`` (a sheet criterion with its status) with the support degree: for a supported criterion the weakest
    support among ``supports`` gives a factor; the degree becomes the factor where there was none, the product where
    there was one, and stays as it was when the factor is 1.0. Any other status is returned unchanged (no degree)."""
    factor = min((SUPPORT_DEGREE[support] for support in supports), default=1.0)
    if verdict['status'] != 'supported' or factor == 1.0:
        return verdict
    return {**verdict, 'degree': verdict.get('degree', 1.0) * factor}
