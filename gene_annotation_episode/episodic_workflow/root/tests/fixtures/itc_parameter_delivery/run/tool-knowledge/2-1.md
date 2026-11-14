# Native BLAST supplied-pair correspondence

## Operation and selection

`native.blastn`, `native.blastp`, `native.blastx`, `native.tblastn` and
`native.tblastx` compare one supplied FASTA query with one supplied FASTA subject.
These local operations answer residue-correspondence questions. Database
identification is a distinct operation and is not an available local route here.
A tool entry does not grant scientific or root episodes direct native execution.

Choose the program from the actual molecules: blastn uses nucleotide/nucleotide,
blastp protein/protein, blastx nucleotide/protein, tblastn protein/nucleotide,
and tblastx nucleotide/nucleotide translated on both axes. Supply exact input
byte hashes, byte sizes, original artifact references when available, and
record-zero identities for the two actual single-record FASTA files. Keep the
original full lengths and any selected intervals. Names alone do not establish
sequence identity, and equal lengths do not establish an operand association.

The configured software binding is an absolute executable path, its SHA-256 and
the declared native version. The contract preserves selected native task,
strand, genetic code, ranges, scoring, filtering, hit/HSP limits and threads.
A compiler preserves those tokens and supplies only the explicit query, subject,
report-format and output-path operands. It rejects database, remote, strategy
import/export and additional path operands. It does not install software, build
an index, select another resource, change a parameter or retry a search.

## Launch and custody

Commission the requested job through the existing launch episode and configured
`launch_local` child. That child owns practical preparation and selects
`practical.job.start`. The caller's existing local lifecycle enforces its
allocation. Verification uses 20 GiB memory, 4 GiB scratch and no wall-time cap.
The native producer is one selected primitive, not a new episode or agent loop.

`requested_job_from_native` constructs the exact requested argv/environment and
`native_blast` job. `validate_native_blast_requested_job` verifies that the
wrapper equals the compiler's output. The producer stages the exact two inputs,
checks their single-record FASTA content and selected ranges, executes one native
process, and seals `native_blast_bundle_v1`. The bundle keeps original selection,
realized argv/environment, native return code, complete stdout/stderr/report,
original and staged input identities, output byte hashes and structured failures.
Temporary/cache/output paths remain within the selected attempt directory.

A sealed attempt replays its retained result without another process. An
unsealed prior attempt is uncertain execution, not permission to retry. Failed
staging and partial native output remain retained; missing reports are failures.
The producer never executes a second search to obtain another report format.

## Monitoring

Use existing generic local monitoring instructions and native execution status.
Observe the selected attempt's native state, return code, stdout/stderr, retained
output availability and measured execution information. Complete logs remain
available even if a decision requests a short view. Process liveness does not
establish productive progress. BLAST does not provide a universal completion
fraction through these artifacts; no throughput, stall judgment, cancellation,
fixed polling cadence or continuation rule is added here.

## Original reports and results

Select exactly one primary report: single-file BLAST JSON (`json15`) or explicit
columns with `tabular6` or `tabular7`. Tabular descriptors carry the actual fields
and delimiter. `std` is not an explicit column declaration. For full correspondence,
select qseqid/sseqid, qlen/slen, qstart/qend/sstart/send, qseq/sseq, qframe/sframe,
length/nident/gaps and score/bitscore/evalue. Native tables may round scores;
retain their actual reported values. Sparse columns keep missing quantities
unavailable rather than manufacturing traceback or denominators.

Results acquisition retains the entire original sealed bundle and source
artifacts. `parse_blast_report_collection` consumes their actual declared formats
and original invocation. Its searches preserve report/search pointers, original
row maps, program identity, native fields, query binding, completion facts and
issues. Format is never inferred from API/local/HPC placement. Unresolved
program geometry cannot be repaired by substituting the executable name.

