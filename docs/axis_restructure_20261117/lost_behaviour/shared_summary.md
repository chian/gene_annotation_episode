# Lost behaviour, shared scope (HEAD files outside the axis folders)

Written 18 November 2026. Read-only review: no code or test was changed and no test was run. HEAD is `97308b94c`.
Per-file table: `shared.tsv` (5,029 rows). This file groups the losses.

## Result

462 files that held working, non-runner code at HEAD have no home anywhere in the working tree now: 430 Python
modules (127,984 lines) and 32 BV-BRC application definition files. 41 more modules (12,481 lines) are uncertain.
At HEAD 176 test files imported a lost or uncertain module directly; at the baseline they held 6,293 tests, 6,058 passing.

| Verdict | Files |
|---|---|
| present (same path, same module name elsewhere, or same definitions under another name) | 1,017 |
| intended removal | 3,509 |
| lost capability | 462 |
| uncertain | 41 |

Where the lost Python modules were at HEAD: `root/library/` 343 (100,202 lines), top-level
`gene_annotation_episode/*.py` 41 (18,384 lines), flat `root/*.py` 46 (9,398 lines). For 171 of them (36,408 lines)
the shared copy was the only copy at HEAD: no axis folder had a module of that name. For the other 259 an axis
folder also had a copy at HEAD and that copy is gone too.

How they went. `root/library/` was removed as a whole on 18 November; the only record is the reason text in
`retired_tests.tsv` ("imports the deleted root library (root/library, deleted on purpose 2026-11-18)", 183 test files).
There is no per-file record for it or for the deleted top-level modules. `runs/claude_ablate/old_root_deleted.tsv`
covers the old root runner (3,432 paths) and lists only 12 library files. Many of the lost modules appear in
`runs/claude_ablate/old_root_broken_importers.tsv`: they imported old-root modules, broke when the runner went, and
were then deleted instead of being repointed.

## Scope and method

Scope: the 9,171 HEAD files outside `root/a101` … `root/a110`. 2,489 are under `docs/` and `research/` and were not
examined. Of the other 6,682: 4,997 non-test Python files (one row each in `shared.tsv`), 671 test files (585 no
longer at their path) and 1,014 data and text files.

For each non-test Python file, in this order:
1. Same path exists now: present (188).
2. A module of the same name exists now and at least 80% of the HEAD file's top-level definitions, or all its
   public ones, are in one current file: present.
3. No module of that name, but every top-level definition is in one current file (renamed or merged), or the name
   minus its axis id exists (`literature_a108_storage` → `literature_storage`): present.
4. Files in the role homes (`root/scientific_process/**` and its file-for-file copies `root/hpc_coordination`,
   `root/published_evidence_assessment`, `root/execution_*`, `root/resource_*`, `root/homology_*`,
   `root/local_job_execution`, `root/hpc_job_execution`), `root/method_loop`, vendor files and files listed in
   `old_root_deleted.tsv`: intended removal.
5. The rest were classed by family from their names, module docstrings and HEAD importers.

Limits. Matching is by top-level definition names; function bodies were not compared, so "present" means the module
and its names exist, not that it behaves the same. Imports were read from `import` statements at HEAD; modules started
by a module-path string (`-m` workers and drivers) show no importer. The axis copies of these modules belong to the
axis reports; a row here says only whether any module of that name is left anywhere.

## Who offered these at HEAD

No axis module imported the shared copies; each axis had its own. The shared copies were offered by the shared root:

- Ordinary tools: the shared `ToolRegistry` (`root/tool_registry.py`). Its catalogue (`root/direct_tool_catalog.py`)
  and executor (`root/direct_tool_execution.py`) imported the tool modules, and `gene_annotation_episode/cli.py`
  built it (`root/tool_configuration.build_tools`) for `root/run_execution.run_workflow`.
- Native job families: the shared execution episodes. `root/execution_episodes.py`,
  `root/execution_resource_information.py` and the `operations.py` of `root/execution_job_submission/**` and
  `root/execution_result_acquisition/` imported them.
- BV-BRC result readers: the adapter table `gene_annotation_episode/bvbrc_appservice_adapters.py` (`bind_adapters`
  named 17 adapters; 10 are gone) and `root/bvbrc_appservice_publication.py`.
- Literature structure and reaction: the shared literature homes (`root/published_evidence_assessment/**`) and
  `root/library/root_literature_contracts.py`.
- Service clients: `gene_annotation_episode/api_services.py` (`build_service`) and `root/api_execution.py`.

All of these offering points are part of the intended removal (old root runner, registry, role homes). The modules
below are what they offered.

## Lost capabilities

Columns: files and lines are HEAD files in this scope with verdict lost; "only copy" counts files with no axis copy at
HEAD; tests are HEAD test files that import a module of the group, with baseline passed/total. File names and test
names per group are in the appendix.

### A. BV-BRC service results

| Group | What it did | Files / lines | Only copy | Tests | Left now |
|---|---|---|---|---|---|
| MSA and MetaCATS | Read native MSA frequency tables and MetaCATS documents, build the numerical sheet, compute counts, statistics and adequacy, grade requested calculations, project selected facts | 31 / 11,256 | 0 | 21 files, 857/858 | nothing |
| GenomeAlignment, Mauve, XMFA | Read Mauve v4 segments, backbone sidecars and XMFA, bind them to supplied inputs, compute site, pair and interval measurements | 28 / 9,740 | 1 | 20 files, 964/968 | nothing |
| ComparativeSystems | Read the six ComparativeSystems formats, build the sheet, compute its quantities, project requested values | 16 / 4,972 | 0 | 6 files, 285/285 | nothing |
| FastqUtils reports | Readers for FASTQ, SAM, BAM, FastQC, Cutadapt, Trim Galore, Hostile, fastq-pair, SAMstat (three versions) and p3-sra JSON; composition, quality, mapping and consistency calculators | 22 / 4,712 | 21 | 12 files, 295/297 | 12 top-level `bvbrc_fastqutils_*` contract/spec modules; no reader |
| Annotation, assembly, HA subtype, subspecies, variation; tool information | Result adapters and native readers for five applications; launch/results tool information for Homology, GeneTree/CodonTree and GenomeComparison | 13 / 3,134 | 0 | 7 files, 115/117 | nothing |
| Application definitions | App specs (original and derived) for 16 of 24 applications, read by `bvbrc_application_definitions` through `MANIFEST.json` | 32 files | 32 | 1 file, 55/55 | 8 applications in `episode_support/forms/application_service_specs/` |

