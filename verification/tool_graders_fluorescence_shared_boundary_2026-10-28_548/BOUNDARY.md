# Shared supplied-fluorescence boundary, 2026-10-28, review 548

This is a source-to-calculation ownership contract for review, not a new goal,
scope amendment, implemented operation, prompt template, or completion claim.
The authoritative supplied goal was read in full from the attachment identified
by the parent. Its objective and all ten operating principles were reread during
the work. This lane changes only this verification directory.

Exactly two inventoried operations are mapped:

| Inventory key | Common analysis | Proposed common numerical authority |
| --- | --- | --- |
| `biomni.tool.cell_biology.perform_facs_cell_sorting` | Apply explicitly selected one-channel thresholds to supplied event measurements; retain membership and selected intensity statistics | `fluorescence_event_population_sheet_v1`; `fluorescence_event_calculations.calculate_fluorescence_sheet` |
| `biomni.tool.immunology.analyze_cytokine_production_in_cd4_tcells` | Apply explicitly selected parent and marker gates to supplied event measurements; calculate conditional marker fractions and explicitly paired control differences | **The same sheet and calculator**, including the same gate, count, fraction, mean/median and difference functions |

These are molecular-measurement analyses, not physical cell sorting, instrument
control, clinical interpretation, inferred cell identity, or gene-function
confidence. A CD4-channel threshold alone does not establish a complete cell
classification. Gene/analyte associations must be supplied with their provenance.

## Actual inspected source and present status

`source-audit.json` records exact file and function hashes and anchors.
`native-functions.txt` retains both complete source functions, with line numbers.
Function hashes cover the full source lines, including a final newline.

| Source function | Complete anchor | Function-lines SHA256 |
| --- | --- | --- |
| FACS | `reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/cell_biology.py:369–470` | `c400891a22aa723c1fb8d42cce9f2c7b9a8241f9a8c16467780c7c2b6e138fb7` |
| Cytokine | `reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/immunology.py:1178–1328` | `9d4f5b14cdd5337b4b807dfbe04790a164501ad6bad6fb270bdb6937c0a7a6ba` |

The two fixed inventory rows both currently mark tool information, sheet,
readers, calculators, result binding and verification pending. They were read,
not edited. The current `knowledge/index.json` and manual search contain no
descriptor for either operation and no fluorescence-event analysis manual.
`knowledge/source-tables.md` describes retained archive/XLSX access; it does not
declare an FCS decoder or a complete CSV event-acquisition path. Existing NMF
local operation information was also read as a transport example.

