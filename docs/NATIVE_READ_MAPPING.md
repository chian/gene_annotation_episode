# Native placements and literal read support

`reads.map` is one ordinary indexed mapping action. The Episode chooses an
existing immutable original-read selection, actual reference operands and a
genomic minimap2 preset. The Episode owns scientific interpretations and its
choice of subsequent investigation. The mapper itself makes no taxon,
annotation, correction, assembly or consensus assignment. The adapter downloads
no software.

```toml
[local_tools]
minimap2_executable = "/absolute/path/to/minimap2"
minimap2_cpu = 1
minimap2_cache_dir = "/absolute/path/to/derived-index-cache"
```

CPU defaults are declared in `defaults.toml`; an absent cache directory resolves
at the ToolRegistry boundary to `workspace/cache/minimap2`. Catalog and native
provenance record the actual path. Later caller resource changes affect new
work; committed operation replay retains its original result. An unconfigured
binary returns ordinary unavailable feedback, without a download or substitute.
The supported native integer interface is kmer 1..28, window 1..255, CPU
1..2147483647, and seed/max_secondary 0..2147483647, matching the pinned native
representation.
Unrepresentable values return field/range feedback before native execution;
they are never narrowed, clamped or replaced. These are representation limits,
not scientific quality thresholds or work budgets.
The existing action-schema boundary reports the selected numeric field, failed
keyword and declared bounds. A selection rejected there never executes or
creates an own-action observation. Direct tool calls expose that same schema
failure; caller CPU errors identify `local_tools.minimap2_cpu`.

```json
{"query_selection_ref":"read_selection_<actual-id>",
 "reference_refs":["reference_<actual-id>"],"preset":"map-ont",
 "parameters":{"secondary":true,"max_secondary":5}}
```

`max_secondary=0` retains native `-N0` semantics: minimap2 disables secondary
output and restores the prior preset's internal best_n, including when
`secondary=true` is also requested. The adapter preserves both requested flags
and discloses this native effect in `native_option_effects`; it does not rewrite
the Episode's request or treat the alias as a result-quality decision.

The explicit selection must fit the assigned members and whole queried-read
intervals. Reference operands can be outside a local annotation assignment;
their reuse grants no write ownership or target extent. DNA processing alphabet
checks do not classify unspecified material or silently convert RNA U symbols.
The initial mapping interface queries whole selected original reads.
The same actual entity may occupy query and reference roles. Its dependency set
contains that identity once, while physical query/reference roles and native
placements remain separate. A self-comparison is not by itself independent
biological support; interpretation remains the Episode's responsibility.

Packed original members stream to FASTA using stable read_subject IDs. Duplicate
native titles do not merge members. Original FASTQ bytes and qualities remain
unchanged; mapping does not use those qualities or infer pairing. Native
unpaired fragment mode is explicit. No host result threshold is applied.

The adapter requests PAF base alignment (`-c`, `--cs=long`). Every projected
placement is an existing `alignment` observation with actual separate operands
and native local bounds. Tool-only `native_minimap2` stores its byte/line locator,
strand, MAPQ and alignment type. MAPQ255 remains missing. Full PAF, stderr,
version/help, staged inputs, actual commands and executable digest are retained.
Independent malformed rows retain exact source/error windows while valid
siblings survive. A row without a base path acquires no invented site map.

Index cache identity binds actual staged reference bytes/identifiers, preset,
index overrides, native version and executable digest. Reused bytes are copied
and digest-checked; original build command and diagnostics remain available.
Incomplete disposable cache entries rebuild locally within the selected action.
Mapping-only options do not pretend to change fixed index options. Native
heuristics, secondary ranking, unset preset defaults and multi-part-index MAPQ
limitations remain explicit, rather than becoming biological verdicts.

