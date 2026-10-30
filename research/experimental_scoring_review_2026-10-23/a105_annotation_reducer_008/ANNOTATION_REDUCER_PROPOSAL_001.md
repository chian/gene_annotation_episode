# One candidate annotation → one A105 coordinate: proposal 001

2026-10-23. **Unadopted, source-free numerical-design proposal.** All new
numbers below are synthetic. No paper or paper-specific packet was inspected;
the required joined design document's embedded source-example table was read
as design context, without interpreting or reusing those scientific examples.
No production scorer, reader, prompt, episode, scientific run, or earlier record
is changed. The ten-sheet count remains **0/10**.

## Recommendation

Supply the candidate's asserted molecular meaning as an explicit formula over
canonical statements. For a complete joint quantitative observation model,
evaluate that formula in the model. When only conventional target-scoped
statement indexes are available, use the following **explicit conventional
reducer**:

\[
F=\bigvee_{g\in\mathcal G}\bigwedge_{i\in g}p_i,
\qquad D_{A105}=\max_{g\in\mathcal G}\min_{i\in g}D_i,
\qquad c_{A105}=\max(0,D_{A105}).
\]

Each set `g` contains claims genuinely required together for one sufficient
way the candidate's asserted molecular function can hold. Different sets are
alternative sufficient descriptions of **that same assertion**. `D_i` is the
completed signed target-scoped index for statement `i`, in `[-1,1]`, supplied
by the existing statement-scoring and source-combination work. It is not a new
source-level score. A one-statement candidate reduces to the earlier proposal
`c=max(0,D)`.

This is a fuzzy/conventional support rule, **not a likelihood, probability,
Bayes factor, or calibration to annotation accuracy**. A required conjunction
is limited by its least supported required statement. Either genuinely
sufficient branch can support the disjunction. Existing native measurement,
comparability, isolation and correspondence components still combine through
their explicit upstream sums, products and covariance. This reducer defines
the previously missing operation across their distinct molecular statements.

For exact binary arithmetic, `min(x,y)=(x+y-|x-y|)/2` and
`max(x,y)=(x+y+|x-y|)/2`; longer sets apply those operations successively.
No extra importance weights or overall grader are introduced here.

The rule is noncompensatory and idempotent: strong evidence for another
required claim cannot compensate for an unsupported requirement, and repeating
a claim does not increase support. It does not accumulate independent
replication across different endpoints. Replication and contradictory results
for **the same statement** must first enter that statement's declared numerical
calculation. The separate multi-homolog proposal supplies those inputs; this
document neither chooses its policy nor recomputes it.

## The indispensable semantic input

Numbers alone cannot determine the result. With the same incoming statement
indexes `(0.84,0.42)`, “both required” gives `0.42`, while “either sufficient”+gives `0.84`. The definition of the candidate determines which question is
being scored. A reducer cannot infer that definition by maximizing the score.

The minimum input is:

1. One persistent candidate identity and a particular semantic revision, for
   the actual supplied target material and scope.
2. Canonical statements with exact endpoint, molecular state, conditions,
   comparison and boundary meanings. A105 covers conversion, transport or
   binding. A106 perturbation/restoration is not inserted into this formula.
3. The required/sufficient formula and its scientific meaning. A formula does
   not mean “run these experiments.” Multiple assays can address one statement;
   assay alternatives are not automatically alternative molecular propositions.
4. Completed statement indexes, their calculation routes, original evidence
   identities, missing bounds and qualifications; or a joint observation model
   that expresses the candidate directly.

No initial candidate annotation is required for investigation. An episode can
start with sequence, selected file contents or snippets. These inputs exist
when findings support describing a candidate. An arbitrary label or public
accession is unnecessary. Evidence revisions retain the same candidate identity;
changed assertion content gets an explicit semantic revision. Competing
candidate functions have separate identities and separate axis coordinates.
They are not OR branches merely because the investigation is undecided.

Only content **actually asserted** by the candidate determines required claims.
“Converts A to P” does not require a separate binding experiment because chemical
conversion involves interaction. Binding may be useful related evidence, but
it cannot alone substitute for conversion or activation. If the annotation
explicitly asserts measured affinity as well as conversion, those are two
assertions and their combination must be stated. No universal assay checklist,
mandatory order, or scientific acceptance condition is introduced.

