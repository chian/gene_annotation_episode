# BtsT original-source packet: transport and deletion-background complementation

Research proposal only. One original paper examined: Kristoficova et al., DOI
10.1128/JB.00599-17, PMCID PMC5738728. No production reader, formula adoption,
episode execution, A101/A102/A103/A104/computational A107 or annotation-credit
aggregation is performed. The adopted GOAL_VERBATIM.txt supersedes the current
historical sheet's target-correspondence sections. The full post-paper reset is
recorded in AUTHORITY_RESET_001.json; adopted goal was read last.

## Source custody and limits

Original article HTML and original Figures 1–5 were acquired from NCBI/PMC and
retained under source/. Article DOI landing source:
https://pmc.ncbi.nlm.nih.gov/articles/PMC5738728/ . Exact request URLs, HTTP
statuses, content types, byte lengths, timestamps and SHA256 hashes are in
source/acquisition.json, source/asset_acquisition.json and
source/alternative_acquisition.json. article_reading.txt is a derived plain-text
projection; pmc_article.html is the retained original. SOURCE_LOCATORS_001.json
indexes relevant projected paragraph locations; original section/figure names
below are the publication anchors. No other paper was opened.

The main-PDF response was an HTML download challenge despite HTTP200. It was
renamed article_pdf_request.challenge.html; acquisition.json's original
filename article.pdf refers to these same bytes, not an acquired PDF. PMC
supplement-PDF/XLSX responses were also HTML challenges. Publisher PDF and
supplement requests returned HTTP403; Europe PMC supplementaryFiles explicitly
reported that the article was not open access, and fullTextXML failed HTTP500.
pmc_bioc.xml was an unsuccessful HTML response, not an experimental XML source.
These payloads are retained but none supplied measurements. Supplementary
Figures S3–S10 were not independently inspected. Their descriptions below come
only from the main article, and the raw uptake data/replicate traces are missing.

## Experimental definitions first

| Experiment | Actual subjects and intended change | Held/reported conditions and denominator | What remains mixed or unmeasured |
|---|---|---|---|
| Fig3 whole-cell complementation | E. coli MG1655 ΔbtsT with pBAD24-btsT versus the same deletion strain with empty pBAD24. The former codes for BtsT-6His. Separate cell preparations; endogenous BtsT is deleted in both. This is reintroduction into a deletion background, not coexistence with native BtsT or a WT-versus-knockout comparison. | LB-grown mid-log cells, no arabinose; leaky expression used for complementation. Washed twice; 100mM Tris/MES pH7.5, 5mM MgCl2; total protein adjusted to 0.35mg/ml. [14C]pyruvate 10µM, uptake at15°C, rapid filtration/scintillation. Figure endpoint nmol retained pyruvate label per mg total cell protein versus seconds. Caption: SD, three biological replicates. | Empty vector is a biological uptake background, not an instrument blank or measured pure diffusion. Other transport/metabolism remain. BtsT abundance, membrane insertion efficiency and relative amounts against physiological WT are not quantified. Native WT uptake is not the third arm of Fig3. |
| Fig4A energy inhibition | BtsT-producing whole cells, untreated/vehicle control versus inhibitor; not a selective BtsT genetic perturbation. | 10µM tracer substrate; 30min preincubation at25°C. DNP2mM, CCCP20µM, nigericin6µM, nonactin10µM, DMSO control. Valinomycin preincubation uses potassium-phosphate pH7.5 rather than Tris/MES; whole-cell valinomycin concentration is not specified in the displayed Methods. Caption: three biological replicates, SD, no background correction. | Global protonophores perturb other cellular processes; valinomycin comparison also changes buffer. A reduced cell uptake endpoint does not alone establish direct proton coupling by BtsT. |
| Fig4B competition | Same BtsT-producing cell system; co-added unlabeled competitor changes. Cold pyruvate and tracer coexist. | Competitor1mM with tracer pyruvate10µM; initial uptake rate nmol mg total protein^-1 min^-1. Caption: three biological replicates, SD, no background correction. | Competitor inhibition is not direct transport measurement of that competitor. Cold pyruvate changes tracer fraction; metabolism and background uptake remain. |
| Fig4C kinetic curve | BtsT-producing intact cells with varied pyruvate concentration. | Diffusion-corrected initial rate fitted to Vmax*S/(Km+S). Methods state constant [14C]pyruvate amount9nmol. Caption error bars are SEM; uncertainty type of the text's fitted Km±6.4 is not expressly defined. | Diffusion correction is not subtraction of every other transporter. Raw points/covariance and fit-parameter covariance are absent here. |
| Fig5A/B reconstitution | BtsT-6His expressed in E. coli LMG194, affinity purified and reconstituted into E. coli polar-lipid liposomes; imposed driving gradients change. No WT/mutant mixture. | Lipid:protein100:1 reported preparation ratio; 400nm extrusion; suspension protein4mg/ml before200-fold dilution. Inside potassium phosphate pH7.6; tracer40µM, valinomycin80µM, assay25°C. Figures distinguish amount nmol/mg protein and initial rate nmol mg^-1 min^-1. Caption explicitly SD from three technical replicates. | Incorporated functional BtsT amount/orientation, vesicle volume and actual measured membrane potentials are not numerically supplied. Protein denominator differs from whole-cell total-protein denominator. Technical repeats are not three independent reconstitutions. |
| Fig5C counterflow | The BtsT proteoliposomes preloaded overnight with10mM pyruvate versus10mM lactate; labeled external pyruvate measured. | 200-fold dilution at25°C; nominal labeled external pyruvate4.7µM. Methods give final external pyruvate54.7µM. | Pyruvate preload contributes50µM cold pyruvate on dilution; lactate preload contributes50µM lactate. Equal total external pyruvate across both preload arms is not established. This is exchange/counterflow, not the Fig5A/B gradient assay. |

