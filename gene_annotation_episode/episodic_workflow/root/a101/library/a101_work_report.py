"""Concrete A101 results for the common original-action/earned-credit report."""
from collections.abc import Mapping
from copy import deepcopy


_QUANTITIES = ('bit_score', 'bitscore', 'evalue', 'identity', 'percent_identity',
    'identities', 'aligned_length', 'alignment_length', 'query_coverage',
    'target_coverage', 'subject_coverage', 'sequence_credit', 'sequence_correspondence')


def _rows(value, path='result'):
    if isinstance(value, Mapping):
        yield path, value
        for name, child in value.items():
            if name != 'received_axis_results':
                yield from _rows(child, path + '.' + name)
    elif isinstance(value, (tuple, list)):
        for index, child in enumerate(value):
            yield from _rows(child, path + '[' + str(index) + ']')


def completed_work_result(selection, outcome, received_records):
    """Use exact own/admitted values; never equate child credit to parent gain."""
    result, limitations = [], []
    tool = str(selection.get('tool', ''))
    form = outcome.get('admitted_child_return')
    relevant = any(token in tool.lower() for token in ('blast', 'phmmer', 'hmmsearch', 'hmmscan'))
    if isinstance(form, Mapping) and 'sequence_credit' in form:
        relevant = True
        result.append({'result': 'Received A101 native sequence-correspondence value',
            'value': form['sequence_credit'], 'unit': 'dimensionless native correspondence',
            'credit_owner': 'Returned child; distinct from original parent earned credit'})
        if form.get('limitations'):
            limitations.extend(deepcopy(form['limitations']))
    for path, row in _rows(outcome):
        if not any(name in row for name in _QUANTITIES):
            continue
        if not relevant and not any(str(row.get(name, '')).startswith(('blast_', 'hmmer_', 'a101_'))
                for name in ('schema', 'version', 'provider')):
            continue
        values = {name: deepcopy(row[name]) for name in _QUANTITIES if name in row}
        scope = {name: deepcopy(row[name]) for name in ('subject_ref', 'query_ref',
            'reference_ref', 'source_ref', 'target_ref', 'scope', 'region',
            'query_start', 'query_end', 'hit_start', 'hit_end', 'status',
            'unit', 'unavailable_reason') if name in row}
        result.append({'result': 'Saved native sequence-comparison quantities',
            'original_result_path': path, **scope, 'quantities': values})
    if not relevant and not result:
        return None
    if not result:
        limitations.append('No numerical sequence-comparison component was present in this original returned payload.')
    return {'axis': 'A101', 'results': result, 'limitations': limitations}
