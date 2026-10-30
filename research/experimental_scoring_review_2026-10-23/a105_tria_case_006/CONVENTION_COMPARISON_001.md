# Consequences for the proposed correspondence convention

Compared after the required full primary-paper authority reset with
`../a105_target_relevance_003/UNCALIBRATED_CORRESPONDENCE_CONVENTION_002.md`.
That document is explicitly a source-free, unaccepted numerical convention;
this comparison neither adopts it nor replaces it. The paper supplies measured
inputs and limitations, not the scoring policy. [Primary source](https://pmc.ncbi.nlm.nih.gov/articles/PMC95154/).

## Which numerical components the paper fills

The worked relationship here is the naturally occurring TriA–AtzA pair. It is
not a relationship to ybhP or to an unspecified new target. No measurements are
invented for a project target. If a later supplied target is different, its own
material must be compared separately.

| Existing convention component | Inspected source input | Numerical result / missing operand |
|---|---|---|
| Raw-score sequence formula `2*S_st/(S_ss+S_tt)` | No compatible pair/self alignment scores are reported | Unknown. Do not put 98, an E-value or residue count into a raw-score operand. |
| Alternative sequence identity formula | Full spans 475 and 475 aa; 9 differing positions; 466 identical positions | `r_identity=466/max(475,475)=0.9810526316`. It is the chosen sequence-family basis, not another independent factor beside a raw-score term. |
| Structural `min(TM_s,TM_t)` or declared RMSD alternative | No experimentally compared structures or native geometric scores in this paper | Unknown. Membership in a structural superfamily is not TM=1. |
| Function-site `matches/declared_sites` | Nine natural differences shown, but no predeclared experimentally characterized site set or single-residue effect measurements | Unknown. Using the nine differences as the denominator would be post hoc and does not identify functional importance. |
| Evolutionary placement support | No tree replicates, placement counts or tested alternative clades | Unknown. A discussion of recent evolution does not populate a bootstrap fraction. |
| System similarity kernel | Some preparation conditions are stated, but no complete source/target assay-condition vectors and no reference covariance/scale | Unknown as a full-system component. Shared labels are not fictitious zero numerical differences. |
| Source directional likelihood index | Specific activities, limits and inhibition percentages are supplied, but ± meanings and sampling covariance are absent; competing endpoint models are not specified | Source S and `B_source=tanh(S/2)` remain unknown. A log activity ratio is not a likelihood ratio. |

For intrinsic chemistry, native-organism system correspondence need not be
declared a required family. For transfer to native physiology, the heterologous
expression/preparation and organism differences matter. The claim's scope
determines which comparisons are relevant; the paper does not mandate all five.

## Arithmetic consequence of the convention

If only the sequence family is observed, its available-component average is

```
R_available = (1 * 0.9810526315789474) / 1
            = 0.9810526315789474
C_target_conventional = 0.9810526315789474 * B_source
```

This is an exact application of the proposed convention's available-modality
rule to a measured correspondence fraction. **C is not filled**, because this
source does not identify B. Setting B=1 just because catalysis was detected, or
manufacturing S from `ln(245/0.01)`, would add an unsupported scoring rule.

As a separately labeled **configuration illustration**, suppose an analyst
declared all five families relevant with equal weight, even though only sequence
is measured. Then the existing proposal gives:

```
observed_weight_fraction = 1/5 = 0.2
R_full_lower = 0.9810526315789474/5 = 0.1962105263157895
R_full_upper = (0.9810526315789474 + 4)/5 = 0.9962105263157894
```

These are identification bounds for an unobserved five-family mean, not
confidence intervals, and they do not fill the other components with zeros or
ones. The single observed family's conditional point remains 0.9810526316.
Declaring all five families relevant is the configuration illustration, not a
fact learned from this paper. There is no numerical completed target score.

This case reveals a real consequence: a very high global correspondence number
coexists with sharply limited transfer of a particular substrate reaction. For
TriA, Table 1's aminoatrazine/atrazine assay contrast exceeds 1700 at the printed
mean and detection threshold, while the proteins remain 466/475 identical.
The two numbers evaluate different questions. The sequence fraction neither
overrides that measured substrate discrimination nor calibrates its strength.
The primary paper also attributes AtzA's deaminase nondetection to earlier work;
the matching AtzA rate matrix was not independently inspected here. Thus this is
not a fabricated fully matched two-enzyme kinetic calibration dataset.

The convention already warns that global similarity can dilute a local
determinant. This paper makes the concern concrete but does not identify the
replacement weights. It does not establish that every protein pair with 98%
identity differs in function, or a general frequency of function conservation
at that identity. One selected counterexample cannot calibrate such a frequency.

## Which coefficients and weights remain unidentified

The pair does not identify sequence-versus-site-versus-structure weights; a
nonlinear mapping from identity to functional conservation; the individual
contribution of any of its nine substitutions; interactions between those
substitutions; a covariance matrix for condition similarity; a target/source
activity-transfer function; or a null/error model for the source assay. Neither
0.981 nor a hypothetical `(475−1)/475` is a function probability.

No engineered mutation data are present. No later mutation paper has been used
to declare a decisive site, to set a site's multiplier, or to supply A105 source
reliability. Causal interpretation of mutation and restoration remains A106.
If A106 later provides site effects, their shared experiment must remain linked
when a site-correspondence component uses them; the same activity is not counted
again as independent A105 evidence.

## Specific sheet consequences for review

1. Keep the source rate profile and its censoring separate from target
   correspondence. Natural protein similarity does not alter observed rates.
2. Retain identity and coverage as measurable inputs. Under the declared
   span-normalized identity convention, multiplying coverage again repeats the
   same denominator and does not gain evidence.
3. Leave function-site correspondence unknown unless the declared denominator
   has an independent mechanistic or experimental basis. Do not select only
   differences and then report 0/9 as a functional match score.
4. Keep assay comparability and effect isolation in distinct numerical cells.
   Shared preparation conditions do not quantify the activity fraction due to
   TriA; partial purification does not establish a fixed penalty.
5. Preserve unknown source-score operands. A completed conventional target
   contribution needs an explicitly justified source evidence index as well
   as the correspondence calculation. That is an unresolved conversion for
   the broader A105 sheet, not a reason to label this paper “high confidence.”

The arithmetic is checked in `arithmetic_checked_001.json`. This is one source's
contribution to completing the user's numerical sheet; it does not settle the
convention or complete any evidence axis.
