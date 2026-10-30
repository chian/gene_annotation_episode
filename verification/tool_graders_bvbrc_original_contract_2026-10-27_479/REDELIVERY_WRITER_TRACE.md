# Saved redelivery decision evidence

This is implementation evidence, not goal authority. The original user goal
and the packet's narrow repair contract remain unchanged.

The current `DecisionSource.call` in `gene_annotation_episode/runtime.py`
initially builds `saved = {"context": context, "schema": schema}`. The exchange
path retains those fields and adds the protocol and, when applicable, frozen
contract information before saving `runtime_model_calls`. The direct path also
saves both context and schema, plus its assignment-transport marker when
applicable. Both paths record purpose `decision`. The retained pre-repair writer
in `tool_graders_composed_assignment_transport_2026-10-27_458/check012/`
contains the same context-and-schema requirement. No inspected actual writer
provides evidence for a saved decision request equal to `{}`.

`Workflow.action_schema` represents `redeliver_report` as a closed object with
required `kind`, `delivery_ref`, `purpose`, and `schema_json`. Its enclosing
response is a closed object containing `selection` and `report_update`.
`Workflow.redeliver` reads the first original delivery, expands the newly
selected form, uses the original child's frozen facts and interpretations,
and saves the revised report attempt. It does not create another completed
scientific action or observation. A revised interpretation must use the same
original meaning and saved value.

The two constructed legacy full-form tests identified in workload 480 had
saved `request="{}"` and a response containing only `selection`. Those fixtures
do not retain the real writer's original allowed schema. Their owner was sent
the following minimal faithful no-profile shape, using `obj(properties)` to
add `type="object"`, all required property names, and
`additionalProperties=false`:

```python
redelivery = obj({
    "kind": {"type": "string", "const": "redeliver_report"},
    "delivery_ref": {"type": "string"},
    "purpose": {"type": "string"},
    "schema_json": {"type": "string"},
})
action_schema = obj({
    "selection": {"anyOf": [redelivery]},
    "report_update": obj({}),
})
request = {"context": {}, "schema": action_schema}
response = {"selection": selected, "report_update": {}}
```

This is explicitly a constructed transport fixture. It does not claim that
the empty context was produced by a live model or that this subset is the
entire current action catalog. Literal closed report schemas can use the
historical no-profile path; these fixtures must not invent compact fact
catalogs. A conflicting allowed purpose or selection shape must still fail
against the original saved schema. Custody retains that requirement instead
of accepting missing original decision authority.

The two affected nodes are:

- `tests/test_bvbrc_homology_returns.py::test_original_redelivery_adds_no_duplicate_rows_or_completed_action`
- `tests/test_bvbrc_phylogeny_returns.py::test_repeated_reads_and_redelivery_create_no_new_records_or_observations`

The other 148 failures in workload 480's broad existing-return checks were
missing retained-fixture artifacts in the bounded snapshots. They remain
unverified cases; this writer trace does not classify them as production
failures or passing cases.
