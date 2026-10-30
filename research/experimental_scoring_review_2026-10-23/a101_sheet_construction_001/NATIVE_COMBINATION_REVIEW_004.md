# Native A101 combination: parent mathematical review 004

This is a numerical scoring proposal for review, not an adopted formula or a
complete A101 sheet. It preserves the original worker's contract, compilation
and synthetic arithmetic. No source measurement is changed and no production
scorer, reader, prompt or scientific run is modified.

## The defect found in the first proposed combination

Parent read the complete native contract, compilation proposal, synthetic
examples, checked-result JSON and parent-review addendum in
`a101_native_score_contract_010/`. Its original synthetic polynomial contains
`-0.0002 * BLAST_bits * HMMER_bits`. Including its function-contrast terms,
its derivative with respect to BLAST bits is `0.065 - 0.0002*HMMER_bits`, and
with respect to HMMER bits is `0.070 - 0.0002*BLAST_bits`.

Thus at 400 bits in the other tool, either stronger native match lowers the
proposed score. No measured relationship justifies that behavior. The original
0.7522493993 example is arithmetically correct but is not selected as a scoring
default. The remedy is not to clip native scores at 325 or 350 bits.

## A finite monotone revision for judging the combination

Retain the original synthetic native inputs and its separate BLAST/HMMER
coefficient scales. Replace the negative product with a declared fixed mixture
of the two algorithm-specific indices. This is a mathematical alternative for
review, not a statistically estimated correction for shared information.

Definitions:

- `b_F`, `b_G`: native BLAST HSP bit scores for a function-grounded reference
  supporting F and a specifically declared different function G, respectively.
- `h_F`, `h_G`: corresponding native HMMER domain bit scores. Their scopes and
  selected references/profiles must be known. A missing alternative is unknown.
- `q`, `r`, `m`: query/reference/profile span fractions from their actual
  distinct denominators; `i`: identical columns / all alignment columns;
  `s`: compatible grounded reference sites / declared relevant site count.

The complete illustrative rule is:

    BLAST_index = 0.025*b_F + 0.040*(b_F - b_G)
    HMMER_index = 0.020*h_F + 0.050*(h_F - h_G)
    z = -3 + 0.5*BLAST_index + 0.5*HMMER_index
           + 0.5*(q + r + m + i + s)
    component = 1/(1 + exp(-z)).

All score coefficients have inverse-bit units; the fractions and remaining
coefficients are dimensionless. The two fixed algorithm weights sum to one.
This is one joint feature calculation over shared sequence evidence, not the
multiplication of two independent confidence probabilities. Repeating a native
result does not create another term. Neither averaging nor omitting the
interaction establishes empirical calibration or resolves unknown dependence.

The numbers are retained or explicitly revised synthetic policy choices. Their
biological scale has not been established. The intercept in particular controls
the baseline; this is not a natural zero-evidence score or a calibrated probability.
An unobserved comparison stays null, not the expression evaluated at invented
zero inputs. The expression is supplied to make the numerical choices reviewable,
not to call this complete because it produces a bounded number.

## Filled example

These are invented arithmetic inputs from the worker's retained fixture.

| Component | Inputs / calculation | Value |
| --- | --- | ---: |
| BLAST native score and contrast | b_F=81.6481474635; b_G=79.7221495839 bits | contrast 1.9259978796 bits |
| HMMER native score and contrast | h_F=60; h_G=64 bits | contrast -4 bits |
| BLAST index | 0.025*81.6481474635 + 0.040*1.9259978796 | 2.1182436018 |
| HMMER index | 0.020*60 + 0.050*(-4) | 1.0000000000 |
| Algorithm mixture | 0.5*2.1182436018 + 0.5*1 | 1.5591218009 |
| Query span q | 236/300 | 0.7866666667 |
| Reference span r | 236/260 | 0.9076923077 |
| Profile span m | 108/120 | 0.9 |
| Identity i | 180/240 | 0.75 |
| Grounded sites s | 3/5, all five assessed | 0.6 |
| Fraction contribution | 0.5*(q+r+m+i+s) | 1.9721794872 |
| Final index z | -3 + 1.5591218009 + 1.9721794872 | 0.5313012881 |
| Proposed bounded component | 1/(1+exp(-z)) | **0.6297865656** |

If instead one of the five sites is unassessed, with three compatible among the
four assessed, `s` is in [0.6,0.8]. The result is an interval
**[0.6297865656,0.6527844667]**, with a null point value. The upper endpoint is not
a confidence limit; it is the result under the unknown site being compatible.

Holding other operands fixed, the revised z increases by 0.0325 per additional
BLAST bit and 0.035 per additional HMMER bit for F. It decreases by 0.020 and
0.025 respectively for a stronger G match. Its monotone logistic map preserves
those directions. No statistically unsupported cross-product can reverse them.

## Limits that still prevent a completed A101 sheet

The case-derived cells remain essential. TriA's 466/475 identity, the QueF-like
domain/pocket/motif distinctions and CodA's source-identification limitations do
not automatically populate this particular two-tool formula. Missing raw scores,
uncertain functional scope or a missing site set are not replaced by the
synthetic inputs. The actual cases must continue to constrain which features
can be combined and for which function.

The contract still needs the final choice of numerical normalization and
weights, combination across several reference groups, complete handling of
required distinct functional regions and contrasting filled real-case outcomes.
Selecting a representative per tool is not a native correction for trying
many references. Repeated or overlapping comparisons do not become independent
evidence; this group component cannot simply be added once per search hit.
BLAST-only and HMMER-only investigations also need a specified subset convention
without silently treating missing tools as zero. No tool is made mandatory.

The original native field definitions remain useful regardless of the final
combination. Parent additionally opened the official NCBI statistics tutorial,
BLAST+ appendix and HMMER 3.4 manual, including the manual's domain/sequence and
independent/conditional E-value distinction. These are tool-documentation reads,
not an additional primary-paper review. No complete reread of all manual pages
is claimed. The exact native documentation and worker inspection receipts remain
in the worker directory.

`check_monotone_native_proposal_004.py` checks this synthetic arithmetic, its
missing-site interval, score-unit conversion and the four score-direction
derivatives at 36 paired settings. It records a separate immutable result in
`monotone_native_parent_arithmetic_004.json`. These checks demonstrate arithmetic
properties only; no biological calibration or production-reader behavior is
established. A101 remains unfinished.
