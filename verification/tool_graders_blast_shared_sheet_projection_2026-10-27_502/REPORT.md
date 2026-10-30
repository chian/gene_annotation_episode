# BLAST retained shared-sheet projection repair

Implementation and verification evidence for the bounded [501 repair contract](../tool_graders_shared_scoring_trace_2026-10-27_501/REPAIR_CONTRACT.md), under the current user-entered goal attachment `pasted-text-1.txt` (SHA256 `f43e46c2433c44d320d1bbdb4e08f6cb85608a29d50911c2be28eb963581b6dc`). This report does not amend that goal, complete the BLAST family, or add a grader. No goal/status file was edited; GOAL.md was not read.

The NCBI API publisher now calculates the common database sheet once and projects the exact retained HSP component. The bounded reader and requested `execution_blast_hsps` facts validate that binding and copy the retained values. The independent identity/span divisions in `blast_search.hsp_row` were removed. The database probability model and W05 were unchanged.

## Changed functions and responsibilities

| File/functions | Change |
|---|---|
| `blast_grading_inputs.parse_blast_json` | Each normalized hit carries `hsp_source_map`, explicitly recording original zero-based `hit_index`/`hsp_index` for each surviving HSP. Malformed predecessor rows cannot shift the native address. |
| `blast_database_grader._build_database_sheet` | Copies that source map beside the existing `hsp_components`. No database model or grouping formula changed. |
| `blast_pairwise_grader.alignment_components` | Calculates independent validated endpoint spans and `query_span_coverage`/`reference_span_coverage` once, before any missing-traceback return. Existing paired cells retain their meaning. |
| `blast_pairwise_grader.build_pairwise_sheet` | Preserves explicit original `source_address` alongside its HSP rows when the normalization supplies the map. Union logic is unchanged. |
| `blast_search.native_hsp_metadata`, `shared_hsp_component`, `hsp_row` | Separates native metadata validation, original-address selection and projection. `hsp_row` requires a supplied component and contains no identity/coverage calculator or fallback. |
| `ToolRegistry._import_blast` | Retains one common grading, finds its exact artifact reference, selects each original HSP through the map, publishes shared cells and records a closed binding. Missing cells and failed projections retain explicit partial feedback. This worker changed no other `tools.py` method. |
| `tool_grading_artifacts.source_tool_grading_entries`, `source_tool_gradings` | Adds an exact artifact-reference accessor using the existing provider/native-artifact custody validation; the existing grading-only accessor delegates to it. |
| `domain.RECORD_SCHEMAS["observation"]["native_blast"]` | Adds optional closed `shared_projection` fields only. |
| `blast_result_views.retained_hsp_component`, `_original_hsp`, `read_blast_hsp`, `blast_hsp_facts`, `BLAST_HSP_FACT_SCHEMA` | Resolves and validates the bound artifact/component; compares all new published measurements; preserves legacy saved values; returns missing numeric cells as null in the requested fact schema. Reads expose retained reported counts/percentages and conflicts. |
| `alignment_site_native.blast_grading`; `blast_hsp_site_inputs.extract_blast_hsp_columns`, `validate_blast_hsp_column_sheet`; `blast_pairwise_grader.blast_hsp_column_correspondence` | Narrow extension approved by root: host-authenticated retained whole-HSP input is passed into selected-column analysis and retained for saved validation. The separate selected-window calculator is preserved. |

Read-only consumers traced: `NCBIBlastService.publish`, `publish_existing_acquisition`, `_source`, `_grade_supplied_result`, `APIServiceExecution.facts`, `ExecutionEpisodes`' fact declaration/admission, and the NCBI fetch extractor in `execution_progress`. Both direct `hsp_row` consumers now provide the shared component. No changes were made to HMMER/Biopython publication, literature, prompts, execution ownership, or continuation/credit.

## Numerical meanings

