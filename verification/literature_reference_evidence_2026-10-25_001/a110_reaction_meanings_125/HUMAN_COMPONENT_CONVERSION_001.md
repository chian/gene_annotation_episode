# Constructed A110 component conversion125

This is a constructed engineering example, not experimental evidence from a paper. Values below are from the original admitted typed return and saved scientific records of the passing ordinary-workflow test.

| Role | Source-supported constructed definition | Prediction (mol/mol) | Basis |
| --- | --- | ---: | --- |
| claim | Balanced reaction model | 1 | conditional_assumption |
| alternative | Alternative bypass model | 0.5 | conditional_assumption |
| alternative | Alternative side reaction | 0.5 | conditional_assumption |
| alternative | Alternative coupled reaction | 0.9 | conditional_assumption |

The alternative whose private key is literally `claim` remains a distinct alternative. Equal 0.5 predictions remain attached to distinct hypotheses. The comparison uses every listed alternative; the result is the existing minimum convention, not an annotation probability.

| Requested component | Original admitted value | Meaning |
| --- | ---: | --- |
| reaction_comparison | -0.4285714285714284 | Minimum of (alternative mean-squared error − claim mean-squared error)/(sum of those errors), conditional on the stated input model |

The private fixture has independent ratio observations 0.7 and 0.9, with claim prediction 1 and alternative predictions 0.5, 0.5, 0.9. The existing calculator gives approximately −3/7; no formula changed.

| Resource | Coefficient | Output/demand definition | Compartment | Period |
| --- | ---: | --- | --- | --- |
| glucose | 1 | Product formation demand | reaction vessel | one-minute assay |
| NADH | 1 | Product formation demand | reaction vessel | one-minute assay |

The existing private resource calculation gives capacity 6 µmol, against demand 10 µmol of P formation. Every coefficient points to that exact demand definition. Supplied versus usable budget meaning remains explicit. The parent requested only reaction_comparison; the resource-capacity cell itself was not returned.

Execution evidence: one selected population operation, one exact semantic receipt, four completed own-action observations, zero model calls, and zero scientific observation/assessment records. The saved return was reconstructed under SQLite mode=ro plus query_only, with source readers, calculators and mutation paths disabled. Scientific labels outside the 24-row working page remain available only through actually received records. Missing possession is displayed as unavailable.
