# A111 native cryo-EM / NMR numerical handoff

**Goal:** extend the existing A111 experimental-observation→mapped-target-feature chain with concrete local observation calculations for cryo-EM and NMR. Criteria: actual native inputs, exact conversions/missingness, contrasting source rows, full joined arithmetic and exact reader cells. This is a bounded research specification for judgment. No policy or completed axis is claimed; A105 remains first and the recorded completed count remains0/10.

The existing combination is preserved:

\[
w=q\,D\,G\,T\,C\,I.
\]

q is measured occupancy/exposure or an explicitly conditional model state; G is the fixed physical-predicate fraction; T is preserved required roles under an actual mapping; C is measured nuisance comparability; I separately bounds attribution to the intended component. D now has the following additional defined native paths.

| Defined path | Native operands | Exact proposed conversion | Numerical meaning |
| --- | --- | --- | --- |
| Cryo-EM local Q | Required local atom/residue Q_j∈[−1,1], same retained map/model | `D=min_j(max(0,Q_j)²)` | Local resolvability index, using the weaker required endpoint. Not global FSC, resolution or an assignment probability. |
| Assigned NMR NOE distances | Experimental bound[L_j,U_j], modeled effective distance d_j, all Å; fixed local panel J | `v_j=max(0,L_j−d_j,d_j−U_j)`; `s_j=exp[−v_j²/(2×.50²)]`; `D=Σs_j/J` | Local restraint agreement conditional on assignment/model. .50 Å is an explicit proposed scoring tolerance, not a measured SD. |

No required endpoint/panel is silently dropped. Q=.8 plus one missing endpoint yields D=null [0,.64]. An NMR panel with v=.5 Å plus one missing restraint yields D=null [.303265329856317,.803265329856317]. Global structure-quality labels, NMR ensemble RMSD and total restraint counts do not fill these cells.

The contrasting actual source calculations are:

| Published case | Actual selected native values | Derived local result |
| --- | --- | --- |
| Cao2013, TRPV1 RTX+DkTx, 3J5Q | G643 local Q pairs(.385,.395),(.374,.430); opposing oxygen distances7.7311,7.7686 Å | Copy D values .148225,.139876; mean .1440505; both satisfy the illustrative width≥6 Å predicate |
| Cao2013, capsaicin state, 3J5R | Q pairs(.337,.338),(.315,.372); distances4.1573,4.7137 Å | D .113569,.099225; mean .106397; both satisfy the declared incompatible width<6 Å predicate |
| Bae2016, K1/2N9Z, medoid9 | Local NOE bounds[0,4.43],[0,5.50] Å; model distances4.078006,3.116844 Å | Violations0,0; D=1 |
| Bae2016, K2/2NAJ, medoid3 | Bounds[0,4.18],[0,4.73] Å; model distances4.516512,3.531801 Å | Violations .336511596354,0; D=.8986676009902625 |

The cryo-EM state contrast changes both the small agonist and toxin presence; it does not isolate a toxin-only effect. C cannot fill the missing attribution bound B for I. The NMR lobes differ in sequence/length and their20 conformers per deposit are model scenarios, not20 independent experiments. Their cross-loop≤4 Å question gives G=1 in both medoids but crosses the boundary across both ensembles. The support-only full-product DG envelopes are K1[0,1] and K2[0,.9205446855153534]. No measured ensemble populations are inferred. [Cao2013](https://pmc.ncbi.nlm.nih.gov/articles/PMC4023639/), [Bae2016](https://elifesciences.org/articles/11273)

Actual target correspondences were not supplied for those papers: T remains null [0,1]. Thus those rows have model-conditional source calculations and bounded target contributions, not invented complete annotations. The separate synthetic examples fill every factor:

| Synthetic example | Complete row arithmetic | Existing whole-sheet result, α=β=1 |
| --- | --- | --- |
| Cryo-EM | E1 copy products `.75×.64×.75×.75×exp(−.0625)×.8=.202913221568` and `.75×.49×1×.75×exp(−.0625)×.8=.207140580350`; copy mean .205026900959. Independent E2 incompatible product `.5×.36×1×.75×1×1=.135`. | P=.102513450480; O=.0675; **Z=A=.035013450480** |
| NMR | N1 `1×.803265329856×.5×(2/3)×1×1=.267755109952`. Independent N2 incompatible `1×.603574684971×1×(2/3)×1×1=.402383123314`. | P=.133877554976; O=.201191561657; **Z=−.067314006681; A=0** |

Each row's counts, bounds, geometry, target roles, conditions and attribution operands are printed in `WORKED_JOINED_EXAMPLES_001.md`. The target role maps are supplied synthetic `DY`→`DF` (3/4 required roles) and `WK`→`WR` (2/3), not homology grades. Negative Z is retained when A clips to zero. Support and opposition share the same denominator. Copies are averaged over their **full products**; averaging D and G separately gives a different, incorrect result.

Paper text, coordinates, restraints and validation of one dataset are one observation. Shared templates/raw data retain dependence. Missing density or a missing NOE supplies no opposing score without a calibrated relevant upper detection limit. The existing N replaces q only when the actual `q_U` and `q_req` operands exist. Nothing here measures catalytic activity, affinity or a perturbation effect by proxy.

The old experiment-roster mean is retained and its limit is exposed: adding a third known-zero-transfer cluster to the synthetic cryo-EM example changes Z from .035013450480 to .023342300320. That is a mean over the declared roster, not cumulative target support. No silent reducer replacement is made.

A localized cross-link can fit the same physical-feature chain, but a set-level PSM/peptide-pair FDR does not determine a particular contact's support. If an actual calibrated per-contact error p existed, the explicit conditional transformation could be D=1−p; no such p is established in this packet. Generic XL-MS coverage is therefore not claimed. Assigned intermolecular NOE distances use the already defined NMR path. The retained exploratory cross-link paper download was not substantively reviewed or used.

**Exact future readers remain UNIMPLEMENTED:** local Q extraction; experimental NOE bound/assignment extraction; single/R-6/SUM/CENTER distance calculation; the two defined D transforms; complete-product scenario collection; and existing row/reducer population. Their fields, units, domains, missing reasons and actual XML/MR selections are in `READER_IO_ADDITIONS_001.md`, with optional physical-weight arithmetic clarified separately. The investigation prompt remains a separate artifact; no scoring sheet or schema is inserted into it.

Finite policy choices for judgment are Q² with a weaker endpoint; the fixed-panel NOE kernel with τ=.50 Å; conditional points plus unweighted scenario envelopes; and preservation or separate correction of the original product/roster mean. These calculations are explicit now; their correctness calibration across modalities and production use remain unverified.

Verification:41 bounded script checks passed, plus4 separate arithmetic checks for scope/weight clarifications and the mean-of-products distinction. No source-independent claim of experimental validity follows from those checks. The full authority set was read initially, after each of the two reviewed source packets, and again after the final numerical audit; exact coverage/truncation repairs are logged. All work is confined to this new directory; no production code, native structure job, annotation run or HPC work occurred.
