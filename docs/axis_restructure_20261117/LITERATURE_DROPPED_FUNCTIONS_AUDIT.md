# Literature chain: functions dropped by the carry-over (audit, 19 November 2026)

Read-only audit. Nothing in an episode or in the library was changed. Method: the `TOOLS = {...}` table of each
current `task.py`, compared with the episode's own files at `97308b94c` (`git show 97308b94c:<path>`, the episode
folders only; the old shared root was not read). No Python was run.

Two parts:

1. The literature chain of A101, A102, A103, A104, A106, A107, A108 and A110 (seven episodes each, 56 episodes), with
   A105 as the reference of a complete chain.
2. Addendum (coordinator's request): every episode of every kind that has or had a `reason` tool, and who reads the
   records its commit writes.

Short names used below: PEA = `published_evidence_assessment`, ESSI = `evidence_search_strategy_improvement`,
SRA = `source_relevance_assessment`, SEE = `source_evidence_examination`, PEE = `passage_evidence_extraction`,
SCI = `source_coverage_improvement`, TEE = `table_evidence_extraction`. Every axis has all seven; the chain is
PEA > ESSI > SRA > SEE > {PEE, SCI, TEE}.

## How "had a reasoning commit at 97308b94c" was decided

At `97308b94c` every literature episode declared two things in its own files:

- `permitted_common_actions`: the kinds of action the model could select. `'reason'` in the returned tuple means the
  episode offered a reasoning commit.
- three hooks, `reasoning_action_schema`, `reasoning_has_task_content`, `execute_reasoning`.

The reference, A105, returned `('tool', 'reason', 'child', 'redeliver_report')` (old `task.py:8-10`, SEE `task.py:9-11`).

| axis | old `permitted_common_actions` (same in all seven) | old hooks | had `reason` |
|---|---|---|---|
| A101 | `('tool', 'child', 'redeliver_report')`, `source_operations.py:7-9` | `source_operations.py:11-18`: schema returns `None`, has-content returns `False`, execute raises `a101_literature_reasoning_not_commissioned` | no |
| A102 | `('tool', 'reason', 'child', 'redeliver_report')`, `episode.py:77-79` (SEE `:81-83`, leaves `:76-78`) | `source_interpretation.py:7,16,26`: source-lead schema, lead check, `store.commit_reasoning` plus `validate_lead` | yes |
| A103 | `('tool', 'child', 'redeliver_report')`, `action_policy.py:13-15` | `source_interpretation.py:7-14`: `None`, `False`, raises `a103_literature_reasoning_not_commissioned` | no |
| A104 | `('tool', 'reason', 'child', 'redeliver_report')`, `role_policy.py:11-13` | `scientific_interpretation.py:12,23,33`: lead schema, required grading (`_required_grading_logic`) or `store.commit_reasoning` | yes |
| A105 (reference) | `('tool', 'reason', 'child', 'redeliver_report')`, `task.py:8-10` | in `grading/` of each episode | yes |
| A106 | `('tool', 'reason', 'child', 'wait', 'redeliver_report')`, `source_operations.py:7-9` | `source_operations.py:11,22,33`: lead schema, required grading or `store.commit_reasoning` | yes |
| A107 | `('tool', 'child', 'redeliver_report')`, `episode.py:41-43` | `configuration.py:28-35`: `None`, `False`, `None` | no |
| A108 | `('tool', 'reason', 'child', 'redeliver_report')`, `source_operations.py:7-9` | handled in old `task.py:93-157` (default `store.commit_reasoning`, required contextual grading) | yes |
| A110 | `('tool', 'child', 'redeliver_report')`, `episode.py:49-51` | `configuration.py:28-35`: `None`, `False`, `None` | no |

**Correction to the starting assumption.** The seven A101 literature episodes did not lose a reasoning commit. Their
old `source_operations.py` has the three hook functions, but as an explicit refusal: no `'reason'` among the permitted
actions, no schema, and `execute_reasoning` raises `a101_literature_reasoning_not_commissioned`. A103 is the same
(`a103_literature_reasoning_not_commissioned`). What these episodes had instead was the `report_update` field of every
decision (old PEA `task.py:100,145`), which the current `report` tool replaces. The reason their credit stays at 0
is given in the notes: their credit reads records that no tool of theirs writes, then or now.

## Table 1: the literature chain

"Tools now" is the number of entries in the current `TOOLS` table. "Credit reads commit-written records" means: the
current `credit.py` counts records that only a reasoning commit or a grader writes.

| axis | episode | tools now | `reason` now | `reason` at 97308b94c | credit reads commit-written or grader-written records | other tools of the old surface missing now |
|---|---|---|---|---|---|---|
| A101 | PEA | 23 (`task.py:440`) | no | no | yes: alignment observations selected by held assessments (`credit.py`, library `grading/sequence_alignment/native_correspondence.py:35-52,79`); no tool of the episode writes either | none |
| A101 | ESSI | 23 (`task.py:432`) | no | no | same | none |
| A101 | SRA | 23 (`task.py:436`) | no | no | same | none |
| A101 | SEE | 16 (`task.py:434`) | no | no | same | none |
| A101 | PEE | 16 (`task.py:352`) | no | no | same | none |
| A101 | SCI | 16 (`task.py:359`) | no | no | same | none |
| A101 | TEE | 16 (`task.py:365`) | no | no | same | none |
| A102 | PEA | 35 (`task.py:588`) | yes (`task.py:545`) | yes | yes: validated leads, `no_applicable_evidence` spans and retained assessments, all written by `reason` (`credit.py` `answers`) | none |
| A102 | ESSI | 35 (`task.py:588`) | yes (`:545`) | yes | same | none |
| A102 | SRA | 35 (`task.py:597`) | yes (`:554`) | yes | same | none |
| A102 | SEE | 17 (`task.py:501`) | yes (`:458`) | yes | same | none |
| A102 | PEE | 17 (`task.py:472`) | yes (`:429`) | yes | same | none |
| A102 | SCI | 17 (`task.py:472`) | yes (`:429`) | yes | same | none |
| A102 | TEE | 17 (`task.py:475`) | yes (`:432`) | yes | same | none |
| A103 | PEA | 24 (`task.py:271`) | no | no | yes: context attachments and measurements selected by held assessments (`credit.py`, library `grading/gene_context_evidence/credit.py:19-36,77`); no tool of the episode writes either | none |
| A103 | ESSI | 24 (`task.py:269`) | no | no | same | none |
| A103 | SRA | 24 (`task.py:281`) | no | no | same | none |
| A103 | SEE | 17 (`task.py:275`) | no | no | same | none |
| A103 | PEE | 17 (`task.py:219`) | no | no | same | none |
| A103 | SCI | 17 (`task.py:219`) | no | no | same | none |
| A103 | TEE | 17 (`task.py:249`) | no | no | same | none |
| A104 | PEA | 34 (`task.py:721`) | yes (`:686`) | yes | yes: leads, `no_applicable_evidence` spans, retained assessments, written by `reason` | the population tools, see note A104 |
| A104 | ESSI | 34 (`task.py:698`) | yes (`:663`) | yes | same | same |
| A104 | SRA | 34 (`task.py:726`) | yes (`:691`) | yes | same | same |
| A104 | SEE | 16 (`task.py:633`) | yes (`:594`) | yes | same | same |
| A104 | PEE | 16 (`task.py:607`) | yes (`:568`) | yes | same | same |
| A104 | SCI | 17 (`task.py:268`) | yes (`:239`) | yes | same | same |
| A104 | TEE | 16 (`task.py:547`) | yes (`:519`) | yes | same | same |
| A106 | PEA | 77 (41 written out + 36 population names, `task.py:856-859`) | yes (`:641`) | yes | yes: leads, `no_applicable_evidence` spans, retained assessments, written by `reason` | `wait` (old `source_operations.py:9`, `waiting.py:8`) |
| A106 | ESSI | 76 (`task.py:738`) | yes (`:561`) | yes | same | `wait` (same lines) |
| A106 | SRA | 76 (`task.py:736`) | yes (`:559`) | yes | same | `wait` |
| A106 | SEE | 54 (`task.py:600`) | yes (`:422`) | yes | same | `wait` |
| A106 | PEE | 54 (`task.py:531`) | yes (`:497`) | yes | same | `wait` |
| A106 | SCI | 54 (`task.py:531`) | yes (`:497`) | yes | same | `wait` |
| A106 | TEE | 54 (`task.py:535`) | yes (`:501`) | yes | same | `wait` |
| A107 | PEA | 24 (`task.py:341`) | no | no | grader-written only: the partner sheets its two populate tools save (`credit.py`: `summary['partner_sheets']`); both tools are in the table | none |
| A107 | ESSI | 24 (`task.py:351`) | no | no | same | none |
| A107 | SRA | 24 (`task.py:366`) | no | no | same | none |
| A107 | SEE | 4 (`task.py:285`) | no | no | same | 13 access tools, see note A107 |
| A107 | PEE | 4 (`task.py:188`) | no | no | same | same 13 |
| A107 | SCI | 4 (`task.py:188`) | no | no | same | same 13 |
| A107 | TEE | 4 (`task.py:188`) | no | no | same | same 13 |
| A108 | PEA | 25 (`task.py:625`) | yes (`:586`) | yes | yes: leads, `no_applicable_evidence` spans, retained assessments, written by `reason` (which also saves the grading sheet) | `material.annotations`, `material.parse`, `material.from_source`, `public.uniprot.search`, `public.uniprot.record`: not determinable, see note A108 |
| A108 | ESSI | 25 (`task.py:625`) | yes (`:586`) | yes | same | same five |
| A108 | SRA | 25 (`task.py:625`) | yes (`:586`) | yes | same | same five |
| A108 | SEE | 16 (`task.py:610`) | yes (`:571`) | yes | same | the three `material.*` |
| A108 | PEE | 16 (`task.py:549`) | yes (`:517`) | yes | same | the three `material.*` |
| A108 | SCI | 16 (`task.py:556`) | yes (`:520`) | yes | same | the three `material.*` |
| A108 | TEE | 16 (`task.py:578`) | yes (`:539`) | yes | same | the three `material.*` |
| A110 | PEA | 35 (`task.py:443`) | no | no | yes: retained assessments (`credit.py`: `finding_progress_credit` over `summary['known_assessment_refs']`); no tool of the episode writes one, a saved reaction sheet earns nothing by itself | none |
| A110 | ESSI | 35 (`task.py:443`) | no | no | same | none |
| A110 | SRA | 35 (`task.py:443`) | no | no | same | none |
| A110 | SEE | 17 (`task.py:402`) | no | no | same | none |
| A110 | PEE | 18 (`task.py:376`) | yes (`:369`) | no | yes, and its own `reason` writes them | none |
| A110 | SCI | 18 (`task.py:376`) | yes (`:369`) | no | same | none |
| A110 | TEE | 18 (`task.py:383`) | yes (`:376`) | no | same | none |

Reference, A105 (already fixed): PEA, ESSI, SRA 64 tools; SEE, PEE, SCI 46; TEE 11; all seven have `reason`
(SEE `task.py:379`, table `:576-617`), which commits the interpretation with its grading sheets and then classifies
the unknown fields of each sheet (`credit.classify_unknowns`); credit reads the sheets and the classification.

### Result in one paragraph

No literature episode of these eight axes lost a `reason` tool that it had at `97308b94c`: the four axes that had one
(A102, A104, A106, A108) still have it in all seven episodes, and the four that did not (A101, A103, A107, A110) had
it explicitly switched off in their old files. Three A110 leaves gained one. The credit problem is separate from a
dropped tool: in A101 (7 episodes), A103 (7) and A110 (PEA, ESSI, SRA, SEE) the current credit counts records that
none of the episode's own tools can write.

## Notes per axis

**A101.** Old tools: `_ACCESS_TOOLS` (15, old `source_contracts.py:23`) for all seven and `_ACQUISITION_TOOLS` (7,
`:24`) for PEA, ESSI, SRA (old `source_operations.py:24-25`). All are in the current tables. `report` is new and
writes no record (PEA `task.py:434-437` returns `{'report': arguments}`). Every current docstring says "The episode
has no reasoning commit" and that the old shared text about reasoning commits "described actions this episode does not
have and is not sent". The credit is the native sequence correspondence of held alignment observations that a held
assessment of the proposed annotation selects. Alignments come from the homology tools and assessments from a
reasoning commit; a literature episode has neither, so its credit can only come from records its parent hands down
(the brief at PEA `task.py:250-253` tells the model that reading and searching earn nothing). This was also true at
`97308b94c` as far as the episode's own files show (credit was `services.scientific_credit`, old shared root, not
read).

