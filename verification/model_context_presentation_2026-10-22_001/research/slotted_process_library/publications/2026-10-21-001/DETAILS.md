# Full bioinformatics component content

The first scientific support slot is unavailable pending scoring-axis review. The old A claim headings are preserved only as nonselectable background; neither those headings nor existing scoring labels are accepted merely because they were written in files. P entries supply reusable thought patterns. The third slot receives multiple actual tools from retrieval, with their exact callable contracts. Published cases below provide provenance for bioinformatics reasoning; they do not define literature workflows. See [CURRENT_SLOT_SOURCES.md](CURRENT_SLOT_SOURCES.md).

## Scientific support slot: unavailable pending review

## Thought patterns

<a id="p01"></a>
### P01: Choose a relevant analogue and bound what transfers

- **description:** Use similarity to a characterized system to form bounded explanations. Choose which sequence, local structural machinery, domain architecture, genomic context or organismal circumstance makes the reference informative for the disputed property; revise misleading comparators.
- **use when:** A nearest hit, fold, motif or similar biological context suggests an annotation, but exact chemistry, recognition or role remains open.
- **live alternatives:** 
  - A relevant shared relationship supports transfer of the disputed property.
  - Only a partial core is shared; recognition, partners or role differ.
  - The comparator or short match is uninformative for this question.
- **decision guidance:** 
  - Prefer references that separate plausible alternatives, not simply the most familiar name or highest global score. Alignments, structures and context searches are ways to inspect a chosen relationship.
  - When a comparison is weak, consider a biologically better reference before treating it as evidence against all relationship.
  - Keep catalytic compatibility, target recognition and native role as separate transfer claims; absent catalytic machinery can overturn an inherited chemistry.
- **outcome contingencies:** 
  - 
    - **if observed:** Relevant machinery corresponds but specificity differs
    - **then consider:** Retain the supported relationship and investigate the differing recognition or contextual features.
  - 
    - **if observed:** Expected catalytic machinery is incompatible
    - **then consider:** Reopen chemistry and preserve only the relationship actually supported.
  - 
    - **if observed:** No informative correspondence is found
    - **then consider:** Keep function unresolved; absence of an informative match is not absence of function.
- **boundary:** Choose a comparator for transfer of a disputed biological property. P02 instead tests an explicit feature-to-function implication against discordant cases. A better sequence score, fold match or neighborhood is a tool result, not the transfer conclusion.

Source observations: E-P01-01, E-P01-02, E-P01-03, E-P01-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p02"></a>
### P02: Seek cases that break a proposed predictor

- **description:** Treat an implication as something that can fail. Prefer feature/function discordance: feature without function challenges sufficiency; function without feature challenges necessity.
- **use when:** An annotation is extended using a residue, motif, similarity rank, genomic partner or contact as a predictor.
- **live alternatives:** 
  - The feature is sufficient, necessary, both or merely correlated in the relevant domain.
  - Discordance is a real exception.
  - Apparent discordance reflects incomplete measurement or an inapplicable assay.
- **decision guidance:** 
  - Name the feature-to-function implication before selecting a comparison. Seek informative discordance rather than additional concordant relatives.
  - Keep blank genomic fields, assay limits and failed complementation distinct; none can silently become another kind of negative.
  - Compare alternative recognition or contextual explanations after an exception, without treating a post-hoc explanation as a validated replacement rule.
- **outcome contingencies:** 
  - 
    - **if observed:** Feature-positive/function-negative is established
    - **then consider:** Narrow sufficiency without automatically rejecting necessity.
  - 
    - **if observed:** Feature-negative/function-positive is established
    - **then consider:** Narrow necessity while retaining uncertainty about alternative mechanisms.
  - 
    - **if observed:** The supposed negative is unmeasured or inapplicable
    - **then consider:** Retain unresolved status and seek an informative comparator.
- **boundary:** A feature/function counterexample tests an implication without establishing classifier accuracy. P01 bounds transfer from an analogue; P17 additionally requires evidence that a causal perturbation selectively changed one property while relevant alternatives survived. Natural discordance alone does not establish causal selectivity.