| Published/internal cell | Authority and meaning |
|---|---|
| `bitscore`, `alignment_score`, `evalue` | Direct copies of `component.native_scores.bit_score`, `.score`, `.evalue`; native bits, native scoring-system units and expected-hit count, respectively. Missing/invalid values remain unavailable. No correctness probability is inferred. |
| `identity_fraction` | Copy of `fractions.alignment_identity`: identical nongap pairs divided by all alignment columns. Actual readable strings take precedence; the existing common component's reported-count/percentage behavior remains when traceback is unavailable. |
| `paired_identity` | Existing `fractions.paired_identity`: identical nongap pairs divided by paired nongap columns. It is not the public alignment-identity denominator. |
| `query_coverage`, `target_coverage` | Copies of `fractions.query_span_coverage`, `.reference_span_coverage`: validated inclusive native endpoint span divided by the complete corresponding operand length, in original nt/aa coordinate units. `target_coverage` still means native hit/reference coverage. |
| Paired coverage | Existing corresponding-position counts divided by complete operand lengths; these fields are not substituted for the span aliases. |
| Intervals, query start/end | Copy the common `endpoint_spans` zero-based half-open intervals. Native original endpoints, strand, frame and units remain in the observation marker/native artifact. |

Endpoint validation uses the existing shared `_axis_geometry`: bounds, frame, strand and translated JSON conventions remain explicit. Reversed nucleotide traversal retains original coordinates; translated axes use original nucleotide lengths. Each shared span stores its interval, numerator, operand-length denominator, unit, traversal direction and alignment-symbol width. Valid independent endpoints remain available without traceback, or when strings disagree with the native span. Such a string conflict still makes paired geometry unavailable. Invalid endpoints/frame/strand make that axis's span unavailable; a missing operand length leaves its fraction null. No uncertainty estimate is invented.

Native reported counts and percentages remain separate from actual string counts and calculated fractions. They and their conflicts are retained in the exact common sheet and exposed by the reader. Valid scores/string counts survive partial native input even when a scoped observation cannot be projected. No grading failure invokes another scorer.

## Exact binding and historical handling

New observations carry `native_blast.shared_projection`:

```
version = blast_shared_hsp_projection_v1
grading_artifact_ref = exact retained tool-grading artifact
native_artifact_ref = exact source native artifact (exact JSON member for ZIP)
hit_row, hsp_row = compact sheet address
```

The existing native marker retains original report/hit/HSP ordinals. Selection validates those ordinals against `hsp_source_map`; equal scores, accession aliases or compact array order never establish the association. The source's immutable request/transport records the projection version, preventing removal of the binding from a new observation to masquerade as legacy data.

Reader checks cover immutable observation/source/reference records, native artifact digest and contents, provider, selected request/program, query/reference identity and lengths, original RID, native geometry, retained artifact membership/custody, normalized native SHA256/document/request, original HSP source map, exact compact component address and all published measurements. The original archive remains an ancestor source while the exact extracted member is the grading/native binding.

Legacy observations and legacy sources without the new version retain their saved numeric values. Their immutable records, native address/operand geometry and original source/submission custody are still checked. No legacy identity/coverage formula remains active and no historical number or credit is rewritten. Tests cover both a deliberately divergent legacy reported identity of 1 versus current traceback identity .75, and an actual previously saved store from verification 299. Original stored observation/source records remain unchanged.

The selected-column read remains a distinct analysis. Its host first authenticates the whole-HSP artifact through the same reader checks, then supplies `whole_hsp_input` containing the exact component and closed artifact/native-address binding. The pure selected-column parser requires matching source and operand relationships. Its saved-sheet validator re-extracts the selected columns from this retained input, avoiding another whole-HSP calculator invocation. Pure calculators do no artifact I/O; host custody validation precedes their supplied inputs. Legacy/standalone site sheets without this optional input retain their original native-input recalculation path.

## Executed numerical examples

The direct and ZIP cases traverse the actual selected `NCBIBlastService.publish` path, retained source/grading, observation, bounded reader and typed requested-return form. Their numerical evidence is in [check002/mismatch_direct.json](check002/mismatch_direct.json) and [check002/mismatch_zip.json](check002/mismatch_zip.json).

