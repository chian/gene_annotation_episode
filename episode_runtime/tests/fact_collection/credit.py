"""Credit: one per extracted fact record and one per confirmed fact record."""


def credit(summary, records):
    return float(len(summary['fact_refs']) + len(summary['confirmed']))