Locations: Results “BtsT activity in intact cells,” “Characterization of pyruvate
transport by BtsT in intact cells,” and “Effects of … on BtsT-mediated pyruvate
transport”; Fig3–5 captions; Methods “Bacterial strains and plasmids,” “Transport
measurements with intact cells,” “Transport measurements with proteoliposomes,”
and “Statistical analysis.”

## Native observations and their numerical contribution

These cells are source evidence, not a confidence probability or final score.
Alternative transformations of one operand must not be multiplied as independent
proofs. The comparisons teach separate signal, comparability and isolation
questions; no categorical reliability number is assigned.

| Source observation | Paired extraction fields and populated numerical cells | Scoring meaning and limit |
|---|---|---|
| Results/Fig3: complemented strain's linear uptake rate described as6-fold control, linear30s; control approximately linear60s. | reported_rate_ratio R=6, reported linear-window test30s/reference60s. Derived excess relative to control R−1=5; excess fraction of complemented signal (R−1)/R=5/6≈0.8333. These inherit the coarse reported fold's precision; no uncertainty is supplied for the fold. | Relative elevation of whole-cell tracer uptake with BtsT reintroduction. The 0.8333 is the fraction above this control under an additive-background interpretation, not the fraction proved to be transported only by BtsT, not percentage physiological restoration, and not an isolation/reliability multiplier. Unequal regression windows require preservation, not silent matching. |
| Results/Fig3: steady level described as0.5nmol/mg, approximately40s, fourfold control. | Reported test amount0.5nmol/mg, reported accumulation ratio4, time≈40s; implied control0.125nmol/mg is derived from rounded prose only. | Native retained-label amount differs from initial flux. Do not borrow this4fold for the6fold-rate comparison. Fig3 visual point below differs from rounded prose; keep both representations and do not average. |
| Fig3 image: at40s, green≈0.60, gray≈0.18nmol/mg. | Graph-derived amount contrast≈0.42nmol/mg, graph ratio≈3.33. Region/source transcription details in GRAPH_TRANSCRIPTION_001.json. Approximate plotted SD green≈0.09, gray≈0.05; caption n=3 biological. | A concrete deletion-background complementation difference. Plotted SD is not SEM or known noise variance, and cross-arm pairing/covariance is unreported. Image/prose differences are alternate coarse representations of one experiment, not independent evidence. |
| Fig4B: competitor1mM with tracer10µM. | Competitor/tracer concentration ratio100 (derived from reported concentrations). | Exposure condition for the observed specificity test; not a selectivity score. The paper reports reduction only with cold pyruvate/Br-pyruvate, but no numeric per-compound rate is transcribed here. Failure to inhibit at this one condition does not prove a compound can never be transported. |
| Results/Fig4C: Km16.5±6.4µM. | reported_value16.5µM; reported_spread6.4µM; relative_reported_spread6.4/16.5≈0.3879. | Apparent whole-cell pyruvate transport parameter and relative printed spread. Its ± meaning remains unspecified; do not convert to SD/SEM/CI or source likelihood. Whole-cell Km does not calibrate a separate proteoliposome preparation. |
| Results/Fig5B: initial combined-H-gradient rate27.7; plot gives rate unit nmol mg^-1 min^-1. Prose omits min^-1. | reported_initial_rate27.7nmol mg protein^-1 min^-1, with unit witness explicitly Fig5B y-axis. Prose describes ΔpH initial rate as2-fold lower. Derived approximate ΔpH/combined-H ratio0.5 follows prose only. | BtsT-containing preparation's transport under imposed gradients, separate from whole-cell uptake. No rate uncertainty is copied from Fig3; Fig5 error bars are technical SD. The “2-fold” wording is coarse; Fig5B red bar is visually around16–17 rather than exactly13.85, so do not convert27.7/2 into a precise measured ΔpH rate. |
| Results/Fig5C: counterflow uptake described as0.28nmol mg^-1 min^-1; Fig5C y-axis is amount, nmol/mg, and the final point near1min is≈0.28. | Preserve reported rate0.28 with its prose unit and separately the graph's amount endpoint; no inference that they are the same numerical measurement. | This exposes a rate/amount ambiguity. A future reader must retain both source units and seek raw time-course fit before treating0.28 as a precisely derived initial slope. Lactate nondetection is not exact0. |

