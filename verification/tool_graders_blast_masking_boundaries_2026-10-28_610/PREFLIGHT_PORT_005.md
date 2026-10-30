# Additive pure input-preflight port

The driver validates the actual staged bytes before native submission. Its Job
legitimately permits artifact_ref=null before shared Store capture. It must not
invent an artifact record or a placeholder occurrence merely to call a parser.
This is an implementation boundary correction, not a new workflow or goal.

The pure input owner adds:

```python
preflight_masking_input_fasta(content: bytes, *, molecule: str) -> dict
```

The exact closed result is:

```text
{
  version: "sequence_masking_preflight_v1",
  valid: bool,
  record_count: integer>=0 | null,
  failures: list[{
    code: restricted machine string,
    record_ordinal: integer>=0 | null,
    line_number: integer>=1 | null
  }]
}
```

This function and parse_masking_input_fasta use the SAME internal FASTA syntax,
raw-case/normalization, molecule alphabet, empty-record and invalid-symbol/gap
validation. Factor their common pure implementation; do not copy a second parser
or substrate policy into preflight or the driver. A valid result requires at least
one nonempty compatible record and no input failures. A parsed empty file has
record_count=0 and valid=false; unreadable content can have unknown count. Boolean
counts, invalid molecule arguments and non-bytes caller inputs are schema errors.
Native content errors return typed failures. No files, Store, I/O, native program,
network or model are used by this function. It has no artifact/record/occurrence
identity fields and establishes no custody.

The invocation owner calls this function only after exact staged-byte identity
checks. It records ordinal/line/code input failures and does not submit invalid
substrates. It retains actual input bytes through the ordinary producer/capture
path. Downstream parsing still requires the real captured Occurrence and yields
the already approved InputParse/InputRecord shapes. No existing core shape,
Job/Bundle/Capture, numerical formula or result interpretation changes.

Focused verification compares preflight acceptance and parser input failures on
valid multi-record native fixtures, duplicates/case, parsed empty file/record,
invalid/gapped symbols and malformed content. No fabricated artifact is needed
for the preflight call. Prior066 verification remains recorded; new assertions
run in a separate bounded attempt without rerunning native programs.
