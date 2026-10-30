# HMMER input integration: observed verification

This is an implementation evidence record, not a goal or scope amendment.
The authoritative user attachment remains unchanged. Earlier attempts and
progress records remain intact.

## Result and limits

The selected alignment-input paths now reach the existing
`hmmer_alignment_preparation_sheet_v1` and
`calculate_hmmer_alignment_preparation_components`, through actual local native
execution, acquisition, saved calculations, publication and requested parent
returns. No new scoring definition or format-specific calculator was added.

The eight verified selected formats are AFA, A2M, PSI-BLAST, SELEX, Clustal,
Clustal-like, PHYLIP and PHYLIPS. A ninth Workflow case verifies alphabet
inference from the original source bytes without an explicit alphabet flag.
These tests use scripted episode choices and the real local execution/result
path; they are not configured-model scientific investigations.

This does not close the entire R2 HMMER/Infernal/Rfam group. TASK/STEERING and
resource presentation remain unfinished. No new API/HPC verification occurred.
Authentic older binary-revision and big-endian producer coverage, historical
HMMER2 binary handling and EVD interpretation remain unestablished. Native
unsafe or undefined parser cases excluded by the frozen source contract remain
excluded, not silently accepted.

## Attempts and correction evidence

| Retained attempt under packet 529 | Passed | Failed | Pytest seconds | Result |
|---|---:|---:|---:|---|
| check013_input_integration | 242 | 25 | 17.341 | Initial assembled integration exposed defects; failure evidence preserved |
| check014_input_repairs | 295 | 0 | 6.262 | Targeted repairs, shared calculations and retained native-build regrading passed |
| check015_input_workflow | 9 | 0 | 232.398 | Eight format cases and one inferred-alphabet case passed through actual Workflow returns and replay |

All three original handles were collected after terminal and quiescent states.
Every receipt retained unchanged source, dependency, standard-library and binary
pins. Execution audits contain no outside module imports or unbound native
mappings; native-library and original fixture hashes are unchanged. Execution
used the existing bounded runner: 20 GiB RAM, 4 GiB scratch, zero swap and no
wall-time limit. No application or scientific package was imported on the host
for these checks.

`INTEGRATION_RESULTS_001.json` maps each of the 25 initial failures to its
passing follow-up. Twenty-three original failed selectors passed check014.
The other two had already completed their native `hmmbuild` work successfully;
new tests regraded those exact retained outputs with native execution forbidden.
The original two complete producer tests were not rerun. The same MAP, checksum,
alphabet, source association and return assertions are used by their shared
test helper.

Concrete corrections were:

- Normalize declared format case only at the local parser dispatch and validation
  boundary. Preserve the actual existing native CLI spelling and original job
  settings. `A2M` and `Clustal` are valid existing native argument values.
- Preserve usable Stockholm geometry with qualified optional annotations. Keep
  known-zero decoded populations distinct from unattempted/unknown decoding;
  retain malformed encoding qualifications rather than rejecting producer facts.
- Use the practical writer's existing canonical JSON serialization for numerical
  artifacts, with reversible escaping only for unpaired surrogate bytes. This
  preserves every previously encodable output byte and leaves global receipts
  and digests unchanged.
- Correct test inputs to supply their declared format or intended explicit
  alphabet. Do not relax operation validation to accommodate incomplete tests.
  All prior numerical assertions in the two adjusted regression files remain.

The proposed missing-return defect was a root review error: the immediate return
was already present in the complete function. No production fix was made for
that claim. Its focused regression passed.

## Numerical and return examples

For each of the eight format Workflow cases, the same logical alignment is
`AAAA`, `AAAA`, `C--C`. The existing GSC calculation yields weights
`[0.75, 0.75, 1.5]` and model columns `[1, 4]`. The requested return contains
exactly these saved quantities:

| Quantity | Value |
|---|---:|
| Input sequences | 3 |
| Input alignment columns | 4 |
| Mapped model positions | 2 |
| Native mapping rows | 1 |

The inferred-alphabet example returns `[3, 12, 6, 1]`, with model columns
`[1, 4, 5, 8, 9, 12]`. The original-byte probe determines DNA. Outputs inherit
that established source alphabet rather than being guessed again.

Retained check013 native builds also passed regrading without another build:

| Native source | Sequences | Input columns | Native model positions | Native checksum | Requested return |
|---|---:|---:|---:|---:|---|
| A2M insertion fixture | 5 | 17 | 12 | 2776554218 | `[5, 12]` |
| Clustal fixture | 3 | 12 | 12 | 3986124183 | `[3, 12]` |

The A2M model map is `[1,2,4,5,6,8,9,10,13,14,15,17]`; the Clustal model map is
`[1,2,3,4,5,6,7,8,9,10,11,12]`. A deliberately conflicting saved model alphabet
does not pass source qualification.

All nine Workflow cases passed saved-only recalculation with original input and
native-attempt directories hidden and acquisition, parsing and native execution
forbidden. Closed replay additionally forbade calculation. Original forms,
artifact bytes and histories were unchanged. One completed child contribution
remained one parent observation, and validated practical completion set future
expected gain to exact zero.

## Snapshot and remaining test limits

Root compared 19 relevant current production/test files with the final frozen
check015 snapshot; all match. The exact paths and hashes are in
`CHECK015_CURRENT_PINS.json`. Earlier parser/native conformance evidence remains
in packet 529 checks007–012, including 378 selected original-source native
comparisons. These successful tests were not repeated without a new reason.

The explicit-DNA fixture adjustment in
`test_actual_gappy_fragment_map_matches_native_forward_map` was inspected but
that native generator selector was not rerun. Its retained native map fixtures
were checked by the calculation tests in check014. This is not a claim that
every historical HMMER test was rerun in one suite.

The separate fluorescence packet548 adds two reviewed source/shared-analysis
mappings and zero implemented operations. Its source hashes and complete
functions were reviewed. Proposed nested data types and invocation contracts
still need to be frozen before coding.
