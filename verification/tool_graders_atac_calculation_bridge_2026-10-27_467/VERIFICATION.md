# ATAC native-sheet calculation-input bridge verification

This is an additive implementation receipt for contracts 460/010, 011 and 013.
The authoritative original attachment has SHA256
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
Its full text was read first; the objective and all sixteen principles were
reread after substantial source/native examination and before handoff.
`GOAL.md` was not read or used. This component does not increase the 308 tally.

## Owned implementation

* `gene_annotation_episode/atac_differential_calculation_inputs.py` provides
  `prepare_atac_calculation_inputs(sheet, *, intervals, ordered_track_rows=None)`.
* `tests/test_atac_differential_calculation_inputs.py` tests its actual consumers.
* This packet owns the runner, exact retained-header fixture copies, immutable
  source/input snapshots, native-job handles, receipts and filled examples.

The bridge validates exact logical roles, conditions, samples, source artifacts,
producer runs, raw-pileup units, depth observations and selected reference
populations. It ignores summary compatibility flags as evidence, keeps each
independent numerical port, and retains shared-content/sample/input dependence.
It does not open paths, parse new artifacts, acquire data, execute native work,
invoke a model, select resources, alter prompts or assign credit.

External numerical tables remain lazy. Invalid reference-bound rows retain
their geometry/ordinal and null only their calculation operand. Negative
numbers, null cells, duplicate rows and unlocated corruption reach the existing
interval classifier. Aliases can reorder an in-memory derived index; an external
stream requiring a changed order raises `atac_projected_track_order_required`.
The raw sheet is unchanged throughout.

Each failed lazy port preserves preceding records and propagates its exception.
The result-worker caller must drain the other supplied ports before sealing
final identity, persist every failure, and save final qualifications after
exhaustion. The bridge does not silently drain another source or recover a job.
When depth units disagree, the returned unit is null; retain the partition and
unavailable-calculation qualification rather than inventing a unit for the leaf.

## Final bounded test receipt

`check004` ran **106 tests, all passed, in 1.23 seconds**. It executed only the
owned test module, importing real parser/sheet helpers and interval/score
consumers from the immutable source snapshot. Tests did not execute MACS2,
inspect BAMs anew or reacquire any scientific input.

* Original handle: `check004/handle.json`.
* Original unit: `gene-local-job-d8d9e35dd32e4847a6ba76760e10072a.service`.
* Receipt: `check004/receipt.json`; exit 0, terminal=true, quiescent=true.
* Verified limits: 20 GiB RAM, 4 GiB scratch, zero swap, no wall-time budget.
* Source, input and interpreter/runner pins were unchanged; checkout drift was
  empty at collection. The runner uses existing `local_jobs/native_lifecycle`.
* `check004/junit.xml`, stdout/stderr, selected request and before/after pin
  manifests retain exact execution evidence.

Earlier check001 passed 79 and check002 passed 83 overlapping checks, before the
actual BAM-dictionary consumer was added. Their BAM checks established declared
metadata only. Check003 passed 106 in 1.03 seconds after 013; its original handle was
collected with unchanged pins. Check004 adds complete saved BAM output examples
and a direct independent-component assertion. These counts are not additive.

## Retained native numerical example

The actual 460 explicit-track bytes passed through `parse_atac_bedgraph`,
`build_atac_differential_sheet`, this bridge, `iter_atac_track_segments`,
`iter_atac_interval_components` and `iter_atac_differential_regions`. Both
in-memory rows and authenticated retained JSONL streams were checked. These are
synthetic engineering inputs whose MACS2 outputs were retained, not biological
validation. Declared depths remain 1 and 2 `million_tags`; pseudocount=0.01.

Every float32 likelihood equals the separately retained native diagnostic value:

| chrToy interval | condition1/background | condition2/background | condition1/condition2 |
| --- | ---: | ---: | ---: |
| [0,100) | -0.41425126791000366 | -0.42277848720550537 | 0.0008388275746256113 |
| [100,200) | 17.699888229370117 | 0 | 17.7408447265625 |
| [200,300) | 6.062438011169434 | 6.076850414276123 | 5.425064273367752e-7 |
| [300,400) | 0.1664436310529709 | 17.734350204467773 | -12.148710250854492 |
| [400,500) | -0.41425126791000366 | -0.42277848720550537 | 0.0008388275746256113 |

