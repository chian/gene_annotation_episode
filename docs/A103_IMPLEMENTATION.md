# A103 gene context

A103 measures genomic organization around an authenticated target locus or a
specifically attributed reference locus. A101, A102 and A105 are implemented
independently. A103 never commissions another evidence axis below itself;
acquired evidence and missing operands are published through the shared parent.

`A103Subtree` supplies the recursive scientific episode contract for locus
identity, organization, component attribution, comparative context, fusion and
regions, cooccurrence, functional contrast and synthesis. These are possible
investigations, not mandatory stages. The common episode loop decides what to
commission. Typed reports distinguish measured organization, association and
functional interpretation; an asserted exact activity cannot create credit.

## Native tools and custody

| Operation | Measurement and attribution |
|---|---|
| `context.bind_locus` | Actual GenBank/GFF3 CDS, coding sequence, genetic code, translation, original coordinates, placement alternatives and source. Caller-supplied target provenance is host bound. Inventory alone contributes zero. |
| `reference.neighborhood` | Reuses the existing genomic neighborhood reader; retains actual features, strands, circular boundaries, signed distances and incomplete flanks. Native annotations remain annotations. |
| `context.compare_neighborhoods` | Fixed organization predicate over declared loci. Each row requires the particular target/homolog and neighboring-component correspondence. Unknown rows retain their denominators and bounds. Sampling is balanced within genome, then within group, then between groups. |
| `context.fusion` | Regions in one actual verified CDS, with separate component maps and explicit definitions. Mapped target traits become local features, including three-base footprints for translated nucleotide inputs. |
| `context.detection_inventory` | Consumes a completed native HMMER search, its authenticated output and exact searched FASTA. Records inclusion state and actual examined CDS coverage. It performs no sequence search. |
| `context.cooccurrence` | Exact one-sided enrichment, contingency table, effect direction, sampling groups, background and unknowns, from received detection inventories. |
| `context.association_channels` | Authenticated STRING `nscore`, `fscore` and `pscore` separately; exact endpoints require received canonical sequence/cross-reference records. Combined scores do not qualify. |
| `context.contrast` | Compares qualified context measurements and their uncertainty against explicit alternatives. Adds no second copy of underlying context credit. |

Every native result has an immutable Source, native sheet and registered
custody. Publication and receipt automatically select the per-use attachment
by schema and actual operands. `episode.credit` is read-only. Late sequence or
endpoint evidence regrades retained measurements without repeating context
jobs. A late detector receipt must match the exact target, expected component
and neighborhood. A negative call also requires a completed native search and
complete coverage of that neighborhood's CDS inventory. The qualified family
relationship can then be false while the original neighbor geometry remains
retained. Conflicting calls remain unresolved.

A family-query map can be inverted for the particular observed component or
region; its scores and statistical direction remain those of the original
native calculation. An exact native placement of a supplied protein feature
maps its local residues back to the original target without another alignment.
A copied label or an arbitrary strong alignment cannot satisfy a missing
component, domain or reference-locus link.

The typed return uses `a103_received_context_records`: completed own records
plus actual received context measurements, per-use grades and mapped local
features. A synthesis can therefore return retained evidence without rerunning
an algorithm. Unreceived upstream records are not implicitly forwarded.
Unsupported functional interpretations fail the report boundary. A parent can
redeliver the same frozen records and independently checked credit through the
measurement-only form while leaving those interpretations rejected.

Sequence-search returns preserve an external protein as their bound query
operand. Both typed coverage and saved-return validation admit that exact
operand, with its molecular/scope check and an original receipt in the results
child. The reference does not become an annotation target. This matters for
neighbor-family searches: rejecting an existing EF-P alignment at the return
boundary previously caused an unnecessary reverse query instead of qualifying
the retained A103 comparison.

## Numerical policy

`a103_bounded_context_progress_v1` measures investigation progress. It is not a
probability of a proposed function. Native recurrence retains actual counts
and group denominators. For each qualified row, its measured context value is
qualified by the specific required sequence/region correspondence, retaining
identity, mapped extent and native strength. The native association must exist
before any attribution can contribute.

The projection takes the maximum compatible eligible contribution in each
original target scope cell, then a length-weighted mean. Duplicates do not add
credit; competing variants remain unresolved. Partial attribution retains a
lower bound and unknown extent. The cooccurrence significance index is
`L/(1+L)`, with `L = -log10(p)`, admitted only for positive effect and independent
declared sampling. Raw p and effect remain available. Related samples cannot
silently acquire independent-row significance.

The root currently enables A101, A102 and A103 and computes
`product(1 + enabled_axis_credit) - 1` independently for each original target,
then takes the assigned-length-weighted mean. An empty axis leaves earned
credit unchanged. Aggregate A101 credit is never an A103 multiplier.

## Execution and verification

All execution must use the [whole-workflow launcher](LOCAL_EXECUTION_POLICY.md),
whose aggregate cap includes Python and provider processes. The current local
budget is 512 MiB RAM, one CPU, zero swap and one workflow per Codex window. Any native profile
requesting more cannot run locally under this budget. Heavy algorithms need
remote execution or explicit user approval for another concrete budget.

All native operations also use the existing shared host admission gate. The A103 profile requests
one CPU thread, at most 2 GiB memory, 1 GiB scratch and 180 seconds per job under
the default policy. Requests and limits reach the parent. A busy host preserves
the prepared handle. Large investigations require a separately configured
resource rather than bypassing local admission.

