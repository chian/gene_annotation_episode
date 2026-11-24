"""Credit: the old operational credit of ``launch`` (carried from ``credit.py``: ``credit_kind`` was
``operational``, ``_live_project_credit`` the formula, binding record ``execution_received_records_credit``,
qualification ``original_request_resource_scope_selector_and_actual_received_unique_information``).

``handoff_unit`` times the number of distinct resource ids with a usable received handoff, not counting the resource
ids already handed off when the commission was made. The old ``acquired_record_unit`` term was multiplied by an
acquired fraction fixed at 0.0 for ``launch`` and is not carried. A resource has a usable handoff when its child
returned handoff references and this episode holds every one of them (``records.holds``). Each resource counts once.
Nothing here bounds, clamps or rescales it. The old ``closed_credit.py`` (the view frozen at closure and re-checked
against the old journal and receipt tables) and the native result families' credit views (roles other than this
launch) are not carried: the system hands the credit its controller last saw to ``final_to_parent``."""


def credit(summary, records):
    credited = [resource_id for resource_id in summary['new_handoff_resource_ids']
                if all(records.holds(ref) for ref in summary['handed_off'][resource_id])]
    return summary['handoff_unit'] * len(credited)