| Native behavior actually in source | Consequence for the new boundary |
| --- | --- |
| FACS accepts CSV, an assumed DataFrame, or FCS through `flowkit.Sample(...).get_dataframe()`. If importing FlowKit fails, it attempts `pandas.read_csv` on the FCS path. | Format must be declared and validated. No FCS-to-CSV fallback or filename-based scientific compatibility. An in-memory table requires an immutable supplied-table artifact and original positional identity before calculation. |
| FACS filters `>= threshold_min`, then `<= threshold_max`; both thresholds may be absent. | Preserve each bound and inclusivity. No automatic threshold. A pass-all selection is explicit. Invalid/inverted bounds are a located request error, not a biological zero. |
| FACS reports `100 * selected/original` as “Enrichment percentage”, with zero for an empty original table. | Name the calculated quantity selected-event fraction/percent. It is not an enrichment fold, purity, recovery, or sorting efficiency. Empty denominator is unavailable. Preserve the native label/value separately. |
| FACS emits only a prose log and selected CSV; `to_csv(index=False)` drops the original index. Mean/median and percent in the log use two decimal places. | Retain original full input, computed membership ordinals and explicit gate request. Do not reconstruct event identity by joining selected values, especially with duplicates. Native rounded values are separate from calculated values. |
| Cytokine input is a condition-to-FCS-path dictionary. The four example condition names generate warnings if absent; no biological replicate dimension exists. | Use positional sample records plus explicit condition, replicate and control associations. Do not make those four names mandatory conditions or infer that equal labels identify equal samples. |
| `sample.compensate()` is attempted; **every** exception is described as no matrix, and processing continues on the original sample. | Preserve actual compensation status, matrix/method if used, input and resulting measurement domains, and the actual failure. Do not infer matrix absence from a catch-all failure or silently accept raw values for a compensated-domain gate. |
| A comment says transform, but no transform call occurs. The first channel containing `CD4` is selected; every channel containing `IFN` or `IL-17` is selected. IFN takes precedence if both substrings occur; repeated matching channels overwrite the same cytokine dictionary entry. | Exact channel positions/native identifiers and explicit supplied analyte mapping are required. No first-match, substring identification or overwrite. Preserve reported native labels only as source labels. Transformation status comes from actual data/provenance, not the comment. |
| Cytokine uses `CD4 > 1000` then marker `> 500`, using string expressions passed to `.gate()`. It emits marker/CD4 percent, or zero if CD4 is empty. | These constants are native implementation facts, never defaults for a new dataset. Require selected finite bounds and operators in the correct domain. The installed API's compatibility with the string gate calls remains unverified. |
| Cytokine subtracts the `unstimulated` percent and clips negative differences to zero; saves `cytokine_frequencies.csv` plus rounded log/table text. Original parent/marker membership and exact marker counts are not emitted. | Require explicit control pairing. Preserve the signed difference and native clipped report separately; do not recover counts from rounded percentages. Retain full events and membership for recalculation. |
| Missing cytokine channels skip a condition; gate errors can omit the condition; missing FlowCytometryTools import or a file-load error can abort outside the inner catch. | Preserve condition-level partial success and located failures. Import/read failure does not create zero measurements. A research log is not a validated measurement bundle. |

No native function was imported or invoked. Static package-entry inspection of
the reference environment identifies pandas but no FlowKit,
FlowCytometryTools, flowio or fcsparser package entry. This is not a deployment
test and does not establish the availability of another environment/resource.
No installation, model call, remote job or scientific execution occurred.

## Existing numerical reuse decision

The narrow production search excludes literature modules and looks for both
exact operation names and fluorescence/cytometry/event-gating terms. It finds
no existing scientific event-gating sheet/calculator. The inspected nearby
calculators are not equivalent analyses:

| Existing implementation inspected | Existing meaning | Reuse decision |
| --- | --- | --- |
| `bvbrc_data_calculators.calculate_facet_fractions` | Bucket document count / exact same-response Solr population; service/transport/population qualification | Preserve its existing implementation. Do not adapt fluorescence events into Solr documents or copy its scientific contract. |
| `expression_nmf_calculations.calculate_nmf_sheet`, `component_measurements`, `residual_measurements` | Fitted factor contributions and expression reconstruction residuals | No NMF numerical reuse; its factor/sample population has different meaning. |
| `atac_differential_calculations` and its interval component calls | Genomic track partitioning, likelihood components and regions | No ATAC numerical reuse; interval spans/likelihoods are not event frequencies. |
| `numerical.py` | Episode yield estimation/controller | Not a scientific-measurement calculator; unchanged. |

The demonstrated missing numerical work is therefore **one** common event-gate
calculator for these two wrappers, not two graders. Standard arithmetic helpers
do not justify importing another analysis's schema. Future aliases performing
this same analysis must feed this exact sheet and calculator. Literature
graders and W05 are not part of this work.

## Exact input and saved-sheet boundary

Proposed type names below describe future contracts; none is currently bound.
Closed schemas reject unknown fields and nonfinite JSON numbers. Restricted
labels preserve exact source names; they carry no unrestricted findings or
instructions. Locations/hashes remain host data, not model prompt text.

`FluorescenceEventSheetV1` has `schema`, `input_sources`, `samples`, `channels`,
`measurement_domains`, `events`, `population_definitions`, `gate_definitions`,
`control_pairs`, `native_reports`, `issues`. Its populated numerical cells are
the full event measurements and declared threshold values, not a claims table.
Calculated membership, counts, fractions and intensity statistics are retained
in `FluorescenceComponentsV1`, bound to that exact sheet and parameter snapshot.