Source observations: E-P02-01, E-P02-02, E-P02-03, E-P02-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p03"></a>
### P03: Discriminate competing inputs by their predicted chemistry

- **description:** Keep the candidate system explicit while choosing substrates, co-substrates or acceptors that distinguish competing recognition hypotheses. Refine the candidate space using identified products and bounded non-products.
- **use when:** Several chemically plausible inputs remain and another family match will not distinguish them.
- **live alternatives:** 
  - Candidate inputs differ at a recognized chemical feature.
  - A side reaction is being mistaken for the preferred reaction.
  - Apparent specificity belongs to another preparation component or coupled partner.
- **decision guidance:** 
  - Choose contrasts changing the feature on which the hypotheses disagree, including close analogues and plausible pathway inputs.
  - Positives may motivate adjacent candidates omitted from the initial library; unavailable compounds remain untested.
  - Interpret the profile at the level of the assayed preparation with conditions and product identity retained; component attribution may need P06.
- **outcome contingencies:** 
  - 
    - **if observed:** A coherent product pattern supports one recognition hypothesis
    - **then consider:** Narrow the tested profile and choose an informative untested boundary.
  - 
    - **if observed:** An attractive input fails under competent conditions
    - **then consider:** Revise input recognition without discarding every supported catalytic relationship.
  - 
    - **if observed:** Comparative kinetics or products are missing
    - **then consider:** Report bounded capacity rather than rank untested native inputs.
- **boundary:** The unknown is which input or recognized chemical feature differentiates candidate reactions in a fixed system. P14 instead asks what transformation actually occurred; P06 asks which component caused it; P11 asks whether the measured capacity is used natively. A proposed assay panel is not an available tool or an instruction to perform new experiments.

Source observations: E-P03-01, E-P03-02, E-P03-03, E-P03-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p04"></a>
### P04: Revise the failed attachment while retaining independent constraints

- **description:** After a competent negative or contradiction, separate the part of the explanation that failed from independently supported constraints. Reopen alternatives within surviving constraints without either preserving the whole annotation or discarding everything.
- **use when:** A reaction or familiar-function assignment fails while pathway placement or another biological association remains supported.
- **live alternatives:** 
  - The reaction was wrong but independent placement survives.
  - The association itself was misleading.
  - The test was not competent to evaluate the proposed function.
- **decision guidance:** 
  - Identify independent support for each part of the old explanation before deciding what survives.
  - Use surviving branch boundaries, required chemistry and distribution to construct a limited alternative set.
  - Preserve association-only wording when no exact replacement reaction is established.
- **outcome contingencies:** 
  - 
    - **if observed:** Reaction fails but independent placement survives
    - **then consider:** Investigate a different compatible transformation.
  - 
    - **if observed:** A new identified product establishes an alternative
    - **then consider:** Replace the failed reaction while retaining unresolved mechanism/native-use questions.
  - 
    - **if observed:** No alternative is established
    - **then consider:** Return the supported association and explicit unresolved claims.
- **boundary:** The starting state is a failed or contradicted attachment to an existing explanation, with independent surviving constraints. P05 starts from a supported system requirement without an assigned contribution. No old claim survives merely because it was recorded; failed expression or retrieval is not a negative activity result.

Source observations: E-P04-01, E-P04-02, E-P04-03, E-P04-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p05"></a>
### P05: Constrain missing-function hypotheses by what the system must accomplish

- **description:** Use a supported output or requirement to distinguish loss of function, unfamiliar replacement, different route and changed demand. Evaluate candidate similarities and context against these system explanations.
- **use when:** A familiar enzyme is missing or a required conversion has no assigned protein despite evidence that the output exists or is needed.
- **live alternatives:** 
  - Capability is absent or supplied environmentally.
  - An unfamiliar protein supplies the same contribution.
  - A different route reaches the output or bypasses the requirement.
  - The presumed system requirement is wrong here.
- **decision guidance:** 
  - Specify the required input/output or demand before choosing families.
  - Prefer distribution, domain combinations and context distinguishing explanations, including pathway-negative organisms when available.
  - Allow an alternative to change the reaction boundary; replacement need not copy every activity of the familiar protein.
