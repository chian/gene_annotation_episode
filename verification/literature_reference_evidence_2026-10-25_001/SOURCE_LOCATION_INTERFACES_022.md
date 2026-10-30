# Literal source quote positions for native literature readers

The full active attachment is
/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt.
Read it completely. This is a primitive source-access addition supporting the
existing source-bound numerical readers, not a new scientific axis, scoring
formula, episode, private extraction workflow or automatic interpretation.
Exactly ten axes remain; A101/computational grading and W05 stay separate.

Observed implementation gap: actual019/020 configured children have repeatedly
read source windows without a numerical operation yet. That alone does not prove
a scientific failure. Independently, materials.source_window returns exact read
windows but no literal quote locator, while native witness schemas require exact
UTF8 byte offsets. Existing controlled native fixtures compute raw.index in
Python. The deterministic position calculation should be available as a selected
primitive to the actual episode. No new paper or paper-specific packet is needed
for this workload; synthetic sources only. This is not an assertion that a locator
alone solves the actual model extraction/delivery gaps.

The proposed behavior was printed in chat before coding: locate an exact supplied
quote in a received source representation, return its source/artifact identity,
UTF8 half-open byte span and nearby unchanged context. The model still selects
the experimental meanings, source text and occurrence; the locator parses no
measurement, chooses no scientific relation, changes no scores or supplies an
overall judgment. Multiple matches stay multiple, absent text stays absent.

## Fixed ownership

Fresh022 owner exclusively owns:
- NEW gene_annotation_episode/source_locations.py
- gene_annotation_episode/tools.py ONLY literal source.locate import/catalog/
  dispatch/custody integration; do not change other-session grader paths
- gene_annotation_episode/literature_episodes.py ONLY source.locate availability,
  source receipt/page-lineage enforcement and implementation fingerprint inclusion
- NEW tests/test_source_locations.py
- NEW tests/test_literature_source_locations.py
- NEW source_locations_022/ verification artifacts below this directory

Wait-target021 owner exclusively owns runtime.py, method_loop/durable.py,
possibly native_event_information.py, and its own tests. Do not edit those files.
Coordinator owns interfaces, integration review, joined checks, later pins and
model launch. No other files/old tests/runs/pins/history, no models/new papers.
Read complete affected implementation functions and every consumer. Preserve
concurrent unowned edits; record initial hashes and report unexpected drift.
No broad rewriting/formatting of shared tools.py.

## Operation

Expose ordinary selected source.locate through the real ToolRegistry and C7
LiteratureEpisodes. Use its existing operation identity/journal/replay and failure
paths, not a private repository loop or additional observations. Accept exactly:

{source_ref, representation:original|text, needle:<nonempty exact literal text>,
 offset:<nonnegative UTF8 byte offset, default0>, limit:<positive match count,
 default8>, context_bytes:<nonnegative context width, default120>}

source_ref/representation/needle required. Original/text are explicit: unlike the
older read-window fallback, absent text is a clear representation failure, not
silently original labeled text. No fuzzy matching, regex, normalization, case
folding, OCR or semantic search. Retain all source bytes/quotes unchanged.
Require original source scope/receipt custody through the existing permitted
record port; C7 must pass its actual received refs for this operation. Reading
stored bytes does not grant a guessed/unreceived source or page access. Preserve
page-root/ancestor checks. Old source.read and other operations stay unchanged.

Return matches in source byte order. Each has witness EXACTLY the existing input
shape {source_ref,representation,start,end,quote}, with artifact_ref alongside
(not inside the witness). Context has its own start/end/text and same artifact.
These witnesses must feed existing native _Sources/NumberSelector unchanged;
source unit parsing/experimental interpretation stays in the existing readers.

Report selected representation/artifact, starting offset, actually scanned range,
total source bytes, returned matches, whether another match was actually found,
and an exact next_query for bounded match pagination when needed. Treat required/
enum/type schema ordering as presentation, but do not weaken semantic constraints.
Empty result means no literal match in the actually examined range, not no
biological evidence. Pagination must not lose repeated/overlapping matches or
split UTF8 characters. Returned contexts must be valid exact UTF8 windows with
bounds and never be relabeled as a match. Different representations remain distinct.

Use streaming bounded-memory search rather than loading an arbitrary huge source
just to locate one quote. Internal byte chunks are an implementation detail, not
an episode itinerary or stopping rule. Validate requested boundaries and scanned
UTF8; binary/malformed text, unavailable representation, bad scope/receipt,
invalid parameters and identity collisions give specific ordinary structured
failures. Do not catch unrelated storage failures as no-match. Stop after the
requested bounded match result plus enough lookahead to establish continuation,
or EOF; do not claim unexamined suffix validity or total match count. Preserve
actual lookup/operation selection; no timer, retry, resource choice or cancellation.

## Required meaningful checks

1. UTF8 offsets versus character offsets, CRLF/markup/text representations,
   repeated/overlapping needles, chunk-spanning quotes, no match, exact EOF,
   multibyte offset/context boundaries, nonUTF8 source, explicit unavailable text,
   empty/boolean/nonfinite/bad indices and bounded pagination without omissions.
2. Returned witness consumed unchanged by existing native number/unit readers;
   comparator just outside a selected numeric quote remains censoring, not zero;
   a shortened unit cannot bypass existing token/context checks. The locator
   must not validate a scientific meaning or infer physical measurement identity.
3. Actual registry operation persistence/replay uses original selected arguments,
   rejects key reuse/custody violations and reuses saved results without opening
   source bytes again. No scientific observation/assessment/source record or
   source count credit is created by literal lookup.
4. Selected literal lookup then selected native population and ordinary typed
   child-to-parent delivery with exact cells in an explicitly controlled synthetic
   episode; source positions come from lookup output. Verify requested subset,
   original source/endpoint bindings, unavailable reasons and one observation per
   actual completed own action. Reading/lookup/calculation/reporting creates no
   extra synthetic observations. No actual model science claim.
5. Catalog/dispatch/initial TASK/restoration retain actual source.locate and full
   task/curt steering; assigned-page descendants work, wrong page/unreceived/
   cross-scope source fails. The descriptor must fingerprint the new helper so
   selected workers cannot silently load another implementation.

Run focused new tests and relevant existing source/registry/literature tests;
report exact commands, results, limits and changed hashes. Do not rerun giant
unrelated grader suites or fix their failures to green. Do not launch a model
or copy mutable unreviewed main into an old pin. Parent will review before any
new captured runtime/live use. All other full-goal gaps remain unfinished.
