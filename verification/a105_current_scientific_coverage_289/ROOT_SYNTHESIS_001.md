# A105 source-evidence coverage and remaining numerical-sheet gap

This is an additive implementation audit under the immutable user-supplied
literature goal. It does not change that goal, adopt an annotation-credit
formula, or replace the ten evidence axes. Its count terms have distinct
meanings: a task-selection family is an instruction/operation mapping, a
worksheet format is a typed numerical return section, and an assay-specific
grader is a source reader plus an appropriate scientific interpretation and
calculation path exercised on an actual assay.

## Current case-grounded numerical contributions

| Experimental question | Exact source information needed | Current numerical cells and meaning | Current boundary |
| --- | --- | --- | --- |
| BbPK D- versus L-erythrulose, Yang et al. original S1Data workbook | Original numeric J cells, group and Parallel labels, native U/mg convention, actual subject; method/control linkage separately | D mean 0.5044733333, L mean 0.1889533333 U/mg; D−L 0.31552 U/mg; L/D 0.3745556422; D descriptive SD 0.03403624735 U/mg. These quantify reported-endpoint separation and reported-entry consistency. | XLSX reader/calculator and source-cell custody exist. Independent preparation n, blank, physical U conversion and particular method linkage remain unknown. One original arithmetic test passed; selected shared-episode test exposed a separate parent TASK boundary failure pending repair. |
| BbPK source-reported concentration curves, same Yang et al. article | Original S1Data concentration rows, 39 rate cells, reporting columns, exact selected fit/sampling interpretation | Per-point spread, 13-point fitted curves and conditional log-efficiency variance are populated. A reported-curve CV around 0.034885 is descriptive. | This is another analysis of source data from the same article, not a second independent paper/assay. Physical preparation grouping and published-fit covariance remain unknown; 59 focused tests passed in the case283 audit. |
| Alkaline phosphatase D101A/E322Y, Sunden et al. Table 1 | Reported 3.1 and SD0.1 M^-1s^-1, marked two independently expressed preparations, SD ownership; unmarked K328A row distinguished | Physical preparation count2 and relative reported SD0.0322581 are source-supported; scenario mean SE0.0707107 M^-1s^-1 and 95% interval [2.20154,3.99846] require declared estimator/normal assumptions. | Source and scenario cells stay separate. K328A row has no established preparation n or contrast SE; three focused current-code tests passed. |
| NfnAB ferredoxin-reduction versus NADH-formation readouts, Wang et al. | Original reported native rates ~23 and ~8 U/mg, different assay protocols, spectral coefficients 8.6 and1.2, physical endpoint meanings | Descriptive 8/23=0.347826 and difference −15 U/mg; coefficient ratio7.1667; a required unmeasured nuisance rate can be solved conditionally. | No measured nuisance rate, standardized same-condition disagreement or joint covariance. Existing selected comparison binding and two focused original-source tests passed. |
| MvhADG/HdrABC Fig.4 endpoint trace, Kaster et al. | Actual initial, late-baseline-at-addition and later trace coordinates, applicability of extrapolation, correction stage | Display-derived retained amplitude fraction131/142≈0.9225, conditional on the selected baseline interpretation. | An installed endpoint-signal reader/calculator and selected repository exist; same trace and reported corrected value are dependent representations. No absolute molar conversion from an unreported path length. This row is a previously established source example, not a new test in this audit. |

These components have different scientific jobs. Preparation SD/SE measures
random precision under a defined sampling unit. A calibration recovery or
matched blank tests a named measurement weakness. A product/reporter contrast
tests a particular endpoint relationship. An activity ratio tests a particular
functional distinction under its assayed conditions. A common subject name or
paper does not make these independent, nor does a native rate alone establish
function specificity or total experimental reliability.

## One logical A105 sheet; modular population

`literature_a105_worksheet.py` currently composes **nine** typed source-format
sections and validates limited source-quantity and assertion links. They are
sections of one logical A105 assessment, not nine axis sheets or nine completed
assay graders. `literature_task_selection.py` describes **36** existing
instruction/operation families across literature responsibilities; **27** are
outside this current A105 worksheet. That difference is a scope/integration
inventory, not a count of missing graders: it includes other evidence axes,
legacy paths, alternate source formats and A105 paths needing review. For
example, the installed original-XLSX reported-entry path is outside the nine
worksheet formats. Adding a format without scientific dependence rules would
allow the same workbook numbers to appear twice as if independent.

