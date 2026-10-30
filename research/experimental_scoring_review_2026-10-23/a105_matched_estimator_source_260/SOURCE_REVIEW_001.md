# Research result: useful matched-chemistry limit case, no adequate estimator covariance

Research-only, original paper 10.7554/eLife.65773 (Rudolph, Roberts, Muthurajan and Luger, 2021), https://elifesciences.org/articles/65773. This packet does not establish the requested source-positive common-unbiased-estimate example. No production, test, existing research record, authority or goal file was edited. No models or provider services were invoked. The immutable original goal is unchanged, and no A105 or overall completion is claimed.

The concrete search gap was two molecular-activity estimates addressing a common unbiased quantity, with actual adequate estimator covariance. This original was selected because the article describes simultaneous HPLC quantification of substrate depletion and product accumulation in the same reaction, and releases numerical source workbooks. Search-result candidates were not treated as scientific evidence or read as additional paper packets. No arbitrary source quota applies; this report returns a concrete limitation promptly rather than manufacturing a successful case.

The complete own post-paper reset is recorded in OWN_POST_PAPER_RESET_001.json. The complete immutable goal, full authority set, all seven current-contract lossless pages, the258 review-only plan and its current formula/covariance resources were read, with latest human steering last, before this conversion. The258 full extraction/sheet schemas and production implementation files were not reread, and their implementation is not assumed. The seven current-contract pages supply complete current formal request/input/sheet contracts and relevant formula/unit/meaning domains.

## What was actually studied

This is a purified biochemical reaction containing wild-type PARP1, NAD+, and a nucleosome or DNA activator, with separate arms adding HPF1 wild type or E284A. HPF1 coexists with PARP1; it does not replace PARP1. The selected Fig6C no-HPF1 timecourse is a single arm, so its NAD+/nicotinamide comparison changes detection species rather than changing a protein. The plus-HPF1 arm introduces a partner and shifts product partition; it is not a replicate of the same-condition no-HPF1 arm.

The inspected selected source locations establish wild-type PARP1 but do not independently resolve organism, accession, construct termini, tags, or specific protein-preparation identity. Those remain unknown in this extraction. Methods delegate PARP1 expression/purification to an earlier publication; that separate paper was not opened. The source figure identifies Nuc165 as an activator/substrate, and the paper's Methods identify Widom601 nucleosome DNA. Expression-host and genotype details must not be inferred from a familiar protein name or imported from a target annotation. A parent needing those fields should inspect the original resource table/linked construct source and perform its own reset.

The Fig6 modified HPLC assay used PARP1 1µM, p18mer or Nuc165 1µM, NAD+ initially200µM, with or without HPF1 2µM, total reaction volume450µL. Aliquots45µL were withdrawn and acid-quenched into45µL perchloric acid1M. Protein precipitation, re-neutralization, and chromatographic analysis quantify NAD+, nicotinamide and free ADPR. This differs from the Fig5 one-minute assay (PARP1 100nM, smaller volume), so values from those figures cannot be joined as same-condition rates. Source locations are the Fig6 caption and the complete bounded HPLC Methods paragraphs in METHODS_HTML_SELECTORS_001.json.

The buffer is defined in Methods as50mM Tris-HCl pH8.0,50mM NaCl,1mM MgCl2,0.1mM EDTA,0.5mg/mL BSA. The temperature of the NAD-cleavage incubation is not explicitly established by the selected HPLC Methods paragraph; the later phosphodiesterase digestion has its own room-temperature condition, which must not be transferred backward to the cleavage reaction.

HPLC peak areas are converted to absolute concentrations by comparison with injected known quantities of NAD+, nicotinamide and ADPR, with source-supplied extinction coefficients. Same-run injection/extraction/calibration effects may be shared. No numerical blank or calibration uncertainty is released in these selected cells. The report that HPF1 alone has no detectable NAD-hydrolase activity is a qualified control, not exact zero. No active fraction, purity fraction or nuisance/background rate is invented.

## The released numbers and their experimental meanings

Original Fig6 workbook: originals/elife65773_fig6.xlsx; actual sheet Fig6C, ZIP member xl/worksheets/sheet2.xml. FIG6C_EXACT_SELECTORS_001.json retains all60 nonempty cells with exact XML-member offsets, exact cell XML, decoded cached value, original workbook and member SHA256. Header A1 is time(s), C1 NAD+, D1 nicotinamide(µM); B1 ADPR. Header D1 supplies the explicit concentration unit for the same labeled table; Figure6C/Methods independently describe absolute concentrations. No graph digitization was used.

