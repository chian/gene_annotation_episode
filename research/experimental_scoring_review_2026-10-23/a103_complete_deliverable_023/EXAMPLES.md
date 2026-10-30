# A103 filled examples and complete calculation chains

Published facts and the retained native result below are inherited from the worker 011 and parent 001/002/003 reviews. This consolidation inspected the cross-case sheet, source trace, exact fields, arithmetic records and synthetic rows. It did not inspect the primary papers or paper-specific packets again. The source/coverage record states that boundary explicitly.

## Published contrasts — populate what was measured

| Field | BioY historical comparative context | RibK historical positive list |
| --- | --- | --- |
| Observation unit / subject | Retained BioY gene contexts distributed among reported genomes | Genomes explicitly named as positive RibK-neighborhood examples |
| Assayed genotype / construct / coexistence | Not a protein-activity assay; no mutant-versus-WT or coexpression comparison enters this genomic sheet | Same: the context list is separate from that paper's molecular assays |
| Tested relation | Reported association with the BioMN module; complete exact spatial predicate and per-locus data unavailable here | Reported RibK/RibB neighborhood relation; complete coordinates and full eligible survey unavailable here |
| Native quantities, reported | 150 retained genes; 127 genomes; source >98% identity filter; approximately one-third module-associated | Nine explicitly named positive genomes |
| Derived quantity with denominator | `150 genes / 127 genomes = 1.1811023622047243 genes/genome`; 23 excess copies relative to one gene per represented genome | `9 listed positives / 9 listed positives = 1` within the selected list |
| What that ratio evaluates | Copy redundancy in that retained collection, not association confidence | Positive-list composition, not prevalence across all searched genomes |
| Missing operands | Exact positive `k`; full observation/dependence table; matched background and stratum populations; exact spatial quantities | Full investigated denominator and negative examples; background and strata; native historical score; exact spatial quantities |
| Populated scoring cells | `C` unknown [0,1]; `E` unknown [−1,1]; `t` unknown [−1,1] | Same |
| One-question compilation | `S∈[0,1]`, `O∈[0,1]`, `c∈[0,1]`; all point values null | Same |
| Interpretation limit | Absence of an optional neighboring module does not by itself oppose every BioY activity | Context supports a related biological role, not the exact reaction/donor |
| Useful complementary measurement | Per-locus assembly/readability and eligible/background tables would fill the context operands; molecular activity belongs to its own axis | Recover full eligible/negative cohort or carry out separately dated defined spatial analysis; molecular assays cannot fill missing neighborhood denominators |

The `S` and `O` ranges above are dependent: one question cannot simultaneously supply S=1 and O=1. The coordinate bound is obtained from the same signed `t`, not by claiming those endpoints coexist. Approximate one-third is not an exact count of 50/150 or 50 independent positive genomes. The exact 150/127 arithmetic is meaningful but is not inserted as a strength multiplier. Published-source anchors and inherited inspection coverage appear in [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md).

## Separate actual native-program example

The retained current-data example is a STRING 12.5 result for the documented RibK–RibB pair. The source trace reports the API version and pair result; the parent's script independently checked the exact unordered identifiers and score field. This consolidation makes no fresh service call or version assertion about today's live service.

| Input / cell | Filled value | Origin and meaning |
| --- | ---: | --- |
| Exact scored pair | `243232.MJ_0055`, `243232.MJ_0056` | Retained current-data pair, not the annotation target ybhP |
| Selected channel / field / scale | neighborhood / `nscore` / unit interval | Native field definition retained by prior review |
| Native score `s` | 0.956 = 239/250 | Recorded computation, biological calibration interval unreported |
| Combined score, excluded | 0.959 | Mixes channels; not substituted for neighborhood |
| Text score, excluded | 0.114 | Other evidence, not an A103 addition |
| Direction `d`, weight `w` | +1, 1 | Proposed one-question compatible-neighborhood definition |
| C, E | Not applicable | No fabricated comparison-population overlap from the native score |
| `t=d*s` | `1*(239/250)=239/250` | Proposed reuse of preserved native magnitude |
| S, O | `1*max(239/250,0)=239/250`; `1*max(-239/250,0)=0` | Explicit compilation |
| Coordinate | `(239/250)*(1-0)=239/250=.956` | Spatial-association support index for the scored pair |

A score for this pair cannot fill the neighborhood of an unmapped new sequence. The transfer/mapping record is separate; no `.956` value is asserted for ybhP or for arbitrary snippets. The actual native number does not retroactively supply a missing 2008 result, and the proposed final index is not an exact-function probability.

## Fully synthetic data-to-coordinate chain

All rows in the retained [synthetic observation fixture](../a103_numerical_sheet_011/synthetic_observation_rows.json) are invented. The fixture contains 30 rows: 28 selected unique representatives, one repeated representation and one nonselected related member. No source paper or biological target supplied these observations. Q1–Q3 denote three distinct spatial relations with equal fixed weights 1/3. A/B are declared sampling strata.

