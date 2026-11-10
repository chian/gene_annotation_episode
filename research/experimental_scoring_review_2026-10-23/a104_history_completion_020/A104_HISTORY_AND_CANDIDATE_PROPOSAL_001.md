# A104: numerical completion of history explanation and candidate reduction

Goal: finish the two undefined numerical meanings identified by the parent
review: a biologically broader explanation for a specified phylogenetic
discordance, and A104's contribution for one persistent candidate across its
relevant inferences and regions. A usable proposal must contain operands,
units, denominators, arithmetic, missingness, source contrasts, checked complete
examples and exact unimplemented reader interfaces. This document supplies one
such proposal for judgment. It does not adopt policy or complete an axis. A105
remains first in the unchanged ten-axis checklist.

This is an additive proposal relative to the complete
`../a104_phylogeny_sheet_012/A104_NUMERICAL_SHEET_DRAFT_001.md` and
`../a104_sheet_construction_001/A104_FORMULA_REVIEW_001.md`. Those files and the
original checker were read completely and remain unchanged. Every numerical
rule below is proposed by this worker unless identified as measured or
source-derived. No production scorer/reader, library prompt, target annotation,
phylogenetic reconstruction, native bioinformatics job or HPC job was run.

## 1. What changes and what stays distinct

Retain the existing region-level placement P, distance O, topology-concordance
counts, and positive/opposing calculation. Replace the narrow explanation
`E=(contact-time fraction + normalized laboratory transfer rate)/2` with:

\[
\boxed{E_k=T_k\,{B_k+M_k\over2}}. \tag{1}
\]

Here B is environmental/route compatibility, M is the fraction of the stated
cargo associated with the specified transfer-capable unit, and T is temporal
feasibility of that particular donor-to-recipient event. These are separately
populated components. Neither present-day contact duration nor a laboratory
transfer-rate assay is compulsory. Existing contact/rate observations remain
valid, separately named facts; equation (1) is a new proposal, not a silent
reinterpretation of the earlier synthetic 0.32.

This explanation can use similar environments, a route between different
environments, and molecular evidence linking the cargo to transfer. It cannot
answer whether the enzyme's function is generally suitable for its organism,
measure enzymatic activity again, or award partner coexpression credit.

Three responsibilities remain separate: an investigation begins from supplied
material and discovers possible functions; this numerical sheet evaluates
emergent function/history inferences; targeted readers populate its exact cells.
No investigation prompt is newly proposed here, and this sheet is not prompt
text. The future reader definitions in section 8 are **UNIMPLEMENTED**.

## 2. Environmental and route compatibility B

Choose a source-grounded, finite environmental compartment partition e=1…m
that is relevant to this transfer hypothesis: for example algal surface,
ingested material, intestinal lumen, or a finer measured oxygen/habitat
partition. A compartment is a biological state, not a numerical grade.
All comparisons use the same partition. Changing its resolution creates a
declared sensitivity scenario. Do not select a coarser partition solely to
make two lineages look alike.

Let d_e and r_e be nonnegative donor and recipient environmental-profile
weights, each summing to one. With actual comparable observations, use
`d_e = n_D,e/N_D` and `r_e = n_R,e/N_R`, retaining the unit counted and its
sampling scheme. Examples of units are sampled lineage occurrences or
observed exposure units. Repeated observations from one host remain clustered
for uncertainty. An organism's single reported isolation site can supply a
one-hot **descriptor**; it does not establish its whole niche distribution or
an ancestor's occupancy probability. Descriptor-based and sampled-profile
calculations are labeled separately.

For direct environmental similarity, K is the identity matrix. For a specified
mediated route, K_eh is the fraction of donor material originating in e that
reaches recipient-accessible compartment h in transferable form under that
route. K is substochastic: K_eh≥0 and Σ_h K_eh≤1. The remainder is loss or
delivery outside the considered compartments. A native observation uses
`K_eh = delivered_exposure_units_eh / at_risk_exposure_units_e`, with mutually
exclusive destinations and one fixed denominator. Counts concern exposure or
material units; kilograms eaten cannot be divided by recipient cell counts.

