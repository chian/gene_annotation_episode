# External-status completed-action consumer correction

Root owns one additional implementation consumer in the isolated API checkout:
`gene_annotation_episode/completion_evidence.py`. Existing ownership in scopes001–010 remains unchanged.

The joined monitoring check reached the actual controller capture path and failed
before observation: `_SNAPSHOT` accepts `external_job_execution_status_v1`, but
`_progress` decodes every non-native status as an episode return. It accesses
`return_available`, `return_id` and `acknowledgment_id`, which external jobs do not have.

Use the existing external-status version constant and validator from
`progress_records` for that alternative. Preserve the original native and episode
branches, current completed_action_evidence_v1 packet, received C8 references,
original times, UnitRef and frozen original action. This correction adds no HTTP,
new observation, credit, estimator meaning, wait choice or status translation.
The waiting/controller consumers continue through their existing validator.

Root also corrects its detached-worker test setup to pass the two actual enabled
scientific planning roles (annotation and scientific_process) explicitly. That
fixture currently leaves the old default improvement role enabled after removing
that role from its composition. This is a test-only setup correction, not a
production change or additional episode.

The entire failed joined input set and log were preserved before either change
at /tmp/hmmer-root-joined-first-inputs-20261022-001, manifest SHA256
`a3a1387e703375631f37528ac9984d4f400565ce9bee42376ff91142264a818f`.
Its source pin and first ROOT_JOINED_SOURCE_INPUTS_001.json stay immutable.
Create a new input manifest before rerunning actual connected, detached-worker
and affected completion-evidence checks. All application sources must be stable
through worker lifetime. No application source in the live scientific checkout
is changed by this isolated workload.
