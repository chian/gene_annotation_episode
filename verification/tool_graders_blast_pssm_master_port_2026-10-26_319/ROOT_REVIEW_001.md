# Root review of the PSSM master field/function port

2026-10-26. Root read the complete new shared master-input module, the affected
calculator import/dimension/molecule/master paths, final output-detachment
change, full handoff, comparison receipt and final regression/example receipts.
The original decoder was moved and reused. Metadata population no longer needs
to call a numerical calculator to obtain the native master sequence.

The final regression passed 236 tests including 66 focused extractor cases.
The 53-case retained original-calculator comparison reports zero complete
output/error mismatches. These suites overlap existing iteration tests and must
not be summed with other packet totals as distinct tests. The final receipt
records equal before/after source hashes, including root's per-search iteration
changes. All checks used local_jobs with 20 GiB RAM, 4 GiB scratch and no wall cap.

The retained native input example decodes 232 symbols with 232 mappings. Missing
master, unsupported encoding and incompatible length remain different qualified
outputs. Matrix/statistical calculations remain in the calculator. The public
metadata extractor has no calculator import, filesystem operation, acquisition
or native execution. Existing iteration's validator alias remains intact.

M317 and R318 consume this public function in their independently owned ongoing
integration. This review establishes the shared input port and unchanged
calculation behavior for the tested cases, not complete native search, resource
deployment or episode communication.
