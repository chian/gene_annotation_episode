"""Credit, by the rule the commissioner names. ``units``: one per completed plan step (an ``idle`` unit after the
plan earns nothing). ``capped``: one per plan step up to a cap. The other rules read the held records: the bytes
of the records the units produced or their children returned; the cells of the commissioned sheet the Episode
holds; the held interpretation accounts that are current, read through the read-only reader's inventories. A rule
may add ``per_step`` for each completed plan step, so that a commissioner can name a finite target the plan
reaches exactly at its last step."""
from ..sheet_library import cells


def credit(summary, records):
    rule = summary['credit']
    return measured(rule, summary, records) + rule.get('per_step', 0) * summary['steps']


def measured(rule, summary, records):
    outcomes = summary['outcomes'][:summary['steps']]
    if rule['rule'] == 'units':
        return float(summary['steps'])
    if rule['rule'] == 'capped':
        return float(min(summary['steps'], rule['cap']))
    if rule['rule'] == 'bytes':
        total = 0.0
        for outcome in outcomes:
            refs = outcome['produced'] if outcome['kind'] == 'tool' else outcome['result']['fact_refs']
            total += sum(len(records.get_artifact(ref)) for ref in refs)
        return total
    if rule['rule'] == 'cells':
        return float(len(cells(records, rule['sheet'])))
    if rule['rule'] == 'current_accounts':
        scope = {'subject_refs': summary['input_refs']}
        held = records.list('interpretation_account', scope)
        current = list(records.iter_current_accounts('interpretation_account', scope))
        if [row['id'] for row in current] != [row['id'] for row in held if records.is_current(row['id'])]:
            raise ValueError('probe_credit_inventories_disagree')
        return float(len(current)) + 0.5 * records.count('hypothesis', scope) + 0.25 * len(
            records.current_assessments(scope))
    raise ValueError('probe_credit_rule_unknown:' + repr(rule))
