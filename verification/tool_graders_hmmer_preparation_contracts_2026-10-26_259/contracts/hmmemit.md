# hmmemit — proposed exact contract

Modes: `sample_core_unaligned` (default), `sample_core_aligned` (-a),
`consensus_simple` (-c), `consensus_thresholded` (-C), `sample_profile` (-p) with
distinct local/unilocal/glocal/uniglocal setting. -a/-c/-C/-p mutually exclusive.
Invocation `hmmemit [options] [-o output] models`; `-N n>0` for sampling, not
consensus. -L is profile expected-length configuration, NOT observed sample length.
--seed default0 is native arbitrary seed; preserve actual selected seed and do not
claim reproducibility if it was0. Native source loops over multiple HMMs despite
the usage heading saying '(single)'; same-alphabet ordered populations are allowed.

Input `models` is supported native HMMER format; output `generated_sequences`
FASTA for core/profile/consensus or `generated_alignment` Stockholm for -a;
stderr and stdout retained separately if -o redirects sequence output. No native
trace is emitted by this utility, although internal traces exist. Do not invent
sample alignment coordinates, domain counts or exact model coverage for FASTA.
Profile samples can include flanks and multiple domains; core samples differ.

Sheet keeps complete models/probabilities and generated rows, exact case/alphabet,
name and sequence, model occurrence association, sample ordinal, model length,
selected N/seed/profile configuration/minl/minu. Sample labels use
`<model-name>-sample<1-based-ordinal>`; consensus uses `<model-name>-consensus`.
Repeated names across input records require occurrence+native order/count binding,
not suffix splitting alone. Stockholm preserves all rows, RF and columns. Every
output row has generated/model_derived basis; no biological source observation.

Pure ports: `parse_hmmemit_fasta(content, *, occurrence, operation)`;
`parse_hmmemit_stockholm(content, *, occurrence, operation)`;
`populate_hmmemit_sheet(*, operation, models, outputs)`;
`calculate_hmmemit_components(sheet, *, parameters={consensus_thresholds,
probability_rounding_tolerance})`. Counts and lengths are residues/nt according
to actual alphabet. Per-model generated count, total/min/max/mean lengths and
alphabet counts are recalculable. In -a mode RF gives match columns; compute
gap/residue counts and occupancy with model-length and sample-count denominators.
These describe generated alignments, not evidence of conservation in organisms.

Simple consensus chooses the first maximum-probability symbol in native alphabet
order per match state; a model-mask 'm' emits unknown X/N. Thresholded consensus
uses pmax<minl -> lowercase unknown, otherwise pmax>=minu -> uppercase symbol,
otherwise lowercase symbol; masked states always unknown lowercase. Preserve
native requested thresholds, probabilities, mask and output case. Recalculate
predicted consensus/check mismatches from saved model cells, without native rerun.
Near ties and rounded probability thresholds need explicit ambiguous validation,
not fabricated exact agreement. No random-sample likelihood is required unless a
future explicit contract supplies exact traces/algorithm; raw FASTA is insufficient.

Checks/failures: full sample population per model vs N, consensus length vs M,
Stockholm width/RF length, unsupported alphabet, duplicate labels, empty model
file (native fails), malformed/truncated generated output, partial later-model
failure, unknown source association. COMMON.md applies. Consumers receive generated
artifacts and typed counts only; an explicitly selected later operation may use
them as simulations/testing inputs with generated provenance retained.

Native examples, all exit0, one model M12: `native/hmmemit_core` N3 seed42 emits
three length12 sequences (total36); `*_alignment` gives3 rows/12 columns/RF12.
`*_consensus` emits ACDEFGHIKLMN; `*_fancy` (--minl0.8 --minu0.9) emits
ACDExGHIKLMN, 1 unknown/12 because position5 pmax~=2/3. Profile -L20 N3 seed42
lengths: local[15,72,39], unilocal[85,31,21], glocal[92,37,30],
uniglocal[100,31,17]. The population denominators are3 each, not20. Full hmmemit.c
and complete simple/fancy consensus functions in emit.c were inspected. This
establishes native invocations/formats; no production grader/binding was added.
