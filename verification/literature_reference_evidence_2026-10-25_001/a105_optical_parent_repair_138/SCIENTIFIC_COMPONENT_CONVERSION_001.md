# A105 coupled-assay repair: independently reviewed primary controls

This is a scientific conversion and implementation-progress report, not a goal amendment, adopted scoring policy or completion claim. The full persistent goal remains active. A105 must be adequate before further A106 expansion.

Root independently rendered and read the complete retained original PMC2223550 article, including tables, footnotes, captions and references. The original HTML hash is `318ac6fe96b509815001892dcaa996688c703175c7dedf88b663d99fe9c90bcf`. Original figure images and underlying instrument traces were not inspected. `POST_PAPER_RESET_138_001.json` records root's own subsequent complete authority/sheet/contract reread;135's unfinished reset was not borrowed.

## Actual experimental meaning

The assayed material is the purified native butyryl-CoA dehydrogenase/Etf complex from *Clostridium kluyveri*. Ferredoxin and hydrogenase from *C. pasteurianum* are added to the coupled system. These molecules coexist; they do not replace one another. H2 is the hydrogenase-dependent downstream endpoint used to report ferredoxin reduction. NADH oxidation and TTC reduction are other experimental endpoints. Activity of the complex does not establish sufficiency of its isolated Bcd subunit.

The Table2 H2 protocol uses37C,0.5mL,0.05mg complex,2.5mM NADH,1mM crotonyl-CoA,10uM FAD and, where indicated,50uM ferredoxin and1.6U hydrogenase. The NADH protocol uses25C,1mL,0.01mg complex,0.1mM NADH,0.1mM crotonyl-CoA,5uM FAD and20uM ferredoxin/0.4U hydrogenase. A unit is defined separately as1umol H2 formed/min or1umol NADH oxidized/min. Matching U/mg spelling does not make these the same measured species or protocol.

Crotonyl omission and methyl-viologen addition are intended mechanistic interventions. Neither is a matched no-enzyme optical blank. Native n, sampling variance and covariance are not supplied for these selected table reports; independent preparation count remains unknown. The paper expressly reports preparation variability, reaction lags and rates not always proportional to enzyme amount. Nominal enzyme loading therefore cannot by itself establish common-condition intrinsic activity.

## Paired extraction and numerical sheet contributions

`read_primary_controls_001.py` independently parses the original HTML table and verifies selected tokens. Its successful actual output is `PRIMARY_CONTROL_CONVERSION_001.json`. This is source-derived research arithmetic, not execution of a new production grader or a model-backed investigation.

| Numerical contribution | Required extraction and calculation | Populated result | Bearing on the functional inference |
|---|---|---|---|
| Coupled H2 endpoint with crotonyl | Table2 H2 block, Fd+Hyd, point report5U/mg |5umol H2/min/mg complex | Measured coupled terminal rate under its actual protocol; no automatic rate of an isolated subunit |
| Same endpoint without crotonyl | Same block/conditions, Fd+Hyd minus crotonyl, report<0.01U/mg | Point unknown; upper threshold0.01 with strict comparator | Mechanistic negative control for the intended substrate requirement; not observed zero |
| Crotonyl-dependent H2 difference |5 minus the nonnegative below-limit control |(4.99,5]U/mg | Magnitude of the endpoint's conditional dependence on crotonyl under this protocol |
| Crotonyl omission loss fraction |1-control/reference |(0.998,1] | More than99.8% loss, conditional on the point denominator and nonnegative below-limit control. A numerical control contribution, not a99.8% probability that the annotation is correct |
| NADH response retained with methyl viologen | Same NADH protocol,5/7 |5/7=0.7142857143 | NADH oxidation persists in that protocol despite the added alternate electron acceptor |
| H2 response retained with methyl viologen | Same H2 protocol,0.02/5 |1/250=0.004 | H2 output is strongly suppressed in that protocol |
| Difference between the two retention fractions |5/7-1/250 |1243/1750=0.7102857143 | Describes protocol-qualified response divergence; not a calibrated same-condition coupling efficiency or causal isolation score |
| Common-condition productive coupling fraction and variance | Would require compatible measured consumption/product outputs, stoichiometry, calibration, common conditions and actual uncertainty ownership |Unknown | These differently configured assays cannot supply that numerical correction |

The parenthesized14 in the NADH reference row is the reported37C value, not another independent replicate. It is not substituted into the25C methyl-viologen comparison. Raising the temperature alone would not repair the remaining protocol differences for a cross-endpoint coupling calculation.

## How these numbers belong in the user's template

The control contrast supplies measured functional dependence of a specific coupled endpoint. Its loss fraction and rate difference are two representations of the same measurements, not independent reliability multipliers. If a later explicit measurement model uses the control to isolate a rate, it must use those primitives and their uncertainty once. Subtracting an intended substrate-omission arm as if it were an instrument blank would change the experimental meaning.

The optical conversion `q=-1000*(sample_slope-blank_slope)/(epsilon*path_length)` supplies a NADH-depletion rate when its actual operands and relationships are supported. It cannot turn that rate into productive ferredoxin reduction by changing the label. The paper's reported extinction coefficient6.2mM^-1cm^-1 does not supply absent optical sample/blank slopes or a measured path length. Those raw operands remain unknown for this text/table route.

The existing corrected-activity sheet can use `a=(q-g)*v/(k*E*u)` only when q, contaminating contribution g, quantitative recovery k, molecular amount E and nuisance-condition response u/v have the required actual meanings. Merely assigning this paper's available numbers to those slots would be wrong. In particular, an extinction coefficient is not recovery, a substrate-omission control is not necessarily contaminant activity, mass of a complex is not automatically molar active-site concentration, and a specific activity measured at another protocol is not a nuisance-response calibration.

Thus the assay-specific interpretation must preserve which functional step is measured, which step is inferred through a reporter, which control tests the inference, and what the complementary endpoint does and does not resolve. The finite numerical control components can support a defined source assertion. No generic overall quality number, automatic target transfer or extra independent-evidence count follows from them.

## Concrete remaining A105 work

- Verify the source-reader/typed-sheet path for these mechanistic control domains; this new arithmetic script alone is not a production reader or selected LiteratureEpisodes demonstration.
- Supply numerical reporter-to-function calibration only where an actual compatible experiment supports it. Distinguish unsupported common-condition coupling here from an unimplemented function when such measurements are available elsewhere.
- Establish case-grounded consequences of nuisance amount/condition differences and assay-specific method weaknesses, with explicit source models and numerical components. Existing quantity ratios and arrangement labels alone do not finish those relationships.
- Connect already implemented precision/evidence calculations that are presently unreachable. Audit134 reproduced the kinetic model-source gap;137 owns its finite implementation. The distinct binding-interaction model-source gap remains unfinished.
- Preserve complementary endpoint meaning and shared observations in the eventual common A105 evidence sheet. Do not substitute source/format operation counts for assay coverage or declare adequacy from this one source.

The prior132 completion audits remain preserved as historical, contradicted assessments. They do not establish current A105 adequacy. No final annotation aggregation, controller rule, A106 implementation or original source result was changed by this review.
