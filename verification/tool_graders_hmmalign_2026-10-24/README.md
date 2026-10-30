# hmmalign native measurements and deterministic calculations

These are native HMMER 3.4 outputs from tiny supplied fixture inputs, not biological
validation data. `native/seed.sto` and `native/sequences.fa` are exact copies of
bundled `hmmer/testsuite/20aa.sto` and `20aa-alitest.fa`. The fragment seed is an
explicit synthetic input with inherited terminal/internal insertions and native
`~` missing symbols. Its resulting outputs are actual native execution results.

Every invocation used the existing `run_local_job` / native lifecycle with
20 GiB RAM, 4 GiB scratch and `wall_seconds=None`. The seven receipts retain the
exact commands, exit codes and verified cgroup limits. Two `hmmbuild --amino
--hand` preparations and five `hmmalign` executions exited zero. No API, HPC,
database BLAST or NCBI job was used. Complete output, stderr, inputs and models
remain under `native/`; no output was reconstructed from a preview.

The inspected native sources were `hmmalign.c`, `tracealign.c`, the posterior
encoding implementation in `p7_alidisplay.c`, `esl_msa_Checksum` in Easel
`esl_msa.c`, Easel's amino/DNA/RNA alphabet definitions, the hmmalign manual, and
native mapali regression tests. The authoritative original objective and entire
design-principles block, followed by B003, were reread after that examination.

## Checkable examples

| Actual mode / row | Original | Match / model | Deleted | Internal insert | Retained terminal | Retained | Trimmed | Sequence match coverage | PP mean bounds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| ordinary / test2 | 25 | 18 / 20 | 2 | 3 | 4 | 25 | 0 | 18 / 25 = .72 | [22.55 / 25, 24.15 / 25) = [.902, .966) |
| trim / test2 | 25 | 18 / 20 | 2 | 3 | 0 | 21 | 4 | 18 / 25 = .72 | [18.75 / 21, 20.15 / 21) |
| mapali / inherited seq1 | 20 | 20 / 20 | 0 | 0 | 0 | 20 | 0 | 1 | unavailable |
| fragment mapali / fragment | 14 | 14 / 20 | 0 | 0 | 0 | 14 | 0 | 1 | unavailable |
| fragment mapali trim / inherited | 26 | 20 / 20 | 0 | 2 | 0 | 22 | 4 | 20 / 26 | unavailable |

The fragment has six missing model positions, not six deletions. Model occupancy
retains the full model denominator, 14/20. Column occupancy excludes `~` from
the observable denominator and reports excluded rows explicitly. Insertion
columns never claim homologous sequence positions. `terminal_unaligned_residues`
counts flanks retained in the output; `trimmed_residues` counts those removed.

The ordinary seed's actual digital checksum is 1166427327; the fragment seed's
is 1589892361. Mapali validation recomputes this native uint32 checksum from
actual supplied seed symbols and validates the supplied native MAP coordinates.
It also checks the ordered inherited prefix, mapped symbols and retained
sequence symbols. A checksum is not a cryptographic identity; artifact custody
remains separate. Claimed checksum metadata without actual seed text does not
establish compatibility. Unknown original offsets remain unknown: synthetic
ACAC → AC trimming retains both possible original intervals, [0,2) and [2,4).

Mapali yields ten inherited rows plus four newly aligned rows in the ordinary
fixture. At its first model column occupancy is 14/14, but native PP_cons covers
the four newly aligned match-state residues. The ten inherited rows have no PP;
their PP means are null. Native PP bins are intervals, not exact posterior
probabilities and not gene-function confidence.

## Interfaces and verification

`hmmalign_inputs.py` owns `parse_hmmalign_stockholm(text, *, artifact_ref,
engine_version)`, `build_hmmalign_sheet(native, *, inputs)`, and the documented
event/record/row stream iterators. Events require no alignment buffering;
assembled interleaved rows buffer one alignment record. Lines, UTF-8 byte
intervals, name occurrences and all original annotations remain retained.

`hmmalign_grader.py` owns `calculate_hmmalign_scores(sheet, *, parameters=None)`.
Only `None` or `{}` is supported; unknown numerical parameters are errors.
The calculator uses populated numerical cells and performs no native parsing,
file access, network request, executable call, Store mutation or LLM call.

Run from the repository root:

```
.venv/bin/pytest -q tests/test_hmmalign_inputs.py tests/test_hmmalign_grader.py
.venv/bin/python verification/tool_graders_hmmalign_2026-10-24/recalculate.py
```

The tests cover actual native output plus synthetic interleaving, duplicate
names/occurrences, exact byte locators, ambiguous joins, wrong sequences and
lengths, missing PP/RF, zero PP, posterior quantization, malformed/truncated
output, invalid saved rows, fragments, inherited insertions, checksum/map
failures and trim-offset ambiguity. Saved sheets and score artifacts for all
five modes are in `saved/`; `EXAMPLES.json` contains the compact filled examples.
`build_retained_examples.py` rebuilds these from retained files without running
a scientific tool. `recalculate.py` reads only saved sheets and expected scores,
then prohibits open/socket/subprocess/parser/builder access inside calculation
and verifies exact numerical equality and no mutation for every mode.

Final owned test run: **73 passed in 0.40 s**. All five saved recalculations
matched exactly. Live fixtures used amino-acid models; DNA/RNA checksum
normalization has synthetic coverage and was not separately executed natively.
The original objective, full design-principles block and complete B003 contract
were reread again after completing this pure-module verification.

Pure parser/calculator verification and bounded native invocation are verified.
Complete selected-tool → resource child → complete artifact → sheet/calculator
→ requested typed receiver integration is **not verified by this worker**. Root
owns that production binding and its tests. No pure test or installed binary is
claimed as proof of episode-path completion. Literature graders and W05 credit
aggregation were not changed.
