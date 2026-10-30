# Scientific-support slot: scoring review proposal, 2026-10-21, record 002

Status: **review, not adoption**. This document proposes the first slot's meaning
and identifies exact changes that would be needed. It changes no library entry,
record schema, score, controller, saved observation or episode relationship.
The companion [case crosswalk](SCIENTIFIC_SUPPORT_CASE_CROSSWALK_2026-10-21_002.json) preserves
the complete group partition, source pointers and current arithmetic rules.
The completed crosswalk covers all 142 groups / 149 retained records; its proposed encodings are not actual runtime target records.

This is a **new permanent record**. The first recorded drafts
`SCIENTIFIC_SUPPORT_SLOT_REVIEW.md` and `SCIENTIFIC_SUPPORT_CASE_CROSSWALK.json`
remain unchanged and are hash-linked from the companion record. The authoritative
correction is [amendment 001](AMENDMENTS/SLOT_CORRECTION_2026-10-21_001.md).
No original research or restored implementation note is overwritten.

## Completed review coverage

| Fixed review partition | Distinct groups | Original records | Concrete support contrasts |
| --- | ---: | ---: | ---: |
| Sequence/structure transfer | 38 | 42 | 38 |
| System and physiology | 52 | 54 | 62 |
| Discriminating follow-up cases | 52 | 53 | 63 |
| **Total** | **142** | **149** | **163** |

The fixed source-group partition is mutually exclusive and complete. Each row
retains every original record's source location, inspection scope, observations,
record digest and trace-extension pointers. Eight groups remain abstract or
summary only; auxiliary abstract-only studies within other groups retain their
own recorded limitations. No primary source was newly retrieved for this review.
The contributors inspected the retained original records and relevant detailed
traces, not the authors' private thought processes. Candidate encodings and
support-route interpretations are review proposals, never newly recorded target
findings or computed published-case scores.

Case-level proposal tags remain visible in the crosswalk. A suggestion framed as
"regulatory contribution", "specificity", "partner requirement" or a time-window
contrast is not automatically another support axis. It can instead be a typed
claim, a condition of an existing support route, or a second-slot thought pattern.
The synthesized entries below require an actual evidential relationship and an
explicit relationship to the code, rather than adopting those labels as axes.

## Requirements, quoted verbatim

> there should be 3 slots from our discussion. 1 related to annotation credit axis, 1 related to thought pattern, and 1 with the tools that the child is scoped to

> biological claim heading is not what i asked for. these should be evidence slots that gain credit

> scientific support slots. basically something real. not vibes like "biological context"

> your biological claim heading is just vague vibes. your scoring is exact. you were told exactly to match up with your scoring, with the potential to adjust the scoring based on past published work describing how annotations are evidenced

The first slot was built incorrectly. A01–A10 selected what a claim was *about*
(activity, specificity, requirements, localization, physiology and so on).
They did not select a scientific-support contribution with a defined relationship
to the score. Their useful biological distinctions are background material, not
valid first-slot entries. The fact that code uses five other labels does not
establish that those five are the correct scientific-support axes either.

The maintained **Follow-up Lane** table is the research starting point. F01–F05
remain its original lanes; they are not proposed replacement credit axes. The
142 groups / 149 records and eight abstract-or-summary groups remain distinct.
Published experiments are the authors' work. The preserved retrospective
calculations are separately identified. Reviewing either is not new evidence
about the fixed gene and earns no target credit.

## What the current score actually computes

The full implementation inspected is `credit.py`, `scientific_credit.py`,
`investigation_progress.py`, `scientific_findings.py`, `finding_validity.py`,
`domain.py`, the relevant Store observation/assessment/account validation, and
the runtime receipt, score-view, decision-context and separate annotation-score
consumers. `default_scientific_binding.py` and `investigation_policy.py` determine
which bindings a new or resumed caller actually uses. The crosswalk exports
eleven named rules with their source locations.

1. An observation names its real source, actual measured/reported subjects,
   measurements and provenance. A sequence alignment does not contain the
   comparator's experimentally established function. That characterization
   needs its own source-bound fact. A source annotation is not a measured target
   function. Source content, copied annotation and coordinate transformations
   do not directly map to evidence components.
