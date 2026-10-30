# R333 additive verification: 78 passing cases

The six owned R source/test files implement the standard five BLAST database
field definitions, deterministic calculators, numerical row population,
projection, identity functions and immutable file worker. The declared pure
ports and the actual-file worker are verified within this boundary. E336 owns
the separate episode selection, publication, communication and consumer proof.

Final check007 passed **78 tests in 19.50 seconds** with return code 0. Its
existing local_jobs receipt records 20.469823124 seconds of service wall time,
20 GiB memory, 4 GiB scratch and no wall cap. Memory was enforced by the
systemd cgroup, swap was disabled, and observed scratch was 10,964,992 bytes.

```
.venv/bin/python -B verification/tool_graders_standard_blast_database_results_2026-10-26_333/run_checks.py check007
```

The runner uses LocalJobPolicy(20*1024**3,4*1024**3,None), with complete pytest
worker artifacts retained under check007/pytest-tmp. No native database BLAST,
scientific API, HPC access, installation or download was performed. The
resource-failure cases inject corresponding exceptions; they are not physical
out-of-memory or full-disk experiments. These checks do not add tool-count or
scientific-credit observations.

## Changes after the historical 77-pass result

- Malformed original JSON HSP slots now retain the positive exact length of
  their valid native hit and the independently authenticated reported query
  length. The regression retains 12 nt and 15 nt, including those exact raw
  coverage denominators. Native scores, paired geometry and qualified/full
  coverage remain unavailable; pairs remain empty and geometry_available is
  false. Valid following HSP pointers still resolve original ordinals through
  the saved303 component indices. No missing or conflicting length is inferred.
- The focused actual-file worker test injects one PSSM calculator ValueError.
  The saved item is exactly {artifact_key:"query",components:null}, while the
  original PSSM sheet remains present. The successful sequence result retains
  its actual303 tag, native HSP bits 20 and qualified reference length 9 nt.
  There are no fabricated PSSM numeric rows. The closed calculation_failed /
  calculator_contract_invalid failure names the original artifact and links to
  the diagnostic containing the exception. The manifest does not contain that
  exception text. This follows accepted327 CONTRACT_ADDENDUM_004; no catch was
  broadened and there is no alternate model or retry.
- Two worker docstrings now use parser terminology. Public names are unchanged.

The earlier check006 receipt, its 77-pass result, HANDOFF_EVIDENCE_001/002 and
VERIFICATION_001 remain unchanged. All earlier failed receipts also remain.

## Retained numerical evidence

The full R1–R10 checks documented in VERIFICATION_001 all ran again. Bits20/18
with equal priors produce .8/.2 at T=1 and 2/3,1/3 at T=2; the actual census
100/10 produces 2/7,5/7. Taxa A,A,B produce one matching pair among three and
target-A fraction 2/3. Supplied completeness95% and contamination125% remain
.95 and1.25, preserving their source, method and linkage.

Translated overlap [0,6) union [3,9) spans 9 nt. tblastn80 aa spans240 nt of a
243-nt reference, giving240/243. The unchanged retained paired BLASTX JSON/table
evidence keeps its paired provenance. The separately labeled synthetic database
range has reported186 nt, full244 nt, selected[29,215), qualified paired186 nt,
full coverage186/244 and first reverse interval[212,215); raw reported-axis
coverage remains null. No selected range leaves selected-query coverage null.

All five mode-specific actual-file worker cases, actual tblastn input-PSSM
population, saved-sheet recalculation without parsing/population, projection
without recalculation, immutable output seals and original attempt/implementation
authentication passed. Synthetic reports are not represented as native database
execution. Missing metadata does not erase valid native scores.

## Frozen sources and artifacts

HANDOFF_EVIDENCE_003.json contains all six current source/test hashes, the
unchanged authoritative objective/plan, accepted addenda001–004, two unchanged
retained paired files, all seven receipts, the actual request's complete loaded
implementation inventory and 30 distinct check007 worker generations. Pytest
current-directory aliases are deduplicated. Expected historical artifact seals
and actual current hashes are separate because fault tests deliberately mutate
some original/saved bytes after sealing.

| File | SHA256 |
| --- | --- |
| native_blast_standard_database_calculators.py | 6e27b630bc8ab56cdc2254a450a2d5e216199ae6aed50ddfeb5b5202480885af |
| native_blast_standard_database_result_views.py | 521980e08f0ef8949a9971861560409d49362c980261dfa4b17b6075350f8b75 |
| native_blast_standard_database_result_worker.py | 1d114a609819900d0f3ba51a47dfa2a17f29469898f5b6d949d2e48d4298a994 |
| test_native_blast_standard_database_calculators.py | fe13d45878a1b410ab8ce6f3beaf2402bdd356c461ab87f2737b0ae011d71c3f |
| test_native_blast_standard_database_result_views.py | 0c133b1f13b8207387ce9c61dccdc01d80e930e800465643e69876585ffcfc3e |
| test_native_blast_standard_database_result_worker.py | d40d261d3f1143ea1c42865608e9b662980da8d6716b5679a8ec51beb185b721 |

The complete immutable objective and all16 principles were reread verbatim,
followed by the complete accepted327 plan, acceptance and addenda001–004.
Objective SHA256 remains
11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7;
plan SHA256 remains
c6f66f93472fcb32798473158153ab3158920f950b79ab65dfcda88af6ff07f1.

No R production edits remain planned. E336 has these frozen source hashes for
its separate verification. Live prepared HPC execution and API-route work remain
unverified here. Unknown full sequence identity/census remains unavailable;
whole-reference functions are not inferred from CDS annotations. The unchanged
303 database semantic-name versus native-path qualification and unsupported
binary/legacy PSSM forms remain explicit limitations. No existing scientific
module, shared integration file, accounting, evidence axis or annotation-credit
formula was edited by R333.