- **outcome contingencies:** 
  - 
    - **if observed:** Candidate tracks the contribution and functional evidence agrees
    - **then consider:** Support the demonstrated contribution; association alone remains a candidate assignment.
  - 
    - **if observed:** Output persists without the familiar route
    - **then consider:** Retain replacement and bypass alternatives.
  - 
    - **if observed:** Only a missing label or textbook gap exists
    - **then consider:** Keep completion provisional instead of assigning a gene to fill a diagram.
- **boundary:** The starting state is a missing explanation for a supported system output or demand, not merely an empty gene label. P04 reopens a failed assignment; P19 explains output retained after a focal loss; P07 explains an endpoint improved by an intervention. This is system-level abduction, not a gene-search task or one-gene-per-step rule.

Source observations: E-P05-01, E-P05-02, E-P05-03, E-P05-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p06"></a>
### P06: Retain the system output and revise who contributes what

- **description:** Keep a real aggregate output separate from its attribution. Compare direct chemistry, substrate/cofactor supply, enabling a complex, downstream filtering and production of an observable signal.
- **use when:** A mixture, complex or cellular endpoint is being used to assign the intended component a molecular job.
- **live alternatives:** 
  - The nominated component performs the transformation.
  - It enables or supplies another contributor.
  - A partner or contaminant creates/filters the signal.
  - The output is real but its source remains unresolved.
- **decision guidance:** 
  - Choose a comparison separating the live contributor assignments while preserving relevant system competence.
  - Independent preparation, selective partner changes, defined systems or positive structural roles can update attribution; no layout is mandatory.
  - Keep the genuine output after attribution fails, and seek a positive contribution rather than an empty scaffold label.
- **outcome contingencies:** 
  - 
    - **if observed:** Changing a downstream partner changes apparent upstream specificity
    - **then consider:** Bound the result to the coupled pair.
  - 
    - **if observed:** Activity follows an identified host protein instead of the intended construct
    - **then consider:** Reassign the activity while leaving the original candidate unresolved.
  - 
    - **if observed:** Positive evidence separates catalytic and enabling roles
    - **then consider:** Assign bounded distinct contributions; unvalidated catalytic-null labels cannot prove dispensability.
- **boundary:** The system output is accepted at its measured scope; the disputed relation is who contributes what. P14 instead disputes the identity of the transformation. P10 disputes the coupled chemical account. P02/P17 address predictor validity or selective necessity rather than assigning all mixture output to its named component.

Source observations: E-P06-01, E-P06-02, E-P06-03, E-P06-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p07"></a>
### P07: Distinguish restoration from bypass, compensation and reduced demand

- **description:** An improved endpoint can repair the proposed molecular relationship, use another route, reduce demand or change downstream consequences. Compare those explanations before treating rescue as mechanistic equivalence.
- **use when:** Complementation, suppressors, adaptive recovery or supplementation improve an endpoint after a focal loss.
- **live alternatives:** 
  - The original molecular contribution is restored.
  - Another route reaches the endpoint.
  - Demand for the contribution is reduced.
  - Only a downstream consequence improves.
- **decision guidance:** 
  - Name the molecular defect rescue is supposed to repair, then seek a comparison separating repair from endpoint compensation.
  - Multi-step bypass, reintroduced lost functions and separate molecular readouts can distinguish the alternatives.
  - Restrict equivalence to the contribution/conditions restored; donor expression does not establish ordinary native role.
- **outcome contingencies:** 
  - 
    - **if observed:** Endpoint recovers while proposed catalytic defect persists
    - **then consider:** Retain compensation or bypass rather than claim molecular repair.
  - 
    - **if observed:** Replacement bypasses several steps or changes cofactor demand
    - **then consider:** Assign the alternative route instead of copying the missing-enzyme name.
  - 
    - **if observed:** Only some outcomes are restored
    - **then consider:** Represent partial/conditional substitution.
