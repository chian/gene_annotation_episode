# A101: native sequence-search numerical contract, research proposal 010

## Goal and completion boundary

The bounded goal is a usable, source-traced numerical input and combination contract for protein BLAST local HSPs and HMMER3 protein/profile searches, including Pfam results. A reader should be able to populate native score components without inventing a judgment grade, distinguish their scope and denominators, calculate the defined quantities, and identify exactly why a proposed mixture is or is not numerically evaluable.

This delivers part of an A101 sheet, not the completed A101 axis or an adopted annotation policy. The overall user goal remains ten usable numerical sheets, beginning with A105, with 0/10 complete. Native search measurements are available inputs; their conversion to specific functional support still requires independently grounded reference functions and an explicit mixture calibration or policy. No calibration data or coefficients have been established here. The finite combination proposal below is unadopted.

The investigation can begin with supplied sequence, a selected file record, or snippets. No candidate function or public identifier is an input prerequisite. Reference functions and specific comparisons can emerge during investigation. An internal sequence label identifies the supplied material, not a claimed public identity. A high search score does not itself ground the function of a reference protein or profile.

This contract defines numerical cells and their operands. Source custody and function provenance are supporting records. Investigation text and populating readers remain separate; no prompt, production reader, library, runtime, or scoring implementation is supplied.

## 1. Common numerical-cell and scope contract

Each numerical cell has `value: number|null`, `unit`, `origin: reported|derived|synthetic`, `value_text` for a native printed token, and `status: observed|derived|not_reported|not_applicable|not_identifiable|incompatible_scope|threshold_censored|reported_zero_bound_unknown`. Optional bounds have separately named `lower`, `upper`, endpoint inclusivity, and `bound_kind: rounding|censoring|missing_operand|model_uncertainty`. A source reference identifies the actual record and field. Null with a status is never replaced by zero, one, or a categorical quality grade.

Store a result's own program/version, exact scoring mode and parameters, query/reference content identities and selected ranges, alphabet, orientation/frame, database or model release, reporting/filter settings, and search completion/output-truncation facts. These are provenance, not additional score multipliers. A numeric value with unknown scope remains recorded but cannot silently populate a more specific cell.

| Field group | Exact fields and types | Required meaning |
| --- | --- | --- |
| Supplied target | `supplied_length: positive integer`, `length_unit: aa|nt`, `supplied_ranges`, `full_target_length: positive integer|null`, `material_completeness: complete|fragment|unknown` | Count actual supplied residues; do not infer omitted sequence. Distinguish selected-region length from biological full length. |
| Comparison entity | `reference_kind: sequence|profile`, `reference_sequence_length_aa: integer|null`, `profile_match_states: integer|null` | A profile's length counts match states, not the length of one characterized protein. |
| Native score scope | `score_scope: blast_hsp|hmmer_domain_envelope|hmmer_full_sequence_profile`, `native_query_role`, `native_target_role` | A BLAST subject may have multiple HSPs. A HMMER sequence/profile comparison may have multiple domains. Keep those rows distinct. |
| Statistics | `statistics_method`, native statistics parameters, `search_space_value`, `search_space_unit`, `search_space_origin: measured|reported_override|unknown` | BLAST effective residue-pair space and HMMER number of targets are different operands. Preserve user overrides separately from actual database counts. |
| Shared contribution | `comparison_group`, `duplicate_of`, `overlap_group`, `family_or_clan_relation`, `same_input_relation` | Record established identities and relationships; an unknown family relationship is not independence. |
| Function grounding | `reference_function_source`, `measured_subject`, `functional_endpoint`, `claim_scope`, `characterization_status`, optional grounded site set | These records establish what could be transferred. A database title, Pfam name, or family membership is not a measured activity. Unknown function grounding does not erase native scores; the functional-transfer component stays unknown. |

This version's worked formulas use amino-acid coordinates. For translated BLAST, retain frame and nucleotide coordinates and provide an explicit nucleotide-to-peptide map before reusing these coverage formulas. A nucleotide length is not an amino-acid denominator.

