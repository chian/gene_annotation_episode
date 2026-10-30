# Concrete root decisions before producer coding

This is a producer/consumer interface review against679 contracts001–004 and the
current679/680 source. It does not change those contracts or the user's goal.
681 has not edited shared code. **RECORD_ADDITIONS_001.md is the final exact
G1–G3 proposal for root007 and supersedes the provisional carrier placements,
requiredness and alternatives below.** It selects optional nullable evidence,
one typed top-level model source audit with XML element/attribute grammar, and
one typed optional manifest request-application member. The earlier alternatives
below explain the source review; they are not competing coding directions.

## G1. Raw native capture evidence has no honest current carrier

Observed: `SolutionPayload` is closed and has `diagnostics_pointer` but no
diagnostics object. `NativePass` has parameters/exception pointers but no native
control/exception payload. `SolverConfiguration` has an integer-controls pointer
but no integer-controls object. `ProblemSnapshot` has no raw reaction flux
expression storage other than upstream `native_optlang_json`, which does not
contain reaction joins.680's `_bind` resolves every typed `*_pointer` against the
current decoded payload. Pointing to a nonexistent key fails; `""` or `/issues`
would be a syntactically valid but misleading substitute for absent evidence.

Recommended root choice:679 adds one nullable finite raw-evidence object named
`native_capture_evidence` to each `ModelSnapshot`, `ProblemSnapshot` and
`SolutionPayload`. Keep exact native exports unmodified. The object is internal
source evidence, with a versioned emitter layout, not another sheet or calculator.
680 preserves it untouched and includes it in the raw-evidence exclusions used by
address traversal. The producer does not copy shared analytical schemas.

Proposed exact emitter layouts:

```text
ModelSnapshot.native_capture_evidence = {
 version: cobra_model_native_evidence_v1,
 source_audit: <G2 exact source-audit object>,
 load_configuration: {solver_interface, lower_bound, upper_bound, tolerance},
 loaded_metadata: {compartments, genes, metabolites, reactions, groups},
 warnings: [actual warning records], loader_diagnostics: [actual records]
}
ProblemSnapshot.native_capture_evidence = {
 version: cobra_glpk_problem_evidence_v1,
 native_variables: [actual index/name/kind/type/lower/upper records],
 native_rows: [actual index/name/type/lower/upper/ordered sparse entries],
 reaction_flux_expressions: [actual reaction ID/position and expr_to_json value],
 configuration: {integer_controls: <complete actual primitive GLPK control object>},
 capture_failures: [actual exception records]
}
SolutionPayload.native_capture_evidence = {
 version: cobra_glpk_solution_evidence_v1,
 native_passes: [{parameters: <actual primitive controls>, exception: <record|null>}],
 configuration_after_solve: {integer_controls: <actual controls|null>},
 raw_getters: <original actual values, including unestablished point values>,
 cobra_return: <original indexed Solution fields|null>,
 diagnostics: {warnings: [...], logging: [...], exceptions: [...],
               request_application: <G3 record|null>}
}
```

No computed feasibility/residual/objective-agreement fields belong here. Missing
APIs/observations are null with their explicit capture failure, not fabricated
objects. Raw nonfinite scientific numbers need the existing finite token/state
encoding rather than JSON NaN. Exception records retain stage, class, message
and traceback as native evidence; they do not cross parent forms as free prose.

Concrete pointers become
`/effective/native_capture_evidence/reaction_flux_expressions/<i>/expression`,
`/effective/native_capture_evidence/configuration/integer_controls`,
`/native_capture_evidence/native_passes/<k>/parameters`, corresponding exception
pointer, `/native_capture_evidence/configuration_after_solve/integer_controls`,
and `/native_capture_evidence/diagnostics`. Before-solve configuration's pointer
can target the effective problem snapshot in the same payload. Solution pointers
target its own payload. This uses eight roles unchanged.

An alternative is a versioned outer producer envelope, but that would require
680 to unwrap/rebase all current absolute JSON Pointers and preserve the envelope
for saved evidence. Adding the raw object to the existing nested snapshots avoids
that broader consumer change. Do not silently implement either alternative.

## G2. Supplied SBML locations and original GPR/metadata

Observed: a JSON Pointer cannot select an XML attribute. Original source
occurrences/CVTerms/units are not all in Cobra `_sbml` or native JSON exports.
Raw original GPR can differ from its loaded string. The current shared source
location contract has only file+JSON Pointer (plus the declared CSV logical
table), while `_bind` validates GPR/annotation pointers in the model payload.

Recommended root choice: use G1's `source_audit` to retain a declared logical
source-record view, copied from the selected bytes without inventing values:

```text
{profile: sbml|cobra_json, original_model: {role: original_model, pointer: ""},
 source_records: [{kind, source_record_index, source_id,
   source_locator: {kind: json_pointer|xml_source_record, value: str},
   supplied_fields: object}],
 sbml_document: object|null, json_document: object|null,
 diagnostics: [actual loader/libSBML records]}
```

