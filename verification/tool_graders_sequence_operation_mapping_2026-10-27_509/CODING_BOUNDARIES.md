# Proposed subsequent coding boundaries

These are proposals produced by the read-only first-eight mapping. They are not an accepted implementation contract, a replacement goal, or a claim that coding has begun. The authoritative attachment and this assignment's exact scope are recorded in `MAPPING.md`. Each future assignment must reread the attachment's objective and all ten operating principles after scientific tools or substantial inspection, then its actual current contract. Inventory labels do not supply a scientific specification.

The shared numerical owners must settle the exact schema and function contracts below before dependent adapters are coded. Independent parser, calculator and resource-adapter work can then proceed in parallel against those agreed ports; shared implementation need not finish first. One owner should integrate edits to `tools.py`, shared native-worker dispatch, and shared message/return admission, because all these operations may touch those files. This is file ownership for coding, not a new runtime coordinator or episode type.

## Existing authority that must remain shared

| Analysis | Actual functions and data definition | Consumers that must continue to receive the same saved numbers |
|---|---|---|
| Sequence extraction | `sequence_extraction_grader.build_extraction_sheet` / `calculate_extraction_scores`; `sequence_extraction_sheet_v1` | `ToolRegistry._derive`, `_grading_values`, retained `tool_grading_artifacts` |
| Translation | `sequence_translation_grader.build_translation_sheet` / `calculate_translation_scores`; `sequence_translation_sheet_v1` | The same derivation/source/publication path; supplied genetic-code snapshot |
| Pairwise correspondence | `biopython_pairwise_grader.build_biopython_pairwise_sheet` / `calculate_biopython_pairwise_scores`; the single correspondence sheet | `ToolRegistry._align_one`, site-reader admission, retained source/grade and return projections |
| Selected sites | `alignment_site_inputs` / `alignment_site_calculators.calculate_reference_site_components`; `reference_site_comparison_sheet_v1` | `alignment_site_native.reference_grading`, `ToolRegistry._alignment_sites`, `alignment_site_returns.project_reference_site_return` |
| Database BLAST | `blast_grading_inputs.parse_blast_json` → `blast_database_grader.build_database_sheet` → `blast_pairwise_grader.alignment_components` / `calculate_database_probabilities` | `_import_blast`, `blast_search.hsp_row`, `blast_result_views`, `APIServiceExecution.facts` and the declared `execution_blast_hsps` return |
| MSA and tree components | `phylogeny_formats` documents and `phylogeny_calculation_contracts`; `phylogeny_calculators.alignment_components` / `tree_components` | Existing BV-BRC MSA/GeneTree/CodonTree calculators, bundle projectors and saved returns; later local native adapters use these same definitions |
| Actual Prodigal candidates | `prodigal_grader.build_prodigal_sheet` / `calculate_prodigal_scores`; `prodigal_sheet_v1` | Existing `genes.predict` selected local worker → `_derive` path, verified in 505 |

Provider custody envelopes can differ. Their numerical sheet definitions and calculations cannot be copied into new wrapper graders. An existing BV-BRC envelope cannot be populated with invented AppService provenance for a local MUSCLE/IQ-TREE result. A truthful common admission boundary is necessary.

## B1 — BLAST alias and parameter binding

**Operation:** `blast_sequence` only. No new scientific calculator. This can be assigned independently of ORF, scanner, site and phylogeny changes, with the shared host integration owner reserving any `tools.py` edit.

**Owned boundary:** `api_blast.NCBIBlastService` request validation/preparation/publication and `acquisition.PublicClients.blast` parameter preservation, plus the actual alias/tool-information selector once its admission location is traced. Do not revive the upstream XML-first-HSP path. Preserve accepted 502 behavior in `blast_search`, `blast_result_views` and `_import_blast`.