- **boundary:** The starting observation is an endpoint improved by rescue, suppression or compensation. The unknown is whether the original molecular contribution was restored. P19 starts from output that never disappeared after focal loss; P05 starts from an unassigned requirement. Positive rescue does not by itself establish isolated chemistry or full reference-function equivalence.

Source observations: E-P07-01, E-P07-02, E-P07-03, E-P07-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p08"></a>
### P08: Test the missing prerequisite behind conditional function

- **description:** Investigate which enabling resource or molecular state permits a supported capability to matter. Distinguish that prerequisite from correlated stress, altered protein amount and reporter failure.
- **use when:** A preparation is inactive or a gene dispensable in one setting despite evidence for a contribution elsewhere.
- **live alternatives:** 
  - A missing cofactor, partner, nutrient, acceptor or resource context enables the function.
  - The capability is absent or irrelevant.
  - The condition changes abundance, another route or reporter competence instead.
- **decision guidance:** 
  - Choose a motivated prerequisite for which the competing explanations predict different outcomes; arbitrary condition variation is insufficient.
  - Contrast focal genotype/protein state across independently varied prerequisite states with identity and competence controls.
  - A successful addition needs molecular/identity evidence before being called direct catalysis or sensing.
- **outcome contingencies:** 
  - 
    - **if observed:** Independent resource-generating changes alter both resource and genotype-specific benefit
    - **then consider:** Support resource-conditioned contribution.
  - 
    - **if observed:** Cofactor-complete preparation gains identified activity
    - **then consider:** Do not use incomplete preparation as functional falsification; keep native delivery unknown.
  - 
    - **if observed:** Only abundance or reporter competence changes
    - **then consider:** Retain indirect alternatives.
- **boundary:** The unknown is which biological prerequisite explains a difference between conditions or preparations. P11 asks whether a demonstrated capacity is used natively; P12 distinguishes temporal consequences. Cofactors, partners and nutrient access are biological operands, not extra slots or execution-resource forecasts. Available records may leave the prerequisite unresolved.

Source observations: E-P08-01, E-P08-02, E-P08-03, E-P08-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p09"></a>
### P09: Separate physical access from chemical competence

- **description:** Explain a missing cellular reaction by contrasting inaccessible substrate/partner, absent substrate, failed catalyst and failed reporter delivery. Prefer changes that discriminate the relevant barrier.
- **use when:** Isolated capability disagrees with cellular function or a compartment-specific readout disappears.
- **live alternatives:** 
  - Catalyst is competent but cannot contact its substrate/partner.
  - Substrate is missing or sequestered on the wrong side.
  - Reporter fails to reach/detect available substrate.
  - Catalyst itself is defective.
- **decision guidance:** 
  - Name the barrier and entities whose contact is disputed; fractionation alone cannot settle it.
  - Different barriers/targeting regions are separate alternatives; global disruption does not identify every native route.
  - Relocation or targeting contrasts can test whether partner/compartment access changes the supported outcome.
- **outcome contingencies:** 
  - 
    - **if observed:** Removing one barrier fails but exposing across another restores the readout
    - **then consider:** Narrow the access explanation while retaining reporter controls.
  - 
    - **if observed:** Export/cleavage succeeds but native output fails
    - **then consider:** Only upstream access is established; downstream compatibility can become P15.
  - 
    - **if observed:** Only prediction or growth is available
    - **then consider:** Keep access provisional; neither establishes direct flux or orientation.
- **boundary:** The unknown is a contact barrier between a competent catalyst, substrate, partner or reporter. P08 concerns other enabling prerequisites; P15 accepts an upstream event and asks what additional compatibility separates it from downstream success. Membrane association or a topology prediction alone does not establish transport, orientation or flux.

Source observations: E-P09-01, E-P09-02, E-P09-03, E-P09-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p10"></a>
### P10: Account for the coupled chemical system

