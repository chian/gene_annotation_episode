# hmmsim — proposed simulation/inspection contract

Exact bundled HMMER3.4 executable and complete src/hmmsim.c inspected. Invocation
`hmmsim [options] <hmmfile>` generates IID random sequences and collects model
score distributions. This is generated data, with no annotation-confidence score
or biological observation. Algorithm modes: Viterbi (`--vit`, default), MSV
(`--msv`), Forward (`--fwd`), Hybrid (`--hyb`). Alignment settings: multihit local
(`--fs`, default), unihit local (`--sw`), multihit glocal (`--ls`), unihit glocal
(`--s`). Keep exact settings even when outputs coincide. Optimized `--fast` has
branches only for vit/msv/fwd; fast+hyb is unsupported/undefined in this source.
The native help lists MPI only if compiled; no MPI binding was verified here.

Input `models` retains all same-alphabet HMM occurrences and full bodies. Explicit
parameters include N generated sequences per model, fixed sequence length L,
seed (0 chooses arbitrary native seed, not deterministic42), background policy
(default/flat/model composition), algorithm/style, fast, experimental length model
and nu, calibration EmL/EmN/EvL/EvN/EfL/EfN/Eft, Forward tail schedule and requested
outputs. The RNG is reseeded per model before calibration; samples across models
are not automatically independent. Background probabilities require explicit
versioned source data for later recalculation. No generated sequence bytes are
written by this program, only scores/optional alignment lengths.

Output `summary` is whitespace text (-o or stdout), without a column header.
For vit/msv/hyb: name then `tailp mu lambda E10 mufix E10fix mufix2 E10fix2 pmu
plambda E10p`; optional -a appends `almean alsd`. For Forward: name then `tailp
mu lambda E10 mufix E10fix pmu plambda E10p`, one row per selected tail mass.
Preserve native rounded tokens and separate full-precision recalculations.
`-v` prints each score to stdout with3decimals even when -o redirects summary;
stdout also receives CPU timing. Native summary names must join model occurrences
by guaranteed serial record order plus name/alphabet validation, not name alone.

Optional roles: `scores` (--xfile) is headerless native-endian C double vectors,
N contiguous elements per input model in serial order; retain byte order,
sizeof(double), IEEE representation and occurrence segment offsets. `alignments`
(--afile, requires -a/--vit) is N rows `integer_alignment_length rounded_bitscore`
per model. Actual source counts M+D+I trace states, despite its stale comment
claiming M+D. `filter` (--ffile) is name/count/fraction. `survival` (--pfile) and
`expected_counts` (--efile) are complete XY plot datasets separated by `&`; retain
all datasets and exact order/meaning, not an arbitrary first plotted curve.
Auxiliary outputs are documented for serial/single-model use; initially require
one model for those outputs or implement/validate explicit serial segmentation.

Quantities: individual scores=(algorithm_log_score-null_log_score)/ln2, in bits;
N is the generated population denominator; L is residues/nucleotides per generated
sequence. Fitted mu/mufix/mufix2 and native calibrated pmu are bit-score locations;
lambda/plambda are inverse bits; E10 variants are expected counts among N at the
10th-highest observed score. tailp is selected tail mass, dimensionless. Native
plambda and pmu are computed in this run via p7_Lambda and algorithm-specific
calibration, not merely copied HMM STATS. Hybrid pmu=0 is explicitly undetermined
in source and must not be represented as a validated calibrated value. Native
alignment mean/sd are trace-state counts; sd uses N-1 sample denominator. Native
CPU timings are separate execution diagnostics.

Proposed pure ports:
`extract_hmmsim(*, models, summary, score_vectors, alignment_rows, filter_rows,
xy_outputs, operation, receipt) -> sheet` and
`calculate_hmmsim(sheet, *, tail_masses, fixed_lambda=0.693147,
filter_threshold, fit_tolerance, rounding_tolerance) -> calculations`.
The sheet retains all vectors/rows, model association, simulation population,
native fit variants and invalid/undefined values. Calculators report count,
mean/min/max, variance, 10th-highest score, independent fitted parameters,
expected-count variants, filter count/N and alignment mean/sd with explicit
inputs. They cannot regenerate samples or recalibrate pmu by executing native code.

For Gumbel fits, solve `1/lambda - mean(x) + sum(x*exp(-lambda*x))/
sum(exp(-lambda*x))=0`; then mu=-log(mean(exp(-lambda*x)))/lambda.
The survival probability is `1-exp(-exp(-lambda*(x-mu)))`, computed stably.
Each E10=N*survival(x10) using its explicit fitted/fixed/calibrated variant.
Forward uses the largest floor(N*tailp) scores (ties remain occurrences),
mu=min(tail), lambda=1/mean(tail-mu), E10=N*tailp*exp_survival(x10), where
exp_survival=1 if x<mu else exp(-lambda*(x-mu)). Its E10p omits tailp because
native calibrated pmu is a full-population origin. Missing vectors prohibit an
independent refit; rounded summaries are not full-precision vectors. N<10 cannot
supply native x10; empty/constant tails and zero fitted slope are invalid or
undefined, not evidence-free zero. Preserve every partial valid vector segment.

Source-specific limitations: --fast with -a uses generic traceback storage that
the optimized scorer does not populate; do not expose as verified. MSV generic
scores in retained examples are identical across all4style settings; preserve
settings and algorithm identity without claiming4independent measurements.
Forward --ffile is a confirmed defect: output_filter_power accepts vit/msv/hyb,
rejects Forward, and its caller ignores the status. A zero-byte filter file after
exit0 is missing/failed output, never zero passing sequences. Hybrid filter uses
exponential survival with undetermined pmu0 while summary uses Gumbel; retain as
native experimental diagnostic with this qualification, not calibrated certainty.

Validation failures include unsupported algorithm/settings combination, absent
body/background, byte representation unknown, binary size !=8*N*model_count,
nonfinite scores/fits, missing auxiliary rows, wrong model association, malformed
XY blocks, counts outside[0,N], and output/summary inconsistencies. Tolerances
reflect native4decimal fit/3decimal score printing. Local prerequisites are exact
binary and staged inputs, caller allocation, no stdin ambiguity, no stall option.
Future preparation driver/result-worker handoff follows COMMON.md and returns
requested typed simulation quantities/validation, never scientific observations.

Native numerical examples: native/hmmsim_{vit,msv,fwd,hyb}_{fs,sw,ls,s} retain all
16 runs, each seed42,N1000,L30 on tiny_dna; every score vector is8,000bytes. All
exit0; Forward filter files are0bytes. native/hmmsim_{vit,msv,fwd}_fast retains
three optimized local examples. For vit_fs, independent score mean is
-5.619071923450204bits; x10=-0.6476082390605439; independent ML mu=
-6.414576359999045, lambda=.7137499186051701, E10=16.174564750739254,
matching native -6.4146/.7137/16.1746. Native filter=368/1000=.3680;
alignment mean=4.439 and sampleSD=1.8616510802899517 (native1.8617).
For fwd_fs tail=.1: tailn100, mu=1.2244937724332836,
lambda=.8836442251850544, E10=12.511194245467216, matching native
1.2245/.8836/12.5112. Source math was checked in Easel GetRank,
GetTailByMass, FitComplete/FitCompleteLoc and IMean. Native execution and
independent arithmetic are preparation evidence; no production grader exists
by virtue of this report.
