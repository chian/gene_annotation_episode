# Producer interface handoff

This additive record implements the accepted 349 lane-2 signatures, 349
addendum006 and the frozen355 locator contract. It changes no earlier record.
Root owns shared registration;358 owns capture, saved grading and returns.

The five modules export these agreed callables:

| Module | Exports |
| --- | --- |
| `native_rna_structure_contracts.py` | `validate_rna_structure_job`, `compile_rna_structure_job`, `requested_job_from_rna_structure`, `validate_rna_structure_requested_job`, `validate_rna_structure_bindings`, `validate_rna_structure_run_plan`, `validate_rna_structure_bundle` |
| `native_rna_structure_tool_info.py` | `rna_structure_tool_contracts`, `rna_structure_tool_information`, imported `validate_rna_structure_bindings` |
| `native_rna_structure_local.py` | `prepare_local_rna_structure`, `local_rna_structure_plan` |
| `native_rna_structure_driver.py` | `run_rna_structure_driver` |
| `native_rna_structure_worker.py` | `predict_rna_secondary_structure`, `analyze_rna_secondary_structure_features` |

The direct scientific signatures remain exactly:

```python
predict_rna_secondary_structure(request: dict, *, model: dict,
    parameter_input: Path | None, output_directory: Path) -> dict
analyze_rna_secondary_structure_features(request: dict, *, energy_model: dict | None,
    parameter_input: Path | None, output_directory: Path) -> dict
```

Root accepted two additional closed JSON-schema exports for existing request
registration: `NATIVE_RNA_STRUCTURE_JOB_SCHEMA` and
`NATIVE_RNA_STRUCTURE_REQUESTED_JOB_SCHEMA`. Their shape descriptions do not
replace ordinary scientific, executable, relationship or custody validators.
`rna_structure_tool_information` returns only name, description, resources and
instructions; callable contracts separately include schema and commissioning
route `launch -> launch_local` on the caller-supplied local resource ID.

The original argv is compiled from the exact selected job. Its required operands
are `--operation`, `--input-json`, `--model-json`, `--output-json`, `--record-key`
and addendum006's `--software-json canonical(Software)`. Selected parameter-file
and energy-output options are appended explicitly. JSON is one argv element.
Staging recompiles only explicit input/output paths; the original requested job
remains in both plan and bundle. No implicit owner-plan read supplies worker
software identity. The CLI checks interpreter, worker source and nonnull native
software identities before native scientific calls. Identity conflicts use
`rna_software_identity_mismatch` and `/software/{field}`.

The fixed names are `rna-structure-plan.json`, `rna-structure-attempt` and
`bundle.json`. The plan sits beside the existing `native.json` lifecycle handle
in the caller's run/episode/operation directory. `prepare_local_rna_structure`
uses `native_lifecycle.prepare_job` without starting work. It authenticates the
original lifecycle request and policy. The selected shared start executes one
driver, which invokes one worker. An interrupted unsealed attempt cannot retry
implicitly. A sealed replay verifies saved file custody and invokes no work.

The staged input names are `input.json` and `model-parameter-input.par`.
Output relative paths come from the selected job and need not use default names.
Every declared input and output receives exactly one ordered manifest row.
Present original input requires exactly its selected SHA-256 and byte count.
Absent files have null hash/size and an associated fixed Issue. The actual worker
return code, scientific native status, later capture status and later delivery
status remain separate. No parser/calculator is called by the producer.

When candidate input bytes differ from the original requested digest/size, they
cannot become a scientific input. The input manifest row is absent with
`rna_input_identity_mismatch`, and the worker is not invoked. Full rejected
bytes are retained in the declared stderr artifact as streaming JSONL:

```text
{
  schema: 'rna_rejected_input_v1',
  role: 'input' | 'model_parameter_input',
  expected: {sha256: Sha, size_bytes: Count},
  observed: {sha256: Sha, size_bytes: Count},
  encoding: 'base64_chunks_in_byte_order'
}
{
  schema: 'rna_rejected_input_chunk_v1',
  role: 'input' | 'model_parameter_input',
  offset: Count,
  bytes_base64: str
}
```

The header precedes all chunks for that role. Each chunk encodes at most49152
raw bytes, uses standard base64, and its offset is the zero-based byte offset
within the rejected candidate. Independently decode chunks and concatenate in
offset order to recover the exact candidate. The temporary rejected file also
remains local but is not a declared operand. Traceback text follows as diagnostic
text. No scientific parser, numerical field or prompt projection consumes this
diagnostic as measurements. By contrast, malformed or non-UTF-8 JSON whose
bytes match the original selected operand is retained as a present original
input, with a failed native record carrying `rna_invalid_input_schema` and the
frozen original record key.

Energy workers load the explicitly selected native parameter set before creating
`RNA.md()`, apply and read back every selected setting, retain other observable
scalar settings, and save the native effective parameter file. Native array
settings are retained in stdout diagnostics; unavailable scalar representations
are explicitly unavailable. The model artifact equals the native record's model
object. Its parameter path/hash/size identify the exact declared effective
parameter output. Full diagnostics remain in stdout/stderr. Raw native return
JSONL uses the closed shape in349 addendum001 before finite/sentinel validation;
exceptions produce no invented return line. Native-output parsers use the native JSON artifact
for scientific values, never stdout scraping.

Runtime TMP/TEMP/TMPDIR and cache paths are explicit inside the attempt; bytecode
writing is disabled. The exact caller policy is20GiB RAM,4GiB scratch and no wall
limit. Source bindings, closed shapes, original input identity, path overlap,
temporary staging names, symlinks, reserved lifecycle paths and native output
custody are checked by ordinary functions. These checks add no episode loop,
scientific acceptance gate, retry or resource decision.

Root and358 were notified of the schema exports, software operand, rejected-byte
diagnostic and final source hashes. See `HANDOFF.md` for receipts and native paths.
