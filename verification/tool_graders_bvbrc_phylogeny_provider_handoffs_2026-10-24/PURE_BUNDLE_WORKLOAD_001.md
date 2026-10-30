# Pure phylogeny bundle integration workload

This workload follows the accepted provider contract and original frozen
numerical contracts. It owns no host custody, registry, episode, library,
prompt, credit or controller changes. Root owns those consuming paths.

## Exclusive new production files

- gene_annotation_episode/bvbrc_phylogeny_bundle_contracts.py
- gene_annotation_episode/bvbrc_phylogeny_bundle_resolution.py
- gene_annotation_episode/bvbrc_phylogeny_bundle_projection.py
- gene_annotation_episode/bvbrc_gene_tree_bundle_adapter.py
- gene_annotation_episode/bvbrc_codon_tree_bundle_adapter.py
- tests/test_bvbrc_phylogeny_bundle_contracts.py
- tests/test_bvbrc_phylogeny_bundle_resolution.py
- tests/test_bvbrc_phylogeny_bundle_adapter.py
- verification/tool_graders_bvbrc_phylogeny_bundle_2026-10-24/*

Do not edit existing provider/shared modules. Their actual staged development
path is verification/tool_graders_bvbrc_phylogeny_implementation_2026-10-24/staging;
root installs the verified modules. No dependency stub counts as verification.

## Public interfaces and exact dependencies

Each thin provider adapter exports ADAPTER_ID (bvbrc_gene_tree or
bvbrc_codon_tree), ADAPTER_VERSION="1", implementation_sha256(),
validate_parameters(parameters), requested_form_schema(fields),
validate_requested_form(requested_form), and:

```python
consume_bundle(bundle: dict, *, artifact_bytes: dict[str, bytes],
               supplied_values: list[dict], requested_form: dict,
               parameters: dict) -> dict
```

The result has the eight existing PureAdapterResult keys. Sheet and components
are always PhylogenySheetSet/PhylogenyComponentSet, including one-analysis cases.
Retain all originally selected analysis IDs, including invalid/partial members.

Use ADDITIVE_CONTRACT sections 3–5 exactly for ReaderSpecPlan, original roles,
semantic SlotRef/TreeSlotRef compilation, parameters, supplied scientific inputs,
population plans, selections and saved set shapes. The old original proposal's
future artifact-ID parameters are superseded only by that accepted addition.
SUPPLIED_CONTENT_CONTRACT_001 supplies authenticated external raw bytes through
the optional original bundle.supplied_contents; it does not change the provider
sheet or SuppliedDocument shapes. Root owns that host transport implementation.

Shared parsers consume explicit native bytes and ArtifactRef; preserve all ten
reader variants and reader outcomes. Provider extraction receives exactly the
declared typed document envelope, original InputBindings, observed run, typed
joins, materialized ProviderAssembly and read parameters. Provider calculators
consume their saved sheet and materialized calculation parameters. Do not
reimplement any arithmetic, native parser or provider join logic here.

GeneTree supports gene_tree and concatenated_sequence_loci. CodonTree supports
core_genome_codon_protein. Validate selected native application IDs and original
task before association-dependent claims. Parser selection follows declared
format/dialect, not a filename or resource label. Missing/unobserved native
methods remain explicit; do not invent PhyML/FastTree log measurements.

## Resolution rules

Resolve exactly each original role and analysis-local slot. Validate actual
bytes/digests/transfer/object/task association; preserve original source facts.
Use every supported C4 task-association kind under its actual qualified meaning;
do not copy Homology's stronger manifest-only restriction. Unproved producer
bytes remain qualified current-byte observations. A role alone cannot prove
which analysis/locus created the file.

Identical repeated representations use the canonical lexicographically smallest
acquisition receipt solely for parsing; every alias stays in SelectionResolution.
Different objects/bytes for one role are ambiguous, never selected by recency.
Identical raw bytes with incompatible parser specifications are a conflict.
Forest tree_index refers to original source-order indices, not successful index.

Compile only the fixed enumerated fields in ADDITIVE_CONTRACT. Do not walk all
JSON recursively substituting strings. Do not mutate the original requested
schema or fill in future IDs there. Missing slots produce nullable provider
references and exact requirements, with independently valid analyses retained.
Materialize selected explicit populations without choosing subsets; retain
whole-document populations separately as the provider defines.

For supplemental parsed documents, authenticate the exact matching declared
ContentBinding from bundle.supplied_contents and reparse its supplied bytes once
at publication to check the claimed ReaderInput.result. Missing bytes affect
only that supplemental document and dependent facts. No I/O or callbacks inside
this pure adapter; a saved provider calculation does not reparse.

## Projection boundary and root handoff

Implement all closed array forms already fixed in CONTRACT_SHAPES and
ADDITIVE_CONTRACT: branches, sites, family memberships, function composition,
relationship comparisons, requested requirements and qualifications. Scalar
selectors must map by a finite named catalog to actual stored Quantity cells;
no user-supplied expression/path/filter language. Preserve quantity units,
denominators and missing-dependency meanings. Unknown normalized branch units
cannot be returned as a requested known-unit scalar; qualified native branch
rows can retain native_unknown with their signed values.

Before coding projection, send root the exact finite scalar catalog and selector
keys derived from the actual completed components. This closes the original
proposal's illustrative-only scalar examples. Assembly/resolution coding can
proceed independently while root reviews that catalog. Do not invent formulas.

The contracts module exposes selector_kind(selection), requested_form_schema
and validate_requested_form without importing a calculator. Root's saved-fact
return reader will consume those functions and schemas, never the calculation
engine. Include a pure finite identifier codec for array references if needed;
give root its exact signatures and encoding before depending on it. A returned
reference must resolve within its actual selected analysis and publication.

Only requested dependencies plus mandatory selected task/input associations
reach adapter missing_requirements. Preserve optional omissions in the saved
sheet/components without making unrelated complete requested facts partial.
Every null has its actual missing/failed/truncated/incompatible cause retained;
empty arrays require actual complete empty populations. Preserve negative and
zero values. No arbitrary exception text enters a diagnostic.

implementation_sha256 hashes actual adapter/contract/resolution/projection and
all repository parser/provider/calculator dependencies with unambiguous framing.
It is a configuration function; scientific calls perform no file reads.

## Verification and ownership limit

Use actual retained native nine-row Codon matrix, partitions/trees/logs and
GeneTree XML examples, separately labeled source-derived/synthetic fixtures.
Verify hand quantities, saved complete outputs, malformed independent files,
multiple analyses, missing alignment with valid tree, wrong task/reference,
ambiguous role, original forest indices, repeated representations, all-gap and
empty populations, unknown alphabets/units/methods, request-limited requirement
closure, exact original schema and artifact preservation, and no hidden I/O.
Test supplemental exact-byte validation and a deliberately forged parsed claim.

Export populated sheet/component sets, requested fields and parameters with
actual code/input hashes. Recalculate saved provider sheets without parsing or
I/O. Do not claim host custody, library selection, immediate-parent admission,
live API/HPC execution or full episode integration from this pure workload.
Root consumes these modules in AppServicePublications._grade, static adapter
registration and the existing results→scientific→root return chain separately.

Reread the immutable objective and all sixteen design principles after each
tool/substantial source examination and before handoff, followed by the exact
current contracts. Preserve every historical contract/report and failed check.
