# Coupled redox assays: primary-source component conversion093

This is a case conversion and implementation record. It does not replace the
fixed pasted goal, adopt scoring policy or add a governing amendment. A105 and
the full literature goal remain incomplete. No new paper was acquired: this
work read the retained primary HTML/text for Li et al., DOI10.1128/JB.01417-07,
PMCID PMC2223550. Primary source and earlier case031 outputs are unchanged.

## Experimental definitions

The preparation is the purified native butyryl-CoA dehydrogenase/Etf complex
from *Clostridium kluyveri* DSM555. The paper identifies Bcd, EtfA and EtfB
subunits by partial amino-acid sequencing; this conversion does not score an
alignment or transfer those findings to another protein. No engineered genotype
or construct boundaries are supplied for these Table2 assays. Genotype remains
unspecified. The whole complex is assayed; the activities do not isolate each
subunit's separate catalytic contribution.

The NADH and H2 assays add ferredoxin and hydrogenase from *C. pasteurianum*.
These molecules coexist with the assayed complex. This is not a mutant replacing
wild type. FAD, substrates and auxiliary molecules remain part of the actual
reaction system. Crotonyl-CoA omission tests that substrate's contribution to
each endpoint. It is not a protein-free blank or a measured contaminating rate.

| Assay | Actual measured endpoint | Table2 conditions | Unit definition |
|---|---|---|---|
| NADH spectrophotometry | NADH oxidation | 1ml,25C,0.1mM NADH,0.1mM crotonyl-CoA,0.01mg complex; indicated Fd/Hyd additions | 1U=1µmol NADH/min |
| TTC spectrophotometry | Artificial acceptor TTC reduction | 1ml,25C,0.2mM NADH,0.1mM crotonyl-CoA,0.4mM TTC,0.01mg complex | 1U=1µmol TTC/min |
| Hydrogenase-coupled gas assay | H2 formation measured by GC | 0.5ml,37C,2.5mM NADH,1mM crotonyl-CoA,0.05mg complex; indicated Fd/Hyd additions | 1U=1µmol H2/min |

Table2 has20 measurement rows and21 reported numbers because one NADH row also
gives the37C value in parentheses. The primary printed marker is retained as
`a`; the separate temperature footnote is labeled`b`. Its content and the Results
identify the parenthetical14U/mg as37C. The code preserves that printed marker
and distinct temperature rather than treating7 and14 as replicates or choosing
the larger activity. All21 are reported summaries, not raw replicate readings.

## Paired extraction fields and numerical cells

The native table heading, mixture label, number/limit and footnotes are retained
with exact original UTF8 byte spans. The explicit mapped TSV has its own source
identity and artifact hash. It does not masquerade as the original HTML.

For each assay the selected complete mixture is the reference r and the selected
omission/mediator mixture is t. The endpoint and normalization must match. The
reader retains source-specific units, actual conditions, count/error-statistic
meaning, and origin. Calculators populate

`difference = r-t`, `retained_fraction = t/r`,
`fractional_decrease = 1-t/r`.

| Crotonyl-CoA omission | Reported r,t in assay-defined µmol/min/mg | Difference r−t | Retained fraction t/r | Fractional decrease |
|---|---|---|---|---|
| NADH oxidation | 7,<.01 | >6.99 | <1/700 | >699/700=.998571428571 |
| TTC reduction | 12,.6 | 11.4 | .05 | .95 |
| H2 formation | 5,<.01 | >4.99 | <.002 | >.998 |

These quantify dependence of each measured endpoint on crotonyl-CoA under that
protocol. They can serve as continuous effect components for that experimental
assertion. They do not establish the probability of the functional assertion.
Strict source limits remain strict through every transformation. These are
images of reported constraints, not confidence intervals. No missing or censored
value becomes zero. No nonnegativity or [0,1] probability clipping is silently
added; a tighter physical parameter domain would be a separately declared model.

The calculator also handles general signed one-sided constraints with an
interval denominator that excludes zero. It preserves open endpoints and
unboundedness. When the denominator admits zero, a single interval cannot
generally represent the ratio image; that ratio is specifically unavailable
while the individual values and difference remain. Actual source uncertainty
is retained separately. Native-span v2 and runtime binding for this additive
v1 table-bound route are still unimplemented.

Seven within-endpoint comparisons were executed, adding FAD omission and methyl
viologen addition for NADH and H2. The latter retain5/7 and.02/5=.004 of their
respective baseline rates. They help expose the weakness of interpreting NADH
depletion alone as ferredoxin reduction. Their different assay protocols prevent
an automatic quantitative cross-assay coupling calculation.

## How these components combine, and what remains unknown

The equation `t=r*(1-fractional_decrease)` explicitly connects the effect
components. They are algebraic views of the same measurements. Multiplying a
rate-derived likelihood by that same derived decrease as another reliability
factor would count its operands again. The three assays remain separate
scientific contributions with their source/dependence relationships; they are
not three independent likelihood factors by default.

Within an assay, the omission contrast keeps the deliberately removed substrate
outside a comparability penalty. The published protocol specifies matching
remaining assay conditions. It supplies neither an empirical correction for
other condition differences nor quantitative preparation-matching uncertainty.
Those numerical corrections remain unknown, not1. The paper explicitly reports
preparation variability, instability, lags and departures from proportionality
between enzyme loading and rate. A per-mg unit is not proof of linearity across
the different loadings used in separate assays.

Sampling counts, SD/SEM/CI, joint covariance and calibration recovery are not
supplied for these Table2 numbers. The original point/statistical calculator
therefore retains unknown source-profile/index cells. The new bound components
preserve additional information without inventing a noise model. No overall
experimental-reliability scalar is populated by this case. Defining and
validating such assay-specific error contributions remains work; missing data
in this paper do not by themselves complete that implementation.

