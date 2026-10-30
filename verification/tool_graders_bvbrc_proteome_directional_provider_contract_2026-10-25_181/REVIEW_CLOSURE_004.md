# Additive review closure: imports, validation and source consumers

This adds root's review clarifications to181/001–003; those records are retained.
The exact001/002 data shapes and selectors stand. Where003's shorthand could
imply a dependency cycle or a second full numerical validation, the explicit
rules here control. This remains design-only.

## Numerical authority and validation once at production

Downstream implementation also consumes179's
`DISJOINT_PREREQUISITES_006.md` and `CALLER_DECIMAL_CONTEXT_007.md`. Native
disjoint aggregation preserves conflict > invalid > missing prerequisites;
the compatible-map precondition in005 remains separate. Exact ratio rendering
is independent of the caller's Decimal precision, exponent bounds, rounding and
traps. Do not replace this arithmetic with default-context Decimal or float.

The applied179 `APPLICATION_RECEIPT_001.json` records nine new numerical/test
files and its packaging change, candidate319 tests and installed native check.
Its pending applied-test field is historical: the subsequent
`applied_verification_001/receipt.json` records319 passing tests,0 failures/errors,
81.257s pytest time and845 source paths unchanged. It explicitly excludes live
service and provider/return integration. Neither receipt completes D/F.

`calculate_directional_components(sheet, parameters=...)` currently validates
the observations/parameters and calls A's full `DirectionalComponents` semantic
validator before returning its exact components. That validator uses B. Thus
001's statement that D invokes full producer validation is satisfied by D
calling this real C entrypoint and publishing that unchanged validated output.
D MUST NOT call the full A component validator again merely to satisfy that
wording. D checks the returned wrapper's closed shape, identity, exact saved
parameters, observed-sheet hash, and copy relationships before projection.
Builder output validation already performed by A likewise need not be repeated.
If an entrypoint stops guaranteeing full validation, it must be fixed at its
producer before publication, not compensated by a second scientific calculator
inside F or saved validation. A/B/C sources are outside D/F ownership.

Full producer validation and authenticated immutable publication carry geometry
validity. Saved-return validation performs exactly001's stored relationships,
including copied native cells, membership, ratios, saved interval cardinality,
supports, and source/parameter links. It does not derive coordinates from strings,
classify residues again, rediscover graph conflicts, or rerun native disjointness.

## Acyclic import and output graph

An arrow means “may import/use”; there is no reverse edge unless explicitly
identified as a local forwarding wrapper. Existing modules below are read-only.

| Layer | Owner/module | Allowed direct D/F dependency |
|---|---|---|
| 0 | F `bvbrc_proteome_directional_fact_contracts` | none; use unchanged legacy fact primitives and data-only schema definitions |
| 1 | D `bvbrc_proteome_bundle_v2_contracts` and its schema asset | F fact contracts, to check the canonical requested form and finite selectors |
| 2 | D `bvbrc_proteome_directional_saved_validation` | D v2 shape/parameter helpers and unchanged data-only native/schema helpers |
| 2 | D `bvbrc_proteome_numerical_sheet` | D v2 shape helpers; unchanged observation/schema helpers |
| 2 | D `bvbrc_proteome_bundle_v2_resolution` | D contracts/numerical-sheet modules; unchanged legacy resolution and real reader/A/C producer entrypoints |
| 3 | F `bvbrc_proteome_directional_projection` | F fact contracts; D contracts' saved-validation port; unchanged legacy projection primitives |
| 4 | D `bvbrc_proteome_bundle_adapter_v2` | D contracts/resolution plus F projection; compose construction, projection and final ABI |
| 5 | D host registry/publication ports | facade; F return binder is not imported by the provider |
| 5 | F return binder/tool information | D facade/contracts plus F projection/contracts; no reverse import into those modules |

F's fact-contract module must not import D v2 modules, F projection, the return
binder, native parser or calculator entrypoints. Its numerical schema constants
are copied/expanded from the unchanged accepted data definitions, not obtained
by evaluating a calculator. This lets D validate parameters and selectors before
F's projection implementation exists, using the real final schema module.

The required public `validate_saved_provider_v2` remains exported by D contracts.
It is a thin local-import forwarding wrapper to D's saved-validation module.
That module may call D's shape/parameter helpers, never the forwarding wrapper.
There is no top-level D-contracts→saved-module edge and no validation recursion.
F projection calls this port once per saved provider validation. F's finite
projection helper itself only consumes the already checked values. Its saved
projection validator invokes D checks, rebuilds the finite projection and compares
the exact saved facts; it does not recursively call its own saved validator.

