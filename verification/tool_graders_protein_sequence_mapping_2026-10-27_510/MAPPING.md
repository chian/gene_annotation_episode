# Four protein sequence operations: implementation mapping

2026-10-27. Read-only source/contract review; this packet is implementation
evidence, not a goal or scope amendment. Only this packet was written. No
scientific imports, native execution, service calls, tests, environment changes,
production edits or progress-row changes were performed.

The supplied attachment was read in full and its objective and all ten operating
principles reread during source inspection. Its SHA256 is
`f43e46c2433c44d320d1bbdb4e08f6cb85608a29d50911c2be28eb963581b6dc`.
`GOAL.md` was not read. The four existing WORK_STATUS rows were read as evidence;
their pending labels were not used to infer missing algorithms.

## Actual operation mapping: one row per operation

In this table, `B/` means
`reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/`.
Each listed implementation and its complete descriptor were read. The Gentner
catalog in `reference/episode_tools/src/gentner_ave/tools/biomni_catalog.py`
only returns registered descriptions/schemas; it supplies no additional analysis.

| Operation | Actual computation and native dependency; scientific question | Existing aliases/reuse and numerical owner | Native retention, association, resource contract actually present | Exact missing behavior |
| --- | --- | --- | --- | --- |
| `predict_protein_disorder_regions` | `B/biophysics.py:1–121`; descriptor `B/tool_description/biophysics.py:2–29`. `requests.post` sends the alphabetic characters extracted by `[A-Za-z]`, preserving case, to `https://iupred2a.elte.hu/iupred2a`, with `iupred2=long`, `anchor2=no`. Parses whitespace columns position/residue/score; ignores comments, blank lines and non-parsable rows. Classifies `score >= threshold` (default .5), counts classified rows, and reports consecutive runs of at least TWO residues. This is remote IUPred2A residue disorder prediction, not locally implemented IUPred and not a function probability. | No matching production operation, IUPred parser, sheet or calculator was found in `gene_annotation_episode`. Existing sequence composition can supply length/symbol validation; it cannot supply disorder scores. A distinct disorder sheet/calculator is required. No structural-confidence or HMMER posterior sheet is equivalent. | Writes a derived CSV with `Position,Amino_Acid,Disorder_Score,Is_Disordered`; returns a text log. Positions are parsed as supplied (intended one-based residues). Raw response, submitted sequence, preprocessing map, model/version, rejected rows and service receipt are not retained. No sequence/residue validation or duplicate/order check. `len(scores)` is called sequence length in the log. Requests have no explicit timeout; no resource episode, bounded capture, or durable result binding is provided by this wrapper. | Add an actual selected API acquisition/capture contract, faithful per-residue text parser, supplied CSV parser with explicit missing provenance, exact original/submitted sequence association, disorder sheet and pure threshold/run calculation, full artifact retention, requested typed result/publication/admission. Verify the actual current service/format later; source availability does not establish service availability. Do not invent a replacement prediction algorithm. |
| `identify_fas_functional_domains` | `B/synthetic_biology.py:1152–end`; descriptor `B/tool_description/synthetic_biology.py:246–272`. Optional `Bio.Seq.Seq(sequence).translate()` then legacy HMMER/Pfam `hmmscan` POST, fixed 2-second sleep, one GET of `Location + '.json'`. Flattens all returned domains and applies nine case-insensitive NAME-SUBSTRING rules. Question: which retained profile matches have names matching this FAS lookup? A matched name/function text is not experimentally established FAS function. | **Reuse `hmmer_search_sheet_v1` and `calculate_hmmer_search_scores` exactly.** API: `api.hmmer.prepare/submit/status/check_handoff/result`, selected `algorithm=hmmscan,database=pfam`. Configured native alternative: `native.hmmscan`, then `execution.results.collect`. These are existing analyses, but the FAS alias is absent. Nucleotide input reuses `sequence.translate`, `sequence_translation_sheet_v1`, `calculate_translation_scores`, `translation_mapping`/`map_interval`. No FAS domain grader is needed. | Upstream keeps only a text report/log: display name after `.split('.')[0]`, description, `ali_from`, `ali_to`, `score`; it defaults missing coordinates/score to zero and drops accessions, E-values, native flags, arrays and ancestry. `pfam_id` is actually the altered hit NAME. Current API path retains complete original selected pages and shared grading; native contract retains stdout/tblout/domtblout/stderr, exact supplied FASTA/profile/pressed companions, selected options, software identity and operand bindings. Native execution is accepted only for configured local resources by `ExecutionEpisodes`; its generic information builder alone does not establish HPC deployment. | Bind the alias to the selected existing actual hmmscan path; **no legacy-wrapper re-execution is scientifically necessary**. Preserve all native hit/domain identities and requested protein or translated-product ancestry. Add a non-scoring FAS label/selection projection and authenticated requested returns. API currently publishes shared measurements but exposes only result references/completion in its facts; it does not populate native HMMER's requested domain-row fact source. Legacy flat domain JSON needs a separately verified format parser if retained historical inputs must be accepted; current parser accepting `results` is not enough to recognize its `score/ali_from/ali_to` fields. |
| `find_n_glycosylation_motifs` | `B/glycoengineering.py:9–46`; descriptor same relative `tool_description/glycoengineering.py:2–22`. Dependency-free scan over `(sequence or '').upper()`. Match exactly N, next symbol not P, then S/T. With default `allow_overlap=False`, advance three symbols after a match; otherwise advance one. Question: where does this literal sequon rule match, under the selected overlap policy? Occurrence is not demonstrated glycosylation. | No matching production motif scanner/sheet/calculator was found. `sequence.inspect` and `sequence_composition_sheet_v1` supply shared length and counts, not order-sensitive motifs. A distinct sequon sheet/calculator is genuinely missing. Reuse composition and source-coordinate mapping; do not duplicate them or treat the motif count as annotation confidence. | Only text is returned: complete aggregate count plus first 100 positions/motifs, then omitted-row count. Positions are one-based offsets in the uppercased supplied string; no whitespace removal, amino-acid validation, sequence identity or native full table artifact. The source loop computes the full population in memory but discards rows after 100 at the return boundary. No API/binary dependency or configured episode binding. | Install the exact source-derived scan as a selected primitive with a complete retained operand/result table and one numerical authority. The 100-row cap is a missing artifact/full-population return behavior, **not a formula change**. Provide typed selection/paging with full count and completeness, exact motif/sequence joins, validation/partial outcomes, saved recalculation and actual child-owned publication/return. |
| `predict_o_glycosylation_hotspots` | `B/glycoengineering.py:49–112`; descriptor `B/tool_description/glycoengineering.py:24–46`. Dependency-free **heuristic**, not NetOGlyc. For each S/T in uppercased sequence, use a centered clipped window; S/T count divided by actual clipped length; exclude S/T immediately followed by P when requested; retain sites with unrounded fraction >= threshold (default .4). Default window 7; even or <3 silently becomes 7. Returned fraction is rounded to 3 decimals after selection. Question: which S/T residues satisfy this density/proline rule? | No equivalent production window/selection analysis was found. Reuse `build_sequence_composition_sheet`/`calculate_sequence_composition_scores` for each explicitly associated window's length and S/T symbol counts; a distinct S/T-density calculation/selection contract is missing. It is different from N-sequon occurrence and from remote disorder prediction. | Returns only text: aggregate candidate count and first 100 candidate positions, residue, rounded density and one-based inclusive window range. No full candidate/noncandidate table, unrounded density, input sequence custody, original requested-versus-effective window, or source mapping. No native binary/API. The link to NetOGlyc is advice in a log, not an invocation/binding. | Retain all per-S/T window operands, including excluded and below-threshold rows, exact counts/denominators and unrounded calculated values; preserve effective versus requested settings. Single shared calculator owns density and candidate decisions; projections only copy. Add complete typed artifact/result path. Keep heuristic identity explicit. Do not invent NetOGlyc results or alter the rule to create a stronger predictor. |

