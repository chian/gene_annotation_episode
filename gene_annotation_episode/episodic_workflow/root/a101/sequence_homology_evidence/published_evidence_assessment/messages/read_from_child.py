"""What this episode takes from the strategy investigation's return: its credit and its typed finding, shown to
the model among the child reports. The old ``from_child_evidence_search_strategy_improvement.py`` recorded the
record refs of the report as received (receipts: the system's custody now), gave the progress provider the form,
read native timing receipts from ``runtime_report_attempts`` and attributed tools; it added no validation, facts
or evidence tokens of its own."""


def read_from_child(slot, result, summary, records):
    return {'slot': slot, 'credit': result['credit'], 'finding': result['finding']}
