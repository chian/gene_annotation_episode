# 054 proposal: publish kinetic source witnesses with bounded display labels

Status: proposal only, pending root release. No production file or test has been changed. This workload is code-only and synthetic-only; no paper, 051 scientific packet/selection, private provider history or live database has been opened.

## Reproduced problem and exact baseline

Root's independently executed `kinetic_witness_parent_review_054/reproduce_label_boundary.py` and `BASELINE_LABEL_FAILURES_001.json` establish two legitimate source witnesses that fail after native reading/calculation during publication: a 611-character condition witness violates reference.label maxLength512, and a 33-character multiline condition witness violates its single-line pattern. Both attempts roll back the whole SQL state and save zero operations. I read that synthetic script and receipt; I have not rerun or changed their immutable outputs.

The complete current `literature_kinetic_storage.py` baseline is preserved in `baseline_001/literature_kinetic_storage.py`, SHA256 `1af09288ff81d8839605f0c4cbfb063af2a831587676bb8d00af50d2bee49d16`. `BASELINE_001.json` records its byte count and unchanged status.

`_bindings.ref` currently assigns the complete source quote to both reference.label and reference.anchor.quote. LABEL is limited to512 characters and excludes CR/LF; ANCHOR independently retains the complete exact UTF-8 quotation and existing16000-character schema bound. The native witness selector itself has no512-character display restriction. The publication defect must not narrow scientific source selections.

## Smallest proposed change

Add one small deterministic private helper directly in `literature_kinetic_storage.py`; call it only for the reference.label value inside `_bindings.ref`.

1. If the quotation already satisfies the existing label length and CR/LF requirements, return it exactly, including existing spaces, tabs and Unicode.
2. Otherwise make a display-only whitespace-normalized preview with `" ".join(quote.split())`.
3. Prefix this transformed display with `[source witness preview] `. If necessary truncate only this display body and append the Unicode ellipsis `…`, reserving space so the complete label is at most512 characters. For normalized text that fits, do not add a truncation ellipsis.
4. Keep the original `anchor` object untouched, including its complete original quote, source_ref, artifact_ref and UTF-8 byte start/end. Derive the existing accession from this original anchor exactly as before.

The helper is presentation only. The preview marker truthfully signals that the display is not an exact quotation. It introduces no new source length restriction, scientific status, fallback operand, source selection, schema version or dependency file. The existing schema, selected operation name, dispatcher and typed interface remain byte-for-byte unchanged.

For the two root cases, publication must succeed with original full quotes retained. The long label becomes `[source witness preview] ` followed by the fitting normalized prefix and `…`; the multiline label becomes `[source witness preview] Condition: first line second line`. Neither label substitutes for source evidence.

## Invariants and consumer trace

| Boundary | Required invariant |
| --- | --- |
| Source acquisition/custody | Existing `_Sources.witness` authenticates the complete original byte interval. No helper touches selections, source bytes, reader output or extraction fields. |
| Calculation | `populate_kinetic_contrast` receives the same complete operands/context. All calculated numbers, units, flags, conditions, missing reasons, physical-measurement IDs and estimate keys remain identical for the same selected source. |
| Reference publication | Only invalid display labels change; full source anchors and anchor-derived accessions remain exact. Generic LABEL/ANCHOR and Store validation remain unchanged. |
| Saved authentication | `_bindings` constructs both published and expected references, so the same deterministic display helper is used during saved validation. No scientific reader/calculator or source bytes are needed to reconstruct that display from the original saved witness. |
| Typed child return | Existing component selection, actual reference resolver, ownership and exact admitted-subset checks continue to govern what crosses. No extra raw numerical cell is authorized by a longer context witness. |
| Provider text | Existing `_kinetic_token_state`, `_kinetic_hidden_records`, `_contains_optical_token` and `_kinetic_received` operate on full original anchors, including when a numerical token lies beyond the displayed prefix. Shortening a label must not bypass numerical masking. Off-page token-source withholding remains effective. |
| State/accounting | One selected population is one existing action; previews create no action, observation, credit, source processing gain or controller decision. Saved reconstruction leaves complete SQL unchanged. |

A transformed reference's content-addressed record ID and the resulting sheet/outcome references will naturally change because the label is part of the record. This does not change physical/estimate scientific identities. Existing short valid references remain identical. Implementation dependencies already fingerprint the storage module, so newly created sheets bind the new generation; this proposal does not migrate, repin or claim cross-generation reopening of historical saved sheets. Original047 releases and051 immutable pins remain untouched.

