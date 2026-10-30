# Proposed disjoint implementation ownership

These are proposed implementation boundaries after this contract, not delegated implementation work. Each implementer must read the authoritative goal and relevant complete consumer paths. No scope row is complete merely because one handoff passes. Existing parent authorization determines when fresh workers begin.

## A. Native readers, metadata, numerical sheet and shared finite types

Sole proposed production ownership:

- `gene_annotation_episode/bvbrc_fastqutils_contracts.py`
- `gene_annotation_episode/bvbrc_fastqutils_schemas.json`
- `gene_annotation_episode/bvbrc_fastqutils_native.py`
- `gene_annotation_episode/bvbrc_fastqutils_fastqc.py`
- `gene_annotation_episode/bvbrc_fastqutils_fastq.py`
- `gene_annotation_episode/bvbrc_fastqutils_reports.py`
- `gene_annotation_episode/bvbrc_fastqutils_sam.py`
- `gene_annotation_episode/bvbrc_fastqutils_metadata.py`
- `gene_annotation_episode/bvbrc_fastqutils_sheet.py`
- `tests/test_bvbrc_fastqutils_native.py`, `tests/test_bvbrc_fastqutils_sheet.py`, own fixture directory `tests/fixtures/bvbrc_fastqutils_native/`

Input: immutable native bytes and declared artifact metadata, exact original task, explicitly supplied/custodied metadata; contract001 and retained producer sources. Output: `NativeDocument`, `Metadata`, `Sheet`, all shared schema getters/validators. Exports are the A functions in CONTRACT001 plus `schema(name: str) -> dict` (detached schema with local `$defs`) and `validate(name: str, value: dict) -> None` with strict finite JSON and semantic validation. `Sheet`/`Components`/parameters/fact schema types must be frozen for B/C; this shared file belongs to A only, so proposed changes are exchanged explicitly instead of conflicting edits.

Implement exact FastQC0.12.1 numeric/HTML subsets, Trim Galore0.6.10 own reports, fastq-pair0.3 stderr counters, Hostile1.1.0 JSON, FASTQ, and SAM/BAM standard1.6. BAM uses standard-library bytes decoding per retained SAMv1 source, including complete typed optional fields and missing values. No filesystem lookup from source paths, external process, reference acquisition or new package dependency. Preserve unsupported Cutadapt/SAMstat/SRA sections as raw blocks, explicit requirements and existing valid cells; no unsupported numerical interpretation. Do not overwrite source counters with recounts.

A must deliver evidence for all finite metric paths, incomplete files, empty/missing modules, FastQC NaN, mislabelled compression, ambiguous/colliding identities, repeated recipe observations, paired/unpaired denominators, genuine vs synthetic identity, and retained complete bytes. Semantic document records/joins must be complete enough to support B. Before returning, give B/C the exact hashes of shared schema and a complete source-linked positive fixture, partial fixture, and unavailable fixture. The shape-only arithmetic example here is not a replacement for a custody/lineage fixture.

## B. Deterministic calculations only

Sole proposed production ownership:

- `gene_annotation_episode/bvbrc_fastqutils_calculators.py`
- `tests/test_bvbrc_fastqutils_calculators.py`

Read-only imports: A's shared contracts; do not import native readers, provider, host or execution layers. Input: saved `Sheet` and `CalculatorParameters`. Output: `Components`, with unchanged native cells and independently versioned formulas, explicit numerator/denominator/operand references and parameter digest. Exports are all B functions in CONTRACT001. No universal aggregate, annotation score, native-status number or pseudo-human-contamination rate. No arbitrary lambda/expression strings.

B can start from this frozen schema and the explicitly synthetic numerical oracle while A builds source-linked fixtures. Validate lineage/units/population before returning an available component. Once A fixtures arrive, validate the real public `populate... -> calculate...` handoff. Test changed quality thresholds without parser/I/O, prefix-only counts without whole-file rates, missing/zero denominators, incompatible pair keys and native rounded-zero fallback. Native raw QC values remain separately inspectable. Return exact source hash and numerical receipts to C/D.

## C. AppService provider, schema-bound projection and saved-value validation

Sole proposed production ownership:

- `gene_annotation_episode/bvbrc_fastqutils_bundle_adapter.py`
- `gene_annotation_episode/bvbrc_fastqutils_bundle_resolution.py`
- `gene_annotation_episode/bvbrc_fastqutils_fact_contracts.py`
- `gene_annotation_episode/bvbrc_fastqutils_bundle_projection.py`
- `tests/test_bvbrc_fastqutils_bundle.py`, `tests/test_bvbrc_fastqutils_projection.py`

Read-only dependencies: A/B modules, existing generic AppService contracts and bundle construction. `consume_bundle` must use the exact signature called by `bvbrc_appservice_publication._grade`. Resolve only selected bundle artifacts and supplied values, checking immutable content hash and original FastqUtils task. Native names do not authenticate source identity. No acquisition, HTTP, hidden retries, native pipeline, source replacement or produced-source fiction.

