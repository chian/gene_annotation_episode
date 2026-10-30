# Implemented sequence-database numerical port

`gene_annotation_episode/blast_sequence_database.py` exports
`populate_blast_sequence_database_sheet(search, *, report_source,
search_binding, query_binding, reference_metadata, description_bindings,
sequence_identity_bindings, target_context=None, database_profile=None)` and
`calculate_blast_sequence_database_components(sheet, *, model=None)`.

The population function copies the complete original 293 search and all supplied
relationships into `blast_sequence_database_result_sheet_v1`. Native HSP scores,
counts, endpoints, strings, all descriptions, every native row, retained original
document/text, query/report/member identity, completion facts and original
request remain in that saved sheet. It validates finite JSON and caller shape;
it does not acquire, execute, publish, or assign annotation credit.

The calculator returns the exact frozen
`blast_sequence_database_result_components_v1` outer shape. Its detached legacy
calculation input contains qualified full lengths and source locators. The saved
outer sheet is unchanged. Invalid source/member/row relationships cannot be
repaired with an accession match, array position, program rename, fabricated
request field or inferred DELTA stage.

## Native and derived numerical fields

| Field | Source or formula | Units / denominator | Missing or incompatible inputs |
|---|---|---|---|
| `coordinate_context.query.reported_length` | Original normalized native `query_len`/`qlen` | Original query aa or nt | Null if not reported/valid; never rewritten as full length |
| `coordinate_context.query.full_length` | Exact complete QueryBinding operand matched to collector `operand_binding`; query-kind/master requirements also validated | Original query aa or nt | Null for absent/unbound/wrong operand, units, full length, native identity, or master mapping |
| `coordinate_context.query.selected_interval` | Exact bound operand selection | Zero-based half-open original query coordinates | Null when unselected or unbound; native endpoints receive no offset |
| `coordinate_context.references[].reported_length` | Original hit `len`/`slen` | Original target-sequence aa or nt | Null if absent or invalid |
| `coordinate_context.references[].full_length` | Native target full length or qualified exact full-sequence binding; both must agree if both exist | Target-sequence aa or nt | Null for incompatible supplied length/sequence relationships |
| `selected_query_coverage[].numerator` | Union of valid paired query intervals intersected with selected interval, per original hit | Original query aa/nt positions; overlapping HSPs counted once | Null when no qualified observed union; an observed partial union can remain numerical |
| `selected_query_coverage[].denominator` | `selected_interval[1] - selected_interval[0]` | Same query coordinate unit | Null without a qualified explicit selection |
| `selected_query_coverage[].value` | Numerator / denominator | Fraction | Null for incomplete native HSP set/geometry or missing denominator; partial union is never complete coverage |
| `database_sheet.hits[].hsp_components[].native_scores` | Native bit score, raw score, E-value, with original precision | Native bits/score/E-value conventions | Native zero remains zero; missing/invalid values remain null |
| `database_sheet.hits[].hsp_components[].reported_counts` | Native alignment length, identities, positives, gaps | Alignment columns | Separate from traceback-derived counts |
| `database_sheet.hits[].hsp_components[].counts` | Existing shared traceback calculator; paired and identical columns, query/reference gap columns; paired positions | Alignment columns plus original-axis aa/nt positions | Counts remain readable without geometry when strings are valid; absent traceback does not create coordinate coverage |
| `database_sheet.hits[].hsp_components[].pairs` | Existing native-format-aware correspondence | Zero-based half-open original-axis intervals; translated residues occupy 3 nt | Native JSON2 negative-frame endpoints use existing JSON2 convention; tables use directional convention |
| `database_sheet.hits[].measurements` | Max HSP bit score, min E-value, retained component count, paired unions, unique/identical pair counts, duplicate representations | Per native hit; full-query and target lengths are separate denominators | Missing/malformed HSP siblings invalidate complete hit coverage but preserve valid observed quantities |
| `database_sheet.sequence_groups` / `dependence` | Existing exact supplied SHA-256 + molecule + full-length relation | Demonstrated target sequence groups | Distinct unresolved groups are model components, not independent experiments |
| `database_sheet.taxonomy` and function-specific taxonomy | Existing per-rank sequence-group counts; same-taxon pairs / comparable pairs; target matching/conflicting/ambiguous groups | Explicit groups and pair denominators | Missing lineage/target remains missing; no HGT inference |
| `database_sheet.source_quality` | Supplied completeness, contamination, contig count, N50, total length, with source/method | Actual source units and documented conversions | Categories never become confidence weights |
| `database_sheet.database_representation` | Matching supplied database identity, release, scope and sequence/group census | Actual database sequence/group counts | Unknown release/scope, mismatch, wrong count units or invalid counts disable only correction |
| `function_weights.sequence_group_contributions` | Existing `2 ** ((bits - largest_scored_function_group_bits) / temperature_bits)` once per group; split equally over its explicit functions | Chosen reference-similarity kernel | Native score/function absence stays explicit |
| `function_weights.function_masses` | Sum per-function kernel contributions | Conditional model mass | Strong unannotated hits retain separate all-group baseline/mass |
| `function_weights.unadjusted_probabilities` | Normalize `prior[f] * mass[f]` | Conditional on supplied scored groups and functions | Null without scored assignments; never calibrated annotation correctness |
| `function_weights.representation_adjusted_probabilities` | Normalize `prior[f] * mass[f] / database_count[f]` | Matching actual function-population counts | Null if correction lacks qualified population evidence |

