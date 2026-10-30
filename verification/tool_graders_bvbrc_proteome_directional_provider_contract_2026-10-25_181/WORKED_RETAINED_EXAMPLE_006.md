# Retained native example through the proposed provider and return

The numerical data here are real retained public native BLASTP text, inspected
alongside179's filled numerical sheet. This is a design trace for the proposed
D/F path, not an executed BV-BRC GenomeComparison job or an authenticated host
publication. Logical labels in the proposed invocation are caller labels only.
Host source IDs below are variables for actual future records; none is fabricated.

## Retained bytes and independently visible measurements

Native file:
`tests/fixtures/bvbrc_proteome_directional/biopython_text_2221L_blastp_001.txt`.
It contains12,858 bytes, SHA256
`e8bcff01bf827d936c36f00e4bbb73f2b5b1dd99b4d37af4cb9a6b0de44e25f8`.
The original retained acquisition record is170's
`ACQUISITION_RECEIPTS_002.json`: public Biopython blob
`ed2eac2ed2ca6e325d2d540a08ea279043427305`, retrieved
2026-10-25T15:09:38.759096+00:00 with HTTP200. The source is
https://github.com/biopython/biopython/blob/biopython-164/Tests/Blast/text_2221L_blastp_001.txt .
This public fixture is native-format evidence, not evidence of the deployed
GenomeComparison producer or the user's executed input roster.

The already populated179 artifact is
`evidence_a/native_2221_scoring_sheet_002.json`,5,197,091 bytes, SHA256
`b6af269c11bea3a24f018c603ab62c756f0c031b978b55674348080d56812cde`.
Its exact observed-sheet hash is
`d20f417b4364ea42b17dfb2740e81fcea6431a63533f77a1267f1889acbc2926`.
Its source fields are explicitly local fixture labels; they cannot be copied
into real host custody. With actual host ContentBindings, the observation hash
will reflect those actual identities, while the numerical answers remain equal.

The report has3 displayed queries,30 description rows,3 subject occurrences,
4 HSPs and23 traceback blocks. Query ordinal1 and its subject ordinal0 both
have reported length600. Their2 HSPs have9 traceback blocks in total:

| Native observation | HSP0 | HSP1 |
|---|---:|---:|
| Reported identities / alignment columns |353/414|115/115|
| Reported positives / reported denominator |353/414|115/115|
| Reported Gaps |missing|missing|
| Bit score |684|258|
| Raw score |1765|658|
| Native expectation spelling |`0.0`|`2e-66`|
| Native expectation group count |missing|missing|
| Displayed query and subject coordinates, inclusive |1..414|486..600|
| Traceback block count |7|2|

The HSP1 expectation's actual byte span is[7535,7540); those bytes are `2e-66`.
The query length600 is at[4186,4189). The reader keeps these locations, native
spellings and the original source SHA; the projection does not reparse the text.

The occupied/paired union is[0,414) plus[485,600), cardinality529. Its coverage
is exactly529/600, rendered at18 half-even places as0.881666666666666667.
The omitted71 query positions are not declared gaps. There are529 unique
coordinate pairs,0 repeated representations,468 identical symbol pairs,
468 resolved amino-acid pairs,468 resolved identical pairs,0 resolved
substitutions,61 unresolved pairs and0 stop-containing pairs. Thus symbol
identity is468/529=0.884688090737240076; resolved-only identity is468/468=1,
and must accompany the61 unresolved pairs. The graph state is
compatible_displayed_partial_map with9 included blocks,0 excluded and0 HSPs
without traceback. Native disjoint-HSP identity/count totals are468 and529.
Missing reported Gaps keep their native-count derived quantities unavailable.

These are displayed-report measurements. Database expectation is retained as a
native statistic, not used to select a corresponding HSP or infer gene function.
The report's database/footer populations are not substituted for displayed
subjects. Its four aliases in the first subject defline do not create four
subject occurrences. No function, taxon, executed-sequence join or producer
retention claim is inferred from this fixture.

