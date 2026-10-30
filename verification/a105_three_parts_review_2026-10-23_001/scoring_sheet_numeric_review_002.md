# A105 numerical scoring-sheet proposal — review 002

The original sheet example was an evidence record, not the requested numerical
scoring sheet. It remains preserved as history. This proposal corrects that
conceptual error; it has not been adopted as the annotation scoring policy.

## New synthetic inputs

All values here are newly invented test data, not measurements of ybhP and not
additional observations in the earlier one-assay H fixture. This example assumes
the actual target protein was assayed in three independent preparations.
Rates use µM/min under matched conditions.

| Preparation | Candidate-reaction sample rate | Matched blank rate | Net candidate-reaction rate | Net rate for a specified alternative reaction |
| --- | ---: | ---: | ---: | ---: |
| 1 | 1.8 | 0.2 | 1.6 | 0.2 |
| 2 | 2.0 | 0.2 | 1.8 | 0.3 |
| 3 | 2.2 | 0.2 | 2.0 | 0.4 |

Additional synthetic instrument checks: a 10.0 µM calibration standard was
measured as 9.8 µM; product mass expected 100.0000 and observed 100.0002 in the
same mass unit for the declared product/ion. No confidence probability follows
from these checks alone.

## Numerical scoring cells

| Component | Calculation from declared inputs | Populated value | What it evaluates |
| --- | --- | ---: | --- |
| Calibration recovery | 9.8 / 10.0 | 0.98 | Accuracy of the quantitative calibration; closer to 1 means smaller recovery bias |
| Product mass error | abs(100.0002 - 100.0000) / 100.0000 × 10^6 | 2 ppm | Agreement of this measured mass with the proposed product; mass alone does not establish unique chemical identity |
| Sample-to-blank rate ratio | mean(1.8,2.0,2.2) / mean(0.2,0.2,0.2) | 10 | Size of the observed signal relative to measured blank |
| Mean net activity | mean(1.6,1.8,2.0) | 1.8 µM/min | Magnitude of the controlled observed activity, not annotation confidence |
| Independent preparation count | Count the three distinct preparation experiments | 3 | Extent of independent experimental replication; three time points would not count as three preparations |
| Relative between-preparation variability | sample SD(1.6,1.8,2.0) / mean(1.6,1.8,2.0) = 0.2 / 1.8 | 0.1111 (11.11%) | Precision across those preparations; this is not a confidence interval or all sources of uncertainty |
| Candidate-to-alternative activity ratio | mean(1.6,1.8,2.0) / mean(0.2,0.3,0.4) | 6 | Observed selectivity relative to that specific tested alternative under matched conditions |

These are proposed numerical inputs to compilation of an annotation score.
They are not seven independent proofs and are not to be summed unweighted:
some derive from the same experiment and quantities. No aggregate, weights,
confidence conversion, universal assay threshold or adopted credit policy is
defined here. Larger activity is not automatically greater annotation support.

Reader functions must populate these numbers from native assay/standard/
instrument results and preparation identities. Typed literature extraction or
dataset analysis can provide the same inputs. Source names, quotations,
conditions and assay identities support the numbers but are not themselves
scoring cells. A literal citation is not independent experimental replication.

The existing one-assay H fixture cannot populate the extra calibration, mass,
independent-preparation precision or selectivity cells. They remain unknown for
that fixture. H-to-target correspondence also remains unknown there.

Status: proposal and arithmetic check only. The new component readers and
annotation-credit consumption are not implemented by this document. The old
four reader tests do not validate these new components or complete W04/W05.
