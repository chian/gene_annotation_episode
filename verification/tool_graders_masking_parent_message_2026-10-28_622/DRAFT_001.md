# Proposed masking return within scientific-parent STEERING

Review draft only. This covers one receiving boundary: an existing
`scientific_process` episode receives its original direct `results` child's
selected masking return, before a possible later own decision. It does not
construct the results child's prompt or change the scientific parent's TASK.
The parent's complete existing TASK and its own action-category yield,
expectation and uncertainty tables remain separately supplied unchanged.

The concrete text below uses the actual DUST return retained by
`check074_masking_workflow`. Its original direct-child selector requested all
original sequence records, `input_length`, `masked_positions`,
`masked_fraction`, relevant checks, output mask ordinal 0, and the saved sheet
and calculations. It did not request WindowMasker statistics. No new numbers
are calculated for this draft.

## Ready-to-print returned-result text

```text
Selected DUST masking result

Requested return: complete. Native execution: succeeded. Native output: complete.

Sequence-preparation measurements for supplied sequences operand 0.
Record ordinals identify the original input order, starting at 0.

| Original record | Input length (nt) | Masked positions (nt) | Masked fraction |
| --- | --- | --- | --- |
| 0 | 80 | 80 | 80/80 = 1.0 |
| 1 | 32 | 0 | 0/32 = 0.0 |
| 2 | 72 | 72 | 72/72 = 1.0 |

Received material: complete mask output (output mask, ordinal 0), saved masking
sheet, and saved calculated components.
```

Only this returned-result text is added to STEERING. Its title is a descriptive
label, not a new TASK or a new return instruction. Mask extent and fraction are
sequence-preparation measurements, not gene-function confidence or new
scientific-evidence scores. The three records are the actual masking job's
supplied file records; they must not be relabeled as the separate 12-nt root
problem sequence.

Every requested quantity is retained here, with no arbitrary row limit. Passing
checks and empty failure/statistics arrays are omitted from this particular text
because they add no actionable qualification. The original typed form retains
them unchanged. This does not establish a general return-everything display.

The received-material labels describe explicit grants. They are not invented
callable aliases. Exact artifact identities remain in the host's original
receipt and operand binding. The concrete mechanism for choosing a displayed
material through a typed action without exposing host hashes still requires
its own implementation after feedback; this draft does not claim it exists.

## Conditional material at the same receiving boundary

These are alternatives for other original direct-child selectors, not extra
facts to append to the DUST example.

For the retained `windowmasker-mask0` result, the requested fraction rows are
`80/80 = 1.0`, `0/32 = 0.0`, and `0/4 = 0.0`, in nt at original ordinals 0, 1,
and 2. Its selected statistics and actionable qualification require this
additional text:

```text
Requested WindowMasker statistics

| Native statistic | Returned value |
| --- | --- |
| Unit length | 3 nt |
| t_low | 3 |
| t_extend | 126 |
| t_threshold | 126 |
| t_high | 126 |

The statistics were supplied; their reference provenance is unknown.
```

Those thresholds are the native statistics-file values. They are not a
restatement of the separately selected masking invocation parameters or a
substitute for them. No unit-count rows were requested. Empty `unit_counts`
does not mean every unit count is zero. The input statistics file was not
returned as an artifact in this case, even though selected scalar statistics
were returned. The direct parent did receive the mask output, saved masking
sheet and saved calculations.

For the completed `check080_masking_workflow_counts_and_saved` create-counts
result, the same receiving boundary instead uses:

```text
Selected WindowMasker reference-statistics result

Requested return: complete. Native execution: succeeded. Native output: complete.

| Native statistic | Returned value |
| --- | --- |
| Unit length | 3 nt |
| t_low | 3 |
| t_extend | 126 |
| t_threshold | 126 |
| t_high | 126 |

Statistics generation from supplied reference-sequences operand 0 is authenticated.
Received material: complete native statistics output (output statistics, ordinal 0)
and saved parsed statistics.
```

Counts creation has no masking population or mask fraction. It therefore has
no sequence-quantity table. The reference-sequence file was not returned as a
file grant. No unrequested unit counts, percentiles, native versions, clipping
parameters or inferred properties are added.

If a later direct-child selector explicitly requests a native unit code, show
its exact native count and code. If that selected code is absent, say it is
absent from the retained statistics; do not manufacture a zero. If a requested
cell is unavailable, retain its actual missing reason. For ambiguous hard-mask
output, `changed_positions` remains a separate quantity from
`masked_positions`; do not substitute a change count for unknown mask extent.

## Evidence and limits

`SOURCE_AND_RECORD_AUDIT_001.json` contains exact retained selected values,
the original DUST direct-child schema/source mapping, the frozen child form,
source pins and static equality assertions. The original scientific upstream
form requested only status, quantities and statistics. That narrower upstream
form does not remove the additional materials or qualifications received from
its own direct results child.

The original DUST workflow has two scientific decisions: commission launch,
then commission results. It closes after the results return. No original third
scientific decision or rendered post-return prompt exists. The draft is
grounded in actual received values, but its presentation is proposed and has
not been sent to a model. No production prompt or renderer was changed.
