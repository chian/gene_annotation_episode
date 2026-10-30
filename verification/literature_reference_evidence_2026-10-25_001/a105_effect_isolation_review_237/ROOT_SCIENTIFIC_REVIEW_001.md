Root review of the mixed-contributor case
=======================================

This implementation evidence does not amend or replace the fixed user goal.
The full post-paper reset is recorded in RESET_COMPLETE_002.json, continuing
the actual untruncated source and authority reads in RESET_PROGRESS_001.json.
The source is Hoffpauir and Lamb (2025), DOI 10.1016/j.jbc.2025.108443,
including its original supplementary DOCX and embedded figure images.

The studied HFP is from Aquifex aeolicus, accession WP_164930753.1; the
comparison IMP is WP_010881296.1. The expression host is E. coli. The original
untagged preparation and later C-terminal His-tagged, differently purified and
heated preparation must remain distinct. The one-pot comparison replaces HFP
with IMP, while each tested protein coexists with its reaction partners and
possible host contaminants. A preparation's dominant protein is not necessarily
the catalyst responsible for an observed reaction.

What the source supports
------------------------

The HFP-containing preparation reaches a Ru5P/R5P composition of 39.7%/60.3%.
Its endpoint ratio is 603/397 = 1.5188916876574308. The printed S5 integral
1.00/1.52 gives the related fraction 38/63 = 0.6031746031746031. These are
representations of the same spectrum, not independent experiments or initial
rates. The result establishes observed interconversion in the preparation at
the reported chemical resolution; it does not assign that chemistry to HFP.

Mass spectrometry identifies E. coli RpiA in the preparation. RpiA's seven
unique peptides and 101/219 residue coverage are identification evidence.
They are not a contaminant molar fraction, activity fraction, false-positive
rate, or compatible numerical g. The 4/5 positive other-preparation cohort
similarly cannot become an HFP attribution probability or assay error rate.

Further purification, a tagged construct and a heat treatment accompany slower
equilibration. The main text's less-than-10-minute / greater-than-18-hour
comparison, S5 room-temperature description and S6 sampling/caption must keep
their individual conditions. Dividing the time thresholds gives 108, but
does not give a matched initial-rate ratio. Recovered active target amount,
contaminant amount and selective treatment effects are not quantified.

The initial stock's Bradford total-protein concentration is 7 mg/ml. Visual
gel inspection estimates approximately 5 mg/ml HFP. Those describe different
measurands in one initial stock. Their approximate ratio 5/7 is useful amount
evidence; it is not an active fraction or proof of quantitative purity. A
conditional reciprocal 7/5 could convert a total-protein-mass denominator
only for a demonstrated same-stock rate with that original denominator.
That rate linkage is absent here, and the factor is not applied.

Existing execution, rather than a duplicate reader
--------------------------------------------------

verify_source_and_amount_001.py independently checks all 46 frozen research
files, 14 literal primary-text spans, six original DOCX members, five actual
Word paragraph locations and nine exact rational calculations. It then calls
the actual current read_amount_inputs and populate_amount_components using
witnesses from the retained primary text, with the original JATS and text
representations separately identified by content hashes. This is a direct
reader/calculator example, not selected episode execution.

AMOUNT_ARGUMENTS_001.json, AMOUNT_EXTRACTION_001.json and AMOUNT_SHEET_001.json
retain the exact source selections, interpretations and resulting numerical
sheet. The amount ratio is approximately 0.7142857142857143 and the conditional
denominator factor approximately 1.4. The approximation survives. Variance
remains unavailable for the stated reason amount_covariance_unreported, and
mass_factor_applied_to_rate is false. The denominator's specific protein
identity is not invented from the named target.

Two root verifier-authoring mistakes were corrected before any output was
written: Word paragraph locations use zero-based indices (not index minus
one), and the short phrase Bradford analysis occurs more than once. The final
selector names the unique longer phrase 7 mg/ml per Bradford analysis.
These were root verification mistakes; no original source or frozen research
packet was changed. ROOT_CHECK_001.json records the successful run.

Scientific combination and the remaining gap
---------------------------------------------

For a justified additive same-endpoint initial-rate model, q = E*a + g;
r = q-g and a = (q-g)*v/(k*E*u). Here k is applicable reporter recovery and u/v
is an applicable nuisance-condition response. Var(r) = Var(q)+Var(g)-2Cov(q,g).
The complete correction requires the actual joint operands and their covariance;
a shared preparation, calibration or subtraction cannot be counted twice.

The existing assay and compiled readers already accept quantitative g and the
calculator already performs the subtraction. This source provides no matched
initial q or quantitative g/bound for the isolation comparison. Thus attributed
rate, isolated activity share, corrected molecular activity and their variance
are unknown due to missing source information. No protein/peptide/time ratio is
substituted. This does not constitute a finished attribution grader for this
design and does not finish the unified A105 assessment.

The necessary next scientific distinction is a witnessed contributor relationship
that separates identification/presence from a same-scale quantitative activity
contribution, preserving endpoint, denominator, preparation, condition,
component-model applicability and covariance ownership. An enum validator alone
cannot establish those interpretations. The seven-paragraph proposed recurring
TASK was printed in the conversation in full after the reset, with STEERING
separately described. No production prompt or schema has yet been changed by
this review.

Before adding another arithmetic branch, a fresh research workload 238 will
seek a contrasting original case that actually measures or bounds an additional
contributor and explains control selectivity. Its assignment preserves the full
goal, requires its own post-paper reset and makes no production changes. That
is a selected next investigation, not a new requirement or an amendment.

No new graders, assay types, axes, runtime gates, controller observations,
target-transfer weights or annotation-credit calculations were created here.
A105 remains incomplete; subsequent axes remain within the original goal but
are not expanded before its adequacy is established.
