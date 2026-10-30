# A105: IscR–promoter EMSA, case096

Research evidence and proposed paired fields/components; not governing instructions,
an adopted scoring policy, production implementation, or a completed A105 grader.

The experiment is Figure8A in Jang et al., *Regulatory Characteristics of Vibrio
vulnificus gbpA Gene Encoding a Mucin-binding Protein Essential for Pathogenesis*,
J Biol Chem (2016), DOI10.1074/jbc.M115.685321,
<https://pmc.ncbi.nlm.nih.gov/articles/PMC4786714/>.

## Experimental definitions

The measured molecule is purified His-tagged **V. vulnificus IscR**, produced in
E. coli BL21(DE3) using pJK0928, a pET28a(+) iscR expression construct. The study's
source strain is V. vulnificus MO6-24/O, a clinical wild-type isolate. The assay
does not mix wild-type and mutant IscR and does not measure an abundance blot.
The source does not specify exact tag/construct boundaries, purity or active
protein fraction in the retained Methods. Aerobic isolation, purification and
use motivate the authors' inference that most IscR is apo; cluster occupancy
was not measured in these binding lanes. Do not turn that inference into 100%
apo or apply an E. coli IscR assay's state measurements to this preparation.

The ligand is a 390-bp gbpA promoter PCR fragment spanning−301 to+88, labeled
using gamma-32P-ATP-labeled GBPA05-F and unlabeled GBPA05-R. Each reaction has
5nM labeled DNA, 0.1microgram poly(dI-dC), 1×binding buffer, volume20microliters,
incubation30minutes at30°C. Buffer composition and detailed electrophoresis
conditions are referenced to prior methods rather than specified here. Images
were visualized using the BAS1500 phosphorimager method described for transcript
analysis; this retained artifact is the published JPEG, not native detector data.

Lanes1–4 change nominal IscR concentration0,10,20,30nM. Lanes5–8 keep IscR30nM
and add15,30,60,120nM unlabeled copies of the same promoter DNA, before IscR.
Both labeled and unlabeled DNA coexist. This is self-competition, not mutation
replacement or competition against a different sequence. The competitor/probe
molar ratios are3,6,12,24; protein/probe ratio on competition lanes is6. These
ratios describe the actual comparison and are not affinity or confidence scores.

Experimental comparability concerns the conditions outside the intended IscR
or competitor change: the protocol specifies the same labeled fragment, nominal
probe amount, incubation, volume and nonspecific competitor. Protein/competitor
stock vehicle contributions, exact recovered amounts and image response are not
documented as equal by these labels; those remain separate unknowns. The lane
total diagnostic below makes one quantitative limitation visible.

Effect isolation asks which molecule caused the altered migration: no-protein
and self-competition lanes link the shift to the protein preparation and same
DNA ligand, while a co-purifying DNA-binding contaminant could track the IscR
dose and also be competed by the same DNA. This is distinct from whether the
lanes share nominal buffer conditions. No unreported purity percentage or
contamination error probability is supplied.

Two retarded bands are labeled B and free DNA is labeled F. Their migration and
intensity are the direct endpoint. The no-protein lane supplies a free-probe
mobility/background control. Poly(dI-dC) challenges nonspecific DNA binding in
all lanes; it is not a measured nonspecific error probability. Self-competition
supports binding to the same DNA preparation but does not quantify discrimination
against an unrelated sequence. Two retarded bands are not two independent assays
or, by themselves, a definitive count of binding sites/stoichiometry.

Source anchors in retained `primary.txt`: Table1 lines87–176; purification283;
EMSA285; general data-analysis statement291; binding Results338; Fig8 caption341;
reported DNaseI protection343 and346. Full article was read, including references.
The general statement of at least3 independent experiments is retained as such;
no exact n, lane SD, independent preparation identities or raw replicates can be
assigned to this displayed gel. Eight lanes are eight conditions, not n=8.

## Actual numerical conversion

All following image numbers are **image-derived and calculated**, not author
reported densitometry. Retained native image:600×937, grayscaleL,67,304bytes;
SHA256 `d30e38e432492d114610de90c542ee04bffabb990a46c04331c9bae24fd8c0eb`.
The original JPEG is unchanged. Original HTML and rendered text have separate
acquisition/byte-identity records beside this report.