## 2. BLAST local-alignment cells

The authoritative native fields are per HSP, not per paper, family, or subject-name occurrence. NCBI documents `score`, `bitscore`, `evalue`, `length`, `nident`, `positive`, `gaps`, endpoint coordinates and query-coverage variants in the [BLAST+ manual, Appendix Table C1](https://www.ncbi.nlm.nih.gov/sites/books/NBK279684/). NCBI's [statistics tutorial](https://www.ncbi.nlm.nih.gov/BLAST/tutorial/Altschul-1.html), sections “The statistics of local sequence comparison,” “Bit scores,” “Database searches,” “The statistics of gapped alignments,” and “Edge effects,” gives the statistical relationships and their qualifications.

| Numerical cell | Input / calculation | Unit and what it evaluates | Missing/uncertainty treatment |
| --- | --- | --- | --- |
| `blast_raw_hsp_score` = S | Native `score`; optionally verify against the actual substitution scores and actual gap convention | Scoring-system points for this local alignment | Matrix name alone is insufficient when the implementation adjusts its scoring matrix. Preserve reported S if recalculation operands are missing. |
| `blast_hsp_bits` = B | Native `bitscore`; where applicable, B = (λS − ln K)/ln 2 | Bits after the specified BLAST statistical normalization | λ has inverse-raw-point units; K is the matching statistical scale. Use the parameters for this score and scoring regime, not guessed default matrix constants. |
| `blast_hsp_E` | Native `evalue` | Expected count under the search's random-sequence null at this score or better | Keep database/search-space and statistical-method provenance. It may exceed one. It is not a probability that a function is wrong. |
| `blast_identity_all_columns` | `nident / alignment_columns`; percentage = 100 × fraction | Fraction of alignment columns containing identical residues; gap columns remain in this denominator | Count from a retained alignment/traceback when available; do not replace this denominator by the shorter full protein. |
| `blast_identity_residue_pairs` | `nident / paired_residue_columns` | A separately named gap-excluding identity fraction | Not the same cell as native percent identity. Missing traceback/counts leave it unknown. |
| `blast_positive_fraction` | `positive / alignment_columns` | Fraction scored as positive under the actual substitution scheme | Not identity or functional-site preservation. Unknown if `positive` is absent. |
| `blast_query_span_fraction` | Inclusive query span divided by declared query length | Fraction of supplied query occupied by the HSP span | Span includes query residues opposite subject gaps. Keep full-target and supplied-target denominators separate. |
| `blast_reference_span_fraction` | Inclusive subject span divided by actual reference length | Fraction of the reference occupied by the HSP span | Not “query coverage”; not proof of matching the same complete architecture. |
| `blast_query_paired_fraction` | Count query residues paired to an actual reference residue / declared query length | Fraction with residue-to-residue correspondence | Requires alignment map; endpoints alone cannot remove insertions. |

For the simple single-HSP Karlin–Altschul regime, let Ω = m_eff n_eff be the **effective** search space, in residue-pair opportunities. Then

    E = K Ω exp(−λS) = Ω 2^(−B).

Thus changing only Ω by a factor a changes E by a and leaves the alignment's S and B unchanged. The effective lengths may differ from physical lengths; `dbsize` and `searchsp` can override search operands. Never substitute a database's number of sequence records for its residue-length operand in this equation.

The equation is not permission to overwrite any reported E-value. The inspected current NCBI source has both `BLAST_KarlinStoE_simple` and `BLAST_SpougeStoE`; the latter uses additional score/length-dependent finite-size terms. Linked-HSP/sum statistics are another scope. Where the actual mode is not the simple regime, retain native E and its method. A reconstruction requires all operands and the same versioned procedure, or returns `not_identifiable`. [NCBI blast_stat.c, functions at source lines 4158 and 5177](https://www.ncbi.nlm.nih.gov/IEB/ToolBox/CPP_DOC/doxyhtml/blast__stat_8c_source.html).

For verification of a conventional additive alignment, S is the sum of actual substitution contributions minus gap costs. If the declared gap convention is g_open + length × g_extend, use exactly that expression. Some software expresses the opening term differently; a gap length must not be counted twice by importing another convention. BLAST's [glossary, “raw score”](https://www.ncbi.nlm.nih.gov/sites/books/NBK62051/) specifies its G + Ln convention. Heuristic search output does not assert that every possible alignment has been scored or that a missing HSP has score zero.

## 3. HMMER3 / Pfam numerical cells

HMMER3's principal score is a sequence/profile ensemble score, not the raw score of the one displayed alignment. Its [3.4 manual, pages 10–11](https://eddylab.org/software/hmmer/Userguide.pdf#page=10) distinguishes Forward ensemble scoring from an optimal pairwise alignment. Preserve final bias-corrected native scores. Do not sum emission scores along the displayed MEA alignment and call that the reported Forward score.

| Numerical cell | Native input | Unit / calculation / meaning |
| --- | --- | --- |
| `hmmer_sequence_bits`, `hmmer_sequence_E`, `hmmer_sequence_bias_bits` | `domtblout` fields 8, 7, 9, or `tblout` fields 6, 5, 7 | One whole sequence/profile comparison. These fields repeat on domain rows; count them once per comparison. |
| `hmmer_domain_bits`, `hmmer_domain_bias_bits` | `domtblout` fields 14, 15 | One domain envelope's score and the correction already applied, in bits. |
| `hmmer_domain_iE`, `hmmer_domain_cE` | `domtblout` fields 13, 12 | Same domain tail probability with different search-space multipliers; not two corroborating measurements. |
| `hmmer_best_domain_bits`, `hmmer_best_domain_iE` | `tblout` fields 9, 8 | Native best domain summary; references a domain contribution already present in `domtblout`. |
| `hmmer_domain_count_reported` | `tblout` field 17 or repeated `domtblout` field 11 | Count of reported domains; do not confuse with posterior expected domain count (`tblout` field 11). |
| `hmmer_profile_span_fraction` | `(hmm_to − hmm_from + 1) / M` | M is the number of profile match states. Includes deleted match states between endpoints. |
| `hmmer_profile_emission_fraction` | Number of profile match states aligned to an actual sequence residue / M | Requires the retained alignment map; excludes deleted match states. |
| `hmmer_sequence_alignment_span_fraction` | `(ali_to − ali_from + 1) / L` | L is actual sequence length; includes inserted sequence residues inside the reported alignment. |
| `hmmer_sequence_envelope_span_fraction` | `(env_to − env_from + 1) / L` | Distinct location-uncertainty span, not aligned-residue coverage. |
| `hmmer_native_acc` | `domtblout` field 22, copied with version/rounding | A native alignment-accuracy summary, not function confidence. No generic extra multiplier is assigned. |
| `pfam_sequence_GA_margin_bits` | `hmmer_sequence_bits − GA1` | Distance from this model/version's sequence gathering threshold; optional if GA1 exists. |
| `pfam_domain_GA_margin_bits` | `hmmer_domain_bits − GA2` | Distance from this model/version's domain gathering threshold; optional if GA2 exists. |

The [manual, pages 67–72](https://eddylab.org/software/hmmer/Userguide.pdf#page=67) defines the tables. In `hmmscan`, the native target is the profile: `tlen=M`, `qlen=L`. In `hmmsearch`, the native target is the sequence: `tlen=L`, `qlen=M`. HMM coordinates always address the profile and alignment/envelope coordinates always address the sequence. Normalize those roles explicitly; a parser must not apply `tlen` as the sequence denominator in both programs.

For final protein Forward scores in the inspected HMMER 3.4 path, use the actual profile's `STATS LOCAL FORWARD τ λ_H` parameters. τ has bit units, and λ_H inverse-bit units. The model's native tail function is

    p_tail(B) = 1                         if B < τ
              = exp[−λ_H(B − τ)]         if B ≥ τ.

For the matching score scope:

    E_sequence = Z × p_tail(B_sequence)
    iE_domain  = Z × p_tail(B_domain)
    cE_domain  = domZ × p_tail(B_domain).

`Z` is the searched number of target sequences (`hmmsearch`) or target profiles (`hmmscan`), unless explicitly overridden. `domZ` normally counts targets passing the sequence reporting threshold; an explicit override can replace it. These positive scale operands may be real-valued overrides even though actual counts are integers. `iE/cE = Z/domZ` when using the same nonzero, unrounded domain tail probability. Changing the database or reporting selection can change those E-values without changing the domain score. The parameters are not BLAST's λ and K. [HMMER 3.4 p7_pipeline.c, lines 774–884](https://github.com/EddyRivasLab/hmmer/blob/hmmer-3.4/src/p7_pipeline.c#L774), [p7_tophits.c, lines 962 and 1751–1777](https://github.com/EddyRivasLab/hmmer/blob/hmmer-3.4/src/p7_tophits.c#L1751), [Easel 0.49 exponential-tail routines, lines 122–145](https://github.com/EddyRivasLab/easel/blob/easel-0.49/esl_exponential.c#L122).

Native `score + bias` reconstructs the corresponding pre-bias score to printed precision; it is not an independent contribution or an invitation to remove the correction. The sequence score is not generally the sum of displayed domain scores: HMMER3 accounts for alignment ensembles, length/null terms, and can use its native reconstruction score. Even a single domain can differ from the full-sequence score. Do not add sequence and domain scores or recompute sequence E by multiplying domain E-values. [Manual, pages 33–38](https://eddylab.org/software/hmmer/Userguide.pdf#page=33); versioned source above.

Native `acc` needs particular care: the manual describes mean alignment accuracy, while the inspected 3.4 `domtblout` writer specifically emits stored `oasc / (env_to − env_from + 1)`. Preserve that native value; do not multiply it by the alignment span to invent an exact expected matching-residue count. Per-residue PP symbols are intervals: for example `9` denotes approximately 0.85–0.95 and `*` 0.95–1.00. A midpoint is not an observed posterior. [Manual, page 39](https://eddylab.org/software/hmmer/Userguide.pdf#page=39); [writer line 1777](https://github.com/EddyRivasLab/hmmer/blob/hmmer-3.4/src/p7_tophits.c#L1777).

Pfam GA values are curated model-specific sequence/domain thresholds, not observed hit values or calibrated probabilities of a specific function. A margin is an ordinary subtraction in matching units, not a cross-profile calibration. The [Pfam glossary, “Gathering threshold”](https://pfam-docs.readthedocs.io/en/latest/glossary.html#gathering-threshold-ga) and [HMMER manual, page 100](https://eddylab.org/software/hmmer/Userguide.pdf#page=100) establish this distinction. A sequence-similarity-network construction threshold likewise does not populate any hit score: it describes which edges were admitted. No network measurements or network-specific policy are adopted here.

## 4. Coverage, site correspondence, missing values, and uncertainty

Coverage over multiple rows uses a union of actual positions, not a sum of percentages:

    C_query_union = |union_j Q_j| / L_query.

Choose the position set explicitly: span positions, paired residues, or profile-emitting positions. An interval span includes insertions/deletions as described above; it does not establish residue-to-residue mapping or coherent domain order. Overlapping envelopes also do not establish duplicate biological domains. Keep alignment and envelope unions separately.

If only a fragment is supplied, its own coverage can be computed. Observed full-target coverage remains unknown when full length is unknown. For observed aligned count a and supplied length L_s known to be part of the target, a/L_full is bounded by 0 to a/L_s when only L_full ≥ L_s is known. This is a bound on the observed contribution, not on possible correspondence in unsupplied sequence. Unknown fragment boundaries must not be treated as whole-protein ends.

Site correspondence requires an independently grounded set of reference sites and their meanings. Let N be the declared number of relevant reference sites, m the number with an assessable target correspondence, k the number whose target residue satisfies a stated allowed-residue set, and u=N−m. A directly mapped incompatible residue is assessable; an unresolved mapping is unknown. Then

    assessed_site_fraction = m/N
    compatible_among_assessed = k/m                    (if m > 0)
    observed_compatible_fraction = (m/N)(k/m) = k/N     (if m > 0)
    possible_compatible_fraction ∈ [k/N, (k+u)/N].

For m=0, the conditional fraction is null, the observed compatible lower bound is 0, and the possible fraction is [0,1]. For N=0 or an unknown site set, the site component is `not_applicable` or `not_identifiable`, not automatically one. Counting sites equally defines a correspondence fraction only; it does not assert equal catalytic importance. Different site weights require actual stated weights and their evidential basis. One indispensable site cannot be made optional by a large global alignment score.

The reader's site operands are exact reference positions, allowed residues with their source, target positions/residues or declared alignment gaps, and mapping uncertainty. A profile-to-target map additionally needs a grounded reference-to-profile map to say anything about a particular characterized reference residue. Profile consensus identity alone does not supply that chain. This arithmetic is a proposed A101 component definition, not a result claimed by the documentation sources or a universal functional-residue gate.

Native scores are deterministic conditional on their actual inputs and implementation; that does not remove model error, alignment ambiguity, or function-transfer uncertainty. Keep these separate from printed rounding. Printed E=0 may be underflow or formatting: use a certified bound only if the producer supplies one; otherwise retain `reported_zero_bound_unknown`. Never apply `−log10(0)=infinity` as evidence or clip E to an invented floor. A nonreported hit is unknown unless a complete, appropriately characterized output procedure establishes an actual censoring bound. Failure, omitted output, a search filter, and measured incompatibility are different outcomes.

## 5. Duplicate, overlapping, and shared-family results

| Situation | Numerical handling and contribution boundary |
| --- | --- |
| One HSP/domain shown in text, table, API, or a paper | One comparison record with several representations. Repeated native fields add no new score. Equal numbers alone do not establish identity. |
| Same target/reference pair rerun or searched in another database | Preserve the different search/statistical contexts. It is another analysis of the same sequence evidence, not independent biological replication. |
| Overlapping BLAST HSPs | Compute union coverage. Do not add identities or scores over shared residue pairs. A single summary can select a declared representative HSP; selection must also be reproduced in calibration. |
| Nonoverlapping HSPs | Counts can add when the counted positions truly are disjoint. Raw-score sums are only a newly defined disjoint-HSP statistic under identical scoring rules; they are not automatically one native alignment score or E-value. Connecting gaps, order/frame consistency and linked-HSP statistics require their own defined treatment. |
| Several HMMER domain rows for one sequence/profile pair | Retain each domain's native components and the single sequence-level value. The full-sequence score already reflects the same sequence/profile evidence. |
| Repeated domains in one protein | Distinct regions can contribute to union coverage and architecture. Repetition does not establish independent experiments or justify adding full-sequence support once per repeat. |
| Overlapping profiles from a Pfam clan | These are related family alternatives on shared residues. Preserve the original wrapper's competition outcome and the raw alternatives, if available. They are not independent votes. |
| BLAST reference protein belongs to the profile's family/seed | Both tools interrogate shared sequence/family information. Preserve the relationship and use a joint calibration or a declared representative; do not multiply purported independent confidences. |
| Strong matches to references with different characterized activities | Preserve the competing function-specific rows and their scores. A native difference may describe the competition; neither summing both as support nor calling one nondetection resolves the functional ambiguity. |

The [HMMER web documentation, “Profile HMM Matches → Pfam”](https://hmmer-web-docs.readthedocs.io/en/latest/result.html#pfam) describes its same-clan competition using the best E-value. This is a documented wrapper behavior, not an automatic property of every raw `hmmscan` result. Do not silently run or impose it here. Related profiles without a recorded clan also cannot be presumed independent.

## 6. Valid arithmetic versus unsupported combinations

| Operation | Defensible meaning / conditions | What it does not establish |
| --- | --- | --- |
| S → B → E | The matching native statistical model and operands, as above | Extra independent support from three encodings of one score |
| B − GA | Model/version-matched bits above its own threshold | Calibrated equivalence to another profile's margin or specific activity |
| B1 − B2 | A descriptive score contrast at declared scope; with identical BLAST λ,K it equals λ(S1−S2)/ln 2 | Probability that one function is right; correction for trying many alternatives |
| Sum of disjoint position counts | Union count when sets are disjoint | Permission to sum overlapping HSP scores or count one site twice |
| Product `(m/N)(k/m)` | Exactly k/N; the assessed/compatible site decomposition | Two independent proofs or a complete function score |
| Sum of native bit scores | A descriptive new statistic only if explicitly defined; a true joint log-likelihood interpretation needs a valid joint model | Automatic cross-tool, cross-profile, or full-plus-domain functional support |
| Product of likelihood ratios | Requires a declared joint likelihood or justified factorization on the same event definitions | Independence merely because the algorithms differ |
| Product of E-values or `(1−E)` terms | No generic native functional meaning | A probability of shared function or confidence in an annotation |
| Sum of expected counts | Can describe distinct predefined counted events by linearity of expectation, with their nulls and trials identified | An aggregate support score from summing each observed hit's E-value |

Even BLAST bit-score summation repeats normalization offsets. Under one λ,K and an artificially defined raw sum S_total=Σ_j S_j,

    B(S_total) = Σ_j B_j + (n−1) ln K / ln 2.

That algebra still does not make disjoint HSPs one alignment or supply their combined search significance. Different scoring parameters invalidate even that restricted identity.

Subtracting pure log-likelihood-ratio scores can cancel a **verified common null** when both describe the same observed data and sample space. Final HMMER scores can have different domain envelopes, null2 corrections, and reconstruction terms; two reported bits values alone do not verify those conditions. A BLAST bit score and a HMMER Forward bit score have neither a guaranteed common functional alternative nor the same native scoring construction.

### Boundary with raw pair/self normalization

If another proposed sheet asks for, for example,

    R_raw = S(q,r) / sqrt[S(q,q) S(r,r)],

its exact raw pair and self scores must come from the declared common scoring scheme, sequence material, alignment scope, gap treatment, and normalization definition, with positive self-score product. An unscored self comparison is missing; a hit bit score, E-value, profile score, threshold, or presumed identity cannot fill it. This contract does not endorse that ratio or establish a universal [0,1] bound for arbitrary scoring systems. Its intended meaning and any bound need to be established for the actual scheme. BLAST's affine raw-to-bit transformation means substituting B for S changes the ratio, even if all three B values are correctly calculated. A HMMER profile comparison has no automatically corresponding pair of raw sequence self scores.

## 7. One finite, unadopted route for combining BLAST and HMMER

This proposal answers how native inputs could enter explicit sums and products without asserting that their bit scores are interchangeable. It is optional, not an instruction to run both programs or a universal evidence threshold. It concerns a defined functional claim that has emerged from evidence, not an initial annotation prerequisite.

For **one target, one independently grounded functional claim, and one shared sequence/family evidence group**, fix a reproducible within-program representative-selection rule. A minimal example selects the maximum BLAST HSP bit score and maximum HMMER domain bit score among the group's already recorded, scope-compatible comparisons; retain the operands supplying each. The same database search, grouping, selection, and missing-input pattern must be used for calibration. This choice is a proposed feature definition, not a way to manufacture independent hits or resolve ambiguous family groupings. Unknown grouping leaves the combined component unknown.

Let b be the selected BLAST HSP bits, h the selected HMMER domain bits, c_q and c_r the BLAST query/reference span fractions, c_m the HMMER profile-span fraction, i the BLAST all-column identity fraction, and s the compatible fraction over the grounded N-site set. Define

    z = β0 + βb b + βh h + βbh b h
           + βq c_q + βr c_r + βm c_m + βi i + βs s
    C_group = 1 / (1 + exp(−z)).

All fractions are dimensionless. βb and βh have units inverse bits, βbh inverse bits squared; the other coefficients and z are dimensionless. There is no numerical default for any coefficient. Native bit scores remain inputs, the interaction permits a joint relationship, and no conditional independence is asserted. The interaction does not itself prove that dependence has been adequately modeled.

The exact calibration operands would be:

1. A versioned table of these numerical feature vectors, their missing-input patterns and grouping/selection procedure; one example represents a distinct characterized comparison, not a duplicate paper or rerun.
2. Binary outcomes y defined by **independent experimental functional characterization at the stated endpoint**: same specified activity versus a characterized different activity. Unknown activity is not a negative label. Shared-profile membership must not supply y. Specify organism/construct and claim scope.
3. Family-group identities, data/model-training membership and held-out splits that prevent copies of the same protein, experiment, or near-equivalent family example from supplying both fitting and validation evidence. The desired application population and its class prevalence must be specified before any probability interpretation.
4. A jointly fitted coefficient vector. One fully specified candidate fitting objective, without an invented penalty, is `argmin_β Σ_g (1/n_g) Σ_{j∈g} [log(1+exp(z_j)) − y_j z_j]`. Here n_g counts distinct training examples in family group g; equal family weights prevent a large represented family from gaining weight solely through duplicate abundance. Complete separation/nonunique or nonfinite fitting returns `calibration_fit_unidentified`, not invented coefficients.
5. Held-out calibration/discrimination results at the actual functional endpoint and complete coefficient samples from resampling **groups**, if uncertainty is requested. Resampling or fitting is not performed here. A numerical logistic output is not an established probability merely because it lies in [0,1].

Without the dataset, coefficients and validation scope, `C_group.value=null`, `status=not_identifiable`, `reason=calibration_absent`; its mathematical output range [0,1] is only a vacuous bound. A BLAST-only or HMMER-only result can use a separately calibrated feature subset if supplied; unavailable tools are not zero-imputed and do not become mandatory. Missing native scores without a finite bound usually leave [0,1]. With fixed coefficients and a bounded site fraction, evaluate both endpoints and take their min/max; do not silently call the lower bound a point estimate. Printed-score rounding can be propagated the same way, preserving correlations where the same operand appears twice.

This defines one group component, not a sum over homolog families or an inter-axis policy. Multiple groups can share references, residues, profiles, experiments and functional conclusions; adding their `C_group` values requires a separately specified aggregation. No A105 transform, fixed transfer grade, global annotation formula, or independence assumption is imported.

## 8. Populating-function boundary and unfinished work

These are exact **unimplemented reader specifications**, not new runtime functions:

| Future reader/calculation | Required inputs | Exact output cells |
| --- | --- | --- |
| BLAST record reader | Original output, matching schema/version, scope and input lengths, statistics/options; retained traceback where present | S, B, E, alignment/count/coordinate cells, producer precision, search-space/statistical provenance |
| HMMER protein reader | Native table and headers, program/version, model metadata and statistics, optional alignment/PP data | Sequence/domain score/E/bias cells with normalized sequence/profile roles; coordinates, counts, native accuracy, optional GA margins |
| Coverage calculator | Typed position sets and explicit length denominators | Span, paired-residue, profile-emission and union fractions, separately named |
| Site correspondence reader | Grounded site set, allowed residues, reference/profile/target mapping and uncertainty | N,m,k,u; assessed/compatible fractions and bounds |
| Optional joint component calculator | Selected native feature vector, established grouping and a supplied calibration artifact | z and `C_group` or bounds/status; no value when essential calibration is absent |

The native operand definitions, calculation boundaries, two filled synthetic program-family rows and checked arithmetic are delivered. Published function-transfer cases, actual calibration, accepted combination choices, implemented populating readers, user feedback on these proposals, and full A101/W04/W05 completion remain outstanding. The synthetic examples are not substitutes for the overall goal's contrasting published cases.
