# A101 component conversion: the retained QueF-like case

This is a primary-source rereview of retained case `seq_queFL_archaeosine`, not a new corpus case. It converts one paper and its own supporting information: Phillips et al., *Diversity of Archaeosine Synthesis in Crenarchaeota*, DOI [10.1021/cb200361w](https://doi.org/10.1021/cb200361w), PMCID PMC3289047. The [supporting PDF](https://ndownloader.figshare.com/files/4192036) belongs to that paper. DOI 10.3390/biom7020036 was not opened. The required complete post-paper authority reread preceded this interpretation; its actual read portions are recorded in `authority_reread_001.json`.

This supplies candidate numerical cells and arithmetic for the user's **scoring sheet**, the second of the three responsibilities. It neither changes investigation prompts nor implements readers. The overall A101 combination remains undecided as assigned. It does not import an A105 formula or turn the experimental expression comparison into an A106 component. No evidence axis is complete.

## Definitions before calculations

| Object or comparison | Exact scope |
| --- | --- |
| Supplied example material | The protein sequence record YP_001055124.1 in Supplemental Data 1, selected as one record. A reader can start with those sequence bytes, without supplying the biological name or an annotation. The published label is retained as provenance, not accepted as its function. |
| Paper's investigated protein | Pcal_0221 from *Pyrobaculum calidifontis* JCM 11548, a member of the eight archaeal QueF-like sequences compared. The supplied record contains **109 amino acids**, counted from its sequence. This is not a whole new annotation target for the running gene investigation. |
| Sequence comparison used to motivate function | Archaeal QueF-like sequences versus bacterial QueF proteins. Bacterial QueF's reported reference reaction is NADPH-dependent reduction of preQ0 to preQ1. The 2012 paper cites earlier work for that activity; that earlier primary study was not opened here. |
| Numerical identity comparison actually reported | The **eight modeled QueF-like proteins versus the C-terminal half of *Vibrio cholerae* QueF**, not a pairwise Pcal_0221-versus-new-target comparison, and not full-length-versus-full-length identity. |
| Reference used for named residue positions | *Bacillus subtilis* QueF; source record NP_389258.1. The paper names Cys55, Asp62, Tyr70 and Glu97. These published coordinates must be retained separately from coordinates counted in the supplied sequence. |
| Protein experimentally characterized in this paper | Pcal_0221 expressed in *E. coli* K-12 MG1655 ΔqueF. This provides a function-bearing reference for later comparisons to a supplied target, with the experimental scope below. The other seven archaeal alignment members are not seven additional activity experiments. |
| Test and control | VDC3368: the ΔqueF background carrying a pBAD24-derived Pcal_0221 expression plasmid; VDC3367: the same ΔqueF background with empty pBAD24. Supplemental Methods call the expression plasmid pGPP358 and later pGP358; preserve that naming inconsistency rather than infer two constructs. |
| Coexistence and changed variable | Native bacterial QueF is deleted in both strains; the test is not a mixture of native QueF and the introduced protein. The intended difference is expression of the archaeal gene. Other host proteins remain, including the pathway and bacterial tRNA-guanine transglycosylase. Protein abundance and a fully sequence-verified recombinant protein product are not supplied. |
| Endpoint that grounds the reference | LC-MS/MS detects archaeosine in test-strain tRNA; analysis of purified tRNA-Asp places the modification at position **34**. This supports a role of expressed Pcal_0221 in archaeosine formation in that heterologous system. It is not a purified-protein substrate-specificity measurement. |
| Precise substrate limitation | The paper leaves **free preQ0 versus preQ0-tRNA** unresolved as the natural substrate. It also does not establish the physiological nitrogen donor through these measurements. The experiment must not be relabeled a direct demonstration of one particular purified-enzyme reaction. |

The sequence selected for the worked case is preserved in `derived_sequence_records.json`. Its bytes are:

```text
MLKVSKSPSLVRLKTRGESVCPISKTVDSFEVSVEYIPRGAVLAIEEFKKMVDSYRGREILHEELAVDLLEKVKAAVNPPYVKVTVKSYYIGVEVEVVAESGGVPPVYI
```

For a future supplied sequence outside this paper, the actual relationship to the characterized Pcal_0221 must be measured. The paper's 16–22% range cannot populate that new comparison. No target-to-itself alignment or invented self score is supplied.

## What the comparison method actually reports

The Bioinformatics Methods name NCBI BLAST tools, ClustalW in SEED or MultiAlign for multiple sequence alignments, Phyre for models, and MultiProt/ESPript for structure-based multisequence comparison. Figure 2C is explicitly a **structure-based** alignment. The paper does not specify a BLAST executable/version, substitution matrix, gap penalties, search-space size or pairwise score output for the reported QueF-like comparison.

The Figure 2C rows comprise eight QueF-like proteins, six unimodular QueF proteins, and the C-terminal regions of seven bimodular QueF proteins. The identity statement accompanies model-versus-crystal-structure comparison to the *V. cholerae* C-terminal domain. Preserve that origin. It is not permission to label the percentage a BLAST percent identity or to claim an independently obtained sequence-only score.

The native numbers are **16–22% sequence identity**, **89–107 C-alpha atoms** in structural superpositions, and **1.5–3.1 Å RMSD**. They are ranges across comparisons. Per-comparison values, their pairing, and the identity denominator are not given. In particular, **89–107 atoms is not an established sequence-alignment length**. RMSD and superposition extent are structural-comparison measurements; retain them as context for the alignment, not additional A101 numerical credit.

## Filled numerical cells and explicit component calculations

Reported values, derived counts, and proposed sheet transformations are distinguished below. None is an annotation probability or an overall relevance grade.

| Proposed cell | Actual operands and calculation | Value | What it evaluates; limits |
| --- | --- | ---: | --- |
| `reported_identity_percent_range` | Copy the reported group range without assigning either endpoint to Pcal_0221 | [16, 22] % | Identity within the reported domain-comparison scope. Exact identical-residue counts, alignment denominator, gaps and per-query mapping remain unknown. |
| `identity_fraction_range` | Proposed unit conversion only: [16/100, 22/100] | [0.16, 0.22] | The same measurement in fractional units, not an additional component to add to the percentage and not a confidence range. |
| `query_length_aa` | Count residues in the selected published sequence, excluding header and whitespace | 109 aa | A denominator available for a later properly defined target-coverage calculation; a length alone does not establish coverage. |
| `reference_length_aa` for the local residue example | Count the full supplied NP_389258.1 sequence | 165 aa | Keeps the reference object explicit; the four-site fraction is not whole-sequence identity. |
| `named_site_identity_fraction` | For the four named mapped sites, sum exact residue matches and divide by the number of evaluated named sites: (1+1+1+1)/4 | **1.000** | Retention of this paper's four specified substrate-pocket residues in Pcal_0221. A descriptive fraction over a deliberately selected site set, not a weighted function score. |
| `intact_QueF_signature_occurrences_query` | Count complete matches to E(S/L)K(S/A)hK(L/Y)(Y/F/W) in the supplied 109-aa record | **0 occurrences** | The particular complete signature is absent from that record. This does not mean that every residue in its local structural counterpart differs, or that NADPH binding has been experimentally disproved. |
| `signature_bearing_sequence_fraction` within the published QueF-like set | Sum the eight record-level presence indicators, then divide by eight supplied full records: (0+0+0+0+0+0+0+0)/8 | **0/8 = 0.000** | A sequence-set description reinforcing the reported family distinction. These are eight related sequence observations, not eight independent functional tests. Do not add this to the query's zero occurrence count as extra evidence. |
| Reference signature check | Exact ESKSLKLY in the supplied B. subtilis sequence, positions 79–86 by one-based supplied-sequence counting | **1 occurrence**, 8 aa | Confirms what the searched signature looks like in the sequence used for site numbering. It does not measure cofactor binding affinity. |

The motif has eight positions. The paper defines `h` only as hydrophobic. To avoid inventing its alphabet, the numerical check used the **less restrictive** pattern `E[SL]K[SA].K[LY][YFW]`, permitting any amino acid at `h`. There are zero matches in each of the eight QueF-like records. Thus the stricter pattern also has zero matches for any hydrophobic subset. A positive hit under this relaxed check would have needed a defined hydrophobic check; none was obtained. This is deterministic checking of supplied source sequences, not a new alignment or homology search.

All zero counts are scoped to the inspected complete records. For an input snippet that omits the relevant region, the absence field must remain unknown. Missing sequence is not observed motif loss.

### Four-site calculation and a coordinate discrepancy

| Named site in main Results | Position counted in supplied B. subtilis sequence | Position counted in supplied Pcal_0221 sequence | Compared residues | Match term |
| --- | ---: | ---: | --- | ---: |
| Cys55 | 56 | 21 | C / C | 1 |
| Asp62 | 63 | 28 | D / D | 1 |
| Tyr70 | 71 | 36 | Y / Y | 1 |
| Glu97 | 98 | 63 | E / E | 1 |

Figure 2C supplies the mapped columns. Supplemental Data 1 supplies the unaligned sequence bytes. The source's B. subtilis site numbering differs by one from counting its supplied sequence from the initial methionine. The initial arithmetic diagnostic caught this; blindly using 55/62/70/97 on those bytes failed. **The origin of the offset is not established here.** It might reflect a numbering convention, but methionine processing or a particular construct must not be asserted without evidence. Keep both coordinate systems. See `arithmetic_correction_001.md`.

The manuscript says the four sites are conserved across the eight QueF-like proteins. The product 4 × 8 = **32 named-site observations** describes that statement's scope; it is not 32 independent experiments or the denominator of a confidence interval. The explicitly filled target row above is Pcal_0221. Full pairwise identity counts and all alignment columns were not reconstructed from the figure.

### Explicit arithmetic that can combine measured quantities, without adopting A101 aggregation

The site component is the explicit sum above. The motif-set component is the separate explicit sum above. Their scopes differ: preserving substrate-pocket residues supports a shared recognition feature, whereas losing the complete cofactor-associated signature limits transfer of the bacterial reduction mechanism. Multiplying 1.000 by 0.000 would erase those distinct meanings and is not proposed.

A useful additional deterministic identity-and-extent cell can be defined without a subjective weight. For one declared alignment, let:

- `N_pair` be the number of aligned columns containing an amino acid from both proteins;
- `N_identical` be exact matches among those columns;
- `L_query` be the full supplied query length.

Then:

`paired_identity = N_identical / N_pair`

`paired_query_fraction = N_pair / L_query`

`identical_query_fraction = paired_identity × paired_query_fraction = N_identical / L_query`.

This proposed product combines identity and extent through a shared denominator. It is a physical fraction of supplied query residues participating in exact matches in that alignment, not a probability of shared function. It is **unknown for this reported group comparison**, because the paper does not supply `N_identical`, `N_pair` or a per-query complete alignment mapping. The native 16–22% percentage is not assumed to use `N_pair` as its denominator. For multiple overlapping alignments, the denominator and unique residue-pair selection must be resolved before computing this cell; one cannot sum repeated matches.

No raw score, bit score, E-value, global identity score, alignment length, gap fraction, alignment coverage, self score or numeric A101 total is manufactured to fill these gaps. A101 still needs a reviewed way to combine compatible tool scores and functional-site information. That choice is outside this single-paper workload, and no A105 S/B combination is imported.

## Experimental comparability and isolation remain different questions

**Comparability:** the Pcal test and empty-vector control share the host ΔqueF genotype and pBAD24 backbone; the main Methods specify LB with 0.2% arabinose. The supplementary routine-growth medium also specifies 0.2% glycerol and growth at 37°C. Exact matched protein concentrations, plasmid expression burdens and per-replicate quantitative normalization operands are unavailable. An equal-expression multiplier is therefore not calculable.

**Isolation:** deletion removes the native bacterial QueF contribution, but product formation still occurs in a host pathway containing other enzymes and tRNA substrates. The product-localization measurements identify what appeared in tRNA, while they do not isolate free-base modification from tRNA-bound modification by Pcal_0221. Purified Pcal_0221 assayed separately on defined free preQ0 and preQ0-tRNA would address that distinction. Those are A105 substrate/activity measurements, not missing A101 alignment scores.

The source provides at least two independent tRNA extractions/analyses, with no exact count per displayed contrast or replicate-level activity values. That statement grounds the experimental reference; it does not provide eight sequence-specific activity tests, a homology uncertainty interval, or an A101 replication multiplier. No A106 perturbation score is calculated here.

## How the evidence limits functional transfer

The conserved pocket, shared domain correspondence and lack of the complete bacterial cofactor signature make this a useful example of **family relationship that does not justify transferring an exact reaction**. Pcal_0221 retains all four selected pocket residues while the paper's heterologous experiment supports archaeosine formation rather than simply reassigning the bacterial NADPH-dependent reductase function. Even a perfect score on the four-site component cannot establish precise substrate specificity.

There are two distinct links that must not be merged:

1. Pcal_0221 ↔ bacterial QueF: reported domain-level relationship and the specified site/motif measurements. The bacterial reaction is contextual reference knowledge cited by this paper.
2. A future supplied target ↔ experimentally tested Pcal_0221: a new target-to-reference relationship is needed. This paper supplies the reference sequence and limited characterized activity, but no alignment score for that future target.

The absence of the signature is a measured qualification to a particular mechanistic transfer, not evidence against every possible preQ0-related function. The unresolved free-versus-tRNA-bound substrate question remains unresolved even after the heterologous product is identified. A useful qualified result must retain both facts.

## Shared evidence, uncertainty and missing operands

| Issue | Required treatment in the sheet |
| --- | --- |
| Identity percentage and fractional conversion | Two representations of one quantity; count once. |
| Four site matches and overall identity | Site matches may be included in overall identical-residue counts. Keep site correspondence explicit; do not claim independent replication or add the count twice without a defined nonoverlapping calculation. |
| Structure-guided alignment and RMSD | The alignment itself depends on structural modeling. RMSD belongs to its structural context; do not present the same model as an independent sequence-only experiment plus a second independent structure experiment. |
| Single sequence and eight-sequence motif descriptions | Nested evidence sets. The Pcal record is already included in the eight; repeated presentation creates no additional evidence. |
| Assay peaks, fragmentation, site localization | Complementary descriptions within the experimental reference chain. They are not separate A101 contributions. |
| 16–22%, 89–107 atoms, 1.5–3.1 Å | Observed comparison ranges, not standard errors, confidence intervals, or independent paired endpoint rows. No midpoint or synthetic variance is inferred. |
| Intact signature not detected | Observed zero in complete supplied records; no zero affinity, zero activity or zero annotation-support score follows. |
| Native sequence scores not reported | `null`, with `not_reported_in_inspected_source`; never 0. |
| Unresolved coordinate convention | Preserve both printed and supplied-sequence coordinates and the observed offset. Do not silently renumber the source. |

Exact missing inputs are: raw/bit scores and their algorithms; E-values and search space; per-query/per-reference pair identification for the range; identity numerators and denominator definitions; full alignment columns or unique residue mappings; exact domain boundaries; alignment start/end coordinates and gap counts; a complete-sequence versus fragment designation for any new input; and an actual target-to-Pcal_0221 comparison if that is the transfer being scored. There is no demonstrated homologous transfer from Pcal_0221 to the workflow's fixed ybhP target in this review.

These omissions are reasons for explicitly empty cells, not a categorical fallback. Exact proposed fields and population sources appear in `reader_fields_001.json`; the source-to-cell table is `source_to_cells_001.tsv`. Neither file is a reader implementation.

The uninspected second DOI could be considered later for a narrowly identified experimental substrate question. It is not necessary to fabricate a sequence statistic now, and it must not be assumed to provide the missing original alignment operands. No second-paper claim is made.
