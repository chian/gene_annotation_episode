# A103 numerical scoring sheet — research draft 011

Goal: a usable numerical gene-context sheet whose cells combine into one candidate's A103 coordinate in [0,1]. This draft supplies the formulas, populated examples, exact input/output contract and arithmetic checks. It does not adopt policy, implement readers, change a prompt or finish A103. Overall completion remains 0/10 pending the parent's sequential review and human feedback, beginning with A105.

## What the coordinate evaluates

A103 evaluates a **specified genomic association** that bears on a candidate function: linkage to a named locus or module, conserved arrangement, orientation/distance relation, or a genomic co-occurrence contrast. It does not measure the correctness of every word in an annotation. A RibB neighborhood can support a riboflavin-related role while assigning the same A103 support to several possible reactions. Exact reaction, partner coexpression, organism plausibility, phylogenetic-tree placement and pathway accounting retain their other axes. A phyletic-profile association statistic is not a phylogenetic-tree placement score.

Discovery can start from supplied sequence, a selected file record or bounded snippets. `candidate_id` and `context_questions` are populated only after possible functions emerge. A public name is not required. Raw input boundaries and target-to-locus mapping remain explicit: a sequence without a genomic locus does not yet supply a neighborhood, and a snippet is not a complete gene.

Each context question describes one biological relation and its comparison population. The question set and its weights are explicit in a versioned sheet. They are not rows per paper, database hit, adjacent gene, overlapping window or model iteration. Several tightly linked genes in one operon form one context question unless a genuinely distinct relation is being tested. Questions are not required runtime actions or a prescribed investigation itinerary.

## Numerical cells

`M` = measured/reported; `D` = derived from actual observations; `P` = proposed scoring policy. The formula below is a proposed support index, not a joint probability. A denominator is always in the same counting unit as its numerator.

| Cell | Exact inputs and calculation | Units/range | Meaning and numerical role |
| --- | --- | --- | --- |
| Homolog identification | Program name/version; native bit score, E-value, alignment lengths, coverage, alternatives; retain program values | Native units | Defines which genes were compared. It is separate from whether those genes are neighbors. Do not recalculate sequence support here or multiply a whole A101 coordinate into A103. Ambiguous assignments yield alternative count scenarios. |
| Spatial measurements, M/D | On the same linear contig, for ordered nonoverlapping genes: `gap_bp = right.start − left.end − 1`; overlapping intervals give negative gap using the same endpoint convention; also count intervening gene records and store strands | Signed bp; nonnegative gene count; strand states | Measured endpoints, not confidence. Circular-origin cases require the explicit contig length and selected shortest valid arc. Cross-contig distance is unknown, never infinity. |
| Observed spatial endpoint, D | Evaluate the explicitly supplied predicate on coordinates/orientation; retain `1`, `0` or unknown. Example fixture: same contig, zero intervening genes, same strand, gap ≤300 bp | Binary event | Counts whether a real spatial relation is present. This is not a binary grade of source quality. A quoted “next to” cannot silently supply bp or strand. The 300-bp fixture definition is P, not a universal operon rule or runtime gate. |
| Foreground context frequency `p_js`, D | `k_js / n_js` after deduplication and one declared representative per dependence block, within stratum s | [0,1] | Fraction satisfying the exact endpoint among eligible homolog-containing contexts. `n` is not papers, technical replicates or all genomes in a database. |
| Background context frequency `b_js`, D | `k0_js / n0_js` using the identical endpoint on the specified comparison locus/genome population | [0,1] | Measures how common the same relation is without the tested association. Allows an association contrast rather than rewarding adjacency alone. |
| Measured comparison overlap `C_j`, D | With foreground stratum proportions `a_js = n_js/Σ_s n_js` and background `a0_js = n0_js/Σ_s n0_js`, `m_js = min(a_js,a0_js)` and `C_j = Σ_s m_js = 1 − ½Σ_s |a_js−a0_js|` | [0,1] | Measures the common portion of declared sampling strata. Examples of strata: assembly readability, gene density, search method, broad sampling group. It does not establish absence of unmeasured confounding. |
| Within-stratum association contrast `e_js`, D/P | `g(p,b)` defined below | [−1,1] | Direction and normalized excess/depletion of the spatial endpoint. This evaluates isolation from the measured genomic background, **not causal isolation of protein activity**. |
| Matched-context magnitude `E_j`, D/P | If `C_j>0`, `E_j=Σ_s (m_js/C_j)e_js`; if C=0, E is not estimable and the contribution below is exactly 0 | [−1,1] | Average contrast only on common strata. Comparability C and contrast E remain separately visible. |
| Matched-context contribution `t_j`, P | `C_j E_j = Σ_s m_js e_js`; terms with `m=0` contribute exactly 0 | [−1,1] | Product of measured comparison overlap and normalized association. No empirical operand is invented. |
| Native context contribution `t_j`, M/P | For a documented unit-interval context channel on the requested target/anchor pair: `t_j = d_j s_j`, where `s_j` is the preserved channel score and `d_j` is the declared semantic direction (+1 or −1) | [−1,1] | Uses the actual program score. Direction is the logical bearing of this specified relation; it is not a strength grade. A low score is not negative evidence, and `1−s` is never automatically opposition. |
| Supporting/opposing totals, P | `S=Σ_j w_j max(t_j,0)`; `O=Σ_j w_j max(−t_j,0)`; `w_j≥0`, `Σ w_j=1` | Each [0,1] | Keeps supporting and opposing information visible; equal question weights `1/J` are the proposed normalization unless explicit different policy weights are supplied. |
| Candidate A103 coordinate, P | **`c_A103 = S × (1−O)`** | [0,1] | One bounded coordinate for the retained hypervolume interface. Signed cells, S and O are retained separately. This is not the hypervolume formula or investigation-progress score. |

