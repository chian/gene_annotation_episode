# C dependency precision correction, 191

This delivery changes only the candidate calculator module, its dedicated test
module and dedicated fixtures. The calculation-contract module, exported
signatures, shared schema and all 18 quantity formulas remain unchanged. No N,
D, P, host, production-root, accounting, prompt, episode, controller or credit
code was edited. This is not whole-tool or live-service completion.

## Demonstrated corrections

The unchanged pinned producer was executed offline on explicit synthetic
feature/subsystem inputs. Repeating feature key `(1.1, f1)` with different
product, PATRIC ID and accession yields two joined `ss_f1` rows. The producer
retains subsystem context and computes three distinct genome/role pairs across
six joined occurrences. Its report remains `100 × 3 / (2 × 2) = 75%`.
`SOURCE_JOIN_WITNESS_001.json` records the actual source hash, environment,
operands, output hash and zero attempted network/authentication calls.

| Saved dependency case | Before correction | After correction |
| --- | --- | --- |
| Joined subsystem association repeated with feature-side metadata differences | incompatible/null; duplicate_record_conflict | available discrepancy 0 percent; native 75% preserved |
| Valid pathway EC formula plus unrelated malformed summary | missing/null | available discrepancy 0 percent; 75 − 100×3/(2×2) = 0 |
| Valid pathway feature formula plus unrelated malformed summary | missing/null | available discrepancy 0; 1 − 4/(2×2) = 0 |
| Valid subsystem role formula plus unrelated malformed summary | missing/null | available discrepancy 0 percent |
| Valid subsystem feature formula plus unrelated malformed summary | missing/null | available discrepancy 0; 1 − 4/(2×2) = 0 |
| Valid subsystem any-record formula plus unrelated malformed summary | missing/null | available discrepancy 0; 1 − 2/2 = 0 |

The summary cases each test an unidentified width-mismatched row and a distinct
identified row with a malformed number. `DEPENDENCY_CASES_BEFORE_001.json` and
`DEPENDENCY_CASES_AFTER_001.json` retain all 11 exact expected/actual results,
source hashes and full sheet/component objects under separate directories.
Each before/after pair uses the identical canonical saved sheet.

The duplicate exception applies only to the native subsystem role formula.
It checks genome/role operands, the genome/feature join identity and subsystem
ID/hierarchy across repeats, before filtering the requested entity. Existing
identity-conflicting rows and explicit duplicate-conflict flags still fail.
Full payloads, every occurrence and N's join qualifications remain preserved.
Non-joined raw/supplied duplicate handling is unchanged.

Formula checks use the selected summary's actual fields and its original
represented-genome population. The change removes only the unrelated-table-row
status dependency. Selected malformed operands, ambiguous summary identity,
changed/missing original genomes and partial objects still fail. The joined
role numerator still requires the complete applicable joined table. Unidentified
raw association rows and family rows still prevent available population/set
quantities. No native number, denominator, source-custody rule or formula changed.

## Terminal verification and preserved history

All C test/check commands used the root `.venv/bin/python`,
candidate `PYTHONPATH`, `PYTHONDONTWRITEBYTECODE=1`, and external logs. Pytest used
`-p no:cacheprovider`. Final C command was `python -m pytest -q -p
no:cacheprovider tests/test_bvbrc_comparative_systems_calculators.py` in candidate.
The separate source witness used root Python and the retained185 vendor
dependencies; it imports the pinned producer directly and does not import N/C.
`pytest_after_002.log` records **82 passed in 22.17s**, exit 0. The earlier
corrected run passed 79 tests. No live test was killed or restarted on an
observation timeout; every session reached a terminal result.

The two pre-correction logs retain the 11 intended failures and one separately
identified guard-test issue. The first guard fixture used the wrong family
document ID; the second reached an N-side short-row failure before C:
`comparative_systems_native_number_column_mismatch`. N creates an empty raw hex
lexeme when its column is absent, then its saved validator rejects that absent
column. This was reported to root and N was left unchanged. A full-width row
with an unavailable family identity now exercises C's population guard.
The N short-row issue remains a separate exact follow-up, not a C completion
claim or a silently relaxed source validator.

`CURRENT_N_TO_C_CHECK_001.json` independently checks all 27 current N-sheet
values against preserved `ROOT_N_TO_C_CHECK_001.json`, with exact expected/actual
values and source hashes. All match exactly: native 75% versus supplied
44.44444444444444%; densities 1 and 5/9; family occupancy 2/3, occurrence mean
1.5, CV 0.4082482904638631; all five native formula discrepancies 0; overflow
aggregate mean 128.5 and independent membership retained. Its final command
exited 0 (`current_n_to_c_check_002.log`). The first verification utility run
mistakenly compared root's file-byte SHA256 with C's canonical JSON SHA256;
that failed log is preserved, and the utility now verifies both conventions
separately. No scientific value changed because of that utility correction.

The focused recalculation test starts with a saved 75.125% native report:
discrepancy stays 0.125 when absolute tolerance changes to 0.125; only the
mismatch qualification changes. N parsing/building, network, process and file
operations are disabled. Original sheet and earlier components stay identical.
Saved validation disables both the calculator entry point and formula function.
The separate audit validates all 22 stored before/after histories without
calculation; historical unavailable results remain historical unavailable values.

`FINAL_AUDIT_001.json` verifies **45 original N/C/root evidence files, all 47
frozen N candidate files and all 99 frozen185 contract files unchanged**.
Original C manifests/results and root's pre-review receipt were not overwritten.

## Pins and exact consumers

Runtime calculator SHA256:
`424ad66e6faa5f246dc0e66ea7fc96a9bdc088f5de2a2484da2539d8532b1b5c`.
Unchanged calculation-contract SHA256:
`a47afffc86e539c3aa4bea8d848f4d71c68e10de7fbb8e0152c7a0a0783b0fad`.
All owned file hashes are in `C_REVIEW_OWNED_FILE_MANIFEST_001.json`.

P190 was notified of the exact runtime pin. Its
`bvbrc_comparative_systems_bundle_resolution.consume_bundle` consumes C after
actual N/D selection. Its projection paths use `validate_components`, copy
saved values and validate saved projections without recalculation. These full
consumer modules were inspected; provider-level verification remains P/root's
work, not a claim established by this C review.

I/root must consume the updated implementation pin through the actual
`AppServicePublications._grade` publication path, preserve separate saved
sheet/calculations, authenticate original-task/artifact/Data/producer custody,
and verify all requested typed own/received returns through episode boundaries.
No provider host, live ComparativeSystems task, live Data acquisition or actual
episode communication was executed by this review. Root owns integration,
production application and fixed accounting.

The authoritative attachment was read completely. Its objective and ENTIRE
DESIGN PRINCIPLES were reread verbatim after substantial native/source work
and at handoff, followed by the agreed numerical/interface and additive
002/003 contracts. Complete current C and relevant N parser/builder/validator
paths, retained producer functions and current P consumers were inspected.
