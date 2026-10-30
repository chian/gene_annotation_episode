# Infernal retained grading and numerical publication: workload 225

Read the ENTIRE immutable original goal attachment and AGENTS.md first. Preserve
the verbatim objective/all 16 principles reset after substantial native study
and before closure. This workload is the Store-facing portion of boundary 5;
there is no new episode type, tool execution, resource choice or scientific score.

## Exclusive ownership

- New gene_annotation_episode/native_infernal_result_publication.py
- New tests/test_native_infernal_publication.py and own fixture directory
- This verification directory

Root owns all existing shared files (including domain.py/state.py), result views,
result operation binding and parent/grandparent return validation. Worker 224
owns native_infernal_result_worker.py; 223 acquisition; 222 producer/bridge.

## Inputs, functions and exact output

Read complete native_hmmer_result_publication.py and its consumers/tests for the
existing bounded process/material/source mechanisms. Reuse matching semantics;
do not route Infernal into HMMER parsing or infer scientific properties from it.
Read complete native_infernal_contracts.py, infernal_native_result_views.py,
223's capture module/contract and 224's worker contract/implementation.

prepare_native_infernal_grading(store, *, bundle, bundle_artifact_ref, artifacts,
directory, policy, selector) returns exactly:
{version:native_infernal_prepared_grading_v1,bundle_artifact_ref,
source_grading_artifact_ref,grading_artifact_ref,sheet_artifact_ref,
scores_artifact_ref,selected_rows_artifact_ref,failures,numerical_complete}.
Artifact references nullable where no output exists. Failures are {stage,code,
record_key:string|null}. Validate captured input/output role/path/hash/size and
original expected input bytes before grading. Keep full bytes retained even
when unusable, with explicit per-file failures. Do not hydrate whole native
datasets/full sheets in the host. Use actual artifact paths and run the existing
bounded local process once with the provided LocalJobPolicy and 224's exact
plan. Own files go under directory/native-infernal-grading; preserve immutable
intent/prepared receipt. Repeating the same completed preparation verifies and
reuses it without parsing/calculation/execution. Interrupted unsealed work is
explicit, not an automatic retry.

Use retain_tool_grading provider episode.execution_result. Stable source grading
schema native_infernal_retained_grading_v1 holds sheet/scores artifact refs,
their actual schemas/formats, and captured artifact descriptors. It must be
independent of selected page/metrics/family. Selected grading additionally holds
source_grading_artifact_ref, selected_rows_artifact_ref, selected_rows_schema
native_infernal_selected_row_v1, selected_rows_format ndjson, bundle_sha256,
original selector, failures, numerical_complete, diagnostic artifacts and actual
worker receipt. Do not reprice old history or rewrite earlier artifacts.

publish_selected_native_infernal_rows(store, *, source_ref,bundle,prepared,scope,
selector) returns {record_refs,rows,failures}. Read only selected NDJSON rows and
small retained grading envelope. Validate source/bundle/prepared/selector custody
and exact requested metrics. Typed row shape is row_schema(family) in root's
views. Worker selected-row shape is fully frozen in 224's WORKLOAD_001.md.
Preserve native record keys as row identifiers: communication resolves them
against exact saved rows; they need no generic accession regex. Copy requested
values and explicit missingness without extra calculations or LLM calls.

Validate subject binding against actual complete original sequence hash/length,
units, explicit binding identity and assigned scope; no arbitrary name or taxon
join. subject_intervals are a list of zero-based half-open original intervals,
not one enclosing span. Validate every interval separately and retain actual
physical footprint. Never map covariance-model positions onto a sequence
reference. Related compact covariance_model operands produce family references;
an explicit supplied reference must have matching actual native identity/type.

Only rows with valid explicit original subject association and actual physical
intervals become observations. Unbound rows still return their requested valid
numbers. Column/pair population rows remain unbound when no single physical
subject is defined; do not fabricate one. A missing association is different
from a supplied wrong association; preserve valid sibling rows.

For published search_hit/search_sequence use kind profile_match; for
alignment_sequence use alignment. Observation contains full available original
family measurement list (not just requested subset), source_subject_refs,
dependencies, anchor:null, operand_intervals with role query and nt units, and
native_infernal:{version:native_infernal_observation_v1,program,family,
record_key,bundle_artifact_ref}. Root adds this exact domain/Store extension.
Projection status published|unbound|invalid, strand plus|minus|null. No timing
or annotation confidence is included in these scientific observations.

The raw original uppercased sequence digest is the identity check; Infernal's
RNA digitization can explain output correspondence but does not silently
replace the original input or Store subject. Existing sequence chunk traversal
semantics may be reused where they match, without modifying existing modules.

## Completion and verification

numerical_complete means the requested extraction/projection was actually
performed; it is not a scientific acceptance gate requiring all possible values
to be knowable. Retained unknowns with explicit missingness can be a valid
completed response. Missing selected records, corrupted original custody and
invalid required extraction stay actionable failures. Parent/controller
completion and credit are root-owned; add no synthetic action/credit here.

Use retained real 222/219/220 results plus specific synthetic negative cases.
Verify all five families, native zero vs missing, correct and wrong subject
bindings, duplicate identities, subset projections preserving observation/source
identity, malformed/partial artifacts, saved preparation replay without worker
launch, and host non-hydration of full sheets. All test processes use existing
run_local_job with explicit 20GiB RAM/4GiB scratch/no wall cap. Report exact tests,
filled numerical examples, source hashes and unverified integration separately.
