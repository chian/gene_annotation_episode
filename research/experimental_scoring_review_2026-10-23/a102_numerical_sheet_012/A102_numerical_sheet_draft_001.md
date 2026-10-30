# A102 structural correspondence: numerical scoring-sheet draft 001

The research outcome is a **fully specified proposed numerical sheet**, with native structural-comparison cells, an explicit bounded compilation, contrasting published rows and a complete synthetic example. Published inputs, arithmetic and proposed scoring conventions are separated. This is part 2 of the user's three-part design. The future population interfaces below describe part 3 without implementing it; no investigation prompt is supplied or changed.

This draft is preparatory. A105 remains first and unfinished; the fixed accounting is **0/10 completed sheets**. No scoring policy, axis completion, probability calibration, production reader, library publication, global weighting or hypervolume change is claimed. The active goal's criteria govern this outcome, rather than the organization of either paper.

## 1. What one sheet scores

Start with the actual supplied sequence, selected file record/region, coordinates or snippets. No searchable public name or initial candidate function is required. After investigation identifies a possible function, one score row evaluates how a particular structural comparison bears on that function at a declared scope. Historical protein names in the worked examples identify examples only; no relationship to the project's active target is implied.

The scored unit is `(supplied target material, emerged function, residue/domain/assembly scope, comparison panel, numerical profile)`. The function can be broad or specific, but its required structural features must be stated at that same specificity. Comparing an accessory domain does not transfer the catalytic function of an entire multidomain reference.

Each comparison retains the target and reference structures, chain/model/state, actual residue correspondence, atom choice, lengths, native method and settings. A parent supplied constraint or incomplete sequence boundary cannot be expanded from a public identifier. Coordinate models are the observed objects; their similarity is not itself a biochemical assay.

## 2. Typed numerical cells

`N?` means finite real number or `null`; `I?` means integer or `null`. Non-null counts are nonnegative; lengths and feature denominators are positive. Every numerical cell retains `origin = reported | native_output | derived | proposed_parameter | synthetic`, its units, source/operand references, and a field-specific missing reason. A nullable uncertainty record has `kind = SD | SE | confidence_interval | hard_bound | ensemble_range | reporting_rounding`, numeric endpoints/value, unit, and any stated confidence level. An absent uncertainty record means **unreported**, never zero error.

