# Actual bedtools deployment and native format checks

Root verification, 2026-10-27. Seven corrected native cases passed using an
explicit project-local bedtools v2.31.1 executable. This establishes the local
prerequisite and the observed nine-column output on synthetic interval inputs.
It does not establish the overlap grader, tool-library binding or episode path.

The extracted executable is
`software/bedtools/ubuntu-2.31.1+dfsg-2/installation/usr/bin/bedtools`, under the
repository. The Ubuntu noble/universe amd64 package was downloaded using the
local signed APT metadata and extracted in project storage. No global package
installation or PATH change is claimed.

| Identity | Value |
| --- | --- |
| Package | bedtools_2.31.1+dfsg-2_amd64.deb |
| Package bytes | 673776 |
| Package SHA-256 | 2be06af20009e942be1b332b54220cee397ecfe51c24578bb586b584a3a30b5e |
| Executable SHA-256 | b6c6e44b79180f0c9f64f916010c71bcd44baf81e5abe71b63f19aa9d4bc9fb6 |
| Actual version response | bedtools v2.31.1 |

`SOFTWARE.json` in that installation directory retains the original identity.
The bounded preparation/test invocation and readonly executed script are in
run001; the corrected independent check and its readonly script are in run002.

## Preserved failed expectation

Run001 downloaded/extracted the executable and passed six cases using explicit
`-f 1e-30 -F 1e-30`. Its seventh assertion incorrectly expected the default
fraction options to omit a one-base overlap within a two-billion-base interval.
The actual default invocation returned that overlap. This was a false test and
planning assumption, not a failure by bedtools. The original script, failed
CHECK.json, native stdout/stderr and nonzero receipt remain unchanged. The final
signed-64-bit case in that original script was not reached.

Run002 uses the corrected invocation for all seven cases:

```text
<explicit-bound-bedtools> intersect -a <A-BED4> -b <B-BED4> -wo -sorted
```

| Synthetic case | Actual pair rows | Actual sum of native widths, bp |
| --- | ---: | ---: |
| Overlapping A intervals | 2 | 8 |
| Both inputs contain overlapping intervals | 3 | 13 |
| Duplicate occurrences in both inputs | 4 | 20 |
| Intervals touching only at an endpoint | 0 | 0 |
| Different chromosome strings | 0 | 0 |
| One base within a two-billion-base interval | 1 | 1 |
| One base at endpoint 9223372036854775807 | 1 | 1 |

Every actual stdout line exactly matched its expected line; every native process
returned zero. Full commands, native rows, output hashes and timings are retained
in run002/work/NATIVE_CHECKS.json and its per-case files. Earlier input pins are
unchanged. These sums are pairwise multiplicity quantities, not unique shared
base coverage. The future deterministic calculator must calculate that separate
quantity from validated pair intersections.

The native fixtures use A1/B1-style tokens. The accepted G1 normalizer generates
s0_r0-style tokens. Untouched files here establish actual native format and
arithmetic, not a completed canonical-token G1 parser path. Token-remapped
fixtures must be identified as derived; a later actual bound driver test will
verify the complete canonical-token path.

## Resource and source receipts

Both runs used local_jobs with 20 GiB RAM, 4 GiB scratch, zero swap and no wall
allocation. Verified runtime maximum is infinity. Scratch is the existing
monitored visible allocation with possible overshoot and a hard per-file limit;
no filesystem sandbox is claimed.

| Receipt | Return code | Service wall seconds | Observed scratch bytes |
| --- | ---: | ---: | ---: |
| run001/receipt.json | 1 | 1.276403783 | 2588672 |
| run002/receipt.json | 0 | 0.316134146 | 143360 |

Readonly executed scripts, checkout script pins and the three existing native
infrastructure sources stayed unchanged during both invocations. Service wall
time includes the selected wrapper work; it is not a pure interval calculation
duration. No API/HPC operation, model call, annotation-credit change, literature
grader or whole-tool completion is claimed.

After examining the actual outputs, root reread the immutable goal's objective
and all sixteen principles verbatim. Packet418 section12 records the corrected
invocation additively. Packet422 accepts only the separate pure G1/G3a workloads;
native driver/local binding and shared episode integration remain unfinished.
