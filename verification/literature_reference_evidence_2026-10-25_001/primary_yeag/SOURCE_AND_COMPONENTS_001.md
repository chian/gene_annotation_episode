# YeaG: replacement-complementation case and numerical-sheet consequences

This is a source-research packet, not a runtime reader, completed sheet, adopted
formula or A106 implementation. It follows the current goal's reference-evidence
scope. No target correspondence or combined annotation credit is calculated.
The complete required post-paper authority reset preceded the interpretation
below; actual reads and source custody are recorded in READ_PROVENANCE_001.json.

## Actual experiment and comparison denominators

Figueira et al., Scientific Reports5:17524 (2015), DOI10.1038/srep17524,
PMID26621053, PMCIDPMC4664914. Original full text and supplement were acquired
from official EuropePMC/PMC sources; original Fig3 and Fig6 images were inspected.
Main source: https://www.nature.com/articles/srep17524 and retained original XML.

Fig3 compares separate E. coli ΔyeaG complementation strains: pBAD18-yeaG
encoding tagged WT YeaG, or the K116A/R232A/K426A/Y382Stop variant. The native
yeaG is deleted in these variant backgrounds. This is not a mutant coexpressed
with endogenous WT YeaG. Plasmid complementation is also not a chromosomal
allele swap. The physiological reference, WT with empty pBAD18, is a distinct
arm from ΔyeaG complemented with plasmid-borne WT YeaG. Those WT references must
not be conflated.

TableS2 describes the WT background using both MG1655 and BW25113 designations;
retain that literal source naming rather than silently resolving it externally.
It identifies ΔyeaG780::km (JW1772-1), inducible 6xHis-yeaG, and point/truncation
constructs. Methods reports 37°C,180rpm, Gutnick medium with glucose0.4% and
3mM ammonium for recovery/prestarvation; complementation expression is induced
with arabinose0.1%, with50μg/ml ampicillin where appropriate. The intended
contrast is the YeaG variant; plasmid, induction, genotype and recovery protocol
are relevant matching conditions. Recovery experiments begin with similar
numbers of viable cells according to Methods. That fact does not establish
identical amounts of active protein during every later measurement.

Recovery growth follows sustained24h N starvation and subculture into fresh
medium. Fig3AB measures OD600 growth trajectories; the Results reports failure
to complement. It does not supply an enzyme activity, substrate/product turnover,
ATP hydrolysis rate, or a measured zero catalytic activity for these variants.
The molecular functional interpretation is inferred from designed mutations
and the phenotype. This paper therefore supplies perturbation/restoration
information relevant to later A106, while teaching comparability/attribution
distinctions that the A105 extraction must retain. Growth must not fill A105's
molecular rate q or its activity normalization.

Fig3C is anti-His band signal for tagged YeaG variants compared with the tagged
WT YeaG lane. Its denominator is the WT6xHis-YeaG signal1.0 in the same displayed
blot panel, not measured endogenous WT expression in an unmodified cell. The
figure provides no visible loading-control panel, raw densitometry, quantitative
signal-response calibration, ratio error bars or replicate identities for these
band ratios. The inspected Methods does not supply those missing measurement
relationships. Same epitope, different molecular forms and a truncated band do
not by themselves establish calibrated molecule counts or native active amounts.

## Additive source conflict: K426A

The prose reports relative protein levels64%,48%,100%,96% for K116A,R232A,K426A,
Y382Stop respectively. The printed Fig3C lane labels are1.0,.64,.48,0 on the
left and1.0,1.12,.96,0 on the right. Thus K426A's corresponding displayed signal
is1.12, while prose says100%. Preserve both representations. Do not silently
replace100% with112%, average them, call them independent experiments or change
the historical correction file. SOURCE_CONFLICT_K426A_001.md identifies this
newly inspected discrepancy separately.

## Populated numerical components and what they evaluate

These are source-reported numerical signal components. They are not an overall
experimental reliability score, nor four independent proofs. Derivations are
arithmetic on reported ratios, not new experimental measurements.

| Variant | Prose reported percent /100 | Fig3C printed normalized signal | Derived prose signal difference from1 | Derived prose log signal ratio |
|---|---:|---:|---:|---:|
| K116A | .64 | .64 | −.36 | −.446287102628 |
| R232A | .48 | .48 | −.52 | −.733969175080 |
| K426A | 1.00 | 1.12 | 0 | 0 |
| Y382Stop | .96 | .96 | −.04 | −.040821994520 |

Numerator: variant tagged band signal. Denominator: the corresponding tagged WT
band signal set to1. Dimensionless ratio r describes the measured abundance
proxy. The difference r−1 and log(r) describe that same comparison; they are
alternative arithmetic representations, not additional score multipliers.
For K426A the received representation set is{1,1.12}; log ratio set is
{0,.113328685307}. This is a source-representation conflict, not a confidence
interval or sampling error estimate. No likelihood variance follows from it.