| Field | Type; units/range | Raw input, denominator and calculation | What it evaluates |
| --- | --- | --- | --- |
| `scope.L_target`, `scope.L_reference` | I? > 0; residues | Count the declared functional comparison region in supplied sequences/constructs; record denominator kind | Intended compared extent, including known residues without coordinates |
| `scope.L_observed_target`, `.L_observed_reference` | I?; residues | Count represented residues in the selected coordinate models | Model completeness; never silently replace sequence/scope denominators |
| `native.n_pairs` | I?; unique residue pairs | Count unique pairs in the actual map, or preserve the explicitly reported paired count | Extent belonging to this comparison |
| `native.n_rmsd_points` | I?; atomic points | Count the points used by the reported RMSD; one Cα per residue only if established | RMSD's true denominator |
| `native.rmsd` | N? ≥ 0; Å | Preserve reported/output value; for a supplied fixed map/transform, `sqrt(sum(d_atom²)/n_rmsd_points)` | Positional deviation for the actual selected atoms |
| `native.tm_target`, `.tm_reference` | N? in [0,1]; dimensionless | Preserve native TM scores and each exact normalization length, distance scale, map and transform | Length-normalized structural correspondence |
| `native.z` | N?; reported dimensionless units | Preserve reported DALI/other native Z, method/version and definition reference | Native structural-similarity statistic; not a normal-tail function probability |
| `coverage.target`, `.reference` | N? in [0,1] | `n_pairs/L_target`; `n_pairs/L_reference` | Matched fraction on each side |
| `coverage.symmetric` | N? in [0,1] | `2*n_pairs/(L_target+L_reference)` | One extent factor, not two independent coverages |
| `geometry.rmsd_kernel` | N? in [0,1] | `1/(1+(rmsd/2 Å)²)` | Explicit compression of the native deviation |
| `geometry.base` (`B`) | N? in [0,1] | RMSD profile: symmetric coverage × RMSD kernel. TM profile: `min(tm_target,tm_reference)` | One whole-scope comparison descriptor |
| `features.K` | I? > 0; distinct physical features | Number of function-relevant structural features in the declared complete feature set | Denominator fixed by the functional inference, not by successful matches |
| `features[k].distance` | N? ≥ 0; Å | Distance between mapped target/reference feature anchors under the retained scaffold transform | Site/interface geometry in its proper structural context |
| `features[k].coordinate_bound` | N? ≥ 0; Å | Actual justified bound on the distance error, with derivation; nullable | Coordinate/state uncertainty affecting that feature |
| `features.n_present`, `.n_absent`, `.n_unresolved` | I; features | Counts of mapped compatible, established absent/incompatible, and unresolved features; sum = K | Site completeness, actual incompatibility and missing information separately |
| `features[k].kernel` | N? in [0,1] | Compatible mapped feature: `1/(1+(distance/1 Å)²)`; established absent/incompatible feature: 0; unresolved: null | Geometric retention of each specified functional feature |
| `features.retention` (`F`) | N? in [0,1] | `sum(feature kernels)/K`, if all kernels known | Mean retention of the required local/context geometry |
| `pair.support` (`E`) | N? in [0,1] | `B*F` | Extent-weighted geometry constrained by function-relevant geometry |
| `panel.support` (`S`) | N? in [0,1] | Maximum `E` among references supporting this function in this scope | Best supported structural correspondence in the explicit panel |
| `panel.competitor` (`O`) | N? in [0,1] | Maximum `E` among explicitly incompatible characterized alternatives at the same scope | Strongest structurally plausible competing correspondence |
| `contribution.nominal` (`A102`) | N? in [0,1] | `max(0,S-O)` | Structural support margin for this function within this panel |
| `contribution.missingness_bounds` | [N,N] within [0,1] | Interval propagation below, conditional on recorded numerical observations | What missing operands allow; not a confidence interval |
| `contribution.measurement_bounds` | [N,N]? within [0,1] | Propagate only supplied justified bounds or defined model/state ensembles | Sensitivity to stated measurement/model uncertainty |
| `replication.independent_determinations` | I? | Count separately established coordinate determinations, retaining phasing/model dependencies | Replication extent; no automatic score bonus |
| `replication.range`, `.SD` | N? with units | Range and sample SD for genuinely comparable independent repeated endpoints; SD denominator n−1 | Consistency, without treating atoms as independent experiments |
| `quality.resolution`, `.R_work`, `.R_free`, `.pLDDT`, `.PAE` | N? or per-residue/matrix arrays; original units | Preserve only applicable model diagnostics for the selected structures | Model uncertainty/validation diagnostics; **not structural-comparison scores** |

For literature, a reported count may fill `n_pairs` while the exact map stays null. That supports a clearly labeled reported-scope descriptor; it does not supply feature mapping, reproduce the alignment, or resolve overlap with another alignment. `n_pairs > min(L_target,L_reference)` is a field inconsistency, not a score to clip. Different units or scopes are not silently repaired.

## 3. Exact correspondence and functional-feature definitions

The residue map is a one-to-one list of `(target model, chain, author residue number, insertion code, label residue number; reference equivalents)`. Atom mappings add atom name, alternate location and allowed chemical equivalence. The alignment record retains the rigid transform, atom selection (`C_alpha | backbone | heavy_atoms | declared_subset`), method/version, cutoffs and outlier rejection. A map from one cutoff cannot be used with the RMSD from another.

Every required feature has a persistent physical-feature key, source-defined role and explicit atom/centroid construction on the reference. Its target counterpart is established through the actual correspondence. An allowed equivalence such as two symmetry-equivalent carboxylate oxygens must be specified before calculating a distance; use the minimum distance only over those permitted role-preserving permutations. Identical coordinates or close sequence letters do not establish a chemically equivalent role. Unknown protonation/chemistry stays unresolved.