`ProviderParameters` and `FactSelection` in the schema asset fix C's finite inputs. `RequestedForm` is a **builder input shape**, not the actual `requested_schema` stored in the AppService selector. C must expose `requested_form_schema(selections: dict[str, dict]) -> dict` that returns the standard closed JSON Schema object (`type`, `properties`, `required`, `additionalProperties:false`) with each canonical property containing the corresponding finite `...Fact` schema and `x-bvbrc-fastqutils: <FactSelection>`. `validate_requested_form` must rebuild and compare the exact canonical schema, including every selector/required field; do not accept arbitrary schemas with a plausible annotation. See fully read `bvbrc_proteome_fact_contracts.py` for the actual receiving grammar pattern, not for scientific meaning.

Facts expose finite measurement/component/category/population/association/requirement/status meanings. Native arbitrary labels are source-bound identifiers in the communication layer, never unrestricted findings. `project_fastqutils_result` copies selected saved values, and `validate_saved_projection` validates equality and ref integrity **without invoking parser/calculator**. Requested missing data is typed unavailable while valid siblings survive. All source refs and record refs must belong to the selected original result; no cross-task or cross-library substitutions. A/bundle failure cannot be hidden by an unrelated successful field.

Facade exports `ADAPTER_ID`, `ADAPTER_VERSION`, `consume_bundle`, `implementation_sha256`, `parameters_schema`, `validate_parameters`, `requested_form_schema`, `validate_requested_form`. Hash closure covers all actual transitive provider/scientific source and schema assets, not merely facade bytes. B's calculation version and original parameters are stored independently of that pin. C returns exact frozen schema+facade signatures and accepted positive/partial/failed bundle examples to D.

The local scientific `Requirement`/`Diagnostic` shapes are not the generic host envelope. C explicitly translates requirements to existing `AcquisitionRequirement` keys `requirement_id, kind, role, source_refs, reason_code`: missing native bytes→`output_bytes` (or `input_bytes` for original inputs); sample/stage/encoding/reference metadata→`scientific_metadata`; version/custody proof→`byte_version_evidence`; unsupported parser→`parser_binding`. Keep the scientific requirement object in the sheet. Host diagnostics use `code, phase, path, severity, evidence_refs`, with native decode/association/publication phases appropriate to their actual source. The provider returns `status` only from `ok|partial|invalid|failed`; this is operational/request completeness, never numerical confidence. The publication layer, not C, creates `sheet_content` and `components_content` bindings from returned `sheet` and `components`.

## D. Existing execution/return boundaries, actual tool info and integration verification

Sole proposed production ownership:

- New `gene_annotation_episode/bvbrc_fastqutils_tool_info.py`
- New `gene_annotation_episode/bvbrc_fastqutils_returns.py`
- Shared `gene_annotation_episode/bvbrc_appservice_adapters.py`
- Shared `gene_annotation_episode/bvbrc_appservice_publication.py`
- Shared `gene_annotation_episode/bvbrc_appservice_host.py`
- Shared `gene_annotation_episode/api_service_execution.py`
- Shared `gene_annotation_episode/execution_episodes.py`
- `pyproject.toml` only for schema package-data inclusion; no native dependency changes are required by this contract
- `tests/test_bvbrc_fastqutils_episode_path.py`, `tests/test_bvbrc_fastqutils_returns.py`, `tests/test_bvbrc_fastqutils_tool_info.py`

D can inspect existing consumers while A/B/C run, but completes registry/returns integration after their concrete handoffs. With four total agent slots, the parent can own D and assign A/B/C to three workers, or serialize D after one slot frees. No worker edits another's files. Shared-file changes belong exclusively to D; no child independently changes accounting, goals, historical receipts, candidate182/186, evidence axes or runtime policy.

Actual receiver changes are listed in CONTRACT001 §8. D must read each affected complete method/path, register the provider pin, publish complete sheet/components on the selected action, add tool contracts with substantive instructions, and expose finite fact families through existing `EpisodeReturnRecords`. Use exact original task, selected schema/parameters and content bindings; latest own result must not revive older success. Forwarded historical facts continue to reference their original publication.

The report translator cannot simply remove regex/union constraints and call the result typed. Use reference/identifier namespaces plus mandatory original fact validation and saved-value equality, following the actual existing communication restrictions. Delivery invokes no scientific parser/calculator. Verify own, parent and grandparent paths, exact admission/custody, and negative tampering cases through actual receiving functions. Existing operational/completion logic remains unchanged except explicit adapter projection handling. Read-filtering job labels assign no new gene-function evidence or local scientific observations.

D should verify packaging imports with public API, selected AppService acquisition/bundle/publication routing, return facts and failure propagation. Synthetic transport tests remain synthetic; a retained genuine artifact test does not become live execution; mocked `start_app2` does not prove service availability. Live runs require actual episode selection and resource access; no live submissions are in this source-contract task.

## Handoff order and stopping boundary

Freeze schema/IDs first. A and B exchange source-linked measurement fixtures; C checks their public interfaces and source custody; D integrates their frozen facade. Fix failures in the owning module, preserve completed valid data and expose missing acquisition needs. No hidden native repair. Parent scope rows only advance for capabilities actually verified. Before proceeding to another required tool, reread the authoritative objective and complete DESIGN PRINCIPLES verbatim.
