# A101 sequence-homology numerical sheet — proposed convention 015

## Goal, status and the numerical choices being proposed

Deliver a usable numerical sheet for sequence evidence connecting supplied
material to characterized reference functions, with complete arithmetic for
multiple references, overlapping comparisons, several tool profiles, partial
scope and conflicting functions. This is a **proposed index convention** for
review. Every mathematical choice below is specified, so missing calibration
does not conceal an undefined combination. Its numerical scale has not been
biologically calibrated; a value of 0.6 is not a 60% function probability.

The three responsibilities remain investigation prompt, numerical sheet and
separate functions populating the sheet. This file supplies the sheet. Exact
reader inputs/outputs are specified in READER_IO_UNIMPLEMENTED.md; none is
implemented. No prompt, production scorer, publication, W05 connection, search
or alignment job is supplied. No whole-axis completion or adoption is claimed;
A105 remains first in the fixed ten-sheet accounting.

Inputs may begin as sequence, selected file contents/regions or snippets.
Neither a candidate function nor a public gene name is required. Native
comparison rows can be filled immediately. A function-specific row is added
when evidence supplies a functional hypothesis and characterized references.

The convention extends the prior monotone mathematical review004, rather than
its rejected negative bit-score interaction. It retains 0.025/bit for BLAST and
0.020/bit for HMMER as **declared illustrative scales**, changes their bounded
mapping, and explicitly supplies the previously missing reference/region/tool
aggregation. The earlier 0.6297865656 example remains its own historical rule;
it must not be relabeled as this rule's result.

## 1. Sheet structure and what each row means

One sheet concerns one supplied target material and one versioned set of
observed comparisons. Store numerical cells separately from supporting source
and scope records. A native comparison is not an experiment on target activity.

| Row | Numerical contents | Supporting meaning |
| --- | --- | --- |
| Material | Supplied length, full length if known, selected coordinate sets | Actual sequence/file selection; complete/fragment/unknown; aa or nt; translated comparisons need an explicit peptide/frame map. |
| Native comparison | Native score(s), E-value(s), bias, lengths, alignment counts and coordinate maps | Exact software/version/settings/search space, query/reference roles, score scope, input identity, reporting completeness. |
| Reference function | No reputation or confidence grade | Actual characterized molecule, endpoint, source experiment, scope and permitted functional labels; annotations alone do not establish measured activity. |
| Feature panel | N, m, k, fractions and bounds for declared sites or sequence predicates | Why this particular feature matters to the stated function; exact coordinates/allowed residues and source; functional necessity is a stronger assertion than relevance. |
| Function/region calculation | Per-comparison weights, per-position maxima, region indices, feature factor, combined A101 index/bounds | The function can emerge during investigation. Broad resemblance and a particular reaction remain distinct scope rows. |

Every numerical cell has value (finite number or null), unit, origin
(reported/derived/synthetic), native printed token when present, lower/upper
bounds when available, and status. Status values are observed, derived,
not_reported, not_assessed, not_applicable, incompatible_scope,
ambiguous_mapping, threshold_censored and reported_zero_bound_unknown.
Bounds are labeled rounding, censoring, missing_operand or joint_sensitivity.
No bound here is silently a statistical confidence interval.

Point-null with an interval is a usable incomplete numerical cell. Unknown
values are never filled with invented observations. Supporting counts report
distinct sequences, profiles, native analyses and characterization experiments
separately; none is a publication-count multiplier.

## 2. Native quantities and denominators

The full native definitions in the inspected contract010 remain applicable.
This table states the fields this proposal consumes and the fields it preserves
without adding the same evidence again.

