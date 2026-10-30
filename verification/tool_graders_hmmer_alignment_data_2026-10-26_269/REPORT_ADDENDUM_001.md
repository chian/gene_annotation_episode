# Final B1 handoff: explicit native returned spans

The final contract reread found that native mapping endpoints were already
retained, but their returned source/target span quantities were not explicit
components. Each interval now also contains returned_source_span and
returned_target_span, each with value/state/unit/inputs. These use the actual
native returned endpoints, independently of map reconstruction. A native no-map
row has no target interval and therefore a missing target span.

For the live ali2model example requesting alignment 1-6 and returning alignment 2-5
to model 1-2, the three distinct numerical spans are 6 requested alignment columns,
4 returned alignment columns and 2 returned model positions. No other port,
top-level row shape, component registry, runtime or ownership was changed.

Final bounded verification: [check005/receipt.json](check005/receipt.json),
**48 passed in 0.61 s**, with 20 GiB RAM, 4 GiB scratch and no wall cap.
[examples002/receipt.json](examples002/receipt.json) reparsed/recalculated all 16
filled examples under those same limits. All native successful comparisons
passed. No native invocation was repeated for this additive change.

Current complete sheets/calculations are in [filled_002](filled_002), concise
numbers in [FILLED_EXAMPLES_002.json](FILLED_EXAMPLES_002.json), and current
source/evidence hashes in
[SOURCE_AND_EVIDENCE_MANIFEST_002.json](SOURCE_AND_EVIDENCE_MANIFEST_002.json).
The preceding report's native count (11: 7 successes, 4 expected failures), inspected
formats, explicit limitations and integration qualifications remain accurate.

| Final source file | SHA-256 |
| --- | --- |
| gene_annotation_episode/hmmer_alignment_preparation_data.py | 17177f61891d65eef10086716c4166f9b7338607cbf862c743ac25d1a7ef7975 |
| gene_annotation_episode/hmmer_alignment_preparation_calculations.py | 69619b4f1e15438da71e8ddbb0768baa20aad06a9ddb80d0dfbd43cded847f28 |
| tests/test_hmmer_alignment_preparation_data.py | 8bcd5af97fbaeaf7ae2554c3d2e4c35403f32ec0daba8235d47cff779761e825 |
| tests/test_hmmer_alignment_preparation_calculations.py | cf528acced87ecc6e0e142b74b5b561f72afa30925310ba50b42cebe4a7042e0 |

The immutable objective and all 16 design principles were reread verbatim after
substantial source/native study and at the tool-completion reviews, followed
by the exact B1 contract. This is an implementation record, not a runtime gate
or an additional observation. Production child/result/receiver integration
remains outside B1 ownership and is not claimed complete here.
