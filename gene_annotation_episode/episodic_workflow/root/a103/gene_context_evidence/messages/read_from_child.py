"""What the A103 head takes from a child's return: its credit and its controlled finding (carried from the old
``from_child_gene_context_evidence.py`` and ``from_child_published_evidence_assessment.py``, which admitted the child's
typed form and received the references it declared, and from ``from_child_execution_progress_assessment.py``, which
read the monitor's ``episode_progress`` references: the system admits the result against the child's own form now and
writes the ``returned`` receipts of the records it names). A child's credit is information for the summary; it is
never added to this episode's credit: what the child graded counts here through this episode's own A103 credit, over
the sheets the child returned in ``finding.sheet_refs`` (now held).

A recursive A103 child returns the controlled features of its sheets; the parent's model is shown those features and
the count of returned references, not the references themselves. Every other child's finding is its own declared
controlled form and is taken as it is, with the selected fact sources as reference counts."""


def read_from_child(slot, result, summary, records):
    finding = result['finding']
    if slot == 'gene_context_evidence':
        finding = {key: value for key, value in finding.items() if key != 'sheet_refs'}
        finding['returned_sheet_record_count'] = len(result['finding']['sheet_refs'])
    report = {'slot': slot, 'credit': result['credit'], 'finding': finding}
    selected = {name: len(value) for name, value in result.items() if name not in ('credit', 'finding')}
    if selected:
        report['selected_record_counts'] = selected
    return report
