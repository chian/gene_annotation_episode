# Source-version publication correction scope023

Root's joined API timing test retained a real importer failure after valid
submission/status/result acquisition: ToolRegistry._source unconditionally
called .get('version') on job_details.database, while the accepted original
status response carried the database selector as a string. Publication raised
AttributeError. The exact failed command/output is retained at
/tmp/api-timing-root-connected-20261022-001/after-fixture-owner-correction.log.
This is separate from the earlier root fixture resource-ID error.

Root read the complete _source and publish_hmmer_snapshot/import branch plus
result snapshot construction. Root owns only the narrow tools.py extraction
correction and tests/test_api_timing_connected.py. If the actual database value
is a dictionary, preserve its existing version lookup. A string or null selector
supplies no release/version; leave it unknown and preserve the existing explicit
response-header fallback. Do not guess a release from a selector, change raw
snapshots, normalize provider identity, or change record/publication semantics.
The joined test must reach actual result publication and inspect unknown source
version for this accepted response. Existing importer/API regressions supply
additional coverage; no new task/episode or runtime policy is added.

All work is isolated generation003. The original source, scientific process and
previous evidence remain unchanged. This report is authorization and defect
custody, not a claim of completed correction or scientific evidence.