| Cell | Input and exact calculation | Unit / role / uncertainty |
| --- | --- | --- |
| BLAST S, B, E | Original HSP score, bitscore, evalue | Raw points, bits, expected null hits. Preserve all; the combination uses B once. |
| BLAST statistical reconstruction, when actually identified | B=(lambda*S-ln K)/ln 2; E=Omega*2^(-B), only for the identified simple single-HSP regime | Omega is effective residue-pair search space, not database record count. Other native modes keep their reported E and matching method. |
| BLAST all-column identity i | n_identical/alignment_columns | Dimensionless, including gap columns in denominator; unresolved symbols stay explicit. Native percent identity converts by /100. |
| BLAST paired coverage | Distinct target residues paired to a reference residue / actual target-scope length; analogous reference count / reference-scope length | Requires a correspondence map. Endpoint span is a different diagnostic and cannot silently fill this cell. |
| BLAST span coverage | Inclusive endpoint span / declared sequence length | Retained diagnostic. Multiple spans use coordinate union. |
| HMMER sequence score/E/bias | domtblout columns 8/7/9, once per sequence/profile comparison | Bits, expected null hits, bits. Repeated sequence fields on domain rows are one result. |
| HMMER domain score/bias | domtblout columns 14/15 | Bias-corrected bits for one envelope; these populate the proposed domain channel. |
| HMMER domain iE/cE | domtblout columns 13/12 | Same tail with different search-space multipliers; not independent support. |
| HMMER map/coverage | Profile match states emitted against actual sequence residues / M; corresponding sequence residue set / target-scope length | M counts model match states. Insertions and deleted match states are not emitted pairs. |
| HMMER span/envelope/acc | Profile span/M, sequence alignment span/L, envelope span/L and reported acc | Separate diagnostics. acc is retained as printed, not function confidence or an invented pair count. |
| Pfam sequence/domain margin | Matching B-GA1 or B-GA2 | Bits above that model/version's threshold, not cross-profile probabilities or additional evidence. |
| Site/predicate panel | Definitions in section 5 | Fractions over explicit grounded feature denominators. |

In hmmscan the sequence is the query and profile the target; in hmmsearch those
roles reverse. Keep coordinates in biological sequence/profile roles. The
inspected protein Forward path uses its actual tau and lambda_H:

    p_tail(B)=1 if B<tau, otherwise exp[-lambda_H*(B-tau)]
    E_sequence=Z*p_tail(B_sequence)
    iE_domain=Z*p_tail(B_domain)
    cE_domain=domZ*p_tail(B_domain).

These equations preserve score/statistics meaning; they are not additional
terms in the A101 index. E=0 stays a displayed/censored value. With no certified
bound it is reported_zero_bound_unknown; never take -log(0), invent a floor,
or infer infinite evidence. A finite reported B can still populate this
bit-score convention. Changing search space changes E without changing B;
this proposed bit-score index deliberately remains unchanged. Consequently it
does **not** claim to correct for search multiplicity or database composition.

For multi-domain proteins use domain scores/maps for region-specific rows.
A whole-sequence HMMER row may be used only in a separately named
whole_sequence profile with a map and a function grounded at that same whole
scope; its coefficient is 0.020/bit under this proposal. It replaces domain rows
for that sequence/profile in that calculation. Never mix whole-sequence and
its domain rows as separate contributing hits. No full-sequence B is cropped,
divided or rebranded as a domain score.

For a BLAST HSP spanning more than the functionally relevant reference region,
the HSP score cannot be claimed to originate solely in the smaller region.
Keep its original scope and score. A smaller function-region row requires an
already available matching scoped score or is unknown; no run is compelled.
The same restriction applies to profile envelopes and model regions.

## 3. A finite native-score index for each observed comparison

Let j denote one scope-compatible native comparison, t its algorithm family,
B_j its original bit score, P_j the set of target residues paired to reference
residues (BLAST) or model match states (HMMER), and R_j the distinct paired
reference positions or emitted model states. Let L_ref,j be the declared
reference region length or model-state count for this native scope. Require
positive length and 0 <= |R_j| <= L_ref,j; disagreement returns a typed invalid
input, never clipping a coverage measurement.

