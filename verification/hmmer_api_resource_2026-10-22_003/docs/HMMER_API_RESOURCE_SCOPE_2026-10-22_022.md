# Explicit fixed-case estimator construction scope022

Root read complete case_execution.py, application_execution_binding.py and
independent_execution.py against isolated generation003. A real reconstruction
gap exists: prepared_case_bindings always supplied ResourceToolEstimator() v2,
so an explicitly timing-enabled assembled factory cannot reopen the v3 choice
through the fixed_case worker. A test-only replacement is insufficient as the
final caller implementation.

The bounded additional workload owns only case_execution.py and new
tests/test_case_resource_estimator.py in generation003. Add optional
PolicyBindings.resource_estimator: ResourceToolEstimator | None = None, validate
that a nonnull value has exactly the existing ResourceToolEstimator type, and
record its exact as_record() under policy-binding.json definitions.resource_estimator
only when explicitly supplied. Default policy output/marker fields remain
byte-for-byte unchanged. At prepared_case_bindings construction, supply that
same caller object if present, otherwise the original ResourceToolEstimator().
No phase, estimate, controller, scalar or duration formula is selected here.

Existing policy source/parameter/definition equality, marker pins and worker
_check_bindings enforce the original choice on resume. Do not infer v3 from a
job, another descriptor or library entry. Do not change independent_execution,
shared method_loop or runtime saved binding formats for this addition.

Verification must cover rejection of untyped objects, old default shape and
estimator behavior, explicit v3 in actual prepared_case_bindings, exact recorded
choice and immutable resume mismatch. C's separately owned actual fixed_case
reconstruction must use this public field and no estimator replacement shim.
Tests are engineering evidence, not configured-model scientific behavior.

This scope authorizes isolated implementation only. Original active source,
existing policy snapshots, scientific state and all prior records stay unchanged.
