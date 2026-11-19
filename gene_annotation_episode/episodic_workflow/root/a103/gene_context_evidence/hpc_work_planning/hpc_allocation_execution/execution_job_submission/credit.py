"""Credit: ``handoff_unit`` times the number of resources for which a usable handoff was newly received (the old
rule ``execution_received_records_credit_v1``, kind ``operational``). A resource already handed off when the
commission began is not counted again (``internal_summary`` leaves it out), and acquired results earn nothing here
(the old ``acquired_fraction`` was the constant 0.0). Never bounded, clamped or rescaled; the unit comes from the
commission through the summary because ``credit`` has no settings."""


def credit(summary, records):
    return summary['handoff_unit'] * len(summary['handed_off'])