- **description:** Choose an explicit account of matter, electrons, cofactors and energy needed for a conversion. Reopen incomplete boundaries when an isolated reaction is implausible or replacement changes metabolic demand.
- **use when:** Output conflicts with a redox/stoichiometric account, or routes with the same product may require different support.
- **live alternatives:** 
  - A consumed partner or favorable coupled reaction is missing.
  - Partial uncoupling or another conversion alters the account.
  - Same output hides changed input/cofactor recycling demand.
  - Chemistry remains unsupported under stated assumptions.
- **decision guidance:** 
  - Choose the boundary and track relevant atoms/electrons/cofactors before calculating.
  - Kinetic activation does not supply missing thermodynamic driving force.
  - Keep measured balances distinct from ideal fully coupled ratios and preserve unknown potentials/recovery.
  - Use route-specific demands to identify which biological comparison distinguishes apparent output equivalence.
- **outcome contingencies:** 
  - 
    - **if observed:** A coupled account resolves the isolated energy deficit
    - **then consider:** Retain feasibility under assumptions; occurrence requires separate evidence (P11).
  - 
    - **if observed:** Measured ratio differs from the ideal
    - **then consider:** Preserve measurement and consider uncoupling/incomplete recovery.
  - 
    - **if observed:** Replacement changes a recycled product/cofactor
    - **then consider:** Expose the changed demand instead of asserting full interchangeability.
- **boundary:** The episode chooses the biological reaction boundary and missing coupled chemistry; a calculator only evaluates the selected account. P06 asks who supplies the output, P07 asks what rescue restores, and P11 asks whether a feasible account is used. Standard-potential feasibility is not measured cellular free energy or native flux; no credit weight is supplied.

Source observations: E-P10-01, E-P10-02, E-P10-03, E-P10-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p11"></a>
### P11: Distinguish a possible route from the route actually used

- **description:** Keep feasibility or measured capacity separate from native use. Contrast ordinary use, conditional backup, side activity and unused capacity without forcing a single-role explanation.
- **use when:** A reaction, model, structure or environmental gene detection is being promoted to main native role or actual flux.
- **live alternatives:** 
  - Capacity supplies the proposed native contribution.
  - It supplies a conditional backup/secondary role.
  - It is side activity or possible chemistry without demonstrated use.
  - Another route supplies the native output.
- **decision guidance:** 
  - Select observations with different expected consequences for native use and mere capacity: endogenous products, demand-specific perturbations or competing routes.
  - Retain genuine earlier side activity when a better native role appears; compatible conditional roles need not be exclusive.
  - Compare plausible exposure/kinetics without inventing concentrations or native substrates.
- **outcome contingencies:** 
  - 
    - **if observed:** Independent native observations agree
    - **then consider:** Support use under those conditions, not total flux or exclusivity.
  - 
    - **if observed:** Only overexpression/high-dose/artificial activity is positive
    - **then consider:** Retain bounded capacity with ordinary responsibility unresolved.
  - 
    - **if observed:** A stronger native explanation is established
    - **then consider:** Revise priority/scope without deleting genuine prior chemistry.
- **boundary:** The unknown is native use of a demonstrated or feasible capacity, including conditional secondary roles. P08 asks which prerequisite enables an effect; P10 asks whether the coupled chemical account is feasible. These are discriminating explanations, not acceptance gates, and a source annotation cannot establish native use by itself.

Source observations: E-P11-01, E-P11-02, E-P11-03, E-P11-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p12"></a>
### P12: Compare biological consequences over the time that matters

- **description:** Choose time/phase contrasts distinguishing transient acceleration, repeated function, adaptation and survival. An early benefit or first product need not predict later outcomes.
- **use when:** Interpretation depends on when an effect appears, how long function is needed or whether operation must repeat.
- **live alternatives:** 
  - Effect is durably beneficial.
  - Early acceleration carries a later maintenance/survival cost.
  - First event succeeds but repeated operation fails.
  - Original observation window missed the relevant phase.
- **decision guidance:** 
  - Choose intervals from biological alternatives rather than a universal cadence.
  - Keep lag, growth, viability and repeated turnover as distinct outcomes.
  - Preserve differing early/late conclusions and investigate explanations that predict both.
