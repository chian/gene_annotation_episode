# Accepted independent directional-report reader boundary

Root review, 2026-10-25. This additive record accepts the standalone coding
boundary in `../tool_graders_bvbrc_proteome_retention_contract_2026-10-25_170/LEGACY_REPORT_READER_CONTRACT_001.md`.
The authoritative attachment and all sixteen design principles were reread.
The goal, existing scientific scope, old schemas and retained runs are unchanged.

## Exact workload and handoff

The fresh reader worker owns only the new directional reader, its contracts,
its schema asset, its two test modules and a dedicated retained-fixture directory
named in that contract. It implements the three exact public signatures there.
Input is supplied legacy BLASTP text bytes with exact NativeSource and declared
format; output is the complete closed DirectionalReportResult, retaining every
native query, description, subject, HSP and traceback occurrence independently.
The existing BLAST grader is the model for separating native measurements from
later calculations. No live search, acquisition, resource decision or combined
scientific score belongs in this reader.

The next consumer will be the separately implemented directional attachment
with actual execution and occurrence evidence. Current B2/B3 accept no such
attachment. The reader must not weaken those schemas or claim an executed
proteome denominator. Root owns subsequent attachment integration and packaging.

## Review clarification

Shape and native consistency are different checks. Syntactically valid observed
numbers may contradict another observed count or coordinate. Preserve their
values and require the corresponding consistency issue; do not reject the entire
retained report or erase its valid neighboring HSPs. An invalid numeric spelling
uses an invalid cell with exact native text and source locations. An actual
missing field stays missing. No inference supplies an unreported zero gap count.

Repeated identifiers remain separate occurrences. A description table is not
zipped to alignment blocks. Statistical footer scope stays attached to the query
where it was observed. Exact byte spans must continue to address original LF or
CRLF bytes. Decimal scores retain nonzero values that binary floats underflow.

## Required verification and remaining dependencies

Use the three acquired primary fixtures and check their original hashes before
copying. Verify the specified query/subject/HSP counts, all thirty description
rows in the 2.2.21 example, optional missing fields, native no-hit observations,
exact traceback strings and source spans. Constructed malformed/truncated cases
must be labeled as such and preserve valid preceding observations. Validate
saved projections without acquisition or scientific execution.

This work establishes format decoding only. Producer stdout/stderr retention,
successful process evidence, original input occurrence mapping, full-report
attachment, calculations using all reported alignments, actual API dispatch,
typed episode delivery and live-resource verification remain required work.
