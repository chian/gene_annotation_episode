# Independent production workloads and exact handoffs

This plan is a proposed provider/integration boundary, not a completion claim. The independent math contract is separately frozen in `MATH_HANDOFF_001.md` and accepted by root for fresh assignment. Association workload A is accepted in root's `ACCEPTED_ASSOCIATION_WORKLOAD_011.json`, with mandatory additive `ASSOCIATION_AUTHENTICATION_CLARIFICATION_012.md` and `EXPLICIT_MEMBER_ENTITY_ASSOCIATIONS_013.md`. The three frozen association files remain unchanged. Original-`#` acquisition parsing is implemented and root-owned, per `../tool_graders_bvbrc_msa_metacats_implementation_2026-10-25/METACATS_INPUT_READER_CONTRACT_005.md`; root reported127 input/shared-format checks and9 subtests, including25 new checks. Those are root's verification results, not executions by this planning task. No production file is owned by this planning task.

Every fresh coding task must begin by reading the entire immutable goal at `/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt`, applicable AGENTS, required design documents and the complete affected implementation/consumer paths. After native/source examination, reread purpose and all sixteen design principles verbatim before translating evidence into code. After completing a tool, perform the same reset and reread its accepted I/O/sheet contract. Give each coder a fresh task, explicit nonoverlapping file ownership and the original resource/communication constraints. Do not reuse a stale unrelated task. This is implementation discipline, not runtime episode behavior.

## A. Common and MetaCATS association/input extraction

Create and own:

* `gene_annotation_episode/bvbrc_alignment_provider_contracts.py` — exact common records, reused native document-envelope validation, ReaderSpec validation, explicit supplied association-role types.
* `gene_annotation_episode/bvbrc_alignment_associations.py` — `extract_inline_fasta_members`, `extract_alignment_associations` and `input_member_occurrence_subject_id`.
* `gene_annotation_episode/bvbrc_metacats_association_contracts.py` — exact category/metadata/biological/native/export association records.
* `gene_annotation_episode/bvbrc_metacats_associations.py` — `extract_metacats_associations`.
* New tests `tests/test_bvbrc_alignment_associations.py` and `tests/test_bvbrc_metacats_associations.py`.

Do **not** own `bvbrc_metacats_input_formats.py` or its tests; root is implementing that exact accepted reader. Do not alter shared AlignmentDocument, FASTA parser, MetaCATS native parsers or math.

Inputs: original host InputBindings; root's MetaCATS input FASTA and existing aligned-FASTA/native metadata/category-table reader results; explicitly authenticated source/transform/metadata/feature/function/taxon records. Exact functions, every nested output and complete original declaration payloads are frozen in `ASSOCIATION_HANDOFF_001.md`, `PROVIDER_RECORDS_001.md` and `NATIVE_DOCUMENT_RECORDS_001.md`, with accepted clarifications012/013. A does not depend on a changing bundle draft for its base definitions. The additive XMFA extension adds only ReaderSpec/ParsedDocument variants to A's common validators after root acceptance; root coordinates that exact change with the association owner, with no second owner editing its files.

Handoff: complete `AssociationSet` and `MetaCATSAssociationSet` values with source IDs, row identities, original occurrence keys, explicit member_entities relationships, transformation maps, categories, biological groups, authentic R-column identity when present, and specific missing requirements. No native R-order evidence is required for ordinary BiologicalAssignment or BiologicalGroupPopulation. R evidence is required for native-source reproduction/export joins. The adapter authenticates original group/auto binding existence and auto-entry parameter pointers/values; the pure MetaCATS extractor validates internal entry/category relations and every supplied actual member key without requiring the original group/auto binding to have any MemberFacts. A fetched occurrence can have a different binding identity. Empty fetched populations preserve requested provenance and unresolved links. This workload does not calculate chi-square or a function-confidence score.