## Numerical/data contracts to freeze before coding

All three proposed new sheets retain the exact supplied subject sequence,
source artifact, subject identity, declared protein molecule, selected parameters,
native/operand row locators, coordinate map and issues. New wrappers/providers
performing the same analysis must feed these exact sheets/calculators. All
calculators are pure and use only saved operands and explicit parameters.
Unknown, failed, partial, incompatible and complete-zero remain distinct.
Uncertainty is absent unless the native source actually supplies it; none of
these quantities is gene-function correctness or experimentally measured
modification occupancy.

| Analysis | Fields, units, populations and missingness |
| --- | --- |
| Disorder (proposed `protein_disorder_sheet_v1`) | Retain each original row's position, residue, literal score and validity; positions bind to submitted sequence and a declared map back to original input. `native_disorder_score`: dimensionless provider score, not a calibrated correctness probability; raw parser does not validate a range. `threshold`: same units, explicit `>=`. `scored_residue_count`: uniquely validated available residue positions; requested length remains separate. `disordered_residue_count`: count among that available population meeting threshold; `disordered_fraction_available = count/scored_residue_count`, null if denominator zero; `disordered_percent_available = 100*fraction`. `region_start/end`: native one-based inclusive and normalized half-open AA intervals; `region_length_aa=end-start` normalized; `region_count`: consecutive classified runs of >=2, matching upstream semantics. Singletons contribute to residue count but not region count. Missing rows do not bridge a run or become ordered residues. A log/CSV count of parsed rows is retained as such, not silently relabeled as full sequence length. Incompatible residues, duplicate positions, unsorted positions, nonfinite scores and partial capture need explicit diagnostics before population calculations. No missing score becomes zero. |
| FAS (existing HMMER sheet) | Preserve exact `record_key`, artifact locator, original hit/domain indices, query/product subject, target name/accession/version, profile/model identity and database release. Reuse all `HMMER_DOMAIN_METRICS` under the definitions already in `hmmer_search_grader._definitions`: model/sequence lengths (positions/AA); model, sequence and envelope spans; their separate full-length coverage fractions; paired/insert/delete/all-column counts; paired coverage; consensus/whole-alignment/API identity with their different denominators; native score/bias bits; conditional/independent E-values with original search population; native accuracy and PP interval means. API bias nats converts through the existing calculator only. Zero E-value remains the native printed value. `sequence_identity_fraction` stays unavailable for a profile consensus. Missing alignments/lengths leave dependent components null with reasons; native independent measurements survive. FAS label rows add exact rule identity, matched native name, family name and source lookup text; these are metadata, not new numerical scores. Nucleotide ancestry retains translation code/strand/frame, complete-codon interval, trailing bases, stop semantics, product mapping and original intervals. |
| N sequons (proposed `protein_sequon_sheet_v1`) | Retain all three-symbol operands with original one-based start and zero-based `[start,start+3)` AA interval, exact motif symbols, input identity and overlap policy. `sequence_length`: shared composition length, supplied symbols (AA only after validated protein input). `motif_count`: number selected by the exact predicate/greedy overlap rule; units occurrences, population the full supplied sequence under that policy, not modified Asn residues. `reported_total_count` and `returned_row_count` describe legacy log custody separately. Complete valid no-match input yields 0; missing/truncated log rows do not yield absent motifs. Empty/length<3 valid supplied sequence has 0 motifs; absent input is not silently converted to empty in the new typed contract. Upstream accepts any middle symbol except P (including invalid '-' or '*'); preserve/report that defect rather than claim validated canonical protein behavior from the log. |
| O heuristic (proposed `protein_st_density_sheet_v1`) | Retain requested/effective window, threshold, proline flag and every S/T center; per row retain residue and source interval, clipped window interval and shared composition sheet. `window_length`: actual clipped supplied-symbol count. `st_count = shared_counts[S]+shared_counts[T]`; units symbols in this window. `st_fraction = st_count/window_length`; dimensionless fraction of that exact window, null when operands/denominator unavailable. `native_display_st_fraction`: upstream rounded 3-decimal display, kept separate. `eligible`: S/T center and not immediately-following-P exclusion; `candidate`: eligible AND unrounded fraction >= threshold. `candidate_count`: count over complete S/T-center population; zero only for complete valid no-candidate results. Missing windows/invalid symbols retain affected-row uncertainty, not assumed amino acids. No percentage of actual modified sites is calculated. Parameter validation must expose upstream fallback and out-of-range/nonfinite inputs explicitly, never silently change saved requested parameters. |

