# A101 component packet: TriA versus AtzA

This packet contributes a worked native-sequence example to the goal of usable numerical sheets for all ten retained axes. It does **not** complete A101, define an overall A101 aggregation policy, or settle the A105 policy under review. Its bounded completion criteria are: recover the actual comparison and denominators; provide numerical component cells and explicit arithmetic; distinguish function correspondence from sequence correspondence; retain absent quantities as absent; and check the arithmetic without running an alignment or a scientific episode. The input is the retained case `seq_triA_atzA_near_identity`; these are reference proteins for sheet construction, not new annotation targets in the production investigation.

Source: Seffernick et al., *J. Bacteriol.* 183:2405–2410 (2001), [DOI 10.1128/JB.183.8.2405-2410.2001](https://doi.org/10.1128/JB.183.8.2405-2410.2001), [PMC95154](https://pmc.ncbi.nlm.nih.gov/articles/PMC95154/). This is an A101-specific reuse of a paper already inspected for A105, not a newly discovered paper. All source sections and Figures 1–4 were inspected; the complete authority reset preceded this scoring interpretation. The PMC article lists no supplementary alignment file. Its full protein comparison is Figure 3. No second primary paper or sequence database record was opened.

## 1. Experimental and comparison definitions

| Object | Exact meaning in this packet |
|---|---|
| Annotation-side target, `Q` | TriA encoded by `triA` from **Pseudomonas sp. strain NRRL B-12227**, the historical name used by this paper. `Q` is a role assigned here to the published sequence; the paper did not label it a database-search query. |
| Reference, `R` | AtzA from **Pseudomonas sp. strain ADP**, as displayed opposite TriA in Figure 3. The paper does not give a versioned AtzA sequence accession in that figure. Its sequence should not silently be replaced by a modern same-name database record. |
| Sequenced target construct | Genomic PCR product cloned in pUC18 as pJS3; expressed in *E. coli* DH5α. A single 1,425-nt ORF was identified. The deposit named in the paper is **AF312304**, without a version. The cloned sequence was checked against three overlapping, approximately 0.6-kb genomic PCR products, each sequenced in duplicate in both directions. No numerical base-call quality/error probabilities are supplied. |
| Protein comparison | Both published proteins have 475 amino acids. Figure 3 spans residue 1 through 475 for each, displays no insertion/deletion columns, and boxes nine substitutions. The terminal `*` is not residue 476. GCG sequence-analysis software is named; version, individual program, scoring matrix, gap costs and alignment mode are not reported. |
| Region definition | Full displayed protein span: `Q:1–475` ↔ `R:1–475`, one-based inclusive protein coordinates. These are not genomic coordinates. No experimentally delimited catalytic domain or function-determining residue set is supplied. |
| What was deliberately compared | Two naturally occurring protein sequences, not a controlled series of nine single-residue mutants. At least nine amino-acid identities differ simultaneously. The enzyme assays also differ in preparation and purification; that variation is not removed by the sequence match. |
| Coexistence | The TriA and AtzA assays use separate preparations. TriA came from DH5α(pJS3); the paper identifies DH5α(pMD4) as the AtzA clone and uses highly purified AtzA in the competition comparison. No assay here intentionally mixes TriA and AtzA or measures competition between coexpressed enzyme variants. Mixed background proteins in a crude/partially purified TriA preparation are a separate issue. |
| Relevant measured endpoints | Sequence residues and counts for A101. Enzymatic substrate loss/product formation and competition in the paper establish what the assayed proteins do, but their rates/inhibition ratios are not A101 homology scores. |

The supplied case record identifies this sequence pair but supplies no standalone FASTA to validate against the current packet. The target here is therefore the **paper's TriA sequence**. Applying the packet to another supplied sequence still requires establishing that sequence's correspondence; its label alone cannot inherit these values.

### Function grounding, with the experimental boundary retained

TriA's melamine/ammeline deamination is supported by this paper's clone-versus-control extract comparison, HPLC products, product mass-spectrometry statements, and substrate panel. The untransformed DH5α control lacked detected melamine degradation. Partially purified TriA had detected melamine activity and no detected atrazine transformation at the stated sensitivity. Those results separate the reactions within this tested panel. They do not make every reaction absent at every possible condition, nor does a nondetection mean an exact zero rate. [Methods; Results; Table 1](https://pmc.ncbi.nlm.nih.gov/articles/PMC95154/#T1).

AtzA's atrazine-dechlorinating activity is the measured baseline of this paper's original AtzA competition experiments, using highly purified enzyme. Its absolute baseline rate is not given in those results. The broader assertions that AtzA has no deaminase activity and excludes particular alternative substrates are attributed in the text to earlier work, especially reference 35 (2000); they must not be counted as a second newly performed substrate panel in this paper. No earlier primary was opened for this packet. [AtzA competition methods/results and Discussion](https://pmc.ncbi.nlm.nih.gov/articles/PMC95154/).

**Experimental comparability** and **isolation of the effect** remain separate. Shared heterologous host and described common buffer/iron-dialysis treatment do not equal matched purity, expression or active-enzyme concentration: TriA assays use crude or partially purified material, while the cross-enzyme competition discussion uses highly purified AtzA. The clone/control comparison addresses whether expressed TriA can account for activity; it does not isolate the effect of any one of the nine residues. Quantitative purity and matched expression inputs are absent. These qualifications belong beside the source-function link; no A105 reliability model is copied into A101 and no categorical substitute is assigned.

## 2. Source-to-numerical-component table

`Reported` means stated in the paper; `figure read` means a count/span/residue read from its existing display; `derived` means arithmetic performed here; `proposed representation` means a possible numerical cell, not a paper result or an adopted score. Numeric uncertainty and source status are separate from the numeric value.

| Numerical cell | Source and inputs | Value | Scoring meaning and limits |
|---|---|---:|---|
| Full target/reference protein lengths | Abstract; Figure 3; reported | 475 aa each | The actual whole-protein denominators. Neither a fragment length nor the PCR-product length. |
| Published aligned residue pairs | Figure 3, matching numbering 1–475 with no gap columns; figure read | 475 pairs | Extent of the displayed comparison; does not identify the underlying GCG algorithm. |
| Amino-acid mismatch count | Results, “DNA sequence of triA”; nine Figure 3 boxes | 9 residues | Sequence differences in one pair; not nine independent experimental effects. |
| Amino-acid identity count | Derived: 475 − 9 | 466 residues | Identical pairs within that full comparison. |
| Full protein identity fraction | Derived: 466/475 | 0.981052631579 | Actual sequence agreement; not a probability of correct substrate or reaction transfer. Paper reports 98%, which remains a separate rounded source number. |
| Full protein mismatch fraction | Derived: 9/475 | 0.018947368421 | Complement of identity for this ungapped, unambiguous display. It is not an additional independent score. |
| Target-side comparison coverage | Derived: 475/475 | 1 | Fraction of the paper's TriA protein included in Figure 3. Does not establish that an external input sequence is complete. |
| Reference-side comparison coverage | Derived: 475/475 | 1 | Fraction of the paper's AtzA protein included. Distinguish the annotation target from a search program's “target” field. |
| Displayed gap/ambiguity counts | Figure 3 inspection | 0 / 0 | No gap or ambiguous amino-acid codes are displayed. This is not a claim of zero sequencing-error probability or zero hidden low-quality bases. |
| ORF length and nucleotide differences | Results, “DNA sequence of triA”; reported | 1,425 nt; 9 differences | Full TriA ORF length and between-gene difference count. A base-by-base nucleotide alignment, nucleotide coordinates and stop-codon comparison are not printed. |
| Sense-coding nucleotide identity | Derived conditionally: (1,425 − 9)/1,425 | 0.993684210526 | Uses the reported 1,425-nt ORF as the shared sense-coding denominator. Preserve the explicit scope assumption; do not present as an exact, independently audited nucleotide alignment. Paper reports 99%. |
| Observed nonsynonymous-difference proportion | Derived: 9 amino-acid-changing nucleotide differences / 9 reported nucleotide differences | 1 | Describes these reported differences only; not dN/dS, a selection statistic, a function score, or nine causal assays. |
| Domain identity/coverage | No domain boundaries or domain-specific count reported | **null** | Full-protein sequence coverage cannot fill a biologically defined domain denominator. |
| Function-required-site identity/coverage | No residue set experimentally linked to the differing specificity in this paper | **null** | A missing function-specific denominator is not zero conservation and is not nine sites. |
| Raw alignment score, bit score, E-value, profile score | Not reported in Methods, Results or Figure 3 | **null** each | Do not invent BLAST/HMMER statistics or a raw GCG score from percent identity. |

Protein fractions are exact arithmetic conditional on the published comparison. Their displayed decimals are rounded for readability. The paper supplies no sequence-error distribution or sampling variance for these counts; uncertainty status is `not_reported`, not “±0”. A binomial confidence interval over these 475 positions would introduce a sampling model that this complete-pair comparison does not supply.

The nucleotide calculation is weaker in scope than the protein calculation: `1,425 = 3 × 475` is consistent with a sense-coding denominator, but does not establish accession-coordinate endpoints, nucleotide gap counts, flanking identity, or treatment of a terminal stop triplet. Those fields remain null. A value for `(1,428 − 9)/1,428` would use an unsupported denominator.

## 3. The actual residue differences, not an inferred functional-site set

The order below is **AtzA reference → TriA target**. Coordinates are the same on both displayed proteins. These entries transcribe Figure 3; they are not newly computed alignments or mutagenesis effects.

| AtzA position | AtzA residue | TriA position | TriA residue | Individually established specificity role in this paper |
|---:|:---:|---:|:---:|---|
| 84 | F | 84 | L | Not established |
| 92 | V | 92 | L | Not established |
| 125 | E | 125 | D | Not established |
| 217 | T | 217 | I | Not established |
| 219 | T | 219 | P | Not established |
| 253 | I | 253 | L | Not established |
| 255 | G | 255 | W | Not established |
| 328 | N | 328 | D | Not established |
| 331 | S | 331 | C | Not established |

The paper offers substrate-binding interpretations and a possible proton-donating group, but does not map that hypothesis to a named numbered residue. Its discussion's inference about localized changes is not a measured TriA/AtzA structure. Thus this table supplies **positional correspondence** only. No A106 single-substitution effect or A111 observed contact/occupancy is produced by it. The number of individually assayed substitutions in this paper is zero; the number of biologically important sites is unknown.

For the *postselected mismatch set* `D`, identity is arithmetically `0/9` and mismatch is `9/9`. These are tautological descriptions of a set defined by mismatch. They must not populate a functional-site score or be multiplied into sequence support. The function-required set `F` has no supplied membership or denominator, so both `identity(F)` and `coverage(F)` are null.

## 4. Explicit sums/products and denominator handling

For a supported region `R`, let `I_R` count identical comparable residue pairs and `M_R` count nonidentical comparable pairs. In this paper's full display all residues are ordinary amino-acid codes and there are no gaps, so:

\[
N_R=I_R+M_R=466+9=475\ \text{residue pairs},\qquad
p_R=I_R/N_R=1-M_R/N_R=466/475.
\]

The display's nonoverlapping printed blocks provide a concrete sum check; these blocks are **not biological domains**:

| Protein interval, inclusive | Compared pairs `n_b` | Differences `m_b` | Identities `i_b` | Within-block identity `i_b/n_b` |
|---|---:|---:|---:|---:|
| 1–50 | 50 | 0 | 50 | 1 |
| 51–100 | 50 | 2 | 48 | 0.96 |
| 101–150 | 50 | 1 | 49 | 0.98 |
| 151–200 | 50 | 0 | 50 | 1 |
| 201–250 | 50 | 2 | 48 | 0.96 |
| 251–300 | 50 | 2 | 48 | 0.96 |
| 301–350 | 50 | 2 | 48 | 0.96 |
| 351–400 | 50 | 0 | 50 | 1 |
| 401–450 | 50 | 0 | 50 | 1 |
| 451–475 | 25 | 0 | 25 | 1 |
| Sum | **475** | **9** | **466** | **466/475**, not the unweighted block mean |

\[
p_{\rm full}=\frac{\sum_b i_b}{\sum_b n_b}
=\sum_b\left(\frac{n_b}{475}\right)\left(\frac{i_b}{n_b}\right)
=\frac{466}{475}.
\]

These multipliers are exact length fractions, not proposed relevance judgments. Overlapping regions must first be reduced to unique residue-pair coordinates; their counts cannot be added as if disjoint. A domain sum would require actual domain definitions before the same arithmetic could be used.

An optional **proposed representation** is the fraction of the full target positions observed identical to the reference:

\[
f_{Q,\mathrm{identical}}=p_{\rm pairs}\times
\frac{N_{\rm pairs}}{L_Q}
=\frac{466}{475}\times\frac{475}{475}
=\frac{466}{475}.
\]

Here `p_pairs` is explicitly defined over known, nongap residue pairs and `L_Q` is the full target length. The product cancels to `I/L_Q`; it changes the denominator, not the confidence in function. It is algebraically redundant with full identity in this case and must not be counted alongside it as another contribution. For a partial future match it would mean “fraction of whole target positions demonstrably identical,” not “fraction with a proven function.” If the full target length is unknown, this quantity is null; a fragment length cannot stand in for it. If the native tool's identity denominator includes gaps/ambiguities, that native value must be preserved separately and must not be substituted for `p_pairs` in this product.

For a future independently established function-required site set `F`, a *proposed* count-based representation would be:

\[
p_F=\frac{\sum_{s\in F,\,\mathrm{mapped\ and\ comparable}}
\mathbf{1}[Q_s=R_s]}{|F_{\rm mapped,comparable}|},\qquad
c_F=\frac{|F_{\rm mapped,comparable}|}{|F|}.
\]

`p_F × c_F` would be the fraction of the defined required-site set observed identical, not a function probability. All operands are null for this paper because `F` is undefined. An empty evidence list does not make `|F|=0` or a perfect-conservation score. Even exact identity at validated catalytic residues may fail to establish substrate specificity; the biological meaning of `F` must remain explicit. No site weights, substitution-matrix weights, threshold, or overall A101 formula are adopted here.

## 5. Exact typed cells for future population

The filled example is `cells_001.json`. This is a proposed sheet component contract, not production reader code. Each numerical cell has the same closed fields:

| Field | Type and constraint |
|---|---|
| `value` | `number \| null`; integer for count cells; null is required when status is `missing` |
| `status` | `reported \| figure_read \| derived \| conditional_derived \| proposed_derived \| missing` |
| `unit` | `amino_acid \| residue_pair \| nucleotide \| fraction \| percent \| native_alignment_score \| bit \| expected_random_matches \| native_model_score` |
| `numerator`, `denominator` | `integer \| null`; fractions require a positive declared denominator unless missing |
| `formula_id` | `literal \| difference \| ratio \| sum_of_disjoint_counts \| identity_times_pair_extent \| unavailable` |
| `input_cell_ids` | Unique list of cell IDs; arithmetic inputs only, not new evidence identities |
| `region_id` | `protein_full \| nucleotide_sense_coding_assumed \| domain_undefined \| required_sites_undefined \| comparison_method` |
| `source_ids` | Nonempty list of named source locations, even for an inspected absence |
| `uncertainty_status` | `reported_rounding_only \| not_reported \| conditional_scope \| missing` |
| `missing_reason` | `null \| not_reported \| undefined_domain \| undefined_required_site_set` |

Sequence identities have values in `[0,1]`; percent literals in `[0,100]`; nonnegative counts retain their units. A raw score is not generally constrained to be nonnegative. None of the status or missing-reason strings is itself a numerical score. All nonmissing arithmetic has a stated denominator or count relationship above. Fraction numerators are identities/mismatches/covered positions, never biochemical rates.

The enclosing record fixes `case_id`, `axis_id`, target/reference roles, one-based region coordinates, the nucleotide-scope assumption, source methods and unknown parameters, per-position differences, and one shared sequence-pair dependence group. Each difference row has integer target/reference positions, one canonical residue letter on each side, and `functional_role: null`. Domain/required-site coordinates and lengths remain null. Function-source links retain `directly_observed_here` versus `attributed_to_prior_work`; they have **no homology-score numeric value**.

Future population is narrow: a literature reader extracts the lengths, printed numbers, displayed residue correspondences and method qualifiers; a dataset reader would accept an actual aligned-record comparison with explicit sequence roles and denominators; a deterministic arithmetic function computes the same count ratios and sums. A selected ungapped comparison cannot be fabricated from a percent-identity quote. An exact raw/bits/E score requires its original result and method/search-space definition. These production readers are not implemented by the arithmetic checker in this research packet.

## 6. Missingness, dependence, alternatives and remaining work

| Issue | Consequence for component use |
|---|---|
| Full protein identity versus exact chemistry | The measured `466/475` is compatible with this pair having different tested reactions. It supports close sequence correspondence; it does not assign atrazine dechlorination to TriA. |
| Melamine-deamination alternative | TriA's own activity measurements establish this observed activity. A fictitious self-alignment score of 1 is unnecessary and would not provide independent support. |
| Atrazine-dechlorination alternative | The same AtzA correspondence score remains `466/475`; it is not rewritten downward to encode the TriA assay nondetection. The separately retained experimental finding limits that functional transfer under the tested conditions. No biochemical activity ratio is copied into A101. |
| Broad homolog/family description | Full correspondence and the source's family analysis can support a broader relationship while a particular substrate claim remains unsupported by A101 alone. The packet offers no calibrated probability for either alternative. |
| Abstract, text, Figure 3 and derived percentages | They are representations of the same sequence-pair evidence. One dependence group covers all of them; derived arithmetic creates no new experiment. |
| Protein and nucleotide identity | The translated comparison and its underlying coding-sequence differences are dependent. Do not add their fractions as independent evidence or combine them by a confidence-product rule. |
| Clone-versus-genome sequence checks | They address cloning/PCR artifacts in the source sequence. Duplicate strands and overlapping fragments do not multiply the number of independently characterized functions or homologs. |
| Approximately 1.5-kb clone, three approximately 0.6-kb checks | These are physical cloning/verification fragments. Their exact endpoints and overlap are not stated. `3 × 0.6 kb` is not unique coverage; no 1,800-nt or greater-than-100% coverage cell is assigned. The published protein comparison remains whole-length. |
| Unknown raw/bit/E/profile score | Leave null; do not substitute zero, infinity, arbitrary confidence, or a newly run algorithm. |
| Unknown functional-site denominator | Leave null. Perturbation experiments linking specific substitutions to activity and a validated mapping could address it, but this paper does not supply those experiments. No additional primary is necessary to complete this bounded native-comparison packet. |
| Structural inference | No observed TriA/AtzA structure, contact distance, ligand occupancy or residue-specific catalytic geometry is extracted. This prevents sequence inference from becoming A111 structural evidence. |

Open work for the broader A101 sheet includes contrasting cases with partial/domain correspondence and genuine function-site mapping; appropriate comparison classes for native raw/bit/profile scores; and an explicitly reviewed way to combine nonredundant A101 components into annotation scoring. Exact sequence accession/version custody for external target reuse also remains unresolved. None of those gaps is filled with an intuitive overall relevance grade. The arithmetic check establishes only the formulas and consistency in this packet, not the correctness of a future reader or the completed ten-axis goal.