The existing within-assay compiled sheet has explicit arithmetic where the
source supplies the operands: attributed rate `q−g`, nuisance response `u/v`,
calibrated/amount-normalized rate `q/(kE)`, and fully corrected activity
`(q−g)×v/(kE u)`. Here `q` is the source endpoint rate after an already-applied
matched blank, `g` an additional matched contaminant contribution, `k` a
validated recovery, `E` the applicable molecular amount, and `u/v` a supported
nuisance-condition response. A stage already applied by the source becomes an
algebraic identity in that *same equation*, not an invented measured zero or
one. Unmeasured operands leave the corresponding correction unavailable.
The conditional source-presence profile requires an adequate known-normal
variance model; it is not a calibrated probability of function. The common
assertion contrast sheet explicitly labels general quality compilation and
same-estimand contradiction compilation unfinished.

## Remaining A105 template work

The present form can return numerical source components and constrained
assertion links, but it does not yet establish a source-grounded compilation
of reliability, method validity, effect isolation and endpoint relevance
across the actual assay designs. The next useful source-positive case must
provide enough matched controls/calibration/product or alternative-substrate
measurements to compute more than a raw activity magnitude. Each comparison
requires the actual subject, endpoint, denominator, preparation relationship,
correction stage and covariance/independence status. A missing input is not a
zero, a default one, or a generic applicability percentage.

Before extending the worksheet to the original-XLSX, amount, gel or other
paths, define the equality/dependence and claim-link relationships for their
actual numerical cells. That is the scientific interface work; an extra entry
in a format registry alone is not A105 adequacy. The common source-level
numerical sheet and later W05 target/credit combination remain separate.

The current parent TASK/STEERING failure and the lost configured model-backed
run are independent completion gaps. Controlled selected tests establish
specific bindings, not complete model-backed A105 scientific performance.

### Later implementation update

The parent TASK/STEERING defect above was subsequently corrected in
`literature_task_selection.py` and verified in the bounded handoff
`verification/a105_parent_task_boundary_287/HANDOFF_001.md`. Root independently
reran the original-workbook parent case and root/nested reported-curve cases:
**10 passed in 159.88 s**. The lost configured model-backed run and the
scientific compilation gap remain open. The earlier failure description is
retained as the observed reason for the correction.

### Later original-source coverage audits

Current case167 WST-8 calibration (audit290) has an installed original-source
reader/calculator and selected typed return for a buffer NADPH standard and a
serum G6PD enzyme spike. Ratios 8.72/8.6 = 1.01395349 and
1.235/1.024 = 1.2060546875 have different scientific meanings; neither is
automatically an applicable correction of the other assay. The reported FBS
recovery 1.2057 is retained beside the displayed-value difference. Two focused
original-source tests passed. Table 3 WST-8/UV protocol comparison is a
separate pending selected-workload audit and must not be counted as a finished
independent assay grade.

Current Kaster endpoint audit292 verified source image coordinates and the
selected section: conditional 131/142 retained amplitude after one displayed
late-baseline correction, with manual reading bounds and no physical variance.
The separate <2 nmol/min alternative-route statement is not a matched `g` for
that trace. Two focused original/selected tests passed.

Current HFP audit293 verified original-source NMR partition fractions 0.603
and 0.397, their dependent ratio, selected typed delivery and the synthetic
compiler's missing-contaminant behavior. RpiA identification does not measure
its same-assay activity. The product-partition tests passed two focused cases;
one focused missing-`g` compiler test passed. HFP-specific q−g and the
isolated activity share remain unavailable from that paper.

These are source-level partials within A105. They add contrasting validity,
endpoint correction and attribution cases, but do not finish general numerical
reliability/validity/relevance compilation across assays or justify an overall
function probability. Count each actual assay and underlying physical
measurement once; alternate readers of the same paper do not create new
experimental verification.

### Later WST-8/UV Table 3 method contrast

