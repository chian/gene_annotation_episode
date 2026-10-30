# Host recovery evidence,407

2026-10-27. This packet verifies the approved403 host boundary. It does not
accept the complete protein tool row or change112/308.

`check005` executed two focused tests from its immutable source snapshot.
Both passed in86.12seconds. Its existing local_jobs receipt records20GiB RAM,
4GiB scratch, zero swap and no wall-time budget. Executed pins were unchanged;
checkout drift was zero. The exact request, native receipt, stdout/stderr and
before/after source pins are retained in that directory.

The first test ran an actual native inspection and actual396 result worker.
Two explicit callers selected the same result action. While the first awaited
preparation, the second waited for406's action lock outside the event loop.
Cancelling the first caller twice left that lock owned until its worker
finished. The second caller then reused the same396 reservation and produced
the result. Exactly one native reservation and one completed result action
were observed; its acquisition count was one.

The second test injected a host interruption immediately after400 wrote its
ordinary source. The pending action exposed no own facts. Retrying that exact
selected action returned the same source using392's retained capture and396's
retained preparation. Producer-file reads and native prepare/start/resume/wait
calls were forbidden during recovery. The completed action supplied one
acquisition contribution and the ordinary eight-field completion proof.

These are host tests over actual practical execution and runtime records. The
outer Workflow chooser, full resource-child communication tree and controller
observation path belong to root's separate connected verification.

Executed production pins:

- `native_protein_structure_results.py`: `04dda1eadd6d9a3cffa2691dc8bfc1ebc0f85d62fda4e1cacc2079718ffa7338`.
- `protein_structure_result_receipts.py`: `6d5c0c7fd007d678457269dcaa52d6fb86322d9517e9f9644dc471c6f0988631`.

No test fabricates scientific measurements. The small supplied structures are
labeled synthetic engineering fixtures; the injected interruption is a test
of recovery, not a claim of a native scientific failure.
