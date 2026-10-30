# Projection extent and failure selection

Additive root clarification for G3a, 2026-10-27. Existing numerical meanings,
record fields and ownership remain unchanged.

Compute aggregate `result_extent` from the scientific sources underlying the
filtered selected population, before paging: complete if all are complete,
unavailable if all are unavailable, otherwise partial. An empty requested page
does not establish complete scientific data. For an occurrence selection with
zero rows, use its selected pair extents. For set metrics use the selected
endpoint sets' extents, independent of native pair failures.

Apply measurement selection before deciding which failures matter. A row's
issues describe that row's requested values or the input/reference/extent
qualifications needed to interpret those values. Top-level failures include
those relevant to the actual returned page plus any failure that directly
invalidates the selected population/page calculation itself. Do not append a
failure for every unreturned row merely because it is in the filtered population.
The aggregate extent and total_rows still describe that population truthfully.
If no occurrence rows can exist because selected inputs are unavailable, retain
the relevant existing missing-input failures; absence of rows is not a no-hit
claim. A valid empty source or an offset beyond a known population is not itself
a failure.

These are pure typed-data projection rules. They do not define a new model
prompt, an invented truncation limit, a new calculation or access authority.