2. A hypothesis specifies a typed target proposition: for example `catalyzes`,
   `functional_family`, `transports`, `participates_in`, `requires`, `located_in`
   or `growth_capability`, with actual entity/context references. An assessment
   links that proposition to one observation using `strengthens`, `weakens`,
   `mixed` or `does_not_discriminate`; applicability is `direct`, `transfer`,
   `contextual`, `scope_limited` or `incomparable`. Conditions and examined
   assumptions remain references. The episode supplies these interpretations;
   the host validates the declared structure and reference relationships.
3. `CreditPolicy.observation_axes` maps **observation kind**, not the hypothesis
   predicate, to one base component. The exact defaults are below. Each eligible
   operand's weight is its bound applicability weight × relation weight ×
   extent factor. Assay magnitude, E-value, identity percentage and model
   confidence do not become reliability estimates in this formula. Query
   coverage can be an extent proxy when exact interval mapping is unavailable.
4. Observed extent is clipped to actual input/source geometry. Inferred extent
   is non-direct and needs explicit bounded target attribution. Material-context
   allocation is explicit and creates no molecular measurement. A published
   reference protein's residue numbers never become measurements of the target.
5. Within a declared compatible account and material cell, `supported` uses
   strengthening evidence as positive and weakening evidence as opposing;
   `weakened` reverses those roles. `unresolved` uses the configured unresolved
   factor. Each component is `max(positive)/(1 + max(opposing))`. Copies do not
   sum. Two truly independent same-axis experiments also do not accumulate.
6. `discrimination` is derived from weakened/unresolved counterevidence and
   explicit alternative contrasts. The same observation may contribute to a
   base component and to this derived component. This is existing arithmetic,
   not a second experiment or an additional action observation.
7. The softened product is computed over the fixed five components. Each cell
   chooses one whole coherent account; incompatible accounts are not fused by
   taking their best axes. The result is integrated over the fixed original
   scope and bound target weights. No annotation verdict or stopping decision
   follows from this calculation. Current correction/withdrawal can lower it.

An `investigation_finding.qualification` such as `prediction_not_measurement`
does **not** automatically change the annotation operand's numeric weight.
Qualification is part of the separate finding identity; annotation weighting
still uses relation, applicability and extent, with withdrawal/replacement
removing inactive findings. A support-entry definition must state the actual
operand relationship, rather than assume that a useful-sounding qualification
has already changed the score.

| Existing component | Exact default observation kinds |
| --- | --- |
| `empirical` | `assay_report`, `biochemical_assay`, `genetic_phenotype`, `growth_assay`, `read_support` |
| `comparative` | `alignment`, `profile_match`, `comparison`, `gene_prediction` |
| `mechanistic` | `structure_match`, `mechanism`, `reaction_context` |
| `biological_context` | `context_measurement`, `context`, `taxonomy_assignment`, `sequence_composition` |
| `discrimination` | Derived by `_components`; never an observation-kind mapping. |

The standard new-application **investigation-progress** channel is different:
`finding_unit × distinct current retained typed findings actually received`.
Finding identity includes the normalized target question, source claim and
qualification. Opinion changes, episode/account identity and quotation windows
do not create another finding. Primary publication metadata, exact original
workbook lineage and explicit same-source-claim links can identify repeated
representations. This is not a general experiment-independence detector.
Valid negative, conditional or nontransferable findings can earn progress.
Retired findings lose current validity; an unreceived replacement earns nothing.
The separately bound `AnnotationSupportScore` supplies the annotation vector and
uses the existing formula with stable integration. Child scalar scores are not
added to parent scores. Historical callers can have different frozen bindings;
this review does not reinterpret them.

These are structural/reference checks, not a proof of scientific entailment.
For example, preserving a mutant strain and a phenotype as real source subjects
does not turn that phenotype into a direct molecular assay on the scoped gene.
The source-subject and applicability distinction must survive the interpretation.
Current construct/context records can retain real identities and anchored
controls, but their existence alone does not validate every causal relationship.

The current constructor also has a precise missing connection. In
`ScientificProcessEpisodes.decision_context`, the old first-slot entry is exposed
as descriptive focus fields. Its `credit_view` delegates to
`WorkflowServices.scientific_credit`, which uses the caller-bound projector,
fixed scope and actual receipt references; it does not read `annotation_ref` or
a library axis binding. This does **not** imply that selecting the first slot
should mask credit or pick another projector. The needed connection may be a
reviewed declaration of which actual support operands the selected entry pursues.
Selection itself must not award credit, alter progress units or reprice history.

