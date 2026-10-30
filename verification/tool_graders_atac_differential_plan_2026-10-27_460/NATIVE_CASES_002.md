# Native MACS2 cases before grader interfaces

The original objective and all sixteen principles were reread after inspecting
the installed 2.2.9.1 commands and source. This packet remains implementation
evidence, not a goal amendment. Prerequisite001 closed successfully with its
original source/interpreter pins unchanged. Only this packet is owned here.

## Version-specific questions

The actual bdgdiff command source writes PREFIX_c3.0_cond1.bed (and cond2/common),
although its help omits the cutoff suffix. Explicit three-filename -o selection
can remove ambiguity without guessing an output directory. Native depth scaling
uses min(depth1, depth2)/depth_i. The score class adds its 0.01 pseudocount before
that scaling, calculates three likelihood components, stores float32 values,
and uses length-weighted means over qualifying segments when merging regions.

The source also calls add(chr, pre_p, values) before advancing pre_p to the next
track boundary, while the receiving field is described as an interval end.
This suggests a coordinate displacement. It is a hypothesis until checked with
actual native output. Never silently repair a reported native interval, call it
a measured interval, or turn a failed/mismatched region into zero.

## Exact probe inputs and outputs

Use the prepared Python 3.11.13/MACS2 2.2.9.1/pysam 0.23.3 environment. No install,
network request, source patch, production library edit or resource substitution
is needed. Freeze the probe and all installed package files used as inputs;
run through local_jobs/native_lifecycle with 20 GiB RAM, zero swap, 4 GiB scratch,
no wall budget, original handle and retained command receipts.

1. Four supplied continuous bedGraph tracks on chrToy[0,500), with five explicit
   100-bp segments. Signal1=[0,20,10,2,0], background1=[1,1,1,1,1],
   signal2=[0,2,20,40,0], background2=[2,2,2,2,2]. The selected depth inputs are
   1 and 2 million reads; these are declared synthetic fixture values, not counts
   inferred from the tracks. Run native bdgdiff at cutoff3, min length50, gap0,
   with exact three output filenames. Export the real TwoConditionScores arrays
   separately to inspect exact stored positions/float32 component values, and
   compare native output positions with the explicitly known input intervals.
   This export is a separate explicitly selected diagnostic execution, not a
   claim that the CLI emitted those arrays itself.
2. Actual coordinate-sorted BAMs with a declared 12,000-bp synthetic reference.
   Condition1 has100 distinct single-end records plus5 exact-coordinate
   duplicates; condition2 has200 distinct records. Use callpeak BAM mode,
   keep-dup1, nomodel, shift-100, extsize200, q0.05 and -B for each condition.
   Retain native peaks, pileup/background tracks, XLS header counts and logs.
   Derive the two bdgdiff depth operands only from each actual XLS's explicit
   tags-after-filtering count, divided by1e6. Do not substitute the requested
   number of input reads. Run bdgdiff with cutoff3/minlen50/gap0 and explicit
   filenames. Preserve any native failure and all prior usable output.

Retain complete native files, exact argv, exit statuses, native score arrays,
input-generating descriptions and file hashes. No gene-function probability,
replicate-variance estimate, fitted differential-expression model or biological
result is claimed. A successful native run still leaves the scoring-sheet,
parser/calculator, production execution and typed episode return work unfinished.

The next contract must resolve any demonstrated native coordinate defect,
state which exact operation produces valid measurements, and preserve the raw
native result alongside any separately named corrected calculation. It must
not propagate a known defective coordinate mapping merely to match a fixture.
