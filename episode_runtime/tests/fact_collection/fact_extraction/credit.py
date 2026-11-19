"""Credit: the share of the commissioned reading that is done. Finding the field completes it; so does reading
every passed record without finding it (the commission is then answered: the field is absent)."""


def credit(summary, records):
    if summary['fact_ref'] is not None:
        return 1.0
    return len(summary['read']) / len(summary['source_refs'])
