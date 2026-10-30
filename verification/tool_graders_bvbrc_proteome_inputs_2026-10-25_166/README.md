# GenomeComparison B1 supplied-input extraction

Implemented the five frozen B1 functions in bvbrc_proteome_inputs.py.
The additive B1_PARAMETER_SOURCES_002.md extends only index_original_inputs
with optional additional_parameter_sources. Inputs and every returned envelope
are checked through the installed B0 contracts. Existing OriginalTask validation
is reused. No B0, schema, native parser, BLAST grader, shared test, registry,
inventory or episode file was edited by this worker.

The extractor retains original FASTA occurrences, exact headers/descriptions and
byte intervals, normalized full sequences, symbol counts and digests. It reads
the declared feature/genome/amino-acid sequence JSON arrays with original row
ordinals, source fields, numeric lexemes, optional identities and explicit
coordinate conventions. Original input indexing preserves original parameter
slots and source-bound submitted/effective thresholds.

These are retained supplied-input observations. Inventory counts and ordering
are not executed membership, execution witnesses or executed-proteome
denominators. No scientific joins or aggregate calculator is installed here.

## Concrete supplied examples

All examples are explicitly synthetic inputs processed by the actual reader.
FILLED_SUPPLIED_INPUT_EXAMPLES_001.json retains their full inputs and outputs.
Correction002's example is reused as supplied text, not represented as new
GenomeComparison output.

* The 59-byte correction input has 3 observed headers, 3 complete records and
  1 valid complete record. Its byte intervals are [0,34), [34,52), [52,59).
  Normalized sequences are ACDE, AA-?1 and the empty string, with counts 4, 5 and
  0. The latter two are invalid sequences with their actual UTF-8 hashes retained.
* The unknown-completeness FASTA has 2 observed headers, 1 complete record and
  1 valid complete record. Its last sequence, count and hashes are null even
  though the received bytes end in a newline.
* Feature metadata preserves explicit aa_length 0 and unknown-convention
  coordinates -2 and 0. A feature_id-only row and a patric_id-only row remain
  valid; a null neighbor stays at its original ordinal as an invalid row.
* The sequence snapshot retains uppercase MD5 text and normalizes "a cd" to
  ACD for a symbol count of 3. A separate all-zero MD5 conflicts with the
  actual sequence digest without overwriting either value.
* Original [G1,G2]+[F1]+[FG1], reference index 3, yields F1→ref, G1→comp1,
  G2→comp2 and FG1→comp3. Submitted min_ident 0 remains separate from the
  supplied effective value 0.1.
* Selecting effective parameters without a submitted source location preserves
  the effective index/snapshot and returns a partial result with an
  original_parameters requirement. Supplying the explicit submitted location
  retains both snapshots.

## Actual verification

* TEST_RUN_001.xml: initial B1 suite, 171 passed.
* TEST_RUN_002.xml and .log: 182 B1 + 52 B0 tests, 234 passed in 1.24 s.
* TEST_RUN_003.xml and .log: final 185 B1 + 52 B0 tests, 237 passed in 1.24 s.
* EXAMPLE_REPLAY_002.json: the 8 saved examples replayed through the final
  source, with exact result equality and source/dependency hashes.

The final command was:

    .venv/bin/python -m pytest tests/test_bvbrc_proteome_inputs.py tests/test_bvbrc_proteome_data_contracts.py -q --junitxml=verification/tool_graders_bvbrc_proteome_inputs_2026-10-25_166/TEST_RUN_003.xml

Tests cover byte-count/SHA mismatches, invalid UTF-8 and escaped surrogates,
CRLF and multibyte offsets, complete invalid/empty and incomplete sequences,
duplicate identities and full-sequence groups, duplicate JSON members,
malformed neighbors, null/blank/omitted cells, numeric lexemes/domains,
coordinate conventions, population completeness, original ordering, exact
parameter-source relationships, detached data and blocked network/subprocess
calls. Each returned shape is exercised against real B0 validation.

FAILURE_PROBE_001.json preserves the observed raw RecursionError for a
1,200-level malformed NativeSource. The B0 owner repaired that public boundary;
the final B1 regression verifies an explicit invalid envelope. The historical
failure receipt was not rewritten.

The complete authoritative objective and all sixteen principles were read
verbatim initially, after native parser/contract examination, and before final
handoff. Proposal001 was read completely; its B1/shared sections, correction002,
the freeze and the additive parameter-source handoff were reread before handoff.
The frozen data-schema SHA remained unchanged.

## Unverified and remaining work

This work inspected the complete existing native reader/contracts, OriginalTask
validator and BLAST pairwise sheet implementation. It tested synthetic supplied
bytes and pure B1→B0 composition. It did not acquire retained real
GenomeComparison results, invoke a scientific native program or service,
authenticate task custody, submit or monitor a job, populate aggregate scientific
sheets, calculate aggregate scores, or exercise episode communication.

B2 joins, qualified execution/occurrence witnesses, B3/B4 sheets/calculators,
full directional reports/producer retention, application adapter/result binding,
resource verification and selected-tool→episode return integration remain
separate required work. Passing this extraction suite does not establish the
complete GenomeComparison capability.
