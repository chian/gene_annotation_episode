# Actual STEERING exposure from completed Workflow009

The existing negative assertion in test_selected_three_slots_and_child_owned_http_route must remain. Final pytest bodies did not run because the earlier source-set guard failed; this read-only audit checks their actual completed presentation files and finds a concrete failure.

Producing chain in gene_annotation_episode/scientific_process_prompt.py:

- render_scientific_process_prompt → _steering.
- _received_records collects references from state.child_reports via _references, looks up the matching row in state.working_state.sources, and passes it through _record.
- _record drops _RECORD_TRACKING keys, but retains id, accession, artifact_ref, request_ref, provider and version.
- _steering sends those records to _values → _rows, producing the “Current interpretations and their received evidence” metadata dump.
- Independently, _steering sends complete state.child_reports to _values. That repeats the same source ID in the references array and in each numeric/detail/missing row's source_ref.

The actual saved context paths are enumerated in PROMPT_EXPOSURE_025.json. They include context.working_state.sources[20].id and context.child_reports[1].numbers[0].source_ref through numbers[4].source_ref. The six actual files scientific-presentation-3.txt through -8.txt contain the final opaque result source ID; the first has nine occurrences. Raw artifact/request digests appear beside it.

A bounded failing excerpt from scientific-presentation-3.txt (STEERING, around line741):

```text
| [6].accession | artifact_bundle_d7f15b066c802156ff7364685af5b0be58a507f8d2122faf95f22a290a7ec575 |
| [6].artifact_ref | artifact_a846d86d8b43a7cd92d57874baa941a799d42c2893ccefeb531951c6893b6502 |
| [6].id | source_88af3848dbab8e698365e66e |
| [6].provider | episode.bvbrc_appservice_bundle_data |
| [6].request_ref | artifact_af0448974069fd6fd5d228627ad88157d72f10bb326e295b2c94de3727137492 |
| [6].retrieved_at | 2026-10-25T09:22:43.497961+00:00 |
| [6].text_ref | null |
| [6].uri | null |
| [6].version | bvbrc_appservice_bundle_data_v1 |

```

Useful decision information in this example is the originally requested member count4, cell count28, gap fraction6/28, entropy0.9182958340544896bits, native score92, their recorded units/origins/population meanings, the selected position details and actual unresolved qualifications. The child completion status and whether the originally required consensus output was acquired matter. The opaque source-envelope id/accession/artifact/request hashes and repeated whole return envelope add tracking information. Original typed forms, stored references, authentication and action operands must remain intact outside this text presentation change.

No replacement scientific interpretation, extra model call, controller change or altered numeric form is proposed. Root owns the production rendering correction and its consumer verification. This worker has not changed it.