**A102.** Old tools: 15 access, 7 acquisition plus the experiment-database tools (names imported from the old shared
root, `source_contracts.py:29`, not read; 11 of them are in the current table), `literature.structure.populate` when
`structure_population` is set (`source_operations.py:26-31`). All present now (`structure_populate`). The docstrings
of the three leaves say "The old `report` tool is gone: the return is controlled features read by code from the saved
sheets". Credit raises `literature_task_kind_not_carried` for any task kind other than `verified_source_leads` and
`source_answer` (assessment, screening).

**A103.** Old tools: 15 access (old `source_contracts.py:23`), plus 7 acquisition for PEA, ESSI, SRA. All present.
`tool_catalog` and `report` are new; `report` writes no record. PEA's docstring: "The episode has no reasoning commit
and no wait (the old `source_interpretation.py` raised `a103_literature_reasoning_not_commissioned`; `waiting.py` had
`supports_wait = False`)". Credit reads held context attachments and measurements selected by held assessments; the
episode's tools write none of them.

**A104.** The old catalogue added population tools when `rate_population` was set (old `source_catalog.py:27-32`;
the flag defaults to `False`, `configuration.py:7`). The names are in old `source_operations.py:18` (35 names:
`literature.concentration_window.populate`, `literature.measurement_comparison.populate`,
`literature.product_coupling.populate`, `literature.measurement_validation.populate`,
`literature.ion_discrimination.populate`, `literature.channel.populate`, `literature.assay.components.populate`,
`literature.calibration.recovery.populate`, `literature.rate.observations.populate`,
`literature.rate.replicates.populate`, `literature.rate.populate`, `literature.rate.source.populate`,
`literature.quantity.populate`, `literature.assay.populate`, `literature.ratio.populate`,
`literature.ratio.source.populate`, `literature.binding.populate`, `literature.binding.model.populate`,
`literature.transport.response.populate`, `literature.figure.populate`, `literature.amount.populate`,
`literature.completion_time.populate`, `literature.active_site.populate`, `literature.product_partition.populate`,
`literature.optical.populate`, `literature.kinetic.populate`, `literature.kinetic.model.populate`,
`literature.binding.interaction.populate`, `literature.binding.interaction.model.populate`,
`literature.controlled_response.source_v3.populate`, `literature.gel.populate`, `literature.parent_depletion.populate`,
`literature.stoichiometric_balance.populate`, `literature.assay_grading.populate`, `literature.a105.aggregate`). None is
in a current A104 table. Whether the old A104 run turned the flag on is not determinable from the episode's files.
The current docstrings say so openly: "The rate-population route of the old episode (rate_population and its populate
tools, the required assay-grading logic of evidence_grading.py) is not carried (no population tool); its required
assay grading is the reason unit". SCI alone has `tool_catalog`. The credit docstring adds that the three A105 task
kinds (`source_answer` measurement, `a105_experiments`, `a105_assembly`) "raise where the count would be made".

