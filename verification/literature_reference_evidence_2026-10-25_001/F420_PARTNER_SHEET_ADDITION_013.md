# Coupled experimental activity and partner interpretation

Additive case-grounded extraction/sheet refinement for A105 and experimental
partner rationale. This is not an eleventh axis, an A101 implementation, an
A107 genomic/coexpression calculation, or final annotation-credit aggregation.
The complete active goal remains unchanged.

## Original experiment and what it isolates

Hasan et al., 2022, DOI 10.1128/mbio.03501-21, PMC8764529, examines purified
CofC/CofD pairs. Mycetohabitans sp. B3 CofC (KQH55_09515; native216aa) coexists
with either M. jannaschii CofD (WP_010870769.1; native311aa) or its cognate B3
CofD (KQH55_09505; native323aa). They are successive catalysts within one assay.
The experiment does not compare two replacements of CofC or measure an isolated
CofC reaction. A partner swap changes CofD identity between the two arms.

The source describes N-terminal His-tagged recombinant proteins, nominal26uM
CofC/34uM CofD, three competing substrates each at .5mM,2mM GTP,2mM MgCl2,
100mM HEPES pH7.4 and50uL volume. LC-MS extracted-ion areas are normalized and
product formation evaluated over0–20min. The source renders Fo as0.14nm; its
unit remains unresolved here. Protein production uses E.coli BL21(DE3) or
LOBSTR-BL21 without assigning the particular preparations in the inspected
methods. Native source-organism identity is not the expression-host identity.

The reported n=3 is labelled biological; distinct preparation identities are
not established here. SD bars are available as plots but not transcribed by
this increment. Mean-bar digitization cannot supply their SD or covariance.

Relevant full primary paragraphs, Figures2/6 and complete native DOCX TablesS2/S3
were inspected; unrelated structural/phylogenetic Results/Methods and other
supplements were not. The complete mandatory post-paper reset preceded scoring
conversion, as recorded in primary_f420_partner_013/PARENT_RESET_001.json.

Comparability concerns the conditions outside the intended CofD identity swap,
including active amounts, preparation backgrounds and quantitative response.
The intended partner change is not a nuisance penalty. Isolation is different:
the final product depends on CofC activation, CofD conversion, intermediate
stability and measurement response. Nominal excess CofD does not establish
complete intermediate recovery or identify CofC's intrinsic specificity.

## Numerical cells and their populating functions

The first direct native reader is read_bar_ordinate(image_bytes,selection) in
literature_figure_measurements.py. Selection declares the exact original pixel
ROI, RGB mean-fill threshold, fixed two-point linear axis calibration and edge
tolerance. It returns a native ordinate, outward digitization bounds, original
image hash and exact selection. No axis, protein identity or statistical
meaning is inferred from pixels. compare_ordinate_cells subtracts two such
ordinates with outward bounds and explicit percentage-point units.

| Numerical component | Actual populated value | Meaning and role |
| --- | ---: | --- |
| Figure2C B3-CofC/Mjan-CofD 3-PG ordinate |75.528596%|Graph-derived coupled relative-turnover ordinate, not molar activity or confidence |
| Figure6B same nominal pair 3-PG ordinate |65.488959%|Separate source representation; original physical-unit correspondence unresolved |
| Figure2C minus Figure6B standard-pair ordinate |10.039637 percentage points; conditional digitization domain[9.464214,10.615060]|Numerical representation-consistency diagnostic. Statistical significance and whether the underlying experiments are identical remain unresolved |
| Figure6B B3-CofC/B3-CofD 3-PG ordinate |89.968454%|Cognate-pair relative-turnover observation |
| Figure6B cognate minus standard 3-PG |24.479495 points; domain[23.848580,25.110410]|Partner-swap coupled-output difference; not increased absolute catalytic activity or upstream-only specificity |
| Same swap,2-PL-derived product |−23.343849 points; domain[−23.974763,−22.712934]|Signed change retained, not clipped to favorable support |
| Same swap,PEP-derived product |−7.949527 points; domain[−8.580442,−7.318612]|Distinct product endpoint; no automatic pooling with the3-PG comparison |
| Quantitative partner-omission effect |null|No such operand is established by the inspected swap measurements |
| CofC-alone activation selectivity |null|Downstream recovery/loss and response-calibration operands missing |
| A105 source likelihood/reliability components |null for this extraction|Known variance, measurement attribution and applicable observation model not supplied by digitization |

