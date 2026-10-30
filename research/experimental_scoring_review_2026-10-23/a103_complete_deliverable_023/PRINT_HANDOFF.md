# A103 content ready for the parent's conversation review

A103 now has one coherent numerical sheet for genomic arrangement and neighborhood. It preserves original context scores and supplies a complete count-based alternative when that is the declared analysis. The broader cooccurrence and phyletic-profile entries from the old field list are excluded from this contract. The sheet can begin from a supplied sequence or snippet; a candidate function and spatial question may emerge during investigation.

For one spatial question, compare the fraction satisfying the same endpoint in the foreground, p, with its background fraction, b. The proposed normalized contrast is:

```
g = (p-b)/(1-b) if p>b; (p-b)/b if p<b; 0 if p=b.
m_s = min(foreground stratum share, background stratum share).
C = sum(m_s); t = sum(m_s*g_s); E = t/C when C>0.
```

C measures overlap in observed sampling conditions; E measures the association contrast within the comparable portion. They remain separate, and t is their product. Known zero m contributes zero without evaluating an unavailable contrast. Positive-sized but disjoint populations therefore give C=0, E unknown, t=0. An entirely empty population gives an unknown contribution because its shares are undefined.

For fixed question weights summing to one:

```
S = sum(w*max(t,0))
O = sum(w*max(-t,0))
A103 contribution = S*(1-O)
```

The full invented dataset has these calculated cells:

| Question | Comparison overlap C | Matched contrast E | Contribution t | Weight |
| --- | ---: | ---: | ---: | ---: |
| Q1 | 1 | 7/12 | 7/12 | 1/3 |
| Q2 | 3/4 | 2/3 | 1/2 | 1/3 |
| Q3 | 1 | −1/2 | −1/2 | 1/3 |

Thus S=13/36, O=1/6 and **A103=65/216=.3009259259**. The fixture reconstructs these counts from 28 distinct selected spatial observations; one repeated representation and one nonselected related member add no evidence. When Q2 is unknown, the point is null and the coordinate is bounded by **[7/72,95/216]=[.0972222222,.4398148148]**. These are missing-input bounds, not confidence intervals.

The published contrasts prevent misleading numerical substitution:

| Evidence | Available numerical cells | What may be concluded numerically |
| --- | --- | --- |
| Historical BioY context survey | 150 retained genes in 127 genomes; 150/127=1.1811023622 genes/genome; approximately one-third module-associated | Redundancy and an approximate association are observed. Exact positive/background denominators are missing; historical coordinate stays null with [0,1]. |
| Historical RibK context list | Nine selected positive genomes; 9/9=1 within that list | This does not establish full-survey prevalence. Historical coordinate stays null with [0,1]. |
| Separately retained STRING RibK–RibB pair | Neighborhood `nscore=.956`; combined `.959` and text `.114` kept outside the calculation | One positive question gives S=.956,O=0, **A103=.956** for that exact scored pair. |

These case values come from prior source reviews; this consolidation did not reread the primary papers or query STRING again. The native `.956` measures its documented association endpoint. The matched-count contrast measures normalized enrichment/depletion. Their combination is a proposed index convention, not a probability of the exact annotation. Neither number is transferred to ybhP or an unmapped new sequence.

Duplicate observations and multiple descriptions of one operon fill the same question. Source conflicts about one locus create alternative scenarios; genuine different loci supply distinct observations. Unreadable sequence context is unresolved, while a complete observed failure of a predicted relation is an actual endpoint zero. The sheet retains supporting and opposing totals instead of converting every nondetection to opposition.

The meaningful policy choices presented for judgment are the normalized residual g, overlap multiplier C, fixed question weights and final S(1−O). All are specified numerically. Source-reported native calibration uncertainty and unrecovered historical cohort operands remain explicit; they do not leave the arithmetic undefined. Exact reader fields now match this restricted scope and correctly distinguish unknown from not-applicable C/E. Reader implementation and W05 annotation-credit wiring remain separate work. No axis completion or human approval is claimed by this handoff.