## Normalize meaning without adding evidence

Convert a positive AND/OR expression into its distinct sufficient clauses:

- Resolve proven synonyms to the same canonical statement ID. Equal scores or
  similar wording alone do not establish equivalence. Conditions, scope,
  direction and numerical boundary must agree.
- Remove repeated IDs inside a clause and duplicate clauses.
- Remove any clause that strictly contains another clause. If `A` already
  suffices, adding `A AND B` adds no new sufficient possibility.

Thus `A OR (A AND B)=A` and `A AND (A OR B)=A`. With `D_A=0.72`, both score
`0.72`, even if B is unknown. Coverage is computed after this normalization;
an absorbed B does not manufacture a requirement or dilute coverage. The
original statement/evidence records remain preserved.

This normalization uses explicit identity and the formula's logical structure.
It does **not** guess biological entailment between differently scoped claims.
A statement about a narrow condition is not a synonym for a statement about
all conditions. A broad family label and a specific substrate function cannot
be made interchangeable to improve the score. If a real entailment is used to
rewrite an assertion, its definition and implications for relevant contrary
evidence must be supplied explicitly. Negative evidence against an entailed
requirement cannot be dropped by changing the wording.

The input language uses positive propositions with signed evidence. Contrary
evidence is not an arbitrary Boolean `NOT` node. An actual negative molecular
assertion needs its own specified numerical comparison; do not make
`A OR NOT A` a manufactured high-scoring annotation.

## Fully filled conventional synthetic sheet

Candidate `synthetic_candidate_01` asserts that the supplied molecule converts
A to P in **both** C1 and C2, and has higher A turnover than B under C1. These
are deliberately the contents of this synthetic candidate, not requirements
for every enzyme annotation. The assignment could have begun from a sequence;
the candidate is stipulated here solely to illustrate the scoring boundary.

The incoming D values are synthetic completed statement-index outputs. Their
upstream measurement/transfer policies are not redefined in this example.
They have no physical units; source measurements and sampling uncertainty
remain in their referenced statement sheets. They are not paper measurements.

| Canonical statement | Exact asserted content | Incoming signed D | Allowed-input bounds | Original measurement references | Formula use |
|---|---|---:|---|---|---|
| `s_c1` | Supplied target converts A→P in C1 | 0.84 | [0.84,0.84] | `m_c1_A`, `m_c1_blank`, `m_c1_cal` | required |
| `s_c2` | Supplied target converts A→P in C2 | 0.42 | [0.42,0.42] | `m_c2_A`, `m_c2_blank`, `m_c2_cal` | required |
| `s_pref` | Corrected A turnover exceeds corrected B turnover in C1; boundary difference 0 | 0.72 | [0.72,0.72] | `m_c1_A`, `m_c1_B`, `m_c1_blank`, `m_c1_cal` | required |
| `s_bind` | Supplied target binds A in C1 under the declared binding comparison | 0.9604 | [0.9604,0.9604] | `m_binding_curve` | related, not a conversion substitute |
| `s_c1_alias` | Exact synonym of `s_c1` | same row, not another D | same row | same observations | canonicalized to `s_c1` |

The native C1 activity contributes to both activity and preference. The sheet
records this overlap; it does not call the two statements independent proofs.
No full calibrated joint target likelihood is supplied in this conventional
fixture. If one becomes available, the joint route below uses it.

\[
\mathcal G=\{\{s_{c1},s_{c2},s_{pref}\}\},\quad
D_{A105}=\min(0.84,0.42,0.72)=0.42,\quad c_{A105}=0.42.
\]

Coverage is `3/3` essential canonical statement inputs with defined point
indexes. It is a descriptive count, not a reliability multiplier. The binding
row and synonym do not raise the numerator or denominator. The output retains
all contributing measurement identities and both the signed index and support
coordinate. It does not calculate other axes, annotation progress or time.

The exact populated research input/output is in `synthetic_sheet_001.json`.

## Contrasting synthetic behaviors

All statements in this table refer to the same fixed target scope within each
example. Changing the assertion changes what is being scored; no favorable
interpretation is selected by the reducer.

