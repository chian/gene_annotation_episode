# A106 consolidated handoff for conversation

**A106 now has one coherent numerical proposal from experimental measurements
to a candidate's annotation-support contribution.** It remains a research
proposal; no production scoring policy, reader or prompt was installed.

For one statement and experimental scope, reference `W`, perturbed `K` and
restored `R` are means of the same nonnegative endpoint with a meaningful zero
and the same eligibility denominator. The numerical cells combine as follows:

| Component | Calculation | What it evaluates |
| --- | --- | --- |
| Effect | `theta=(W-K)/(W+K)` | Size/direction of the measured perturbation contrast |
| Restoration | `r=clip(1-abs(R-W)/abs(W-K))` | Return toward the reference phenotype, penalizing overshoot |
| Comparability | `C=product[min(x0,x1)/max(x0,x1)]` over distinct applicable unintended quantity differences | Similarity of measured experimental conditions outside the intended change |
| Isolation | `I=min(clip(1-Bpert/abs(W-K)),clip(1-Brest/abs(R-K)))` | What remains after separate endpoint-scale nuisance bounds for perturbation and rescue |
| Correspondence | `H=M*O` | Measured molecular relationship and scoped system overlap |
| Source effect and row | `a=orientation*theta*r*C*I`; `q=H*a` | Signed contribution before final uncertainty treatment |

`clip` restricts values to [0,1]. Orientation follows the actual statement,
not the observed sign. `M` uses a declared sequence relation
`coverage*identity*required-feature agreement`, a structural relation
`min(two normalized TM scores)*required-feature agreement`, independently
measured interchangeability, or verified target identity. `O=sum min` of actual
source/target context frequencies within the statement's scope; verified same
scoped system gives 1. No intuitive overall relevance grade replaces these
components. Unknown inputs remain unknown. Amount is not activity; intended
depletion is not also a comparability penalty.

Distinct assays of the **same statement** now combine as:

```
Q_statement = sum(H*a) / max(1,sum(H))
F_candidate = min(required statement values)
              or max(genuinely sufficient alternatives)
signed_A106 = nearest-to-zero bound of the joint candidate interval
A106_coordinate = max(0,signed_A106)
```

This uses the same H in numerator and denominator. An exact `H=0` experiment
leaves the result unchanged. A relevant negative result lowers a positive
statement score. Different candidate annotations remain separate; required
claims cannot be replaced by a favorable subset. Shared observations and
correspondence enter one joint uncertainty calculation, followed by one
nearest-to-zero and one positive-part operation. Generic exact extrema for an
H box include its vertices **and** intersections with `sum(H)=1`; shared exact
H variables are collapsed first. Missing nominal inputs leave the coordinate
null unless its value is algebraically identified. A measured interval crossing
zero is different: its conservative coordinate is 0 with point/interval retained.

**Complete synthetic single row:** `W=100,K=20,R=90` events per 100,000 cells;
rescue/reference amount `90/100`; nuisance bounds `Bpert=8,Brest=7`; mapping
`M=(90/100)*(72/90)*(3/4)=.54`; context overlap `.8`. Thus
`theta=2/3,r=.875,C=.9,I=.9,H=.432` and **q=.20412**. For the stipulated
deterministic box `W=[98,102],K=[18,22],R=[88,92],Bpert=[6,10]`, with other
factors exact, the tight shared-variable interval is
**[.181074193548,.224565517241]**. The earlier **[.176418,.233766]** is a
valid looser enclosure of the same input box, not different experimental data.

**Complete synthetic candidate:** a candidate requires promotion of X and Y.
Three paired biological blocks produce means `(W,K,R)=(100,20,90)` for X and
`(80,40,75)` for Y. Their shared H is `.432`; source products are `.4725` and
`.23625`, giving rows `.20412` and `.10206`. A genuinely contrary X assay has
`W=60,K=100,R=70,C=.8,I=1,H=.8`, hence `a=-.15,q=-.12`:

```
Q_X=(.20412-.12)/(.432+.8)=.0682792207792
Q_Y=.10206
F_point=min(Q_X,Q_Y)=.0682792207792
```

The specified synthetic model has one common `N(0,4)` block error across all
six readouts, so mean covariance is `4*J_6/n`. The common 95% error radius is
`1.95996398454*2/sqrt(n)`; deterministic shared H bounds are `[.378,.486]`.
Keeping both dependencies gives candidate interval
**[.0442385231161,.0922521350772]** and conservative coordinate
**.0442385231161**. This conditional model interval is not the probability the
annotation is correct.

| Change to that candidate | Conservative coordinate |
| --- | ---: |
| Before the contrary assay | .0860564901154 |
| After the contrary assay | .0442385231161 |
| Six actual independent synthetic biological blocks instead of three | .0458107392757 |
| Duplicate report, or an added exact-H=0 experiment | Unchanged |

The replication change reduces mean covariance; it does not add source-count
points or shrink the shared transfer bounds. An actual relevant zero can change
the statement denominator. An unavailable result remains a missing operand.

**Necessity is separate.** A statement requiring at least 50% loss from W=100
has `D_required=50,theta_required=1/3`. Observed `K=97`, effect bounds
`[-.02,.05]`, measured effective perturbation `.95` and cancellation isolation
`.9`, with C=H=1, give point **-.271979695431** and interval
**[-.3021,-.24225]**. The candidate coordinate is 0 with the opposition retained.
This challenges that numerical minimum, not every possible role. Without the
actual minimum or relevant perturbation measurement, this score cannot be filled.

The contrasting published components remain limited. The earlier source worker
reported YeaG K116A signal at **.64 of the WT plasmid signal**: that can populate
one conditional amount-comparability cell, not activity or a WT-mixture fraction.
The K426A figure/text discrepancy yields alternative agreement values
**.892857 versus 1**, retained as one unresolved observation. YeaG growth-lag
and long-term survival endpoints remain separate. Cas2's **30/32=.9375**
33-bp spacers and **26/32=.8125** plasmid-derived spacers describe selected
listed entries; they do not provide acquisition-frequency denominators.
Missing calibration, quantitative controls, residual activity, uncertainty and
target correspondence prevent whole published scores. These empirical facts
are inherited from the earlier source inspection, not newly reviewed papers.

The main consequential choice is explicit: one distinct source with
`H=.1,a=.8` gives **.08**, whereas ten distinct such sources give **.8** under
the proposed floor-one normalizer. This is a scoring convention, not a calibrated
transfer law or A105 policy adoption. Other proposed choices are the symmetric
effect, overshoot penalty, C×I product, molecular/system formulas, min/max
candidate meaning and nearest-to-zero uncertainty treatment.

The current deliverable includes exact future reader fields for native data,
controls, source/target relationships, unique observations, covariance, every
row component, statement sums/denominator and candidate result. All readers
remain unimplemented. The 35 read files and inherited receipts were inspected;
the parent receipts contain 176 row assertions and 15 candidate assertions.
This consolidation checked preservation, links, formula/field consistency and
numeric transcription without rerunning those programs or scientific jobs.
Complete synthetic arithmetic and contrasting published subcells are delivered;
complete published candidate totals and new user acceptance are not claimed.
