# Read-only review of C365 population integration

2026-10-26. Review scope: the completed C365 U06 integration against 361's
PLAN_001 and CONTRACT_ADDENDUM_001–003, accepted pure implementation 363, and
metadata 364 including root's one-sided-unknown correction. This review found
no concrete defect in the inspected U06 implementation. The bounded integration
is acceptable as a supplied-data calculation and controlled selected-child
return path. This is not acceptance of a live database deployment, a full
scientific episode investigation, or the all-308 goal.

The reviewer ran no tests, native tools, database searches, network requests or
HPC jobs. Work consisted of source/receipt inspection, JSON comparisons and
SHA-256/byte-length comparisons. Only this new 375 directory was written.
Production, tests, accounting and permanent direction records were not changed.
The immutable goal was read in full initially; its purpose and entire DESIGN
PRINCIPLES block were reread verbatim after examining the saved outputs, followed
by the complete current 361 contract and all three additive contracts.

## Scope and ports

The inspected paths cover standard blastn/blastp/blastx/tblastn/tblastx, including
tblastn supplied PSSM, and PSI sequence/PSSM/MSA plus DELTA's explicitly bound
sequence-database stage. Profile/domain calculations and VDB retain their
separate contracts. There is no annotation-score, prompt, resource-selection or
controller change.

The integration passes optional per-search population associations into v3
direct sequence sheets and v3 iteration sheets, then into the existing numerical
calculator and sequence_function/sequence_population rows. The substantive
native/source extraction, numerical sheet and deterministic calculation remain
separate. The standard and PSI/DELTA hosts still have no new episode-accessible
saved-function selector. The public saved calculator and existing worker reuse
are the reviewed recalculation ports.

The inspection followed complete relevant changed functions through metadata
preparation, original captured source binding, direct/iteration sheet creation,
saved validation, calculation, numerical rows, publication, result ownership,
immediate-child forms, admission and receiver facts. Read-only consumers included
both result_views, the standard calculators, both result owners/returns and
publication implementations, the relevant ExecutionEpisodes selection/fact/
admission/credit/completion methods, execution_progress.describe_target,
EpisodeReceipts.receive, the closed communication schema compiler, and
EpisodeReturnRecords. The controlled SyntheticHost implementations and the full
new integration/recalculation tests and fixture were inspected as source.

## Accepted behavior

1. **Original selected database and root custody.** The v3 metadata envelope
   retains the original root bundle and manifest values with their actual
   captured artifact/source identities, digests and byte lengths. Root bundle
   size comes from bundle_capture.size_bytes. It is not computed from a new
   serialization. Native `_population_capture_binding` compares the selected
   descriptors, original root value and captured source identities against the
   worker request/catalog; available original root/manifest records cannot be
   dropped. `_population_sheet_binding` checks the original v3 selection and
   exact SearchKeys across direct and iteration sheets, preventing an erased or
   downgraded interpretation from becoming parameter-only reuse.

2. **Semantic census joins.** The supplied assertion binds the complete literal
   ordered native operand, actual manifest digest and semantic population to the
   actual census artifact, length and record pointer. Profile.source must equal
   census_source.source_ref, and the original census value must equal the
   profile with source removed. Source, artifact and byte-digest report aliases
   are independently rejected. Available Store bytes alone do not grant the
   selecting parent or child authority. Unresolved selected declarations stay
   present, so a valid sibling cannot erase them.

3. **Unknown identity.** The final metadata helper at
   native_blast_database_population_metadata.py:420 checks null release/scope on
   either side of the assertion/selected-identity comparison before comparing
   known values. In the absence of another contradiction, this is unavailable,
   not a known identity conflict. A known unequal value remains conflicting.
   This is root's corrected helper, not the superseded 364 behavior.

4. **Narrow failure resolution.** Standard worker `_resolved_population_failures`
   at line341 resolves only the active failure mapped from the exact original
   `native_path_semantic_identity_population_equality_unproven` issue index and
   complete SearchKey. It requires a selected nonempty v3 association list and
   the already-calculated matching context/relation with every association
   available and no reason codes. Original issues and diagnostics remain. The
   removal precedes calculation-exception index assignment; unrelated failures
   retain their effect. No global metadata exclusion or new completion gate is
   introduced. Zero-hit success remains a measured empty result. Partial native
   execution can retain useful calculated rows while complete remains false.

5. **Unchanged numerical meanings and returns.** Only the justified native-value
   versus semantic-value mismatch is relaxed. Existing census count units,
   release/scope, observed-group, missing-function and zero-count checks remain.
   The conditional reference kernel is unchanged; source quality, taxonomy and
   other unused inputs are not silently weighted. PSI/DELTA forwarding is keyed
   to the complete search and excludes the domain stage. Record-quality values
   0.9 and 0.6 retain their original record locators. Existing row projection,
   original commission/receipt validation, exact registered fact schemas,
   frozen child forms and receiver admission carry the numbers without an LLM
   restatement. Function/population rows are source-only, not new biological
   observations. The source/fact identity and existing credit path do not turn
   each internal calculation or row into a new own action.