**Concrete input/output:** normalize a supplied sequence into a real scoped operand reference; the selected request carries program, database, hit-list setting and explicitly chosen algorithm settings. The upstream hardcoded settings are `expect=100`, `word_size=7`, `megablast=True`; the existing API signature admits none of those three. Resolve faithful per-program defaults or extend that existing signature and the real native request together. Unsupported combinations produce a typed input failure; do not silently drop settings. Output remains the original submission/RID, complete retained JSON2 artifact and the existing address-linked HSP return. A legacy first-result preview, if requested, is a separate projection of that retained population.

**Consumers:** `NCBIBlastService.prepare/invoke/decode/publish`, `PublicClients.blast`, `publish_existing_acquisition`, `_import_blast`, saved HSP readers and `execution_blast_hsps` admission. Read their full affected paths before changing them. The alias must not own polling cadence, deadlines, retries or substitutions.

**Completion evidence:** parameter round-trip through the actual native request; original query/reference units; complete-hit retention with original addresses; sheet/publication/return equality; empty and malformed-partial results; saved reads do not rescore; one actual child-owned requested-return exercise. Reuse 502 numerical evidence unless a changed boundary warrants a new case. No local database BLAST.

## B2 — Common correspondence and site admission, then two adapters

The source-neutral numerical owner first settles the exact correspondence and site admission contracts for truthful producer semantics, preserving all Biopython cases and the accepted 504 arithmetic. Independent adapters can then be coded against those ports while shared implementation proceeds. This owner controls `biopython_pairwise_grader.py`, the relevant branches in `alignment_site_inputs.py`, `alignment_site_calculators.py` only if its declared meaning needs extension, and the explicit saved-sheet validator. Merely passing a fake `mode='local'`, matrix or native score is not a valid adapter.

The required output is one common correspondence sheet with source/algorithm parameters, supplied traceback, oriented geometry, original-coordinate mapping, literal/case policy and unavailable native scores. The same existing calculator produces counts and fractions. Do not create a scan-specific identity/coverage calculator. The site sheet adds an explicit supplied-alignment mode and input provenance, while retaining the same requested-position population and denominators.

### B2a — `align_sequences` sliding-window adapter

**Proposed pure adapter signature:** `extract_scan_placement(native: dict, *, query_occurrence: int, placement_ordinal: int, operands: dict, source: dict) -> dict`. The result is the existing common correspondence sheet extended by B2, not a new scan scoring schema. The native enumeration can remain a small selected tool primitive; it is not an episode.

**Native envelope:** full target string/identity/length; ordered query occurrences with full original strings/identities/lengths; actual uppercase and A/T/C/G-only complement policy; threshold one literal mismatch; every placement's zero-based target start, strand, oriented query string and reported mismatch tuples. Preserve occurrence and placement ordinals, including duplicates and both representations of palindromes. No optimum score, significance, or Biopython version is invented. A source/native digest identifies the actually executed scanner implementation.

**Geometry:** each placement spans the whole oriented short string and the matching fixed target window. Minus orientation maps short offset `j` to original `length-1-j`; target positions remain original zero-based coordinates. Per-placement identity denominator is the actual compared columns. Any aggregate locus coverage uses an interval union and distinguishes target loci from orientation representations and query occurrences. The original upstream behavior on empty/ambiguous symbols must be explicitly supported or rejected by the invocation contract; no silent reinterpretation.

**Consumers:** selected native-operation dispatch (`sequence_ops`, `sequence_worker`, `_prepare_sequence_work_async` and `_sequence_worker_async`, or the equivalent existing selected primitive boundary) → retained scan source → B2 sheet → host publication of requested placement records. The host owner owns source admission, typed return validation and selected-site source support if requested. No call to `sequence.align` may substitute for the scan.

**Checks:** exact/mismatch/no-placement; forward/reverse coordinates; palindrome target/query ACGT gives two placements but four-base locus union; repeated query occurrences; query longer than target; declared empty/ambiguity handling; saved recalculation and source-vs-calculated mismatch conflict; equality of published and returned shared components.

### B2b — `find_sequence_mutations` supplied-alignment reader

