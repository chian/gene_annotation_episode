# Source-populated numerical example for review

This is an independently checked example of the proposed sheet, not output
from an implemented production population operation. Values are extracted from
the original Fig6C workbook for WT PARP1 + Nuc165 without HPF1. Context and
actual source selectors are retained in SOURCE_SELECTION_PROPOSAL_001.json and
SOURCE_SELECTOR_MAP_001.json. Root must review source-meaning assignments;
schema/custody checks alone do not establish their scientific adequacy.

| Operand | Original cell | Source value |
| --- | --- | ---: |
| start coordinate | A2 |1s |
| end coordinate | A5 |50s |
| NAD+ start/end | C2/C5 |200 /100µM |
| nicotinamide start/end | D2/D5 |6.5 /101µM |
| free ADPR start/end | B2/B5 |2.8 /13.2µM |

| Derived cell | Exact value | Display | Scoring relevance |
| --- | --- | ---: | --- |
| substrate_loss |100 |100µM |Observed depletion magnitude |
| total_product_gain |189/2 |94.5µM |Observed cleavage-associated product accumulation |
| fate_product_gain |52/5 |10.4µM |Observed free ADPR accumulation |
| chemical_discrepancy |11/2 |5.5µM reaction equivalents |Signed mismatch of substrate loss and total cleavage-product gain |
| chemical_ratio |200/189 |1.0582010582 |Agreement of matched chemical readouts under the declared1:1 reaction scale |
| chemical_relative_discrepancy |11/189 |0.0582010582 |Signed relative mismatch, not a confidence value |
| fate_fraction |104/945 |0.1100529101 |Free ADPR fate relative to total measured cleavage |
| substrate_depletion_fraction |1/2 |0.5 |Substantial source-scale depletion; does not establish an initial-rate regime |
| coordinate_span |49 |49s |Released coordinate spacing, not resolved physical sampling interval |

The source-only physical rate cells remain unavailable because the selected
evidence does not settle the first coordinate's actual sampling-time meaning.
With an explicitly selected timing sensitivity, conditional average NAD+ loss
is6000/49≈122.44898µM/min; nicotinamide gain is810/7≈115.71429µM/min; free ADPR
gain is624/49≈12.73469µM/min. These reside only in conditional_value, not source
rate value. They are not initial rates, Vmax, kcat or active-site-normalized
activity, and none replaces the displayed1s with0s.

Uncertainty and standardized discrepancy cells remain unavailable: this packet
does not supply justified joint covariance for the selected estimators. Source
blank/recovery/error and active-site fraction are unknown. The nominal enzyme
concentration does not establish an active-site count. The eight source values
are supporting readings, not eight independent proofs. Chemical mismatch, ratio
and relative mismatch are dependent transforms. The fate ratio shares their
nicotinamide denominator but addresses a different functional distinction.

Chemical accounting does not isolate PARP1 from all alternative contributors.
This example supplies no quantitative contamination correction, independent
preparation count or target correspondence. Reaction withdrawals also prevent
turning every concentration into cumulative moles by multiplying by the initial
volume. The separate synthetic covariance artifact illustrates uncertainty
arithmetic only; none of its matrix entries is paper data.
