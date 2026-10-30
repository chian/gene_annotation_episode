# Original active-site titration case populated

The full goal remains active and unchanged. This is one assay-specific normalization contribution within A105, not a completed A105 grader or scoring sheet. No other axis, W05, annotation-credit formula, controller or production code changed in this turn.

## Experimental definitions and source meaning

Source: Development of an active-site titrant for SARS-CoV-2 main protease as an indispensable tool for evaluating enzyme kinetics, DOI 10.1016/j.apsb.2024.03.001, PMC11121168. Root reread the complete main article body, title and abstract and the retained original supplement's S5-S7 caption/text pages. Root's own full post-paper reset, current extraction/sheet contract and latest-human-instruction reread are recorded in ROOT_POST_PAPER_RESET_001.json. No researcher/coder reset was borrowed.

The actual studied molecule is SARS-CoV-2 Mpro. The His-tagged and tag-cleaved/native preparations are separately assayed; they do not coexist in these titration arms. Viral genotype is not selected. Tag removal, preparation/stock differences and assay dilution must remain distinct from a causal effect of a tag. The within-titration changed variable is titrant concentration. The source normalizes initial product-formation rates to a no-titrant control and obtains the active-site estimate from the fitted x-intercept. That reference is not a measured no-enzyme blank.

The source infers one titrant per active site from irreversible inhibition and the covalent active-site adduct. That inference does not independently standardize the molar active titrant concentration. The reported molecular weight is an assumption of 34.21 kDa per monomer. One site per monomer is separately interpreted from the protomer's catalytic-site description. A dimer does not make this assumed monomer mass a dimer mass.

## Source operands and populated numerical sheet

The following are outputs of the actual selected reader/calculator, independently checked against exact Fraction arithmetic. Native source quotes/units, not precomputed numerical data, were supplied as selections.

| Component | Main Figure2: His-tagged | Supplement FigureS5: native | Meaning |
| --- | ---: | ---: | --- |
| Protein mass concentration | 2.0 ng/µL | 7.5 ng/µL | Reported amount in this titration |
| Assumed mass per monomer | 34.21 kDa | 34.21 kDa | Source assumption, not a newly computed sequence mass |
| Calculated total monomer concentration | 58.46243788 nM | 219.23414206 nM | 1000*mass[ng/µL]/MW[kDa] |
| Reported estimated active-site concentration | 32.6 nM | 43.0 nM | Source fitted titer, under its nominal titrant basis |
| Sites per total monomer | 0.557623 | 0.1961373333 | Active-site estimate/total monomer estimate |
| Conditional active monomer fraction | 0.557623 | 0.1961373333 | Density given one functional site per monomer |
| Conditional total/active denominator factor | 1.7933263154 | 5.0984684201 | Total monomer estimate/active-site estimate |
| Reported rounded active fraction | 0.56 | 0.20 | Original percentages converted to fractions |
| Derived minus reported fraction | -0.002377 | -0.0038626667 | Numerical discrepancy retained; no silent reconciliation |

The two density/biological-fraction rows are conditional interpretations of the same inputs, not independent evidence. The total/active factor could multiply the same rate when its denominator was total monomer. It must not be applied to an already active-site-normalized rate. The paper's downstream kcat convention already uses active sites; both saved sheets and returned rows preserve `not_applied_already_active_normalized`. No rate was mutated or corrected again.

Native FigureS5's 7.5 ng/µL and 43 nM titration are not FigureS6's later 5.65 ng/µL kinetic dilution. The original caption is selected explicitly; no 43 nM concentration was carried into the later diluted assay.

## Uncertainty, repetition and complementary evidence

The reported spreads are 3.8 and 0.9 nmol/L, explicitly SDs associated with linear regression. The source captions describe five and three experiments on aliquots of the same respective preparation. They do not establish five and three independent protein preparations. Source repetition meanings and actual spread quotes remain in extraction and requested returns. This reader does not compute an independent-preparation count; its numerical count remains null, an implementation limitation rather than a claim that the captions fail to describe shared preparation.

Proposed relative reported fit-spread arithmetic is 3.8/32.6=0.1165644 and0.9/43=0.0209302. It has been checked separately but is not implemented as a component of this reader. It is not preparation CV, SEM, known sampling variance or full fraction uncertainty. Full covariance propagation remains unimplemented, and the selected source operands do not supply the full joint error information. No division by sqrt(5) or sqrt(3), calibrated confidence or reliability probability is invented.

The covalent structure and inhibition behavior support the titrant interpretation, addressing a different weakness from fluorescence-response calibration or quantitative titrant-stock calibration. They are complementary evidence, not additional independent active-titer replications. The active fraction is not the paper's separate optical inner-filter correction factor.

## Selected execution, typed return and saved reconstruction

`populate_primary_003.py` used the previously independently tested frozen implementation in151/pin_001. It retained exact original XML and supplement PDF bytes and their explicit text derivatives, initialized an empty original target scope, and created no fake target sequence. Root supplied reviewed source selections. The provider and controller choices are controlled fixtures; no autonomous actual-model extraction is claimed for this demonstration.

One ordinary literature child selected two `literature.active_site.populate` operations, one for each preparation. Its original parent-defined typed form returned all nine requested components per sheet:18 rows. One child delivery plus the two own population actions and the parent's source-subject reasoning action produced exactly four runtime observations. No scientific observation/assessment records or synthetic scientific gains were manufactured. Source/experiment bookkeeping and mathematical transforms do not become extra independent evidence.

The Store was closed and reopened. The actual compose_episode_bindings factory restored the saved descriptor under PRAGMA query_only. Reads of both original primary assets and their text derivatives, and any call to the scientific reader, were forbidden. Saved typed returns and possession-safe projections reconstructed identically with zero database changes. This does not claim a fully read-only Workflow initializer.

Versions001 and002 failed before episode execution due to source selector mistakes: matching the supplement's table of contents and not preserving a PDF line break. Their scripts, logs and state are retained. Version003 selected the actual complete caption and actual whitespace-preserving source span. No production parser was weakened and no measurement changed.

## Handoff and remaining goal work

The later annotation-credit owner can use these source-subject-specific denominator and uncertainty components only with the correct preparation, endpoint and normalization relationship. These components are not target correspondence, function probability or final annotation credit. No A101/A105 multiplication is performed here.

Primary conversion is now delivered for this finite path. A105's broader assay validity, comparability, isolation, functional discrimination, uncertainty and cross-experiment combination still require adequacy assessment. Do not use this one successful case or reader/test counts as that assessment.

The same live configured006 run is still active. Its original first child return was admitted, and its parent-selected second child was verified live as PID3322001/start_ticks94068803. A read-only copy of the public typed return is retained in CONFIGURED006_TYPED_RETURNS_UNREVIEWED_001.json. Root has not read or scientifically assessed that copied packet. Review it and the corresponding original source under an own full post-paper reset before interpreting its scoring components. No provider requests/responses or private conversations were copied or examined. Preserve the same session97191; do not restart it because the first child exited after returning or an observation timed out.