To bring back: contracts to `episode_support/forms/service_calls/`, readers and bundle adapters to
`episode_support/readers/service_calls/`, calculators to `episode_support/calculations/`, graders to
`episode_support/grading/`, specs to `episode_support/forms/application_service_specs/`. They are offered by adding
each adapter to an axis's `bvbrc_appservice_adapters.py` table and its API job binding
(`root/aNNN/<head>/execution_job_submission/api_job_execution/` and `execution_result_acquisition/`). Axes that had
copies at HEAD: MSA/MetaCATS A102; GenomeAlignment and ComparativeSystems A103; annotation, assembly, HA, subspecies,
variation A101 and A110. FastqUtils readers had no axis copy.

### B. Native job families

| Group | What it did | Files / lines | Only copy | Tests | Left now |
|---|---|---|---|---|---|
| Flux balance analysis | Read Cobra/GLPK captures and the five-column CSV, inspect and edit models, select results, run the result worker, offer `perform_flux_balance_analysis` | 20 / 6,908 | 1 | 13 files, 543/552 | contracts, driver, local launch, storage in `episode_support` (8 modules); no reader, model tools, result worker or tool |
| Fluorescence and flow cytometry | FCS and event readers, compensation and preparation, event calculations, report readers, driver, result worker | 27 / 6,085 | 20 | 20 files, 631/665 | six contract modules (several validators pruned), storage, return views; the driver named in the contracts does not exist |
| Genomic interval overlap | Overlap calculations, result worker, result and return views, capture, local launch, tool information | 14 / 4,518 | 1 | 4 files, 154/154 | contracts, inputs reader, driver |
| Chromatin interaction | Result receipts, capture, local launch, preparation, presentation, tool information | 15 / 3,380 | 8 | 1 file, 121/121 | top-level Hi-C/cooler readers, calculations, result worker and driver remain; nothing launches or captures them |
| ATAC differential accessibility | Result receipts, capture, local launch, preparation of the result worker, presentation, tool information | 15 / 3,520 | 6 | 5 files, 93/120 | top-level calculations, inputs, scores, result worker and driver remain; nothing launches or captures them |
| Expression NMF | Independent calculations from saved operands, result worker, capture, preparation, presentation, tool information | 11 / 1,594 | 2 | 2 files, 32/38 | contracts, inputs, sheet, views, storage, driver, local launch |
| HOMER motifs and TF binding sites | HOMER readers and measurements, HOMER execution and worker, Biopython TF scoring driver, TF measurements, result worker, both tools | 25 / 12,259 | 11 | 8 files, 309/320 | nothing |
| MACS2 peaks and LUMPY | MACS2 capture parsing and saved views, request binding; LUMPY execution, host, observations, request binding | 13 / 3,856 | 9 | 5 files, 173/191 | four top-level `macs2_peak_*` modules; no LUMPY module |
| Infernal preparation; Infernal, HMMER, PHMMER results | Readers for cmbuild, cmcalibrate, cmstat, cmconvert, cmfetch, cmpress, cmemit and their calculations; acquisition and publication of Infernal and HMMER attempts; PHMMER text parser and grading worker | 35 / 10,089 | 11 | 16 files, 460/481 | contracts, drivers, local launch, tool information, search grader; no preparation reader, acquisition or publication |
| BLAST database results | Acquisition of PBS attempts and publication of retained numerical generations for database and standard-database BLAST | 4 / 2,602 | 0 | none direct | result workers, result views, contracts, drivers remain |
| RNA structure | Comparison calculations, worker and publication; scan calculations; acquisition; result custody, facts and preparation; presentation | 24 / 4,975 | 11 | 2 files, 91/92 | contracts, driver, local launch, worker, calculations, comparison inputs and views |
| Protein conservation and phylogeny | MUSCLE alignment conservation and IQ-TREE phylogeny: tools, result workers, publication | 6 / 3,203 | 0 | 4 files, 141/144 | two result-contract modules, MUSCLE and IQ-TREE drivers |
| Restriction mapping | Input freezing, job custody, publication, registry, selection, tool information for `find_restriction_sites` | 9 / 2,508 | 8 | 2 files, 91/91 | four top-level modules (contracts, native, readers, worker); the tool name appears nowhere |

To bring back: readers and views to `episode_support/readers/<domain>/`, calculators to
`episode_support/calculations/`, capture and acquisition to `episode_support/acquisition/`, publication and receipts
to `episode_support/records/`, local launch, preparation and result workers to `episode_support/jobs/`, drivers and
tool information to `episode_support/tools/<domain>/`. Each family is offered by a local or HPC job binding
(`…/execution_job_submission/local_job_execution/`, `hpc_job_execution/`) and the matching
`execution_result_acquisition/acquisition_source.py`. Axes that had copies at HEAD: flux balance A110 (A107);
fluorescence, ATAC, chromatin A105, A106, A108; genomic overlap A103, A107; NMF A107; HOMER and TF A105, A106, A108;
Infernal and RNA structure A107, A110; HMMER, PHMMER and BLAST database A101, A103, A104; conservation and phylogeny
A104. The role-keyed parts of the old files (typed-return admission, completed-action receipts) should not come
back; the readers, calculators, workers and publication steps should.

### C. Ordinary tools of the shared registry

