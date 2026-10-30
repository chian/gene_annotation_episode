# Projection verification corrections, 2026-10-25

These receipts preserve failed checks and subsequent corrections. Earlier logs,
serialized examples and accepted contracts remain unchanged. This is an
implementation record, not a runtime gate or a claim of live execution.

* `TEST_INITIAL_001.txt`: 7 failures, 70 passes. One implementation defect was
  the static absent-cell unit for `continuity_delta`; its actual unit is
  `augmented_observations`. Other failures exposed incorrect test expectations:
  the selected DNA deletion count is 1; the selected protein detail count is 2;
  the raw R group record is physical row 1; the underflow pair is retained in
  raw R while the filtered pair export is empty; and XMFA source positions
  48/1 are zero-based, corresponding to one-based positions 49/2.
* `TEST_SECOND_002.txt`: all 77 checks passed after those corrections.
* `TEST_THIRD_003.txt`: 7 failures, 70 passes after additional native identity
  checks. XMFA metadata `member_number` is a saved NativeNumber record, not a
  bare integer; projection now reads its actual value. The remaining setup
  error followed the shared codec's accepted restriction of requirement and
  reason references to `@requirements`; the deliberately forged requirement
  test now uses that valid scope before testing unknown identity rejection.
* `TEST_FOURTH_004.txt`: 3 failures, 91 passes. Expanded actual alignment metric
  coverage exposed `site_count` being caught by the `site_` row-metric prefix;
  it now maps to its saved top-level cell. The incomplete-original-map test
  also selected an unaffected row; it now selects the actual partial row 1.
* `TEST_FIFTH_005.txt`: all 94 checks passed.
* `REPLAY_INITIAL_006.txt`: a verification-helper failure on the legitimately
  empty `frequency_deltas` list in the all-missing MetaCATS example. The helper
  now selects a frequency delta only when an actual row exists. No scientific
  result or production formula was altered.
* `REPLAY_SECOND_007.txt` and `SAVED_REPLAY_006.json`: all 21 serialized examples
  and 599 requested fields passed the blocked replay.
* `TEST_FINAL_008.txt`: all 100 checks passed after adding the accepted bounded
  scientific-symbol checks. `REPLAY_FINAL_009.txt` and `SAVED_REPLAY_009.json`
  passed the same 21-example/599-field replay and proved that the pinned source
  files did not change during the run.

Accepted contract corrections are recorded separately by root as
`MISSING_MEASUREMENT_METHOD_025.md`, `NATIVE_MEASUREMENT_METHOD_026.md` and
`CLOSED_ALIGNMENT_RETURN_VALUES_027.md`. They permit null method identity when
no method is recorded, distinguish native observations from calculated cells,
and close the outward XMFA selection record while preserving original
commissioning selections. They do not change scientific calculations.

The final additional replay will use the shared owner's finite registration
of actual consumed diagnostics. Its receipt and hashes are additive because
that registry changes the exact outward qualification schema and values.
