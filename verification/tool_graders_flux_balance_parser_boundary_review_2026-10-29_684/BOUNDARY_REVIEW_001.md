# Supplied-byte FBA parser boundary review, 684

Production was read only. This review owns this packet, the four new cases in
`tests/test_flux_balance_parser_boundary_684.py`, and generated
`bounded529/check147_review684` output, as assigned by root. It changes no
sheet, calculator, parser, producer, execution, prompt, inventory or progress row.
The original user attachment remains authoritative; this is implementation
evidence, not a goal or scope replacement.

`bounded529` below denotes
`verification/tool_graders_hmmer_map_verification_2026-10-28_529`.

## Result

The existing 56 passing reader cases are substantiated by their actual saved
receipt, audit, individual case reports and byte hashes. Four new narrow
reproductions demonstrate two parser defects: later-pass issue locations use
compacted indices, and malformed producer role values escape as `TypeError`.
Neither is an absent-producer complaint. Contract 005's expected-term-count
repair belongs to 683 and was not duplicated.

## Public input to output boundary

All metadata arguments are validated by the shared closed-record validator.
Invalid caller metadata can raise a specific `ValueError`. Valid File metadata
must match the supplied byte length/SHA before content is interpreted. Content
errors ordinarily become located issues and preserve independent valid rows;
the demonstrated source-role exception below violates that recovery behavior.

| Public parser | Supplied inputs and interpretation | Returned record and limits |
| --- | --- | --- |
| `parse_cobra_glpk_model_capture(raw, *, source, original_model)` | `cobra_model_capture_v1` bytes plus capture File and original-model File metadata. Reads normalized loaded-original/effective snapshots; it does not load SBML or Cobra JSON. Checks profile/loader pair and original-model format. | `ParsedModelSnapshots`; separate snapshots, native metadata, source-ID joins, feature audit and issues. Expected populations and surviving entity positions remain explicit. |
| `parse_cobra_glpk_problem_capture(raw, *, source, models)` | `cobra_glpk_problem_capture_v1` bytes and validated ParsedModelSnapshots. Parses variables, sparse expressions, objective, reaction-variable joins and captured configuration. | `ParsedProblemSnapshots`; original/effective phases separate. Bad sparse terms are excluded with `terms_complete=false`; original variable positions survive. Cross-model mismatches remove offending joins/rows and mark partial representation. |
| `parse_cobra_glpk_solution_capture(raw, *, source, problem)` | `cobra_glpk_solution_capture_v1` bytes and validated ProblemSnapshot or null. Parses actual statuses, native passes, objectives, primals/activities/reaction fluxes and configuration. | `ParsedNativeSolution`; duplicate values remain ambiguous evidence. Invalid independent rows are excluded with issues. `not_established` removes present candidate getter values; it does not manufacture a zero point. |
| `parse_biomni_fba_csv(raw, *, model, source)` | Exact header `reaction_id,reaction_name,flux,lower_bound,upper_bound`; UTF-8 with optional BOM; validated ModelSnapshot or null. | `ParsedFluxRows`; original logical data-row indices, IDs, associations and exact tokens. Malformed-width rows do not shift later rows; unclosed quoting ends interpretation because later logical indices are unknowable. Missing/nonfinite/invalid/zero and infinite bounds remain distinct. Decimal flux precision is unknown and `float_hex=null`. |
| `parse_fba_capture(payloads, *, expected)` | Eight exact role keys, each `{file, bytes, state}`; validated FBAAttemptIdentity. Verifies role formats and bytes, then request/manifest identities, model/problem/solution/CSV records and recognized legacy log grammar. | `ParsedFBABundle`, accepted unchanged in meaning by `populate_flux_balance_sheet`. Invalid request/manifest identities cannot certify the request, but independent scientific records survive. This does not establish original-writer custody, execution binding or episode delivery. |

`populate_flux_balance_sheet` only validates/detaches ParsedFBABundle and adds
the shared sheet version/operation/mode. Readers invoke no numerical calculator.
The same shared contracts apply to both normalized SBML and Cobra-JSON profiles.

