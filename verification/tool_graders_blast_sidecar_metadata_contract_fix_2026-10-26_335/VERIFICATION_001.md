# Sidecar metadata correction 335: verification

2026-10-26. The production correction is exactly two comparison operands in
`gene_annotation_episode/native_blast_database_metadata.py`:

- `_lower_payload`, line440: hash capture role `metadata`, retaining the logical
  sidecar role's original selected-identity lookup.
- `_resolve_document`, line730: hash capture role `metadata`, retaining the
  sidecar role lookup, full selected-identity equality and null-capture handling.

Both N implementations already emit and require this key. No N code, schemas,
original identities or selected role meanings changed. `SOURCE_DIFF.patch` and
`SOURCE_AFTER.json` verify that applying precisely those two replacements to the
retained original source produces the final production file byte for byte.

| Source | SHA-256 |
| --- | --- |
| Before M | `c1007308fffd828fca4a8c5a26aa36b442d0a28ee8ed184917b549bb0bbb433c` |
| After M | `398d992c4d9841bdbe4b2414f51fdacea2a757c3cd6c5d0e9d9019440c8cfcec` |

## Actual checks and retained failures

Every run used `.venv/bin/python -B` through `run_local_job` with
`LocalJobPolicy(20*1024**3,4*1024**3,None)`. Receipts establish the 20 GiB cgroup
memory maximum, zero swap, 4 GiB scratch monitor/per-file limit and infinite
runtime limit; no wall-time budget was introduced. Scratch monitoring retains
its existing possible-overshoot qualification.

| Receipt | Actual result | Interpretation |
| --- | --- | --- |
| `check001_before/receipt.json` |24 passed, 24 failed, 27 setup errors | Initial harness omitted the parent of pytest's basetemp directory. Retained unchanged. Only the 335 runner was corrected; production M was still original. |
| `check002_before/receipt.json` |24 passed, 51 failed; 3.98s pytest | Correct harness, original M. Both roles fail public validation on actual retained native6/standard producer shapes. Actual native6 preparation drops the selected source relations. Old logical-role keys are incorrectly accepted. |
| `check003_after/receipt.json` |144 passed; 5.15s pytest |75 new sidecar cases plus 69 existing `test_native_blast_database_metadata.py` cases. Source hash is unchanged throughout this run. |

The existing standard metadata suite is owned and run independently by332 after
notification of the new shared-source hash.335 did not rerun that suite or any
E/full episode/worker suite. Existing native metadata tests were run once after
the correction. These counts are test cases, not tools or scientific results.

## Concrete examples

`fixtures/INDEX.json` pins the exact original N313/N331 bundles, independent
selected plans, full captured bytes and their hashes. Tests independently call
the appropriate public N bundle validator before public M validation. Standard
jobs remain standard jobs; no native6 execution wrapper is fabricated.

- N313 psiblast: the 22-byte preparation input manifest has key
  `database-metadata-3c9b7669f91fc68d75697f7cb7bef9e4c4c4760c772277a2803113acc4432031`;
  the 48-byte offline configuration has key
  `database-metadata-5622a49ad76973019c7021291505680b9afb12882c74fc452d66222b2c450b1b`.
  Both fail before and validate after. Native6 preparation retains zero of the
  two requested relations before, and both original relations after.
- Retained N331 blastn and blastp: preparation/offline sidecars are 36/35 bytes.
  Both roles validate after correction with their original database owner,
  selected identity and captured source reference. They formerly fail with
  `sidecar_capture_key_conflict`.
- Retained N313 shared-identity case: both logical roles legitimately point to
  one 22-byte captured artifact. After correction both document addresses and
  both original sequence-record source relations remain; the capture is not
  duplicated or converted into two independent evidence contributions.
- Two new deliberately synthetic producer fixtures (native6 and standard5)
  give the two roles identical bytes at distinct selected paths. Each N producer
  emits two distinct keys, both accepted by M. Swapping the keys fails both N
  validation and public M validation; native6 preparation also rejects the swap.
- The exact pinned M332/check003 counterexample is N-valid and retains its old
  invalid result. Public M now accepts its supplied JSON sidecar. A nonexistent
  literal JSON pointer remains invalid.

`EXAMPLES_001.json` contains these before/after outputs, normalized sources,
actual byte sizes, original capture keys and normalization maps. Complete failed
and passing output remains in each check's temporary directories. The existing
synthetic N fixture commands ran twice before and twice after (one native6 and
one standard5 per substantive run); these are simulated executables, not BLAST.

Counterexamples cover both roles and job shapes: arbitrary capture key, old
logical-role key, changed selected original path/artifact reference, absent
selected sidecar, wrong document hash/size/bytes, undeclared source, unsupported
text pointer, nonexistent JSON pointer, missing document, duplicate document,
wrong native6 sidecar identity, wrong/null capture, duplicate role and changed
retained bytes. Native6 resolver failures preserve the valid sibling and its
original ordinal/pointer. Public validation is tested with I/O, subprocess,
socket and native6 job-validator entrypoints forbidden. Inputs remain unchanged.

## Inspection and scope limits

Read the complete immutable objective/all16 principles, AGENTS and required
design records; accepted327 with addenda001/002; M317 and relevant314 address,
document-catalog, population and verification contracts; N313/002/004/005.
Traced both N `_databases` capture functions, artifact construction and complete
bundle validators; M's complete public validation/lowering, byte-catalog,
document resolver and native6 preparation paths; and332's supplied-byte source
resolution and metadata-preparation consumer. The correction contract records
root's explicit expansion from one comparison to both consumers of this defect.

Original objective/design records, original332 failure, retained N source
records and pinned fixture bytes were verified unchanged. The only production
edit is the two-line M correction; the only new test module is
`tests/test_native_blast_database_sidecar_metadata.py`. Other335 files are the
additive contract, fixture retention/runner scripts, source snapshots/diff,
source/custody manifests, examples and test receipts.

No real database BLAST, API, HPC, installation or download ran. This verifies
metadata input compatibility and the native6 preparation path, not deployment,
new native scientific measurements or complete episode communication. No
scientific field, formula, source schema, return form, credit, continuation,
episode choice or historical action changed. No older frozen worker generation
was regenerated or assigned the new implementation hash; new interpretations
will use the changed source identity through the existing identity mechanism.
Root owns any subsequent integration check and accounting.

Before closeout, the objective and entire sixteen-principle block were reread
verbatim from the immutable attachment, followed by the complete current335
correction contract. This is implementation discipline, not a runtime action.