Consumers: `extract_msa_sheet` and `extract_metacats_sheet`. The adapter resolver authenticates content, dispatches readers and compiles SlotRef fields before calling these extractors. Association code performs relationship checks; custody remains host-owned.

Tests: exact header/sequence joins with selected normalization; duplicate first-token labels/full headers; identical sequences under distinct identities; original inline FASTA content/pointers/physical locations; metadata duplicate overwrite/native concat hazards; explicit member_entities with two features sharing sequence, wrong SourceRecord kinds, duplicate links and unrelated shared evidence; negative/reverse/translated/stripped coordinate maps; downstream separate reference/segment/gap-fill operands; original `#` versus masked terminal dash; metadata-only A with actual B/C R columns; twelve-group padded R tokens; commas/blank values in labels; multiple category columns with repeated headings; files/groups/auto mode; wrong category/hash/task evidence; valid biological grouping without any R operand. No network/native execution.

`input_member_occurrence_subject_id(input_binding_id:str,member_id:str,occurrence_index:int)->str` returns canonical `input_member_occurrence:<percent binding>/<percent member>/<decimal occurrence>`. It is an identifier for shared Subject.id, not a Store reference. This lets composition/taxonomy count distinct supplied occurrences without changing shared calculator shapes. Source-record identity remains explicit. Existing shared MemberRef coverage/reference APIs cannot distinguish same-ID occurrences; only a uniquely resolved original MemberRef may be lowered, with an explicit requirement otherwise.

## B. Biological arithmetic and adequacy — already independently frozen

Exact ownership, inputs, output record definitions, consumer signatures, tests and accepted native-count-ID correction are all in `MATH_HANDOFF_001.md`. This can proceed independently from A/C/D/E/F/G. Its handoff is actual validated BiologicalCounts/Statistics/Effects/ExpectedCountAdequacy plus the additive TestFamily provenance, original native API compatibility, and a verification-only native old-to-v2 rekey map. It requires no provider envelope to calculate from actual alignment/membership values.

Root-owned separate input parser hands all workloads the existing ParseResult[AlignmentDocument] while preserving original `#`; it does not replace A's original-input/member association work.

## C. MSA provider and deterministic component assembly

Create and own:

* `gene_annotation_episode/bvbrc_msa_provider_contracts.py`
* `gene_annotation_episode/bvbrc_msa_inputs.py`
* `gene_annotation_episode/bvbrc_msa_grader.py`
* `gene_annotation_episode/bvbrc_msa_xmfa_inputs.py`
* New tests `tests/test_bvbrc_msa_provider.py`, `tests/test_bvbrc_msa_provider_replay.py`, `tests/test_bvbrc_msa_xmfa_inputs.py`.

Exact functions: `extract_msa_sheet(...)`, `validate_msa_sheet(sheet)`, `calculate_msa(sheet,parameters)`, `verify_xmfa_source_inputs(...)`, `extract_msa_xmfa_bindings(...)`. Inputs/outputs are the closed `PROVIDER_RECORDS_001.md`, `NATIVE_DOCUMENT_RECORDS_001.md`, MSA/common tags in `CALCULATIONS_001.md`, and exact additive `XMFA_PROVIDER_EXTENSION_001.md` for root acceptance. Depend on A's complete `AssociationSet` and common validators, not an unfinished full episode. Depend on installed `parse_msa_frequency_table`, `msa_native_entropy`, `msa_reference_differences`, shared alignment/coverage/tree/composition/taxon/comparison functions, plus actual Newick/FASTA parse records. The full-XMFA mode consumes the accepted pure XMFADocument, root's bind_xmfa_sources/validate_xmfa_bindings_for_document, and the four exact outputs assigned by `ACCEPTED_XMFA_CALCULATORS_WORKLOAD_014.md`. Reuse them directly; C does not own or modify those pure files.