## Concrete candidate entries for the first slot

These are **candidate scientific-support routes**, derived from the cases, not
adopted axes or a fixed number of new dimensions. Each states the exact support
being sought. An entry must bind to declared score operands before becoming
selectable. Several candidates currently land in the same component; that fact
is visible rather than disguised as a completed score redesign. A tool name is
listed only after the support definition and does not choose the conclusion.
Listed operations are implemented references, not proof of live service access,
authentication, resource deployment or a particular retrieved child tool set.

| Proposed support entry | Precise support and limiting records | Positive, negative and conflicting outcomes | Existing numeric route / unresolved boundary | Available operations, last |
| --- | --- | --- | --- | --- |
| **Function transfer from a characterized sequence homolog** | A bounded target property is supported by actual sequence correspondence to a comparator with separately recorded functional characterization. Preserve homolog identity, domain/coverage correspondence, relevant site observations, actual assay scope and counterexamples. HemK, TriA/AtzA, HisN and YadB supply different limits. | Matching ancestry can strengthen family/chemical-class support while exact specificity stays unresolved. A competent discordant activity comparison weakens that transfer without erasing ancestry. Failed expression is not a negative enzyme assay. | Sequence/profile correspondence maps to `comparative`; characterized activity maps to `empirical`. The current schema can state their distinct hypotheses but has no explicit typed link saying which characterized property is being transferred through which correspondence. Identity alone never supplies that link. | `public.hmmer.*`, `public.blast.*`, `public.uniprot.*`, `sequence.align`, `sequence.sites`; read retained characterization facts. |
| **Function transfer constrained by structural correspondence** | A target's relevant local machinery, pocket, access route or architecture corresponds to a characterized structural comparator. Preserve actual structure identity, residue/ligand correspondence, model origin and the comparator's measured function. Broad fold similarity is a weaker proposition than matched productive chemistry. | A conserved catalytic core may strengthen broad chemistry; changed pocket/loop geometry can weaken specificity transfer. Bound ATP supports binding in MJ0577 while purified-alone hydrolysis and native switch function remain separate. An absent structural hit is bounded by the search. | `structure_match` maps to `mechanistic`. The same component also receives chemical-account reasoning. Origin/provenance can distinguish measured and modeled structures in records; the component does not supply a calibrated model-to-function rule. | Existing source/image/material readers can inspect supplied/deposited material. Native structure search, superposition, docking and coordinate-contact calculation are not present in the inspected callable map. |
| **Functional association from conserved gene organization** | A target repeatedly occurs in a specifically organized locus, operon, domain fusion or regulatory neighborhood with a characterized process. Preserve actual genome/strain identity, feature order/orientation, domain boundaries and exceptions; association is to the process, not automatically its precise reaction. | Recurrent HemK–RF1 organization or YjeF fusion supports functional association. OarX neighborhoods retain thiamin association despite tested substrate failures. Broken or nonuniversal organization limits transfer rather than proving absence. | Usually `context`/`context_measurement` → `biological_context`; raw feature labels alone are source assertions. Gene proximity, fusion and direct activity are recordable separately, but there is no declared support-basis type for the organizational inference. | `public.ncbi.sequence`, `material.annotations`, `reference.neighborhood`, `sequence.view`, `sequence.align`; supplied tables through `source.xlsx.*`. |
| **Functional association from evolutionary co-distribution** | Presence/absence or replacement of a properly identified homolog tracks a separately established pathway/product requirement across explicitly selected organisms. Preserve organism inventory, homolog detection method, missingness, paralogs and exceptions. QueF distribution, HisZ/HisG architecture and OarX/FmnO show why correlation cannot be universalized. | Covariation strengthens bounded pathway association. Retained product with the usual gene absent motivates an alternative contributor. A blank unexamined cell is unknown, not biological absence. Repeated closely related genomes do not establish independent replicated evidence. | Context/comparison records currently map to `biological_context` or `comparative` depending on kind. The schema has no explicit association-test/detection-scope record; choosing a different kind can change the base component without changing the biological claim. | Actual sequence search/acquisition, taxonomy and supplied-table operations exist. No inspected operation computes a phylogenetically corrected association or performs a complete pan-genome audit. |
| **Molecular function established by identified inputs and outputs** | The actual protein/preparation performs a defined conversion, transport, binding or physical effect under stated conditions. Preserve product/recipient identity, assay competence, controls, substrate panel, units and source subjects. A proxy signal is not the completed conversion. QueF, M3K, YadB, TM0936 and YjeH provide different resolution tests. | A product-identifying positive strengthens only the tested property. A competent negative weakens that property under its conditions. Insolubility, absent substrate, incomplete partners or unresolved contamination leave intrinsic capacity unresolved. Genuine side activity does not establish ordinary native responsibility. | Assay kinds → `empirical`. Different target predicates and typed qualifications can preserve these conclusions now. The numeric component does not distinguish direct product identity, proxy readout, affinity or assay-panel completeness merely from kind. | Read existing typed records, source text, images and supplied workbook rows. No wet-lab assay is an execution operation in the workflow. |
| **A component's contribution supported by selective perturbation and restoration** | A defined molecular/cellular output changes when a specific component or interaction changes, with relevant abundance, localization, preparation and alternative-route controls. Preserve actual genotype/construct, partners, conditions and readout. EnvC, TsaE, Cas2, YabA and YbeY show distinct contributions. | Preserved binding/localization with lost activation can strengthen an activation contribution and weaken copied catalytic attribution. Rescue supports the restored relationship; bypass and overexpression do not automatically establish the normal reaction. A silent single deletion leaves overlap/demand alternatives. | Usually assay/genetic kinds → `empirical`; structural interface evidence may enter `mechanistic`. Existing `participates_in`, `partner_dependence`, `requires` and separate direct-activity hypotheses can express this. The component merges system attribution and direct isolated chemistry numerically. | Read exact existing/source genotype, interaction and outcome records; supplied tables/images are available. Native perturbation experiments and interaction measurements are unavailable. |
| **Native deployment supported by coordinated expression or molecular response** | The target and the proposed process are measurably available or change together in the relevant native condition, cell state or phase. Preserve measured entity, reporter versus direct readout, organism, sampling/replicate context and matched process partners. Cdv induction and YeaG state/site contrasts limit broad deployment claims. | Coordination strengthens compatibility with native participation. Decoupling or selective unaffected targets narrows the claim. Expression is not catalytic action; a reporter, pooled protein value or changed phosphosite does not establish flux, a direct substrate or every member of a population. | Context measurements generally enter `biological_context`; a genetic readout can enter `empirical`. Typed contexts preserve the distinction, but the existing vector has no defined expression/deployment operand. This candidate needs more deliberate support thresholds before it is selectable. | Supplied source/XLSX/image and existing-record readers. No implemented transcriptomic/coexpression/phosphoproteomic analysis operation was found in the inspected map. |
| **Physiological compatibility supported by measured access and location** | Protein, substrate and required partners have demonstrated access to the relevant compartment/orientation under the claimed conditions. Preserve the measured preparation, sided-access/fractionation controls and distinction between native and engineered location. MurJ, DsbD, AmiC, PibD and HpnN separate access from chemistry. | Correct measured access strengthens a physiological proposal's prerequisite; absent access can weaken it while retaining intrinsic activity. A processed/exported protein can still fail assembly. Failed reporter access or degraded fusion cannot establish wrong protein location. | Measured access may be an assay (`empirical`) or context (`biological_context`); prediction may be a comparison/structure kind. Location and chemical claims are already different typed hypotheses. An explicit basis is needed so kind choice does not masquerade as a different support source. | Read actual source/image/material records and compare sequences/sites. Native SignalP/DeepTMHMM, class-III predictor and localization assays are absent from the inspected map. |
| **Native contribution supported by allele-linked, condition-matched organism performance** | A defined physiological outcome depends on the gene/activity in an explicit strain, resource condition, environment, time window and population context. Preserve restoration/competition controls and distinguish growth, survival, colonization and recovery. Ttr and YeaG show opposing outcomes across conditions or times. | A matched effect strengthens only that conditioned contribution. A matched nonphenotype weakens universal necessity; it does not erase a biochemical capability. Contradictory survival/recovery results remain separate claims, not an average or a universal benefit. | `growth_assay`/`genetic_phenotype` → `empirical`. Context references can express the conditions; no additional axis is required merely to record them. Whether physiological corroboration deserves a distinct support dimension is an unresolved scoring-policy question. | Read exact existing/source performance/genotype records and supplied tables/images. No culture, animal, environmental competition or new single-cell experiment is available. |
| **A proposed function constrained by a complete chemical/resource account** | The named reaction or coupled system is compatible with actual substrates, products, cofactors, electron sources/sinks and required regeneration under explicit assumptions. Distinguish observed chemistry from feasibility. Bcd/Etf, F420, UbiUV, BioZ and ThyX show different missing or changed obligations. | An impossible account weakens the proposed route; a feasible account only removes that objection. Isotope/product evidence can constrain atoms or steps. A shared final product does not establish identical routes, native donor, flux or stoichiometry. | `reaction_context`/`mechanism` → `mechanistic`, while actual assays enter `empirical`. Typed reaction/source records preserve much chemistry; the score has no separate assumption-validity or thermodynamic-certainty operand. Structure homology and accounting therefore currently share a component despite different support relations. | `public.rhea.*`, `public.chebi.*`, source/typed-record readers. Native atom/electron balancing, thermodynamics and arbitrary arithmetic are not callable operations in the inspected map. |

