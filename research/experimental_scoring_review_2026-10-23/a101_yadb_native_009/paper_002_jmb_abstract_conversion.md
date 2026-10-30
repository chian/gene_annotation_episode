# A101 source conversion 002: the cited YadB protein comparison

Status: **primary abstract inspected; full Methods, Results, tables and figures unavailable**. This is a bounded partial source conversion, not a full-paper review, adopted scoring formula, completed A101 sheet or production implementation. It follows the parent's authorization to inspect one specifically cited paper after completing paper 001 and its provenance. No third paper was opened.

Source: Campanacci et al. (2004), *The Escherichia coli YadB Gene Product Reveals a Novel Aminoacyl-tRNA Synthetase Like Activity*, JMB 337:273–283, DOI [10.1016/j.jmb.2004.01.027](https://doi.org/10.1016/j.jmb.2004.01.027), [primary abstract on PubMed](https://pubmed.ncbi.nlm.nih.gov/15003446/). The abstract was inspected in full through the browser, especially its first three sentences and functional comparison. The publisher API supplied metadata only; `view=FULL` returned HTTP 401, ScienceDirect returned HTTP 403. HAL record `hal-02919268` is a citation notice with no deposited full text. OpenAlex was used only to discover repository access, not as biological evidence. The saved `paper_002_sources/pubmed.html` is a verification-page response, **not** a saved copy of the article. The usable abstract is in the browser tool outputs identified in the read provenance.

After those access checks, the entire required authority set was actually reloaded in complete chunks before this interpretation. See `authority_read_provenance_002.json`. The latest all-ten-sheets human goal was read last. No A105 overall formula is imported.

## Definitions and source limits

The comparator is now explicit: **E. coli YadB, 298 amino acids**, versus **E. coli GluRS, 468 amino acids**. The reported sequence identity is **34%**. This resolves comparator organism and nominal complete protein lengths left unspecified in the first-paper conversion. It still does not give the exact sequence accessions/versions, alignment region, denominator, aligned residue count, gap treatment, algorithm, score matrix, gap penalties, native raw/bit score or E-value.

The abstract reports a missing complete anticodon-loop interaction domain in YadB. It does not give that domain's coordinate boundaries. The 170-residue difference in total protein lengths therefore must not be presented as a measured 170-residue domain deletion: other length differences or insertions may contribute.

The comparison concerns two natural proteins, not a mutant replacing or coexisting with wild type. The abstract mentions molecular replacement for crystallography, which is **not** the protein sequence-alignment algorithm. Experimental constructs, tags, preparation genotypes, condition matching, protein coexistence, independent preparation count, assay controls and uncertainty are not available in the inspected abstract. Unknown assay comparability and isolation cannot be filled by sequence identity. Those questions remain distinct from the A101 sequence comparison and from each other.

## Actual numerical components and bounds

The following calculations are proposed sheet components or bounds, not confidence values. `P` means the number of residue pairs in **one-to-one, nongap correspondence** between these two protein sequences. It excludes a reference residue aligned to a gap and excludes double use of a query residue across repeated local hits.

| Sheet quantity | Defined arithmetic and actual result | Denominator / what it evaluates | Source and limitation |
|---|---|---|---|
| `query_length_aa`, `reference_length_aa` | **298**, **468** | whole proteins reported by source | Abstract, first three sentences; sequence bytes and version not yet checked |
| `reported_identity_pct` | **34%**; unit conversion **34/100 = 0.34** | original alignment denominator not stated | Abstract; same underlying comparison cited by NAR, not independent replication |
| `length_difference_aa` | **468 − 298 = 170 aa** | total-length difference | Derived from those two lengths; not an exact domain boundary or measured gap count |
| `length_ratio` | **298/468 = 149/234 = 0.6367521368** | target length / reference length | A size comparison; not observed alignment coverage |
| `maximum_paired_reference_fraction` | **min(298,468)/468 = 0.6367521368** | maximum possible paired reference positions / 468 reference residues | A mathematical bound under one-to-one pairing; does not establish that the maximum is reached |
| `minimum_unpaired_reference_count` | **468 − min(298,468) = 170 aa** | reference residues that cannot all have distinct query partners | Bound; alignment may leave more than 170 unpaired |
| `minimum_unpaired_reference_fraction` | **170/468 = 85/234 = 0.3632478632** | necessarily unpaired reference positions / 468 | Complement of the upper bound, not a second independent score |
| `paired_query_coverage`, `paired_reference_coverage` | **P/298 ∈ [0,1]**, **P/468 ∈ [0,0.6367521368]** | actual paired positions / each full length | Exact point values unknown until a residue-level alignment is obtained |
| `raw_score`, `bit_score`, `e_value`, `identity_count`, `similarity_count`, `gap_columns` | **unknown** | native tool output fields | The abstract cannot fill them; this is missing access/data, not a measured zero |

There is a useful exact multiplication linking the coverage cells:

`paired_reference_coverage = paired_query_coverage × (298/468)`.

All operands have defined meanings: `P/468 = (P/298) × (298/468)`. Since the unknown `P/298` lies in `[0,1]`, the result lies in `[0,0.6367521368]`. This preserves a genuine numeric restriction without inventing a point estimate. If all 298 query residues were paired, the upper endpoint would be attained; that is a **conditional bound**, not an observed full-length alignment.

A second proposed product, once a real alignment is present, is `exact_match_reference_fraction = (I/P) × (P/468) = I/468`, where `I` counts exact identical amino-acid pairs. Its query analogue is `I/298`. This links local match density with molecular coverage transparently. `P=0` makes the density undefined and is handled explicitly; absent alignment data is a separate missing state. **Do not insert 0.34 for I/P** until the published denominator and gap handling are established. Thus no `0.34 × 298/468` functional score is reported. The 34% identity and length ratio do not, by themselves, provide the missing native alignment score or a calibrated contribution to annotation credit.

These relationships evaluate how much of a full reference can be represented by this shorter target. They are useful alongside a native alignment score and domain/residue mapping. They do not replace the native score, and they do not assign a probability that the whole reference function transfers. A contribution formula that combines score magnitude, coverage, conserved functional sites and reference-function specificity remains necessary work for the parent A101 sheet.

## Characterized function and feature evidence

The abstract's experimentally characterized scope is glutamate activation without a tRNA requirement, plus glutamyl transfer to a tRNA whose identity was **not yet established in this paper's abstract**. It explicitly distinguishes this behavior from canonical GluRS and reports no transfer to E. coli tRNA-Glu. This source alone must not be described as directly identifying tRNA-Asp Q34 as the product site; the later NAR study supplies that identification. The non-detection of tRNA-Glu transfer lacks a detection limit and cannot be converted to exact zero activity or numerical selectivity.

The abstract also reports three cysteine zinc ligands and a fourth, weaker tyrosine ligand in YadB, and a crystal resolution of **1.5 Å**. The ligand positions are not given in the abstract, nor is a complete reference-to-target site map. A `3/4` conservation component would be fabricated: three cysteines among four YadB ligands is not evidence that exactly three of four aligned functional residues are conserved. Resolution is structural measurement support, not a sequence-homology score. These observations can guide a later targeted residue comparison but do not supply one.

The useful contrast is precise: a real sequence relationship can coexist with a missing reference domain and a changed biochemical reaction/substrate. Family-level correspondence therefore cannot authorize transfer of the full canonical GluRS function. Conversely, the function difference does not erase the sequence relationship.

## Reader contract, dependencies and next missing input

Readers would fill `query_length_aa:int`, `reference_length_aa:int`, `reported_identity_pct:float`, `identity_denominator:enum|unknown`, and source locations from the primary record. A deterministic calculation can populate total-length difference and the conditional one-to-one coverage bounds. A sequence parser must separately validate actual source bytes, completeness and versions. An alignment parser would populate `paired_positions`, `identity_count`, `similarity_count`, gap runs, domain-relative coordinates, native scores and tool parameters. These reader responsibilities are proposed; no production reader is installed.

The length ratio, maximum paired coverage and its complementary unpaired fraction all reuse **the same two lengths**. Count them as one set of related measurements, not three independent confirmations. Identity repeated in NAR is a citation of this comparison. Any new computation on the same two sequences is a reproducibility analysis, not independent functional replication. Raw scores, bit scores and E-values from one run likewise share the alignment and must not be independently summed as separate evidence.

Full Methods/Figure access remains needed to determine whether the article supplies the actual original alignment, method and residue counts. If it does not, the exact two sequence versions and a declared local comparison would be required to produce reproducible new measurements, explicitly labeled as new rather than published. That computation was not run. Neither the PNAS source nor another primary paper was opened to fill the gap silently. The current packet gives an actual useful length/coverage constraint but leaves the native score, exact coverage and score-to-function conversion unfinished.

Arithmetic was checked with exact rational numbers: **149/234 + 85/234 = 1**; multiplying the maximum paired-reference fraction by 468 recovers **298**; the complementary count is **170**. See `checked_arithmetic_002.json` and `check_arithmetic.py`.
