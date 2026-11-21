"""What the head takes from a child's return: controlled data only. The child's credit (its productivity), the
controlled features of the sheets it and its descendants saved, with their references, and the assessments committed
with grading (``finding``), and the fields this episode selected: the committed records of the recursion child
(references), the relevant lead count and lead sources and the requested cell rows (references)
of the literature child. No text a child's model wrote reaches this episode.

Carried from the old ``from_child_sample_context_evidence.py`` and ``from_child_published_evidence_assessment.py``
(``receive_report``: the references the admitted form named). The assessments the head knows from a child are the ones
its finding names (``assessment_refs``)."""
LEADS = 'literature_source_lead_dispositions'
GRADING_CELLS = 'literature_a108_grading_cells'
AGGREGATION_CELLS = 'literature_a108_aggregation_cells'
COMMITTED = 'committed_record_refs'
SELECTABLE = {COMMITTED: COMMITTED, LEADS: 'leads', GRADING_CELLS: GRADING_CELLS,
              AGGREGATION_CELLS: AGGREGATION_CELLS}


def assessments(records, refs):
    """The assessments among ``refs`` (held)."""
    return [ref for ref in dict.fromkeys(refs)
            if ref.startswith('assessment_') and records.get(ref)['record_type'] == 'assessment']


def read_from_child(slot, result, summary, records):
    report = {'slot': slot, 'credit': result['credit'], 'finding': result['finding']}
    for name, key in SELECTABLE.items():
        if name in result:      # exactly the fields this commission selected
            report[key] = result[name]
    return report
