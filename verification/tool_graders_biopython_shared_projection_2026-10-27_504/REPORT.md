Biopython R1 shared publication repair — verification packet 504

This packet records the delegated R1 Biopython identity/coverage repair and the
approved compatibility change for the structure consumer. It is implementation
evidence, not a replacement goal or a claim that the Biopython family or R2 is
complete. Authority remains the original user attachment with SHA-256
`f43e46c2433c44d320d1bbdb4e08f6cb85608a29d50911c2be28eb963581b6dc`.

The native producer now emits `biopython_pairwise_native_v2`, retaining native
score, full lengths, aligned strings, coordinates, intervals, parameters,
version and limitations. It no longer counts paired/identical positions or
calculates the three convenience fractions. Explicit no-alignment output retains
its parameters and has `aligned=false`, `native_score=null`.

Both native formats populate the existing `biopython_pairwise_sheet_v1` and
`calculate_biopython_pairwise_scores`. Legacy required reported fields and their
conflict checks remain. The marker distinguishes intentionally absent derived
fields in new raw results. `shared_calculator_pins.json` verifies byte-identical
source for the shared count, fraction, geometry, sheet validation, definitions and
calculator functions.

`ToolRegistry._align_one` grades once, retains that exact grading, and projects
the following cells into new publication and preview:

| Published/preview field | Shared score cell |
| --- | --- |
| `paired_positions` | `paired_positions` |
| `identical_positions` | `identical_positions` |
| `identity_fraction` | `paired_identity` |
| `query_coverage` | `query_aligned_coverage` |
| preview `reference_coverage`, observation `target_coverage` | `reference_aligned_coverage` |

Aligned coverage includes nongap positions opposite insertions; paired coverage
and alignment-column identity remain separate. Missing calculated cells stay
null in preview and absent from numeric observations. Grade failure cannot restore
legacy convenience values. Native score/lengths can survive grading failure.
Published operand intervals come from validated sheet geometry.

`changes.diff` includes the owned production/test edits; its `tools.py` section
contains only `_align_one`, because other agents concurrently own other methods.
`before/` and `source_pins_before.json` retain the before state. The structure
contract adds only v2 raw aligned/no-alignment union members; legacy shapes and
structure calculations remain unchanged. Its workflow test assertion now reads
paired count from retained shared grading.
`owned_fragment_pins.json` verifies that the current owned production functions,
v2 types, focused tests and workflow assertion match the frozen check004 source.

The synthetic protein alignment `ACD-EFG` / `ACTVE-G` uses lengths 10/12,
intervals [1,7]/[3,9], and coordinates
`[[1,4,4,5,6,7],[3,6,7,8,8,9]]`. The DNA analogue is exercised through `reads.align`.
Native aliases deliberately report 20 paired, 21 identical, identity .2 and
coverage .1/.2. Both production publication paths and their requested child
returns retain those conflicts but expose these shared results:

| Component | Result |
| --- | --- |
| Paired / identical / alignment columns | 5 / 4 / 7 |
| Paired identity / alignment-column identity | .8 / 4÷7 |
| Query / reference aligned coverage | .6 / .5 |
| Query / reference paired coverage | .5 / 5÷12 |

`numerical_summary.json`, `check001/reads.align.numerical_report.json` and
`check002/sequence.align.numerical_report.json` retain the exact native input,
grading, observation values, preview and requested typed record references.
The tests assert one worker call and one grade call, exact equality with retained
score cells, delivery into the parent's received working state, operation replay
and return redelivery without changing closed runtime observations. Saved-sheet
recalculation runs with alignment execution forbidden.

Executed coverage includes real Biopython 1.88 DNA/RNA/protein local and global
tiny alignments, six real `sequence.align` publication modes, six selected
scientific-child `sequence.align` modes plus `reads.align` DNA/global, real local
no-alignment, native global zero-paired alignment, nontrivial denominator cases,
invalid/missing geometry and traceback, absent/rejected grading, and valid read
siblings surviving an injected resource failure. Alignment-site publication tests exercise
DNA/RNA/protein selected positions, explicit no-alignment and site-grading partial
failure. Direct structure correspondence tests exercise real new native aligned
and no-alignment outputs plus reconstructed legacy shape acceptance.

