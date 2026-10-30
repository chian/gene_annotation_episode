The bounded native-file helper in `gene_annotation_episode/native_file_capture.py`
implements contract419. It reuses `materials.artifact_file` for complete streaming
Store capture and `materials.artifact_path` for retained SHA-256 verification.
This is a mechanical dependency for root's overlap result handler. It does not
complete a scientific tool, change any inventory tally, or establish episode
integration.

The implemented public API is:

```python
capture_native_file(store, *, directory: str, relative_path: str,
                    format: str,
                    media_type: str = 'application/octet-stream') -> NativeFileIdentity
capture_declared_native_files(store, *, directory: str,
                              declarations: list[NativeFileDeclaration]) -> list[NativeFileCapture]
retained_native_file(store, identity: NativeFileIdentity) -> Path
```

The three TypedDict records retain contract419's exact fields. Returned records
are detached. Counts reject booleans and require nonnegative integers. SHA-256
strings use 64 lowercase hexadecimal characters. Format/media labels reject
empty values and Unicode control characters. The entire declaration list,
duplicate-path constraint, and canonical directory spelling are validated
before any capture. Each result row preserves its original list position.
Declared absence performs no producer access. Present files retain all actual
bytes, including digest/size mismatches. Independent successes survive missing
producer files.

Every producer path component is opened from `/` with `O_DIRECTORY |
O_NOFOLLOW`; the final component uses `O_NOFOLLOW | O_NONBLOCK` and a regular-file
`fstat` check. The existing copier receives `/proc/self/fd/<fd>` while the
descriptor stays open. No second mutable producer-directory lookup supplies
the bytes. The helper closes all opened descriptors on success and failure.
Known Store failures retain typed storage errors rather than becoming producer
absence. Invalid copier references are identity errors; unexpected programming
errors propagate.

`retained_native_file` validates the closed identity, artifact reference/digest
relationship, Store metadata, actual retained digest, actual size, and regular
retained file. It never receives or reopens an original producer path. A known
nonregular or symlinked retained final node is rejected before the shared
verifier opens it.

Verification used an actual Store and actual local files. The single retained
attempt, [check001](check001/receipt.json), passed **125 tests in 122.14 seconds**;
there were no failed attempts to discard. The separate bounded worker also
generated and reread six actual [capture examples](check001/example_capture.json).
Full [pytest output](check001/stdout.txt), [JUnit results](check001/pytest.xml),
[selected request](check001/selected_request.json), readonly executed sources,
and before/after source pins remain in that attempt.

The local_jobs receipt records these resource facts:

| Fact | Actual recorded value |
| --- | ---: |
| Memory maximum | 21,474,836,480 bytes (20 GiB) |
| Swap maximum | 0 bytes |
| Scratch allocation | 4,294,967,296 bytes (4 GiB) |
| Runtime allocation | None; verified `infinity` |
| Service wall duration | 124.227803077 seconds |
| Observed scratch allocation | 48,267,264 bytes |
| Native return code | 0 |
| Executed source pins unchanged | true |
| Checkout source drift at run completion | none |

