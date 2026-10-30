# Printable A111 handoff

**A111 now has one coherent numerical research proposal for X-ray, local cryo-EM Q and assigned NMR distance restraints.** It is proposed mathematics, with exact reader fields and checked examples; no production adoption or real-target annotation is claimed.

Each observed structural feature reaches the target through explicit numerical components:

`support = q × D × G+ × T × C × I`

`opposition = q × D × G− × T × C × I`

Here q is measured occupancy/eligible-object fraction or a clearly conditional model state; D is local experimental fit; G+/G− are fractions of fixed physical predicates supporting/opposing the feature; T is preserved required molecular roles; C compares nuisance conditions excluding the intended change; I separately bounds attribution to the intended component. A model occupancy fixed at1 is not a measured occupancy probability. Transfer can use actual sequence mapping, structural correspondence or controlled measured interchangeability.

| Bounded native fit branch | Proposed calculation | Reused source example |
| --- | --- | --- |
| X-ray | `D=min(max(0,RSCC)²)` over required endpoints | MJ0577 ATP .963²/.958² gives copy mean .9225665. YwlE phosphate D .935089 contrasts with its poorer-fitted contact D .597529. |
| Cryo-EM | Same calculation with actual local Q | TRPV1 state copy means .1440505 and .106397 from their selected residue Q panels. The agonist/toxin state change does not isolate toxin action. |
| Assigned NMR distances | `v=max(0,L−d,d−U)`; `D=mean(exp(−v²/(2×.50²)))` over a fixed restraint panel | DkTx lobe medoids D1 and .898667600990. Their20-model ensembles are alternative fits, not20 experiments. |

These source values were inspected by the earlier structural/modality researchers and recalculated here from their cross-case receipts. All real-source target mappings remain unknown. The source-local numbers therefore do not become complete real-target scores.

**The changing-roster denominator is repaired.** For each fixed physical question, use the strongest current supporting chain P and strongest current opposing chain O. Then use fixed question/family weights:

`P111=Σα_fΣβ_fj P_fj`, `O111=Σα_fΣβ_fj O_fj`,

**`Z111=P111−O111`, `A111=max(0,Z111)`**.

| Same question's evidence | Old roster mean Z | Current proposal Z |
| --- | ---: | ---: |
| +.3655125 | .3655125 | .3655125 |
| Same, plus an experiment with T=0 | .18275625 | **.3655125** |
| +.3655125,+.2885625,−.486 | .056025 | **−.1204875** |

This measures the strongest documented evidence in each direction. Its explicit tradeoff is that additional weaker positive repetitions do not increase the scalar. Replication, disagreement and native uncertainty remain separately visible. Duplicated files collapse to one observation. Superseded fits are excluded from current maxima. Equivalent copies use fixed complete-product means; alternative conformers/states stay joint scenarios rather than competing simultaneous evidence.

The examples also repair a sign omission: a contact that meets the explicit opposing distance criterion is now counted as opposition even if other contacts in the same observation support the candidate. Missing required values remain null; no calibrated detection limit means no numerical nondetection opposition. An empty inventory has zero documented support with **unexamined** coverage, not a finding of biological absence.

| Complete synthetic example | Current result |
| --- | --- |
| Two X-ray feature families | P=.27875625,O=.243,**Z=A=.03575625**; sensitivity Z[−.0937404,.2965130125] |
| Cryo-EM contacts, one mixed observation and one contrary observation | P=.205026900959,O=.135,**Z=A=.070026900959** |
| NMR contacts, one mixed observation and one contrary observation | P=.267755109952,O=.402383123314,**Z=−.134628013362,A=0** |
| Candidate H_A across four fixed families, using all three modalities | **Z=A=.001727846899**; sensitivity Z[−.063020478101,.132106228149] |
| Candidate H_B with the same ligand/interface expectations and reversed EM/NMR geometry | **Z=A=.034028403101**; sensitivity Z[−.030719921899,.164406784351] |

The shared uncertain ligand/interface evidence cancels within each candidate-comparison scenario: **ΔZ_A−B=−.032300556202**, conditional on the exact synthetic EM/NMR operands. Neither candidate has robust positive absolute direction under the displayed sensitivity bounds. These are structural indices, not annotation probabilities.

Choices for judgment are explicit: RSCC/Q square and weakest endpoint; NMR tolerance .50 Å; products; fixed role/geometry definitions and weights; nuisance scales; strongest support minus strongest opposition. There is no essential undefined calculation within these finite branches. Calibration and policy adoption remain unclaimed rather than being added as completion prerequisites.

Verification: **112 bounded arithmetic assertions passed**, including40 retained NMR scenario recalculations, zero/duplicate invariance, updated-current-fit behavior, mixed opposition, missingness, and shared candidate uncertainty. No primary-paper reread, production reader/scorer test, native structure computation, annotation run or HPC work occurred. All new files are confined to `a111_complete_deliverable_027/`. The complete sheet, field crosswalk, worked inputs, source attribution and actual read/test log accompany this handoff.