No new uncertainty interval is fitted. Original native statistical quantities,
supplied metadata, model assumptions and parameters remain inspectable. The
model's retained-but-unused list remains unchanged: taxonomy, target taxonomy
agreement, source quality, annotation evidence codes, alignment coverage,
identity and shared studies.

## Identity, provenance and result qualification

The RowIndex maps legacy component positions to original hit, description and
HSP ordinals. JSON locators point into the unchanged native document using the
native singular `description` field. Table locators retain `/sections/N` and
actual data-row ordinals/line membership; independently sorted plural metadata
is not paired by position. The full SearchKey is checked before any legacy link
validator sees the inner binding.

The JSON report index must match the exact original `BlastOutput2` report
pointer: array entries retain their canonical index, and the object form has
report index zero. Equal report contents do not make two indices interchangeable.
Tables require null member ordinal, report index zero, and exact equality with
the SearchKey rebuilt from their retained text and supplied layout.

The table check consumes only the collector's exact `table_layout` descriptor:
original `format`, original nullable `declared_fields`, and effective `delimiter`.
It never guesses these from symbols or comment-like text. An old saved search
without that descriptor remains explicitly unavailable; no historical record
is rewritten.

The archive member digest is the exact decompressed member-byte digest from
workload 304's `archive_member.sha256`, distinct from container `native.sha256`.
Absent and conflicting digests produce different issues. Acquisition remains
responsible for authenticating `artifact_ref`, supplied complete sequence bytes,
and provenance records against actual captured artifacts. The pure adapter
validates supplied relationships; it does not authenticate a Store through I/O.

`complete`, `partial`, `no_reported_hits`, `unavailable` and `incompatible` are
result-data qualifications, not scientific acceptance or continuation gates.
PSSM/MSA master coordinate axes are not published as biological query sequences.
The adapter makes no publication call and defines no new episode or runtime gate.

## Shared legacy ports and consumers

`build_database_sheet` adds only `geometry_program=None` and
`calculation_context=None`. Null preserves legacy behavior/schema. Explicit
geometry must exactly match each ordinary executable or the established
PSI/DELTA → blastp map. RPS and VDB cannot use that port. The execution program
remains unchanged. Qualified geometry reaches both alignment calculations and
exact sequence-identity links.

The context carries original reporting facts and supplied database identity;
requested hit/HSP limits and release/scope stay separate from the original
request. Existing `blast_graders.grade_blast_result` and
`bvbrc_homology_grader.build_homology_sheet` remain null-port callers. Their
calculation consumers retain the existing formula. No iteration, HPC execution,
result publication or typed episode-return consumer is installed by this work.
