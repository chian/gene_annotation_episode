"""What this episode takes from a child's admitted result. The system admits the result against the child's own form
and writes the ``returned`` receipts of the records its ``record_refs`` fields name; nothing of that custody is done
here.

The report is the child's credit (its productivity: whether to commission it again) and its controlled finding
(information for the summary, never added into this episode's credit), the records the child returned (the
references of its ``*_refs`` fields, in custody) and the handoff records a launch returned
(``execution_handoff_refs``). Nothing else of the result is kept: no returned list or record is shown to this
episode's model."""


def read_from_child(slot, result, summary, records):
    refs = []
    for name, value in result.items():
        if name not in ('credit', 'finding') and name.endswith('_refs'):
            refs.extend(ref for ref in value if ref not in refs)
    handoff = list(result['execution_handoff_refs']) if 'execution_handoff_refs' in result else []
    return {'credit': result['credit'], 'finding': result['finding'], 'record_refs': refs, 'handoff_refs': handoff}