| Group | What it did | Files / lines | Only copy | Tests | Left now |
|---|---|---|---|---|---|
| Molecular measurement and sequence tools | Tool contracts, preparation, isolated-worker execution and retained publication for ITC thermodynamics, coordinate liftover, circular dichroism, arsenic speciation, protease kinetics, protein disorder, Cas9 edit outcomes, VCF results, somatic variants (Mutect2/SnpEff), ESM gene embeddings, and the molecular sequence tools (alignment, ORFs, glycosylation motifs, primer placement); the three store-free workers; publication readers and custody | 72 / 21,765 | 48 | 17 files, 516/572 | the measurement and contract modules at top level (`itc_binding_*`, `liftover_*`, `circular_dichroism_*`, `protease_kinetics_measurements`, `protein_disorder_*`, `reference_edit_outcomes`, `vcf_result_measurements`, `somatic_variant_contracts`, `esm_gene_embedding_*`, `molecular_sequence_*`); no tool wrapper, worker entry or publication |

The calculations survive but nothing can call them: the tool names (`analyze_itc_binding_thermodynamics`,
`liftover_coordinates`, `predict_protein_disorder_regions`, …) now occur only in privacy lists and receipt tables.
To bring back: tool wrappers and publication to `episode_support/tools/` and `episode_support/records/`, workers to
`episode_support/jobs/local_execution/`, and an entry for each in `episode_support/tools/tool_catalog.py` and in the
`tools.py` of the axis that needs it (A105 had protease and ITC presentation copies; A101, A105, A106, A108 had edit
outcome, VCF and molecular measurement copies; A110 had the sequence tools).

### D. Literature

| Group | What it did | Files / lines | Only copy | Tests | Left now |
|---|---|---|---|---|---|
| Structure (former A111) and reaction (A110) evidence | Source-bound coordinate/validation reader and geometry calculations with their repository; reaction measurement readers, ratio and resource-constraint calculations, native observation selectors, reaction and native repositories | 17 / 3,497 | 6 | 2 files, 26/26 | the two prompts, reaction instructions and two reaction renderers in `episode_support/literature/` |

To bring back: `episode_support/literature/readers/`, `calculations/`, `storage/`, `forms/`; offered by the A102
literature binding (structure) and the A110 literature binding (reaction)
(`root/a102|a110/<head>/published_evidence_assessment/literature_binding.py`).

### E. Service clients and projections

| Group | What it did | Files / lines | Only copy | Tests | Left now |
|---|---|---|---|---|---|
| HMMER web API | `api.hmmer.databases/prepare/submit/status/check_handoff/result`: request freezing, single submission, status, handoff and result page custody | 5 / 869 | 5 | none direct | none; `api.hmmer.result` is named only in `tool_information.py` |
| Enrichr | Finite Enrichr HTTP stages, protocol custody and recovery, publication metadata | 3 / 846 | 1 | 3 files, 138/138 | `enrichr_contracts.py`, `enrichr_reference_privacy.py` |
| Addgene sequence facts | Closed literal Addgene metadata | 2 / 424 | 0 | 1 file | `addgene_access.py`, `addgene_sequence_native.py` |
| UniProt selected fields | Project selected facts from one UniProt publication | 1 / 716 | 0 | 1 file, 58/58 | `api_uniprot.py`, `uniprot_native.py`, `uniprot_return_contracts.py` |
| Alignment-site projections | Field schemas and requested projection contracts for alignment-site results; decision text values | 2 / 556 | 1 | 3 files, 97/116 | `alignment_site_calculators`, `_inputs`, `_mapping`, `_native` |

To bring back: `episode_support/acquisition/service_calls/` (HMMER, Enrichr), `episode_support/readers/` (UniProt,
alignment sites), offered through an axis `api_services.py` and its API job binding.

## Uncertain (41 files)

| Group | Files / lines | Why uncertain |
|---|---|---|
| BV-BRC AppService and Data host steps | 10 / 3,704 | Operand custody, selected operations, monitor observation, download publication, Data and MinHash acquisition custody, written as mixins of the old API episode. `appservice_source.py` bindings exist in A103 and A104; equivalence not checked |
| Protein structure result custody | 13 / 2,719 | Results-episode acquisition, publication, receipts and typed returns. The protein structure tools, readers and workers survive in `episode_support` |
| BLAST results-episode operations | 5 / 2,367 | Acquisition and publication inside the old results episode; BLAST acquisition and publication modules survive |
| Execution progress observation | 1 / 1,868 | `ExecutionProgressProvider` for monitors; `progress_provider.py` exists in `episode_support/jobs/service_calls/` |
| Terminal and local file capture | 3 / 1,015 | Retained scientific files from general commands; `native_file_capture.py` exists |
| A107/A110 component reports | 4 / 430 | Receipt-bound component reports and source schemas |
| Literature readers | 3 / 281 | `literature_source_inputs`, `literature_product_partition_number`, `literature_partner_operand_information` |
| HPC calendar scheduler, native operation lock | 2 / 97 | `hpc_scheduler.py` backed the monitor's calendar controller; `native_operation_lock.py` was used by 11 ordinary tools, all lost |

## Names gone from modules that are present (28 files)

These modules exist now, but public names they defined at HEAD are defined nowhere. Listed in the `evidence` column.
The larger cases: six fluorescence contract modules (validators), `literature_numerical_contracts`
(`freeze_contracts`, `validate_frozen_contracts`, `expand_numerical_form`, `uses_fact_references`),
`protein_structure_action_records` (five names), `practical_execution_records` (`flux_balance_role_paths`,
`lumpy_role_outputs`, `requested_job_role_paths`), `circular_dichroism_tools` (`prepare_…`, `publish_…`),
`hpc_monitoring` (`HPCContinuationEstimator`), `alignment_site_native` (`read_selected_reference_alignment`),
`tool_information` (`workflow_execution_catalogs`), `api_services` (`validate_fresh_service_configuration`).

## Intended removals (3,509 files)

| Category | Files |
|---|---|
| `scientific_process` homes | 1,521 |
| Duplicate trees (root copies of the `scientific_process` subtree, paired file for file) | 1,515 |
| Recorded in `old_root_deleted.tsv` (runner, root task, registry and composition, credit path, axis-id tables, role-keyed return and receipt admission) | 233 |
| Extra yield estimators | 75 |
| Old runner support not in the record (homology job-role bindings, API and execution episode mixins, resource and HPC loop helpers, private helpers) | 55 |
| Examples, tools and the local example that drive the deleted runner | 29 |
| Old root literature and decision presentation, declarations | 29 |
| Root `ToolRegistry` mixins and tool retrieval declarations | 24 |
| `method_loop` copy | 12 |
| Role-keyed typed-return admission not in the record | 10 |
| Package markers, vendor | 6 |

