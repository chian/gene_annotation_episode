"""Credit: the old operational credit (``ExecutionEpisodeCredit._live_project_credit``, ``credit_kind``
'operational', binding ``execution_received_records_credit``): ``handoff_unit`` for each distinct resource whose
original request got a usable handoff in this Episode and had none when it began, plus ``acquired_record_unit`` times
the acquired fraction, which the old code fixed at ``0.0`` for a launch (a launch acquires no result; its ``mixed``
branch was dead). The formula is kept; nothing bounds, clamps or rescales it.

The usable handoffs are in the summary: each launch child's report says whether its handoff was established and
names the handoff records it returned.

BLOCKED-ON-JOB-SERVICE: handoff record kind (the job ledger of LAUNCH_MONITOR_EXTRACT_MECHANICS section 6). The old
code re-read each received handoff record (``job_progress_provider.targets.usable_handoff(target)``) to learn its
target resource and usability; wanted call: ``records.table(JOB_LEDGER).select({'event': 'handoff', 'job': handle})``
for each handoff reference a child returned. No job record kind exists, so the child's own report (completed, with
handoff references) is the count, and the resource id is the one this episode commissioned. The old
``closed_credit.py`` (the view frozen at closure and re-checked against the old journal tables) is old-runner
machinery: the system hands the credit its controller last saw to ``final_to_parent``."""


def credit(summary, records):
    handoff_count = len(set(summary['handoff_resources']) - set(summary['received_handoff_resources']))
    acquired_fraction = 0.0
    return summary['handoff_unit'] * handoff_count + summary['acquired_record_unit'] * acquired_fraction