\[
d^{route}_h=\sum_e d_eK_{eh},\qquad
\boxed{B=\sum_h\min(d^{route}_h,r_h)}. \tag{2}
\]

B is a unitless overlap coordinate in [0,1]. Direct K=I measures environmental
profile similarity, not physical contact probability. Routed K measures the
overlap after a particular supported delivery route; it can be positive when
the resident habitats differ. It is not a probability that HGT occurred.

All inputs refer to the stated event interval/scenario. Extant observations
are retained separately when the ancestral relationship is unresolved. A
scenario may explicitly assume an ancestral habitat; that assumption must be
visible and varied, not relabeled as measured history. A matching environment
does not infer direction, timing, successful integration or protein function.

### Narrow judgment fields when no native route measurement exists

The permitted grader can bound **one K_eh cell for a named physical route
step**, or bound ancestral d/r profile cells, with the simplex constraints
retained. Its question is the fraction of the declared exposure units delivering
transferable material between those exact compartments, conditional on the
specified scenario. The scale has physical endpoints 0 and 1; it has no
low/medium/high ladder and supplies no whole-HGT or whole-function grade.

The output must identify the donor material, destination, event interval,
reference class, excluded alternative routes, contrary evidence and the
quantitative constraint behind each bound. If prose supports a route but no
fraction, return [0,1], not an invented midpoint. A justified constraint such
as “at most the unprocessed fraction can carry viable donor cells” can bound
K using the measured processing fraction. A route requiring viable cells and
one requiring DNA only are separate scenarios with different operands.

A native joint measurement has priority over this judgment. Grader disagreement
is a sensitivity envelope, not independent replication or a standard error.
The formula remains usable with bounds; no experiment or execution gate is
created by an unidentified point.

## 3. Cargo/mechanism compatibility M and chronology T

### Cargo/mechanism compatibility

Let C_k be the explicitly proposed transferred cargo region, with total unique
length L_k>0 in bp (or consistently in aa when only protein material is known).
Partition it into disjoint intervals I_j whose lengths sum to L_k. Let m_j be
the fraction/probability of interval membership in a transfer-capable unit for
the stated event mechanism and lineage. The unit may be a conjugative element,
transducing segment, or successfully taken-up DNA fragment; a plasmid is not
required for every mechanism.

\[
\boxed{M_k={\sum_j |I_j|m_j\over L_k}}. \tag{3}
\]

This is expected cargo coverage by the stated molecular transfer explanation,
not sequence identity, the number of mobility genes, a transfer-rate ratio,
or enzymatic activity. Every site contributes once. Known linked interval
membership in an appropriately demonstrated transfer-capable unit is 1;
documented exclusion from that specified unit is 0. If native joint
reconstruction samples exist, m_j is the weighted fraction of those samples
with that membership, calculated within the original joint model. Do not
multiply an additional copy of its gene-tree support into m_j.

Crucially, a relaxase annotation nearby is not demonstrated transfer capacity.
A targeted reader may grade only the conditional membership proposition
“this exact cargo interval belongs to the specified transfer-capable unit in
the relevant ancestor,” using source evidence about linkage, boundaries and
mobility. It cannot grade the whole HGT explanation or the candidate function.
For uncertain intervals it returns continuous bounds m_j∈[0,1], preserving
the source/assumption that constrains them; absent constraints leave [0,1].

A direct transfer assay with verified cargo and matched controls can establish
capacity and interval membership. Its counts, denominators, cargo identity and
background are retained, but high transfer efficiency does not by itself make
more of the candidate's cargo historically explained. The earlier normalized
rate M remains a separate diagnostic under its original name; it is not
arithmetically substituted for this different coverage quantity. This explicit
semantic change avoids calling a guessed rate a historical explanation.

Nondetection of transfer is not m=0 unless the capacity exclusion for the exact
unit is established with its scope/detection limits. A route outside the
specified mechanism remains a different hypothesis. Contradictory localization
or linkage observations remain in alternative admissible m scenarios rather
than being erased by a favorable source. No min/max operation is performed
over papers to choose the most favorable membership estimate.

### Chronology

