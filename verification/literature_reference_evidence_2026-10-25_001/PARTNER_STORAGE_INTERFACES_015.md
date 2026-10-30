# Selected partner components: storage and typed returns

Depends on the fixed PARTNER_COMPONENT_INTERFACES_015.md (including additive
clarifications) and PARTNER_READER_INTERFACES_015.md. Those modules now pass120
joined checks. This workload binds their actual outputs, not new paper reading.

Fresh storage owner exclusively owns gene_annotation_episode/literature_partner_storage.py
and tests/test_literature_partner_storage.py. Existing production files remain
coordinator-owned. Do not change reader/core files, existing runtime/calculators,
pins, live runs, scientific cases, sources, controllers or historical records.

Model the established literature_figure_storage.py and LiteratureRateRepository
pattern, preserving its entire authority/publication/replay/subset behavior.
LiteraturePartnerRepository extends LiteratureRateRepository; provider is
literature.experimental.partner, record_version literature_partner_record_v1,
operations_table literature_partner_operations, received_table
literature_partner_received. Reexport partner_population_schema.

Selected coordinator tool name is literature.partner.populate. Use the exact
reader arguments, never numeric operands from selected arguments. Bind every
direct source: root, data_source_ref, nine nonnull literals in LITERAL_FIELDS
order, then interpretation_witnesses, deduplicated. Retain all scoped ancestors.
Validate run/episode/scope authority, actual receipt, assigned-page lineage for
ALL direct refs, and transitive provenance. Make extraction/calculation and
immutable publication one transaction. Repeated request reuses original saved
output with no re-reading or recalculation. No observation/credit from internal
steps, record creation, replay or return assembly.

Nine source-bound literal bindings in fixed LITERAL_FIELDS order:
subject_ref,partner_ref,experiment_ref are reference records;
endpoint_ref,normalization_ref,function_ref are terms;
reference_condition_ref,omitted_condition_ref,addback_condition_ref are
assay_condition contexts. Each nonnull binding has its actual source/artifact/
span/quote anchor. Preserve distinct roles even when text spans coincide; copy
the established context auxiliary-reference pattern where necessary.

Payload exactly the needed version,input_source_ref,input_artifact_ref,
input_source_refs,direct_input_source_refs,data_source_ref,extraction,
experimental_bindings,sheet:{cells}. Retain full source recipe, core input,
comparison checks, native spreads and eight cells in extraction. Validate saved
request and payload authority/headers, direct source set/order, bindings and
literal meanings, all versions/closed scientific structures, exact saved outcome
and numerical cell metadata. Do not call readers, calculators, _Sources, or open
original paper/recipe/witness bytes from saved read, project, replay, admit or
forward. These use committed artifacts only. No quiet fallback reacquisition.

Typed rows: sheet_ref,evidence_source_ref,data_source_ref,nine bindings,
component,eight cell fields,formula_code,source_kind,comparison_checks,
arm_metadata, and the fixed metadata below. x-source=literature_partner_cells.
Reference/enum fields must have original declared meanings and actual resolvers.
Source-kind uses existing SOURCE_KINDS; nullable origin is required for a missing
arm. Cells contain signed differences/fractions and explicit conditional domains,
not only[0,1]. Native unreported unit stays null. Allowed cell bound kinds are
point_only_not_uncertainty and conditional_input_domain_not_CI. Preserve both
bounded/null-point and populated/singleton statuses; no SD or CI inference.

comparison_checks is exactly the core two-check structure. Each check has
matched|different|unresolved status, differing_factors (array of nonempty actual
saved factor names), and null or the core's finite unavailable-reason vocabulary.
These are saved fact fields validated against the extraction, not free reports.
Their meaning is differing recorded experimental factor attributes; no inference
of physical difference from a missing attribute. Exact factor strings are source
field identifiers, not arbitrary findings or instructions.

arm_metadata exactly {reference,omitted,addback}; each null or exactly
{partner_state,condition_coverage,spread:{kind,magnitude}} from core input.
This keeps ±58 unspecified, SD/SEM/CI distinction and condition completeness
through the parent boundary. Raw recipe factors/measurements stay in committed
evidence. Parent receives requested numerical rows and one interpretation panel.

Fixed metadata:
evaluation_scope=reference_experimental_partner_components
target_correspondence=not_evaluated
partner_necessity=not_inferred
statistical_uncertainty=not_evaluated
measurement_corrections=not_applied

formula codes (same order as COMPONENTS): native_partner_reference_v1,
native_partner_omitted_v1,native_partner_addback_v1,partner_reference_minus_omitted_v1,
partner_loss_over_reference_v1,partner_addback_minus_omitted_v1,
partner_gain_over_loss_v1,partner_gain_over_reference_v1.

Use the existing inherited exact subset validation/admission/forwarding APIs.
Returned rows must equal the saved requested subset, including qualifiers,
spreads/checks/bindings and fixed metadata. No model composing recorded facts.
Missing field bindings remain null rather than a forged role or placeholder.

Meaningful checks cover real Store/source/recipe publication and source anchors,
missing/partial/known-different/censored cells, source/scope/page/ancestor guards,
transaction rollback and idempotence, exact subset/receipt preservation,
inconsistent/forged metadata rejection, saved-only reopening with original
artifacts/reader/core/_Sources disabled and SQL query_only, and header/request
authority. No model, native alignment, network, new episode or W05 change.

## Closed-form factor-reference clarification

The owner correctly found that raw arbitrary factor-name strings cannot cross
the closed parent form. Preserve raw core checks unchanged in extraction, but
typed rows and selected-result metadata replace differing_factors with
differing_factor_refs (actual term references). Add factor_bindings to the saved
payload, mapping each distinct differing factor name to its term reference.

Mint deterministic source-bound terms: namespace=literature_partner_condition_factor,
accession=identity('partner_factor',{'data_source_ref':data_source_ref,'factor':name}),
label=name,term_type=other,source_ref=data_source_ref,anchor=null. This represents
a decoded field in the retained dataset; do not forge an original-paper span.
The term schema permits a source-bound term without a literal text anchor.
Publish these references in record_refs/changed_record_refs with ordinary custody.
Saved validation checks membership in actual recipe factors, exact term fields/
identity and projection against the retained core checks, without original-byte
reads. Parent reference resolution then supplies actual factor labels. The nine
literal source bindings retain their exact text anchors and declared meanings.
No raw factor-name strings or free prose occur in the typed comparison check.
