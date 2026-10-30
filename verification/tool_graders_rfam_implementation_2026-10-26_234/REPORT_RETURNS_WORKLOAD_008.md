# Rfam native-report publication and requested returns

Fresh worker244 owns `rfam_batch_publication.py`, `rfam_batch_returns.py`, NEW
`tests/test_rfam_report_publication_returns.py`, and verification ending244.
Existing publication/return tests belong to root and remain unchanged. Root
owns selectors, API service, execution wiring, descriptors and final integration.
Worker242 owns all report numerical modules and the factored geometry.

Read original immutable goal, AGENTS, complete PUBLICATION003/RETURNS004 and
REPORT006 contracts and full current publisher/return paths before changes.
Repeat original objective/all16 principles VERBATIM after substantial source/
native examination and at closure; do not paraphrase that reset.

## Exact selected input and pure dependencies

Root is adding `rfam_batch_result_selector_v3`, which has the same fields as
previous selectors but requires representation `out`, model_metadata_ref=null,
and nullable report projection. It requires sequence_batch request v2; no guess
about an old single-sequence submission's generated name. Older v1/v2 selections
retain their original behavior, including artifact-only old report selections.

Worker242 exports types/constants in `rfam_batch_report_contracts.py` (present):
RfamBatchReportParseResult, RfamBatchReportSheet, RfamBatchReportCalculation,
REPORT_FORMAT, REPORT_PARSE_VERSION, REPORT_SHEET_VERSION,
REPORT_CALCULATION_VERSION, RFAM_REPORT_ISSUE_CODES,
RFAM_REPORT_MISSING_REASONS, RFAM_REPORT_METRICS, RFAM_REPORT_METRIC_UNITS,
RFAM_REPORT_PROJECTION_SCHEMA, validate_rfam_report_projection(value),
validate_rfam_report_sheet(sheet),
validate_rfam_report_calculation(calculation, *, sheet).
The last two are pure structural/association checks without parsing/calculation.

Numerical dependencies have these frozen signatures:
populate_rfam_batch_report_sheet(content, *, input_identity, capture, submitted_content)
calculate_rfam_batch_report_components(sheet, *, parameters)
project_rfam_batch_report_result(sheet, calculation, *, projection, artifact_bindings)
Capture uses the existing batch-table capture with representation out. Parameters
are the existing explicit RFAM_CALCULATION_PARAMETERS. Projection is the existing
compact envelope with `model_name` additionally present on each row; accession
is separately nullable. It does not manufacture an accession from a model name.

## Publication

Add the report branch only for v3. Retain the same original submission, native
response and derived grading sources, canonical parse/sheet/calculation artifacts,
manifest fields, original selector/assignment and acquisition receipt. No new
acquisition or source lookup occurs inside parsing/calculation. All report bytes
are retained. Numeric projection may contain known native cells and explicit
unavailable cells; missing model coverage is no acceptance gate. Incomplete body,
invalid identity, wrong job/query/file and unsupported requested projection remain
specific partial/failed results while valid partial native facts survive.

Do not call the JSON parser, infer an RF accession, or treat report line positions
as JSON pointers. Map report issues using their closed code/severity/field/
native_query_name/source_line meanings; preserve their specific diagnostic codes.
The publisher must preserve exact original operation replay and reject conflicting
reuse. Existing metadata scope repairs and old native/scalar behavior remain.

## Return boundary

Keep `rfam_result_rows` and `rfam_result_populations` unchanged for old formats.
Add one FACT_SOURCES entry `rfam_report_rows`, a closed array of the same row
fields as rfam_result_rows PLUS nullable `model_name`. Its metric/unit/reason
enums use the report contract. source_ref/record_key/query_occurrence_key/
family_accession keep their current namespaces. model_name is a nullable
identifier in new `rfam_model` namespace. Strand remains +|-|null.
Report population facts use existing rfam_result_populations with identical
meanings. No empty fake hit row is required for a complete zero-hit report.

Choose row facts from the authenticated manifest's actual format, not a guessed
value or a source-provider scan. Do not silently broaden old row forms. Preserve
the original projection and original requested fact families. Report return
authentication validates original raw response/submission identity, exact frozen
v3 selector, complete parse/sheet/calculation/manifest bindings and source hashes,
and recomputes only the requested view of already calculated values. It may not
parse again or recalculate numerical scores. New report identities resolve only
from original own requested projection or actually admitted child forms.

Extend existing immediate-parent results->scientific_process->annotation
validation/admission/forwarding to this third family. Existing parent/owner,
commission, scope, frozen-form and redelivery checks remain. No source-only form
or unrequested report field grants access to additional rows or model identifiers.
Root will connect the new rfam_model namespace in shared API/execution resolvers.

## Verification

Use actual selected API receipts and real Store, controlled retained report
responses and explicitly marked generated-header variants. Do not submit jobs.
Verify scalar/gap/correspondence values, nullable accession and denominator,
complete-empty/partial/malformed cases, selected row limits, foreign identity,
projection/manifest tampering, source-only restriction, both forwarding boundaries
and exact old v1/v2 behavior. Replays/return reads must forbid transport, parser,
calculator and model calls. No extra action/observation/credit.

Run dedicated new tests with20GiB RAM/4GiB scratch/no wall-time cap, source hashes
and retained failed attempts. Notify242 of a concrete interface mismatch; root
resolves shared-selector/wiring defects. Report exact qualified verification and
remaining full Workflow evidence; do not claim live or complete-goal completion.
