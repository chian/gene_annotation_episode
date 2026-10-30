# A103 — genomic arrangement and neighborhood: consolidated numerical sheet

This is one usable research scoring sheet, with exact populating fields and worked calculations. It consolidates draft 011 and the parent's additive correction 003. It proposes an A103 contribution; it does not mark the axis complete, adopt policy, implement readers, or change the ten-axis checklist. The deliverable is the sheet and its calculations, not a paper count.

The contribution evaluates a **specified spatial genomic relation bearing on an emerging functional explanation**. Its scope is proximity, order, orientation, spatial module colocation, and the documented native neighborhood channel. Genome-wide co-distribution, phyletic profiles, partner coexpression and a general presence/absence axis are outside this contract. Exact reaction identity is not established by a neighborhood score. Two candidate reactions predicting the same neighborhood receive the same A103 contribution.

Investigation may start from supplied sequence, selected file contents or snippets. A candidate function and relevant spatial questions may emerge later. A sequence must be mapped to a locus before that locus's neighborhood can be attributed to it; a public searchable name is unnecessary. Unknown or ambiguous mappings remain explicit.

Each question is one biological spatial relation and one comparison population, not one publication, gene hit, sliding window or model turn. Fix the question set, scopes, metric routes and weights before comparing results. Keep unresolved questions in that set. Use one route per question; count and native summaries of the same relation are alternatives, not extra contributions.

## The numerical sheet

`M` means a retained measurement; `D` means arithmetic from those inputs; `P` means a proposed scoring convention. Every probability-like bound below is an identification bound unless explicitly labelled otherwise.

| Numerical cell | Inputs and exact calculation | Units / range | Meaning and role |
| --- | --- | --- | --- |
| Spatial measurement, M/D | For genes ordered left to right on one linear contig, `gap_bp = right.start - left.end - 1` using 1-based closed coordinates; retain strands and number of intervening genes | Signed bp; integer gene count | Describes the arrangement. Overlap has negative gap. Cross-contig distance is unknown. Circular arcs require their length and a stated unwrapping; otherwise the relevant measurement remains unknown. |
| Spatial event, D | Evaluate the specified predicate from those measurements; result `1`, `0`, or unknown | Binary event | A measured relation, not a source-quality grade. Synthetic example: same contig, no intervening genes, same strand, gap ≤300 bp. This cutoff is an example's definition, not a universal operon rule. |
| Foreground frequency `p_js`, D | `k_js / n_js`; incomplete enumerated cohort gives `[k_js/n_js, (k_js+u_js)/n_js]` | Fraction of declared eligible units | `k` positives, `u` unresolved; denominator contains positives, negatives and unresolved opportunities, after duplicate/dependence handling. |
| Background frequency `b_js`, D | `k0_js / n0_js`, with the corresponding incomplete-cohort interval | Same counting unit and endpoint | Frequency under the declared background comparison. It is not the proportion of papers disagreeing. |
| Population shares, D | `a_js = n_js/N_j`, `a0_js = n0_js/N0_j`, where `N_j=Σ n_js`, `N0_j=Σ n0_js` | Fractions | Shares of planned opportunities in stated comparison strata. Unresolved outcomes remain in these denominators. |
| Common mass `m_js` and comparison overlap `C_j`, D | `m_js=min(a_js,a0_js)`; `C_j=Σ m_js = 1 - ½Σ abs(a_js-a0_js)` | [0,1] | Measured overlap in declared sampling conditions, such as assembly readability or gene density. It does not eliminate unmeasured confounding. |
| Within-stratum contrast `g_js`, D/P | `g(p,b)` below | [−1,1] | Excess or depletion of the spatial endpoint relative to its measured background. This is association specificity; it is not causal attribution of protein activity. |
| Matched contrast `E_j`, D/P | If `C_j>0`, `E_j=Σ(m_js*g_js)/C_j` | [−1,1] | Association contrast within the common portion. It remains separate from comparability `C`. |
| Count contribution `t_j`, P | `t_j=Σ(m_js*g_js)=C_j*E_j` when `C_j>0`; corrected zero-mass rules below | [−1,1] | Explicit product of measured comparability and normalized association contrast. |
| Native neighborhood contribution `t_j`, M/P | Retain documented score `s_j∈[0,1]`; `t_j=d_j*s_j`, where `d_j` is +1 or −1 for the sourced logical direction of the specified relation | [−1,1] | Uses the program's neighborhood score. Low score is not opposition; never substitute `1-s`. Direction is logical compatibility, not a subjective strength grade. |
| Supporting total `S`, P | `Σ_j w_j*max(t_j,0)` | [0,1] | Weighted supporting spatial relations. |
| Opposing total `O`, P | `Σ_j w_j*max(-t_j,0)` | [0,1] | Weighted opposing spatial relations, retained separately. |
| A103 coordinate `c`, P | **`c=S*(1-O)`** | [0,1] | Proposed input coordinate for later annotation-credit work. It is neither an exact-function probability nor investigation-progress credit. |

