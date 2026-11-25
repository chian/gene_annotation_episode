"""What this episode takes from the search child's admitted result. The system admits the result against the child's own
form and writes the ``returned`` receipts of the records its ``record_refs`` fields name; nothing of that custody is done
here.

The report is the child's credit (its productivity), its controlled finding (the state of the search, the number of hits
and of claims, its timing: information for the summary, never added into this episode's credit), and the references of the
records the child returned, by kind: the handoff record, the status records, the closure record and the graded records
(the graded search and the kept claims: what this episode's credit reads). A kind the child did not return is an empty
list."""

RETURNED = {'handoff_refs': 'execution_handoff_refs', 'check_refs': 'check_refs', 'closure_refs': 'closure_refs',
            'graded_refs': 'graded_refs'}


def read_from_child(slot, result, summary, records):
    returned = {kind: list(result.get(name, [])) for kind, name in RETURNED.items()}
    refs = list(dict.fromkeys(ref for found in returned.values() for ref in found))
    return {'credit': result['credit'], 'finding': result['finding'], 'record_refs': refs, **returned}