All coefficients in this section are **proposed conventions**, not measured
properties or category grades:

    a_BLAST = 0.025 / bit
    a_HMMER = 0.020 / bit
    f_t(B) = 1 - exp[-a_t * max(B,0)]
    r_j = |R_j| / L_ref,j
    w_BLAST,j = f_BLAST(B_j) * r_j * (0.5 + 0.5*i_j)
    w_HMMER,j = f_HMMER(B_j) * r_j.

Both w values lie in [0,1]. They evaluate the recorded comparison's native
strength, its reference extent, and, for the pairwise profile, its measured
identity. The BLAST identity term is one joint feature with the native score,
not an independent biological replication. HMMER has no invented identity to a
single consensus protein. Model/sequence scope and functional grounding still
matter; these scalar mappings cannot make an uncharacterized profile specific.

The chosen native scales give f_BLAST(40 bits)=f_HMMER(50 bits)=1-exp(-1).
They use the prior review's inverse-bit scales but are not fitted biological
equivalences. The 0.5/0.5 pair-identity mixture deliberately retains substitution
information when exact identity is low. It has no empirical optimum established
here. Zero/negative reported bits contribute zero positive native strength under
this declared transformation; missing bits are unknown, not max(0,missing).

Only supported native units can enter a channel. A raw score can supply B if
the native conversion and all parameters are actually known. E alone, a GCG
identity percentage or an SSN cutoff cannot populate B. Other tools keep their
native fields but need a separately declared monotone transformation before
entering the same compiled index; this proposal's finite supported domain is
protein BLAST and HMMER. Unsupported input returns unsupported_score_profile,
not a guessed tool weight.

## 4. Multiple references, tools, functional alternatives and regions

For each emerging function F, retain its distinct function-grounded reference
groups. Several references, clans, repeated HSPs, profile members and searches
can share target residues. This convention never assumes those are independent.
For each residue p in target scope and each algorithm t, calculate:

    M_t,F(p) = max({w_t,j : p in P_j and j supports F at this scope} union {0}).

The maximum runs over **all** recorded compatible references/groups for this
function and tool, not one sum per family or paper. Overlaps and duplicates
therefore cannot add votes. New distinct references can improve the maximum or
cover new residues. Genuine independent functional characterizations are counted
as provenance but do not receive a numerical replication bonus in A101. That
is an explicit conservative choice, not an assertion that replication lacks
scientific value. A repeated identical search or paper adds no change.

Let G_F be the actually observed and characterized functions incompatible with
F **at the same claim scope**, rather than every other annotation string:

    O_t,F(p) = max({w_t,j : p in P_j and j supports a member of G_F} union {0}).

A broader parent function, a second compatible activity, or a function in a
different domain is not automatically contradictory. The relationship must be
declared as compatible, nested, incompatible_at_scope or unresolved from the
functional meanings and source evidence. An unresolved assignment produces
bounds, not an intuitive signed grade. A single ambiguously characterized
reference is not duplicated into certain F and certain G observations.

The target scope consists of nonempty, source-defined required regions D_d.
Use one region for an undivided scope. Distinct biological requirements can
define several regions; printing blocks cannot. Overlapping region requests
are merged by transitive overlap and set union before calculation, preventing
the same residues from becoming extra requirements. Unknown boundaries remain
unknown. The denominator L_d=|D_d| is fixed for each resulting region.

Algorithm profiles are explicit:

| Declared calculation profile | Tool weights |
| --- | --- |
| BLAST only | pi_BLAST=1 |
| HMMER only | pi_HMMER=1 |
| BLAST plus HMMER | pi_BLAST=pi_HMMER=0.5 |

The profile records which analyses supply the calculation. It is not selected
by maximizing the final score. A missing operand in an included channel cannot
be removed as though the tool was never used. A separately reported subset
calculation is allowed and clearly labeled; the two profile scores are not
claimed calibrated to one another. No second program is mandatory.

