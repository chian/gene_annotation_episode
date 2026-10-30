# Live record reconstruction verification workload

The adopted GOAL_VERBATIM.txt controls. This is engineering verification of actual
configured-model selected operations and typed delivery, not a new source review.

Fresh worker owns only new files under live_record_reconstruction_001/ in this
verification directory. No runtime, source packet, original case, immutable pin,
active state, configuration, progress policy or historical receipt edits.

Inputs: live_yeag_004/ and live_pin_004/, resolved from this directory. Inspect
public action/return records only. Never inspect provider events/private reasoning.
Read root AGENTS.md, current goal, complete relevant Store/repository/binding paths
before constructing the check. Do not open or interpret a primary paper/packet.

Build a reusable command taking --run, --pin and --output-directory. Open active
SQLite read-only, obtain a consistent SQLite backup into a new owned destination,
then copy immutable artifacts named by that snapshot. Reopen only the owned copy
using the pinned actual Store/repository. Disable population/parser/calculator/model
entrypoints during projection so a successful read proves saved-result use.

Check actual operation-selected sheet identity, immutable payload equality, requested
cell projection/typed schema, and any actual admitted parent subset against saved
selected cells. Audit actual receipt and report boundaries if present; absence is
pending/unverified, not success. Do not call receive_cells or manufacture deliveries.
Check actions/observations accounting by episode and explain pending/failed work;
do not assume all action rows correspond to completed observations.

Outputs: executable check, machine-readable receipt, short evidence/limits report.
Separate repository reopen proof from actual host restart (not established here).
No API calls, workflow resume, inference, forced closure or writes to live Store.
