# Parent-defined native-rate acceptance cases

These are synthetic scientific contracts for reviewing workload 024. They are
not paper measurements, a new sheet or a replacement for the remaining goal.
The existing ten numerical rate components and v1 calculations are the basis.

## Known endpoint contrast, different constructs

The source explicitly reports the same endpoint and protein-mass normalization
basis for two deliberately different constructs. Reference is 12 nmol/min/mg;
test is 3 nmol/min/mg. Actual subject/construct/preparation witnesses remain
separate for each arm. With supported common endpoint/basis, the cells are:

| Component | Value | Unit |
| --- | ---: | --- |
| reference_rate | 0.012 | umol/min/mg |
| test_rate | 0.003 | umol/min/mg |
| rate_difference | 0.009 | umol/min/mg |
| retained_fraction | 0.25 | fraction |
| fractional_decrease | 0.75 | fraction |

This is a source endpoint contrast. It does not isolate the construct effect
from unmeasured preparation differences. Identical constructs are not required
to obtain this contrast, and the contrast does not prove nuisance comparability.

## Explicit uncertainty model, unknown observation IDs

Extend the preceding synthetic source with reported sample SD 2 nmol/min/mg
for the reference and 1 nmol/min/mg for the test, each n=5. The source explicitly
supports the selected independent normal groups model. Physical observation
IDs remain unknown; preparation and construct identities remain separate.

Reference mean SE is `0.002/sqrt(5)` umol/min/mg. Test mean SE is
`0.001/sqrt(5)` umol/min/mg. Conditional difference SE is 0.001 umol/min/mg.
This model does not turn n into biological replication or identify actual
observations. A missing physical ID alone must not erase the supported
conditional calculation. Known reuse of the same observation must defeat a
false independence assertion; repeated labels or source representations must
not supply independent observations.

## Same printed unit, different source definitions

Synthetic reference reports 7 U/mg and defines its endpoint-specific unit as
2 umol of the selected molecular entity per minute. Synthetic test reports
0.1 U/mg with an independently selected definition of 1 umol of that same
entity per minute. Both definitions are actually in the source and bound to
the respective endpoints. Expected rates are 14 and 0.1 umol/min/mg;
difference is 13.9, retained fraction is 1/140, and fractional decrease is
139/140. Raw U/mg ratios cannot cancel unlike source-defined factors.

If both source definitions instead supply 2 umol/min, expected rates are
14 and 0.2, difference 13.8, retained fraction 1/70, and fractional decrease
69/70. The original tokens and both exact definition paths must persist.

Changing the definition's entity to an endpoint-incompatible entity is a
repairable association error, not permission to reuse the scale. An absent
definition preserves raw selected tokens and an unavailable converted rate;
it does not supply a universal U factor.

## Unknown or incompatible meanings

Known individually convertible rates retain their own values and units when
the endpoint or normalization relation is unknown/different. Pair cells stay
unavailable with the actual reason. Equal unit strings or labels do not prove
common experimental meanings. Preserve actual per-arm source bindings through
typed delivery and saved-only reopen.

An amount/time rate versus concentration/time rate remains dimensionally
incompatible even when numerical values happen to match. No reaction volume
or conversion between dimensions may be invented.

## Source limits and lexical completeness

A test reported as greater than 3 nmol/min/mg retains its lower-limit relation
and native token; the threshold cannot become an observed point or zero. The
same applies to upper limits. A comparator outside a narrowly selected witness
still matters. A clipped minus sign, exponent, unit denominator or spread
token must not be accepted as a different scientific number.

Missing uncertainty remains unknown. Untyped spread is retained as untyped.
Any approximate source quantity must retain its qualification; it cannot
become an exact measurement by selecting only the decimal digits.

## Persistence and ordinary communication

One selected native population operation returns one saved result through the
ordinary action path. Source reads, witness validation, unit conversion and
arithmetic inside it do not create extra observations. The requested parent
field may have any caller-owned name. Only its requested component subset is
admitted, including actual native per-arm bindings and unavailable meanings.
Replay and reopen compare with the original saved cells without reading the
primary artifact or rerunning extraction/statistics.
