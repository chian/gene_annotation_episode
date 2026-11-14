# Authenticated original retained protein reader input

These are preserved historical test inputs, not newly executed science or output
from this refactor. No Store, numerical worker, provider or workflow was executed
while preserving them on 2026-11-11. The original recorded inputs remain intact.

Origin:
`runs/check336_protein_structure_current_v2_workflow/tmp/test_current_v2_alignment_oper0/current-v2/{state,run}`
and its parent `PROTEIN_STRUCTURE_CURRENT_V2_WORKFLOW.json`.
The original saved-action test names these as genuine original336 V1 receipt
inputs. Their positive execution claim belongs to that original proof; copying
and hashing them does not validate any current relocated implementation.

All 292 files under state/ and run/ were copied byte-for-byte, with the proof
file separately preserved. FILE_SHA256SUMS covers all293 input files. The copied
manifest was verified against every original path using sha256sum; the proof
lives one directory above current-v2 in the original layout.
The two prior independently recorded pins match:

- state/state.sqlite3:
  efb35ce65a40b064ba9179b08c604779b9274a9da8cbe5311f2ae7fcd10609b7
- PROTEIN_STRUCTURE_CURRENT_V2_WORKFLOW.json:
  4265809860a1e6bcda1f734bd44efa964551087ec7dfdc92ae63fd9e89d54043

Recorded absolute paths, native request bytes, worker/source identities, receipt
schemas, observation IDs and original numerical outcomes are untouched. Original
source/control paths inside the records remain historical provenance. A reusable
reader fixture must explicitly handle original path custody before claiming it
can execute independently from the original runs directory. That wiring is not
yet implemented or validated; do not rewrite stored paths or hashes to make a
relocated reader accept them. No source-authentication or scientific validator
may be replaced with a success stub.

The intended next checks are no-native read-only Store/receipt authentication,
original saved-sheet permission, source/byte tamper rejection, frozen receiving
prefix, and denial of an unreturned fitted transform. No raw structure parsing,
new numerical calculation, producer capability, progress credit or native launch
is required by this input preservation step.
