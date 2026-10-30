# Selected-witness repair feedback, prospective 030 proposal

This proposal uses synthetic witnesses only. No paper, private model history,
run024 pin/state, scientific score or stored historical failure is changed.

`ExperimentalContractError(code, field, *, detail=None)` retains its current
code, field, string and one-element `args`. An optional detached `detail` mapping
is carried by the existing invalid-operation feedback, only for an attached
`source_quote_mismatch`. No other failure receives new feedback fields.

Proposed exact detail keys:

| Key | Meaning |
| --- | --- |
| kind | Fixed `selected_source_span_observation` |
| source_ref | Actually authorized selected source |
| artifact_ref | Artifact returned for the selected representation |
| representation | Selected `original` or `text` |
| start, end | Original selected UTF8 byte offsets, end exclusive |
| actual_utf8_length | `end - start` of the strictly decoded selection |
| nominated_utf8_length | UTF8 length of the nominated quote, nullable if it cannot encode |
| first_mismatch_utf8_byte | Zero-based differing byte relative to start; common-prefix length for a length-only difference; nullable if nomination cannot encode |
| selected_span_text | Exact strict UTF8 decoding of the selected source bytes |

The detail is constructed only after existing source authorization, span bounds
and strict UTF8 decoding succeed. It contains no candidate replacement,
occurrence search, normalized string, fuzzy match, neighboring context or
scientific interpretation. The episode chooses any next repair action.

The existing factual renderer already includes all feedback through
`_source_result -> _values -> _safe -> _rows -> _table`. No renderer/TASK change
is proposed. Example existing receiving rows are
`feedback.detail.kind | selected_source_span_observation` and
`feedback.detail.selected_span_text | abc`. Table escaping changes presentation
only; the recorded detail retains the exact string.

## Read-only consumer and accounting trace

`_Sources.witness` calls the injected authorized `read_source`, validates the
artifact/content result, then bounds, strict UTF8 and equality. Its successful
return remains the original witness plus artifact identity. `_Sources` is shared
by assay, amount, binding, binding model, context, figure, partner, native rate,
ratio, reaction, structure and transport readers. All existing two-argument
exception construction and reraising remain valid.

Native rate repository `populate_native -> read_source -> _native_source` checks
receipt, scope and selected page ancestry before reading artifact bytes. C7
`_tool_arguments` checks catalog/schema/assigned-source ancestry before repository
execution. C7 catches the original exception and returns the ordinary invalid
outcome without source publication.

`DecisionSource.execute` records the actual invalid result with null credit;
`FeedbackEpisode` catches `ActionFailure` with no controller observation.
The next decision receives the saved outcome/feedback. Runtime replay reads the
existing `runtime_actions.result` before dispatch; older saved failures remain
their original payload, without retrospective enrichment. Closing numerical
facts and typed return validation use the ordinary saved source-rate projection.

## Verification design

ASCII and multibyte Unicode; internal byte differences and both directions of
length-only mismatch; original/text artifact identity; identical successful
witness return; invalid span/UTF8 and rejected access without selected content;
unchanged non-mismatch failure feedback; lone-surrogate nomination; existing
factual rendering; controlled selected invalid attempt followed by an explicitly
fixture-chosen exact repair, one successful population, typed child return,
actual action/observation counts and replay with forbidden dispatch.

Shared production edits remain withheld until the parent explicitly releases
030 ownership after 029 terminal stable checks and agrees the interface.

## Additive presentation finding

The existing table renderer removes CR and renders LF as `<br>`. The underlying
saved `selected_span_text` stays exact, but that displayed row alone does not
distinguish CR/LF. An additional proposed field `selected_span_text_json`, equal
to `json.dumps(actual, ensure_ascii=False)`, exposes a reversible JSON string
literal of the same selected span through the unchanged table. It makes tabs,
CR/LF and control characters visible without normalization. This field awaits
the parent's interface decision together with the original payload.

## Accepted interface addendum

The parent accepted the prospective interface, including the additional JSON
literal. Shared ownership is still unreleased. The literal will round-trip to
the exact selected text and visibly escape LF, CR, tab, control characters,
literal pipe (`\u007c`), and tag-looking angle brackets (`\u003c`, `\u003e`).
Unicode may be escaped as a representation; the exact raw text remains beside
it. `json.loads(selected_span_text_json) == selected_span_text` is required.
This avoids changes to Markdown-table rendering or TASK/STEERING templates.
