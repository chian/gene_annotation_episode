"""The return. Always returned: the Episode's credit (the system hands it in ``completion``), the finding (which
field, whether it was found, its value and the record it was read from), the value as text and the fact record
(returned in custody). The two optional fields are returned only when the commissioner selects them."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'field': Field('text', 'The commissioned field'),
    'found': Field('boolean', 'Whether a passed record has the field'),
    'value': Field('text', 'The value of the field, when found', required=False),
    'source_ref': Field('text', 'The passed record the value was read from, when found', required=False),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the extraction found', form=FINDING_FORM),
    'fact': Field('text', 'The extracted value, or "not found"'),
    'fact_refs': Field('record_refs', 'The fact record'),
    'field': Field('text', 'The field that was extracted', required=False),
    'records_read': Field('list', 'The records read before the fact was found, in order', required=False),
})


def final_to_parent(summary, completion, selection):
    found = summary['fact_ref'] is not None
    finding = {'field': summary['field'], 'found': found}
    if found:
        finding.update(value=str(summary['value']), source_ref=summary['read'][-1])
    result = {'credit': completion['credit'], 'finding': finding,
              'fact': str(summary['value']) if found else 'not found',
              'fact_refs': [summary['fact_ref']] if found else []}
    if 'field' in selection:
        result['field'] = summary['field']
    if 'records_read' in selection:
        result['records_read'] = summary['read']
    return result
