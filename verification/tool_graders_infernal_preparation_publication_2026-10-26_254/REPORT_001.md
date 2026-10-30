# Preparation grading and publication — workload 254

Implemented the exact P2 retained-grading/publication boundary in the two owned
production modules, with their two test files. No runtime, schema, pure grader,
native producer, capture module, inventory, observation or annotation-credit code
was changed by this workload. Root owns episode integration and requested typed
failure forwarding.

## Public handoff and retained data

The frozen APIs are implemented:

```
prepare_native_infernal_preparation_grading(store, *, target, capture,
    capture_directory, directory, policy) -> Prepared
publish_selected_preparation_result(store, *, source_ref, prepared, selector,
    directory, policy) -> Publication
validate_prepared_grading(store, prepared, *, bundle, verify_files=True)
validate_publication(store, publication, *, source_ref, prepared, selector,
    directory, policy)
```

The final helper authenticates an existing successful publication receipt only;
it cannot initiate work. `Prepared.grading_artifact_ref` is the entire pure
grading result, while sheet and calculation artifacts are independently retained.
`source_grading_artifact_ref` is the stable `retain_tool_grading` envelope. It
contains original plan/bundle/capture, original and effective parameters, exact
occurrences, numerical artifact identities, failures and graded status. Worker
timings, directory placement and diagnostic text stay in separate receipts, so
selection and worker placement do not change source identity.

Grading requires an already completed immutable capture receipt and authenticates
its saved replay. It never performs first acquisition or opens the original
native attempt. Exact original-bundle occurrence pointers distinguish identical
bytes used for multiple roles. Mutated final input bytes remain retained partial
occurrences and are excluded as original grader operands. Working copies remain
separate and are not duplicated as original models. A single-key fetch retains
canonical JSON of the actual original requested job as its derived request input.

Both grading and selection run through existing `local_jobs` with the caller's
20 GiB RAM, 4 GiB scratch and no wall-time cap. The host streams custody checks;
full numerical JSON loading, parsing/calculation, and selection occur in their
separate bounded tasks. Neither worker selects native work or starts an episode.
The projection uses the actual R1–R5 pure projector, including source association
for rows, selected artifacts and populations, and all repeated selected checks.

## Failure and replay contract

Failures remain exactly `{stage, code, record_key}` internally. Capture/native
and sheet issue codes are retained verbatim. Copied common issue stages include
format, extraction, association, validation and calculation. Locators identify
the actual occurrence when unique, otherwise `bundle_ref#/failures/index` for a
native failure; the unsuccessful native summary uses `bundle_ref#/returncode`.
Missing outputs therefore keep separate original failure associations.

Caught exception messages that are not literal machine codes become bounded
failure codes. Existing literal code syntax is `[a-z][A-Za-z0-9_]{0,191}`. This
normalization applies only to caught exceptions, leaving existing capture codes
and their encoded file associations untouched. Generic worker fallback codes
are `native_infernal_preparation_result_worker_ValueError`, `..._OSError`,
`..._KeyError`, `..._TypeError`, and `..._IndexError`. Reader, launch and output
retention boundaries have their own bounded invalid/unavailable codes. Exact
exception text is retained in worker stderr or the worker diagnostic receipt,
outside typed failures. Synthetic tests verify this separation.

Successful `Publication` always has a real nonnull projection artifact and its
actual population. Saved success requires completed status and the original
Prepared failures. Failed projection seals `projection-failure.json`, then raises
`native_infernal_preparation_projection_worker_failed`, or
`native_infernal_preparation_saved_numerical_grading_unavailable` when numerical
selection has no retained grading. Replay raises the same sealed failure without
restarting a worker. A failed or uncertain grading task is likewise never retried
silently. With failed grading, explicit artifact-only selection still returns
valid captured artifacts; numerical population stays unavailable when numerical
selection fails.

`graded=True` means the pure task completed and its complete artifacts were
retained. It does not mean native success or passing validation checks. Root's
results completion concerns the requested acquisition/projection. A complete
acquisition may report missing-key diagnostics, independently of satisfaction of
the original fetch request; no validator-pass completion gate was added here.

## Verification and actual numbers

[NUMERICAL_EXAMPLES_001.json](NUMERICAL_EXAMPLES_001.json) indexes 11 populated
cases, full grading/sheet/calculation artifacts, native and grading receipts,
failure records, selected returns and offline replay. Every indexed file has
its measured SHA-256 and byte size. Four cases reuse unchanged original 252
captures; the other seven case paths execute tiny selected native operations
through 251's actual reservation/driver and existing lifecycle. The previous-SSI
case also executes its separate index producer. Synthetic custody/error tests
are explicitly labeled and are not native measurements.