The selected original-source comparison for case167 now reads the paper's
12.51 ± 0.36 and 14.88 ± 0.39 nmole/min/μg method reports. The exact unit
identity is 1 nmole/min/μg = 1 μmol/min/mg. It populates a descriptive
protocol ratio 417/496 = 0.8407258065 and difference −2.37 μmol/min/mg.
These reuse the same two source values; they are not independent evidence.
The WST-8 and UV enzyme concentrations are respectively 2/3 and 1/2 μg/mL,
a 4/3 ratio, so a common-condition ratio and combined rate remain unavailable.
The SDs do not establish joint covariance or independent preparation count.
New V2 implementation receipts retain the older V1 cold-read path. Root
independently ran the three focused original-source/cold-read tests: 3 passed.
The agent's broader run exposed five stale parent TASK expectations after the
separate TASK/STEERING ownership correction; a bounded correction is pending.

### Later Fluc electrical and FrsA negative-evidence audits

The retained original Fluc article now has a selected electrical channel
verification (`verification/a105_fluc_original_channel_294/HANDOFF_001.md`).
The paper's 1.8 pA dominant insertion step at −200 mV and a 53 ± 1 mV
salt-gradient reversal yield a **conditional** 1800/253 = 7.1146245059 pS
chord conductance. A separate 119 ± 3 mV bi-ionic reversal correctly blocks
that chord calculation. The article's 7 pS description depends on the same
source current; the charge-equivalent conversion is not F− flux. Primitive
variance and independent protein preparation count remain unavailable. Root
independently ran the three original-source, typed-return and cold-replay tests:
**3 passed in 15.66 s**. `literature_channel_cells` remains absent from the
logical worksheet's FAMILIES roster, so this is not yet a composed A105 grade.

The FrsA negative-evidence audit
(`verification/a105_frsa_negative_evidence_current_audit_297/ROOT_AUDIT_001.md`)
paired three readout designs with required extraction operands. MIMS uses
50 nM enzyme for 12 min (36 µM·s exposure); NMR uses 5 µM for 90 min
(27,000 µM·s). Their exposure ratio is 750, but different conditions and
uncalibrated detection prevent a sensitivity or evidence-strength ratio.
The ADH/NADH reporter pool to pyruvate ratio is 0.2/5 = 0.04, which is a
capacity relationship, not a recovered activity fraction. Nondetection is
not zero; no calibrated upper enzymatic rate or contradiction score can be
populated from the retained observations. This audit adds no code or completed
grader and identifies the exact missing limit/recovery fields.

### Comparison prompt test repair

The stale assertions above were corrected in the existing comparison binding
test only (`verification/a105_comparison_parent_task_tests_295/HANDOFF_001.md`).
The comparison-owning episode retains its full TASK, while an annotation
parent receives selected child facts in STEERING without importing the child's
method instructions. The agent ran the complete modified file: **27 passed**.
Root independent full-file verification is running at this checkpoint; no
production behavior or scoring policy changed.

Root subsequently completed that independent full-file run:
`.venv/bin/python -B -m pytest -q tests/test_literature_measurement_comparison_binding_268.py`
returned **27 passed in 158.68 s**. This supersedes only the pending-test
status in the preceding paragraph.

### Repeated packet check, no new assay count

Root reread the retained HFP case145 and NfnAB case255 proposals with the
required post-packet authority and current-contract resets. Their selected
observations overlap the already audited HFP product/contamination case and
the already installed NfnAB comparison path, respectively. The HFP 60.3/39.7
composition cannot supply a same-endpoint contaminant contribution `g`; the
NfnAB ~23/~8 U/mg comparison has different protocols and an unresolved
optical nuisance rate. These packet reviews create **no additional grader,
assay, or independent experiment**. The comparison file run above is the
bounded current implementation verification for NfnAB, not a newly collected
paper measurement.

### Composed Fluc electrical and ion sections