**A106.** The 36 population names of the old catalogue (old `source_contracts.py:40`) equal the 36 names of the
library's `POPULATION_OWNERS` (`literature/storage/literature_repositories.py:61-99`), which every current table
includes. `literature.intervention_analysis.contract` was offered by PEA only (old `source_operations.py:81`) and PEA
still has it. `literature_a106_score_judgment` and `open_population` are new. The one thing missing is `wait`: all
seven old episodes permitted it (`source_operations.py:9`) and had `supports_wait` return `True` (`waiting.py:8`);
the current docstrings say "The old `wait` and `redeliver_report` actions are not carried (a child completes inside
the unit that commissioned it)".

**A107.** PEA, ESSI, SRA: 15 access + 7 acquisition + 2 partner populate tools then and now (the old
`EXPERIMENT_DATABASE_TOOLS` was empty, `contracts.py:30`). SEE, PEE, SCI, TEE had the 15 access tools and the two
populate tools (old `source_operations.py:12,26`); they now have `source_read`, `source_locate` and the two populate
tools. Missing (old `contracts.py:31`): `state.query`, `source.sequence.scan`, `source.sequence.references`,
`source.experimental.records`, `image.view`, `source.archive.members`, `source.archive.extract`, `source.xlsx.sheets`,
`source.xlsx.rows`, `source.pdf.info`, `source.pdf.text`, `source.pdf.page`, `execution.estimate`. The docstrings say
it: "The other access tools of the old catalogue (state, sequence, archive, workbook, PDF, image operations) ran
through the A107 tool registry, which is not carried (`AXIS_WAVE_BLOCKERS_a107.md`); they are not offered." Credit
counts partner sheets, which the populate tools write, so credit can move. The credit docstring: "the axis's
finding-progress projector counts retained assessments, which no A107 literature episode writes".

