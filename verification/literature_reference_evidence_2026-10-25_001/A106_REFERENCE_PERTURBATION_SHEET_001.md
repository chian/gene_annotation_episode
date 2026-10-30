# Executable source-effect portion of the A106 proposal

The adopted literature goal remains active and incomplete. This additive sheet
preserves the historical proposals, including the consolidated
`research/experimental_scoring_review_2026-10-23/a106_complete_deliverable_028/A106_NUMERICAL_SHEET_028.md`.
It specifies the finite source-effect portion implemented in this increment.
It neither adopts the entire proposal nor supplies an eleventh evidence axis.

In proposal028, the source effect is `a=s*theta*r*C*I` and the later row is
`q_point=H*a`. Here `reference_restoration_index` names that proposed **source
effect a**, with one nominated nuisance-amount comparison. No H operand is
supplied, set to1 or inferred. Molecular/system correspondence, candidate
combination and annotation credit remain later work. Multiple comparability
terms, general uncertainty, necessity challenges and source aggregation are
unfinished, rather than implicitly covered by this finite implementation.

## Separate scientific instructions and extraction

`gene_annotation_episode/literature_perturbation_prompt.py` contains the recurring
investigation TASK. It asks the reader to establish recipient, donor, changed
copy, coexisting copies/partners, actual arms, endpoint, denominator, conditions,
controls and measurement limitations. It distinguishes reconstitution, variant
replacement and selective perturbation followed by restoration. This sheet is
not inserted into that TASK.

`read_perturbation_inputs` reads original source witnesses and an optional
actually received retained-measurements source. The twelve literal fields are
molecule, recipient, donor, experiment, reference_arm, perturbed_arm,
restored_arm, partner, endpoint, normalization, condition and intended_change.
Design, endpoint calibration, endpoint comparability, amount role and direction
are explicit source interpretations, supported by literal witnesses. Their
finite labels describe experimental meaning; they are not numerical grades.
Quote validation establishes custody, not correctness of interpretation.

Seven numerical operands occur in retained source bytes, not model numerical
arguments: W,K,R,A_reference,A_restored,B_pert,B_rest. Every retained operand
has a value or explicit null, measurement ID, unit, source/artifact identity and
JSON role. Physical IDs do not imply sampling independence. Reusing an ID for
inconsistent values/units fails; equal values with different IDs remain distinct.
Known W/K/R require distinct observations to establish their contrasts.

W/K/R are already nominated endpoint values on the same nonnegative ratio scale;
this first reader does not calibrate raw PCR intensity or estimate population
means from raw biological units. A values compare one specifically nominated
nuisance amount outside the intended change. B values are supplied applicable
upper bounds on alternative contributions to the respective endpoint contrasts.
The retained-data boundary does not estimate those bounds, establish coverage
of every nuisance, or infer zero interference from a missing control.

## Numerical cells and populated illustration

All numbers below are **synthetic**, with W100,K20,R90 events per100000 cells,
A_reference100,A_restored90 molecules per cell, B_pert8,B_rest7 endpoint units,
distinct arm observations, validated same endpoint, selective perturbation and
restoration, nominated nuisance amount, and direction s=+1. These are not Cas2
measurements. They illustrate arithmetic, not biological precision.

| Executable cell | Inputs and calculation | What it evaluates | Synthetic value |
| --- | --- | --- | ---: |
| reference_endpoint | W, endpoint units | Reference outcome | 100 |
| perturbed_endpoint | K, same units/denominator | Perturbed outcome | 20 |
| restored_endpoint | R, same units/denominator | Restored outcome | 90 |
| perturbation_difference | D=W-K, endpoint units | Magnitude/direction of intervention contrast | 80 |
| symmetric_effect | theta=(W-K)/(W+K), dimensionless | Proportional intervention effect on a meaningful-zero scale | 0.6666666667 |
| restoration_fraction_raw | (R-K)/(W-K), dimensionless, unrestricted | Reversal fraction, retaining overshoot | 0.875 |
| restoration_agreement | r=clip(1-abs(R-W)/abs(W-K),0,1) | Proposed agreement with return to reference | 0.875 |
| amount_comparability | C=min(A_reference,A_restored)/max(A_reference,A_restored) | Proposed agreement of this nominated nuisance amount | 0.9 |
| perturbation_isolation | I_pert=clip(1-B_pert/abs(W-K),0,1) | Residual attribution under supplied perturbation bound | 0.9 |
| restoration_isolation | I_rest=clip(1-B_rest/abs(R-K),0,1) | Residual attribution under supplied restoration bound | 0.9 |
| effect_isolation | I=min(I_pert,I_rest) | Proposed weakest-comparison isolation | 0.9 |
| reference_restoration_index | s*theta*r*C*I | Proposed conditional source-effect product a | **0.4725** |
| reference_index_lower | Joint bound on the same product, not yet implemented | Unknown joint uncertainty | null |
| reference_index_upper | Joint bound on the same product, not yet implemented | Unknown joint uncertainty | null |