N/O inputs are already sequence strings upstream. FASTA, selected file segments
or snippets need the existing intake/selection association before these analyses;
a FASTA header is not amino-acid content. IUPred's `[A-Za-z]` cleanup can even
incorporate letters from a FASTA header. Any compatibility adapter retaining
that cleanup must preserve the original-to-submitted index map and diagnose it.

## Actual consumers and reuse boundaries

* API HMMER: `HMMERAPIExecution.execute` owns one selected result-page action;
  it calls `ToolRegistry.publish_hmmer_result` -> `_hmmer_grading` ->
  `grade_hmmer_api_result` -> `parse_hmmer_api_result` ->
  `build_hmmer_search_sheet` -> `calculate_hmmer_search_scores`.
  `retain_tool_grading` binds the complete sheet/scores to the source's original
  native artifact. `_publish_hmmer_domain` joins original array indices with
  `api_domain_scores`, projects `HMMER_DOMAIN_METRICS`, and copies coverage
  aliases from those calculated fields. Do not reintroduce arithmetic here.
* `acquisition.parse_hmmer` and `_publish_hmmer_rows` presently require the
  current SUCCESS/`result`/`alignment_display` publication contract. The numerical
  parser accepts a `results` envelope but still reads current domain
  `bitscore`, `ienv/jenv`, and `alignment_display.hmmfrom/hmmto/sqfrom/sqto`.
  Legacy FAS `domain.score/ali_from/ali_to` are not equivalents merely because
  the JSON envelope is accepted. Original fields must not be renamed without
  authentic format/unit evidence.
