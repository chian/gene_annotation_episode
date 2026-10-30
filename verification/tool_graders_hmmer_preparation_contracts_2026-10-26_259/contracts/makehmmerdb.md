# makehmmerdb — proposed index preparation contract

Bundled HMMER3.4 executable present; full makehmmerdb.c/fm_alphabet.c and complete
fm_readFMmeta plus structs inspected. Invocation `makehmmerdb [options] seqfile
binaryfile`. Inputs: complete supplied sequence collection (`sequences`), explicit
alphabet/format when selected, bin length, SA frequency and block size. Outputs:
one complete `fm_database` binary, stdout parameter header, stderr native elapsed
seconds and receipt. Native supports DNA and RNA input, converting U to T in its
DNA index; hidden --fwd_only produces one traversal index. Source also exposes
--amino and can produce an amino index, but current fm_readFMmeta explicitly
rejects alph_type!=fm_DNA, including in downstream exactmatch. Do not call an
amino output a usable nhmmer or exactmatch database. Its generation is observed,
its consumption is unsupported in this source version.

Use ordinary explicit paths. Native output '-' is passed to fopen as a literal
filename, despite generic command-line wording suggesting streams. Do not treat
it as stdout. Temporary fmtmp file and all outputs must be confined to the chosen
attempt directory. Native input formats are Easel sequence formats; initial pure
extraction may establish FASTA only and leave other formats explicit unsupported.
--bin_length must be a power of2 in32..4096 (error text incorrectly says128);
--sa_freq must be a strictly positive power of2 (native misseszero validation),
and block_size is positive integer decimal Mbases, <=3500 before conversion;
avoid overflow. Options must be caller-selected, not resized by infrastructure.

Binary format has NO magic/version marker; do not infer it from suffix. Require
explicit producer version, byte order and exact format contract/source binding.
Fields are serialized individually, without C struct padding. On this retained
little-endian native build, header is `<BBBBIIIHIIQ` (34bytes): fwd_only,
alph_type, alph_size, charBits, freq_SA, freq_cnt_sb, freq_cnt_b, block_count,
seq_count, ambiguity_range_count, total_char_count. `seq_count` counts stored
segments, not necessarily unique original sequence occurrences; total_char_count
excludes overlap duplicated between FM blocks. AlphDNA=0,size4,bits2;
amino=4,size26,bits5. Index alphabet types are categories, not numeric scores.

Each seq_data row serializes `<IQIIHHHH`: target_id(zero-based source sequence
ordinal), target_start(one-based source coordinate), fm_start(zero-based block
offset), length(symbols), name/acc/source/desc byte lengths, followed by their
NUL-terminated byte strings in that order. Keep each row occurrence and original
source sequence occurrence; repeated names/bytes do not merge. Ambiguity ranges
are signed int32 lower/upper, zero-based inclusive within the relevant block;
associate using each block's ambiguity offset/count. Native replaces ambiguous
DNA symbols with fixed-seed42 random canonical letters and retains ranges. Keep
original sequence and ambiguity symbols; substituted letters are generated
index representation, never observed source residues.

Each index block has `<QIIIIII`: N(includes one terminal sentinel), term_loc,
seq_offset, ambig_offset, overlap, seq_cnt, ambig_cnt. Forward-search section
stores packed original T, BWT built on reversed T, SA samples and occurrence
counts; paired section stores the other BWT/counts but no T/SA. DNA stores4symbols
per byte, high2bits first; sentinel is encoded as A with separate term_loc.
Lengths: packed=ceil(N/4); SA entries=1+floor(N/freq_SA); b-count rows=
1+ceil(N/freq_cnt_b); sb-count rows=1+ceil(N/freq_cnt_sb). Each row has alph_size
uint16/uint32 counters respectively. Original T excludes its final sentinel when
comparing input residues. Forward-only changes storage/traversal availability,
not the original sequence population. Preserve complete block arrays even if
episode-facing result requests only counts.

Proposed pure ports: `extract_hmmer_fm_database(content:bytes, *, occurrence,
producer_contract) -> {metadata,segments,ambiguity_ranges,blocks,issues}`;
`populate_makehmmerdb_sheet(*, sequences, database, stdout, stderr, operation,
receipt) -> sheet`; `calculate_makehmmerdb(sheet, *, source_bindings,
alphabet_normalization, producer_contract) -> calculations`.
Checks compare unique target IDs/segments/covered source intervals, exact
normalized original sequence bytes outside recorded ambiguous ranges, character
count, overlap handling, array sizes/offsets, sentinel representation and block
population. Calculations expose original sequence count, segment count, source
symbol total, ambiguity union length/fraction with explicit denominator and
actual file bytes. Full BWT/SA/internal counter validation can be a separate
explicit decoder validation level; metadata parsing alone is not proof of it.
Neither index size nor validation success is annotation confidence.

Failure states distinguish unsupported/unversioned format, incomplete header or
arrays, missing source occurrence, segment/reference mismatch, repeated labels,
inconsistent counts/ranges, invalid options, binary overwrite/write failure,
and incomplete attempt. Native success does not prove downstream compatibility.
Prerequisites: exact SSE-capable executable/build, supplied inputs, local
allocation20GiB/4GiB/no wall limit and explicit output/temp directory. Future
preparation driver/result-worker collects exact index and originals; typed return
reports format/compatibility/populations and artifact refs via COMMON.md. No
automatic downstream search/index test, remote binding or biological observation.

Native examples with --block_size1: makehmmerdb_dna index314bytes, makehmmerdb_fwd
226bytes, RNA339bytes, amino618bytes, ambiguous325bytes; all exit0. DNA header
is(0,0,4,2,8,65536,256,1,2,0,28). Its two source sequences have16+12=28nt;
segment(target_id,start,fm_start,length) tuples=(0,1,0,16),(1,1,16,12),
first blockN29 includes sentinel, seq_count2, no ambiguities. RNA retains U in
source but decoded index T is the DNA-normalized equivalent. Amino header
(1,4,26,5,8,65536,256,1,2,0,40) is writer output only, not supported reader input.
Ambiguous source has18nt, ranges[4,5] and[10,13], union6nt/fraction1/3;
packed original T decodes ACGTGGACGTATGTACGT (excluding sentinel), preserving
generated replacements separately. makehmmerdb_invalid_bin --bin_length31
exits1 with native error and no successful index. Retained receipts/logs support
these facts; no production parser, calculator or episode binding is claimed.
