# Additive implementation-binding correction after root review

Root identified a concrete existing-reader limitation after reading the frozen proposal. This note clarifies the future implementation boundary; it does not modify the frozen proposal/IO/TASK, source records or user goal.

The proposed `Kd_test`/`Kd_reference` selections in FUNCTION_IO_001.md are **future common-sheet roles**, not evidence of an installed, source-bound Kd operation. The inspected current `literature_kinetic_inputs.py` defines `PARAMETER_UNITS` only for `Km`, `kcat` and `catalytic_efficiency`. Its input meanings do not include Kd. `COMPARISON_VALUES.subject_relationship` supports `same_molecule_and_construct`, `different`, `unknown`, `conflicting`; `literature_kinetic_calculations.py` requires `same_molecule_and_construct` for its supported comparison. A WT-versus-mutant contrast deliberately changes the construct and must not be mislabeled to pass that path.

Thus the common-sheet implementation must explicitly do the following unfinished work:

1. Establish and verify a possessed, source-bound route for each Kd estimate with the correct binding-parameter meaning, subject/construct, units, conditions, normalization, uncertainty and source witness. If an existing binding-reader path is reusable, verify its actual selected storage/typed-return/replay binding first. This note does not establish that route and makes no repository-wide claim that no Kd reader exists.
2. Preserve Kd and Km as different estimands. Their common µM units cannot authorize substituting one for the other or attaching one parameter's uncertainty to the other.
3. Implement explicit intended-variant subject relationships and native same-parameter cross-arm contrasts in the future common assessment. Do not weaken or reinterpret the existing kinetic comparison contract, or silently relabel mutant and WT as the same construct.
4. Verify the actual selected native kcat/Km rows needed by the common calculator. Defining a selector role does not prove possession or a registered consumer path. The source paper supports the central quantities, but their common comparison and cross-arm uncertainty remain unimplemented.

The occupancy/inverse calculations here are standalone research calculations, not existing kinetic-reader results. The inverse free S is a **model-fitted sensitivity point**, not a new source fact, source concentration estimate, independent experiment or validation. Forward substitution proves the algebra; it does not validate the physical model or any missing scientific relationship.

This owner subsequently inspected only current `literature_kinetic_inputs.py` lines1–115 and `literature_kinetic_calculations.py` lines295–325 to verify the parameter enum and subject-comparison restriction. The complete kinetic implementation was not re-audited, and no kinetic reader/calculator or episode operation was executed. These engineering inspections do not open another scientific paper and do not replace the already completed own post-paper reset.

MANIFEST_002.json includes this additive note and records hashes/limited extents for the additional implementation inspection. MANIFEST_001.json and every previously frozen scientific document retain their original bytes.
