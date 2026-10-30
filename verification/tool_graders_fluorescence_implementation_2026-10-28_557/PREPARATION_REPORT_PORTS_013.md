# Selected preparation and native-report parser ports

Implementation contract, 2026-10-28. This does not change the user goal or
historical records. It freezes the P and R workloads from
`verification/tool_graders_fluorescence_preparation_boundary_2026-10-28_573/PROPOSAL_001.md`
sections 2–5, with `REVIEW_CORRECTION_002.md` and the clarifications below.
Common-core contract012 is implemented; reuse its exact sheet/calculator.

## P: finite preparation of selected event values

Own new `fluorescence_preparation_contracts.py`,
`fluorescence_preparation_readers.py`, `fluorescence_event_preparation.py`,
`tests/test_fluorescence_preparation.py` and
`tests/test_fluorescence_preparation_readers.py`. A narrowly factored strict
selected-dataset decoder in `fluorescence_fcs_reader.py` is also P-owned;
existing encoded-reading semantics and byte identities must remain unchanged.

Implement exactly the public signatures and closed PreparationRequest,
ResolvedPreparation, PreparedEventData, PreparationOutcome, MatrixReadResult and
assembly shapes in proposal001 section5. The input_domains argument is the
ordered available Domain list against which request.input resolves; the producer
separately enforces original-input versus earlier-preparation topology. Parent
parse validation enforces the actual selected domain/source/event relationships.

Only `fcs_scale_flowio_1_4_0` and `spill_compensate_flowutils_1_2_2` execute.
Use the actual library implementations for scaling and compensation, with the
specified strict metadata preflight and exact ordered axis mapping. No custom
replacement equations, inferred gates, inferred channel sets, raw-value fallback,
clipping, pseudoinverse, row deletion, automatic install or unselected transform.
Imports may be lazy; unavailable/incompatible backends remain explicit outcomes.
Do not present source inspection or a stubbed library as native verification.

Preparation contracts and outcomes are numerical data, not execution controls:
their request/input digests use existing core canonical/digest. Consumers must
use these helpers, not the differently encoded control canonical function.
Callers retain actual recipe bytes; this pure boundary validates recipe object
and supplied identity shape. The producer separately authenticates those bytes
before calling it. Output source identities are assembled only after actual
prepared data and resolved parameters bytes are retained, as proposal001 states.
Full original input and original event identities remain available.

## R: extract actual reported numbers

Own new `fluorescence_native_report_contracts.py`,
`fluorescence_native_reports.py`, `tests/test_fluorescence_native_reports.py`,
and distinctly labelled format fixtures under the worker's evidence directory.
Only the three exact source-defined log/CSV profiles in proposal001 are included.
Read the complete original functions identified in573/SOURCE_MANIFEST_001.json.

Keep these ports:

```
validate_report_input(value, *, definitions, event_inputs, preparations) -> dict
validate_report_parse_result(value, *, binding) -> dict
parse_fluorescence_native_reports(raw, *, binding, association_raw) -> dict
```

Resolve the proposal's missing parser association context with one explicit port:

```
make_fluorescence_report_binding(report_input, *, definitions, event_inputs,
                                 preparations) -> dict
ReportParseBinding = {
  version: "fluorescence_report_parse_binding_v1",
  report_input: ReportInput,
  definitions: {populations, gates, control_pairs, native_reports: []},
  event_inputs: [existing EventInput],
  preparations: [PreparationRequest]
}
```

The returned binding is a validated independent copy. Parser and result validator
receive this closed binding, not an unchecked ReportInput alone. It supplies
the exact selected input sources, domains, samples, gates and controls needed
to check an association. It contains no measured event array. P owns validation
of PreparationRequest; R imports that port when preparations are present rather
than defining a competing shape. Report field/source keys must be distinct from
each other and from event/prepared source keys. Exact locator, request and
definition relationships remain validated; labels do not authorize joins.

ReportInput, locators, ReportAssociation and NativeReportParseResult retain the
exact proposal001 shapes. Incoming association bytes are data: unavailable,
wrong-digest, malformed or semantically mismatched association bytes preserve
native numbers and the original component_request, with source-scoped
native_population_unknown. Malformed caller binding shapes are contract errors.
The common calculator already makes the unsupported delta unavailable. Do not
clear the link, invent a denominator, substitute a number from metadata, or
recompute a summary inside this parser.

Read byte/line/record locations from the actual source, preserve lexical tokens,
source rounding and missing rows, and use the existing shared NativeReport/Issue
types. A hash proves the report bytes, not its historical execution. Source
format fixtures are labelled fixtures; authentic successful execution is a
separate root-owned verification. FACS selected CSV remains an event input;
the arbitrary pandas to_string display is not a fourth report profile.

## Shared constraints and handoff

P and R can code concurrently against these frozen ports. Neither edits producer,
worker, receipts, routing, tool information, prompts, goal, global designs or
the existing common sheet/calculator. Root separately connects their exact
returned records to the selected producer and results worker. A pure parser
implementation does not establish that connected capability.

Use the concrete numerical and failure examples in proposal001 section7 and
contract012. Tests must verify preserved raw/prepared relationships, exact native
tokens and locations, correct versus missing association, partial data, and
saved-sheet calculation through the existing calculator. No second scoring path.
Host work is stdlib/source inspection only. Root runs all application imports,
native libraries and tests in the existing 20 GiB RAM/4 GiB scratch/zero-swap
runner, without a wall limit. Send explicit test selectors and required files.

Read the full user-entered goal first. Reread its objective and entire operating
principles after the tool work and substantial source examination, then this
contract before handing off. Do not read GOAL.md or mutate earlier records.