- **outcome contingencies:** 
  - 
    - **if observed:** Recovery improves but later survival falls
    - **then consider:** Represent both outcomes in their windows.
  - 
    - **if observed:** One product forms but repeated turnover fails
    - **then consider:** Narrow the missing contribution toward sustained operation.
  - 
    - **if observed:** A later phase exposes a phenotype
    - **then consider:** Restrict the early nonphenotype without pretending it observed the later result.
- **boundary:** The competing explanations differ in phase, duration or repeated operation, rather than merely being measured at different times. P13 separates biological units or mixtures at a relevant resolution; P08 tests a prerequisite. A setting-and-time difference such as ex-vivo versus infection does not isolate a temporal effect. This supplies no execution timer or stopping rule.

Source observations: E-P12-01, E-P12-02, E-P12-03, E-P12-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p13"></a>
### P13: Resolve an aggregate claim at the biological level that separates explanations

- **description:** Ask whether pooled change reflects uniform effects, selective subsets or changed mixtures. Choose biologically meaningful units whose contrasts separate those explanations.
- **use when:** A population, protein or process label pools outcomes with potentially different biological meanings.
- **live alternatives:** 
  - Units change similarly.
  - A subset changes while others retain function.
  - Mixture/baseline changes rather than each unit’s response.
  - Missing/censored/differently normalized measurements leave quantification open.
- **decision guidance:** 
  - Choose resolution from the competing biological explanations, not just because finer data exist.
  - Compare affected/retained units while preserving baseline versus response and readout definition.
  - When needed resolution was not measured, qualify the aggregate claim rather than impute cell fates, occupancy or missing values.
- **outcome contingencies:** 
  - 
    - **if observed:** Retained units contradict uniform loss
    - **then consider:** Bound dependence to the affected subset.
  - 
    - **if observed:** Distributions differ beyond a simple average shift
    - **then consider:** Retain heterogeneous-state explanations; fate needs independent evidence.
  - 
    - **if observed:** Site/condition records do not support pooling
    - **then consider:** Return separate records; missing ratios are not zero abundance.
- **boundary:** The competing explanations differ across biologically meaningful units or mixtures, not simply across more rows in a table. P12 contrasts phases or repeated operation. Record identity and normalization remain prerequisites for either pattern; finer extraction alone is a tool task and a changed phosphosite does not establish direct catalysis.

Source observations: E-P13-01, E-P13-02, E-P13-03, E-P13-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p14"></a>
### P14: Distinguish the transformation from its proxy readout

- **description:** Treat bands, cofactor changes, substrate loss and downstream signals as compatible with several transformations. Prefer evidence separating intended chemistry from half-reactions, spontaneous conversion or artifacts.
- **use when:** A proxy is naming a reaction without establishing what actually changed.
- **live alternatives:** 
  - Proxy reflects identified intended product.
  - A half-reaction/alternative creates the same proxy.
  - A spontaneous downstream step follows different enzyme chemistry.
  - Disappearance/migration changes without productive conversion.
- **decision guidance:** 
  - Name rival transformations before selecting product, labeling, temporal or chemical-competence evidence.
  - Keep genuine partial chemistry when full product is absent.
  - Structural plausibility can guide discrimination but cannot identify the chemistry alone.
- **outcome contingencies:** 
  - 
    - **if observed:** Identified products/labeled atoms distinguish the event
    - **then consider:** Assign that transformation at tested scope.
  - 
    - **if observed:** Proxy persists without expected product
    - **then consider:** Reopen partial/alternative chemistry.
  - 
    - **if observed:** Only disappearance or band shift is observed
    - **then consider:** Record it specifically; productive synthesis stays open.
- **boundary:** The disputed relation is what transformation occurred, including whether a proxy reflects a half-reaction or spontaneous downstream event. P06 instead asks who caused an established output; P03 compares recognized candidate inputs. Product-identifying author experiments are source evidence, not newly available wet-lab actions.

Source observations: E-P14-01, E-P14-02, E-P14-03, E-P14-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p15"></a>
### P15: Hold upstream success while investigating downstream failure