* API `facts`, `read_result` and `validate_report` authenticate original own
  acquisition and return `execution_result_refs` and completion. They do not
  construct requested HMMER domain rows. `APIServiceExecution.facts` delegates
  legacy HMMER facts, and `ExecutionEpisodes.facts` leaves its native HMMER row
  sources empty for that API branch. This is a specific numerical-return gap,
  despite retained numeric observations being available through canonical state.
* Native HMMER already routes `native.hmmscan` through launch/local, selected
  `practical.job.start`, original bundle capture and
  `NativeHMMERResults.execute`. `native_hmmer_result_worker.run` calls
  `grade_hmmer_native_artifacts`, then `projected_measurements` from
  `hmmer_native_result_views`. `publish_selected_native_hmmer_rows` publishes
  those values; `NativeHMMERResults.facts` returns only requested
  `execution_hmmer_domain_rows`. Its closed selector carries family, row
  keys/offset-limit and explicit metric names. These are reusable mechanisms,
  not proof of FAS alias, all formats, or current live deployment.
* Translation: `sequence_ops.translate` -> `ToolRegistry._derive` ->
  `grade_translation` retains the genetic-code snapshot and numerical sheet,
  publishes a product with `translation_mapping`, and exposes mapped typed
  observations. `sequence_mapping.map_interval` carries a selected AA interval
  to the original ordered nucleotide segments, including orientation. Reuse
  this product instead of translating inside a domain-result parser.
* The three missing analyses have no existing production parser/publication or
  typed-return consumer. Shared infrastructure available for their integration
  is `retain_tool_grading`, canonical source/observation publication, selected
  result facts, and `EpisodeReturnRecords` authentication of immediate-child
  forms against original contracts/frozen facts. These utilities perform no
  new scientific calculation. They do not themselves make an alias installed.

## Proposed subsequent ownership and signatures (not implemented)

Each pure owner receives only its exact analysis and new files below. Root owns
shared dispatch/tool information, API/local execution selection, publication,
fact-source registration, receiver admission and communication changes. No
worker should edit the existing HMMER, composition or translation calculators.