Required useful modes: new ordinary DNA/protein alignment, supplied prealigned analysis with its real definition mismatch qualified, segment alignment, concatenated segments with explicit segment/coordinate maps, first-block Mauve AFA projection clearly labelled, native frequency/consensus/reference comparisons, optional actual FastTree output and supplied organismal relationship comparison. Missing original map or deployed FastTree version does not suppress independent alignment/gap/entropy values. It does suppress unsupported coordinate/model/support claims.

Handoff: populated numerical MSASheet and Components, including native observations and all independent requested arithmetic. The additive extension defines the complete initial-v1 full-XMFA provider shape, explicit source-reader/byte verification and four calculation outputs. Preserve `mauve_blocks` as unintegrated until those actual handoffs are installed and tested; source/binder availability alone is not completion. Actual first-block AFA and full XMFA are separate analyses with explicit dependence. `full_xmfa_slot_id` stays the caller's slot while xmfa_document_id is the actual parsed ID. GenBank/DNAstar source records remain a precise unbound extractor requirement; valid literal/native-coordinate requests survive missing source bindings.

Tests: actual retained DNA/protein foma tables and consensus bytes; score92 versus entropy0.918295834..., score81 versus entropy0.811278124..., protein score100 with tied Del/Gly; blank counts; unknown protein detail; strict-majority deletion versus unknown residue; full-row terminal masks with column subsets; duplicate coordinate observations; exact reference row/string identity; incomplete maps; translation and reverse-strand correspondence; segment gaps/order; multiple analyses with same filename; optional tree support/branch units absent; complete saved-data replay with parser/acquisition disabled. Add every explicit XMFA source-byte/native-axis/original-map case in the extension, including six blocks, source lengths50/41/49, first-block39 identities/7 substitutions out of46, conflicting claimed sequences and unbound formats. Do not synthesize a native alignment score where none exists.

## D. MetaCATS provider and deterministic component assembly

Create and own:

* `gene_annotation_episode/bvbrc_metacats_provider_contracts.py`
* `gene_annotation_episode/bvbrc_metacats_inputs.py`
* `gene_annotation_episode/bvbrc_metacats_grader.py`
* New tests `tests/test_bvbrc_metacats_provider.py`, `tests/test_bvbrc_metacats_provider_replay.py`.

Exact functions: `extract_metacats_sheet(...)`, `validate_metacats_sheet(sheet)`, `calculate_metacats(sheet,parameters)`. Depend on A's exact MetaCATSAssociationSet; the installed five native parsers and original calculator APIs; B's exact mathematical outputs; root's input reader. Provider-envelope/dispatch implementation can proceed while B is being coded because its accepted signature/shape is explicit; numerical end-to-end tests wait only for the named functions, not for an entire tool family or all host wiring.

Handoff: MetaCATSSheet with original row/metadata/category/group/R/export identities and actual native observations; Components with explicit requested biological and native-reproduction results, effects, adequacy, populations and correction families. Never gate biological counts on R evidence. Never attribute an R native result to a biological group merely by exported heading order. `calculate_metacats` passes actual saved output values unchanged into dependent calculations; it does not silently rewrite native test df or underflow p.

Tests: seven executed native cases (`official_na`, `aa_two_groups`, `aa_three_groups`, `native_pair_tail_underflow`, `metadata_only_first_group`, `all_missing`, `twelve_groups`); use corrected twelve-group provenance in EXAMPLES_002. Include full312-test official population versus143 filtered rows; p<cutoff versus <=; complete empty eligible family; malformed/native NA/underflow numbers; extra metadata groups; repeated/blank/comma labels; absent original input but retained filtered tables; available original# input; unknown source-vs-mask provenance; changed epsilon recalculation with native numbers unchanged; independent success despite one category failure; complete source/biological FDR provenance validation.

## E. Pure adapter selection, projection and facades

Create and own:

* `gene_annotation_episode/bvbrc_alignment_bundle_contracts.py`
* `gene_annotation_episode/bvbrc_alignment_bundle_resolution.py`
* `gene_annotation_episode/bvbrc_alignment_bundle_projection.py`
* `gene_annotation_episode/bvbrc_msa_bundle_adapter.py`
* `gene_annotation_episode/bvbrc_metacats_bundle_adapter.py`
* New tests `tests/test_bvbrc_alignment_bundle_resolution.py`, `tests/test_bvbrc_alignment_bundle_projection.py`.