Features may include active-site atoms, ligand-pocket anchors, oligomer-interface anchors, or anchors fixing the orientation of required domains. A centroid lists all constituent atoms and uses their unweighted Cartesian mean. Each scored distance is therefore in Å. Angles and assay rates are not mixed into this distance kernel. If a function requires angular constraints, represent the orientation by explicit non-collinear positional anchors with their physical definition; do not recode an angle as an arbitrary Å distance.

Use the scaffold superposition that produced the comparison. Independently refitting a mobile functional site would hide a changed relation to the scaffold. A separately refitted site can be retained as a shape-only diagnostic, with its own transform, but does not fill this contextual feature cell. For an independently functioning domain claim, a domain-scoped transform is legitimate and must be named as such.

`K` is a set of **distinct physical features**, not a count of paper statements or equivalent atom encodings. Two source descriptions of the same anchor are one feature. If a feature supports several biological roles, list those roles without multiplying its count. The feature list must be complete for the expressly limited structural inference; this is not a claim to know every cause of biochemical function. Unknown relevant sites yield unknown `F`, rather than a made-up general reliability grade.

An established deletion of a required feature can contribute a measured zero. An unresolved side chain, missing density, unknown alignment or unexamined domain contributes an unknown value, not zero. A match involving an explicitly different chemical feature has zero compatibility for that specified atom-role relation; this is a counted correspondence condition, not a categorical overall grade.

## 4. Native scores and the bounded combination

The concrete **RMSD profile** used for the published worked rows is:

\[
C_i=\frac{2n_i}{L_{t,i}+L_{r,i}},\qquad
G_i=\frac{1}{1+(r_i/(2\,\mathrm{\AA}))^2},\qquad
B_i=C_iG_i.
\]

\[
F_i=\frac{1}{K_f}\sum_{k=1}^{K_f}
\frac{1}{1+(d_{ik}/(1\,\mathrm{\AA}))^2},\qquad E_i=B_iF_i.
\]

The sum uses the zero/unknown treatment in section 3 for absent/unresolved features. The selected scales are **proposals**: 2 Å gives half response to a 2 Å whole-selected-region RMSD; 1 Å gives half response to a 1 Å displacement of a specified functional anchor. The tighter local scale makes local chemistry more demanding than broad fold correspondence. Neither is a universal physical tolerance or a calibrated error probability. Equal `1/K` weights give each distinct declared geometric feature equal influence; this is a visible convention, not an empirical importance weight.

The **TM profile** uses the native scores directly:

\[
B_i=\min(TM_{t,i},TM_{r,i}).
\]

Both normalizations must refer to the declared scopes. The smaller score prevents a near-perfect small-substructure match from masquerading as a complete correspondence of both scopes. Do **not** multiply by coverage again: TM already normalizes its residue sum by a length. If two normalizations have different maps/transforms, they are separate variants: calculate each variant's `B*F` with its own mapping and retain the range; do not borrow the better site's transform for the other score. A sole one-direction TM score remains a native number; the two-direction descriptor has a missing operand and bounds, rather than an invented reverse score.