No entry above is a complete episode definition, a task order or a fixed tool
bundle. The second slot supplies the thought pattern for deciding which
alternative to examine; the third is the actual relevant tool set selected from
the callable map. Literature episodes retain their separate implementation and
permitted child relationships. Sources about published annotations can inform
this bioinformatics support library without turning literature work into these
constructed bioinformatics investigations.

## What the five current components do and do not preserve

`empirical` is a valid code dispatch label for several recorded measurement
kinds. It is too broad to serve as a concrete first-slot entry by itself: a
purified-protein product assay, heterologous rescue, reporter response and native
survival effect do not establish the same proposition. The records can preserve
their different subjects, hypotheses and conditions already. Thus this is not
proof that every such contrast needs a new hypervolume dimension. A split is
justified only if the intended score should preserve those support contributions
separately rather than keep the current within-axis maximum.

`comparative` combines homologous sequence/profile support, arbitrary comparison
and gene prediction. A gene model is not functional homology. HisN shows that
higher sequence similarity does not order complementation support; TriA/AtzA
shows that very high identity does not transfer specificity. Assessments can
mark those overclaims `does_not_discriminate`, `weakens` or non-direct, so the
current code is not forced to make the wrong annotation. What is missing is an
explicit scientific-support basis joining the correspondence to the separately
characterized property. The score is not a calibrated homology model.

