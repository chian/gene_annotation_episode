# Partner interpretation TASK clarification — workload 160

This is an additive implementation and synthetic-verification record, not a
replacement goal, numerical contract, scoring sheet, or scientific result.
The original supplied goal remains authoritative. Scope here is the recurring
A105/supporting-partner investigation guidance already discussed in chat.
No paper or retained paper-specific packet was opened. No actual model call,
private model/provider request, response, or log was accessed. No current run
was restarted or rewritten.

## Changed files and exact wording

The only changed existing production file is
`gene_annotation_episode/literature_partner_prompt.py`. The exact pre-edit file
is preserved in `PARTNER_PROMPT_BEFORE_001.py`; its bytes match the fingerprint
captured before mutation in `BEFORE_001.json`. The exact final file is preserved
in `PARTNER_PROMPT_AFTER_001.py`.

Two scientific paragraphs were added after the opening paragraph:

> Identify the source-backed nonpartner condition factors relevant to the selected comparison and their reported levels before calling coverage complete. Complete coverage requires a nonempty selected factor set with known levels; do not invent factors or assume that unreported attributes match. Keep the intended partner change separate from these factors so its presence or absence is not penalized as a nonpartner difference. When condition matching is incomplete, mark coverage partial or unreported and retain the native rates with the specific unresolved comparison. Retain known selected factors under partial coverage; use unreported only when no factors are selected. An unreported selection does not establish that the publication omitted those conditions. A matched comparison is conditional on this supplied scope; it is not a global validity or purity proof.

> Identify the actual measured molecular species and endpoint, and establish each added component's role from the source. A primary reaction participant or carrier differs from an enzyme that generates a reporter or coupled signal. Reporter dependence alone establishes neither physiological partner necessity nor isolated intrinsic activity of the assayed subject. Keep the studied molecule's source organism, expression host and accessory-component source distinct. Equal units or a shared paper do not establish shared molecular identity, biological origin or assay role.

The existing relationship paragraph now also says:

> Preserve source-established physical measurement identity across contrasts: a reused reference is shared evidence, not an independent experiment. A baseline measurement reused as addback is not a separately observed restoration; a missing addback remains unknown.

The complete numerical sheet was not inserted into the prompt. The existing
schemas, component list, formulas, readers, storage, return contracts, renderer,
episode binding and continuation implementation were not edited. The prompt
instructs scientific interpretation; calculators retain their existing
deterministic responsibilities. No pseudoquality grade, probability or target
transfer calculation was added.

## Decision and information trace

| Responsibility | Inspected path and resulting behavior |
| --- | --- |
| Investigation owner | `LiteratureEpisodes.instructions` and `decision_context` preserve the child's assigned question and scoped iterative choices. `literature_experimental_prompt._task` appends the complete literal PARTNER_TASK on every literature decision, unless already present in supplied instructions. The new paragraphs explain how to interpret the selected experiments; they prescribe no child itinerary. |
| Selected action | The episode supplies actual source spans, molecular/endpoint meanings, physical-measurement witnesses, selected condition factors and coverage through `literature.partner.source.populate`. The intended partner state remains a separate arm field. The condition list therefore describes nonpartner factors. This is instructional guidance, with no new automatic action or runtime gate. |
| Deterministic components | The existing native reader verifies selected bytes, parses supported number/unit tokens and passes the established input shape to `populate_partner_components`. Partial or unreported coverage preserves native rates while the relevant contrast is unavailable. Existing validation already requires known nonempty factors for complete coverage and no selected factors for unreported coverage. No factors are invented by this change. |
| Durable state | `LiteraturePartnerRepository.populate` preserves selected arguments, source witnesses, native evidence, physical-measurement identities, numerical inputs and calculated cells. Saved reads validate and project the original material without rereading scientific sources or rerunning calculations. A reused baseline cannot become a distinct addback through this guidance. |
| Parent/child return | `_rate_facts`, `partner_cells_schema`, report validation, admission and received-cell projection preserve exactly requested numerical rows and limitations. The source-evidence parent retains REFERENCE_PARENT_TASK. Its STEERING renders admitted partner comparison checks, coverage, actual source meanings and unavailable reasons. PARTNER_TASK is not injected into the parent's task. |
| Lookup and reconstruction | `_SessionConnection._presentation` reconstructs bootstrap/delta state and rerenders the whole task after information lookup. The compact profile appends only requested operation-contract text to TASK; it does not replace scientific instructions. Cold bootstrap receives the same complete partner guidance and answered lookup information. |
| Implementation identity | `LiteratureEpisodes.as_record` already includes `literature_partner_prompt.py` bytes in its implementation digest. `compose_episode_bindings` compares the complete descriptor. A descriptor constructed with the exact pre-edit prompt is rejected against current bytes; a newly captured current descriptor reconstructs exactly. Historical descriptors and runs were not changed. |
| Credit and continuation | Existing ordinary selected-action accounting and the configured controller remain responsible. The synthetic workflow performs four completed actions: root commission, child population, child reasoning and root reasoning. It records four runtime observations and one population operation, with no extra observation for extraction, arithmetic, transport or rendering. Its fixture scientific credit remains zero. |

