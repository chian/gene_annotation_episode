# A105 Arad3529 primary-paper conversion: substrate specificity and product check

This is a source-grounded A105 research conversion, not an adopted overall grade,
an additional evidence axis, or a completed reader. The immutable user-supplied
goal remains authoritative. The original paper is Fan et al., *JACS* 135,
795–803 (2013), doi:10.1021/ja309680b, [author-hosted original PDF](https://www.chem.tamu.edu/rgroup/raushel/publications/P274-JACS-Pterin%20Deaminase-2013.pdf).
The downloaded nine-page PDF is `source/P274-JACS-Pterin_Deaminase-2013.pdf`,
SHA256 `620b47080c971b74e30c2c107d704ab24759433fc80326668dc647b4e26b1ae3`;
`source/P274-JACS-Pterin_Deaminase-2013.layout.txt` is its 594-line
`pdftotext -layout` rendering. Page numbers below refer to printed article pages.

## Experimental definition

| Relationship | Original paper evidence | A105 meaning and limit |
| --- | --- | --- |
| Assayed subject | *Agrobacterium radiobacter* K84 Arad3529 gene cloned into CHS30, which encodes a C-terminal TEV-cleavable StrepII/6xHis tag; expressed in *E. coli* BL21(DE3) pRIL; sequential affinity and size-exclusion purification, SDS-PAGE check (pp. 796–797, Methods) | Purified recombinant Arad3529 preparation was assayed. Actual tag-cleavage state and independent purification count are not established. This is not an in-organism pathway measurement. |
| Screening arrangement | Addition of 1.0 µM enzyme to 100 µM compound in 20 mM HEPES pH 7.7; UV-visible spectrum 240–400 nm (p. 798, Physical Library Screening) | The intended changed variable across screened wells is compound identity. The paper does not report matched blank slopes or per-compound detection limits. Screening enzyme concentration must not be borrowed for later kinetic fits. |
| Screening set | 11 docking-prioritized compounds, 104 known amidohydrolase substrates, then 11 pteridine-ring compounds after pterin positives; eight predicted candidates and three negative-control nucleosides described in Results (pp. 798–799) | Selection sets overlap conceptually and were not random independent replications. A failed screen is not a measured zero; exact negatives and limits require the supplementary list and assay-specific thresholds. |
| Quantitative assay | Reported `kcat`, `Km`, `kcat/Km` for substrates in Table 2; Methods prints substrate/product differential extinction coefficients and wavelengths for a subset (pp. 798, 800) | This is a UV-derived kinetic profile under reported pH 7.7 protocols. Methods specifies oxidized biopterin at 260 nm with `Δε = 6527 M⁻¹ cm⁻¹`, but does not list a wavelength/`Δε` for 7,8-dihydrobiopterin. Actual raw slopes, path length, matched blanks, preparation identities, fit covariance and exact uncertainty semantics are not given in the main paper. |
| Product check | 100 µM pterin-6-carboxylate plus 150 nM Arad3529 in 50 mM ammonium bicarbonate for 1 h at 25 °C; filter, then ESI-MS reaction filtrate versus a 100 µM pterin-6-carboxylate sample; reported m/z 206.04 to 207.02, consistent with 2,4-dihydroxypteridine-6-carboxylate (p. 798, Confirmation of Product Formation) | The two m/z values label **different source-defined analyte samples**, substrate versus proposed reaction product. Their observed separation is 0.98 m/z. It is not a measured-versus-theoretical mass error for one ion; ppm error, unique identity, product yield and MS-based rate cannot be calculated. A matched no-enzyme incubation and ion/adduct assignment are not specified here. |

The author interpretation is pterin deaminase activity in Arad3529 and a
possible oxidized-pterin degradation role. The former is supported by in-vitro
kinetics plus the one product check; the organismal pathway remains a proposal
(pp. 800–801). Docking ranks are prediction/selection information, not extra
experimental replicates or A105 activity measurements.

## Paired extraction fields and numerical cells

| Reader/extraction fields with source | Numerical component and calculation | What it evaluates / availability |
| --- | --- | --- |
| Same named Arad3529 molecular construct, with preparation relationship unknown; substrate identity, parameter kind `kcat/Km`, Table 2 values and units, source-conditioned comparison scope | Reported biopterin efficiency `η_O = 1.0 × 10^6 M⁻¹ s⁻¹`; reported 7,8-dihydrobiopterin efficiency `η_R = 9.3 × 10^2 M⁻¹ s⁻¹`. Existing canonical units are `60` and `0.0558 µM⁻¹ min⁻¹`. | Two populated source kinetic parameter cells, not two independent experiments. Both are fitted efficiency estimates. |
| Same pair, explicitly separate substrate assays; pH 7.7 shared but full nonintended condition match not proven; reported-protocol scope | Existing kinetic-sheet `parameter_ratio = η_O/η_R = 100000/93 = 1075.2688172` (dimensionless); `parameter_difference = 999070 M⁻¹ s⁻¹ = 59.9442 µM⁻¹ min⁻¹`; `log_parameter_contrast = ln(100000/93) = 6.980325971817`. | Descriptive nominal oxidized-versus-7,8-dihydro biopterin efficiency contrast. The ratio is one functional-distinction component, not a final confidence or common-condition preference. Ratio, difference and log are dependent transformations of the same two estimates. The written parenthetic Table 2 spreads are retained with **unspecified statistic**, not promoted to SD or SEM. |
| Table 2 `kcat` and `Km` separately, values, units, parenthetic/± notation and fit basis | For biopterin: `kcat = 46 ± 4 s⁻¹`, `Km = 47 ± 9 µM`; for 7,8-dihydrobiopterin: `kcat = 0.090 ± 0.007 s⁻¹`, `Km = 93 ± 13 µM` (p. 800). | Retain as reported numerical parameter cells. They come from the same kinetic fits as efficiency and cannot be added as independent support. The paper does not define whether ± is SD, SEM or fit error or give biological preparation n. |
| Two efficiency estimate sampling units, variance definitions and covariance; source observation model | `Var(log η_O/η_R) = Var(log η_O)+Var(log η_R)−2Cov(log η_O,log η_R)`. | General kinetic-sheet `log_contrast_variance`, standard uncertainty and conditional source-profile score remain **unavailable**: Table 2 parentheses do not provide an applicable log covariance or a known-normal observation model. Do not infer independence from separate rows. |
| Original product-check substrate sample and reaction filtrate with exact source m/z, enzyme/compound/timing, ion identity/adduct, expected exact product m/z, mass calibration | Observed source separation `207.02−206.04 = 0.98 m/z`; prospective same-ion exact-mass error cell `10^6×|m_observed−m_theoretical|/m_theoretical`. | The source separation is a useful **recorded measurement relationship**, not itself a calibrated validity score. The prospective error cell is **unavailable** because theoretical ion/adduct identity, sufficient m/z precision and calibration are absent; never calculate ppm between substrate and product. |
| MS peak areas/standards, matched no-enzyme incubation, recovery and time course for the same pterin-6-carboxylate assay | A possible product-yield or product-to-substrate balance requires calibrated product amount and denominator; a background-corrected rate requires measured enzyme-present minus matched no-enzyme signal. | These numerical validation/effect-isolation components are **unavailable**. The MS experiment supports product plausibility for one substrate, not a quantitative correction factor for every Table 2 kinetic rate. |
| Screen-negative substrate identity, exposure, each assay's source-calibrated detection limit and controls | Conditional activity upper bound would require an established limit, unit conversion, enzyme amount and time/linearity. | The paper's non-detection of dihydrofolate/tetrahydrofolate is reported as `<0.0008 s⁻¹` (p. 799), a **censored `kcat` statement for those substrates**, not zero. Other screened negatives without a numerical limit do not populate a bound. The cited `<0.0008 s⁻¹` cannot be substituted for the matched biopterin/dihydrobiopterin efficiency denominator. |

The current logical A105 worksheet contains a `literature_kinetic_cells` section
that can represent reported protocol parameter contrasts and preserve missing
variance. A source-specific selected reader for this PDF and a product-ion
identity/mass-validation reader were **not implemented by this research case**.
The old synthetic mass-error illustration in
`verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md`
must not be filled with 206.04 and 207.02, because they are different analytes.

## A105 assembly and scientific limits

The kinetic contrast already has explicit arithmetic, `η_O/η_R`. A corrected
raw UV rate would additionally require the assay's measured absorbance slope,
matched blank and possible contaminant contributions, differential extinction
coefficient, optical path length and active-enzyme concentration for that exact assay:
`k_attributed = (dA/dt_sample − dA/dt_blank − dA/dt_contaminant)/(Δε × path_length × active-enzyme concentration)`.
This assumes additive matched background signals. The source supplies a
substrate-specific `Δε` for oxidized biopterin but does not print one for
7,8-dihydrobiopterin; it also lacks other needed operands, so this
equation is a **proposed extraction/calculation mapping**, not a newly populated
corrected rate or an aggregate A105 score. The published fitted kinetic
parameters remain valid as *reported* estimates; missing raw operands mean the
reader cannot independently validate their full calibration/attribution.

Comparability and isolation are different. The biopterin pair uses the same
assayed molecular identity and pH, with substrate redox state as the nominal
intended contrast. The original Methods name 7,8-dihydro-L-biopterin as the
reduced reagent but do not specify the oxidized biopterin stereochemistry;
that relationship requires source clarification. The missing reduced-biopterin optical calibration and
unreported preparation/path-length/blank relationships constrain a
common-condition comparison. Purification and one
substrate-versus-reaction MS comparison help assign an enzymatic/product
relationship, but no quantitative matched no-enzyme signal excludes all
preparation-associated or chemical background. The MS check addresses the UV
readout's **product-identity** weakness for pterin-6-carboxylate only. It is not
independent replication of the biopterin kinetic contrast.

For the future investigation TASK, ask specifically which compounds were
assayed, whether their measurements share the same protein construct,
preparation, controls and kinetic model, what substrate/product optical signal
means, how product identity was checked, and which non-detections have calibrated
limits. Keep those instructions out of the numerical sheet. A model can select
source-grounded meanings (`same/different/unknown/conflicting`); finite readers
and calculators should parse numbers, units, bounds and exact spans. The future
A105 sheet should retain one source-level contribution per physical
measurement, with explicit dependency links among Table 2 parameters and the
complementary MS endpoint. No source-specific matched calibration, preparation
variance, effect-isolation rate, W05 credit or target transfer is established.

## Reset provenance and exact verification

After the original nine-page PDF was read in complete sequential text portions
(lines 1–120, 121–240, 241–360, 361–480 and 481–594), and before the
component interpretation above, I reread without truncated tool output:
the entire original user-supplied 202-line goal attachment; root `AGENTS.md`
(209 lines); `docs/EPISODE_STRUCTURE.md` (1–120, 121–240, 241–351);
`docs/TIME_AWARE_ESTIMATION.md` (1–130, 131–260, 261–384);
`docs/TOOL_KNOWLEDGE.md` (1–120, 121–224); `docs/TASK_AND_STEERING.md`
(1–157); both Task/Steering and Evidence Axis Review amendments;
`VERBATIM_DIRECTION.md` (complete), `VERBATIM_RECOVERY_002.md` (1–110,
111–215); the complete Evidence Axis Library Instructions amendment (1–125,
126–244); the complete earlier numeric review; and the entire 142-line
research `AGENTS.md`. I then read the complete current
`literature_a105_worksheet.py` (1–120, 121–240, 241–360, 361–431),
`literature_experimental_contracts.py` (1–156),
`literature_kinetic_inputs.py` (1–150, 151–300, 301–450, 451–606),
and `literature_kinetic_calculations.py` (1–155, 156–310, 311–461),
then reread the complete root `AGENTS.md` so the latest supplied user
instructions were last. The latest user request is to keep going; none of
those records changes the immutable goal.

Arithmetic was checked with exact `Fraction` operands through `.venv/bin/python`:
efficiency ratio `100000/93`, log ratio `6.980325971817`, canonical values
`60` and `0.0558`, canonical difference `59.9442`, and displayed m/z
separation `0.98`. No selected
LiteratureEpisodes run or product-specific reader test was performed for this
paper.
