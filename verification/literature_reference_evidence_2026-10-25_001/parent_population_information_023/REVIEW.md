# Parent population information 023 — scoped implementation and verification

The explicitly configured source-evidence annotation parent now receives the
actual literature child population operation names and descriptions before
selecting a child's requested numerical form. Its recurring TASK renders those
14 entries in one table. Existing child catalog entries, schemas, order and
dispatch are unchanged. This is capability information, not reader completion
or numerical delivery from the actual020 paper.

Only these production files changed:

| File | Change |
| --- | --- |
| `gene_annotation_episode/literature_episodes.py` | Move the existing population catalog construction unchanged into the pure, role-independent `_population_catalog`; child `catalog` extends it; explicitly source-bound root `initial_decision_context` projects only `name` and `description` under `reference_evidence_parent.child_population_operations`. |
| `gene_annotation_episode/literature_reference_parent_prompt.py` | Render that projection in the recurring TASK under “Population operations available within literature children,” with columns “Child operation” and “Input capability and meaning.” |

New test: `tests/test_literature_parent_population_information.py`. All other
outputs created by this owner are in this 023 directory. No runtime, durable,
source-location, tool dispatch, reader, calculator, scoring, historical run or
pin file was edited. The workspace has no `.git` repository; a scoped `git
status` attempt therefore returned “not a git repository.” Source scope was
verified by exact original hashes and an AST comparison instead.

The initial production hashes matched the ownership contract exactly:

| File | Before SHA-256 | After SHA-256 |
| --- | --- | --- |
| `literature_episodes.py` | `ddabb6d6f5048276e5c8eda47e812538975b2350a326813cec469ad4cd83d053` | `f0133c6272edb46409dca7b32dcd44429d758b64d45c7eaba68dfb55c7303208` |
| `literature_reference_parent_prompt.py` | `dc8db411948432ca187f51c38d3e22ffedfa2c4380362a8744936989f1cfb89f` | `b34f7317c8ae19d8426cacd5f332c8e2ed917ecdac0fd6df3b6b6e00782d98d2` |
| New test file | absent | `092d0408c3e9daa45e69643a85168843d2afaf22cdcd67a1deeddc4bc890405f` |

`population_catalog_before.json` was captured from the original C7 source
before editing, using an empty ordinary-tool catalog and a synthetic literature
context. It contains all 14 population entries, including every original input
schema, in order. Its 493380 bytes have SHA-256
`cf6c09e480151012122c232641bad514bd4a2ab20ca4cc5a3af27f240e9a5faa`.
The new test asserts both that immutable baseline hash and full entry equality
for every one of the seven literature roles, including the ordinary-tool prefix.
The baseline is verification data; its schemas are not concatenated into the
new metadata table.

`source_change_audit.json` records an AST comparison against the original two
files captured at the contract hashes. All 30 other C7 methods, including
`execute`, `_tool_arguments`, assignments, reports and credit paths, are
unchanged. The extracted helper's population construction equals the original
catalog block exactly. Removing only the new parent metadata field restores
the original initial-context AST. Removing only the new table statements
restores the entire original parent-prompt AST. `owned_source_changes.patch`
records the source diff. Temporary original-source copies used by this audit
were removed after producing the evidence.

The complete source-to-consumer trace inspected was:

