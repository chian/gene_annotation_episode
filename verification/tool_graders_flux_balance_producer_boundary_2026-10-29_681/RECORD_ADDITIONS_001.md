# Exact proposed producer additions for root contract 007

This source-only proposal resolves the G1–G3 carrier choices in
`INTERFACE_GAPS_001.md`. It does not change shared code or the frozen contracts.
679 owns the shared types and validators;680 owns supplied-byte parsing. The
producer owner imports those definitions. Root assigns the actual edits.

## 1. Additive fields and compatibility

| Existing shared record | New property | Meaning |
|---|---|---|
| `ModelSnapshot` | `native_capture_evidence: object or null`, optional | Actual loaded metadata/configuration observations separate from exact Cobra JSON/SBML exports. |
| `ProblemSnapshot` | `native_capture_evidence: object or null`, optional | Actual native rows/columns, reaction expressions and integer controls separate from exact optlang/GLPK/LP exports. |
| `SolutionPayload` | `native_capture_evidence: object or null`, optional | Actual pass parameters, exceptions, getter observations and returned Cobra data. |
| `EffectiveModelPayload` | `source_audit: FBASourceAudit or null`, optional | Original supplied XML source view and binding to exact input bytes. |
| `ParsedModelSnapshots` | `source_audit: FBASourceAudit or null`, optional | The same bound source audit, retained for saved calculation and inspection. |
| `FBANativeManifest` | `request_application: FBARequestApplication or null`, optional | Typed evidence of original selected request application. |

Each added property is optional and nullable. An absent property leaves an old
record valid; null means no retained evidence of this type. Neither means an
empty native observation, successful application, complete source audit, or
default-zero measurement. Existing version literals remain unchanged because
these are optional additions. Every newly emitted producer record explicitly
includes its applicable property, with an actual object or null and a specific
existing Issue when capture failed. Do not rewrite previously retained bytes,
invent evidence in normalized677 fixtures, or change saved sheet digests.

The shared object validator must check required properties and reject unknown
properties while permitting these declared optional properties. It must not
silently make all prior required properties optional. Every member inside the
new typed records below is required unless explicitly marked nullable; only the
six containing properties above are optional. Finite-JSON validation still
applies recursively.

680 preserves raw `native_capture_evidence` unchanged. Add this property to the
existing raw-data traversal exclusions alongside native JSON exports. Do not
interpret arbitrary native dictionaries as typed File or SourceLocation records.
The new **typed** `source_audit.original_model` and request-application locations
are ordinary source addresses and must be bound/validated; they are outside
opaque raw evidence. Existing `*_pointer` semantics remain absolute JSON Pointer
within the containing capture artifact. No alternate envelope or ninth role is
introduced. Old absent fields stay absent in retained structures; a parser may
use `.get()` internally without materializing fabricated objects.

## 2. Exact native-evidence emitter layout and pointer targets

These are versioned native evidence layouts, not replacements for679's Number,
Bound, problem, solution, or calculation records. They preserve API observations;
679/680 own all normalized numerical meanings.

```text
ModelSnapshot.native_capture_evidence = {
  version: "cobra_model_native_evidence_v1",
  load_configuration: {solver_interface, lower_bound, upper_bound, tolerance},
  loaded_metadata: {compartments, genes, metabolites, reactions, groups},
  warnings: [WarningObservation],
  loader_diagnostics: [DiagnosticObservation],
  capture_failures: [ExceptionObservation]
}
ProblemSnapshot.native_capture_evidence = {
  version: "cobra_glpk_problem_evidence_v1",
  native_variables: [actual ordered native column observations],
  native_rows: [actual ordered native row observations and sparse entries],
  reaction_flux_expressions: [
    {reaction_position, reaction_id, expression: <actual expr_to_json result>}
  ],
  configuration: {integer_controls: <actual primitive glp_iocp fields or null>},
  capture_failures: [ExceptionObservation]
}
SolutionPayload.native_capture_evidence = {
  version: "cobra_glpk_solution_evidence_v1",
  native_passes: [
    {parameters: <actual primitive controls or null>,
     exception: <ExceptionObservation or null>,
     effective_problem_sha256: <exact effective_problem artifact SHA256>,
     raw_status_after: <actual original-problem status/return codes>,
     raw_original_problem_after: <actual immediate indexed getter observations>}
  ],
  configuration_after_solve: {
    integer_controls: <actual primitive glp_iocp fields or null>
  },
  raw_getters: <actual indexed native/optlang getter observations>,
  cobra_return: <actual original Solution status/objective/indexed series or null>,
  diagnostics: {
    warnings: [WarningObservation],
    logging: [LoggingObservation],
    exceptions: [ExceptionObservation]
  }
}
```

