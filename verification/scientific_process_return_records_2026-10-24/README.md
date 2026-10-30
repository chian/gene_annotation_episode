# Pure scientific-process return record repair

Implemented only `gene_annotation_episode/scientific_process_reports.py`, its
existing pure tests, the new `test_scientific_process_return_records.py`, and
dedicated literal fixtures. `scientific_process_records.py` was not changed.
No mother, provenance, runtime, prompt, provider, descriptor, scoring, controller,
or accounting changes belong to this workload.

The full host result still uses `scientific_process_result_v1` and retains the
complete original construction selection. The reader accepts literal legacy v2
and current v3 selections without renaming their keys or references. New typed
returns use `scientific_process_result_v2` with a separate compact
`scientific_process_selection_report_v1`. Only original option references and
ordered `{name, resources}` choices enter that selection; legacy resources stay
null. Selected current information is validated against the exact frozen body.

The source schema uses actual frozen option/name/resource enums. Semantic
validation additionally verifies the full option/digest tuple and each actual
name/resource pair. Existing `communication.py` was unchanged. Initial credit,
closing credit, binding identity, own-action count and closing yield are copied
exactly. Stable union retains own-first order and rejects conflicting invocation
bodies, including mixed representation versions unless explicitly projected first.

Verification command:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -q tests/test_scientific_process_reports.py tests/test_scientific_process_return_records.py
```

Result: **146 passed in 2.05 seconds**. `pytest-pure-001.log` retains the output.
Coverage includes the independent literal old schema, exact old slot spelling,
current v3 parsing with process-only/tool-only/both bindings, multiple tools and
same-name resource variants, resource-only profiles, zero tools, mapping proxies,
finite and boolean numeric failures, wrong references/pairs/bodies, closed prose
rejection, signed/coded/null yields, detachment, input-byte preservation, stable
deduplication and conflicting bodies. A no-completion builder reads no context.
Failing spies guard refitting, invocation/discovery and state writes in projection.

Concrete examples were retained with:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B verification/scientific_process_return_records_2026-10-24/check_repaired_records.py
```

This accepts the planning directory's retained full current v1 row with its
actual published A104/P01 library, under all four binding combinations. Its new
projection exactly equals the independent planning specimen `proposed-row.json`
and passes the unchanged closed form guard. The retained broken hybrid schema
still fails. All retained planning inputs are unchanged by hash.

The independent legacy example retains `annotation_distinction` and projects
`fixture.inspect` to a null resource even though its frozen catalog says local.
The current multiple-choice example preserves, in order, `fixture.inspect/hpc`,
`fixture.remote/api`, and `fixture.inspect/local`. Its original initial credit
15.25, closing credit 14.5, two own actions, expected next gain -0.25, lower -0.5,
upper 0.125, alpha 0.05, continuation cost 0.125 and stop flag true remain exact.
These are synthetic engineering quantities, not biological measurements.

`before-sha256.json`, `VERIFICATION.json` and `example-input-sha256.json` retain
source/input identities. The copied literal schema is explicitly a reviewed
compatibility fixture, not a saved historical run artifact. Original goal SHA-256
is `11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
The original objective and entire DESIGN PRINCIPLES block were read verbatim,
including the required reset after substantial source inspection and after the
work. The complete frozen return contract was reread before completion.

This evidence establishes only pure records, schema and projection. It does not
establish source authentication, blocking/detached episode admission, v8 binding
reconstruction, receiver steering, scientific execution or complete tool-grader
integration. Those have separate owners. No live API, model or native job ran.
