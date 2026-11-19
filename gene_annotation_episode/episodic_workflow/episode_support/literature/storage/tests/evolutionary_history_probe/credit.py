"""Credit: one for each library call that returned."""


def credit(summary, records):
    return float(len(summary['outcomes']))
