# N native-reader and numerical-sheet handoff

N's implementation is confined to the five assigned new production files, two
assigned test files, dedicated fixture directory, and this evidence directory.
The production root, sibling code, package registration, fixed accounting,
episode/runtime code, prompts, literature work and annotation credit are untouched.
This is not a whole-tool completion or service-deployment claim.

## Delivered ports

- `bvbrc_comparative_systems_handoff_contracts.py`: `schema`, `validate_shape`,
  `canonical_sha256`; detached finite JSON and exact integer fields. No N/D/C/P/I
  implementation imports. The packaged JSON is byte-identical to the reviewed
  115-definition asset, SHA256
  `b1310c2f3c7a464191f8c9eb5918d516ed2e6dd13f49bec024a2e9a8bde159f8`.
- `bvbrc_comparative_systems_native.py`:
  `parse_comparative_systems_document(content, *, document, format_profile,
  producer_evidence)` for all six declared profiles. Bytes/format identity,
  strict JSON, duplicate keys, embedded manual/pandas TSV, raw field lexemes,
  malformed row retention, exact-width hex consistency, unknown producer and
  witnessed source-defect qualifications are implemented.
- `bvbrc_comparative_systems_sheet.py`:
  `build_comparative_systems_sheet(documents, *, analysis_id, original_request,
  producer_evidence, document_selection, population_assignments,
  supplied_record_sets, reference_memberships)`. It retains every selected
  document and genes/raw association occurrence, native numerical fields,
  separate PLFam/PGFam rows, explicit assigned populations, supplied snapshots,
  duplicates, hierarchy/ID conflicts, categories, overview counts and malformed
  variant rows. It imports no D/C/P/I implementation and makes no acquisition.
- `bvbrc_comparative_systems_sheet_contracts.py`:
  `validate_native_document`, `validate_sheet`; detached closed shapes and saved
  field/reference/population relationships. These do not parse bytes, rebuild
  sheets, repeat Data extraction, rerun formulas or authenticate host custody.

## Actual verification

The final command used the root `.venv/bin/python`,
`PYTHONDONTWRITEBYTECODE=1`, candidate `PYTHONPATH`, both N test modules and an
external pytest cache. It exited 0 with **86 passed in 5.46 seconds**.
`pytest_005.log` is the terminal output; exact commands and earlier passing
results are in `COMMANDS_AND_RESULTS_001.json`. Ordinary observation timeouts
were resumed through their original handles; no live test was stopped or rerun
because an observation timed out.

The tests exercise actual exported functions, including independent expected
numbers and source locations. Coverage maps to all ten N cases in 185:

| N case | Actual checks |
| --- | --- |
| 1 | All six profiles; all three JSON documents and every embedded table; wrong profile/array rejection; dynamic arbitrary metadata preservation. |
| 2 | Manual tabs versus quoted/multiline pandas fields; duplicate keys/headers; invalid Unicode and unpaired surrogate; malformed JSON/CSV; blank/header-only tables; invalid widths with later valid rows. |
| 3 | Executed-source witness versus unknown or source-examined identity; source-loss code never inferred from the profile. |
| 4 | Exact original direct IDs, unknown groups/executed IDs, explicit assignment IDs and incompatible assignments, sibling failures, supplied-population collisions. |
| 5 | Native count/token/occurrence meanings; blank IDs and exact `292462.10`; zero, missing, invalid and partial populations. |
| 6 | Separate pathway/EC/raw/genes rows; repeated and conflicting record IDs; explicit raw-to-joined correspondence with unmatched rows and many-to-many multiplicity. |
| 7 | Literal superclass casing; hierarchical key/ID conflict; contradictory categories retained; two malformed matrix headers and extra column; nullable matrix subsystem ID; imputed inactive remains imputed. |
| 8 | Source-executed hex 255/256; invalid symbols, length, sums and membership; reversed order and duplicate display names/IDs; independent aggregate/list measurements survive overflow. |
| 9 | Additional unchanged-producer witness with repeated rRNA feature, blank-AA omission, short-row omission, absent family descriptions and no-family accepted genome; negative/nonfinite/invalid numeric lexemes; no invented feature IDs or individual lengths. |
| 10 | Native overview leaf/parent counts retain their source meaning, with no global-unique reinterpretation; release stays null/qualified. |

Saved-value tests reject changed numerical values, units, source fields,
entities, populations and removed qualifications without invoking the parser.
Pure parsing/building tests forbid network/process operations. The additional
source execution used the unchanged pinned source with every authentication and
network route blocked; `OCCURRENCE_WITNESS_001.json` records zero attempted calls.