The complete F projection signatures, making002's reference to the existing ABI
literal, are:

```python
def project_requested_facts_v2(sheet: dict | None, components: dict | None, *,
    missing_requirements: tuple[dict, ...], diagnostics: tuple[dict, ...],
    requested_form: dict, parameters: dict) -> dict: ...

def validate_saved_projection_v2(sheet: dict | None, components: dict | None, *,
    facts: dict, status: str, missing_requirements: tuple[dict, ...],
    diagnostics: tuple[dict, ...], requested_form: dict, parameters: dict,
    original_task: dict, bundle_sha256: str, bundle: dict | None = None) -> dict: ...
```

Both return exactly `{status,facts,missing_requirements,diagnostics}`; validation
returns detached values. `bundle=None` is not accepted on the authenticated
return path. It is only the inherited optional argument spelling. Projection
preserves provider requirements, deterministically appends current-field failures,
and rejects a saved requested-field failure that it cannot regenerate for this
exact form, as the existing v1 projection does. Thus repeated saved projection
does not accumulate duplicate requirements. Combined status is ok iff every
requested fact is available, otherwise partial; sheet=null gives invalid with
empty facts. Request-status/requirements facts remain available descriptors even
when reporting a precise unavailable requested value. If an unchanged legacy
request_status names a directional field, its tails copy that field's
`context.requirement_refs` and `context.qualification_refs`; legacy targets still
use their original top-level tails.

D resolution exposes a private construction result with sheet/components and
requirements/diagnostics. It never imports the facade or F projection. The facade
passes that result into F's real `project_requested_facts_v2`. There is no fallback
stub, temporary empty fact producer or import guarded into false success.
Each worker can independently test its assigned layer; the final facade and host
checks wait for the exact other exports named in003.

The facade's implementation digest includes the actual complete file/schema
closure of these imports and reused numerical/native/legacy primitives. It must
include both new F modules and the optional F static asset if used. No existing
v1 closure source is edited. Root owns composition of176 and the completed D/F
deltas into the designated candidate; neither worker edits frozen176/179.

## All fourteen source families and availability consumers

F exclusively owns the existing `bvbrc_proteome_returns.py` changes. It adds these
exact kinds→source suffixes alongside the unchanged eight legacy entries:

```text
directional_count          -> directional_counts
directional_fraction       -> directional_fractions
directional_coverage       -> directional_coverages
directional_native_integer -> directional_native_integers
directional_native_decimal -> directional_native_decimals
directional_state          -> directional_states
directional_extremum       -> directional_extrema
directional_intervals      -> directional_intervals
directional_columns        -> directional_columns
directional_edges          -> directional_edges
directional_conflicts      -> directional_conflicts
directional_support        -> directional_support
directional_issues         -> directional_issues
directional_requirements   -> directional_requirements
```

Every suffix has prefix `bvbrc_proteome_`. F updates `_FAMILIES`, `FACT_SOURCES`,
`_KINDS`, `proteome_fact_sources`, `requested_sources`, `_saved_facts`,
`project_proteome_facts`, `_values` and the semantic/schema dispatch used there.
`_owner` and current-publication selection accept the original selected version1
or2 and its exact configured pin; they do not accept version2 under a version1
pin. `_values` must apply each new family's full original semantic validator,
not only the broader parent-form translation. `_report_node` receives only
reviewed new numeric/reference shapes; legacy transformations stay unchanged.
The one new token namespace is `bvbrc_proteome_document`. This token is validated
against actual requested facts; it is not an invented Store source.

F verifies every family through the following actual consumers. All are dynamic
once176 is composed; extra production edits outside F's existing ownership are
not required:

| Actual consumer | What must work for all fourteen sources |
|---|---|
| `ExecutionEpisodes._appservice_sources` → `fact_sources` | complete source descriptors and exact closed report schemas |
| `ExecutionEpisodes.received_report_sources` | same definitions available to scientific/annotation receivers |
| `EpisodeBindingRegistry.received_report_sources` → `Workflow.report_sources` → runtime `_compile_form` | available top-level x-source and correct array type; no new global source whitelist |
| `BVBRCAppServiceHost.facts` → `BVBRCProteomeReturns.facts` | actual results owner, newest selected original publication, requested families only |
| `ExecutionEpisodes.facts` → `APIServiceExecution.facts` | same child-owned facts reach the existing execution path |
| `BVBRCProteomeReturns._values/_frozen/_validate_historical` | full original fact semantics, duplicate field rejection, saved/frozen equality |
| `ExecutionEpisodes.validate_received_report/received_form_references` | original commission/form, immutable original publication and possession before admission |
| `BVBRCProteomeReturns.received_context/received_facts` → `ExecutionEpisodes.received_report_facts` | only admitted actual rows forwarded; no current-publication substitution into history |
| `APIServiceExecution.resolve` and `ExecutionEpisodes.resolve/resolve_received_reference` | actual source custody and finite internal namespace values;178 synchronous reuse only |