The A105 worksheet now admits the two already installed Fluc source formats,
electrical channel and ion discrimination, as separately scoped numerical
sections of **one A105 sheet**. There are now eleven supported source formats,
not eleven evidence-axis sheets or eleven completed assay graders. The larger
system still has exactly ten evidence axes. The original nine-format subset
remains available. The selected original-XML case returns 1800/253 =
7.1146245059 pS conditional chord conductance and an unavailable chord
variance, plus F− >30,000 and Cl− <30 ions/s source threshold rows and their
nominal threshold quotient 1000. That quotient is not a physical selectivity
lower bound if the alternative rate could be zero. Electrical charge
equivalents are not ion flux. The electrical row identifies Fluc-Ec2, while
the ion-efflux summary lacks a construct-specific witness; a common Ec2
assertion and cross-assay equality are therefore unsupported. An unresolved
cross-section link is admitted, and a false same-parameter link is rejected.
The bounded implementation and test evidence are in
`verification/a105_channel_ion_worksheet_298/HANDOFF_001.md`. The agent's
joined suite passed 93 tests; after its final direct TASK/STEERING assertion,
the three-mode episode/cold-reconstruction test passed three. Root
independently ran the final focused worksheet files, **62 passed in 32.68 s**,
and the direct episode integration case, **1 passed in 43.51 s**. These are
controlled tests, not a live model-backed literature assessment or a general
assay-validity compilation.

### Arad3529 original-paper specificity and product case

The original Fan et al. JACS paper and the bounded conversion are retained in
`verification/a105_arad3529_primary_case_299/`. Reported biopterin versus
7,8-dihydrobiopterin catalytic efficiencies are 1.0×10^6 and 9.3×10^2
M^-1s^-1. Their reported-protocol ratio is 100000/93 = 1075.2688172; the
canonical values 60 and 0.0558 µM^-1min^-1, difference 59.9442 and log ratio
6.980325971817 all derive from the same two fitted values. The reduced
compound is explicitly 7,8-dihydro-L-biopterin, while the oxidized Table 2
label does not establish matched stereochemistry. The main-paper Methods do
not give the reduced compound's optical coefficient, and the source does not
establish joint fit covariance, matched blanks or independent preparation
count. Thus the ratio is a descriptive functional distinction, not an isolated
redox effect or calibrated precision score. A separate pterin-6-carboxylate
product check records substrate m/z 206.04 and reaction-product m/z 207.02;
these are different analytes, so their 0.98 m/z separation cannot populate a
same-ion ppm mass-error or yield cell. The report pairs source fields with
numerical cells and missing operands, but added no reader or episode run.
After reading that retained packet, root reread the complete immutable goal,
the complete per-paper authority set, current logical worksheet and kinetic
extraction/calculation contracts before converting the case in conversation.
A fresh bounded implementation workload is testing whether the existing
kinetic reader can populate the original Table 2 contrast through selected
LiteratureEpisodes execution; its result is pending at this checkpoint.

### Pa0142 original-paper alternative-substrate case

The original Hall et al. JACS article and ACS supporting information were
reviewed in `verification/a105_pa0142_primary_case_301/REPORT_001.md`.
Purified Pa0142 from *P. aeruginosa* PAO1 has reported 8-oxoguanine, guanine
and isocytosine catalytic efficiencies of (2.0±0.1)×10^4,
(1.3±0.4)×10^3 and (2.2±0.1)×10^3 M^-1s^-1 in separate pH 8
ammonia-coupled assays. The worksheet's descriptive same-enzyme substrate
contrasts are 200/13 = 15.38461538 and 100/11 = 9.09090909. Their common
8-oxoguanine numerator is one physical estimate, so the two ratios are
dependent; the corresponding canonical values are 1.2, 0.078 and 0.132
µM^-1min^-1. The source does not define its ± statistic or provide the
covariance/known-normal model needed for the kinetic profile/index cells.
It reports MS/UV product confirmation without spectra, calibrated recovery,
stoichiometry or yields, and supplies no matched no-enzyme blank, active-site
titration or independent-preparation variance. Thus it supplies a numerical
substrate-distinction contribution but no quantitative method-validity or
effect-isolation correction. Its separate Pa0134/b2883 `<5×10^-3 s^-1`
statement is a censored, different-enzyme turnover parameter, not a Pa0142
efficiency denominator. This research case added no reader or selected episode
run. After reading its retained report, root reread the complete immutable
goal, complete per-paper authority set and current A105/kinetic contracts
before converting the case in conversation. A source-specific selected reader
exercise remains to be implemented; its numbered-substrate cross-reference
and printed scientific notation are concrete reader gaps.

### Arad3529 selected kinetic path, verified