**Proposed pure adapter signature:** `extract_supplied_alignment_reference_sites(native: dict, *, molecule: str, selection: dict, operands: dict, source: dict, original_mappings: dict) -> dict`. Output is `reference_site_comparison_sheet_v1` with B2's explicit supplied mode. `alignment_site_native.reference_grading` needs a truthful source branch; it currently admits only Biopython, native phmmer and minimap2.

**Native envelope:** both full gapped strings and operand identities; declared molecule; explicit query/reference coordinate starts and units, if known; literal case comparison and gap exclusion policy; supplied `query_start` and historical reported token list when importing old output; equal-length/completeness state. Strings are supplied evidence, not a new aligner result. If only alignment-column offset is known, ungapped original coordinates remain unavailable.

**Output:** typed compared-column records with alignment column, query nongap offset, reference nongap offset and proven original coordinates kept separately; native token string preserved separately. The requested site population, pair count, mismatch count and ratios come from the shared site calculator. Gap columns are excluded from this wrapper's substitution comparison, not asserted absent. Unequal suffixes are truncated/unexamined, not a completed no-variant result. Case-sensitive source semantics must survive unless normalization was explicitly selected.

**Consumers:** `alignment_site_inputs` mode validator → `calculate_reference_site_components` → `alignment_site_native.reference_grading` → `_alignment_sites` → `project_reference_site_return`. Source descriptor/operand validations and return fields must admit the real supplied-string source. A token-format projection may be added without recalculating scientific counts.

**Checks:** `ACGT` / `AGGT` gives `G2C`; `A-CG` / `ATGG` at start 10 yields historical `G12C` but query nongap offset one; explicit gap-only and unequal-length states; lower/uppercase difference; empty strings; invalid zero/negative start policy; partial rows retained; saved-only and actual requested child-return equality. No variant caller/native aligner or additional scientific confidence score.

## B3 — ORF candidate provenance and derivation reuse

**Operation:** `annotate_open_reading_frames`. The scanner's ATG-to-first-stop enumeration is a distinct candidate-generating algorithm, not Prodigal. Its extraction, translation and overlapping interval measurements reuse the existing definitions.

**Proposed pure adapter signature:** `extract_orf_candidates(native: dict, *, input_sequence: str, subject_ref: str, parent_mapping: dict) -> dict`. The output is a retained candidate envelope whose transformation sheets are the existing extraction/translation sheets. Preserve candidate ordinals, actual native tuples, unfiltered/filtered membership, requested parameters, native summary and exact source mapping. If the selected operation does not retain the pre-filter population, mark it unavailable rather than reconstructing it from filtered output.

**Input semantics:** input sequence/identity/length; minimum nt length including stop codon; searched strands; source implementation/version; stop/start policy; code-1 translation table snapshot and actual Biopython version; each candidate's oriented nt/aa symbols, original zero-based half-open interval, strand and searched frame. Enumeration and filter are actual native work, not fake `sequence.view`, `sequence.translate` or Prodigal receipts. The translation parser must faithfully admit `to_stop=True` and omitted terminal stop semantics or the episode must select the existing corresponding transformation explicitly.

**Shared-owned fields:** the extraction/translation owner controls any native-parser admission change in `sequence_extraction_grader.py` / `sequence_translation_grader.py`. Add candidate population counts, strand counts, length sum/mean and distinct interval coverage to the existing reusable candidate/interval definition where applicable, without duplicating Prodigal's arithmetic or requiring its model scores. The denominator is the post-filter candidate population; overlaps count separately in the mean and only once in interval-union coverage. Empty mean is unavailable even when the native rounded report says zero. No confidence score.

**Consumers:** selected scanner primitive → raw source retention → shared transformation sheets → `_derive`-equivalent feature/product publication → requested typed candidate/sequence/component refs. The host owner must preserve parent offsets exactly once. Actual Prodigal `genes.predict` and 505 evidence remain unchanged and separately identified.