| Shared field group | Required meaning and association |
| --- | --- |
| `input_sources[]` | Complete retained original bytes (`NativeFileIdentity`: artifact, digest, size, declared format), selected FCS dataset position or CSV dialect/header record, complete/partial/unknown extent, parser/version, native declared totals separately from decoded totals. Original bytes are never replaced by the sorted CSV or log. |
| `samples[]` | Original sample occurrence; source/dataset binding; supplied sample/condition/biological-replicate/technical-replicate identifiers or explicit unknowns; supplied gene/analyte/reference associations. Duplicate labels remain distinct occurrences. |
| `channels[]` | Original parameter/column ordinal and exact native names. FCS keyword metadata including parameter names, labels, ranges/scaling information remains retained. CSV duplicate headers require positional selection. Marker identity is an explicit association, not inferred from a header. |
| `measurement_domains[]` | Domain ID, exact channels/order, native physical/scale units or explicit unknown units, acquisition/preparation provenance, compensation state and transform state, original and prepared source identities. Compensation states distinguish explicitly uncorrected, known applied, failed, unknown; transformation distinguishes explicit none, known applied, unknown. Applied operations require actual method, parameters, channel mapping and matrix/artifact where applicable. |
| `events[]` | `(source occurrence, dataset position, event ordinal)` identity; CSV original record/line/byte location or FCS DATA event location where available; exact decoded channel values and per-value state (`observed`, `missing`, `invalid`, `unavailable`), raw lexical values when textual. Ordinals are zero-based native record occurrences before filtering. Malformed rows retain their ordinal and failure; no renumbering after rejection. |
| `population_definitions[]` | Explicit complete-source population or explicitly selected subset, and parent population links. A truncated read cannot masquerade as a complete source or become an implicit chosen subset. Do not assume singlet, viable-cell or other unperformed gates. |
| `gate_definitions[]` | Gate ID, parent population, exact channel occurrence/domain, lower/upper finite bounds with independent inclusive/exclusive flags; explicit absent bound; or explicit pass-all. Gates form an acyclic parent-linked definition. FACS maps to one gate; cytokine maps to a supplied parent gate plus supplied marker gate(s). |
| `control_pairs[]` | Explicit target sample/marker-population and control sample/marker-population IDs, denominator basis, condition/replicate relationship, and supplied comparison-definition correspondence. Same analyte and compatible gate/domain meanings must be demonstrated. No auto-pairing by condition name, order or filename. |
| `native_reports[]` | Original artifact and native row/column/text location, native quantity label, value token, parsed numeric value if valid, units/population/denominator if actually known, and explicit rounding/truncation metadata. Native and calculated values are distinct even when they agree. |
| `issues[]` | Closed code/stage enums and exact sample/channel/event/gate/control/source locators. Raw errors may stay in retained logs; model-facing failure fields are constrained. Valid independent samples/populations remain usable. |

The FCS reader decodes supplied events; it does not choose compensation or a
transform. If calculation is requested in an applied domain, the required input
is the complete prepared event array **with event-by-event correspondence to
the original array and actual method/matrix/transform provenance**. If that
output is not available, return `measurement_domain_unavailable` for affected
gates. Source discovery does not establish a compensation API or logicle
implementation. Such a requested preparation remains explicitly unfinished;
there is no hidden fallback to raw or guessed preprocessing. An explicitly
selected uncorrected domain can be used as such. Unknown physical units do not
prevent counts in a documented identical instrument domain, but do prevent
unit/calibration transfer or physical concentration claims.

## Numerical components, units and missing-input rules

All entries carry sample/population/gate/channel/measurement-domain references
as applicable, `value`, `state`, `reason`, and explicit operand references. Counts
are integer event counts. Calculated numbers are derived descriptive measurements;
native events are observed (or retain a supplied predicted/synthetic origin).
No uncertainty is inferred. Supplied measurement uncertainty can be retained
with method and units; no event-level standard error, confidence interval,
replicate precision or gene-function probability is invented.

