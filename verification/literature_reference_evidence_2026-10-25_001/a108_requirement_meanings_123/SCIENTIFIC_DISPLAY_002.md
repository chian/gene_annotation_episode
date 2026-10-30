# Actual constructed A108 return, corrected fixture002

Constructed engineering source and prepared retained JSON only. This is not a primary-paper experiment or automatic native extraction.

The parent actually received selected_point =0.5. The unchanged conditional sheet also gives capability_point=1 for these supplied synthetic domains and relations; no biological capability was inferred from names.


Context operating requirements

| Requirement | Source-supported definition | Entity or substance | Property | Biological setting | Function relationship | Unit basis | Supported domain | Incompatible domain |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Requirement 1 | Glucose concentration requirement | glucose | local concentration | cytosol | carbon supply | mM | [0, 2] | [3, 4] |
| Requirement 2 | Nitrate concentration requirement | nitrate | local concentration | periplasm | electron acceptor availability | mM | [0, 2] | [3, 4] |

Alternative biological routes

| Route | Source-supported definition | Required predicates | Biological setting | Function relationship | Requirement set complete | Joint operating support | Membership source support | Joint-scope source support |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Route 1 | Joint assimilation route | Requirement 1, Requirement 2 | same cell | carbon supply | true | established | The joint route requires cytosolic glucose and periplasmic nitrate in the same cell. | The joint operating domain across both locations was assessed together. |
| Route 2 | Alternative acceptor route | Requirement 2 | periplasm | electron acceptor availability | true | established | The alternative route requires nitrate in the periplasm. | The alternative operating domain was assessed separately. |