The predicate is same contig, same strand, zero intervening genes and gap ≤300 bp. For the first foreground row, subject `[1000,1299]`, anchor `[1330,1629]`, both `+`: gap `1330-1299-1=30 bp`, event 1. The third foreground row has anchor start 1802: gap `1802-1299-1=502 bp`, event 0. Every selected fixture row has resolved synthetic identity and a complete observation window. The source-event duplicate is excluded, as is the nonselected member sharing a dependence block. Their exclusion changes no eligible count.

| Q / stratum | Foreground k/n | Background k0/n0 | p | b | a | a0 | m=min(a,a0) | g(p,b) | m*g |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 A | 2/3 | 0/3 | 2/3 | 0 | 1/2 | 1/2 | 1/2 | `(2/3-0)/(1-0)=2/3` | 1/3 |
| Q1 B | 2/3 | 1/3 | 2/3 | 1/3 | 1/2 | 1/2 | 1/2 | `(2/3-1/3)/(1-1/3)=1/2` | 1/4 |
| Q2 A | 3/3 | 1/2 | 1 | 1/2 | 3/4 | 1/2 | 1/2 | `(1-1/2)/(1-1/2)=1` | 1/2 |
| Q2 B | 0/1 | 0/2 | 0 | 0 | 1/4 | 1/2 | 1/4 | 0 | 0 |
| Q3 A | 0/2 | 1/2 | 0 | 1/2 | 1/2 | 1/2 | 1/2 | `(0-1/2)/(1/2)=-1` | −1/2 |
| Q3 B | 1/2 | 1/2 | 1/2 | 1/2 | 1/2 | 1/2 | 1/2 | 0 | 0 |

| Question | N, N0 | C=Σm | t=Σm*g | E=t/C | w | w*t positive | w*t negative magnitude |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 | 6,6 | 1 | `1/3+1/4=7/12` | 7/12 | 1/3 | 7/36 | 0 |
| Q2 | 4,4 | 3/4 | 1/2 | `(1/2)/(3/4)=2/3` | 1/3 | 1/6 | 0 |
| Q3 | 4,4 | 1 | −1/2 | −1/2 | 1/3 | 0 | 1/6 |

```
S = 7/36 + 1/6 + 0 = 13/36 = .3611111111111111
O = 0 + 0 + 1/6 = 1/6 = .1666666666666667
c = (13/36)*(1-1/6) = 65/216 = .3009259259259259
```

Q2 explicitly separates comparison overlap 3/4 from within-comparable-strata contrast 2/3. Q3 makes observed opposition visible. Holding Q3's slot/weight fixed while setting t3=0 gives c=13/36; the observed negative relation decreases it by `13/216=.0601851851851852`. That decrease concerns annotation support; it does not erase the information gained in the investigation.

## Missing and zero-weight boundary examples

| Example, synthetic | Complete calculation | Output and meaning |
| --- | --- | --- |
| Q2 wholly unresolved; Q1 and Q3 unchanged | At t2=−1: `S=7/36`, `O=1/2`, c=7/72. At t2=+1: `S=19/36`, `O=1/6`, c=95/216 | Point null; coordinate **[7/72,95/216]=[.0972222222,.4398148148]** |
| One unresolved member | Foreground n=4,k=2,u=1 gives p∈[1/2,3/4]; background b=1/4. `g_low=(1/2-1/4)/(3/4)=1/3`; `g_high=(3/4-1/4)/(3/4)=2/3` | With C=1, t∈[1/3,2/3]. The unresolved member is not a negative. |
| Disjoint strata, both populations nonempty | A: `(k,n;k0,n0)=(1,1;0,0)`; B: `(0,0;1,1)`. N=N0=1. Common shares both 0 | C=0; each unavailable contrast skipped; E null; t=0; one-question S=O=c=0. No usable common comparison, not biological disproval. |
| Entire background empty | A only: `(1,1;0,0)`. N0=0, background shares undefined | C/E/t points null; one-question c null with [0,1]. Never reuse the disjoint-population zero. |
| Partial overlap | A `(1,2;0,2)`, B `(1,2;0,0)`. N=4,N0=2. A m=1/2,g=1/2; B m=0, contrast skipped | C=1/2; t=1/4; E=1/2; one-question c=1/4 |
| Known zero weight on an unknown question | w=(1,0), t=(.956,unknown) | Second term has zero weight; S=.956,O=0,c=.956. Unknown t is retained without invalid multiplication. |

These examples cover an observed zero, lack of overlap, empty population, missing outcome and irrelevant zero weight without equating their meanings. The new bounded check receipt independently verifies the joins shown here; inherited 44- and 19-check runs are reported separately, without adding them as unique coverage.
