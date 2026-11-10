# Proposed executable scoring rubrics: A107 and A110

These are explicit **proposals**, not previously approved numerical rules. Native
quantities retain their actual units, method, bounds, conditions and experiment
identity. Literature extraction and dataset analysis supply the same formal
inputs. A paper and its underlying dataset are representations of one experiment,
not two contributions. No current run, scoring formula or controller is changed.

## A107: required partners and coexpression

| Route | Exact numeric rule | Required evidence / limit |
| --- | --- | --- |
| Partner homology | Native E-value and bit score, unchanged | Actual required-partner identity, examined genome, program/search space and original score. No cross-program averaging. |
| Identified partner fraction | identified required partners / required partners | Same fixed, source-defined required set and genome; denominator must be positive. An unexamined partner is unknown, not absent. |
| Coexpressed partner fraction | required partners satisfying the original matched-expression criterion / required partners | Same required set, matched samples/conditions and actual source/analysis criterion. The library invents no correlation or p-value cutoff. |
| Coexpression | Native statistic; -log10 of actual p/q for the stated positive-association test | Preserve effect direction and the actual null/contrast; a nonsignificant result is not negative evidence. A native zero without a bound cannot become an invented finite/infinite log score. |
| Contradiction | competently established missing required partners / required partners | Explicit examined-genome/detection evidence; polarity is opposing. Missing annotation does not qualify. |

Example: a fixed required set of four partners with three identified gives 3/4 =
0.75 identified-partner coverage. If two meet the actual matched-expression
criterion, coexpression coverage is 2/4 = 0.5. These are component-coverage
measurements, not probabilities of function. No average of the two is presumed.

## A110: chemical/resource account

Keep A110 as a separate definition while retaining the unresolved historical
merge record; do not silently erase its content or pretend an unmerge quote was
recovered.

| Proposed grade | Exact nested requirements |
| --- | --- |
| 0 | No higher level is yet warranted; report unknown inputs explicitly. |
| 1 | Actual conversion, species, stoichiometry and system boundary are specified. |
| 2 | Grade1 plus actual element and charge balance. |
| 3 | Grade2 plus explicit electron balance and carrier/resource regeneration. |
| 4 | Grade3 plus an energetic account appropriate to the stated conditions and coupling. |

Element and charge balance are zero-residual calculations, not an LLM opinion.
Electron balance likewise uses the actual donor/acceptor equivalents. Missing
inputs give unknown criteria and an attainable-grade interval. A supported
inconsistency is reported separately with opposing polarity. Native residuals
and conditional Gibbs free energy remain numeric outputs with their original
units/assumptions. Favorable feasibility is not observed intracellular flux.

## Specific function and remaining integration

The descriptors in entries/A107.json and A110.json are consumed by
`evidence_axis_scoring.score_axis`. This publication does not choose an overall
annotation aggregate, cross-method calibration or production caller binding.
Those must be explicit; passing these route tests is not completion of the full
annotation credit path.
