# Exact reference membership binding from supplied Data records

This closes the remaining reference-record mapping named in003. It adds no
schema field, service call, reference database or scientific formula. P owns
this pure selection/validation in its existing bundle_resolution.py. D's
SuppliedRecordSetsV1 remains unchanged; I authenticates its original inputs.

## Input and ownership

The requested ReferenceMembershipV1 objects remain explicit provider parameters.
P resolves them against already selected D record sets, exact qualified Data
inputs and their retained bytes. It passes only source-verified memberships
to N. An unmatched or conflicting declaration yields the existing specific
reference requirement/diagnostic and preserves unrelated native calculations.
Do not accept a self-consistent parameter object as its own evidence.

The supported source for this binding has basis=supplied_data_api. Other basis
values require their own real producing-evidence contract; none is invented
here. A synthetic unit fixture may exercise the Data path with synthetic
qualified inputs, clearly labelled as such, without claiming host admission.

## Select the exact record population

For each membership, use its source_locations to identify exactly one selected
D record set with collection=pathway_ref or subsystem_ref as appropriate.
The locations' source_ref/raw_artifact_ref pairs must agree with the selected
qualified input bindings and collectively name all pages of that record set.
Zero candidates are missing; multiple distinct matching record sets are
ambiguous. Identical bindings do not become independent reference evidence.

Every location must resolve within those retained native bytes. A response,
docs-array, row or member-cell pointer may be used. After exact entity/map
selection below, every contributing member cell must be covered by a selected
location, using parsed JSON-pointer token ancestry rather than string prefixes.
An exact empty response needs its response/docs-array location; it is not
proved by a nonexistent row. Preserve all D rows and source locations.

P may filter a fully acquired broader query to the exact requested entity and
map context. It must inspect every retained row needed to determine that
membership; an invalid/unidentified relevant row cannot become absence.
Do not select one convenient page or the first matching row.

## Pathway references

Use the saved valid scalar cells id, pathway_id, ec_number, map_name and
map_type. Select exact pathway_id equality with the requested pathway entity.
Every relevant required cell must be present, valid and of the registry's
declared type. The members are the distinct exact ec_number strings in the
selected map context. Keep duplicate occurrences in D; do not count them twice
in the reference set. Conflicting unique IDs remain incompatible.

The Data field registry has map_name and map_type, but no native map_id field.
For this binding, a non-null map_id is an explicit derived context identifier:
canonical JSON of [map_type, map_name], using the same finite-JSON canonical
serialization as the shared contract. For example, the two native strings
KEGG and Glycolysis identify the string ["KEGG","Glycolysis"]. This is not
reported as an upstream native identifier. P decodes/checks that exact pair
and selects only rows with those two native values. It does not infer a pair
from a basename, pathway ID, arbitrary label or regular expression.

With map_id=null, exactly one observed (map_type,map_name) pair is permitted
for a nonempty selected pathway population. Multiple pairs are ambiguous,
even when their EC sets happen to agree. A fully acquired exact empty query
can have an empty observed reference set with no observed map; the resulting
ratio still has its ordinary missing empty-denominator behavior.

## Subsystem references

Use exact subsystem_id equality. Extract the valid native role_id array as a
set of exact strings. Role names are retained separately; independent role_id
and role_name arrays are never zipped. The requested component_kind must be
role_id and map_id must be null. Check every non-null requested hierarchy/name
field against its corresponding retained native field; conflicting observed
contexts for one selected subsystem remain incompatible. Do not turn missing
hierarchy metadata into an invented hierarchy or choose the first context.

## Completeness, release and exact declared values

The requested members must equal the complete derived set (set equality with
the requested duplicate-free order preserved). Do not silently accept a
caller-supplied subset or append members to the original parameters.

For a complete membership, the D population must be complete for its declared
query, with complete page coverage, single_response/proven_same_snapshot,
valid relevant cells and no conflicting IDs. Unknown multi-page consistency,
missing rows or conflicting records cannot establish a complete set. Partial
observed records stay retained in D and produce an incomplete/missing reference
requirement when the requested complete membership cannot be verified.

The current Data input contract has no authenticated reference-release field.
release therefore remains null with reference_release_unknown. A non-null
caller release is not proof of a release and cannot be silently copied as one.
The other source/metadata qualifiers remain attached to the reference and its
calculation; neither complete query coverage nor a reference set establishes
biochemical sufficiency or physical presence/absence.

## Required verification

Use actual D extraction and then the actual P/N/C path with controlled native
Solr-envelope bytes: a four-EC reference gives native2/4 and later3/4; a
subsystem role-ID array remains valid with independently ordered role names;
two map contexts require exact selection; a complete empty reference remains
distinct from missing and incomplete acquisition. Reject a fabricated member,
wrong source/pointer/entity/map, changed bytes, omitted page, unsupported release,
conflicting ID, malformed relevant cell and self-authored completeness claim.
Native-only sibling results remain available when the reference is unusable.
The pure path performs no Store/network/model/process access. I separately
tests actual source custody and original parameter authentication.