**A108.** Old `_A108_ACCESS_TOOLS` (`source_contracts.py:23`) names 16 tools and `_A108_ACQUISITION_TOOLS` (`:24`)
names 11. Five names are not in the current tables: `material.annotations`, `material.parse`, `material.from_source`
(all seven) and `public.uniprot.search`, `public.uniprot.record` (PEA, ESSI, SRA). The old catalogue offered a name
only when the tool registry also had it (`source_operations.py:13-20`), and the registry was in the old shared root,
so whether the model ever saw these five is not determinable. The current comment (PEA `task.py:78-80`) says the
three `material.*` names are "a name the library does not offer"; nothing is said about the two `public.uniprot.*`
names. The two population tools (`literature.a108_grading.populate`, `literature.a108.aggregate`) are present.

**A110.** Old tools: 15 access, 7 acquisition plus the experiment-database tools for PEA, ESSI, SRA, and
`literature.reaction.populate`, `literature.reaction.source.populate` for all seven (old `source_operations.py:12-13,
26-31,39`). All present. PEA's docstring: "The old permitted common actions were tool, child and redeliver_report (no
reasoning action, so there is no reasoning tool here)". The credit of all seven counts retained assessments and says
"a saved reaction sheet by itself earn[s] nothing". PEE, SCI and TEE now have `reason` and can write assessments.
PEA, ESSI, SRA and SEE cannot: their `known_assessment_refs` (SEE `messages/internal_summary.py:44`,
`view.records.list('assessment')`) fills only from what children return, so their own populate tools never earn
credit.

**All axes.** `redeliver_report` was a permitted action of every old literature episode and is in no current table;
the current docstrings call it old-runner machinery.

