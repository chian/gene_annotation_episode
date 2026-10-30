# Deterministic received witness enumeration

This clarifies394's phrase "deterministic delivery order"; it does not change
which descriptor is actually received or any use permission.

397 traced the complete existing completion/admission and internal redelivery
paths. runtime_completion_slots.sequence records completed/admitted order for
durable original child returns. Internal redelivery saves its report attempt and
semantic receipts without a completion slot/new observation; older blocking
returns also lack that durable admission record. No common chronological arrival
order is recorded for all eligible forms. Do not infer one from decision_index.

Use the existing deterministic enumeration: frozen ancestors before current
episode, then recorded decision_index, the exact four-source key order, and
source-row order. For each operation, use the first eligible actual descriptor
in that enumeration as its authority witness. Its complete original contents,
allowed use, original commission and frozen report-prefix membership must match.
Do not union uses from different descriptors or admit a later report merely
because its commissioning decision_index is lower.

This order selects a witness; it is not an arrival timestamp, new numerical
measurement, credit observation or episode-owned scientific choice. Existing
completion, admission, redelivery and frozen-prefix schemas remain unchanged.
