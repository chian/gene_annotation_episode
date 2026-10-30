# BV-BRC compact return consumers

This packet records implementation and verification evidence. The original user
attachment remains authoritative: `/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt`,
SHA-256 `11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
No repository goal file was read or used as authority.

## Changed boundary

The seven original return consumers called `AppServiceCustody._attempt`, then
compared the originally selected `schema_json` literally with the child's
expanded measurement schema. An original `episode-fact:` reference therefore
failed after a valid expansion.

The consumers now use custody's authenticated expanded schema. They retain
their existing typed-form validation, original commission lookup, child scope
validation, selected purpose check and frozen original form equality. Custody's
independently owned repair authenticates the original selected form against
the original decision's saved role/fact catalog. This packet makes no change to
custody, runtime, communication, calculators, numerical sheets or credit.

The changed files are:

- `gene_annotation_episode/bvbrc_alignment_returns.py`
- `gene_annotation_episode/bvbrc_genome_alignment_returns.py`
- `gene_annotation_episode/bvbrc_homology_returns.py`
- `gene_annotation_episode/bvbrc_phylogeny_returns.py`
- `gene_annotation_episode/bvbrc_proteome_returns.py`
- `gene_annotation_episode/bvbrc_comparative_systems_returns.py`
- `gene_annotation_episode/bvbrc_fastqutils_returns.py`

`consumer_changes.json` records original and repaired file digests. The
`original_consumers` directory supplies the exact pre-repair comparison inputs.
The final narrow corrections to two existing Homology/Phylogeny redelivery
fixtures are recorded separately in `fixture_changes.json` and `original_tests`.
They restore the original decision-frame shape traced in the actual runtime
writer and add a conflicting-schema rejection; they do not change custody.

## Verification meanings

`tests/test_bvbrc_compact_family_returns.py` distinguishes:

1. Constructed historical records with real Store, Journal, AppServiceCustody,
   TypedReportContract and all seven actual family-return classes. Full
   admission, scientific-process forwarding and redelivery use valid empty
   scientific facts. Compact/full forms, original selection identity, changed
   scope/purpose, substituted children, forged expansion, added facts, frozen
   form mismatch and damaged original frames are checked.
2. Nonempty numerical rows from existing family fixtures and real saved-value
   projections. The exact original rows traverse each actual consumer's
   `_attempt` contract path and explicit redelivery. This specifically tests
   compact contract preservation; it does not prove fresh native acquisition
   or the complete publication-to-parent scientific path.
3. Actual Workflow-created preparation commissions and explicit redelivery,
   using workload 479's scripted preparation fixture. All seven consumers
   authenticate these real runtime records. The returned facts here are
   preparation receipt references, not scientific measurements.

Saved reads run with SQLite `query_only=ON`, compare the complete database dump,
and forbid current Workflow catalog/fact discovery. Network and subprocess
creation are forbidden by the constructed family fixture. Numerical projection
setup is separate from saved-return reads. No credential, live API, native
BV-BRC scientific execution, configured model or HPC execution is claimed.

## Execution custody

Every application import and test executes through `run_checks.py` using the
existing `local_jobs`/`native_lifecycle` handle. The only host imports bootstrap
that lifecycle. Each attempt retains an immutable source snapshot, complete
installed dependency closure, copied interpreter and copied standard library,
with before/after digests. The selected policy is 20 GiB RAM, 4 GiB scratch,
zero swap and no wall-time budget.

Baseline comparisons copy the same source snapshot and substitute only the
seven original consumer files. `selected_request.json` identifies the source
attempt and whether the original consumers were selected. Status and collection
continue on each original handle. Run receipts and exact test outcomes are
reported in `RESULTS.md` and `COLLECTED_HANDLES.json`. All nine native handles
are collected; the prelaunch preparation failure did not create a native job.
