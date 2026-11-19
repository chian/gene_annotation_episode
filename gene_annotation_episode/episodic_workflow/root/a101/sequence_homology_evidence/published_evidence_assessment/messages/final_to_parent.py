"""The return. Always returned: credit (the system hands it in ``completion``; it is the productivity signal and
nothing restates it) and the finding the head needs to decide whether to commit assessments on the returned
sources, run alignments for named homologs or recommission literature (``INVESTIGATION_FINDING_FEATURES_a101.md``
sections 9 and 10): the counts code reads from the latest controlled report (entries, unresolved target
correspondence, one count per claim kind) and the chosen sources, those of entries with an applicable claim (record
references). A101 has no literature grader: no sheet exists. No model-written text is returned. It declares no
selectable field."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sequence_homology_evidence.literature_claim_reports import (
    COUNT_FIELDS, chosen_source_refs, report_counts)

FINDING_FORM = RecordForm({
    **COUNT_FIELDS,
    'source_refs': Field('record_refs', 'The sources of the report entries with an applicable claim'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The controlled counts of the published evidence report and its chosen sources',
                     form=FINDING_FORM),
})


def final_to_parent(summary, completion, selection):
    report = summary['report']
    return {'credit': completion['credit'],
            'finding': {**report_counts(report), 'source_refs': chosen_source_refs(report)}}