**Checks:** ATGATGTAA with minimum 6 yields `[0,9)` and `[3,9)`, mean 7.5 nt; containment filter leaves one. Include reverse original mapping, overlapping frames, exact minimum, missing terminal stop, invalid symbol/translation failure, completed empty result, code snapshot replay, no double offset, and sheet→feature/product→requested child-return equality.

## B4 — Common native MSA/tree admission and numerical meanings

**Operations consuming this output:** `analyze_protein_conservation` and `analyze_protein_phylogeny`. This shared owner must settle the exact common schema/function contract before native adapters are assigned. Their implementations can proceed in parallel against that contract; they do not wait for the shared implementation to finish. Existing BV-BRC analyses already use the numerical components; do not restart them.

**Owned shared files:** `phylogeny_calculation_contracts.py`, `phylogeny_calculators.py`, and the common alignment/tree sheet admission used by existing MSA/tree extractors. A shared owner also allocates any necessary existing BV-BRC extractor/validator changes; a local parser must not weaken BV-BRC custody validation. Existing generic component interfaces are:

```python
alignment_components(alignment, *, population, alphabet, case_policy, pairs=())
tree_components(tree, *, leaf_population, support_observations,
                native_measurements, branch_unit, pairs)
```

The alignment population remains `{population_id, alignment_id, row_indices, columns_0based, completeness, evidence}`. The alignment/tree documents, evidence references and node/row identities already have common definitions. Use those exact numerical inputs and outputs through one shared sheet admission; provider-specific run/custody envelopes may wrap them. Do not fork the calculators or create `protein_conservation` and `protein_phylogeny` scoring sheets that duplicate the same fields.

**Specific shared additions:**

- Literal all-row maximum-symbol fraction and tied-consensus policy. For an actual equal-length MSA, denominator is selected actual rows; gaps, ambiguities and case remain literal under the selected policy. Source tie rule is first encountered in retained row order. Keep canonical-only majority and native rounded conservation observations separate. An all-gap column's literal fraction one does not imply biological conservation.
- Literal full-column identity distance, used by actual `DistanceCalculator('identity')`: `1 - equal_literal_columns/alignment_length`, with default skipped-letter set empty. Gap-gap contributes equality. Preserve native distance observations and conflicts separately from shared derived values. Empty/nonrectangular alignments must be invalid or explicitly unavailable under this contract; do not turn padding into input evidence. If preserving the upstream helper's empty-length return one, identify it as a native edge behavior, not the ordinary defined ratio.
- Known identity-distance branch unit for actual NJ, distinct from expected substitutions per model site. Tree code already permits signed lengths; do not clamp negatives. Add exact support-method admission for evidenced IQ-TREE ultrafast bootstrap, with its actual native scale. Missing method or completed-replicate counts stay unavailable. A requested `-bb 1000` is not a measured replicate population.

**Frozen output needed by dependent parsers:** accepted native source/method discriminators; exact common sheet placement for literal components, native distance matrix and support metadata; original-row↔alignment-row↔tree-tip association table; partial/failure envelope; requested-return projection fields. This is a precise schema dependency, not a whole-family blocker. Existing `bvbrc_msa_inputs.extract_msa_sheet` requires `source_dialect='retained_bvbrc_msa'`, `tool='C-L204-MSA'` and observed AppService versions; `extract_common_fields` permits only `gene_tree`/`codon_tree`. A local run cannot be pushed through either unchanged.

### B4a — Native MSA / conservation / explicit NJ artifact reader

**Owned parsers:** a native run-envelope reader, `phylogeny_formats.parse_aligned_fasta` reuse, and an actual retained identity-distance-matrix reader. Any CLUSTAL reader is owned once in `phylogeny_formats.py` and shared with B4b. Proposed entrypoint: `read_native_alignment_bundle(*, input_artifacts: tuple, output_artifacts: tuple, run: dict, associations: dict) -> dict`; outputs are the existing document/read-outcome types plus B4's explicit run/measurement associations.

