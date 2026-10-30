# Concrete integration ports and partial primary inputs

Additive implementation clarification to008; original contracts/verification
records are unchanged. This does not change the user's goal or claim completion.

## Additional public ports consumed across owners

A exports from native_fluorescence_local.py:

```python
fluorescence_native_request(plan, paths) -> dict
```

This is the same pure builder used by actual original-job preparation. Return
exact keys command,cwd,file_bytes,ready_path,release_path,result_path,stdin_path,
env. command=fluorescence_driver_argv(plan); cwd=parent of original execution_id;
file_bytes=policy.scratch_bytes; the three native paths come from the supplied
paths; stdin_path=null; env=fluorescence_environment(selected Software,
attempt_directory=original attempt_directory). It authenticates recorded plans
without opening files or comparing today's installed runtime. The actual native
reservation/request format remains the existing native_lifecycle format.

B exports FLUORESCENCE_RESULT_SELECTOR_SCHEMA, OUTPUTS, PLAN_VERSION,
RESULT_VERSION, CONTEXT_SCHEMA, validate_fluorescence_projection(value)->View
and validate_file(value, *, saved=False)->FileIdentity from
fluorescence_result_contracts.py. OUTPUTS is the fixed ordered tuple of
(role,relative_path,format) for the five008 output roles. saved=True requires
format fluorescence_event_population_sheet_v1. C uses B's View/context/fact
validators; it must not invent another validator or recalculate values.

Historical receipt validation authenticates original controls and selection,
not today's resource/software configuration. New native work still validates
actual bound capability. Saved-sheet recalculation authenticates its genuinely
received operand and current finite worker, not the old producer deployment.

## Demonstrated defect and narrow shared-core repair (root-owned)

Current fluorescence_event_contracts._validate_sheet requires every declared
subset/correspondence ordinal to occur in retained primary events. A partial or
unavailable primary batch therefore prevents preservation of a valid original
definition, and may discard independent valid samples during sheet assembly.
The existing calculator also assumes every subset ordinal was retained. Merely
relaxing that validator would let pass_all manufacture counted events.

Root will repair these exact consumers together, preserving their single shared
sheet/calculator and all original definitions/measurements:

- A complete, available primary source keeps the existing strict reference
  check. A declared ordinal absent from that complete population is invalid.
- A partial/unavailable primary source may retain original declared subset and
  derived correspondence entries referring to unavailable primary events.
  Missing rows are never synthesized. All existing ordinal, one-to-one mapping,
  sample/domain/source and actual derived event checks remain in force.
- The effective membership universe is retained primary ordinals for all, or
  their intersection with declared subset ordinals for subset. Keep the full
  original subset definition separately and unchanged in the sheet.
- An explicit subset is complete only if its primary domain is available and
  every declared subset ordinal is retained. It may be complete even when an
  unrelated tail of the primary source is partial. An all-population requires
  an available primary domain and source extent complete.
- Missing primary population remains unavailable, not a zero population. An
  incomplete retained prefix produces qualified counts over the retained
  events; fractions requiring the original population stay unavailable with
  incomplete_population. Derived rows associated with missing primary events
  remain saved but do not enter the retained primary membership universe.
- Independent valid samples continue to calculate normally. Requested views
  copy those saved components, including their exact qualifications.

Use one small internal _population_universe(population, retained_ordinals,
*, source_extent, domain_state)->(sorted_ordinals,complete) in
fluorescence_event_contracts.py for the calculator and component relationship
validation. It defines retained population membership only; it performs no
scientific score or acquisition. Do not add a second fraction/count calculator.

Concrete regression example: A's partial primary input retains event0=10 and
event1=20; original subset is [0,1,2], pass_all gate. Retained and selected count
are2 qualified, no membership row/event2 is invented, parent fraction is null
with incomplete_population, retained intensity mean is15 qualified. Independent
complete B with values[5,7] retains count2, parent fraction1 and mean6. If A is
unavailable its counts/fraction/intensity are null and B remains unchanged.
If A is partial but the requested subset is[0,1], that exact subset is complete.

Root owns the narrow changes to fluorescence_event_contracts.py,
fluorescence_event_calculations.py and new
tests/test_fluorescence_partial_primary.py. A/B/C keep their ownership from008;
do not edit these files or silently remove definitions to get a passing sheet.
Tests will run through the existing bounded lifecycle; no new runtime result
is claimed by this source-grounded clarification.