For one gate, let `P` be its confirmed parent event set, `E` the members whose
required gate-channel values are finite/valid, `S` the true gate members, `F`
the false members, and `U = P − E` the undecidable members. Preserve the exact
ordinal sets, not just their lengths. Thus `S ∪ F = E`, `S ∩ F = ∅` and
`|P| = |S| + |F| + |U|`. Parent-membership uncertainty is separately retained;
it must not be silently dropped before evaluating a descendant's denominator.
A known-false ancestor excludes an event; a true ancestor plus unknown gate
value leaves membership unknown. Unknown ancestry remains unknown unless a
supplied predicate conclusively excludes the event. There is no implicit
imputation, gate adjustment, complete-case choice or cross-sample pooling.

| Component | Calculation and population | Unit / denominator / unavailable behavior |
| --- | --- | --- |
| `retained_event_count` | Count every retained original event record, including located invalid records | events; no denominator. Native declared count remains separate; incomplete unparsed tail count stays unknown. |
| `parent_event_count` and `parent_unknown_count` | Counts of confirmed and undecidable parent members | events; a count of confirmed members is marked lower-bound when the parent membership is incomplete. It is not an exact denominator in that case. |
| `evaluable_event_count`, `selected_event_count`, `rejected_event_count`, `unknown_gate_event_count` | `|E|`, `|S|`, `|F|`, `|U|`, with exact membership sets and count exactness | events. Missing channel values are unknown, not false or zero. An entirely missing source is unavailable, not an empty table. |
| `selected_fraction` | `|S| / |P|` only for a complete declared population with exact parent membership and no undecidable gate members | dimensionless, denominator `|P|`; null `empty_parent_population` for zero denominator; null `unknown_gate_membership` or `incomplete_population` when membership/source is incomplete. |
| `selected_percent` | `100 * selected_fraction`, using the same calculated fraction | percent; same population/denominator/state. This is a shared calculated alias, not another publisher calculation. |
| `evaluable_fraction`, `evaluable_percent` | Optional **explicitly requested** `|S| / |E|` and `100 * fraction` for the finite-valued subset of a known complete parent | dimensionless / percent, denominator `|E|`; retain excluded event ordinals and missing counts. Empty evaluable set => null. Unknown parent membership or truncated source => unavailable. Never publish this as the full-parent fraction. |
| `selected_intensity_count`, `selected_intensity_missing_count` | Finite observed selected values and the remaining selected values for the requested channel | events. If selected membership is uncertain, these describe confirmed-selected events only and must be qualified as such. |
| `selected_intensity_mean` | Sum of the requested finite selected values divided by their count; retain sum/count | original declared measurement-domain unit, denominator finite selected count; null for zero finite values or numerical overflow. Explicit finite-value subset and missing count accompany it. |
| `selected_intensity_median` | Middle ordered finite selected value; average of the central two for an even count | same unit and finite-value subset; retain count; null for empty or unrepresentable arithmetic. No log/geometric mean substituted. |
| `control_difference_fraction` | Explicit paired target fraction minus control fraction | dimensionless; retain both numerators and denominators. Null if either fraction unavailable or comparison meanings incompatible. Separate samples are not pooled. |
| `control_difference_percentage_points` | `100 * control_difference_fraction` | percentage points, signed, not percent change or fold change. Negative values are retained. |
| `native_minus_calculated` | Optional comparison of a native numeric report to the exact matching calculated component | native component units; both values/identities and formatting metadata retained. No equality tolerance is guessed from display text. Explicit `.2f` source formatting may establish agreement at that reported precision. |

The native clipped background-subtracted percentage is retained as a reported
quantity. If a receiver explicitly requests reproduction of that legacy derived
quantity, the **same common calculator** can expose separately named
`legacy_nonnegative_difference_percentage_points = max(0, signed_difference)`
with its clipping parameter and provenance. It never overwrites the signed
difference. Native zero with an empty denominator remains a conflicting native
report, not a valid calculated zero. Counts cannot be recovered by inverting
rounded percentages. Neither selected-event fraction nor intensity mean becomes
an annotation score.

## Callable boundaries for later coding

