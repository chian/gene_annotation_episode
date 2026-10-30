# Existing local phmmer result binding verification

This verifies the existing child-selected local phmmer path under
`docs/TOOL_GRADER_BATCH_003_LOCAL_BINDING_2026-10-24.md`. The implementation
changes only `homology_results.py`, `phmmer_result_worker.py`, and the new
`phmmer_grading_worker.py`. The pure HMMER readers, sheet builder and calculator
remain the numerical authority.

`NativePhmmerInput.from_job` now supplies the already produced `domains.tbl`.
Its immutable bytes, the stdout/tblout/query artifacts, sequence/database and
executable identities, and parser/calculator fingerprint identify the parse.
Supplied command/settings remain capture metadata. They do not change the
numerical cache key because these calculators do not consume them. A new
publication overlays that capture's descriptive settings on its sheet; cached
grade files, old sources and old observations remain unchanged.

The bounded worker stores native events and join indices in SQLite. Unique
reciprocal identity/domain-coordinate matches associate stdout and table rows.
Ambiguous representations stay unjoined with issues. One alignment at a time
receives its actual query/reference sequences, populated sheet and calculations.
The original alignment source retains the grading artifact, and the original
alignment observation carries the additional typed numbers. No action,
observation, episode, scientific credit formula or continuation rule is added.

## Exact validation record

- `commands.json` and `pytest.log` retain the original broader run: **28 passed,
  1 failed in 630.12 seconds**. The failure was the existing identical-byte cache
  test: a new provenance wrapper omitted top-level supplied settings and caused
  unnecessary reparsing. That run is deliberately not rewritten as successful.
- The cache distinction above repairs that failure.
  `final_focused_checks.json` records the final command and **6 passed in 114.37
  seconds**. It covers the original failing test, a new limit-zero capture then
  publication regression, bounded malformed-table publication, synthetic grading
  failure, nested resource typed return, and Workflow return/admission/replay.
- `focused_checks.json` records earlier targeted commands, including wrong
  native program identity and malformed later table rows. These overlap other
  checks and are not additive test totals. The final whole group was not rerun.
- `final_implementation_sha256.json` identifies the final implementation and
  owned test files. There are currently 19 binding, 2 return, and 11 original
  extraction cases; this is an inventory, not a claim of one final 32-test run.

The original extraction cases use their existing smaller parser-only fixture
limits. New native searches and new bounded grading/parser fixtures use 20 GiB
RAM, 4 GiB scratch and no wall limit. The recorded runner reports cgroup memory
and swap enforcement, an unset wall budget, and monitored scratch accounting
with possible overshoot; this verification does not claim a stronger scratch
filesystem quota.

## Actual native data and numerical examples

`native_execution_receipts.json` records six tiny actual native phmmer launches
across the original and focused verification runs, including the original
commands, bounded-runner metadata, return codes and artifact digests. The tests
reuse a 253-residue supplied query against one or two explicitly supplied
sequences. The two-target fixture includes one target with three inserted G
residues. The zero-hit test runs the same tiny input with the explicit reporting
cutoff `-T 1000000`; its actual stdout/tables and zero-row summary remain in
`pytest/test_native_zero_results_is_di0/`. Its `run_local_job` helper cleans its
temporary runner receipts, so this directory retains native output and the
successful asserted return code, not a durable native handle for that case.

The 17-target/20-domain case uses existing native output from
`cases/gene_001/jobs/homology_001/`; no new reference-database search was run.
All twenty native alignments received sheets and recalculated exactly. The
test disabled filesystem opening, networking and subprocess launch during
saved-sheet calculation. It also checked actual operand correspondence,
native inclusion/accuracy/bias/envelopes, original domains and typed numbers.

`numerical_examples.json` points to five filled `.sheet.json` and `.scores.json`
pairs exported from those passing cases. The export command is:

```text
.venv/bin/python verification/tool_graders_phmmer_binding_2026-10-24/run_verification.py --export-examples
```

It explicitly reports the original suite's nonzero status and does not change
that result. It recalculates every exported sheet and asserts equality.

| Native result | Paired positions | Model span | Sequence span / envelope | Paired model coverage | Model span coverage | Native domain score / accuracy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ANGE2_BOVIN retained domain | 147 | 152 | 157 / 175 | 147/253 = 0.581027668 | 152/253 = 0.600790514 | 15.4 bits / 0.70 |
| YBHP_ECOLI retained self match | 253 | 253 | 253 / 253 | 1 | 1 | 591.5 bits / 1.00 |
| Actual tiny insertion target | 253 | 253 | 256 / 256 | 1 | 1 | 583.1 bits / 1.00 |
| CBID_GEOMG retained domain | 24 | 24 | 24 / 45 | 24/253 | 24/253 | -2.7 bits / 0.77 |

The insertion target's paired sequence coverage is 253/256 = 0.98828125 while
its sequence-span coverage is 1. ANGE2's sequence identity is 45/147 =
0.306122449, distinct from native accuracy 0.70. Its posterior lower/upper
means are 0.643630573 and 0.732802548 over the recorded posterior population;
these are display-derived bounds, not annotation correctness probabilities.
The examples also retain a native -0.9-bit domain and explicitly unavailable
components without replacing them with zero.

## Failure, custody and communication coverage

Tests separately label synthetic duplicate table/stdout rows, wrong-program
headers, malformed later rows, changed/duplicate reference sequences,
unexpected queries, partial output, printed zero E-values, parser/calculator
failure and historical parser semantics. These are engineering faults over
actual tiny data, not new biological measurements. Valid siblings and original
native bytes survive; missing tables leave explicit unavailability. A grading
failure keeps the original alignment and reports partial grading feedback
without changing actual native-completion facts. Changed database identity is
rejected before references are published. Paging, source custody, site
extraction, repeated witnesses, and unchanged canonical observations are
checked through the original interfaces.

`typed_return_evidence.json` records the actual original Workflow form and
admission path with scripted episode choices and an explicit zero engineering
credit projector. There are eight recorded scripted decisions, eight selected
actions, and eight controller observations: two parent child-commissions, five
launch actions, and one extraction action. The returned original observation
reference exposes the new numerical components. Reopen/replay changes no
records, actions or observations and requests no further scripted decision.
The separate nested resource test follows launch -> local child -> results
child -> parent typed admission. Full sheets remain outside result forms and
model-facing contexts. No configured live LLM or production scientific credit
policy is exercised by these fixtures.

## Limits and authority reset

This verifies the existing detached local **phmmer** binding. It does not prove
API/HPC deployment, large-database performance, independent background episode
deployment, other HMMER program bindings, or production scientific continuation.
No API, HPC, BLAST, literature operation, unrelated live run or goal-document
rewrite was performed by this workload. Supporting acquisition/library/status
changes remain root-owned.

The immutable original attachment was read in full before work. Its objective
and entire DESIGN PRINCIPLES block were reread verbatim after substantial native
review and again after implementation, followed by both B003 contracts. This
was implementation review only; it adds no runtime gate or credited work.