`mechanistic` combines structural correspondence and reaction accounting. TM0936
retains an amidohydrolase core despite wrong substrate transfer; Bcd requires a
correct coupled electron account. These are different sources of constraint.
The current schema can state both; the vector treats them as competing maxima
in one component. Splitting them would change how independent support combines
and therefore requires explicit policy, not a label change.

`biological_context` has no single support criterion: it accepts taxonomy,
composition, generic context and context measurements. Taxon or GC content alone
does not support a molecular function. Recurrent operon organization, conditioned
deployment and measured cellular access have different actual facts and failure
modes. Concrete support entries must specify those facts and bind their
assessments; simply renaming the component would leave the problem unchanged.

`discrimination` is a cross-cutting property of the interpretation, not a fifth
source class. It overlaps the second-slot choice to test alternatives, but a
thought pattern earns no credit until actual evidence distinguishes something.
Its current arithmetic deliberately gives additional volume to interpreted
negative/contrast evidence. That may be a desirable policy; it is not evidence
independence. Keeping it, conditioning it differently, or retaining the distinction as nonnumerical interpretation metadata outside
the multiplicative support dimensions is a user-visible score decision.

## Concrete arithmetic checks and schema gaps

The following are **synthetic operands evaluated with the unchanged existing
functions**, not computed scores for the published cases or the fixed gene.
They use the current default policy, one full-scope cell and its existing scale.

| Hypothetical operands | Components affected | Existing full-scope value |
| --- | --- | ---: |
| One supported, strengthening transfer comparison of weight .6 | `comparative=.6` | 0.1759530792 |
| Same observation also weakens an explicit alternative with weight .6 | `comparative=.6`, `discrimination=.6` | 0.6686217009 |
| Copied same-axis positive comparison | Still `comparative=.6` | 0.1759530792 |
| A genuinely separate same-axis positive comparison of equal weight | Still `comparative=.6` | 0.1759530792 |
| Weight-.6 support and weight-.6 opposition for the supported claim | `comparative=.375` | 0.1099706745 |
| One direct activity operand of weight1 | `empirical=1` | 0.2932551320 |
| Same assay also weakens an explicit alternative of weight1 | `empirical=1`, `discrimination=1` | 1.4662756598 |
| Weight1 direct support opposed by a weight-.6 transfer | `empirical=.625` | 0.1832844575 |

