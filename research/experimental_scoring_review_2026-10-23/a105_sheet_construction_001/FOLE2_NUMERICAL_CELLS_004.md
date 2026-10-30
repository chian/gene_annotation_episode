# A105: FolE2 measured responses and shared-reference cancellation

2026-10-23. Additive conversion after the parent's complete post-paper authority
reread. No new scoring rule, production reader, prompt, policy or scientific run.
Primary source: Sankaran et al., DOI 10.1128/JB.00287-09, PMC2772490. Native
measurements, evaluations of the paper's fitted model and synthetic arithmetic
checks remain distinct.

## Experimental definitions

The assayed enzyme is recombinant **B. subtilis GCYH-IB (FolE2/YciA)** expressed
in E. coli. The activity preparation's exact construct/tag and clone strain are
not specified in the inspected Methods; purification is referred to an earlier
paper, which the parent has not inspected. Do not substitute the N. gonorrhoeae
crystallographic or gel-filtration preparation's identity.

The metal panel compares separate reactions of the same named enzyme, not a
mixture of two comparison proteins. It deliberately changes metal identity AND
concentration. Table 2 reports optimum concentrations, not equal-concentration
tests or metal-binding affinities. The general fluorescence assay uses 100
micromolar GTP and the metal panel uses 2 micromolar protein. Fe(II) additionally
uses anaerobic conditions and a different counterion. These extra differences
are not assigned a zero correction.

The separate substrate-kinetic experiment uses 0.5 micromolar protein, 500
micromolar MnCl2, 1 mM DTT, and GTP from 3 to 50 micromolar. Its fitted response
cannot silently be multiplied by the metal-panel response: Zn-specific kinetic
parameters and the joint metal/substrate response are not supplied. Genetic
growth/complementation findings remain A106.

## Numerical cells

| Cell | Reported operands or declared calculation | Value and meaning |
|---|---|---|
| Mn reference activity | Table 2, Mn(II) at 500 micromolar | 100 relative units, by normalization |
| Zn activity | Table 2, Zn(II) at 50 micromolar | 14 +/- 1 in the same relative units |
| Measured condition-response ratio | 14/100 | **0.14**, Zn50/Mn500 for this enzyme and protocol |
| Reverse response | 100/14 | **7.14285714** |
| Log response | log(14/100) | **-1.96611286** |
| Zn/Fe condition response | 14/75; Fe(II) at 1000 micromolar | **0.18666667**; includes the stated condition differences |
| Fitted apparent kcat | Kinetic Results | **0.0011 per second** |
| Fitted apparent Km | Kinetic Results | **9.87 micromolar** |
| Apparent efficiency | 0.0011/(9.87*10^-6) | **111.44883485 per molar per second** |
| Fitted saturation at 3 micromolar GTP | 3/(9.87+3) | **0.23310023** |
| Fitted saturation at 50 micromolar GTP | 50/(9.87+50) | **0.83514281** |
| Model-evaluated rate at 3 micromolar GTP | 0.5*0.0011*3/(9.87+3)*60 | **0.00769231 micromolar/minute** |
| Model-evaluated rate at 50 micromolar GTP | 0.5*0.0011*50/(9.87+50)*60 | **0.02755971 micromolar/minute** |
| Substrate response, 50 to 3 micromolar | preceding lower/higher rate | **0.27911422** |

The last three rate cells evaluate the reported fitted model within the stated
substrate range. They are not newly measured raw rates. Their common enzyme
amount and kcat cancel in the response ratio. Holding substrate concentrations
fixed, the derivative of its log with respect to Km is

`1/(Km+50) - 1/(Km+3) = -0.06099722151 per micromolar`.

The Km contribution to log-response variance is this derivative squared times
Var(Km). Concentration error and covariance enter separately when known. The
paper does not supply the fitted-parameter covariance, so a variance value is
not invented.

## How the cells combine in the user's sheet

A measured same-molecule condition response r multiplies the appropriate
molecular effect: `activity_condition2 = activity_condition1 * r`. For this
paper's metal normalization, `100*0.14=14` reconstructs the same observed datum;
it is not new independent evidence. In log units the corresponding correction
adds: `log(activity2)=log(activity1)+log(r)`.

When this equation reuses the reference observation, retain its covariance.
Writing M and Z for the original positive Mn and Zn measurements,

`log(M) + [log(Z)-log(M)] = log(Z)`.

The reference error cancels. Treating the source activity and its own derived
ratio as independent would count the reference's uncertainty twice. Equally,
the ratio (Z/M)/(F/M) simplifies to Z/F; the shared Mn measurement cancels.
The two displayed ratios are not independent experiments.

This does not mean a 0.14 activity response is a 0.14 reliability score. With an
exact positive multiplier and a zero-activity comparison, scaling both an
effect a and its standard error by r leaves `a^2/(2*V)` unchanged. It changes
the expected activity magnitude. A nonzero functional boundary or uncertain
response can change the numerical evidence comparison. The comparison must
state which of these questions it evaluates, rather than automatically applying
an additional 0.14 penalty to B.

Experimental comparability remains separate from isolation: the metal protocol
defines a joint condition change; it does not identify any contaminating
protein or chemical-background contribution. No-protein/process blanks,
calibration recovery and protein-attributed activity are not numerically supplied
in the inspected material. No numerical S/B for isolated molecular activity or
an unassayed homolog is derived here. Useful measured responses remain retained.

## Uncertainty, nondetection and correspondence limits

- Table 2 does not define its printed +/- quantity's statistical kind. Fig. 3
  separately describes SD bars and four sets of triplicate assays. Do not
  convert the Table 2 spread into SEM by dividing by sqrt(12), or call twelve
  measurements twelve independent protein preparations.
- Table zeros denote nondetection across tested conditions where the footnote
  says so. Detection limits remain unknown. They are not exact zero rates,
  infinite log ratios or fully specified censored-likelihood observations.
- The post-washing metal/protein measurements do not determine active enzyme
  fraction during an assay with added metal. They cannot divide kcat or become
  an extra isolation weight.
- Reported sequence/structure correspondence retains its actual subject and
  denominator. For example, the paper reports 35% identity between the B.
  subtilis and N. gonorrhoeae proteins but supplies no quantitative calibration
  of their metal-response ratio. Similarity is not such a response multiplier.
- The structural search matches a different-reaction protein over 197 C-alpha
  positions, while the shared core with another same-reaction enzyme spans 94.
  Native coverage is informative but does not by itself establish identical
  molecular activity. No new correspondence grade is inferred here.

## Parent verification

The parent read the complete worker case and handoff/locator correction, cached
primary activity Methods and Table 2, Fig. 3 caption and image, kinetic/metal
Results, and the relevant structural-search/core-comparison paragraphs. PMC
web access returned recaptcha, EuropePMC web failed and its XML API returned
HTTP500; the retained primary HTML/text was used. A broad structural selection
was truncated; the actual comparison paragraphs used here were reread completely.
The full article, supplement, earlier assay/purification paper and raw curves
were not claimed inspected.

After inspection the parent fully reread the mandatory authority set in six
nontruncated groups, including every listed design/amendment/verbatim/template
document, local instructions/assignment, and the current goal last. It then
made this conversion. The worker's seven arithmetic/check groups passed.
`check_fole2_join_004.py` independently checks the parent conversions, gradients,
shared-reference cancellation and the explicitly synthetic scale-invariance
example. Neither checker implements production scoring.