## Concrete frozen invocation before acquisition

The main worked request asks for one exact native expectation. These are proposed
caller-owned values; they can be frozen before the member's source/hash exists.
All fields are supplied, with no inferred numerical defaults:

```json
{
  "version": "bvbrc_proteome_bundle_parameters_v2",
  "analysis_id": "retained_example",
  "native_documents": [],
  "primary_document_id": null,
  "supplied_data_evidence": null,
  "calculation_parameters": null,
  "directional_documents": [{
    "document_id": "retained_2221",
    "requirement_id": "dir_report",
    "report_key": "retained_2221",
    "role": "proteome_directional_report",
    "declared_format": {
      "format": "ncbi_blastall_blastp_pairwise_text_v1",
      "version": "2.2.21",
      "mode": "protein_database_search_pairwise_display",
      "producer_source_ref": null,
      "transformation_evidence": []
    }
  }],
  "directional_calculation_parameters": {
    "version": "bvbrc_proteome_directional_parameters_v1",
    "formula_version": "displayed_blastp_correspondence_v1",
    "amino_acid_alphabet": "standard20",
    "ratio_decimal_places": 18,
    "rounding": "half_even"
  }
}
```

Call the proposed `requested_form_schema_v2` with exactly:

```json
{
  "positive_expect": {
    "kind": "directional_native_decimal",
    "scope": "hsp",
    "document_id": "retained_2221",
    "query_ordinal": 1,
    "subject_ordinal": 0,
    "hsp_ordinal": 1,
    "metric": "expect"
  }
}
```

Let P be the complete parameter object above, F the generated canonical form and
DF the exact declared_format above. The complete host ResultSelector is:

```text
{
 version:"bvbrc_appservice_result_selector_v1",
 endpoint:"requested_projection",
 requirements:[{
   requirement_id:"dir_report", role:"proteome_directional_report",
   required:true, declared_format:DF,
   producer_rule_evidence:null, exact_object:null
 }],
 adapter:{adapter_id:"bvbrc_proteome",adapter_version:"2",parameters:P},
 requested_schema:F,
 supplied_metadata:[], supplied_contents:[], supplied_capabilities:[]
}
```

The actual caller configuration separately binds the actual computed v2 code
digest. It cannot supply an invented future implementation hash. D's selector
validator checks dir_report's role and entire format equality now. The results
episode later selects the real Workspace download operation and explicitly binds
its `requirement_ids:["dir_report"]`. The actual operation's receipt/member must
carry that membership. A filename, folder, matching hash or declaration alone
does not establish it. If the episode selects two matching actual members,
the provider reports ambiguity instead of choosing one.

For the exact-selector variant, replace only requirement_id with the actual
already-possessed `source_ref` and `raw_artifact_ref` pair before freezing the
request. The variant cannot be constructed from unknown future IDs. It uses the
same role, format, report_key, numerical parameters and requested field.

## Concrete custody and storage chain

Use these symbols only for records created/authenticated by the actual host:

* `S_report`, `A_report`: selected download's real source/raw artifact references.
* `S_bundle`: actual artifact-bundle ContentBinding.source_ref, also the result
  reference in the publication and the outer typed return row.
* `S_sheet`, `S_components`: real ContentBinding.source_ref values created by
  `_put_content` after the pure provider has returned its exact dictionaries.
* `S_publication`: real immutable BundlePublication source. Its saved adapter
  result binds S_sheet and S_components; the outer row does not predict them.

The actual acquisition's source/task/receipt/origin and selected requirement
membership must authenticate S_report/A_report. The actual ContentBinding has
the native byte hash/count above, with its own real source/artifact fields.
For a complete retained object its observed transfer flags are true/yes; a real
partial acquisition instead retains its actual incomplete flags. Neither this
design nor the public fixture acquisition proves a BV-BRC task association.

