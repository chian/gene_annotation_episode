# Root review: standard BLAST calculation and result-worker boundary

Accepted the declared R333 implementation boundary on 2026-10-26 after reading
all three production modules and all three test modules, including the final
malformed-HSP length correction and PSSM-exception regression. The full immutable
objective was read; its purpose and all16 principles were reread verbatim before
acceptance, followed by327's R interfaces, numerical fields, formulas and return
contract. Addenda001–004 apply. No original goal or accepted record was changed.

The final production identities inspected are:

| Module | SHA256 |
| --- | --- |
| native_blast_standard_database_calculators.py | 6e27b630bc8ab56cdc2254a450a2d5e216199ae6aed50ddfeb5b5202480885af |
| native_blast_standard_database_result_views.py | 521980e08f0ef8949a9971861560409d49362c980261dfa4b17b6075350f8b75 |
| native_blast_standard_database_result_worker.py | 1d114a609819900d0f3ba51a47dfa2a17f29469898f5b6d949d2e48d4298a994 |

Final test identities: calculators
fe13d45878a1b410ab8ce6f3beaf2402bdd356c461ab87f2737b0ae011d71c3f;
result_views
0c133b1f13b8207387ce9c61dccdc01d80e930e800465643e69876585ffcfc3e;
result_worker
d40d261d3f1143ea1c42865608e9b662980da8d6716b5679a8ec51beb185b721.

Root inspected the actual check007 stdout and local_jobs receipt:78 passed in
19.50 pytest seconds; returncode0;20GiB memory,4GiB scratch,no wall cap;
20.469823124 service-wall seconds. The worker tests retain30 distinct manifest
paths. Root did not rerun this suite or execute native BLAST. The earlier77-pass
check006 and its failed predecessors remain historical facts, not extra tools
or independent tests to add to78.

Before the last correction, root independently checked233 distinct file
descriptors in HANDOFF_EVIDENCE_002. The only mismatches were the two test files
then receiving the explicitly requested new assertions. The three production
hashes, retained native paired-format inputs, original receipts and indexed
worker artifacts matched that evidence. Later identities above supersede the
old source snapshot for new work, without rewriting its receipts.

The inspected functions preserve the agreed separation: supplied-byte sheets,
one public sequence calculation per search, one PSSM calculation per actual
input, complete saved scientific components, closed numerical rows, and pure
receiver-selected projections. The I/O worker verifies original captures and
the named implementation, writes immutable complete artifacts and byte-indexed
rows, and retains bounded failures with exception prose only in diagnostics.
Saved recalculation keeps original input interpretation and row identities;
projection neither repopulates sheets nor invokes a scientific calculator.

Root independently read saved worker generations showing:

- Equal priors and native bits20/18 give F/G masses1/.25 and weights.8/.2.
  Changing temperature from1 to2 gives masses1/.5 and weights2/3,1/3 in a new
  generation. Original input identity and prior generation remain unchanged.
- Actual supplied census counts100/10 give adjusted weights2/7,5/7 at the
  original temperature. The model remains a conditional reference calculation;
  taxonomy, source quality, coverage and related components are retained and
  are not silently used as weights.
- The actual tblastn PSSM worker preserves six original frequency-ratio cells
  0,1,2,3,4,5 and missing score cells as null, including saved reuse.
- A malformed table row retains its original position and an unavailable
  score, while the preceding valid row retains bits20 and a scoped native-row
  failure is delivered. No zero replacement occurs.
- The new PSSM-exception generation is partial, keeps the successful direct
  sequence calculation and HSP/search/sequence rows, emits no PSSM rows, and
  names artifact `query` at `/pssm/0` with calculation_failed and
  calculator_contract_invalid. Diagnostics point to that exact failure.

The reviewed numerical tests additionally establish full244nt versus reported
186nt and explicit selected186nt coverage, reverse interval[212,215),80aa to
240/243nt reference coverage,9nt overlapping-interval union,taxaA/A/B pair
fraction1/3 and target agreement2/3, and95%/125% assembly measurements becoming
.95/1.25 without clamping. Malformed JSON HSPs now preserve known reported
query/reference lengths12/15 while scores, pairs and coverage remain
unavailable. These are implementation examples, not new annotation findings.

Acceptance does not establish the E336 selected-tool/resource-child/received-form
path, prepared or live HPC deployment, every API route, every native format or
whole-tool completion. E336 is verifying the actual integration separately.
Multi-record FASTA provenance remains a known shared missing capability under
337 planning; native database path versus semantic census identity remains a
separate qualification limitation. The other fixed308 obligations remain.
The implemented-grader tally stays103/308 with205 outside it.
