"""Credit: one per completed plan step (a unit after the plan's last step earns nothing)."""


def credit(summary, records):
    return float(summary['steps'])
