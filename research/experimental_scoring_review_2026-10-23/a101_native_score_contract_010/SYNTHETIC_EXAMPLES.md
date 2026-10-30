# Synthetic numerical rows for the native-score contract

Every number below is invented for arithmetic. No sequence was aligned, no database was searched, and no scientific program or service was executed. These are not published cases or generated native output. In particular, the stipulated statistical parameters are not claimed to have been calibrated for the invented alignment/profile operands.

## Row B: BLAST-shaped local protein HSP

The supplied target Q has 300 aa; reference R has 260 aa. The alignment has 240 columns: 180 identical residue pairs, 52 other residue pairs, four query-gap columns and four reference-gap columns. Thus 232 columns pair actual residues. The spans are query 20–255 and reference 5–240, both 236 aa using 1-based inclusive endpoints. Each sequence has four residues opposite gaps in the other sequence.

The synthetic substitution sum is 230 raw points. There are two gap openings, eight total gap columns, gap opening cost 11 and extension cost 1 per column under the declared G+Ln convention:

    S = 230 − 2×11 − 8×1 = 200 raw points.

With stipulated λ=0.267 inverse raw points, K=0.041, effective query length 280 and effective database length 1,000,000:

    B = (0.267×200 − ln 0.041)/ln 2 = 81.64814746351466 bits
    Ω = 280×1,000,000 = 280,000,000 effective residue-pair opportunities
    E = 0.041×280,000,000×exp(−0.267×200)
      = 280,000,000×2^(−81.64814746351466)
      = 7.3895255387619×10^−17 expected null hits.

This assumes the simple single-HSP regime specified in the contract. Tenfold **effective search space**, with all other operands held fixed, gives E=7.3895255387619×10^−16; S and B do not change. This says nothing about the probability of a wrong annotation.

| Numerical component | Calculation | Value |
| --- | --- | ---: |
| All-column identity | 180/240 | 0.75 (75%) |
| Residue-pair identity, separately named | 180/232 | 0.7758620690 |
| Query span coverage | (255−20+1)/300 | 0.7866666667 |
| Reference span coverage | (240−5+1)/260 | 0.9076923077 |
| Query residue-pair coverage | 232/300 | 0.7733333333 |

The different denominators answer different questions. The native significance/score calculation does not make either coverage fraction a functional-transfer probability.

## Row H: HMMER/Pfam-shaped protein/profile comparison

The same synthetic supplied sequence Q has 300 aa. A hypothetical profile has 120 match states; it is not a real Pfam model. The proposed native record shape is `hmmscan`, so `qlen=300` and `tlen=120`. The full-sequence score is stipulated as 62 bits with bias 2 bits, and its one reported domain score as 60 bits with bias 1 bit. These are separate native-scope inputs; the whole-sequence score is not recalculated by adding the domain score and another contribution.

The profile's stipulated Forward statistics are τ=5 bits and λ_H=ln 2 inverse bits. The search-space operands are Z=20,000 profiles and domZ=8 reported profiles. For this arithmetic fixture:

    p_sequence = exp[−ln 2×(62−5)] = 2^−57
               = 6.93889390390723×10^−18
    p_domain = exp[−ln 2×(60−5)] = 2^−55
             = 2.77555756156290×10^−17
    E_sequence = 20,000×p_sequence = 1.38777878078145×10^−13
    iE_domain = 20,000×p_domain = 5.55111512312580×10^−13
    cE_domain = 8×p_domain = 2.22044604925032×10^−16
    iE_domain/cE_domain = 20,000/8 = 2,500.

The two domain E-values encode the same domain score under different search spaces; they are not two pieces of evidence. Changing the producer's reporting selection could alter domZ while the score stayed fixed.

HMM span 5–112 contains 108 model positions, including six deleted match states. There are 102 match states paired to sequence residues plus six inserted sequence residues. Alignment span 21–128 therefore contains 108 sequence residues; envelope span 18–132 contains 115.

| Numerical component | Calculation | Value |
| --- | --- | ---: |
| Profile span coverage | (112−5+1)/120 | 0.9 |
| Profile match-state emission coverage | 102/120 | 0.85 |
| Sequence alignment-span coverage | (128−21+1)/300 | 0.36 |
| Sequence envelope-span coverage | (132−18+1)/300 | 0.3833333333 |
| Pre-bias domain score, to the stipulated precision | 60+1 | 61 bits |
| Sequence margin above synthetic GA1=25 | 62−25 | 37 bits |
| Domain margin above synthetic GA2=24 | 60−24 | 36 bits |

GA1 and GA2 are explicitly synthetic model-threshold operands. They are not current Pfam thresholds or a required acceptance rule. The margins are numerical distances from those stipulated thresholds, not converted confidence or function scores.

## Site component and incomplete mapping

Suppose a separately grounded synthetic reference-site set has N=5 sites. The correspondence map assesses m=4; k=3 satisfy their declared allowed-residue sets, one is known incompatible, and one is unmapped. Then

    assessed fraction = 4/5 = 0.8
    compatible among assessed = 3/4 = 0.75
    observed compatible fraction = (4/5)(3/4) = 3/5 = 0.6
    possible compatible fraction = [3/5, (3+1)/5] = [0.6,0.8].

The incomplete site's value is unknown. The lower bound is not silently treated as the full site's observed value. In the separate complete compilation fixture, the fifth site is expressly stipulated as assessed and incompatible; that fixture's s=0.6 is a point input. Neither fixture supplies a real functional reference or mapping.

## Overlap and duplicate arithmetic

Three retained interval representations are [20,255], [200,280], and a repeated [20,255]. Their union is [20,280], length 261. Query span coverage is 261/300=0.87. Adding their lengths would count shared residues and the duplicate twice. The interval union says nothing about consistency of reference coordinates or whether those alignments form a single coherent alignment. No combined bit score or E-value follows from the union.

## Raw pair/self substitution counterexample

For the purely illustrative raw expression `200/sqrt(600×520)`, the value is 0.3580574370. Using BLAST bit transformations of the same three numbers under the stipulated λ,K instead produces 0.3714984974. The values differ because the raw-to-bit mapping contains an additive offset. This demonstrates why native bit scores cannot be substituted into a raw-score normalization; it does not endorse this raw normalization or establish its functional meaning/bounds.

## Compilation, check results, and limits

`COMPILATION_PROPOSAL.md` supplies the expanded finite sum/product route, explicitly grounded alternative-function operands, every synthetic coefficient, and the fully populated bounded contribution. Its complete arithmetic result is 0.7522493993 under that invented convention. The preserved missing-site variant produces the interval [0.7522493993,0.7704131110], with no point estimate. Neither is a function probability or adopted policy.

The first script `synthetic_arithmetic_check.py` checks raw/bit/E relationships, distinct coverage denominators, the HMMER two-search-space relationship, site decomposition, duplicate/overlap union, raw-score substitution difference and an initial joint-expression example. `synthetic_joint_alternative_check.py` adds function contrasts, a complete point example, the missing-site bounds, duplicate-group behavior and strict relative comparisons for tiny E-values. The second check deliberately avoids relying on the first script's generous absolute tolerance for very small quantities.

Both scripts ran successfully with Python 3 standard-library arithmetic only. Their results are in `synthetic_arithmetic_results.json` and `synthetic_joint_alternative_results.json`. No fitting, annotation scoring against real evidence, output parser implementation, BLAST/HMMER alignment, search, scientific job or service call occurred. The native source documents supplied definitions; no published function-transfer example was converted.