These are proposed Python signatures, not installed functions. Type definitions
and validators are owned once by the sheet/calculation owner.

```python
# Pure format readers: bytes supplied by the owning acquisition/result action.
parse_fluorescence_csv(raw: bytes, *, source: NativeFileIdentity,
    format_spec: CsvEventFormat, sample: SampleMetadata,
    channels: tuple[ChannelBinding, ...], domain: MeasurementDomain) -> EventParseResult
parse_fluorescence_fcs(raw: bytes, *, source: NativeFileIdentity,
    dataset_position: int, decoder_profile: FcsDecoderProfile,
    sample: SampleMetadata, channels: tuple[ChannelBinding, ...],
    domain: MeasurementDomain) -> EventParseResult
parse_fluorescence_table_snapshot(raw: bytes, *, source: NativeFileIdentity,
    snapshot_profile: FrozenTableProfile, sample: SampleMetadata,
    channels: tuple[ChannelBinding, ...], domain: MeasurementDomain) -> EventParseResult
parse_fluorescence_native_reports(raw: bytes, *, source: NativeFileIdentity,
    report_profile: NativeReportProfile, supplied_links: NativeReportLinks) -> NativeReportParseResult

# One sheet builder/validator; reader failures and valid events survive together.
populate_fluorescence_sheet(parsed: tuple[EventParseResult, ...], *,
    populations: tuple[PopulationDefinition, ...], gates: tuple[GateDefinition, ...],
    control_pairs: tuple[ControlPair, ...],
    native_reports: tuple[NativeReport, ...]) -> FluorescenceEventSheetV1
validate_fluorescence_sheet(sheet: FluorescenceEventSheetV1) -> FluorescenceEventSheetV1

# One numerical owner, called identically by both operation adapters.
evaluate_gate_membership(sheet: FluorescenceEventSheetV1) -> GateMembershipComponents
calculate_population_fractions(membership: GateMembershipComponents, *,
    denominator_requests: tuple[DenominatorRequest, ...]) -> PopulationFractionComponents
calculate_population_intensities(sheet: FluorescenceEventSheetV1,
    membership: GateMembershipComponents, *,
    requests: tuple[IntensityRequest, ...]) -> IntensityComponents
calculate_control_differences(fractions: PopulationFractionComponents, *,
    pairs: tuple[ControlPair, ...], include_legacy_clipping: bool) -> ControlDifferenceComponents
calculate_fluorescence_sheet(sheet: FluorescenceEventSheetV1, *,
    parameters: FluorescenceCalculationParameters) -> FluorescenceComponentsV1

# Copies selected calculated cells; never repeats gate, ratio, percent or mean math.
project_fluorescence_result(sheet: FluorescenceEventSheetV1,
    components: FluorescenceComponentsV1, *,
    selection: FluorescenceProjectionSelection) -> FluorescenceResultViewV1
```

`EventParseResult` is `{schema, source, sample, channels, domain, extent,
native_declared_event_count, events, unlocated_invalid_count, issues}`.
`FluorescenceComponentsV1` is `{schema, sheet_sha256, parameters,
memberships, population_components, intensity_components, control_components,
native_comparisons, status, issues}`. Its arithmetic performs no acquisition,
subprocess, LLM call, resource choice or gate/control selection. All parameters
are explicit. Recalculation with a different gate is a separately selected pure
calculation using saved full events and a new immutable parameter/sheet identity;
old events, components, returns and observations are unchanged.

`FluorescenceResultViewV1` is `{schema, selector, status, rows,
total_selected_rows, returned_row_count, offset, has_more, issues}` with typed
row variants for populations, intensities, controls and native comparisons.
Selection uses exact sample/gate/channel occurrence IDs and explicit row windows;
duplicates, missing values and zero values keep their identities. The internal
binding links components to the saved sheet; receiver projections include only
the requested values and necessary units/population/denominator qualifications.
Full event arrays remain saved. A parent receives a saved-sheet artifact only
when explicitly requested through its typed return.