For the count route the event is the candidate-compatible spatial pattern; sign comes from excess/depletion of that event. A relation's absence opposes only a claim that predicts that relation, not every possible activity of the gene. Native negative direction requires documented incompatibility with the specific claim; association with a second pathway does not by itself establish incompatibility.

```
g(p,b) = 0                 if p=b
       = (p-b)/(1-b)       if p>b
       = (p-b)/b           if p<b

w_j >= 0; sum(w_j)=1 for a nonempty question set
proposed equal-question convention: w_j=1/J
```

The branches avoid division by zero: `g(0,0)=g(1,1)=0`, `g(1,0)=1`, `g(0,1)=-1`. Homolog-identification scores retain their original units as identification evidence; no whole A101 or A102 coordinate is multiplied into this sheet. A native neighborhood row has `C` and `E` **not applicable**, rather than measured values of 1.

## Zero, missingness and uncertainty — complete calculation rules

1. If both population totals are known and positive, calculate shares first. **If a stratum has known `m=0`, its weighted term is exactly zero without evaluating its unavailable contrast.** Its `p`, `b` or `g` can still be unknown. If all common masses are zero, `C=0`, `E` is unestimated, `t=0`. This denotes no usable matched comparison, not measured biological absence.
2. If an entire foreground or background population is empty, its share distribution is undefined. Set `C` and `E` unknown and `t` unknown with outer bound [−1,1]. Do not confuse this with two positive-sized, disjoint populations. Unknown population sizes likewise do not create shares or a point estimate.
3. For a finite enumerated stratum, require `positive + negative + unresolved = planned_n`. For `n>0`, use the frequency interval in the table; if `n=0`, frequency is unknown [0,1]. A positive-only published list is not an enumerated full denominator. Approximate fractions remain approximate with unreported precision; they do not become exact integer counts.
4. For known positive common masses, `g` is nondecreasing in `p` and nonincreasing in `b`, so `g_low=g(p_low,b_high)` and `g_high=g(p_high,b_low)`. Then `t_low=Σ m*g_low`, `t_high=Σ m*g_high`, skipping known zero masses. `E` bounds divide by known positive `C`. Unknown shares give conservative outer bounds [−1,1] for `t`; finite enumerated alternative tables can provide tighter bounds by separately evaluating each table.
5. Native missing score with known positive direction gives `t∈[0,1]`; negative direction gives [−1,0]; unknown direction gives [−1,1]. Never turn a filtered-out, top-k-omitted or unmapped result into zero. An exact scored pair's value remains valid for that pair while its transfer to an unmapped supplied target stays unresolved. Evaluate documented possible mappings separately; do not choose the highest score.
6. For `t_j∈[L_j,U_j]`, `S_low=Σw max(L,0)`, `S_high=Σw max(U,0)`, `O_low=Σw max(-U,0)`, `O_high=Σw max(-L,0)`. Because `c` is nondecreasing in each signed `t`, **`c_low=S_low*(1-O_high)` and `c_high=S_high*(1-O_low)`** are valid outer bounds. If consistent scenarios constrain several cells together, evaluate each scenario and take the minimum lower / maximum upper coordinate; do not combine incompatible scenarios as extra evidence. Unknown zero-weight questions contribute zero without resolving their values.
7. Supply a point only when the corresponding numerical quantity is identified. Do not silently choose an interval midpoint or lower endpoint. A nonempty weighted sheet with all unknown contributions has coordinate [0,1], point null. No questions, or no candidate yet, is `no_evidence`, point null and [0,1]; an invalid count/weight has a typed failure and no coordinate. Known zero contribution is a different state.
8. These intervals cover missing-input identification, not sampling/generalization error. Preserve any source-reported interval with its method and unit of replication. No sampling interval or independence is inferred from genome counts. Native `.956` is an exact retained computational value; biological calibration uncertainty remains unreported. This sheet defines no extra uncertainty-discount multiplier.