The role in scoring is comparability outside the intended catalytic mutation.
K116A and R232A have lower measured signal, so their failed rescue could be
partly explained by the amount of produced protein. K426A lacks that particular
reduced-signal explanation under either reported representation, while other
weaknesses remain. Y382Stop's near-WT signal does not isolate catalytic loss
because it removes the STK-containing part of the protein as well as changing
its molecular form. A single abundance multiplier cannot encode those effects.

The numerical components combine through an experimentally supported response
model, not by multiplying a failed-rescue label by r. Let L denote recovery lag
measured in minutes, E the calibrated relevant protein amount, and F_WT(E) the
WT dose-response under the same experimental conditions. A proposed matched-
amount loss contrast is e=F_WT(E_mut)−L_mut(E_mut). Its operands and uncertainty
must come from actual dose-response and phenotype measurements. This source
provides the abundance proxy r but not calibrated E or F_WT. The corrected
contrast, its variance and numerical source evidence therefore remain unknown.
A growth lag is not an enzyme rate; A105's (q−g)/(kEh) rate correction is not
applied to OD or lag by substituting similarly named fields.

A simpler unadjusted recovery-restoration comparison would be
I=[L(Δ+WT)−L(Δ+empty)]−[L(Δ+mut)−L(Δ+empty)]
 =L(Δ+WT)−L(Δ+mut).
It measures the observed phenotype difference at the actual expression levels,
not the mutation effect isolated from protein amount. The same empty control
cancels algebraically; its uncertainty must not be counted twice as if the two
contrasts used independent empty controls. Source curves would need explicit
lag extraction/fitting, definition and covariance before filling I or a signed
statistical source score. Failed complementation is not substituted as a
numerical zero effect. The current packet does not digitize those trajectories.

If a later supported normal contrast supplies e and its proper variance V,
S=e|e|/(2V) and proposed tanh(S/2) are defined conditional source components from
the current sheet. No such values are produced here. The point comparisons,
precision, dependence and endpoint meaning must be established first. W05 and
A101/A105 target correspondence remain separate.

## Why arrangement changes interpretation

As an explicitly counterfactual arithmetic illustration, suppose .64 meant the
mutant/WT molecule ratio within one preparation, WT remained present, mutant
had zero activity, and molecular contributions added linearly. Then mutant
fraction=.64/(1+.64)=.390243902439 and WT fraction=1/(1+.64)=.609756097561.
Residual total activity would be.609756097561 under those assumptions, not.64.
This is not the arrangement measured in Fig3, and the paper's separate-strain
band ratio cannot fill the within-cell mixture ratio. The actual deletion-
background experiment is confounded by differing expressed amount; it does not
have the additional endogenous WT activity mixture posited in this illustration.
Other cellular contributors and network effects still complicate attribution.

## Keep the corrected endpoints and uncertainty separate

- Fig3AB recovery growth includes K116A,R232A,K426A,Y382Stop. Its curves use
  SD,n=3. Methods generally describes means from3independent experiments or
  more unless specified otherwise. Independent preparation identities and
  cross-strain pairing/covariance are not given; time points are not repeats.
- Fig3C band ratios have no specified panel-specific sampling uncertainty or n.
  The curve error definition is not borrowed for the blot ratios.
- Fig6A survival uses CFU/ml over5days, error SEM,n=3.
- Fig6B survival includes K426A and Y382Stop, CFU/ml at20min,72h,120h, error SD,n=3.
  It does not contain a K116A survival comparison. Do not attach64% to a fabricated
  K116A survival result or assume Fig3C abundance is a time-resolved concentration
  measurement during5days of starvation.

## Targeted extraction/judgment instructions and remaining measurements

Ask the reader to establish the deletion genotype, the actual complementation
construct, whether WT and mutant proteins coexist, which WT arm is the numerical
denominator, the assay endpoint and culture stage, the literal band ratios and
any source conflict. Ask separately whether a particular amount measurement is
applicable to the phenotype timepoint/condition, whether band signal is calibrated
to molar or active amount, and whether the mutation leaves additional properties
unchanged. Allowed findings are supported, unresolved or conflicting with source
witnesses; these are interpretation states, not numerical quality grades.

Useful complementary measurements would be: calibrated linear-range protein
quantification with a loading denominator and independent preparations; expression
matching or a WT dose-response across the observed variant amounts; direct
molecular assays for the altered catalytic function and relevant structural/
localization/stability effects; and endpoint-specific survival measurements when
survival is the claimed result. These could populate comparability corrections,
attribution and their uncertainty. They are not a mandatory episode itinerary,
not independent-proof bonuses, and not permission to divide lag by band intensity.

The current finite assay graph only accepts concentration-rate q/g/u/v, molar E
and recovery k. Fig3 band ratios/phenotypes cannot fill those physical operands.
A dedicated relative-abundance and restoration-response contract remains needed;
retaining this packet is not a claim that those functions are implemented.

The empty-vector lane printed0 is retained as an image label, not an exact
zero molecule concentration or a quantitative zero functional contribution.
A detection limit/noise model for that label is not supplied.
