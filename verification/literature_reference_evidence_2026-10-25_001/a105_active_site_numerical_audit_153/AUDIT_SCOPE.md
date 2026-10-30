# Independent A105 numerical audit 153

This workload uses synthetic UTF-8 source text and explicitly controlled
source-span/interpretation selections. It reads no primary paper or retained
paper-specific packet and makes no model call. It supplies engineering evidence,
not experimental findings, scientific axis completion or W05 credit wiring.

Only this verification directory and
`tests/test_a105_active_site_numerical_audit_153.py` are owned by this workload.
No production, amendment, goal, controller or foreign tool-grader file is edited.
`GOAL.md` is neither read nor used.

## Three independent cases

| Synthetic arrangement | Expected numerical components | Scientific restriction |
|---|---|---|
| 0.3 mg/mL, 30 kDa per monomer, 2 uM titrated sites; equivalent 300 ng/uL, 30000 Da, 2000 nM | C = 10000 nM; density = 0.2; conditional one-site fraction = 0.2; conditional denominator factor = 5 | Equivalent units and reciprocal aliases do not provide independent replication. Nominal titrant basis stays explicit. Regression SD remains its source kind; full joint fraction uncertainty remains an implementation gap. No rate is modified. |
| Same protein concentration, 16 uM sites, other/one-site stoichiometry | Density = 1.6; conditional factor = 0.625 | Other stoichiometry leaves biological fraction unavailable. With one-site interpretation, fraction is unavailable for physical inconsistency while measured density remains 1.6. No clamping or invented probability. |
| Per-dimer or missing molecular mass; separately zero active amount and zero mass concentration | A = 2000 nM survives missing monomer conversion. Measured A = 0 supports fraction 0; reciprocal C/A is undefined. A positive A survives C = 0 while A/C is undefined. | No implicit dimer-to-monomer coefficient, no missing-as-zero conversion, and numerator zero is distinct from denominator zero. |

## Read provenance

Read completely before audit implementation:

- Original user goal attachment `/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt`.
- Root `AGENTS.md`.
- `docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md`.
- `research/experimental_scoring_review_2026-10-23/AGENTS.md`.
- `docs/EPISODE_STRUCTURE.md`, `docs/TIME_AWARE_ESTIMATION.md` and `docs/TASK_AND_STEERING.md`.
- Active-site input/calculation/storage/render/prompt modules available during development.
- Complete `literature_assay_inputs.py`, `literature_rate_native_inputs.py`,
  `literature_rate_domains.py` and `literature_experimental_contracts.py`.
- Complete relevant `domain.py` functions `canonical`, `identity`, `obj`,
  `_validator`, `validate_schema` and the `REF` definition.
- Storage adapter's inherited constructor, native-source custody methods and
  receipt methods were inspected for context; they are outside the executable
  mathematical claims of this audit.

Initial combined tool outputs were truncated. The goal, root instructions,
W04 instructions, research instructions and execution/estimation documents
were subsequently reread separately in complete untruncated outputs.

The reader/calculator and reused fractional-number reader were reread completely
after owner152's stable-ready signal. `READ_PROVENANCE.json` records their exact
SHA-256 hashes, which match the latest passing invocation. `run_audit.py` retains each pytest invocation's
stdout/stderr, exit status and all source hashes before/after execution.
No passing moving-tree run is described as root's frozen joined proof.

## Actual verification outcome

Two invocations are preserved; both passed the same three independent cases.
The second strengthened zero checks to assert the exact failure reasons and
also verifies that a source-reported fraction of zero survives. These runs do
not add up to six unique cases.

- `check_20261027T185345.338539Z`: 3 passed in 0.31 s.
- `check_20261027T185401.033997Z`: 3 passed in 0.30 s; no audited file changed
  during the invocation. There were no failing pytest invocations.
- Reader SHA-256: `714e8086c217b2c6353c466f4e366d6bf470f9d98b89fc5d6057170d32d8eb27`.
- Calculator SHA-256: `aa11b14e757a1c15b0d0729e8bcb81e22e5bbd07d22561549635b050e76fcaf2`.

All expected numerical values in the table above were observed. The individual
active-site concentration and source-reported fraction remain exactly zero in
the zero-active case; the conditional fraction is zero and the inverse has
`zero_active_site_concentration`. The zero-total case instead has
`zero_total_monomer_concentration` for density. A dimer molecular-mass basis
reports `molecular_basis_per_dimer_coefficient_unimplemented` for C, while A is
preserved. Missing MW reports `source_measurement_unavailable` for C.

`SYNTHETIC_NUMERICAL_OUTCOMES.json` retains the populated numerical sheets for
the variants within these three cases. All examples remain synthetic. No
unresolved numerical defect was found within this exercised scope. The initial
development-stage zero rejection was raised directly with owner152 before
stable-ready; owner152 corrected it before either invocation, so no failing
test is erased or claimed to have been run.

## Unverified by these three checks

No actual literature-model run, typed child-to-parent admission, complete
method_loop/controller observation accounting, cold repository replay or
end-to-end investigation is exercised. Root and owner152 own those checks.