For each region:

    H_d(F) = sum_t pi_t * [sum_(p in D_d) M_t,F(p)] / L_d
    X_d(F) = sum_t pi_t * [sum_(p in D_d) M_t,F(p)*O_t,F(p)] / L_d
    C_d(F) = H_d(F) - X_d(F)
           = sum_t pi_t * mean_(p in D_d){M_t,F(p)*(1-O_t,F(p))}.

H_d is observed correspondence support; X_d is the explicitly defined penalty
for overlapping observed alternative-function correspondence; C_d is the
remaining index. Native evidence and its contradiction stay printable
separately. Increasing an F weight cannot lower C_d when competitors are fixed;
increasing an incompatible competitor cannot raise it. The penalty is a
scoring convention for ambiguity, not an estimate that a G hit disproves F.

For K required regions, use the equally weighted geometric mean:

    H_F = product_d H_d(F)^(1/K)
    C_native,F = product_d C_d(F)^(1/K).

This is a specified conjunction of required-region support, not multiplication
of independent probabilities. Duplicating a requirement cannot add a term.
An empty required-region list is invalid_scope; one region reduces to its
ordinary C_d. All factors zero or any zero factor gives zero observed index.
A missing/unobserved region is kept as uncertain when its measurement is
unknown; absence of observed support does not establish biological absence.

G_F may be empty because no incompatible characterized comparison was recorded.
Then X_d=0 is the penalty from the **recorded set**, not a measured negative
search. The calculation is labeled recorded_competitors_only, with alternative
coverage unassessed or partial. No search of competitors is required to execute
or investigate. Unknown alternatives cannot justify a specificity claim; the
open-alternative sensitivity range is [0,C_native,F] if arbitrary unobserved
overlapping alternatives remain possible. This range is not a confidence
interval. The finite current-evidence index remains separately visible.

## 5. Sequence features qualify a function at its actual scope

For each source-grounded panel l, declare N_l unique site/predicate questions.
Let m_l be assessed and k_l be compatible under the stated allowed symbols or
predicate. A mapped incompatible residue is assessed. An unresolved map or
unseen snippet region is unknown. Exact identity and functional compatibility
are different predicates; an allowed substitution set cannot be invented.

    assessed_l = m_l/N_l
    compatible_among_assessed_l = k_l/m_l  (null when m_l=0)
    s_l in [k_l/N_l, (k_l+N_l-m_l)/N_l].

For all-assessed panels s_l=k_l/N_l is a point. N_l must be positive;
an absent/unknown panel is not a panel with value one. A motif occurrence count
can supply a declared presence predicate 1(count>=1), with its exact sequence,
pattern, search boundaries and allowed alphabets. This is a measured sequence
event, not a numbered confidence category. Negative from a whole supplied
record and unknown from a snippet are distinct.

Collapse duplicate predicates within a panel. Duplicate panels are one panel.
If a predicate occurs in several panels, give it only one scored ownership
under the declared panel definitions; other occurrences are displayed links.
Panel definitions cannot be changed to remove an unfavorable measured feature.
Different but dependent features can share a map; this weighted composite never
claims statistical independence.

For L nonempty, relevant panels with no established strict necessity:

    A_F = (1/L) * sum_l s_l.

Equal panel weights are proposed policy. They keep a pocket panel containing
four positions from automatically receiving four times the weight of one
cofactor-pattern question. Per-panel fractions remain visible. This evaluates
feature correspondence for the scoped inference, not enzyme activity.

An independently established **necessary** sequence feature is stronger than
a merely associated motif. Necessary predicates form a separate, deduplicated
set and are not also included in A_F. Let v_h be 1 when its stated necessary
condition is met, 0 when a mapped observation contradicts it, and [0,1] when
unresolved. Define V_F=product_h v_h. The product is logical conjunction, not
independence; no proven necessity is inferred just from conserved residues.
A contradicted indispensable feature cannot be compensated by a large bit
score. This affects that exact function row and does not erase broader family
correspondence. It is a numerical inference boundary, never a runtime stop.

Two explicitly named output forms are available:

    homology_only_index(F) = C_native,F
    feature_qualified_index(F) = C_native,F * A_F * V_F.

