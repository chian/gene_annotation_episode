# Implementation identity and shared observation ports

Additive root clarification, 2026-10-27; frozen425 record shapes are unchanged.

If the selected interpreter or implementation-file bytes do not match their
declared identities, the driver must not use that unqualified implementation
to parse inputs. Independently staged and verified original bytes may survive.
Their SetOutput has parse_extent=null and absent parsed/canonical files.
SoftwareVerification is failed; affected PairOutput entries are
native_unavailable with null manifests and located software_identity_mismatch
failure indices. Do not call those sources malformed or infer analytic emptiness.

Root's concrete read-only helper module is
gene_annotation_episode/native_genomic_overlap_observations.py, with ports:

```python
genomic_overlap_observed_files(plan: dict, view: dict, *,
    log_window_bytes: int, log_roles: tuple[str, ...]) -> tuple[list[dict], list[dict], bool]
read_genomic_overlap_output(plan: dict, *, path: str, offset: int, limit: int) -> dict
```

LocalPracticalOperations authenticates the original reservation and expected
receipt identity before calling either helper. The first consumes one actual
native.status view, reads fixed file availability/size plus requested bounded
stdout/stderr tails, and returns existing resource-observation output/log rows
and result_available. It performs no status call, scientific parse, capture,
polling decision or new observation itself. Ordinary output roles use
requested_output:<absolute-path>; stdout/stderr keep those roles. If the driver
never wrote its logs, return the original lifecycle logs with their real paths.

Result availability is actual presence of a parsed-set, pair-manifest,
overlap-stdout or batch-manifest file, including a genuinely present empty table.
It is not successful execution or validated scientific completeness. An earlier
pair file remains available when no final batch was sealed. Writer closure is
qualified only by the supplied actual lifecycle terminal observation here;
the later results handler validates individual seals separately.

The second helper accepts only exact fixed output paths or the original
lifecycle stdout/stderr paths. It returns the unchanged bounded window shape:
path, offset, returned_bytes, size_bytes, bytes_base64, text_utf8. Validate
offset>=0 and 1<=limit<=1MiB, excluding bools. Use the existing mechanical
native_file_capture pinned regular-file opening, without Store capture or a
new access authority. No symlink component, nonregular endpoint or unlisted
path may supply bytes. Missing files remain unavailable rather than zero-byte
successful output.

Root owns these helpers and tests/test_native_genomic_overlap_shared.py along
with the previously declared shared integration hooks. Tests must exercise
early pair output without a final batch, failed-driver log fallback, missing
versus present empty files, exact bounded reads and excluded paths. Follow the
same local_jobs limits and readonly-source evidence discipline as004.
