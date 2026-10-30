# Root review of iteration field/function implementation

2026-10-26. The accepted pure PSI/DELTA iteration component workload is
implemented and its stated verification is checked. This is not completion of
either native scientific tool or its episode path.

The deliverable is the field definitions and the functions
`populate_blast_iteration_sheet` and `calculate_blast_iteration_components`.
The nineteen saved example files are verification outputs of those functions.

Root read both initial production modules completely, then reviewed the changed
source/projection/count, checkpoint, inclusion and convergence paths and their
regressions. The final implementation preserves the exact delivered303/305/306
outputs. Its two narrow private helper calls are documented with exact arguments
and tested without admitting a sequence model for an unknown stage.

Three review findings were corrected:

1. A complete, source-qualified empty membership record now permits measured
   zero; an empty list is not treated as missing data.
2. An after-search checkpoint association alone no longer compares a matrix's
   length with the full query. The comparison requires the exact supplied PSSM
   master-axis relationship.
3. A copied native iteration label that conflicts with the retained source is
   incompatible. The actual source label remains retained.

Additional reviewed fixes preserve original collection completion/limit facts,
permit independent qualified checkpoint and search-convergence associations,
and ensure missing numerical cells point at an existing source container.

Root read check004's actual resource receipt and parsed its JUnit report:
324 tests, zero failures/errors/skips, 4.758 seconds pytest time. The receipt
records returncode0, 20 GiB RAM, 4 GiB scratch and no wall-time cap. This comprises
98 iteration cases and226 direct dependency regressions. Earlier failed receipts
remain unchanged. The final export receipt has returncode0.

Root independently checked every hash in IMPLEMENTATION_HASHES.sha256,
AUTHORITY_AND_INPUT_HASHES.sha256 and SOURCE_HASHES_AFTER.sha256. All matched.
The eight shared production dependencies are unchanged. All nineteen generated
sheet/component files match their saved manifest. Root inspected the generated
numerical summary and the underlying test assertions, including:

- A,B,B then B,C: raw hits3/2, unique targets2/2, added/removed/retained1/1/1.
- Explicit supplied membership A,B,B: raw3, unique2, duplicate1, included2.
- Existing sequence model: weights2/3 and1/3, not added across searches.
- DELTA domain fixture:42 bits minus same-model threshold40 = margin2 bits;
  query/model coverage50/100 =0.5.
- Authentic retained upstream PSSM inputs:232 positions and26/28 residue rows;
  the missing master remains missing.

The eight constructed search cases are synthetic. The two PSSM artifacts are
retained upstream input fixtures. Neither proves a new native search, source
membership/convergence extraction, actual resource execution or an episode
return. Saved-sheet offline recalculation and unchanged dependency composition
are verified by the passing tests; no redundant test rerun was needed after
review because source hashes match the tested implementation.

Still required: native membership/convergence extractors and authentic mode
fixtures; native producer/database deployment; actual metadata acquisition;
selected child execution, full result acquisition and authenticated requested
typed returns. No new tool completion or progress-tally increment follows from
this component review. Native producer313 and result-contract314 are separate
active workloads; VDB312 review is still open.
