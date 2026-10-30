# Phylogeny publication and immediate-parent return reader

This workload reads already published requested facts. It does not extract
native measurements, recalculate, acquire data or change the episode tree.

## Exclusive files

- gene_annotation_episode/bvbrc_phylogeny_returns.py (new)
- tests/test_bvbrc_phylogeny_returns.py (new)
- verification/tool_graders_bvbrc_phylogeny_returns_2026-10-24/* (new)

Root owns existing host/API/execution registrations, tool information, adapter
registration and full Workflow tests. The separate bundle workload owns all
five bundle modules and its tests. No edits to either owner's files.

## Input/output interfaces

Export FACT_SOURCES, IDENTIFIER_NAMESPACES, phylogeny_fact_sources(),
requested_sources(schema), project_phylogeny_facts(body, *, requested_sources),
and BVBRCPhylogenyReturns(execution). The class exposes the same host-callable
method signatures as BVBRCHomologyReturns: facts(context, schema),
received_context(context), received_facts(context, schema),
validate_received_report(context, form, schema),
record_admission(context, form, schema, operation_key),
resolve_own(context, reference, namespace), and
resolve_received(context, reference, namespace).

Use the eight original fact-source namespaces from BOUNDARY_PROPOSAL section7:
measurements, branches, sites, family_membership, function_composition,
relationship_comparisons, requirements and qualifications, all prefixed
bvbrc_phylogeny_. Each row carries original publication source_ref and requested
field. Array item types and finite enums are exactly CONTRACT_SHAPES and
ADDITIVE_CONTRACT, including nullable arrays versus measured empty arrays.
Fix the exact row value-key mapping with the bundle worker before coding.

Use only the bundle contracts module's pure finite selector/schema/reference
functions. Read SCALAR_CATALOG_001 and REFERENCE_CODEC_001 (the two redundant
literal_literal metric names were corrected additively in the implementation).
No calculator/parser import or callback. No JSON expression language. Saved
publication facts must match the original selected adapter, version, schema,
field selector, analysis and decoded reference scope. Integer nodes/columns
must agree with the original requested selection and actual published result
semantics. The authenticated publication retains full source and sheet proof;
do not give an ancestor access to unrequested fields through a source ID.

## Custody and consumers

AppServicePublications.read authenticates bytes, saved inputs and original
commission. The reader projects only that publication's saved requested facts.
Latest means numerical original operation order, never directory hash order.
Preserve current original-commission, immediate-child admission, frozen form,
scope, original field and no-duplicate receipt checks from EpisodeReturnRecords
and the existing Homology reader. Source presence alone never grants access.
Semantic references are labels in the admitted publication, not acquisition
receipts. A parent forwards only its admitted original typed facts.

Root will consume the module in APIServiceExecution initialization,
AppServiceHost.facts, and ExecutionEpisodes' fact declarations, received facts,
reference resolution, report validation and admission paths. Root integrates
both scientific adapter IDs without changing Homology behavior or method_loop.

## Verification

Test every scalar/array family, null versus empty, negative and zero values,
wrong adapter/source/analysis/selector/schema, malformed canonical references,
unrequested extra fields and wrong scoped node/column references. Test actual
completed-action custody and immediate-child returns with real saved records,
including tampered/missing reports and replay creating no new observations.
Disable scientific calculations/parsers/acquisition while reading and
forwarding. Controlled fixtures prove only their stated boundaries; do not
claim native service execution or a full selected-tool Workflow test here.

Reread the immutable objective and all sixteen design principles after source
study and before handoff, followed by these contracts. Preserve old reports.
