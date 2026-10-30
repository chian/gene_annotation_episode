# Additive core clarification 002

This clarifies the three incomplete pure-core fields in INTERFACES_001.md without
changing the original user goal or adding modes. Use 001 plus this clarification
as the proposed coding contract. This is source-based planning; native compatibility
remains the separate bounded oracle's responsibility.

## 1. One parameter authority

`sequence_masking_contracts.py` owns all program/mode parameter shapes. The native
compiler imports and uses that validator; it must not create a different parameter
schema or admit an unparsed free-form options list. Every key in the following
objects is **required**. Each value is explicitly nullable. Null means “the caller
did not select this native option; omit its CLI argument.” It does not mean zero,
false, a recommendation, a guessed default or a known effective native value.

No calculator changes these native parameters. The complete Operation, exact
compiled argv, native version when measured, original stdout/stderr, and native
statistics metadata preserve what was requested and what is actually observable.
Default values inferred solely from different-version source stay unknown.

```text
dustmasker / mask requested_parameters = {
  window: integer>=1 | null,
  level: integer>=0 | null,
  linker: integer>=0 | null
}

segmasker / mask requested_parameters = {
  window: integer>=1 | null,
  locut: finite number>=0 | null,
  hicut: finite number>=0 | null
}

windowmasker / mask requested_parameters = {
  window: integer>=1 | null,
  t_extend: integer>=0 | null,
  t_thres: integer>=1 | null,
  t_low: integer>=1 | null,
  t_high: integer>=1 | null,
  set_t_low: integer>=1 | null,
  set_t_high: integer>=1 | null,
  t_low_pct: finite number in [0,100] | null,
  t_extend_pct: finite number in [0,100] | null,
  t_thres_pct: finite number in [0,100] | null,
  t_high_pct: finite number in [0,100] | null,
  dust: bool | null,
  dust_level: integer>=0 | null
}

windowmasker / create_counts requested_parameters = {
  checkdup: bool | null,
  mem: integer>=1 | null,
  unit: integer in [1,16] | null,
  genome_size: integer>=1 | null,
  meta: string without NUL | null,
  t_low: integer>=1 | null,
  t_high: integer>=1 | null,
  t_low_pct: finite number in [0,100] | null,
  t_extend_pct: finite number in [0,100] | null,
  t_thres_pct: finite number in [0,100] | null,
  t_high_pct: finite number in [0,100] | null
}
```

All integer options additionally fit the native signed 32-bit CLI range. `bool`
does not qualify as an integer. Floating-point inputs must be finite. No extra
key is allowed. No `locut <= hicut`, threshold ranking, presumed window-length
ordering or other unestablished scientific relationship is fabricated; retain
native rejection as a native failure. The supplied bounds above constrain the
proposed supported interface, not a claim that every binary accepts every value.

Names map literally to native options (`window` -> `-window`, etc.). Floats are
serialized by one deterministic round-trip-safe representation. Explicit boolean
keys such as `dust` and `checkdup` use native boolean values `true`/`false`, with
installed syntax confirmed by the oracle. `parse_seqids` and DUST `hard_masking`
are native flags derived from Operation fields, not parameter-object keys.
Masking style hard is legal only for DUST FASTA; interval style only for interval;
create_counts has output ascii_statistics, style not_applicable and
parse_seqids=false. Unsupported parameter/program/mode combinations are schema
errors before selected execution, not silently ignored options.

`-in`, `-out`, `-infmt fasta`, selected `-outfmt`, `-ustat`, `-mk_counts`,
`-sformat ascii` and explicit uncompressed-mode selection are compiler-owned
arguments derived from the job and declared artifact operands. Do not expose path
overrides in parameters. Do not emit `-outfmt` in create_counts or `-sformat` in
mask mode. One mode must not acquire the other mode's input or output automatically.