Fig3 manual numerical bounds, plotted SD approximations and figure/prose
disagreements must be visible to consumers. None are supplied to a known-normal
likelihood as exact observations or zero-error parameters.

## Source-level component equations and missingness

The useful A105 source question is whether the selected preparation transports
pyruvate under the specified conditions. The useful A106 question is whether
reintroduction of btsT raises deletion-background uptake, and separately whether
native loss/restoration establishes its physiological contribution. Those are
different questions, even when Fig3 informs both.

1. **Whole-cell complementation effect.** Extract per independent preparation
   slope rC and rD from a declared common initial interval, after retaining raw
   counts, filter/instrument blank, conversion factor and total protein mass.
   Component e=rC−rD has units nmol mg total protein^-1 min^-1. If the source
   supports paired preparations, d_i=rC_i−rD_i and mean(d)=sum(d_i)/n;
   Var(mean(d))=sample_variance(d)/n. Otherwise retain group counts, means, SD
   and actual dependence; for a difference of mean estimates
   V=VC+VD−2Cov(C,D). Thus preparation precision and control sharing enter the
   effect calculation once. Three biological replicates do not by themselves
   establish paired or independent-arm sampling. No raw replicate slopes are
   retained here, so the mean-rate difference/variance are unavailable.
2. **Fixed-time amount contrast.** For the expressly chosen40s endpoint,
   eA=AC−AD≈0.42nmol/mg from the image. It is a useful partial component for
   accumulation. Its uncertainty requires the arm mean uncertainties/covariance
   and the digitization model. It is not divided by40s and called an initial
   rate. It is not the same observation as an independently measured slope.
3. **Restoration fraction.** A true WT-referenced restoration fraction requires
   (rC−rD)/(rWT−rD), with matched WT, deletion and complementation conditions,
   actual expression amounts and joint uncertainty. rWT is absent from Fig3,
   so this component is null. The native-loss effect rWT−rD is likewise null;
   a large complemented/control fold cannot fill either missing cell.
4. **Experimental comparability versus isolation.** If an independently
   measured same-endpoint outside-variable response h=u/v applies, correct
   e/h, propagating shared covariance. If a separately measured unwanted
   contributor g changes across arms, correct e−g before amount/condition
   normalization; do not apply an additional arbitrary isolation fraction.
   Here nominal matched total protein does not establish matched BtsT amount,
   and unmeasured changes in metabolism/background uptake are not g=0.
   h,g and molecular turnover remain unknown. The historical concentration-rate
   q,g,k,E,u,v calculator cannot directly accept a per-mg cell uptake rate as q.
