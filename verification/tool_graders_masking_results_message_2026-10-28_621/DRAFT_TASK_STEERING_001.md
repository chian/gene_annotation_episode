TASK

Acquire the DUST interval masks for the supplied nucleotide FASTA and return the parent’s selected measurements, checks and artifacts. This results episode owns obtaining those results and deciding what useful acquisition action to take next. The scientific parent decides what the returned preparation results mean for its investigation.

The assigned job is dustmasker in mask mode, with interval output and sequence-ID parsing disabled. Its recorded version is 1.0.0, from BLAST package 2.17.0. No override was selected for window, level or linker; their effective native defaults are not established by that omission. Keep the original job, supplied input, local resource and selected output fixed. The allocation is 20 GiB RAM and 4 GiB scratch, with no wall-time limit. Acquire through the supplied original handoff.

The parent selected every original record in the supplied FASTA, the sole original mask output, and the saved sheet and original calculations. Return exactly these fields through the existing typed form:

| Field | Requested content and meaning |
| --- | --- |
| quantities | For every original input record: input_length in nucleotides; masked_positions in nucleotides; and masked_fraction with its numerator, denominator, value and any missing-input reason. |
| artifacts | The selected original mask output, with its recorded completeness. |
| saved_data | The retained sheet and original calculations needed for later inspection or an explicitly commissioned recalculation. |
| checks | Relevant saved checks for the selected records and their common input/output relationships. |
| failures | Relevant recorded failures, preserving their stage, restricted reason and affected original record or material when known. |
| statistics | No WindowMasker fields or unit codes were selected for this DUST job; return the corresponding empty selection. |
| status | Fulfillment of this selected request: complete, partial, failed or unavailable; separately, the original native outcome and whether its output is complete. |
| completed | Whether the original requested acquisition and typed return have been validated as fulfilled. |

Choose one permitted action using the information already received. Consider what the action could resolve: uncertainty about the original attempt’s readiness, availability of the requested original data, or a specific reported acquisition problem. A handoff, a live process or an available filename alone does not establish acquired measurements. Use actual prior attempts and their qualifications to distinguish useful additional work from repeating an unchanged result.

| Result operation | What it does and when it can help |
| --- | --- |
| execution.results.status | Observe the exact handed-off attempt once, including available state, output and log information. It does not collect the requested measurements or artifacts. Use it when that observation could inform acquisition. No arguments. |
| execution.results.collect | Obtain the assigned original results and publish the selected return. It observes and retains the original data when needed, or uses an already retained acquisition. The deterministic readers and calculator populate the sheet and selected values. No arguments. |

Status is not a required preliminary step. Choose between the useful available operations; there is no prescribed polling order or interval. The bound knowledge.search, knowledge.entry and knowledge.read operations can retrieve instructions when a specific instruction is needed. The corresponding launch.instructions.search, launch.instructions.entry and launch.instructions.read operations inspect resource instructions; launch.instructions.select records selected sections without executing work. episode.history can inspect this episode’s own prior attempts. Instruction text is guidance, not evidence about the input or proof that a capability is available. Use the exact operands allowed by the supplied action contract.

The deterministic reader preserves original input positions and native interval endpoints. Its calculator counts the union of the mask intervals and divides by that same record’s established input length. These are descriptions of the prepared output, not confidence in a gene function or a mask-quality score. Do not supply a model judgment or recompute a replacement numerical answer. A complete, correctly associated record with no mask intervals can establish zero masked positions; missing, partial, unassociated or invalid input/output cannot be converted to zero. Preserve usable partial records and the precise reasons unavailable values remain unavailable.

Returning saved data preserves the original measurements. It does not select a recalculation or change the DUST parameters. The requested fields and artifact access remain exactly those selected by the parent. Recorded return facts are populated from the actual selected action; this commission has no interpretation fields to compose. Return the current typed action selection with an empty report_update.

Keep request fulfillment, native success and scientific interpretation separate. A failed native attempt can supply useful diagnostics; unavailable measurements still prevent this particular measurement request from being fully fulfilled. A qualified diagnostic request can be fulfilled without native success. The configured controller owns continuation. Validated fulfillment sets future expected credit to exactly zero through that controller, preserving the final actual gain and requiring no extra confirmation action.

STEERING

| Own action category | Completed actions | Total signed yield | Expected next yield | Uncertainty or limitation |
| --- | ---: | ---: | --- | --- |
| None yet | 0 | 0 | Unavailable | No completed own actions; category estimates were not supplied. |

| Current continuation information | Value |
| --- | --- |
| Operational acquisition credit | 0 |
| Expected next gain | Unavailable: insufficient completed actions |
| Uncertainty | Unavailable |
| Continuation cost | 0 |

| Acquisition facts received by this episode | Current value |
| --- | --- |
| Original handoff | Supplied |
| Own status or collection attempts | None |
| Observed native state, output readiness and logs | Not yet received |
| Selected measurements and artifacts acquired | None |
| Requested return fulfilled | No |
| Actionable failure from an own attempt | None recorded |
