# hmmstat — proposed inspection contract

One inspection mode, `hmmstat <hmmfile>`, reports model-derived summary statistics
for every model occurrence. Bundled3.4 executable and full hmmstat.c/modelstats.c
inspected; native help/output retained. Input `models` is a complete same-alphabet
HMM collection; output `summary` is complete stdout including native header and
all rows, plus stderr/receipt. An existing pressed companion may affect native
file opening; bind exact supplied/staged source and any companions explicitly.
No database search occurs and no annotation-confidence score is appropriate.

Columns: idx (one-based model occurrence index), name, accession (`-` absent),
nseq (source sequence count), eff_nseq (effective source count), M (match states),
relent (mean match relative entropy), info (mean match information), p relE
(occupancy/transition weighted position relative entropy), compKL (composition
KL). Counts/lengths are not function evidence. All four entropy columns are bits,
derived from model probabilities and the native background; three are per-model
position summaries, compKL is the divergence of aggregate composition. Native
numbers have2decimals; raw tokens and native-rounded values must remain separate
from recalculated full precision. Model header NSEQ/EFFN absence/default sentinel
does not become measured zero. Name/accession are labels, never unique keys.

Proposed pure ports:
`parse_hmmstat(text, *, operation, occurrence) -> {rows, issues, completeness}`;
`populate_hmmstat_sheet(*, models, summary, operation, receipt) -> sheet`;
`calculate_hmmstat(sheet, *, background, length_probability,
probability_rounding_tolerance, summary_rounding_tolerance) -> calculations`.
Join each native row to input occurrence/record ordinal using idx plus checked
name/accession/alphabet/M/NSEQ/EFFN. Preserve all model bodies and numerical
arrays. Unsupported binary source can retain summary rows but its independent
probability recalculation stays unknown, never guessed from summaries.

Let p[k,a] be match emission probabilities, q[a] supplied background and M model
length. H(p)=-sum(p log2 p), with zero terms defined0. `relent` is mean_k
sum_a p[k,a] log2(p[k,a]/q[a]); `info`=H(q)-mean_k H(p[k]). The source comment
above p7_MeanMatchInfo has a reversed sign in its displayed expression; the
implemented function returns H(background)-H(match), which the native example
confirms. Do not implement the stale comment formula.

For occupancy o[0]=0, o[1]=t[0,MI]+t[0,MM], and
o[k]=o[k-1]*(t[k-1,MM]+t[k-1,MI])+(1-o[k-1])*t[k-1,DM].
Composition vector c[a]=sum_k o[k]*p[k,a], normalized by sum_a c[a]; compKL=
sum_a c[a]log2(c[a]/q[a]). This is not the header COMPO field by assumption.
Position relE combines sum_k o[k]*KL(p[k]||q)/sum_k o[k] with a transition
term, summed k=2..M then divided by sum_k=2..M o[k]. For each k, its term is
`[o*MM*ln(MM/p1)+o*MI*(ln(MM/p1)+ln(IM/p1))+
(1-o)*DM*ln(DM/p1)]/ln2`, with o=o[k-1], transitions at k-1. Preserve the
actual source use of MM in the MI term. Native default p1=350/351. Missing
background/transition arrays, M<2, invalid denominator or nonfinite native tokens
produce unknown/invalid separate states; do not silently manufacture zero.

Native default q is uniform(.25) for DNA/RNA; amino q is the20 supplied constants
in src/hmmer.c:p7_AminoFrequencies (Swiss-Prot50.8 source composition, not the
present input database). An explicit versioned copy of these constants is needed
by calculators. Model transition/probability rounding needs stated tolerance;
calculators must not silently normalize stored distributions unless that is an
explicit selected calculation. Report probability-mass residuals separately.

Validation checks model/row cardinality and exact associations, column grammar,
finite value states, source completeness, full probability body and background,
and native-vs-recalculated values within documented rounding tolerance. Failures
include mixed alphabets, malformed/truncated later records (valid earlier rows
survive), incorrect reference, duplicate-label ambiguity and missing/empty output.
Sheet/calculation/failure envelope, bounded local route and consuming preparation
driver/result-worker/typed-return handoff follow COMMON.md; API/HPC and complete
episode integration remain unverified.

Native examples native/hmmstat_{protein,dna,rna,annotated} all exit0. Each has
nseq3/eff_nseq3.00/M12. Protein no-prior output is relent4.38/info4.10/
p_relE4.38/compKL.79. DNA and RNA each report1.01/1.01/.89/.01.
Annotated protein reports2.45/2.35/2.43/.35. Independent calculation from retained
DNA probability tokens and q=.25 gives mean entropy .9925134248800135,
info1.0074865751199864, relent1.0074921672642938,
p_relE .8906422345697793, compKL .006355823477963574. These match printed
native values to2decimals; tiny info/relent difference arises from stored
probability rounding. Occupancy first=.9807699880,last=.9457525653.
