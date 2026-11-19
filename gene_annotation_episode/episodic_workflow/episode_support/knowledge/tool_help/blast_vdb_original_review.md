# Root review of VDB field/function implementation

2026-10-26. Root read both production modules completely and reviewed the final
changed feature, population and completion paths with their regression tests.
The six public population, parsing, binding and calculation exports retain the
accepted309/312 interfaces. This review concerns those pure components; native
VDB tool execution and the complete episode path remain unfinished.

Root checked the actual check_007 receipt and JUnit report:66 tests, zero
failures/errors/skips,0.481 seconds pytest time, returncode0. The receipt records
20 GiB memory,4 GiB scratch and no wall-time cap. Every recorded before/after
source hash is equal; root independently checked the current file hashes against
that receipt. Shared parsing/geometry/program-context sources are unchanged.
Earlier failed receipts remain retained. No redundant rerun was needed after
review because current code matches the final tested code.

Corrected and verified during review:

- Source availability and original row completeness are determined before
  population calculations. An unreadable, incompatible, entirely malformed or
  failed empty result cannot establish an observed zero. Independent supplied
  population counts and function fractions survive.
- Malformed dropped subjects leave retained valid-subject counts and partial
  flags. Those counts follow309's stated retained-valid population; they are
  not relabeled as original native totals.
- Two original hits explicitly linked to the same exact member and feature
  retain both HSP rows and union corresponding positions once. Different native
  hit ordinals do not imply conflicting feature identity.
- Function-assignment scope must agree with the counted entity. Feature or
  sample assignments cannot become whole-sequence assignments.
- Incomplete demonstrated sequence groups or source sample relationships
  preserve known numerators and withhold complete population fractions.
- Translation maps retain actual ordered original base positions, triplets,
  genetic code, leading/trailing unmatched bases and terminal stop. No guessed
  code, first master or start-symbol substitution is introduced.

Root read the exported numerical summary and corresponding test assertions.
The seventeen synthetic sheet/component examples and three native-format parser
examples are verification outputs of the implemented functions, not the task's
deliverable or authentic new native searches. Explicit GBSeq parent/feature
binding examples retain their input and result. The export receipt is
example_export_002/receipt.json, returncode0; root checked the example manifest
file lengths and hashes against actual saved files.

Checkable examples include:

- Two observed reads, one demonstrated full-sequence group, two source samples;
  supplied denominators10 reads,4 unique sequences,5 samples produce0.2,0.25,0.4.
- Translated forward/reverse CDS examples preserve9 nt corresponding to3 aa,
  query coverage0.5 and feature-residue coverage1.0. Original reverse positions
  are retained in descending transcription order.
- Two overlapping native hits for one member/feature union9 nt and3 residues
  once, preserving both original hit rows.
-3 demonstrated sequences with species groups2/1 give1 matching pair of3,
  and2/3 target-compatible groups under supplied exact taxonomy.
- Missing layout or source conflict with otherwise valid population data keeps
  observed counts/fractions unavailable; a qualified actual empty report permits
  zero.

The retained authentic paired BLAST fixtures exercise shared geometry only;
their native execution identity is not changed to VDB. No new native VDB search,
API/HPC request, installation or scientific dataset acquisition occurred.
RunInfo, exact blast_vdb_cmd four-column output and the narrow GBSeq parser are
tested with synthetic native-format inputs. Additional native taxonomy/assembly
adapters are not invented; supplied-explicit records remain distinguished.

Still required: authentic VDB mode outputs; prepared deployment/offline dataset
configuration; source metadata acquisition and any missing format adapters;
an explicitly defined VDB function-weight model; selected resource execution,
complete result acquisition and authenticated requested typed returns. No W05,
literature, evidence-axis, final annotation score, controller or prompt changed.
This component review does not add either VDB mode to the existing tool tally.
