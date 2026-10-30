# Local commission frame scope clarification 002

This new clarification supplements permanent scope 001, SHA256
8e6d561fd028bcdbf374603eff3f8a82e5f5452a95ebaa8af2f0e972c168c25d.
It does not overwrite that record, change file ownership or authorize active
runtime integration.

A valid present C1 commission is retained when its original action row or table
is unavailable. Its accounting_status is null and its row includes
original_action_unavailable. A present action whose selected contents conflict
with the original C1 selection is an identity conflict. Missing action support
is anomalous under C1's atomic writer, but it is not an excuse to erase the known
commission or invent an empty population.

A backward UTC read bracket raises
ValueError('local_commission_frame_clock_order_failure'). It supplies no clamped
duration or fabricated capture time.

In return_scan.reads, next_cursor is null for a failed page read; after_cursor
retains its actual requested value, and the UTC started_at/finished_at bracket
still records that attempt. On failure, the scan's next_cursor retains the last
validated cursor (zero before any successful page). Read failures mark the scan
unavailable if no valid page was obtained and incomplete after any valid page.
Known return observations stay observed; remaining presence is unknown.

An existing empty C1 population needs no backend read. Its return scan is
complete with next_cursor 0, exhausted false and an empty reads list. This says
every captured commission has been accounted for; it does not claim an observed
empty backend or historical absence of commissions when C1 metadata is missing.

These definitions are passed verbatim to both isolated coding workers before
verification. No formula, model assumption, current scientific source, old
observation or live state is changed.
