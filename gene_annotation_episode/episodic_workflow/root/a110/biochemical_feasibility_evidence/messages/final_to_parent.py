"""The return. Always returned: the Episode's credit (the system hands it in ``completion``), the finding (what this
episode interpreted, committed and had returned) and ``committed_record_refs`` (the acquired scientific records this
episode committed and its children returned, in custody). Selectable: ``component_axis_native_component_records`` and
``component_axis_native_execution_records``, the references of the received components and execution findings that
the tool ``received_evidence`` read."""
from method_loop import Field, RecordForm

NOT_WRITTEN = 'No interpretation was written before the episode ended.'
NOT_QUALIFIED = 'No interpretation was written, so nothing is qualified.'

CHILD_FORM = RecordForm({
    'slot': Field('text', 'The child commissioned'),
    'child_credit': Field('number', "The child's own credit (information; never added to this credit)"),
    'finding': Field('record', "The child's finding, as it returned it"),
})
FINDING_FORM = RecordForm({
    'written': Field('boolean', 'Whether an interpretation was written before the episode ended'),
    'interpretation': Field('text', 'The interpretation of what the investigation has established'),
    'qualification': Field('text', 'What the interpretation leaves unresolved'),
    'source_refs': Field('list', 'The sources the interpretation rests on'),
    'retained_finding_count': Field('integer', 'The distinct retained scientific findings this episode holds'),
    'inactive_dependency_count': Field('integer', 'The known findings that are no longer current or valid'),
    'reasoning_commits': Field('integer', 'The reasoning commits this episode made'),
    'children': Field('list', 'Each child commissioned, in order', items=CHILD_FORM),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the investigation interpreted, committed and had returned',
                     form=FINDING_FORM),
    'committed_record_refs': Field('record_refs', 'The acquired scientific records this episode committed and its '
                                                  'children returned'),
    'component_axis_native_component_records': Field(
        'record_refs', 'The received native component records', required=False),
    'component_axis_native_execution_records': Field(
        'record_refs', 'The received native execution records', required=False),
})


RECEIVED_ROWS = {'component_axis_native_component_records': 'native_components',
                 'component_axis_native_execution_records': 'execution_findings'}


def _selected(name, summary):
    """The value of one selectable field: the source references of the received rows it names."""
    return sorted(row['source_ref'] for row in summary['received'][RECEIVED_ROWS[name]])


def final_to_parent(summary, completion, selection):
    progress = summary['investigation_progress']
    report = summary['interpretation']
    finding = {'written': report is not None,
               'interpretation': NOT_WRITTEN if report is None else report['interpretation'],
               'qualification': NOT_QUALIFIED if report is None else report['qualification'],
               'source_refs': [] if report is None else list(report['source_refs']),
               'retained_finding_count': progress['retained_finding_count'],
               'inactive_dependency_count': len(progress['inactive_dependencies']),
               'reasoning_commits': sum(1 for item in summary['actions'] if item['name'] == 'reason'),
               'children': [{'slot': child['slot'], 'child_credit': child['child_credit'],
                             'finding': child['finding']} for child in summary['children']]}
    result = {'credit': completion['credit'], 'finding': finding,
              'committed_record_refs': list(summary['committed_record_refs'])}
    for name in selection:
        result[name] = _selected(name, summary)
    return result
