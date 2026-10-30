# A103: a second published-case-linked numerical example

The missing example is now filled through the existing **native neighborhood route**. A new STRING retrieval for the BioY/BioN reference loci in *Rhodobacter capsulatus* SB1003 supplies `nscore=0.844`. This is a database observation made on 2026-10-24 UTC, linked to Hebbeln et al.'s published biological case; **0.844 was not reported by the 2007 paper**. It does not replace or reconstruct that paper's survey.

## What was investigated

The question is whether neighborhood evidence associates the BioY and BioN loci in the named reference organism, consistent with a shared transport-system role. The selected entities are `272942.RCAP_rcc03249` and `272942.RCAP_rcc03250`. The latter's STRING display name is `cbiQ3`; UniProt explicitly connects `bioN`, `cbiQ3`, the locus, and the same STRING identifier. The identity trace below concerns reference loci. The historical assayed plasmid sequence was not compared to either reference protein.

This is an observational genomic comparison. Mutant/wild-type coexistence, assay rate and causal effect isolation are not its measured variables. The native route has no separately available matched sampling table: `C` and `E` are **not applicable**, not measured ones. Its score measures the documented neighborhood evidence channel; it does not establish the chemistry, obligatory dependence on BioN, physical binding, or causal isolation of transport activity.

## Actual filled sheet cells

`M` = recorded native output; `D` = arithmetic; `P` = the existing sheet's proposed scoring convention. The columns are **two separate one-question sheets**, not two questions to pool across organisms. The RibK comparator is inherited from the parent's checked record and the complete deliverable 023; this worker did not reopen its paper or rerun its query.

| Exact cell / calculation | Existing RibK–RibB example | New BioY–BioN example | Origin / meaning |
| --- | ---: | ---: | --- |
| `native.pair_ids` | `243232.MJ_0055` / `243232.MJ_0056` | `272942.RCAP_rcc03249` / `272942.RCAP_rcc03250` | Exact scored reference entities |
| `native.field_name`, `native.raw_scale` | `nscore`, `unit_interval` | `nscore`, `unit_interval` | M; channel-specific API value |
| `native.raw_value = native.score.point = s` | **0.956 = 239/250** | **0.844 = 211/250** | M; actual numerical scoring operand |
| `native.direction = d` | +1 | +1 | P; each question is compatible neighborhood association, not an intuitive magnitude grade |
| `C`, `E` | not applicable | not applicable | No made-up sampling-overlap inputs |
| `t = d*s` | **239/250 = 0.956** | **211/250 = 0.844** | D/P; native route |
| Fixed `weight = w` | 1 | 1 | P; one question in each example |
| `supporting_total = S = w*max(t,0)` | **0.956** | **0.844** | D/P |
| `opposing_total = O = w*max(-t,0)` | **0** | **0** | D/P; no scored opposing question supplied |
| `coordinate = c = S*(1-O)` | **0.956** | **0.844** | D/P; proposed A103 coordinate for the respective reference pair |
| Combined `score`, **excluded** | 0.959 | 0.999 | M; mixes evidence channels and cannot replace `nscore` |

The native neighborhood difference is `0.956−0.844 = 0.112 = 14/125`. The combined-score difference instead is `0.999−0.959 = 0.040 = 1/25`, reversing the numerical ordering. This is a descriptive comparison of stored values, **not a calibrated cross-species probability comparison or proof that one biological conclusion is more reliable**. It makes the A103 channel boundary consequential with real numbers.

The BioY result's remaining native channels are retained for audit only: `fscore=0`, `pscore=.766`, `ascore=.064`, `escore=.655`, `dscore=.8`, `tscore=.892`. None contributes to the A103 coordinate. In particular, phyletic presence, coexpression and activity evidence do not become genomic-neighborhood scores.

## Unknowns and scope

The exact computational cells have equal lower/upper bounds at their recorded values; the database supplies no biological calibration interval or sampling interval here. Direct versus transferred neighborhood contributions and their source-genome breakdown remain unreported. A missing interval is not zero uncertainty. No independent-replication bonus is inferred.

The new query does not recover historical BioY foreground/background counts, a spatial cutoff or stratum shares. For that **separate historical count-route sheet**, `C∈[0,1]`, `E,t∈[−1,1]`, `c∈[0,1]`, with null points, remain appropriate. An approximate summary is not an exact `50/150` observation table. Reasons and source coverage are in [SOURCE_AND_IDENTITY_TRACE.md](SOURCE_AND_IDENTITY_TRACE.md).

No mapping from an arbitrary supplied sequence, snippet or ybhP to these loci was performed. Consequently **no 0.844 target-annotation coordinate is asserted**. An unmapped target's corresponding coordinate remains point null with the existing outer bound `[0,1]`. The reference-pair result is usable without pretending that target correspondence has been established.

Repeated API responses, the paper's description, STRING aliases and UniProt cross-references do not supply independent observations. The two API responses contain the same pair and are counted once. The alias records identify the subject; they are not extra evidence-strength multipliers. An absent or filtered pair would remain missing, not receive `nscore=0`; here the exact pair was returned.

## Verification and status

`check_arithmetic.py` checks the complete saved mapping, the single returned pair, the BioN alias and STRING cross-links, the two equivalent API rows, raw channel values, proposed one-question compilation and descriptive differences. It writes `arithmetic_receipt.json` and `filled_cells.json`. These are research arithmetic and custody checks, not production readers or biological calibration.

This additive example repairs the missing second empirical scoring operand and supplies a complete native-route calculation. It leaves the existing formulas, permanent records and checklist untouched. The parent owns criterion acceptance and axis/goal completion; the user has not yet judged this addition.
