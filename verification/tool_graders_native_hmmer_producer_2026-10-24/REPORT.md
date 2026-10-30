# Native HMMER producer verification, 2026-10-24

Implemented only the B004 workload-1 files: `native_hmmer_contracts.py`,
`native_hmmer_driver.py`, `native_hmmer_tool_info.py`, their three focused test
files, and this verification directory. Shared execution, Store, graders,
episode prompts, credit and continuation were not edited by this workload.

The pure compiler validates finite JSON, exact original wrapper equality,
program/mode operand roles, all four explicitly supplied pressed companions,
declared outputs, path confinement and supported native options. It opens no
files. Search stdout/tables and stderr are required; hmmalign retains Stockholm
and stderr. Optional -A alignments, jackhmmer checkpoint prefixes and nhmmer
alignment-mode --hmmout are retained. Checkpoint files retain separate paths;
their query/round relationships are not inferred from suffixes. Unsupported
Dfam, per-position and Pfam table outputs, external matrix/background/index
paths, and unrepresented native flags reject explicitly.

The producer stages exact original input bytes in an exclusively owned fresh
attempt, checks expected sizes/digests and executable digest, runs the selected
command once, and atomically publishes `bundle.json`. Original argv remains in
the validated requested job; realized staged argv and actual environment are
separate manifest fields. Inputs, scratch, cache and outputs remain within the
attempt. Caller policy is unchanged. A sealed replay verifies artifact digests;
conflicting or unsealed attempts never rerun. Native nonzero outcomes preserve
produced bytes and structured stage-specific failures.

The caller must run the producer through its existing resource boundary.
The producer does not install another native lifecycle or poll work. The
retained live checks used `run_local_job`, with verified 20 GiB memory,
4 GiB scratch and no wall-time limit. Hard outer termination can leave an
unsealed attempt; that remains uncertain, with no replacement execution.

Scientific information is supplied only for explicit
`{program, mode, software}` bindings. The host catalog uses the requested
`native_hmmer_tool_contracts(bindings, resource_kind=..., resource_id=...)`
commissioning interface. Public projection contains exactly name, description,
resources (one local/hpc string), and instructions. Configured mode/software
restrictions remain in the separate invocation schema. No executable discovery
or remote deployment inference occurs.

## Actual native runs and numerical examples

All inputs below are tiny synthetic sequence/profile fixtures from B003;
all output bytes came from actual installed HMMER 3.4 execution. Each run
directory contains the plan, bounded runner receipt, full staged inputs,
sealed bundle, full native output, populated sheet, calculated scores and
an example carrying its actual record key.

| Native operation | Native result and checkable example |
| --- | --- |
| hmmscan | One domain; 72.1 bits; model and sequence spans 20/20 = 1. |
| hmmsearch | Four domains; selected test1 domain 72.1 bits, spans 20/20. |
| hmmsearch with explicit high native thresholds | Successful completion with zero domains; five artifacts, including the native empty alignment output. |
| jackhmmer, -N 2 | Eight domain rows across retained rounds; selected round domain 68.2 bits. Nine artifacts include two HMM and two MSA checkpoints. |
| nhmmer sequence | Three loci; forward locus 92.2 bits, model span 100/100 = 1, sequence span 100/120 = 0.8333333333333334. |
| nhmmer profile | Three loci; forward locus 120.9 bits, model span 100/100 and sequence span 100/120. |
| nhmmer alignment | Three loci; forward locus 120.9 bits; constructed HMM and included MSA retained separately. |
| nhmmer profile, --watson -Z 0.1 | Two loci; actual strand selection and search-space operands retained. |
| nhmmscan | Three loci; selected locus 120.9 bits. Model length 100 remains distinct from query length 120. |
| hmmalign ordinary | Four rows; test1 has 20 match-state residues, model occupancy 20/20 = 1 and sequence match coverage 20/20 = 1. |
| hmmalign --trim | Four rows; complete trimmed output and original input metadata retained. |
| hmmalign --mapali | Four new plus ten inherited rows; 14 rows retained and graded. |

Each successful saved sheet recalculated identically with filesystem,
subprocess and network operations prohibited during calculation. Each sealed
attempt replay returned the original manifest; tests also forbid new process
creation during replay. Native program, inputs and output bytes remain separate
from scientific confidence: this workload defines no new numerical formula.

An additional actual hmmscan attempt deliberately supplied a nucleotide h3p
file alongside the protein profile's other companions, with the supplied file's
own correct digest and native stem. The command ended with returncode -6 and
an 84-byte stderr reporting a forward-score underflow. Stdout/tables existed
with zero bytes. The bundle preserved these exact facts and replayed unchanged.
This is a failed execution, not a complete zero-hit scientific search. The
verification script's initial expectation of nonempty stdout was corrected to
match the retained actual empty stream; the failed native attempt was not rerun.

## Checks and exact commands

Final focused command:

```text
.venv/bin/pytest -q tests/test_native_hmmer_contracts.py tests/test_native_hmmer_driver.py tests/test_native_hmmer_driver_retained.py
64 passed in 2.73s
```

Native verification commands:

```text
.venv/bin/python verification/tool_graders_native_hmmer_producer_2026-10-24/run_native.py hmmscan
.venv/bin/python verification/tool_graders_native_hmmer_producer_2026-10-24/run_native.py hmmsearch
.venv/bin/python verification/tool_graders_native_hmmer_producer_2026-10-24/run_native.py jackhmmer
.venv/bin/python verification/tool_graders_native_hmmer_producer_2026-10-24/run_native.py nhmmer
.venv/bin/python verification/tool_graders_native_hmmer_producer_2026-10-24/run_native.py nhmmscan
.venv/bin/python verification/tool_graders_native_hmmer_producer_2026-10-24/run_native.py hmmalign
.venv/bin/python verification/tool_graders_native_hmmer_producer_2026-10-24/verify_native_failure.py
```

Every original native argv is in its bundle and every outer execution command
is in its runner receipt. Tests additionally cover missing/wrong inputs and
software, unsupported/conflicting options, incomplete pressed operands, wrong
pressed stems, output escape/overlap, synthetic scratch exhaustion, native
nonzero/partial output, exactly one actual HMM for hmmalign, immutable replay,
conflicting requests and mutated/symlinked sealed outputs.

Inspected installed primary sources include the six programs' native option
tables, nhmmer input-mode selection, hmmalign framing, and the pressed profile
I/O implementation. Inspected existing local_jobs, native_lifecycle and its
worker in full. B003/B004, original authoritative objective/design principles,
episode/resource design, and practical/task guidance were read. The original
objective and complete design-principles block were reread verbatim after
substantial source review and after each scientific tool, followed by B004.

## Boundaries not established here

These are producer/native-format and deterministic recalculation checks. They
do not establish scientific child construction, selected launch/resource
ownership, complete artifact import/publication, typed parent admission,
exactly-once episode credit, or practical endpoint integration. Root owns those
shared paths. No live API, HPC, database BLAST or literature work was performed.
The local checks do not establish HPC deployment. Hmmalign real fixtures here
use protein profiles; additional alphabets are retained explicit native choices.

Pressed sidecars are explicitly named, digest-checked and staged under the
native expected stem. This identifies exactly the supplied set. It is not a
proof of index generation, freshness or full consistency with every source
profile; a complete independent binary consistency audit is not implemented.
The controlled wrong-companion failure above does not imply that every possible
stale or inconsistent pressed set is detected. HMMER's own native checks and
failure output are preserved without overstating their coverage.
