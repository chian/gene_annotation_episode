# convert2blastmask reader and common masking sheet — 639/001

This packet records the core implementation and its bounded verification. It is
implementation evidence, not a replacement goal or a scope amendment. The
original supplied attachment remains authoritative. The frozen 637 contract was
read in full and its SHA-256 remains
`c580517cbb07533479d59ade535962d2bf87b253dd48d7b6a7e23596782f11e1`.
No native conversion was executed by task 639. Tests consumed the original 636
native bytes and compared their retained size/hash identities.

## Delivered interfaces and ownership

* `sequence_masking_contracts.sequence_masking_molecule(operation: dict) -> str`
  validates the existing closed Operation authority and returns the explicitly
  supplied conversion molecule or the unchanged legacy substrate.
* `blast_maskinfo_inputs.parse_blast_maskinfo(content: bytes, *, occurrence: dict,
  native_format: str) -> dict` reads exactly the supplied occurrence bytes. It
  returns `blast_maskinfo_parse_v1`; no execution success is inferred from syntax.
* `blast_maskinfo_inputs.populate_mask_conversion(*, operation: dict,
  input_records: list[dict], parsed_maskinfo: dict, custody: dict,
  native_outcome: dict) -> dict` creates the conversion variant of
  `sequence_masking_parsed_output_v1` and delegates to the existing
  `populate_sequence_masking_sheet`, returning `sequence_masking_sheet_v1`.
* `calculate_sequence_masking_components` remains the only numerical authority.
  Both exact native rows and authenticated known-zero omissions enter its same
  existing `hmmer_search_grader._union` and `genomic_overlap_calculations._ratio`
  paths. The adapter does not calculate counts, fractions or confidence.
* The existing result views copy calculated values. A validated omitted native
  row has nullable `native_interval_count` with
  `native_mask_record_not_emitted`; that structural absence alone does not make
  an otherwise fulfilled selection partial.

Only the four assigned `sequence_masking_*` modules, the new
`blast_maskinfo_inputs.py`, the two new focused test modules, and this verification
packet were changed by this task. Root additionally authorized the narrow legacy
parameterization correction in `tests/test_sequence_masking.py`: its exact four
original program/mode cases are now explicit, while conversion required fields
are tested in the new module. Native execution, tool information, shared dispatch,
worker/publication integration and inventory changes belong to the other owners.
No prompt, episode template, scoring policy, yield or continuation rule was added.

## Native information, identity and missing-data behavior

The XML and ASN.1 text readers retain ordered native trees, actual byte/physical
line spans, root metadata, original group/member/interval ordinals, and every
interval's complete native Seq-id. XML's serialized program code remains separate
from ASN.1 text's absent integer code. Both single `int` and `packed-int` are
handled. Unknown identifier/location semantics remain explicitly unavailable
while their syntax remains retained. External DTDs/entities are never fetched.

The retained 636 XML/text examples cover local string/integer IDs, the accession
and version in `other`, and the database and typed tag in `general`. IDs 1, 3 and
4 from no-parse mode remain integer IDs. They are checked after occurrence-order
proof, not used to join header strings. Equal duplicate headers remain separate
input and native occurrences.

Authenticated structured order requires the original successful complete
conversion, complete valid supplied sequences, supported complete structure,
matching full masked-input population and exact lowercase-run/native relationships.
Explicit `native_masked_input_iteration` bindings require that same proof and the
matching original masked ordinal. The basis label alone does not prove a partial
record. A closed valid partial record can retain a caller-declared association
and exact conditional extent, with `unknown/caller_declared_association`; it is
not upgraded to authenticated native order. This corrects the initially overly
permissive explicit-binding branch found in root review, without changing any
frozen interface or the contract file.

Bare intervals remain one headerless native stream. A nonempty one-input stream
requires the explicit one-input binding. A multi-input stream stays unassigned.
An empty artifact has no synthetic native row, ordinal or locator.

Known-zero omissions are separate records. Failed/unknown/incomplete outcomes,
partial or unsupported parsing, caller-only custody, source conflicts, changed
options declarations and unavailable input substrates do not gain zero through
an empty XML document or an omitted native group. The successful uppercase and
failed malformed 636 XML are confirmed byte-identical.

Saved-sheet validation checks the convenience native fields against their
retained syntax, validates common-row/native/source relationships, and reruns the
single deterministic association constructor against saved original outcome and
custody. It performs no artifact I/O, converter invocation or acquisition.
Legacy saved shapes do not acquire converter-only fields or association values.