Files with no deletion record (178 flat `root/*.py`, 1,108 library, 115 top-level) were classed from their content;
the rows above marked "not in the record" are the ones judged to be runner support. `examples/` now holds one JSON
file; no script starts a run from there.

## Tests and data

- 585 of 671 in-scope test files are no longer at their path; `per_file_comparison/shared_summary.md` covers them.
- `root/tests/fixtures`: 882 files deleted; 354 have no file of the same name left (BV-BRC application artifacts 68,
  Hi-C native 57, ATAC native 31, FastqUtils about 100, flux balance probe 20). Tests for restored modules need them from
  `git show HEAD:`.

## Appendix: files and tests per group

`[L]` `root/library/`, `[R]` flat `root/`, `[G]` top-level `gene_annotation_episode/`, `[S]` application spec.
Tests show baseline passed/total; `test_` and `.py` are omitted.

### BV-BRC MSA and MetaCATS results

Files: bvbrc_alignment_associations[L] bvbrc_alignment_bundle_contracts[L] bvbrc_alignment_bundle_projection[L] bvbrc_alignment_bundle_resolution[L] bvbrc_alignment_provider_contracts[L] bvbrc_alignment_tool_info[L] bvbrc_alignment_values[L] bvbrc_contingency_math[L] bvbrc_metacats_adequacy[L] bvbrc_metacats_association_contracts[L] bvbrc_metacats_associations[L] bvbrc_metacats_biological_calculators[L] bvbrc_metacats_biological_contracts[L] bvbrc_metacats_bundle_adapter[L] bvbrc_metacats_calculation_contracts[L] bvbrc_metacats_calculators[L] bvbrc_metacats_format_contracts[L] bvbrc_metacats_formats[L] bvbrc_metacats_grader[L] bvbrc_metacats_input_formats[L] bvbrc_metacats_inputs[L] bvbrc_metacats_provider_contracts[L] bvbrc_msa_bundle_adapter[L] bvbrc_msa_calculation_contracts[L] bvbrc_msa_calculators[L] bvbrc_msa_format_contracts[L] bvbrc_msa_formats[L] bvbrc_msa_grader[L] bvbrc_msa_inputs[L] bvbrc_msa_provider_contracts[L] bvbrc_msa_xmfa_inputs[L]

Tests (21 files, 857/858): root/tests/bvbrc_alignment_tool_info(118/119) tests/alignment_result_presentation(2/2) tests/bvbrc_alignment_associations(15/15) tests/bvbrc_alignment_bundle_projection(111/111) tests/bvbrc_alignment_bundle_resolution(54/54) tests/bvbrc_alignment_values(27/27) tests/bvbrc_metacats_associations(17/17) tests/bvbrc_metacats_biological_calculators(77/77) tests/bvbrc_metacats_calculators(36/36) tests/bvbrc_metacats_expected_adequacy(15/15) tests/bvbrc_metacats_format_contracts(26/26) tests/bvbrc_metacats_formats(31/31) tests/bvbrc_metacats_input_formats(23/23) tests/bvbrc_metacats_provider(31/31) tests/bvbrc_metacats_provider_replay(9/9) tests/bvbrc_msa_calculators(42/42) tests/bvbrc_msa_formats(45/45) tests/bvbrc_msa_provider(39/39) tests/bvbrc_msa_provider_replay(1/1) tests/bvbrc_msa_xmfa_inputs(29/29) tests/xmfa_formats(109/109)

### BV-BRC GenomeAlignment, Mauve and XMFA results

Files: bvbrc_genome_alignment_host_inputs[R] bvbrc_genome_alignment_associations[L] bvbrc_genome_alignment_bundle_adapter[L] bvbrc_genome_alignment_bundle_contracts[L] bvbrc_genome_alignment_bundle_projection[L] bvbrc_genome_alignment_bundle_resolution[L] bvbrc_genome_alignment_calculation_contracts[L] bvbrc_genome_alignment_calculators[L] bvbrc_genome_alignment_input_contracts[L] bvbrc_genome_alignment_inputs[L] bvbrc_genome_alignment_retained_records[L] bvbrc_genome_alignment_sheet[L] bvbrc_genome_alignment_tool_info[L] genome_alignment_reference_contracts[L] mauve_backbone_calculators[L] mauve_backbone_contracts[L] mauve_backbone_formats[L] mauve_v4_calculation_contracts[L] mauve_v4_calculators[L] mauve_v4_format_contracts[L] mauve_v4_formats[L] xmfa_calculation_contracts[L] xmfa_calculators[L] xmfa_coordinates[L] xmfa_format_contracts[L] xmfa_formats[L] xmfa_source_contracts[L] xmfa_sources[L]

Tests (20 files, 964/968): tests/bvbrc_alignment_associations(15/15) tests/bvbrc_alignment_bundle_projection(111/111) tests/bvbrc_genome_alignment_associations(30/30) tests/bvbrc_genome_alignment_bundle_contracts(22/22) tests/bvbrc_genome_alignment_bundle_resolution(0/0) tests/bvbrc_genome_alignment_input_contracts(50/50) tests/bvbrc_genome_alignment_inputs(70/70) tests/bvbrc_genome_alignment_retained_records(53/53) tests/bvbrc_genome_alignment_tool_info(0/4) tests/bvbrc_msa_provider_replay(1/1) tests/mauve_backbone_calculators(42/42) tests/mauve_backbone_formats(60/60) tests/mauve_bbcols_calculators(55/55) tests/mauve_v4_calculators(48/48) tests/mauve_v4_formats(29/29) tests/xmfa_calculators(80/80) tests/xmfa_coordinates(42/42) tests/xmfa_format_contracts(108/108) tests/xmfa_formats(109/109) tests/xmfa_sources(39/39)

### BV-BRC ComparativeSystems results