D resolves exactly one directional selection at selection_index0 and stores
result_index0. The saved reader has report_key retained_2221 and source
S_report/A_report. A report_ordinal0 maps to that same reader occurrence.
`sheet.directional_results[0]` and
`sheet.directional_sheet_result.sheet.reader_results[0]` are exactly equal.
The numerical wrapper copies the observed directional sheet; its legacy sheet
is null and directional_operand_binding is unbound. C's exact components carry
the new actual observed hash and unchanged explicit parameters. ProviderComponents
binds the entire ProviderSheet hash and has legacy=null. C has already invoked
A's full component validation before returning; D does not repeat its geometry.

The pure provider produces the requested fact. The host stores its exact sheet
and components, immutable scientific_adapter_result, and publication. On return,
`AppServicePublications.read` authenticates the actual inputs/bundle/acquisition,
pin and content hashes. F checks saved relationships and copies the exact saved
fact into the parent's typed row. No native parser or calculator runs here.

## Fully specified requested numerical fact

The notation below is a complete value construction using the actual source
variable, not JSON purporting that symbolic text is a Store source.
`R(kind,p)` is the existing `encode_reference(kind,"retained_example",p)`;
it is used only by deterministic projection. `O` is
`/sheet/directional_sheet_result/sheet/reader_results/0`; `H` is
`O + /queries/1/subjects/0/hsps/1`. `document_id` is the frozen document token,
validated through the new document namespace. A native-cell fact has no numerical
parameter dependence: parameter_ref=null. Its native operands are the exact
selected cell and the explicitly exposed expectation-group cell. Other HSP
diagnostics, such as missing Gaps, are separately available issue facts; they do
not change this native expectation's availability or invent a reason for it.

```text
positive_expect = {
 availability:"available", quantity:"expect",
 context:{
   target:{document_id:"retained_2221",report_ordinal:0,
     query_ordinal:1,subject_ordinal:0,hsp_ordinal:1,block_ordinal:null,
     description_ordinal:null,database_header_ordinal:null,statistic_ordinal:null},
   native_source_ref:S_report,
   value_ref:R("field",H+"/expect"),
   parameter_ref:null,
   operand_refs:[R("source_field",H+"/expect"),
                 R("source_field",H+"/expect_group_count")],
   report_parse_state:"ok",body_complete:true,object_complete:"yes",
   declaration_state:"matching_version",operand_binding:"unbound",
   supports:[],mapping_state:"compatible_displayed_partial_map",
   qualification_refs:[],requirement_refs:[]
 },
 cell:{state:"present",value:{sign:0,digits:[2],exponent:-66}},
 unit:"expected_count",statistic_kind:null,
 expectation_display:"positive_reported_decimal",
 expect_group_count:{state:"missing",value:null}
}
```

For example the generated value_ref is literally
`bvbrc_proteome_field:retained_example/%2Fsheet%2Fdirectional_sheet_result%2Fsheet%2Freader_results%2F0%2Fqueries%2F1%2Fsubjects%2F0%2Fhsps%2F1%2Fexpect`.
It addresses the actual saved native cell, not arbitrary caller-supplied JSON.
The original saved cell retains native_text/value `2e-66`, byte span and SHA.
Canonical transport never turns this exact positive value into a float or0.

The final row is exactly:

```text
{
 source_ref:S_bundle,
 field:R("field","/facts/positive_expect"),
 value:positive_expect
}
```

The parent's closed form can select one required property `expectations` whose
schema is exactly
`proteome_fact_sources()["bvbrc_proteome_directional_native_decimals"]["report_schema"]`.
The top object is closed and requires expectations. Its value is the one-row
array above. Its ExactDecimal portion uses only closed objects, constrained
integer digits/sign and integer exponent, accepted by the existing real parent
validator. The original full fact semantics and exact saved equality are also
mandatory; a looser parent form cannot alter that row.

For this single available request, projection status is ok even though the full
numerical result has partial status from unrelated missing reported Gaps.
Actual required-artifact acquisition must still be complete for host practical
completion. No completion proof is claimed by this unexecuted design example.

