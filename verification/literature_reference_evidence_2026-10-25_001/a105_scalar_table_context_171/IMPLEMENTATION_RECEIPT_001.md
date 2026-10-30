# Scalar table-field context correction

This narrow engineering increment changes only `gene_annotation_episode/literature_partner_source_fields.py` and adds `tests/test_literature_scalar_table_context_171.py`. No goal, amendment, prompt, controller, credit or other production file was edited. All source fixtures are explicitly synthetic HTML/JATS-style table text; no original scientific paper, retained scientific case packet or actual private model/provider content was opened.

## Observed failure and change

The baseline reader interpreted `<td>10</td><td>-2 +/- 0.2</td>` as if the adjacent signed value were an interval endpoint of the selected `10`. The exact failing test uses the Unicode plus/minus marker and is retained in BASELINE_FAIL_001.log/xml. Baseline shared-source SHA256 was `5158e9ec97a7fa592ed4d03b81cba3e9c94a7331e35d4249df166899da0a925a`.

The shared parser now computes a separate direct-interval context bounded by definite table fields. Raw boundary extraction was factored into private `_table_contexts`; existing `_unit_contexts` preserves its previous transformations. New `_interval_contexts` recognizes actual tags before decoding entities, removes inline formatting, and treats structural markup within a field as whitespace. `_relation` accepts an optional private `interval_contexts` argument used only by the direct digit/dash and dash/digit interval checks. `read_source_number` supplies that view. Its public signature, output fields, witness coordinates, actual source bytes, named qualifier guards and soft-break numeric-clipping guard remain unchanged. Direct private `_relation` consumers retain the prior default behavior.

The new tests also exposed four baseline acceptance errors for genuine same-field intervals hidden by inline markup or line breaks. BASELINE_INLINE_INTERVAL_PROBE_001.json demonstrates those pre-existing errors without modifying the baseline. The corrected classifier rejects both endpoints of those intervals. It still accepts complete signed points in separate table cells and rejects a selection that clips the leading sign, decimal fragment or exponent.

## Verification

The final joined invocation passed **576 tests in 20.28 seconds**, with zero failures, errors or skips: 63 new parametrized boundary checks and 513 existing scalar, source-defined-unit, range-scope and structural/integration cases. The exact command and hashes are in FINAL_MANIFEST_001.json. Raw stdout and JUnit results are JOINED_002.log/xml.

Earlier records remain intact:

- FOCUSED_001: 57 passed, four failures exposing the genuine hidden-interval problem.
- FOCUSED_002: all 61 initial new checks passed after that correction.
- JOINED_001: 575 passed, one failed synthetic expectation. The test incorrectly expected a scalar after literal encoded `</b>` text to be an ordinary point; the unchanged lower-bound guard correctly sees the literal trailing greater-than character. The expectation was corrected without a production change. The distinct-field fixtures were also balanced into valid table markup before the final invocation.

Final production SHA256: `6683a39272203ff0b2844c951ab13b2333ae0ae16e3966c4eb932970f30764a8`. PROPOSED_DIFF_002.diff is the final production diff. No further production edits occurred during the final invocation. Root and calibration169 were notified of stable dependency bytes.

READ_PROVENANCE_001.json identifies the complete code consumers actually inspected. This verifies the finite parser correction and its bounded engineering consumers. It does not establish scientific assay reliability, correctness of model-supplied experimental roles, broader axis coverage, whole-project test status, actual model science or A105 adequacy. Root's earlier 126-check frozen run predates this helper change and remains separate historical evidence.
