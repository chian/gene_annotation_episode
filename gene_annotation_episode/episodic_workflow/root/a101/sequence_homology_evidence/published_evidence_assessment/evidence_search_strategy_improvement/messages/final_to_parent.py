"""The return. Always returned: credit (the system hands it in ``completion``; it is the productivity signal and
nothing restates it) and the finding the published evidence assessment needs to decide whether to read the
candidate sources, recommission the strategy or write its report (``INVESTIGATION_FINDING_FEATURES_a101.md``
section 10): the candidate sources of the latest controlled report (record references), the number of candidates
and the number of distinct search approaches (search tools) it names. No model-written text is returned. It
declares no selectable field."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'candidate_source_refs': Field('record_refs', 'The relevant source candidates the strategy found'),
    'candidate_count': Field('integer', 'The number of candidate sources'),
    'approach_count': Field('integer', 'The number of distinct search approaches (search tools) tried'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The candidate sources and the approaches tried', form=FINDING_FORM),
})


def final_to_parent(summary, completion, selection):
    report = summary['report']
    candidates = [] if report is None else list(dict.fromkeys(row['source_ref'] for row in report['candidates']))
    approaches = set() if report is None else {row['approach'] for row in report['approaches']}
    return {'credit': completion['credit'],
            'finding': {'candidate_source_refs': candidates, 'candidate_count': len(candidates),
                        'approach_count': len(approaches)}}
