# Additive correction to frozen proposal001

Root identified an incorrect/ambiguous phrase in
`PAIRED_CONTRACT_PROPOSAL_001.md:168–169`:

> NoHPF1 alone nondetection is retained as nondetection, never exact zero.

The corrected scope is **HPF1-alone nondetection, without PARP1**. It is not
nondetection in the selected **PARP1 + Nuc165, without HPF1** arm. Preserve the
former as nondetection, never exact zero; do not use it as a numerical blank for
the selected arm.

Checked the complete owned packet with a text search and inspected the four
source-populated JSON examples. Their selected measurements are reported
points, with no nondetection assigned to the selected arm. HPF1 is marked
absent in that arm. The schema's generic nondetection values contain no
HPF1-specific association. The `noHPF1` contribution-key label in the example
builder correctly identifies the selected arm and does not describe a
nondetection. No extraction/schema/example requires a numerical or semantic
change for this correction.

All 25 artifacts listed in frozen `PROPOSAL_MANIFEST_001.json` still match their
original hashes. The frozen001 packet remains unchanged. This correction uses
root's already-converted scope; no new primary read, scientific inference,
production change or scope expansion was made. Coding remains unreleased.