If no necessary predicate is established, the empty product V_F=1 is a neutral
operation labeled none_established, not an observed score of perfect necessity.
If the feature-qualified form has no identified relevant panel, A_F is unknown
with [0,1], so its point is null. It is never filled by the neutral empty mean.
If all relevant known predicates are necessary and no other panel is applicable,
A_F=1 is a neutral operation explicitly labeled all_features_in_necessary_set.
The homology-only form remains numerically available with its narrower meaning.

The selected output form is fixed in the calculation record and carried to a
future consumer. An unfavorable site cannot trigger a silent switch to the
homology-only form. A supplied snippet can still have a scoped homology result;
it cannot be relabeled as a complete protein or a complete necessary-site test.

## 6. Missingness, contradiction, uncertainty and nondetection

For every comparison provide lower/upper weights and guaranteed/possible paired
position sets P_minus and P_plus. Exact maps have equal sets. An unknown map has
an empty guaranteed set and possible positions restricted to the actual scope.
Do not extend a supplied fragment to unknown residues.

Monotonic f, identity and reference fractions give w_minus/w_plus by endpoint
evaluation; B missing without bounds gives f in [0,1]. A missing fraction gives
[0,1]. Native deterministic counts are conditional on the supplied map, not
independent Bernoulli draws. Do not attach binomial intervals to aligned sites.

    M_minus(p)=max({w_minus,j: p in P_minus,j} union {0})
    M_plus(p) =max({w_plus,j: p in P_plus,j} union {0})

Use the same construction for O. Then the fully specified conservative bounds
are:

    C_d,minus = sum_t pi_t * mean_p[M_minus(p)*(1-O_plus(p))]
    C_d,plus  = sum_t pi_t * mean_p[M_plus(p)*(1-O_minus(p))]
    C_native,minus = product_d C_d,minus^(1/K)
    C_native,plus  = product_d C_d,plus^(1/K)
    Q_minus = C_native,minus * A_minus * V_minus
    Q_plus  = C_native,plus  * A_plus  * V_plus.

These enclosure bounds remain valid without assuming independent scores,
features or maps. They can be wider than the feasible joint range. Preserve
shared-variable constraints and uncertainty provenance; do not call the
enclosure a joint probability interval. Point stays null whenever an essential
operand is non-point. Native producer rounding can supply an interval only
under its known rounding convention; precision of printed digits alone does
not quantify alignment/model/function-transfer error.

| Situation | Defined treatment |
| --- | --- |
| Same result in paper, dataset, API or repeated report | Reuse the same comparison; maxima and counts do not change. |
| Different references/profiles on overlapping target residues | Max within algorithm/function at each residue; never add a hit count. |
| New reference supports new target positions | It may increase mapped extent, with unchanged target denominator. |
| Strong native result for a different incompatible function | O increases at its actual mapped positions; both raw and net indices remain visible. |
| Contradictory characterizations of the same reference at the same endpoint | Keep the reference label unresolved; it has possible F/G assignment, yielding bounds. Do not create two certain experiments from one conflicted label. |
| Different endpoints or different conditions | They are not contradiction until the claim asserts their incompatibility. A105/A106 retain their actual measurements. |
| Complete output with no reported match | No observed positive row. Record search coverage/filters; failure to report a hit is not proof that every possible score is below a threshold. |
| Certified censoring of an eligible native comparison | Bound its score using the producer's proven reporting guarantee and exact statistics; otherwise score stays unknown. A heuristic prefilter does not establish such a bound. |
| E=0 | Preserve token and certified bound, if any. Finite B can still be used; no E-derived infinity. |
| Target full length unknown | Calculate only the supplied-scope row; full-target row is null. No invented whole-protein denominator. |
| Unknown reference characterization | Preserve native correspondence; specific-function membership remains unknown. |
| Absent entire algorithm | Use the declared one-tool profile. A missing value from an included algorithm stays an interval. |