`populate_blast_pairwise_sheet(search, operand_bindings=...)` validates supplied
query/reference relationships and stores a copied numerical sheet with exactly
`schema`, `search` and `operand_bindings`. Both actual operand descriptors carry
subject_ref, length, molecule, artifact_key, native_id and selected_interval.
The host authenticates these against the selected original inputs and options.
The sheet preserves native measurements independently of calculation.

`calculate_blast_pairwise_components(sheet)` is separately callable on saved
JSON. It performs no source access, network request, executable call or model
call. It reuses the existing BLAST correspondence arithmetic and retains native
HSP scores separately. The complete components remain saved; the existing
results host returns only the parent's requested typed numerical quantities.
Parsing, calculation and projection do not create additional actions or credit.

## Numerical meanings

| Quantity | Inputs and calculation | Units and denominator | Missing or conflicting input |
| --- | --- | --- | --- |
| Alignment columns | Number of columns in equal-length qseq/hseq; native align_len is preserved separately | aa columns for protein/translated alignments; nt columns for blastn | Without traceback, usable reported counts remain; invalid strings do not become correspondence |
| Paired columns | Columns with a nongap symbol on both axes | Count of residue pairs | Reported align_len minus reported gaps is available without traceback when valid |
| Identical pairs | Paired columns with equal uppercase symbols | Count of residue pairs | Native identity remains separately available; inconsistencies are explicit |
| Substitutions | Paired columns minus identical pairs | Count of residue pairs | Unknown when either count is unavailable |
| Query/reference gaps | Hyphens on the corresponding traceback axis | Count of alignment columns | Unknown without valid traceback |
| Paired identity | Identical paired columns divided by paired columns | Fraction; denominator paired columns | Null for zero/unknown denominator; union identity is withheld for conflicting mappings |
| Alignment identity | Identical pairs divided by all alignment columns | Fraction; denominator includes gap columns | Valid native reported percentage may survive missing traceback |
| Original correspondence | Each nongap symbol maps to its original interval; translated symbols span three nt | Zero-based half-open original nt/aa intervals | Invalid spans, phase, bounds or direction retain counts but withhold geometry |
| HSP paired coverage | Paired original positions divided by actual full operand length | Fraction, separately on each original operand | Unknown without valid geometry or denominator |
| Union coverage | Length of the union of paired intervals across all valid HSPs divided by actual full length | Fraction on each operand; duplicates/overlaps counted once | This is observed-union coverage, not one selected global alignment; incomplete geometry is qualified |
| Selected-operand coverage | Union paired positions within the explicit selected interval divided by interval length; full length when selection is null | Fraction; numerator and denominator retained | Null for incomplete/unavailable geometry; zero only for an established zero population |
| Native raw/bit/E scores | Actual per-HSP native score, bit_score and evalue | Native score units, bits, expected count respectively | Missing remains null; alternatives are not summed |

The `coordinate_context` explicitly retains each native reported length, actual
full length, selected interval and original coordinate unit. Native query_loc can
make reported query_len equal the selected span while endpoints still reference
the full sequence. No offset is added. Full and selected coverage remain distinct.
For example, query_loc31-210 with 180 paired nucleotide positions in a 240-nt
query gives full coverage180/240 and selected coverage180/180.

BLAST JSON translated negative-frame HSPs can report ascending endpoints; native
tabular reports instead use descending endpoints. The shared geometry helper
handles that explicit JSON convention without changing saved native endpoints
or frames. Untranslated reverse blastn keeps its native descending coordinates.
For reverse blastx query_loc30-215 in a 244-nt input, 62 paired amino-acid columns
cover 186 query nt: full coverage186/244, selected coverage186/186. The first
paired original codon is [212,215), followed by [209,212).

E-value is a retained native measurement and never a paired-sequence relevance
multiplier. None of these quantities is annotation confidence. Numerical
uncertainty is not invented when the native tool supplies none. Successful
zero-hit, missing report, bare empty unqualified table, partial geometry,
malformed fields and failed execution remain distinguishable. A successful
process receipt alone is not a scientific result or proof of full episode-path
integration.
