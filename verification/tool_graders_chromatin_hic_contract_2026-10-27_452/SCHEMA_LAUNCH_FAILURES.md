# Static-schema launcher failures retained

Before schema001 existed, the agent selected
`reference/episode_tools/.venv/bin/python -B run_bounded.py launch schema001 schema_compatibility_probe.py <packet>`
instead of the `.venv/bin/python` infrastructure launcher recorded in the earlier
successful prerequisite002 pins. The selected scientific reference environment
does not supply the launcher's jsonschema dependency. No native job, handle,
attempt directory or schema result was created by this invocation.

The terminal tool output was:

```text
Traceback (most recent call last):
  File "/home/chia/repos/gene_annotation_episode/verification/tool_graders_chromatin_hic_contract_2026-10-27_452/run_bounded.py", line 26, in <module>
    from gene_annotation_episode.local_jobs import LocalJobPolicy
  File "/home/chia/repos/gene_annotation_episode/gene_annotation_episode/local_jobs.py", line 18, in <module>
    from .acquisition import AcquisitionError
  File "/home/chia/repos/gene_annotation_episode/gene_annotation_episode/acquisition.py", line 29, in <module>
    from .domain import PUBLICATION_ID_PATTERNS
  File "/home/chia/repos/gene_annotation_episode/gene_annotation_episode/domain.py", line 12, in <module>
    import jsonschema
ModuleNotFoundError: No module named 'jsonschema'
```

A mistakenly issued `collect schema001` with the same launcher then failed with
the identical traceback, before examining a handle. It did not submit or retry a
job. Both failures were visible to root and are recorded here as tool-terminal
transcripts, not native lifecycle receipts. The tool call printed only its output;
no original exit-code object or raw stderr file was retained, so this record does
not invent one.

The subsequent explicit correction selected the already evidenced
`.venv/bin/python` infrastructure launcher, retaining the script snapshot and
scientific reference interpreter inside the bounded job. That job is schema001;
its own handle and receipts are separate evidence. No environment was changed or
dependency installed.
