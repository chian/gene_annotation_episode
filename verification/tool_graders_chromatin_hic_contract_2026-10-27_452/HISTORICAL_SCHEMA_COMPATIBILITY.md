# Narrow historical-form compatibility amendment

This is a proposed boundary, not an implemented migration or reproduced runtime
regression. Root identified the exact comparison. 452 read the complete
communication, chromatin return-view and return-authority modules, the relevant
receipt/host validation paths and existing return-view tests. Bounded schema001
decoded the production literal and traversed references without importing a
scientific production module. Its original handle, source/interpreter pins and
terminal/quiescent exit0 remain. Earlier infrastructure-launch failures are
retained in SCHEMA_LAUNCH_FAILURES.md.

## Precisely affected schemas

`chromatin_record_schema` includes the transitive `$defs` closure of its root.
`_array_schema` embeds that closure, modifies saved identity constraints and
derives `$id` from the full schema before `$id` is added.
`communication._compile_closed_schema` currently requires canonical-JSON equality
with the single current registered field schema. A reachable additive enum or
variant therefore changes acceptance of frozen forms even when old values still
validate. This is a confirmed static implication, not an executed regression.

| Source | Exact closure before export customization | Effect of the proposed HIC additions |
|---|---|---|
| chromatin_interaction_projection | BooleanComponent, CalculationParameters, ContactParameters, Failure, InsulationParameters, Locator, Measurement, NormalizationSpec, PageResult, ProjectionContactPairsRow, ProjectionDistanceExpectationsRow, ProjectionDomainsRow, ProjectionInsulationWindowsRow, ProjectionPopulationMetricsRow, RequestedProjection, RowQualifications, UncertaintyNotMeasured, Unit | Failure/Locator change this field schema and its `$id`. The path is RequestedProjection → Failure → Locator. |
| chromatin_interaction_failures | Failure, Locator | Both proposed changes alter this field schema and its `$id`. |
| chromatin_interaction_saved_sheets | NativeFileIdentity, SavedSheetBundle | Export adds ChromatinSavedSheetIdentity. NativeMetadata, PopulationReadEvidence, Locator, Failure and SoftwareBinding are unreachable. Keep this exact exported schema and `$id` unchanged. |

`schema001/SCHEMA_REACHABILITY.json` retains full edges and source hashes. The three
`schema001/*.static_schema.json` files retain the complete pre-change field trees,
including `$id`, `$defs` and `x-source`, mechanically constructed from the actual
unmodified literal using the inspected export/digest algorithm. They are static
source evidence, not production-call output. Before installing legacy literals,
compare them with actual pre-change exports or already recorded forms under the
same pinned sources. A claimed `$id` alone never authorizes a schema.

The mechanically derived original ID suffixes are:

* projection: `1ba0f49fee68561bf3ce14354a05629212dcb55256d129862a96533396805447`;
* failures: `ae45a8a267c4d93d704f92b33e8bf5c903a1e3e70e7042c15b5dafc37318b4c8`;
* saved sheets: `3c59bfb40181590201fe697182de4b5606df0f033a245fb3ca7b205179174f1b`.

## Unchanged value semantics and alternatives

No existing Cooler return relationship check needs to change. RequestedProjection
checks population membership, exact requested fields, component/row joins, page
cardinality and nested BooleanComponent state/value consistency. Failure has no
additional `_relationships` branch. SavedSheetBundle uses existing identity,
artifact digest and sheet/table format checks. Keep these checks unchanged.
New HIC header/block rules apply to extraction and sheet records outside these
return-schema closures.

| Alternative | Assessment |
|---|---|
| Exact frozen legacy projection/failure schemas beside current schemas, with unchanged value checks | Recommended narrow proposal. Preserves original forms and their own value constraints. Saved-sheet schema stays identical. |
| New HIC fact-source names and duplicate projection records | Requires extra source dispatch, receipt and ownership joins despite shared numerical semantics. No scientific need for this duplication was established. |
| Generic schema registry or historical semantic-validator framework | Unnecessary here because old value semantics do not change. Do not add arbitrary registration or a revision system to this workload. |

## Recommended compatibility contract

1. Freeze the two complete pre-change field schemas as reviewed immutable
   production literals, preserving original `$id`, scalar types, `$defs`,
   reference annotations and provenance. Do not derive legacy trees by removing
   selected fields from current schemas. Do not modify old schema_json,
   report-contract, form, facts, receipts, prefixes or artifacts. Workflow451
   continues on its frozen source and forms.
2. Add only a narrow detached helper:
   `chromatin_fact_schema_alternatives(source: str) -> tuple[dict, ...]`.
   Projection/failures return current and the one known exact legacy schema,
   deduplicated if equal. Saved sheets return the unchanged current schema.
   Unknown sources fail. There is no caller-provided revision, arbitrary schema
   registration or runtime dependency on a verification packet.
   `chromatin_fact_sources()` retains its signature and exports current schemas
   for new parent choices.