clip(x,0,1)=min(1,max(0,x)). Every exponent is1. Restoration agreement,
comparability, isolation and the combined index are proposed conventions.
Native endpoint origins remain reported, graph-derived or synthetic as received;
raw arithmetic is derived. Common W/K/R are shared operands, not independent
proofs. The index is not a causal probability, target transfer, annotation
credit, or investigation-progress reward.

`populate_source_restoration` performs exact-rational intermediate arithmetic
and checks each final floating-point range separately. An overflowing raw ratio
does not erase a separately representable clipped agreement. Preventable
intermediate overflow or underflow does not manufacture zeros.

## Missingness and applicability

Each numeric cell has value, unit, status, formula, origin, unavailable_reason
and conditional_on. Typed returns replace the formula text by a closed formula
code; they preserve numerical values and scientific qualifications.

Unvalidated ratio scale or unsupported common endpoint prevents derived effects.
Absent arm values or physical identities leave the relevant contrasts unknown.
Reconstitution and variant replacement can retain usable two-arm data but cannot
invent a restoration triple. Zero denominators stay undefined. Overshoot stays
visible in the raw ratio; the proposed agreement clips to[0,1].

The C calculation is restricted to a nominated nuisance amount. Intended depletion
does not become a second nuisance penalty. This finite interface cannot yet
represent a scientifically established inapplicable comparability factor; it
returns amount_is_intended_change or a missing-role reason rather than silently
setting C=1. Missing B is not B=0. A missing/undefined factor does not become
a zero or one in the final product. Algebraic identification on bounded domains,
as described in proposal028, is not fully implemented here and remains work.
Both bound cells explicitly return joint_uncertainty_unreported.

## Primary Cas2 contrast

The independent original-source review and complete post-paper reset are retained
in CAS2_PARENT_REVIEW_001.md and CAS2_PARENT_READ_PROVENANCE_001.json. Source
selectors used by the controlled executable example quote the unchanged XML.

The recipient is cas-free BL21-AI; donor Cas1/Cas2 derive from MG1655. A plasmid
pair labeled WT is not a native wild-type organism. Cas1 coexists as a required
partner. Variant replacement and domain truncation do not supply a native
gene-deletion/complementation experiment. The measured readout is OD-normalized
PCR, without the calibration/eligible-population information required for an
acquisition rate. A visible product is not an event frequency or numerical
equivalence, and signature-residue mutation is not a measured catalytic-null.

The executable example therefore preserves molecule/recipient/donor/partner,
PCR endpoint, normalization witness, cas_free_reconstitution design and
qualitative_only status. W/K/R and all effects remain null; units are unreported
because no dimensional numerical outcome was supplied. The source index has
ratio_scale_not_validated, and its bounds have joint_uncertainty_unreported.
Selected spacer composition and repetition counts do not fill missing rates.

## Selected execution and later handoff

The ordinary selected operation is literature.perturbation.populate inside the
existing LiteratureEpisodes. Its repository saves the original extraction,
numerical sheet, literal bindings, request and selected outcome transactionally.
requested_perturbation_components selects a typed subset under
literature_perturbation_cells. Returns keep experimental bindings, endpoint and
amount units, design/calibration/amount-role interpretations and missing reasons.
Replay copies committed results without source rereading or recalculation.

Later consumers may use these source components and their exact experimental
scope/dependencies. They must obtain target correspondence separately and must
not infer H=1, complete scientific validity, independent replication, resolved
uncertainty or a final annotation score from the existence of this sheet.
No A101/A105 combination, W05 aggregation, controller change or synthetic
observation is installed by this increment.
