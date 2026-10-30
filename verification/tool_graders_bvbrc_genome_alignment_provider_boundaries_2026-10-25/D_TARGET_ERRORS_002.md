# Exact request-local native target errors

Additive clarification of `D_CONTRACT_001.md`, requested by root review. Only the following exact `str(ValueError)` values from the indicated public call may become a `RequestOutcome(state="incompatible", measurement=null)`. The caller must first validate the plan, retained data and constructed native argument shapes. Match complete strings, never prefixes, substrings or all `ValueError`s.

| Public call | Exact allowed error strings |
| --- | --- |
| `calculate_mauve_v4_segments` | `mauve_v4_selection_member_unknown`, `mauve_v4_selection_record_unknown`, `mauve_v4_selection_column_outside_record`, `mauve_v4_selection_population_incomplete` |
| `calculate_mauve_backbone_components` | `mauve_backbone_selection_member_unknown`, `mauve_backbone_selection_record_unknown`, `mauve_backbone_selection_population_incomplete` |
| `calculate_mauve_bbcols_components` | `mauve_bbcols_selection_record_unknown`, `mauve_bbcols_selection_population_incomplete` |
| `xmfa_alignment_components` | `xmfa_selection_member_unknown`, `xmfa_selection_block_outside_document`, `xmfa_selection_column_outside_block` |
| `xmfa_interval_coverage` | `xmfa_selection_member_unknown`, `xmfa_selection_block_outside_document`, `xmfa_selection_column_outside_block` |
| `xmfa_column_coordinates` | `xmfa_cell_block_outside_document`, `xmfa_cell_record_outside_block`, `xmfa_cell_column_outside_record` |
| `xmfa_source_positions` | `xmfa_query_member_unknown`, `xmfa_query_outside_source` |
| `bind_xmfa_sources` | none; it already returns data-dependent source failures in its typed result |

Unknown member/record/block errors map to provider diagnostic `bvbrc_genome_alignment_provider_selection_target_missing`; all other listed errors map to `bvbrc_genome_alignment_provider_selection_target_incompatible`. The diagnostic path is exactly `/calculation_plan/requests/<request_index>` and its evidence refs come only from that outcome's actual primary artifact/source. The associated requirement uses kind `parser_binding`, the selected slot's role and the same reason code. Keep the resolved attempted call, request ID, request index and document ID; subsequent requests still execute.

`selection_document_conflict` is deliberately absent: D itself inserts the resolved document ID, so that error is a provider/saved-binding defect and must propagate. Duplicate indices/pairs, malformed arguments/selections, invalid case policy/basis, bad source bindings, malformed C metadata, numeric-contract errors and every unlisted error also propagate. Missing symbol/denominator/interval witnesses are already ordinary typed native results and are not caught exceptions. BBCols lacks a complete member census, so there is deliberately no invented `mauve_bbcols_selection_member_unknown` check.

Saved validation distinguishes a retained incompatible **attempt** from calculated output. The attempted call remains shape-valid even when its target index/member is absent or outside bounds. Do not reject that entire saved sheet by imposing successful-call target bounds on the incompatible outcome; validate its identity, stored attempted parameters, finite cause and absence of measurement, then check applicable native target relationships structurally. Calculated outcomes require valid target references and complete correspondence to their actual native return. This preserves a failed request on replay without invoking a native calculator to rediscover its exception.

Observed source locations: `mauve_v4_calculators._selection`; `mauve_backbone_calculators._base` and `calculate_mauve_backbone_components`; `xmfa_calculators._selection`; `xmfa_coordinates.xmfa_column_coordinates` and `xmfa_source_positions`. Contract verification must exercise one case for every listed code and one unlisted code per function proving it is not swallowed. This table freezes behavior without changing any native module.