Failure rows have exactly `{code, stage, source_position, sample_position,
channel_position, event_ordinal, gate_id, control_pair_id}`; unused locators are
null. Stages are `input`, `parse`, `domain`, `gate`, `calculation`, `capture`,
`projection`, `return`. Required codes include `source_unavailable`,
`native_format_mismatch`, `decoder_unavailable`, `truncated_source`,
`invalid_event_row`, `ambiguous_channel`, `channel_missing`,
`measurement_domain_unavailable`, `measurement_domain_mismatch`,
`gate_parameter_invalid`, `unknown_parent_membership`, `unknown_gate_membership`,
`empty_parent_population`, `empty_evaluable_population`, `incomplete_population`,
`control_missing`, `control_pair_incompatible`, `native_count_conflict`,
`native_population_unknown`, `derived_numeric_overflow`,
`retained_artifact_mismatch`, `calculation_sheet_mismatch`, and
`unreceived_saved_sheet`. Failures are field/population-local where possible.
Status `partial` preserves valid samples/components; no empty result fabricated
for an unreadable source. `unavailable` numeric cells use null plus a reason,
never zero/NaN/sentinel fluorescence.

## Aliases, parser equivalence and exact consumer dependencies

| Incoming name/representation | Binding rule |
| --- | --- |
| `perform_facs_cell_sorting` or its exact `biomni.tool.cell_biology` inventory key | One operation alias; its selected-event/intensity request feeds the common sheet/calculator. It does not expose instrument control. |
| `analyze_cytokine_production_in_cd4_tcells` or its exact `biomni.tool.immunology` key | One operation alias; supplied parent/marker/control definitions feed that same sheet/calculator. |
| Original CSV, explicitly frozen DataFrame, original FCS decoded by FlowKit or FlowCytometryTools | Parser/input adapters only. Same values, domain, event identities and gate definitions must yield the exact same common numerical components. Library identity cannot select scoring. |
| Native selected CSV or cytokine summary CSV/log without original events | Native report acquisition only; available reports are retained, and missing event-level inputs are explicit. These summaries alone cannot complete event membership or saved gate recalculation. |

No additional operation, provider, endpoint or remote deployment is introduced.
The following are exact existing code dependencies/patterns, not claims that a
fluorescence selector already reaches them:

| Existing consumer/function | Exact required input/output and remaining fluorescence connection |
| --- | --- |
| `native_file_capture.capture_native_file`, `capture_declared_native_files`, `retained_native_file` | Reuse complete byte retention and verification with `NativeFileIdentity`. The new operation must supply its original received input identity, native file declarations, writer closure, sample/dataset binding and access authority. These helpers confer byte custody only. |
| `resource_tool_information.bound_resource_tool_contracts`; `ScientificToolLibrary.freeze`, `resolve_tool_info`, `resolve_invocations` | Require an actual caller-bound operation contract with a commission route, resource ID/role, typed request, and substantive operation information. Current code does not have either fluorescence contract. Only a later verified binding can expose one. |
| `LocalPracticalOperations._execute` (`practical.job.start`), `_handle`; `native_expression_nmf_local.prepare_local_expression_nmf`, `local_expression_nmf_plan` | Existing local execution reserves/starts the selected native handle and authenticates original assignment/attempt. NMF-specific functions cannot accept a fluorescence job. A new fluorescence original-input/parameter/environment manifest and corresponding local adapter are missing; selected repair/retry remains episode-owned. |
| `NativeExpressionNMFResults._original`, `_saved`, `_worker`, `execute` | Transport reference: original closed writer → full capture → finite reader/calculation worker; saved mode authenticates the received sheet before calculation. Its `applies` requires `expression_nmf_result_selector_v1`, so it is **not** a fluorescence result handler. Needed new output: retained full events + common sheet + calculations + requested projection with matching identities. |
| `execute_expression_nmf_worker` and `project_nmf_result` | Existing saved-sheet/worker/projection separation, read completely as a reference. Their NMF matrices and numerical calculations are not reusable fluorescence functions. New fluorescence worker must call `calculate_fluorescence_sheet` once and project its cells without another numerical path. |
| `ExpressionNMFResultReceipts.publication`, `NativeExpressionNMFResults.facts` | Pattern for returning only requested typed facts from retained projections. Needed fluorescence artifact set is specifically original sources, numerical sheet, component bundle and requested projection; a path or prose log cannot supply it. NMF `analysis_complete`/fit predicates must not become fluorescence biological-success gates. |
| `EpisodeReturnRecords.authenticate`, `context`, `_attempt`, `_admission_index` | Reuse shared original immediate-parent/child ownership and saved-return validation. The new typed fluorescence return source must authenticate the actual original commission and frozen values, not locate any similarly named artifact in the Store. |
| `ExpressionNMFReturns._received`, `facts_for_closure`, `validate_received_report`, `record_admission`, `authenticate_received_saved_sheet` | Current NMF-specific consumers provide an inspected pattern for original received facts, forwarding prefixes and explicit saved-sheet access. New fluorescence typed sources/validators and registration are missing; do not send fluorescence values through NMF schemas. |
| `ExecutionEpisodes` routing/return registrations in `execution_episodes.py` | Inspected NMF registration anchors: 196–201 initialization; 633–637 operand validation; 1377–1379 result catalog; 1460–1464 dispatch; 1756–1758 receiving fact sources; 1813–1815 closure; 1995–1996 report validation; 2168–2172 results facts; 2267–2269 admission; 2375–2378 saved operand. Each corresponding fluorescence consumer remains to be implemented and read in full before later edits. |

