<!-- Latest review002 supersedes the named wording error in REPORT.md; see RESEARCH_CORRECTIONS_001.json. Earlier draft is preserved. -->
# A105 Fluc case: actual transport evidence and numerical section proposal — review002

Research proposal only. No production reader, grader, episode, prompt, controller or credit function was changed. This one experimental study does not establish A105 adequacy. Parent messages are deliberately metadata-only; the parent must read this packet, perform its own required reset, then print the useful definitions, numbers and proposed TASK before coding.

## Source and version

Stockbridge RB, Robertson JL, Kolmakova-Partensky L, Miller C. *A family of fluoride-specific ion channels with dual-topology architecture.* eLife 2:e01084 (2013), DOI [10.7554/eLife.01084](https://elifesciences.org/articles/01084). Publisher primary-source XML and HTML as served on this research date, plus Figures 2 and 3, are retained under `source/`, with custody hashes. This is not an archived pre-correction edition; no claim is made to have inspected the historical erroneous Figure 1 image. The article is CC BY.

The [formal correction, eLife 01700](https://elifesciences.org/articles/01700), corrects swapped La1/La2 sequence labels in Figure 1A. It does not report a new experiment, change the selected Ec2 electrical measurements or provide an independent replicate. Preserve the correction alongside the original study. The selected calculations below concern Ec2, avoiding interpretation of the corrected La sequence alignment. No sequence-transfer scoring is performed.

The source was read in three stages: selected Methods/Results/captions/construct table and original figures; formal correction; then a newly relevant full Discussion section exposed by a source-witness check. Each was followed by this agent's own complete authority/current-contract reset. `POST_PAPER_RESET_001.json`, `POST_CORRECTION_RESET_002.json` and `POST_FINAL_SOURCE_RESET_003.json` identify the actual full reads. The final component conversion follows the third reset. No second experimental paper was opened.

## Establish the actual experiments

The principal electrical subject is **Fluc-Ec2**, from an *E. coli* virulence plasmid, reference sequence YP_001481330.1 (Table 1). The expression host is *E. coli* BL21-DE3. Synthetic constructs carry a C-terminal LysC recognition site and hexahistidine tail, given in Methods as TRKAASLVPRGSGGHHHHHH. The precise tag-cleavage state in the selected electrical traces is not specified by those passages; the separate topology experiment's proteolysis must not be assigned automatically to the electrical preparation. Exact construct sequence boundaries and a measured active fraction remain unresolved in this packet. Purification by affinity, ion exchange and size exclusion supports preparation identity but does not measure zero contaminating activity.

The paper also reports Bpe liposome assays, but Ec2 and Bpe are separately prepared proteins, not coexisting wild-type/mutant molecules. A single preparation can contain multiple functional channel units. The study concludes a dimeric functional architecture, while its Discussion explicitly leaves one versus two parallel pores unresolved. Per-functional-unit, per-polypeptide and per-pore denominators must remain distinct.

| Arrangement | Actual measurement and controls | Intended comparison and relevant additional differences |
|---|---|---|
| Ion-specific electrode efflux from reconstituted liposomes, Figure 2A | External anion appearance after valinomycin; detergent releases remaining trapped anions. Liposomes contain 150 mM KF and 150 mM KCl in *E. coli* polar lipids. | F versus Cl transport is the functional distinction. The electrodes differ. Results describe both external anions, whereas Methods say 1 mM KF **or** KCl according to the measured ion; preserve this source-condition qualification. No electrode calibration uncertainty or raw detection-limit derivation is supplied here. |
| Macroscopic planar-bilayer recording, Figure 2B/C | Electrical current and reversal under defined cis/trans ionic conditions; trans is ground. Before addition/closed levels and protein-dependent appearance provide different control information. | High-density liposomes deliver packets of multiple proteins. A large insertion step is a vesicle event, not one channel. These recordings establish bulk conductance/selectivity and do not identify active molecule number. |
| Low-density planar-bilayer single-unit recording, Figure 3 | Reported dominant insertion-step amplitude relative to the fully closed-channel mean; low-density reconstitution plus the step histogram supports unitary event interpretation. | This deliberately changes the density to resolve functional units. It does not make every event one channel or prove a pure, known active population. Smaller events and subconductance states remain real qualifications. |

The bilayer is POPE/POPG. Electrical salt-gradient conditions are cis 300 mM NaF, trans 30 mM NaF, Mops-NaOH pH7; the source identifies an approximately eightfold **activity** gradient despite the tenfold concentration ratio. The bi-ionic arrangement is 300 mM NaF versus 300 mM NaCl. Voltages were corrected for junction potentials whose stated magnitudes were below 3 mV. That correction magnitude does not quantify the remaining voltage uncertainty. Macroscopic signals were low-pass filtered at 500 Hz and sampled at 2 kHz; single-channel signals were subsequently filtered at 100 Hz. Do not manufacture a specific missed-event correction or temporal resolution from bandwidth alone.

## Pair extraction fields with numerical section cells

These are sections/components within the logical A105 sheet. They are not new axes, generic quality grades or independent proofs merely because several cells are populated.

### Observed signal, normalization and functional attribution

Source `s2-2`, Figure 3 caption and Methods `s4-6` support:

| Extracted source field | Native value | Meaning |
|---|---:|---|
| Dominant insertion-step magnitude |1.8 pA | Representative dominant amplitude, not a reported population mean/SD. The source defines its zero using the closed-channel level. |
| Recording voltage |−200 mV | Voltage relative to trans ground. |
| Salt-gradient reversal central value |53 mV | Reported summary from separate bilayers under the stated ionic condition; it is not an event-specific paired reversal measurement. |
| Reversal reported spread |±1 mV | Error type and exact averaging estimator are not defined in the selected caption. Do not call it SD or SEM. |
| Reversal repeat basis |4–5 separate bilayers | A range of bilayer counts; not exact independent protein-preparation n. |

The targeted electrical calculation is a **chord-conductance** conversion at the stated condition:

    DeltaV = Vrecord - Ereversal = -200 - 53 = -253 mV
    g_chord = 1000 * step_magnitude_pA / abs(DeltaV_mV)
            = 1800/253 = 7.1146245059 pS.

This is a nominal conversion using reported central/representative quantities from a common ionic-condition interpretation. It is not a per-event paired estimate, a fitted differential slope or evidence of an Ohmic current–voltage relation over every voltage. The source's reported conductance is 7 pS; the new calculation and that source value reuse the same signal, so their agreement is not independent validation.

Omitting reversal would give 9 pS. The omitted-driving-force result is larger by 253/200=1.265, or 26.5%. This is a deliberately incorrect counterexample, not another observation or a proposed score. It shows why concentration/voltage context belongs in the extraction contract before a current can inform functional comparison. Treating the driving force as 200 mV silently changes the denominator.

Using exact SI elementary charge e=1.602176634e-19 C:

    monovalent_charge_equivalents_per_second = 1.8e-12/e
                                              = 1.1234716334e7 s^-1.

Current/e counts **monovalent charge equivalents**. Assigning all of this to F ions additionally uses the ion-selectivity interpretation; no exact measured fraction of F-carried versus other current is supplied. Retain the authors' approximately 10^7 F-ion/s interpretation separately from this charge conversion. A numerical F-specific fraction must not silently become1. Likewise, a protein-dependent step and closed-channel baseline are not a measured zero contaminating conductance from every source.

If separate open and closed current measurements are available, their signal combination is `DeltaI=Iopen-Iclosed`. Here the source already reports a step amplitude relative to its closed level. Do not subtract a second blank. A functional-rate model could subsequently use `J_F = phi_F * phi_channel * abs(DeltaI)/(abs(z)*e)`, but unmeasured attribution fractions stay unknown; this paper's representative current does not populate them automatically.

### Gating contribution and uncertainty

The source reports full-open occupancy greater than 95% at the investigated voltages. Preserve that as a reported lower limit, not as exactly 0.95 or a reliability multiplier. If the occupancy and full-open amplitude are linked to the same unit/time-window under the same condition, treating the representative amplitude as a point estimate gives this **nominal conditional threshold arithmetic** for the full-open-state contribution:

    Pfull * Jfull > 0.95 * Jfull = 1.0672980518e7 charge equivalents/s.

This is only nominal arithmetic for that state under the stated interpretation; it is not a verified physical or confidence lower bound for every channel. The same-unit/time-window linkage and amplitude uncertainty are unresolved, so an actual jointly estimated mean-rate cell remains unknown. It does not reconstruct total measured average flux or determine contributions from substates. For a fully observed level series the correct compilation is `Jmean = sum_s(P_s*J_s)`, with mutually exclusive level meanings and covariance retained. No raw dwell-time series was extracted here. The approximately 20-s all-points histogram is not a set of independent biological measurements.

For a signed current model `g=I/(V-E)`, first convert current and voltage to SI amperes and volts. If native pA/mV units are retained instead, include the conductance conversion factor in the gradient. First-order uncertainty would be:

    grad_g = (1/(V-E), -I/(V-E)^2, I/(V-E)^2)
    var_g = grad_g * Cov(I,V,E) * grad_g_transpose.

This defines the necessary uncertainty cell and its operands. It is not populated here: amplitude variance, error definitions, voltage uncertainty and cross-covariance are unresolved. The published ±1 mV cannot be used as known variance or a confidence interval. Preserve reported spread alongside an unavailable propagated variance. These are missing scientific inputs in this packet; the absence of an electrical unit/variance reader in the inspected transport path is a separate implementation gap.

### Ion specificity: keep the experimental denominators separate

The electrical bi-ionic experiment reports reversal 119±3 mV and an approximate lower permeability-ratio limit around 100. Preserve it as the authors' model-derived approximate lower limit. A recalculation under a Goldman-type bi-ionic model would require the applicable convention, temperature and ionic activities:

    PF/PCl = exp(F*Erev/(R*T)) * (a_Cl_trans/a_F_cis)

for the stated monovalent-anion/cis-trans convention and limiting model. Equal nominal 300 mM concentrations are not proof of equal activities. Neither temperature nor the full relevant activity/model information is supplied by the selected passages. Leave a recomputed permeability ratio unknown. Do not compare raw current magnitudes at different driving forces as permeability ratios.

The Discussion supplies an additional important limitation/result: matched liposome assays have a reported Cl turnover upper limit below 30 ions/s and F turnover lower limit above 30,000 s^-1. Arithmetic on those reported thresholds gives a ratio greater than 1000 under the source's common-assay/unit interpretation. The Results separately qualifies the F lower estimate as approximate, based on assumed liposome size and the instrument's dead-time. Thus this is **reported-limit arithmetic**, with those qualifications; it is not a confidence bound on a precisely identified permeability parameter.

The same Discussion reports an overall selectivity stronger than 10^4-fold using liposome and electrical information. Preserve that assertion separately. The two displayed liposome thresholds alone do not derive the stronger bound. Dividing a voltage-clamped single-channel electrical throughput by a liposome chloride limit requires additional comparability/driving-force/active-unit linkage. Those methods use different membranes, counterions, voltage control and readout calibrations. Do not promote that cross-assay quotient automatically to a matched specificity score; do not call the source statements contradictory simply because one bound is weaker.

Cl nondetection is consequently not exact zero or infinite selectivity. The numerical upper turnover estimate is reported in Discussion; it is not absent from the paper merely because Figure 2A's chloride trace looks flat. Its underlying raw detector threshold and unitary-turnover derivation remain unresolved here.

## Why the liposome endpoint is not an initial rate

Valinomycin-stimulated F release outruns the stirred-cuvette dead-time. The paper explicitly precludes a measured initial rate in this assay. A total-release-normalized plateau is a released fraction, not a molar/time rate. The raw template should retain the initial baseline, plateau and detergent endpoint before computing:

    released_fraction = (signal_plateau-signal_initial) /
                        (signal_detergent-signal_initial).

No absolute plateau values were digitized in this packet, so that proposed cell remains unpopulated. The shared initial and detergent signals create covariance between normalized curves/cells. A residual fraction can inform the fraction of vesicles without active transport under the assay, but it does not by itself prove physical absence of all Fluc protein; inactive or inaccessible units are possible alternatives unless independently resolved. The paper's Poisson-dilution inference depends on its reconstitution/model assumptions. Do not turn the approximate empty-vesicle fraction into an exact channel count or active fraction.

## Complementarity, independence and scientific bearing

The electrode assay directly detects external anion appearance and supplies chemical specificity information, but fast F transport prevents initial-rate resolution. Electrical recording resolves rapid discrete conduction events and gating, but current is charge flow and unit interpretation needs event-density/baseline/ion-selectivity evidence. Reversal behavior provides a complementary discrimination between anion and cation contributions. These weaknesses and complementary experiments must be named; counting three assay views as three independent replications is wrong.

The source histogram has 63 insertion events from approximately 50 bilayers. Keep insertion count, bilayer count, observation time and protein-preparation count separately. The independently prepared proteins enumerated for the separate Poisson-dump assay must not be borrowed as the independent preparation count of Figure 3 current measurements. The exact preparation ownership of the selected Figure 3 events is unresolved.

The supported functional interpretation is passive, strongly F-selective conductance by the studied Fluc preparation under the measured artificial-membrane conditions. It does not establish ATP-driven transport, universal unidirectional export, exact pore count, native membrane conductance, organism-wide physiological contribution or transfer to a different protein. Those distinctions constrain the functional assertion; they are not generic categorical penalties.

## Reader/calculator work and scope of reuse

The inspected `literature_transport_inputs.py`, `literature_transport_calculations.py` and `literature_transport_prompt.py` implement substrate-test/reference/Km selection, a common-curve interpretation and Michaelis–Menten saturation response. That is a useful condition-response component for an applicable carrier experiment. It does not consume current, voltage, reversal, state occupancy, electrical baseline, detector dead-time or ion-permeability limits. A channel does not acquire a Km merely because the file is named transport.

Before adding another operation, root should check whether existing generic source-span/figure/controlled-comparison paths already supply usable pieces. Custody, exact token selection, uncertainty ownership, typed admission and saved reconstruction patterns can be reused. The required missing scientific contract here is electrical/liposome-assay specific: distinguish net step from current levels, packet insertion from supported unitary events, voltage reference/driving force, chemical versus charge endpoint, censoring/reporting mechanism and actual sampling units. No exhaustive claim about every other module is made from the three transport files alone.

The proposed targeted numerical outputs are chord conductance, charge-equivalent throughput, conditional state-weighted contribution, same-arrangement reported-limit ratio and their separately unavailable uncertainty/attribution/model components. Native source claims, qualifiers and original identities accompany those numbers; they do not replace them. The same physical measurements feed several views, so dependent identities remain shared through child returns. A proposed TASK is in `TASK_PROPOSAL_002.md`; the paired field/component record is in `EXTRACTION_AND_COMPONENTS_002.json`. These remain proposals until root review, conversation examples and implementation.

No generic overall reliability/validity/relevance probability or category-weight formula is adopted. The source-based numerical components and explicit uncertainty/specificity relationships are the literature handoff for later credit work. Sequence/structural correspondence and final annotation aggregation remain outside this case.
