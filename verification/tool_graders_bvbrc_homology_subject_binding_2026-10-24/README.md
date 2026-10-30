# Pairwise reference association correction

The original C4 bridge accepted a subject digest without comparing it to the
reference sequence actually submitted. The retained counterexample changes only
the subject digest from SHA256(MKTGG) to SHA256(AAAAA); the earlier bridge still
returned three paired residues, coverage .6/.6 and identity 1. This was a real
association defect, not a new scoring requirement or a method_loop defect.

`bvbrc_homology_subject_binding.py` now checks the submitted reference operand,
complete FASTA, actual member count, length, sequence digest, molecule, source
membership and exact native identifiers. The C4 adapter invokes it after native
decoding and before pairwise sheet construction. A contradictory digest now
leaves the requested pairwise quantities null and returns specific requirements.
Native data and the original supplied assertions remain retained. Unrelated
native counts are not converted to zero or discarded. No scientific formula,
episode type, action count, continuation rule or method_loop implementation changed.

The helper is part of the installed implementation digest, now
`6431e9b48d6015056915c610f125653a9bbb886e0195bd1a24a1fc531896a809`.
Source-complete synthetic pairwise fixtures replace earlier asserted reference
identities in the adapter tests. Earlier permanent verification records remain
unchanged; they did not establish this association check.

The connected focused group passed **158 tests in 18.61 seconds**: 76 adapter,
71 new subject-association and 11 library tests. These counts are not additive
to prior runs that tested the same cases. The exact command, result and JUnit
record are retained here. A separate preflight validates all five Homology
programs in raw, processed and tabular representations with actual synthetic
reference FASTAs and calculated identities.

The actual pairwise composed Workflow and isolated installed-wheel verification
are running separately. This record does not claim those checks passed, nor
does it claim live BV-BRC, native BLAST, HPC or configured-model execution.
The earlier complete database paths passed at their preserved previous pin:
three launch/results/replay tests and four library/scientific/root tests. The
pairwise-only correction does not retroactively reprice or rewrite those runs.

The exact source-value and handoff contract is the additive document
`docs/TOOL_GRADER_BVBRC_HOMOLOGY_SUBJECT_BINDING_2026-10-24_001.md`.