## Exact identities, source addresses and producer obligations

1. Emit all eight roles with the formats in contract 002: original_model
   (`sbml|cobra_json`), selected_request, effective_model, effective_problem,
   solution, flux_csv, native_log and manifest. Non-original formats are the
   exact frozen version strings; native_log is `utf8_text` or explicitly
   `biomni_fba_log_v1`. Manifest lists the other seven roles, never itself.
2. Supply immutable actual bytes and their exact File identities. A mismatched
   hash/length or conflicting identity for one artifact_ref cannot authorize
   source binding. Truncated JSON is not interpreted as a full capture;
   complete independent logical rows of truncated CSV can survive. Retention
   does not by itself make an incompatible artifact usable.
3. Preserve the original selected requested_job object. The parser binds a
   detached copy, then compares `execution_contracts.digest(raw["requested_job"])`
   with the expected digest; it never hashes the bound replacement as the
   original request. The raw object remains unchanged. Attempt equality,
   original-model SHA/size/format, selected software digest/source-function
   digest, manifest role identities/effective-problem digest, distribution
   versions and interface checks are separate. Existing positive binding and
   raw-job/expected-digest tampering cases cover this distinction.
4. Typed `{role,pointer}` becomes `{file,pointer}`; typed `{role,identity}`
   becomes a retained File only when the exact identity matches. Opaque native
   JSON dictionaries are preserved as evidence, not recursively rebound.
   Every nonnull `*_pointer` field is resolved against its containing capture
   document. JSON Pointer escaping and array indices are checked.
5. Prefer the full bundle boundary for producer integration: it supplies all
   successfully decoded JSON role documents for cross-role target lookup.
   Standalone calls have only their own capture bytes. They can validate other
   retained File identities and pointer syntax, but cannot inspect the target
   contents of files whose bytes they did not receive. Their `retained_N` file
   aliases are not a reconstruction of every producer role name.
6. The already documented SBML limitation remains: no frozen nonempty XML
   logical JSON-Pointer profile exists. Use the empty whole-artifact pointer;
   do not substitute XPath or claim nonempty target inspection. This review
   does not count that accepted limitation as a new defect.
7. Emit source-order entity positions and expected native populations, native
   numeric tokens/hex/precision, explicit sparse completeness, and separate
   loaded-original/effective operands. Keep original GPR and loaded GPR,
   auxiliary/split variables, native objective constant/interface offset,
   native reaction fluxes and CSV observations separate. Null/unknown remains
   unavailable information, not inferred scientific data.
8. The current `utf8_text` role is diagnostic evidence only. Only the declared
   legacy wrapper grammar supplies a formatted-six-decimal objective and
   source active-count observation. Options/diagnostics capture and request
   realization fields are 681's producer-design work, not defects invented by
   this review. Existing manifest `request_realization` is a retained producer
   assertion subject to identity checks; parser availability alone proves no
   real execution.

Source inspection of the complete reader, contracts, sheet and canonical
digest implementation finds no file/network/acquisition/solver or LLM call in
the parser path. The existing purity case blocks file opening and scientific
imports during parsing. That test does not separately instrument every possible
network primitive; no network or subprocess call exists in the reviewed reader.

## Demonstrated defects and exact reproduction

The four new cases assert required behavior and intentionally fail on the
unchanged parser. Complete controlled input/actual-output JSON is retained in
`bounded529/check147_review684/fba684_*.json`; no native producer or new solve
was used. All inputs remained unchanged.

