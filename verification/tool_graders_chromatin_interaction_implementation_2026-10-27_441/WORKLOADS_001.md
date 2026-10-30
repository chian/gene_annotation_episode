# Chromatin implementation ownership and accepted interfaces

Additive implementation record, 2026-10-27. This does not replace the original
user-supplied goal, change the fixed scope, or claim a working tool. Root reviewed
the complete439 contract, closed-record field inventory, concrete numerical
examples, array interfaces and lifetime/relationship rules before assigning code.
The original goal attachment remains authoritative:
`/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt`,
SHA256 `11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
Do not read GOAL.md. Every fresh owner reads the original attachment and repeats
its required objective/all16-principle context reset after substantial native
or external examination and before completion.

## Accepted scope and source versions

The fixed row is B-L124-analyze_chromatin_interactions and its existing local
binding. Both source-intended calculations are retained:
cis_anchor_contact_enrichment and cross_window_insulation_heuristic, each with
explicit raw or precomputed-weighted normalization. This is no new evidence axis,
annotation-score formula, literature grader, episode type or autonomous workflow.

The following439 files define the accepted coding interfaces. Earlier draft
snapshots and corrections remain in439. Further discoveries require an additive
interface correction communicated to every affected owner.

| File in packet439 | SHA256 |
|---|---|
| CONTRACT.md | 2c83429fa82dc94baa04fbc1bc1ad052da8d7562b4421da4b6cd9931a25a3017 |
| RECORD_SCHEMA.json | df4fafcc7c50a5afff5dc0e4bd961c910f695ead03a77e90ee3045f02d4617af |
| RECORD_INTERFACES.pyi | 0a70c4ce605623f61ed42fcf7ad740772ff4b44bda58bcfdcb908349a281d497 |
| RECORD_SHAPES.md | be63c0e91d286c206ddfcc1b93525c2fd3702eefd84e406587ce39124ab5f093 |
| WORKED_RECORDS.json | d1002a156dac237954f0663c2f98a422b8e1258a69f8ad00aa9610f6ad9be82a |

Immediate native implementation is explicit Cooler HDF5 schema3/group selection.
HIC remains required separate format work with unresolved completeness/sentinel
semantics. The runtime library must not advertise HIC as available. HIC does not
block implementation of the fixed Cooler records and calculations. No generic
fallback, first chromosome, silent raw normalization, inferred element class,
fabricated zero matrix or scientific-value acceptance threshold is permitted.

The parent-selected anchor is interval_start or a supplied coordinate inside
the element. The comparison population is the exact selected cis region; its
same-distance mean is not silently taken from the whole chromosome. Insulation
includes every mathematically full window, correcting the inspected source's
omitted final window. These choices remain explicit in the selected operands.

## Parallel owners

All production names below are under gene_annotation_episode. Each owner also
owns only the corresponding newly named tests and its own verification packet.
No owner edits shared execution, literature, scoring, accounting, other tool
modules, another owner's files or the accepted records above.

| Owner | Exclusive production files | Responsibility and exact handoff |
|---|---|---|
| C1 inputs and numerical sheet | chromatin_interaction_contracts.py; chromatin_cooler_inputs.py; chromatin_interaction_inputs.py; chromatin_interaction_tables.py | Closed type/schema validation; supplied HDF5/element parsing; reference/sample joins; finalized table descriptors; read-only array contexts; populated ContactSheet. |
| C2 calculations and selected return | chromatin_interaction_calculations.py; chromatin_interaction_result_views.py | Deterministic contact and insulation components, explicit parameters and requested projection. Consumes the fixed sheet plus read-only ContactTables, without acquiring or parsing original native input. |
| C3 finite execution and retained calculation worker | native_chromatin_interaction_contracts.py; native_chromatin_interaction_driver.py; native_chromatin_interaction_local.py; chromatin_interaction_result_worker.py; native_chromatin_interaction_preparation.py; native_chromatin_interaction_tool_info.py | Actual dependency-pinned request/plan, sequential population extraction/seals, bounded native execution and bounded saved-data calculation. Uses ordinary local_jobs/native_lifecycle; owns no episode decisions. |
| Root C4 shared integration | native_chromatin_interaction_capture.py; native_chromatin_interaction_results.py; chromatin_interaction_returns.py; chromatin_interaction_return_views.py; chromatin_interaction_operands.py; chromatin_interaction_execution_information.py, if individually needed; existing shared consumers | Original selected-input authority; complete file capture; received-only saved operands; exact typed returns, credit/endpoint consumers and full Workflow. Reuse existing shared mechanisms; do not clone an independent authority system. |

C1 publishes contracts/types first so C2/C3 can import the shared definitions.
Their coding does not wait for a complete parser or native deployment. Unit
fixtures may instantiate the agreed data; that does not establish native or
host integration. Joined tests require actual completed implementations.

440 independently supplies DEPENDENCIES.json, FIXTURES.json and actual native
receipts. Its existing reference Python/h5py/NumPy environment is a concrete
producer candidate, not a fabricated full SoftwareBinding. C3 freezes actual
module/dependency bytes after its code exists. Do not alter shared environments
or substitute an unverified interpreter.

## Function ownership and noncircular flow

C1 contracts owns `validate_chromatin_record(kind: str, value: object) -> dict`
and the corresponding record type exports. One mechanical schema export is
also required for existing resource/commission consumers:
`chromatin_record_schema(kind: str) -> dict`. It returns an independent copy of
a standalone2020-12 schema with its exact selected root, only reachable local
definitions and a stable local id. It accepts only named contract definitions.
This is data-shape validation, not an executable scoring-rule language. JSON
byte decoders reject duplicate keys and nonfinite constants before calling the
object validator; an already decoded object cannot reveal discarded duplicates.

C1 cooler module owns read_cooler_contacts. C1 inputs module owns
parse_chromatin_elements, extract_chromatin_metadata and build_chromatin_sheet.
C1 tables module owns open_chromatin_contact_tables and
read_chromatin_sheet_tables. Exact signatures and dtypes are439's .pyi; export
ContactTables/ContactPopulationArrays from the contracts module for all owners.
HIC's eventual module has a separate owner and is not implemented as a fake
successful stub in C1.

The concrete flow is:

1. C3 supplies the immutable native input and output streams for one frozen
   population. C1 writes complete canonical table encodings and returns finalized
   metadata/drafts, including explicit present/absent states. C3 closes/hashes/
   seals the population before advancing to the next originally selected one.
2. Root capture supplies actual retained identities for those closed tables.
   C3 worker opens only those supplied streams and enters
   open_chromatin_contact_tables(descriptors, streams=...).
3. In that context, build_chromatin_sheet receives both TableDescriptors and
   table_views. No pre-existing sheet or original HDF5 reread is required.
4. C2 calculates from this sheet and the same read-only arrays. The standalone
   contact/insulation functions receive explicit normalization plus their own
   parameters. The aggregate receives CalculationParameters unchanged.
5. project_chromatin_result returns exactly the selected typed fields and their
   necessary qualifications. Complete components and data remain retained.
6. A later saved calculation receives the actual previously returned sheet/table
   bundle. read_chromatin_sheet_tables validates it using the same array loader.
   It does not reacquire native inputs, rerun extraction or change old results.

Arrays support repeated traversal/random access through the context lifetime.
No one-shot iterator, Python list of all pixels, dense whole-chromosome copy or
unprovided path lookup is an allowed substitution. The loader owns its mappings;
the caller owns stream lifetime. Returned records contain no live array handles.

## Verification and reporting

Use existing local_jobs/native_lifecycle for every executable test/native check:
20GiB RAM,4GiB scratch,zero swap,no wall allocation. Retain exact source/binary
pins, requests, outcomes and failed attempts. Follow an existing live handle to
termination; an observation timeout is not a restart condition.

C1 verifies genuine HDF5 bytes, missing/malformed data, explicit/implicit zeros,
weights and masks, coordinate/index/reference/element associations, supplied
streams and mapping lifetime.440's two real serialized synthetic fixtures are
inputs, not proof that C1 works. C1 must run its own parser over them.

C2 verifies all439 hand-worked answers, changed parameters from the same saved
data, unknown/zero denominator distinctions, masks, duplicates, missing cells,
all-full windows, tied minima and projections. Raw6 over mean4 is fold1.5;
weighted6 over mean7 is6/7. Cross sums[5,1,5,1,5] give mean3.4 and variance3.84;
at threshold-1, boundaries20/40bp delimit20bp. These become verified only after
actual calculators run. Keep complete numeric components separate from the
parent's requested subset.

C3 verifies actual selected interpreter/dependencies, population seals and
partial survival, one finite invocation, original-attempt recovery, complete
table retention, retained-only recalculation and explicit resource failures.
Root verifies selected library through launch/local/results and typed parent
receipt, actual credit/baseline/endpoint/replay and model-message boundaries.
No full-tool tally increment follows from any one standalone component.

Do not code new TASK/STEERING templates under this assignment. Any needed
message boundary is separately printed for the user's required running feedback.
Native monitoring/tool information is deterministic data under existing resource
episodes, not a new LLM judge or per-tool monitoring episode.