For a TriA-like or QueF-like contrast, the extra discrimination value is a real
feature of the existing proxy. It cannot be described as a second independent
assay. Conversely, source-independent corroboration in one axis currently adds
no volume beyond the maximum. These are tradeoffs to evaluate, not a numerical
bug proved by the labels.

The HisN/deaminase counterexample trace exposes a separate, concrete schema gap.
It retains Bc1793 SAH efficiency `<10` and Tvn0515 adenosine/MTA efficiency `<10`,
with computed ratio bounds `>37000` and `>26000`. The current numeric ATOM has
`value`, optional `approximate` and optional unspecified plus/minus uncertainty;
it has no `<`, `<=`, `>` or `>=` comparator. A retained quote can preserve the
text, but a bare number10 is not that censored measurement and zero is wrong.
A typed numeric bound operator is a justified schema proposal. The four HisN
candidates are not a classifier benchmark; complementation failure is not a
purified-enzyme null, and using the same proteins as HMM seeds and validation
would not supply independent validation.

## Concrete recommendation and alternatives for judgment

**Recommendation: define concrete first-slot support entries using the existing
record operands and the actual caller's annotation policy. Do not add a
`support_basis` record field now. Do not mask scientific progress, select another
projector or change numerical axes/weights as part of repairing the library.**
This recommends a minimal correction for judgment; no entry is adopted here.
It does not endorse the five existing labels as scientifically adequate categories.

The first-slot entry should declare its support proposition, the relevant actual
observation kinds and their component routes, the assessment relationships that
make those observations relevant, source/target applicability, required extent
semantics and known qualifications. For example, the sequence-transfer entry
can declare that the current default policy sends `alignment`, `profile_match`
and `comparison` to `comparative`. A characterized comparator's actual function
remains a separate `assay_report`/`biochemical_assay` source fact routed to
`empirical`; correspondence is not that assay. A target `functional_family`
claim and a target `catalyzes` claim are distinct existing hypotheses. Transfer
uses a justified non-direct assessment and bounded inferred attribution, rather
than declaring the source assay direct on the target. `does_not_discriminate`
can preserve ancestry while withholding exact-activity support. The original
source, observations, source subjects, conditions and hypothesis/assumption
references already retain the claimed characterization and correspondence.

The declaration is **library instruction metadata**, not a target observation,
another score, or a mandatory evidence-acquisition procedure. The existing
constructor must actually expose that metadata to the child; its present
descriptive field selection alone does not do so. The metadata must name the
actual bound policy's routes. A caller can override `observation_axes`, so the
five default names must not be silently treated as the caller's universal policy.
The existing caller-owned projector continues to score actual received findings
and annotation accounts. Selecting or reselecting a library label earns nothing.

The same approach is expressible now for the other retained distinctions:

- A gene-neighborhood/fusion or cross-organism association can use actual source
  features, contexts and observations with a bounded `participates_in` or
  `functional_family` hypothesis. The current policy usually sends context kinds
  to `biological_context`; this is a precise existing dispatch, not the support
  entry's name or a claim that the category is adequate. Unknown homolog calls,
  different strains and nonuniversal linkage remain explicit limits.
- An assay, complementation or native physiological perturbation can preserve
  its actual preparation/organism, readout and conditions through existing source
  subjects, contexts, observations and typed target hypotheses. `binds`,
  `catalyzes`, `requires`, `partner_dependence`, `participates_in`, `regulates`,
  `located_in` and `growth_capability` separate different conclusions. They do
  not automatically establish causal entailment. Most such reported tests use
  kinds mapped to `empirical`; keeping their maximum is a combination policy,
  not an inability to record the different results.
- A measured structure, structural comparison or reasoned chemical account can
  preserve its source, model/measurement origin, conditions, actual materials
  and uncertainty. `structure_match`, `mechanism` and `reaction_context` all map
  to `mechanistic` under the current default policy. That merger is again a
  policy choice. It does not mean a matching fold proves a reaction or an energy
  account proves that the reaction occurred.
