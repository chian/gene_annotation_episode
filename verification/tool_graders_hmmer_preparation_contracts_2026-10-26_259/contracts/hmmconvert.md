# hmmconvert — proposed exact contract

Modes `ascii`, `binary`, `legacy_hmmer2`; format revision is an explicit parameter.
Invocation `hmmconvert [-a|-b|-2] [--outfmt 3/a|3/b|3/c|3/d|3/e|3/f] models`.
Input role `models`, format HMMER3 ASCII/binary revision or HMMER2 ASCII supported
by native p7_hmmfile reader. Output role `converted_models` is stdout itself,
including binary bytes; stderr separate. No implicit sidecar or summary. --outfmt
is incompatible with -2. Mixed alphabet populations are native errors. Retain the
entire supplied input and produced prefix on a failed later record.

Pure API: shared `extract_hmmer_models` followed by
`populate_hmmconvert_sheet(*, operation, inputs, outputs)` and
`validate_hmmconvert_sheet(sheet, *, parameters={probability_tolerance,
expected_revision, source_output_occurrence_bindings})`. Calculations contain
decoded input/output model counts, per-model LENG difference, matched names/
accessions/counts, body probability differences where BOTH are decoded, optional
field retention/loss and artifact byte sizes. These are transformation validation
quantities, not confidence scores. Denominators refer to complete decoded model
populations; binary bytes alone do not establish a decoded model count.

Native versions must retain different grammar/meaning. 3/f includes MM and
consensus position annotation; 3/e has consensus but no MM; 3/a-d omit consensus;
MAXL is written only from 3/c. 3/a STATS stores VLAMBDA, VMU, FTAU, whereas 3/b-f
stores separate MSV, VITERBI, FORWARD location/scale pairs. No missing legacy
parameter is zero. HMMER2 is converted ls-mode semantics and quantized log-odds,
not HMMER3 negative-ln probabilities; use an explicit legacy decoder or unknown
content validation. Conversion to legacy may lose information by design; report
which fields survived rather than claiming byte equivalence or identical search.

Binary uses native uint32 magic, int/float layout and optional flag-controlled
arrays; p7_hmmfile_WriteBinary is the reference. A magic check is format framing
only, not full numerical/association validation. An optional separately selected
conversion can supply a decoded ASCII companion for validation, but the parser
must never invoke hmmconvert. Preserve that companion's independent occurrence,
request and exact binary-source association. Byte-identical input and output
still remain distinct occurrences.

Checks/failures: wrong declared signature/revision, incomplete model terminator,
invalid probabilities/array lengths, mismatching source/output model population,
duplicate names or accessions, mixed alphabets, unknown binary architecture,
legacy unsupported quantities, nonzero native exit with valid prefix, empty
output versus missing file. Use COMMON.md envelope and result handoff. Produced
models may become explicitly selected operands of later HMMER operations; the
validator itself starts none. Local executable and input only are prerequisites.

Native examples all exit0: `native/hmmconvert_ascii` (6670bytes, 3/f), `*_3a`
(6615), `*_3b`/`*_3c`/`*_3d` (6631 each), `*_3e` (6665), `*_legacy2` (5175),
`*_binary` (2725). Each ASCII output has one model NAME tiny_protein LENG12
NSEQ3; HMMER3 outputs EFFN3, HMMER2 lacks that field. Binary begins
`baedede8` (little-endian 0xe8ededba); its observed size is2725bytes, not a
decoded population count. Explicit `native/hmmconvert_binary_to_ascii` returned
exactly the original6670bytes, independently checkable byte for byte. Full
hmmconvert.c and complete WriteASCII/WriteBinary functions were inspected. No
production parser, calculator or full episode integration is claimed.
Additional native annotated-format examples: native/hmmconvert_annotated_3a
through native/hmmconvert_annotated_3f retain the actual conversion stdout of
native/hmmbuild_annotated/profile.hmm. All six exit0 and preserve supplied
illustrative protein GA/TC/NC pairs plus RF/CS/MAP. Actual byte sizes by revision
a,b,c,d,e,f are6696,6712,6712,6712,6746,6752. CONS only appears from3/e;
MM only from3/f. 3/a VMU is -5.908600 (the MSV location in this source writer),
whereas3/b-f VITERBI location is -6.1309; do not infer historical VMU equals
the separately stored modern VITERBI value. Neither source model nor conversion
emits COM lines; COM handling still needs an explicitly supplied test case.