## Reads

Complete authority reads: root `AGENTS.md`, the immutable originally supplied
goal attachment, the W04 evidence-axis amendment, `TASK_AND_STEERING.md`,
`EPISODE_STRUCTURE.md`, and `TIME_AWARE_ESTIMATION.md`. `GOAL.md` was not read.

Complete implementation reads: `literature_partner_prompt.py`,
`literature_partner_inputs.py`, `literature_partner_native_inputs.py`,
`literature_partner_calculations.py`, `literature_partner_storage.py`,
`literature_partner_source_fields.py`, `literature_partner_defined_units.py`,
`literature_partner_operand_information.py`, `literature_episodes.py`,
`literature_experimental_prompt.py`, `literature_reference_parent_prompt.py`,
`episode_bindings.py`, `episode_composition.py`, `decision_context.py`,
`composition_information.py`, and `episode_contract_information.py`.
The complete `_SessionConnection` implementation in `providers.py`, including
`complete` and `_presentation`, and the complete `text_instructions` helper in
`scientific_process_prompt.py` were read. Full provider/runtime files beyond
these receiving paths were not reviewed as part of this prompt-only change.

The complete partner legacy/native integration tests and experimental prompt
delivery tests were read. Relevant synthetic fixture, shared-measurement,
operand-binding, compact-presentation and read-only reconstruction tests were
also inspected before their selected checks were run.

## Verification

`tests/test_literature_partner_interpretation_task_160.py` adds six synthetic
checks (five test functions, including two coverage cases). They establish:

- The complete scientific partner instructions recur through bootstrap, delta,
  own-information lookup and cold restoration, without a narrative history dump.
- The actual partner-operation contract lookup in the current compact profile
  preserves the scientific TASK and puts its requested contract text in TASK.
- Partial coverage retains known selected factors. Unreported coverage with no
  selected factors retains native rates and explicit unavailable contrasts.
- A binding constructed with the exact original prompt bytes fails descriptor
  reconstruction against the changed prompt; a current descriptor restores.
- Actual ordinary child/parent transport retains child assignment and return
  purpose, recurring child TASK, the parent's own TASK, requested partial cells,
  source meanings and one observation per completed own action.

The final focused command selected this new file and seven existing test nodes:

```text
.venv/bin/pytest -q \
  tests/test_literature_partner_interpretation_task_160.py \
  tests/test_literature_partner_calculations.py::test_baseline_copy_cannot_manufacture_an_addback \
  tests/test_literature_partner_calculations.py::test_missing_addback_preserves_the_two_arm_contrast \
  tests/test_literature_partner_calculations.py::test_same_physical_measurement_is_not_an_independent_role \
  tests/test_literature_partner_calculations.py::test_one_sided_condition_factor_is_missing_information_not_a_difference \
  tests/test_literature_partner_operand_bindings.py::test_actual_typed_subset_next_decisions_and_first_readonly_reconstruction \
  tests/test_literature_partner_integration.py::test_partner_task_repeats_after_lookup_delta_and_reconstruction \
  tests/test_literature_partner_native_integration.py::test_native_task_repeats_across_lookup_and_restoration \
  --junitxml=verification/literature_reference_evidence_2026-10-25_001/a105_partner_interpretation_task_160/TEST_RESULTS_003.xml
```

Result: **14 passed in 20.10 s**. The one-sided-scope node contains two cases.
The existing read-only reconstruction check disables original-source acquisition
and the partner reader, and rejects writes while projecting the original
admitted subset. This is a synthetic engineering check.

Earlier overlapping results are not additional unique coverage: initial five
new checks passed in 11.35 s; a 13-check group passed in 21.10 s before the compact
lookup check was added. `TEST_RESULTS_001.xml` preserves a collection error from
a mistyped existing node; that attempt ran zero tests. The corrected groups are
preserved as `TEST_RESULTS_002.xml` and `TEST_RESULTS_003.xml`.

`AFTER_001.json` confirms that only the partner prompt changed among the 14
tracked existing files. The three closed argument/return schemas have the same
pre/post fingerprint. Fresh descriptor configuration is unchanged; its
implementation fingerprint changes as intended. These counts describe one
prompt module, existing numerical components and engineering tests, not new
assay graders.

## Limits

Controlled transport responses establish delivery of instructions, not that a
configured model makes the intended scientific distinctions on a real paper.
No primary-source scientific extraction or selected actual-model investigation
was run. The closed contract gains no new dedicated biological-role,
organism/host/accessory-origin, or cross-sheet independence fields. Its original
scientific interpretations and source-backed identities retain their existing
meanings. The prompt cannot turn a supplied-scope matched comparison into a
global validity, purity, mechanism or physiological-necessity proof. Full A105,
the larger original literature goal, A106, W05 and final annotation credit are
not declared complete by this increment.