- Negative/conditional findings, intact binding with lost conversion, processed
  proteins with failed assembly, condition-specific rescue, residual function,
  and opposing time-window outcomes can be separate existing source propositions
  with existing relations/qualifications. No additional score or record kind is
  required just to state them. Time/population reasoning belongs in the thought
  pattern and observation conditions, rather than becoming a new credit axis
  merely because the investigation used it.

The concrete retained-case **numeric representation addition** is an optional
bound operator. For example, a future typed activity value could retain
`value: 10`, its actual unit reference and `bound: "less_than"` for the reported
`<10`, with finite alternatives `less_than`, `less_or_equal`, `greater_than` and
`greater_or_equal`. Omission preserves an ordinary reported number; it must not
invent scientific exactness. The same supports IscR's `>1000 nM` IC50 values and
the retained deaminase ratio bounds. Currently a literal quote can preserve
these facts, and a qualitative qualified finding can be recorded, but a plain
numeric10 cannot faithfully encode `<10`. This addition would preserve data,
not change annotation weights. All consumers that currently treat a number as
an exact coordinate or extent must be checked before allowing such a bound in
their fields; an upper-bound query coverage must not become an exact measured
coverage. No other new target schema is demonstrated necessary merely to retain
the reviewed scientific distinctions. More automatic validation of genotypes,
causal controls or characterized-function transfer would be a separate specified
capability, not something this review pretends the current host already proves.

Three **numerical combination choices remain unresolved**:

| Choice for judgment | Current exact behavior | Consequence of changing it |
| --- | --- | --- |
| Preserve current component merging or split particular support contributions | Product assays, heterologous rescue and native physiological perturbations can all enter the same empirical maximum; structural transfer and chemical accounting share mechanistic; several organizational/deployment/access routes share context. | A split can reward corroboration that a maximum currently hides, but can also reward two dependent descriptions of one source. Extra dimensions change the product and scale even with otherwise unchanged weights. A library rename does not decide this. |
| Retain derived discrimination in the product or retain the distinction as nonnumerical interpretation metadata | The same qualifying/contrasting observation can affect a base component and discrimination, as the exact synthetic values above show. | Removing or conditioning this factor changes the existing reward for useful negative/contrast evidence. It is not a second independent experiment. No separate discrimination score is proposed. |
| Retain same-axis maximum or define an explicit provenance-aware accumulation | A copied same-axis observation and a genuinely separate equal-weight same-axis experiment both leave the maximum unchanged. | Accumulation would need an exact definition of repeated versus independent contributions and its numerical rule. The review supplies source dependence and exceptions, not invented probabilities or weights. |

YihU provides a concrete dependence test for the first choice: its published
kinetic measurements can be recorded as `assay_report` and enter `empirical`;
ratios calculated from those same measurements can be recorded as `comparison`
and enter `comparative`. The retained mutant ratios help reject a simple
active-amount-only explanation, but they are not another independent experiment.
Existing observation dependencies and source provenance can retain that
derivation; the current projector does not automatically remove cross-component
dependence. An added `support_basis` label alone would not solve it. The intended
reward for derived comparative interpretation versus additional evidence needs
an explicit policy decision.

My recommendation is to repair the first-slot definitions and their visible
relationship to **actual existing operands** before changing this combination
policy. If the user instead chooses different support dimensions or dispatch,
publish an explicit new policy/projection version and evaluate it prospectively.
Do not retrofit saved observations or quietly run additional dimensions over
closed histories. Keep received investigation progress, annotation support,
monitoring information and duration expectations separate throughout. These are
implementation decisions for review, not new runtime approval gates or stopping
rules.

## Verification of this review record

Validation checked exact partition membership, all 149 retained source-record
identities, original line-addressed or nested JSON values, recorded inspection status,
existing proposed kind/predicate/qualification enums and valid code-rule IDs.
The original case-register SHA-256 and both frozen draft-001 hashes matched.
The companion includes the eight synthetic unchanged-function arithmetic
scenarios, policy operands and outputs. Those checks are not per-case numeric
scoring, wet-lab work or a configured-model scientific demonstration. No model,
episode, worker, target observation, production edit, new axis or numerical
weight was created or adopted by this review.
