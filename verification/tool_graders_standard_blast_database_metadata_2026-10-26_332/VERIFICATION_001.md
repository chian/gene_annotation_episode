# M332 verification record

Final command:

```text
.venv/bin/python -B verification/tool_graders_standard_blast_database_metadata_2026-10-26_332/run_verification.py check009
```

Result: **70 passed in3.86s**. The existing local_jobs lifecycle enforced
LocalJobPolicy(20*1024**3,4*1024**3,None):20GiB memory,4GiB scratch, no wall cap.
The actual service elapsed time was4.393140282s and observed scratch was2248704
bytes. Exact selected command, policy, enforcement and exit status are retained
in [selection](check009/selection.json), [receipt](check009/receipt.json),
[stdout](check009/stdout.txt), and [stderr](check009/stderr.txt).

## Coverage and checkable numerical examples

| Accepted case | Verified behavior |
| --- | --- |
| M1 | Real standard job through the unchanged two public metadata tuples; original job metadata and selected-results metadata; wrong tuple, bytes/digest/pointer, unreceived documents, duplicate descriptors and original manifest-slot drift; pure preparation/population and unchanged inputs. |
| M2 | Multi-record native FASTA, case retained separately from normalized symbols, exact received snapshot identity, repeated native names/equal lengths ambiguous, explicit DNA/RNA types, missing/wrong/duplicate subject snapshots. |
| M3 | Complete JSON and FASTA references; wrong molecule/length/digest, HSP fragments, duplicate proofs and missing sources retain native scores; translated nucleotide references require nt proofs; demonstrated identical complete sequences group once. |
| M4 | Sparse original hit/HSP/description ordinals, independent metadata merging, dropped metadata units preserving original payload pointer, conflicting taxon does not borrow function. |
| M5 | Full244nt versus reported186nt and selected[29,215); native coordinates30..215 remain unshifted; first translated paired interval[212,215),62aa columns occupy186nt. |
| M6 | All five standard programs plus tblastn PSSM alias; exact attempt/manifest/report identity; native database path retained separately from selected semantic identity. |
| M7 | Missing optional metadata preserves rows, release/scope/count conflicts disable only adjustment, feature-only function stays in retained source and is excluded from the whole-contig kernel. |
| M8 | iupacaa, ncbieaa and ncbistdaa masters; exact ACD column map and explicit received master-subject relationship; missing, compound, invalid, gapped and same-length impostor cases; no iterations. |

The numerical baseline is retained as
[inputs](check009/temporary/pytest/test_M1_real_standard_job_publ0/supplied_inputs.json),
[sheets](check009/temporary/pytest/test_M1_real_standard_job_publ0/sheets.json) and
[components](check009/temporary/pytest/test_M1_real_standard_job_publ0/components.json).
The unchanged303 kernel gives bit scores20 and18, masses1 and0.25, unadjusted
weights F=0.8/G=0.2, and census-adjusted F=2/7/G=5/7 for actual supplied synthetic
counts100/10 out of1000. Full-query paired coverage is4/8=0.5; selected coverage
is null because no interval was selected. These are conditional reference
weights, not annotation confidence.

The translated example is retained as
[inputs](check009/temporary/pytest/test_M5_retained_paired_range_0/supplied_inputs.json),
[sheets](check009/temporary/pytest/test_M5_retained_paired_range_0/sheets.json) and
[components](check009/temporary/pytest/test_M5_retained_paired_range_0/components.json).
Full-query coverage is186/244 and selected coverage is186/186=1.

Three PSSM cases retain inputs/sheets/components under
`check009/temporary/pytest/test_M8_pssm_supported_exact_m{0,1,2}/`.
The complete ACD master map is column0→position0/A,1→1/C,2→2/D.
No PSSM is constructed or consensus generated.

