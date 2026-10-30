# Protein execution schema reuse

The native execution validators now reuse private validators over fixed schemas.
Every supplied payload still undergoes the original Python-type, finite-number,
schema and relational checks. Binding-specific documents still use the current
supplied operation, scientific mode and software. Public schema exports are fully
detached, so changing an exported inner resource cannot alter later definitions.
No authority verdict, receipt, payload, current-byte check or result is cached.

The public function signatures, schema values, content-derived IDs, scientific
measurements, action credit and episode continuation rules are unchanged.

## Verification

`check001` passed **85 tests in 55.20 seconds**: 33 new schema-equivalence,
mutation-isolation, strict-type, binding and concurrent-validation cases, plus
52 existing native contract, tool-information and execution cases. Execution
tests use synthetic PDB/mmCIF inputs with real native workers and local durable
execution. They include exact supplied transforms, held-out 2 angstrom results,
retained alignment correspondence, missing coordinates, failed software/inputs,
partial results and replay. They are not configured-model science or the full
Workflow test.

The run enforced 20 GiB RAM, 4 GiB scratch, zero swap and no wall-time budget.
Executed source hashes stayed unchanged; checkout drift was zero. The prior
implementation is retained under `prechange/`; both it and the new code were
pinned in the executed source snapshot. Exact source pins, diff, request, output
and receipt are retained alongside this report.

415 independently repeated its real retained 410/check007 admission diagnostic
with the same harness after these checks. Both runs accepted the original form
through the actual resolver and semantic callback, with unchanged retained
inputs. Profiled wall time changed from 48.274595 to 32.5116 seconds. Schema
construction changed from 295 calls to 9; all 293 payload checks still ran,
including the same 125 request and 58 job validations. This is a measurement of
one profiled diagnostic, not a claimed full-Workflow speedup. Registry traversal
remains a separately measured cost and was not changed.

415 retains the exact comparison, per-stage measurements and qualifications.
The frozen harness compares original form/facts and actual admission outcomes;
it does not serialize the returned ParentReport object for a separate object
comparison. Source-level claims must retain that distinction.

## Remaining work

410 continues the complete selected-tool/child/return/recalculation Workflow on
its existing frozen sources. 412's separate retained-target checks are separately
recorded. Receiver text and model decision operand selection remain unfinished.
No whole protein capability or additional tool-count acceptance follows from
this optimization. The accepted tally remains 112/308.

The initial metadata setup command used an unavailable bare `python` executable
and returned 127 before running its script. It was corrected to `.venv/bin/python`.
There was no failed scientific run or unrecorded test attempt in packet416.
