"""Credit, by the rule the commissioner names. ``units``: one per completed plan step (an ``idle`` unit after the
plan earns nothing). ``capped``: one per plan step up to a cap. The other rules read the held records: the bytes
of the records the units produced or their children returned; the cells of the commissioned sheet the Episode
holds; the held interpretation accounts that are current, read through the read-only reader's inventories; the
reads of the selections its units froze, listed and paged through the reader; the records its units produced that
may be read as a source (not the diagnostics of their outcomes). A rule may add ``per_step`` for each completed
plan step, so that a commissioner can name a finite target the plan reaches exactly at its last step."""
from ..operations_library import may_be_read_as_a_source, read_page, selected_reads
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
    if rule['rule'] == 'selected_reads':
        total = 0
        for outcome in outcomes:
            selection = outcome['outcome']['selection']
            refs = selected_reads(records, selection['id'])
            if read_page(records, selection['library_ref'], selection_ref=selection['id'])['total'] != len(refs):
                raise ValueError('probe_credit_selection_and_page_disagree')
            total += len(refs)
        return float(total)
    if rule['rule'] == 'sources':
        return float(sum(may_be_read_as_a_source(records, ref) for outcome in outcomes if outcome['kind'] == 'tool'
                         for ref in outcome['produced']))
    raise ValueError('probe_credit_rule_unknown:' + repr(rule))
