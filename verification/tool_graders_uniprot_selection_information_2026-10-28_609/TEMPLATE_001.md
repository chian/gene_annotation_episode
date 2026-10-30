UniProtKB return choices for a results child

This reply describes the information you can request from the child's assigned
UniProtKB record or search page. It contains no acquired UniProt findings.

In your closed return form, choose one top-level field name. Give that field
`$ref: episode-fact:uniprot_selected_returns` and `x-uniprot-selection` containing
`version: uniprot_return_selection_v1` and your explicit `pages` list. The host
expands the return type internally. An empty `pages` list requests no UniProt
facts or materials. No fields or grants are inserted for you.

For this results child, use `publication: {"mode":"assigned_page"}`. It covers
the child's actual acquisitions of its assigned request and selected page,
including separate retained acquisitions if that same request was tried more
than once. It does not choose a new query, fetch another page, retry, or select a
preferred acquisition. Each page clause requires `publication`, `page_fields`,
`records`, and the boolean `grant_source`. Each record clause requires `record`,
`fields`, and the boolean `grant_sequence_artifact`.

| Choice | Exact selection and meaning |
| --- | --- |
| Records whose positions are unknown | `record: {"mode":"all_native_records"}` selects every original row on the assigned page. Malformed or unbound rows remain qualified unavailable rows. It selects only the fields you list. |
| Known primary accession | `record: {"mode":"primary_accession","accession":"P0AAW1"}` selects every row with that exact native primary accession. It does not match secondary accessions or collapse duplicates. Use your actual chosen accession. |
| Known row position | `record: {"mode":"ordinal","ordinal":2}` selects original zero-based row 2. Positions are not renumbered around malformed rows. Use this only when the position is known. |
| Page metadata | `page_integer` with `field: total_results` requests the recorded query total. `page_token` permits `release`, `release_date`, `next_cursor`, or `next_url`. `page_text` permits those four fields or `effective_query`, with an explicit character window. Missing page metadata stays unknown. A selected next cursor or URL does not fetch the next page. |
| Integer record values | `integer` with `field` equal to `taxon_id`, `entry_version`, `sequence_version`, `reported_sequence_length`, or `observed_sequence_length`. Taxon ID is an identifier; versions are version numbers; lengths are in amino acids. Reported length is native metadata; observed length is the published length derived from the stored sequence. |
| Exact record tokens | `token` permits `primary_accession`, `secondary_accession`, `uniprot_id`, `sequence_md5`, or `sequence_crc64`. Supply `array_ordinal` as the original zero-based index for a secondary accession and `null` for the other token fields. |
| Text | `text` requires `field`, an exact record-relative JSON `pointer`, `offset`, and `limit`. For example, `protein_name` at `/proteinDescription/recommendedName/fullName/value` addresses that name alone. Offset is zero-based Unicode code points; limit is a positive number of code points. The reply preserves total text length and omitted extents. It does not return the surrounding object. |
| EC assignment | `ec_assignment` requires the exact record-relative pointer ending in `/ecNumbers/N/value` within a recommended, alternative, or submission name, including a `contains` or `includes` component. The reply preserves the name owner and entry-versus-component scope. An EC annotation is not a target experiment. |
| GO or other cross-references | `cross_reference` takes `selection: {"mode":"database","database":"GO"}` for every exact GO member, or `mode: all`, or `mode: ordinal` with the known original index. Supply `include_evidence` explicitly and a `properties` list. Each property request has an exact `key` and `window: {"offset":0,"limit":80}` using your chosen bounds. `properties: []` requests none. `GoEvidenceType` is native property text, not an ECO conversion or a grade. |
| Feature locations | `feature_location` takes a known original ordinal, `mode: all`, or `selection: {"mode":"entry_interval_overlap","start":9,"end":20,"coordinates":"zero_based_half_open","unit":"aa"}`. The example interval is entry residues 10 through 20. Supply `include_evidence`, `type_window`, and `description_window` explicitly; each window is `null` when unrequested or an offset/limit pair. |
| Evidence associations | `evidence` takes `selection` with `mode: owner_ordinal`, a record-relative `owner_pointer` and local zero-based `ordinal`; `mode: all_at_owner` with `owner_pointer`; or `mode: all_record`. Owner-local ordinal zero at two different owners denotes different associations. ECO, source and source identifier remain associated with that owner. |
| Sequence letters | `sequence_window` requires `start` and `end`, with `0 <= start < end`, in zero-based half-open amino-acid coordinates. `[9,19)` requests ten residues, native positions 10 through 19. The interval must fit the actual entry sequence; an unavailable or out-of-range sequence is not padded or clipped. |

Text field names are `protein_name`, `gene_name`, `entry_type`,
`protein_existence`, `entry_date`, `taxon_name`, `taxon_synonym`,
`taxon_lineage_name`, `feature_type`, `feature_description`, `xref_property_key`,
`xref_property_value`, `comment_text`, and `native_text`. Each named field must
use its matching native branch. `native_text` addresses an explicit string leaf
in the selected record. Sequence letters at `/sequence/value` require
`sequence_window`. Indexed text and EC pointers require known original positions;
they do not discover an unknown member. GO membership, feature overlap and
explicit all-member selections do not require those positions.

Exact feature intervals match overlap when the feature starts before the
requested end and ends after the requested start. Exact disjoint features and
features explicitly on another sequence are excluded. Fuzzy, invalid, missing
or unresolved locations remain indeterminate. Native feature coordinates stay
one-based inclusive; an exact derived interval uses zero-based half-open
coordinates. An interval past entry length is unavailable, not shortened.
For a database criterion, an invalid or missing database value is indeterminate,
not evidence of absence. `include_evidence: true` returns evidence owned by the
selected feature or cross-reference and its descendants, preserving each owner;
`false` leaves that evidence unrequested. There is no best-member rule or hidden
member limit.

| Material choice | Meaning |
| --- | --- |
| `grant_source: true` | Request the whole native source for the selected page. This is broader material access than selected fields or windows. |
| `grant_sequence_artifact: true` | Request the selected record's full stored sequence artifact. It does not grant its reference record or whole native source. |
| Both grants `false` | Request only the listed facts and windows. Selected text or sequence windows do not grant surrounding material. |

Keep known-empty, absent, null, invalid, unreceived and unavailable distinct.
Partial valid fields survive failures in sibling fields. Exact duplicate page,
record and field selectors are invalid. Different clauses may overlap; that
does not add evidence or credit. UniProt annotations and evidence associations
remain source claims with their qualifiers, not function-confidence scores.

Use this information to finish the same pending decision and construct your
chosen typed response. The lookup has not completed an action or changed yield.
