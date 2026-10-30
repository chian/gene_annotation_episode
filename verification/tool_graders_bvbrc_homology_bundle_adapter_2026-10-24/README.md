# Synthetic C4 Homology bridge verification

Run with `.venv/bin/python verification/tool_graders_bvbrc_homology_bundle_adapter_2026-10-24/build_examples.py`.

The fixture inputs and all custody identifiers are explicitly synthetic. The
native-shaped Homology bytes come from the existing Homology synthetic fixtures.
The harness calls the actual C4 schema validator, Homology readers and metadata
converter, shared BLAST sheets/calculators and requested-fact projection. It
retains full bytes, full result/sheet/components, a partial publication before
metadata and a saved-sheet temperature-1 recalculation.

No model, scientific executable, remote API, HPC resource, Store, episode,
retry, credit observation or completion proof is invoked. Complete root-owned
host and episode-path verification is a separate integration responsibility.

CHECK_RESULTS.json contains checkable numerical results and the actual
implementation digest. SOURCE_SHA256.json lists inspected runtime dependency
and owned test/document bytes. PYTEST.txt and pytest-result.json record the
actual focused verification command/result when run. Earlier Homology and BLAST
verification records remain unchanged.

The recorded focused run passed 369 tests in 134.58 seconds, including all 76
adapter tests and the existing Homology input/grader, explicit BLAST association,
C4 contract and bundle-value checks. The example assertions verify coverage
0.60/0.75, conditional weights 2/3 and 1/3, saved-sheet recalculation 0.8/0.2,
and unavailable weights before metadata arrives.
