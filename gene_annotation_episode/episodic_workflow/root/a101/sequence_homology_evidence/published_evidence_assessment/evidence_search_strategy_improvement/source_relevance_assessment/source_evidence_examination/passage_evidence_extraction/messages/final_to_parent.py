"""The return. Always returned: credit (the system hands it in ``completion``; it is the productivity signal and
nothing restates it) and the finding: the counts code reads from the latest controlled report
(``INVESTIGATION_FINDING_FEATURES_a101.md`` section 9) and, per entry, its source (a record reference), its byte
window, its claim kind, its subject relation, whether it reports a measurement and the optional annotation as
written in the source (section 10). No model-written text is returned. It declares no selectable field."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sequence_homology_evidence.literature_claim_reports import (
    COUNT_FIELDS, PASSAGE_LOCATION, entry_form, report_counts, returned_entries)

LOCATION = tuple(PASSAGE_LOCATION)
FINDING_FORM = RecordForm({
    **COUNT_FIELDS,
    'entries': Field('list', 'One entry per passage a claim rests on', items=entry_form(LOCATION)),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The controlled report of the supplied passages', form=FINDING_FORM),
})


def final_to_parent(summary, completion, selection):
    report = summary['report']
    return {'credit': completion['credit'],
            'finding': {**report_counts(report), 'entries': returned_entries(report, LOCATION)}}
