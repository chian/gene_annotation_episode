# Standalone directional BLASTP text reader verification

This work implements only the accepted standalone reader boundary in
`../tool_graders_bvbrc_proteome_retention_contract_2026-10-25_170/LEGACY_REPORT_READER_CONTRACT_001.md`,
its correction002, root acceptance008, and coordinate clarification010. The
authoritative attachment and all sixteen design principles were read verbatim
before implementation and after the complete native-output inspection.

## Implemented boundary

- `parse_genome_comparison_directional_report(content: bytes, *, source: dict,
  declared_format: str, report_key: str) -> dict` checks the exact current
  NativeSource shape, byte count and SHA256, then decodes supplied bytes.
- `directional_schema(name: str) -> dict` returns a detached closed schema.
- `validate_directional_report(value: dict) -> dict` checks data shapes, source
  binding, nested byte spans, ordinal hierarchy, cell spellings/states and
  required consistency issues, returning a detached copy without IO.

The new parser, contracts and schema are independent files. Existing A/B1/B2/B3/B4
implementations and schemas, producer source, host/runtime/controller/method_loop,
pyproject, inventory/status, permanent direction records and active runs were not
edited by this workload. Root owns packaging and subsequent attachment.

Every native query, displayed description, aligned subject, HSP and traceback is
an ordered occurrence. Native IDs are not unique keys. Descriptions are not
attached to subjects. Scores and E-values use decimal strings; missing optional
positive/gap measurements remain missing. Contradictory lexically valid numbers,
including coordinate0, remain present with the required issues. Malformed numeric
spellings retain their exact text and byte locations in invalid cells.

## Actual native evidence

The three public Biopython reports and acquisition receipts were copied exactly
into `tests/fixtures/bvbrc_proteome_directional/` after checking their recorded
SHA256 values. `SOURCE_INPUTS_001.json` records the supplied source bindings.

| Retained report | Query lengths | Descriptions per query | Subjects per query | HSPs per query |
| --- | --- | --- | --- | --- |
| BLASTP2.0.11 | 102 | 0 | 0 | 0 |
| BLASTP2.2.2 | 1922,1374 | 15,8 | 15,8 | 16,9 |
| BLASTP2.2.21 | 472,600,473 | 10,10,10 | 1,1,1 | 1,2,1 |

The2.2.21 second query retains353/414 and115/115 identities. Inspection of its
saved coordinates gives529/600 union span coverage on each displayed sequence
and468/529 summed identities for these disjoint HSPs. First-HSP inclusive coverage
414/600 and legacy endpoint subtraction413/600 remain different quantities.

The2.2.2 first subject retains53/176 and20/47 identities,68.9/37.7 bit scores,
raw scores167/86, Expect3e-12/.007, and the first HSP's36/176 gaps. The second
HSP's native gap field remains missing. Coordinate unions are219/1922 query and
144/249 subject; overlapping subject intervals do not establish independent
aggregate correspondence. The native16/29 positives with printed54% remain
unchanged. The2.0.11 no-hit report retains6999 database sequences,1461753 letters,
and zero sequences better than native threshold10.0.

The full generated projections are `FILLED_NATIVE_2011_001.json`,
`FILLED_NATIVE_2202_001.json` and `FILLED_NATIVE_2221_001.json`.
`NUMERICAL_CHECKS_001.json` records numerical inspection; this is example
arithmetic, not a newly bound general scientific calculator.

## Tests and additive corrections

The final focused command was:

```text
.venv/bin/python -m pytest -q tests/test_bvbrc_proteome_directional.py tests/test_bvbrc_proteome_directional_contracts.py --junitxml=verification/tool_graders_bvbrc_proteome_directional_2026-10-25_172/TEST_RUN_004.xml
```

Result: **79 passed in8.64s**. The exact log and JUnit result are retained.

Earlier test receipts remain unchanged:

- Run001:69 passed,1 failed. A constructed geometry test changed a coordinate but
  did not actually change the traceback width it expected to flag.
- Run002:75 passed,1 failed. After the test also shortened a subject fragment, its
  shifted query column exposed a parser problem: an unreadable middle line split
  adjacent query/subject rows into separate traceback occurrences.
- The parser now preserves those adjacent sequence rows together and retains the
  damaged middle line as unparsed source material with an issue. Run003 passed76
  tests; additional explicit-zero, malformed-number and no-hit-text cases brought
  the final suite to79 passing tests.

The tests check real native numerical values and populations, every populated
cell's original byte slice, constructed CRLF/UTF-8 layouts, missing optional
fields, native zero versus underflowing nonzero E-values, duplicate native IDs,
missing/malformed later HSP fields, truncation preserving earlier results,
inconsistent counts/coordinates, unknown footer records, source completeness and
caller errors. Projection tests reject removed required consistency issues,
changed source/ordinal relationships, invalid values, extra keys, and unintended
statistic cells. All raw scientific mutations are explicitly constructed tests.

`TRUNCATION_PROBE_001.json` records275 constructed prefix cuts through native
headers, scores, counts and traceback rows: every case returned a structured
result, with no exception. This probe preceded the damaged-midline grouping fix;
the final suite separately verifies that corrected path.

`SAVED_REPLAY_001.json` records successful revalidation and numerical inspection of
all three saved projections with file access, socket creation and subprocess
creation disabled. Detached-copy behavior was also checked. No scientific
algorithm, acquisition, job submission or LLM was invoked.

## Precise remaining limits

These files verify decoding of the three reviewed legacy BLASTP releases only.
They are public native test outputs, not a BV-BRC deployment observation or task
custody witness. `ok` describes successful interpretation and supplied artifact
completeness; it does not establish successful execution, every expected input,
undisplayed hits, all database hits, or an executed proteome denominator.

The validator has no native bytes argument. It validates a saved projection's
internal consistency and declared byte binding; it cannot independently prove
that an arbitrary supplied projection equals a retained artifact. The parser
checks the actual supplied bytes and tests verify every extracted cell slice.

Producer stdout/stderr retention, process/input occurrence witnesses, B2/B3
attachment, complete-hit scientific calculators, packaging, selected API dispatch,
typed episode delivery and live-resource verification remain separate work. The
current B2/B3 schemas still admit no complete directional-report attachment.
No annotation confidence, function assignment, task direction, input occurrence,
whole-proteome denominator, credit or continuation decision is inferred here.