The bounded implementation in
`verification/a105_arad_kinetic_selected_300/REPORT_001.md` uses the original
PDF, a geometry extraction that proves the two printed exponents, and a
source-linked derived transcription. The current literal V3 reader consumes
the explicitly derived `1.0e6` and `9.3e2` tokens. It populates the two
canonical efficiencies, the descriptive ratio 100000/93, and its log through
one selected `LiteratureEpisodes` operation, typed return and read-only cold
SQLite reconstruction. Root independently reran the exact focused test:
**1 passed in 17.05 s**. Direct parsing of the printed mantissa-times-ten
notation is still unimplemented; no V3 reader release pin was changed.
The paper lacks an applicable joint covariance and observation model, so the
variance and source profile cells remain unavailable. This test establishes a
reader/episode path, not a complete assay reliability score or A105 completion.

### Existing configured A105 run: recovered public partial state

Root inspected the existing configured worksheet case278 without reading provider
content. The original process identity recorded in its handoff is no longer
live. A read-only status snapshot at
`verification/a105_configured_worksheet_278/PUBLIC_STATUS_20261029T011730136380Z.json`
shows the saved run still labeled `running`, with 615 selected action rows,
548 ordinary observations, 618 model-call rows (one pending), and nine admitted
child returns. Those counts have different meanings; the saved state is neither
closed nor proof of a final worksheet. No final original caller form was found
or manufactured. A fresh bounded recovery audit owns an additive plan; no
model call has been replayed by root.

The public typed returns from the original eLife alkaline-phosphatase paper
include one populated D101A/E322Y pNPP efficiency report: 3.1 ± 0.1
M^-1s^-1, converted to 0.000186 ± 0.000006 µM^-1min^-1, relative reported
SD 1/31 and physical preparation count 2. Statistical estimator count and
mean SE remain unavailable, so no assumed n=2 confidence interval is promoted.
An earlier child return had an unsupported-unit partial before the later
successful unit resolution. Separate child interpretations report only
preparation-level pNPP optical signal, unresolved mutant attribution, and
differing WT/MgCl2 conditions. These are actual model-selected typed partial
returns, not root-validated final source/scoring judgments. After reviewing the
paper-specific public returns, root completed the per-paper goal/authority and
current-sheet/kinetic precision-contract reset before interpretation. The
source assay still lacks a source-supported method-validity/effect-isolation
quantity and a final parent assessment.

### Pa0142 selected two-contrast path, verified

The original Hall et al. PDF/SI, page image, pinned glyph geometry and explicitly
marked transcription support the two selected kinetic comparisons in
`verification/a105_pa0142_kinetic_selected_303/REPORT_001.md`. Two
`literature.kinetic.populate` operations returned eight requested rows in one
typed A105 worksheet. The shared 8-oxoG physical estimate is 1.2
µM^-1min^-1; separate guanine and isocytosine estimates are 0.078 and 0.132
µM^-1min^-1. Descriptive ratios are 200/13 and 100/11. The numerator's
physical-observation identity is reused across comparisons, so those ratios
are dependent. The original source's ± meaning, preparation count, joint
covariance and complete nonintended-condition matching remain unknown; the
variance/profile/index cells remain unavailable. The selected test also rejects
a censored kcat bound from different enzymes as a Pa0142 efficiency denominator.
Cold read-only SQLite reconstruction reproduces the saved rows without source
reacquisition or calculation. The agent's focused run passed two tests; root
independently reran the same file: **2 passed in 23.89 s**. Both runs used a
scripted decision provider and fixture controller, so they establish a bounded
source-backed selected path, not model-backed scientific assessment or a complete
A105 assay grade. The PDF scientific-notation typography is authenticated by
geometry before deriving literal reader tokens; direct typographic parsing is
not implemented. Root completed the required post-packet reset before this
interpretation.

### Configured run replay started after read-only audit

`verification/a105_configured_run_recovery_305/REPORT_001.md` records a
read-only audit of the original configured run. It verified 1,037 frozen source
files, ten entrypoint/contract files, the prepared caller and saved root request,
the dead prior process identity, nine already admitted child returns, and the
unanswered `child_10` decision 18 physical exchange. Root independently ran
the audit with zero database changes, then started the original pinned
`caller_002.py execute` on the original saved run. The new process was live at
this checkpoint. A resumed model request, child return, final worksheet and
scientific completion have **not** yet been observed or claimed. The earlier
interrupted call may need a second physical model inference because no original
response was journaled; the logical decision and prior observations must not
be duplicated. Post-replay public-journal verification remains pending.