| Semantic situation | Declared input/formula | Signed result | Coordinate or identification bounds |
|---|---|---:|---|
| Genuine required conjunction | A AND B, D=(0.84,0.42) | 0.42 | 0.42 |
| Either of two sufficient explanations of the same exact molecular assertion | A OR B, D=(0.84,0.42) | 0.84 | 0.84 |
| One single-step mechanism or a two-step mechanism, each explicitly sufficient for the same net molecular assertion | P OR (Q AND R), D=(0.72,0.84,0.42) | 0.72 | 0.72 |
| Narrow condition scope | A: operation in C1, D=0.84 | 0.84 | 0.84 |
| Broader condition scope | A AND B: operation in C1 and C2, D=(0.84,0.42) | 0.42 | 0.42 |
| Related binding result | Original formula, plus related binding D=0.9604 | unchanged | unchanged |
| Required claim opposed | A AND B, D=(0.84,-0.42) | -0.42 | 0 |
| One sufficient mechanism opposed, another remains supported | P OR (Q AND R), D=(-0.72,0.84,0.42) | 0.42 | 0.42 |
| Every sufficient path has an opposed requirement | P OR (Q AND R), D=(-0.72,0.84,-0.42) | -0.42 | 0 |
| Contrary observations revise the same statement's upstream score | P changes 0.72→0.10 in P OR (Q AND R); Q=0.84,R=0.42 | 0.42 | 0.42; no historical maximum |
| Unavailable required statement | A AND B, D_A=0.84, D_B unknown | [-1,0.84] | null; [0,0.84] |
| Known path plus incomplete alternative | P OR (Q AND R), D=(0.72,0.84,unknown) | [0.72,0.84] | null; [0.72,0.84] |
| No data for any required statement | nonempty formula; every D unknown | [-1,1] | null; [0,1] |
| Repeated/synonym required claim | A AND alias(A) AND B, D=(0.84,0.42) | 0.42 | 0.42; two unique leaves |
| Added logically redundant clause | A OR (A AND B), D_A=0.72; any or missing B | 0.72 | 0.72; one essential leaf |

The alternative-mechanism rows are **stipulated semantic fixtures**, not a
biological rule that arbitrary reactions imply a common function. The branch
definitions must include the conditions and relationships that make each
sufficient. Merely testing the same net reaction with two assays does not
create two such branches. Contradictory evidence for the common net reaction
must enter its statement/model; it cannot be placed only against one mechanism
to preserve a favorable alternative. Unrelated conversion and transport
functions remain separate candidates.

The difference between these legitimate formula structures is essential
mathematics. It cannot be postponed by calling every statement score the
whole-axis coordinate. This document supplies that missing calculation as a
proposal; it does not imply adoption or completion of the full A105 sheet.

## Preserve the actual joint observation model

When a joint model spans the declared molecular assertion, use the formula to
define its two parameter regions and calculate

\[
S_F=\sup_{F}\ell(y;\theta,\eta)-\sup_{\neg F}\ell(y;\theta,\eta),
\quad D_{A105}=\tanh(S_F/2),\quad c_{A105}=\max(0,D_{A105}).
\]

Use closures of the regions at numerical boundaries, preserve actual physical
parameter domains, and retain shared nuisance parameters. This is the existing
proposed signed profile-fit contrast applied to **the whole asserted molecular
formula**, not a product or sum of separately optimized marginal scores. It is
still not a probability. Model normalization and the positive-support floor
remain pending choices.

For the fully defined known-normal model `y ~ N(theta,V)` with explicit linear
statement inequalities, put

\[
Q(\theta)=(y-\theta)^T V^{-1}(y-\theta),\quad
S_F=\tfrac12\{\min_{\neg F}Q-\min_F Q\}.
\]

The formula determines unions/intersections of constrained parameter regions.
The joint normal fixture has exact numeric `y`, `V`, parameter order, inequality
coefficients and boundaries in `synthetic_sheet_001.json`. No unknown covariance
is set to zero. An unidentified required endpoint is not turned into a measured
equal-fit result by taking two formal suprema over an unobserved parameter.

For synthetic `y=(2,3)` and `V=I`, with atoms `theta_1>0`, `theta_2>0`:

| Formula | Correct joint S | Correct joint D and c | Conventional marginal result for comparison |
|---|---:|---:|---:|
| Both required | 2 | 0.761594156 | 0.761594156 |
| Either sufficient | 6.5 | 0.996997635 | 0.978026115 |
| Both required, observations (-2,3) | -2 | D=-0.761594156; c=0 | D=-0.761594156; c=0 |

The first equality is a property of this example, not proof that conventional
min/max reconstructs all joint likelihoods. The disjunction already differs.
The semantic formula remains unchanged between routes. A model is selected
because it describes the actual observations, never because its score is larger.

If a quantitative model supports only a **predefined compound substatement**,
keep that substatement's joint calculation intact as its input row. Do not
decompose it into marginals and then multiply them. Any subsequent combination
with conventional indexes is explicitly a conventional result, not a recovered
full likelihood. The substatement and its place in the formula must be declared
by meaning; regrouping clauses after seeing scores is not permitted as a
numerical definition. A declared full-model route with missing model operands
remains unavailable/conditional; it does not silently switch to an available-
only average or a different favorable semantic formula.

### Two ratios sharing one measurement

Take the synthetic observed log-rate vector `(x_A,x_B,x_C)=(3,1,0)`, with a
specified reference rate inside each logarithm, known covariance `I`, and the
same original x_A in both contrasts. Let

\[
y=(x_A-x_B,x_A-x_C)=(2,3),\qquad
V=\begin{pmatrix}2&1\\1&2\end{pmatrix}.
\]

For the specifically declared disjunction “either stated preference holds,”
the best opposed fit is `(0,0)`, so `S=7/3` and **c=0.823200646**. Pretending
the two ratios are independent replaces the covariance with `diag(2,2)` and
incorrectly gives `S=3.25`, **c=0.925346225**. The conventional marginal maximum
would be **0.809301070**; it is a different conventional calculation, not the
joint result. The exact available joint model supplies `0.823200646` here.

The original measurements are represented once and transformed together.
Separate ratio names or source records do not make two independent A readings.
With conventional inputs and unknown joint dependence, min/max adds no
independent-proof bonus; original measurement overlap remains explicit.

## Missing inputs, uncertainty and coverage

For the conventional route, let each incomplete input have an allowed set
`D_i in [l_i,u_i]`. An entirely unmeasured index has `[-1,1]`, **not D=0**.
For the rectangular allowed set, monotonicity gives

\[
D_F\in[\max_g\min_{i\in g}l_i,\ \max_g\min_{i\in g}u_i],
\quad c_F\in[\max(0,D_L),\max(0,D_U)].
\]

These are identification/sensitivity bounds, not confidence intervals or a
uniform distribution. If cross-statement allowed inputs obey additional joint
constraints, retain them. The box calculation is then labeled an outer bound;
exact bounds require `inf/sup` over that declared joint set. Marginal sampling
confidence intervals do not automatically become a simultaneous interval for
the whole annotation. Measurement uncertainty already used to obtain each D
remains in its upstream model and must not be penalized a second time.

Return a point only if the complete declared calculation supplies it, or the
projected bounds coincide. For example `A AND B` with `D_A=-0.2` and unknown B
has signed bounds `[-1,-0.2]` but coordinate exactly `0`. Mark this
`identified_projection_with_missing_input`, retaining B as missing; it is not
an observed zero-effect assay. Otherwise the coordinate is `null`, with bounds.
A separately requested conditional calculation can be retained under
`conditional_result`, with explicit assumptions. It does not fill the full
coordinate, and the midpoint or lower bound is not silently selected.

Coverage reports distinct essential canonical statements after absorption:
complete-point count, conditional count, unavailable IDs and their fractions.
It also preserves the original evidence-union and sharing map. Counts measure
which inputs exist; they are neither replication counts nor multipliers. A
0/3 coverage record differs from a three-statement measured opposition yielding
c=0. A formula not yet defined has status `semantic_input_missing`, not “no
experimental support.”

## Exact proposed research fields

All fields below are new sheet IO unless explicitly called existing references.
They are not claimed to be implemented production contracts. References retain
the actual records; no new model call is asked to restate recorded facts.

