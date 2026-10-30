# Additive215 correction: exact covariance symmetry and scope limitation

This corrects the bounded repair record without replacing its original receipts or the frozen root220 pin001.

## Exact symmetry

Root220 ROOT_ASYMMETRY_PROBE_001.json independently demonstrates that the prior v2 validator accepted the exact integer covariance [[10**18,10**17],[10**17+1,10**18]]. Its two unequal off-diagonal integers become the same binary float when NumPy projects the matrix; comparing only the float array therefore failed to detect asymmetry. The original passing tests did not cover this counterexample.

The v2 source validator now compares each retained raw numeric entry with its transpose entry before creating the NumPy float array. Exact disagreement returns the existing symmetric_covariance_required failure. Finite/shape validation precedes this check, and the existing float PSD check follows it. There is no covariance repair, symmetrization, schema change or recalculation of saved outputs.

The new regression goes through the actual selected literature.assay.components.populate operation with actual possessed q/E operands and source-owned covariance. The asymmetric case returns invalid, symmetric_covariance_required:covariance, and no changed/output record. Its exactly symmetric large-integer contrast completes, passes the exact typed form boundary, preserves the retained integer covariance and matches an independent Fraction Jacobian oracle. Both fixtures are explicitly synthetic; their magnitudes are numerical test operands, not paper measurements.

Only literature_compiled_assay_inputs.py and the existing215 test file were reacquired and edited. Other shared files belong to218. FINAL_CODE_HASHES_002.json identifies the exact corrected files; original001/002 receipts are preserved. This correction targets the v2 named-subset validator; it does not rewrite legacy validation history or saved v1/v2 projections.

## Qualified numerical-scope claim

Root220 ROOT_CONTEXT_SCOPE_PROBE_002.json establishes a separate inherited metadata boundary defect. An actual selected v2 request for only measured_endpoint_per_selected_amount_propagated_variance returns that numerical component, but a valid broad assay.condition source witness is copied into assay_meanings.condition and includes an unrequested distinct residual value 0.001 per_min_squared. This mechanism originated in v1. Root's attempt001 used invalid conditions instead of condition, so only attempt002 demonstrates this finding.

The earlier REPAIR_001.md statement that derived-only returns do not disclose unrequested primitive values or covariance matrices describes the formal numerical operand fields. It must not be read as an entire-row numerical-scope guarantee: arbitrary source context literals can also carry numbers. Narrow component selection and exact schema validation do not resolve that leakage. No context-field fix, schema alteration or historical value change is included in the current authorization.

The future compatible common projection must retain full original witnesses in host custody while returning context scoped to the requested information. The prospective221 PROJECTION_SCOPE_ADDENDUM_001.md calls for artifact/coordinate ownership masking of unrequested numerical owners plus a bounded guard for broad statistical context, preserving concise relevant temperature/pH context. A broad witness that cannot be scoped without new interpretation should return an explicit implementation-scope-unresolved condition, not falsely assert the source lacked information. This requires a separately versioned common-row/projection path, with selected-operation/admission/reconstruction tests for numerical material embedded in condition, preparation, uncertainty and assay descriptions. Existing v1/v2 schemas and saved rows remain readable unchanged. This is a recorded future implementation requirement, not a new scoring policy or a claim that the defect is fixed.
