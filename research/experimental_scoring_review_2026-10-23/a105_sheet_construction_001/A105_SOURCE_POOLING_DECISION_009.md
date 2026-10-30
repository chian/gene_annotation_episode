# A105: a concrete nonaccumulating source-combination proposal

New source-free mathematical proposal for user judgment. Existing proposals,
permanent records and receipts remain unchanged. No production code, prompt,
reader, scientific run or adopted scoring policy changes. A105 remains
unfinished. This proposal addresses the explicit remaining decision in the
completion review, rather than opening more papers to answer a normative
combination question.

## Scope

Different assayed source molecules can bear on the same declared molecular
statement about the supplied target. Their measured source effects are fitted
first, with shared assay variables, repeats and uncertainty handled in that
source model. The existing uncalibrated correspondence calculation produces
one current signed index D_i for each such source-to-target relationship.
Each index is in [-1,1], with native components and source limits retained.

The proposed rule below concerns those uncalibrated source indexes. It does
not change experimental correction, source likelihood, measured correspondence,
calibrated common-target estimation, or the candidate's required/sufficient
statement reducer. A different endpoint or incompatible target/condition scope
does not enter the same pool. A source can be qualified by a different condition
without being called a contradictory experiment.

## Fully specified proposed rule

For a nonempty set of currently available, coherently scoped source indexes:

    strongest_support = max(0, max_i D_i)
    strongest_opposition = max(0, max_i (-D_i))
    signed_statement_index = strongest_support - strongest_opposition
    support_coordinate = max(0, signed_statement_index)

All coefficients are explicit and equal to one. No allocation vector, roster
denominator, family discount or inferred effective sample size is required.
The result is a conventional balance of the strongest evidence on each side;
it is not a likelihood, probability, calibrated target response or dependence-
corrected estimate. This wording is part of the proposal's meaning.

It deliberately gives no extra support for adding weaker positive evidence from
another homolog, and no extra opposition for weaker negative evidence. A
stronger finding on either side can change the result. This loses information
about independent agreement across sources; the full numerical source rows
remain available. Max pooling also does not correct selection bias from a
large noisy search. Those are limitations to judge, not statistical guarantees.

## Observed evidence and missing evidence

The roster is the scientific evidence actually available for this statement.
It is not claimed to include every homolog or every unperformed experiment.
An absence of observed opposition sets the maximum over that empty observed
subset to zero; this means no opposed index has been received, not proof that
opposition does not exist. An empty entire evidence set returns a null point,
with uninformative bounds and no-data status.

A source already in the declared roster with an unresolved required D_i input
retains its allowed interval; it is not discarded to obtain a favorable point.
For a rectangular set of source-index bounds, the signed expression is
coordinatewise nondecreasing. Evaluate the whole expression once at all lower
endpoints and once at all upper endpoints to get tight bounds for that box.
Retain a null point unless the image is a singleton. Shared constraints must
be preserved; a containing box gives only outer bounds for a coupled set.
Uncertainty about unsearched future evidence is not converted into invented
source rows. Sampling uncertainty and these identification bounds are distinct.

## Repetition and correction

Actual observation identities determine duplicate representations before fitting
each source model. A genuinely independent new assay of the same source can
change its current fitted effect, variance, S and D. It is not a second homolog
vote. Use the current fit, not the largest historical D. A corrected source
finding replaces the corresponding current calculation while its old record
remains historical. Conflicting source versions require explicit resolution or
allowed alternatives; they are not independent supportive observations.

Different homologs are not declared duplicates merely because they are related.
Their rows remain separate. The proposed max rule simply does not add their
indexes. Shared source-to-target uncertainty is not claimed to be estimated by
this rule. Where an applicable common-target response model and joint covariance
exist, the already defined calibrated route fits that model instead. Do not
mix its likelihood with uncalibrated indexes as independent evidence.

## Checked synthetic consequences

The existing synthetic H1/H2 operands are reused, not new observations:

    D_positive = 0.8*tanh(4/2) = 0.7712220640606535
    D_weaker_positive = 0.4*tanh(2/2) = 0.30463766238230594
    D_contrary = -0.30463766238230594

The alternative column uses the earlier fully specified conditional unit-
allocation rule tanh(sum(atanh(D_i))). It is shown to expose the choice,
not described as a calibrated likelihood or accepted policy.

| Available synthetic source indexes | Proposed strongest-side difference | Unit-allocation accumulation |
|---|---:|---:|
| One positive | 0.771222064061 | 0.771222064061 |
| Positive and weaker positive | 0.771222064061 | 0.871181484985 |
| Positive and contrary | 0.466584401678 | 0.609869037957 |
| Ten equal positive homolog indexes plus contrary | 0.466584401678 | 0.999999995150 |
| Positive and equal opposite | 0 | 0 |
| Positive and added zero | 0.771222064061 | 0.771222064061 |

An independent repeat inside a source calculation still matters. In the existing
known-normal synthetic example, source observations 2,2 with variances 1,1 have
S=4. A third independent observation 2 gives S=6. At R=0.8 the source index rises
from 0.771222064061 to 0.796043802949; the strongest-side rule propagates that
increase. It does not treat three publications of the first two observations
as that third independent experiment.

## Exact additional numerical fields

No new observation reader is needed to specify this proposed calculation:

- `current_source_indexes`: the existing coherently scoped D_i values or bounds,
  with canonical observation/source relationships and the declared R basis.
- `strongest_support`, `strongest_opposition`: the two defined observed maxima.
- `signed_statement_index`, `support_coordinate`: the difference and its
  positive part, with the sign retained for steering and subsequent combination.
- `index_bounds`, `coordinate_bounds`, `result_status`: deterministic image
  bounds and null/identified status, preserving missing operands and joint
  constraints.

These are sheet cells and future deterministic calculations, not implemented
readers, prompt content or runtime fields. The candidate-level min/max proposal
would consume the signed statement index, clipping only at its final output.

## Decision still needed

The recommendation is strongest-support minus strongest-opposition for the
uncalibrated multi-homolog route. The explicit tradeoff is that the number of
agreeing homologs does not itself raise support. Adopting it would remove the
unselected allocation table from this route, while preserving calibrated
combination where its actual inputs exist. The user has not yet selected this
proposal. Unanswered questions are not acceptance. Other A105 conventions remain
visible in the existing complete candidate review for the same judgment.
