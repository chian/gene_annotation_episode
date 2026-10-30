# Infernal cmalign numerical sheet and calculators

## Authority and reset

Read the entire authoritative goal attachment before work:
`/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt`
SHA256 `11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
Read AGENTS.md and docs/TOOL_GRADER_GOAL_AND_PRINCIPLES_2026-10-24_001.md.
After substantial native/documentation examination and after each tool, reread
the original objective and all 16 design principles verbatim, then this contract.
Do not rewrite permanent directions. Literature and W05 are outside this task.

## Ownership and handoff

Implement ONLY these new production files:
- gene_annotation_episode/cmalign_inputs.py
- gene_annotation_episode/cmalign_grader.py
- tests/test_cmalign_graders.py
- tests/fixtures/cmalign_graders/*
All other writes belong under this verification directory. Existing runtime,
other graders, inventories, prompts and global design files are read-only.
Root owns launch/results wiring and receives your pure functions below.
No dependency on the concurrent Infernal search sheet: cmalign is covariance
model alignment, not database identification or a cmsearch hit table.

## Exact operation and input contract

Scope A-L067-cmalign, actual Infernal 1.1.5 Stockholm/Pfam alignment output and
the native --sfile score table, with --ifile/--elfile metadata when needed to
resolve insertion/local-end geometry. Preserve algorithm settings such as
optacc/CYK/sample, banding, truncation, --matchonly, --mapali, seed and local/global.
Do not relabel sampled alignments as deterministic predictions. The parser and
calculator themselves are deterministic for supplied artifacts.

`populate_cmalign_sheet(artifacts: list[dict], *, operation: dict,
sequences: list[dict] | None = None, model: dict | None = None,
inherited_alignment: dict | None = None) -> dict`

Each artifact: `artifact_id: str`, `format: "stockholm"|"cmalign_sfile"|
"cmalign_ifile"|"cmalign_elfile"`, `content: str`, `complete: bool|null`.
Operation: `program:"cmalign"`, `native_version:str|null`, `settings:dict`.
Supplied sequence rows: name, optional accession, actual sequence and/or length,
optional occurrence and explicit origin newly_aligned/inherited/unknown. Model:
name, optional accession, consensus_length, optionally native model header.
Use exact, validated associations; duplicate identifiers without a distinguishing
association are ambiguous. Inherited alignment rows are never silently new work.

## Sheet contract

Finite JSON `schema="cmalign_sheet_v1"` with operation, artifacts, alignments,
sequences, columns, issues and status (available/partial/missing/invalid).
Keep full native alignment strings, RF, SS_cons, per-sequence PP, PP_cons when
present, all annotations and segment/row locators. Join --sfile rows by validated
sequence identity/occurrence, retaining native index, length, cm from/to,
truncation, bit score, avg pp, band/alignment/total seconds and native matrix MB.
Timing is timing information, not annotation evidence.

Keep exact sequence-position-to-alignment-column correspondence, model-position
correspondence where it can be established, inserted positions, missing positions,
deletions and local-end states separately. Native RF '~' has local-end semantics;
do not copy hmmalign's interpretations blindly. If explicit native sidecars are
needed for model coordinates, request/consume them rather than inventing a map.
Preserve native posterior quantization bins and their documented probability
bounds; missing PP is unknown, never zero. Native avg pp is retained separately
from bounds calculated from printed PP bins. Preserve SS_cons pairing and
gapped/missing residue relationships; do not call a gap a pairing mismatch.

## Calculation contract

`calculate_cmalign_scores(sheet: dict, *, parameters: dict | None = None) -> dict`
Output schema cmalign_scores_v1 with operation, explicit parameters, sequence
components, column/pair components, issues, status and numerical definitions.
Parameter `population="all"|"newly_aligned"|"inherited"` defaults all and affects
aggregate populations only; retain every sequence component. Reject unknown knobs.
Components: native bits and avg pp; retained nucleotide counts; model-position
occupancy, deletion, insertion, missing/local-end counts where exact; original
sequence and model denominators; model occupancy and sequence matched coverage
only when mapping supports them; per-sequence PP lower/upper mean from actual
available PP bins with explicit population and unavailable count. Never convert
ordinal PP labels into exact probability or annotation correctness.
Column occupancy keeps numerator/denominator and missing rows separate. Where
SS_cons supplies an unambiguous paired-column map, count actually observed
two-nucleotide pairs and canonical AU/UA/GC/CG/GU/UG pairs; define the denominator
as observed pairs of unambiguous A/C/G/U (T normalized only with declared rule).
Gaps/ambiguous bases/missing symbols are excluded with separate counts. This
describes consistency with the supplied model alignment, not experimentally
proven structure or gene function. No arbitrary overall confidence score.
Each number defines inputs, formula/native source, units, population/denominator,
coordinate convention, uncertainty and missing behavior. Calculators consume
extracted numerical data, not native text; saved recalculation disables parsers,
I/O, subprocess and model calls and preserves the original saved sheet.

## Native verification and deliverables

Read full existing hmmalign_inputs.py/hmmalign_grader.py and BLAST pairwise
sheet/calculator paths as separation examples, and cmalign's full manual and
relevant native source. Reuse utilities only if actual semantics match; do not
alter those files in this workload. Installed executables are under
resources/software/infernal-1.1.5-install/bin/; small models and sequences under
resources/software/infernal-1.1.5/tutorial/. Verify binary/input hashes; copy
any mutable inputs. Run small actual cmalign cases with native score/insert/EL
sidecars, explicit CPU, 20 GiB RAM and 4 GiB scratch, no wall-time cap. All run
files belong under this verification dir. Do not download large models/databases.

Tests must cover real native full and truncated alignments, match-only output,
missing PP, local ends, supplied model/sequence mismatch, multiple sequences,
interleaved records, malformed/truncated Stockholm, absent score sidecar, ambiguous
joins, inherited rows, missing/zero denominators, native quantization bounds and
saved-sheet recalculation. If a format gives only partial geometry, retain exact
available quantities and state the precise missing sidecar/field; do not pretend
that all quantities are available. Add fixtures with native provenance separately
from synthetic adversarial cases. Preserve original source and artifacts.

Deliver filled sheet and numerical examples, implementation file hashes, exact
test/native command receipts, saved recalculation proof, consumer interface notes
and any format limitations. No claim of full production episode integration;
root owns that remaining path.
