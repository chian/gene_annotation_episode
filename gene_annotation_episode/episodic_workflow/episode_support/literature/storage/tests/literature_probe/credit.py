"""One credit per completed plan step."""


def credit(summary, records):
    return float(summary['steps'])