Key implementation anchors are native_blast_database_result_worker.py:415 and
:463, blast_database_population_associations.py:172,
native_blast_database_population_metadata.py:468 and :491,
blast_database_grader.py:778 and :1138, blast_iteration_calculators.py:358,
native_blast_standard_database_result_worker.py:341, and
native_blast_database_result_worker.py:839. The original contracts and whole
relevant call paths, rather than these anchors alone, were used for the review.

## Actual numerical and custody evidence

All 16 entries in C365 SOURCE_PINS_CURRENT_002.json match the current files in
both SHA-256 and byte length. The native worker is
`de6d17d20188129142e7d8a6c94581dc89418a6312ab17f42983fcae2a5f980f`;
the standard worker is
`cbdd3c86a11a383961b06048e55060df44184441b5a69e54c35579fd1d4b17ff`;
the metadata helper is
`f1fef5d3cb315f531f628b77ef3b5708ddc03f5f7200c3256e33fce20fc3b156`.

All 119 distinct artifact references in
examples_002/ACTUAL_TYPED_NUMERICAL_EXAMPLES_002.json match their retained files
in digest and length. For each of its 14 positive cases, the recorded function
and population rows equal the actual publication, original requested parent
form and received parent facts. This was a comparison of existing records, not
a new execution of the return path.

The explicit synthetic example has bit scores 20 and 18, equal priors, N=110,
N_F=100 and N_G=10:

| Quantity | F | G |
| --- | ---: | ---: |
| T=1 function mass | 1 | 1/4 |
| T=1 unadjusted conditional weight | 4/5 | 1/5 |
| T=1 representation-adjusted weight | 2/7 | 5/7 |
| T=2 function mass | 1 | 1/2 |
| T=2 unadjusted conditional weight | 2/3 | 1/3 |
| T=2 representation-adjusted weight | 1/6 | 5/6 |
| Census fraction, independent of temperature | 10/11 | 1/11 |

At T=1 the prior-weighted masses are 1/2 and 1/8; dividing by 100 and 10 gives
1/200 and1/80, then normalization gives 2/7 and 5/7. T=2 changes the second rate
to 1/40. The retained saved blastp, PSI and DELTA calculations report those T=2
values with calibrated_annotation_probability=false. These are conditional
model weights from supplied synthetic facts, not measured annotation accuracy.
The three recorded parent quality returns preserve 0.9/0.6 on the original
records and their function-specific projections.

## Verification limits and bounded follow-up

C365's retained evidence comprises 55 distinct new passing cases across runs,
plus 277 historical passing cases. It must not be described as 332 tests all run
against the final native worker. The compared before/after manifests each track
66 files and show no within-run changes:

| Retained run | Actual result | Source qualification |
| --- | --- | --- |
| hosts_007 | 9 pass, then 1 failed MSA fixture | Native worker precedes final v3 custody guard; failure retained |
| regression_008 | 277 pass | Same earlier native worker; historical regression evidence |
| final_custody_009 | 25 pass | Final U06 production sources; earlier alias-test fixture revision |
| remaining_hosts_010 | 20 pass | Final U06 production sources; earlier alias-test fixture revision |
| alias_011 | 1 pass | Entire current 16-file packet matches |

Thus 46 distinct new cases have final U06 production-source receipts, and 9 positive
host cases have the earlier receipt. The final alias addition changed two test
files, not production. The recorded runs used local_jobs with 20 GiB RAM,
4 GiB scratch and no wall-time limit; scratch monitoring is not a hard total
filesystem quota. The reviewer did not rerun them.

If root needs an all-required-modes claim specifically at the final production
pins, the useful bounded follow-up is the existing
test_selected_children_preserve_population_numbers_and_original_typed_returns
with `-k 'not msa and not tabular and not rounds and not queries'`: precisely
the nine early positive cases. Use the existing bounded launcher and a new
receipt directory. No broad 277-case repeat or new native database run is
recommended by this review.

SyntheticHost invokes real selection, producer/capture, worker, publication and
form/return functions but supplies the synthetic transport/output and manually
journals runtime actions, child closure and delivery. These fixtures do not run
a new scientific model investigation or demonstrate a complete shared
method_loop/controller episode. No live database, service or HPC deployment,
authentication, scientific census measurement, or resource availability is
established. Existing live-resource work remains open. This enhancement adds
no tool count; the shared 110/308 tally is unchanged. Root retains ownership of
acceptance and accounting.
