# Root concentration-window conversion and implementation gap

This is implementation evidence for the fixed user goal, not an amendment or
replacement goal. It continues the already inspected Rudolph et al. eLife 65773
case. Root completed its own post-paper reset in ROOT_POST_PAPER_RESET_001.json
before this conversion. No new paper, source acquisition or biological result
is introduced here. The prior primary-source receipts and root conversion are
in a105_matched_estimator_source_260 and a105_matched_estimator_review_263.

## Experimental definitions

The selected Fig. 6C arm contains WT PARP1 and Nuc165 without added HPF1.
An HPF1-added arm contains coexisting molecules, not replacement PARP1. HPF1
E284A is a distinct partner variant. Do not merge these arrangements.

The modified HPLC protocol describes 1 µM PARP1, 1 µM activator, 200 µM NAD+,
a 450 µL reaction and 45 µL aliquots quenched with 45 µL 1 M perchloric acid.
Do not borrow the separate Fig. 5 concentration/time protocol, its repetition
statement or a filter-assay no-PARP1 blank. The protein resource accessions do
not resolve every preparation/construct detail. Missing definitions stay missing.

The original workbook and actual rendered figure identify concentration units
as µM. PDF text glyph corruption is a representation problem; it is not a
biological disagreement or permission to multiply concentrations by 1000.
HPLC uses calibration standards, but this selected record does not supply a
usable joint uncertainty model or establish blank and recovery values.

## Paired extraction and numerical components

Retain original workbook sheet/cell identity, literal number, unit support,
source/artifact identity and exact source location. Select the actual arm,
analyte, series, aliquot/time-window relationship, normalization and any
prior correction. Preserve reported points, bounds, approximations and ND.

| Operand | Start coordinate 1 s | End coordinate 50 s | Measurement |
|---|---:|---:|---|
| S | 200 µM | 100 µM | NAD+ concentration, workbook C2/C5 |
| N | 6.5 µM | 101 µM | Nicotinamide concentration, workbook D2/D5 |
| A | 2.8 µM | 13.2 µM | Free ADP-ribose concentration, workbook B2/B5 |

These are source numbers. The following are derived numerical components:

| Component | Calculation | Value | Bearing on experimental evidence |
|---|---|---:|---|
| Substrate loss | S_start − S_end | 100 µM | Extent of substrate disappearance |
| Nicotinamide gain | N_end − N_start | 94.5 µM | Extent of the cleavage-associated product endpoint |
| Free ADP-ribose gain | A_end − A_start | 10.4 µM | Extent of the specifically measured free-product endpoint |
| Signed balance discrepancy | substrate loss − nicotinamide gain | 5.5 µM | Agreement of the selected chemical account, without an invented tolerance |
| Loss/product comparison | substrate loss / nicotinamide gain | 200/189 | Descriptive comparison of the two chemical endpoints |
| Free-product partition | free ADP-ribose gain / nicotinamide gain | 104/945 ≈ 0.11005291 | Product-fate resolution relative to cleavage, conditional on the endpoint/chemical relationship |

These differences are explicit signed sums. The partition is an explicit
multiplier: partition × nicotinamide gain reconstructs free ADP-ribose gain.
That reconstruction reuses the same measurements and is not extra verification.
The balance discrepancy concerns method/chemical agreement; the partition
concerns functional resolution. Neither is a reliability probability or a
molecule-specific causal fraction. The denominator and its scientific meaning
must survive the return to a parent.

The released coordinates differ by 49 s. If their physical elapsed-time meaning
is explicitly supported, conditional interval-average components are 100/49
µM/s and 94.5/49 µM/s for loss and nicotinamide gain. A coordinate difference
can be retained when that physical interpretation is unresolved; concentration
differences remain useful. Do not relabel interval averages as initial velocity,
Vmax, kcat or active-enzyme-normalized turnover. Do not replace the first
coordinate by zero because the graph has a logarithmic time axis.

## Uncertainty, dependence and limitations

For ordered concentration vector U=(S_start,S_end,N_start,N_end,A_start,A_end),
the differences use rows (1,-1,0,0,0,0), (0,0,-1,1,0,0) and
(0,0,0,0,-1,1). An applicable joint covariance C would propagate as B C Bᵀ.
It is not supplied by the selected trajectory. Time-point variation is kinetic
change, not replicate noise. One released series does not establish biological
n=1. Shared aliquots/calibration do not establish missing covariance values.
The separate Fig. 6D repetitions do not become Fig. 6C uncertainty.

Retain signed contradictions and ratios outside a proposed physical domain;
never clamp them into agreement. ND is not exact zero. Withdrawn aliquots and
quench dilution must retain their actual meanings; do not multiply all
concentrations by the initial reaction volume to claim cumulative amounts.

The existing reported-product-partition reader accepts already reported
fractions. It cannot read this concentration trajectory and calculate the
differences above. The existing common assessment expects particular rate and
kinetic operands; relabeling these concentrations as those inputs is invalid.
This is a missing production reader/calculator, separately from genuinely
missing scientific uncertainty and controls.

The next implementation is a targeted concentration-window reader with paired
closed extraction, calculation and numerical-sheet contracts. It must preserve
usable partials and distinguish missing inputs from unimplemented functions.
Reviewing that interface against this already converted example is engineering
reuse; it does not authorize another paper search or a new biological inference.
Selected execution, typed delivery and reconstruction still need demonstration
after the numerical implementation exists. A105 and the larger goal remain open.
