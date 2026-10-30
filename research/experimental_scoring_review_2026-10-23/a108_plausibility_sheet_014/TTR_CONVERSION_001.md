# Tetrathionate primary-to-sheet conversion, after full reset 02

Primary: Winter et al., 2010, [10.1038/nature09415](https://doi.org/10.1038/nature09415),
*Gut inflammation provides a respiratory electron acceptor for Salmonella*.
Main text and Methods Summary were read from Europe PMC XML, all four main
figure captions were read, and Figure 1 was inspected visually. Supplementary
Methods and figures were not accessible in the attempted downloads.

## Experimental definition and source-filled cells

The environmental measurement is tetrathionate in cecal contents of mice four
days after infection. Figure 1E compares mock infection, wild-type Salmonella,
invA spiB Salmonella, and a strain labeled `ttr` in wild-type mice, plus `ttr`
infection in Cybb-deficient mice. These are different host/pathogen states, not
replicate measurements of one unaltered ecological state. The exact `ttr` lesion
for this panel remains unverified because the supplementary strain table was
not read. No purified target/comparison protein is mixed in this measurement.

| Cell | Source and measurement | Value | Role in the sheet |
|---|---|---:|---|
| `bulk_tetrathionate` | Fig. 1E, LC-MS, WT mice infected with `ttr` strain | approximately 3.3 mM | Environmental concentration; approximate reading of the plotted geometric mean |
| `plot_reading_range` | Visual read against the 0–4 mM axis | 3.2–3.4 mM | Analyst display-reading range only; not a biological CI or SEM |
| `independent_units` | Fig. 1 caption | n≥3 | Exact n and animal-level values unavailable; do not pretend n=3 exactly |
| `tested_sufficient_concentration` | Results, in-vitro co-culture | 2.5 mM | A reported concentration sufficient for outgrowth under those conditions; not a minimum required concentration |
| `concentration_comparison` | Derived from the two preceding concentrations | ~3.3/2.5=1.32 | A contextual concentration margin; not a final applicability score |
| `reading_range_margin` | Derived interval arithmetic | [3.2/2.5,3.4/2.5]=[1.28,1.36] | Propagates display-reading uncertainty only |
| `wild_type_residual` | Main text and Fig. 1E | nondetected/not accumulated; numeric LOD unknown | Cannot enter the sheet as zero or imply no production/access |

The graph shows geometric means ± standard error. Individual concentrations,
recovery, quantitative detection limit and uncertainty on the 2.5 mM comparison
are unavailable here. A plotted mean cannot supply the fraction of mice whose
local concentration exceeds an operating requirement.

## Conversion into the user's numerical template

This case supplies actual organism/sample chemistry. Its role in A108 is to
compare local exposure in a specified host/infection state with the contextual
requirements of a possible function. It does not itself establish that all
Salmonella environments contain tetrathionate. Bulk contents are not the same
as the exposure at a cell or enzyme. Accumulation in the respiration-deficient
strain must not be transferred unchanged to respiration-competent bacteria.

Experimental comparability: the gut specimen and broth differ in matrix,
oxygenation, spatial organization and consumption; the genetic changes alter
the context producing/consuming tetrathionate. The denominator of the diagnostic
ratio is the 2.5 mM broth concentration, not WT concentration or protein amount.
There is no measured correction for those context differences in the inspected
material, so the bulk-to-local mapping remains an interval of unknown extent.

Effect isolation is a different question. LC-MS addresses chemical identity and
amount in the specimen; it does not identify one protein as the source of every
measured molecule or establish a direct target contribution. Perturbation,
competitive growth and restoration belong to A106. Their values are not added
to this A108 concentration component. A source's physiological endpoint can
describe a contextual requirement, but its original intervention experiment is
not counted a second time here.

In the current sheet the specimen concentration may populate an exposure cell;
the measured operating domain must be supplied separately. Merely being above
one sufficient test concentration does not authorize all higher concentrations
as a supported domain, since toxicity, other substrates and oxygen could matter.
Consequently the ratio 1.32 is filled, while the specimen's full joint A108
contribution remains a bound, not a fabricated point score. Nondetection with
unknown LOD also leaves a bound; it is not contradiction by itself.

The synthetic complete example supplies the missing paired local exposures,
physical-access observations, measured operating domain and sampling denominator.
Those are explicitly new invented test values, never attributed to this paper.
