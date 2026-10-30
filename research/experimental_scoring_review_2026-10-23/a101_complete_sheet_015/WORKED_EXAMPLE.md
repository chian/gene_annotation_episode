# Completely calculated example for proposed A101 convention015

**Every native value, sequence extent, reference function, group assignment,
site panel and model parameter in this file is synthetic.** No BLAST/HMMER
output was generated or parsed. These numbers do not belong to the published
cases or to ybhP. They demonstrate that the proposed arithmetic can be evaluated.

The supplied target has 100 aa. The first calculation has one declared
undivided required region, positions 1–100. F and G are stipulated characterized
functions that are incompatible at this scope. Two reference groups support F.
The related HMMER profile shares the first group's information. Every listed
position in the table has a resolved residue-to-residue/model-state pair;
there are no gaps or uncertain coordinates in this fixture.

| Synthetic comparison | Function/group | Native bits | Target paired positions | Paired reference / denominator | Identity / all columns |
| --- | --- | ---: | --- | ---: | ---: |
| B_F1, BLAST HSP | F / F_A | 80 | 1–60 | 60/60 | 48/60 |
| B_F2, BLAST HSP | F / F_B | 60 | 41–100 | 60/60 | 42/60 |
| B_G1, BLAST HSP | G / G_A | 65 | 1–60 | 60/60 | 45/60 |
| H_F1, HMMER domain | F / F_A | 50 | 1–50 | 50/60 model states | Not a pair-identity input |
| H_F2, HMMER domain | F / F_B | 70 | 51–100 | 50/50 model states | Not a pair-identity input |
| H_F1_related_profile | F / F_A | 45 | 1–50 | 50/60 model states | Not a pair-identity input |
| H_G1, HMMER domain | G / G_A | 60 | 1–50 | 50/50 model states | Not a pair-identity input |

BLAST's stipulated simple-regime effective search space is 90 × 1,000,000 =
90,000,000 residue-pair opportunities. E=90,000,000 × 2^(-B). HMMER's stipulated
Forward parameters are tau=5 bits, lambda_H=ln(2)/bit, Z=20,000 and domZ=8.
These are fixture parameters, not actual defaults or a profile calibration.
The native-statistic outputs are retained in the receipt. HMMER full-sequence
scores are respectively 52, 72, 47 and 62 bits; the domain calculation does not
add these repeated/scope-distinct values. For every HMMER row iE/cE=2500.

The separate five-site panel is fully assessed, with three compatible and two
incompatible sites: s1=3/5=0.6. A distinct one-predicate panel is fully compatible:
s2=1/1=1. Thus A_F=(0.6+1)/2=0.8. No independently established necessary
predicate is stipulated, so the empty conjunction V_F=1 is a neutral
operation, explicitly labeled none_established. This is not a positive
measurement of every possible indispensable residue.

Using the fixed proposal:

    f_B(B)=1-exp(-0.025*max(B,0))
    f_H(B)=1-exp(-0.020*max(B,0))
    w_B=f_B * reference_paired_fraction * (0.5+0.5*identity)
    w_H=f_H * profile_emission_fraction.

| Comparison weight | Full arithmetic | Value |
| --- | --- | ---: |
| w_B_F1 | (1-exp(-2)) × 1 × (0.5+0.5×0.8) | 0.778198245087 |
| w_B_F2 | (1-exp(-1.5)) × 1 × (0.5+0.5×0.7) | 0.660339363874 |
| w_B_G1 | (1-exp(-1.625)) × 1 × (0.5+0.5×0.75) | 0.702702284196 |
| w_H_F1 | (1-exp(-1)) × 50/60 | 0.526767132357 |
| w_H_F2 | (1-exp(-1.4)) × 1 | 0.753403036058 |
| w_H_F1_related | (1-exp(-0.9)) × 50/60 | 0.494525283550 |
| w_H_G1 | (1-exp(-1.2)) × 1 | 0.698805788088 |

At positions 41–60 the BLAST F1 value wins the maximum; F2 covers 61–100.
The related weaker HMMER profile changes no maximum. The distinct groups and
the two algorithms therefore do not become seven independent votes.

    H_BLAST = (60*w_B_F1 + 40*w_B_F2)/100
            = 0.731054692602
    X_BLAST = 60*w_B_F1*w_B_G1/100
            = 0.328105010628
    C_BLAST = H_BLAST-X_BLAST = 0.402949681974

    H_HMMER = (50*w_H_F1 + 50*w_H_F2)/100
            = 0.640085084208
    X_HMMER = 50*w_H_F1*w_H_G1/100
            = 0.184053960533
    C_HMMER = H_HMMER-X_HMMER = 0.456031123675.