3. `_compile_closed_schema` keeps existing top-level, finite-JSON and exact
   canonical-JSON comparison requirements, comparing chromatin fields to those
   finite explicit alternatives. Do not accept by source, `$id`, digest claim,
   subset or payload compatibility alone. Altering an old tree while keeping its
   old `$id` still fails.
4. Keep `validate_chromatin_fact_values(source, value)` and the old relationship
   checks unchanged. Current additive record schemas may accept both old and new
   values. `_validate_form` already additionally validates against the original
   recorded field schema; retain that check. New hic_bytes/hic_vector locators or
   HIC-only failure codes must fail in legacy fields even when current record
   validation accepts them. Existing old hic_block values remain allowed.
5. Keep `select_chromatin_return_facts(groups, *, schema)`'s signature; validate
   every requested field against its exact accepted field schema as well as
   shared semantic checks. Current source-only validation is insufficient by
   itself. Check every repeated source field under its own tree. Preserve values
   and order; report incompatibility without dropping fields, substituting
   failures, recalculating or rewriting the parent's form.
6. `ChromatinInteractionReturns._values` already validates the original form
   before source checks. `_own_facts`, saved-bundle authentication, result receipt
   validation and the result host can retain unchanged shared value checks.
   Regression-test their actual paths; do not preemptively thread revision
   arguments through them. Historical delivery uses recorded forms/receipts,
   never reopened native inputs. A new receiving form may accept exact old facts
   only if its own schema and existing custody checks permit them.

This finite two-schema compatibility change does not loosen the generic grammar,
change scientific calculations, add a runtime gate or rewrite closed history.

## Exclusive files and handoffs

Root retains H2/H3 ownership until explicit reassignment, as its handoff014
records. H2 supplies the additive Failure/Locator diff while preserving existing
return relationship checks. H5 is a small separate boundary, assignable to root,
owning only:

* new `gene_annotation_episode/chromatin_interaction_legacy_return_schemas.py`;
* `gene_annotation_episode/chromatin_interaction_return_views.py`;
* the chromatin branch of `gene_annotation_episode/communication.py`;
* `tests/test_chromatin_interaction_return_views.py` and new
  `tests/test_chromatin_hic_return_schema_compatibility.py`;
* regression additions in `tests/test_chromatin_interaction_returns.py` and
  `tests/test_chromatin_interaction_result_receipts.py`.

No production return-authority, receipt, result-host or generic episode-record
module edit is currently needed. An actual regression must establish any further
change before root reallocates ownership. H4 retains the assembled HIC workflow
test and located C2 diagnostic; other owners do not concurrently edit H5 files.

## Required verification

Before the H2 diff, retain/compare all three actual exported schemas and actual
old Cooler form/receipt examples under pinned source. After the diff verify:

* Exact old projection/failure schemas and old values still compile and validate;
  current HIC schemas/new values pass. Saved-sheet canonical schema and `$id` are
  byte-identical to the retained baseline.
* Direct failures and failures nested in projections reject HIC-only codes or
  new locators under old schemas and accept them under current schemas. Existing
  old hic_block values still pass. No old field is expanded in place.
* Forged IDs, changed definitions under old IDs, omitted reference constraints,
  weakened additionalProperties, unknown enums and scalar-type changes fail.
  Repeated source fields are each checked against their own complete tree.
* Population/field/page/Boolean relationships and artifact identity, foreign
  receipt and unreceived-bundle rejection remain unchanged. Shape acceptance
  never establishes possession or origin.
* Replay an actual frozen Cooler form through `_historical`, `_received`, closure
  prefix and saved-bundle authentication with original contract/form/fact/receipt
  hashes unchanged. No native read, network or recalculation occurs in historical
  delivery; saved-sheet recalculation remains a separate selected action.

These tests remain unexecuted here. Run them through the required bounded
lifecycle. Schema001 proves static reachability and retained schema/source facts,
not compatibility implementation or a production-test pass.

Final additive baseline verification: root explicitly requested the actual
export check before modifying contracts. Bounded schema002 used `.venv/bin/python`
to call current `chromatin_fact_sources()` and compare all three full field trees
against schema001's static trees. All three canonical-JSON comparisons passed.
`schema002/ACTUAL_EXPORTS.json` retains the complete callable return;
`schema002/*.actual_schema.json` retain the complete individual field trees;
`ACTUAL_EXPORT_CHECK.json` retains comparisons, exact IDs/hashes and imported file
pins. All source and interpreter pins remained unchanged. The original lifecycle
receipt records terminal/quiescent exit0, 20GiB RAM, 4GiB monitored scratch, zero
swap, no wall limit, elapsed0.638025146s and observed scratch794624bytes. Root may
use these exact pre-change trees as reviewed static production data, without a
runtime dependency on this packet. Changed-schema regression and history replay
tests remain unexecuted.