The dependency for CSV calculator development is a validated `EventParseResult`
plus explicit gate/domain/denominator requests, not completion of FCS deployment.
The dependency for FCS equivalence is a real decoded event bundle with complete
metadata and ordinal correspondence, not a whole unrelated tool family.
The dependency for control subtraction is two calculated compatible fraction
rows plus an explicit control pair, not a compulsory condition collection.
The dependency for real requested-return verification is the new result host's
retained sheet/components/projection and actual original child commission,
not just passing arithmetic examples.

## Proposed exclusive future file owners

These assignments are a review proposal only; no coding agents are launched.
Only the coordinator may edit shared routing files after the contracts are
reviewed. No owner writes a second sheet or calculator for the other wrapper.

| Owner | Exclusive proposed files | Input/output boundary |
| --- | --- | --- |
| Shared sheet and numerical owner | `gene_annotation_episode/fluorescence_event_contracts.py`, `fluorescence_event_sheet.py`, `fluorescence_event_calculations.py`; `tests/test_fluorescence_event_calculations.py` | Own all types, validators, numerical field meanings, gate logic and arithmetic above. Receives parser records; emits one shared calculated bundle. |
| Format-reader owner | `gene_annotation_episode/fluorescence_event_readers.py`, `fluorescence_native_reports.py`; `tests/test_fluorescence_event_readers.py` | CSV/FCS/DataFrame-snapshot adapters and native-report parsing only. Consume frozen types; no threshold/domain/control guesses or numerical score implementation. |
| Operation/result owner | `gene_annotation_episode/native_fluorescence_contracts.py`, `native_fluorescence_local.py`, `native_fluorescence_capture.py`, `native_fluorescence_results.py`, `fluorescence_result_worker.py`, `fluorescence_result_views.py`, `fluorescence_returns.py`; corresponding new integration tests | Authentic received inputs, original selected job, complete capture, finite worker, shared-calculator invocation and exact requested return. Depends on named parser/sheet/component/projection outputs, not another entire work block. |
| Coordinator/information owner | Future `native_fluorescence_tool_info.py`, one `knowledge/supplied-fluorescence.md`, its index entry, and required shared routing registrations in `execution_episodes.py`/`practical_execution_operations.py` | Only after actual operation bindings and user-reviewed message boundaries exist. No prompt template is proposed in this artifact. Resource/software instructions match verified deployments. |

## Numerical examples and verification obligations

`arithmetic-examples.json` is a deliberately synthetic arithmetic oracle.
`check_arithmetic.py` uses only the Python standard library. Its success checks
the stated arithmetic, not CSV/FCS parsing, installed dependencies, grader
implementation, compensation, episode delivery or live science.

