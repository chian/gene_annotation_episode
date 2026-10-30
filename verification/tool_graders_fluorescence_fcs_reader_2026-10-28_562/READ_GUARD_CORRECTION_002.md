# Preventing invalid native ANALYSIS reads

The coordinator resolved the review question in FREEZE_001.json: contract006
requires preventing the invalid ANALYSIS read itself. Rejecting event admission
after the constructor had read invalid ANALYSIS bytes was insufficient.

`_SegmentGuard` is a fresh BytesIO subclass for each actual FlowIO constructor.
Once FlowIO exposes both native.header and native.text, the handle calls the
existing `_segments` validator before its next read/read1/readinto operation.
It contains no metadata decoder, offset substitution, permissive mode or global
monkeypatch. FlowIO still parses native HEADER, TEXT and valid ANALYSIS metadata.

An invalid span raises the existing internal native-failure object before the
underlying read occurs. `_decode` preserves its exact issue code and the actual
pre-error native object. HEADER/TEXT and reported TOT therefore remain available;
invalid ANALYSIS has not been established and is not retained. Process/resource
exceptions continue to propagate. Closing the handle releases its reference to
the native object, avoiding a reference cycle through FlowIO's `_fh` attribute.

Three additional controlled test functions exercise the new boundary:

- `test_invalid_analysis_read_is_prevented_before_facts_are_established`
  covers EOF and later-dataset spans, selected datasets at zero and nonzero
  offsets, and all three guarded read entrypoints. It verifies that no ANALYSIS
  read returns bytes and no ANALYSIS metadata is retained.
- `test_valid_analysis_and_selected_values_survive_guard` verifies valid
  ANALYSIS bytes, selected event values and complete extent at both offsets.
- `test_guard_does_not_swallow_resource_failure` verifies MemoryError/OSError
  propagation and handle closure when the guard's validation itself fails.

These remain explicitly controlled tests with handwritten structural stubs,
not authentic native-format measurements. The native test owner separately
verifies actual FlowIO constructor behavior. No other owner file was changed.

The parser and test module passed stdlib AST parsing on the host. No host
application import, runtime test, native execution or data acquisition occurred.
All runtime results remain pending the coordinator's bounded combined check.