Files: bvbrc_comparative_systems_host_inputs[R] bvbrc_comparative_systems_bundle_adapter[L] bvbrc_comparative_systems_bundle_contracts[L] bvbrc_comparative_systems_bundle_projection[L] bvbrc_comparative_systems_bundle_resolution[L] bvbrc_comparative_systems_calculation_contracts[L] bvbrc_comparative_systems_calculators[L] bvbrc_comparative_systems_data_contracts[L] bvbrc_comparative_systems_data_inputs[L] bvbrc_comparative_systems_fact_contracts[L] bvbrc_comparative_systems_handoff_contracts[L] bvbrc_comparative_systems_native[L] bvbrc_comparative_systems_publication[L] bvbrc_comparative_systems_sheet[L] bvbrc_comparative_systems_sheet_contracts[L] bvbrc_comparative_systems_tool_info[L]

Tests (6 files, 285/285): tests/bvbrc_comparative_systems_bundle(73/73) tests/bvbrc_comparative_systems_data_inputs(51/51) tests/bvbrc_comparative_systems_native(50/50) tests/bvbrc_comparative_systems_projection(53/53) tests/bvbrc_comparative_systems_publication(15/15) tests/bvbrc_comparative_systems_sheet(43/43)

### BV-BRC FastqUtils report readers

Files: bvbrc_fastqutils_tool_info[G] bvbrc_fastqutils_bam_reader[L] bvbrc_fastqutils_bundle_adapter[L] bvbrc_fastqutils_calculators[L] bvbrc_fastqutils_composition[L] bvbrc_fastqutils_consistency[L] bvbrc_fastqutils_cutadapt_reader[L] bvbrc_fastqutils_fastq_reader[L] bvbrc_fastqutils_fastqc_reader[L] bvbrc_fastqutils_hostile_reader[L] bvbrc_fastqutils_json_tokens[L] bvbrc_fastqutils_mapping[L] bvbrc_fastqutils_native[L] bvbrc_fastqutils_pair_report_reader[L] bvbrc_fastqutils_quality[L] bvbrc_fastqutils_sam_reader[L] bvbrc_fastqutils_samstat_legacy[L] bvbrc_fastqutils_samstat_native[L] bvbrc_fastqutils_samstat_svg[L] bvbrc_fastqutils_sheet[L] bvbrc_fastqutils_sra_native[L] bvbrc_fastqutils_trim_reader[L]

Tests (12 files, 295/297): root/tests/fixtures/bvbrc_fastqutils/bundle/fixture_support(no row) tests/bvbrc_fastqutils_metadata(16/16) tests/bvbrc_fastqutils_provider(33/33) tests/bvbrc_fastqutils_report_calculators(20/20) tests/bvbrc_fastqutils_report_formats(31/31) tests/bvbrc_fastqutils_returns(1/1) tests/bvbrc_fastqutils_samstat_legacy(57/57) tests/bvbrc_fastqutils_samstat_mapping(60/60) tests/bvbrc_fastqutils_samstat_svg(45/45) tests/bvbrc_fastqutils_sequence_formats(1/1) tests/bvbrc_fastqutils_sra(26/26) tests/bvbrc_fastqutils_tool_info(5/7)

### BV-BRC annotation, assembly, HA subtype, subspecies and variation results; BV-BRC tool information

Files: bvbrc_annotation_bundle_adapter[L] bvbrc_annotation_contracts[L] bvbrc_annotation_native[L] bvbrc_assembly_bundle_adapter[L] bvbrc_assembly_native[L] bvbrc_homology_tool_info[L] bvbrc_influenza_ha_bundle_adapter[L] bvbrc_influenza_ha_native[L] bvbrc_phylogeny_tool_info[L] bvbrc_proteome_tool_info[L] bvbrc_subspecies_bundle_adapter[L] bvbrc_subspecies_native[L] bvbrc_variation_bundle_adapter[L]

Tests (7 files, 115/117): root/a106/tests/annotation_bundle_fixtures(no row) root/tests/bvbrc_phylogeny_tool_info(66/67) tests/bvbrc_annotation_bundle_adapter(0/0) tests/bvbrc_annotation_native(0/0) tests/bvbrc_application_returns(21/21) tests/bvbrc_proteome_directional_tool_info(7/7) tests/bvbrc_proteome_tool_info(21/22)

### BV-BRC application definitions

Files: ComparativeSystems[SS] ComprehensiveGenomeAnalysis[SS] CoreGenomeMLST[SS] FastqUtils[SS] GenomeAlignment[SS] GenomeAnnotation[SS] GenomeAssembly2[SS] InfluenzaHASubtypeConversion[SS] MetagenomeBinning[SS] MetagenomicReadMapping[SS] SARS2Assembly[SS] SubspeciesClassification[SS] TaxonomicClassification[SS] Variation[SS] ViralAssembly[SS] WholeGenomeSNPAnalysis[SS]

Tests (1 file, 55/55): tests/bvbrc_application_definitions(55/55)

### BV-BRC AppService and Data host steps

Files: bvbrc_application_value_identity[G] bvbrc_appservice_preparation[G] bvbrc_appservice_publication_validation[G] bvbrc_appservice_response_decoding[G] bvbrc_appservice_custody[R] bvbrc_appservice_host[R] bvbrc_appservice_monitor[R] bvbrc_appservice_publication[R] bvbrc_data_host[R] bvbrc_minhash_host[R]

Tests (11 files, 328/377): tests/bvbrc_application_returns(21/21) tests/bvbrc_appservice_compact_custody(0/30) tests/bvbrc_appservice_custody(77/78) tests/bvbrc_appservice_inputs(27/27) tests/bvbrc_appservice_request_content(12/12) tests/bvbrc_appservice_supplied_contents(12/12) tests/bvbrc_fastqutils_returns(1/1) tests/bvbrc_proteome_directional_publication(7/10) tests/episode_received_report_prefix(19/19) tests/molecular_result_facts(39/50) tests/molecular_sequence_input_bindings(113/117)

### Flux balance analysis

