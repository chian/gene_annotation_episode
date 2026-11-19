"""Credit: one for each plan step carried out (an ``idle`` unit after the plan earns nothing)."""


def credit(summary, records):
    return float(summary['steps'])
