# Proposed scientific-parent receiving text, 506/001

These are STEERING inserts for running user feedback. They are not approved or
coded templates. The parent's own complete TASK and its own yield table are
built separately. Provenance notes below are review evidence, not prompt text.
No example supplies a next-action choice or an invented operand alias.

## 1. Illustrative future RMSD request and saved recalculation

Proposed text:

> Protein comparison — PDB chain A fixed; chain B moving. Cα fit on 3 residue pairs.
>
> | Requested calculation | Evaluation population | RMSD (Å) |
> |---|---|---:|
> | Original | 1 selected residue pair | ≈2 |
> | Saved-sheet recalculation | All 4 mapped residue pairs | ≈1 |

This is an illustrative future parent request concerning RMSD, explicitly
selecting `evaluation_rmsd` plus `fit_used_count` and `evaluation_used_count` for
their scientific populations. It uses values already present in actual retained
410 check011 root-return summaries. The actual 410 selector requested six
fields, including alignment score, mapped count and SSE; it remains unchanged.
This proposed narrower request is not an automatic current-turn focus filter
and is not represented as the actual 410 selected return.

The retained numbers came from local native extraction/alignment/comparison on
a synthetic PDB fixture with scripted episode choices. This is not a live-model
prompt run or a newly executed narrower request. Both comparison identities
explicitly state `fit_then_evaluate_ca` and `identifiable_fit`. Chain A versus B
identifies the fixed and moving inputs. The model and TER segment values add no
further distinction in this example, so the main display omits them. Show them
when they identify the selected input/site. Exact evaluation populations are
1 and 4; fitting population is 3 in both. The original request and saved
parameters establish the selected versus all-mapped evaluation labels. The
host's original/saved label must use the exact receipt-selector join described
in the contract, not the order of these rows or their numbers.

Exact retained RMSDs are `1.9999999999999991` originally and
`0.9999999999999996` later. `≈` is an explicit
formatting proposal. No threshold classification is recomputed from it.
No coordinates or transform matrices were requested in these returned summaries,
so none appears. Neither return establishes stability, scientific confidence,
unchanged structure or function. The later requested threshold is not displayed
as a measurement when no threshold-result field was requested.

## 2. A selected distance request absent from a partial window

Proposed text:

> Requested site distances — partial.
>
> Window: zero-based offset 1, limit 1; 1 of 3 requested rows returned, 2 omitted.
>
> | Evaluation request index, zero-based | Distance |
> |---:|---|
> | 99 | Unavailable: requested evaluation entry not found |
>
> Two of the three requested entries matched retained evaluation entries.

This is an explicitly synthetic display input transcribed from the existing
`tests/test_protein_structure_result_views.py` case
`test_missing_explicit_sites_are_rows_and_windows_count_full_population`.
The request indexes are `[3, 99, 1]`, offset 1, limit 1. The expected counts are
requested 3, matched 2, returned 1, omitted 2. The displayed unresolved request
99 has an empty value list and `selected_field_unavailable`; no residue name or
distance is invented. This fixture expectation was read, not executed for 506.
It does not represent a new native failure or a newly admitted parent return.

## 3. Supplied sequence use and an explicit sequence projection

Descriptor-only proposed text:

> Supplied sequence — PDB chain A; implicit model, zero-based index 0; TER segment 0.
>
> 4 observed residues. Supplied for sequence alignment and structure correspondence.
>
> Requested projection fields unavailable; affected projection and site unspecified.

Input: historical 397 four-source form copied in 413. Its received sequence
descriptor contains length 4, `observed_polymer`, and the two listed uses. The
separate failure has `selected_field_unavailable`, field `projection_fields`,
with null projection/site. Its custody is present internally; no claim of absent
custody is made. Sequence letters are not in this descriptor and are not
displayed. No saved input or unreturned table is opened.

If the parent instead explicitly requested letters and residue-map values, the
following separate input gives this proposed text:

> Extracted sequence — PDB chain A; implicit model, zero-based index 0; TER segment 0.
>
> `AGST` — 4 observed residues. Supplied for sequence alignment.
>
> | Sequence position, zero-based | PDB residue | Insertion code | Residue symbol |
> |---:|---:|---|---|
> | 0 | 10 | blank | A |
> | 1 | 10 | A | G |
> | 2 | 11 | blank | S |
> | 3 | 15 | blank | T |

Input: historical 407 extraction return, retained as 413's
`test_actual_runtime_pending_re1` metadata. It explicitly selects `descriptor`,
`alignment_sequence`, `sequence_length`, `residue_map_row`, and all sequence
positions; these selected cells contain the displayed values. This separate
descriptor grants only `sequence_align`. It must not borrow
`structure_correspondence` from the first example. The 407 metadata record is
component evidence, not fresh proof of scientific-parent admission or prompt
delivery. These two inputs demonstrate when letters and maps belong in the
message; they are not combined into one invented return.

The exact callable reference/descriptor still remains private. The prose use
statement does not implement a way to choose that operand in the current
tool/assignment JSON. Root must close that separate shared interface before
claiming the parent can perform the displayed follow-up use through a model.
