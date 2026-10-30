# Proposed native cryo-EM and NMR operands for A111

Goal: make the existing structural-evidence product numerically usable for two additional, explicitly bounded experimental measurement paths. Criteria are native local cells, exact conversions, actual contrasting source rows, complete synthetic joins, and exact future reader inputs. This is a research proposal for judgment. It adopts no policy, implements no production reader, and completes no axis. A105 remains first; 0/10 remains the recorded status.

This adds to `a111_structural_evidence_sheet_017`, whose three initial specification files were read completely. Preserve its occupancy q, physical-feature agreement G, actual target correspondence T, experimental comparability C, separate isolation I, and signed reducer. For a detected event:

\[
w=qDGT C I,\qquad h\in\{+1,-1\}.
\]

The spaces have no mathematical meaning: this is the six-factor product q × D × G × T × C × I. D measures one specified aspect of local observation support, not overall structure quality or correctness probability. The same source observation and mapped target feature remain one evidence chain. An unknown target mapping never becomes a default transfer grade. Investigation prompt text, the sheet below, and functions populating its cells remain separate. This packet does not change a prompt.

## Cryo-EM: local Q-score index

Method selector: `cryoem_local_q_squared_001`.

Required native panel: the Q-score of every declared local atom or residue needed for the feature. Select a single declared granularity, retain the exact map/model and local selection, and preserve native Q values in their dimensionless correlation domain [−1,1]. A residue-average Q is a residue-average diagnostic; it does not become the Q-score of each individual atom. The demonstrated cases use residue-level Q from wwPDB validation.

\[
D_{EM}=\min_{j\in J}\bigl[\max(0,Q_j)^2\bigr],\qquad |J|>0.
\]

