# Profile-search field and function definitions

The implementation deliverables are the field definitions and two pure functions:

- `blast_profile_inputs.populate_blast_profile_sheet(search, *, report_source,
  search_binding, query_binding, profile_records, profile_bindings,
  function_bindings, model_relations, target_context=None)`.
- `blast_profile_calculators.calculate_blast_profile_components(sheet)`.

Populated sheets and components under `examples003/filled/` are verification
outputs. They are not profile-search observations or an annotation exercise.

Population validates exact caller shapes and finite JSON values, detaches inputs,
and retains the complete original collector search and every supplied model
record, including unknown native fields. It performs no score calculation or
scientific identifier join. Calculation revalidates the saved sheet, qualifies
source relationships, and returns the exact frozen v1 components. Neither
function uses a Store, filesystem, network, native process, or model service.

## Input cells

The exact `blast_profile_search_sheet_v1` outer fields are `schema`, `search`,
`report_source`, `search_binding`, `query_binding`, `profile_records`,
`profile_bindings`, `function_bindings`, `model_relations`, `target_context`.

`search` retains actual native numerical HSP measurements, their original
objects/text, all original report/search/hit/description/HSP ordinals, request,
completion facts and collector issues. It is not merely a source catalog.
`ReportSource`, `SearchBinding`, `QueryBinding`, `DatabaseIdentity`, `Provenance`
and all row/source keys have the exact common-port shapes in the frozen contract.

| ProfileRecord field | Meaning and source | Missingness |
| --- | --- | --- |
| `profile_key` | Caller's stable key for this supplied model record | Required; duplicate keys are rejected |
| `database_identity` | Explicit model database membership, version, release, scope, preparation type and source | Unknown optional fields remain null; unestablished/conflicting membership cannot qualify a model link |
| `model_identifier` | Explicit namespace, identifier value and optional version | No inferred alias; literal native id/accession or validated native `gnl\|namespace\|value`/numeric accession-version spelling is required |
| `pssm_key`, `master_sequence_ref` | Supplied PSSM/master references, retained without constructing biological sequences | Nullable; this function does not decode PSSMs or acquire masters |
| `num_columns` | Actual number of model positions from the supplied model record; positive integer | Null disables the model-coverage denominator |
| `specific_bits_threshold`, `reporting_bits_threshold` | Optional real model thresholds in bits, supplied from that model's record | No default; zero is a measured threshold, not missing |
| `source`, `native_record` | Source-qualified complete supplied record including unknown fields | Required; provenance pointers are not evidence of arbitrary identifier aliases |

The optional native Scoremat threshold names are `params.bitScoreThresh` and
`params.bitScoreReportingThresh`. This workload accepts already extracted typed
ProfileRecords; workload306 owns any input decoding. It neither asserts these
fields exist in every native RPS output nor claims a native specific-hit category.

`ProfileBinding` names the full original SearchKey, hit and description ordinal,
profile key, exact native `{id,accession,title,taxid}` including absent nulls, and
relationship provenance. Same-index bindings in another archive member or
iteration cannot link. Multiple plausible models for a hit remain ambiguous.

`FunctionBinding` stores explicit profile/function/evidence/provenance links.
`ModelRelation` stores only supplied identical-model, family, superfamily, or
overlapping-training-set relationships. Titles, taxa and similar scores produce
neither relation. `target_context` is retained but unused by this version.

## Source and geometry qualification

The calculator reuses `resolve_blast_program_context`, retaining the real selected
executable. Its exact resolved geometry is `blastp` for RPS/DELTA and `blastx`
for RPSTBLASTN. A native token omitted by table6 does not contradict an exact
selected invocation that the existing resolver resolves. A collector context
whose geometry is null or contradictory cannot be repaired by an override.

Normal RPS/RPSTBLASTN require database mode, sequence input, profile reference,
explicit domain stage/provenance and RPS preparation. DELTA keeps its
invocation-wide sequence reference and requires a separately established exact
domain section, database identity, source and DELTA preparation. No stage is
inferred from position, round number, title, or `-show_domain_hits`.

Supplied source objects/text are rechecked with the existing collector readers.
Canonical original search pointers, iteration labels, complete row maps, native
projections and query bindings must agree. JSON uses original object pointers;
tables retain `/sections/N` plus original line and data-row ordinals. Table
rechecks consume only the explicit `normalized.native.table_layout`
`{format,declared_fields,delimiter}` from workload307. Missing old layouts remain
unavailable. There is no delimiter enumeration or format inference.

Archive member ordinal/digest is checked against
`normalized.native.archive_member`, independently of the container digest.
Missing digest is unverifiable; differing known digests are a conflict. Actual
artifact-reference custody remains an acquisition/producer responsibility.

`QueryBinding` must equal the original bound collection operand and agree in
role, molecule, axis kind, units and full length. Native reported length must be
compatible with full length or the explicit selected span when reported. The
collector's native identifier/title binding is rechecked. No range offset is
ever added to native coordinates. Null/unmatched bindings disable full/selected
denominators while keeping source-level native geometry. A missing sequence
digest flags unknown biological identity but does not erase otherwise established
full/selected coordinate measurements. No biological sequence is published here.

## Numerical output cells

The exact `blast_profile_components_v1` outer fields are `schema`, `search_key`,
`status`, `hsps`, `models`, `function_components`, `dependence`, `taxonomy`, `issues`.
All arithmetic is deterministic and has no manufactured uncertainty interval.
Native statistical quantities retain their original meaning and precision.

