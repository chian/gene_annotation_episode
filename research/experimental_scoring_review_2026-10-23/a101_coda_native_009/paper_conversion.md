# A101 paper conversion: CodA and the failed archaeal candidate

Status: single-paper research conversion, not an adopted or complete A101 sheet.
The source belongs to the existing 142-group corpus. This is a fresh inspection
of that source and its supplement, not a newly discovered case. No second paper,
alignment run, production reader, prompt, scorer, scientific episode or HPC job
was used. The complete post-paper authority reread preceded this conversion;
its actual read coverage is recorded in `authority_reread.md`.

Primary source: Hitchcock et al., *Rescue of the Orphan Enzyme Isoguanine
Deaminase*, DOI [10.1021/bi200680y](https://doi.org/10.1021/bi200680y),
[author-hosted primary PDF](https://www.chem.tamu.edu/rgroup/raushel/publications/P258-Biochemistry-Isoguanine%20Deaminase-2011.pdf).
Supporting information: [10.1021/bi200680y.s001](https://doi.org/10.1021/bi200680y.s001),
[publisher deposit PDF](https://ndownloader.figshare.com/files/4288957).
Locations below use printed article pages and supplement page/table numbers.

## Experimental and comparison definitions

The proposed archaeal subject was *Picrophilus torridus* protein gi|48477797,
expressed as a codon-optimized gene in *E. coli* BL21 using pET-28 or PGS-21a.
The source does not provide the synthetic nucleotide sequence, complete protein
sequence, exact fusion boundaries, or sequence alignment. Its inferred reference
relationship was to the SAH-deaminase-related portion of COG0402. The stated
substrate-recognition comparison is SAH-deaminase His137 versus a glutamine at
the corresponding position in the selected subgroup. The candidate's own
residue number and the specific aligned SAH reference sequence are not supplied.

This was heterologous expression in a host containing endogenous enzymes. The
archaeal protein and host proteins could coexist in the extract; their soluble
fractions were not quantified. The intended variable was expression of the
archaeal candidate. Host background, mostly insoluble expression and fusion
behavior prevented attributing the observed activity to that candidate. The
paper therefore does **not** establish either its activity or its inactivity.

The activity subsequently identified was *E. coli* CodA/CDA, gi|16128322, from
BL21(DE3) stationary-phase lysate. Purification plus peptide identification led
to recombinant CodA assays. These measured the same protein with different
substrates, not a target-versus-homolog sequence comparison. YahJ gi|16128309 and
SsnA gi|33347706 were other purified candidates with reported nondetection;
the inspected source supplies neither a numerical detection limit nor complete
conditions for those negative tests. They must not become zero enzyme activities.

Experimental comparability and isolation remain distinct. The CodA substrate
comparison is described as using identical reaction conditions at pH 7.7, but
it does not establish comparable assay conditions for the archaeal protein.
Attribution of extract activity to the archaeal protein is a separate problem
from this condition mismatch. Purified recombinant CodA and product
identification address attribution to CodA. Neither result supplies a missing
sequence-comparison score.

## Source-to-cell conversion

| Inspected source and actual input | Proposed cell or role | Calculation / filled result | Limit and axis boundary |
| --- | --- | --- | --- |
| Article p.5555 and Fig.1 p.5556: BLAST sequence-similarity network cutoff `1e-70` | `network_evalue_cutoff` | Preserve `1e-70` as a dimensionless threshold | This is a network construction parameter, **not** a selected target/reference E-value, its bound, a bit score, or a global alignment score. No pair-specific score can be populated from it. |
| Article p.5555: His137 in SAH deaminase versus Q at the reported counterpart in the candidate subgroup | `reported_named_site_identity` for the declared one-site comparison | Observed comparable sites `K=1`; identical residues `M=0`; `M/K=0/1=0`; mismatch count `K-M=1` | Literal identity over one reported site, not a functional probability or an activity knockout. This is author-reported correspondence; coordinate-verified correspondence remains unknown. |
| Same one-site comparison; declared site set `R=1` | `reported_site_observation_fraction`, combined named-site agreement | `K/R=1`; `(K/R)×(M/K)=M/R=0` | The multiplier expresses the numerator/denominator relationship; it does not add independent evidence. The zero must not zero out all A101 support. |
| Fig.3 and article p.5556: CodA Q156, E217, H246, D313, D314 | Source feature set for a later target alignment | Five explicitly listed source positions; no target mapping and no populated target-site agreement | Structural contacts define which sequence positions could be compared. Their structural evidence belongs to A111; mapping them through a target alignment is the A101 operation. Do not assume SAH H137 and CodA Q156 are aligned because both are discussed as recognition residues. |
| Supplement Table S2 p.5: ten peptide-coordinate intervals | Experimental source identification, separate from homology score | Inclusive interval lengths sum to **142 distinct residues**; ten intervals do not overlap | This is peptide identification coverage, not homolog alignment coverage. Full intact protein length is not stated in the inspected paper/SI, so a whole-protein coverage fraction stays unknown. Last observed coordinate 427 is not proof that the protein ends there. |
| Supplement p.2: modeled CodA residues 4–425 | Structural model span; source mapping qualification | `425−4+1=422` modeled positions in the stated continuous interval | This is neither full sequence length nor alignment length. It cannot supply a homology coverage denominator. |
| Article p.5556: CodA efficiencies for isoguanine and cytosine `(6.7±0.3)×10^5` and `(1.5±0.1)×10^5 M^-1 s^-1` | Experimental grounding for reference functions | From rounded central estimates: `6.7/1.5=4.4666667` for those two substrates under the reported conditions | This ratio is A105 biochemical information, **not** an A101 score or transfer multiplier. Error type, covariance and independent preparation count are unspecified; no probability or propagated interval is assigned. |

The two kinetic measurements establish an experimentally studied reference with
more than its pre-existing cytosine label. They do not establish isoguanine as
the physiological substrate of every bacterial homolog. The paper's broad
extension to bacterial cytosine deaminases is an author prediction, not a panel
of independently tested homologs. The source's deletion result is perturbation
evidence; it is not converted into an A101 component or developed into A106 here.

## Numerical components that still require the missing alignments

These are component calculations for the requested numerical sheet. They are
not a proposed overall aggregation and introduce no confidence ladder or A105
formula. Native program scores would be retained in their own cells. All the
following filled results are `null` for the target/reference comparisons in this
paper because their required operands were not reported.

1. **Keep actual score types separate.** A pair's reported raw alignment score,
   bit score and E-value retain program, version, matrix, gap penalties,
   statistical search space, score scope (HSP/domain/sequence) and query/reference
   operands. A network cutoff cannot populate any of those result cells. An
   E-value is not a probability that the functional annotation is wrong. No
   pair/self raw-score normalization is possible here.
2. **Separate local identity from coverage.** For one consistent, selected
   alignment correspondence, let `L_T` be the known number of residues in the
   supplied target material, `A_T` the number of unique target positions covered
   by that correspondence, `P` the number paired to a resolved nongap reference
   residue, and `I` the number of identical resolved pairs. Then:

   `C_T = A_T/L_T`, `P_T = P/A_T`, `I_local = I/P`, and
   `F_T = C_T × P_T × I_local = I/L_T`.

   Every fraction is dimensionless in `[0,1]`; `F_T` is the fraction of supplied
   target residues with an observed identical reference counterpart, not
   annotation confidence. Zero denominators yield unknown, not zero. Reference
   coverage `C_R=A_R/L_R` remains separately visible. A snippet's `L_T` only
   describes that snippet; whole-protein coverage is unknown unless whole length
   and placement are independently established. Overlapping HSPs cannot be
   summed without resolving repeated or conflicting residue mappings. Preserve
   a program's percent identity and its actual denominator separately: it may
   use gapped alignment columns rather than this `P` denominator.
3. **Count functional-site agreement within an explicitly declared set.** With
   `R` relevant reference positions, `K` mapped positions having resolved residue
   pairs, and `M=Σ 1[target_residue=reference_residue]` over those `K` pairs,
   retain observation coverage `K/R` and local identity `M/K` separately.
   Their product is `M/R` only as an observed exact-match fraction. With `U=R−K`
   unresolved sites, the possible complete-set identity fraction lies between
   `M/R` and `(M+U)/R`; these are missing-data bounds, not confidence bounds.
   Unknown source-to-target mappings cannot be classified as mismatches.
   Identity is not chemical interchangeability or functional necessity. Any
   biochemical acceptance set for a position needs independent justification.
4. **Represent alternatives by actual paired comparisons.** For the same target
   and comparable scoring setup, `Δb = b(target, reference_A) −
   b(target, reference_B)` is a signed difference in bits. Keep both native
   scores and sequence/region coverage. A functional comparison also requires
   actual experiments supporting each reference's function. Here neither native
   pair score exists; the archaeal candidate is not an experimentally
   characterized isoguanine reference. A numerical preference margin is
   therefore unknown. Family labels cannot supply its missing operands.

The actual one-site calculation is deliberately narrow: reported H/Q comparison,
one observed position, one mismatch. It is a worked local-identity cell, not a
substitute for this paper's absent native alignment scores. The general
component formulas above are unfilled proposals. The paper cannot complete a
fully populated A101 example or determine how native scores should be combined
across algorithms.

## What similarity did and did not accomplish

The network and reported local recognition difference motivated an investigation
without prior functional knowledge of the archaeal candidate. Shared family
membership and catalytic features provided useful search context. The initial
activity observation could not be assigned to that candidate because host
enzymes contributed to the extract. This is an attribution failure, not proof
that a high pairwise alignment score predicted the wrong function.

**No high global alignment score is reported here.** Consequently this case
cannot supply a numerical example of high global identity or bit score failing
to transfer function. It instead exposes two precise limitations: a network
edge threshold does not score a particular pair; and a known substrate label
does not imply that other substrates were tested and excluded. Local recognition
features, substrate chemistry, protein identity and experimental context must
remain attached to a function-transfer inference. The source itself reports
different substrate-binding features across COG0402 despite common catalytic
and metal-binding features; it supplies no residue-count denominator from which
to calculate family-wide conservation.

## Dependence, reuse, and what would repair the gaps

- Raw score, bit score, E-value, identity, gaps and coverage from the same
  alignment share underlying residues. Multiple summaries are not independent
  homology observations. An A101 combination must account for that dependence;
  this packet selects no overall weights.
- The H/Q mismatch and its `0/1` identity are the same observation. Its agreement
  product is an algebraic restatement, not an additional contribution. The
  source does not provide a count of sequences in each subgroup, so three
  exceptional subgroups do not give a numerical conservation percentage.
- CodA contact positions drawn from structure and then checked in a sequence
  alignment form one linked evidence chain. Reusing those residues across A101
  and A111 cannot create two independent experiments.
- The ten peptide intervals identify one source preparation. They are not ten
  functional assays or ten homologs. Purification, peptide identification,
  product spectra and kinetics address complementary questions; their reports
  are not interchangeable independent replications.
- Resolve missing sequence comparison operands by obtaining the actual supplied
  target material, exact reference sequences/versions and native alignment
  results with parameters and coordinates. An exported source network with
  edge-level scores could recover network comparisons; its diagram cannot.
  This work has not been run.
- Resolve the archaeal candidate's activity attribution with measurements on a
  demonstrably identified soluble candidate preparation and appropriate host
  controls. Resolve its nondetection, if any, with a stated assay sensitivity
  and compatible conditions. Those are experimental needs, not invented A101
  penalties or production experiment requests.

## Reader field contract proposal

These fields identify what future targeted readers would populate. They do not
implement such readers. A source locator is provenance, not a score.

| Record | Exact candidate fields and types | Numerical rule / missing treatment |
| --- | --- | --- |
| Supplied material | `sequence_kind: enum(protein,nucleotide)`; `sequence_text: string|null`; `selected_record_or_region: string|null`; `residue_count: uint|null`; `completeness: enum(complete,fragment,unknown)`; `full_length: uint|null` | Accept sequence/file/snippet without annotation or public identifier. Never infer full length from a highest observed coordinate. |
| Native comparison | `target_ref, reference_ref: string`; `program, version, score_scope: string|null`; `raw_score, bit_score: number|null`; `evalue: decimal_string|null`; `is_threshold: bool`; `matrix: string|null`; `gap_open, gap_extend: number|null`; `effective_search_space: number|null` | Retain score type and operands. A threshold stays distinct from a result. Null records why input is absent; it does not encode zero evidence. |
| Alignment geometry | `target_length, reference_length: uint|null`; `target_covered, reference_covered, resolved_pairs, identical_pairs, alignment_columns, gap_columns: uint|null`; `aligned_target, aligned_reference: string|null`; `coordinate_intervals: array|null`; `native_pident, native_qcov: number|null`; `native_denominator_definition: string|null` | Calculate coverage/identity from explicit counts and one consistent mapping. Preserve native reported values independently. |
| Functional sites | `site_set_id: string`; `reference_position: uint|null`; `target_position: uint|null`; `reference_residue, target_residue: AA|null`; `mapping_basis: enum(author_reported,alignment_verified,unknown)`; `role: enum(recognition,catalysis,metal_binding,unknown)`; `site_count, observed_pair_count, exact_match_count: uint|null` | Author-reported H/Q agreement can be filled; coordinate-verified agreement stays null. Site identity and missing-data bounds follow the formulas above. |
| Functional reference grounding | `assayed_sequence_ref: string|null`; `function_endpoint_ref: string`; `assay_subject_ref: string`; `reference_mapping_verified: bool|null`; `experiment_ref: string` | Link to measured activity and limitations without copying kinetic or perturbation values into sequence-score cells. An uncharacterized candidate is not positive function ground truth. |
| Dependence and limits | `source_record_ref, underlying_comparison_ref, underlying_experiment_ref: string|null`; `derived_from: array[string]`; `missing_reason: enum(not_reported,not_retrieved,not_measured,not_applicable,ambiguous_denominator)` | Same underlying data remain linked across derivative cells and axes. No independent-replicate count is inferred from the number of rows or reports. |

Inspection: complete three-page article text; Figures 1–3 and Scheme 1; complete
six-page supplement, with Tables S1–S3 visually checked. Table S2 supplies
positions and mass columns, not peptide letter sequences or database-search
scores. Exact amino-acid sequences, alignment files, network edge scores,
original spectra and raw assay data were not retrieved. Arithmetic checks are
in `checked_arithmetic.json`. Numerical aggregation, calibration and production
population of A101 remain unfinished.
