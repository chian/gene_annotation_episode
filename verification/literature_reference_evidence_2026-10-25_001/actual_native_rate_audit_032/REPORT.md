# Actual native rate audit032

Snapshot transaction: 2026-10-26T12:43:43.474524+00:00 to 2026-10-26T12:43:46.078813+00:00.
Host saved-only replay completed: 2026-10-26T12:45:14.227912+00:00.

Passed scoped public-record and saved-only projection checks. Actual numeric population is **not demonstrated**: the saved operation completed, but all ten saved components are unavailable. All eight parent-requested projected cells have null values with `source_defined_unit_definition_required`. This is preserved missingness, not a zero score.

| Saved arm | Literal number | Native unit | Defined unit supplied | Converted value |
|---|---:|---|---|---|
| reference | 7 | U/mg | False | null |
| test | 0.1 | U/mg | False | null |

No scientific interpretation of those source assignments was performed. Pinned saved validators confirm selected number/unit/meaning associations and immutable reference identities. Original source bytes were neither copied nor read. No native parser, population calculator, model transport, delivery, numerical fit, repricing, or controller observation ran. Saved unit-validation arithmetic was used only to validate original associations.

Decision26 saved sheet: `source_3c0a6e5c5495d870e1d30d1d`. Payload SHA-256 `ac879bd246a69e45368a3322195f6e46f7e2e4705b06ca384d4f3ad4f7db3799`. Request SHA-256 `be065a7a85d9ebb6fc307e34ff97192db12d38c544986ee860d518b5ffb9c943`.

The original selected native form has 24 required fields. It omits eight explicit reference namespaces: assayed_subject_ref, experiment_ref, and both arms’ subject/construct/preparation references. It is not an exact schema copy. `format=reference` still checks actual custody/existence; its absent namespace alone does not check record type. Downstream native repository reads validate generated reference/context/term identities and source association. The actual LiteratureEpisodes semantic admission method reprojects and compares exact saved values/bindings. Detached invalid-binding probes were rejected by both repository and that consumer; an unreceived sheet was rejected. These are host diagnostic probes, not actual admission.

Snapshot counts: 31 actions, 19 observations, 19 completion slots, one native rate operation, zero report attempts, zero closed forms, zero parent native-cell admissions.

| Episode | State | Own action rows | Observations | Original completion slots |
|---|---|---:|---:|---:|
| literature | active | 28 | 18 | 18 |
| annotation | active | 3 | 1 | 1 |

All saved observations matched unique completed own actions, original credit, unit identity and completion-slot input. Failed attempts retained their original codes and null credit. Population26 supplies one child observation at zero original credit; internal extraction/projection added none. Original public table hashes stayed equal through constructor setup, replay and a second Store reopen. No new tables were needed in the owned backup.

Final process cut 2026-10-26T12:45:44.741962+00:00: PID1614626 present=True, state=S, same original start_ticks=True; terminal RESULT.json present=False. Process liveness does not prove productive progress or scientific completion. The audit does not poll or resume it.

Parent closure/admission remains unverified and pending, not failure. Recheck the same existing child handle through public records later. The snapshot can precede subsequent live changes. This establishes an independent host repository reconstruction from a consistent SQLite backup, not a detached/model-run reconstruction or byte-identical original SQLite file. The backup includes unqueried private database tables; private provider files were not copied. Only two immutable sheet/request artifacts were copied.

Reproduce the frozen snapshot replay from repo root:

```sh
.venv/bin/python -B -P verification/literature_reference_evidence_2026-10-25_001/actual_native_rate_audit_032/audit.py --replay verification/literature_reference_evidence_2026-10-25_001/actual_native_rate_audit_032/snapshot_001
```

`snapshot.json` records source/pin hashes and read scope; `receipt.json` records exact projection, contract, operand, rejection, accounting and imported-code evidence. The original first replay attempt failed on the audit’s MappingProxy normalization and was corrected only in this owned script; that stderr is retained as an audit-development artifact. Later explicit replay succeeded. No old run failures were enriched. No whole A105 sheet/axis, W05 aggregation, or full-goal completion claim is made.
