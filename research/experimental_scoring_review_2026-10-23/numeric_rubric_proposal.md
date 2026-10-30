# Rejected scoring-sheet proposal — correction, 2026-10-23

The original proposal below is preserved unchanged as a record of what the
assistant wrote. It is not a current implementation specification or an accepted
replacement for the user's template.

The proposed experimental relevance (R), measurement validity (V), attribution
(A) and transfer relevance (T) scales selected broad categories and assigned
numbers. They did not calculate each component from its individual measurable
contributions. Their products and worked grade changes therefore do not deliver
the requested scoring sheet. Calling the grades quality indices or proposals
does not correct this failure.

For example, the reported YeaG protein-abundance comparisons were used to select
attribution grades rather than thoughtfully converted into the user's
experimental-relevance calculation. The experimental arrangement and the
meaning of the abundance comparison must be established before deciding how
that measurement contributes. Neither the old grade nor the raw abundance ratio
alone establishes overall relevance.

The measurements, source references and YeaG endpoint correction remain research
material. Use them to populate and develop calculations within the user's
template. Do not treat this draft's four-factor organization, grade spacing,
ceilings or exact handoff as user requirements. The first scoring sheet remains
unfinished; this correction does not supply a replacement.

<!-- PRESERVED ORIGINAL BELOW -->

# Proposed numerical interpretation cells for experimental evidence

Later clarification: see the evidence-transfer addendum in
docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md. Evidence
transfer can rest on relationships other than sequence homology. The T ladder
below remains a candidate for review, not an adopted rule or a user-prohibited
component. Its retention here preserves the proposal that was actually made.

This is a concrete part-2 proposal for user review. It defines four numerical
cells and fills them on observed result–inference pairs. It does not adopt
weights, change an evidence axis or annotation-credit function, create an
episode or runtime gate, or design part-3 readers. The companion compilation
proposal supplies native signal, precision, comparable replication and the full
experimental-reliability calculation.

The proposed values are **annotation-quality indices, not probabilities**. A
value of 0.25 means one quarter of the contribution of an otherwise identical
row with value 1 under the proposed multiplicative compilation. It does not
mean a 25% probability that a function is correct. The ordering has observable
anchors; the numerical spacing is a normative choice, not empirically calibrated
by these retrospective cases. Giving the values this explicit numerical use is
a proposal to review, rather than relabeling an ordinal category as a measured
confidence.

## The actual numerical sheet

The scored object is one measured result or explicitly linked complementary
bundle, one bounded inference, and one declared target scope. An investigation
can start from supplied sequence, selected file contents or snippets. The
inference is recorded when it emerges; no initial annotation candidate or
searchable gene name is required.

| Scoring cell | Numerical domain | Question answered | Inputs needed to assign the number |
| --- | --- | --- | --- |
| **R — experiment-to-inference relation** | 0, 0.25, 0.5, 1; or an explicit unresolved set/range | Assuming the endpoint is real, correctly attributed and applicable to this system, how directly does it test the inferred operation? | Declared measured endpoint; inferred operation; the contrast or manipulation; what operation remains unmeasured. |
| **V — measured-readout validity** | 0, 0.25, 0.5, 1; or unresolved set/range | Does the measurement establish the declared endpoint under its measurement model? | Actual blanks, references, assay-competence/access checks, endpoint identification and relevant range/linearity validation; observed analytical failures. |
| **A — attribution to subject/property** | 0, 0.25, 0.5, 1; or unresolved set/range | Does this result belong to the named protein, component or molecular property at the specificity claimed? | Subject/component manipulations; restoration or reciprocal controls; protein amount and other relevant perturbation effects; specific competing sources. |
| **T — correspondence to the annotation target** | 0, 0.25, 0.5, 0.75, 1; or unresolved set/range | How much of this same bounded inference transfers from the established source scope to the declared target scope? | Supplied target material and boundaries; measured subject identity; relevant compartment, partner, substrate/cofactor, dose and environmental state; actual bridging comparisons. |

Each numerical entry requires its applicable anchor and the specific observed
comparison that establishes it. A source identifier or prose finding is not a
score. Those supporting records remain beside the numerical sheet. Native
measurements are retained with their units and uncertainty; none is replaced by
these four judgments. Missing source access is unknown, not a low grade for an
experiment whose controls have not been inspected.