Scratch uses the existing monitored visible allocation with possible overshoot
and a hard per-file limit. The receipt does not claim a filesystem sandbox.
The bounded invocation was:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B verification/tool_graders_native_file_capture_2026-10-27_420/run_bounded.py check001
```

The focused tests establish:

- Complete streaming retention of 2,097,176 bytes with producer and retained
  verifier reads of 1,048,576, 1,048,576, 24, then 0 bytes; whole-file helper
  reads are prohibited by the test instrumentation.
- Empty present bytes, declared absence despite an existing current file, no
  access for absent-only/empty requests, unavailable files beside valid files,
  and preservation of original row order.
- Independent digest and size mismatches with their actual retained bytes;
  detached declaration and identity results, including deduplicated equal bytes
  carrying different supplied format labels.
- Duplicate paths, missing/extra fields, invalid types and values, control
  labels, and unsafe path spellings rejected before capture.
- Actual symlinks at an absolute ancestor, assigned directory, relative
  directory and final file; actual directory, FIFO and Unix-socket final nodes.
  FIFO opening is asserted nonblocking and does not wait for a writer.
- Actual replacement of the producer directory entry between descriptor open
  and copying, with retention of the original inode's bytes.
- Retained-only verification after deleting the original producer file and
  directory, with path-opening instrumentation restricted to Store artifacts.
- Retained same-size mutation, truncation, removal, FIFO and symlink replacement;
  actual Store SQL metadata mismatches and missing metadata; rejection of corrupt
  previously retained bytes during a subsequent capture.
- Malformed copier-reference returns and injected Store I/O/database failures
  distinguished from producer absence; unexpected programming-error propagation.
- Actual descriptor closure after successful capture, missing/failing paths,
  nonregular nodes, symlinks, copy/storage failures and programming errors.

The examples are synthetic byte fixtures, with real file and Store execution:

| Example | Declared bytes | Actual bytes | Outcome |
| --- | ---: | ---: | --- |
| `abc` | 3 | 3 | verified |
| Empty bytes | 0 | 0 | verified |
| Declared `abc`, actual `xyz` | 3 | 3 | digest_mismatch; actual `xyz` retained |
| `abc` with declared size 4 | 4 | 3 | digest_mismatch; actual `abc` retained |
| Missing present file | 3 | unavailable | unavailable |
| Declared-absent file that exists today | null | uninspected | declared_absent |

The SHA-256 of retained `abc` is
`ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad`.
The SHA-256 of retained empty bytes is
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
The SHA-256 of retained `xyz` is
`3608bca1e44ea6c4d268eb6db02260269892c0b42b86bbf1e77a6fa16c3c9282`.
Each artifact reference is `artifact_` followed by that digest.

These are the principal executed source pins; the full dependency pins are in
[source_pins_before.json](check001/source_pins_before.json) and their verified
after-run counterpart:

| Source | SHA-256 |
| --- | --- |
| `gene_annotation_episode/native_file_capture.py` | `889f9a370faac34d1d4e973b14e52866a461895fe2a6716b141e7ae3d54eda7b` |
| `tests/test_native_file_capture.py` | `e13fecbac5fc006f28313360e890766450931aa4efd8b6764ff4cdb6341ee925` |
| `gene_annotation_episode/materials.py` | `ad433751338bf78b886190f20d8022fd9c1db502911440106b14b05f36f5d0d9` |
| `gene_annotation_episode/state.py` | `7c807dfc6b86521095ad53f11f18810f1590cf8a9db9e5e7dc2ab617697731ed` |
| `gene_annotation_episode/native_protein_structure_acquisition.py` | `bf29e5789029f3f92a6bdeaf61ab7245fefd22f513e7a691c6db10a19f118635` |
| `gene_annotation_episode/native_rna_structure_acquisition.py` | `c8b427a8643305ef9500db764f9a51762bc7d12d44db9501d9f07d1c411149c9` |
| `gene_annotation_episode/local_jobs.py` | `4f31bc4713353356fbbf31af4063e77e87aa1bd869be6c145d3f001a268c5452` |
| `contract419/CONTRACT.md` | `25b2bb81ade4c354f2690ada190f39a538539f526b64ae5b9fcb8ea9182102bf` |
| Immutable attached goal | `11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7` |

Source inspection covered the full current protein/RNA acquisition modules,
complete `materials.artifact_file` and `artifact_path`, Store construction,
artifact retention/getting and metadata `get`/`_require` APIs, and local_jobs.
AGENTS.md and the required episode, timing, practical execution, task/steering,
tool-library and tool-grader design documents were read. The immutable objective
and all sixteen principles were read before work, reset after substantial source
inspection, and reread after output inspection before this handoff, followed by
contract419. The fixed overlap inventory row was inspected but not edited.

Root still owns original manifest/job/commission validation, writer-closure
evidence, access authority, selected-action receipts, replay, scientific parsing,
and integration through the receiving episode. A pinned descriptor protects the
opened inode against directory-entry replacement; it does not stop another
writer from modifying that inode. A returned Store Path is verified at reading
time and is not a lock against later external mutation. Linux `/proc/self/fd`
and the specified POSIX open flags are required. No new native algorithm,
network acquisition, model call, scientific calculator, credit observation,
prompt, existing family migration, or inventory change was introduced. The live
410 Workflow verification was not accessed or stopped. This component suite does
not establish whole-overlap operation or full episode-path completion.
