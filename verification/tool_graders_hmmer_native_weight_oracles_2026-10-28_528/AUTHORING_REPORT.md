# HMMER native helper oracle authoring — packet 528

Status: authored and statically inspected; unexecuted. Only standard-library
inspection, editing, hashing, JSON handling and AST parsing were performed.
No application/test module was imported, no test collected or run, and no
compiler, native program, network request or resource job was launched by this
author. Consequently this packet establishes no new numerical/native/episode
verification result and does not complete R2 or an inventory row.

The original supplied attachment remains authoritative. Its complete contents,
AGENTS.md, contract 516, helper implementations/tests/reports from packets
524/525, and the complete affected common-normalization/reconstruction functions
were read. The objective and all ten operating principles were reread verbatim
after tools/source examination. The same objective/principles and current 516
contract are reread before final handoff. No GOAL.md or replacement goal/scope
file was read, created, edited or used.

## Authored files and numerical ownership

`tests/test_hmmer_alignment_native_weight_oracle.py` contains 57 planned pytest
cases. It compares the existing `gsc_raw_weights`, `blosum_raw_weights` and
`sample_easel_pb_rows` implementations with runtime native diagnostics. All
normalized Python weight comparisons use the one existing
`hmmer_alignment_preparation_calculations._normalize_easel_weights` function.
The private MT word-stream comparison uses the existing sampler class. There
is no duplicate normalization, pair-identity, tree, clustering or sampling
algorithm in this test.

`weight_oracle.c` is a verification-only adapter. It includes the retained real
`esl_msaweight.c` and intercepts DNorm solely to copy its incoming vector, then
immediately calls original DNorm. DScale is untouched. Its raw and normalized
weights therefore come from the actual native GSC/BLOSUM routines. It calls
real XDiffMx/UPGMA/SetCladesizes for the diagnostic tree, SingleLinkage for
cluster arrays, XPairId for identity operands, and native vector operations for
standalone normalization. The original numeric C sources are separately compiled
and linked, with the retained archive supplying other Easel support. `%a`
strings retain exact native doubles; no rounded Stockholm WT is used as an
internal weight oracle.

The sampler reuses packet 525's `sampler_oracle.c` unchanged. It compiles the
actual `esl_rand64.c` and emits full native row arrays or uint64 streams. The
case inputs are constructed and labeled as such. No hand-written expected
array masquerades as a captured native result. Sample counts and all returned
row ordinals remain inspectable in job-local outputs.

Only the assigned new test and this packet were changed. Existing production,
tests, runtime, prompts, inventory and documentation were not edited. The
common production snapshot remains owned by packet 526/root. The oracle does
not add a scoring sheet, acquisition operation, execution policy, credit
observation, continuation rule or episode type.

## Planned conformance coverage

| Group | Planned cases | Exact comparison |
| --- | ---: | --- |
| GSC | 15 | Raw/normalized doubles, native Kahan sum, ordered children, branch doubles and clade sizes |
| BLOSUM | 16 | Raw/normalized doubles, native Kahan sum, native assignment IDs/sizes and exact cutoff |
| Shared normalizer | 6 | Native DSum, DNorm then DScale for zero-sum 49-row and roundoff-sensitive positive operands |
| Native Deal | 17 | Every sampled row ordinal; N=50,001 and 130,001, m=10,000, seed42, strict N=130,000 boundary, positive seed edges, m=1/full sample, safe integer boundaries |
| Native MT stream | 3 | Every one of 625 uint64 words for seeds 1, 42 and UINT64_MAX, crossing two refills after initialization |

Alignment cases include singleton/no-residue singleton, identical canonical or
degenerate rows, identical all-gap rows, mixed gap/missing/nonresidue inputs,
minimum-residue-count identity denominators, exact UPGMA ties, reordered source
rows, clade-weighted distances, zero-subtree allocation, transitive links,
BLOSUM reverse-stack cluster IDs, cutoff equality and its next representable
larger double, endpoints 0/1, RNA and amino-acid degeneracies.

For example, the explicitly supplied pair `A-CG` / `AT--` is expected to expose
one identical residue and denominator 2 through the real XPairId call. These
are source-derived input semantics; this author has not observed the native
answer. Numeric weights, tree arrays, cluster IDs and sample indices are read
from C at test execution, not substituted by that example.

Singleton GSC does not invoke native UPGMA: its empty diagnostic arrays are
explicitly labeled `singleton_early_return_no_native_tree`. The singleton raw
weight is copied from the real early-return result. Singleton BLOSUM cluster
diagnostics are obtained by an independent actual SingleLinkage call, whose
basis is separately labeled.

## Inputs, verification state and handoff

The finite native dependency closure is 40 .c/.h files plus the retained
`libeasel.a`, selected `alimask`, and companion `alimask.c`: 2,453,821 native
bytes. `SOURCE_PINS.json` records individual hashes/sizes, the explicit profile
association, the two diagnostic hashes, and the exact 46-entry `support_files`
list including its own manifest. The selected executable digest is
`4cf273b7b4b52363468b758a39bedf8f00540b01983bf6641ffd36140afad547`;
the source version is HMMER 3.4 inside Infernal 1.1.5 with Easel 0.49. This
association does not establish the selected executable's original compiler or
prove that a separately compiled diagnostic behaves identically to its CLI.

`RUN_REQUIREMENTS.md` supplies the exact selected test, environment paths,
compile/link options, native support inputs and output-retention requirements.
Root accepted the explicit three-variable boundary and owns the configured
compiler/system library pins and the frozen native_lifecycle/local_jobs job
under 20 GiB RAM / 4 GiB scratch / no swap / no wall-time cap. The fixture
fails on absent or changed required inputs, records complete process outcomes
before comparisons, and never falls back to host Easel discovery or skips.
`AST_CHECK.json` reports static parsing and the planned case count; it is not a
pytest result. `FROZEN_MANIFEST.json` identifies the authored handoff bytes.

Native seed zero and m=0, out-of-range counts, and native signed-overflow setups
are excluded. Arbitrary positive helper seeds are separate from alimask's
effective PB configuration seed42, which remains independent of supplied CLI
seed. None of these helper cases verifies the N>50,000 eligibility decision,
fragment rejection/fallback, full weighted occupancy/map, original alimask CLI,
or the full child-owned Workflow return path. Those checks, saved-only
recalculation and closed replay remain packet 526/root responsibilities.

Remaining for this packet: root-owned compilation and actual execution of all
57 cases, inspection of retained native output/receipts, and any repair justified
by a real failure. Exact double/libm conformance is still unverified. No broader
unfinished deliverable is hidden or reclassified by this authoring record.
