"""Credit: ``handoff_unit`` times the number of resources for which a usable handoff was newly received (the old
rule ``execution_received_records_credit_v1``, kind ``operational``; resources already handed off at the start are
excluded by the summary; acquired results earn nothing here). A handoff counts when the child returned handoff
references and this Episode holds each of them. Never bounded, clamped or rescaled."""


def credit(summary, records):
    for ref in summary['handoff_refs']:
        if not records.holds(ref):
            raise ValueError('execution_handoff_reference_not_held:' + ref)
    return summary['handoff_unit'] * len(summary['handed_off'])
