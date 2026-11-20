"""Credit: the established handoff earns the commission's completion target, once.

The old live credit of this role was ``handoff_unit`` for a usable handoff (``api_execution.credit_view``; the
acquired-record part was zero for a launch, which acquires nothing). The launching parent commissions this episode
with that unit as ``completion_target``, so the credit is the target when the Episode holds the handoff row of a
submission the service accepted (a row of the job ledger, written by the ``job_access`` service in the ``submit``
unit and read here through ``records``), and zero before. A lookup and a failed submission earn nothing. Never
bounded, clamped or rescaled."""
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import JOB_LEDGER


def credit(summary, records):
    held = [records.table(JOB_LEDGER).get(ref)['event'] for ref in summary['handoff_refs']]
    return float(summary['completion_target']) if 'handoff' in held else 0.0
