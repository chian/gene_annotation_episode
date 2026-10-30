# MinHash contracts and saved projection verification

This records a completed component verification within open R1/R2 work. It is
not completion of the MinHash episode path, the BV-BRC R2 group or the goal.

Workload A's pure selector/metadata/publication-input validators and common
fraction helper, and workload C's saved-value projection, are implemented and
verified at the retained snapshots. The original common sheet and calculator
schemas remain in use. Distance and binomial calculations were not rewritten.
The full calculator and projection consistency check now use the same fraction
helper; projection copies the saved values.

| Attempt | Result | Qualification |
| --- | --- | --- |
| check001 | 423 passed, 4 failed; 2.563 seconds | The four failures could not open the original retained Mash genomes.dist fixture, omitted from the root-created snapshot. |
| check002 | 4 passed; 1.724 seconds | Staged the original missing fixture and reran only those four cases. No production or test assertion change was needed. |

There are 427 distinct passing cases across these attempts, with no overlap in
their passing identities. This is not one fresh 427-case passing suite. Both
original handles were collected after terminal/quiescent status. All source,
dependency, interpreter, standard-library and native pins stayed unchanged;
both import/native mapping audits were clean. All seven owned source/test files
still matched both frozen snapshots at the recorded check. Tests used the
existing local lifecycle with 20 GiB RAM, 4 GiB scratch, zero swap and no wall
limit. No external API call, native MinHash search or HPC job ran.

Passing checks cover legacy publication projection, both request modes, closed
input shapes, strict integers and exact per-field artifact/list associations,
explicit missing inputs, both-key row joins, duplicate and unmatched metadata,
zero/partial/malformed native values, saved-sheet recalculation and requested
value equality. Projection works with the full parser/calculator and I/O
disabled. Pure source references in these fixtures establish no actual custody.

In the synthetic 2/3 example with k=1, lengths 2/2 and alphabet size 2, the common
calculation gives distance 0.22314355131420976 and p-value 0.2592592592592592.
Changing only explicitly supplied k to 2 gives 0.11157177565710488 and
0.10400000000000001. The projection copies those saved components; original
reported values and artifacts remain unchanged. K-only metadata keeps distance
available and p-value unavailable. These are numerical fixtures, not new
biological or live-provider results.

The exact diagnostic-form registration test remains unexecuted pending B521's
communication.py integration. It is retained unchanged, without skip/xfail.
Service publication, actual metadata/source custody, saved-result commissioning,
selector-independent acquisition credit, full child/parent delivery and closed
Workflow replay remain the B521/D522 integration work. Instruction presentation
and live service/remote sketch-parameter verification are also unfinished.

Root reviewed the pure contracts, numerical refactor, complete changed
projection logic, authored tests and worker reports; read the relevant existing
service, host, API execution and original-return consumers; inspected both
receipts, JUnit outcomes and execution audits; and compared current owned bytes
with both snapshots. The full original objective and ten operating principles,
then the complete 517 contract and root clarification, were reread before this
record. CHECK_RESULTS.json preserves the exact counts and verification limits.
