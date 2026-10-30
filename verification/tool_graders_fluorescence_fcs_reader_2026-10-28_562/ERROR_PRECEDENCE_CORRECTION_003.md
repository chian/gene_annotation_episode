# Preserve an established strict decoder failure

Bounded check017 reported 227 passed and one failed test. The unmodified official
data_stop_offset_discrepancy_example.fcs correctly caused actual FlowIO to raise
its strict DATA-offset discrepancy error. `_decode` converted that to the existing
native_format_mismatch issue. The outer parser then checked segment bounds and
replaced this already-established failure with truncated_source.

The correction moves the existing decoder-error return immediately after native
metadata retention and before the outer segment check. It changes no decoder
flags, offset values, scientific calculations, shared validation or native tests.
The BytesIO guard added in freeze002 still prevents invalid ANALYSIS reads and
returns its original specific failure code. Established HEADER/TEXT and native
TOT remain retained on strict native failure.

The controlled regression is
`tests/test_fluorescence_fcs_reader.py::test_established_native_error_precedes_post_decode_segment_check`.
It supplies a strict decoder failure with a DATA stop that a subsequent check
would classify as truncated, and requires native_format_mismatch plus retained
HEADER/TEXT and TOT. This is controlled failure-path verification; the unmodified
official native fixture remains the independent reproduction and is unchanged.

Host checks were limited to source/AST/hash and retained test/audit record reads.
Both changed Python files parse as AST. Runtime verification of this correction
is pending the coordinator's bounded check018. check017 is not relabeled passing.

The separate unbound libnss_mdns4_minimal mapping is audited in
HARNESS_MAPPING_AUDIT_003.json. No parser exception suppression or harness change
was made to hide it. Current library hashes do not establish historical before/
after equality for a library that check017 did not pin.