### Source-bound dependency across two kinetic contrasts

The opt-in V2 context of the **same** A105 worksheet now admits
`same_physical_measurement` between two delivered kinetic parameter cells.
It requires the same non-null physical-observation and numeric-measurement
references, the same source, value, unit and parameter metadata, and source
witnesses that contain the numeric token. V1 remains the default, including
its original relation vocabulary. The Pa0142 two-contrast selected return and
cold read-only reconstruction exercise the link; distinct physical identities
with equal numbers and conflicting numbers under one identity are rejected.
This does not create another grader or calculate an aggregate specificity
score. The implementation receipt is
`verification/a105_native_dependency_link_307/REPORT_001.md`; root
independently reran the focused test, **2 passed in 21.01 s**. The two ratios
still need their joint covariance for a dependence-aware combined score.
The V2 validation test did not establish parent-facing rendering: current
`literature_experimental_prompt._worksheet_context` and
`literature_a105_worksheet_render.render_a105_worksheet` recognize only V1.
The V2 link is therefore not yet known to appear in the receiving episode's
STEERING. A bounded correction and actual prompt-path test are pending.

### P205 matched-control parent-depletion case: research partial

The original Marti et al. article, supporting PDF and authors' Sheet1 row 5
workbook are audited in
`verification/a105_matched_control_primary_306/REPORT_001.md`. For
capecitabine at 24 h, the source reports active P205 removal fraction
0.6880062978 (SD 0.0108692606), inactive S146A 0.0987152898
(SD 0.0274700308), and abiotic −0.0387430561 (SD 0.0769096425).
Workbook K5 gives active minus S146A = 0.5892910080, and L5 gives active
minus abiotic = 0.7267493538. The latter two share the active observation
and are not independent contributions. These are controlled **parent
depletion** components, not a source-proven P205 catalytic product yield.
Matched mutant protein amount, exact fraction normalization, replicate units,
joint covariance and P205-specific product identity remain unverified. The
paper's P131 product experiment belongs to another enzyme. This research
packet adds no production reader or grader; a fresh bounded implementation
workload is building the source-bound XLSX path and selected typed exercise.
Root completed the post-packet goal/authority and current-sheet/endpoint
contract reread before this conversion. The existing endpoint-signal reader
handles graph coordinates, not this workbook's dimensionless 24 h fractions.

### DeoA ion-trace product-control search: bounded reader gap

The new original Gruber et al. 2026 article and supplements are audited in
`verification/a105_product_control_search_309/REPORT_001.md`. Purified E. coli
DeoA has active and heat-inactivated uridine assay arms; main Figure 5c shows
uridine ion decrease with uracil and ribose-1-phosphate ion increases. The
reported 50 µg/mL in 150 µL implies 7.5 µg nominal enzyme preparation per
reaction. Main Methods say 10 mM each substrate, while a related supplement
caption says 1 mM and a different mixture: a tenfold documentation conflict,
not a resolved main-assay amount. The displayed values are ion counts on
different analyte scales without analyte-specific molar calibration or unique
product identification. Thus a same-ion active-minus-inactive trace contrast
is a candidate numerical component for a targeted multi-channel graph reader,
but molar substrate loss/product gain and a stoichiometric product-coupling
ratio are unavailable. Source replication lower bounds are not a paired
main-figure n or covariance. This packet added no production grader or
selected episode. Root completed the post-packet full goal/authority and
current worksheet/endpoint contract reset before this conversion. The
existing single-trace endpoint reader must not be relabeled as a multi-ion
product-yield reader.

### Configured run first replay reached new work, then service overload

The original pinned caller's first live replay reconstructed the saved
history and continued `child_10` from logical decision 18. It recorded
source reads and other new selected work, reaching 628 action rows, 559
ordinary observations and 631 model-call rows, with the original nine
admitted returns unchanged and root child action 10 still pending. The
next model call (child logical call 31) failed with service `serverOverloaded`
(`Selected model is at capacity`); the caller saved `operational_failure`.
This is an operational failure, not scientific closure. Root's read-only
checkpoint found unique `(episode_id,decision_index)` action keys, unique
observation and model-call keys, and one unanswered call. After confirming
the old process ended and inspecting the original caller's retry path, root
launched the **same pinned caller and saved run ID** again. That second replay
is live; no final typed return or new scientific conclusion is claimed.