- **description:** Preserve demonstrated recognition, binding, cleavage or delivery when productive output fails. Compare the additional compatibility or coupling explanations rather than repeat upstream positives.
- **use when:** Binding/processing is being treated as sufficient for catalysis, assembly, regulation or organismal output.
- **live alternatives:** 
  - Upstream engagement is sufficient here.
  - Another structural/chemical/partner constraint blocks progression.
  - Upstream readout differs or was misidentified.
  - Downstream measurement is incompetent.
- **decision guidance:** 
  - Seek contrasts with upstream competence but differing downstream outcomes.
  - Separate unexpressed constructs from expressed/processed variants.
  - If progression remains unexplained, return separated outcomes instead of inventing a mechanism.
- **outcome contingencies:** 
  - 
    - **if observed:** Both substrates bind but only one converts
    - **then consider:** Narrow productive recognition beyond binding.
  - 
    - **if observed:** Expressed processed variant fails assembly
    - **then consider:** Support an additional compatibility requirement without assigning its mechanism.
  - 
    - **if observed:** Only upstream event is known
    - **then consider:** Leave final role unresolved.
- **boundary:** The accepted starting evidence establishes an upstream event while the downstream outcome differs or remains unknown. P09 disputes physical contact; P17 requires selective causal perturbation with retained alternative properties. P15 can preserve a downstream unknown without isolating its cause; no recognize–process–assemble itinerary follows.

Source observations: E-P15-01, E-P15-02, E-P15-03, E-P15-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p16"></a>
### P16: Distinguish direct input action from indirect response and feedback

- **description:** Environmental responses can arise through direct ligand recognition, cofactor chemistry, changed abundance or system-demand feedback. Choose contrasts distinguishing those routes before assigning a direct sensor or regulatory sign.
- **use when:** Induction, binding or physiology is being treated as proof of direct signal recognition.
- **live alternatives:** 
  - Input binds the regulator.
  - Input changes a cofactor/state without selective ligand binding.
  - Partner demand/feedback mediates the response.
  - Abundance or another regulator explains it.
- **decision guidance:** 
  - Keep signal, molecular state, amount, DNA recognition and productive regulation distinct.
  - Choose contrasts controlling the relevant alternatives, including target classes and feedback demand.
  - Direct binding addresses recognition; promoter binding alone proves neither signal binding nor transcriptional sign.
- **outcome contingencies:** 
  - 
    - **if observed:** Purified protein binds input with informative controls
    - **then consider:** Support assay-specific binding without claiming the whole native mechanism.
  - 
    - **if observed:** State controls distinguish cofactor chemistry from feedback
    - **then consider:** Retain compatible supported routes; do not call a chemical input a selective ligand.
  - 
    - **if observed:** Response is known but direct action untested
    - **then consider:** Report response with sensing route unresolved.
- **boundary:** The disputed relation is how a biological input reaches a regulatory response, not general response correlation or component attribution. P06 assigns contribution to an established system output; P08 asks which prerequisite enables function. Direct ligand binding, cofactor chemistry and feedback are different explanations; promoter binding alone supplies neither input sensing nor transcriptional sign.

Source observations: E-P16-01, E-P16-02, E-P16-03, E-P16-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p17"></a>
### P17: Separate linked functions through selective dissociation

- **description:** Seek comparisons preserving one property while changing another. Use their dissociation to distinguish a required functional relation from amount, delivery, stability or another linked activity.
- **use when:** A mutant phenotype is assigned to one molecular function despite several potentially affected properties.
- **live alternatives:** 
  - Named function is required.
  - Amount/localization/assembly/another function explains the effect.
  - Distinct connections jointly contribute but can reside on different molecules.
  - The measured activity and native role dissociate.
- **decision guidance:** 
  - Prefer positive evidence that alternative properties survive; a failed construct is not automatically selective.
  - Reciprocal/complementary contrasts are informative when their predicted results differ, without requiring them universally.
  - Keep incomplete perturbation validation as a limit rather than claiming a specific null from its label.