For native jointly sampled donor/recipient histories and event dates z, retain
their native weights w_z≥0 with Σw_z=1. Let t_z be 1 if the proposed directed
event lies on contemporaneous donor and recipient branches, and 0 if those
branches cannot coexist at that event time. Then:

\[
\boxed{T_k=\sum_z w_z t_z}. \tag{4}
\]

The denominator for an unweighted ensemble is its number of history samples;
T=valid samples/total samples. A completely specified compatible chronology
has T=1 and a demonstrated impossible one T=0. Unknown dates or just two
undated intervals do not justify a uniform distribution; T remains [0,1] or
a source-constrained bound. Mere lack of dates is not impossibility. With
joint dependence among chronology, environment and cargo, use equation (1)
**within each joint history sample**, then take its native weighted mean;
`mean(T)*mean((B+M)/2)` is not a substitute. The simpler product in (1)
applies when the supplied B/M are invariant across the specified chronology
samples, as in the complete synthetic example below.

The temporal factor rules out an impossible specified donor/recipient event.
It is an explanatory numerical input, not an acceptance gate or an instruction
to obtain dated trees. The episode can continue with its actual partial sheet.

### Why this sum and multiplier

B and M each answer one different explanatory question; their equal mean
allows environmental support or molecular-route support to provide partial
explanation. Full E=1 requires both at 1 and a compatible chronology. The mean
does not assert independence. T multiplies because the named directed event
cannot explain history when its chronology is impossible. The half weights
and this treatment of chronology are finite policy choices for review, not
coefficients fitted from these sources. An unknown component stays an interval.
For example, B=.8, M unknown, T=1 yields E∈[.4,.9], not E=.8 or E=0.

## 4. Regional contribution, asymmetry and sparse references

The original sheet's definitions remain explicit here. For candidate function
f, incompatible characterized alternative g, query q and each tree r, compare
all fixed pairs in R_f×R_g using rooted q/reference triplets. Count n_f for
q with the f reference, n_g for q with g, n_out for references together, and
u unresolved. N=|R_f||R_g| is fixed. Resolved P=(n_f−n_g)/N; unresolved
P lies in [(n_f−n_g−u)/N,(n_f−n_g+u)/N]. Missing triplets are not dropped.

For x=f or g, d_qx is the minimum patristic distance to an x reference and
s_x is the median within-x nearest-other-reference distance, all on the same
region/tree and in substitutions/site. O_x=min(1,s_x/d_qx), with O_x=1 when
d_qx=0 and s_x>0. Fewer than two distinct x references, unknown lengths/units,
or zero spacing leave O_x unknown in [0,1]. Duplicated labels do not fix this.

Given independent organism-tree information with the existing copy mapping,
N_hist fixed query-anchored triplets, n_v concordances, and d_k discordances
assigned once to each specific event k:

\[
H_r={n_{v,r}+\sum_k d_{kr}E_{kr}\over N_{hist}},\qquad
s_{fg,r}=\max(P_{fg,r},0)O_{f,r}H_r,\qquad
c_{fg,r}=\max(-P_{fg,r},0)O_{g,r}. \tag{5}
\]

One event affecting many triplets reuses one E and its uncertainty. It does
not create repeated independent transfer observations. Unassigned discordances
and unresolved histories contribute bounds [0,1] for their fixed slots.
Known vertical concordance needs no transfer explanation. Gene/species
discordance alone is not identified HGT.

For the fixed characterized alternative set, s_fr=min_g s_fg,r and
c_fr=max_g c_fg,r. Average those complete per-tree expressions using the one
declared ensemble's native weights, obtaining A+ and A−; Z=A+−A−.
No branch percentages are multiplied or mixed across bootstrap/posterior
methods. One point tree gives a point-tree score with uncertainty unavailable,
not a zero-width confidence interval. The original empirical quantile rule
`sorted[max(1,ceil(pR))]` remains unchanged for an unweighted ensemble.

