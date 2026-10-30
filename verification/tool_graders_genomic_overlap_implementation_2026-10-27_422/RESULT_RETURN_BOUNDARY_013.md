# Runtime return boundary and preparation clarifications

Additive root implementation decision, 2026-10-27. No scientific calculation,
worker record, episode type, prompt or annotation-credit rule changes here.

## Preparation clarifications

NativeFileCapture owns Store acquisition/custody. Staging already retained,
verified bytes into an exclusive private execution snapshot may stream those
bytes into a separate inode with exact digest/size comparison. It must preserve
shared Store artifact permissions and must not register a second invented
artifact. This narrows012's overly broad wording about every full-file copy.

Qualify actual terminal/quiescent worker execution during creation through the
existing lifecycle. Historical replay checks retained actual receipt joins;
it does not poll today's unit or add a second terminal detector.

A valid plan-matching WorkerResult remains the original record even when some
captured outputs fail subsequent qualification. Keep all four actual capture
rows and report located semantic/retention failures. Capture outcome verified
means byte agreement, not semantic qualification. Only a missing, malformed or
plan-incompatible worker-result produces result=null/outputs=[]. Do not discard
valid independent partial captures because another output is unusable.

## Root runtime-facing data boundary

The pure Projection and WorkerCapture records remain exactly frozen418/428.
The current runtime's fact sources accumulate values from completed own actions
and immediate-child returns. Therefore the runtime source
`genomic_overlap_pair_metrics` is an array of these unchanged Projection objects.
This explicitly corrects428's single `{overlap: Projection}` runtime-return
sketch: a requested runtime field is `{overlap: [Projection, ...]}`. One result
normally supplies one item. Multiple received children never force choosing an
arbitrary first/latest result or overwriting a prior projection. The parent can
choose the outer field name and which sources it requests. G3a still controls
the exact rows/measurement fields inside each projection.

Two additional independent optional fact sources are:

- `genomic_overlap_saved_sheets`: array of actual G1 NativeFileIdentity records
  whose format is genomic_region_overlap_sheet_v1. These are explicit operands
  for a later selected saved-sheet calculation, not scientific measurements or
  automatic permission to use every file captured by a child.
- `genomic_overlap_failures`: array of original located G1 Failure records.
  Missing requested measurements stay unavailable; no empty complete projection
  is manufactured when a worker failed to produce one.

All three source descriptors use the existing report_schema convention.
Only sources requested in the receiving form cross the boundary. Equal returned
values may be deduplicated as representations, never counted as independent
evidence. Artifact identities are internal typed operands and stay out of
model-facing steering. No prompt/template implementation is assigned by this
record; its detailed TASK/concise STEERING review is separate.

Root owns a pure `genomic_overlap_return_views.py` module with these ports:

```python
genomic_overlap_fact_sources() -> dict
requested_genomic_overlap_sources(schema: dict) -> tuple[str, ...]
validate_genomic_overlap_fact_values(source: str, value: object) -> list
select_genomic_overlap_return_facts(groups: dict, *, schema: dict) -> dict
```

These define closed typed values, requested-source selection and detached
copies. They perform no Store read, output qualification, calculation, source
publication, interpretation or authority grant. Original selected action and
completed child return records must establish actual values before these ports
are called. The result host/returns owner will enforce those separate joins.

Tests cover all three descriptor schemas, exact G1 values, unsupported sources,
wrong saved-sheet format, extra/invalid fields, nonfinite numbers, several
received projections without overwriting, requested-only selection and detached
outputs. Root owns the test and shared integration; agents432–434 do not edit
this module. All numerical verification remains within the existing bounded
test mechanism. Creating these descriptors alone increments no completion count.