| Cell | Exact measurement/formula, population and units | Unavailable/conflicting inputs |
| --- | --- | --- |
| HSP `native_hsp` | Entire original JSON HSP object; for a table, the original row including exact lexical values and fields | Malformed nonobject rows remain in the sheet and collector issues, not fabricated HSP objects |
| HSP `native_components` | Complete existing `alignment_components` output from normalized HSP fields, resolved geometry and legitimate source/full bounds | Native scores/counts survive missing traceback or incompatible coordinates; component-specific issues remain |
| Native `bit_score`, `score`, `evalue` | Individual native HSP values, no averaging/summing across HSPs/models | Missing or invalid values remain null; native underflowed E-value zero stays zero |
| Alignment/paired/identical/gap counts | Shared traceback counts where strings exist; reported counts remain separately visible; paired reported columns can be `align_len - gaps` when valid | No gapped string length is substituted for paired coverage; inconsistent counts remain qualified |
| `representative_symbol_identity` | Identical displayed pairs / paired displayed columns; fraction with explicit numerator/denominator | Native reported counts can supply it when traceback is absent but the counts are valid; no denominator means null. Unknown profile stage disables this profile-specific interpretation |
| `reported_query_length` | Native `query_len`/`qlen`, in original aa or nt | Null when unreported/invalid |
| `full_query_length` | Exact source-qualified QueryBinding full length, in original aa or nt | Null for unbound/conflicting query. A missing digest alone does not make an established length missing |
| `selected_query_interval` | Explicit original zero-based half-open selected interval | Null if not supplied or query binding unavailable; no inferred whole-sequence selection |
| `reported_model_length` / model `reported_model_lengths` | Native hit `len`/`slen`, and distinct retained lengths of established HSP links | Kept separate from supplied model columns; any missing/disagreeing native length disables the model denominator |
| `model_matches.model_columns` | Supplied model `num_columns` for an established model link | Null for unavailable/ambiguous/incompatible links or absent columns |
| `*_bits_threshold` | Actual supplied candidate-model threshold, in bits | Missing stays null; conflicting same-model records cannot yield a unique threshold. Unqualified release does not erase the supplied threshold |
| `specific_bits_margin`, `reporting_bits_margin` | Native HSP bit score minus the respective actual threshold, in bits | Requires an available exact model link and the same explicit nonnull release; missing/conflicting score, threshold, link or release gives null. Version does not invent release |
| `observed_paired_query_intervals` | Union of actual paired query intervals for this established model, zero-based half-open original aa/nt | Only observed subsets remain when some geometry is missing; unestablished model links are not merged |
| `observed_paired_model_intervals` | Union of actual paired model intervals for this established model, zero-based half-open model positions | Same missingness rule; representative residues are not biological reference sequences |
| `paired_query_units`, `paired_model_positions` | Sum of interval-union lengths, counting overlapping positions once within this model | Null when no geometry is available; an actually observed empty paired set gives zero |
| `query_coverage` | Paired query union units / source-qualified full query length | Numerator/denominator retained separately; value null when geometry incomplete or denominator unavailable |
| `selected_query_coverage` | Length of paired query union intersected with the explicit selected interval / selected span | No selected interval means null; incomplete geometry keeps observed numerator and null value |
| `model_coverage` | Paired model-position union / source-bound `num_columns` | Denominator only when all native reported lengths agree; no complete coverage value from incomplete geometry |
| `paired_query_overlap_units` | Intersection length of two distinct established model query unions in the same original search, in aa/nt | No overlap penalty or independence multiplier; incomplete unions carry `complete_for_reported_hsps=false` |

`geometry_complete` means complete geometry for the model's established reported
HSPs, not successful/exhaustive native execution. Malformed HSPs in a bound hit,
unassignable malformed hits/table rows, invalid selected bounds, and unresolved
associations prevent a partial union being labeled complete. Native execution
completion remains separate in the retained search and enclosing issues/status.

Existing component field names such as `reference_paired_coverage` use the
alignment-symbol coordinate meaning under enclosing `reference_axis_kind =
profile_model`; they never convert the model into a biological reference. Native
JSON uses `blast_json2`, tables use `directional`; translated reverse triplets
and frame arithmetic come entirely from the shared alignment implementation.

`function_components` groups only supplied explicit function bindings, with
profile keys, established HSP row keys and original binding indices. It has no
conditional sequence-population weights or annotation probability. The original
provenance stays in the sheet. Missing function assignments remain absent.

`dependence.relations` retains the supplied relations verbatim. Distinct models
remain separate even when a supplied relation says same family/superfamily or
identical model. This version does not combine models into one biological entity.

`taxonomy` is exactly unavailable for population `model_training_sequences`,
with null components and reason `model_training_membership_not_supplied`.
A displayed representative's taxid never becomes model-training taxonomy.

## Failures and statuses

Caller shape/nonfinite-data defects raise specific `blast_profile_*` ValueErrors.
Scientific source conflicts/missingness become the exact shared Issue shape.
The closed module-level `ISSUE_CODES` enumerates diagnostic categories; wrapped
collector/alignment issues retain the complete original issue under
`details.native_issue` and original source location. Native malformed-row
ordinals are never compacted into component indices.

`complete` means qualified supplied calculations without identified missingness;
`partial` keeps surviving measurements and explicit issues. `no_reported_hits`
requires an actual explicit empty native hit report plus successful complete
producer facts. Failed/missing reports and unknown profile stage are unavailable;
contradictory source/mode inputs are incompatible. These categories are not
numerical confidence grades or scientific completion judgments.

No production consumer is installed by this workload. Future DELTA iteration
code can consume these exact v1 fields. A real child-owned native result producer,
authenticated acquisition, profile membership/release inputs, typed episode
projection and return path remain separate unverified work.
