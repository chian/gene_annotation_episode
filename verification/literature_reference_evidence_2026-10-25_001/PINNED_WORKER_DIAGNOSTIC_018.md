# Pinned worker import diagnosis and prospective repair

The native017 worker failure is explained by import precedence. Its root imported
the selected pin, but durable.start invoked Python with `-m` from the caller's main
checkout directory. Python put that implicit directory ahead of the correctly
constructed pinned PYTHONPATH. The worker therefore loaded main durable_worker
and main independent_execution; the latter correctly rejected a different
implementation hash before opening its scientific episode.

Seven actual trace-only diagnostic records were inspected. Their creator at
method_loop/durable_worker.py32–35 writes only version, observation time,
exception type and traceback. They consistently name main durable_worker.py72
and main independent_execution.py365. No child episode/result archive, model-call
content, model exchange or provider log was read. Read-only C1 metadata supplies
selected implementation hash64426e48ed0b852b53d13d8fd4dac074e1f30020671001393e26f93a37540003.
All605 original017pin files still verify against its unchanged manifest.

Three isolated, read-only import probes used that exact pin in PYTHONPATH:

| Working directory | Safe-path flag | Imported runtime/factory |
| --- | --- | --- |
| Main checkout | Off | Main checkout; different implementation hash |
| Main checkout | On | Exact017pin, matching the selected C1 hash |
| Exact017pin | Off | Exact017pin, matching the selected C1 hash |

After the coordinator authorized the repair, the sole production change adds
`-P` to the actual worker subprocess command in method_loop/durable.py528.
This interpreter flag suppresses the implicit unsafe cwd path while retaining
the explicit import roots already supplied by the owning caller. The project
already requires Python>=3.11. No working-directory override, environment-wide
safe-path setting, fallback implementation or identity-check bypass is added.

Changing each harness's cwd to the pin is an operational workaround, but changes
the meaning of relative caller operands and only covers those particular callers.
Changing durable.start's cwd has the same broader semantic risk. A bespoke `-c`
bootstrap that rewrites sys.path could preserve cwd, but is unnecessary here;
the supported interpreter flag handles this exact startup precedence problem.

The original commission, goal/scope, selected factory arguments, resource
allocations, source versions and typed form remain authoritative. Backend claim,
readiness handshake, process identity, durable return publication, acknowledgment
and event notification are unchanged. The same ordinary Episode owns iteration,
credit and continuation. This change neither creates an observation nor chooses
new work, retries, cancellation or a different scientific approach.

The new tests/test_pinned_worker_imports.py runs two real subprocess consumers:
one with its factory in the selected runtime and one in an explicit caller
extension directory. Both start actual durable.start from a directory containing
shadow runtime/factory modules. The selected ordinary two-action Episode returns
its exact original `{value:6}` form. Tests verify actual imported source paths,
unchanged caller cwd and successful relative-input access, exact commission,
same process incarnation on repeated start, and one invocation. The factories
and controllers are synthetic engineering fixtures; no configured model runs.

One joined invocation passed34tests in26.86s: the two new consumers plus existing
durable and independent Episode checks. Terminal session65209 exited0. The
production diff against unchanged017pin is exactly the one added `-P` command
element. Final source hashes and complete read provenance are in
PINNED_WORKER_DIAGNOSTIC_018.json.

The already running017root keeps its old loaded/pinned launcher; this prospective
repair does not claim to fix that current run. Neither it nor the original YeaG
run was stopped, resumed, restarted, repriced or otherwise modified. Old pins,
failed attempts, original credit and history remain facts. A future correctly
captured runtime can use this repair, while any caller-directed later recovery
must preserve those original identities and must not silently adopt newer code.
Actual configured-model numerical population and typed scientific delivery remain
separate verification requirements.