Files: flux_balance_execution_inputs[R] flux_balance_assignment_identity[L] flux_balance_model_tools[L] flux_balance_native_capture_contracts[L] flux_balance_operands[L] flux_balance_ordinary[L] flux_balance_readers[L] flux_balance_request_binding[L] flux_balance_result_contracts[L] flux_balance_result_receipts[L] flux_balance_result_selection[L] flux_balance_result_views[L] flux_balance_return_views[L] flux_balance_sheet[L] flux_balance_tools[L] flux_balance_worker_contracts[L] native_flux_balance_capture[L] native_flux_balance_preparation[L] native_flux_balance_tool_info[L] native_flux_balance_results[R]

Tests (13 files, 543/552): tests/flux_balance_core_679(48/48) tests/flux_balance_evidence_contracts_687(95/95) tests/flux_balance_evidence_parsing_689(60/60) tests/flux_balance_model_tools(29/29) tests/flux_balance_model_views(70/70) tests/flux_balance_native_capture_697(41/41) tests/flux_balance_ordinary(3/3) tests/flux_balance_ordinary_returns(10/10) tests/flux_balance_parser_recovery_686(28/28) tests/flux_balance_partial_terms_683(9/9) tests/flux_balance_prior_sources_692(41/41) tests/flux_balance_readers_680(51/51) tests/macs2_peak_execution(58/67)

### Fluorescence and flow cytometry

Files: fluorescence_result_observation[R] fluorescence_context_views[L] fluorescence_event_calculations[L] fluorescence_event_preparation[L] fluorescence_event_readers[L] fluorescence_event_sheet[L] fluorescence_execution_information[L] fluorescence_fcs_reader[L] fluorescence_native_reports[L] fluorescence_operands[L] fluorescence_preparation_readers[L] fluorescence_prepared_results[L] fluorescence_result_views[L] fluorescence_result_worker[L] fluorescence_tool_guidance[L] native_fluorescence_capture[L] native_fluorescence_driver[L] native_fluorescence_local[L] native_fluorescence_observations[L] native_fluorescence_preparation[L] native_fluorescence_prepared_driver[L] native_fluorescence_tool_info[L] original_fluorescence_execution_information[L] original_fluorescence_observation[L] original_fluorescence_result_receipts[L] original_native_fluorescence_results[L] native_fluorescence_results[R]

Tests (20 files, 631/665): root/tests/fluorescence_episode_routing(22/37) tests/fluorescence_context_views(10/10) tests/fluorescence_event_calculations(31/31) tests/fluorescence_event_readers(57/57) tests/fluorescence_event_sheet(66/66) tests/fluorescence_fcs_reader(81/81) tests/fluorescence_local_routing(62/62) tests/fluorescence_native_reports(77/77) tests/fluorescence_partial_primary(12/12) tests/fluorescence_prepared_bindings(5/5) tests/fluorescence_prepared_core(49/49) tests/fluorescence_result_contracts(24/24) tests/fluorescence_result_receipts(18/18) tests/fluorescence_result_worker(18/18) tests/fluorescence_returns(14/14) tests/fluorescence_tool_info(6/6) tests/fluorescence_worker_preparation(1/20) tests/native_fluorescence_capture(11/11) tests/native_fluorescence_contracts(52/52) tests/native_fluorescence_driver(15/15)

### Genomic interval overlap

Files: genomic_overlap_calculations[L] genomic_overlap_execution_information[L] genomic_overlap_operands[L] genomic_overlap_presentation[L] genomic_overlap_result_views[L] genomic_overlap_result_worker[L] genomic_overlap_return_views[L] native_genomic_overlap_capture[L] native_genomic_overlap_job_schema[L] native_genomic_overlap_local[L] native_genomic_overlap_observations[L] native_genomic_overlap_preparation[L] native_genomic_overlap_tool_info[L] native_genomic_overlap_results[R]

Tests (4 files, 154/154): tests/genomic_overlap_analytic_capture_loss(50/50) tests/genomic_overlap_calculations(18/18) tests/genomic_overlap_operands(73/73) tests/genomic_overlap_return_views(13/13)

### Chromatin interaction

Files: chromatin_interaction_operands[R] chromatin_interaction_result_receipts[R] chromatin_interaction_execution_information[L] chromatin_interaction_presentation[L] chromatin_result_completed_receipts[L] chromatin_result_native_receipts[L] chromatin_result_receipt_values[L] chromatin_result_scientific_receipts[L] chromatin_result_worker_receipts[L] native_chromatin_interaction_capture[L] native_chromatin_interaction_local[L] native_chromatin_interaction_observations[L] native_chromatin_interaction_preparation[L] native_chromatin_interaction_tool_info[L] native_chromatin_interaction_results[R]

Tests (1 files, 121/121): tests/chromatin_interaction_operands(121/121)

### ATAC differential accessibility

Files: atac_differential_operands[R] atac_differential_result_receipts[R] atac_differential_execution_information[L] atac_differential_presentation[L] atac_result_completed_receipts[L] atac_result_native_receipts[L] atac_result_receipt_values[L] atac_result_scientific_receipts[L] atac_result_worker_receipts[L] native_atac_differential_capture[LG] native_atac_differential_local[L] native_atac_differential_preparation[L] native_atac_differential_tool_info[L] native_atac_differential_results[R]

Tests (5 files, 93/120): root/tests/atac_differential_execution_integration(10/15) root/tests/atac_differential_result_receipts(35/55) tests/atac_differential_operands(21/21) tests/atac_differential_result_preparation(2/4) tests/atac_differential_result_worker(25/25)

### Expression NMF

Files: expression_nmf_operands[R] expression_nmf_calculations[L] expression_nmf_execution_information[L] expression_nmf_presentation[L] expression_nmf_result_worker[L] expression_nmf_selector_schema[L] native_expression_nmf_capture[L] native_expression_nmf_job_schema[L] native_expression_nmf_preparation[L] native_expression_nmf_tool_info[L] native_expression_nmf_results[R]

Tests (2 files, 32/38): root/tests/expression_nmf_execution_integration(0/5) tests/expression_nmf_numerics(32/33)

### HOMER motif enrichment and TF binding-site scoring

