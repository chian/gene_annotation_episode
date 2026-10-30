This workload implements numerical publication from captured native HMMER
bundles. It does not execute a new scientific search, select resources, run a
model, change annotation credit, or prove an episode communication path. Root
owns the actual acquisition/attempt/receiver qualification and integration tests.

`EXAMPLES.json` points to the checked examples in `examples_checked/`. Each case
contains an actual Store, complete captured inputs and outputs, full populated
sheet and score artifacts, selected NDJSON, the original result source,
published observations when binding is valid, the selected acquisition envelope,
and a selector-independent source envelope. The biological Store subjects and
operand bindings are explicit synthetic association fixtures; scientific output
bytes come from the existing captured native producer runs listed in each
`EXAMPLE.json`. No new native search is represented by these examples.

Concrete filled measurements:

| Case | Actual numerical components | Publication |
| --- | --- | --- |
| Protein `test3` domain | model span 20/20 = 1.0; paired model positions 19/20 = 0.95; sequence span 24/28 = 0.8571428571428571; paired sequence positions 19/28 = 0.6785714285714286; native domain score 41.2 bits; conditional E-value 2e-14 | Bound to the exact original captured database sequence and its matching Store subject |
| Profile query with no database-sequence binding | domain score 72.1 bits; paired positions 20; paired model and sequence coverage both 1.0 | Explicitly unbound; no observation and no invented subject |
| Reverse nucleotide locus | native score 120.9 bits; paired positions 100; model coverage 100/100 = 1.0; sequence coverage 100/120 = 0.8333333333333334 | Bound actual reverse target; native strand `-`, typed returned strand `minus` |
| Trimmed `test2` alignment | original length 25; retained residues 21; trimmed residues 4; model occupancy 18/20 = 0.9; original-sequence match coverage 18/25 = 0.72 | Bound original sequence, using validated original coordinates rather than trimmed length |

`recalculation.json` records exact saved-score equality and unchanged input
sheets for all four examples. Network sockets, process launch, and file opens
are prohibited after the saved sheets and expected scores are loaded. Reproduce
it from the repository root with:

```
PYTHONPATH=. .venv/bin/python verification/tool_graders_native_hmmer_publication_2026-10-24/recalculate.py
```

`pytest-final.txt` and `VERIFICATION.json` record the final owned-publication,
closed-schema, and B003 pure reader/calculator checks, their exact command,
return code, and owned production-file hashes before/after the run. Bounded
workers use caller policy 20 GiB RAM, 4 GiB scratch, and no wall-time limit.
The pre-correction run passed **218 tests in 226.86 seconds**: 49 publication/view tests
and 169 existing B003 reader/calculator tests. All three owned production-file
hashes remained unchanged during that run.
Tests cover all 12 captured producer modes across six programs; additional
retained B003 fragment/mapali/trim modes; malformed/missing output siblings;
negative scores and zero E-values; no hits; wrong names, ordinals and sequences;
duplicate database names; query ordinals; dependent jackhmmer rounds; reverse
loci; exact-key and offset/limit selection; stable source and observation
identity across selectors; source-only/unbound measurements; streamed host
publication; retained worker failure; and no hidden replay retry. The selected
metric set changes the returned row, not the original observation identity.

A later episode integration check found that an explicitly wrong biological
subject was rejected correctly but its returned row still said `unbound`.
`binding-status-correction.json` records the subsequent focused four-test pass
and changed publication-file hash. Explicitly rejected name/sequence/interval,
scope or reference mappings now return `invalid`; only an absent association
returns `unbound`. Valid siblings still publish, and invalid/unbound siblings
retain their numerical measurements. The 218-test receipt remains historical;
the correction's practical-completion integration proof is owned by worker 068.

Earlier exploratory artifacts remain under `examples/`. Their nucleotide
profile metadata was rejected because the first implementation did not
normalize native `ALPH DNA` to the calculator's `dna` value. The final worker
preserves `native_alphabet` and normalizes only the parsed alphabet. The final
checked nucleotide example is numerically complete. `examples_final/` preserves
the first case from a verification-script invocation that failed while making a
relative display path; the script now resolves its destination first. Neither
earlier directory is the checked evidence index. These partial artifacts were
retained rather than silently overwritten.

Known boundaries remain explicit: native profiles are not original biological
sequences; duplicate database names without a unique association stay unbound;
later jackhmmer learned rounds cannot bind their model consensus to the original
query and require an explicit actual database-sequence binding. Corrupt or
missing siblings remain failures alongside useful rows. Full episode admission,
new native producer execution, PBS deployment, and remote services are outside
this publication workload and are not claimed by these tests.
