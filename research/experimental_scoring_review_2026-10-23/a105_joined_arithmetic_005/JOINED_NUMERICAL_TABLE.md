# A105 joined arithmetic — synthetic and unadopted

This independently coded research check joins only the supplied numerical proposals. It adopts no scoring formula and completes no sheet. No paper, primary-source packet, reader, prompt, production file or scientific run was inspected or changed.

| Cell | Exact expression | Value | Meaning / units |
| --- | --- | ---: | --- |
| Corrected activity a | (1.2−0.2−0.15)/(1×1×1.25) = 17/25 | 0.680000000000 | min⁻¹ |
| V | 0.0256+0.001156+0.00296225+0.0144+0.004624+0.0625 = 444969/4000000 | 0.111242250000 | min⁻²; each supplied variance contribution once |
| S | a²/(2V) = 924800/444969 | 2.078347030917 | dimensionless, specified comparison |
| B | tanh(S/2) | 0.777561486079 | bounded signed transform, not probability |
| r_sequence | 2×240/(300+320) = 24/31 | 0.774193548387 | normalized supplied sequence score |
| r_structure | min(0.9,0.85) = 17/20 | 0.850000000000 | supplied structure correspondence |
| r_site | 8/10 = 4/5 | 0.800000000000 | supplied site correspondence fraction |
| r_evolution | 85/100 = 17/20 | 0.850000000000 | supplied evolutionary correspondence fraction |
| r_system | exp[−½(7²/100+0.5²/1)] = exp(−37/100) | 0.690734330637 | supplied system similarity transformation |

All rate and protein units use a declared synthetic concentration convention: rates in µM/min and protein in µM. This makes a min⁻¹; no real experimental units are inferred. The six V terms are assumed already on the corrected-activity scale, with covariance accounted for upstream or zero. Their underlying experimental derivations are unavailable.

The model comparison is explicitly hypothetical: nonnegative activity versus fixed zero, evaluated at this positive a and supplied fixed V. The positive-a expression S=a²/(2V) is not a general sign rule for a negative measurement. Swapping the ordered model comparison gives −S, −B and −D. B is neither a probability nor calibrated evidence strength.

The following are competing **unadopted** combinations: R_A=Σr_j/5; R_H=5/Σ[1/(0.1+r_j)]−0.1; D=B×R. The harmonic shape 0.1 and equal family weights are not calibrated. The proposed c=max(0,D) is also unadopted; signed D remains present.

| Available components / quantity | Arithmetic proposal | Shifted harmonic proposal |
| --- | ---: | ---: |
| All five: R | 0.792985575805 | 0.788899482632 |
| All five: signed D | 0.616595042762 | 0.613417854083 |
| All five: proposed c | 0.616595042762 | 0.613417854083 |
| Evolution missing: four-family conditional R | 0.778731969756 | 0.774832970240 |
| Evolution missing: four-family conditional D | 0.605511987661 | 0.602480275803 |
| Evolution missing: four-family conditional proposed c | 0.605511987661 | 0.602480275803 |
| Evolution missing: full five-family R bounds | [0.622985575805, 0.822985575805] | [0.243116702604, 0.812177004175] |
| Evolution missing: full five-family D bounds | [0.484409590129, 0.639921887345] | [0.189038184568, 0.631517558326] |
| Evolution missing: full five-family proposed c bounds | [0.484409590129, 0.639921887345] | [0.189038184568, 0.631517558326] |
| Comparison reversed: all-five signed D | -0.616595042762 | -0.613417854083 |
| Comparison reversed: all-five proposed c | 0.000000000000 | 0.000000000000 |
| Comparison reversed, evolution missing: D bounds | [-0.639921887345, -0.484409590129] | [-0.631517558326, -0.189038184568] |
| Comparison reversed, evolution missing: proposed c bounds | [0.000000000000, 0.000000000000] | [0.000000000000, 0.000000000000] |

The missing-evolution conditional values use the four observed families: R_A,4=Σ_known r/4 and R_H,4=4/Σ_known[1/(0.1+r)]−0.1. They are not estimates of the complete five-family value. The full-five bounds substitute the allowed missing-component endpoints 0 and 1 only to calculate monotone bounds. No missing measurement is entered as zero, no midpoint is supplied, and these are not confidence intervals. For positive B, D and proposed c share these bounds; reversed D bounds are [−B R_upper,−B R_lower] and proposed c becomes [0,0].

The contaminant subtraction addresses isolation of this preparation's activity; the response/recovery/protein corrections address the supplied measurement/comparability adjustments. Those adjusted quantities and their uncertainty enter a and V once. No additional 0.85 attribution multiplier or 0.8 similarity multiplier follows D. The numerical 0.85 structural component and 0.8 site component remain the separately requested correspondence inputs; they are not a second correction of the assay.

The family fractions describe supplied correspondence measurements, not independent experiments. Their denominators and transforms are explicit; pair/self sequence scores must share a scoring convention, structural scores must be comparable, and site/evolution denominators require a defined eligible set in any real sheet. The system squared differences must have the same squared units as 100 and 1. No calibration, cross-family independence or real target relationship is established by this arithmetic fixture.

Checks passed: exact rational activity/variance; independent binary-float recalculation of the complete join; ordered-comparison sign reversal; units invariance (a=0.011333333333 s⁻¹, V=0.000030900625 s⁻² leaves S unchanged); ten exact all-equal harmonic identities; missing-component bounds; same measurement in two representations retains one observation and unchanged V/S; six original variance terms used once; no extra correction multipliers. These checks validate arithmetic only.

`joined_results.json` contains numerical cells, 60-digit calculation forms, exact fractions for rational values, formulas/conditioning, and the complete instruction-read provenance. Transcendental decimals are approximations to the exact expressions above; displayed values are rounded to 12 places. `check_arithmetic.py` uses only the Python standard library and no production modules. Run it with `.venv/bin/python research/experimental_scoring_review_2026-10-23/a105_joined_arithmetic_005/check_arithmetic.py`.
