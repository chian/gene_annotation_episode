# A105 experiment SOP: adding a sheet class and its experiment types

Written 2026-11-21 from the code as it stands and from the conversation traces. It covers how the 25 `ligand_binding`
types (spr ... proximity) were built, written so that the other seven classes (`activity_rate`, `endpoint_conversion`,
`product_distribution`, `reaction_coupling`, `transport_response`, `protein_signal`, `protein_amount`) can be added
the same way, **one experiment type at a time**. The worked examples are **SPR**, which is quantitative, and
**pull-down/co-IP** (`pulldown`), which is qualitative.

Path abbreviations used below:

| Name | Path |
| --- | --- |
| `EP` | `gene_annotation_episode/episodic_workflow` |
| `G` | `EP/episode_support/literature/grading/experimental_activity_evidence` |
| `F` | `EP/episode_support/literature/forms/experimental_activity_evidence` |
| `PAGE` | `EP/root/a105/experimental_activity_evidence/literature/strategy/web_search/page` |
| `LEAF` | `PAGE/chunk`, the extraction leaf. The `table` and `report` leaves pick their types from `F` `FORMS`. |
| `<t>` | The experiment type, a value of `EXPERIMENT_TYPES` |
| `<m>` | Its module suffix. It is usually `<t>`, but `alpha` for `alphascreen` and `trp` for `trp_quenching`. |

