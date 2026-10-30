# A103 native-score inspection — separate current dataset

This is a dated program-output example, not a third case paper and not a reconstruction of either historical paper's scores. The two primary-paper resets preceded this inspection.

Official documentation inspected: [API output fields](https://string-db.org/help/api/), [score/channel FAQ](https://string-db.org/help/faq/), [database schema](https://string-db.org/help/database/), and [getting-started explanations](https://string-db.org/help/getting_started/).

The API distinguishes `nscore` (gene neighborhood) from `score` (combined), and separately reports fusion, phyletic-profile, coexpression, experiment, database and text-mining channels. The FAQ relates neighborhood scoring to intergene nucleotide distances. The database documentation distinguishes direct and transferred neighborhood evidence. Help describes confidence using a KEGG-map association benchmark; that benchmark is not experimental proof of a protein's exact function. The inspected documentation does not supply a version-12.5 target-specific error interval. The generic API version endpoint returned 12.5. API decimal scores differ from downloadable integer scores scaled by 1000. These definitions determine which numbers can enter A103; they do not validate exact molecular activity.

## Actual retrieved cell

`string_ribk_pair.json` retains the exact selected pair, query, timestamp and returned fields:

| Quantity | Actual value | Use |
| --- | ---: | --- |
| `nscore` | 0.956 | The native numerical neighborhood-association cell |
| Combined `score` | 0.959 | Audit only; mixes other channels |
| `tscore` | 0.114 | Audit only; does not enter A103 |
| `fscore`, `pscore`, `ascore`, `escore`, `dscore` | 0 | Retained, not separate opposing evidence |

Mapped pair: `243232.MJ_0055` and `243232.MJ_0056`. The mapping endpoint returned ribB and ribK labels. Labels do not supply functional ground truth or an alignment of an arbitrary newly supplied sequence.

The query returned 36 rows despite two requested proteins and `add_nodes=0`. A second compact retrieval inspected all 36 rows and selected the exact unordered requested pair. No highest-scoring partner was selected. The selected row is complete; the initial 10-row preview omitted it and truncated later channel keys. This was repaired before using any score.

For the scoped predicate “the specified database RibK entity has neighborhood association with the specified RibB entity,” the proposed one-question sheet has signed cell `t = 0.956`, `S = 0.956`, `O = 0`, and `c_A103 = 0.956 × (1 − 0) = 0.956`. This is an annotation-support index based on the returned neighborhood score, **not a 95.6% probability of CTP-dependent catalysis**, nor evidence that an unnamed target is this entity. If the candidate adds that chemical specificity, this coordinate still describes only its RibB-association facet.

The native score already summarizes context evidence. The paper's nine listed neighborhoods and this native score are not independent additions. They occupy one context question; historical paper counts stay visible, while the explicitly selected current native projection supplies the numeric cell. An alternative historical-only sheet remains bounded/unknown. No silent “best score” selection is allowed.

## Calibration and search-space limits

Keep database version, network type, exact channel, query mapping, request cutoff and result limits. `required_score=0` is a retrieval parameter, not a scientific acceptance threshold. An omitted row, an unavailable organism, a truncated query or an unresolved mapping is not an observed native score of zero. A returned zero channel is lack of contribution through that channel, not probability one of functional incompatibility.

The native score's training/calibration population, exact underlying genomes, transferred/direct split and current target-specific validation performance were not recovered from this compact response. This limits biological interpretation. It does not make arithmetic on the actually returned program score undefined. Replacing the score with a calibrated probability of a narrower function requires a corresponding validation dataset; the draft does not invent one. The 0.041 prior in the FAQ's combined-score example is not a default biological confidence or an additional score multiplier here.

The skill used was [life-science-research:string-skill](/home/chia/.codex/plugins/cache/openai-curated-remote/life-science-research/1.0.3/skills/string-skill/SKILL.md). Its `scripts/rest_request.py` executed the mapping, network and version queries. No remote computation job, scientific episode or production reader was launched.