| Path | Type and meaning | Population/calculation |
|---|---|---|
| `axis_id` | literal `A105` | sheet definition |
| `candidate.id` | stable nonempty candidate key | identity established when the candidate emerges; not a per-turn or coherent-set hash |
| `candidate.semantic_revision` | nonempty revision key | records changes to the asserted meaning; evidence updates alone do not create another candidate |
| `candidate.subject_material_ref`, `.scope_ref` | exact target-material and applicable-condition references | supplied sequence/file/snippet boundaries and known conditions |
| `candidate.annotation_record_ref` | existing record ref or null | optional historical/account link; not the new candidate's identity |
| `candidate.member_statement_ids`, `.related_statement_ids` | distinct canonical ID lists | membership in this persistent grouping and related findings; related rows do not automatically enter the formula |
| `candidate.alternative_candidate_ids` | distinct other candidate keys | separate functions; no scoring across these IDs here |
| `formula.expression` | nonempty positive `statement`, `all_of`, `any_of` tree | explicitly declared molecular assertion, not selected from scores |
| `formula.semantic_basis_refs` | references explaining scope and sufficient/required meanings | scientific interpretation of the stated assertion; no overall numerical grade |
| `formula.canonical_sufficient_routes` | nonempty list of nonempty canonical-ID sets | deterministic synonym resolution, DNF expansion, duplicate/superset removal |
| `aliases[].alias_id`, `.canonical_id`, `.equivalence_basis_ref` | exact equivalence mapping | supplied statement equivalence; conflicting numeric aliases are a representation problem, not independent rows to average |
| `statement_inputs[].statement_id`, `.statement_definition_ref` | canonical identity and exact endpoint/condition/comparison definition | statement sheet; optional current `hypothesis_ref` can be attached |
| `statement_inputs[].upstream_row_ref`, `.upstream_calculation_ref` | exact current completed row and declared formula | upstream same-statement combination, including all relevant opposing evidence and multiple-source policy |
| `statement_inputs[].index_kind` | `joint_profile_normalization` or `conventional_target_index` | declared by that row; no likelihood meaning inferred from its numeric range |
| `statement_inputs[].signed_target_index` | finite `[-1,1]` or null | upstream statement calculation; not a source chosen by this reducer |
| `statement_inputs[].point_basis` | `complete`, `conditional`, `unavailable` | available mathematical inputs and explicit assumptions, not scientific acceptance |
| `statement_inputs[].identification_bounds` | ordered pair in `[-1,1]` or null with exact reason | allowed missing/sensitivity operands; no sampling-interval relabeling |
| `statement_inputs[].original_measurement_refs`, `.assessment_refs`, `.shared_nuisance_refs` | exact record-ID arrays | established identities/dependencies; unique experiment count is not inferred from array length |
| `statement_inputs[].sampling_uncertainty_ref`, `.condition_refs`, `.missing_operands` | refs and specific missing operand names | existing measurements/model qualifications; no unreported uncertainty fill |
| `input_snapshot_ref` | immutable evidence snapshot reference | identifies exactly which row revisions produced this number |
| `reducer.route` | `declared_minmax_convention` or `joint_profile` | model-based declared choice; never numeric optimization over routes |
| `reducer.definition_ref`, `.coordinate_mapping` | version and literal `positive_part` for this proposal | explicit scoring convention subject to user judgment |
| `joint_model.model_family` | here `multivariate_normal_known_covariance` | actual justified observation model; this file does not supply a universal model selector |
| `joint_model.parameter_order`, `.observed_contrasts`, `.known_covariance` | ordered IDs, finite vector y, complete positive-definite V in corresponding product units | actual joint observations/transformation; no diagonal independence fallback |
| `joint_model.statement_constraints[]` | statement ID, coefficient vector a, boundary b, unit; atom `a·theta>b` | exact numerical comparison, with the domain preserving physical constraints |
| `joint_model.parameter_domain` | explicit linear inequalities with numeric operands, or declared unrestricted real domain | actual parameter meaning; nonnegative activity is not silently signed |
| `joint_model.native_observation_refs`, `.linear_transform`, `.native_covariance` | original identities and, when a linear transformation is used, its exact operands | deterministic joint transformation; duplicate original measurements represented once |
| `result.signed_axis_index`, `.profile_log_ratio` | D in `[-1,1]` or null; S in nats or null | joint S/tanh or conventional min/max; conventional D is never back-converted into a likelihood |
| `result.coordinate_value`, `.coordinate_bounds` | finite `[0,1]` or null; ordered bounds with type | one positive-part map after candidate calculation; bounds as above |
| `result.status`, `.conditional_result`, `.missing_operands` | availability type, separate conditional calculation, exact missing inputs | preserve known zero, opposition, missing, conditional and conflicting representation distinctions |
| `result.coverage` | essential unique count, complete count, conditional count, unavailable IDs, fractions | after semantic normalization; no scoring multiplier |
| `result.provenance` | used statement revisions, original observation union, shared-observation map, route/formula version | deterministic references to actual inputs |

