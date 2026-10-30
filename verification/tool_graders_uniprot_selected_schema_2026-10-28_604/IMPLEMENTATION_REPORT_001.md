# Selected UniProt schema and validation increment C

Implemented the six pure public ports from ROOT_CODING_PORTS_003.md in
`gene_annotation_episode/uniprot_return_contracts.py`, with only the exact new
UniProt registration and selected-value branches added to `communication.py`.
The original supplied user goal remains authoritative. This report records an
implementation increment, not a changed goal or provider-completion claim.

## Definitions, selection, and validation

One runtime `_DEFINITIONS` tree contains the exact 54 definitions from the frozen
Contract002 artifact. Both the detached selection schema and fully inlined
selected return schema derive from that tree. Runtime code does not read
verification files. The builder derives the text bound from the parent's
explicit selected windows and attaches an unchanged strict-JSON selection.

The validator distinguishes JSON booleans, integers and floats, rejects
non-finite/non-JSON inputs, and uses complete matches for the frozen anchored
token/digest/identifier patterns. This prevents Python's trailing-newline `$`
behavior from admitting a non-token without changing the frozen schema tree.
Explicit native text windows still accept source newlines and Unicode.

Selection checks cover duplicate publication/record/field criteria, incompatible
publication modes, scalar and token alternatives, semantic text/EC pointers,
explicit all/ordinal/primary-accession clauses, GO/database selection,
entry-interval feature overlap, evidence owners, and text/sequence intervals.
Different record criteria can overlap. Nothing selects an extra field or grant.

Value checks cover request-array correspondence, page and selected-record count
relationships, original ordinals, absent/null/invalid/unavailable distinctions,
exact character-window arithmetic, sequence-window sizes and overlapping-window
consistency, collection count partitions, explicitly requested ordinal membership,
feature interval and endpoint relationships, record-local evidence owner/ordinal/
pointer tuples, selected xref properties, and source/sequence grant-to-witness
joins. They establish internal consistency; the future host return reader must
authenticate actual values and complete source/receipt tuples.

`requested_uniprot_selection` examines whole top-level fields only, rejects
duplicate registrations, and compares the complete canonical JSON field against
the builder output. `uniprot_fact_sources` advertises exactly the specified
object-valued empty-selection source.

## Actual communication consumer trace

Inspected the complete communication compiler, form validator, semantic union
traversal, fact insertion, interpretation extraction and generation conversion.
The new compiler branch accepts only this exact top-level source and generated
schema. The new value branch maps declared errors to the existing
`ReportBoundaryError.diagnostic` with the selected field path. Existing generic
prose restrictions and other source branches were preserved.

Inspected the existing `TypedReportContract` constructor/admission,
`_compile_form`, `_references_in`, report construction in `DecisionSource.finish`,
and the receive-form reference collection boundary. The schema travels within
the existing measurements schema; object-valued facts already pass through
`form_with_facts`. Existing semantic traversal visits nullable explicit grant
descriptors. Witness IDs have no reference semantic format and cause no resolver
calls in the tests. Explicit grants call only the source or artifact resolver.
An independently requested reference field retains its own deliberate meaning.

The full pre-existing contract-information helpers and relevant native UniProt
scalar/feature/evidence/xref extraction and validation paths were also read.
Root separately owns compact selected-form expansion and saved declarations;
C did not edit that module. No runtime traversal, receipt, API, episode-loop,
prompt, model, numerical grader, annotation-credit or controller code was edited.
`COMMUNICATION_DIFF_001.patch` records the two scoped branches against check052's
source snapshot. `SOURCE_HASHES_001.json` records the tested source hashes.

## Verification evidence

All application execution was performed by root's existing bounded runner with
20 GiB memory, 4 GiB scratch, zero swap and no wall-time cap. Worker-local checks
were limited to stdlib AST/JSON/source inspection. AST inspection confirmed the
54 runtime definition literals exactly match the frozen artifact.

- Root check053: 219 passed, 2 failed. Both failures were the frozen JSON test
  artifact being omitted from the runner snapshot; no implementation assertion
  failed. Its communication, compact-selection and existing contract-information
  selectors exercised the exact source branch alongside unrelated contracts.
- Root check054: pytest collection stopped because P's test module used pytest's
  reserved `request` parameter name. P repaired its own test names; no production
  repair was needed for that collection error.
- Root check055: `tests/test_uniprot_return_contracts.py` and
  `tests/test_uniprot_return_projection.py` report **148 passed in 6.41 seconds**
  in `check055_uniprot_selected_projection/stdout.txt`. This includes C's final
  strict-pattern and present-collection ordinal regressions plus P's retained
  native-record projection cases. Root's terminal/quiescence and pin collection
  are the authority for the final runner receipt; stdout alone is not that
  receipt.

The numerical examples retain their factual meanings: a 10,000-character name
with offset 20 and limit 40 returns 40 code points with omitted prefix 20 and
suffix 9,940; sequence `[9,19)` returns 10 residues; native GO indices 2 and 31
remain 2 and 31; evidence ordinal zero at two owners remains two distinct cells.
None of these quantities is an annotation-confidence score.

## Explicit remaining integration work

This increment does not establish authenticated acquisition-to-results-to-parent
delivery, frozen successful-attempt forwarding, source/sequence receipt admission,
closed replay, alias identity accounting, material-consumer access enforcement,
or a full-sequence-artifact downstream operand. It does not fix the own-outcome
raw context fallback or implement any parent/child/ancestor model-facing template.
Those host and presentation boundaries retain their separate owners and tests.
No API call, native scientific job, HPC job or configured-model episode ran here.
No provider-completion count or inventory completion claim was added.

Reread the original objective and all ten operating principles after substantial
work, and reread Contract002 and ROOT_CODING_PORTS_003.md before this handoff.
