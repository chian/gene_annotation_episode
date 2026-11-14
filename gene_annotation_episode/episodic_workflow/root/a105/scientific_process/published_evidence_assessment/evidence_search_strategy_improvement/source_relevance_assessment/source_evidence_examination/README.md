# Source evidence examination: one episode organization example

This directory is the complete source-examination episode. Its existing
method_loop role is `literature_page`; its commissioning parent is
`source_relevance_assessment`. The implementation is written in advance.
An invocation supplies a source assignment, objective and result contract;
it does not generate episode code.

`episode.py` connects the following implementations. The central task and
scientific functions live in their responsibility files.

| File or directory | Responsibility |
| --- | --- |
| `from_parent.py` | Admit the source assignment, its custody and requested return contract. |
| `goal.py` | Validate the commissioned objective and required result; expose planning context with the same progress definition used for credit. |
| `task.py` | Select and execute the source's work through the existing iterator, including tools, scientific interpretation and child work. Interpretation requiring grading saves its sheet in the same action. |
| `task_decision.py` | Present the available work and exchange decisions with the provider. |
| `task_state.py`, `task_records.py` | Save and restore the task state and action records. |
| `internal_summary.py` | Present source custody, own outcomes, unresolved work, commissioned goal and current facts to the next decision. |
| `to_child_table_evidence_extraction.py`, `from_child_table_evidence_extraction.py` | Send a table-reading assignment; receive that child's typed results. |
| `to_child_passage_evidence_extraction.py`, `from_child_passage_evidence_extraction.py` | Send a passage-reading assignment; receive that child's typed results. |
| `to_child_source_coverage_improvement.py`, `from_child_source_coverage_improvement.py` | Send a source-coverage assignment; receive that child's typed results. |
| `grading/` | Evidence applicability, required assessment contracts, typed scientific findings and saved grading sheets. |
| `scoring/` | Numerical calculations and their saved scientific results. `assay_evidence.py` contains the numerical functions extracted from the assay grader. |
| `credit.py` | Credit for the commissioned result, retaining the original policy for graded experiments, revisions and unresolved evidence. |
| `yield.py` | Estimate remaining commissioned credit and apply the existing continuation policy. |
| `to_parent.py` | Expose and validate the requested scientific return facts. |
| `prompts/`, `tools/` | Private scientific prompts, source readers, operand validation and operation catalogues. |
| `scientific_records.py`, `source_references.py`, `received_evidence.py` | Access and validate this episode's scientific records and received evidence. |
| `configuration.py`, `source_contracts.py`, `waiting.py` | Fixed configuration, schemas and existing wait declarations. |
| `binding_record.py`, `implementation_sources.py` | Identify the exact configured implementation and locate its source/contract assets. |

These are responsibilities in the iterative process, not a one-pass pipeline.
Planning and summary inform each next action. An accepted interpretation must
retain its typed investigation finding and required grading sheet before credit.
Scientific evidence scoring and task-progress credit remain distinct. The
existing method_loop controller decides continuation from the yield estimate.
Returning a partial or unresolved assessment does not manufacture support.

## What was actually split

The former local `requests.py` and `returns.py` have been replaced by the
directional files and the separate goal/task/report responsibilities.
The source's decision/execution implementation was extracted from the axis
runtime into `task.py`, `task_decision.py`, `task_state.py` and
`task_records.py`. The connector declares that private task implementation.

The A105 runtime now honors three optional binding interfaces: the private
task type, outgoing child assignment preparation, and incoming child-result
handling. Bindings without these interfaces retain their previous path.
Redelivery uses the original saved child action to choose the counterpart.

The 214 reachable scientific helper modules have private copies here, with
imports directed to those copies. Their original scientific descriptions are
retained. The assay grader's seven numerical functions now live in
`scoring/assay_evidence.py`; the grader calls them when assessing the evidence.
The module ownership/provenance map is `ownership_pilot.json`.

Shared method_loop, provider transport, database/domain infrastructure and
source acquisition services remain external dependencies. Existing release
provenance constants still identify the historical implementations they describe.
The three child episode directories are separate episodes and have not undergone
this responsibility split. This example does not claim completion of the larger
episode reorganization.

## Validation retained on 2026-11-11

- All 246 private Python implementation modules compile and import.
- All 214 scientific helper bodies match their originals after import relocation
  and the declared numerical extraction. The seven extracted numerical function
  bodies also match individually.
- The local suite has **103 passing tests and 23 failing tests**. All 23 failing
  test identities and error messages match the unchanged A105 implementation.
  They include existing contract/expectation failures and unavailable old imports.
- Controlled tests exercise private task selection by the actual runtime entry
  point, default behavior for other bindings, child counterpart delivery,
  grading/scoring-before-credit order, completed-action replay, goal/credit
  consistency, yield at completion, implementation paths and invalid tool outcomes.

Receipts are retained at:

- `runs/source_episode_pilot_20261111_final/results.xml`
- `runs/source_episode_pilot_20261111_final/comparison.json`
- `runs/source_episode_pilot_20261111_final/stdout.log`
- `runs/source_episode_pilot_20261111_baseline/results.xml`

These checks establish the file split and controlled behavior. They do not
establish autonomous source examination, saved whole-workflow reopening or
combined-root integration; the central ledger records the existing integration
gaps.

## What this example establishes for the next scope

A useful episode split must follow execution and messages through the runtime,
as well as separate the binding's methods. A connector-only move leaves the
central task elsewhere. Goal planning must use the actual commissioned result
and credit definition. Grading and numerical scoring need explicit ownership
even when they were previously interleaved in one file.

The scientific dependency footprint is much larger than the original seven
binding files. A broader scope should explicitly distinguish each episode's
private scientific implementation from reusable infrastructure and preserve
the existing formulas, contracts and evidence identities while moving them.