| Example | Shared sheet | Published / reader / requested facts |
|---|---|---|
| `ACGT` versus `AGGT`, reported identity 4, four columns | Actual identical pairs 3; alignment identity .75; native reported identity 4 and `reported_count_traceback_conflict` retained | All identity values .75; bit score 12.5, native score 25, E-value 0 and span coverages 1/1 agree. Instrumented whole-HSP calls: publication 1, read 0. |
| `AC-GT` versus `ACAGT`, lengths 4/5 | Span coverage 1/1; paired coverage 1/.8; paired identity 1; alignment identity .8 | Span aliases remain 1/1; identity .8. |
| Duplicate HSP plus overlapping [0,4) and [2,6) mappings | Union length 6; duplicate mapping group [0,1]; one sequence group/database contribution despite aliases | No HSP sums or alias weights are introduced. |
| Missing traceback, identity count and native score | Native bit score 12.5 remains; valid span coverage 1; paired coverage unknown | HSP survives with partial feedback; missing `alignment_score`/`identity_fraction` are explicit null in facts. |

The shared-loop integration suite also ran a mismatch with reported 8 identities but 6 actual identities in 8 columns. The scientific parent received .75 through its requested `execution_blast_hsps` form; scoped later reads, saved fact validation and closed replay preserved those values without additional acquisition.

## Verification and pins

Both attempts used `native_lifecycle`/`local_jobs`, 20 GiB RAM, 4 GiB scratch, zero swap and no wall-time cap. Source/dependencies/interpreter/stdlib were copied and frozen before launch. Native executable/library closure was resolved and hash-pinned inside the bounded job, then compared after execution. Original handles, terminal outcomes, stdout/stderr, JUnit, source/dependency/stdlib/binary pins, loaded modules and native-library resolution/pins remain in each attempt directory. No timeout triggered cancellation or resubmission.

| Attempt | Actual result | Receipt |
|---|---|---|
| `check001` | 352 passed, 1 failed; 350.94 s. The sole failure was test setup calling `_source` outside its publication context, before the legacy reader was reached. | [receipt](check001/receipt.json), [JUnit](check001/junit.xml), [audit](check001/execution_audit.json) |
| `check002` | 20 passed; 96.46 s. Corrected fixture plus the actual saved legacy store and valid equal-scoring sibling-address forgery case. Production BLAST code was unchanged. | [receipt](check002/receipt.json), [JUnit](check002/junit.xml), [audit](check002/execution_audit.json) |

These counts overlap and are not added as separate coverage. The first attempt includes common pairwise/database/parser/integration suites, BLAST binding/API service/reader/typed-return suites, site tests, retained native coordinate conventions and native standard-database calculators. The second reruns the focused repair module after its fixture correction and added historical/address cases. All nine contract regression categories are covered across these runs. Both audits report no outside Python modules, no unbound native mappings and unchanged native closure; all frozen source/dependency/stdlib/interpreter hashes are unchanged.

Exact finished production hashes are in [finished_production_pins.json](finished_production_pins.json); they match `check002`. [finished_blast_function_pins.json](finished_blast_function_pins.json) shows the BLAST publisher and its existing source/grading helpers also match `check001`. The shared `tools.py` file differs between attempts only in the separately owned `_align_one` method. All other BLAST-owned production files match both attempts.

This worker did **not** capture a separate pre-edit source snapshot or pre-edit hash manifest. The `*_pins_before.json` files are post-edit, pre-execution baselines. They are not reconstructed pre-edit evidence. The 501 read-only review is evidence of the original defect, not a source-byte baseline.

## Limits

This repair verifies saved/synthetic API envelopes, actual publication and requested child-return machinery, deterministic saved recalculation, and previously retained native coordinate examples. It performs no new BLAST run, public API request, database search, native program deployment or HPC execution. The broader R2 authentic-format/configured-resource obligations for standard, iterative, profile and VDB BLAST remain separate and unfinished to their prior evidence levels. No whole-family completion or new algorithm count is claimed. Historical saved site artifacts of every shape, every alternative provider wrapper and all extended BLAST modes were not exhaustively replayed. No unrelated investigation or NMF job was cancelled/restarted.

The current user goal objective and all ten operating principles, and the 501 repair contract, were reread before acceptance.
