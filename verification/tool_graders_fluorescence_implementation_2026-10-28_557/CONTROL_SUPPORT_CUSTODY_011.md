# Missing support bytes do not authorize a control comparison

Additive implementation clarification to008. The user goal is unchanged.
Owner B found that preserving declared comparison metadata while reporting a
missing support artifact could still let the existing calculator produce a
control difference from an unauthenticated comparison basis. Whole-worker
analysis_complete=false alone does not make that numerical cell safe to return.

Retain original definitions, associations and observed event values. Do not
clear a basis, rewrite units, erase valid samples, or fetch a substitute file.
Independent counts/intensities continue to describe their actual retained data.

Root provides this pure field-dependency port in fluorescence_event_contracts:

```python
control_comparison_files(sheet, *, control_key) -> list[dict]
# Each row is {file:FileIdentity,pointer:str}; pointer addresses that exact
# file identity in the saved sheet. Original deterministic encounter order.
```

It validates the sheet and returns the files used by the current control
comparability definition: the control pair comparison_basis.evidence_file;
both primary-domain comparison_basis.evidence_file values when present; and,
along both complete gate ancestry chains, threshold-channel analyte.file and
threshold-domain comparison_basis.evidence_file when present. Include each
field location once, even if identical bytes support several fields. It does
not read any file or assert biological comparability. Preparation parameter
files and other metadata remain recorded inputs; this port follows the exact
fields on which the existing control comparability calculation depends.

After native batch assembly and before calculation, B checks these identities
against support_input roles whose exact original bytes could not be verified.
For each affected control append the existing core Issue with stage=input,
control_key set, other locators null, and code source_unavailable for an absent
file or retained_artifact_mismatch for wrong bytes/identity. Preserve the
specific support role/index and original file identity in the existing
capture/worker failures and original Job. No fallback source read, new issue
schema, arbitrary prose, or altered original definition is required. Deduplicate
identical Issues in their original encounter order. Saved recalculation retains
these Issues; it cannot silently rehabilitate the original unavailable support.

The single shared calculator's control() consumes those located input Issues.
It preserves each as an operand/qualification and sets all numerical differences
for that control to null/unavailable. Missing support is distinct from an
observed incompatible control pair: do not invent control_pair_incompatible
merely because bytes are missing. Existing left/right fractions and independent
counts/intensities remain their actual calculated values. No return adapter
postprocesses a calculated number into another score or silently drops the
requested control cell.

Root owns the helper, narrow shared-calculator change and
tests/test_fluorescence_control_support.py. B owns its existing worker translation
and tests. C's typed receipts/return schemas do not change. Native practical
completion still fails for missing required original support capture; saved
calculation completion follows010 and can return appropriately unavailable
comparison cells without reacquiring data.

Verify missing versus mismatched support, exact support-file dependency
locations, unrelated control/sample preservation, unchanged observed fractions,
saved-only recalculation, selected return equality and no fabricated zero.
