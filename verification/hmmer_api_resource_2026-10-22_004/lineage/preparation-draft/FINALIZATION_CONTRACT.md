# API004 finalization contract for root review

Proposed permanent NEW paths, currently not created by preparation:

- `/home/chia/repos/gene_annotation_episode/docs/HMMER_API_RESOURCE_VERIFICATION_2026-10-22_004.md`
- `/home/chia/repos/gene_annotation_episode/verification/hmmer_api_resource_2026-10-22_004`

The concrete publication script is `/tmp/api-planning-publication-preparation-20261022-001/publish_reviewed_api004.py`. It has not been executed. It requires both `--publish` and an explicit reviewed-contract JSON. A missing flag/contract cannot publish. Before any write it validates exact approved candidate membership/hashes/sizes, the exact reviewed report hash, all344 root input source/test records,133 runtime/211test membership, runtimepin16435877..., root316-result record and all no-overwrite path conditions. It never imports application code, opens databases, executes tests or calls transport.

Root's approval must identify the final concrete `ROOT_REVIEWED_PUBLICATION_CONTRACT.json`, final full `APPROVED_MEMBER_INVENTORY.json` and final report candidate bytes. These files are prepared only after the supplemental unchanged-test result and all final evidence is materialized. Existing drafts, input snapshots, failure logs and parent files remain untouched. The independently checked316 total includes only135legacy+1detached+180consumers; producer groups and the supplemental1node stay separate.

On an authorized invocation the script creates only the two new permanent paths, copies the exact prepared candidate, writes a fresh outer manifest, verifies copies, applies declared file modes0444/0555, report0444 and capsule directories0555, and rechecks no extras and all hashes/modes. It never chmods the shared checkout, old publications, actual fixture source or other main directories. The parent verification directory is outside this mode contract; no broader replacement-proof filesystem claim is made. A failure retains any newly created partial artifact for inspection and does not rewrite source/reference/content identities or repair original application data.

Root remains responsible for independent review/authorization before permanent materialization and independent final publication verification afterward. New paths are additive. The script makes no whole-goal completion or scientific inference claim.
