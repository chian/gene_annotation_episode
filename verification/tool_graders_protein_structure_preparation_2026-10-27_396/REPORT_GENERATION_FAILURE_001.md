The first metadata-only `record_handoff.py` run exited 1 while enumerating
`prepared.json` paths. It attempted to decode the deliberately invalid symlink
preflight fixture and raised `json.decoder.JSONDecodeError: Expecting value:
line 1 column 1 (char 0)` at original line 78.

This was report generation after the completed 81-test run, not a scientific
worker, pytest or lifecycle failure. The helper now skips symlinks and explicitly
records the deliberate lost/changed retained-artifact fixtures. No production
module, test source, original native bytes, executed snapshot or receipt was
changed by this correction. The earlier generated files are exact copies or
summaries of their unchanged originals.
