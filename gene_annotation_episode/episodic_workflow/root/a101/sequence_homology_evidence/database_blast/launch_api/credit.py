"""Credit: the established handoff earns the commission's completion target, once (owner decision D17: only what is
gained). The target is earned when the episode holds the handoff row of a submission the service accepted, a row of the
job ledger that the job service wrote in the ``submit`` unit and that is read here through ``records``; before that, and
for a failed submission, the credit is zero."""
from episode_runtime.job_access import JOB_LEDGER


def credit(summary, records):
    held = [records.table(JOB_LEDGER).get(ref)['event'] for ref in summary['handoff_refs']]
    return float(summary['completion_target']) if 'handoff' in held else 0.0