Numerical meanings: DUST window/linker are nucleotide counts and level is the
native algorithm's threshold; SEG window is an amino-acid count, while locut/hicut
are native SEG trigger/extension thresholds. WindowMasker window/unit are nt
counts; count/window thresholds and replacement scores stay in native score/count
units, without conversion to confidence or entropy. The `_pct` options are native
percentile selectors, not masked proportions. `mem` is native megabytes available
to counts generation; it is not the outer process allocation or an observed usage.
`genome_size` is a supplied count-generation parameter, not a measured denominator
for mask fraction. `meta` is retained native metadata, not model instructions.

Statistics metadata may record thresholds and `##pct`; those are measured native
fields in WindowMaskerStatistics. A native fallback/ignored percentile override
does not become effective just because the caller supplied it. Preserve the
requested parameter, original warning, and unavailable effective value. Do not
reverse-engineer or rerun the native masking algorithm in the calculator.

## 2. Unknown versions and public validator kinds

`Operation.engine_version` is **nonempty string or null**. Null means unknown.
The host may set a string only from the selected executable's authenticated native
version record or a clearly supplied declaration; the core does not discover it.
The occurrence/custody qualification distinguishes authenticated from supplied
artifacts. Unknown version does not license a fabricated current release string.

Add `InputParse` and `NativeOutcome` to the public
`validate_sequence_masking_record(kind, value)` kinds. Also expose the explicitly
defined `Count`, `Fraction` and `RecordComponents` kinds so the result projection
can validate them without defining another schema. The total set is:

```text
Operation, Occurrence, InputRecord, Custody, ParsedMaskOutput,
SequenceMaskingSheet, SequenceMaskingComponents, StatisticsBinding,
WindowMaskerStatistics, NativeOutcome, InputParse, Count, Fraction,
RecordComponents, Failure, Check
```

## 3. Invalid sequence retention and denominator semantics

`InputRecord.length` is **integer>=0 or null**. The parser first removes FASTA
layout whitespace to produce `original_sequence` with its original character
case. `normalized_sequence` is the uppercase version of that same string. It
does not remove gaps, discard bad symbols, substitute N/X, or reinterpret RNA as
DNA. Both strings retain invalid content as data; original raw bytes remain in
the input artifact.

For a complete, compatible, gap-free record in its declared molecule alphabet,
`length = len(normalized_sequence)` and measures nt or aa positions. For gaps,
unsupported symbols, incompatible molecule, truncated/unreadable input, or any
other failure to establish that substrate, `length=null`; an input-stage typed
failure identifies the record and reason. Such an input must never supply a mask
fraction denominator, even if the number of characters is easily counted. The
native binding rejects it before launch rather than silently repairing it.

A genuinely parsed header with no sequence has known `length=0`, remains an
explicit empty record, and receives an empty-record check/failure for the first
native binding. It is not submitted. Its pure mask fraction is undefined with
`zero_denominator`, not zero. An empty or missing file produces no fabricated
record; it has a file-level failure. An unknown sequence length stays null.

The initial declared alphabets are the existing normalized substrate alphabets:
DNA `ACGTNRYKMSWBDHV`; protein `ACDEFGHIKLMNPQRSTVWYBXZJUO*`. Compatibility with
the selected native tool is separately qualified by actual native behavior. An
accepted native normalization that changes a supplied symbol must be explicit
and tested before exact mask inference; no general replacement convention is
assumed. Keep gaps unsupported in this raw-sequence interface.

Checks/failures associated with inputs remain in the sheet's `checks`/`failures`.
To make that flow explicit in the existing `inputs: list[InputRecord]` port, add
two required fields to the 001 InputRecord shape: `checks: list[Check]` and
`failures: list[Failure]`. The input parser also aggregates those into InputParse.
The population function carries them forward from each input and custody, including
any `length=null` reason, rather than making an incomplete input valid because an
output block exists. `input_length` components are null with that reason, and all
derived exact mask quantities/fractions are null when their substrate is invalid.
