# hmmbuild — proposed exact contract

Modes: `build_alignment` and `build_single_sequence_matrix`; retain alphabet
amino/DNA/RNA, architecture (`--fast` or `--hand`), weighting, priors and RNG seed.
The same HMMER3/f output grammar is shared; the estimator meanings differ.
Native `--singlemx` forces matrix construction for one aligned sequence.
Stockholm/other aligned formats use alignment estimation by default; unaligned
single-sequence input handling must be bound to actual recognized input format,
not guessed from file extension. Matrix-file input is a separate retained role.

Invocation: `hmmbuild [options] [-o summary] [-O resaved.sto] models.hmm msa`.
Input `alignment` is complete Stockholm initially; native `--informat` also
accepts a2m/afa/psiblast/clustal/phylip and other Easel formats. Those formats must
have separately established readers or remain explicit unsupported extraction.
Input stdin is native-supported, with retained supplied bytes; output `-` is
forbidden. `-n` is single-alignment only; multiple MSAs require native ID names.
No external databases are needed. `--cpu` is caller-selected; actual native help
does not expose MPI in this build. `--mxfile` requires a supplied square matrix.

Outputs: complete HMMER3/f `models`; summary stdout or `-o` text; optional
`resaved_alignment` Stockholm; stderr. Preserve all per-MSA models/summary rows.
`-O` is a possibly changed alignment (Plan7 restrictions), not byte identity or
proof that original column coordinates survived. Sequence identities and
original-to-resaved/model MAP correspondence must be validated explicitly.

Sheet fields per summary row: native idx (one-based), name, nseq (input sequence
count), alen (input alignment columns), mlen (match states), eff_nseq (effective
weighted sequence count), re/pos (mean match KL against native background,
bits/match position), description; nucleotide rows additionally W (model window
upper bound, nt). Preserve original tokens: summary eff_nseq has 2 decimals and
re/pos 3; HMM EFFN has 6 decimals and is a distinct native representation.
Model fields: NAME/ACC/DESC, LENG, ALPH, NSEQ, EFFN, CKSUM, MAP/RF/MM/CONS/CS
flags, optional MAXL, GA/TC/NC pairs, STATS LOCAL MSV/VITERBI/FORWARD (location
bits and scale inverse bits), complete match/insert emission and transition
probabilities, COMPO and position annotations. Calibration comes from native
simulations; it is not empirical gene-function confidence.

Associations: each ordered MSA occurrence -> summary row -> output model record,
checked with name/accession/alphabet/count/length and MAP; resaved MSA membership
maps separately. Duplicate bytes/IDs cannot collapse input alignment roles.

Proposed functions: `parse_hmmbuild_summary(text, *, operation, occurrence)`;
`populate_hmmbuild_sheet(*, operation, inputs, outputs, models, alignments)`;
`calculate_hmmbuild_components(sheet, *, parameters={background, probability_
rounding_tolerance, summary_rounding_tolerance})`. Calculations: actual row/column
counts, RF consensus count; mlen/alen; eff_nseq/nseq with explicit input count;
probability mass residual per distribution; mean match entropy and relative
entropy from saved probability arrays/background. Formula KL =
`sum_k sum_a p[k,a]*log2(p[k,a]/q[a])/M`; zero terms contribute zero. Unknown
background means unknown KL, not default replacement. Do not rebuild models to
recalculate. Full no-prior emission frequencies are checkable from saved counts.

Checks: summary/header/input population agreement; termination and full body;
alphabet/weights/columns; RF required for --hand; requested output presence;
ordered one-to-one associations; inconsistent metadata; duplicate-name ambiguity;
partial multi-MSA output (native can emit the first model before a later naming
failure); invalid probabilities and malformed or absent files. Preserve failed
run's valid earlier models with incomplete population.

Output/failure envelope, resource constraints and consuming-function handoff are
COMMON.md. No scientific observation or confidence score. Downstream explicit
model operands for hmmsearch/hmmscan/hmmalign/nhmmer may consume the validated
produced artifact; no search is started by preparation/calculation.

Native evidence: `native/help_hmmbuild`, `native/hmmbuild_protein`,
`native/hmmbuild_dna`. The protein example has 3 input sequences, 14 alignment
columns, 12 match states, EFFN=3, native re/pos=4.376; model length/input column
fraction=12/14=0.8571428571428571 and effective/input count ratio=1. Position 5
has F count 2 and Y count 1; native negative-ln tokens 0.40547 and 1.09861
represent approximately 2/3 and 1/3. Resaved MSA has 12 columns, demonstrating
the need to preserve both alignment coordinate systems. Source:
`hmmbuild.c:output_result` and `modelstats.c:p7_MeanMatchRelativeEntropy`;
complete bundled hmmbuild.man and native help were inspected. Examples establish
native format and invocation, not a parser, calculator or episode binding.

Additive format correction from complete p7_hmmfile_WriteASCII inspection:
GA/TC/NC cutoffs have two values for protein (sequence/domain) but a single value
for DNA/RNA. Their meanings must not be flattened to a universal pair. The current
protein example has no cutoff headers; those cells are missing, never zero.
Additional native format examples (requested by model-reader workload):
`native/hmmbuild_rna/profile.hmm` is an actual `--rna --hand --cpu 1 --seed 42`
build of inputs/rna.sto: ALPH RNA, LENG12, MAXL73, NSEQ3/EFFN3, GA10.10 with
one nucleotide cutoff value. `native/hmmbuild_annotated/profile.hmm` is an actual
`--amino --hand --cpu 1 --seed 42` build of inputs/protein_annotated.sto:
LENG12, RF/MM/CS/MAP all yes, supplied illustrative GA12.30/4.50,
TC15.60/6.70 and NC8.90/2.10. Positions2/3 carry mask m and consensus x;
secondary structure H is retained. These cutoffs were supplied in the synthetic
input, not fitted or scientifically calibrated. Neither build emitted COM lines.
All records retain full native probability bodies, receipts and exact inputs.

Additive single-sequence matrix evidence and association correction:
`native/hmmbuild_singlemx` is an actual `--amino --singlemx --cpu 1 --seed 42`
build from inputs/protein_single.sto. Its summary identifies MSA `single_protein`,
but model NAME is `single`, the single input sequence identifier. Consequently
summary-name equality is not a universal association check: this mode associates
the ordered MSA, its sole sequence occurrence and the ordered model, preserving
the distinct native names. The original MSA accession is not inherited. Native
summary nseq=1, alen=12, mlen=12, eff_nseq=1.00 and re/pos=0.628; model NSEQ=1,
EFFN=1.000000, MAP/RF/MM/CS=no, and COM `[1] [HMM created from a query sequence]`.
The COM line is native output, not supplied provenance. Matrix-derived emission
probabilities are not empirical single-sequence residue frequencies. Position1
A has native token1.27959, decoded probability exp(-1.27959)=0.27815131911860913.
Across all12 complete match vectors, direct independent KL using the explicit
20 amino background constants from hmmer.c:p7_AminoFrequencies yields
0.6282749544993825 bits/match, agreeing with the native 3-decimal0.628; largest
match probability-mass residual is2.686507735383259e-6 from saved rounded tokens.
mlen/alen=1 and effective/input count=1 have explicit denominators12 and1.