- **outcome contingencies:** 
  - 
    - **if observed:** Function fails despite retained amount/delivery
    - **then consider:** Exclude simple instability/mislocalization without inventing direct binding.
  - 
    - **if observed:** Complementary defects restore function but same-defect controls do not
    - **then consider:** Support joint contribution of distinct connections.
  - 
    - **if observed:** Endpoint survives a supposed catalytic-null mutation without null validation
    - **then consider:** Do not infer catalytic dispensability from the label.
- **boundary:** The contrast must preserve relevant alternative properties while perturbing a proposed causal relation. P02 can use natural feature/function discordance without causal selectivity; P15 can preserve successful upstream and failed downstream events without isolating the cause. Ordinary suppression is not reciprocal separation-of-function evidence; mutagenesis is not an available operation merely because a case reports it.

Source observations: E-P17-01, E-P17-02, E-P17-03, E-P17-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p18"></a>
### P18: Explain conflicting biological results with discriminating scope contrasts

- **description:** Compare incompatible biological claims by testing whether a difference in organism, molecular state, assay window, relation or construct predicts the disagreement. Preserve genuine conflict when available observations do not distinguish the explanations.
- **use when:** Studies or assays appear to support incompatible assignments or dependencies.
- **live alternatives:** 
  - Results genuinely conflict under comparable conditions.
  - Both hold in different states/organisms/windows.
  - A proxy has been given a stronger interpretation.
  - A specific construct or record error explains a result.
- **decision guidance:** 
  - State the incompatible biological relations and the matching conditions needed for a real contradiction; source identity does not decide which relation is correct.
  - Seek evidence testing the proposed explanation, not just metadata differences.
  - Plausible scope differences are not resolutions until a discriminating comparison exists.
- **outcome contingencies:** 
  - 
    - **if observed:** A corrected construct/condition is linked to the discrepancy
    - **then consider:** Revise only the interpretation supported by the correction.
  - 
    - **if observed:** Scope explanation remains untested
    - **then consider:** Retain conflict and the missing comparison.
  - 
    - **if observed:** Records concern different outputs/phases
    - **then consider:** Restrict claims without calling them equivalent replications.
- **boundary:** The starting evidence contains incompatible biological claims at apparently comparable scope; the problem is to test an explanation for the disagreement. P04 revises a failed attachment within one explanation. Organism, condition or construct differences are candidate explanations, not automatic resolutions. This is not a publication search, paper-ranking or literature-reading process, and no observation or saved credit is rewritten.

Source observations: E-P18-01, E-P18-02, E-P18-03, E-P18-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p19"></a>
### P19: Investigate the route behind residual function

- **description:** Preserve reproducible output after a focal loss while distinguishing another contributor from incomplete perturbation, imported product or reduced demand. Revise exclusivity without erasing the lost route’s genuine contribution.
- **use when:** Knockout/depletion leaves growth, product or activity unaccounted for by the current explanation.
- **live alternatives:** 
  - Another contributor supplies residual output.
  - Perturbation is incomplete or a suppressor restores original activity.
  - Environmental supply or bypass reduces demand.
  - Residual readout is an artifact or different output.
- **decision guidance:** 
  - Choose a contrast within the residual-function background separating an alternative contributor from remaining original activity or supply.
  - Restoration/independent activity can clarify attribution without settling every native route/cofactor.
  - Combined perturbations are recorded evidence or candidate work, not an automatic requirement for new experiments.
- **outcome contingencies:** 
  - 
    - **if observed:** Additional loss removes residual output and restoration recovers it
    - **then consider:** Support overlap at measured scope, not universal exclusivity.
  - 
    - **if observed:** Output depends on supply or unremoved activity
    - **then consider:** Restrict redundancy to the actual bypass/perturbation.
  - 
    - **if observed:** Residual route cannot be assigned
    - **then consider:** Return retained function with its source unknown.
- **boundary:** The starting observation is reproducible output retained after a focal loss. P05 explains a missing assignment for a system requirement; P07 explains an improved endpoint after intervention. Residual function permits alternative contributors but does not identify them, and combined-gene evidence does not isolate every member.

Source observations: E-P19-01, E-P19-02, E-P19-03, E-P19-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).
