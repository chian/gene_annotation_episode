"""Credit: one for each distinct usable execution handoff the Episode holds.

The old credit was ``services.bound_role_credit`` (the credit of the selected resource adapter, an ``operational``
credit; the number was defined outside this folder). The count of usable handoffs is the credit the launch step
produces (``LAUNCH_MONITOR_EXTRACT_MECHANICS.md`` section 4: "launch: for example one per usable handoff"). A
handoff is identified by its capability binding and its execution handle, and the summary keeps the latest usable
check of each (``messages/internal_summary.py``). The value comes from what the resource tools returned: credit has
no services. It is never bounded or rescaled."""


def credit(summary, records):
    return float(len(summary['execution_handoffs']))
