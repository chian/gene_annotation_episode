# Infernal search numerical sheet and calculators

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
- gene_annotation_episode/infernal_search_inputs.py
- gene_annotation_episode/infernal_search_grader.py
- tests/test_infernal_search_graders.py
- tests/fixtures/infernal_search_graders/*
All other writes belong under this verification directory. Existing runtime,
other graders, inventories, prompts and global design files are read-only.
Root owns launch/results wiring and receives your pure functions below.
No dependency on the concurrent cmalign implementation: it produces a separate
alignment sheet. Search tables cannot establish aligned-residue correspondence.

## Exact operations and input contract

Scope: A-L067-cmsearch and A-L067-cmscan. Native Infernal target-hit table formats
1 and 3 for both; format 2 for cmscan only. Preserve full native stdout/alignment
artifacts in fixtures; these table functions do not invent alignments from spans.

`populate_infernal_search_sheet(artifacts: list[dict], *, operation: dict,
sequence_metadata: list[dict] | None = None,
model_metadata: list[dict] | None = None) -> dict`

Each artifact has `artifact_id: str`, `format: "infernal_tblout"`,
`table_format: 1|2|3`, `content: str`, and `complete: bool|null`. Operation has
`program: "cmsearch"|"cmscan"`, `native_version: str|null`, and `settings: dict`
with recorded native options; absent settings stay absent. A native footer and
external completeness declaration are independent facts; contradictory program,
version, format or completion declarations must be exposed, not ignored.

Supplied sequence metadata rows have `name`, optional `accession`, `length`,
optional `sequence`, and optional explicit `artifact_id` and `occurrence`.
Model rows have `name`, optional `accession`, `consensus_length`, and optional
`artifact_id` and `occurrence`. Null/omission means unknown, not zero. Validate
length and identity relationships; ambiguous names/duplicate metadata cannot be
resolved by taking the first record. Native lengths and supplied lengths must
agree before denominators can be used. Preserve supplied metadata and join status.

## Sheet contract

Finite JSON object `schema="infernal_search_sheet_v1"` with `operation`,
`artifacts`, `hits`, `issues`, `status` (available/partial/missing/invalid).
Artifact entries retain complete native text, headers, footer/completeness,
all row locators and decode/format issues. Every native row, including `?` rows,
has a stable artifact/line locator; malformed rows remain diagnosable alongside
valid rows. Do not truncate or sort away native order.

Each hit preserves native target/query names/accessions plus explicit physical
sequence and covariance-model roles. cmsearch target is sequence and query is
model; cmscan reverses those roles. Preserve algorithm cm/hmm, model_from/to,
sequence_from/to, strand, truncation, pass, gc_fraction, bias_bits, bitscore,
evalue, inclusion, description, model/sequence lengths with native/supplied
provenance. Coordinates retain native one-based inclusive endpoints and derived
zero-based half-open intervals; sequence reverse strand is not a reversed model.
Format 2 additionally preserves idx, clan, olp, anyidx/anyfrct1/anyfrct2,
winidx/winfrct1/winfrct2 and actual native meaning of -, double quote and -1.
Validate cross-hit overlap references without confusing separate query lists.
Do not convert overlap classifications or inclusion flags into confidence.

## Calculation contract

`calculate_infernal_search_scores(sheet: dict, *, parameters: dict | None = None) -> dict`
Output schema `infernal_search_scores_v1`, operation, explicit parameters,
per-hit numerical components, per-sequence/strand aggregates, issues and status.
Parameters may select aggregate population `hit_scope="reported"|"included"`
(default reported); they do not alter retained native hits. Reject unknown knobs.
Keep native score, E-value, bias and GC directly. Compute model span length
`model_to-model_from+1`, sequence span length `abs(sequence_to-sequence_from)+1`,
model_span_fraction against validated consensus_length and sequence_span_fraction
against validated physical sequence length. These are span fractions, not paired
coverage, identity or probability. Aggregate union physical positions within an
unambiguous sequence/strand population; retain count, union numerator, denominator
and duplicate/overlap memberships. Do not sum scores/E-values or claim independence.
Zero E-values remain native zero; do not invent finite log scores. Preserve known
native statistical limitations and recorded search-space settings.
Each calculated field defines inputs, formula, units, population, denominator,
coordinate convention, uncertainty and missing behavior. Invalid cells do not
erase unrelated valid native measurements. Recalculate using populated numerical
cells only, with acquisition/parser/subprocess/model calls disabled.

## Native verification and deliverables

Read full existing rna_evidence.py, the BLAST pairwise/database sheet/calculator
paths as a separation example, and native Infernal documentation/source as needed.
Installed executables: resources/software/infernal-1.1.5-install/bin/.
Tiny supplied native inputs: resources/software/infernal-1.1.5/tutorial/.
Verify binary/input hashes. Execute small real cmsearch and cmscan cases under
20 GiB RAM / 4 GiB scratch, no wall-time cap. Copy inputs before cmpress or any
operation that writes adjacent files; all run files stay in this verification dir.
Use explicit CPU selection and preserve command, exit, stdout/stderr, native
files and provenance. No reference downloads or large databases are needed.
Test actual formats 1/2/3, role reversal, reverse strand, multiple hits/queries,
no hits, missing denominators, false metadata joins, malformed/truncated rows,
duplicate representations, overlapping intervals, boundary positions, native
inclusion/reporting distinctions and unknown/contradictory declarations.
Native docs have wording/count inconsistencies: real emitted fields plus primary
source determine formats; report discrepancies explicitly. Do not weaken tests
or silently narrow supported formats to make verification pass.

Deliver filled sheet and numerical examples, implementation file hashes,
native command receipts, exact test results, saved-sheet recalculation evidence,
consumer interface notes and remaining integration limitations. No claim of
production episode-path completion: root owns that wiring.
