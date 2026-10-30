# Assigned external-job dependency custody

Root traced `Workflow.expose_assigned_job`, including its existing transaction
and `ProgressProvider.expose` consumer. C additionally implements the existing
synchronous optional port on `HmmerProgressProvider`:

```python
def dependency(self, spec, *, operation_key): ...
```

It validates the original durable commission, same run, selected API resource
ID/kind/registry, the complete immutable adapter order against
`operations.open_order`, original normalized request and assigned subject scope.
Foreign resource assignments return None. Conflicting recognized API assignments
fail explicitly. It performs no HTTP or current progress/status acquisition.

The saved `source` provider is `hmmer.progress.assignment`. Its closed JSON
body has exactly `version="api_job_dependency_v1", run_id, owner_handle,
owner_episode_id, commission_sha256, registry_ref, job_ref, request_sha256,
order_operation_key`. Values come from the original commission/order and actual
registry. The source's operand reference is the actual request subject. Original
UTC retrieval time and artifact bytes provide custody; source replay uses the
original body/time rather than creating a new fact. The same operation key with
different original operands fails identity validation.

The returned relationship is exactly `{handle: original provider_job,
kind: "job", relation_ref: saved_source_id, observed_at: original_source_time,
state: "pending"}`. Pending here records the original assigned dependency,
as in the existing native port; it does not claim that a later remote job is
currently pending. It earns no scientific or monitoring observation by itself.
The unchanged runtime publishes that relationship to the owning child's exposed
dependencies. A monitor may select it through the existing recursive mechanism.

Root's caller-bound native/API progress router dispatches this port by the
actual selected resource ID, and retains native legacy job assignments through
the existing native port. Scope/observe/dependency lookup of physical handles
uses actual registered ownership, never a guessed reference prefix. The router
descriptor lists both original providers, without inventing a combined registry.

A new external HTTP observation requires a nonempty original selected operation
key. `HmmerProgressProvider.observe(..., operation_key=None)` fails
`hmmer_progress_operation_key_required` before HTTP. It does not invent an
unkeyed request identity. Existing native/unkeyed behavior stays unchanged.

This extends only C's existing new module and root's existing setup ownership.
It adds no episode, loop, selection, automatic traversal, status refresh or
continuation policy. All coding remains in the isolated API checkout.
