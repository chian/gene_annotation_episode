# Existing qualification domain in the one-input return

The actual one-input projection retains `qualification.domain="pairwise"`.
This is an existing projection-family grouping label. It is not the assigned
question kind, a member count, or evidence that two structures were compared.
The actual question is `kind="scan"`, with one saved member and zero comparisons.

In the check004 source snapshot, `rna_structure_comparison_views.py:68` defines
`PROJECTION_QUALIFICATION_SCHEMA`. Its `domain` field is an enum containing
`pairwise`, `selected_sites`, and `declared_scan`; it has no description equating
the value with two scientific inputs. `_project_one` at line248 chooses the tag
from the requested output family: every `scan_*` family gets `declared_scan`;
position changes and site-metric comparison counts get `selected_sites`; all
other families, including every structures projection, get `pairwise`.
The assignment's `question.kind` and number of members do not enter that choice.

The exact tag remains part of the typed returned record. Projection validation
reconstructs and compares the whole record (`rna_structure_comparison_views.py:444`),
and the results/return adapters authenticate that record against the original
receipt. No scientific calculation, credit, or completion decision uses this tag.
The current model-facing presentation does not read or display it:

- `rna_structure_comparison_presentation._projection_text` dispatches on the
  projection's `family`; structures render the explicitly selected fields.
- `_qualification` reads population, site and pair coverage, issue rows and
  qualification codes. It does not read `domain`.
- Both receiving-parent and results presentation use these functions; generic
  copies of the same selected projection are removed from the rendered context.

The actual retained result, passed through the existing controlled provider
lookup boundary, renders as:

```text
Requested RNA structures — requested-structure

Sequence coordinates: zero based.

| Member | Selected field | Complete supplied value | Origin | State |
| --- | --- | --- | --- | --- |
| supplied-RNA | Original sequence | GGGAAACCC | supplied; origin unknown | present |
| supplied-RNA | Dot-bracket | (((...))) | supplied; origin unknown | present |
```

The scoped `unknown source origin` qualification is also rendered. No `pairwise`
occurs in the captured text. The complete provider request is retained at
`check004/temporary/pytest/test_actual_status_update_and_0/status-then-collect/FRAMED_PROVIDER_TURN_002.txt`.
That transport check replays the actual collected receipt through a controlled
lookup response. It is not an additional Workflow action or a model turn after
practical completion.

The raw typed tag remains imprecise vocabulary for a single structure. This
packet changes neither that schema nor any scientific projection/calculation.
The existing reader does not turn it into a claim that a pairwise scientific
comparison occurred.