**Asymmetry is retained and exposed.** H discounts supporting placement but
does not discount placement with an incompatible characterized function.
This makes support a positive transfer claim requiring historical coherence;
opposition says the observed geometry conflicts with the incumbent function.
Opposition to f does not certify a historically justified positive annotation
of g. With P=1, O_f=O_g=.75 and H=.4, f receives +.30, while reversing the
same comparison gives -.75 for g, not -.30. For common O and H, the sum of
the two signed orientations is `-|P| O (1-H)`. This is not a symmetric
probability model. A symmetric-history alternative would be a different policy;
it is not silently adopted here.

| Sparse case | Definite result under this proposal |
| --- | --- |
| No incompatible characterized comparator | P and the discriminatory endpoint are unidentified; retain raw clade placement and distances, but output A+,A−∈[0,1], Z∈[-1,1], c∈[0,1], point=null. Absence of a comparator is neither full support nor contrary evidence. |
| Only one positive characterized reference, with usable alternative set | P can be calculated; O_f remains [0,1]. Supporting term is [0,max(P,0)H]; opposing term may be fully known. Example P=.8,H=.5,c=0 gives support [0,.4], not the point .4. |
| Only one contrary reference | O_g remains [0,1]; observed contrary topology is retained but its normalized opposing magnitude is unidentified. |
| Exactly zero term multiplied by an unknown factor | That product is zero; the unknown factor itself remains unknown. |
| More references, new alternative, or revised claim scope | Recalculate the current persistent candidate; retain earlier results as history, never sum revisions as evidence. |

These are identified bounds with defined arithmetic, not missing formulas or
requirements to commission more analyses. Native-input gaps are listed so the
episode can choose whether addressing them is useful under its ordinary
continuation controller.

## 5. A definite whole-candidate reduction

One persistent candidate C has a fixed current set I(C) of distinct,
A104-relevant evolutionary/functional inferences. Deduplicate entailed
restatements: a specific enzymatic function and its synonymous name are one
inference, and a broader family name entailed by it is not a second vote.
For inference i, a declared set R_i identifies the homologous regions whose
history is necessary to transfer that inference at its stated resolution.
Unrelated tails, an expression observation or an assay magnitude are not
inserted into R_i. Source-grounded mapping of function to region is an input,
not a length-based convenience weight selected after seeing the scores.

For each required region r, collect its distinct, valid, comparable analysis
scenarios j. Identical source bytes/analysis represented in several papers
are one analysis, while different models using the same alignment are
sensitivity scenarios. Independent studies of the same region also remain
separate scenarios rather than additive votes. Use the conservative reduction:

\[
S_r=\min_j A^+_{rj},\quad C_r=\max_j A^-_{rj};\qquad
S_i=\min_{r\in R_i} S_r,\quad C_i=\max_{r\in R_i} C_r; \tag{6}
\]
\[
\boxed{S_C=\min_{i\in I(C)} S_i,\quad
O_C=\max_{i\in I(C)} C_i,\quad
Z_C=S_C-O_C,\quad c_{A104}(C)=\max(0,Z_C).} \tag{7}
\]

Equation (7) is the definite proposed [0,1] A104 coordinate supplied for
annotation scoring. S_C,O_C,Z_C and all interval/status fields accompany it.
W05's production wiring and cross-axis formula are separate; this coordinate
is not left undefined as “later wiring.” No global hypervolume is changed.

The meaning is **common positive support remaining across the candidate's
required evolutionary inferences after its largest contrary contribution**.
It is a conservative compatibility coordinate, not probability all claims are
true. Min/max deliberately prevent extra easy claims, long domains, papers,
or duplicated references from diluting a hard contrary inference. They also
mean extra supportive studies do not automatically add credit. This is a
finite policy choice whose consequence should be judged, not hidden.

Different domains need not share a phylogenetic tree. Their separate histories
enter the candidate's semantic requirements via (6), so a fusion can retain
two histories without pretending it evolved as one uniform block. A claim
that requires only one catalytic region does not inherit another region's
opposition unless that region bears on the claim. A claim of a joint two-domain
function retains both necessary regions; a shorter essential domain is not
overridden by averaging it with a longer one.