| Defect | Controlled input | Actual output | Required repair |
| --- | --- | --- | --- |
| D1a: model join issue loses original array index | `source_to_loaded_ids=[{}, conflicting mapped row at index 1, valid mapped row at index 2]` | Conflict has `source_row_index=0` and `field=/source_to_loaded_ids/0/source_to_loaded_ids`. Three reactions and the valid source row 2 survive. | Carry original array index through `_rows` into `_model_capture`'s join validation. Report row 1 and a source-resolvable field, rather than appending a whole-record validator path to a compacted row path. |
| D1b: problem join issue loses original array index | `effective.reaction_variables[0].forward_variable_position=true`; row 2 has `forward_variable_id="WRONG"`. | Conflict for reaction_position 2 points to `/effective/reaction_variables/1`, where the independent AB row actually resides. Seven variables, five constraints and reaction_position 1 survive. | Carry original row identity through `_problem_snapshot` join filtering; the conflict belongs to `/effective/reaction_variables/2`. |
| D2: malformed role crashes partial recovery (two cases) | `variable_values[0].primal.source={role: [], pointer: "/variable_values/0/primal/value"}`; repeat with `role: {}`. | Public solution parser raises `TypeError: unhashable type: 'list'` / `'dict'`; it returns no partial result. | `_bind` must type/shape-check role selectors before dictionary membership/lookup and raise the shared specific validation error. Existing row recovery should retain variable positions 1–6, all three reaction values and all five constraint values with a row-0 schema issue. |

D1 is owned by reader row-index propagation and issue construction, not by
the scientific entity-position schema or calculator. The same post-filter
enumeration pattern occurs in other `_model_snapshot`, `_problem_snapshot`
and `_problem_capture` recovery passes; those sites need inspection during the
same narrow repair, but this review executed only the two tabled examples.
Specifically, `_model_snapshot` enumerates previously filtered entity rows for
out-of-population issues and filtered stoichiometry/medium rows for relationship
issues; group-member issues omit the containing original group/member path.
`_problem_snapshot` enumerates filtered reaction-variable rows and combines
surviving constraints with the objective when locating out-of-range terms;
that latter issue uses `/effective/terms` rather than an actual expression's
source path. `_problem_capture` again enumerates already filtered reaction joins
and constraints for cross-model errors. Original indices should flow through
these passes, including any earlier constraint or term rejection. These are
source-traced coverage requirements, not additional executed demonstrations.
D2 is owned by `_bind`'s producer-address validation and its callers' existing
ValueError recovery. No global catch-all or permissive role coercion is needed.
The unexecuted full-bundle route calls the same helper; only the direct solution
entrypoint was used for the two TypeError reproductions.

## Verification evidence and limits

`check143e_readers680`: inspected original receipt, audit, selected request,
stdout and all 56 unique call reports. All 56 outcomes are passed; pytest reports
56 passed in 2.84 s. Receipt return 0, terminal/quiescent; source, dependency,
stdlib and executable pins unchanged. Audit has no outside modules or unbound
mappings and confirms native/retained fixtures unchanged. All five reviewed
receipt/report hashes match 680 EVIDENCE. No successful suite was rerun.

Current reader/test/digest source equals the final frozen 680 source. The
shared contracts file now differs only by 683's separately assigned 005 change
to nullable expected_term_count and its conditional comparison; the 680 receipt
is evidence of its original frozen contract, not a retroactive test claim for
later source. The authentic CSV and all other original 677 source pins still
match 680's evidence. CSV values IN=7, AB=6, OUT=6 are tested authentic retained
rows; normalized seven-variable/five-constraint captures and objectives -4.25
and -2.75 are explicit test transformations, not an emitted production format.

`check147_review684`: exactly four new cases ran once; four failed at the
intended recovery assertions in 0.59 s. Collected return 1, terminal/quiescent;
source/dependency/stdlib/executable pins unchanged; no outside modules/unbound
mappings; native and original fixture pins unchanged. Explicit check005
dependencies, 20 GiB RAM, 4 GiB scratch, zero swap, no wall cap. Observed scratch
603230208 bytes. No solve, acquisition or download ran.

The next concrete action is a fresh reader-repair assignment for D1/D2, using
the four saved regressions unchanged plus narrowly affected address/index cases.
Root's additive `679/IMPLEMENTATION_CONTRACT_006.md` now defines that repair;
this reviewer read it in full and makes no production repair. Preserve
the raw request digest semantics and all independent valid rows. Then continue
681's separately owned producer design and authentic emitted-format
verification. Original writer custody, production capture, installed operation,
saved-result publication, requested child returns and live-resource verification
remain unfinished; this review does not claim those outcomes.