With cutoff 3, minimum 50 bp and gap 0, the three separately derived regions are:

| Category | Interval | Float32 mean score |
| --- | --- | ---: |
| condition1 | [100,200) | 17.7408447265625 |
| common | [200,300) | 5.425064273367752e-7 |
| condition2 | [300,400) | 12.148710250854492 |

The full original sheet, five component rows and three derived regions are in
`check004/FILLED_NATIVE_EXAMPLE.json`. Native BED coordinates and decimal scores
remain untouched: for example condition1 still reports [0,100), score 17.7408.

## Actual BAM reference observations and saved output

The original 468 bounded read-only inspection retained both actual 48-byte SAM
headers with SHA256
`de304859b98b91098107cee514e9a4db20a605030e9c14433f505ad5815af891`.
Each declares `chrToy` length 12000; neither has M5. Exact copies and original
input/header/receipt provenance are in `native_headers/CUSTODY.json`. Workload 468
performed that inspection; this workload consumed its retained bytes only.
Matching dictionaries establish compatibility under the supplied reference
assignment, not identical genomic sequence. Missing M5 stays unknown.

The real parsers/sheet/bridge select post-filter counts 100/200 `tags`, preserving
native totals 105/200 separately. The actual header records bind to their exact
run/input occurrence. Both original BAMs have different byte identities despite
identical header content; their occurrences are retained independently.

`check004/FILLED_BAM_EXAMPLE.json` retains the complete native sheet, 415 derived
partition/component rows and two derived regions. Calculated condition1 is
[908,1141), float32 mean 149.95016479492188; calculated condition2 is [2916,3183),
mean 117.07485961914062. These are outputs of the separately verified partition
and scoring functions, not a claim that native displaced BED coordinates/scores
are their oracle. Original native BED rows remain [907,1140), 147.378 and
[2915,3182), 116.383; the native common BED retains zero reported rows.
Condition1's [8060,10060) span and all tracks' [10060,12000) tail remain unknown
where unreported, never substituted zero.

## Counterexamples and inspected boundary

Tests cover independent absent/incompatible background2; swapped roles,
conditions and producers; wrong run/input/sample/reference associations;
missing reference lengths, unknown chromosomes and explicit aliases; actual
reference overruns versus a narrower selected population; overlapping invalid
rows; zero, negative and null values; unlocated corruption; duplicate source
occurrences; complete empty versus absent files; failed producers with readable
rows; unverified identities; late checksum/read/order failure; caller draining
two separately failing streams; huge coordinate spans without per-base arrays;
genuine missing and zero native depths; forged depth values/locators/artifacts;
declared unit/population/lexeme mismatch; and contradictory copied summary flags.

Actual BAM-header checks include historical missing observations; matching
reference labels with conflicting actual lengths; wrong run/input ordinal/ref;
missing, duplicate or malformed required SQ fields; partial/unsupported and
unverified headers; unlocated dictionary corruption; selected-population versus
extra contigs, including an identifiable malformed unselected contig; aliases;
present conflicting M5 versus unknown M5; and same-content distinct input
occurrences. Saved-sheet recalculation forbids file access, sockets and native
subprocesses, changes explicit scoring parameters, and leaves native data fixed.

Complete relevant modules/paths inspected: the ATAC contracts, native parsers,
sheet/depth selector, new BAM reference parser and assembly extension, all
interval/region and numerical-leaf consumers, exact fixture helpers and retained
native evidence, local_jobs/native_lifecycle, and the actual runner. Required
episode/resource design documents were read; none of those behaviors changed.

This establishes a parser→sheet→bridge→calculator component integration. It does
not establish the selected-tool/resource-child producer binding, production
result worker, persisted result receipts or typed episode-return path. Those
remain root-owned integration work. No live MACS2, API/HPC job, configured-model
episode, W05/evidence-axis/literature implementation or tally increase is claimed.