If several regions are alternative sufficient witnesses rather than jointly
required, the scope must say so before scoring. This version treats each
source-supported requirement map as a separate candidate-scope scenario and
returns their interval envelope; it does not select the favorable map. A
disjunctive function claim such as “f or g” must be evaluated against functions
incompatible with that union; the f-versus-g contrast cannot be recycled as
opposition to the union. Defining the function set is an input to the existing
reference reader, not an undefined arithmetic operation.

Empty/missing required-region sets or no A104-relevant inference produce
point=null and c∈[0,1], with the specific missing-scope reason. A nonphylogenetic
claim stays outside I(C), explicitly unassessed by A104. This is a contribution
to the candidate's annotation score, not a claim that A104 evaluates every
kind of biological assertion. Scope changes are retained and compared as
scope changes; past revisions are not extra candidates or observations.

Unknown rows remain in the required set. For intervals [S_L,S_U] and [O_L,O_U],
apply the same min/max to corresponding bounds, then
`Z∈[S_L−O_U,S_U−O_L]` and
`c∈[max(0,S_L−O_U),max(0,S_U−O_L)]`. These are conservative identification
bounds, not confidence limits. Retain shared-operand identity and joint native
samples so dependencies can tighten the bounds; no new independence assumption
is introduced by this formula.

## 6. Source contrasts and what their numbers actually mean

| Inspected source / location | Actual or derived number | Relevance to the gap; limits |
| --- | --- | --- |
| Smillie 2011 main abstract; supplement Methods pp. 1–5 | Reported 25-fold recent-HGT enrichment; derived inverse relative frequency 1/25=.04 | Shows a numerical ecological comparison can exist. Its observed population, ascertainment and phylogenetic strata matter; .04 is not an ancient-event probability or a B overlap. |
| Smillie supplement, phylogenetic mapping and limitations | 23% lacked enough homologs for the quartet analysis; >99% support among those analyzed | Missing comparators are a real native-input limitation. Neither aggregate percentage populates the target's P or O. |
| Hehemann 2010 Fig. 3, visually inspected; PorA/PorB versus AgaA/AgaB | P(Bp1689)=+1; P(Bp1670)=-1 | A plausible marine transfer narrative cannot make agarase placement support porphyranase. The comparison retains positive and contrary regions/inferences. |
| Hehemann 2010 main discussion, resident contexts and food-route argument | Direct overlap of the two stated one-hot resident descriptors =0; routed overlap =k for the unmeasured marine→gut route fraction k | Different resident habitats do not rule out mediated transfer. k is now a precise, narrow reader/grader field, not an invented ancient contact duration. |
| Hehemann 2010 Table 1 / Results | Observed cohort proportions 4/13=.307692 and 0/18=0 | Native distribution facts retained; diet was not individually measured, ascertainment differs, and related hosts are not independent transfers. These are not added to B again. |
| Hehemann 2010 mechanism paragraph / Supplementary Table 3 | Cargo/mobility associations described; no transfer capacity fraction measured | Populates linkage evidence and specific uncertainties for m_j. Best-hit identities and nearby mobility annotations do not become a measured M. |
| Existing A104 sheet and user direction | P/O/history geometry and broader event-explanation requirement | Defines the numerical questions; papers inform operands, not the chosen averaging or candidate min/max policy. |

**Additive clarification to PAPER01_SMILLIE_2011_001.md:** that paper note
proposed a conditional-frequency ratio as a possible B-style compatibility
input. The final proposal does not equate it with the overlap B in (2).
The native 25-fold ratio and derived .04 remain useful diagnostics/source
examples; they are not substituted for a differently defined environmental
overlap or transferred without calibration to ancient marine-to-gut events.
This distinction preserves the note instead of rewriting it.

The two primary papers support contrasting numerical questions: matched
ecological exchange frequencies versus a specific route across unlike habitats.
The source packets contain exact inspection coverage and experimental-definition
limits. No other primary source or retained case packet was interpreted here.

## 7. Fully populated synthetic candidate and checked arithmetic

**Every value in this subsection is invented fixture input.** It is not a
measurement of porphyran proteins, the annotation target, or any biological
dataset. Source-informed meanings do not turn these values into published data.
The arithmetic checker reads no biological data and runs no phylogenetic tool.

