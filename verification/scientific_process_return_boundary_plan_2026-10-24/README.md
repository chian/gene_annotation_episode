# Scientific process return boundary planning evidence

This is a read-only production investigation supporting
`docs/SCIENTIFIC_PROCESS_RETURN_BOUNDARY_CONTRACT_2026-10-24_001.md`.
Only that new document and this new evidence directory were written.

The successful reproduction command was:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B verification/scientific_process_return_boundary_plan_2026-10-24/run_reproductions.py
```

The existing isolated mother-return regression failed, as expected, in 0.19 s.
`isolated-regression.log` retains its exact output. `checks.json` retains the
separate pure current/legacy record, form, description-string and descriptor
examples. The full inputs and generated schemas are the adjacent
`current-row.json`, `legacy-row.json`, `current-generated-schema.json` and
`legacy-current-generated-schema.json`. Frozen fixture libraries remain here.

The additional pure planning command is:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B verification/scientific_process_return_boundary_plan_2026-10-24/check_proposed_schema.py
```

It confirms the proposed compact wire shape passes the unchanged communication
guards, with exact copied numerical fields. It also checks
`literal-legacy-form-schema.json`, a constructed literal compatibility fixture
for a v1 result containing a v2 selection and the historical
`annotation_distinction` slot. That file is not represented as a saved historical
run artifact. Its purpose is a standalone expected schema independent of the
new source generator. Outputs are `proposed-row.json`, `proposed-schema.json`
and `proposed-schema-check.json`. This is not a production implementation test.

Observed boundary failures:

- Legacy v2 selection against current form: v3 version expected.
- Correct only that const in a detached example: historical
  `annotation_distinction` slot rejected because `evidence_axis` expected.
- Current v3 record with bound process/tool libraries: `KeyError('annotation_ref')`
  or `KeyError('tools')`; unbound structural validation succeeds.
- Current v3 record against current form: missing required `annotation_ref`.
- Both full four-field tool information and the three-field parent view fail
  the existing closed-schema guard on description prose.
- Missing `resources` on `fixture.inspect` fails setup; an explicit local
  fixture succeeds and emits v7, including when semantic retrieval is configured.

`VERIFICATION.json` records the exact pytest command and matching before/after
hashes for 453 production and test Python files. No source or test changes occurred.
There were zero external, model or scientific-job calls. The retained numerical
values (15.25, 14.5, counts and null yield) are synthetic parser fixtures, not a
biological measurement or adopted scoring policy. This task does not execute a
repaired episode path or claim production completion.

An initial attempt used `/usr/bin/python3`, which lacks Biopython in this
environment. Its pytest import failure is preserved in
`environment-attempt-regression.log`; the script then also stopped during
tool-information setup with `ModuleNotFoundError: No module named 'Bio'`.
The command above uses the existing repository virtual environment and is the
completed reproduction. No packages were installed.

The original objective and complete DESIGN PRINCIPLES were read verbatim from
the immutable user attachment, including a reset after substantial source
inspection. Its verified SHA-256 is
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