The XML locator is explicitly a source-record description, not a fake JSON
Pointer into XML; preserve source IDs, original order and literal/source presence.
Typed source locations for these audited values point into
`effective_model:/loaded_original/native_capture_evidence/source_audit/...`.
`source_audit.original_model` points at the whole exact input artifact.
For a directly supplied JSON field a typed `{role:original_model,pointer:...}`
can additionally point to its actual field. Loaded annotation/GPR pointers remain
within the model payload; original GPR points to the retained audited original
field, not the later loaded rule. Source fields genuinely absent are omitted
inside `supplied_fields`, with no getter default or assigned unit masquerading
as a source field. Effective snapshot can reference the same source audit once
by pointer rather than duplicating full source metadata.

679 should own the source-record type decision;680 must preserve/validate the
meaningful typed source relationship. No new numerical sheet is proposed.

## G3. Per-change/request application is not transported

Observed: `FBANativeManifest` carries aggregate `request_realization` only.680
builds ConstraintChange rows from selected request and effective reaction IDs,
then assigns `application="unknown"` for all rows and
`objective_application="unknown"`. There is no structured producer input from
which the parser could honestly populate applied/rejected/not_attempted.

Recommended root choice:679 freezes a small source record
`FBARequestApplication = {constraint_changes:[ConstraintChange],
objective_request:ObjectiveRequest, objective_application:<existing enum>,
solver_option_applications:[{name:feasibility_tolerance|optimality_tolerance|
integrality_tolerance, application:applied|not_requested|rejected|not_attempted,
issue_code:IssueCode|null}], request_realization:exact|mismatch|unknown}`.
It is actual request/application evidence, with requested bounds located in the
unchanged selected_request. Put it in G1's Solution diagnostics (which can be
emitted with count0 for a handled pre-solve failure), or add one explicitly typed
manifest field if root prefers validation at that boundary.680 consumes the
frozen record, cross-checking selected order/values/reaction IDs and effective
values without recomputing scientific diagnostics. An available contradictory
application record must become a conflict, not a convenient “exact” assertion.

Actual solver-option values already live in before/after configurations. Do not
create a second native options/calculation schema. Whole-request validation can
mark all operations not_attempted on an invalid request; on an unexpected setter
failure preserve previous applied changes and later not_attempted changes.

## G4. Original selected request can name prior files outside eight roles

Observed: FBAJob permits model acquisition receipt File and requested Bound
SourceLocations.680 `_bind` rejects any retained File not among the supplied
eight role files; `ParsedFBABundle` requires all source files in retained_files.
The initial null-source supplied-bound/supplied-file case works, but an unchanged
valid prior-source request can fail before decoding its model.

Proposed choice for the first producer binding: supplied SBML/JSON plus bounds
whose original sources are null or already among its eight artifacts; preserve
any other selected request byte-for-byte and report this binding limitation.
Do not delete/rewrite existing prior-source fields to make their digest pass.
For general support root should freeze explicit authenticated prior-file inputs
for680/capture (separate custody metadata, eight scientific roles unchanged),
or a rigorously defined selected-request source rebinding that keeps the raw
request identity and original provenance. No parser should guess trust from a
path or fabricate an artifact_ref. Repository acquisition stays separately
selected and cannot happen inside this producer.

## G5. Source-function pin convention

`source_function_sha256` is required by679/002 but its byte domain is not stated.
677 retains the whole Biomni source-file pin. Proposed convention is exact bytes
of the whole four-argument definition, lines33–147 inclusive including final
newline, SHA `ab47e2640366833d05cf896091e1c3803ce69aae940bfa46ba993abda51983b9`.
Keep module SHA `9ac7daa2c5257347e041a1c68eb59dbc98a77eac62402b8f67e7ee3d288b0c40`
separately in software/source custody. Root should explicitly select the
convention; never reinterpret old module pins retroactively.

## G6. Point qualification and native option ranges

677 establishes only a real optimal LP with one simplex return0, status5,
primal/dual2/2. The pinned Cobra/optlang sources permit raw retrieval after some
nonoptimal statuses; GLPK defaults can also return finite zeros before a solve.
Root assigned the precise primary-source status/return rule to685. Its source
review establishes that NOFEAS can carry an actual original basic point, so a
blanket FEAS/INFEAS-only filter is not the producer contract. Preserve raw getters
immediately after each actually returned native pass; a later optlang pass can
reset statuses/objective and invalidate the final state. Earlier points remain
per-pass evidence, not substitutes for the final SolutionPayload. Use685's exact
returned-pass/final-state predicate. UNDEF is not evidence of a native point.
Do not manufacture another native pass. A truly established infeasible candidate
must not be discarded just because its residuals fail.

Also, optlang's native tolerance setters assign GLPK control fields directly;
the current shared request schema only excludes negative values.685's GLPK5.0
source review establishes strict `0 < tol_bnd < 1`, `0 < tol_dj < 1` and
`0 < tol_int < 1`. Public optimality remains absent in optlang1.9.1, and the producer
must not silently translate that request into `tol_dj`. Use the final685 source
handoff for exact range and qualification implementation. Observed1e-7 is a real
supported setting, not a replacement for a selected value.681 itself made no
network request or new native solve;685's source findings are separately owned
evidence, not a native measurement by681.