Use the complete toy trees already defined in the prior sheet, reproduced here:

```text
T+ = (((q:.6,f1:.2):.1,f2:.3):.2,(g1:.2,g2:.2):.2);
T- = ((f1:.2,f2:.2):.2,((q:.6,g1:.2):.1,g2:.1):.2);
U  = topology(T-), from stipulated independent organism information.
```

For T+, n_f=4,n_g=0,N=4,P=1,s_f=.6,d_qf=.8,O_f=.75;
for T-, n_f=0,n_g=4,N=4,P=-1,s_g=.4,d_qg=.8,O_g=.5.
There are six history triplets: all six discordant in T+, all six concordant
in T-. Each T+ region has one stipulated event accounting for those six
relations; this is one event per region, not six replications.

Region R1 has these completely specified explanation inputs:

| Component | Synthetic operands | Calculation |
| --- | --- | --- |
| Donor profile d | 80 marine and 20 intestinal observations out of 100 | d=(.8,.2,0) over marine, intestinal, coastal |
| Recipient profile r | 75 intestinal and 25 coastal observations out of 100 | r=(0,.75,.25) |
| Route K from marine | 60 units delivered to intestinal, 10 coastal, 10 lost, out of 80 | K_marine,int=.75; K_marine,coastal=.125; remainder=.125 |
| Route K from intestinal | 20/20 remain intestinal | K_int,int=1; all other specified entries zero |
| Routed donor profile | .8×.75+.2×1=.8 intestinal; .8×.125=.1 coastal | total delivered mass=.9; loss=.1 |
| B | min(.8,.75)+min(.1,.25) | .85 |
| Cargo intervals | 600 bp with m=1; 200 bp with an explicitly synthetic narrow-reader judgment m=.5; 200 bp with documented exclusion m=0 | M=(600+200×.5+0)/1000=.7 |
| Chronology | 9 compatible joint history samples out of 10, with invariant B/M | T=.9 |
| E | .9×(.85+.7)/2 | .6975=279/400 |
| H for T+ | (0+6×.6975)/6 | .6975 |
| Supporting T+ term | 1×.75×.6975 | .523125 |
| Contrary T- term | 1×.5 | .5 |

The same toy geometry is used for R2 and R3 as independently stipulated
regional inputs; it is not three biological reconstructions. R2 has B=1
(identical measured one-compartment profiles, K=I), M=.6 (600/1000 bp within
the stipulated transfer-capable unit), T=1, E=.8. R3 has B=1, M=1 (1000/1000
bp) and T=1, hence E=1. Each is one ensemble of ten equally weighted trees:

| Region | T+ / T- multiplicities | E(T+) | A+ | A− | Regional signed |
| --- | ---: | ---: | ---: | ---: | ---: |
| R1 | 8 / 2 | .6975 | .8×.75×.6975=.4185 | .2×.5=.10 | .3185 |
| R2 | 9 / 1 | .8 | .9×.75×.8=.54 | .1×.5=.05 | .49 |
| R3 | 6 / 4 | 1 | .6×.75=.45 | .4×.5=.20 | .25 |

Candidate C contains two distinct A104-relevant inferences: I1 requires both
R1 and R2; I2 requires R3. There is one analysis scenario per region. Therefore:

\[
S_{I1}=\min(.4185,.54)=.4185,\quad O_{I1}=.10;
\qquad S_{I2}=.45,\quad O_{I2}=.20;
\]
\[
\boxed{S_C=.4185,\ O_C=.20,\ Z_C=.2185,\ c_{A104}(C)=.2185.}
\]

Adding a duplicate report of R1, an alias for I1, or a longer irrelevant tail
does not change .2185. A new valid R3 scenario with A+=.2,A−=.25 yields
S_C=.2,O_C=.25,Z_C=-.05,c=0; the contradiction remains visible. It does not
terminate the investigation or remove other axes' evidence.

Uncertainty/missingness examples for the same fixed candidate:

| Changed input only | Checked result |
| --- | --- |
| R1 narrow membership judgment m∈[.3,.7] instead of .5 | M∈[.66,.74]; E∈[.6795,.7155]; R1 A+∈[.4077,.4293]; candidate c∈[.2077,.2293] |
| That m entirely unidentified [0,1] | Candidate c∈[.1915,.2455] |
| R1 B entirely unknown, with M=.7 and T=.9 retained | R1 A+∈[.189,.459]; other required regions cap common support at .45; candidate c∈[0,.25] |
| R1 has one positive reference only, so O_f is unknown [0,1] | R1 A+∈[0,.558]; candidate c∈[0,.25]; fixed opposition is preserved |
| Candidate label and wording are revised without changing scientific scope or inputs | Current coordinate is still .2185; the previous version is not a second contribution |

The R1 signed-score empirical 2.5th/97.5th quantiles are -.5 and .523125;
these are resampling spread, not candidate-truth confidence limits. Candidate
min/max is a reduction of the regional coordinates after their stated
ensemble averages. Its uncertainty is propagated from shared native inputs
or bounds; do not manufacture a joint bootstrap by pairing arbitrary regional
replicate numbers.

## 8. Exact proposed reader/calculator additions — UNIMPLEMENTED

Every numerical cell uses `{value,lower,upper,unit,status,uncertainty_kind}`.
Status distinguishes observed, derived, explicit_judgment, scenario_assumption,
synthetic, missing or invalid. Units and point availability are not confidence
scores. Provenance includes immutable source/measurement identities and exact
locators outside model-facing text. These additions target equations (1)–(7):

| Function | Required typed input | Exact output cells/responsibility |
| --- | --- | --- |
| `read_event_environment_profile` | `event_id:string`, `lineage_role:donor|recipient`, `event_interval_ref:string|null`, `profile_kind:sampled|descriptor|ancestral_model|scenario`, `compartments:[string]`, `observations:[{measurement_id,cluster_id,compartment,nonnegative_weight,unit,source_locator}]`, `scope_mapping_ref`, `missing_constraints` | `profile:[{compartment,numerator,denominator,weight,bounds}]`, `profile_kind`, `sampling_unit`, `shared_observation_ids`, `event_mapping_status:observed|modeled|assumed|unresolved`; normalize unique compatible units only, preserve extant vs ancestral distinction. |
| `read_route_transition` | Same event/partition, `route_id`, `material_form:viable_cell|virion|DNA_fragment|other_declared`, `exposure_window`, `at_risk_units_by_origin`, mutually exclusive `delivered_units_by_destination`, `lost_or_unobserved_units`, units and original IDs | `K:[{origin,destination,numerator,denominator,value,bounds}]`, `row_loss_mass`, `measurement_status`, `shared_observation_ids`; validates nonnegative row sums≤1 and no destination double count. |
| `bound_missing_route_cell` | One exact unavailable K cell, its physical definition, source evidence, contrary evidence, reference class, and event assumptions | `cell_key`, `value_or_null`, `lower`, `upper`, `constraint_refs`, `assumption_refs`, `status:explicit_judgment|missing`; no categorical grade or overall score. Native cells cannot be overwritten. |
| `read_event_cargo_membership` | `event_id`, `cargo_region`, `coordinate_unit:bp|aa`, `mechanism`, `intervals:[{start,end,transfer_unit_ref,capacity_evidence_ref,membership_evidence_ref,native_membership_samples_or_null,source_locator}]`, shared IDs | Disjoint full-cargo partition `{start,end,length,m_j,bounds,status}`; `L_cargo`; actual native transferred-interval and capacity facts kept separate. Overlaps are unioned, uncovered intervals remain unknown. |
| `bound_missing_cargo_membership` | One interval's exact ancestral membership proposition, route/capacity/lineage assumptions, native-input absence, evidence and counterevidence | `interval_ref`, `m_point_or_null`, `lower`, `upper`, `constraint_refs`, `assumption_refs`; cannot grade functional activity, generic neighborhood or the whole HGT event. |
| `read_event_chronology` | `event_id`, `native_joint_history_samples:[{sample_id,weight,donor_branch_interval,recipient_branch_interval,event_time,direction}]` or explicit time constraints; original units/rooting | `feasibility_by_sample`, `native_weights`, `T_or_bounds`, `time_unit`, `joint_sample_ref`, missing reasons; no inferred uniform date distribution. |
| `calculate_event_explanation_v2` | d,r,K, disjoint cargo/m_j, chronology and shared/joint dependency references | `routed_d`, `B`, `M`, `T`, per-joint-sample E and `E_v2`; preserve all component bounds and legacy C/rate diagnostics. Apply (1)–(4), never select the favorable event scenario. |
| `compile_A104_region_v2` | Existing complete regional reader outputs, fixed alternative/reference manifests and histories, `E_v2` by event/tree/scenario | Existing P/O/H/per-tree terms/A+/A−/signed/quantiles plus missing inputs and sensitivity scenario IDs; only E meaning changes by explicit version. |
| `read_candidate_A104_requirements` | `persistent_candidate_id`, `current_revision`, actual candidate contents, explicit `inference_scopes`, `entailment_or_alias_groups`, `required_regions_by_inference`, `requirement_map_scenarios`, and source-backed scope relationships | Unique current I(C), fixed R_i, unassessed assertions, alias-collapse mapping, unresolved-scope reasons. It produces no confidence or automatic requirement weights. Interpretive scope mappings remain explicit inputs. |
| `compile_A104_candidate_v1` | Deduplicated comparable region scenarios, complete requirement map, numerical intervals and shared-dependency map | `region_S/region_O`, `inference_S/inference_O`, `candidate_S`, `candidate_O`, `candidate_signed`, `candidate_A104_coordinate`, bounds, `missing_native_inputs`, `scope_status`, source/analysis dependencies; computes (6)–(7) deterministically. |