**Native inputs:** exact input FASTA bytes and stable occurrence IDs; actual selected MUSCLE or ClustalW invocation/version; successful native aligned bytes with real dialect; logs/exit state; native rounded conservation table if present; full native distance matrix with original row/column order, chosen metric and version; real NJ Newick linked to that matrix. Source wrappers' raw-string/list inputs become retained FASTA with explicit generated-ID joins. Equal lengths alone do not prove a true MSA.

**Required exclusions:** upstream right-padding and independently aligned second-row pseudo-MSA are specific failures, not parseable scientific alternatives. An explicitly selected conservation job can declare MUSCLE alignment plus identity-distance NJ and column conservation as its composite computation. Those deterministic steps do not require separate episode/action selections. An IQ-TREE failure cannot silently substitute NJ unless a later episode-owned selection authorizes that different computation. Preserve genuine partial output artifacts on failure.

**Consumers:** B4 common sheet/calculators, actual local/HPC selected job boundary appropriate to the configured resource, retained source publication and requested MSA/column/matrix/tree facts. A selected composite tool can execute its declared deterministic steps. It cannot secretly change alignment strategy, retry policy or tree method after failure. This contract does not prescribe separate actions, extra decisions or a child itinerary for those steps.

**Checks:** A,A,-,- yields literal .5 and canonical 1; all-gap literal1/canonical unavailable; tie order; ambiguity/case; exact vs rounded file values; unequal rows; duplicate IDs and stable joins; full matrix symmetry/diagonal/native conflict; actual tree→matrix association; signed NJ branches; saved-only recalculation and requested-return equality.

### B4b — IQ-TREE native reader and selected tree binding

**Owned parser:** actual IQ-TREE output/log/run metadata → existing Newick document plus B4's support/model records. Proposed entrypoint: `read_iqtree_bundle(*, alignment_artifact: dict, tree_artifact: dict, run_artifacts: tuple, run: dict, associations: dict) -> dict`. It performs no execution or scoring.

**Native inputs:** selected real MSA/dialect, complete tree bytes, executable/version, actual model/log evidence, command/requested settings and observed support output. Preserve tip identity joins, raw support labels, branch units and actual completed replicate evidence when available. A plot or file path is not an acquired tree. Do not infer observed model/support solely from an attempted command.

**Consumers:** B4 common tree sheet/calculator and the same retained/requested-return chain as B4a. Native execution is selected through the existing resource child and runner. A declared alignment-plus-IQ-TREE composite may execute both steps without another episode decision; hidden failure-triggered ClustalW→MUSCLE→pairwise or IQ-TREE→NJ transitions are prohibited substitutions. `fasttree` is currently unsupported by the upstream source despite its default; a truthful invocation contract must reject it or bind an actually implemented selected operation after a separate concrete scope decision. No placeholder tree is ever accepted as native science.

**Checks:** real IQ-TREE format/version example; precise support method/percent; absent and ambiguous support; requested vs observed replicates; malformed tree with preserved valid artifacts; duplicate/missing tip joins; pre-aligned input validation; actual child return copied from retained common sheet. Do not rerun unchanged BV-BRC native jobs to establish this new format.

## B5 — pLannotate and Prokka native-bundle contracts before parser allocation

These two independent discovery/binding tasks can start once a concrete source/native inspection need is reported. This packet has not run either tool or inspected an installed implementation beyond the wrapper. Resource availability is unknown, not proven absent. The immediate output is an authentic native-bundle/dialect contract, not an invented scoring implementation.

### B5a — `annotate_plasmid`

**Required specific output:** selected pLannotate version/source; actual CSV bytes and schema/dtypes; declared native engine(s) and available full search artifacts; DB/config identities; submitted input bytes, original length and topology; q/s coordinate bases and circular duplicated-coordinate rules; exact meanings/units of score, pident, percmatch, abs percmatch, pi_permatch, priority, wiggle, fragment and feature identity fields. Capture the real temporary outputs before cleanup. Parser allocation for each matching artifact depends on that artifact's dialect proof, not completion of every pLannotate feature.

