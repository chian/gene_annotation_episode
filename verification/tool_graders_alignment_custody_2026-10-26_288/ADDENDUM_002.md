# Final host-boundary verification

This is additive to REPORT_001.md. The original report, failed logs and passing
run_002 examples remain unchanged.

## Final executed result

`run_004` passed all **65 tests**, with no failures or skips, in **98.15 seconds**
of pytest time (98.906 seconds measured by the local execution service). The
before/after source hashes are identical: `changed_sources=[]`.

The run used `.venv/bin/python` through the existing
`gene_annotation_episode.local_jobs.run_local_job`, 20 GiB RAM, 4 GiB scratch
and no wall-time cap. Full stdout, stderr, JUnit, invocation, resource metadata
and source hashes are in `run_004/`. The test source SHA-256 is
`b77e77c1f9eb6d40137991e33d0e0a85e4f087b167ac143bfeb9d875d4269eee`.

## Source reassignment repair verified

Root corrected the original native-source/operand association identified by
both failing run_003 counterexamples. Each counterexample creates a new,
digest-valid alignment observation with a real, different same-length query
or reference, while retaining the original native alignment source. It also
updates the observation's dependencies and operand intervals consistently.
The new observation is rejected before site publication; matching lengths and
internally valid record identities do not prove native operand association.

Root's new Biopython sources retain ordered unique operand identities, and the
site reader/host port check them against the selected alignment. The analogous
phmmer path uses its existing operand identities. This suite directly exercises
the Biopython reassignment cases; it does not claim a new native phmmer run.

Two additional tests exercise legacy Biopython publication. Each performs a
real native `sequence.align` call, removing only the newly introduced
`operand_refs` source metadata at the `_source` seam to represent the old
source shape. With the actual saved producer operation and arguments present,
the result is usable and its selected sites report two paired positions, one
identical. Removing that producer operation makes the later site request
invalid with no published records. No fabricated producer operation substitutes
for actual native publication.

The run_001 frozen-scope failure, native processing-unit and minimap2
quality/geometry failures described in REPORT_001 and messages to root also
remain covered by this passing full run. All production corrections were made
by root; workload 288 changed only its assigned tests and verification files.

## Exact verification limits

This suite verifies the host ports against real saved Store, Journal,
BindingContext and receipt state and actual ToolRegistry results. It verifies
declared selection/pagination, original assignment authentication, durable
operation joins, pre-action HSP receipt authority, exact native artifact and
operand association, legacy versus failed versus empty results, and frozen
facts with JSON types preserved. It does not recompute grading during closure.

Native execution here comprises tiny Biopython pairwise alignments and one
forward/reverse minimap2 mapping fixture. The BLAST cases use a synthetic
offline native-response fixture through the real publisher and reader. There
was no API request, HPC deployment, database BLAST run, or live annotation.
The fixture records runtime own actions directly. Complete Workflow child
commission, parent admission, replay/redelivery and credit-continuation
verification remain root's separate integration responsibility.

The seven complete numerical envelopes in `FILLED_EXAMPLES_001.json` remain
unchanged run_002 evidence. No prior result was recalculated or relabeled as a
run_004 result.

Before handoff, the immutable original objective and all sixteen design
principles were reread verbatim, followed by CONTRACT_001.md,
RETURN_CONTRACT_002.md and OWN_ACTION_RETURN_PORT_PROPOSAL.md. No requirement,
inventory completion row, annotation-credit rule, literature grader or
episode prompt was changed by this workload.