Native column observations retain native index/name/kind/bound type, actual bound
getter returns and typed-side qualification. Native row observations retain
native index/name/bound type, actual bound getter returns, actual `nnz`, and each
native returned column index/coefficient in returned order. This preserves getter
defaults without treating an unused bound side as zero. Typed bounds use GLPK's
bound type; sparse equations use the actual returned entries. The raw record may
contain a placeholder getter zero which the corresponding typed bound correctly
marks unbounded. Full variable populations, counts, indices and auxiliary columns
are not filtered to reactions.

Raw float observations retain a finite JSON value when finite, `repr(value)`, and
`float.hex()` when finite. For a nonfinite return retain null in the finite-value
slot, the actual native token, and an explicit nonfinite observation state. An
exception means no return, not a numeric zero. These raw encodings do not have
typed SourceLocations recursively embedded inside them. Normalized existing
Number/Bound records point to the actual observation's value/token field and use
the shared source/precision/missing-state rules. Do not put NaN or infinity in
JSON number syntax. Integer codes and counts are retained as exact integers.

Diagnostic layouts are fixed for the emitter:

```text
ExceptionObservation = {
  stage: existing Issue stage, operation: string,
  exception_module: string, exception_class: string,
  message: string, traceback: string
}
WarningObservation = {
  stage: existing Issue stage, category_module: string, category_name: string,
  message: string, filename: string or null, lineno: unsigned integer or null
}
LoggingObservation = {
  stage: existing Issue stage, logger_name: string, level_number: integer,
  level_name: string, message: string,
  pathname: string or null, lineno: unsigned integer or null
}
DiagnosticObservation = {
  stage: existing Issue stage, producer: string,
  code: integer or string or null, severity: integer or string or null,
  message: string, line: unsigned integer or null,
  column: unsigned integer or null
}
```

These are actual caught objects, native log records and libSBML diagnostics, not
generated explanations. Do not synthesize traceback/filename/line information.
They are internal retained evidence; parent returns continue to use the declared
typed issue/result form. Standard finite native control values retain their
actual native field names. A nonprimitive callback/data pointer is recorded as
unavailable with its type and capture issue, never serialized as executable data
or replaced by a guessed control value. Complete primitive controls are retained
at each actual native pass entrance; observed mutations remain separate records.
685's source review requires immediate post-return original-problem getter/status
capture before control returns to optlang, since a later internal pass can reset
the state. The raw pass rows retain those observations and the pre-solve problem
artifact identity. Earlier pass data never replace the final solution fields.

Required pointer targets for newly emitted captures:

| Typed field | Pointer within its containing artifact |
|---|---|
| Problem `reaction_variables[i].flux_expression_pointer` | `/<phase>/native_capture_evidence/reaction_flux_expressions/<i>/expression` |
| Before-solve `integer_controls_pointer` | `/effective/native_capture_evidence/configuration/integer_controls` |
| Solution `native_passes[k].parameters_pointer` | `/native_capture_evidence/native_passes/<k>/parameters` |
| Solution `native_passes[k].exception_pointer`, if an exception exists | `/native_capture_evidence/native_passes/<k>/exception` |
| After-solve `integer_controls_pointer` | `/native_capture_evidence/configuration_after_solve/integer_controls` |
| Solution `diagnostics_pointer` | `/native_capture_evidence/diagnostics` |

Here `<phase>` is exactly `loaded_original` or `effective`; positions retain the
original actual sequence. The number of raw pass rows equals typed pass rows and
they correspond by native-pass position. Capture failure may leave a null target
and an explicit issue; a nonnull typed configuration must not assert that its
unavailable raw controls were fully captured. No false `""` pointer to an entire
artifact is substituted for a missing control/diagnostic observation.

## 3. Typed supplied-source audit and XML address grammar

Add these shared records (names below are exact proposed public schema names):

```text
FBAXmlName = {
  namespace_uri: string or null,
  local_name: nonempty string
}
FBAXmlPathStep = {
  name: FBAXmlName,
  sibling_ordinal: unsigned integer
}
FBAXmlAttribute = {
  name: FBAXmlName,
  value: string
}
FBAXmlNamespace = {prefix: string, uri: string}
FBAXmlSourceElement = {
  source_record_index: unsigned integer,
  path: nonempty array of FBAXmlPathStep,
  parent_source_record_index: unsigned integer or null,
  child_source_record_indices: array of unsigned integer,
  namespace_declarations: array of FBAXmlNamespace,
  attributes: array of FBAXmlAttribute,
  text: string or null,
  tail: string or null
}
FBASourceAudit = {
  version: "cobra_fba_source_audit_v1",
  input_profile: "sbml" or "cobra_json",
  original_model: SourceLocation,
  xml_elements: array of FBAXmlSourceElement or null,
  issues: array of existing Issue
}
```

