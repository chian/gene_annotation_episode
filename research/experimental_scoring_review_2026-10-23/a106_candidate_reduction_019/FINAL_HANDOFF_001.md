# A106 numerical candidate handoff

**Proposed, not adopted.** This closes the arithmetic gap from scoped
perturbation/restoration rows to one persistent candidate's A106 contribution.
All existing records are preserved, and no production implementation or axis
completion is claimed.

The recommendation is:

    q_g = H_g * a_g
    Q_statement = sum_g q_g / max(1, sum_g H_g)
    F_candidate = min(required statement values)
                  or max(genuinely sufficient alternative statement values)
    signed_A106 = nearest-to-zero bound of the propagated candidate interval
    A106_coordinate = max(0,signed_A106)

a is the existing signed source-effect product with H factored out.
Comparability, isolation and molecular/system correspondence remain separate
measured multipliers. Assays of the same statement share its denominator;
different required statements combine afterward. Missing nominal inputs remain
null unless the output is algebraically identified.

The full synthetic example has one candidate requiring two inferences. Shared
biological measurements give q_A1=0.20412 and q_B1=0.10206, both using one
shared H=0.432. A genuinely contrary assay gives q_A2=-0.12 and H2=0.8:

    Q_A = (0.20412-0.12)/(0.432+0.8)
        = 2103/30800 = 0.06827922077922077
    Q_B = 0.10206
    F_point = min(Q_A,Q_B) = 0.06827922077922077

Shared primitive uncertainty gives the checked candidate interval
[0.04423852311606068,0.09225213507719301]. Its conservative A106 contribution
is **0.04423852311606068**.

| Revision of the same candidate | Conservative contribution |
| --- | ---: |
| Two required inferences, before contrary assay | 0.08605649011535974 |
| Add contrary assay for the first inference | 0.04423852311606068 |
| Increase unique biological blocks from 3 to 6 | 0.04581073927568406 |
| Duplicate a report | Unchanged |
| Add a distinct experiment with exact H=0 | Unchanged |

The actual replication change is covariance of the six-component sample mean
from 4*J_6/3 to 4*J_6/6, under the stated synthetic known-error model. It does
not shrink the shared transfer uncertainty. Distinct competing candidates
retain their own meanings, identities and scores.

The important review choice is explicit: this normalizer avoids the old
1/G mean's dilution by H=0 experiments, but allows several distinct weak
correspondences to accumulate until their total H reaches one. After that it
is an H-weighted mean; weaker positive assays can lower it. This is a proposed
bounded scoring convention, not a calibrated evidence probability. The pending
A105 strongest-side pooling proposal remains unanswered and is not adopted.

Read the complete numerical contract and example together:

- [Candidate numerical contract](A106_CANDIDATE_REDUCTION_001.md)
- [All native operands and full worked example](WORKED_CANDIDATE_001.md)
- [Exact UNIMPLEMENTED reader IO additions](READER_IO_ADDITIONS_001.md)
- [Additive final clarifications](FINAL_CLARIFICATIONS_002.md)
- [Checked arithmetic results](ARITHMETIC_RESULTS_001.json)
- [One-off arithmetic checker](check_arithmetic_001.py)
- [Authority, source coverage and execution limits](AUTHORITY_AND_COVERAGE_001.md)

No new paper or retained paper-specific packet was reviewed. The source-based
row formulas remain the earlier A106 work; the new reduction is mathematical
research with a synthetic complete example. The arithmetic checker passed.
Reader implementation, biological calibration, production consumption, user
adoption and checklist completion remain outside this delivered increment.