| Native cell | Reported value | Meaning |
|---|---:|---|
| A2 |1s|first released no-HPF1 timepoint, not an assumed true zero-time point|
| C2 |200µM|remaining NAD+ at1s|
| D2 |6.5µM|nicotinamide at1s|
| B2 |2.8µM|free ADPR at1s|
| A5 |50s|later released timepoint|
| C5 |100µM|remaining NAD+ at50s|
| D5 |101µM|nicotinamide at50s|
| B5 |13.2µM|free ADPR at50s|

The same table also has no-HPF1 timepoints10,25,120,300,600,1200,3600s and a distinct plus-HPF1 ADPR/NAD+ timecourse in E/F. It has no replicate dimension, experiment IDs, SD/SEM values, joint estimator covariance, or nicotinamide column for the plus-HPF1 arm. Timepoints along a depletion curve are not repeated estimates of one constant concentration. The first arm's NAD loss and NAM gain plausibly address the same integrated NAD-cleavage amount after an explicit1:1 chemistry conversion, but this source does not establish that both are unbiased estimates with sufficient joint uncertainty.

Nicotinamide formation reports all NAD glycosidic cleavage, including protein ADP-ribosylation and free-ADPR production. It does not by itself measure hydrolase-specific activity. Free ADPR is a distinct output; treating free ADPR and total NAM as interchangeable estimates would erase the biological partition that this study investigates. Chromatographic chemical identification does not itself isolate every molecule-specific catalyst contribution.

## Conversion into numerical components

The following are proposed research component conversions and exact arithmetic from original cells. They are not executed populations of the current formal sheet. All native values above are reported; all numbers below are calculated; there are no synthetic numerical values.

Let S1=C2, S50=C5 be remaining NAD concentrations, N1=D2, N50=D5 be NAM concentrations, and A1=B2,A50=B5 be free-ADPR concentrations. The window has Δt=50−1=49s. Choosing a measured first point avoids substituting nominal200µM for an unmeasured zero-time baseline.

| Proposed numerical cell | Calculation | Value | What it evaluates |
|---|---|---:|---|
| substrate-loss concentration L |S1−S50|100µM|Observed NAD disappearance over the selected interval|
| product-gain concentration R |N50−N1|94.5µM|Observed NAM appearance over the same interval|
| signed mass-balance discrepancy D |L−R|5.5µM|Difference after conditional1:1 NAD-to-NAM reaction scaling|
| descriptive substrate/product ratio |L/R=200/189|1.0582010582|Agreement on this integrated reaction scale; not an accuracy or reliability probability|
| average substrate-loss rate |L/Δt=100/49|2.0408163265µM/s|Interval-average rate, not initial rate,Vmax,kcat or rate at saturation|
| average product-gain rate |R/Δt=27/14|1.9285714286µM/s|Interval-average NAM appearance on the same49s window|
| free-ADPR gain |A50−A1|10.4µM|Accumulation of a particular NAD-cleavage fate|
| free-ADPR gain / NAM gain |10.4/94.5=104/945|0.1100529101|Conditional integrated fraction of cleavage assigned to released ADPR; it does not estimate the same quantity as total cleavage|

Each difference is an explicit sum with coefficients+1 and−1. Each interval-average rate uses the fixed time multiplier1/49s. The product-fate fraction and the two cleavage estimates share NAM and/or NAD data: ratio, difference, average rates and fraction are dependent views, not separate independent evidence. A biological statement about hydrolase partition needs the free-ADPR numerator as well as the total-cleavage denominator. It cannot be replaced by the larger total NAD-cleavage signal.

The1:1 linkage is a chemical reaction model, not an invented quality weight. It requires no additional NAM source or NAD sink, comparable concentration recovery and analyte calibration, and an applicable reaction account. The source establishes intended cleavage chemistry, but not an exhaustive numerical correction of every possible sink/source or systematic recovery bias. Thus these data support descriptive linked-chemistry calculations and a conditional common-quantity interpretation; they do not establish two unbiased estimates to combine with GLS.

