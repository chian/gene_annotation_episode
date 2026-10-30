# Controlled Workflow attempts

All protocol replies and decisions are explicitly controlled local fixtures.
Scientific output bytes are retained native examples. Production transport,
custody, parsers, providers, calculators, forms and controllers are exercised.
No configured model, live BV-BRC service, new native algorithm or HPC job runs.

## Attempt001

Command:

```text
.venv/bin/python -m pytest -q tests/test_bvbrc_alignment_episode_flow.py -x --junitxml=verification/tool_graders_bvbrc_alignment_episode_flow_2026-10-25/initial-001.xml
```

This attempt was interrupted by the test operator after roughly7minutes to
diagnose substantial CPU time before acquisition. It had reached the first
scientific material action (2episodes,2selected action rows,2model calls).
No completed Workflow or passing integration claim is made for this attempt.
Its retained start provenance and state are under runs/msa_dna-r64ijb44/.
SIGINT did not end the process; SIGTERM ended pytest with exit143. No runtime
controller or episode cancellation behavior was modified.

The following test-harness corrections were made after source inspection:
parser sentinels now target the actual _parse function and the separate
MetaCATS input-reader module; a real selected report redelivery is requested
after results closure and is counted as an internal model decision without
an additional completed action or observation.

## Attempt002

```text
.venv/bin/python -m pytest -q tests/test_bvbrc_alignment_episode_flow.py -k msa_dna -x -o faulthandler_timeout=30 --junitxml=verification/tool_graders_bvbrc_alignment_episode_flow_2026-10-25/diagnostic-002.xml > verification/tool_graders_bvbrc_alignment_episode_flow_2026-10-25/diagnostic-002.log 2>&1
```

The30second pytest faulthandler setting only prints a diagnostic stack; it does
not stop a test, episode or controller. The original YieldController and
estimate_score_yield remain unchanged.