### V2 dependence display and P205 selected worksheet section

The receiving parent now recognizes the opt-in A105 V2 worksheet context and
renders its `same_physical_measurement` link as one shared original physical
measurement and dependent contrasts. The selected Pa0142 typed-return and
cold-reconstruction test passed. This corrects the earlier V2 parent-display
gap; it does not calculate a combined specificity score or establish covariance.

The P205 authors' original workbook now populates an eight-cell section of the
**same A105 worksheet** through a selected `literature.parent_depletion.populate`
action, typed child-to-parent return, parent STEERING and read-only saved
reconstruction. The three arm removal fractions are 0.68800629778328803
(active), 0.0987152898299202 (S146A) and −0.038743056052261297 (abiotic).
The respective source-reported SDs are 0.0108692606063584,
0.0274700307939434 and 0.076909642509430096. Exact decimal arithmetic
populates active−S146A = 0.58929100795336783 and active−abiotic =
0.726749353835549327, checking the workbook's two difference cells within
1e−12 fraction. Both differences reuse the same B5 active measurement; they
cannot count as independent verification. Raw normalization denominator,
joint uncertainty, matched mutant protein amount and P205-specific product
identity remain unavailable. Thus the numerical cells describe controlled
parent disappearance, not catalytic product yield or a complete assay grade.
There are now twelve supported source formats of one A105 worksheet, not
twelve axes or twelve completed assay graders. The original report and bounded
implementation details are in
`verification/a105_p205_parent_depletion_308/REPORT_001.md`.

Root independently ran the settled combined P205, V2 dependence-display,
Pa0142 link and legacy worksheet/integration suite: **85 passed in 197.43 s**.
This verifies the exercised source-bound paths; A105's common numerical
reliability, validity, effect-isolation and claim-relevance compilation is
still incomplete. A configured model-backed final assessment remains pending.

### Later primary-source product-accounting research

The Zaman and Friesen NMR packet
`verification/a105_calibrated_product_primary_311/REPORT_001.md` yields a
calculated 0.1892 mM phosphate product from the selected starting pNPP and Pi
integrals. It does not supply a numerical final pNPP concentration for the
same assay or a validated relative NMR response and relaxation correction.
Thus it cannot fill a paired molar substrate-loss/product-gain balance.
Triplicate reporting alone does not supply joint covariance. This packet
added no selected reader or complete score.

The Klimacek, Zhong and Nidetzky original CcCdP article and authors' Figure 2
workbook are retained in
`verification/a105_cccdp_mass_balance_312/REPORT_001.md`. For the paper's
90-minute G2-acceptor assay, the original source cells give G2 loss
21.953216 mM, summed observed soluble product molecules 17.884131 mM,
weighted added-glucosyl equivalents
`G3 + 2*G4 + 3*G5 + 4*G6 = 37.846643 mM`, and separately measured
phosphate 43.291423 mM. The two descriptive accounting ratios are
17.884131/21.953216 = 0.814647430244 and
37.846643/43.291423 = 0.874229590466. The latter uses a one-phosphate
per donor-use interpretation. The difference 5.444780 mM is an inferred
balance remainder, not an observed insoluble product or isolated enzyme
activity. Product concentrations and phosphate have reported marginal SDs,
but their cross-analyte pairing/covariance is not established, so ratio
uncertainty is unavailable. The time-zero G2 cell matches the nominal 25 mM
charge; a separate measured starting estimate is not established, so G2 loss
and its acceptor-accounting ratio are conditional on that starting value.
The initial 100 mM donor is a nominal condition,
not a measured denominator with known uncertainty. Multiplying the
phosphate/nominal-donor ratio by the soluble-product/phosphate ratio cancels
the same phosphate measurement and yields only
`37.846643/100 = 0.37846643`; it is not an independent confirmation.
No no-enzyme contrast or
source-grounded validity multiplier is obtained from these cells.

This is one additional A105 experimental design with a source-positive
weighted-sum calculation, not a new evidence axis or completed common A105
grade. A fresh implementation workload is connecting its selected original
workbook path to the same logical worksheet; production scope and tests remain
pending at this checkpoint. Root performed the required complete post-paper
authority resets before interpreting each original packet.
