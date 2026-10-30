# A105 insert boundary — proposal for review

The accepted meaning is preserved: “A105 is experimental molecular activity: what substrate was converted into what product, what was transported, or what bound—including measurements from a close homolog.”

The example fills gene identity. The actual parent commission supplies the candidate; no function or finding was invented.

| Information required by the insert | Decision it informs |
| --- | --- |
| Assayed subject and preparation | Whether the measurement concerns ybhP or requires transfer |
| Molecular endpoint | Whether the experiment measures the proposed conversion, transport or binding |
| Native quantities, units, controls and conditions | Observed outcome and meaningful comparisons |
| Source experiment/dataset | Traceability and recognition of repeated representations |
| Homolog correspondence and limits | How the measured property bears on ybhP |
| Negative results, uncertainty and untested conditions | What the candidate annotation still leaves unresolved |

This is the evidence-axis contribution to recurring TASK. Thought-pattern instructions, tool information, parent constraints and typed return form remain separate inputs. Received findings belong in STEERING. No scoring sheet, numeric rules, credit formula or itinerary appears here.

Inspected leak paths:

- `ScientificProcessEpisodes.decision_context` passes measurement/criterion metadata and `axis_judgment_contract` into context.
- `ScientificProcessLibrary.entry` returns the entire entry, including `scoring_rubric`; runtime’s handler retains it.
- Runtime passes context to `_SessionConnection.complete`, which serializes it using `json.dumps`. `model_snapshot`/`state_frame` retain these fields in the exchange path.

Inspected instructions, mother/library, runtime/provider and template proposal. No production edits, tests, model/network calls or jobs.
