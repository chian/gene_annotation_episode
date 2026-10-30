# Concrete verification cases for the proposed contract

These are specifications for future implementation checks. They do not claim the parser/calculator/service exists. `fixture-manifest.json` identifies documentation bytes versus synthetic cases. `single-input-identity.json` is a clearly example-scoped metadata operand, not a production source record. Every JSON file is complete as a supplied fixture unless explicitly named incomplete/unsupported; a fixture is not automatically a valid producer response.

Use the official expected ID, exact 119 nt query and hash from `single-input-identity.json`. A synthetic native-response test capture can specify complete, HTTP200, matching artifact digest, request job ID and submitted hash. The populated proposal in `proposed-single-sheet.json` instead says `evidence_kind: official_documentation_example` and `http_status: null` to avoid implying an actual result request. Its `proposed-single-calculation.json` contains actual filled numerical components; both are hand-authored expected outputs, not executed production reader/calculator results, as `proposed-output-provenance.json` records. Source refs are separate fixture refs. Proposed calculator parameters are explicitly supplied, not silently filled.

## Single source-example result

Input `official-single-result.json` is the exact JSON object extracted from the official docs source, not reserialized. Expected parser result: single JSON format, complete valid native row population, one retained row `/hits/5S_rRNA/0`, declared=observed=1, exact query/job match. Metadata absence is ordinary missingness, not a failure of the native result.

| Component | Expected numerical value | Meaning |
|---|---:|---|
| native score | 104.9 | bits, unchanged |
| native E | 4.5e-24 | native E-value, unchanged |
| native GC | 0.49 | rounded reported fraction, unchanged |
| original native endpoints | 1,119 | inclusive physical query positions, + strand |
| normalized query interval | [0,119) | zero-based half-open |
| query length / span | 119 / 119 | nt |
| hit span fraction | 1.0 | span over submitted query length |
| + strand row count / sum / union / excess | 1 / 119 / 119 / 0 | no duplicated span |
| + strand union fraction | 1.0 | exact known query denominator |
| - strand row count / sum / union / fraction | 0 / 0 / 0 / 0.0 | measured empty opposite-strand reported population |
| model display endpoints | 1,119 | display positions; not full model length |
| represented model positions, **if separately supplied valid simple-display parse** | 119 | represented positions in this unabridged example |
| model-consensus compared / equal, **if separately parsed** | 119 / 79 | canonical symbol comparisons after uppercase and T/U equivalence; model consensus is not a physical reference |
| conditional consensus equal fraction, **if separately parsed** | 79/119 = 0.6638655462184874 | comparison only; not annotation probability |
| model full length / model coverage | null / null | not supplied; missing denominator |

Without supplied `alignment_components`, represented-model/count/correspondence numbers are null with `alignment_not_parsed`; the table's conditional expected numbers are for the separate display parser workload. The fully retained original strings remain available. PP contains119 `*` symbols; each source example position's placement-bin meaning can later be represented as [.95,1], **not** a point value1.0 or query-annotation confidence1.0. Do not claim timing uncertainty, database release, model release, version, threshold, inclusion, search-space or number of models from this fixture. OpenAPI version0.1.0 and display119 are not substitutes.

## Empty and absent results are different

- `synthetic-empty.json`: exact original nonempty query/job, complete body, numHits0 and hits{}. Expected complete reported population, zero rows, both strand union lengths0 and fractions0.0. No family annotation or organism-wide absence claim. No per-hit metrics exist; do not fabricate a dummy zero-score hit.
- Actual retained `../source_evidence/official-old-job.result.json`: empty query with numHits0. Expected rejected attributed result with `rfam_result_sequence_identity_empty`; sheet/calculation null. The raw declared0 remains in the artifact but is **not a measured zero for this input**. `/status` NOT_FOUND remains native absence evidence.
- Actual retained zero-byte tblout/out: artifact-only retention; scientific format unverified, no inferred empty Infernal table. A later complete native header/footer-bearing no-hit table can be a different valid case if its format/identity is established.

## Partial data and independence

`synthetic-partial.json` supplies three rows under the same family; native declared count3 agrees with observed count3.

1. Row0 is the complete source example: all native scalar and query-span numbers above survive.
2. Row1 has end120 with known query length119: independently valid score104.9/E4.5e-24/GC.49 survive, but interval/span/fraction are null, reason coordinates_invalid and issue coordinate_out_of_bounds. Never clamp end120 to119.
3. Row2 has start110,end10,strand-: scalar interval [9,110), span101, fraction101/119 = 0.8487394957983193. Its copied `#SEQ 1 ...119` display contradicts the reverse hit; correspondence fields unavailable with alignment conflict. Do not reuse the copied display to fabricate 119 aligned reverse residues.

