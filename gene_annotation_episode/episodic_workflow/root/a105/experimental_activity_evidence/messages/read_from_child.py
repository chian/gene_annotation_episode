"""What this episode takes from a child's admitted return: its credit, the controlled features of the sheets of its
finding and the counts of its finding; from the literature child the selected answers as counts and references; from
the head child the selected ``committed_record_refs``. The sheets, experiments and assertions named are held through
the ``returned`` receipts, so ``credit`` and ``internal_summary`` read them through ``records``. The old admission
of the child's form into the head's own repositories and receipt ledger is the system's custody and is not
carried."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_finding_forms import (
    LEADS, SCREENING)

COMMITTED = 'committed_record_refs'
COUNTS = ('assay_count', 'assessment_count', 'assay_count_with_evidence_ratio', 'no_applicable_span_count')


def read_from_child(slot, result, summary, records):
    if slot not in ('experimental_activity_evidence', 'published_evidence_assessment'):
        raise LookupError('no_such_child_slot:' + slot)
    finding = result['finding']
    report = {'slot': slot, 'credit': result['credit'], 'assay_sheets': finding['assay_sheets'],
              'aggregation_sheets': finding['aggregation_sheets'], 'counts': {name: finding[name] for name in COUNTS},
              'lead_source_refs': result[LEADS]['lead_source_refs'] if LEADS in result else [],
              'screening_covered': result[SCREENING]['commissioned_spans_covered'] if SCREENING in result else False}
    report['committed_record_refs'] = result[COMMITTED] if COMMITTED in result else []
    return report