The numerical ratio14/5 is not adopted as a measured reaction stoichiometry.
The two rates share37C but have different NADH/substrate concentrations, volumes,
enzyme loads and endpoints. A same-endpoint contrast request returns the two
individual measured rates with an endpoint-mismatch reason. This does not forbid
an independently specified stoichiometric analysis using appropriate observations.
The paper's completion experiments and its extrapolated fully coupled mechanism
remain separate measured/inferred relationships, not controls that erase those
protocol differences.

## Assay-specific interpretation questions and complementary evidence

The proposed recurring task text is:

> Determine what the reported experiments establish about the assayed complex's
> activity. For each readout, identify the molecule physically measured, the
> auxiliary reactions connecting it to the proposed product, and the molecules
> present in each arm. Distinguish substrate/cofactor omission, mediator addition
> and auxiliary-protein omission from a matched no-reaction background. Preserve
> conditions outside the intended change, preparation identity and units. Select
> the source rates/limits and their actual uncertainties; do not perform the
> arithmetic in the interpretation response. Identify which experiment addresses
> a named alternative explanation and which dependence or limitation remains.

This is a printed case-grounded proposal, not a newly installed model prompt.
A model-facing sheet dump or generic overall-quality question is not supplied.
The proposed constrained meanings include the following separate questions:

| Question | Allowed interpretation meanings | This paper's bearing |
|---|---|---|
| What was measured? | Cofactor depletion; artificial-acceptor reduction; auxiliary-coupled product; direct product measurement; unknown/conflicting | NADH,TTC,H2 differ in measured species and inference chain |
| What subject is isolated? | Purified complex; isolated subunit; crude preparation; unknown/conflicting | Purified complex, with auxiliary molecules present |
| What control relationship applies? | Intended-variable omission; matched no-reaction background; mediator addition; unknown/conflicting | Crotonyl omission is an intended-variable control, not a background subtraction |
| Are other conditions comparable? | Reported matched protocol; explicit additional differences; not established/conflicting | Within-assay protocol matching; cross-assay differences retained |
| Is quantitative error information supplied? | Actual source locations for reported statistics/controls; no applicable report; unknown/conflicting | No Table2 sampling/error-rate operands supplied |

Interpretations need their selected literal source locations. Correct quotations
establish custody, not correctness of the scientific interpretation. Any future
typed episode return must carry these meanings and the requested numerical
components through the ordinary parent-defined form. No such execution is
claimed here.

NADH depletion establishes electron-donor turnover, but alternative electron
destinations remain possible. TTC is an artificial acceptor and cannot alone
establish physiological ferredoxin reduction. The H2 assay tests the reduced-
ferredoxin/hydrogenase chain but inherits its coupling dependence and gas
quantitation limits. GC standard-curve values were not supplied. The reported
MALDI mass change offers a distinct product-identity observation; exact mass
alone does not establish unique chemical identity or an assay error rate.
The purification gel/partial sequencing help identify the preparation but
supply no quantitative purity fraction or isolated-subunit attribution here.

These overlapping experiments retain corroborative value because their
weaknesses differ. No endpoint-based family collapse removes them. A numerical
combination requires a supported relationship/error model, with shared original
measurements and preparations kept distinct from genuinely separate assays.
No assay false-positive/false-negative rate is invented from its modality name.

## Executed scope and limits

The existing mapped-table reader populated21 source records. Seven comparisons
ran through both the original point/statistical calculator and the new bound
calculator. The existing source-bound optical reader extracted the actual
reported coefficient6.2mM^-1cm^-1. Its rate and variance stayed unknown because
sample/blank slopes, path length and covariance are absent. The coefficient is
an optical conversion operand; it is not measured calibration recovery.

The first script attempt encountered a source heading row represented by two
HTML cells with an empty second cell. It stopped before writing output. The
finite parser was corrected to recognize that actual heading structure; all
subsequent assertions passed. This changed no source number or interpretation.

Five dedicated primary-case tests verify all mapped original byte spans,
reproduce the mapped reader output, reconstruct seven bound outputs without
file acquisition, validate the original optical partial with reader/calculator
sentinels, and preserve the cross-endpoint limitation. The focused combined suite
passed187 tests. No model, network acquisition, native episode, typed return,
controller observation, annotation-credit aggregation or computational-biology
software was executed for this case. There are no newly completed assay-specific
graders asserted by these partial components.

## Final numerical representation repair002

The current verified outputs are in `generation_002/`. The initial top-level
JSON/TSV outputs remain historical results from before the following numerical
representation repair. They are not the final reconstruction target.

The new bound calculator now checks selected normalized records against their
retained literal table rows and uses the exact reported decimal token. It does
not open the original source. This preserves small differences between large
printed decimals that round to the same float, and prevents an extremely small
nonzero source limit from becoming an exact-zero constraint. Exact rational
endpoints are serialized without changing Python's global integer-string limit.
Finite nonpoint float bounds round outward so projection cannot tighten an
exact reported constraint. A fully unbounded image is labeled`unbounded`, distinct
from missing input. Point projections retain their exact source rational too.

One intermediate stress test exposed Python's integer-string serialization
limit for a constructed1e-9999 threshold;190 tests passed and that test failed.
The exact-integer serialization was repaired. The final focused suite passed
**192 tests in1.19s**, including the five primary-case tests. The primary paper's
numbers and scientific interpretations did not change. No legacy reader,
calculator or recorded scientific score was rewritten by this repair.