For a reviewable handoff, define the **structural contribution factor**
`B = R × V × A × T`. This is only the interpretation-dependent part of the full
proposal. The experimental-reliability structural factor is `B_E = V × A`.
Signal resolution, precision and replication still have to act through the
companion calculation. Thus `B=1` does not mean perfect experimental reliability,
and `B_E=1` does not supply an unreported uncertainty or an independent repeat.

## Exact anchors

### R: which operation was tested?

| R | Observable anchor | Case-grounded meaning |
| ---: | --- | --- |
| **0** | The measured endpoint supplies no discriminating observation for this inference within the declared scope. | A result about one reaction does not establish an unrelated reaction. A valid contrary result is not R=0: it can be a direct test with R=1 and an opposing outcome. |
| **0.25** | An association, expression change, binding event or other proxy is compatible with the function, but the experiment does not measure the function or a required partial operation of it. | PopZ–ParB binding alone for cellular origin anchoring; YeaG induction alone for later survival. Stronger binding or induction does not change this anchor. |
| **0.5** | A required partial operation or experimentally linked downstream consequence is observed, but the defining operation/product of the inference is not measured. | CsiD-associated oxygen consumption for L-2-hydroxyglutarate formation: oxygen use can occur without the inferred productive chemistry. A completed cofactor half-reaction need not establish the complete reaction. |
| **1** | The defining endpoint is measured at the resolution stated in the inference. For a causal-dependence inference, the manipulated comparison measures that same endpoint. | SPR for binding under the tested conditions; chemical/stereochemical identification for product formation; deletion/addback plus origin imaging for PopZ-dependent polar origin residence. |

R deliberately assumes attribution rather than grading it again. A selectively
inactivated molecular property followed by failed rescue can directly test that
property's necessity for the measured phenotype. If selectivity of the
inactivation has not been established, A decreases; R is not decreased for that
same reason. Similarly, measured polymer formation can be R=1 for FtsW polymerase
catalysis while A assesses which component supplied that chemistry.

### V: was the stated readout measured validly?

| V | Observable anchor | Required distinction |
| ---: | --- | --- |
| **0** | A demonstrated analytical failure invalidates this stated endpoint: for example, a supposed product is shown to be another compound, or the measured increment is wholly accounted for by the measured blank. | This zero applies to the invalid endpoint, not every other result in the experiment. |
| **0.25** | A demonstrated measurement distortion affects the stated result, no adequate correction is available, and some endpoint information remains interpretable. | The distortion must actually be observed; an imagined possible artifact does not establish this grade. The retained information must be identified. |
| **0.5** | The endpoint has an interpretable response and relevant basic reference/control, but a specific measurement-model requirement remains unvalidated at the conditions used for the claimed numerical result. | CysQ low-substrate initial-rate behavior remains unconfirmed despite a good progress curve at a higher substrate concentration. This concerns model validity, not the size of its fitted error bar. |
| **1** | The reference/blank and assay-competence evidence support the declared endpoint, and the identified material analytical alternative is addressed by an appropriate discriminating comparison. No observed measurement-model failure remains within this narrow scope. | Authentic chemical standards/orthogonal chemical identity for HFP preparation isomerization; binding controls and reverse immobilization for the existence of PopZ–ParB binding; independent growth readouts for the YeaG recovery-growth phenotype. |

These are assay-specific observable requirements, not a count of controls. V=1
does not require every assay to have the same controls, or claim that every
conceivable artifact has been excluded. The assessor names the material
analytical alternative and the contrast addressing it. If that decision cannot
be made from inspected evidence, use an unresolved value.

V does not absorb missing precision, unknown preparation counts, a biological
proxy gap, target transfer or protein contamination. In HFP, the product can be
chemically identified with V=1 while its assignment to HFP has A=0. For a
negative result, validity of observing no signal is distinct from the sensitivity
needed to exclude a specified activity: an unknown detection bound remains a
missing native resolution input. It is not exact zero activity.

### A: who or what caused the measured effect?

