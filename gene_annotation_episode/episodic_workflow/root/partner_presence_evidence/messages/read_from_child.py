"""What the head takes from a child's admitted return (old ``from_child_*.py`` and ``child_commissioning``
receivers). The report is the child's admitted result under its slot: the credit and finding it always returns and
each field the commission selected. The records a child returned are held by this Episode as ``returned`` (custody);
the old receivers' work (``EpisodeReturnRecords`` admission, the receipts ledger, ``received_form_references``,
native timing receipts, tool attributions, the progress provider's ``_receive_progress`` for the monitor child with
its content-digest signature, ``EpisodeReceipts``) is the system's and is not carried. Nothing is written here."""


def read_from_child(slot, result, summary, records):
    return {'slot': slot, **result}
