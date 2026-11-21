"""Credit: one per completed pair."""


def credit(summary, records):
    return float(summary['steps'])


def ceiling(summary, records, action_type, arguments, ctx):
    """A pair adds one credit; the idle unit adds none."""
    return {'compare': 1.0, 'idle': 0.0}[action_type]
