"""Credit: one per completed plan step (an ``idle`` unit after the plan earns nothing)."""


def credit(summary, records):
    return float(summary['steps'])