| A | Observable anchor | Case-grounded meaning |
| ---: | --- | --- |
| **0** | A concrete competing source is supported or the stated assignment is invalidated, and the recorded result contains no separable target-specific contribution. | HFP-associated isomerization after common-preparation contamination and host RpiA evidence; a dependence conclusion built on a demonstrated wrong genotype. This is zero usable attribution from that result, not proof of absolute target inactivity. |
| **0.25** | The target-associated intervention or preparation changes the endpoint, but an actually observed co-change offers a material competing explanation and has not been separated. | YeaG K116A failed recovery-growth rescue at 64% of WT abundance. Reduced amount is observed; it is not proven to be the cause of failure. |
| **0.5** | A target-associated comparison supports the assignment and no observed competing co-change establishes the 0.25 anchor, but the experiment does not discriminate a named source/property alternative required by the inference. | K426A at 100% WT abundance still lacks a demonstrated selective loss of the claimed catalytic property; FtsW-plus-partner product alone does not assign catalysis between the components. A target-containing preparation versus no-enzyme control alone reaches this anchor for intrinsic target catalysis. |
| **1** | A discriminating target/component/property comparison addresses the identified competing assignment within the exact claim scope. | FtsW catalytic substitution together with active-site-inactivated bPBP distinguishes polymerase ownership in the tested complex; target loss and WT addback support target dependence of the measured phenotype. A catalytic-property claim additionally needs evidence that the intervention isolates that property. |

The last anchor is relative to the specificity of the inference. Selective
deletion/addback may suffice for a gene contribution while failing to establish
the gene product's catalytic mediation. The same experiment can therefore give
A=1 for gene contribution and A=0.5 for a more specific property assignment.
Changing the claim creates a distinct row with shared provenance; it does not
create a second independent experiment.

For HFP, A=0 is a proposed treatment of unusable positive attribution from a
confounded preparation. It does **not** imply that the fraction due to RpiA was
quantified, that every conceivable HFP contribution was experimentally excluded,
or that one should create a high-quality negative activity measurement. A
target-specific residual activity remains unmeasured.

### T: what reaches the declared target?

T is applied only to an additional source-to-target transfer of the **same
bounded inference**. It is not another penalty for the missing functional
endpoint already charged to R. Record which required determinant is matched,
different or unknown; do not average a list of matching metadata fields.

| T | Observable anchor | Meaning of the numerical entry |
| ---: | --- | --- |
| **0** | A feature required by this transfer is demonstrably absent/incompatible, or an actual matched transfer comparison shows that the claimed source behavior is not reproduced. | The source result supplies no positive contribution for this transfer. A contrary target measurement remains a separate opposing result; it is not discarded. |
| **0.25** | Subject correspondence is established, but a specified relevant condition actually differs and no comparison bridges its effect. | Same protein sequence with a changed compartment, dose or partner can occupy this anchor when incompatibility is not established. Sequence identity does not make the condition change disappear. |
| **0.5** | Subject correspondence and the identified required determinants are supported as matching by actual sequence/structure/context evidence, but this endpoint has not been tested across the source–target boundary. | This is a specifically documented transfer hypothesis, not a grade based on a percentage-identity cutoff or merely belonging to the same species. A missing required determinant leaves a range/unknown instead. |
| **0.75** | The same bounded endpoint is demonstrated in a stated source–target bridge, but one named relevant condition of the requested target still differs from that bridge. | For example, a matched homolog replacement establishes the endpoint in the target host under ectopic expression, while the requested native-dose inference remains untested. Both the measured bridge and the remaining condition must be identified. |
| **1** | There is no transfer beyond the declared measured/inferred source scope, or the same bounded endpoint is directly established in the requested target with its identified relevant conditions. | The exact tested exported-TrxA system is its own target. A more general native TrxA assignment is a different target scope. |

No annotation target material was supplied for this design exercise. Actual
user-target T cells therefore remain unknown. The worked examples below declare
their source-system demonstration targets explicitly; their T=1 means no
additional transfer, not a fabricated correspondence to an unseen sequence.

## Avoiding overlap and double penalties

Each stated weakness has one primary numerical home. Additional facts can expose
different weaknesses, but one fact must not automatically decrease several cells.

