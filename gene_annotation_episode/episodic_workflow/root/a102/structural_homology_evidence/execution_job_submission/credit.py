"""Credit: the old operational credit of ``launch`` (carried from ``credit.py``: ``credit_kind`` was
``operational``, ``_live_project_credit`` the formula).

``handoff_unit`` times the number of distinct resource ids that have a usable received handoff, not counting the
resource ids already handed off when the commission was made. The old ``acquired_record_unit`` term was multiplied
by ``new_acquired_record_count`` fixed at zero for ``launch`` and is not carried. A resource has a usable handoff
when its resource child returned handoff references and this episode holds them (``records.holds``): the old
``usable_handoff(target)`` of the progress provider read the handoff record, and the records are custody now. Each
resource counts once. Nothing here bounds, clamps or rescales it. The old closed credit (the view frozen at
closure and re-authenticated against the old journal and receipt tables), ``completion_for_action`` and
``verify_completion`` (the practical completion proof) are old-runner machinery: the system hands the credit its
controller last saw to ``final_to_parent``."""


def credit(summary, records):
    credited = [resource_id for resource_id in summary['new_handoff_resource_ids']
                if all(records.holds(ref) for ref in summary['handed_off'][resource_id])]
    return summary['handoff_unit'] * len(credited)