Replication is not a reason to add a probability. Distinct characterization
experiments validate reference function on their own axes. Search analyses of
the same residues are shared sequence evidence even if software differs.
Experimental comparability and effect isolation affect what reference function
is grounded; this sheet does not replace their molecular-activity or
perturbation scores with new A101 numbers. A101 is not a compulsory transfer
multiplier on A102–A111 or on all possible evidence-transfer relationships.

## 7. Component/source trace and contrasting examples

Paper-specific science and source-populated cells are deliberately in three
separate packets so each can be inspected with its own required reset:

| Numerical component or boundary | Inspected source extent | Local packet / result category |
| --- | --- | --- |
| Scope/identity counts; exact denominator and missing native score | Complete retained parent conversion of Seffernick et al., DOI 10.1128/JB.183.8.2405-2410.2001; parent primary scope remains documented there | packet_003_tria.md; source-derived counts, no new native run |
| Separate recognition/motif panels; whole-record versus domain absence; coordinate conventions | Complete retained parent conversion of QueF-like paper, DOI 10.1021/cb200361w | packet_002_quefl.md; source-derived fractions and motif count |
| Network cutoff versus hit; assayed-source identity versus target mapping | Complete retained parent conversion of Hitchcock et al., DOI 10.1021/bi200680y | packet_001_coda.md; source-derived site and coverage distinctions |
| BLAST native field names, HSP scope, counts and reporting/search-space fields | NCBI BLAST+ Appendix Table C1, freshly opened; statistics tutorial sections local scores, bits, database searches, gapped statistics, edge effects | Primary official documentation; source links in READ_AND_CHECK_AUDIT.md |
| HMMER native domain/full score and E fields; roles; emitted acc denominator | Retained official 3.4 source p7_pipeline.c 774–884; p7_tophits.c 1697–1787, actually read here | Primary code definitions; no execution of native program |
| Exponential-tail and simple BLAST reconstruction | Retained official Easel source 122–145; NCBI blast_stat.c 4158–4175, actually read here | Native-statistic definitions, not functional scoring |
| Saturation scales, identity mixture, max aggregation, opposition penalty, geometric mean, panel average | This proposal, informed by the native contract010 and monotonicity review004 | Proposed mathematics only; no source is claimed to calibrate these choices |

WORKED_EXAMPLE.md provides a fully calculated multi-reference, multi-profile,
contradictory synthetic example, with native operands marked synthetic.
check_research_arithmetic.py checks that example, the source-derived fractions,
duplicates, region aggregation, missing bounds and monotonicity. It is a
research calculation, not a native parser or production scorer.

## 8. Exact remaining choices and limits

The proposed sheet's arithmetic is defined. The remaining choices for human
judgment are its **policy values and scientific adequacy**: saturation scales,
the identity mixture, maximum versus a future calibrated reference model, equal
tool weights, the opposition penalty, equal required-region weights and equal
feature-panel weights. They are printed and sensitivity-tested rather than
hidden behind future calibration. Alternative conventions would receive new
identities and additive records.

The three published packets provide contrasting, populated numerical
components, but none supplies the actual native score/map inputs required for
a complete real-case value under this convention. Missing real native
measurements are not repaired by synthetic fixtures. No complete real native
dataset-to-sheet reader demonstration, empirical calibration, user adoption,
reader implementation or W05 integration has occurred. Feedback on the actual
proposed sheet remains outstanding. These are the precise completion limits;
paper counts and successful arithmetic alone do not close the sheet checklist.

## 9. Additive clarification 001: supplied-query orientation and score allocation

The earlier HMMER descriptions in sections 2–3 describe a supplied sequence
compared to a function-grounded reference profile. They are too narrow for
phmmer, which constructs a profile from the supplied query. The following
orientation definition governs those symbols without changing the equations:

| HMMER comparison orientation | P_j in supplied target | R_j and L_ref,j |
| --- | --- | --- |
| Supplied target is the native sequence; function reference is a profile | Sequence residues paired to emitted model match states | Distinct emitted states of the function reference profile; denominator is that profile's match-state count |
| Supplied target is represented by the native query profile, as in phmmer | Original supplied-query residues reached through the explicit profile-state-to-query map and paired to native reference-sequence residues | Distinct paired residues in the characterized reference sequence; denominator is its declared scope length |

The HMMER score, E-values and their search spaces retain their native orientation
in both cases. Do not swap their native meanings to make the biological target
always the native sequence. A later-iteration profile requires its actual
state-to-original-query map and training dependencies; absent mapping leaves
P_j uncertain. It does not create a new independent HMMER vote. Paired-reference
coverage now has an explicit biological reference denominator in both modes.
The HMMER channel remains the same 0.020/bit convention, with no invented
sequence identity factor. Native web identity, when retained, carries its
documented denominator separately; it is not automatically BLAST all-column i.

This clarification is supported by the actually opened official HMMER 3.4
tutorial source, “The programs in HMMER,” and HMMER web Results, “Alignments”
and “Profile HMM Matches.” They document query-derived profiles, profile/query
coordinates and the hmmscan role reversal. These are documentation reads, not
another paper inspection or native analysis.

The uniform assignment of w_j to each paired target position is an explicit
score-allocation convention, not a native per-residue likelihood. No result
claims that each residue independently generated B_j. A functionally irrelevant
score scope cannot become relevant by allocating it to a small mapped subset.
That limitation and the requirement to retain original score scope remain even
when a required target region intersects a larger compatible comparison.

## 10. Additive clarification 002: uncertain membership and unavailable results

For function F, every row has guaranteed and possible membership in the
supporting set and, separately, in its same-scope incompatible set. Established
F membership enters both M_minus and M_plus; merely possible F membership
enters only M_plus. An established incompatible membership enters both
O_minus and O_plus; a merely possible incompatible membership enters only
O_plus. Thus, in section 6's maxima, lower sets require guaranteed membership
as well as guaranteed positions, and upper sets require possible membership
and possible positions. These two conditions are independent *tests of
eligibility*, not an assertion that biological observations are independent.

A source conflict that makes one label possibly F or possibly G can enter
both upper envelopes, but neither lower envelope. Those two assignments need
not be jointly feasible; the resulting bounds remain conservative. A tighter
optional sensitivity calculation enumerates only declared feasible assignments
and reports the minimum/maximum of the same complete formula. Unknown function
vocabulary is represented as possible membership within its declared scope,
not as guaranteed F support. No extra numerical credibility grade is used.

There are three different situations for required target positions:

| Available information | Recorded-set arithmetic and bounds |
| --- | --- |
| A supplied native result is complete for its declared analysis scope and has no compatible reported pair at p | Observed M(p)=0. This is absence of recorded correspondence; it is not a biological negative or an upper bound on every unreported score. Reporting/filter limits remain visible. |
| An included analysis result, or a declared part of its expected scope, is unavailable | Its unknown contribution needs an explicit availability envelope, defined below. The selected calculation point is null. A separately labeled observed-subset calculation may still be printed. |
| Other analyses, references or alternatives were never included in the declared calculation | They do not become missing rows or invented measurements. The result is conditional on its observed set; the open-alternative sensitivity already defined remains separate. |

For unavailable included information, record two position sets per tool:
U_t,F for positions at which that information could supply F support, and
U_t,G for positions at which it could supply incompatible support. They are
restricted to actual known supplied scope and native-analysis coverage. An
entire unavailable included analysis with unresolved function contents uses
both sets equal to that known scope. If its known contents concern only an
identified F comparison, use row-level operand bounds for that comparison;
do not invent a missing incompatible comparison. Unknown expected boundaries
produce a null full-scope calculation; a known supplied subset remains usable.

The upper envelopes become:

    M_plus(p) = max(max_of_possible_F_rows(p), 1(p in U_t,F))
    O_plus(p) = max(max_of_possible_G_rows(p), 1(p in U_t,G)).

