# Selected-alignment fields and functions: completed connection

This adds to REPORT_001.md without changing its historical claims. The missing
native paired-BLAST source connection described there is now implemented and
verified by workload 300. The three fixed rows covered here are
A-L064-native-pairwise, A-L064-blast-hsp and A-L064-mapping-correspondence.

The deliverables are reusable field definitions, functions that populate those
fields from retained alignments, separate numerical calculators, and delivery
of the requested fields through the scientific child's existing return path.
Filled sheets are verification examples.

## Fields and functions

The reference-position sheet retains the selected positions, duplicates,
actual correspondence, gaps, insertions, original-coordinate ancestry and
available read quality. The BLAST column sheet retains the selected window,
symbols, operand intervals, units, frames, directions and original whole-HSP
measurements. Separate calculators produce counts and identity/coverage ratios
with explicit numerical numerators and denominators. Saved-sheet recalculation
does not acquire data or rerun the alignment.

The new native_blast_pairwise_hsp host function authenticates the actual native
paired source, full operand identities, report membership, original HSP ordinal
and retained measurements. Existing selected-column functions use the actual
JSON or declared-table coordinate convention. The API source path retains its
own identity and validation. The existing own-action and requested-return
consumers accept the new source without creating another scientific observation.

## Verification added after the baseline

- All twenty retained actual native paired reports and all thirty-six HSPs
  pass through their production publication functions and the column functions.
- One actual small reverse-BLASTX execution passes through the existing local
  launch, results, scientific-parent receipt and scientific-child selected-column
  return. Its four identical pairs give identity 4/4, query coverage 12/244 and
  reference coverage 4/80. The query intervals are [209,212), [206,209),
  [203,206), [200,203) nucleotides; reference intervals are [10,11) through
  [13,14) amino acids. Original frame -3 is retained.
- That path records one site action, one site calculation and no new scientific
  observation for viewing the HSP. There are seven total completed actions and
  seven observations. Closing and repeated delivery use the stored facts, with
  the calculator disabled after the original extraction.
- Workload 300's successful runs contain 297 distinct passing test cases,
  independently checked against JUnit identities. Its final 27-case check has
  1,235 tracked files unchanged during execution. Earlier limited manifests and
  failed checks are preserved and qualified in its VERIFICATION.md.
- The actual frozen tool library supplies both selected-site instruction
  entries. Paged knowledge reads reconstruct their complete text. This check
  executes no scientific tool and creates no scientific record.

The original baseline's source snapshot differs now in five deliberately
extended production/instruction files and the root-owned index. Those exact
changes are covered by the workload 300 receipts and the library check. All
other baseline tracked files remain unchanged. The completion manifest records
the comparison; the old snapshot has not been rewritten.

The separate five-case BV-BRC regression verification also passed on its
isolated source snapshot. That resolves the five earlier provenance errors
without changing the original broad test result or asserting an all-suite pass.

## Scope of the result

The reference-position and mapping rows use their existing verified scientific
child paths and retained native artifacts described in REPORT_001.md. The
selected native BLAST columns add the actual full Workflow example above.
Only reverse BLASTX was newly executed through the whole Workflow for workload
300; the other native program/format cases reuse actual retained reports.
Missing-string and conflicting-format tests are explicitly synthetic.

These checks establish the specified numerical fields/functions and receiving
paths. They do not establish new API/HPC deployments, autonomous scientific
decision quality, an annotation score, W05, literature grading, every producer
resource path, or complete implementation of all fixed inventory rows. The
earlier phmmer example still uses its documented older flat launch route.