`original_model` is `{role:"original_model", pointer:""}` before680 binding;
after binding it is the existing File+pointer SourceLocation. This whole-file
pointer is valid for XML. The audit is located once at **effective_model role,
`/source_audit`**, outside loaded/effective snapshots. Its profile equals the
containing model payload's profile. Both snapshots reference this same source.

For SBML, enumerate every XML **element** in document preorder. Array index,
`source_record_index`, and referenced parent/child indices use this original
preorder and are never compacted after an unsupported scientific element. The
first/root element has parent null, one path step and sibling ordinal zero.
Every later path appends one step to the parent's path. `sibling_ordinal` is the
zero-based ordinal among the parent's element children with the same expanded
`(namespace_uri,local_name)`; it is not an XPath string, global ordinal or native
Cobra position. Parent and ordered child indices must agree bidirectionally.
Sibling paths are unique and are validated against those relationships.

`namespace_uri=null` denotes no namespace. Namespace declarations are only those
actually declared on that element; inherited bindings are obtained from the
parent chain. The default prefix is `""`. Names are expanded XML names; attribute
namespace rules differ from element default-namespace rules as in XML. Duplicate
expanded attribute names are invalid input, not a merge. Attributes are retained
in original encounter order, although that order has no scientific meaning.

Attribute `value`, element `text` and `tail` are the source parser's XML character
data after XML entity/line-ending normalization, **not** libSBML getter values,
Cobra defaults, a generated reaction formula, serialized rewritten XML, or claims
about byte-exact lexical spelling. Preserve whitespace, empty strings, and null
distinctions returned by that parser. Exact original bytes remain the authority
for lexical spelling, namespace prefix spelling, comments and processing
instructions. No external entity/network resolution is allowed. Any source
feature that cannot be represented is retained in original bytes with a specific
issue; it is not silently normalized into supported linear model semantics.

Example of an original SBML bound attribute value: if source element preorder17
has `fbc:lowerFluxBound="LB_IN"` as attribute2, the audit stores its expanded FBC
name and `value:"LB_IN"`. Its typed address is
`{role:"effective_model", pointer:"/source_audit/xml_elements/17/attributes/2/value"}`.
The referenced parameter's actual `value="-10"` is separately represented by its
own source element/attribute, with its own address. The audit does not replace a
parameter reference with the resolved number or insert a `units` attribute.

SourceIdJoin rows for SBML use the absolute XML element preorder as
`source_record_index`; `kind` distinguishes the biological entity. Their source
address selects the actual audited element/ID attribute. SourceFeature rows
select the actual source element/attribute. A loaded reaction's
`gpr_source_pointer` selects its actual original `geneProductAssociation` element
record under `/source_audit/xml_elements/<i>`; child indices preserve the exact
and/or/product-ref tree. If original SBML has no single text GPR string,
`gpr_native` remains null and `gpr_loaded` is the actual Cobra rule. Do not present
the loaded rule as an original source string.

For Cobra JSON, set `xml_elements=null`. Actual source values use ordinary
SourceLocations directly into `original_model` JSON, e.g.
`/reactions/0/gene_reaction_rule`; SourceIdJoin source indices are the actual
array indices within their declared kind. A same-artifact `gpr_source_pointer`
cannot point directly into another file: retain that source string in the
snapshot's native evidence and point there, with a separate typed source join
to the unchanged original JSON field. No raw JSON copy is required in the audit.
Genuinely absent JSON fields stay absent in the original bytes; an API default
may be recorded as a loaded observation only.

Capture this audit from the selected original bytes before loading the model.
If model loading fails but source decoding succeeded, the model payload may have
both snapshots null and retain the complete audit. If source decoding fails,
retain original bytes, audit null, and actual diagnostics/Issue; never reconstruct
source information by re-exporting the loaded/effective Cobra model.

## 4. Typed request application in the manifest

Use the **optional nullable `FBANativeManifest.request_application` member**;
there is no second request-application copy inside opaque solution diagnostics.

```text
FBASolverOptionApplication = {
  name: "feasibility_tolerance" | "optimality_tolerance" | "integrality_tolerance",
  application: "applied" | "not_requested" | "rejected" | "not_attempted" | "unknown",
  requested_source: SourceLocation,
  effective_source: SourceLocation or null,
  issue_code: existing IssueCode or null
}
FBARequestApplication = {
  version: "cobra_fba_request_application_v1",
  selected_request: SourceLocation,
  constraint_changes: array of existing ConstraintChange or null,
  objective_request: existing ObjectiveRequest,
  objective_application: "applied" | "model_default" | "rejected" | "not_attempted" | "unknown",
  objective_requested_source: SourceLocation,
  objective_effective_source: SourceLocation or null,
  solver_option_applications: array of FBASolverOptionApplication,
  request_realization: "exact" | "mismatch" | "unknown",
  issues: array of existing Issue
}
```

