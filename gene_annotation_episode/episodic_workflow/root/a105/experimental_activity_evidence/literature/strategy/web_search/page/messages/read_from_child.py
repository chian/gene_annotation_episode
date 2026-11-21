"""What this episode takes from a child's admitted return. Every report holds ``slot``, ``credit``, ``counts``,
``lead_source_refs`` and ``screening_covered``; the two slots of the old return form add the sheets, and the chunk adds
its record references. Nothing else of the child's work reaches this episode; the records are held through the
``returned`` receipts, so ``internal_summary`` and the sheet update read them through ``records`` and the Store.

``chunk`` (a leaf extractor, ``chunk/messages/final_to_parent.py``): its return is ``credit``, the ``finding`` counts
(``stated``, ``newly_stated``, ``asked``) and the selected ``record_refs``, the immutable leaf records. This episode groups
them into graders and updates the subscoring sheet (``task.update_sheet``). The chunk answers neither a screening nor a
lead disposition: ``lead_source_refs`` is empty and ``screening_covered`` false for it, because it returns none.

``table`` and ``report`` still declare the old return form (``literature_finding_forms.return_fields``: ``assay_sheets``,
``aggregation_sheets`` and the counts of ``COUNTS``); they are read as that form until they are rewritten as extractors."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_finding_forms import (
    LEADS, SCREENING)

COUNTS = ('assay_count', 'assessment_count', 'assay_count_with_evidence_ratio', 'no_applicable_span_count')
CHUNK_COUNTS = ('stated', 'newly_stated', 'asked')
LEAF_SLOTS = ('chunk',)


def read_from_child(slot, result, summary, records):
    report = {'slot': slot, 'credit': result['credit'],
              'lead_source_refs': result[LEADS]['lead_source_refs'] if LEADS in result else [],
              'screening_covered': result[SCREENING]['commissioned_spans_covered'] if SCREENING in result else False}
    finding = result['finding']
    if slot in LEAF_SLOTS:
        return {**report, 'counts': {name: finding[name] for name in CHUNK_COUNTS},
                'record_refs': list(result['record_refs'])}
    return {**report, 'assay_sheets': finding['assay_sheets'], 'aggregation_sheets': finding['aggregation_sheets'],
            'counts': {name: finding[name] for name in COUNTS}}