## Additional exact selectors over this same retained sheet

The following compact table uses R/Q/S/H/B key shapes from002 and the same
document_id. Each is a separately selectable fact, not a mandatory request bundle.

| Exact selector suffix | Exact saved result and projection meaning |
|---|---|
| directional_count, report, metric=displayed_query_count |3 query_occurrence |
| directional_count, report, metric=displayed_hsp_count |4 hsp_occurrence |
| directional_count, subject, q1/s0, metric=displayed_block_count |9 block_occurrence |
| directional_coverage, query, q1, metric=any_displayed_subject_query_paired_union | count529 displayed_position; reported_length600; exact ratio529/600; denominator ref O+/queries/1/length; interval_count2 |
| directional_intervals, same query/metric, offset0,limit1 | items[{start:0,end:414}],total_count2,returned_count1,next_offset1 |
| directional_intervals, same query/metric, offset1,limit1 | items[{start:485,end:600}],total_count2,returned_count1,next_offsetnull |
| directional_fraction, subject, q1/s0, metric=compatible_unique_pair_symbol_identity |468/529, rendered0.884688090737240076, pair_population529/468/61/0 |
| directional_fraction, subject, q1/s0, metric=compatible_unique_pair_resolved_identity |468/468, rendered tuple0/[1]/0, same pair_population529/468/61/0 |
| directional_native_decimal, hsp, q1/s0/h0, metric=expect | tuple0/[0]/0; printed_zero_precision_unknown; original native0.0 retained; missing group count retained |
| directional_native_integer, hsp, q1/s0/h1, metric=gap_count | unavailable; cell missing/null, unitalignment_column; requested_value_unavailable requirement if requested |
| directional_count, hsp, q1/s0/h1, metric=query_gap_columns | observed traceback-derived0 alignment_column, available; separate from the missing native Gaps clause |
| directional_extremum, subject, q1/s0, metric=minimum_reported_hsp_expectation | selected original h0/expect, tied count1, excluded count0, printed-zero qualification; no conversion into certainty |
| directional_support, subject, q1/s0, collection=pair_geometry_support, member=included_blocks,offset0,limit9 | exactly h0/b0..6 and h1/b0..1, all with report0/q1/s0; no others |
| directional_state, report, metric=operand_binding | unbound, even with authenticated actual host byte custody |

Coverage's rendered tuple has sign0,digits
`[8,8,1,6,6,6,6,6,6,6,6,6,6,6,6,6,6,7]`, exponent-18.
Its original numerator529 and denominator600 remain unreduced. Coverage context
references the saved directional calculation parameters and the cell's exact
stored FieldRef inputs from179/002. Its support summary is basis trace_paired,
included9/excluded0/missing-trace0/complete true; its value_ref addresses the
actual saved PositionUnion. Compatible fractions use the graph's pair_geometry
support and preserve its mapping state. Those contexts do not infer input-roster
or protein-identity joins.

Adding the missing native gap request makes projection statuspartial, even if
all other selected fields remain available. The unchanged request_status selector
can name that field and returns state unavailable with its exact generated
requirement reference. The separate directional_requirements selector exposes
the generated code `proteome_directional_requested_value_unavailable`, required
input scientific_metadata, this document token and requested field reference.
Its actual deterministic requirement identity is created by projection and saved;
it is not falsely equated with the acquisition membership ID dir_report.

## What this example establishes and leaves open

Native bytes, preserved numerical answers, exact decimal/rational transport and
the full intended selection/storage/return mapping are concrete. Existing
closed-form engineering probes accepted the tuple representation. No new D/F
implementation, full parent form, host publication or custody trace has been
executed in181. Those are005's required implementation checks.
Producer retention, executed input occurrences, row-to-HSP lineage and a real
GenomeComparison service run remain unestablished. The plan preserves that
absence while allowing useful report-derived numerical facts to return.