The negative-to-zero rule and exponent 2 are explicit proposed numerical choices. Native values outside [−1,1] are invalid; do not clip them into validity. This is a local resolvability index, not 1−a calibrated assignment error. The native Q calculation compares the local map profile around model atoms to a reference profile; its retained software/settings matter. This packet consumes reported local Q, and does not claim to recompute it from maps. Q can be low while global resolution is favorable, and a locally fitted model can still have the wrong atom identity. Global resolution, FSC threshold, whole-map Q, Q-relative percentile and particle count cannot replace this local panel. [MapQ documentation](https://github.com/gregdp/mapq)

For Q intervals `[l_j,u_j]`, clip only the transform at zero: `D_L=min_j max(0,l_j)^2`, `D_U=min_j max(0,u_j)^2`. With a required endpoint missing, its native admissible Q domain is [−1,1], hence transformed [0,1]; the point remains null. Example: Q=.80 plus a missing second endpoint gives D=null [0,.64], not D=.64 and not D=0. No required local observations gives null [0,1] with `invalid_denominator`; it is never an empty-product 1. Bounds inferred only from rounding are not supplied.

G is calculated from the exact coordinates/observations selected for the same map/model, using the existing fixed physical predicates. Alternative atom identities, map versions or refinements are joint scenarios. A half-map split is a validation relation within a dataset, not two independent experiments. Symmetry copies receive the existing copy mean over full products; do not first average D and G separately and multiply those means.

The [Cao conversion](PAPER_CONVERSION_CAO2013_001.md) supplies all native local Q and distance cells. For the selected opposing G643 oxygen pairs, 3J5Q has D values .148225 and .139876 (copy mean .1440505); 3J5R has .113569 and .099225 (mean .106397). Their states differ, so these are not inconsistent repeats of one conditional state. Their target T remains null.

## Solution NMR: assigned experimental proton-distance restraints

Method selector: `nmr_local_noe_restraint_kernel_001`. Coverage is assigned experimental NOE-derived distance restraints, including an intermolecular contact when its endpoints and native averaging convention are established. This does not assert conversion coverage for every NMR observable.

For each declared distinct experimental restraint j and model/assignment scenario m, retain the exact proton endpoint selection, source peak/restraint identity, lower/upper distance bounds `[L_j,U_j]` in Å, and the modeled effective distance `d_jm` in Å. Bounds obey `0≤L_j≤U_j`; `d_jm≥0`. An Xplor `assign ... t l u` supplies `[t−l,t+u]`, not `t±u` and not a central measured distance when l=t. Any pseudoatom correction already included in a native bound is not added twice. Homology-imposed disulfides, force-field geometry and hydrogen bonds inferred only from the model are not experimental NOE restraints.

\[
v_{jm}=\max(0,L_j-d_{jm},d_{jm}-U_j),\qquad
s_{jm}=\exp\left[-\frac{v_{jm}^2}{2\tau_j^2}\right],\qquad
D_{NMR,m}=\frac1J\sum_{j=1}^{J}s_{jm}.
\]

The finite proposal is `τ_j=.50 Å` for every restraint in this distance-only method, with a fixed declared panel and equal weights. Thus v=0, .5 and 1 Å yield s=1, .606530659712633 and .135335283236613. τ is a scoring tolerance, **not** the measured distance SD. A restraint with a wide allowed interval is not relabeled a precise observation. D is local agreement with the actual experimental restraints conditional on their assignments and the chosen model; restraint fitting on the same data does not become held-out validation or a calibrated model-accuracy probability.

Required restraint/endpoint panels must actually cover the local feature being claimed. Declaring just the best-fitted available restraint while omitting other required local roles changes the question rather than validating the larger feature. The same experimental peak/constraint reproduced in multiple files has one panel membership. Adding copies of it cannot change J. The panel and denominator are fixed before comparing scenarios; never drop the violated or unread member.

### Exact distance convention

The demonstrated source rows use one explicitly named proton at each endpoint, so `d=||x_a−x_b||₂`. When the native protocol genuinely supplies grouped proton selections and its convention is known, the permitted exact calculations are:

| Native convention | Effective distance, all coordinates in Å | Required parameters |
| --- | --- | --- |
| `single` | `r_ab` | One atom at each endpoint |
| `R-6` | `[(Σ_ab r_ab^−6)/N_pairs]^−1/6` | The complete admitted pair set, including its fixed N_pairs |
| `SUM` | `[(Σ_ab r_ab^−6)/n_mono]^−1/6` | Complete admitted pair set; the source's strictly positive monomer normalization n_mono |
| `CENTER` | `||mean_a x_a−mean_b x_b||₂` | The exact endpoint atom sets |

For positive distances 3 and 10 Å, R-6 gives 3.366977181405646 Å, while SUM with n_mono=1 gives 2.9996356549220624 Å. They are not interchangeable. A zero physical proton separation is an invalid structural input for this calculation, not an infinite favorable NOE. Unknown averaging, atom-name aliases, stereoassignments or bound corrections return null distance/support with the precise unresolved field. Genuine alternative assignments are scored as scenarios, unless the source itself defines their joint ambiguous-restraint averaging; never take the shortest distance as a silent substitute. [Xplor-NIH native averaging documentation](https://nmr.cit.nih.gov/xplor-nih/xplorMan/node379.html)

### Missingness and uncertainty

For fixed L,U and a modeled distance interval `[d_L,d_U]`, `v_min=max(0,L−d_U,d_L−U)` and `v_max=max(0,L−d_L,d_U−U)`. Therefore `s_L=exp[−v_max²/(2τ²)]`, `s_U=exp[−v_min²/(2τ²)]`. For alternative source bounds, assignments or models, evaluate the admitted complete scenarios and retain their extrema; do not independently vary source-coupled values into an impossible combination.

A completely unresolved required restraint supplies s=null [0,1]. If c restraints are known and u are unknown in the fixed J=c+u panel, `D_L=Σ_known s_j/J`, `D_U=(Σ_known s_j+u)/J`, with null point. A panel containing s=.606530659712633 and one missing restraint yields D=null [.303265329856317,.803265329856317]. Empty or wholly inapplicable experimental panels remain null [0,1], not D=1. Missing experimental data and known experimental violations remain different cases.

Deposited ensemble members are model scenarios within one dataset. Compute the entire qDGTCI product in each scenario before taking the min/max envelope. The original core's copy mean is **not** applied to alternative NMR conformers. A named medoid has a valid model-conditional point. An ensemble without measured physical conformer weights has no population-weighted point; an equal average over its models would invent such weights. Model counts do not become experimental n, q, or statistical precision. If separate measured physical weights exist, retain their normalization, uncertainty and joint provenance; that is a different explicitly weighted observation, not a default of this method.

The [Bae conversion](PAPER_CONVERSION_BAE2016_001.md) supplies two native restraints per local panel. K1/2N9Z model9 has D=1. K2/2NAJ model3 has D=.8986676009902625. For the local question cross-loop proton distance≤4 Å, both medoids give G=1, while both ensembles cross the boundary. Their full joint DG ranges are [0,1] and [0,.9205446855153534], respectively. T remains null without a target mapping. No ensemble spread becomes an uncertainty probability.

## Combining the new operands with the unchanged chain

Use the existing q provenance distinction: refined/measured/count-derived occupancy and a literal model-conditioned q=1 are not the same thing. Fixed atom occupancy, selected cryo-EM particle fraction, NMR conformer counts and uncorrected peak integrals do not establish a solution-state q. When the question is literally within a named model, q=C=I=1 retain that conditional meaning only. The general target support remains unknown where required target roles, condition measurements or attribution bounds are absent.

For each declared elementary question, average equivalent copies' **positive and opposing products** within a canonical dataset, average unique eligible dataset/state rows within their dependence cluster, and average the clusters. Apply fixed elementary weights β and feature-family weights α exactly as in the original arithmetic addendum:

\[
P_{fc}=\operatorname{mean}_e\max(h_e w_e,0),\quad
O_{fc}=\operatorname{mean}_e\max(-h_e w_e,0),\quad
P_{111}=\sum_f\alpha_f\sum_j\beta_{fj}\operatorname{mean}_cP_{fjc},
\]
\[
O_{111}=\sum_f\alpha_f\sum_j\beta_{fj}\operatorname{mean}_cO_{fjc},\quad
Z_{111}=P_{111}-O_{111},\quad A_{111}=\max(0,Z_{111}).
\]

One source dataset represented by paper, restraint file, coordinates and validation remains one observation. Technical spectra, symmetry copies and alternative refinements add no independent experimental n. Two genuinely independent local measurements may occupy separate clusters only with actual sample/data provenance. Shared starting models or restraints retain a dependency edge, including mixed cryo-EM/NMR docking. A source reused on another axis is still the same source contribution; this sheet does not grant extra independent credit.

For calibrated nondetection use the existing `N=max(0,1−q_U/q_req)` in place of q. The D panel concerns actual observed surrounding site markers or detected assigned restraint support; do not manufacture a Q-score or NOE for an absent ligand/contact. A missing peak, omitted model atom, or empty density without a calibrated relevant q_U remains unknown, not opposition. Calibrated limits must refer to the actual detection mechanism and experimental conditions. Different agonist states or constructs remain different scoped questions unless a broader comparison was explicitly declared; contradictory outcomes on the same question retain opposite signs and the same denominator.

The original available-experiment mean has a material limitation: adding a relevant roster member with T=0 or another known zero factor dilutes both means. It estimates the declared experiment-roster mean of chain contributions, not a sum of evidence or maximum attainable target support. This packet exposes that behavior and does not silently replace the reducer. The synthetic cryo-EM example gives Z=.0350134504795206 with two clusters; adding a third known-zero row gives .0233423003196804. W05 and any reducer correction remain separate work.

## Finite proposed choices for judgment

1. Use local Q², with the weaker declared endpoint, for the bounded cryo-EM branch.
2. Use the fixed local NOE panel's mean Gaussian violation score with τ=.50 Å for the bounded NMR branch. This is a fit index and does not assign error probabilities.
3. Retain residue/atom granularity and model-conditional labels in returned numerical cells; no unconditional scalar is inferred from a conditional example.
4. Retain complete-scenario NMR envelopes without invented ensemble weights; retain ordinary copy means for actual equivalent copies.
5. Preserve the original product and mean reducer for these demonstrations, while exposing its roster-dilution estimand for separate review.

The branches have explicitly different native meanings; their numerical index scale is proposed, not empirically calibrated across modalities. Calibration and production implementation remain unverified, but neither leaves the arithmetic above undefined. Cross-linking and other solution observables are assessed separately in `CROSSLINK_SOLUTION_SCOPE_001.md`; preserving their raw values alone does not earn a claim of supported numerical coverage.