`selected_request` selects `/requested_job` in selected_request role. Objective
requested source selects `/requested_job/native_flux_balance/objective` there;
effective source selects `/effective/objective` in effective_problem role when
that state is retained. Constraint rows preserve requested order; null and empty
constraints stay distinct. Use existing ConstraintChange/Bound types, with the
bound source pointing at the respective unchanged selected-request bound record.
Any earlier provenance remains in that original selected request; it is never
deleted or rewritten to pass identity checks. Effective reaction positions refer
to the actual effective model, not constraint-list indices.

Exactly three solver-option application rows appear, in the declared order
feasibility, optimality, integrality. `requested_source` selects the corresponding
field under `/requested_job/native_flux_balance/solver_options`. An available
effective source selects the corresponding Number in effective_problem role's
`/configuration_before_solve/<option_name>`. There is no second numerical options
schema. Null requested value means `not_requested`, not applied-default. Public
optimality is unsupported by the selected optlang interface; a nonnull request
is rejected before optimize with `solver_option_unsupported`.

679 validates local relationships and existing enum/number/source shapes.680
cross-checks this record against the untouched selected request, retained model,
problem and configurations, including constraint order/IDs/bound values,
objective choice and option fields. Compare selected scientific values and
meaningful joins, not newly bound SourceLocation object bytes. Request identity
is still checked using `execution_contracts.digest` on the original decoded
request **before** any role rebinding. A contradiction becomes an existing
`request_effective_mismatch`/identity issue, not acceptance of the producer's
assertion. The manifest's aggregate realization must agree with its nonnull
application record.

Successful setter execution alone is insufficient for `applied`: record actual
readback and its source. `model_default` requires retaining the original selected
objective without requested replacement. Complete validation failure before
application records applicable operations as `not_attempted`, count0. Unexpected
setter failure preserves prior applied rows, the failed row and later
not_attempted rows; no optimize occurs. An unsupported or unobservable readback
remains unknown. `exact` requires all requested values and supported semantics
to be realized; `mismatch` requires actual contradictory/rejected realization;
missing evidence stays unknown.

680 populates the existing NativeFBAResult constraint/objective/application and
realization fields from this typed source, preserving all new evidence in the
retained manifest. Old records with absent/null application keep their current
honest unknown application values. Do not infer `applied` merely because an ID
exists or final bounds happen to match.

## 5. Exact owner handoffs and verification additions

* Shared schema owner: `flux_balance_contracts.py`, corresponding679 contract007,
  and its owned tests. Add only these optional fields/new source records and
  meaningful joins; no new sheet or calculator policy.
* Supplied-byte parser owner: `flux_balance_readers.py` and its owned tests. Carry
  optional source audit; bind typed locations; preserve opaque native evidence;
  consume/cross-check request application.684's independent malformed-role and
  source-index repair remains contract006, not producer behavior.
* New native producer owner: the four new native modules and new producer test
  file enumerated in `PRODUCER_PLAN_001.md`. Emit explicit fields using the shared
  definitions and consume685's exact G6 range/point qualification handoff.
* Capture/worker owner: separate new `native_flux_balance_local.py`,
  `native_flux_balance_capture.py`, `native_flux_balance_results.py` and
  `flux_balance_result_worker.py` against the main
  plan's typed host/custody handoff. Existing execution-file edits remain with
  the independently assigned root integration owner.

Required new tests, in addition to main plan P1–P11: old saved/normalized records
without each optional field; explicit null evidence; source audit retained after
model-load failure; namespaced attributes/default namespace/repeated same-name
siblings; IDs and parameter references with omitted units; nontrivial source GPR
tree; actual empty string versus absent text/attribute; JSON original versus
loaded defaults; malformed parent/path/child joins; audit original-file identity
conflict; exact original constraint order including null versus empty; rejected
unsupported optimality; earlier applied and later not-attempted changes; native
diagnostic/pass pointer resolution; contradiction between request readback and
manifest assertion; and request identity unchanged through role binding.

Source-derived/normalized fixtures must be labeled as such. Authentic output
validation later uses the new producer's one selected call on a tiny explicit
fixture, with actual sealed bytes and writer-closure evidence. Reusing677 native
observations proves those observations only; it does not turn diagnostic probe
JSON into emitted producer format. This planning task executed none of these
tests and emitted no native artifacts.