Saved-artifact validators are exercised for every populated fixture. Dedicated
sequence and PSSM reuse tests prohibit all preparation/population hooks, collector,
metadata public validator, native parser/master extractor and file/process/network
I/O. Closed fields, original normalized slots, source identities, subject links,
full proof symbols and saved binding/source relationships have tamper cases.

## Native versus synthetic evidence

All database job envelopes, manifests, reports, subject snapshots, assignments,
counts and PSSM text are explicitly synthetic fixtures. Synthetic JSON reports
carry synthetic=true and not_native_measurements=true. No local database BLAST,
HPC/API scientific job, installation or download ran.

Only one unchanged retained actual paired report was read for format/geometry:
`verification/tool_graders_blast_pairwise_2026-10-26_294/native_ranges/blastx_range_reverse_json15/attempt/report.json`,
SHA256 d565f98c56572894b4507e873fac0cf3ac848b29891aa7f654131b101426e227.
It has bl2seq and a subjects target. Its byte identity is asserted unchanged;
it is never relabeled as database execution. The separate database range fixture
is deliberately synthetic.

## Preserved failures and dependency correction

| Run | Outcome |
| --- | --- |
| check001 |52 passed initial M suite. |
| check002 |Runner source-snapshot bug before any local job/test; failure.json retains exact failure. Node selectors were subsequently separated from filesystem paths. |
| check003 |1 failed: N-valid preparation sidecar rejected by old public metadata validator. Exact original counterexample retained. |
| check004 |52 passed,1 same shared sidecar failure. |
| check005 |64 passed,2 shared sidecar failures for both logical roles. |
| check006 |66 passed,2 same sidecar failures. |
| check007 |69 passed against corrected dependency; examples retained. |
| check008 |69 passed; source/test snapshot and multi-record FASTA counterexample retained. |
| check009 |70 passed; final implementation/dependency bytes and hashes, including assembly source/linkage-source regression. |

Root-assigned335 corrected the shared validator's capture-role comparison while
preserving logical sidecar-role identity.332 did not edit shared source and did
not weaken tests to hide the failures. Actual dependency hash in check009 is
398d992c4d9841bdbe4b2414f51fdacea2a757c3cd6c5d0e9d9019440c8cfcec.

R333's retained check002 exposed an additional valid assembly payload that fresh
M accepted but saved M validation rejected. The saved source-substitution check
omitted the public assembly.linkage_source field. Check009 includes the narrow
fix and an M regression retaining separate assembly/source-link documents and
the supplied0.95 completeness/1.25 contamination fractions. No R test or shared
source was changed by332; the original consumer failure remains in333/check002.

## Authority, hashes and reset

Initial complete reads included the immutable goal, repository AGENTS/GOAL,
EPISODE_STRUCTURE, TIME_AWARE_ESTIMATION, practical execution documents, accepted
327 plan/acceptance/addenda,331 actual contracts and handoff, the actual public
metadata validator, collector, native PSSM/master and303 implementation paths.

Authoritative goal SHA256:
11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7.
Accepted327 plan SHA256:
c6f66f93472fcb32798473158153ab3158920f950b79ab65dfcda88af6ff07f1.
Final module SHA256:
4ecc1f0584d3bdde2e394c50fd0bed5c48da60c399f95b4957d5f37369f5cfba.
Final test SHA256:
7ce140a83e416a0de60e8cf778edb779f1fbe15860ab1b1b18a1461fed9cc86f.
All consumed implementation hashes and exact source snapshots are in
[check009/source_snapshot.json](check009/source_snapshot.json).

The required instruction is:
“After completing work on each tool, and before moving to another tool, reread
the objective and the entire DESIGN PRINCIPLES block above from the authoritative
goal text. Read it verbatim.”

The objective and complete16-principle block were reread verbatim after retained
native-output study before implementation, and again before this completion
record. The accepted current M contract, acceptance and both addenda were reread.

No complete episode integration or deployment is claimed. R/E remain their
separately owned consumers. The measured existing multi-record FASTA address
limitation is preserved in [LIMITATION_001](LIMITATION_001.md).
