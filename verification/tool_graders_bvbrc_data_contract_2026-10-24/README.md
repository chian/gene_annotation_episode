# BV-BRC Data API planning evidence

This directory contains read-only native evidence and proposed implementation
contracts. It does not contain an installed v2 service or completed episode run.

- `D1_QUERY_CONTRACT_FROZEN.json`: immutable query/registry handoff.
- `CONTRACT_SHAPES.json`: exact D2–D5 shared records, report schemas and functions.
- `FILLED_EXAMPLES.json`: expected typed outputs from retained native values;
  hypothetical host/source/admission envelopes are labeled synthetic.
- `RECEIVER_TEXT_EXAMPLE.txt`: selected exact values for receiver presentation.
- `ALIAS_AND_COVERAGE_MAP.json`: both original accounting aliases, 66 required
  collection/mode combinations and two join projections; no accounting edits.
- `REPORT.json`: offline planning/schema/native-evidence checks and their limits.
- `*.body` and matching `*.meta.json`: complete native response bytes, provenance,
  headers and digests. Credential/cookie header values are redacted.
- `official/`: pinned official source and per-file provenance.

To check these planning artifacts from repository root:

```
python3 verification/tool_graders_bvbrc_data_contract_2026-10-24/build_contract_artifact.py
.venv/bin/python verification/tool_graders_bvbrc_data_contract_2026-10-24/verify_planning_contract.py
```

The generator/checker only writes this directory. The existing closed report
schema validator accepts all six proposed forms without schema relaxation.
These checks do not exercise a production compiler/parser/calculator, host
admission, prompt delivery or model episode.
