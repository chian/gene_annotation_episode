"""The return. Always returned: credit (the system hands it in ``completion``; it is the productivity signal and
nothing restates it) and the finding the source relevance assessment needs to decide whether to examine another
source (``INVESTIGATION_FINDING_FEATURES_a101.md`` section 10): the examined source (a record reference) and the
counts code reads from the latest controlled report (section 9: the readings written, those with unresolved target
correspondence, one count per claim kind). No model-written text is returned. It declares no selectable field."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sequence_homology_evidence.literature_claim_reports import (
    COUNT_FIELDS, report_counts)

FINDING_FORM = RecordForm({
    'source_refs': Field('record_refs', 'The examined source (one reference)'),
    **COUNT_FIELDS,
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The controlled counts of the examined source', form=FINDING_FORM),
})


def final_to_parent(summary, completion, selection):
    return {'credit': completion['credit'],
            'finding': {'source_refs': [summary['literature_assignment']['source_ref']],
                        **report_counts(summary['report'])}}