Validation checks mathematical meaning (count sums, interval coverage, units,
normalization, source aliases, contradictory mapping). It is not a scientific
approval service, reviewer episode, mandatory assay sequence or stopping rule.
No model is called just to repeat source facts or compute arithmetic.

For conservative component bounds with nonnegative input intervals, compute
`d_route_L[h]=sum(d_L[e]*K_L[e,h])`,
`d_route_U[h]=min(1,sum(d_U[e]*K_U[e,h]))`,
`B_L=sum(min(d_route_L[h],r_L[h]))`,
`B_U=min(1,sum(min(d_route_U[h],r_U[h])))`; M/T/E follow their positive
weighted sums/products. Shared input constraints and native joint samples
take precedence when available. These simple bounds can be wider than the
jointly feasible range; label them conservative and never call them independent
replicate uncertainty. Fixed denominators retain unknown exposure, cargo and
triplet slots rather than dropping them.

## 9. Dependencies, finite choices and completion boundary

Shared evidence retains its actual identity. A105 characterization labels the
reference functions; its rate magnitude is not an A104 bonus. A107 partner
coexpression is not used. A104 uses food/habitat observations only for their
relation to this specific transfer route. The sheet declares that shared dependency and supplies
no cross-axis independence claim or extra evidence count. W05 must receive
these identities along with the coordinate; this draft does not claim to have
solved or implemented the global correlated-axis formula.

Finite policy choices exposed for judgment are: the environmental partition
and overlap metric; cargo-length coverage as mechanism support; equal B/M
influence; chronological feasibility as a multiplier; retained inverse-reference
spacing and asymmetric positive/contrary weighting; conservative min/max across
analysis scenarios, necessary regions and inferences; and positive-part mapping
to one annotation coordinate. No coefficient or essential reducer is left to
unspecified future work. The choice among policies is not called data missingness.

Native-input gaps in the published examples remain genuine: no complete event
dating distribution, no measured historical route transition, no verified
ancestral cargo membership probability, and no complete branch-length/
organism-tree ensemble for the retained porphyran example. The formula defines
what to do with each gap without inventing data. These examples do not establish
calibration, human acceptance, implemented readers, a real fully populated
dataset sheet, production scoring or axis completion. Their arithmetic and the
complete synthetic candidate are checked in `arithmetic_checks_001.py` and
`arithmetic_results_001.json`.
