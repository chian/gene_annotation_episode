# C/D metadata verification 340

All checks used the existing `run_local_job` path, `.venv/bin/python -B`,
20 GiB RAM, 4 GiB scratch and no wall cap. Each check retains selected command,
policy, source bytes and hashes before execution, after hashes, stdout, stderr
and a native lifecycle receipt. The receipts report cgroup MemoryMax 20 GiB,
zero swap and infinite runtime. Existing scratch enforcement retains its
documented monitoring/possible-overshoot qualification.

| Check | Actual result | Meaning |
| --- | --- | --- |
| check001 | 140 passed in 5.33s | Both existing metadata suites after the bounded implementation. |
| check002 | 188 passed, 1 failed in 8.03s | Expanded tests. The single failed assertion expected a different rejection code for declaring a v2 sheet v1; the actual closed v1 validator correctly rejected it. |
| check003 | 649 passed in 14.12s | Corrected the test expectation to the actual `blast_sequence_database_inner_binding_fields_invalid`; no production change. Ran 9 relevant suites on one stable source snapshot. |
| check004 | exit 0; retained numerical replay | Saved standard/PSI/DELTA calculations with preparation, FASTA/native parsing, path reads, processes and sockets forbidden. |
| check005 | exit 0; source identities verified | Source/receipt/example identity packaging and exact preservation check of335's two lines; no scientific test rerun. |

check003's suites are both owned metadata files plus sidecar metadata, shared
FASTA identity, public sequence database, explicit associations, generic database
grader, iteration inputs and iteration calculators. Full selections are in
`selection.json`; no unrun broader suite is implied.

The retained M332 v1 example is loaded from its original artifacts and compared
against the entire new v1 sheet and calculated component dictionaries. Its
original source-address conflicts, native 20/18 scores and null function weights
remain. A separate v2 input uses339's exact new descriptor/payload and original
FASTA/assignment JSON. Both ordinal 0/1 proofs and associations survive.

The v2 numerical oracle retains 10-aa references with symbol digests
`be5884f5108f13d3e64bda3992e916bc204e704322e49bb1623ef9a7b496e64b`
and `f287ecbc4ac4c62be5c3deae84ca86ae001be2061987568c4a1d8eedebd55f64`.
The unchanged kernel gives masses 1/.25 and weights .8/.2 at T1, 2/3–1/3 at T2,
and 2/7–5/7 with actual retained census total 1000 / F 100 / G 10. Native scores remain
20/18. Equal complete symbols remain one group with explicit F/G split .5/.5;
absent assignments produce no function weights. No function is derived from a
header, ordinal or successful proof.

Tests also cover valid 0 / invalid 1 / valid 2 and unavailable 3, duplicate headers,
wrong proof ordinal/source/format/digest/length/molecule, cross-record description
links, same-record sequence and metadata conflicts, mixed JSONv1/FASTAv2 offsets,
all five standard reference-axis modes, whole-file receipt tampering, null JSON
locators, closed locator objects, nonempty-pointer payload rejection with an
independently valid descriptor, absent proof and retained native measurements.
Saved proof/locator/document/symbol tampering and declared-v1 downgrade are
rejected. Actual PSI/DELTA result-worker calculation invokes the existing saved
iteration dependency with retained v2 metadata and no FASTA reopen/reproof.

check004's canonical saved hashes before and after recalculation are identical:

| Sheet | SHA256 |
| --- | --- |
| Standard v2 | `5e20ed3daa0531369be37869cd768ee76da33cfc270924b55fe04382d47baa91` |
| Standard census v2 | `7b0ce5dc7b663667ab8f1d54775986328b794ff1bfa9ca2b3f400c876a137496` |
| PSI | `851a4578d98618fbd9f452ea6ea1b9e6d2316df42f08b863167df5726967ec25` |
| DELTA | `2c94970abcd06dc57d0d0edc25eccc94854ac5cfb1c9a82ce157650d58c2ecd7` |

The immutable goal was read in full and its purpose/all16 principles reread
verbatim after source and retained-data study. Accepted337, acceptance and both
addenda were reread before handoff. AGENTS and required goal, episode, estimation,
practical execution, task/steering and tool-grader design instructions were read.
Only the two owned modules and their corresponding tests changed in production;
new scripts/evidence are in340. Permanent decisions and progress accounting were
not edited.335's comparison operands remain exact.341's requested short source
pin was honored and released before this handoff.

The scientific evidence here is synthetic/retained-format data, not live native
database execution. Full worker request/reuse and episode communication remain
integration343/root's work. No credit or completion count is inferred from these
test totals.