The source prose reports65%,26.5%,8.5% for the standard B3 pair. This is retained
as reported text; it does not overwrite either plotted representation. Different
means and SD bars alone do not prove a publication error or statistical conflict.
Native plot quantization, sampling spread, normalization and unresolved source
representation identity have different meanings and remain separate.

The difference components are sums with explicit coefficients(+1,−1). They can
populate an A105 source-contrast or consistency analysis when its actual error
model is supplied; they are not independent proofs to add to a reliability
score. For a supported paired normal difference, the existing A105 route needs
the actual paired differences, independent pair count and paired sample SD.
For a supported known-covariance contrast it needs the actual covariance.
This increment supplies neither and does not invent an S, bounded index or
confidence level. Final target correspondence and W05 combination stay later.

## Corrections to the retained conversion and necessary extraction fields

The earlier retained template_a105_reactions_001/05_f420_partner_2022_001.md is
preserved as history. Its claimed denominator of the sum of final-product
rates must not be treated as newly verified from the inspected Methods.
Those Methods describe AUC normalization without identifying enough of its
denominator/calibration to establish molar fractions. The plotted percentages
are preserved without renormalizing them to sum100. Product-specific response
factors, raw areas and their covariance remain unextracted.

Required extraction fields developed from this case are:

- Both assayed molecule/construct identities, their native organisms and
  expression hosts; nominal and active amounts separately.
- Coexisting catalysts within an arm versus the replaced partner between arms.
- Sequential-catalyst, physical-complex, binding and necessity relationships
  separately. An arrow in a pathway diagram does not establish a stable complex.
- Product-specific endpoint, numerator and normalization denominator; reported
  relative signal versus calibrated molar flux.
- Each original figure/text/data representation, its physical measurement/unit
  linkage and unresolved duplicate/conflict status. Equal labels do not establish
  independent experiments or identical original measurements.
- Graph extraction recipe, digitization domain, native SD/error interpretation,
  repeat label and actual independent-unit identities separately.
- Quantified omitted-partner/addback arms, detection limits, changes outside
  the intended factor and applicable functional boundary when necessity is
  actually tested. No omission result is manufactured for a swap experiment.

If final flux v_j is interpreted as upstream activation a_j times downstream
recovery q_j, a_j=v_j/q_j and its selectivity require measured q_j and a supported
kinetic/recovery model. Unknown q_j is not1. A direct intermediate measurement,
calibrated recovery/loss experiment or appropriately justified independent
single-step assay could address this isolation gap. A correction applied to
rates must not become a second penalty on the same evidence.

## Proposed aspect-specific investigation instructions

Determine what the measured activity establishes about the reference molecule
and its assayed partners. Identify every catalyst present in each reaction,
which molecule changes between arms, and whether the readout measures an
intermediate, final product or indirect response. Trace which steps and
measurement responses can change that readout. Separate a partner swap from
omission and addback. Preserve quantitative controls, source conditions,
normalization, error meanings and original measurement identities. Resolve
whether each result concerns the pair, one component, binding, a sequential
pathway or an obligatory physical complex. Retain competing source
representations and unknown requirements. Models identify these experimental
meanings; readers and calculators supply numerical components.

These instructions were explained in chat before expansion. They are a proposed
scientific TASK addition, not an installed episode prompt or a wholesale sheet.

## Executed scope and unfinished integration

The fresh owner implemented the pure reader/comparison and70 meaningful checks.
The coordinator read the code, corrected a cropped-ROI mean-edge error and
percentage-point units through additive clarification014, then executed seven
original graph selections and four numerical comparisons. Independent exact
rational calculations confirmed the returned means and bounds. Original
images, recipes, hashes and results are retained in primary_f420_partner_013.

This helper is not yet bound to a selected LiteratureEpisodes operation or its
typed child return. No whole partner workflow or axis is complete. The existing
source_quantity path only handles specific_activity/apparent_km and cannot
silently accept relative-turnover bars. Selected custody and typed handoff of
both catalysts, source representation meaning and digitization bounds remain
necessary integration work. A quantitative omission/addback source case is
still needed to develop the actual requirement components. Computational
partner presence/coexpression and final annotation credit remain separate.
