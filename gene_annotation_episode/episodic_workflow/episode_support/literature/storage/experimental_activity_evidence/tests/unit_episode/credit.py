"""Credit: one per function run."""


def credit(summary, records):
    return float(min(len(summary['outcomes']), summary['steps_planned']))