## Filled actual outputs

`write_actual_sheets_001.py` runs the delivered reader and builder over the
retained labelled sources and saves four complete sheets. The aggregate
`FILLED_ACTUAL_NUMERICAL_EXAMPLES_001.json` includes their full numerical rows,
population descriptors and hashes.

| Actual source-executed synthetic sheet | Checkable values |
| --- | --- |
| `pathway_subsystem_sheet_actual.json` | Native pathway: 2 genomes, 2 EC tokens, 4 feature tokens, 3 genome–EC pairs, 75 percent, feature density 1. Native subsystem: 2 roles, 4 features, 75 percent, reported any-record fraction 1. Retained raw table has 5 occurrences and 2 distinct EC/role IDs. The separately supplied later snapshot remains 3 genomes, 3 EC IDs and 4 pairs; it never overwrites native 75 percent. |
| `families_sheet_actual.json` | Each PL/PG namespace: 3 accepted occurrences, 2 positive genomes, native represented set 3; counts 2/1/0; lengths min 100/max 300/mean 200/population SD 81.64965809277261 amino acids. Native 00 has unknown-completeness presence state. |
| `hex_256_sheet_actual.json` | Token `10001`, aggregate 257, 2 positive genomes; both per-genome cells incompatible/null. |
| `occurrence_omissions_sheet_actual.json` | Three accepted family occurrences from two repeated rRNA rows plus one CDS row; mean 166.66666666666666; count order 2/1/0 at exact IDs `292462.10`, `2.1`, `3.1`. The short and blank-AA rows were omitted by the producer; the no-family accepted genome remains in the represented set. |

The variant witness preserves active 3/likely 2 occurrence counts, fixed
inactive-placeholder 0 and imputed-missing 0, nine header fields and ten row
fields. Its `subsystem_id` remains null. Native any-record fraction 1 does not
become an activity probability; category-set calculations remain C's job.

## Source/contract clarifications

`SOURCE_LITERAL_CORRECTIONS_001.md` records exact source locations for the
summary's uppercase `SYNTHETIC` versus the raw table's lowercase `synthetic`, and
the variant matrix's absent subsystem ID. Frozen 185 files are not changed.

For selected-component populations, `raw_occurrence_count` counts the selected
association occurrences carrying that component, while
`distinct_valid_member_count` counts distinct valid component IDs. The witness
therefore stores 5 and 2, respectively; the initial illustrative example used 2
for both. No source duplicate is removed from the sheet.

A native represented population is its explicit returned set. Original genomes
outside that set remain in the separately retained original/executed population;
they are not reported as missing members of the named returned set. A returned
ID outside an explicitly evidenced executed set is incompatible. Unknown group
expansion does not invent an executed set.

`join_results` describes correspondence between explicitly selected retained
raw and joined tables, using their declared keys. It does not reconstruct the
unretained original feature-side table or claim its original cardinality.
Every joined genes row remains available to C even when no separate genes
authoritative view was selected. No variant cross-document ID join is guessed.

## Exact unfinished consumers and evidence

1. D supplies production-extracted `SuppliedRecordSetsV1` from exact qualified
   Data bytes/selection. N accepts those shared shapes and preserves their
   records/populations; the filled supplied inputs here are frozen synthetic
   examples, not live or host-admitted Data publications.
2. C consumes N's saved sheets through
   `calculate_comparative_systems_components`. C separately verified 27 expected
   quantities against earlier actual N outputs. Final-byte consumption and the
   quantity-specific handling of repeated joined source IDs with differing
   feature-side metadata are C's independent verification responsibility.
3. P must call the explicit parse/build ports from `consume_bundle`, resolve
   requirement/exact-artifact selection and producer mappings, invoke D/C only
   for selected dependencies, project the frozen requested fields, and include
   all transitive code/assets in its implementation pin.
4. I must authenticate original task/artifacts, qualified producer and Data
   bindings; bind the actual scientific selection to the API child; connect
   `AppServicePublications._grade` and original stored results; and implement
   the seven finite own/received return families with existing admission.
5. Root owns JSON package-data registration, integrated verification, production
   application and fixed-row accounting.
6. A live ComparativeSystems result, deployed producer/dependency/reference
   versions, real Data access and full typed episode communication remain
   unverified. N has made no service request or scientific execution claim.

The authoritative attachment was read verbatim before work and its objective
and entire 16-principle block were reread after native examination and at handoff.
The agreed numerical/interfaces and additive 002/003 were reread before closing
N. The pinned producer, actual BLAST pairwise grader, current C consumer paths
and relevant design/status instructions were inspected. No skill or external
workflow engine was added.