| Named weakness | Primary cell | Cells held unchanged for this reason |
| --- | --- | --- |
| Binding does not measure origin residence | R | V and A of the binding result; T when no additional source–target transfer is requested. |
| A real chemical reaction may belong to host contamination | A | V for the chemically identified product; R for observing that reaction. |
| A nominal catalytic mutation also lowers abundance | A | R for the causal phenotype comparison; V for the measured growth response. |
| The partner, rather than the nominated subunit, could supply catalysis | A | R for a measured product; V if product identification is intact. |
| Low-substrate time points were not shown to satisfy the rate model | V | Native precision remains as reported; do not reduce it a second time merely because of this same missing model check. |
| A protein is exported experimentally, while the requested target remains cytoplasmic | T | R for the same oxidation endpoint; V and A within the engineered source system. |
| Error bars or preparation independence are unreported | Native precision/replication cells in the companion proposal | R/V/A/T receive no invented penalty for the same absence. |

This division depends on explicit endpoint and scope. The same missing
observation must not be relabeled as several different weaknesses. A broader
claim can genuinely add a second requirement, such as both an unmeasured
mechanism and a new target organism; each limitation then needs its own distinct
factual basis.

## Filled result–inference examples

All values below are **proposed rubric applications**. Source scope is the
demonstration target unless a row explicitly names a transfer. `B_demo` is the
product of these four cells, not the completed reliability score. Native
precision/resolution can remain unknown even when this product is known.

