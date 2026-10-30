# Inspected source and format evidence

This is planning evidence, not native scientific output. No library import,
scientific tool, calculator, native-format fixture or episode was executed.

## Authority and original rows

The complete original supplied attachment was read from
`/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt`.
The verified SHA-256 is
`11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
No GOAL.md was read. AGENTS.md and the complete EPISODE_STRUCTURE,
TIME_AWARE_ESTIMATION, PRACTICAL_EXECUTION, original practical contract,
TASK_AND_STEERING, TOOL_KNOWLEDGE and tool-grader principle documents were read.
Historical design documents were treated as implementation evidence, not goal
authority. The goal-status row, fixed scope row, local resource row and SA-0262
source alias were read; the older inventory row was also inspected. No row changed.

## Current installed source

Complete function:
`reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/genomics.py`,
lines1091–1421, `analyze_chromatin_interactions(hic_file_path,
regulatory_elements_bed, output_dir="./output")`.
The registration in `biomni/tool/tool_description/genomics.py` and Gentner's
`tools/biomni_catalog.py` lookup path were inspected. The registration is a
description, not this workflow's production callable.

Current whole source SHA:
`74714f05594d4655e946107628114339452cab8eecbb4005feccea49be2906c5`.
Function excerpt SHA:
`7e960d2a3fbc8486d46c061efb05d7585f670850fb08b9624c299afcdcde0f58`.
The alias's historical full-file SHA is
`04063191bd3f293279f5cbe91b1b8d8633359c991a1b16c1ab9c3a8f141cd9ed`.
These facts differ; there is no assertion that the entire installed file is
still the inventory snapshot. The exact current excerpt is retained here.

Static directory/package-metadata inspection found:

| Environment | Presence observed | Absence in inspected site-packages directory |
| --- | --- | --- |
| root `.venv` | NumPy2.5.4, SciPy1.18.1 | cooler, hicstraw, h5py, pandas, biomni |
| `reference/episode_tools/.venv` | Biomni0.0.8, h5py3.16.0, NumPy2.5.0, SciPy1.18.0, pandas2.3.3 | cooler, hicstraw |

Package directories/dist-info do not establish working imports or a correct
selected runtime. Other installations were not searched or tested. There is no
chromatin-specific production binding found in the inspected workflow package.

## Authoritative external format facts

Only primary project documentation/source was used. Complete downloaded bytes,
URLs, sizes and hashes are in SOURCE_FILES.json. The current-branch bytes are
snapshot evidence identified by their hashes; a future implementation must pin
its actual dependency version. Direct downloads of two ReadTheDocs source URLs
returned403; those failures remain in SOURCE_FILES.json. Their project GitHub
sources were retained instead. Browser reads of the rendered documentation
succeeded. No scientific dataset was acquired.

1. [Cooler schema3](https://cooler.readthedocs.io/en/latest/schema.html),
   with [project schema source](https://github.com/open2c/cooler/blob/master/docs/schema_v3.rst).
   It defines HDF5 chrom/bin/pixel/index tables, zero-based half-open bins,
   optional weights/assembly metadata, symmetric-upper versus square storage,
   and explicit URI groups. A multi-resolution container needs a selected
   group. A fixed resolution is distinct from variable bins.
2. [Cooler matrix API](https://cooler.readthedocs.io/en/latest/api.html#cooler.Cooler.matrix),
   with [project implementation](https://github.com/open2c/cooler/blob/master/src/cooler/api.py).
   Matrix calls apply existing weights; they do not compute them. The inspected
   class method and underlying matrix function preserve multiplicative/divisive
   choices. Sparse balanced returns contain only stored pixels, so a mask has
   to be retained separately to distinguish a masked bin from implicit zeros.
   The contract deliberately requires explicit normalization convention rather
   than relying on column-name defaults.
3. [HIC format v9](https://github.com/aidenlab/hic-format/blob/master/HiCFormatV9.md).
   The complete specification was read. It describes header/assembly/chromosome/
   resolution records, matrix/block indexes, compressed sparse/dense blocks,
   expected vectors and normalization-vector indexes. BP and FRAG are distinct
   units. A chromosome-pair map's absence is distinct from a present indexed
   matrix with no stored contact blocks. Dense no-value encodings need explicit
   qualification before treating them as biological zero.
4. [hic-straw Python instructions](https://github.com/aidenlab/straw/blob/master/pybind11_python/README.md)
   and [C++ Python-binding source](https://github.com/aidenlab/straw/blob/master/pybind11_python/src/straw.cpp).
   The complete README and relevant complete functions were read: readHeader,
   readFooter, readMatrix, readBlock, readNormalizationVector, MatrixZoomData
   constructor, getNormVector, getExpectedValues, getRecords,
   getRecordsAsMatrix and exposed binding methods. Missing maps can return an
   empty vector; getRecordsAsMatrix turns emptiness into a1x1 zero; normalized
   getRecords filters NaN/Inf. This is why installing that package alone does
   not repair the wrapper's false-zero behavior. Its URL mode is not allowed
   inside the supplied-data parsers.

## Actual workflow implementation paths examined

The following were examined for responsibility boundaries. This list does not
claim that every line of every large module or the entire workflow was audited.

* Complete `native_file_capture.py`, `tool_grading_artifacts.py`,
  `native_genomic_overlap_tool_info.py`, `native_genomic_overlap_local.py`,
  `native_genomic_overlap_results.py`, `native_genomic_overlap_capture.py`,
  `local_jobs.py`, `episode_return_records.py`.
* BLAST `parse_blast_json`, `build_pairwise_sheet`,
  `build_database_sheet`, `_validate_saved_population`,
  `calculate_database_probabilities` and their extraction/association context.
  Existing BLAST behavior was used as a separation example and was not changed.
* Overlap `genomic_overlap_result_worker` data records and `_native`, `_saved`,
  `_publish`, `run_genomic_overlap_result_worker`, `main`; result preparation
  builders, retained-input helper, `_run` and `prepare_genomic_overlap_worker`.
  Contact algorithms do not reuse overlap numerical semantics.
* `ExecutionEpisodes` configured tool/request/result branches and relevant
  selection, target, fact/received-return, reference, completion and credit
  consumers; `LocalPracticalOperations` selected handle/job/status/read paths;
  `ExecutionTargetReader._native/returnable_handoff`.
* `ScientificToolLibrary` catalog, actual information/invocation resolution
  and literal retrieval; `ScientificProcessLibrary` snapshot/construction
  context. The exact consumer list in CONTRACT uses existing method names.
* Packet418 contract, packet422 root acceptance and packet428 result contract
  as existing seam examples. Some broad reads were output-limited; the relied-on
  source functions and final shared-seam corrections were read separately.

This is source availability/semantics evidence. The packet verifies no runtime
deployment, contact numerical result, native-format parser or full return path.

## Final additive exposure and document-check record

The separate reference checkout exposes its Biomni description through
`gentner_ave.deps.load_deps` → `biomni.utils.read_module2api` →
`make_analysis_agent.call_biomni_tool` → `AnalysisExecutor.run_biomni_tool`.
The declared `GENTNER_AVE_DISABLE_BIOMNI_TOOLS` default is false; its effective
runtime value and a live call were not tested. Current workflow
`ToolRegistry.catalog`, `ExecutionEpisodes.resource_tool_contracts/_request_schema`,
`ScientificToolLibrary.freeze/_tool_information/resolve_invocations` and
`Workflow.scientific_retriever_catalog/catalog` do not import that catalog or
have a named chromatin binding in the inspected source. This does not exclude
an arbitrary explicit caller-supplied practical command or audit historical runs.

Later local_jobs runs validated only this packet's schema, synthetic records,
cross-record relationships and retained-source hashes. The final report is
DOCUMENT_VALIDATION.json: 121 definitions, 70 complete synthetic records, nine
negative shape checks and seven retained-source hashes passed. Resource evidence
shows 20 GiB RAM, 4 GiB scratch, zero swap and no wall budget; the final job took
1.849430633 seconds. No native parser, scientific calculator, native input fixture
or full episode workflow was executed by this packet. The initial 60-record
check and its source draft were preserved separately.

Before final handoff, the original objective and entire sixteen-principle block
were reread verbatim again, and the original attachment SHA-256 remained
11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7.
