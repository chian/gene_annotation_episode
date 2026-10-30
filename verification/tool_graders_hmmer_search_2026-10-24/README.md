# HMMER protein/profile search numerical verification — 2026-10-24

This directory verifies pure native-output parsers, metadata extractors, numerical
sheets and deterministic calculators. It does **not** establish complete episode
integration, scientific parent/child communication, installed production bindings,
or an annotation-confidence formula.

Implemented programs/formats: native HMMER 3 protein tblout/domtblout/stdout for
phmmer, hmmsearch, hmmscan and jackhmmer; full provider API JSON for phmmer and
hmmscan. Native and API identities are retained independently. `record_key` is a
JSON-encoded string `[artifact_ref, record_role, absolute_native_line_or_pointer]`.
API locators preserve original hit/domain array indices and JSON pointers; native
reported-domain ordinals stay in `native.reported_domain_ordinal`, separately from
API indices. Native domain count fields describe reported domains, not all internal
domains. Exact bytes and complete native source texts remain attached to the sheets.

The actual source custody references and SHA-256 values are in SOURCE_MANIFEST.json.
Native receipt files preserve the actual run commands and resource observations.

## Executed and retained examples

- phmmer: existing actual run in cases/gene_001/jobs/homology_001, 17 targets and
  20 reported domains. This run was parsed; it was not rerun. The top domain has
  253 paired residues, full model/sequence coverage, actual operand identity
  253/253 = 1, score 591.5 bits, bias 1.8 bits, independent E-value 6.6e-177.
- hmmsearch: actual HMMER 3.4 bounded execution against the bundled 20aa-alitest
  four-sequence input. The test2 domain has model length 20, sequence length 25,
  18 paired columns, 3 insertions and 2 deletions; span coverage 20/20 and 21/25,
  paired coverage 18/20 and 18/25. Score 39.6 bits, bias 6.1 bits, i-Evalue 6.2e-14.
- hmmscan: actual HMMER 3.4 execution against a local pressed copy of bundled
  20aa.hmm. Four input queries are retained. The test2 domain has the same
  18/3/2 alignment counts as hmmsearch with the model/sequence axes inverted,
  and native i-Evalue 1.5e-14. The 20-position model is not a physical sequence.
- jackhmmer: actual HMMER 3.4 bounded execution with up to three requested native
  rounds. Native convergence occurred after two rounds, with 4 then 0 new targets.
  Eight hit/domain rows across the two dependent rounds remain available. Tables
  contain final-round rows only. Round-2 test2 has 20 paired columns plus 1 insert,
  paired sequence coverage 20/25 = .8, consensus identity 16/20 = .8 and score
  55.8 bits. Later-round consensus equality is not original-query identity.
  Both model-at-round-start and included-alignment-at-round-end checkpoints,
  and the final included alignment, are retained.
- API phmmer: two actual service pages acquired on 2026-10-22; no new service
  request was made. Page 1 contains two hits and four internal domains, page 2
  one hit and one domain. The retained gapped example has 25 identities,
  API identity 25/89 = .2808988764, paired consensus identity 25/88 = .2840909091,
  and all-column identity 25/91 = .2747252747. Bias .03572461009 nats / ln(2)
  = .05153971781 bits. A complete page is not the complete hit population.
- API hmmscan: numerical role-inversion tests use explicitly synthetic JSON.
  The zero-hit saved fixture is synthetic because the planned historical fixture
  path is absent. No actual positive/negative API hmmscan call was made here.

Native executions used `run_local_job` with **20 GiB RAM, 4 GiB scratch and no
wall-time budget**. Only bundled tiny inputs were used. hmmpress is a preparation
prerequisite, with native receipt/output retained; it has no confidence score.
No database BLAST, external API or HPC job was executed.

## Calculations and missing data

The sheet contains native measurements, explicit metadata joins, validated
zero-based half-open intervals and extracted alignment counts. The calculator
separately derives spans and coverage, identity fractions, PP bounds, matching
model cutoff margins and per-hit interval unions. Each scalar has its numerator,
denominator, units/source definition and scoped unavailable reason. Individual
components remain inspectable; no overall function-confidence score is produced.

PP characters are retained as ordinal observations. For sequence residues with
available characters, lower/upper mean bounds use 0:[0,.05), 1:[.05,.15), ...,
9:[.85,.95), *:[.95,1]. Gaps and missing characters have explicit counts. The
25-identity API example has posterior bounds .8277777778–.9094444444 over 90
sequence residues; these are bounds, not exact posterior probabilities.

Actual sequence identity requires explicit physical sequence operands whose
full lengths and interval contents agree with the native display. Profile
consensus identity remains a different field. Native printed accuracy and
provider oasc are retained with their own meanings; the provider does not
supply the native table's rounded accuracy column, so that scalar remains null.

Native flags are preserved and are not reconstructed from significance values.
Zero E-values remain zero, and negative scores remain negative. GA/TC/NC cutoff
margins require exact model identity and separately supplied sequence_bits and
domain_bits. Unknown population/reference metadata stay unknown. Ambiguous
joins remain separate representations with an issue; they are not independent
evidence. Queries inferred only as table names have unknown occurrence and do
not claim zero acquired hits. Unknown calculator parameters raise ValueError.

## Streaming and production handoff

- iter_hmmer_table_rows(stream, *, program, role, artifact_ref, engine_version=None)
  yields hit/domain/annotation/issue events, one native row at a time.
- iter_hmmer_stdout_events(stream, *, program, artifact_ref, engine_version=None)
  yields query/hit/domain/iteration/statistic/annotation/issue events, buffering
  at most one target block. Query headers are immediate; // and [ok] observations
  are annotations. Iteration events arrive at round closure. Domain-to-hit joins
  are left explicit for the consuming on-disk index. Query/round/target identities,
  exact line/UTF-8 byte positions and native numerical fields are preserved.
- iter_hmmer_stdout_queries(...) retains at most one query, for callers who
  explicitly want query bundles. It is not the bounded production extraction
  interface for a large single-query search.

The API parser reads the full original payload before lossy projection. Root
owns the production facade, source custody attachment, local immutable-domain
artifact retention, API original-index joins, child-owned execution bindings and
requested typed return verification. No shared production file was edited here.

## Verification

`.venv/bin/pytest -q tests/test_hmmer_search_inputs.py tests/test_hmmer_search_grader.py`
passes 39 tests. Cases cover actual native and API formats, model/sequence axis
inversion, gaps, negative/zero values, missing denominators, malformed numeric
components, truncated output, duplicate query names and ambiguous associations,
wrong labels/lengths, original API array indices after damaged rows, exact byte
locators, native statistical populations, posterior bounds, original sequence
versus consensus identity, native inclusion, cutoff scopes, overlapping unions,
jackhmmer rounds/checkpoint append occurrences, bounded event streaming, and
unknown parameters/nonfinite JSON.

`save_examples.py` produced complete filled sheets and results for each native
program and both retained API pages. Reloading each saved sheet reproduced its
scores with file opening, socket creation and subprocess creation prohibited.
Recalculation never invoked a native program or acquired data. These files are
verification artifacts, not production integration receipts.