**Declared up front: how the owner's "no hard-coded thresholds" rule is applied (step 3).** The values in the
converters (for example `G/literature_spr_converter.py` `MIN_CONCENTRATIONS=5`, `LOW_FACTOR`, `CHI2_OVER_RMAX_MAX`;
`G/literature_pulldown_converter.py` `MIN_WASH_NACL_MM`, `MIN_REPLICATES`) were RESEARCHED per assay: each is what is
generally reasonable for that method, with its reason in the comment. They are KEPT. What the rule removes is a hard
pass/fail cut-off at such a value: each researched value becomes the centre or scale of a GRADUAL curve, so assay
quality can vary around it. The per-type `QUANTITATIVE_STRENGTH_ANCHORS` (the noise end and strong end of each
method's constant) are owner-approved ends of a gray scale and stay. Never replace researched values with a generic
formula used for every assay (a 2026-11-21 pass did exactly that, `d = n/(n+1)` everywhere, and was reverted).

---

Trace references ("line N") are line numbers of
`/home/chia/.claude/projects/-home-chia-repos-gene-annotation-episode/6505138e-b5fa-4641-9b42-c1589dca8429.jsonl`.

## Step 0. Per class: the inventory protocol, the predicate and the experiment list

### 0a. How the binding list was actually obtained (recovered from the traces)

The coordinator relayed that the list was "built with the owner through a protocol". The traces show something
narrower, and the difference matters for the other seven classes:

| When (trace `6505138e-...jsonl` line, UTC) | What happened |
| --- | --- |
| 34847 (2026-11-20 01:52) | Owner: "I had you read like 150 papers to group together and list out all experiments that exist." That earlier work was done with Codex in October. |
| 34850-34985 | The agent searched `research/experimental_scoring_review_2026-10-23/` (`SYNTHESIS.md`, `EMERGING_LANES.md`, `a105_complete_deliverable_022/A105_NUMERICAL_SCORING_SHEET_001.md`, built from 142 groups and 149 records). That material is clustered by calculation route, not by experiment type. Owner at 34950: "don't get poisoned by the old stuff." |
| **35001 (01:56:49)** | **The owner pasted the binding list** ("Label-free biophysical methods ... SPR ... Proximity labeling"), saying the methods "all have their own metrics of goodness, controls, measurement technique, noise expectations, number of replicates needed, and certainty". This is the first occurrence of the list in any Claude trace. A grep of the five other `.jsonl` sessions under `-home-chia-repos-gene-annotation-episode*` returns zero hits for "surface plasmon" or "microscale thermophoresis". **The traces do not show where the owner got the pasted list.** |
| 35030 (02:00) | Owner: "I want a system for doing this. Either from the past list or in the future ... I kind of would like not to redo that massive amount of work ... prefer you find it." |
| 35045, 35297, 35337 | Read-only finder agents searched the research folders, the docs, `verification/`, git history and the Codex sessions under `/home/chia/.codex/sessions/2026/10/` (`01a17595`, `01a189c4`, `01a18ef4`). Result: `docs/axis_restructure_20261117/EXPERIMENT_INVENTORY_SEARCH.md` and `EXPERIMENT_INVENTORY_SEARCH_2.md`. **No per-technique list or per-technique criteria was found.** The nearest finds were the Codex 6+2 family roster (`verification/a105_sheet_reader_inventory_315/`), the enzyme-assay audits (`verification/biochemical_assay_guides_318/`, `verification/biochemical_fourteen_graders_319/`) and the owner's own biochemical questions (`..._SEARCH_2.md` section 2(c)). |
| 35340 (02:09) | Owner: start with one slice, "find out what questions you need to ask me ... you can use that list to help you build." |
| 35396 | SPR build prompt. The coordinating agent drafted the SPR criteria in the prompt itself ("SPR criteria to draft (the owner will correct them)") and pointed to the PopZ case in the owner's review folder as the real published case. |
| 35545 (02:21) | Owner: "I would not know how to correct criteria and thresholds. What's important is that they are a refactored part of the code put in the appropriate places so they can be read by human programs and fixed alongside experts." |
| 35587 | Owner: "the extraction output should match what the SPR grader needs." |
| 36015, 36033 (04:18) | `/goal`: build every type on the list one at a time "the way SPR was done". The agent finds a published paragraph per technique itself through public literature search and names the paper. |
| 36651 (pulldown), 38159 (DSF) and the others | For each type, the coordinating agent wrote the type's domain notes (what it reports, its controls, its artefacts) into a build prompt. The build agent decided the record fields and criteria and found a real CC-BY or CC0 open-access paragraph through Europe PMC full-text XML, recording the PMC id, licence and verbatim text. |
| 37089, 37189, 37303, 37317, 37592, 37607, 39922, 40572, 44739, 50215 | Owner corrections from reviewing results. Each one became a general rule, applied to every type by parallel agents (37570-37576 moved thresholds to the sheet side; 37779-37785 added quote support). |

So the protocol the traces support is the following. Repeat it per class:

1. **Search for prior work first, read-only.** Ask the owner where it lives. Search `research/experimental_scoring_review_*`,
   `verification/` (for enzyme classes: `biochemical_assay_guides_318`, `biochemical_fourteen_graders_319` and
   `a105_sheet_reader_inventory_315/SHEETS.tsv`), the `docs/axis_restructure_20261117/EXPERIMENT_INVENTORY_SEARCH*.md`
   files, git history, and the Codex session files (grep only, never cat). Write the findings to one search file.
   Use old material for knowledge only and keep the current paradigm ("don't get poisoned").
2. **Get the class's experiment list.** If the owner supplies one, as for binding, it is the definition. If not,
   draft it from the sources found and domain knowledge, and mark it a **draft for the owner to correct**. One entry
   per protocol that can be reapplied to anything, not per paper or per case. This follows the owner's Codex-era
   rule, quoted in `..._SEARCH_2.md` section 2(d).
3. **For each type, fill the template below.** Where the owner gave questions, use them. For example, the owner's
   biochemical questions are sensitivity, kinetic parameters, conditions (temperature, in vitro or in vivo, realism
   of the chemistry), expected signal in messy samples, and a control for spontaneous reaction. The criteria are
   drafted by the agent and corrected later by the owner and experts. They must be readable in one declaration file
   (step 2).
4. **Find one real published paragraph per type** (step 6) before the type counts as built.
5. **Owner review of the real results.** Each ruling becomes a general change applied to all types of the class,
   not a per-type patch.

### 0b. The class's claim predicate

- **File:** `G/literature_row_contract.py`.
  - Add the class's predicate or predicates to `CLAIM_PREDICATES_BY_CLASS`. This is the marked EXTENSION POINT;
    today it holds only `'ligand_binding': ('binds',)`.
  - Add a predicate to `SYMMETRIC_PREDICATES` only if "A p B" is the same as "B p A". `binds` is symmetric.
    Predicates like `catalyzes` and `transports` are not.
  - A claim names molecules only (`CLAIM_FIELDS`: `predicate`, `subject_id`, `partner_id`). It never carries a
    threshold or a physical prediction (OWNER_DECISION 1).
- **Proposals only, for the owner to confirm:** `activity_rate` and `endpoint_conversion` use `catalyzes`;
  `transport_response` uses `transports`. No proposal is made for `protein_signal` and `protein_amount`.
- **Check that the hypotheses fit.** `G/literature_claim.claim_of_hypothesis` accepts only a hypothesis whose value is
  a `term_ref` or `reference` (the partner). A class whose hypotheses carry another value type, such as an amount
  or an enum, cannot be read into a claim today. Raise this with the owner and do not patch it silently.
- **Acceptance:**
  - `G/literature_page_update._check_claims` accepts a claim with the new predicate and maps it to the class.
  - `G/literature_bearing.bearing` returns `direct` for a record of a type of the class whose `target_id` equals the
    claim's subject.

### 0c. The class's decisions to make before the first type

Read these from the code; each can need an owner decision:

| Code | What to check |
| --- | --- |
| `G/literature_assay_grading.py` `QUANTITY_KINDS[<class>]` and `CRITERIA_BY_TYPE[<class>]` | The quantity kinds and the sheet criteria a converter of this class must fill. Example for `activity_rate`: `COMMON_CRITERIA` plus `rate_regime`, `normalization_basis`, `kinetic_model`, `partner_perturbation`. |
| `QUALITATIVE_STATEMENT` | Values are `interaction_detected`, `interaction_not_detected` and `interaction_not_stated`. They are phrased for binding. Decide whether a qualitative result of the class (activity detected or not, transport detected or not) reuses them or needs new values. Changing them is a contract change, so ask first. |
| `ROLE`, `IMMOBILIZATION_SIDES`, `ROW_DEPENDENCE_KEYS` | These are binding-flavoured: `analyte`, `immobilized`, `surface`. The pull-down maps prey to `analyte_preparation_ref`, bait to `immobilized_preparation_ref`, and `surface_ref` to None. Each new converter maps its own preparations onto these four keys and documents the mapping. |
| The direction of a quantitative effect | `G/literature_direction.strength` assumes the effect is a binding constant in nM, where smaller is stronger, read against per-type anchors. A rate, a fold change or an amount needs its own direction rule under the step 3 owner rule: researched per-method scale ends (like the binding anchors), a smooth monotone curve between them, lowered by the stated spread, unknown when the value is not stated. This change is inside `G`. Write it as a separate, class-scoped function and get the owner's agreement on its form before using it. |

### 0d. The inventory template (the design doc's template, one entry per type)

Fill this in the class's section of `docs/axis_restructure_20261117/A105_SCORING_DESIGN.md`, the way section 6 holds
binding.

```text
experiment:            <name>                       (type id <t>, snake_case, short, as in EXPERIMENT_TYPES)
family:                <technique family>
evidences (sheet):     <class>                      (predicate: <p>)
native outputs/units:  <...>                        (each becomes a record quantity with a unit vocabulary)
controls required:     <...>                        (each becomes a yes/no fact)
noise expectations:    <...>                        (what the paper must state for the sheet to compare against)
replicates needed:     <...>                        (recorded as a count + independence fact; no cut-off)
certainty:             <how its result is bounded>  (quantitative effect, or qualitative detected/not detected)
readers that supply it:<display types>              (today: text and tables only, see Known gaps)
past work (where):     <paper, case record, existing code>
```

**Acceptance for step 0:**
- The predicate is added (and is symmetric only if it truly is).
- The class's list is in the design doc, marked owner-confirmed or draft.
- Every type has a filled template.
- The search file names every place searched and what was or was not found.

---

## Step 1. The record form (`F/literature_<m>_record.py`)

The record is the grader's input and also the extraction's answer form (step 5). Copy the shape of
`F/literature_spr_record.py`, or of `F/literature_pulldown_record.py` for a qualitative type.

### What goes in the record

- **Constants:** `VERSION`, `EXPERIMENT_TYPE`, `QUANTITIES`, `UNITS` (a unit vocabulary per quantity), `FACTS`
  (name to answer set, usually `YES_NO` = yes, no, unknown, not_applicable), plain choice vocabularies, and
  `PREPARATION_KEYS`.
- **Constructors:** `point`, `unavailable` and `fact`. Every stated value carries `support`.
- **Operands** use the shape `{value, unit, status 'point'|'unavailable', reason, measurement_keys, source_refs,
  origin, native_component, support}`. A value not given is `unavailable` with a reason. **It is never 0 and never
  omitted.**
- **Other parts:** `facts` `{answer, source_refs, support}`, `choice_support` for plain choices, `spans`
  `{ref: {locator: 'bytes a-b of the source', quote}}`, and `preparations` (record refs; no passage states them, so
  they stay None).

### Rules

- **Generic shape only.** `G/literature_grader_record.merged_record` merges member leaf records by **structure**
  (`quantities`, top-level operands, choices named in `choice_support`, `facts`, `spans`, `preparations`, identity
  keys). A record outside this shape cannot be merged.
- **One field holds one thing.** The pull-down keeps `fold_enrichment`, `percent_input_recovered` and
  `input_fraction` as separate fields. No free text: names come from fixed vocabularies, and everything else is a
  number, a fact answer or a ref.
- **Record what the class's noise and certainty need for the sheet to judge with same-paper quantities.** Examples:
  the stated spread and its kind (`spread_kind` in SPR), the control value beside the test value, and the series
  next to the constant.
- **Qualitative types** have no constant. The pull-down's statement comes from the fact `prey_detected_in_eluate`.
  Do not invent a constant or force a semi-quantitative number into the effect.

**Acceptance:** `F/tests/test_literature_<m>_extraction.py` (step 5) asserts that the schema holds exactly the fields
of the form and that the vocabularies are the form's vocabularies. Pulldown examples:
`test_the_schema_has_exactly_the_fields_of_the_form` and `test_the_vocabularies_are_the_forms_vocabularies`.

---

## Step 2. The grader: facts only (`G/literature_<m>_criteria.py` and `G/literature_<m>_grader.py`)

### The criteria file

`<M>_CRITERIA` is a tuple of `{id, question, reads, rule, thresholds, returns}`. `returns` lists every
`(status, reason_code, when)` the criterion can produce. The only constants allowed in this file are unit
conversions marked `FIXED_BY_DEFINITION`, for example `NM_PER_M` in SPR, and `MM_PER_UNIT` and `MIN_PER_UNIT` in
pull-down.

### The grader file

- One short function per criterion, in declaration order, listed in `EVALUATORS`, plus
  `grade_<m>(record) -> {version, experiment_type, experiment_ref, criteria: {id: {status, support_refs}}, reasons, native}`.
- Statuses are `supported`, `unknown`, `conflicting` and `not_applicable`. A fact stated as `no` is a fact, and the
  grader may return `conflicting` for it (SPR `fact_answered_no`, pull-down `prey_found_in_negative_control`).
  Silence is `unknown`, never `no`.
- **No threshold and no judgement.** Where a number would be compared with anything, the grader records the number
  and its refs in `native` and returns `unknown` with a reason ending in `_recorded_for_the_sheet`. Pattern:
  `G/literature_spr_grader._concentration_series` records `concentration_count`, `concentration_low_over_kd`,
  `concentration_high_over_kd` and `concentration_refs`. `G/literature_pulldown_grader._recorded` is the generic
  helper.
- A `supported` or `conflicting` result always carries support refs. The pull-down `_result` raises `ValueError`
  without them; copy that guard (SPR's `_result` lacks it).
- `native['support'] = criterion_supports(record, <M>_CRITERIA)` keeps the quote-support class of every field each
  criterion reads. The grader does not judge it.
- A qualitative type also puts its statement in `native`. For pull-down that is
  `interaction = INTERACTION.get(prey_detected_in_eluate)` with `interaction_refs`.

**Acceptance:**
- `G/tests/test_literature_<m>_grader.py` on built records.
- `G/tests/<m>_cases.py` with `test_literature_<m>_real_case.py`: the real published paragraph's record gives only
  the criteria it supports. The pull-down real case asserts exactly four supported facts.
- Add the type to `G/tests/test_literature_criteria_declarations.py`. Its checks: the declaration is complete, the
  grader evaluates exactly the declared criteria in order, every returned `(status, reason)` is declared, and there
  is no inline threshold number in the grader.
- Add the type's criteria to `docs/axis_restructure_20261117/A105_GRADER_CRITERIA_INDEX.md`. The declarations test
  checks the index for some types.

---

## Step 3. The converter: judgement on the sheet side (`G/literature_<m>_converter.py`)

### The converter's output

`convert_<m>(graded) -> {version, experiment_type, experiment_ref, source_ref, dependence, extraction, sheet,
null_components, direction_field_support, [qualitative_effect]}`

- `extraction` is the `grade_assay` input:
  - `assay_type` is the class.
  - `quantity_kind` comes from `QUANTITY_KINDS[class]`.
  - `quantities` uses the `ROLES` keys. `effect` and `effect_variance` are filled only when honestly given; every
    other role is null, with a reason in `NULL_REASONS`.
  - `interpretations` uses `CRITERIA_BY_TYPE[class]` sheet criteria.
- `sheet = grade_assay(extraction)`.
- `dependence` holds the four `ROW_DEPENDENCE_KEYS`.

### The judging mechanism (unchanged from the old converters)

- `JUDGES = {(criterion, '<...>_recorded_for_the_sheet'): judge_fn}`.
- `_criterion(graded, name)` returns the grader's own answer, or the judge's answer when the grader handed the facts
  to the sheet.
- `CRITERIA_MAP` maps each sheet criterion to its member criteria. The rules:
  - any `conflicting` makes the sheet criterion `conflicting`; otherwise any `unknown` makes it `unknown`;
    otherwise it is `supported`;
  - `not_applicable` members are dropped;
  - the degree is the **minimum** member degree.

### OWNER RULE: researched per-assay values, made gradual (the smart way)

This is the procedure. Do it per assay; never apply one formula to every assay.

1. **Research the assay first.** For each criterion, find what is generally reasonable for THIS method (method and
   guideline papers, the assay's own physics; e.g. SPR: analyte concentrations spanning about 0.1x to 10x KD, chi^2
   small relative to Rmax; ITC: the c-value window; pull-down: wash stringency and empty-bait/bead controls). Record
   the value AND its reason and source in the converter (a commented constant marked `EXPERT_REVIEW`, so the owner
   can correct it). The grader stays facts-only: it reports the real value; the converter judges it.
2. **Soften, do not cut.** Turn the researched value into a gradual curve so quality can vary around it:
   - a value at or better than the researched "good" value gives full agreement; it falls smoothly (not as a step)
     towards a researched "no longer meaningful" value, giving partial credit in between (degree in [0, 1]);
   - a lone minimum (for example `MIN_CONCENTRATIONS = 5`) becomes a curve that reaches full credit at the researched
     value and gives partial credit below it, instead of pass/fail;
   - an existing full-agreement to zero-agreement ramp (for example `LOW_FACTOR` 0.2 -> `LOW_ZERO_FACTOR` 1.0) already
     is gradual: keep it.
3. **Directionally correct for this assay:** better quality never lowers the degree, worse never raises it.
4. **Unknown when the paper gives nothing to judge** (the value is not stated); unknown is never opposition.
   How much an unknown criterion still counts is a PER-ASSAY decision, not a global number. The owner's 0.9 was
   reasoned for KD: its reference range is well established even when the paper states little. An assay whose
   readout is only relative, or that needs its own calibration or in-paper controls to mean anything, may deserve
   much less when those are unstated. Record per assay: absolute vs relative readout, what calibration or controls it
   needs, and the resulting weight for an unstated criterion. Decide it yourself by asking the owner's questions and
   writing the answers down: What does the assay actually measure; is the readout absolute or only relative? Is
   there a reference range we would trust if the paper did not state the detail (as for KD)? What does an unstated
   control or calibration do to what the number means: benign typical practice, or uninterpretable? If we assume it
   is fine and are wrong, how badly does the score mislead? Is the answer consistent with how KD was treated? The
   decision follows from the answers; the written chain is what the owner reviews. Never use the
   unknown weight as part of a degree curve (a degree describes the stated value; the weight is for unstated ones).
5. `conflicting` is kept for what the paper itself states or shows against the standard (a fact answered `no`, a
   prey in the negative control, a signal no larger than the paper's own control).
6. **Never** replace a researched value with a generic shape used across assays, and never drop a researched value
   because it is a number. Where the paper's own numbers give a better scale (an effect relative to its own stated
   uncertainty), use them in addition, not instead.
7. **KD strength** keeps the owner-approved per-type `QUANTITATIVE_STRENGTH_ANCHORS` (noise end, strong end): the
   strength rises smoothly between them on the log scale and is lowered by a stated spread. A new type with a
   constant gets researched anchors of its own the same way.

### Consistency rules (the same idea is treated the same way in every assay)

1. **Replicates mean precision** (a mean's standard error goes as 1/sqrt(n)): with independence stated yes, degree =
   min(1, sqrt(n / MIN_REPLICATES)) using the assay's researched minimum; independence not stated: unknown; a stated
   `no` stays the grader's conflicting fact; n >= 1 is never conflicting.
2. **A short series or count is low partial credit, never `conflicting`.** Below the researched minimum (concentrations,
   temperatures, titration points, injections, orientations) the degree falls by the assay's own reasoned shape.
   `conflicting` is only for what the paper states or shows against the standard, or a value at the far zero end of a
   researched ramp.
3. **No unknown weight inside a degree.** A degree describes a stated value; never use any unknown weight as a curve's
   floor, ceiling or factor. Give the curve its own researched ends, or leave the criterion unknown.
4. **No unreasoned new numbers.** A zero end or shape constant added while softening must carry its physics or
   literature reason in its `EXPERT_REVIEW` comment, or be removed.

### Range review (after softening, per assay)

Go through EVERY researched value and curve of the assay and ask the owner's questions, writing the answers in a short
block in the converter docstring:
1. What does this criterion protect against in this assay; what failure does it catch?
2. Is the value general practice for the method (cite a method or guideline paper) or lab/instrument-specific?
3. Should the scale be absolute, or relative to something the paper itself states (the measured constant, the probe or
   protein concentration, the control's signal)? If relative, does the grader collect that fact?
4. If the value is wrong or the paper deviates, how badly does the score mislead, and does the curve's shape reflect
   that (steep where small changes matter, gentle where they do not)?
5. Is it consistent with the other assays (the consistency rules above)?
Update the converter where the answers say so; keep a value the answers support. It may change nothing, or show a new
way to think about the assay; either way the reasoning is recorded. A needed fact the grader does not collect is a
grader gap: list it (adding it changes the grader, form and passages and needs a real-model run, steps 1-7).

### The unknown weight (per assay, per criterion)

Decided with the questions in rule 4 of the owner rule above; the full answer chain per assay is
`docs/axis_restructure_20261117/A105_ASSAY_CALIBRATION_DETAILS.md`. The values live in `G/literature_row_contract.py`:
`WEIGHT_UNKNOWN_BY_TYPE` (the assay default, anchored so SPR is the owner's 0.9) and `WEIGHT_UNKNOWN_BY_CRITERION`
(overrides per sheet criterion where the answers differ within an assay); `weight_unknown(type, criterion)` picks the
override, else the default; `literature_resolution.row_weight` applies it per result. A new type adds its entry to both
(the contract refuses a type without a default). A result with no applicable criterion counts its type's default.

### Quote support, effect support and the qualitative statement

- **Quote support:** each member verdict goes through `literature_quote_support.apply_support(verdict, supports)`,
  as in the pull-down converter. `direct` is 1.0, `implied` 0.7, `about_something_else` 0.3 (`SUPPORT_DEGREE`). The
  weakest factor counts once. Support never changes a status.
- **`direction_field_support`:** the support class of the field that fixes the direction.
  - SPR: `kd['support']` when a KD is given.
  - Pull-down: the support of `prey_in_eluate` when a statement exists.
  - None when the direction is unknown.
  - It is required whenever the direction is known; `literature_direction` raises without it.
- **Qualitative statement:** `qualitative_effect = {statement, support_refs, ...}`, with `statement` taken from
  `QUALITATIVE_STATEMENT`. Detected supports, not detected opposes, not stated is unknown. The magnitude is
  `QUALITATIVE_LOG_RATIO[<t>]`. A type with a qualitative effect fills no `effect`.

**Acceptance:** `G/tests/test_literature_<m>_converter.py` proves, for every judge:
- **Monotone:** a better value never lowers the degree, and a worse one never raises it.
- **Bounded:** the degree is in [0, 1].
- **Unknown, not 0:** with the value not stated, the result is unknown.
- **No step:** around each researched value the degree changes gradually (a value just below the researched one
  gets partial credit, not 0).
- **Values are named:** every number a judge uses is a named, commented `EXPERT_REVIEW` constant with its reason and
  source; no unexplained inline numbers. The grader itself holds no thresholds
  (`test_no_inline_threshold_number_in_the_grader`).
- **Support:** support lowers the degree and never changes a status.
- **Statement:** a qualitative statement maps to the expected `direction_and_ratio`.

---

## Step 4. Registration (each file edited once per type)

| File | Edit |
| --- | --- |
| `G/literature_row_contract.py` | Append `<t>` to `EXPERIMENT_TYPES`. Make `CLASS_OF_EXPERIMENT_TYPE[<t>]` the class: today it maps every type to `ligand_binding` with a comprehension, so make it an explicit mapping. Add `QUALITATIVE_LOG_RATIO[<t>]`, an `EXPERT_REVIEW` magnitude; whether this per-type constant stands under the no-threshold rule is open (see Known gaps). If the type reports a constant, add its researched `QUANTITATIVE_STRENGTH_ANCHORS` entry (noise end, strong end, with the reason), as the binding types have. Add its `WEIGHT_UNKNOWN_BY_TYPE` default and any `WEIGHT_UNKNOWN_BY_CRITERION` overrides, decided with the questions (step 3, "The unknown weight"). |
| `G/literature_populated_grader.py` | Import `grade_<m>` and `_criterion as judge_<m>`. Add both to `GRADERS` and `JUDGES`. |
| `G/literature_page_update.py` | Import `convert_<m>` and add it to `CONVERTERS`. |
| `F/literature_leaf_extraction.py` | Import `literature_<m>_extraction` and add it to `FORMS`. Write `<M>_INSTRUCTIONS` modelled on `PULLDOWN_INSTRUCTIONS` (type description, stated/unavailable rules, "silence is unavailable, not no", exact unit conversion only, "several experiments: the one about the proteins the text is about", support) and add it to `INSTRUCTIONS`. `QUOTE_UNIQUENESS` and `IDENTITY_PARAGRAPH` are appended automatically. |
| `PAGE/chunk/messages/read_from_parent.py` | Append `<t>` to its hand-written `EXPERIMENT_TYPES` tuple. `table` and `report` read `tuple(FORMS)`; the page reads the contract's tuple. |
| `PAGE/chunk/tests/test_extraction_leaf.py` | Add `<m>_real_world` and `<m>_synthetic_world`, copied from `pulldown_real_world` and `pulldown_synthetic_world`, and extend the type-tuple test. |

**Acceptance:** run all the offline tests of `F/tests`, `G/tests` and the leaf, through the launcher. Earlier types
stay green.

---

## Step 5. The extraction answer form (`F/literature_<m>_extraction.py`)

Copy `F/literature_spr_extraction.py`, or `literature_pulldown_extraction.py`. The form is **derived from the record**;
it is not a second schema.

### What the module offers

- `field_names()` gives the quantities, series, choices and facts in the form's order. `MEANING` holds one general
  description per field.
- `answer_schema()`: each field is `{status 'stated'|'unavailable', value, unit (where the field has one), quote,
  support, reason}`.
- `validate_answer(answer, chunk)` raises `ExtractionRefused`:
  - the answer must satisfy the schema;
  - a stated field carries value, unit, quote and support and no reason; an unavailable field carries only a reason
    from `REASONS` (`not_stated_in_passage`, `unit_not_in_vocabulary`, `ambiguous_or_conflicting_in_passage`);
  - numbers must be above 0;
  - **the quote must occur in the chunk exactly once.**
- `quote_span(chunk, quote)` gives the **UTF-8 byte** span, found by code. The model never gives an offset.
- `record_from_answer(answer, chunk, chunk_offset, experiment_ref, source_ref, assertion_ref)`:
  - spans are absolute (`'bytes a-b of the source'`);
  - an unstated fact is `unknown`;
  - `preparations` are None.
- **Quote only.** The model gives the quote; code finds it. Facts are stated only when the quote itself says them;
  they are never worked out from other numbers.

### The identity block

Added automatically by `F/literature_identity_extraction.py` through `answer_schema_with_identity`. Do not redefine
it.

- `ASKED` holds the contract's identity fields minus the code-stamped ones.
- `target_id` is required for bearing. A grader with no stated target bears on nothing (`target_not_stated`) and
  still counts in credit.
- `partner_id` is optional.
- The model gives the name **as written**, inside a unique quote. Code normalizes it with `normalize_identity_ref`
  (casefold, whitespace collapse, Unicode dashes to hyphen).
- `temperature_c` is converted by code from C or K.
- Every identity field is stated with a support, or unavailable with a reason.

**Acceptance:** `F/tests/test_literature_<m>_extraction.py`, with the same set as pulldown:
- the schema matches the form, and the grader reads exactly the fields the schema asks for;
- a correct synthetic answer becomes a record the grader accepts. For a quantitative type every criterion is decided
  through `_criterion`; the pull-down asserts all `supported`;
- the span counts bytes, not characters (multi-byte text);
- the real paragraph states only what it states;
- a quote not found exactly once is refused, and an answer outside the schema is refused;
- the stated/unavailable rules and the support rules hold;
- every synthetic field is stated, and every synthetic quote occurs once and says its value.

---

## Step 6. The passages module (`F/tests/<m>_passages.py`)

### REAL: one paragraph from a real published paper, never invented

- Find it through Europe PMC open-access full text (`/europepmc/webservices/rest/{PMCID}/fullTextXML`). Prefer
  CC BY or CC0.
- Copy the paragraph **whole, verbatim**, with only the markup removed. The pull-down uses PMC3641083
  (PLoS ONE 2013, CC0). SPR reads the owner's primary text of PMC2745220 from
  `research/experimental_scoring_review_2026-10-23/template_a105_binding_002/popz_2745220_primary.txt`.
- The docstring names the paper, PMC id, DOI, licence and what the paragraph does and does not state.
- Shorten a real chunk only if a needed quote occurs twice, and then say exactly what was removed.
- If no usable paragraph exists, **say so and stop. Never substitute an invented one.**

### SYNTHETIC

- An explicitly synthetic passage that states **every** field of the form.
- It contains multi-byte characters (`µ`, `°`, `×`) so byte and character offsets differ.
- It uses made-up molecule names (the pull-down uses DX-3 and DX-9).

### Constants

- `SYNTHETIC_STATED` and `REAL_STATED` map field to `(value, unit, quote)`.
- `REAL_ALLOWED` maps field to the set of allowed `(value, unit)` pairs: every value the paragraph clearly states by
  the field's general meaning.
- An optional `REAL_SUPPORT` holds the non-direct support classes; pull-down marks `negative_control_done: 'implied'`.
- `answer_from`, `synthetic_answer` and `real_answer`.

### Expected identity constants

These are read by `check_expected_identity` in `PAGE/chunk/tests/test_extraction_model_run.py`, and all are
normalized:

- `SYNTHETIC_TARGET` and `SYNTHETIC_PARTNER`.
- `REAL_EXPECTED_TARGET` and `REAL_EXPECTED_PARTNER`. Use None when the paragraph names no single target; a stated
  target is then an overreach.
- `REAL_EXPECTED_PAIR`, only when the paragraph names a symmetric interacting pair. It is a tuple of two groups of
  acceptable spellings, it replaces the real target and partner checks, and either orientation passes. Example from
  ITC: `(('hsp90',), ('hop',))`.
- A type with several real chunks suffixes the constants by variant (dialysis: `_METHODS`, `_RESULT`).
- A passages module not named `<t>_passages` needs an entry in `PASSAGES_MODULE_OF_TYPE`.

**Acceptance:** the extraction tests of step 5 pass on both passages, and the real paragraph's offline record
(`G/tests/test_literature_<m>_real_case.py`) gives only the criteria the paragraph supports.

---

## Step 7. Real-model acceptance run (one at a time, through the launcher)

### Add two tests to `PAGE/chunk/tests/test_extraction_model_run.py`

Copy `test_the_real_pulldown_paragraph_of_pmc3641083_states_only_what_it_states` and
`test_a_synthetic_pulldown_passage_stating_every_field_is_filled_and_every_criterion_decided`.

- **Run ids:** `a105-extract-<t>-real-real` and `a105-extract-<t>-synthetic-real`. `expected_identity` parses them.
- **Both tests:**
  - `finish()` checks the run ended by `yield_stop`, the return was admitted, and resume replayed with no new model
    call;
  - `report()` runs `check_identity` on every accepted call: each quote occurs once, vocabularies are valid, a name
    lies inside its quote, `target_id` is the normalized name, and the expected identity holds;
  - `calls = no_unrecovered_rejection(calls, units)`.
- **Real test:** every accepted call satisfies `stated <= set(REAL_ALLOWED)`, each stated `(value, unit)` is in
  `REAL_ALLOWED[name]`, and each quote has a `quote_span`. Then `newly_stated < asked`. Unstated allowed fields are
  printed, not required.
- **Synthetic test:** `unstated == []` and the answer's fields equal `SYNTHETIC_STATED`. Then `newly_stated > 0` and
  `credit == newly_stated / asked`.
- **Note:** SPR's real test (`test_the_real_popz_paragraph_...`) is older and weaker. It only checks the KD and
  `newly_stated < asked`. New types use the pull-down pattern.

### Run the tests

Run one test at a time, never overlapping, with a fresh run directory each time. It needs the owner's Codex sign-in.

```bash
cd /home/chia/repos/gene_annotation_episode && bash tools/one_workflow.sh --slot <slot> runs/<fresh-name> -- \
  env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -m model_run -s -q \
  --basetemp=runs/<fresh-name>/tmp PAGE/chunk/tests/test_extraction_model_run.py -k <t>
```

A busy slot means wait. It is not a reason to stop another workflow.

### Pass conditions

- No unrecovered rejection.
- **Real:** the model states only what the text states.
- **Synthetic:** the model states every field, and every criterion is decided (in the offline grader and converter
  tests, step 5).

### Classify every failure, and report it plainly

| Failure | What it means | What to do |
| --- | --- | --- |
| **Overreach** | The real run states a field or value outside `REAL_ALLOWED`, or a target the paragraph does not name as the assayed molecule. | Make only **general** wording changes in `MEANING` or `<M>_INSTRUCTIONS`, then rerun. **Never loosen the test** to admit it. |
| **Expectation too strict** | `REAL_ALLOWED` misses a value the paragraph clearly states by the field's general meaning. | Widen `REAL_ALLOWED` and say exactly what changed and why. Arithmetic or counting errors in one's own test are the same case. |
| **Normal retry** | A quote or schema refusal followed by an accepted call. | Not a failure. Owner (line 37592): "that sounds like the code was doing its job". Count it and summarize it meaningfully. |
| **One-off hallucination** | A single wrong statement. | Check whether the prompt or examples mislead. If not, reproduce once more (owner, line 37089). |

For every field stated on the real paragraph, check that the quote really says it and report any field you doubt.

---

## Step 8. End-to-end check through `page_update`

### What `page_update` runs

`page_update(sheet_state, graders, claims)` in `G/literature_page_update.py` runs:

1. `merged_record`, then `GRADERS[<t>]`, then `CONVERTERS[<t>]`;
2. per claim, `bearing`; only a `direct` result gets `direction_and_ratio`;
3. `row_weight`;
4. `validate_result`;
5. `merge_row_state`, `complete_row`, `merge_main`, `axis_output` and `row_features`.

### The test

The reference is `PAGE/tests/test_branch_page_model_run.py`: the page is commissioned for the hypothesis "PopZ binds
ParB" over the real SPR paragraph. The real page model chooses its units, the real chunk child extracts, and the
page's `update_sheet` (`PAGE/task.py`) runs `group_leaf_records`, `finalize_grader` and `page_update`.

For each new type, copy this test with:
- the type's real paragraph;
- a hypothesis whose predicate is the class's;
- subject and partner names that equal `REAL_EXPECTED_TARGET` and `REAL_EXPECTED_PARTNER`.

### Acceptance (all from the page's return)

- **Bearing direct:** a feature row exists with `target_id` equal to the claim's subject, `assertion_ref` equal to
  the hypothesis, and `experiments >= 1`.
- **Graded direction:**
  - a quantitative result has `supports` with `0 < log_ratio <= QUALITATIVE_LOG_RATIO[<t>]`, or `neutral` at
    strength 0, and never `opposes`;
  - a qualitative result has `supports` or `opposes` with `log_ratio = QUALITATIVE_LOG_RATIO[<t>]`;
  - `effect_support` is `SUPPORT_FACTORS[direction_field_support]`.
- **Row and score:**
  - `scores` carry the target;
  - the row's `weight` is in [0, 1], with unknown criteria counting the assay's own unknown weight;
  - `0 <= credit <= 1`;
  - the run ended by `yield_stop`;
  - resume replays with no new model call.
- **No raw record leaks:** the return's `finding` holds only `scores` and `features`.

---

## Rules that apply everywhere

- **Launcher only.** Every local Python command, including tests, helper scripts and checks, goes through
  `tools/one_workflow.sh`. Use a fresh `runs/<name>` each time, one workflow at a time per slot, and
  `--basetemp=runs/<name>/tmp` (AGENTS.md "Local execution policy").
- **Real tests only.** Tests use real code on real published text. There are no mocks or fakes of the code under
  test. Acceptance is the real-model run (owner, line 37888: "no offline tests ... now we need real tests"). The
  offline tests guard the code and do not replace the real run.
- **No fallbacks.** No guards, autofixes, stubs or `NotImplementedError` placeholders. A wrong commission fails with
  its error (AGENTS.md).
- **Never change the yield-estimator types** the owner designed. Do not use forecast estimators in this axis.
  Tuning their settings is allowed; changing their type is not (owner, line 46141).
- **No central changes.** Stay inside your parts: `G`, `F` and the A105 `PAGE` subtree files listed above. Do not
  touch `episode_runtime/`, `method_loop/` or `yield_control/` (owner, line 50448).
- **No hard-coded thresholds, the smart way (step 3).** Keep each assay's researched values and make them gradual
  around those values; never cut pass/fail at them, never replace them with a generic formula; unknown when the paper
  does not state the value.
- **The grader holds facts; the sheet side judges** (owner, lines 37303 and 37317).
- **Quotes, not prose.** The model returns quotes that code locates. Everything passed upward is a number, count,
  vocabulary value, name or ref.
- **Unknown is never 0 and never opposition.** Silence is unavailable, not `no`.
- **One experiment type at a time**, each finished through step 8 before the next.
- **Declare mistakes plainly.** Every mistake is named as a mistake in the report (owner, line 39379). Do not soften
  a failure into "normal" unless it is a recovered retry.
- **Delete unwanted code directly.** Do not add shims or restore deleted code to make something pass (AGENTS.md
  "Removing unwanted code").

## Known gaps

- **Figures and plots are not read.** Only text chunks, tables and document-order reports are. Values shown only in a
  figure are unavailable. The old figure reading is to be added back later (design doc section 8;
  `A105_FIGURE_EXTRACTION_FINDINGS.md`).
- **Only open-access full text is read.** The full text comes from Europe PMC open access (a PMCID is required).
  Other papers give at most the abstract from the search response. There is no general web search or publisher
  scraping.
- **Softening the binding converters is pending.** Their researched values stay; the hard pass/fail cut-offs among
  them (lone minimums such as `MIN_CONCENTRATIONS`, `MIN_REPLICATES`) are to be made gradual around those values,
  per assay (step 3). `QUANTITATIVE_STRENGTH_ANCHORS`, `QUALITATIVE_LOG_RATIO` and `SUPPORT_DEGREE` are approved
  scale ends and weights, not cut-offs.
- **The direction rule covers binding constants only.** `literature_direction` handles only nM binding constants,
  where smaller is stronger. Every other class needs its own direction rule (step 0c).
- **Some vocabularies are binding-specific.** `QUALITATIVE_STATEMENT`, `ROLE`, `IMMOBILIZATION_SIDES` and
  `ROW_DEPENDENCE_KEYS` are worded for binding (step 0c).
- **`claim_of_hypothesis` reads only partner-valued hypotheses** (step 0b).
- **The 150-paper inventory has not been found.** The October Codex inventory was never located as a list
  (`EXPERIMENT_INVENTORY_SEARCH*.md`). The binding list in use is the owner's paste of 2026-11-20 (step 0a).
- **Two identity risks.** Two same-type experiments in one document that state no differing identity feature merge
  into one grader (contract ruling D: this undercounts evidence and does not overcount it). A leaf that cannot name
  its type has no experiment.