Exact inputs/functions/outputs are in `BUNDLE_AND_RETURN_001.md`, `PROVIDER_PARAMETER_CLARIFICATIONS_002.md` and `XMFA_PROVIDER_EXTENSION_001.md`. Depend on A's ReaderSpec/common/supplied-role validators and C/D's exact provider functions. No new host schema: original ArtifactMember has role but no requirement ID. Multiple analyses/categories use explicitly selected unique bundle-role aliases. Supplied original files/metadata and staged XMFA source files are actual authenticated bytes. Resolve exact slots, preserve all analyses, compile fixed typed SlotRefs, invoke parsers/providers/calculators once during publication, save whole numerical sheets/components, and project only the original finite requested form. Cross-analysis families use exact analysis-scoped TestSelectors and named source results, then compile unchanged pure TestFamily/p-cell operands. Multiplicity return selectors use all_family or explicit scoped tests, never unknown future IDs.

Tests: actual retained native bytes in authenticated-shape fixtures, exact declared format mismatch, hash/byte count, missing/ambiguous/incomplete slots, repeated same representations, same bytes under two explicit category declarations, no parser selection by extension, partial category with other category success, forged supplied claims, missing inputs/metadata versus zero result, invalid requested selectors, unknown future IDs avoided by slot/row/field/scoped-test selection, two analyses reusing a category ID, wrong auto-entry pointer/value, empty explicit row selection, complete requested projection with unrelated unfinished optional work retained, saved original adapter pin identity, and four XMFA finite projections with exact verified source bytes. These are pure bundle fixture tests, not live BV-BRC proofs.

## F. Saved return owner and host wiring

Create `gene_annotation_episode/bvbrc_alignment_returns.py`; own new tests `tests/test_bvbrc_alignment_returns.py` and `tests/test_bvbrc_alignment_episode_integration.py`. Exact class/functions/source schemas are in `BUNDLE_AND_RETURN_001.md`.

One root-assigned integration owner exclusively edits these existing files after coordination with ongoing phylogeny verification: `gene_annotation_episode/bvbrc_appservice_adapters.py`, `gene_annotation_episode/api_service_execution.py`, `gene_annotation_episode/bvbrc_appservice_host.py`, `gene_annotation_episode/execution_episodes.py`. The exact consumer functions are listed in the bundle contract. Do not split these edits between other workers or alter their existing phylogeny dependencies while an ongoing test requires them. No changes to shared method_loop, credit or continuation are required.

Depend on E's requested-form/catalog/encoding contracts and actual adapters; C/D's saved sheet/component identities; G's declaration function for discovery. Authenticate original saved result + sheet + component content. Copy only saved AdapterResult.facts. Reject forged child values/identifiers, sibling access, unreceived facts, another run/scope/assignment, altered original selector or pin, changed saved components, and later-file substitution. Validate parent admission against original child report and exact requested typed facts. No parser/calculator/network call is permitted during later facts/forwarding/recovery.

Full path verification must exercise selected `child_tool_info` -> ordinary launch/resource/results commission -> actual acquired retained native bytes -> adapter numerical sheet/calculation -> original requested report -> scientific parent admission. Use recorded native bytes with explicit synthetic transport/selection fixtures where a live resource is unavailable, and label that evidence accordingly. A test calling only `consume_bundle` is not full episode-path verification. Verify multiple selected tools and all three construction slots remain intact, TASK/STEERING behavior unchanged, and no extra completed action/credit observations are introduced by parsing or forwarding.

## G. Real tool information and narrow mode accounting

