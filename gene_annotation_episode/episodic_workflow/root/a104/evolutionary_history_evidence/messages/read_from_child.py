"""What the parent takes from each child's admitted result.

The system admits the result against the child's own form and writes the ``returned`` receipts of the records it
names. From a child of its own kind this episode takes only the credit (information for the summary, never added to
this episode's own credit) and the controlled finding (the features of its A104 sheets, whose references this
episode now holds), plus the committed record references the commission selected. From the ``hpc`` child it takes the
result under the child's own names."""
OWN = 'evolutionary_history_evidence'
RECORD_SOURCE = 'committed_record_refs'


def read_from_child(slot, result, summary, records):
    report = {'credit': result['credit'], 'finding': result['finding']}
    if slot == OWN:
        if RECORD_SOURCE in result:
            report[RECORD_SOURCE] = result[RECORD_SOURCE]
        return report
    report.update({name: value for name, value in result.items() if name not in ('credit', 'finding')})
    return report