One `source_content` observation retains **search scope/result custody** for both
zero and positive results. It names the library container, exact query selection
and actual reference dependencies, with empty physical operand intervals. Its
count is projected native placements, not biological absence or completeness.
Declared source `query_selection_ref`, `operand_refs` and auxiliary artifacts
preserve derived operand ancestry and raw bytes even when no placement exists.
The container does not mean that unselected members were searched. This uses the
existing zero-credit source_content binding and adds no controller action.
Custody can remain readable in a disjoint member scope as reusable context.
A generic observation-reference form can carry that actual custody record; its
field name does not manufacture a measured-scope promise. The record/source
still names the original searched selection, supplies no physical extent or
credit for disjoint members, and grants no library-wide mutation authority.
Disjoint export retains that provenance while its eligible geometry stays the
requested scope. Stronger kind/extent promises are not invented by this adapter.

Native result rows have a twelve-row preview and exact placement total.
`all_observations_query` pages the same source's typed `alignment` and
`source_content` rows; `query_result_kinds` declares both. Complete publication
IDs remain in durable `record_refs` and recorded committed/last-outcome form
facts. Runtime automatic last-outcome presentation uses caller-owned
`restoration.preview_size`, with total/included/truncated counts. Visible basis
uses actually presented context. Truth in source.last_outcome/journal, admitted
child forms and explicitly selected exact history/query reads is unchanged.
Presentation makes no extra model call or controller observation.
Mapping uses the shared host `native_publications_v1` batch declaration, also
used by generated gene/sequence and selected read batches. Its preview supplies
a bounded own-action `episode.history` publication-ID query; exact journals and
explicit reads retain the full result. See
[bounded restoration](BOUNDED_RESTORATION.md#generated-publication-batches-and-bounded-id-recall).

`sequence.sites` accepts positions or a half-open reference window and uses the
actual backend. Reverse-strand query coordinates/quality indices stay on the
original query; oriented and original bases are separate fields. Deletions have
no query position. Insertions occupy a reference boundary, not an invented
reference residue. Outside-alignment positions have no measured query base.
Only known declared quality encodings produce numeric character scores; unknown
encoding retains raw characters and null scores. Scores are not recalibrated
accuracy. Actual queried-original positions must fit assigned scope.
An actual unmapped aggregate/correction product remains locally inspectable
when its existing aggregate attribution is owned; local product coordinates do
not become an invented exact original-position map.

Literal base/gap inspection now publishes `kind=comparison` for **both** backends,
with source version `literal_alignment_sites_v2`. It is not a mechanistic
experiment. This corrects future tool outputs without rewriting old observations
or rescoring frozen investigations. Hypervolume, evidence weights, target
denominator, signed deltas and continuation controller are unchanged.

Episodes still own error-versus-disruption, reference bias, repeats, assumptions,
conditions, competing interpretations and subsequent work. Existing assessments,
coherent current annotations and parent-defined forms use actual member-local
extent and typed source-bound references. Mapping counts/activity earn no
automatic annotation credit; no consensus or variant verdict is generated.

Engineering fixtures use explicitly synthetic reads, actual pinned native
minimap2 and scripted providers. They cover coordinates, source custody, selected
scope, failures/cancellation, replay/cache identity, zero/positive portable
closure, complete form facts beyond preview and one parent action per child.
These checks do not establish intelligent annotation or biological accuracy.
Input/output normalization is disk-streamed, but existing publication-ID tracking,
complete form facts and explicitly requested site windows can grow with work.
No arbitrary-library constant-memory/throughput claim is made. Disposable native
index bytes are not required in portable export; build/digest provenance is.

Assembly/consensus identity and read-to-consensus attribution remain unimplemented.
A polished base is not exact extraction; alignment CIGAR is not a derivation
`sequence_mapping`. Repeated reads/views do not prove independent molecules, and
checking a future assembly with its own construction reads is not independent
validation. No assembly requirement, forced child topology, gate or stopping rule
is introduced.

Primary interfaces read: [pinned README](https://github.com/lh3/minimap2/blob/v2.31/README.md),
[pinned manual](https://github.com/lh3/minimap2/blob/v2.31/minimap2.1),
[official release](https://github.com/lh3/minimap2/releases/tag/v2.31).