| Owner | Proposed files and signatures | Specific input/output handoff |
| --- | --- | --- |
| Disorder parser/calculator | `protein_disorder_formats.py`: `parse_iupred_text(text, *, artifact_ref)`, `parse_disorder_csv(text, *, artifact_ref)`; `protein_disorder_grader.py`: `build_protein_disorder_sheet(native, *, sequence, subject_ref, sequence_mapping, submission)`, `calculate_protein_disorder_scores(sheet, *, threshold)` | Parser returns retained native rows/locators/issues, never performs HTTP. `submission` supplies posted sequence, preprocessing map, long mode, anchor2 flag, endpoint/response identity, model version when known. CSV import cannot infer missing request/provenance. Calculator retains the upstream fixed minimum region length of 2 and returns `{schema, rows, regions, summary, definitions, issues}`. Root wraps `{sheet,scores}` in original source custody. |
| N sequon analysis | `protein_sequon_grader.py`: `build_protein_sequon_sheet(sequence, *, subject_ref, sequence_mapping)`, `calculate_protein_sequon_scores(sheet, *, allow_overlap)` | Builder retains the source sequence, shared composition sheet and complete indexed triplet operands; calculator is the sole predicate/overlap/count implementation. Operation stores complete structured data rather than calling the legacy truncated logger and recovering answers from prose. Compatibility log imports, if required, retain their partial-return qualification. |
| O density analysis | `protein_st_density_grader.py`: `build_protein_st_density_sheet(sequence, *, subject_ref, sequence_mapping, requested_window, effective_window)`, `calculate_protein_st_density_scores(sheet, *, min_st_fraction, disallow_proline_next)` | Builder retains all S/T centers, clipped intervals and exact existing composition sheets for their windows. Calculator obtains validated length/symbol counts from `calculate_sequence_composition_scores`, owns the one S/T sum/fraction and candidate rule, and returns full rows/summary. Recalculation may change threshold/proline policy from saved windows; changing window size requires a new explicitly derived sheet from retained sequence, never relabeling old rows. |
| FAS alias/projection | `fas_domain_projection.py`: `project_fas_domain_rows(grading, *, label_rules, requested_metrics, subject_mapping)`; `fas_domain_return_views.py`: `fas_domain_fact_sources()`, `validate_fas_domain_selector(value)` | Consume the existing `{sheet,scores}` and exact source-bound rows. Reuse `projected_measurements`; do not calculate coverage/identity/E-values or create a new domain sheet. `label_rules` preserves the nine source name-substring rules and source identity, including possible multiple matches on one native row. Closed return keeps original row key, native profile reference, query/product subject, mapped source intervals, requested calculated metrics and explicit unavailable reasons. |
| Root integration | New `protein_sequence_result_views.py`/`protein_sequence_returns.py`, plus minimal owned edits to `tools.py`, configured API execution and `execution_episodes.py`/tool-information registration as required by selected route | `project_protein_sequence_rows(grading, *, selector)` only copies calculated fields. `record_admission(context, form, schema, operation_key)` and `validate_received_report(context, form, schema)` authenticate receipt, source, original subject/row, requested selection and equality. Parent-selected schemas return only requested facts. Pure new graders have no Store, execution, resource-selection or LLM dependency. |

The new field/schema names above are proposed coding handoffs, not installed
contracts. Root must freeze the following choices before assigning coding:

1. Route FAS to current selected `hmmscan` and retain its label rules as explicit
   name-based metadata. No second native run and no replacement HMMER formula.
   Exact Pfam-accession classification would require an actual supplied mapping;
   the upstream substring dictionary is not such a mapping. `ketoacyl-synt_C`
   can match both KS and KS-C rules; do not count two labels as two domains.
2. For a new FAS nucleotide call, freeze the explicitly selected translation
   contract. The legacy wrapper's implicit behavior is standard table 1,
   forward frame 0, non-CDS translation retaining stops. Existing
   `sequence.translate` supports making those choices explicit; use a retained
   translation if already available. Never choose another frame/code silently.
3. Give API disorder its own bounded acquisition adapter. The inspected source
   establishes an intended endpoint, not a working current provider contract.
   Missing endpoint/deployment verification is that specific open item; do not
   replace it with simulated/native-looking scores.
4. Keep N and O as distinct analyses sharing composition/coordinate components.
   Preserve N overlap policy, O edge denominators, O fallback-to-seven behavior
   when explicitly supporting legacy compatibility, and disorder's >=2 region
   rule. Any changed scientific behavior must be stated separately from fixing
   validation, capture and full-population return.

## Needed numerical and full-return verification

These are **hand-calculated future cases**, not results of tests or native runs.