The model-family fields above give a fully specified calculable example. Other
observation families must retain their own exact sheet operands and declared
joint likelihood; the string `joint_profile` by itself does not supply them.
The conventional route does not require a fictitious joint likelihood where
only a conventional source-to-target index exists.

## Current implementation boundary

The separate current-code inspection is in
`../annotation_axis_boundary_008/IMPLEMENTATION_BOUNDARY_001.md`. Its findings
were received directly; no duplicate production-code audit was performed here.

- Current annotation records are revisioned subject/context accounts with
  `coherent_sets`, interpretations and assessment references. A coherent-set
  hash can change on evidence revision. `alternative_refs` refers to individual
  hypotheses, not persistent evolving multi-claim candidates. The current
  resolution enum is not a selected candidate ID.
- A hypothesis reference can persist for exactly unchanged proposition content.
  It can be a member-assertion reference; it cannot stand in for an arbitrary
  multi-claim candidate identity.
- `score_axis` currently returns experiment/route records and
  `annotation_aggregate=None`; it has no typed candidate membership input.
  The runtime's optional annotation projector has one scalar `credit` and an
  optional `axis_components` mapping, not a map of candidate scores. The
  default annotation scorer remains unbound.
- The retained softened hypervolume requires each explicitly configured axis
  coordinate to be finite and in `[0,1]`; no default axes/weights/epsilon or
  A105 mapper is installed. This research output does not change its formula.

Defining this reducer is A105 numerical-design work. Production storage for
persistent candidates, readers populating these exact cells, availability-aware
adapters, ten-axis policy binding and end-to-end verification remain later
implementation work. An unbound or unknown coordinate is not zero. No old
account-maximum rule, five-axis projector, or 100-point scale is reinstated.

Scientific investigation progress, timing, monitoring credit and continuation
are outside this coordinate. A useful correction can lower c. A zero or null
coordinate does not stop an episode or impose a scientific acceptance gate.

## Exact choices to put to the user

This is one recommended practical proposal, not an adopted menu of scorers.
The material decisions are:

1. **Meaning of conventional whole-candidate support:** use the weakest required
   statement and strongest genuinely sufficient branch, with the stated
   idempotence/absorption behavior. This is the new convention requiring
   judgment; it does not come from the existing runtime.
2. **Existing nonnegative boundary choice:** retain signed D and use its
   positive part for H. Opposition then cannot be distinguished below zero in
   that single coordinate, although it remains in the sheet.
3. **Incomplete whole-candidate output:** recommend null plus identification
   bounds unless the projection is identified. A conditional available-input
   number may be shown separately, but cannot masquerade as the complete c.

The required/sufficient semantics for an actual candidate are scientific inputs,
not a universal preference to choose once for all functions. The proposed
normalization S/B and upstream source-combination policy remain their own
pending decisions. There is no authority here to install any of them.

`check_reducer_arithmetic_001.py` passed 24 synthetic cases and 252 monotonicity
comparisons. `check_semantic_normal_form_002.py` adds 625 equivalence comparisons,
explicit absorption and canonical coverage; its coverage definition supplements
the first checker's simple referenced-leaf count. Exact results are retained in
`arithmetic_001.json` and `semantic_arithmetic_002.json`. These checks establish
the stated arithmetic only, not biological sufficiency, likelihood fit to real
data, empirical calibration, implemented readers or a live annotation path.
