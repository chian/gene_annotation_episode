# Pairwise Homology verification

This work verifies the separately selected
`bvbrc.homology.pairwise_correspondence` mode. All native responses are explicitly
synthetic; no BV-BRC service, BLAST executable, configured model, or HPC resource
ran. The only controlled execution behavior is scripted decisions, a fixture
continuation estimator for the root/scientific input-preparation work, and the
NativeClient transport. Production parsing, custody, source resolution,
publication, numerical calculation, return admission, and practical completion
are exercised unchanged.

The supplied DNA is `ATGAAAACTGGGTAA` (15 nt), and the single supplied protein
reference is `MKTGG` (5 aa). The synthetic blastx HSP reports `MKT` against `MKT`,
query coordinates 1–9 with frame +1, reference coordinates 1–3, and one HSP.
The submitted database FASTA contains exactly that reference. Full original
FASTA strings, actual sequence hashes, member identities, membership evidence,
the exact original request, native artifact bytes, and source associations are
retained. The reference remains evidence outside the one-target scope.

| Requested measurement | Value | Meaning |
| --- | ---: | --- |
| Query paired coverage | 0.6 | 9 unique paired original nt / 15 supplied nt |
| Reference paired coverage | 0.6 | 3 unique paired original aa / 5 supplied aa |
| Distinct aligned pairs | 3 | Distinct aa correspondences with original coordinate intervals |
| Paired identity | 1 | 3 identical pairs / 3 distinct paired positions |

The retained query intervals are `[0,3)`, `[3,6)`, `[6,9)`; reference intervals
are `[0,1)`, `[1,2)`, `[2,3)`. Native E-value remains a native measurement and
does not determine paired relevance. No database function weights or annotation
credit formula is used.

`tests/test_bvbrc_homology_pairwise_workflow.py` constructs the scientific child
through the actual library and three-slot constructor. The child selects three
`material.parse` actions before commissioning launch/API and results work.
The input sources are not preseeded through `initial_known_record_refs`.
The result path selects task information, Workspace metadata, download
capabilities, the task manifest, and complete native bytes. It retains separate
numerical sheet/components and returns only the four requested measurements
through results → scientific parent → root. Practical roles use their existing
validated exact-zero completion; fixture-only root/scientific continuation is
recorded explicitly. Replay must add no native call, action, observation,
report, or model request.

`tests/test_bvbrc_homology_subject_binding.py` separately tests the pure reference
association boundary. It covers inline/retained FASTA, source/member identity,
sequence/hash/length/molecule conflicts, membership, native identifiers and
explicit mappings, zero hits, multiple submitted references despite one hit,
escaped/ancestor pointers, absent evidence, and prohibited I/O.

Historical receipts are retained:

- `pure-proof-gap-before-repair.json` demonstrates that the prior adapter accepted
  a contradictory reference digest while returning all four pairwise values.
  It is a pure adapter counterexample, not an episode-custody claim.
- `pytest-first.*` records the first full-run fixture error: the unsupported
  `inline_parameter` plus `link_evidence` combination. Both fixture bindings
  were corrected to the supported `supplied_link` form, and actual request and
  selector validation passed before the next run.
- `subject-binding-first.*` records 59 passes and one discovered inventory
  sequence-conflict defect. The production owner repaired the validator.
- `subject-binding-expanded.*` records 71 passes after the additional exact
  relationship cases.
- `workflow-input-proof-preflight.json` checks the exact intended Workflow
  operands against the repaired pure validator and actual decoded query shape.
- `pure-proof-gap-after-repair.json` verifies the connected adapter's truthful
  `.6/.6/3/1` result and null measurements for a contradictory reference digest.
- `inflight-return-snapshot-2026-10-24-001.json` preserves the two publications
  and intermediate return state from the corrected full Workflow fixture.
- `admitted-stale-return-snapshot-2026-10-24-001.json` preserves the subsequently
  admitted results return: the four null values came from partial decision 3,
  although decision 6 had recorded the correct final values. The production
  owner was notified that latest-publication lookup reversed hash-directory
  order rather than recorded operation order.
- `pytest-integrated-order-defect.*` and `integrated-order-defect-summary.json`
  retain that full run: 75 passed, 2 failed in 1737.71 seconds, with 16 actual
  actions/observations/model calls and 4 admissions. Numeric delivery and the
  exclusion of the earlier partial source failed. Replay assertions were not
  reached. The run's additive `PROVENANCE_CORRECTION.json` distinguishes the
  actual null returns from the expected values mislabeled by its old exporter.
- `pre-order-repair-native-publication/` copies the actual decision-6 sheet and
  components with checked hashes/sizes; it does not replace the failed return.
- `repaired-production-source-preflight.json` records 355 source fingerprints
  after the owner connected the chronological-action repair and support-return
  role restriction. The next full run records matching source snapshots before
  and after closure, with actual versus expected measurements separated.

The integrated run uses the production owner's stable adapter pin
`6431e9b48d6015056915c610f125653a9bbb886e0195bd1a24a1fc531896a809`.
The repaired full run completed with **76 passed and one verification assertion
failure in 1331.85 seconds**. Both actual parent admissions received the correct
four values, and all 355 before/after source fingerprints matched. The remaining
assertion compared the host API outcome to Workflow's additional pending-work
snapshot; it did not indicate a native or scientific replay failure.

The corrected focused replay against that same retained run passed separately:
**1 passed in 7.20 seconds**. It compares the actual retained host outcome,
separately validates Workflow's pending-work snapshot and unchanged action, and
checks unchanged source/action/model/observation/report counts with native and
model calls forbidden. No all-green 77-test invocation is claimed. See
`FINAL_VERIFICATION.json`, `pytest-integrated-repaired.*`, `pytest-retained-replay.*`,
and `runs/pairwise-ih4zrdlw/saved-replay-verification.json`.

The corrected provenance helper rechecks its original explicit file set and
records loaded modules separately. All earlier runs, failures and corrections
remain retained under `runs/`; no prior evidence was deleted.
