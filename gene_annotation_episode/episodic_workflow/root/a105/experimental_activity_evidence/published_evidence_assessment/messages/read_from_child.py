"""What this episode takes from a child's admitted return: its credit and the controlled features of the sheets of
its finding, the counts of its finding, and the selected answers as counts and references. Nothing else of the
child's work reaches this episode; the sheets, the experiments and the assertions named are held through the
``returned`` receipts, so ``credit`` and ``internal_summary`` read them through ``records``.

The three children declare the same return form (``literature_finding_forms.return_fields``)."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_finding_forms import (
    LEADS, SCREENING)

COUNTS = ('assay_count', 'assessment_count', 'assay_count_with_evidence_ratio', 'no_applicable_span_count')


def read_from_child(slot, result, summary, records):
    finding = result['finding']
    return {'slot': slot, 'credit': result['credit'], 'assay_sheets': finding['assay_sheets'],
            'aggregation_sheets': finding['aggregation_sheets'], 'counts': {name: finding[name] for name in COUNTS},
            'lead_source_refs': result[LEADS]['lead_source_refs'] if LEADS in result else [],
            'screening_covered': result[SCREENING]['commissioned_spans_covered'] if SCREENING in result else False}