| Boundary | Inspected implementation and resulting behavior |
| --- | --- |
| Authority | Complete 023 contract, active attachment `ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt`, root `AGENTS.md`, `GOAL.md`, `docs/EPISODE_STRUCTURE.md`, `docs/TIME_AWARE_ESTIMATION.md`, `docs/TASK_AND_STEERING.md`, and the W04 evidence-axis amendment. |
| Ownership and catalog | Complete original and changed `literature_episodes.py`; helper has no context, services or identity parameters. Actual child roles and executable catalog still own the population operations. No fake child identity is constructed to project parent metadata. |
| Source assignment | `initial_decision_context` retains its existing explicit `reference_parent_sources`, root annotation role, received-source and scope checks, and original custody fields. Unconfigured parents, scoped/non-annotation contexts and ordinary children receive no new metadata. |
| C7 composition | `EpisodeBindingRegistry.initial_decision_context`, `BindingContext`, and complete `episode_composition.py`: saved descriptor configuration reconstructs the same metadata; no annotation executable binding or resource capability is added. |
| Application delivery | Complete `DecisionSource.call` and `instructions`, and relevant complete `WorkflowServices` catalog, source-reference, execution and own-outcome methods: only new decisions get the bound initial information; saved historical requests retain their original context. |
| Provider and frames | Complete `_SessionConnection.complete`/`_presentation` and `decision_context.py` frame construction/application: actual provider text receives full TASK on bootstrap, delta, same-decision lookup and reconstructed bootstrap. Typed output schemas stay unchanged. |
| Rendering | Complete parent prompt and relevant complete shared experimental rendering functions: only names/descriptions enter the added TASK table. Existing own-operation operands and declared return schemas retain their separate purpose. Returns, lookup qualifications, yield tables and missingness remain terse STEERING. |
| Actual input distinctions | Complete rate reader and rate `populate`, native partner input reader and partner `populate`: rate accepts a received CSV/TSV summary with exact headers; native partner parses selected literal spans, supported units and source-defined endpoint units. The descriptions copied into metadata are the existing ones. No descriptions or reader capabilities were broadened. |
| State and accounting | Synthetic real-store runtime commissions exactly the selected child, populates its selected rate operation once, admits the caller's arbitrarily named closed field and performs one selected parent reasoning action. Exactly three provider decisions and three observations; controller scores `[[0, 0], [0]]`; scientific credit zero. The metadata projection itself changes no database row/schema and calls no execution or credit service. |

Exact test commands and results:

```text
.venv/bin/python -m pytest -q tests/test_literature_parent_population_information.py
13 passed in 20.90s

.venv/bin/python -m pytest -q tests/test_literature_reference_parent_prompt.py tests/test_literature_reference_parent_delivery.py tests/test_literature_experimental_prompt_delivery.py tests/test_literature_episode_branches.py tests/test_literature_rate_episode_integration.py tests/test_decision_provider_frames.py
47 passed in 39.67s
```

The second command's stdout and exact argv/exit status are saved in
`affected_tests.txt` and `affected_tests.json`. The first execution of the new
test command produced 10 passes and 3 failures in 20.79s: its fixtures expected
an unbound registry lookup to return `None` instead of raising `LookupError`,
omitted journal-table initialization before an own-outcome read, and selected
an empty reasoning commit that is not a completed action. Only the new test
fixtures were corrected; no production fix was made in response. The repeated
new-test command then passed all 13. An initial bare `python` baseline-capture
attempt failed because `python` is not on PATH; the capture was successfully
performed with `.venv/bin/python` before source edits.

The new checks explicitly establish acquired CSV/TSV versus literal source-span
and endpoint-unit descriptions, full catalog equality, no schema/ID/sheet
projection into the added table, source custody, descriptor reconstruction,
TASK-only metadata, repeated full assignment/constraints/return meanings,
TASK deduplication, qualified returns and lookups only in STEERING, unchanged
arbitrary parent field names, no parent executable population grant, and no
synthetic action/observation/credit from projecting capabilities.

Limits: this owner launched no model and acquired or interpreted no paper. The
controlled provider uses scripted RPC responses; the runtime fixture uses
synthetic TSV input, a scripted provider and fixture controllers. Existing
affected tests include retained-source fixtures, not new source acquisition.
These checks do not establish that a model will choose a compatible reader or
form after receiving the information. Missing native readers remain missing;
actual020's failed native quote check and lack of numerical delivery are not
changed. Actual022's captured 625-file pin and model run remain immutable and
outside this owner's work. No A105-axis, other-axis, full-goal, W05 or
annotation-credit completion is claimed.