## Shared evidence, replication, contradiction and nondetection

Deduplicate source-event and assembly/version/locus-pair/predicate identities before counting; equal numbers are not proof of common identity. A paper, its table and a database reprint of the same event fill one observation. Several windows or genes describing one operon relation fill one question. An existing native neighborhood score and its source counts fill alternative routes for that question. The native combined score and non-neighborhood channels remain audit-only.

Declare dependence blocks and choose one representative per block before viewing outcomes, using assembly completeness then an immutable-ID tie-break, or an explicit source rule. Keep excluded members and reasons. The example's 28 representatives demonstrate arithmetic, not biological independence. Source >98% sequence filtering does not establish independent genomes. Repeated representations earn no replication bonus; more unique observations change frequencies and their uncertainty rather than automatically increasing the coordinate. Shared genomes across distinct questions remain documented dependencies; their sum is a fixed descriptive index, not independent probability multiplication.

Conflicting reports about the same locus create alternative consistent observations and bounds. Different arrangements in genuinely distinct surveyed loci are separate observations. A negative spatial event requires an adequately examined locus under the same endpoint definition; contig breaks, incomplete assemblies, ambiguous homologs and insufficient search sensitivity are unresolved. A complete observed failure of the predicted spatial relation is an event zero, whose effect depends on the matched background. Optional proximity cannot be relabelled a universal requirement to manufacture opposition.

## Filled values and choices presented for judgment

The full chains are in [EXAMPLES.md](EXAMPLES.md). Historical BioY supplies 150 retained genes in 127 genomes, `150/127=1.1811023622` genes/genome, and an approximate one-third association; historical RibK supplies nine selected positive genomes, `9/9=1` only within that positive list. Neither provides complete matched-cohort operands. Each historical-only coordinate is null with [0,1] bounds. These are missing empirical inputs, not undefined arithmetic.

The separately dated retained STRING pair `243232.MJ_0055`–`243232.MJ_0056` supplies neighborhood `.956`, not combined `.959`: with one positive question, `S=.956`, `O=0`, **`c=.956`** for that scored pair. The fully synthetic three-question chain gives `t=(7/12,1/2,-1/2)`, `w=(1/3,1/3,1/3)`, `S=13/36`, `O=1/6`, **`c=65/216=.3009259259`**. It has no biological target attribution.

The meaningful choices are residual normalization `g`, overlap multiplication, equal question weights, and `S(1-O)`. Native scores and count contrasts have different calibration meanings. Their permitted weighted combination is expressly a proposed index convention; preserving values does not make those scales interchangeable probabilities. A changed question set, route, reference population or weights defines a new sheet, not a retrospective repricing. These fully specified choices remain open to human judgment without requiring production reader implementation or new paper collection to make the mathematics usable.
