# Saved calculation completion follows original acquisition

Additive 2026-10-27 correction to 016's completion dependency. An intervening
saved-results assignment can fail to deliver its requested projection while
still returning a valid saved sheet. Its `delivery_complete=False` must not
erase an earlier verified complete native acquisition of that exact sheet.

Validate every retained origin and its exact sheet/selected historical target
relationship. Then current saved completion requires both:

1. A verified complete original native-acquisition witness for that sheet and
   selected historical target, reached through the authenticated origins.
2. Qualification and delivery of the current assignment's requested results.

For multiple legitimate paths to the same sheet and target, one verified
complete original witness suffices. Do not select an arbitrary first origin,
discard other origins, or require every intervening saved assignment to have
completed its different return. If every original native-acquisition witness
is partial or missing, there is no complete acquisition witness.

Read only frozen controls and Store metadata during historical qualification.
Do not reopen scientific bytes, probe native execution or rewrite earlier
actions, failures, forms, completion flags or gains. The current selected use
still verifies its own saved input and requested outputs. No score formula,
annotation gate or new episode type is introduced.

Workload 436 owns the helper and focused verification: an actual failed saved
projection with a valid returned sheet followed by a successful saved
calculation, plus rejection of completion when all original acquisition paths
are partial. Earlier in-flight snapshots remain separate evidence.
