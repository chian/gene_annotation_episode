# Published case 2: the organism's cellular process constrains the transferred role

Source: Lindås et al. 2008, [PNAS](https://doi.org/10.1073/pnas.0809467105),
one of the primary reports in retained case `cellular_cdv`. Only this report
was inspected; the second paper in that case was not opened. The retained
HTML/text in this folder came from PMC. Primary text lines 124–529 cover the
abstract, complete main Results, Discussion and Methods. The full authority
reset was completed before this interpretation.

## Experimental definitions and source operands

Sulfolobus acidocaldarius DSM639 cells were examined in exponential growth.
The baseline localization comparison follows native CdvA/B/C through cell
stages; it is not mutant replacement or mixed WT/mutant expression. Fig. 1
places leading-edge segregation onset at approximately 50–60 min and division
10–15 min later. Figs. 2–3 report native bands associated with constricting cells,
including occasional bands before visibly separated nucleoids. Cell counts
needed for frequencies are not supplied in the inspected text. Tunicamycin
increased band-bearing cells threefold, but the underlying counts are absent.
The authors report that conditional mutants at 81°C had severe viability and
morphology defects that prevented a clean interpretation. CdvB/C resemble
eukaryotic endosomal-sorting components; the proposed archaeal role is division.

Source locations: Fig. 1 caption; “Colocalization…”; “Effects of Antibiotic…”;
Discussion; Methods, “Strains and Growth Conditions” and “Immunostaining.”

## Context conversion

Sequence similarity to a protein known in endosomal sorting does not make
“endosomal sorting” the physiological role in every organism. A108 separately
asks whether the proposed cellular site and life-cycle event exist in this
organism. A104 still owns ancestry; A107 owns partner coexpression; perturbation
effects remain A106. This comparison needs cellular-state information even
when there is no measured environmental-exposure dataset.

| Emerged role and A108 requirement | Exact operand | Numerical interpretation |
|---|---|---|
| Component operating at a gradual cytokinetic constriction; the organism must generate such a division site | Observed native S. acidocaldarius constriction morphology in Figs. 2–3 | For the narrow **existence of this cellular opportunity in this organism**, one observed target organism-context satisfies the requirement: 1/1=1, conditional on the stated morphological interpretation. This is not the fraction of cells with a Cdv band. |
| Endosomal cargo sorting; an endosomal compartment is necessary | Number/presence of endosomal compartments in the exact target organism and permitted role context | Not established by this report's division images. Sheet value [0,1], point=null. Do not infer measured organelle absence from “archaeon,” or fabricate a negative endosome census. A supplied anatomy record establishing absence would give [0,0] for this requirement. |
| Role strictly requiring visibly completed genome segregation before any Cdv assembly | Necessary-condition claim itself | Do not install this requirement: the reported early bands contradict its necessity. Do not count early bands as defective organism context for a broader division role. |
| Transfer from this strain to all members of an archaeal clade | Target-specific division mode or a measured phenotype population and explicit transfer scope | Missing. Membership in the same named clade is insufficient. The phylogenetic presence/absence figure is not a phenotype frequency or A108 multiplier. |

The first row concerns the organism's capability to make a constriction site;
it does not use Cdv fluorescence as an independent A108 functional proof. Native
cell morphology provides the context operand. Cdv's location supplies a separate
protein-to-process relationship, and that original observation is identified as
shared wherever another axis consumes it. If the target is not this strain,
the context must be observed or explicitly transferred rather than copied.

## Calculations and limits

The interval sum [50,60]+[10,15]=[60,75] min is the broad onset window implied by
the reported approximate ranges. It is not a confidence interval, an independent
sample distribution, or a permissible timing window for every cell. No overlap
score is calculated by treating these ranges as uniformly populated.

The reported threefold enrichment has form
`(band-positive treated cells / all treated cells) /
(band-positive control cells / all control cells) = 3`.
Its four counts and sampling design are missing. It supplies neither an absolute
context-compatible fraction nor an A108 effect-isolation number. Drug treatment
changes the cell-cycle composition and remains a perturbation experiment.

Baseline stage comparisons concern the same species and growth regime; cell
stage is deliberately different. Antibody background, image selection and
independent cell/culture denominators are separate validity questions. The
presence of a constriction site is not specific proof that any one Cdv protein
causes it. Individual-protein contribution requires the other evidence axes.

This source contrasts with the porphyran example: a novel ecological role is
not excluded because characterized homologs came from a different habitat;
here, a familiar homolog's process label is not copied until the target's
cellular setting is established. Both arguments produce explicit required
trait operands, rather than a generic “typical for this clade” grade.
