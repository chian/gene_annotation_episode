# Root integration clarification and unfinished templates

Additive clarification after the first packet draft, 2026-10-27. These are
implementation boundaries only. No template acceptance or code is claimed.

Root owns common source-aware grouping. The selected placement is after
`view.model_inputs(...)` and before `DecisionSource.call` / `model_snapshot`.
Runtime still has the original `(report.as_record(),
report.contract.measurements['schema'])` pairs there. This avoids introducing
custody/contract metadata into method_loop's declared_inputs. The proposed pure
overlap `(form, schema)` selector can be consumed at that boundary, or root's
common grouping can provide its same requested-source information. There must
be only one owner of the shared context assembly. No selection resolver has
been approved or coded.

The following concrete template boundaries remain separate:

| Template | What is proposed here | What remains unfinished |
| --- | --- | --- |
| Results-child return received by the scientific parent | Three small exact requested-fact display proposals; parent retains its full scientific TASK | User feedback, source-aware grouping, provider/scientific rendering integration, exact descriptor selection handoff, final model-text and next-action verification |
| Scientific-child forwarded return received by root/another scientific parent | Same requested-value rendering boundary applied to that parent's actual admitted form, preserving its own TASK | Root text dispatch, forwarded schema/source mapping, no hidden-sheet grants, final rendered-text and valid next-action verification |
| Results episode's own TASK and STEERING | Separate text draft for review in DISPLAY_DRAFTS.md, with fixed selector/parameters and own outcomes | User feedback and dedicated native/saved results rendering; current generic TASK says bounded file/page reads even though this results catalog has only status/collect; provider currently falls through to JSON |
| Launch episode supplied-input presentation | Current exact request/receipt/path requirements and ownership traced | A separate concrete template and feedback: show selected sets, formats/reference declarations and fixed parent constraints; keep machine binding descriptors internal while preserving a usable child selection |
| Local resource child's supplied-input presentation | Existing frozen input inheritance and exact unchanged-request validation traced | A separate concrete template and feedback for its actual job/resource decision inputs and own outcomes. Delegation to PracticalResourceEpisodes alone proves no reviewed overlap-specific supplied-input text. No claim of a byte-window mismatch is made for this launch-child template. |

Closing the parent display contract does not close these other templates.
The overlap calculator, native execution, requested typed return authority and
controller behavior remain reused. Shared semantic input selection is a named
integration dependency; this packet does not install a generic resolver or
pretend display labels are callable operands.