The normalized contrast is fully defined at the boundaries:

```
g(p,b) = 0                         if p = b
       = (p − b) / (1 − b)         if p > b
       = (p − b) / b               if p < b
```

The branch conditions guarantee a nonzero denominator, including p/b at 0 or 1. A positive maximum is reached when the endpoint occurs in every foreground context but is not universal in background. A negative maximum occurs when it is absent from foreground but occurs in background. Common endpoints yield no enrichment. Neither high frequency nor a low p-value alone becomes the final coordinate.

Native and count routes are two ways to fill a context question, not independent contributions to add for the same evidence. `metric_route` names the selected route and why it answers the question. Preserve any alternative measurements beside it. A new metric/version cannot silently replace history or be selected just because it yields a higher score. Native channel scores and normalized excess indices are not identically calibrated; their combination is explicitly a policy index. A probability interpretation would require additional calibration and is not claimed.

## Filled published-source and current-data examples

| Sheet/example | Numerical cells actually available | Compiled result and limit |
| --- | --- | --- |
| BioY 2007 historical cohort | 150 retained genes; 127 represented genomes; 150/127 = 1.1811023622 genes/genome; approximately 1/3 module-associated, exact numerator unknown | Selected-context frequency is approximate; full matching/background/individual-locus operands absent. Historical-only `t∈[−1,1]`, coordinate bound **[0,1]**, point null. This is not “50 independent positive genomes.” |
| RibK 2008 historical list | Nine explicitly named positive genomes; 9/9=1 among those listed positives | Positive-selection denominator is not all investigated genomes. Historical-only `t∈[−1,1]`, coordinate bound **[0,1]**, point null. No invented background or distance. |
| Current STRING RibK–RibB association | Native `nscore=0.956`, combined score 0.959, text score 0.114; use only 0.956 | One declared question: `S=.956`, `O=0`, **`c=.956`**. It evaluates the specified database pair's contextual association; exact CTP-dependent activity and arbitrary sequence-to-locus mapping are outside this number. |

The historical-paper blanks are missing empirical inputs with explicit bounds. The arithmetic is defined. A new native datum does not retroactively fill a missing 2008 program score. Paper packets give the definitions, source locations and follow-up needed to narrow those bounds.

## Fully filled synthetic cohort example

All values in this section are invented to exercise the sheet; none are measurements of the real papers or ybhP. One candidate has three predeclared context questions, each with weight 1/3. Every count is over unique dependence-block representatives after excluding duplicate representations. In each foreground/background stratum, the denominator is the declared number of eligible representatives. Strata A/B stand for matched sampling conditions, not functional categories.

| Question | Stratum | Foreground k/n | Background k0/n0 | Foreground share a | Background share a0 | Common share m | g(p,b) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 | A | 2/3 | 0/3 | 1/2 | 1/2 | 1/2 | 2/3 |
| Q1 | B | 2/3 | 1/3 | 1/2 | 1/2 | 1/2 | 1/2 |
| Q2 | A | 3/3 | 1/2 | 3/4 | 1/2 | 1/2 | 1 |
| Q2 | B | 0/1 | 0/2 | 1/4 | 1/2 | 1/4 | 0 |
| Q3 | A | 0/2 | 1/2 | 1/2 | 1/2 | 1/2 | −1 |
| Q3 | B | 1/2 | 1/2 | 1/2 | 1/2 | 1/2 | 0 |

Thus Q1: `C1=1`, `E1=t1=7/12`; Q2: `C2=3/4`, `E2=2/3`, `t2=(3/4)(2/3)=1/2`; Q3: `C3=1`, `E3=t3=−1/2`.

```
S = (7/12 + 1/2 + 0) / 3 = 13/36 = 0.3611111111
O = (0 + 0 + 1/2) / 3    = 1/6   = 0.1666666667
c = (13/36)(1 − 1/6)    = 65/216 = 0.3009259259
```

These intermediate 1/2 values are derived fractions/products, not moderate-strength categories. Q2 illustrates the specific comparability loss: only 3/4 of the foreground/background stratum mass overlaps. Q3 keeps an opposing spatial association visible rather than coding all nondetection as zero. With Q3=0 but its slot/weight retained, c becomes 13/36; with its observed negative value c decreases to 65/216. That decrease is not negative scientific-investigation progress.