For clarity, the protein TM-score definition uses a normalized sum of per-pair distance kernels and optimized superposition. The inspected implementation sets final `d0=0.5 Å` for normalization length ≤21, otherwise `max(0.5,1.24*(L−15)^(1/3)−1.8) Å`. The actual retained software output and version govern each real row. This definition and normalization distinctions were checked against [official TM-score documentation](https://zhanggroup.org/TM-score/) and its [implementation](https://zhanggroup.org/TM-score/TMscore.cpp). An aggregate RMSD cannot reconstruct that per-pair sum or its optimized alignment.

For a DALI result, its native Z, RMSD, aligned count and exact scope all remain cells. This draft compiles its RMSD/count through the RMSD profile; **Z is not a second multiplicative proof from the same alignment**. A Z-only excerpt can inform ranking but cannot fill a geometry/extent product whose operands it does not report. It has `B=null`, with bounds constrained by any known extent. This is an exact missing-input rule; no unspecified conversion from Z to probability is left for a future grader. The MJ0226 paper names two search programs without assigning every printed statistic to an exact software/version, so its printed Z is labeled accordingly. The official DALI pages were inaccessible during this bounded review; no unretrieved formula is claimed.

Choose one profile for a given comparative panel. Do not take the maximum across incomparable TM and RMSD conversions. This draft supplies a concrete RMSD convention and a native-TM convention, **not an assertion that they share calibrated numerical units**. Mixed-profile evidence is preserved as separately scored panels, and an overall mixed-profile point contribution remains null until the same declared profile is available or the user adopts an explicit cross-profile policy. No automatic tool selection or alignment execution follows from missingness.

Within one coherent profile, target and functional scope:

\[
S_f=\max_{i\in\mathcal S_f}E_i,\quad
O_f=\max_{j\in\mathcal O_f}E_j,\quad
\boxed{A102_f=\max(0,S_f-O_f)}.
\]

All coefficients are now explicit: scale 2 Å, scale 1 Å, equal feature weight `1/K`, unit competitor subtraction, and no between-paper or laboratory weight. The result is a **dimensionless structural support margin in [0,1]**, not a probability, an overall annotation score, or an adopted axis weight. `S` and `O` remain visible even when the margin is zero. A tie means the structural evidence does not discriminate that declared contrast; it is not evidence that neither structure matches.

`S` and `O` include only comparisons at a compatible scope. A shared nucleotide-binding feature is not an incompatible function merely because two protein names differ. Different substrate activities may coexist. Opposition requires an explicit functional contrast whose alternatives are incompatible under the claim's stated scope, with its justification retained. A multifunctional reference cannot automatically be called opposition. Inference about which function a reference has belongs to the source chain/A105/A111 as appropriate; its whole activity/occupancy score is not copied into A102.

An unexamined or unspecified alternative panel gives unknown `O` in [0,1]. No competing reference investigated is not a measured zero. A panel intentionally containing only supporting references yields `S` as a **support-only descriptor** and `A102=null`; it must not be presented as a discrimination result. Within an explicitly evaluated contrast panel, an actually measured absent comparison may supply zero. The margin is conditional on the declared panel, never proof that no other function exists.

The product `B*F` asks for simultaneous broad correspondence and retention of function-relevant geometry. These factors can derive from overlapping coordinates; **no independence assumption is made**. The second factor can only constrain `B`, never inflate it. It does intentionally place additional importance on the declared functional region. This local emphasis is a proposed scoring choice to judge, not another experiment. Do not sum `r`, `C`, `G`, `B`, `F` and `E` as independent evidence.

## 5. Comparability, isolation and uncertainty

Comparability records construct boundaries, intended domain, ligand/metal state, assembly, crystal packing, temperature and model type outside the intended protein difference. These are not a checklist of binary score bonuses. A meaningful numerical comparability diagnostic is a **measured displacement bound or ensemble range** for the same mapped atoms across relevant states/constructs. For example, a matched-state comparison may show that a loop difference disappears; record and recalculate that specific row. Different global/domain/atom scopes remain separate rows.

If actual target/reference perturbation bounds over a fixed map are `u_t,u_r` in RMS Å, let `u=u_t+u_r`. The triangle inequality bounds the comparison RMSD by `[max(0,r−u),r+u]`, when those bounds and coordinate-frame assumptions apply. The geometric kernel is decreasing, so its bounds are `[G(r+u),G(max(0,r−u))]`. Apply the analogous rule to each mapped feature with its own justified distance bound. Reported SD is not a hard bound and cannot be inserted into this formula without naming a probabilistic interval model. A same-protein RMSD with a different map or unknown count is not automatically such a bound.

Resolution, R-free, pLDDT and PAE diagnose different aspects of a model. No `1−R_free`, inverse-resolution or `pLDDT/100` multiplier is proposed. A model score can describe how the **model** corresponds while true-structure uncertainty is unquantified. When physically justified alternative models are supplied, retain each native comparison and report their range under the same scope; that is a finite ensemble range, not a confidence interval. Do not estimate SE by treating hundreds of matched atoms as independent experiments.

Isolation asks what the geometric readout identifies. It identifies correspondence between particular models and mapped features. A geometric match does not isolate an enzyme's activity, binding affinity or causal mechanism. Functional-site geometry and explicit alternative-function comparisons refine that structural inference. Biochemical assays or perturbation/restoration can address different weaknesses through A105/A106; occupied ligands and experimental contacts belong to A111. Their evidence can define a relevant site without becoming additional A102 observations. Docking affinity and sequence identity never substitute for the structural-comparison cells.

Keep three uncertainty outputs distinct: algebra on reported numbers, missing-input feasibility bounds, and measurement/model uncertainty. No missing SD is replaced by zero, and no choice of 2 Å versus 3 Å is called experimental uncertainty; it is policy sensitivity.

For `K` features with known kernel sum `H` and `u` unresolved features:

\[
F\in[H/K,(H+u)/K].
\]

For nonnegative intervals, `E∈[B_low F_low,B_high F_high]`. For each set of compatible reference intervals, `S_low=max(E_low)`, `S_high=max(E_high)`, and likewise for `O`. Then:

\[
A102\in[\max(0,S_{low}-O_{high}),\;\max(0,S_{high}-O_{low})].
\]

These may be conservative outer bounds because inputs share coordinates; they do not invent independence. If relationships constrain combinations of endpoints, enumerate the actual variants rather than pairing impossible extremes. Missing `B` with known coverage `C` lies in [0,C] under this profile; unknown coverage permits [0,1]. A null feature set gives `F∈[0,1]`. A point remains null whenever required operands or panel definitions are unknown. Statistical intervals must retain their confidence level and joint-coverage assumptions separately.

## 6. Contrasting published rows

These rows are filled from the two separate source packets. They concern different target proteins, so they are **not** one candidate/competitor panel. Their juxtaposition contrasts broad versus partial correspondence. See [AF2372 conversion](AF2372_sheet_conversion_001.md) and [MJ0226 conversion with additive arithmetic correction](MJ0226_sheet_conversion_001.md).

| Published comparison | Native RMSD / matched count | Length denominators and scope | Native reported Z | Derived C | Proposed G, 2 Å | Proposed B=C×G | Function-specific F / E / A102 |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| AF2372–MJ0109 | 1.5 Å / 209 residues; atom choice unresolved | 252/252; paper-stated monomers | null | 0.8293650794 | 0.6400000000 | 0.5307936508 | F null; E [0,0.5307936508]; A point null |
| MJ0226–histidyl-tRNA synthetase | 2.7 Å / 76 Cα pairs | 193/421; deposited whole polymers; match only lobe/C-terminal domain | 5.9; exact tool attribution unresolved | 0.2475570033 | 0.3542958370 | 0.0877084157 | F null; E [0,0.0877084157]; A point null |
| MJ0226–glycyl-tRNA synthetase | 3.1 Å / 75 Cα pairs | 193/505; same whole-deposit convention | 4.6; exact tool attribution unresolved | 0.2148997135 | 0.2939015430 | 0.0631593574 | F null; E [0,0.0631593574]; A point null |

The AF row remains a reported-scope descriptor because exact compared chains/states/map and RMSD atom choice were unrecovered. The MJ rows' whole-deposit arithmetic is numerically defined but does not claim domain coverage. The required domain denominators and feature maps are absent. Their native scores therefore do not justify copying whole synthetase function. No numerical site incompatibility is fabricated from the paper's verbal qualifications.

The printed RMSDs have no reported statistical uncertainty. A derived squared-distance sum is legitimate from the MJ Cα counts **only as arithmetic on rounded reported RMSDs**: 554.04 Å² and 720.75 Å². The AF atomic denominator is unknown, so no such sum is filled there. No uncertainty or site-score estimate is extracted from a figure's appearance.

This is a finished calculation of the available published components, with explicit missing function-specific operands. The next section supplies the complete compilation example without pretending the missing operands were published.

## 7. Complete synthetic example and checks

**Every input in this section is invented for arithmetic demonstration.** It is not an alignment run, a claim about either published protein, or evidence about the current annotation target. The hypothetical panel compares one specific single-site function with an explicitly incompatible alternative. Both comparisons use the same 100-residue target scope and 100-residue reference scope, the RMSD profile, four distinct role-compatible functional anchors and the same declared scaffold/context convention. Exact maps and transforms are assumed supplied by the fixture; these values are not derived from a real coordinate file.

| Cell | Supporting reference | Incompatible reference |
| --- | ---: | ---: |
| Scope lengths | 100,100 residues | 100,100 residues |
| Native-style matched count | 90 Cα pairs | 80 Cα pairs |
| Native-style RMSD | 1 Å | 2 Å |
| Symmetric coverage C | 0.9 | 0.8 |
| RMSD kernel G | 0.8 | 0.5 |
| B=C×G | 0.72 | 0.40 |
| Required feature distances, Å | 0,1,1,2 | 1,2,2,3 |
| Feature kernels at scale 1 Å | 1,0.5,0.5,0.2 | 0.5,0.2,0.2,0.1 |
| F = sum / 4 | 0.55 | 0.25 |
| E=B×F | 0.396 | 0.100 |

\[
\boxed{A102=\max(0,0.396-0.100)=0.296.}
\]

The value means that, under the declared convention and comparison panel, the supporting structural correspondence exceeds the incompatible correspondence by 0.296 units. It does not mean a 29.6% probability of the function.

If the supporting reference's last site is **unresolved**, its known kernel sum is 2.0 and `F∈[2/4,3/4]=[0.5,0.75]`; `E∈[0.36,0.54]`; with the unchanged competitor, `A102∈[0.26,0.44]`, point null. If that feature is instead **established absent**, its kernel is zero, `F=0.5`, `E=0.36` and `A102=0.26`. Missingness and absence have distinct numerical meanings.

For an explicit synthetic sensitivity calculation, suppose each RMSD has a valid ±0.2 Å hard bound and each listed feature distance has a valid ±0.2 Å hard bound. Apply the formulas in section 5, truncating the lower distance at zero. Exact results are in `checked_examples_001.json`; these are conditional worst-case bounds, not statistical confidence intervals. The checks do not reinterpret the published cases' unknown errors as these synthetic bounds.

Duplicate the supporting row or its literature/dataset representation: `S=max(0.396,0.396)` stays 0.396, so the margin stays 0.296. Add a second supporting correspondence with E=0.30: still 0.296. A genuinely stronger incompatible correspondence with E=0.50 gives margin zero, while S=0.396 and O=0.50 remain reported. A comparison to a different, incompatible domain scope is retained in another panel and is not silently subtracted or pooled.

Length check: a hypothetical 100-residue exact substructure in a 200-residue reference gives native-TM-formula values 1 and 0.5 when all matched distances are zero. This draft's TM descriptor is 0.5. Multiplying by symmetric coverage 2/3 again would give 1/3 and is prohibited double normalization. Naming a 100-residue reference domain instead would define a **different scope**, not a correction of the original row.

RMSD check: under a fixed illustrative transform and 2 Å kernel scale, distance pairs `[2,2]` and `[0,sqrt(8)]` both have RMSD 2 Å, but their mean kernels are 0.5 and 2/3. This proves why a mean RMSD/count pair cannot determine the mean distance kernel, still less a native optimized TM score. It also explains why the proposed RMSD compression is explicitly labeled as a separate convention.

## 8. Shared evidence, consistency, contradictions and nondetection

One alignment's RMSD, Z, TM, map, coverage and site comparisons are multiple views of **one structural comparison**. Native metrics are not summed as separate proofs. A coordinate deposition, a paper figure and a downloaded copy of the same model share one determination. Symmetry-related chains, molecular-replacement models, predictions from the same template and alternative outlier cutoffs are not automatically independent replications.

Reference pooling uses `max` to avoid adding the same structural chain repeatedly. This deliberately gives no replication bonus; independent replication is reported in separate numerical diagnostics. A new reference can change the maximum, and contradictory references remain in the panel. Max is a conservative anti-counting convention for repeated support, not a complete statistical model of replication or a license to select whichever model version gives the largest number.

For alternative parameterizations or representations of the **same underlying comparison**, use the explicitly source-designated primary result. If none is designated, retain all admissible variants, compute their individual products and give their range with point null. Do not select the largest value by default. Structurally different states are separate condition-specific rows; a state range is only reported for a clearly defined scope of variation. This also preserves genuine contradictory correspondences rather than averaging them away.

An actual failed structural search can be recorded with the searched database/version, thresholds and covered query scope. It is not an RMSD of infinity or a universal absence claim. If the tool explicitly bounds its similarity statistic, retain that bound in its native cell; otherwise it gives no numerical geometry bound beyond missingness. Missing image tables, failed web access, missing residue maps and unreported results are **not nondetections**.

The same target/reference chain may appear on A101, A102 and A111. Retain shared evidence identities so later credit wiring can avoid treating a repeated underlying observation as independent. No cross-axis score multiplication or global weighting is installed by this draft.

## 9. Source-to-cell table

| Source | Inspection in this workload | Cells and design issue grounded |
| --- | --- | --- |
| [Stieglitz et al. 2002](https://doi.org/10.1074/jbc.M201042200), via retained AF2372 packet | Complete packet and numerical companion; prior source limitations preserved | Native RMSD/count/lengths; global versus local distinctions; state/model dependence; unavailable exact operands |
| [Hwang et al. 1999](https://doi.org/10.1038/10745), author-posted full text | Complete primary body, Methods, tables, captions, references; publisher Fig. 3 pixels at available resolution | Contrasting native Z/RMSD/counts, partial domain scope, limitations of copying specific function |
| [1B78 entity 1](https://data.rcsb.org/rest/v1/core/polymer_entity/1b78/1), [1ADJ entity 1](https://data.rcsb.org/rest/v1/core/polymer_entity/1adj/1), [1ATI entity 1](https://data.rcsb.org/rest/v1/core/polymer_entity/1ati/1) | Focused current RCSB metadata via skill | Deposited polymer length denominators; no alignment or domain map inferred |
| [Official TM-score documentation](https://zhanggroup.org/TM-score/), [help](https://zhanggroup.org/TM-score/help.html), [implementation](https://zhanggroup.org/TM-score/TMscore.cpp) | Documentation and exact normalization/kernel code sections; not whole program review | Native score units, normalization orientation, length-dependent scale, distinction from aggregate RMSD |
| User numerical template002 and full instruction/reset set | Full post-paper reread twice | Numerical cells plus explicit sums/products, source conversion, no categorical grade, three-part separation |
| This draft, equations and synthetic fixture | Proposed policy arithmetic only | 2 Å/1 Å scales, equal feature means, max pooling and contrast margin; **not sourced calibration** |

Full coverage and reset receipts are `inspection_coverage_001.json`, `authority_reset_001.json`, and `authority_reset_002.json`. Retained web extracts are under `sources/`. The RCSB skill used was [rcsb-pdb-skill](../../../../.codex/plugins/cache/openai-curated-remote/life-science-research/1.0.3/skills/rcsb-pdb-skill/SKILL.md); its actual absolute location is recorded in the handoff. No second structure search or comparison job is hidden in a metadata lookup.

## 10. Exact future population interfaces — all unimplemented

The sheet defines its cells first. These are targeted future interfaces, not delivered readers or generic scoring agents.

| Future function | Exact inputs | Exact outputs into this sheet | Determinism / limit |
| --- | --- | --- | --- |
| `read_reported_structure_comparison` | Retained source segments with page/table identifiers; source-linked typed extraction of compared objects, metric/count and qualifiers | `native.rmsd`, `native.z`, `native.n_pairs`, `native.n_rmsd_points`, reported lengths and uncertainties; unresolved fields null | Literal extraction requires source confirmation; arithmetic and unit conversion deterministic. No inferred chains or hidden alignment |
| `read_native_alignment_record` | Actual native output, declared software/version/settings, both scoped sequences/models, residue-pair table and transform(s) | Native scores, normalization lengths/scales, atom map, transforms, unique pair counts and output uncertainty | Deterministic parsing/consistency checks; must not run a new alignment |
| `read_scoped_structure_metadata` | Supplied construct/sequence scope plus coordinate-file metadata or explicitly joined accession metadata | Scope and observed lengths; model/chain/state/quality fields with actual provenance | Deterministic counting/joins; deposited sequence is not automatically biological full length |
| `populate_feature_geometry` | Declared required physical-feature set; atomic definitions/equivalences; actual residue/atom maps, transforms and coordinates | K, per-feature distances, kernel inputs, present/absent/unresolved counts | Distances/counts deterministic. Choice of function-relevant features needs source-grounded interpretation; no intuition grade |
| `populate_structural_components` | Native cells, named profile, explicit 2 Å/1 Å parameters, required-feature set, missingness/uncertainty records | C,G,B,F,E and separate nominal/missingness/measurement bounds | Equations in this sheet; no learned calibration or model-composed numeric score |
| `populate_comparison_panel` | Registered target/function/scope, explicit supporting/incompatible/shared/unresolved relationships, source dependency links, declared profile and variants | S,O,A102, preserved contradictory/other-scope rows, duplicate groups and exact bounds | Numerical pooling deterministic after the scientific relationship and scope are supplied; different function names alone cannot populate opposition |

A complete populated-row output is `{scope_ref, profile_ref, B, F, E, native_cells, feature_cells, missingness_bounds, measurement_bounds, uncertainty_status, source_refs, dependency_ref}`. A panel output is `{target_material_ref, function_ref, scope_ref, profile_ref, supporting_row_refs, opposing_row_refs, excluded_scope_row_refs, unresolved_row_refs, S, O, A102_nominal, A102_missingness_bounds, A102_measurement_bounds, panel_limitations}`. References bind to actual records; they are not public-name prerequisites or scored cells. Restricted relationship values mean `supports_declared_function`, `incompatible_for_declared_contrast`, `shared_feature_only`, or `unresolved`; these choose a scientific comparison set, not numeric category weights.

An input failure preserves valid native cells and names the unresolved relationship: `missing_scope_length`, `unknown_atom_denominator`, `missing_pair_map`, `mismatched_metric_scope`, `missing_required_feature_set`, `unresolved_feature`, `undefined_competitor_panel`, `mixed_metric_profiles`, or `conflicting_source_values`. No extra model call composes recorded facts. The proposed readers remain unimplemented, and they are not inserted into any episode prompt.

## 11. Draft completeness and open judgments

Every proposed calculation, unit, denominator, normalization, coefficient and missing-input behavior above is defined. The published examples have actual native numerical values and checked derived rows; the synthetic fixture fills the complete combination. The source trace, dependence rules, contradictory-scope treatment and future fields are concrete. The check script is research arithmetic over fixed examples, not a production scorer or reader.

The **published function-specific point scores remain unfilled** because exact sites, maps/states and compatible contrast panels are missing. They are not left to an unspecified intuitive grader. Actual coordinate reconstruction/alignments were outside this assignment. The score conventions still require the user's judgment: the 2 Å and 1 Å scales, equal feature means, conservative max pooling, unit subtraction and separate treatment of metric profiles are proposed, uncalibrated choices. Feature sets must be source-grounded for each emerged function; no universal catalytic-site list is claimed.

The parent must print the formulas and examples for feedback. This draft does not satisfy that conversation criterion by merely existing on disk, and does not mark any axis complete. Later feedback can change the proposal additively. Implementation, dataset-reader demonstration, cross-axis credit integration and any adopted mixed-metric policy remain separate work.
