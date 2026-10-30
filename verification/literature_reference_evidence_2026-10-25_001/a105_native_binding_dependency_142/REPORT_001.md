# Native binding dependency compatibility verification

This is implementation evidence for a bounded W04 compatibility repair. It is
not a new instruction, scoring policy, A105 adequacy claim or goal-completion
record. The original supplied user goal remains authoritative and incomplete.
No paper was opened or interpreted during this engineering task.

## Defect and bounded production change

The native binding writer failed before publication because its exact rate
dependency pin was `171eb81f23bcf5b8c048807a093a066f42674f960ac59826cbcb4ae3d94490b4`,
while the current rate storage is
`66f7b53adfb4fd873386fd04a3bff681c871f29a69848e94567c1792420be541`.
`baseline_001.log` and XML preserve that observed failure.

Only `gene_annotation_episode/literature_binding_interaction_storage.py` was
changed in production. The original byte-identity exception is explicit:

| File | Before SHA256 | After SHA256 |
| --- | --- | --- |
| native binding storage | `0dd5b0bbee30809560a1b39715c05c493c38d94581bbd255ebcbcdee2f6b749e` | `3fe2db26d4217aa99d081fb3aaa0634c778de054adfdeed523a25afc3d7f6582` |
| rate storage | `66f7b53adfb4fd873386fd04a3bff681c871f29a69848e94567c1792420be541` | unchanged |

Storage lines 47–64 declare the two exact supported rate implementations and
the exact original whole nine-file dependency snapshot, including validation
version. `_dependencies` at line 86 continues authenticating all frozen live
dependencies. New writes retain the actual current file hashes. Saved reads at
line 360 admit only the exact current snapshot or the exact original snapshot.
There is no independent per-file cross-product for saved metadata. In particular,
original storage plus the newer rate hash is rejected because the original
writer could never have produced that combination. Null/missing/extra/unknown
metadata and unknown actual rate or calculator bytes remain rejected.

The native version, request, outcome, source identity, source ancestry, eight
cells, bindings, receipt methods, scoring meaning and component projection were
not changed. Saved original dependency metadata is returned intact; no backfill
or migration occurs. The new test file is
`tests/test_a105_native_binding_dependency_142.py`, SHA256
`396dad1ec8488c3c7c43f173c091886f68086217b310e0514da62b0e2cd413e8`.

## Complete path review

Read the full original native binding storage and saved validator, and both
full historical/current rate implementations. The historical rate and original
binding files are retained in
`a105_visual_signal_repository_071/pin_004/gene_annotation_episode/`; their nine
hashes match the admitted original snapshot. Full native render and current
supplemental binding model storage were also inspected. The selected dispatch,
fact routing, report validation, typed receipt admission and received-fact
consumers were read in `literature_episodes.py`, `episode_services.py` and
`episode_admission.py`, along with the complete existing native storage and
integration tests.

`RATE_METHOD_COMPARISON_001.json` records every base method's source and AST
comparison. The two changed existing inherited methods are rate-specific
`populate_native` (line 291) and `_validate_native_saved` (line 435). The new
`source_domain_projection` (line 618) and new domain projection class implement
the rate-only return path. These methods are inherited by the binding class,
but are not called by its selected binding operation or return path.

The native binding overrides `populate`, `read` and `project_cells`. Ordinary
`literature.binding.interaction.populate` dispatch selects that `populate`;
only `literature.rate.source.populate` dispatch selects `populate_native`.
Generic custody and receipt functions dispatch back to the native `read` and
`project_cells` overrides. `SELECTED_BINDING_SELF_CALLS_001.json` follows all
reachable `self` calls from population, reads, projection, ownership checks,
validation, admission and receipt reconstruction. Neither changed rate-specific
method nor the new domain view occurs in that reachable set.

The inherited functions used by this path are identical in both rate versions:
constructor/table setup; native source/provenance authorization; delivery
table/digest/install helpers; original typed-runtime form authentication;
sheet-owner validation; fact selection and validation; received subset
admission, digest validation and reconstruction. Consequently the domain
extension does not alter the selected binding path's numerical or custody
behavior. The supplemental model repository calls the same native `read`; its
own broader validation remains agent140's separately owned verification.

## Actual verification

| Run | Result | Preserved evidence |
| --- | --- | --- |
| Baseline native population | 1 expected failure | `baseline_001.log`, `baseline_001.xml` |
| Existing native storage and integration tests | 50 passed, 181.90 s | `native_001.log`, `native_001.xml`; session 77092, exit 0 |
| New compatibility test attempt 1 | 14 passed, 1 failed, 14.63 s | `compatibility_001.log`, XML; session 18979, exit 1 |
| New compatibility tests after harness-path correction | 15 passed, 23.39 s | `compatibility_002.log`, XML; session 54227, exit 0 |

The first compatibility attempt failed because pin004 contains the original
production implementations but only the ratio test harnesses. The corrected
test explicitly imports the unchanged current native C4 engineering harness
while loading all production application modules from the historical pin.
Both actual imported module paths and the complete historical dependency map
are preserved in
`pytest_002/test_untouched_historical_runt0/historical_stdout.log`.

That isolated subprocess executes native population and actual C4 admission,
including admission rollback and original typed subset authentication. It
creates an actual historical native operation, source bindings, outcome and
typed parent receipt using the original storage/rate implementations. It does
not manufacture a historical record by editing newer metadata or science.
The sources are explicitly synthetic engineering fixtures, not experimental
findings or an actual model-backed literature investigation.

The current reader then reopens that state with SQLite `mode=ro`. The test
forbids reading the experimental source artifacts, decoding images, parsing,
calculating and receiving again. It verifies the exact original saved payload,
dependency metadata, outcome and selected-operation replay, and copies only
the parent's originally admitted `interaction_ratio` cell (value 4). Ordinary
LiteratureEpisodes received-fact routing reproduces that same subset. The full
database dump remains unchanged and no controller observation is created.

Current native tests independently verify actual selected nested episode
execution, exact completed-own-action observations, typed C4 admission and
rollback, cold receipt reconstruction, unrequested operand masking, source
custody, limits, partial uncertainty, aliases and tamper rejection. The new
unknown-version tests mutate only isolated dependency copies; no hash function,
guard, production file, fixture or historical pin is bypassed or modified.

## Limits and ownership

This establishes compatibility for the two named rate dependencies on the
selected native binding path and preservation of the exact original saved
snapshot. It does not certify arbitrary future dependencies, all historical
binding versions, cross-version newly written maps, direct misuse of inherited
rate-specific entry points, numerical correctness of rate domain arithmetic,
or scientific adequacy of A105. Agent140 owns the supplemental model path and
the root owns joined packaging/current-primary verification.

No W05, annotation-credit aggregation, controller, tool grader, original native
calculator/input/validator/render, existing test, source fixture, historical pin
or source case was edited. No repository goal file was read, created or edited.
`BEFORE_001.json`, `AFTER_001.json`, `NATIVE_STORAGE_DIFF_001.patch` and
`TERMINAL_RESULTS_001.json` record the bounded source change and terminal results.