Lower envelopes continue to use actual guaranteed rows only. This is an
interval representation of an unavailable measurement, not a synthetic hit,
experiment, observed score, or extra tool call. It supplies no comparison count
or completed-work credit. Region means, geometric means, feature factors and
the section 6 bound formulas are otherwise unchanged. Where only observed
partial alignments are available from a complete declared result, uncovered
positions are ordinary recorded zeros; they do not automatically create U.

For example, a fixed two-tool, one-residue calculation has observed BLAST
M=0.6, O=0 and an unavailable included HMMER analysis at that residue.
Its C bounds are [0.5*0.6, 0.5*0.6+0.5]=[0.3,0.8], with null point.
For fixed A=0.8 and neutral V=1, the qualified bounds are [0.24,0.64].
The separately declared BLAST-only profile gives C=0.6 and Q=0.48; it is a
different named calculation, not an imputation in the two-tool result.

If a 0.7-weight comparison can support either F or incompatible G, but only
one label, alongside guaranteed M=0.4, the conservative single-position C
bounds are [0.4*(1-0.7), 0.7]=[0.12,0.7]. Enumerating the two permitted
assignments gives the same endpoints. This explicitly defines the ambiguous
reference case rather than treating one disputed label as two certain hits.

Policy coefficients and transform identities have origin=proposed; actual
native measurements remain reported, calculations from measured operands are
derived, and fixture operands/results are synthetic. The proposed origin
extends the Cell enumeration where a coefficient is represented as a Cell.

## 11. Populated numerical sheet instance: synthetic full calculation

This is a populated instance of the sheet, not a published protein result.
All observations and reference assignments are synthetic. Their complete
native input rows, coordinate intervals, search spaces and panel operands are
printed in WORKED_EXAMPLE.md and CURRENT_SYNTHETIC_ARITHMETIC_002.json.
The declared profile is BLAST plus HMMER, with one required region of 100 aa,
two F reference groups, one incompatible G group, and feature-qualified output.

| Numerical cell | Value | Inputs / denominator / interpretation |
| --- | ---: | --- |
| H_BLAST | 0.731054692601763 | Native-weight maxima across 100 target residues |
| X_BLAST | 0.3281050106281468 | Overlapping F/G weight products across those 100 residues |
| C_BLAST | 0.40294968197361625 | H_BLAST minus X_BLAST |
| H_HMMER | 0.6400850842077626 | Domain-native weight maxima across 100 target residues |
| X_HMMER | 0.18405396053278728 | Overlapping F/G weight products across those 100 residues |
| C_HMMER | 0.4560311236749753 | H_HMMER minus X_HMMER |
| H_F | 0.6855698884047627 | Equal algorithm mean, one required region |
| X_region | 0.256079485580467 | Equal algorithm mean; region-specific ambiguity penalty |
| C_native,F | 0.42949040282429574 | H_F minus X_region for this one-region instance |
| Panel 1 assessed | 5/5 = 1 | Five declared site questions |
| Panel 1 compatible | 3/5 = 0.6 | Three compatible of five assessed and required questions |
| Panel 2 assessed / compatible | 1/1 = 1 | One distinct declared predicate |
| A_F | 0.8 | (0.6+1)/2 panels |
| V_F | 1 | Neutral empty conjunction; no necessary predicate established |
| Homology-only index | 0.42949040282429574 | C_native,F; retained diagnostic, not the selected output |
| Selected feature-qualified index | **0.3435923222594366** | C_native,F * 0.8 * 1; dimensionless uncalibrated index |

For these exact fixture inputs, the numerical operand bounds equal their
points. That equality describes fixture arithmetic, not biological uncertainty.
Unknown unobserved alternatives give the separate sensitivity [0,
0.3435923222594366]. An unavailable included native channel instead gives a
null point and operand bounds, as in section 10 and its separate receipt003.
No table cell is an overall intuitive confidence grade or a probability.
