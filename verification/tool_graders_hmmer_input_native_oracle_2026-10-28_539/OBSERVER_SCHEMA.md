# Native input observer output and meaning

This is diagnostic verification only. Actual native values are produced only when
root executes the bounded job. The observer is not a second scientific calculator,
a HMMER CLI artifact, a cmemit producer receipt, or a production dependency.

`input_observer classifier A B ... Z` receives exactly 26 explicit nonnegative
int64 counts. It refuses overflowing totals and narrowed counts above INT_MAX
before entering native code. `guess FORMAT ALPHABET /absolute/input` and
`read FORMAT ALPHABET /absolute/input` require a declared Easel format and one
of `auto`, `amino`, `DNA`, `RNA`. Tests supply only pinned, staged input paths.

The top-level JSON object has exactly these keys:

| Field | Meaning |
|---|---|
| kind, version, easel_version | `diagnostic_easel_alignment_input`, 1, original EASEL_VERSION |
| mode | `classifier`, `guess`, or `read` |
| format, requested_alphabet | Original declared arguments; both null in classifier mode |
| status | Actual classifier/guess return, open failure, or read return, according to executed operation |
| open_status, read_status | Actual C return if that operation occurred; null otherwise |
| selected_alphabet | Original C enum decoded as amino/DNA/RNA; null for unknown |
| classifier_calls | Ordered actual calls, each `{counts_az: [26 int64], status: int, alphabet: string|null, byte_offset: int|null}` |
| error_hex | Native afp->errmsg C-string bytes as lower-case hex, null without afp |
| read_line_number | Actual afp->linenumber after read, null if no read |
| nseq, alen | Actual digital MSA dimensions, null when no MSA returned |
| rows | Native row order; each row has exactly ordinal, name_hex, digital, description_hex, accession_hex, SS_hex, SA_hex, PP_hex |
| annotations | Native RF_hex, MM_hex, SS_cons_hex, SA_cons_hex, PP_cons_hex; null without an MSA |
| metadata | Native name_hex, accession_hex, description_hex, author_hex; null without MSA |
| unparsed_gc | Native ordered `{tag_hex, value_hex}` column strings |
| unparsed_gr | Native ordered `{tag_hex, row_values_hex}` per-row strings |
| checksum_status, native_checksum_uint32 | Actual esl_msa_Checksum status/value; null without MSA |

All `*_hex` fields are native NUL-terminated C-string bytes, or null if absent.
An empty string is the real empty native string, not missing data. `digital` is
constructed by looking up each actual digital code in the actual alphabet's
`abc->sym`; it is canonical digital text, not preserved lexical source text.
Names remain positional rows even when duplicate names occur. The exact source
bytes remain in pinned input files and the per-case retained native input.

`guess auto` opens in text mode, calls original esl_msafile_GuessAlphabet, and
never reads a row. Its wrapper can see the already-open buffer and records the
actual esl_buffer_GetOffset at each classifier call. No threshold number, line
number, rule label or EOF flag is invented as native instrumentation.
`read auto` invokes native digital Open, including its internal guessing. The
handle is not visible to the wrapper during Open, so those byte offsets are
null. Their histograms/status/alphabet remain actual captured calls. Explicit
alphabets bypass native guessing and produce no classifier calls.

The original alphabet source is compiled with only its classifier symbol renamed.
The wrapper delegates immediately to that function and copies the actual input
histogram and return. Every other relevant compiled native source is unchanged.
A normal diagnostic exits zero even for actual native 3/7/26; the native status
and operating-system return code are retained separately. Native parse errors
return no MSA: diagnostic partial rows are not fabricated. Unexpected exceptions
or build failures remain failed tests with their original stdout/stderr.