| ID | Actual result and exact inference | Native information and discriminating comparison | R | V | A | T_demo | B_demo |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| P1 | PopZ–ParB binding exists under the tested SPR conditions. | Apparent Kd 20 nM; FtsZ/BSA controls and reverse immobilization. The uncertainty and preparation count are unknown. [Fig. 3D and main SPR procedures](https://pmc.ncbi.nlm.nih.gov/articles/PMC2745220/) | 1 | 1 | 1 | 1 | **1** |
| P2 | The same SPR result bears on PopZ-dependent native polar origin retention. | Binding supplies an association proxy; origin residence is not an SPR endpoint. The target is still the study's C. crescentus protein/system, with no additional organism transfer. [Fig. 3D](https://pmc.ncbi.nlm.nih.gov/articles/PMC2745220/) | 0.25 | 1 | 1 | 1 | **0.25** |
| P3 | PopZ contributes to stable polar origin retention in the studied cells. | Loss/addback, dynamic origin imaging, independent origin labeling and elongated-cell controls address the actual cellular endpoint. This does not establish every detail of a force-bearing mechanism. [Figs. 1–2 and main Results](https://pmc.ncbi.nlm.nih.gov/articles/PMC2745220/) | 1 | 1 | 1 | 1 | **1** |
| H1 | The HFP-containing preparation interconverts the two sugar phosphates. | 39.7% Ru5P / 60.3% R5P; NMR identity and reversibility. The preparation is the subject of this narrow statement. [Fig. 5](https://pmc.ncbi.nlm.nih.gov/articles/PMC12051542/) | 1 | 1 | 1 | 1 | **1** |
| H2 | The same preparation signal is assigned to intrinsic HFP isomerase activity. | Four of five unrelated preparations also isomerize; host RpiA is detected by MS. No target-specific residual is separated. The product remains real. [Competing-activity Results and main-text account of Figs. S7–S8](https://pmc.ncbi.nlm.nih.gov/articles/PMC12051542/) | 1 | 1 | 0 | 1 | **0** |
| Y1 | The AAA+ catalytic property is necessary for the studied recovery-growth phenotype, inferred from K116A failure. | K116A fails recovery-growth complementation at **64%** of WT amount. The observed abundance change remains a competing assignment. [Fig. 3A,C](https://pmc.ncbi.nlm.nih.gov/articles/PMC4664914/) | 1 | 1 | 0.25 | 1 | **0.25** |
| Y2 | The STK catalytic property is necessary for that recovery-growth phenotype, inferred from K426A failure. | K426A fails complementation at **100%** of WT amount. Abundance is addressed; a selectively catalytic defect is not directly established by the alignment-based substitution. [Fig. 3B,C](https://pmc.ncbi.nlm.nih.gov/articles/PMC4664914/) | 1 | 1 | 0.5 | 1 | **0.5** |
| F1 | FtsW supplies polymerase catalysis in the tested FtsW–bPBP complex. | Polymer formation requires the compatible partner; FtsW catalytic-Asp substitution removes it while TP-inactivated bPBP still stimulates it. Assay: 0.5 µM FtsW, 1 µM bPBP, 10 µM Lipid II, typically 30 min. [Figs. 1–2 and PGT methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC6430707/) | 1 | 1 | 1 | 1 | **1** |
| T1 | Exported TrxA promotes OmpA oxidation in the tested engineered dsbA background. | OmpA oxidation half-time changes from **60 to 5 min**; corrected genotype/partner comparisons qualify this system. The inference is conditional contribution, not direct reaction with every AP molecule. [Fig. 1 and Table 2](https://pmc.ncbi.nlm.nih.gov/articles/PMC94335/) | 1 | 1 | 1 | 1 | **1** |
| T2 | Transfer of T1's periplasmic oxidation role to the unexported, cytoplasmic TrxA comparison. | The required export is absent; the actual cytoplasmic comparison does not reproduce the exported phenotype. This zero concerns that transfer, not a claim of zero baseline OmpA oxidation. [Fig. 1 and Table 2](https://pmc.ncbi.nlm.nih.gov/articles/PMC94335/) | 1 | 1 | 1 | 0 | **0** |
| Q1 | The reported CysQ low-substrate apparent PAP Km is valid under the stated initial-rate model. | Km **8.1 ± 3.1 µM**; a 25 µM PAP progress curve has R² **0.993**, but low-substrate linearity could not be confirmed. No-enzyme controls and internal standard support the endpoint; the target-containing preparation alone leaves intrinsic attribution at 0.5 for this restricted packet. [Table 1 and MS kinetic Results/Methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC2711008/) | 1 | 0.5 | 0.5 | 1 | **0.25** |

Q1 scores the stated model parameter, not a blanket rejection of PAP hydrolysis.
Its ± type remains unknown in the inspected record. The fit's precision must not
be invented from its V grade. Likewise P1 scores the existence of binding, not
an assertion that the apparent SPR Kd is an artifact-free intrinsic affinity.

**YeaG endpoint correction:** the paired K116A/K426A comparison above is
recovery growth in Fig. 3. The separate survival experiment is Fig. 6:
Fig. 6A tests deletion/WT addback, and the Fig. 6B legend names K426A and Y382Stop.
It does not name K116A. The combined E2 packet in the lane review spans both
endpoints; it must not be read as K116A survival data. Retained primary text was
checked at `/tmp/episode-published-cases/cellular/PMC4664914.paragraphs.txt`,
Fig. 3 Results/caption and Fig. 6B caption. No exact mutant rescue fraction or
CFU effect was reconstructed.

## Numerical complement and counterfactual tests

The entries marked **counterfactual** are arithmetic design tests conditional on
the stated new result. They are not newly performed experiments or assertions
that the result would occur. The held-constant cells are shown to make the
specific repaired weakness reviewable. Complementary readouts do not become
independent repetitions.

| Comparison | Named weakness and status | Changed cell | Other cells held fixed | Change in B_demo |
| --- | --- | --- | --- | ---: |
| PopZ SPR alone → cellular loss/addback plus origin imaging | Actual complementary evidence measures the previously missing cellular endpoint. The bundle now supports the narrow cellular dependence inference. | R: 0.25 → 1 | V=A=T=1 | **0.25 → 1** |
| FtsW-plus-partner polymer alone → catalytic FtsW and TP-inactivated-partner contrasts | Actual component controls distinguish which component supplies polymerase catalysis. The first state is a deliberately restricted subset of the paper's evidence. | A: 0.5 → 1 | R=V=T=1 | **0.5 → 1** |
| K116A at 64% WT amount → matched-amount K116A that still fails recovery-growth rescue | **Counterfactual:** removes the observed abundance confound only. K426A is an actual comparator illustrating matched abundance; it is a different substitution and does not itself repair K116A. | A: 0.25 → 0.5 | R=V=T=1 | **0.25 → 0.5** |
| Matched-amount K116A or K426A failure → selective catalytic-loss validation with relevant folding/localization/interaction competence retained | **Counterfactual:** separates the claimed catalytic property from the remaining named perturbation alternative. | A: 0.5 → 1 | R=V=T=1 | **0.5 → 1** |
| CysQ low-substrate fit → a valid low-substrate progress/calibration experiment and appropriately refitted parameter | **Counterfactual:** repairs the specific initial-rate-model gap. A new numerical Km and its error would come from the new measurements; neither is assumed here. | V: 0.5 → 1 | R=T=1; A=0.5 | **0.25 → 0.5** |
| Same endpoint transferred only by correspondence → same endpoint measured in the target through an ectopic-expression bridge → measurement under its relevant native conditions | **Counterfactual transfer ladder:** first supplies a measured bridge, then removes the named dose-context remainder. This is not fulfilled by a sequence-identity percentage. | T: 0.5 → 0.75 → 1 | R=V=A=1 | **0.5 → 0.75 → 1** |
| More precise NMR of the same HFP preparation | Repairs precision of the preparation chemistry, not its attribution. | A stays 0; the native precision cell may improve | R=V=T=1 | **0 → 0** |

The HFP example also tests direction: adding contaminant-discriminating evidence
can change the earlier preparation-to-target attribution from A=0.5 to A=0.
That decreases this annotation contribution while increasing scientific
investigation progress. A genuinely target-specific new activity experiment
would be a new result/bundle with its own A; it would not retroactively purify or
rewrite the old observation.

As a further cross-assay check, CsiD oxygen consumption has R=0.5 for L2HG
formation, while NMR/LC-MS with enantiomer standards gives R=1 for that product.
The reported **53 ± 3 µmol min⁻¹ mg⁻¹** oxygen-consumption activity does not turn
into a measured product rate, stoichiometric coupling ratio or independent
replication. V and A need their own unchanged or separately supported entries;
the retained product-identification packet does not justify inventing a
target-specific attribution control. [CsiD Fig. 2 and product-identification
Methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC6265302/)

## Unknowns, handoff and limits

An unresolved cell is an explicit allowable set or range with the missing
operand. Examples are `T=unknown [0,1]` when no actual annotation target exists,
or `A in {0.5,1}` when a known target-associated comparison is available but
the inspection does not establish whether the discriminating attribution
control was performed. Those intervals describe unresolved rubric assignment,
not sampling uncertainty or a confidence interval. Do not insert the midpoint.
For nonnegative cells the corresponding product bounds can be propagated over
the compatible assignments. Known zero A or T makes this positive-contribution
product zero while other unknown cells remain visibly unknown.

The compilation handoff is exactly `(R,V,A,T)` plus these unresolved bounds and
the specific weakness-to-cell assignments. The companion proposal can use
`V×A` as its experimental-reliability ceiling and `R×V×A×T` as its target
contribution ceiling, with native signal/precision and genuinely comparable
independent evidence supplying the remaining numerical terms. A dependent
complement replaces the justified cell value for its linked bundle; it is not
an additional independent draw. A new citation, report or repeated extraction
of the same evidence changes no cell or contribution.

The unresolved normative choices for user review are the 0.25/0.5/0.75 spacing,
the multiplicative numerical use, the A=0 treatment of unusable positive
attribution despite an unmeasured residual, and the compressed T transfer
ladder. Their case-based meanings are explicit enough to challenge, but neither
empirical calibration nor cross-grader reproducibility has been demonstrated.
An honest unknown remains preferable to deciding that an uninspected source
has no control. Higher quality of a valid opposing result belongs in the
companion opposing-result calculation; these cells must never convert that
result into positive support merely because its quality is high.

Inspection for this proposal covered AGENTS.md, the evidence-axis amendment,
RESEARCH_SCOPE.md, SYNTHESIS.md, all three complete lane summaries and the
selected underlying case-review packets. Targeted retained primary passages
were checked for the HFP contamination interpretation and YeaG Fig. 3/6 endpoint
distinction. Browser attempts reached an HFP page and browser challenges for
the other selected PMC pages; they do not establish fresh complete primary
reading. No raw dataset, kinetic fit, gel or image was reanalysed. The existing
142-group corpus and its 21-group new-primary-reading accounting are unchanged.
No production code, reader, prompt, scoring policy or episode behavior was
changed.