Files: homer_motif_contracts[LG] homer_motif_measurements[LG] homer_motif_received_values[L] homer_motif_result_contracts[LG] homer_motif_tools[LG] homer_tf_worker_ports[L] native_homer_execution[LG] native_homer_worker[LG] tf_binding_driver[LG] tf_binding_measurements[LG] tf_binding_received_values[L] tf_binding_result_contracts[LG] tf_binding_result_worker[LG] tf_binding_tools[LG]

Tests (8 files, 309/320): root/tests/tf_binding_tools(24/24) tests/homer_motif_measurements(65/65) tests/molecular_result_facts(39/50) tests/native_homer_execution(45/45) tests/tf_binding_driver(24/24) tests/tf_binding_measurements(46/46) tests/tf_binding_result_contracts(48/48) tests/tf_binding_result_worker(18/18)

### MACS2 peaks and LUMPY structural variants

Files: lumpy_assignment_identity[L] lumpy_request_binding[L] macs2_peak_assignment_identity[L] macs2_peak_presentation[L] macs2_peak_request_binding[LG] macs2_peak_tools[LG] native_lumpy_execution[L] native_lumpy_host[L] native_lumpy_job_schema[L] native_lumpy_observations[L] native_lumpy_software[L]

Tests (5 files, 173/191): root/tests/lumpy_execution_registration(31/32) root/tests/lumpy_request_binding(39/39) root/tests/lumpy_resource_workflow(0/1) root/tests/native_lumpy_execution(45/52) tests/macs2_peak_execution(58/67)

### Infernal model preparation, Infernal and HMMER result custody, PHMMER

Files: infernal_result_presentation[R] homology_result_coverage[L] homology_result_publication[L] infernal_native_result_views[L] infernal_preparation_artifact_declarations[L] infernal_preparation_artifacts[L] infernal_preparation_calculation_declarations[L] infernal_preparation_calculations[L] infernal_preparation_emission[L] infernal_preparation_emission_calculations[L] infernal_preparation_emission_check_declarations[L] infernal_preparation_emission_declarations[L] infernal_preparation_model_declarations[L] infernal_preparation_models[L] infernal_preparation_result_views[L] infernal_preparation_statistic_declarations[L] infernal_preparation_statistics[L] native_hmmer_acquisition[L] native_hmmer_preparation_failure_views[L] native_hmmer_preparation_result_publication[L] native_infernal_acquisition[L] native_infernal_preparation_acquisition[L] native_infernal_preparation_failure_views[L] native_infernal_preparation_result_publication[L] native_infernal_preparation_result_worker[L] native_infernal_preparation_worker[L] native_infernal_result_publication[L] native_phmmer_inputs[L] native_phmmer_parser[L] native_phmmer_preparation[L] native_profile_presentation[L] phmmer_format[L] phmmer_grading_worker[L] native_hmmer_results[R] native_infernal_results[R]

Tests (16 files, 460/481): root/tests/native_infernal_preparation_reference_visibility(0/21) tests/infernal_preparation_artifacts(24/24) tests/infernal_preparation_calculations(29/29) tests/infernal_preparation_emission(49/49) tests/infernal_preparation_emission_calculations(25/25) tests/infernal_preparation_models(22/22) tests/infernal_preparation_result_views(17/17) tests/infernal_preparation_statistics(32/32) tests/infernal_result_presentation(21/21) tests/native_infernal_acquisition(95/95) tests/native_infernal_preparation_acquisition(90/90) tests/native_infernal_preparation_result_publication(1/1) tests/native_infernal_preparation_result_worker(1/1) tests/native_infernal_preparation_worker(10/10) tests/native_infernal_publication(1/1) tests/native_infernal_returns(43/43)

### BLAST database result acquisition and publication

Files: native_blast_database_acquisition[L] native_blast_database_result_publication[L] native_blast_masking_results[L] native_blast_standard_database_acquisition[L] native_blast_standard_database_result_publication[L] native_blast_utility_results[L] native_blast_database_results[R] native_blast_results[R] native_blast_standard_database_results[R]

Tests: no HEAD test file imports these modules directly.

### Restriction mapping

Files: restriction_mapping_action_records[L] restriction_mapping_bound_contracts[L] restriction_mapping_inputs[L] restriction_mapping_jobs[L] restriction_mapping_publication[L] restriction_mapping_references[L] restriction_mapping_registry[L] restriction_mapping_selection[L] restriction_mapping_tool_info[L]

Tests (2 files, 91/91): tests/restriction_mapping_action_records_729(53/53) tests/restriction_public_tool(38/38)

### RNA structure results and comparison

Files: native_rna_structure_acquisition[L] native_rna_structure_job_schema[L] native_rna_structure_tool_info[L] rna_comparison_result_records[L] rna_result_operand_authority[L] rna_result_preparation[L] rna_result_publication[L] rna_result_records[L] rna_result_reference_access[L] rna_structure_comparison_calculations[L] rna_structure_comparison_presentation[L] rna_structure_comparison_publication[L] rna_structure_comparison_worker[L] rna_structure_presentation[L] rna_structure_scan_calculations[L] native_rna_structure_results[R] rna_comparison_result_custody[R] rna_comparison_result_facts[R] rna_result_custody[R] rna_result_facts[R] rna_structure_comparison_operands[R] rna_structure_comparison_prompt[R] rna_structure_comparison_results[R] rna_structure_prompt[R]

Tests (2 files, 91/92): tests/native_rna_structure_contracts(40/40) tests/rna_structure_presentation(51/52)

### Protein conservation and protein phylogeny tools

Files: protein_conservation_publication[L] protein_conservation_result_worker[L] protein_conservation_tools[L] protein_phylogeny_publication[L] protein_phylogeny_result_worker[L] protein_phylogeny_tools[L]

Tests (4 files, 141/144): tests/protein_conservation_publication(19/19) tests/protein_conservation_result_worker(54/54) tests/protein_conservation_tools(18/18) tests/protein_phylogeny_native_and_retained(50/53)

### Protein structure result custody