Analysis uses zero-based, half-open rectangles. Lane x centers are
47,93,140,190,242,291,341,392; baseline x ranges are center±19. Upper shifted
band y=[197,215), lower shifted=[219,239), free=[248,274). Background is each
lane's x range with y=[151,190). Whole-lane check uses y=[145,278), excluding
the printed frame. Coordinates are analyst-declared after viewing source labels,
not reported by authors or inferred by an automatic band recognizer.

Let D=255−JPEG grayscale. For each band b in lane i,
S_ib=sum(D in band)−N_ib*mean(D in that lane's background).
This explicitly proposed local-background model assumes a uniform baseline
within the selected lane region. It does not claim that baseline is physically
correct. Negative corrected values remain negative. The selected ROIs partition
the three visible band areas; material in smears, elsewhere in the lane, wells,
or outside the shown gel is not silently counted as one of them.

Define B_i=S_upper+S_lower; T_i=B_i+S_free; f_i=B_i/T_i when T_i>0.
**f is a selected shifted display-darkness fraction, not molecular bound fraction.**
JPEG contrast, detector response, native saturation, exposure and processing are
unknown. The radiolabel design alone does not linearize the published JPEG.

| Lane | IscR nM | Competitor nM | Upper S | Lower S | Free S | f | T/T_lane1 |
|---|---:|---:|---:|---:|---:|---:|---:|
|1|0|0|0|0|100577|0|1|
|2|10|0|3439|55150|81813|0.417295|1.3960|
|3|20|0|38473|58516|51687|0.652351|1.4782|
|4|30|0|41602|34222|31487|0.706582|1.0670|
|5|30|15|21880|69413|78936|0.536295|1.6925|
|6|30|30|1973|54569|89692|0.386654|1.4540|
|7|30|60|353|34490|96784|0.264710|1.3087|
|8|30|120|0|1741|115223|0.014885|1.1629|

S has display-gray-level×pixel units. Numerical zeros in this display do not mean
zero molecules or a known biological detection limit. The selected lane totals
range100577–170229, a1.6925-fold spread despite reported5nM labeled DNA throughout.
That diagnostic can reflect loading/recovery, differential complex signal,
contrast/clipping, or other processing; this image does not identify the cause.
It prevents treating T as demonstrated conserved molecular mass or silently
using its normalization to erase that uncertainty.

## Paired extraction fields and numerical sheet cells

| Proposed cell | Exact extraction inputs/location | Formula and worked result | Scoring meaning and combination role |
|---|---|---|---|
|No-protein shifted display fraction f0|Fig8A lane1 band/background pixels, 0nM IscR label|0/(0+100577)=0|Measured displayed background at shifted mobility; subtract in an IscR-associated contrast. No conversion to false-positive probability.|
|30nM shifted fraction f30|Fig8A lane4, its three band ROIs|75824/(75824+31487)=0.706582|Relative selected signal in shifted species; same numerator/denominator retained.|
|Protein-associated shift Δ30|f30 and f0, no-competitor lane relationship|f30−f0=0.706582|Control-adjusted display effect associated with added IscR; not total reliability.|
|Retained shift R120|Fig8A lane8 at120nM competitor, lane4 reference, lane1 control|[(1741/116964)−0]/[0.706582−0]=0.021066|Fraction of the no-protein-adjusted display shift retained under this particular self-competition dose.|
|Self-competition removal C120|Same exact operands as R120|1−R120=0.978934|Control result linked to specificity for the same DNA preparation. C120 and R120 are alternative representations, not two contributions.|
|Self-competitor-removable IscR-associated shift D120|Δ30,C120 and shared operands|Δ30*C120=f30−f120=0.691697|Explicit multiplication compiling the signal and competitive reversal into one assay contrast. It is not a probability or an overall experimental-reliability grade.|
|Selected-signal recovery diagnostic|All T_i, common5nM labeled probe, lane1 reference|T_i/T_1=1.0000–1.6925|Identifies quantitative comparability/calibration concerns, rather than rewarding equal-input labels as proof of equal recovered signal. Do not multiply this diagnostic as a reliability weight.|
|Off-band display diagnostic|Whole-lane corrected sum minus three-band sum, divided by whole-lane sum|Baseline fractions0.0035–0.0160|Selected-band omission check within the shown lane. Not a complete recovery measure or bound on unshown complexes.|
|Display black-level occupancy|Count of gray0 pixels per ROI, corresponding pixel count|Lane4:73/2432=0.030016|Shows digital-minimum occupancy. Does not establish native phosphorimager saturation or a correction factor.|
|Image-analysis-choice range for D120|All14 declared ROI/background variants|0.691385–0.704998|Sensitivity to stated extraction choices; not sampling variance, a confidence interval or a complete error bound.|
|Independent-preparation precision|Preparation IDs and replicate lane measurements absent|Unknown|No n=8, no SD/SEM conversion or precision bonus from pixels.|
|Calibrated molecular binding/affinity/error contribution|Native signal calibration, active species, applicable binding model, replicate/covariance data absent|Unknown|No Kd, intrinsic affinity, assay error probability or overall reliability scalar populated.|

Useful partial calculations survive missing biological precision. For each valid
image variant D120 is calculated using its own f0,f30,f120 together; ranges are
not formed by independently mixing extrema from different variants. Baseline
Δ30=0.706582 and C120=0.978934 share operands. Their product algebraically cancels
f0: **D120=f30−f120**. This is why treating those two rows as independent proofs
would overstate the evidence. With actual repeat data, Var(D120)=Var(f30)+Var(f120)
−2Cov(f30,f120); no covariance or variance is available here. Shared background,
probe preparation, protein preparation and image processing can contribute
dependence, distinct from random lane error. The observed monotonic dose pattern
is useful; it supplies no numerical chance of that pattern under a null model.

There is no source-grounded function mapping these image components plus the
missing assay-error terms into a single experimental-reliability probability.
That required conversion remains unresolved rather than filled with1 or a verbal
category coded as a number. D120 is a concrete component with explicit arithmetic
for later combination; W05/target transfer/final annotation credit are outside
this case. A105 is not complete.

## What complementary experiments address

The same paper reports DNaseI protection of−184..−145 and−124..−88 using the same
390-bp DNA but25nM probe. This provides sequence-region localization beyond a
mobility shift and helps address the possibility that a retarded band is
uninformative about which promoter region is bound. Figure9 pixels were not
downloaded or quantified in this task. Its reported protection is not an
independent replication of Figure8 densitometry, does not map each shifted band
uniquely to one site, and does not quantify an error rate. Same protein/probe
preparation relationships must remain unknown where not reported.

A matched unrelated-DNA or sequence-site mutant competition assay would address
sequence discrimination more directly; it is not reported as a Figure8A control.
Native calibrated exposures/dilution standards would address image-response
linearity and clipping. Independently prepared protein/probe replicates would
address reproducibility and some preparation contamination explanations. Purity
or identity measurements would address contaminating DNA-binding activity;
measured cluster occupancy would test the mostly-apo inference. These are
concrete missing error contributions, not a mandatory universal checklist or
new eligibility gate. No absent experiment is scored as zero.

The transcription/deletion results in this paper bear on regulation. EMSA alone
does not establish whether IscR activates transcription, nor an in vivo effect
size. No sequence or structure transfer from this reference to another target
is calculated here.

## Aspect-specific interpretation TASK proposal

Determine what the selected experiment establishes about the assayed IscR
molecule binding the specified gbpA promoter DNA. Establish the actual protein,
construct and preparation state; distinguish the authors' aerobic mostly-apo
inference from measured cluster occupancy. Identify the DNA fragment, label,
nominal concentrations, buffers and other molecules. Map the no-protein,
protein-titration and self-competition lanes using the figure labels and methods.
Distinguish free DNA, the two retarded species and any unresolved smear or overlap.
Explain which comparisons isolate protein addition and which test competition
by the same unlabeled ligand. Keep omissions, uncertain identities and possible
alternative stoichiometries explicit. A gel band is not an independent assay.

Decide whether the available artifact supports only display-intensity comparisons
or a calibrated molecular fraction. Identify actual response/processing evidence;
do not infer linearity, equilibrium, detector saturation, active protein fraction,
sampling uncertainty or affinity from the appearance of the published gel.
Preserve control-linked partial measurements and identify the particular
additional evidence needed for a stronger interpretation. Separate direct DNA
binding from activation and from transfer to another protein. Return the
declared experimental meanings and operand relationships; deterministic functions
perform intensity extraction, unit conversion and arithmetic. Do not produce an
overall confidence grade or insert the numerical sheet into this TASK.

Proposed constrained interpretation outputs (semantic fields, not numeric scores):

- `endpoint`: `mobility_shift_of_labeled_DNA`, `abundance`, `other`, `unknown`,
  `conflicting`.
- `comparison_role`: `protein_addition`, `same_DNA_self_competition`,
  `different_DNA_competition`, `other`, `unknown`, `conflicting`, with exact lane refs.
- `species_role`: `free_probe`, `retarded_species`, `unresolved_material`,
  `unknown`, `conflicting`; no forced stoichiometry assignment.
- `protein_state_basis`: `directly_measured`, `handling_based_inference`,
  `unreported`, `conflicting`, with source-supported state description.
- `signal_scale`: `published_display_darkness`, `native_linear_tracer_signal`,
  `other_calibrated_signal`, `unknown`, `conflicting`; calibrated values require
  actual source evidence, not a model's preference.
- `supported_assertion`: `binding_to_specified_DNA_under_assayed_conditions`,
  `competition_by_specified_DNA`, `neither_resolved`, `conflicting`.
- `limitation_kind`: specific allowed names for unmeasured calibration,
  unresolved band identity, absent replicate variance, unknown preparation
  dependence, unmeasured state fraction, or missing sequence-discrimination control.

Each interpretation cites its actual Methods/figure/Results anchor. Source
conflicts retain alternatives. Unknown fields do not prevent valid pixel cells.
These proposed meanings require the user's running feedback before production
prompt implementation; they add no runtime approval stage.

## Exact reader/calculator changes this case requires

The current production `literature_binding_reader.py` reads selected IC50 or
reported-Hill-Kd JSON table tokens; `literature_binding_calculations.py` computes
parameter contrasts. Neither reads gel pixels. Keep those outputs distinct.
Do not put this case's f or D into a binding-parameter field or call a graph
axis reader a gel reader.

1. An assay-relationship interpretation input must carry selected retained
   source passages plus original image view. Its return must bind each lane to
   protein/ligand/competitor roles and measured species, preserving all source
   anchors and conflicts. Generic family classification alone is insufficient.
2. A separate retained-gel image input must carry original source/artifact/view
   identity, exact native-byte hash, dimensions, channel/gray encoding,
   transformation history, panel region, lane relationships, band/background/
   whole-lane ROIs, declared ROI alternatives and their selection basis. No
   invented gel axes. A saved transcription is not pixel extraction.
3. A deterministic image reader must validate those bytes/coordinates, retain
   raw sums/counts, background method/operands, corrected sums without clipping,
   digital extrema and overlap/unresolved status. Invalid one-band ROIs preserve
   other valid bands with specific unavailable reasons; unknown scale is not an
   acquisition failure. Equal values do not merge distinct lanes.
4. The targeted calculator must populate B,T,f,Δ,R,C,D,selected-signal recovery
   and off-band diagnostics using explicit denominator/context checks. T<=0,
   missing required bands, conflicting lane roles or an unavailable reference
   yield an unavailable affected contrast while preserving raw valid cells.
   Reported ND/limits retain their own meanings; no exact-zero imputation.
   Molecular fractions need applicable calibration; affinity needs an actual
   applicable model and operands. Do not fit a generic one-site Kd to two shifted
   species merely because nominal concentration labels exist.
5. Persist the image, ROIs, interpretation outputs and all operand identities
   through the existing selected LiteratureEpisodes boundary. Exact replay must
   not reacquire, reinterpret or select new ROIs. Alternative readings of the same
   physical band are related readings, not independent experiments. Different
   overlapping assay methods can still add verification; retain their actual
   preparation dependence and errors rather than collapsing by endpoint.

Only a narrowly scoped verification script implementing this one image's declared
extraction/arithmetic exists in `verification/.../gel_case_096/measure_figure8a.py`.
It performs no acquisition, OCR, model call, biological suite, curve fit or
production invocation. Eight focused custody/replay/relationship/arithmetic and
unknown-preservation checks passed. No production path or model-backed scientific
run was changed or launched. Production reader integration and a calibrated
reliability conversion remain unfinished work.