**Proposed custody reader:** `read_plannotate_bundle(*, input_artifact: dict, artifacts: tuple, run: dict, database_manifest: dict | None) -> dict`, returning complete native rows with original ordinals, raw scalar tokens, source associations, native feature intervals and independent requirements. This is an acquisition/parser envelope, not a new confidence sheet. Exact normalized numerical field mapping is frozen only after native/source evidence resolves the above unknowns.

**Consumers:** actual engine parser → existing shared correspondence/database sheet where supported; existing extraction/interval definitions for proven feature geometry; native pLannotate priorities and fragment decisions retained separately; requested feature and source-evidence projections. If only rounded percent identity exists, identity count is unavailable. Missing subject traceback remains missing. Circular original sequence length is the coverage denominator, with origin-crossing geometry split into proven original segments.

**Resource ownership/checks:** selected pLannotate CLI/resource, preserved native bundle and errors; authentic circular and linear CSV cases, negative strand/origin crossing, empty result, missing DB release, full native row retention and partial cleanup failure; shared calculated/published/returned equality where inputs support calculation. No engine or score meaning may be guessed from familiar CSV headers.

### B5b — `annotate_bacterial_genome`

**Required specific output:** selected Prokka version/configuration and actual output bundle (GFF3, GenBank, FAA, FFN, TXT, stdout/stderr, additional underlying search/candidate outputs only when actually produced). Freeze stable contig/feature/locus-tag/Parent/protein/gene joins; coordinate basis, strand, phase, translation table and partial-feature semantics; native provenance for every claimed component algorithm.

**Proposed custody reader:** `read_prokka_bundle(*, input_artifact: dict, artifacts: tuple, run: dict) -> dict`, returning complete feature/sequence records, association rows, native component artifact references, diagnostics and requirements. A native log count/file size remains a run fact. Caller genus/species/strain labels are not measured identifications.

**Consumers:** actual Prodigal records → existing Prodigal sheet only if evidenced; authentic retained BLAST/HMMER/other component artifacts → existing appropriate readers/calculators; feature extraction/translation → existing transformation sheets. Full annotation feature relations and functional source assertions remain typed evidence; do not create an aggregate all-purpose confidence formula. GFF CDS alone cannot supply missing native score, confidence, tool version or a complete candidate population. Reuse existing GenBank parsing only after reading its full `acquisition.parse_genbank` implementation against the required native joins; this task did not establish that it satisfies Prokka association requirements.

**Resource ownership/checks:** explicit Prokka selected job, real full bundle, no silent Prodigal substitution; several contigs, negative CDS/phase/code, duplicate/missing locus tags, non-CDS features, native partial outputs, source component links, extraction/translation consistency and requested typed feature return. Existing 505 is evidence for actual Prodigal single-mode publication only. It is not Prokka verification.

## Shared host/return integration and completion boundary

Each coding task must identify its exact source provider, immutable input records, native artifact roles, selected action, parser result, retained sheet/components and requested return form before publishing. Bind through existing episode/resource mechanisms and shared `method_loop`. The host integration owner reads affected consumers and message contracts in full, including `docs/TASK_AND_STEERING.md`, `docs/EPISODE_STRUCTURE.md` and `docs/TIME_AWARE_ESTIMATION.md` when that work changes behavior. No prompt was edited or approved by this mapping.

Successful evidence must distinguish tool information, invocation, sheet, parser/metadata, calculator, result binding, numerical checks, episode checks and actual live resource. Preserve unavailable provenance, completed empty results, malformed/partial data and failed execution separately. Saved-only recalculation must consume retained data without native rerun; return construction must project saved numbers without a second scientific scorer. One selected completed action produces one observation; parser and report steps do not add progress. Parent-defined returns stay typed, and controller/launch ownership stays unchanged.

Root retains progress and fixed-row accounting. This packet's proposed assignments neither mark wrappers complete nor count them as new algorithms.