Files: native_protein_structure_job_schema[L] protein_structure_execution_information[L] protein_structure_projection_publication[L] protein_structure_return_values[L] native_protein_structure_results[R] protein_structure_report_boundary[R] protein_structure_result_acquisition[R] protein_structure_result_publication[R] protein_structure_result_receipts[R] protein_structure_result_science[R] protein_structure_return_facts[R] protein_structure_return_operands[R] protein_structure_return_visibility[R]

Tests: no HEAD test file imports these modules directly.

### Ordinary molecular measurement and sequence tools

Files: api_sequence_support[G] arsenic_speciation_tools[GL] arsenic_received_values[L] esm_embedding_received_values[L] esm_gene_embedding_publication[LG] esm_gene_embedding_tools[LG] esm_worker_ports[L] glycosylation_received_values[L] itc_tools[L] liftover_tools[L] molecular_action_custody[L] molecular_provenance_display[L] molecular_publication_custody[L] molecular_publication_reader[L] molecular_result_facts[LG] molecular_result_recognition[L] molecular_sequence_input_bindings[LG] molecular_sequence_tools[LG] molecular_value_presentation[L] molecular_worker_ports[L] ordinary_scientific_worker_ports[L] physical_measurement_worker[L] physical_measurement_worker_ports[L] primer_received_context[L] protease_kinetics_result_contracts[LG] protease_kinetics_tools[LG] protease_received_context[L] protein_disorder_received_values[L] protein_disorder_tools[LG] received_molecular_capabilities[L] reference_edit_outcome_tools[LG] sequence_analysis_worker[L] sequence_support_contracts[LG] sequence_support_publication[LG] somatic_variant_driver[LG] somatic_variant_publication[LG] somatic_variant_received_values[L] somatic_variant_result_worker[LG] somatic_variant_tools[LG] vcf_received_values[L] vcf_result_tools[LG] molecular_result_actions[R] molecular_result_custody[R] molecular_result_execution[R] molecular_result_original_evidence[R] molecular_result_publication[R] molecular_result_saved[R] molecular_result_supplied[R] molecular_result_values[R] molecular_sequence_results[R] itc_binding_presentation[G] molecular_measurement_tools[G] molecular_sequence_execution_driver[G] molecular_sequence_ordinary[G] molecular_sequence_result_worker[G]

Tests (17 files, 516/572): root/tests/addgene_selected_process_path(0/1) root/tests/lumpy_resource_workflow(0/1) root/tests/tf_binding_tools(24/24) tests/bvbrc_data_recovery(10/33) tests/liftover_tool(0/1) tests/molecular_publication_custody(48/57) tests/molecular_result_facts(39/50) tests/molecular_sequence_input_bindings(113/117) tests/molecular_sequence_ordinary(42/42) tests/molecular_sequence_received_source(35/35) tests/native_homer_execution(45/45) tests/protease_kinetics_result_contracts(88/88) tests/reference_edit_outcome_tools(19/24) tests/sequence_support_publication(23/23) tests/somatic_variant_native(21/21) tests/tf_binding_shared_authority(9/9) tests/vcf_result_workflow(0/1)

### Literature structure and reaction evidence

Files: literature_reaction_calculations[L] literature_reaction_inputs[L] literature_reaction_meanings[L] literature_reaction_native_inputs[L] literature_reaction_native_return_contracts[L] literature_reaction_return_contracts[L] literature_reaction_source_contracts[L] literature_reaction_types[L] literature_structure_calculations[L] literature_structure_input_contracts[L] literature_structure_inputs[L] literature_structure_return_contracts[L] literature_structure_types[L] literature_reaction_native_storage[R] literature_reaction_source[R] literature_reaction_storage[R] literature_structure_storage[R]

Tests (2 files, 26/26): tests/reaction_source_witness_labels(8/8) tests/source_literal_display_labels(18/18)

### Literature readers

Files: literature_partner_operand_information[L] literature_product_partition_number[L] literature_source_inputs[L]

Tests: no HEAD test file imports these modules directly.

### HMMER web API operations

Files: api_hmmer_handoff_records[R] api_hmmer_operations[R] api_hmmer_progress[R] api_hmmer_protocol[R] api_hmmer_result_records[R]

Tests: no HEAD test file imports these modules directly.

### Enrichr service

Files: api_enrichr[G] api_enrichr_host[G] enrichr_publication_metadata[R]

Tests (3 files, 138/138): root/tests/root_enrichr_publication_metadata(35/35) tests/enrichr_api_service(48/48) tests/enrichr_host(55/55)

### Addgene sequence facts

Files: addgene_sequence_facts[GL]

Tests (1 files, 0/1): root/tests/addgene_selected_process_path(0/1)

### UniProt selected-field projection

Files: uniprot_return_projection[L]

Tests (1 files, 58/58): tests/uniprot_return_projection(58/58)

### Alignment-site projections

Files: alignment_result_presentation[L] alignment_site_projection_requests[L]

Tests (3 files, 97/116): tests/alignment_result_presentation(2/2) tests/alignment_site_action_records(42/61) tests/alignment_site_returns(53/53)

### A107/A110 component reports

Files: component_axis_cell_receipts[L] component_native_source_snapshot[L] component_native_tool_contracts[L] component_received_reports[L]

Tests: no HEAD test file imports these modules directly.

### HPC calendar scheduler

Files: hpc_scheduler[G]

Tests: no HEAD test file imports these modules directly.

### Native operation lock

Files: native_operation_lock[G]

Tests (1 files, 6/6): root/tests/shared_native_operation_lock(6/6)

### Execution progress observation

Files: execution_progress[L]

Tests (4 files, 98/115): root/tests/api_rfam_service(44/45) root/tests/fluorescence_episode_routing(22/37) root/tests/lumpy_execution_registration(31/32) tests/protein_structure_execution_information(1/1)

### Terminal and local file capture

Files: local_file_capture_results[R] terminal_native_file_capture[RG]

Tests (5 files, 156/174): root/tests/lumpy_workflow_checks(no row) root/tests/execution_local_file_sources(67/74) root/tests/lumpy_execution_registration(31/32) root/tests/lumpy_resource_workflow(0/1) tests/macs2_peak_execution(58/67)
