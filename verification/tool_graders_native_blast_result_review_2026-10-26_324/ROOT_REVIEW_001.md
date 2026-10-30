# Root review of the combined numerical result worker and views

2026-10-26. Root read the complete R318 worker/views, its handoff and the actual
communication/reference consumers. R318's old hashes and receipts remain facts;
this additive record describes the reviewed root324 corrections.

The complete captured-artifact path now reports missing artifacts in original
bundle order. The failure schema uses constrained locator values for unavailable
artifact/search/row addresses; those locators do not claim possession. Actual
returned row identities and source references still require reference validation.
These are the two changes specified in CONTRACT_001.md. No numerical formula,
public function signature, episode decision or credit formula changed.

Current SHA-256 values:

- worker: `f5779805bdfaa49fcf1d7f0d1e52d66400f9b0799cee174918369ef7795de619`
- views: `0d3ad104b8d26249ff79806a586fa332a6fedd3b892bb991bbb56c232e3aa80d`
- root review tests: `2519bb6b79244b548c9ce585573977ffc92b1401d6a3e137da108c5d64a66362`

check001 passed **69 tests in 38.45 seconds**, using stable M317/addendum007,
20 GiB RAM, 4 GiB scratch and no wall cap. Its selected command, native local-job
receipt, stdout, stderr, JUnit and retained fixtures are saved unchanged. The
tests include three separate worker processes with Python hash seeds 1, 2 and 91:
identical logical missing-artifact requests produce byte-identical diagnostics
and numerical rows, retaining every independent usable report. All 67 existing
R worker/view tests passed along with the two root correction tests.

The worker retains full parser/calculator outputs, validates explicit calculation
parameters, saves qualified failures and preserves exact input/implementation
identities for reuse. It does not swallow a calculator exception as a successful
empty result, silently pick among conflicting PSSMs or invent a replacement model.
The views copy requested saved measurements and preserve missingness and units.
They do not perform an additional calculation or interpret scientific support.

This review accepts the R324 field-population/calculator/view implementation.
Tests used synthetic captured artifacts and previously retained native PSSM
material; they did not run native database BLAST. Actual episode publication,
scientific-record validation, complete child returns and the native convergence
extractor binding remain separately owned work. No inventory tally is increased
by this review alone.