`examples/a103_gene_context_investigation.py` runs retained real PoxA/YjeK/EF-P,
BioY/BioMN, YjeF and MJ0044 inputs. Fresh A103 scientific choices use the configured
model; the parent handoff and existing native HMMER launch/results mechanics
are scripted and reported as such. This harness explicitly selects a smaller
native profile: one CPU, 128 MiB memory, 32 MiB scratch and 180 seconds. The
whole workflow still has its separate 512 MiB aggregate cap. The scripted
parent preserves a requested family query, shares the exact missing operands,
and reuses complete panel searches by peptide identity. Expected biological interpretations are not
supplied to the model. Required sequences, original GenBank responses and
provenance hashes live with the tests. Disposable databases, traces, source
snapshots, temporary files and caches belong under `runs/`.

The pre-reset investigations were interrupted. Partial grants and scripted
detector controls do not count as completed fresh investigations. The snapshot
runner's `--retained-case` option makes a consistent read-only backup of a
previous case's records and artifacts, declares the received records explicitly,
and starts new A103 model decisions. Completed native searches are reused only
after their custody, query sequence, termination and exact database hash pass
validation. The handover chain distinguishes retained measurements from newly
executed jobs. Repeated activity questions do not complete a comparison case:
the controller requires measurements covering its supplied genomic sources.

Each completed run audits actual native job receipts, nonoverlapping job
intervals, source-backed credit, and latest A103 owner versus receiving-parent
credit. See `tests/a103_run_audit.py` for the read-only audit, and
`tests/test_a103_context.py` for missing-link, local-scope and custody controls.

## Completed real cases

The four completed investigations have these controller results. A102 is zero
in these context investigations; the root uses the independent-axis formula
above. These numbers describe investigation progress, not function probability.

| Case | A101 | A103 | Root |
|---|---:|---:|---:|
| BioY/BioMN | 0.783140 | 0.500000 | 1.674711 |
| YjeF | 0.231179 | 0.084809 | 0.335594 |
| MJ0044 | 0.818507 | 0.333333 | 1.424676 |
| PoxA/YjeK/EF-P | 0.994159 | 0.937134 | 2.862953 |

YjeF completed with fresh model choices and native execution. The other three
completed with fresh model choices on explicitly declared retained real
measurements, adding native work where still required. Interrupted attempts
remain in their handover chains and are included in the job/resource audit.
Every latest A103 owner agrees with the receiving parent. Every positive A103
contribution has an actual native context measurement.

BioY retained measured BioN-like/BioM-like organization at the target and scoped
nondetection in an examined complete 11-CDS reference neighborhood. Detector
receipt resolved the older comparisons' unknown bounds automatically, without
rerunning those measurements. An expanded incomplete genomic record remains
unknown; the local result is not whole-genome absence.

YjeF placed two independently mapped regions at zero-based intervals [32,195)
and [241,462) in the same verified 515-residue coding product. The partial,
distant domain correspondences limit fusion credit. MJ0044 measured different
organization across three loci; a pseudogene in one examined reference window
keeps that row unknown and its comparison bounds at [1/3,2/3].

The YjeK target has measured divergent EF-P adjacency in E. coli and Salmonella,
with 41-bp and 40-bp gaps. A third, actual W83 KamA locus supplies a contrasting
local context with scoped EF-P-family nondetection. The fully attributed
expanded comparison contributes 0.468567. The controller retains the higher
two-positive-locus contribution, 0.937134, under the approved maximum-pooling
policy; adding a contrasting panel does not erase that prior measurement.
Exact activities and partner necessity remain unresolved by these context
measurements.

The retained-chain audit counts completed native commands separately from
unreleased preparations. The latter includes one canceled neighborhood
preparation for MJ0044 and one canceled parser preparation for PoxA; neither
native command started. All completed native jobs succeeded. Counts below
include earlier retained work, including the PoxA parser recovered from an
already completed native HMMER output. They exclude separate engineering
controls. Workflow time includes unsuccessful attempts in the declared chains.

| Case | Completed native jobs | HMMER searches | Native wall seconds | Workflow minutes | Peak scratch MiB |
|---|---:|---:|---:|---:|---:|
| BioY/BioMN | 21 | 3 | 41.06 | 35.25 | 157.91 |
| YjeF | 5 | 1 | 8.22 | 3.19 | 99.84 |
| MJ0044 | 18 | 4 | 34.81 | 18.31 | 160.43 |
| PoxA/YjeK/EF-P | 19 | 4 | 37.88 | 18.14 | 148.99 |

Actual native intervals do not overlap within or between these case histories.
Every native request used one CPU, at most 128 MiB memory, 32 MiB scratch and
180 seconds. All workflows kept the 512 MiB aggregate memory cap, one CPU and
zero swap; the largest recorded memory peak was 512.62 MiB, and none of these
case histories had an OOM event. Scratch stayed below the monitored 256 MiB
workflow limit.

A separate scripted control over the real two-locus YjeK/EF-P inputs exercised
the corrected external-query return end to end. It completed with A103
0.937134, root 2.862953, nine native jobs (two searches, two parsers and five
context measurements), owner/parent agreement and no undelivered results.
Exactly two required family searches sufficed; no reverse EF-P query was
launched. The four-case PoxA history still truthfully includes the earlier
unnecessary fourth query. The real retained BioY scope control also preserved
local nondetection versus unknown incomplete-record coverage without a new
sequence search or context measurement.
