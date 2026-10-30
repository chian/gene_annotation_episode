# IscR2013 experimental structure: primary-source review and component proposal

Status: original-source research packet for independent parent review. One paper, DOI [10.1038/nsmb.2568](https://doi.org/10.1038/nsmb.2568), [PMC3676455](https://pmc.ncbi.nlm.nih.gov/articles/PMC3676455/), with its three directly associated deposits [4HF0](https://www.rcsb.org/structure/4HF0), [4HF1](https://www.rcsb.org/structure/4HF1), [4HF2](https://www.rcsb.org/structure/4HF2). No second paper, target mapping/alignment, structural superposition, runtime/grader installation, annotation-credit work or scientific episode execution occurred. The source-local calculations below do not imply a complete A111 implementation.

## Return to the user's three-part template

The article supplies experimental observations and limitations. It does not replace the template. Investigation instructions identify the precise structural question and separate density-supported assignments, fitted geometry and causal inference. The numerical sheet contains actual distances, fractions, diagnostic residuals and explicitly conditional products. Targeted extraction/calculation operations populate those cells. They are separate responsibilities; no complete sheet is inserted into a prompt.

The current A111 proposal was located through fixed progress016 and reread in full with its extraction crosswalk after source inspection. Its target correspondence `T` is explicitly outside this literature task. The proposed additive boundary is a **reference-only structural component** `p_ref=q D_X G+ C I`, `o_ref=q D_X G− C I`; later work owns any use of T and any credit. This does not silently set T=1, calculate a target score, or modify the existing proposal. Missing local RSCC prevents a complete source product here. Raw geometry remains useful partial work.

## What was actually studied

Original-source locators refer to `article_clean.txt` BioC passage numbers, original HTML section titles, Table1 and figures. The original retained HTML and BioC are both copied without changes. `DEPOSITION_EXTRACTION_001.json` preserves native mmCIF categories, selected atom rows, missing residues/atoms, revision metadata and inventories.

- Organism: E. coli IscR, expressed in BL21(DE3) for crystallography. The general strain-construction paragraph names PK7878, BL21(DE3) ΔhimA::tet ΔiscR::kan, whereas the crystallography-specific paragraph says BL21(DE3). The latter does not itself establish that its host has both deletions. Preserve these two source scopes; the precise crystallography host genotype is unresolved beyond its explicitly named BL21(DE3) background.
- Every crystallization construct is C92A/C98A/C104A, with a C-terminal 6×His tag. The crystallography preparations are Ni-affinity purified, exchanged into 25 mM Tris pH7.5 and 150 mM NaCl; E43A uses 500 mM NaCl. These are the structural preparations, **not** the separate anaerobic fluorescence-assay preparations with fractional Fe-S loading or EDTA/dithionite removal. No 27–56% or 40–50% Fe-S occupancy is assigned to a crystal from those binding experiments. [Methods: passages45,47–51.]
- 4HF1: IscR-3CA, source sequence residues1–162 plus GG linker and HHHHHH (170 deposited polymer positions), two protein chains A/B plus DNA chains C/D. DNA is a 29-mer type2 hya site: C `ATAAATCCACACAGTTTGTATTGTTTTGT`, D `ACAAAACAATACAAACTGTGTGGATTTAT`. Coordinates represent the coexisting protein-DNA complex. The preparation mixes protein and DNA at a stated 1:1 molar ratio, final500 μM each; the wording does not specify protein monomer versus dimer concentration. Do not equate this mixing ratio with the observed two-protein/one-duplex stoichiometry. Hanging drops use an equal volume of 0.2M ammonium sulfate and20% glycerol. [Results passage8; Methods47; `_entity`, `_entity_poly`, `_atom_site`.]
- 4HF2: E43A in the same3CA background, same170-position tagged polymer format and same two29-mer DNA entities. It is a separate preparation/crystal, not E43A and Glu43-containing protein co-mingled in one structure. Buffer salt500 versus150mM and phosphate0.2–0.3M versus sulfate0.2M qualify comparisons; the intended E43A substitution is not the sole preparation difference. [Methods45,47; `_entity.pdbx_mutation`.]
- 4HF0: DNA-free3CA(1–133), GG linker plus6His (141 deposited positions), generated because full-length3CA did not crystallize without DNA. Hanging drops at room temperature use2–2.2M ammonium sulfate and20% glycerol. The intended DNA-bound/unbound contrast also changes construct boundaries and crystal conditions; a pure DNA-induced causal change is therefore not isolated by this pair alone. [Methods48.]
- All three are clusterless experimental constructs; there is no holo-IscR crystal in this paper. The absence of Fe-S modeled atoms is consistent with the engineered3CA design. It is not a measured wild-type Fe-S occupancy upper bound, nor evidence that a physiological metal site does not exist. [Results8; Discussion37.]
- A phasing preparation uses SeMet and K51M/K69M/K103M/K159M to strengthen anomalous signal, at2.90Å. That derivative is not silently assigned to native4HF1 or to all constructs. SAD phasing, PHENIX Solve/Resolve/Autobuild, manual Coot building, molecular replacement from the derivative and TLS refinement create shared methodological/model dependencies. [Methods49–51.]

## Native measurements versus models and interpretations

X-ray intensities are experimental measurements. Electron-density maps depend on amplitudes/phases and processing; the fitted atomic coordinates are a model. The paper's images1–3 depict fitted models, not raw density. Figure6 is the proposed mechanism schematic. The article reports only weak/missing density in the cluster region and cites supplementary Fig5 for a map portion. The supplementary PDF was not obtained: the retained earlier PMC response is an HTML challenge, and this worker's Springer-CDN attempt failed DNS. No supplementary density figure is claimed inspected. Coordinate and structure-factor CIF files were actually acquired for all three deposits; no raw diffraction-image files, density-map recomputation, map inspection or independent real-space validation was performed.

Table1 reports one crystal per dataset. An asymmetric-unit pair is not two independent crystal replications; three different construct/state structures are not three repeats of an unchanged endpoint. The phasing derivative, native datasets and reused initial model must remain separate observations with shared-template edges. Binding and mutagenesis can test a functional interpretation but are neither independent structure replications nor direct catalytic measurements.

| Native Table1 quantity | 4HF1 IscR-DNA | 4HF2 E43A-DNA | 4HF0 DNA-free |
|---|---:|---:|---:|
| Resolution high limit, Å |2.22|2.99|1.90|
| Rwork, % |20.28|22.94|19.33|
| Rfree, % |22.79|26.11|22.05|
| Rfree−Rwork, percentage points, derived |2.51|3.17|2.72|
| Completeness overall, % |94.0|98.8|99.98|
| Completeness highest shell, % |72.1|95.0|100.00|
| I/σI overall (highest shell) |17.57 (5.04)|15.36 (5.15)|16.89 (2.78)|
| Protein B factor, Å² |57.90|89.27|30.90|
| DNA B factor, Å² |87.50|122.48|inapplicable; table has0|
| Protein atoms |1913|1744|1743|
| DNA atoms |1183|1183|0|

These evaluate different quantities. Resolution is a reciprocal-space limit, Rfree a held-out diffraction residual under its selection, B a fitted displacement parameter, and completeness a reciprocal-space sampling fraction. No single confidence grade follows, and none replaces local RSCC. B factors are not coordinate SEs. Reported precision supplies no sampling uncertainty. Table bond-length/angle RMS deviations (.004Å/1.01°, .004Å/1.02°, .008Å/.98°) describe model restraint deviations, not experimental contact errors. The Methods report98.8%,96.5%,99.1% allowed Ramachandran regions; this does not supply a local side-chain assignment probability.

Source disagreement is retained: deposited Rfree4HF1 is.2277 rather than Table1's22.79%;4HF2 is.261 rather than26.11%, with Rwork.229 rather than22.94%. The difference is small but not silently reconciled as equality or selected by best score. 4HF1 refine high limit2.222 versus displayed2.22 reflects another representation. 4HF2 structure-factor header reports high limit2.222 while the paper/refinement uses2.99; this packet does not establish why. A future real-space calculation must bind the correct selected refinement/reflection data rather than substitute that header as the final resolution. Current depositions have revision histories, including later repository updates; these are retained current depositions, not asserted byte-identical2013 downloads.

The paper reports a homodimer and single duplex in4HF1's asymmetric unit. The PDB assembly describes four polymer chains as “tetrameric”: two are protein and two are DNA strands. That string is not evidence for a tetramer of four IscR proteins. 4HF0 also has a software-defined alternate tetrameric assembly alongside an author/software dimer. Preserve assembly provenance; it does not demonstrate a solution tetramer.

Paper Fig1 says density is missing beyond136 and144 for the two color-coded chains; deposition auth A ends144 and B ends136. No conflict is inferred by assuming that a figure color defines chain A. Explicit missing-residue lists are retained. Source-native unmodeled ranges include:

| Deposit | Protein chain A | Protein chain B |
|---|---|---|
|4HF1|89–103;145–170|85–91;137–170|
|4HF2|87–103;133–170|85–99;137–170|
|4HF0|85–97;134–141|85–101;136–141|

These include different tags/linker extents. Omitted coordinates mean unmodeled/unresolved in this refinement, not physical absence from the sample. Selected Arg59 side-chain atoms are unobserved in DNA-free data; explicit missing-atom rows, not residue omission alone, distinguish side-chain uncertainty. No alternate location labels other than `.` occur in modeled polymer atoms; absence of modeled alternates does not prove a single physical conformation. Deposited protein/DNA occupancy parameters are1.00. Their fixed/free refinement status is not established, and those parameters are not measured population occupancies. 4HF0 contains sulfate and37 waters; the0.50 occupancy appears in sulfate atoms, not a partially populated IscR/DNA contact.

Model-derived architecture includes wHTH major/minor-groove contacts, a dimerization helix and the approximate3400Å² interface area. Preserve the paper's surface-area convention as incompletely specified; this worker did not recompute it. The reported8.4° bend,33.1° twist,14.3 versus11Å major-groove widths and20°/5.8Å changes are descriptions/comparisons of fitted models and ideal B-DNA, not independent structural repetitions or measurements of DNA-binding energy. No structural alignment was rerun.

Observed/model-supported contacts in Fig2 concern Glu43 with C7/C8 and C7′/A8′, Ser40 with purines, Gln44 with thymines, and Arg59 in the minor groove. The proposed holo-state Glu43 relocation, electrostatic exclusion of type1 DNA, and intersubunit cluster signaling are interpretations from apo structures plus complementary functional evidence. They are not direct observations of a holo/type1 complex; Fig6 labels uncertainties. A contact does not itself quantify affinity, free-energy contribution, transcriptional activation, or catalysis.

## Paired extraction fields and populated numerical sheet cells

The bounded numerical example asks a narrower physical question: in the retained4HF1 model, are the Glu43 carboxylates proximal to the four named exocyclic amines? It does not test a reaction mechanism. Every selector is model1, author chain/residue/atom ID, no symmetry transform, no alternative-location selection. Chain pairing A→D and B→C names the two source binding interfaces; C7/C8 are DC/DC and D7/D8 DC/DA. This is identity resolution inside one experimental complex, not target correspondence.

`d_j = min(||OE1−N||, ||OE2−N||)` inÅ uses the **defined two-oxygen chemical group**, retaining both distances. This is not minimum-over-alternative models or assignment cherry-picking. The test intentionally does not assert a specific oxygen identity, hydrogen orientation or donor angle. Proposed supporting set `[0,3.5]Å`; incompatible set `[4.5,∞)Å`; the intervening gap is unresolved rather than automatic opposition. These thresholds are an illustrative explicit proposal, not reported paper cutoffs or a calibrated H-bond classifier.

| Exact extraction selectors | Minimum group distance,Å, coordinate-derived | Enters positive set? | Enters incompatible set? |
|---|---:|---:|---:|
|A GLU43 {OE1,OE2} to D DC7 N4|2.814260471|1|0|
|A GLU43 {OE1,OE2} to D DA8 N6|3.504470573|0|0|
|B GLU43 {OE1,OE2} to C DC7 N4|2.648124053|1|0|
|B GLU43 {OE1,OE2} to C DC8 N4|3.056920182|1|0|

The complete fixed panel hasJ=4; `G+=Σpositive_j/4=3/4=.75`, `G−=Σincompatible_j/4=0/4=0`. Each number evaluates **specified model-geometry compatibility**, not general experimental validity. Changing the proposed positive threshold to3.6Å yields4/4=1;3.4Å retains3/4. That sensitivity belongs beside the result; no boundary-based declaration disproves the paper's hydrogen-bond interpretation. Contact3.504Å also lacks a reported uncertainty bound, so its conditional classification is not robust experimental separation from3.5Å.

| Sheet cell | Exact extracted input / proposed definition | Numerical output and meaning | Missing/uncertainty/dependence |
|---|---|---|---|
|`G+`,`G−`|four atom-group distances and disjoint predicate sets above|.75 and0; model compatibility fractions|one fitted dataset; no independent-n increase from four contacts|
|`q_model_conditioned`|condition on the selected modeled atom state|1 by declared conditional definition|unconditional measured occupancy remainsnull; deposited1.00 retained separately|
|`D_X`|fixed residue panel A43,B43,D7,D8,C7,C8, native local RSCC; `min(max(0,RSCC)^2)`|null, logical[0,1]|local validation/map analysis not performed; resolution/Rfree do not fill RSCC|
|`C_single_state`|single deposited-state geometry statement, no intended causal contrast|1 by scope definition|does not extend to DNA-bound/unbound or E43A causal comparisons|
|`I_assignment_conditioned`|one modeled eventY=1, alternative-assignment contributionB=0 under explicit atom-assignment conditioning|1 underthat narrow condition|not a measured bound on biological/chemical misassignment; unconditionalI remainsnull|
|`p_ref`|`q_model_conditioned D_X G+ C_single_state I_assignment_conditioned`|null, logical[0,.75]|D_X missing; neither1 nor.75 is imputed as complete evidence|
|`o_ref`|same product withG−|0 algebraically under this conditional geometry panel|does not fillD_X or establish no other opposition|
|`N`|calibrated occupancy upper limitqU and entailed minimumqreq|unavailable|no such experiment/limit here; missing density is not exactzero|
|`T`, targetA111, globalcredit|deferred beyond reference-literature scope|null|no target mapping or aggregator is implemented|

The source-local product is a proposed conventional index, not a likelihood or probability. Its factors belong to a **single** chain. The two half-sites are chemically different C/C versusC/A, so this packet keeps four separate constraints in one declared question rather than assuming equivalent physical populations and averaging independent evidence. If a later task declares truly equivalent copies, average their complete products with fixed membership before evidence reduction. Distances, model occupancy and local fit reuse one model; do not give them separate independent-proof bonuses.

Useful additional numerical cells are diagnostics, not score multipliers: source-coordinate coverage is129/162=.796296 for each4HF1 chain,115/162=.709877 and121/162=.746914 for4HF2,120/133=.902256 and116/133=.872180 for4HF0. Those denominators are source-construct native residue spans, excluding GG/His tags. This is **not** A101 alignment coverage and says nothing directly about the contact's local density. Completeness percentages retain reciprocal-space denominators; do not confuse them with source-coordinate coverage. Rfree−Rwork uses the same dataset'spercent units, as explicitly calculated above; it is a diagnostic of fitting/generalization difference, not `(1−Rfree)` confidence.

## Necessary revisions and remaining exact work

1. Separate the currentA111 reference cells from itsT/target reduction; this task supplies only the source side. Preserve native observations, exact subjects/constructs and declared conditioning. Later W05/target workflows choose how to join them; this worker does not.
2. Add `occupancy_refinement_status` and an unconditional occupancy missing reason. An occupancy column of1.00 must not create a population measurement. No arbitrary grade replaces that missing information.
3. Carry `measurement_basis=diffraction|map_statistic|fitted_coordinate|reported_interpretation`, `used_for_refinement`, exact map/model/reflection binding, method/version and source-version disagreements. A coordinate-derived distance and local RSCC are different measurement/model relationships.
4. Preserve explicit side-chain unobserved atom lists, omitted native residues versus tags, alternative-location IDs and model/state alternatives. They are needed to evaluate whether all required endpoints exist.
5. Structural causal contrasts require nuisance/exclusion panels. DNA addition also changes truncation and crystallization conditions; E43A comparisons change salt and precipitant. Those are comparability questions. Isolation additionally needs an actual bound or experiment addressing alternate causes of the structural change; matching conditions alone is not such a bound. No salt-response scale, causalB/Y or factorC is fabricated.
6. A future local-fit reader must inspect valid localRSCC tied to these actual coordinates/reflections or compute it with declared map/model settings. File acquisition alone does not establish a fitted map statistic. The failed supplementary access remains a source limitation. A valid validation acquisition would be new source work requiring the post-packet reset.

Targeted deterministic operations actually executed here: retained-file custody hashing; boundedmmCIF token/category extraction; exact atom selectors and Euclidean distances; predicate fractions; source-coordinate coverage; native percentage arithmetic; partial-input propagation. `inspect_depositions_001.py` is a small research parser, not a general validatedmmCIF library. Initial development exposed a quoted-underscore token-boundary error and a polymer-inventory inclusion of waters; the retained extraction uses quote-aware tokens and polymer label selectors, and source-native coverage excludes tags/nonpolymers. No broad production capability is inferred from these checks.

The original Table1 selection is manually transcribed, explicitly labeled, and attached to original HTML. Ten bounded checks in `ARITHMETIC_CHECKS_001.json` establish this packet's arithmetic and preservation of missing inputs. These are not general reader tests, model-backed literature extraction, typed parent delivery, reconstruction verification, controller-observation accounting tests or evidence that the adopted goal is complete. The required production relationships remain unfinished outside this worker's permitted research-only scope.

## Concrete aspect-specific interpretation questions for later review

These are proposed content responsibilities for an existing literature task, not installed prompts or a new episode type. A full recurringTASK must include the assigned structural question, supplied source material, observed molecule/construct/state, model-versus-observation distinction and requested field meanings; a separate curtSTEERING block supplies relevant earlier outcomes. No whole scoring sheet belongs in either.

- Given the crystallography Methods and accession record, which preparation, mutation set, boundary and partners actually produced this dataset? Allowed outcomes: source_explicit; conflicting_source_scopes; not_reported. Return exact fields/anchors; never import binding-assay occupancy or invent a genotype.
- For each proposed structural assertion, is its basis a measured diffraction quantity, local map statistic, fitted coordinate geometry, or author inference? Allowed outcomes: these four defined bases, mixed_with_explicit_members, unknown. A holo-state mechanism diagram cannot populate directholo contact measurements.
- Is the occupancy a deposited parameter, a demonstrably refined estimate, a measured population fraction, or a conditioned state? Allowed outcomes preserve unknown refinement status; no truth-confidence number is requested.
- Does a claimed causal structural comparison differ only in the intended variable? Return each explicit nuisance difference or unknown, and identify which field affectsC versus which actual contributor bound is available forI. Do not turn that list into an overall number.

Models resolve these experimental meanings and selectors; the deterministic calculator performs arithmetic. Any future inference prompt still needs the parent's separate template review under current instructions. No second model call composes or restates parsed facts.