| Actual case | Retained numerical result or validation |
|---|---|
| cmemit consensus | 12 residues, 8 GC, 12 canonical denominator, GC fraction 8/12; original case-preserving sequence retained. |
| cmbuild | 3 sequences, 12 alignment columns, 12 consensus nt, 4 pairs; paired fraction 2×4/12. |
| cmcalibrate | Local CYK header lambda 0.44855, mu_orig −2.53576, tail mass 0.1, 4,409 random hits, 10,000 calibration nt. Saved calculation gives mu_extrap −7.669156707154264 versus native −7.66916, residual 0.000003292845735636263. |
| cmstat score conversion | Local Inside E=0.01, 10 million nt, effective random-hit count 3,812,000; native 45.32 bits, saved calculation 45.3239102053337 bits, residual within native 0.005-bit half-width. |
| cmfetch key_file | Actual rc0 with 2 requested, 1 satisfied and 1 missing key; requested_keys_satisfied is fail. |
| cmfetch single_key | Key provenance points to canonical original request, with its operation/key/compiled-argv relationship validated by the common worker. |
| cmpress | Four original source/stem/current-attempt bindings; every source_binding and the quartet_binding pass. These establish captured producer association, not decoded index-entry integrity. |
| Previous SSI | Bytes are retained; source_binding remains unknown and metadata failure names the unavailable original producer binding. |
| Merge scores | All eight original partition arrays retained: lengths 3149, 3035, 4409, 3812, 3181, 3172, 3957 and 3315, totaling 28,030 scores. Each length matches its native score count. Original partition-request provenance remains explicitly unavailable. |
| Failed calibration | Actual rc1 and copied model survive as partial data with original failures. Pure grading can still complete. |
| ASCII conversion | Actual converted model measurements and format/identity validation remain separate from binary content claims. |

The saved calibration calculation is `mu_orig + log(tail_mass)/lambda`;
the negative mu values and signed residual remain unchanged. GC-dependent
partition-request identity cannot currently be authenticated by the frozen port,
including when the selected GC file is missing from capture. It stays unknown;
no command text or caller assertion becomes original producer proof.

The final full owned suite [publication_006](publication_006/receipt.json) passed
51 tests in 384.74 seconds. All owned sources were stable during that run; the
receipt honestly records root's concurrent views change from `65df80ed...` to
`385641ad...`. After the last success-receipt guard, the final targeted suite
[publication_008](publication_008/receipt.json) passed five tests in 29.54 seconds
with all recorded sources stable. Together they cover 54 distinct passing tests
(56 executions, two overlaps). Root's frozen integration run remains the global
checkpoint; this workload does not claim a complete episode path.

Historical receipts are retained. In publication_001, five test assertions used
the wrong expected row or assumed the single-key missing case had rc0; the real
rc0 missing case is key_file. Corrected assertions passed subsequent runs. In
publication_007, ten checks passed and three new tamper fixtures omitted the
canonical trailing newline, so they rejected before the intended guard. The
fixture serialization was corrected and all three targeted guard checks passed
in publication_008. No native data or production numerical formula was changed
to accommodate these test corrections.

Offline replay forbids subprocess/network, native plan discovery/acquisition,
all original attempt file reads, grader/recalculator/projector calls, and host
hydration of the full numerical artifacts. It returns the same authenticated
Prepared and Publication. Byte/source/occurrence/return substitution and tampered
success-receipt evidence reject. The evidence collector inspected all 55 stores
from the two indexed passing suites: zero Store observations. No target gene,
biological reference, annotation confidence, scientific credit or extra own
action was created.

## Final checkpoint and scope qualification

| Owned file | SHA-256 |
|---|---|
| native_infernal_preparation_result_publication.py | 4c58812054e63bf93824c77b716c801426a243039e39627b72c924f69e699f0f |
| native_infernal_preparation_result_worker.py | 4a611509dcd984a7f33da7b82f34269690a6078fd3dc53dca21c1658d64bdf46 |
| test_native_infernal_preparation_result_publication.py | a5ddbc20768014311fb72f4ca6074acf93f4164bc877e2dc83ddf86715496615 |
| test_native_infernal_preparation_result_worker.py | 16896b170a1473e69c8d96f159e9c8e1861e2d712c43d439e0301ef64945c469 |

Read the immutable original goal completely, required AGENTS/docs, the complete
native producer/capture/grading/publication paths and root's current complete
results consumer. Per the mandated reset, reread the original objective and all
16 principles verbatim after study and before closure, followed by the current
P2, R1–R5, common interfaces and numerical contracts. Original goal SHA-256 is
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.

No API/HPC/Aurora invocation, software installation, live scientific gene
investigation, complete binary decoder, or episode communication path is claimed
by these tests. Every preparation mode is covered by the common pure dispatcher
contract, but this workload's actual native examples cover only the modes named
above; broader mode and nested-boundary verification belongs to root/256/257.