| Operation | Checkable numbers and numerical edge cases | Actual-path verification still required |
| --- | --- | --- |
| Disorder | Four residues with scores `.6,.7,.4,.8`, threshold `.5`: 3 classified residues, fraction `3/4=.75`, percent 75; one length-2 region at native 1–2; position 4 is a singleton. At `.75`: one classified residue and zero length>=2 regions. Test exact threshold, gap, duplicate/out-of-order position, wrong residue, nonfinite score, empty/error/HTML response, truncated capture and CSV-only missing metadata. | Authentic service response and retained full artifact; selected API child -> parser -> same sheet/calculator -> publication -> requested parent rows; available-residue denominator versus complete query length; equality of returned values to saved scores; saved-only threshold recalculation; original action replay without HTTP; completion/failure does not create new scientific observations. |
| FAS | Hypothetical profile interval 11–30 has span 20; model length 100 gives `.2`; protein interval 31–50 with length 200 gives `.1`. These must be exact existing HMMER values. For a forward frame-0 translation of nt `[0,600)`, AA `[30,50)` maps to nt `[90,150)` through existing mapping. Test one KS-C row matching two name rules, no matches, repeated names/accessions, malformed preceding rows retaining original indices, missing display/length, E-value zero, multiple pages, and legacy flat fields remaining unavailable when format unverified. | Existing actual selected hmmscan job, full native page/bundle, FAS alias selection and requested row delivery through scientific parent; protein and nucleotide modes; no unsolicited translation/resubmission; unchanged saved HMMER recalculation; page completeness explicit; requested/API/native published numbers equal the shared score row. Required new evidence concerns alias/projection/returns, not rebuilding HMMER's fit/search. |
| N sequons | `NNST`: `allow_overlap=False` selects one `NNS` at 1; True selects `NNS` at 1 and `NST` at 2. `NPS`: zero. `N-S` is a source-validation defect that upstream matches; do not report it as a validated amino-acid sequon without qualification. Test lowercase, empty, <3 symbols, no matches, repeated motifs, and >100 retained matches. | Selected local primitive stores all rows and original sequence, emits requested subset plus full count/completeness, and retains identical values in sheet/calculated/publication/return layers. Full source provenance for file/snippet inputs, ancestry through selected sequence view, saved-only recalculation under both overlap policies, replay with no duplicate action/credit. |
| O heuristic | `STP`, window 3: center 1 window `ST` has `2/2=1`; center 2 window `STP` has `2/3`, display `.667`, and is excluded when followed-by-P disallow is true. At threshold .4, candidate count is 1 with exclusion, 2 without. At threshold `.667`, position 2 is excluded even without proline rule because unrounded `2/3 < .667`. Test clipped termini, all/no S/T, even/<3 window fallback, invalid thresholds, invalid symbols, and >100 candidates. | Selected local primitive retains all S/T windows including noncandidates; existing composition counts feed one new density calculator; source/row/position joins and typed return match exact calculated values. Verify saved threshold/proline recalculation, displayed rounding versus selection, complete artifact versus bounded page and closed replay. No NetOGlyc invocation or actual modification claim. |

For all new return paths, test forged row/source/subject references, reordered or
modified numerical values, unavailable requested fields, valid partial siblings,
no-hit versus unavailable inputs, the original immediate-child requested form,
scientific-parent admission and closed replay. Native fixtures, synthetic faults,
controlled episode paths and live-resource verification must be reported
separately. No completion claim is made here for any of the four operations.

## Source/contract evidence

Read complete relevant numerical paths: `hmmer_graders.py`,
`hmmer_search_grader.py`; API parser/builder and their full helpers in
`hmmer_search_inputs.py`; `sequence_composition_grader.py`,
`sequence_translation_grader.py`, `sequence_mapping.py`; the complete upstream
four functions/descriptors. Read actual publication, result-action, fact,
selector, projection, custody and admission methods named above, rather than
inferring capability from imports. The existing native path was traced at its
operation contract, acquisition/result dispatch, calculator invocation,
publication and requested-return consumers; this was not a rerun or a complete
audit of all HMMER execution modes.

Relevant shared implementation contracts were read: repository `AGENTS.md`,
`docs/TOOL_GRADER_GOAL_AND_PRINCIPLES_2026-10-24_001.md`,
`docs/TOOL_GRADER_BATCH_001_2026-10-24.md`,
`docs/TOOL_GRADER_BATCH_003_2026-10-24.md`, and
`docs/TOOL_GRADER_BATCH_003_LOCAL_BINDING_2026-10-24.md`. Older goal pointers and
per-tool sheet wording inside those records do not supersede the current
supplied goal's common numerical-authority requirement. Historical HMMER public
contract records 001/002 were read as dated evidence only, not present service
availability.

Installed source SHA256 values:

* `B/biophysics.py`: `7eb57d570d516ab22c089f0ff22141d3bb4f0fa73875208f32bcf375a0cb4127`
* `B/glycoengineering.py`: `ed3726d318f239e98183a359f18bcd341f4159ef2e400322c6141f77dcd2aff2`
* `B/synthetic_biology.py`: `f21d456a16a0c4c69e1158ad06f5516f4ab990035e91b7eedd0aa38ed5ff5782`
