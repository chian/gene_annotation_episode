# A105 assay interpretation: Aquifex HFP and a contaminating isomerase

This is one case analysis, not a completed scoring sheet. The source is
Hoffpauir and Lamb (2025), DOI
[10.1016/j.jbc.2025.108443](https://doi.org/10.1016/j.jbc.2025.108443),
[PMC12051542](https://pmc.ncbi.nlm.nih.gov/articles/PMC12051542/). Main-text
Methods/Results/Discussion and associated main figure legends were inspected
from retained original HTML and its text projection. Supplementary images/raw
integrations were not inspected: the DOCX link returned HTML, and the PMC
availability skill's configured endpoint returned 404. Source-access and full
reset provenance are in the companion files. No application scientific run,
controller observation, production change or annotation credit was created.

## Define the experiments before calculating

The studied reference is the A. aeolicus histidine-family phosphatase HFP/PP17,
heterologously produced in E. coli BL21(DE3). The initial PP constructs were
codon optimized in pET20b with a stop before the C-terminal histidine tag. A
separate C-terminally tagged HFP construct was subsequently prepared. These
constructs/preparations must remain distinct. The retained case index supplies
the aq_1744 locus label; this review did not independently verify that mapping
against supplementary Table S1. The reference is not the workflow's annotation
target.

There are several different experiments in this paper:

1. **Preloaded pathway screen.** ARAPDP and DHBP were generated before candidate
   phosphatases were added; later lumazine/riboflavin enzymes supplied a coupled
   optical readout. Both HFP and IMP preparations produced a coupled signal
   consistent with the required dephosphorylation; this is an experimental
   inference from the coupled assay, rather than a direct initial-rate assay.
   The raw observation is a spectrum, with riboflavin assessed at 470 nm to
   reduce interference from species absorbing at 410 nm. A positive pathway
   signal is not a direct initial-rate measurement of HFP.
2. **One-pot pathway comparison.** Separate vessels received HFP or IMP along
   with the pathway enzymes and initial substrates. Nominal candidate amounts
   were 8.4 and 8.8 μM, respectively, with incubation at 55 °C for 4.5 h. Candidate
   phosphatase identity was deliberately changed; candidate amount also differed.
   Only the HFP-containing arm facilitated riboflavin formation in this arrangement. The HFP and
   IMP candidates replace one another between vessels; this does not establish
   that either preparation contains only one protein.
3. **Competing activities.** NMR examined GTP, NADPH and Ru5P under the specified
   conditions. IMP depleted NADPH/Ru5P, explaining how an enzyme capable of the
   desired dephosphorylation can nevertheless prevent the final coupled signal.
   HFP-preparation isomerization was identified by phosphorus/carbon NMR, but
   those measurements identify chemistry in the preparation, not its protein
   catalyst.
4. **Isomerase attribution controls.** Additional purification, a tagged
   construct and heating changed the observed time to equilibrium. Four of five
   randomly selected PP preparations also had isomerization activity, and mass
   spectrometry detected host RpiA in an HFP sample. These observations address
   attribution. They do not quantify the RpiA contribution to a matched HFP
   reaction rate.

## Numerical components that the inspected source can support

`NUMERICAL_COMPONENTS_001.json` retains operands, calculations and qualifications.
All source-derived values below are descriptive components or explicitly
conditional conversions; none is an overall reliability probability.

| Component | Source and operands | Calculation | Meaning and limits |
| --- | --- | --- | --- |
| Nominal target-mass to total-protein estimate | HFP purification, original HTML p0170: visual gel estimate about 5 mg/ml HFP; Bradford total-protein estimate 7 mg/ml | approximately 5/7 = 0.7143 | Measures disagreement between target-specific and total-protein amount estimates in that described stock. Different measurement methods and approximate gel estimation prevent treating this as a validated active fraction. |
| Conditional mass-denominator correction | Same stock estimates | approximately 7/5 = 1.4 | A same-stock per-total-mass rate would increase by this factor when expressed per estimated HFP mass, **if** those estimates and linkage were valid. No activity is corrected here; this is not recovery k or a reliability multiplier. |
| One-pot nominal amount comparability | One-pot Methods, original HTML p0195: 8.4 μM HFP and 8.8 μM IMP | 8.4/8.8 = 0.9545 | The HFP arm has about 4.55% lower nominal candidate amount. This accompanies the intended molecule change. It cannot supply a numerical activity correction without actual rates and a supported amount-response relationship. |
| Isomerization-positive control-panel fraction | Results, competing activities: four positive preparations among five examined | 4/5 = 0.8 | Describes this observed control panel. It is not HFP's probability of being a false annotation, a general assay false-positive rate, or independent biological replication. |
| Reported equilibrium-time contrast | Results: tagged/further purified preparation >18 h versus earlier sample <10 min | later/earlier time > (18 × 60)/10 = 108 | A strict duration-ratio lower bound. It is not an inverse rate ratio: construct, purification, recovered enzyme amount and assay linkage are not fully matched. |

The 39.7%/60.3% Ru5P/R5P equilibrium composition further supports that a real
isomerization occurred in the preparation. It does not identify the responsible
protein. Multiple purification methods, NMR confirmation and MS detection must
not be added as independent repetitions of the same molecular-activity claim.

## Fit the measurements to the existing assay sheet honestly

The existing point route has precise roles:

- q: already net sample-minus-blank concentration/time for the measured endpoint.
- g: separately quantified contaminant contribution to that same endpoint.
- k: quantitative recovery ratio.
- E: assayed-molecule molar concentration.
- u/v: separate same-endpoint nuisance-condition response outside the intended
  difference.

For the inspected one-pot passage, E can retain the **reported nominal** 8.4 μM
HFP or 8.8 μM IMP. It does not become an uncertainty-free active-site amount.
The current reader was exercised on those exact source spans using the immutable
023 implementation. Both values parsed correctly; q, g, k, u and v stayed null.
`populate_corrected_activity` therefore returned null for all six correction/
uncertainty/profile components with `correction_inputs_unreported`. These are
pure researcher-selected reader/calculator calls, not model-backed extraction,
repository population or typed runtime delivery. `EXISTING_READER_CHECK_001.json`
records this distinction and the source/parser hashes.

The selected endpoint was explicitly represented as the static optical readout
(`other_measured_endpoint`). Inspection of `LiteratureAssayRepository.populate`
shows its additional `endpoint_requires_different_model` guard for the correction
model; that repository guard was not executed in the pure check.

Do not substitute any of the descriptive ratios above for missing correction
operands. In particular, 5/7 is not k; RpiA presence is not g; a slow approach to
equilibrium is not q; the HFP/IMP intended comparison is not u/v; and a positive
control is not a measured no-enzyme blank. RpiA isomerization and riboflavin
formation are different endpoints. Subtracting their rates would require a
validated coupled-assay relationship, even if both happened to use molar units.

## Extraction fields, sheet cells and functions

| Required extraction | Numerical use | Existing support or actual gap in the inspected assay route |
| --- | --- | --- |
| Actual construct/preparation, host and coexisting proteins; observation and assay identity | Determines which values may enter the same contrast and normalization | Existing source-witness/assay literal fields and arrangement instructions; interpretation/linkage remain explicit. A nominal-versus-calibrated/active amount basis needs its own qualification rather than a bare E value. |
| Nominal molar amount with exact unit and source location | `protein_amount` E | Existing `_Sources.measurement` and `read_assay_inputs`; stock total mg/ml cannot replace E. |
| Total protein and target-specific amount estimates, measurement methods and approximation | Proposed target/total amount component and conditional denominator factor | Not represented by the current six-primitive assay contract. A targeted quantity/ratio reader and explicit approximate uncertainty would be needed; no new production function was implemented here. |
| Raw spectrum, wavelength, matched blank, dilution, matrix/path conditions and quantitative standard curve | Net final product concentration, then a rate only if time dependence is established | Current q input assumes an already reported net concentration-rate. It does not calibrate raw absorbance or establish pathway-to-target turnover. Those functions are unfinished for this source format. |
| Same-endpoint contaminant contribution and its linkage to the assayed preparation | g, then attributed rate q−g | Existing arithmetic supports a valid reported g. The inspected main text does not supply one. MS identification or a control-panel frequency does not fill it. |
| Independently quantified recovery of a known standard in this assay | k | Existing exact point reader and correction denominator; no recovery ratio was established here. |
| Same-endpoint nuisance-condition control excluding intended phosphatase identity | u/v | Existing reader and arithmetic; none was established here. |
| Actual paired observations, repeat/preparation identities, uncertainty and covariance | Corrected activity uncertainty and conditional profile components | Existing covariance ownership and propagation retain unknowns. “Triplicate” and 512 NMR scans do not establish three independent protein preparations or known covariance. |
| Exact censored time tokens, endpoint criterion and per-preparation conditions/amounts | Descriptive elapsed-time bound | Not rate operands. A duration parser can preserve this observation; a kinetic comparison additionally needs information the inspected text does not provide. |

## What a meaningful numerical conversion would require

The existing correction combines physically defined components as
`a = (q−g) × (1/k) × (1/E) × (v/u)`. This paper does not provide the required
matched inputs, so that expression stays unpopulated.

For a coupled optical assay, a separate proposed conversion would first use a
source-supported calibration function C and matched blank to obtain
`P_net = dilution × [C(A_sample) − C(A_blank)]`. A time series and validated
linear interval are needed for `q_product = dP_net/dt`; dividing a single final
absorbance by 4.5 h does not supply an initial rate. A separately measured
coupling relation `c = q_product/q_target` could then support
`a_target = (q_product−g_product)/(c × E)` **only** where the design establishes
that the background subtraction and coupling relation apply to those same
measurements. c is an endpoint-conversion relationship, not the existing
recovery k. None of A_sample, A_blank, C, c or g_product was obtained as a
quantitative matched input in this review. These are proposed field/function
requirements, not new measured numbers, adopted weights or a new global score.

Missing scientific measurements and missing implementation are separate: a new
optical reader would not invent the absent matched calibration, time series or
contaminant contribution. Conversely, retaining these missing inputs honestly
does not implement the new calibration/coupling conversion when suitable data
do become available.

The purity estimate, control-panel fraction and time bound must not be summed
as if independent support. They share preparations/assays and evaluate different
relationships. Their useful scoring consequence is to preserve the missing
attribution and calibration components while retaining the observed chemistry.
Final reference-to-target transfer and annotation-credit combination remain
separate later work.

## Scientific consequence and remaining qualifications

The coupled screen and competing-substrate experiments support different
assertions: performing the desired chemical step and functioning compatibly in
the complete substrate mixture. A failure in the one-pot readout does not erase
the earlier coupled evidence consistent with phosphatase chemistry. Likewise, authentic
isomerization in an HFP preparation does not establish HFP as its catalyst.
The host-contaminant evidence changes that attribution while leaving the
observed reaction intact.

A matched quantitative contaminant-removal/addback or selective-control
experiment, with preparation amounts and direct same-endpoint rates, would
address the attribution weakness. Direct calibrated product measurements and
validated coupling/linearity would address the optical-pathway conversion gap.
These are possible complementary investigations, not a mandatory itinerary.

Source discrepancies remain visible: the reverse-isomerization Methods passage
prints 0.67 **M**, whereas the preceding standard assay uses 0.67 **mM**; the
one-pot paragraph describes 400 μl mixture divided into two 250 μl vessels. The
original HTML confirms those printed statements. This review does not silently
repair them or infer exact cross-assay concentrations/volumes. Supplementary
figures, raw spectra, replicate-level values and batch correspondence were not
reanalyzed. No absence claim extends to uninspected supplementary material.
