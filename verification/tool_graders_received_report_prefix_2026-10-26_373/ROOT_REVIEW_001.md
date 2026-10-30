# Frozen received-report prefix: root verification

Recorded 2026-10-26 America/Chicago (final test receipt is 2026-10-27 UTC).

## Accepted change and its boundary

An episode's inherited report operands are limited to reports its parent had
actually received when that episode was constructed. A smaller original child
commission index is not evidence that the report had already arrived. This
matters for independently returned RNA sheets and for actual failure forms
that have no scientific source record.

The existing `runtime_receipt_inheritance` table now stores a nullable frozen
received-report prefix. It contains the original successful received form's
identity and the original contract/form digests. It does not copy scientific
data, create a new scientific record or produce an action observation. Existing
rows without a prefix retain their original manifest; replay does not fill them
with subsequently received reports. New empty prefixes remain empty on replay.

`EpisodeReceipts.read_manifest` reads the existing manifest without initializing
schema or committing the caller's transaction. Commission and AppService
inheritance validation compare the complete stored manifest. Constructor schema
initialization and `bind` use the existing Store transaction/savepoint behavior;
neither commits a caller's unfinished commission.

The root reviewed the changed receipt implementation, commission and AppService
consumers, the new tests and the relevant model-context construction paths. The
new prefix remains host metadata; it is not added to a child model prompt. The
complete RNA operand authority path has its own E371 verification and is not
declared complete by this shared-component review.

## Actual verification

`check002/stdout.txt` records **135 passed, 8 deselected in 756.72 seconds**.
`check002/receipt.json` records return code 0 and `source_unchanged: true`.
The bounded runner used the existing local job implementation with 20 GiB RAM,
4 GiB scratch and no wall-time budget. It retained the complete source snapshots,
before/after hashes, request, stdout, stderr and native job receipt.

The four test modules were:

- `tests/test_episode_received_report_prefix.py`;
- `tests/test_episode_commissions.py`;
- `tests/test_bvbrc_appservice_custody.py`;
- `tests/test_episode_receipts.py`, with the known eight baseline failures
  explicitly deselected as described below.

The 23 new cases verify actual null-source report forms; late returns with lower
commission indices; replay and reopen; other parents/runs and failed attempts;
initially absent journal tables; rollback of binding, reading and construction;
legacy schema/row migration without retroactive authority; read-only missing
table and ordinary SQLite tuple behavior; malformed saved metadata; full
commission/AppService prefix equality; and rollback with absent, legacy and
current receipt schemas.

Final changed source pins:

| File | SHA256 |
| --- | --- |
| episode_receipts.py | 359a59c73bb93c49e2c5486613fe91b0bc14a8bd2a103fdd81ac8b2ae914bd6b |
| episode_commissions.py | a9f27938fd7948942f6e184b0daec123ab5d5542cda484ea8d412d0ea5ee838a |
| bvbrc_appservice_custody.py | b74e31706bf23b711cc1e2820e0a9951e698f272f828d76c32bc356289453a28 |
| test_episode_received_report_prefix.py | 4a790a726cb519a5110467e3175d32ad9e45fea8a0b32cd68d714debeb7b5f70 |

## Retained failed run and exclusions

`check001` remains unchanged. It recorded 131 passes and nine failures. One was
a new test fixture trying to deepcopy an immutable MappingProxy; the fixture was
corrected to use the existing plain-value conversion. The other eight were the
same broader receipt tests previously reproduced with pre-360 modules. They were
not repaired, rewritten or silently counted as passing here:

- `test_runtime_credits_only_requested_child_information_and_replay_keeps_history`
  (two parameterizations);
- `test_native_workbook_pages_return_one_finding_through_child_form_and_replay`;
- `test_selected_state_read_delivers_existing_findings_but_detail_read_does_not`
  (two parameterizations);
- `test_different_parent_scalar_does_not_remove_child_inherited_information`;
- `test_failed_form_repair_and_interruption_preserve_work_and_observation_boundary`
  (two parameterizations).

Their earlier reproduction is recorded in
`verification/tool_graders_rna_structure_integration_2026-10-26_360/ROOT_REVIEW_001.md`
and its `check014` evidence. They remain unfinished U05 work, distinct from the
original completed U04 regression repairs. This is not a full-suite pass.

The subsequent constructor transaction repair and three additional rollback
cases are recorded additively in 362 `CONTRACT_ADDENDUM_011.md` and included in
the final check002 result. No scientific formula, annotation credit, completed
observation, local stopping rule or resource selection changed in this work.
No native RNA, API or HPC scientific execution was needed by this check. No
additional tool is counted complete.
