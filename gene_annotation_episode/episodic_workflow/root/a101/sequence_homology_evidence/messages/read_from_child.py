"""What this episode takes from a child's admitted result (the old ``from_child_<role>.receive_report`` of each of
the seven child roles). The old ``admit_return`` / ``receive_report`` custody (saved attempts per ``delivery_ref``,
the receipts of child-form references, progress provider forms, native timing receipts, tool attributions) is
machinery: the system admits the result against the child's own form and writes the ``returned`` receipts of the
records its ``record_refs`` fields name. The old ``receive_progress`` of the monitor (reading every
``episode_progress`` reference through the progress provider) is the monitor's own ``monitoring_progress_refs``
field here.

The report is the child's credit (its productivity: whether to launch it again) and its controlled finding
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