## Actual numerical checks

All quantities below were checked through the existing shared calculator and
against the requested public projection, with source identities retained.

| Retained example | Input length | Masked positions | Masked fraction | Native interval count |
| --- | ---: | ---: | ---: | ---: |
| Four-input occurrence 0 | 12 nt | 5 | 5/12 | 3 |
| Four-input occurrence 1, omitted uppercase | 8 nt | 0 | 0 | null, native row not emitted |
| Four-input occurrence 2 | 8 nt | 4 | 0.5 | 2 |
| Four-input occurrence 3 | 8 nt | 3 | 0.375 | 2 |
| Duplicate header, occurrence 0 | 6 nt | 2 | 2/6 | 1 |
| Duplicate header, occurrence 1 | 6 nt | 4 | 4/6 | 2 |
| Protein | 19 aa | 7 | 7/19 | 3 |
| Single interval stream | 8 nt | 4 | 0.5 | 2 |

Changed-symbol quantities are not applicable to conversion and remain null.
No uncertainty or gene-function-confidence value was invented.

## Bounded checks and historical attempts

All application imports and tests used the existing 529 runner with the existing
`check005/dependencies` closure: 20 GiB RAM, 4 GiB scratch, zero swap and no wall
cap. Host work was text/JSON/AST/hash inspection and stdlib editing/staging. Full
receipts, stdout/stderr, selected requests, test reports and audits are copied
under `runner_evidence/`; originals remain in the 529 attempt directories.

| Attempt | Actual result | Purpose |
| --- | --- | --- |
| `check099_mask_conversion_core` | return code 4; zero tests | Launcher was given `tests/` prefixes although it already adds that directory; historical error preserved |
| `check099b_mask_conversion_core` | return code 0; 84 passed in 1.44 s | Native parse/conversion cases and all 52 existing legacy tests |
| `check099c_mask_conversion_core` | return code 0; 41 passed in 1.20 s | Native-order correction, declaration and saved-tree consistency, seven exact legacy serialization comparisons and focused core regression |
| `check099d_mask_conversion_validation` | return code 0; 3 passed in 0.49 s | Converter-only association rejection in legacy variants and invalid-input/declared-options counterexample |

All four attempts were collected terminal and quiescent. Successful receipts
retain unchanged source, dependency, standard-library and interpreter pins. All
execution audits report no outside modules, no unbound native mappings, unchanged
native libraries and unchanged original retained inputs. Repeated successful
examples were not converted again; the later checks were justified by explicit
validation changes and the previously unverified exact-serialization requirement.

Saved-only recalculation was checked with file opening, sockets and process
launch denied. Exact legacy serialized sheets and components were compared with
the original input/calculator source frozen in check097 for dust/seg/windowmasker
interval and FASTA outputs, including native statistics and hard-mask ambiguity.
The existing legacy suite supplies malformed, missing, partial, failed and
numerical compatibility checks. The final converter-only validator delta does
not change the numerical path tested in check099c.

## Review trace and limits

The complete original four core modules, the shared union/ratio functions, and
the masking result worker, publication, result-view, results and returns paths
were examined. They preserve the numerical chain: retained input/output -> one
sheet -> one calculator -> copied requested components -> frozen typed returns.
This task does not claim a full review of all multi-provider execution consumers;
root owns and tests those integration points. Native binding owner640 owns
command construction/preflight/capture and their separate verification.

Completed at the core level: explicit molecule Operation/helper, XML and ASN.1
text parsing for the observed forms, bare interval handling, common-sheet
population, qualified association/omission evidence, one calculator path,
requested-value equality, pure saved recalculation, malformed/partial cases,
and legacy exact serialization preservation.

Still unfinished: ASN.1 binary decoding; established multi-root/multi-list and
continuation framing semantics; header-plus-interval input with actual supplied
sequence and length custody; unobserved Seq-id/header normalization; remote
resource binding/live verification. Multi-root and continuation data are retained
with explicit partial diagnostics, not declared complete. Synthetic single ASN.1
interval and doubled-quote cases establish reader tests, not additional live
native capture. Actual complete episode/parent delivery and saved-publication
replay are root-owned check101 work and are not established by these core checks.
This packet makes no whole-tool or whole-R7 completion claim.