The historical eight native examples and their entire saved grading results are
recalculated exactly, including issues and numbers. `historical_pins_before.json`
and `historical_pins_after.json` match for the native examples, filled examples
and retained gap-only native fixture. None of those files was rewritten.

All app imports/tests use the established native lifecycle/local-jobs runner:
20 GiB memory, 4 GiB scratch, zero swap and no wall-time limit. Source, dependencies,
interpreter, stdlib and native libraries are pinned; original handles and stdout,
stderr, JUnit results, audit, status and receipts are retained per attempt. Scratch
uses the existing monitored visible-byte enforcement, with its reported possible
overshoot, rather than claiming a filesystem sandbox.

Attempt history (each follow-up addresses a demonstrated test/closure failure):

| Attempt | Actual outcome |
| --- | --- |
| check001 | 90 passed, 5 failed, 1 fixture setup error in 319.55 s. The synthetic sequence child lacked reference scope; four tests assumed a retained null key that Store omits. Structure fixture could not import frozen jsonschema in its independent native service. |
| check002 | 18 passed, 1 structure fixture setup error in 211.77 s. Corrected scope/null assertions and all selected R1 failure cases passed. Independent service imported user-site NumPy 2.5.2 instead of selected frozen 2.5.4, correctly rejected by software identity validation. |
| check003 | 1 structure fixture setup error in 84.26 s. Conventional interpreter layout alone did not prevent the same user-site mismatch. |
| check004 | 1 passed in 2696.54 s (44:56): the existing full structure workflow test completed its exact requested-return and native/grading identity assertions. Original handle collected with exit 0, terminal/quiescent. |

Checks 001–003 were collected from their original handles: terminal/quiescent,
exit 1, unchanged source/dependency/stdlib/interpreter and native-library pins,
empty outside-module and unbound-mapping audit lists. Their failures remain in
the evidence. The final runner keeps its copied interpreter in `runtime/bin`,
the matching copied stdlib in `runtime/lib`, copied dependencies through a frozen
`.pth`, and `pyvenv.cfg` disabling user-site packages. The independent-service
probe in check004 confirms frozen Python/stdlib/NumPy 2.5.4/Biopython paths and
`user_site_enabled=false`; no production software identity check was weakened.

Check004's collected receipt reports unchanged source, dependencies, stdlib and
interpreter. Its execution audit reports pytest return code 0, unchanged native
libraries, no outside modules and no unbound mappings. Observed scratch was
678,264,832 bytes. Service elapsed time was 2702.837198093 s; the pytest duration
above includes the workflow and its validation, not only the alignment's native
execution time. All four original handles are collected and no job was restarted
or resubmitted because a wait ended.

`case_history.json` preserves every attempt per test case. Across the retained
attempts, all 106 distinct selected cases have a passing latest outcome. This is
an aggregate of targeted attempts, not a claim that one fresh 106-case suite was
rerun after the earlier fixture corrections. No broader rerun followed the pass.

The full existing structure workflow used synthetic four-residue PDB 3.x files
and scripted scientific choices with actual native execution and Workflow
communication. It completed two native structure sequence extractions, actual
`sequence.align`, native comparison and saved-sheet recalculation. All 13
requested child forms are recorded and all 14 episodes have yielded. Both
structure-derived operands were authenticated before native alignment; the new
raw native shape and exact retained shared grading passed the structure
correspondence and comparison path. The existing test asserts exact forwarding
of requested summaries into the root's received context.

`structure_workflow_summary.json` indexes the fixture records and four successful
result receipts. Native alignment score is 19 with four paired/mapped residues;
fit uses three pairs, original evaluation uses one pair with SSE approximately
4 square angstroms and RMSD approximately 2 angstroms. The separately requested
saved recalculation evaluates all four pairs and returns RMSD approximately
1 angstrom. Original acquisition/network entry points were denied for that saved
phase. This selected workflow case executes saved recalculation but does not run
the separate structure-specific closed-observation replay assertion; the
Biopython sequence/read operation replay and child-return redelivery invariants
are explicitly asserted by the focused tests described above.

The delegated Biopython R1 repair and approved structure-format compatibility are
verified. This packet does not establish new R2 messages or other tool families,
external API/HPC execution, or large database execution.