With equal algorithm weights:

    H_F = (H_BLAST+H_HMMER)/2 = 0.685569888405
    X = (X_BLAST+X_HMMER)/2 = 0.256079485580
    C_native,F = H_F-X = 0.429490402824
    feature_qualified_index = C_native,F × A_F × V_F
                            = 0.429490402824 × 0.8 × 1
                            = 0.3435923222594366.

The 0.343592 result is the declared **index conditional on these observed
comparisons and coefficients**, not a 34.4% probability. Its two-tool
correspondence support, observed ambiguity penalty and feature qualification
are separately inspectable numbers.

## Contrasts and missing-data behavior

| Changed fixture or scope | Defined result / interpretation |
| --- | --- |
| Repeat B_F1 or deliver it again as a paper/table/API row | Exactly unchanged, 0.3435923222594366. |
| Delete the weaker related HMMER profile | Exactly unchanged; it supplied no new maximum or covered position. |
| No incompatible comparison has been recorded | C_native=H_F=0.685569888405; qualified index 0.548455910724. This is a different observed set, not proof that competitors were excluded. |
| Unknown alternatives outside the observed set | Sensitivity range [0,0.343592322259], separate from the conditional point; not a CI. |
| Fifth site unassessed, with three compatible among four assessed | s1 in [0.6,0.8], A in [0.8,0.9]; qualified point null, bounds [0.343592322259,0.386541362542]. |
| B_F1 identity missing, all other inputs fixed | Qualified point null, conservative endpoint bounds [0.324337166071,0.349761830545]. |
| BLAST-only declared profile | Qualified index 0.322359745579. HMMER absence is not imputed as zero. |
| HMMER-only declared profile | Qualified index 0.364824898940. This subset is labeled; the profile is not chosen to maximize output. |
| Same B with displayed E=0 | Finite bit-channel result unchanged; the zero token supplies no infinite support. |
| Two genuinely required regions, 1–50 and 51–100 | C1=0.195007885999, C2=0.663972919649; C_native=sqrt(C1*C2)=0.359833232792; qualified=0.287866586234. |

The two-region variant is a different, explicitly stipulated biological
requirement, not a second reading of printing blocks. It shows why a weaker
required region remains visible. The one-region and two-region results are
not alternative outputs from which a scorer silently picks the larger.

## Sensitivity to explicit numerical choices

Holding the synthetic observations fixed:

| Convention change for discussion | Qualified index |
| --- | ---: |
| Multiply both inverse-bit scales by 0.5 | 0.278513274975 |
| Keep proposed scales | 0.343592322259 |
| Multiply both inverse-bit scales by 2 | 0.363839961812 |
| Give BLAST identity coefficient 0, native factor 1 | 0.347574642535 |
| Give BLAST identity coefficient 0.5, native factor 0.5 | 0.343592322259 |
| Give BLAST identity coefficient 1, native factor 0 | 0.335443589151 |

The last three rows change the factor from (1-a)+a*i, not an ordinal
classification. These alternatives are sensitivity calculations; convention015
continues to specify a=0.5. No sensitivity result selects a policy by itself.

Research arithmetic passed twelve check groups, including forty-two native
own/alternative score-direction settings, independent closed-form versus
position-wise calculations, duplicate invariance, overlap, units, full/domain
separation, E=0, missing bounds, region conjunction and retained source-count
arithmetic. The primary native fixture and checked results are in
arithmetic_receipt_001.json; additive separated exports are described in the
audit. Native parsing, biological calibration and production scoring were not
tested because none was implemented.

Current review pointers: CURRENT_SYNTHETIC_ARITHMETIC_002.json is the separated
synthetic receipt and does not expose paper-specific calculations together.
orientation_arithmetic_002.json checks the explicit biological reference
denominator. missing_membership_arithmetic_003.json checks uncertain labels
and unavailable included results; its formulas are in the current sheet's
additive clarification002. These later files preserve receipt001 unchanged.
