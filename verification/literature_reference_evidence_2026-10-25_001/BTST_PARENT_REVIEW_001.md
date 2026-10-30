# Parent review: BtsT transport evidence and paired component revisions

Original source: Kristoficova et al., DOI10.1128/JB.00599-17, PMC5738728.
Parent independently read retained original-HTML scientific text through its
article_reading.txt projection (Results, Discussion, Methods), original Figures3,
4 and5, and the source-worker packet. The Methods portion truncated in the first
combined output was reread completely at lines142–159; packet was reread in two
complete sequential portions. The online PMC request now returns a browser
challenge; the retained successful original HTML/image bytes remain the evidence.
Failed PDF/supplement/XML requests are not experimental sources.

The full mandatory authority reset followed the paper review and preceded this
interpretation. BTST_PARENT_READ_PROVENANCE_001.json identifies the exact files,
hashes and portions read. Current goal and latest human scope were read last.

## Actual experiment and source definitions

Figure3 compares separate E.coli MG1655 ΔbtsT preparations containing pBAD24-btsT
(BtsT-6His) or empty pBAD24. Both lack chromosomal btsT; this is reintroduction
into the deletion background, not mutant and native BtsT coexisting, nor a
matched native-WT/deletion comparison. Whole-cell total protein is adjusted to
.35mg/ml, [14C]pyruvate is10uM,15°C,pH7.5. Retained radiolabel per mg total cell
protein is the plotted endpoint. Transport and metabolism/background uptake
remain mixed. Neither matched total protein nor common growth conditions
establishes equal transporter amount, membrane incorporation or isolated flux.

Caption3 specifies SD from three biological replicates. Their pairing is not
specified. Figure4A/B also says SD/three biological replicates/no background
correction; Figure4C instead says SEM for plotted uptake points. The fitted
Km±6.4 uncertainty kind is not expressly identified. Figure5 specifies SD from
three technical replicates; these are not three independent reconstitutions.
The global statistical-analysis prose does not resolve these panel-specific
differences or identify covariance/preparation ownership.

Reconstituted BtsT-6His is purified from LMG194 and incorporated into polar-lipid
proteoliposomes. It has a different protein denominator, preparation, temperature
and substrate concentration from intact cells. Changing driving gradients asks
about transport energization; imposed gradients are not measured potentials.
Empty-liposome controls are described but the original supplementary figures
were not acquired. The exact coupling stoichiometry remains unknown. The
Results/Methods Na-condition buffer difference remains conflicting.

## Numerical fields, components and combination

1. **Native whole-cell kinetic parameter:** exact HTML sectionsec2-4, direct
   paragraphindex1 reports16.5±6.4uM. Paired fields retain subject BtsT, analyte
   pyruvate, apparent_km role, actual source selectors and exact expression.
   Cells reported_value16.5,reported_spread6.4,relative_reported_spread
   .3878787878787879 describe the source parameter and printed precision only.
   No SD/SEM/n or likelihood is inferred from another panel.

2. **Comparability response:** h=[St/(Km+St)]/[Sr/(Km+Sr)] is applicable only
   under an actually supported common Michaelis-Menten kinetic curve, endpoint,
   preparation and analyte. A declared same-curve illustration at10/40uM and
   Km16.5 gives h=.5330188679245283. It is a proposed conditional response
   calculation using reported Km and illustrative concentrations; it is not a
   comparison of the paper's actual whole-cell and vesicle systems. Different
   curve keys produce null response, preserving native operands. Derivative
   propagation uses all three inputs' full covariance, including the one shared
   Km, exactly once. Unknown covariance stays unknown. Where scientifically
   applicable, an independently measured endpoint contrast is corrected e/h,
   and its joint uncertainty propagates the same correction; no additional
   reliability multiplier is applied to count it twice.

3. **Initial uptake contrast:** the source's coarse reported sixfold increase
   supplies R=6,R−1=5,(R−1)/R=5/6 as alternative forms of one comparison. The
   last number is a fraction above this empty-vector uptake background under an
   additive interpretation; it is not an isolated-BtsT fraction or confidence.
   Reference/test fitting intervals differ (approximately60s/30s). Native
   replicate slopes, common interval and joint uncertainty remain missing.

4. **Fixed-time accumulation:** the manually read40s graph points approximately
   .60 and.18nmol/mg give difference.42 and ratio3.33. Visual reading tolerances
   [.59,.61] and[.17,.19] give difference range[.40,.44], not a confidence
   interval. This cannot be divided by40s and called an initial uptake slope.
   Rounded prose.5/fourfold and graph values remain alternate representations
   with disagreement, not averaged independent observations.

5. **A106 distinction:** reintroduction raises deletion-background uptake. True
   WT-referenced restoration requires (rC−rD)/(rWT−rD) with matched endpoints,
   conditions and uncertainty; rWT is missing. Neither6 nor5/6 fills this cell.
   The native-loss effect is likewise unknown. No-growth-defect prose is a
   physiological qualification, not zero molecular transport.

Reconstitution addresses specific whole-cell background/metabolic alternatives;
it does not retroactively assign their magnitudes to zero. A quantified unwanted
contribution g and same-endpoint outside-variable response h answer separate
isolation/comparability questions. Source contrast S and proposed tanh(S/2)
require an actual sampling/threshold model; current rounded folds and graph
readings do not supply one. Those dependent numbers stay unknown. Additional
native transport trace/control readers remain required.

## Current implementation boundary

TRANSPORT_INTERFACES001/002 define a finite native HTML quantity reader and
separate same-curve response calculator before fresh disjoint coding. The
existing quantity selected operation/typed return is extended for original HTML;
no seventh evidence axis, per-assay episode or extraction loop is introduced.
The response calculator's selected storage/typed integration is separate
unfinished work until connected and verified. A105/A106 use of this evidence
does not implement A101, target correspondence, combined credit or W05.