F's episode-path test must exercise this full chain, including the role-specific
availability/compilation step, for the new families. An isolated call to
`proteome_fact_sources` is insufficient. `runtime.py`, `episode_bindings.py`,
`communication.py`, `form_reference_validation.py`, host API binding and prompt
templates remain read-only; if the complete composed path reveals an actual
missing consumer, report its exact call and required change before expanding
ownership. Existing003 ownership stands, with this consumer coverage explicit.

## Exact scoped publication and read predicates

D exclusively implements these ports in `bvbrc_appservice_publication.py`.
Use the same pure predicate for publish and authenticated read:

```text
native_usable = any(member.transfer.body_complete is true
                    and member.transfer.object_complete == "yes"
                    for member in bundle.artifacts)
directional_saved =
    selected (adapter_id,adapter_version) == ("bvbrc_proteome","2")
    and adapter_result is not null
    and adapter_result identity equals that selected identity
    and adapter_result.status in {"ok","partial"}
    and adapter_result.sheet_content is not null
expected_result_refs = [bundle_content.source_ref]
                       if native_usable or directional_saved else []
```

The directional exception requires an actual saved sheet ContentBinding from
the authenticated pinned adapter publication. It does not require components
to be available: a retained valid failure/partial sheet can supply requested
states and precise unavailable fields. It grants no complete-download claim.
The native-usable branch remains unchanged for all old adapters. A global-invalid
v2 adapter without a sheet does not qualify for the new exception.

For exact2 only, `_grade` invokes the facade's selector cross-validator before
consume_bundle. `_requested_status` adds exact2 to the existing set whose adapter
status can distinguish irrelevant retained requirements from failures of the
requested projection. Bundle status continues to determine acquisition
completeness. In particular bundle.partial cannot yield requested_form_status
satisfied even if an available requested prefix fact exists. The expected
outcome status is completed iff requested_form_status is satisfied, else partial.
Completion proof is the existing exact practical-completion object iff status
is satisfied; otherwise null. No scientific-completion interpretation is added.

In `read`, after authenticating source, original owner, immutable publication,
inputs, original selection, acquisitions, exact rebuilt bundle, pin and contents:

1. Recompute the predicate above and compare the entire result_record_refs list.
2. Recompute `_requested_status` and its exact missing-requirement array, as now.
3. For exact2 require proof presence iff status satisfied, then apply the existing
   exact proof identity/assignment/receipt-hash check. Compare saved outcome
   status to the expected completed/partial status.
4. Preserve the existing exact outcome/publication/ref equality checks. Loading
   contents authenticates bytes; F subsequently validates their finite relations.

`own_results` reads those actual refs. `completion` adds exact2 to the existing
newest-publication branch. A latest failed/unusable or partial publication cannot
revive an earlier completion proof. `BVBRCProteomeReturns.facts` applies the same
newest-publication rule to both versions. Historical admitted return rows still
authenticate their named original source, even if a newer partial exists.

Recovery that finds `scientific_adapter_result.json` uses that immutable exact
result. It performs no parser, builder, calculator, request or process action.
The extra result reference is not an acquisition, credit event or completion
observation. Missing roster/producer/row-to-HSP evidence stays missing.

## Remaining deterministic projection detail

For002 report-level numerical issue pages, concatenate in this order: the exact
selected `C[R].diagnostics` array, the directional observed-sheet diagnostics
that reference this report, then the directional components-root diagnostics
that reference this report. Preserve native array order within each. Identity is
the original saved issue reference, not equal issue text; retain distinct source
references once each. Equal diagnostics at different saved array positions have
different references and remain distinct; do not infer unsaved propagation
lineage or call them independent evidence. Include a root issue only if its report key or FieldRef
names this report; unscoped global failures remain provider requirements and do
not manufacture per-report evidence. All other issue pages preserve their exact
scope's saved array order. Page boundaries therefore remain replay-stable.

Tool-library changes describe actual selected calls and these return meanings.
Parent TASK/STEERING presentation is separate and unassigned. No model prompt
rewrite, new grader episode, LLM restatement or general validator widening is
part of D/F.
