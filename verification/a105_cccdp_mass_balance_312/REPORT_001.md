# A105 CcCdP original-source paired-account research

This is a bounded original-source conversion under the immutable user-supplied
literature goal. It supplies a worked numerical A105 proposal and exact reader
inputs; it is not a completed grader or an adopted annotation-credit policy.
The original paper is Klimacek, Zhong and Nidetzky (2021), DOI
10.1186/s13068-021-01982-2, with the authors' Figure 2 and Figure 3 workbooks
at Zenodo DOI 10.5281/zenodo.4555807. The inspected source copies are in
`source/`; SHA256: article HTML
`bed5ff3b157dae8567f9d810fe292fa573a3bf54ebcd9a819a259686362f03a6`,
Figure 2 XLSX
`7d5fbe5b3eb18aa18417bcd8f151951e021e7619f306c1dd11b6e508b3e972af`,
Figure 3 XLSX
`8640de5eb981712cb7690266651b5dc35225fd7d1d22e47767aa4c067618e9b9`.

## Actual experiment and question

The assayed molecule is N-terminal His-tagged cellodextrin phosphorylase from
*Clostridium cellulosi* (CcCdP; article GenBank CDZ24361.1). This paper uses
purified protein prepared by a cited earlier method; its current Methods do not
establish the expression host or independent purification-preparation count.
The Figure 2D reaction has nominal 100 mM α-glucose-1-phosphate donor and
25 mM cellobiose (G2) acceptor, 1 U/mL enzyme (0.08 mg/mL), 50 mM MES pH 7,
45 °C, 1 mL, and time sampling. Reactions were duplicate. The intended varied
condition across Figure 2 A-D is the donor/acceptor starting ratio; comparisons
across those panels therefore have a changed substrate dose, while within the
D time course the sampled time changes. A matched no-enzyme numerical arm,
same-aliquot analyte covariance and independent preparation count are not
provided in the inspected source.

G2, G3, G4, G5 and G6 are measured by refractive-index HPLC, with authentic
standard calibration ranges respectively 2.5-50, 2.5-15 (G3/G4), 1-7.5 and
1-2.5 mM. Pi is measured separately by a colorimetric method. All five HPLC
means selected below are within those stated ranges. The article's reaction
account is one Pi released per glucosyl unit transferred from donor to a COS
acceptor; a G3 molecule has one added unit relative to G2, G4 two, G5 three,
and G6 four. This is an explicit chemical model, not an extra measured value.
The Figure 3 "insoluble" quantity is calculated as a residual from Pi and
soluble COS; it is not an independent measurement of solid product.

## Figure 2D original-data cells at 90 minutes

The initial G2 25 mM is `Data!B52`; the 90-minute row is `Data!61` in the
original Figure 2 XLSX. Original numeric cell values, preserving the source's
reported mean/SD distinction, are:

| Measurand | Mean cell, mM | Source SD cell, mM |
| --- | ---: | ---: |
| G2 | B61 = 3.0467840000000002 | C61 = 0.353912 |
| G3 | D61 = 5.5448360000000001 | E61 = 0.037394999999999998 |
| G4 | F61 = 6.6495870000000004 | G61 = 0.003399876 |
| G5 | H61 = 3.7561990000000001 | I61 = 0.31350299999999998 |
| G6 | J61 = 1.9335089999999999 | K61 = 0.069866999999999999 |
| Pi | N61 = 43.291423000000002 | O61 = 1.0822860000000001 |

`A61` and `M61` both report 90 min; `A52` and `M52` both report zero. Zero-time
G3-G6 and Pi entries are printed as numeric zeros, but this does not establish
a detection limit or absence of background reaction in a matched no-enzyme arm.

## Paired extraction fields and proposed numerical cells

The reader must bind original workbook bytes/hash, Figure 2 `Data` sheet,
panel D label and panel-specific headers, exact row/time, analyte labels,
source cell addresses, numeric lexical values, metadata conditions and
calibration ranges. It must keep assayed CcCdP distinct from any annotation
target, and record that HPLC/Pi means share a reaction design but were read by
different methods. Their duplicate reaction SDs do not give joint covariance.

Define `L = G2_0 − G2_t = 21.9532159999999998 mM` and
`M = G3+G4+G5+G6 = 17.8841310000000005 mM`. The descriptive acceptor
molecule-account ratio is `R_A = M/L = 0.8146474302443888`, and the residual
`L−M = 4.0690849999999993 mM`. This checks how much of measured G2 loss is
represented by measured soluble COS molecules. It is not a direct solid-product
measurement or an enzyme-specific fraction.

Define soluble added-glucosyl equivalents
`W = G3+2G4+3G5+4G6 = 37.8466430000000008 mM`. With measured
`Pi = 43.291423000000002 mM`, `R_G = W/Pi = 0.8742295904664533`, and the
residual `Pi−W = 5.4447800000000012 mM`. `R_G` evaluates the fraction of
apparent transfer equivalents recovered in the measured soluble products under
the one-Pi-per-transfer model. The source interprets missing equivalents as
insoluble products; that conclusion is conditional on the reaction account,
measurement calibration and absence of other phosphate sources/sinks.

The nominal donor-to-soluble-product yield can be written as the explicit
multiplier `(Pi / 100 mM nominal donor) × (W/Pi) = W/100 = 0.37846643`.
This is an outcome component for the *soluble-product claim*, not a reliability
or annotation probability. The two factors share the Pi measurement, so their
product is one dependent expression of `W/100`, not two corroborating assays.
`R_A`, `R_G` and the yield share G3-G6 and must not be added as independent
credit. The general A105 compilation of method validity, effect isolation,
uncertainty and claim relevance is still missing. No ratio variance, SE or
confidence interval is computed without within-reaction covariance. No
matched-control correction or protein-specific attribution factor is imputed.

The current A105 worksheet admits twelve source formats but no specific
multi-product stoichiometric-balance section. Its product-coupling format is
for product versus cofactor **rates**, so repurposing that calculation for
finite G2/COS/Pi concentrations would be wrong. A targeted reader/calculator
and typed selected path are the next implementation workload. This is a new
assay design, not a thirteenth completed grader by declaration.

## Authority and verification scope

After inspecting the original article and authors' initial workbook layout,
root reread the complete immutable goal and complete per-paper authority set
in sequential untruncated portions, plus the current full A105 worksheet and
product-coupling input/calculation contracts. Root then inspected the selected
row and made the exact Decimal calculations above; no production reader or
selected LiteratureEpisodes action was run for CcCdP at this checkpoint.
Latest user instruction: continue the existing goal, with A105 first.
