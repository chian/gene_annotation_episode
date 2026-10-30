# Fresh064 — print-ready scientific handoff

One primary paper was read in full, the original Figs. 3 and 6 were actually
viewed, and the complete applicable post-paper reset was performed before this
conversion. The supplement layout was read for specific strain/construct and
loading/calibration questions. No other paper, search, model call, runtime,
production calculator or implementation was run. Root still owes its own
source read/reset; this report is not independent verification by root.

Fig. 3C is anti-His expression signal in E. coli ΔyeaG cells receiving separate
plasmid YeaG constructs. The mutant replaces missing chromosomal YeaG; it does
not coexist with chromosomal WT. The reference is His-tagged, plasmid-expressed
WT in the corresponding blot, not native untagged WT expression. Exact Fig. 3C
sampling/loading linkage is incompletely reported. Supplement Table S2's
MG1655/BW25113 naming issue is preserved, not silently repaired.

| Variant | Actual reported signal / corresponding plasmid-WT signal | Proposed arithmetic: difference from reference | Scientific use |
|---|---:|---:|---|
| K116A | 0.64 | −0.36 | Expression-signal difference can confound recovery-growth failure |
| R232A | 0.48 | −0.52 | Same issue, separately measured variant |
| K426A | image1.12 versus Results1.00 | +0.12 versus0 | Unresolved representation conflict; no single selected point |
| Y382Stop | 0.96 | −0.04 | Similar reported signal does not restore deleted domain or prove active amount |

These are reported printed summaries, not freshly measured pixel intensities.
The figure's vector0 is not a measured detection threshold. Loading control,
exposure/linear range, calibration, blot-specific replicate count, spread and
shared-denominator covariance are unavailable. No molecule-amount, purity,
active-fraction or activity-reliability value follows from the image alone.

The principal scientific destination is A106 comparability in a
perturbation/restoration experiment. A105 source-activity operands remain
unknown here. Fig. 3 concerns recovery growth; Fig. 6B prolonged-starvation CFU
tests K426A and Y382Stop, not K116A. The old K116A survival implication must not
return.

Concrete proposed numerical cells include r, r−1, ln(r), and (r−1)², each with
its actual signal basis, construct, denominator and conflict state. The latter
is a proposed additive signal-mismatch operand, not a generic reliability
grade, likelihood or independent piece of evidence. For K116A these are .64,
−.36, −.446287103, .1296. No average across the four different mutant
interventions is justified. The present amount contract supports mg/ml stock
target/total or µM nominal arms; this dimensionless blot signal does not fit
either unchanged.

For an explicitly synthetic direct-enzyme example ONLY: if calibrated molecular
amount ratio Em/Ew=.64 and corrected rate ratio vm/vw=.20, the per-amount
activity ratio is .20/.64=.3125. Here 1/.64=1.5625 is a denominator-conversion
multiplier applied once, not a confidence multiplier. This paper supplies
neither direct-rate ratio nor calibrated molecular amount. Recovery lag cannot
be divided by .64; a matched WT expression-dose/recovery-response measurement
is the missing relationship.

Next reader design should distinguish printed-summary extraction from actual
densitometry. Both require aspect-specific interpretation of signal meaning,
lane/construct/host arrangement, reference basis, endpoint linkage, replication
and conflicting representations. Raw densitometry additionally requires
declared image/background regions, acquisition/linear-range controls, loading
and applicable molecular calibration. The deterministic calculator performs
the arithmetic after those meanings and operands are retained. These are
multiple reusable reader needs feeding experimental components, not a generic
gel grade or a new axis.

Full equations, finite interpretation meanings, missing-input/dependence rules,
and precise reader needs: PAIRED_COMPONENTS_002.md. Experimental definitions and
source locations: SCIENTIFIC_CASE_001.md. Provenance/hashes:
READ_PROVENANCE_001.json and READ_HASHES_001.json. Numeric research receipt:
RESEARCH_ARITHMETIC_003.json. No proposed scoring policy was adopted.