Current compiled-assay formal contracts inspected through root257's complete lossless pages use product/reporter turnover operands in per_min and have no direct terminal-concentration pairing/rate-window or paired-replicate covariance reader for this example. The current native inputs should not be fabricated by relabeling the amounts as kcat or inserting an unknown enzyme-active fraction. Review-only258 explicitly preserves terminal amounts without implementing their rate comparison. To admit these data appropriately would require a reviewed interval-concentration difference/rate reader with explicit timepoint/aliquot/calibration dependencies, keeping this denominator as reaction volume. That proposed extension is not coded here.

## Why estimator covariance is still missing

The observed tuple is U=(S1,S50,N1,N50), and the proposed linear estimator map is B=[[1,-1,0,0],[0,0,-1,1]], giving (L,R)=BU. With an adequate joint covariance C_U, estimator covariance would be C_LR=B C_U Bᵀ. The shared physical reaction, aliquots, HPLC instrument and calibration can create nonzero cross terms. No C_U is reported. Setting it to diagonal or inserting zeros from source silence is invalid.

If future genuine repeated reaction units supplied paired(L_i,R_i) at the same prespecified window, and an independent identically distributed reaction-unit sampling model were justified, the sample-mean estimator covariance could be estimated as s_pair/n, where s_pair=(1/(n−1))Σ_i[(L_i,R_i)−(Lbar,Rbar)] [(L_i,R_i)−(Lbar,Rbar)]ᵀ. This is a proposed estimator formula with no paper-derived numerical matrix. Technical replicates within independent experiment blocks would require the actual nesting/weighting model; dividing technical SD by total cell count would not establish between-experiment precision. Common calibration effects need their own propagation/coverage and can remain outside repeated-unit covariance.

The workbook provides one trajectory, not these paired repeated units. A sample covariance across its changing timepoints mainly captures the kinetic trend. It is neither covariance of(L,R) at one window nor covariance of a fitted rate. Treating50% substrate depletion and eventual exhaustion as linear initial-rate points would impose an unsupported kinetics/error model. A fitted two-output trajectory could, in principle, have a joint parameter covariance, but there is no reported fitted likelihood, residual-correlation model, replicate hierarchy or covariance sufficient to recover it here.

Accordingly V_D,standardized discrepancy,GLS multipliers,combined estimate,combined variance and any accuracy/reliability probability remain unknown. If actual adequate C for(L,R) were later supplied and the common unbiased-quantity model were supported, the proposed explicit sum would be μ=wL L+wR R, with wL=(C_RR−C_LR)/(C_LL+C_RR−2C_LR),wR=1−wL and variance(C_LL C_RR−C_LR²)/(C_LL+C_RR−2C_LR), subject to the covariance/domain treatment under review in258. None of those numerical weights is available from this paper. No arbitrary equal weighting or zero covariance is substituted.

## Complementarity, limitations, and next useful evidence

Experimental comparability is unusually strong for the two analytes in the same quenched reaction aliquot, subject to their different analyte calibration/recovery. That is separate from effect isolation: total NAM contains all cleavage fates, while free ADPR isolates the released-product fate, and neither proves exclusive catalysis by a named polypeptide through a numerical purity correction. A measured substrate/product balance can address unaccounted chemistry; a no-enzyme/matched-matrix blank and recovery control would address spontaneous loss/background and analyte response. These are specific complementary measurements, not compulsory assay quotas or categorical scores.

The released Fig5D sheet has four numerical columns per condition for percent treadmilling and for NAM-derived total activity. Headers do not independently establish cross-block same-column experiment identities. Even if genuine pairing were confirmed, a fraction and a total amount concern different quantities; algebraically reconstructing ADPR from their product would reuse them and would not create independent measurement validation. The separate Fig5/6 protocols cannot be pooled as matched conditions. This clarifies the earlier progress message that loosely called the Fig5 columns paired.

The next source-positive search needs raw paired same-window same-quantity measurements indexed by actual repeated reaction/preparation units, or an explicitly reported relevant joint fitted-estimator covariance, together with a supported sampling/chemical model. This original lacks that input in the inspected public workbooks. It remains useful as a source-grounded missing-covariance/endpoint distinction example. The full literature implementation goal and this specific positive-example gap remain unfinished.

The coordinator must independently read the original and perform its own complete reset before scientific interpretation. The packet's derived inventory and prose do not substitute for that review.
