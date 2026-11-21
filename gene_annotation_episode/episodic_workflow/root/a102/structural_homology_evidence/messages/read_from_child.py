"""What this episode takes from a child's admitted result. The system admits the result against the child's own form and writes the
``returned`` receipts of the records its ``record_refs`` fields name; nothing of that custody is done here.

The report is the child's credit (its productivity: whether to commission it again) and its controlled finding (information for
the summary, never added into this episode's credit), and the references of the records the child returned, by kind: the handoff
records, the status records, the closure record and the graded records (what this episode's credit reads). A kind the child did not
return is an empty list. Nothing else of the result is kept: no returned list or record is shown to this episode's model."""

RETURNED = {'handoff_refs': 'execution_handoff_refs', 'check_refs': 'execution_check_refs',
            'closure_refs': 'execution_closure_refs', 'graded_refs': 'graded_refs'}


def read_from_child(slot, result, summary, records):
    returned = {kind: list(result.get(name, [])) for kind, name in RETURNED.items()}
    refs = list(dict.fromkeys(ref for found in returned.values() for ref in found))
    return {'credit': result['credit'], 'finding': result['finding'], 'record_refs': refs, **returned}