5. **Optional statistical conversion in the existing sheet's meaning.** With
   an actually supported known-normal source contrast e and known V>0, the
   stated proposal is S=e*abs(e)/(2V), then B=tanh(S/2). With actual independent
   paired differences and unknown normal variance, the sheet instead uses its
   paired-normal profile formula. Neither model is established for these retained
   rounded folds/image data, so S/B are null, not fabricated0 or1. This proposal
   concerns the source contrast only. There is no target-transfer multiplier,
   source pooling or final annotation-credit calculation in this packet.
6. **Same-system substrate correction.** For genuinely comparable whole-cell
   measurements on the same fitted curve, h=[S1/(Km+S1)]/[S2/(Km+S2)]. The
   shared Km enters once, with its actual fit covariance. The historical10/40µM
   calculation is a conditional same-system scenario; the paper's10µM whole-cell
   and40µM proteoliposome protocols do not satisfy that common-curve condition.
   Therefore h cannot be used to compare those two actual experimental systems.

These equations use explicit differences, sums and multipliers to populate
numerical components. The unreported operands are scientific missing inputs;
transport-specific parsing, graph extraction and statistical calculators remain
unimplemented work. A mathematical proposal does not implement them.

## What the complementary evidence repairs, and what it does not

Reconstitution addresses the whole-cell objection that retained label can
reflect other transporters and metabolism. The article reports little uptake
in protein-free liposomes (S10), but that original control image/raw values were
not acquired; do not enter an exact blank or purity fraction from the prose.
Quantified empty-liposome, nonspecific-binding/filter and incorporated-protein
controls under each buffer/gradient would support more specific effect isolation.

The YYC202 comparison (S7) changes aceEF/pflB/poxB/pps metabolism, and the main
text says its uptake pattern was similar while metabolism could not be fully
blocked. It is complementary qualification, not an independent pure-transport
measurement or proof metabolism contributes zero. Native btsT in YYC202 has not
been stated deleted, unlike MG1655 ΔbtsT; do not transplant the deletion arrangement.

The main text reports no growth defect of MG1655 ΔbtsT in LB or pyruvate M9
(S5). This limits an unconditional physiological-necessity claim; it is not
zero molecular transport activity. Growth curve rates/equivalence margins were
not acquired. MBP-fusion/maltose complementation and topology inference are
separate constructs/endpoints; neither supplies a BtsT transport restoration
percentage or an experimental 18-helix structure.

Gradient manipulation supports energy coupling, but the exact H+:pyruvate
stoichiometry is explicitly unknown. Do not turn the inferred “more than one”
proton into a measured coefficient. Results and Methods give inconsistent
Na-condition buffer descriptions: Results says sodium-phosphate pH7.6, while
Methods bufferE is Tris/MES pH5.8 with50mM NaCl. That condition must remain
conflicting rather than silently chosen; no strong Na-specific conclusion or
comparability number is calculated from it. Direct gradient/proton-flux
measurements would address coupling amount and actual driving-force questions.

Fig3 rows, sixfold prose and fixed-time graph are one experiment family. Fig4C
kinetic fit reuses uptake methodology and its own diffusion correction; its
multiple concentrations are not multiple biological preparations. Fig5 technical
replicates, its slope and time-course representations are not independent
reconstitutions. The global Methods statement about independent samples and
SEM does not override panel-specific SD/technical captions; retain that source
inconsistency and seek preparation identities before assigning statistical n.

## Focused reader/interpretation questions for the next implementation

Investigation instructions should ask which actual cell/protein preparation,
endpoint, denominator, interval, background and intended variable the source
supports. They should explicitly distinguish accumulated radiolabel, initial
transport slope, direct competitor transport, growth and inferred coupling.
Closed meanings can be transport_flux / accumulated_tracer / growth / unknown /
conflicting; restoration basis can be deletion_complement_vs_empty_vector /
matched_wt_deletion_complement / other / unknown / conflicting. A literal
source witness establishes custody, not scientific correctness.

The numerical sheet needs endpoint-specific native units, test/reference arms,
time interval, source-fold precision, reported-versus-graph origin, source
representation conflicts, replicate basis and full covariance owners. A targeted
reader should populate those exact fields; deterministic arithmetic should
calculate the supported differences/ratios and model quantities. Missing WT,
amount calibration, covariance, raw slopes and reconstitution independence must
survive partial returns. No complete scoring sheet is inserted into a prompt.

Next implementation remains the parent's decision after independently reading
the source and completing its reset. This packet is not an installed transport
reader or A106 grader, and the parent must present useful proposed numerical
examples in the conversation before broad replication.