## Missing information and uncertainty

1. Preserve null native values; never infer zero from omitted/threshold-filtered/top-k output. If a native magnitude is wholly missing, its magnitude lies in [0,1]; a known positive direction gives `t∈[0,1]`, a negative direction gives `t∈[−1,0]`, and unknown direction gives [−1,1]. A returned native score has an exact **computational** value while its biological calibration uncertainty can remain unreported.
2. For an enumerated finite count stratum with `n` planned, `k` observed positives and `u` unresolved members, use `p∈[k/n,(k+u)/n]`. This covers incomplete assemblies, ambiguous homology or unreadable context without calling these negatives. Corresponding background bounds use their own denominator. If n=0, the frequency is unknown [0,1], with the zero-opportunity reason. Unknown total denominators imply [0,1], not a fabricated n.
3. For each stratum, g is nondecreasing in p and nonincreasing in b. Therefore its bound is `[g(p_low,b_high),g(p_high,b_low)]`. Use the fixed declared stratum masses; unresolved members stay in that denominator. If stratum masses themselves are unknown, report `t∈[−1,1]` and the missing field. No division by unknown quantities occurs.
4. Sum weighted bounds for t. The coordinate is nondecreasing in every signed t: compute its lower bound using every t lower endpoint, and its upper bound using every t upper endpoint. These are identification bounds, not confidence intervals. Unknown covariance/dependence can widen but cannot be silently assumed away.
5. Finite-cohort fractions are descriptive. Sampling/generalization uncertainty is separate. Where independent sampling blocks are justified, the sheet can retain a reported confidence interval or a block-resampling interval. None was reported for the historical context counts; do not manufacture binomial confidence intervals from related genomes. No synthetic CI is used as biological validation.
6. A snippet with no unambiguous locus retains a valid supplied-material record and unknown A103 values. Failure to map it is not evidence against a function. No point coordinate is exported for an interval-only sheet unless W05 later explicitly defines such a policy; this draft does not silently choose its lower bound or midpoint.

Synthetic uncertainty check: keep Q1=7/12 and Q3=−1/2, but make Q2 wholly unresolved, `t2∈[−1,1]`. The exact propagated coordinate bounds are **7/72 = 0.0972222222** to **95/216 = 0.4398148148**. The point value is null. All-missing gives [0,1]. Zero questions gives a declared no-evidence state, point null and [0,1]; it does not assert biological zero.

## Dependence, contradiction and nondetection

- Deduplicate on assembly/version/locus pair/endpoint and source-event identity, not numerical equality. A source article, a downloaded table and a database reprint of the same comparison fill the same cells. Duplicate rows leave the arithmetic unchanged.
- Related genomes are sampled as explicitly declared dependence blocks. This draft's default example uses one predeclared representative per block (chosen by assembly completeness, then an immutable identifier tie-break), with all omitted rows retained for sensitivity checks. Do not choose representatives by supporting outcome. A paper's >98% sequence filter is not a proof of genomic independence; absent block information stays unknown.
- Overlapping windows and several pairs from one operon are repeated descriptions of one arrangement. Pool unique observations within that question; do not multiply native neighborhood, same-operon and distance scores from the same genes as independent probabilities. Native score calibration may already use genome conservation: do not add an arbitrary repeat-count bonus.
- A negative observation must satisfy the same homolog search/readability requirements as positives. Unassembled locus, contig-edge uncertainty, missing gene call or below-sensitivity search is unresolved. In a complete eligible genome, failure of the stated spatial relation is a genuine endpoint zero. It affects that relation, not every function associated with the gene.
- Opposing arrangements can produce signed depletion relative to the matched background. A native high score for a logically incompatible arrangement can be negative only if incompatibility with the specific candidate context predicate is documented. Association with another pathway is not automatically mutually exclusive.
- Noisy contradictory source reports about the **same locus** create alternative observation scenarios and bounds. They do not become one supporting plus one opposing independent question. Distinct complete genomes that actually have different arrangements are both observations in the declared population.
- Experimental validation labels, database annotations and curator names are not ground truth for all loci. For a functional inference narrower than context association, retain a separate discrimination statement or measured contrast; do not invent an “exact-function confidence” multiplier. If two candidate reactions predict the same context, their A103 coordinates are equal.
- Sequence, structure and context can share identification inputs. This sheet records those links and claims no statistical independence from A101/A102/A104 or other axes. W05 owns connection to the retained hypervolume; nothing here changes it.

## Proposed choices requiring review, not hidden empirical defaults

The residual normalization g, multiplication by comparison overlap C, question weights and final `S(1−O)` are proposed policy choices. They are completely specified and testable, but are not calibrated biological parameters. Equal weights normalize declared questions, not credibility or publication count. A native score is preserved on its stated scale; interpreting it as a probability of exact function is expressly unsupported. Human feedback can revise these choices additively. The draft is not promoted by passing arithmetic checks.
