# FCS encoded-event parser implementation evidence

This packet records the parser assignment in557/006 with metadata clarification007.
It does not change the user-supplied goal or establish either operation's complete
execution, resource binding, scientific-parent return or closed replay.

The two existing operations remain `perform_facs_cell_sorting` and
`analyze_cytokine_production_in_cd4_tcells`. Both use the existing
`fluorescence_event_population_sheet_v1`, `populate_fluorescence_sheet`,
`calculate_fluorescence_sheet` and `project_fluorescence_result`.

## Implemented boundary

`parse_fluorescence_fcs(raw, *, source, sample, channels, domain)` accepts exact
retained bytes, the frozen `fcs_flowio_1_4_0_encoded` profile, and an explicitly
bound primary encoded domain. It returns the existing validated EventParseResult.
The common request-validator extraction is byte-for-byte neutral when reversed;
the reconstructed prior module matches check016's recorded SHA256. All other
seven core production/test pins match557/ROOT_CORE_VERIFICATION_001.json.

The parser invokes actual FlowIO1.4.0 with fresh BytesIO handles and explicit
zero-based dataset traversal through relative NEXTDATA values. Metadata-only
calls locate the selected dataset; only its DATA is decoded. Strict offset
options retain their defaults. The implementation uses FlowData.events directly,
preserves integer values and the decoder's integer range-bit masking, and adds
no gate, ratio, percentage, intensity or annotation-confidence calculator.

Caller sample/condition/replicate/association/unit information is copied. Names
remain positional even when duplicated. Native TEXT supplies only actual PnN
and present PnS values where caller fields are null. Missing PnE/PnG/PnS remain
absent from retained native TEXT; decoder defaults are not presented as observed
metadata. Every finite value copies the explicitly supplied measurement origin.

The parser retains actual native TOT separately from retained Event rows and
replaces caller extent/count claims with parsing outcomes. Nonfinite cells are
invalid/null without dropping rows. A returned incomplete last row keeps its
available prefix and original ordinal. Decoder-discarded incomplete integer
tails qualify only the returned prefix; they do not produce reconstructed values.
Complete empty input stays complete; a failed/no-established-value decode does
not establish a zero population. Event line and byte positions remain null.

## Failure and provenance handling

| Situation | Outcome |
|---|---|
| Malformed caller shapes or positional joins | Existing typed contract error |
| Wrong retained artifact size/hash | retained_artifact_mismatch; no events |
| Requested unavailable/failed domain | measurement_domain_unavailable; state preserved |
| Missing decoder or version other than1.4.0 | decoder_unavailable; no events |
| Unsupported native format, malformed metadata, strict discrepancies or cross-dataset segment | native_format_mismatch; no events |
| Truncated source/segment or incomplete returned row | truncated_source with established prefix only |
| Requested ordinal after terminal NEXTDATA | source_unavailable |
| Actual PAR exceeds supplied bindings | invalid_channel caller error |
| Additional requested positions | channel_missing and unavailable cells |
| Positional name mismatch | located native_format_mismatch; no events |
| Actual retained rows differ from reported TOT | native_count_conflict; partial extent |
| Process/resource exception | Propagated, not converted to scientific success |

Metadata already exposed before a strict constructor failure is preserved under
flowio.header./flowio.text./flowio.analysis. keys. The original artifact remains
authoritative for lexical keys and values normalized or discarded by FlowIO.

## Inspection and verification limits

Read all seven pinned FlowIO source modules in557/flowio_source_1_4_0 and checked
their hashes against both source manifests. Read the shared request/result
validation paths, complete CSV/snapshot reader, sheet builder, calculator and
result projection consumers. Read contracts001–007 and the original user goal;
repeated the original objective and full operating principles after logical
tool/source examinations. Never read GOAL.md.

Host work was limited to source reading/writing and stdlib AST/hash operations.
All three owned Python files parse as Python AST. No host application import,
test, native execution, scientific download or installation was performed.

Exact controlled-test selector: `tests/test_fluorescence_fcs_reader.py`.
These tests use explicitly identified stand-in decoder values and handwritten
structural stubs to exercise caller, failure, identity and metadata joins. They
are not actual scientific or native-format verification. Owner563 separately
owns tests/test_fluorescence_fcs_native.py and actual writer/upstream-fixture
evidence. The coordinator owns every bounded runtime check.

Runtime test results remain pending in this static packet. No actual numerical
answer, installed production decoder, preprocessing, operation route, resource
deployment, episode return or saved replay is claimed by these source checks.
