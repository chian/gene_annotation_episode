# Exact BLAST archive-member digest propagation

Implemented only the frozen additive port in `blast_report_collection.py`:

```text
search.normalized.native.archive_member = {
    ordinal: original ZIP member ordinal,
    name: original ZIP member name,
    sha256: SHA-256 of that member's original decompressed bytes
}
```

`_archive` passes `artifact["members"][ordinal]["sha256"]` into the optional
`member_sha256` argument of `_collect_document`, which forwards it to
`_json_search`. The latter adds the field to the existing archive-member
descriptor. The container digest remains `normalized.native.sha256`.
Standalone JSON keeps `archive_member: null`; the tabular path is unchanged.
No digest comes from reserialized JSON or a filename lookup.

The only production source edited is `gene_annotation_episode/blast_report_collection.py`.
The only test source added is `tests/test_blast_archive_member_digest.py`.
Existing tests, the legacy reader, permanent instructions, the inventory,
execution, grading calculations and worker 303's files were not edited.

## Inspected path and contribution boundaries

- Read the complete collector, including artifact validation, `ZipInfo`-based
  archive reads, manifest diagnostics, native search branches, and the tabular
  path. Every ZIP descriptor is appended before any member can be skipped, so
  the descriptor list retains the original ordinal even for nonreports or
  unreadable/malformed siblings.
- Read the original single-query archive reader and `parse_blast_json` return
  construction. Its exact `{ordinal, name}` member descriptor remains unchanged.
- Read `blast_program_context.py`, `blast_pairwise_results.py`, the complete
  `native_blast_result_worker.run` consumer and `native_blast_hsp_views.py`.
  The new field is storage identity, not a new measurement, result row, episode
  action, observation, scoring component or continuation decision.
- Read the entire retained NCBI manifest and report. They contain one query,
  seven hits and seven HSPs. The original hit/description associations, native
  measurements and JSON layout are retained.
- Worker 303 was notified of the exact new field after it became available.
  Validation of its separate `ReportSource.member_sha256` contract belongs to
  that workload. No historical collection was repaired or rewritten here.

## Verification actually run

All runs used `.venv/bin/python` through the existing `local_jobs.run_local_job`
boundary with **20 GiB RAM, 4 GiB scratch, and no wall-time cap**. Each receipt
records the verified cgroup limits, native return code and source hashes.

1. `baseline_001/receipt.json`: pre-change parsing of the retained NCBI archive;
   saved the complete collection, legacy single-query output and native numerical
   evidence. Exit 0.
2. `tests_001/receipt.json`: **143 passed**, including **9 new tests** and the
   complete existing `test_blast_report_collection.py`,
   `test_blast_program_context.py` and `test_blast_grading_inputs.py` suites.
   Exit 0. The existing duplicate-name fixture emitted its expected ZIP warning.
3. `current_001/receipt.json`: parsed the same retained bytes using the changed
   collector. Exit 0. `current_001/comparison.json` records full collection
   equality with the baseline after removing only the new member digest.
   Legacy single-query output and numerical evidence files are byte-identical
   to the baseline.

The nine new tests verify actual retained archive bytes; all original member
ordinals and artifact/member digest agreement; duplicate filenames with
different bytes and multiple reports; equal decoded JSON with different
whitespace; directories, manifest members, malformed JSON, malformed report
siblings and unlisted members; both `bl2seq` and iteration branches; unchanged
standalone JSON2/JSON15; and supplied-byte parsing without filesystem, network
or process access. Repackaged layouts are synthetic identity counterexamples,
not new scientific results. The pre-existing paired-report cases consume
retained native bytes; they do not execute BLAST.

Concrete retained evidence:

| Quantity | Value |
| --- | --- |
| Container bytes | 2,911 |
| Report member ordinal / name | 1 / `DTKE1D4G016_1.json` |
| Report member bytes | 12,592 |
| Query length | 253 amino acids |
| Native hit count / HSP count | 7 / 7 |
| First HSP score / bit score | 1,358 / 527.709 |
| First HSP identities / alignment length / gaps | 253 / 253 / 0 |

Container SHA-256:
`38908947ffab7a09a8260c6c6933b53cd35c066a3630e5e072c61be0a51c771f`

Report member SHA-256:
`e343568a2833a49ce7667779b8e9763cf9cb0229d3f24893a26cbb643e40bbe0`

Complete per-hit native scores, identities, alignment lengths, gap counts,
E-values and accession associations are saved in both
`baseline_001/native-evidence.json` and `current_001/native-evidence.json`.

No native algorithm, API call, HPC call, database search or installation was
performed. No new full Workflow run or new episode communication run was
performed; this packet verifies the narrow parser identity change and its
unchanged existing consumers by inspection and the specified regressions.
Worker 303's new database adapter integration remains a separate verification
claim.

## Exact source identity

Collector SHA-256 before:
`0d017e56aa57ae53c8ff92ab6b227f758badcc648dc7c8a7c07d32f05e9f99a5`

Collector SHA-256 after:
`ce42a2d59b690f162fb011ef1e18242ce0133688b51de71abdbf8ba494cdb193`

New tests SHA-256:
`832aba9df1d2211a56fa6d207af2a61a565ff02b501c6a0f80c7f70602de6594`

`source_hashes_before.sha256`, `source_hashes_after.sha256` and the run receipts
preserve the exact legacy-reader, program-context and existing-test hashes.
The watched sources were unchanged during each run. This directory is not a
Git checkout; these hashes and saved outputs establish the before/after record.

The full immutable objective, all sixteen design principles, applicable
repository/tool-grader instructions, relevant inventory rows and frozen
`CONTRACT_001.md` were read. The original objective and all sixteen principles
were reread verbatim after native-output study, followed by the contract, and
again before handoff.