Expected overall parse/projection partial, preserved all three raw rows, valid-interval count2. + strand valid-subset sum/union119, - strand sum/union101. Global interval-population completeness false; + strand completeness false because row1's interval is unusable. The reverse-strand scalar population is complete for its known rows even though its alignment projection is partial. Aggregate values carry these qualifications. Native row count agreement alone does not establish full numerical completeness.

`synthetic-duplicate-hits.json` contains two exactly repeated rows. Preserve both distinct JSON pointer row identities. Native row count2, duplicate_row_count1, + strand sum238, union119, overlap_excess119, union fraction1.0. No score sum209.8, multiplied probability or two independent supporting observations. - strand remains0. Repeated acquisition of the identical source does not create a new scientific contribution.

## Contradictions and unsupported forms

| Fixture/case | Expected retained behavior and failure |
|---|---|
| `synthetic-conflicting-job.json` | Reject attributed whole result; job identity conflict; exact raw body retained; no sheet/calculation for assigned job |
| `synthetic-conflicting-sequence.json` | Same length is insufficient: exact hash conflict rejects whole result |
| `synthetic-conflicting-count.json` | Preserve valid row's score and span; declared2, observed1; partial with hit_count_conflict, reported_set_complete=false; valid row union119 is a qualified observed subset |
| `synthetic-conflicting-strand.json` | Native score/E/GC survive; coordinates1..119 with strand- contradict direction; query interval-dependent fields unavailable, do not flip/swap silently |
| `synthetic-untyped-multiple-envelope.json` | OpenAPI permits arbitrary items; recognize multi shape but scientific parser returns unsupported, sheet=null and multiple_sequences_schema_unestablished. This fixture's item is intentionally invented and is **not** an example of native multi-item semantics |
| `synthetic-unsupported-display.json` | Native row score/coverage remain; shorthand-bearing display intentionally incomplete, so correspondence unsupported/invalid and no invented model span/length. This is not a valid native truncation example |
| Missing score; E negative; GC>1; boolean start; NaN or duplicate JSON key | Field-specific unavailable values or whole JSON rejection as specified; preserve all independently valid scientific cells and exact raw bytes; valid numerical0 remains0 |
| Complete-looking JSON bytes with capture.body_complete=false | Retain raw capture as partial; never mark complete reported population merely because current received bytes happen to parse |
| A supplied accession-only current RF00001 model of length119 | Retain metadata unbound; native model-release/digest absent, so model_length and model coverage remain null with model_binding_unverified |
| Two conflicting purported same-model lengths | Metadata conflict, no arbitrary first denominator; native query numbers remain usable |

Missing schema metadata is not filled by convenience constants: native CM/HMM mode, bias, pass, inclusion, native truncation classification, full searched population and actual search thresholds remain absent in these JSON fixtures. The family-map name is not a function assignment. Taxon/source-quality/annotation confidence are not reconstructed from RF accession alone.

## Required deeper examples that remain to be acquired

These are not falsely supplied as existing native fixtures:

- A small successful current single-query request/submission/status/result set with exact bytes and query scope, plus a valid no-hit response if actually obtained.
- A real two-query batch result with unique names, followed by the exact format's handling of repeated first-token names and identical sequences. Preserve occurrence ordinals; never zip sorted name lists or collapse by digest. If native output lacks enough mapping information, return ambiguity and retain all bytes rather than assign a first match.
- Actual deployed tblout and out from that same known job, qualified for headers/version/mode/footer/count, including absence/partial-body cases. Compare same-job representations without treating them as independent searches.
- Valid native reverse-strand, insertion/deletion, local-end, truncation and missing-PP displays, including any wrapping introduced by the remote JSON producer. The richer parser must distinguish recoverable native omitted-position counts from exact unrepresented correspondence.

Loopback tests should assert precisely one request per selected operation; no submit hidden in status/fetch; no extra GET hidden in submit; no redirect/retry/sleep; preserved uncertain POST; replay without a new request; explicit original handle; exact error bytes; original duplicate-name member mapping. Integration tests must use the actual configured API branch, selected operation journal, publisher and immediate-child typed custody, not a direct parser invocation masquerading as integration.

The local example verification script checks only the supplied fixture bytes and elementary expected arithmetic. It does not establish any of the deeper native or production integration requirements above.