1. **Complete selected population.** Ordinals 0–7 have values
   `[90, 100, 125, 150, 200, 250, 300, 350]` in one explicitly declared
   untransformed arbitrary instrument domain. Inclusive bounds 100–250 select
   `[1, 2, 3, 4, 5]`: selected=5, parent=8, fraction=5/8=0.625,
   percent=62.5, intensity sum=825, mean=165, median=150. These are dataset
   examples, not suggested biological thresholds.
2. **Missing event value.** Replace ordinal 7 with missing. Parent remains 8;
   selected=5, evaluable=7, unknown=1. Full-parent gate fraction is unavailable.
   An explicitly requested evaluable-subset fraction is 5/7≈0.7142857142857143
   (71.42857142857143%). Known selected mean/median remain 165/150 and are
   qualified. The old wrapper can still print 62.50%; that report does not
   change the new population meaning.
3. **Signed control comparison.** Explicit strict parent `CD4 > 1000` and marker
   `IFN > 500` gates on supplied synthetic values give target 2/4=50% and matched
   control 3/4=75%. Threshold-equal values are excluded. Difference is −1/4,
   or −25 percentage points. Native clipping reports 0; retain both.
4. **Zero versus unknown.** A known parent with four members and no marker
   positives has fraction 0/4=0. An empty parent has counts 0/0 with unavailable
   fraction `empty_parent_population`. A missing file has unknown counts.
   These three returns must differ. A displayed native 33.33% for 1/3 does not
   become the exact fraction and cannot identify an unknown denominator.

Future verification must cover, separately:

- Exact threshold equality for each inclusive/exclusive side; absent bounds;
  explicit pass-all; inverted/nonfinite bounds; duplicate values and row labels;
  parent gate ancestry and requested denominator; original selected ordinals.
- Missing/invalid/nonfinite cells, malformed CSV row with retained ordinal,
  truncated event stream, FCS declared-count conflict, unknown unparsed tail,
  wrong dataset/format, unavailable decoder, duplicate/ambiguous channels.
- Real CSV and authentic FCS recordings with documented channel/scaling metadata;
  matching normalized event populations through different parsers produce the
  **same** sheet/component numerical fields. This is not yet tested.
- Compensation failure versus absent matrix; already compensated data; explicit
  raw domain; mismatched gate domain; known/unknown/no transformation. Never
  double-compensate or infer a transform from the source comment.
- Explicit control pairing, wrong marker/gate/domain, unmatched condition or
  replicate, duplicated condition label, missing control, signed negative
  differences, optional legacy clipping and empty denominators.
- Native rounded/truncated text versus actual event recomputation, overwritten
  native cytokine aliases, incomplete native summary, count conflicts and
  inability to reconstruct original identity from a selected CSV.
- Saved-only recalculation with no acquisition or native invocation; explicitly
  selected changed gates preserve the original history and values; output
  projection equality with calculated cells, including percent aliases.
- Correct resource child and original attempt, selected action replay, source
  custody and writer closure, partial result retention, typed requested return,
  saved-sheet access only through actual received ownership, scientific-parent
  forwarding and closed replay. No new credit/continuation rule.

## Completion accounting

| Deliverable | Status at this boundary |
| --- | --- |
| Exact source and alias mapping for the two named operations | Documented here, pending coordinator review |
| Shared sheet/calculator ownership and numerical examples | Proposed contract; standard-library arithmetic checked separately |
| Tool information and callable deployment | Not implemented/verified for either operation |
| Sheet, readers and shared calculators | Not implemented by this lane |
| Authentic CSV/FCS parser and scientific numerical verification | Not run |
| Actual child-owned result binding, requested return, saved replay | Not implemented/verified for these operations |
| Local/API/HPC live-resource verification | Not run; actual configured software/input bindings remain missing |

The original required work remains open. If reviewed, this artifact can advance
the parent's R3 boundary mapping count by two (26→28). It cannot count either
operation as implemented or complete. No goal/progress file was edited.