## Prospective files and explicit exclusions

After root release, the only existing file changed will be:

- `gene_annotation_episode/literature_kinetic_storage.py`

The only new test file will be:

- `tests/test_literature_kinetic_witness_publication.py`

Receipts, a delivery patch, final baseline comparison, test logs and any bounded synthetic probe outputs will be written only under this054 directory. No generic domain/Store, native reader, calculator, validator, base044, amount, optical, prompt, episode/runtime, controller, C7 manifest or source051 changes are proposed. The similar all-family publication pattern is a possible future concern; no other family has been independently reproduced/released by this workload.

## Verification plan after release

All new cases will be explicitly synthetic and use the actual existing source reader, calculator and repository publication route, rather than supplying parsed scientific numbers.

1. Exercise complete conditions, subject/construct and interpreted relationship witnesses with long single-line, LF, CRLF, combined multiline/long, and multibyte Unicode text inside the existing anchor bound. Include valid511/512-character and invalid513-character display boundaries. Check published labels against the actual generic LABEL schema, and assert valid short labels remain exact. Verify original artifact bytes at every anchor and full original quotes, byte offsets and source identity after population.
2. For each selected source, compare its saved extraction, calculation input, full calculation result, cell values and physical/estimate identities against an independently called existing native reader/calculator using that same source and nomination. Display transformation must not change any of them. Verify existing raw numeric-token bindings still use their actual token anchors.
3. Exercise a long/multiline witness through the actual `LiteratureEpisodes.execute` binding and ordinary shared Episode child-return path. Request only parameter_ratio/log contrast in an existing typed form, validate using the actual binding/resolver, and establish exact child ownership, parent admission, requested values and unchanged source-qualified metadata. Assert one population, the expected ordinary own-action observations and zero invented scientific credit; repeat delivery must not add progress.
4. Drive the real provider presentation path with the existing controlled wire. Include broad full-source condition/physical witnesses that contain unrequested parameter/uncertainty tokens within the display prefix and beyond the truncation position, with token references both visible and off-page. Assert requested contrasts remain visible; raw and canonical unrequested values/counts/confidence/intervals remain withheld in child and source-evidence parent text. Inspect full anchors rather than trusting the preview text.
5. Build a genuine C4 typed admission and reconstruct its original exact parent receipt from saved artifacts. Close and reopen with an actual SQLite `mode=ro` connection. Forbid source artifact access, native reading, scientific calculation, re-receipt and credit projection during reconstruction. Assert original outcome, selected parent cells, full anchors and admission are identical, complete SQL dump unchanged, and no observations added. The test must establish the forbidden-source boundary before invoking reconstructed reads, not only after prewarming them.
6. Keep source-custody rejection meaningful: a wrong quote or byte interval must still fail and roll back publication rather than being made acceptable by display normalization. Saved display/anchor tampering must still fail existing authentication.

Run the new dedicated test file first, then the four existing kinetic test modules. Run the existing related prompt/parent-admission tests if the new real-boundary checks expose a concern. Report exact commands/results and any uncovered limitation. Tests are engineering evidence only, not a configured-model scientific demonstration or completion of A105/W04/W05.

## Inspection record for this proposal

Fully read: full active-goal attachment; root AGENTS.md and GOAL.md; EPISODE_STRUCTURE.md; TIME_AWARE_ESTIMATION.md; TASK_AND_STEERING.md; W04 amendment; latest039 human direction and both040 clarification records; all four current kinetic implementation modules and all four kinetic test modules; root synthetic reproduction and receipt; episode_admission.py; literature_reference_parent_prompt.py.

Relevant complete functions/blocks read: generic LABEL/ANCHOR/reference schema and validate_schema; Store._anchor and applicable publication/reference-validation blocks; `_Sources` source/witness custody; kinetic source operation dispatcher/fact sources/routes/typed validation and delivery hooks; base044 delivery authentication, native source authorization, owner/subset validation and receive/reconstruction methods; service kinetic repository accessor; TypedReportContract; actual form validation/reference resolver; kinetic/overlap/selected-record/presentation functions and shared task/steering renderer; existing controlled provider-wire and source-service test setup. Large generic runtime/Store modules were inspected only at the relevant paths, not claimed read in their entirety.

No scientific source paper/packet was inspected and no scientific interpretation or new task template is proposed. No reset/research attestation is implied. No tests have yet been run by054; root's recorded baseline failures are retained as independent evidence.
