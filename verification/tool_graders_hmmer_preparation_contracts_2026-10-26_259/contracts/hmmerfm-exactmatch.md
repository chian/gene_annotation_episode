# hmmerfm-exactmatch — proposed index diagnostic contract

Exact executable/source present; complete hmmerfm-exactmatch.c and relevant
fm_general interval/coordinate functions inspected. Invocation
`hmmerfm-exactmatch [--out hits] [--count_only] [--fwd_only] qfile fmfile`.
Modes are location enumeration versus count-only, with forward-only versus
forward-and-reversed-string traversal. These are index diagnostics in this
preparation assignment, not annotation evidence or profile/BLAST search scores.
`r` means reversed string, NOT reverse complement or a biological minus strand.

Input `queries` is plain text one literal sequence per line, NOT FASTA. Retain
every line occurrence and exact bytes, including duplicate query sequences.
Source uses fgets256, strips LF only, does no safe alphabet validation and no
empty-line handling. Proposed binding requires nonempty canonical DNA (U accepted
as T if explicitly normalized), no CR/whitespace/FASTA header, at most254symbols
per LF-terminated line; unsupported characters must fail before native execution.
Do not silently split long queries or drop lines. Inputs `fm_database` and
`source_sequences` retain complete exact index and original source occurrences;
the original source is parser/validator metadata, not an additional native arg.
Only verified DNA FM producer contract is valid; protein FM writer output is
unsupported by fm_readFMmeta, whose error status exactmatch ignores. Require
well-framed compatible metadata before native invocation; unknown format !=zero.
Input '-' is opened as a literal filename; use ordinary staged paths.

Output `hits` comprises query-line groups followed by indented rows
`coordinate f|r target_name`, blank line separator, for queries with retained
hits only. Native default --out value is 'none' and it really writes a file named
none; production should always select explicit attempt-local --out. `--out -`
mixes hits and parameter banner on stdout. Count-only produces no location rows
and an empty requested hit file is expected, not missing data. stdout contains
native parameter/alphabet/index-setting header; stderr contains `hit: Q (H)`,
`miss: R`, elapsed seconds, occurrence-call diagnostics. Preserve all artifacts.

Native coordinates after segment mapping are one-based source coordinates,
despite the stale main-function comment saying zero-based. Forward anchor is
leftmost start; reversed anchor is rightmost end. For query length L, proposed
normalized inclusive source interval is f:[c,c+L-1], r:[c-L+1,c], followed by
explicit bound/symbol/ambiguity checks. Do not repair native anchors silently.
Join target_name to the bound FM segment/target population; duplicate names may
make the emitted label insufficient for unique occurrence identity. Keep all
candidate associations/unresolved status rather than picking a first sequence.
Query groups follow input processing order, omitting unreported queries; use
exact supplied query occurrences and deterministic group/order constraints.

Native meanings differ by mode. Count-only H sums raw FM interval sizes over
blocks and enabled directions: it includes ambiguity replacement matches,
cross-sequence matches and block-overlap duplicates. Q counts query occurrences
with any raw interval. Location H counts native deduplicated emitted tuples;
dedup uses target_id/direction/anchor, not names alone. Location Q counts queries
with at least one retained hit after native validation. In BOTH modes miss R
increments only when raw interval count=0; queries whose matches all get filtered
are counted in neither location Q nor R. Thus Q+R need not equal input query N.
Count-only output has no per-query counts; do not invent them from the aggregate.

Proposed pure ports:
`extract_hmmerfm_exactmatch(*, query_lines, database_metadata, source_sequences,
hits, stdout, stderr, operation, receipt) -> sheet` and
`calculate_hmmerfm_exactmatch(sheet, *, coordinate_policy,
alphabet_normalization, expected_source_bindings) -> calculations`.
Sheet retains per-query/per-output row occurrences, native Q/H/R, counts' exact
population meanings, native anchors/direction and associated source/index.
Calculator separately reports emitted count, valid/invalid/unresolved tuple
counts, normalized intervals and symbol equality, overlap/duplicate groups,
query population denominator, source-symbol denominator and consistency checks.
An optional explicitly requested exhaustive literal comparison against complete
supplied source can calculate missing/extra tuples for tiny verification; it is
not permission to rerun native search or silently replace its output. Missing
source prevents sequence validation; count-only mode leaves locations unmeasured.
No E-value, function transfer score or annotation confidence is manufactured.

Confirmed native limitations: boundary filter tests `(anchor-fm_start)+L-1 >
segment.length`, which has an off-by-one at the right boundary and treats reverse
end anchors as forward starts. It can admit invalid reverse intervals and discard
valid reverse boundary hits. Preserve native rows, then flag actual failures;
do not claim native exact-match completeness from exit0. It also restores
ambiguities only in location mode. Runtime occ/sec is computed using cfg after
fm_configDestroy and elapsed may be0; retain raw diagnostic tokens with invalid/
unverified numerical status, never as measured productive throughput. The tiny
examples establish formats and these limits, not correctness for larger blocks.

Failure shape follows COMMON.md with structured issue codes for query grammar,
unsupported/unknown FM contract, malformed/partial metadata or hits, count
inconsistency, ambiguous source/query association, out-of-bounds interval,
symbol mismatch, ambiguity-overlap, invalid diagnostic, missing or partial
output and nonzero execution. Valid partial rows remain available. Local binary,
SSE-compatible exact FM input, explicit source map and caller20GiB/4GiB/no-wall
allocation are prerequisites. Preparation result worker receives the sealed
original attempt, returns requested typed native/validated facts separately,
and creates no biological observation. No remote/HPC/production binding claimed.

Native examples (all in native/hmmerfm_exactmatch_*): queries.txt has7occurrences
including ACGT twice against seq0=ACGTACGTACGTACGT and seq1=TTTTACGTGGGG.
`forward` locations yields Q5,H15,R2; all15forward matches independently verify.
`counts_forward` yields Q5,H16,R2 (one cross-sequence raw occurrence).
`locations` yields Q5,H17,R2; `counts` Q5,H19,R2. Native location row TTTT r3
on seq1 implies interval[0,3] and is invalid; r4 is valid. Expected GGGG r12 is
absent. Thus native17 rows contain16valid matches, while a direct complete-source
enumeration has17valid matches; matching aggregate totals cannot prove correctness.
`reverse` queries TGCA/GCAT/AAAA returns7reverse rows versus9expected: TGCA r4
on seq0 means reversing source[1,4]=ACGT gives TGCA; boundary r16 is omitted.
`forward_index` yields same15 as forward-only on paired index.

`ambiguous` queries ACGT/GG/ATGT/GGAC returns Q1,H3,R0 after filtering generated
index matches; `ambiguous_counts` reports Q4,H6,R0. These are different native
populations. `zero` queries AAAA/CCCC yields Q0,H0,R2, exit0 and empty hits file:
a measured empty location result, distinct from unsupported or missing files.
`default_output` confirms literal file none containing7rows. Complete receipts,
inputs, outputs and source-index files are retained, including duplicate query
occurrences. Native bugs are documented, not fixed or concealed by this report.