Create `gene_annotation_episode/bvbrc_alignment_tool_info.py` and new `tests/test_bvbrc_alignment_tool_info.py`. Own only those files; discovery wiring belongs to F. Exact declaration signature/names/routes are in the bundle contract. Depend on E's original selector parameter/form schemas, existing assignment_schema and configured adapter pins. No service probe or submission is part of tool discovery.

Every entry contains real name, description, resources and substantive instructions. Preserve parent selection information and selected-child callable commissioning contracts. Only configured API route is advertised; source-present local/HPC binaries and current credentials remain separate facts. Monitoring instructions retain native task/log information under the generic monitor task, with no mandated cadence or automated retry. Files/groups/auto and ordinary/prealigned/segment/Mauve distinctions are real scope differences, not invented confidence tags.

Root owns permanent progress updates: retain fixed original inventory keys `bvbrc/service/msa_snp_analysis` and `bvbrc/service/metacats`, add mode/resource subdivisions without dropping the original identity, and update completion columns only with actual evidence. Tool info, sheet, parsers/extractors, calculators, production result binding, numerical/integration checks and live-resource status remain separate.

## Independent scheduling and exact unresolved dependencies

A, B, G and the separate XMFA format/math work can run independently after their respective contracts are accepted. C/D can implement against A's frozen output contracts; each awaits only A's exact functions for integration tests, and D awaits B's named new functions. E can implement resolver/form validation against frozen schemas before C/D are installed, then finish native-byte integration when their entry points exist. F can implement pure saved-record validation from agreed fixtures while E is finishing; shared wiring and complete episode-path proof require E/C/D/G installed together. Use fresh parallel workers where available; no broad “all provider work blocked” label is justified.

Remaining concrete gaps cannot be erased by this contract:

* **Full XMFA:** accepted parser/source-binding/coordinate/metric outputs at `../tool_graders_bvbrc_msa_xmfa_boundaries_2026-10-25/PROPOSED_CONTRACT.md`, frozen SHA256 `f6ebf5348d260c2f84b6cf3d245a050a329b0fd670aa237a4a769f340943f701`, plus accepted addenda009/010/014. Root exclusively owns `xmfa_sources.py`, `xmfa_source_contracts.py`, `tests/test_xmfa_sources.py`; separate parser owner has `xmfa_formats.py`/`xmfa_format_contracts.py`; calculator owner014 has `xmfa_coordinates.py`, `xmfa_calculators.py`, `xmfa_calculation_contracts.py` and two new tests. C consumes their actual typed results through the additive provider extension; E/F consume its finite projections. No provider coder edits those pure files. GenBank/DNAstar source-byte extraction remains an explicit binding gap even when a supplied source JSON object validates. No fake flattened AlignmentDocument.
* **Prealigned definition mismatch:** current retained MSA definition file-type enum does not establish the source's aligned-file bypass. Need actual deployed definition/accepted parameter evidence before the real launch route can claim that bypass. Existing acquired AFA can still be read/compared.
* **Original coordinate/segment maps:** actual retained input/output/transformation evidence is needed. Shared ungapped coordinates exist now; original genome/translated/concatenated coverage must stay qualified when evidence is absent. An original MemberRef ambiguity cannot be erased by collapsing occurrences.
* **Live version/resource status:** retained source revisions and local native components do not establish the current deployed MSA/MetaCATS engine versions, native task-produced byte versions, complete live Workspace output population, or live episode execution. Those remain explicit separately tracked verification work, not a reason to withhold all saved-data functionality.
* **New biological and adequacy math:** accepted workload B now has actual new modules; root owns acceptance of its numerical/replay verification. D consumes those exact outputs and their accepted standard-pair/provenance boundary, never fake native R identities. This planning task did not run B's tests.
* **Original `#` input parser:** root-owned implemented reader, separately verified by root. A/D/E must still wire its exact selection and preserve source `#` separately from generated terminal masking through the whole selected result path.

No new native/live/HPC jobs, remote submissions, ongoing phylogeny test modifications, W05 aggregation, literature work or generic scoring layer are authorized by this planning task.
