# Current application tool inventory — 2026-10-24

The existing application declares **54 ordinary operations** (55 with optional timing estimation) and **61 resource execution variants**: 27 local, 16 HPC, 18 API. The combined four-field map has **115 name/resource rows** and **96 unique names**. Thirteen ordinary literature/document operations are excluded here, leaving **41 ordinary non-literature operations**. Complete names, descriptions, resources, instructions, schemas and evidence are in [current.json](current.json).

The 61 execution rows comprise **36 generic infrastructure variants**, **20 HMMER/phmmer/BLAST lifecycle variants**, and **5 UniProt/BV-BRC data retrieval variants**. Shell, file, status, prepare, collect and progress operations do not imply independent scientific graders.

| Scientific algorithm family | Actual interface/resource | Existing grader and deployment limit |
| --- | --- | --- |
| Biopython pairwise alignment | `sequence.align`, `reads.align`; local | Native scores/identity/coverage exist; no tool sheet. Biopython 1.88 installed. Aurora proves only its earlier manual global-alignment test. |
| Prodigal | `genes.predict`; local Pyrodigal meta/single | Native CDS/confidence/score; no tool sheet. Pyrodigal 3.7.1 installed. |
| minimap2 | `reads.map`; local, six presets | PAF/cg/cs reader; no tool sheet. Binary 2.31-r1302 exists; executable is not selected by package/default local config. |
| Infernal cmsearch | `rna.cmsearch`; local | fmt3/native source reader; no tool sheet. Binary 1.1.5 exists; requires explicit executable and selected CM. |
| HMMER phmmer | local `homology.*`; API `api.hmmer.*` | Two native formats/readers; no tool sheet. Local pinned executable/reference FASTA exist. |
| HMMER hmmscan | `api.hmmer.*`; API | API domain/coverage reader; no tool sheet. Local binary exists but no dedicated local callable. |
| Rfam batch cmscan | `public.rfam.search/collect`; API | Native family/score/coordinate reader; no tool sheet. Historical calibration paths are missing here. |
| BLAST | five programs through `public.blast.*`/`api.blast.*`; local test helper; HPC formats | **Two standalone sheets implemented**, with native and metadata readers. No production grader binding. Actual local pairwise test exists; saved live API checkpoint is WAITING/blocked; HPC execution unverified. |

Additional deterministic measurements/preparations are sequence/read composition, translation, sequence views and translation-code lookup. Data readers include alignment sites/BLAST HSPs, GenBank neighborhoods, material FASTA/FASTQ/GenBank intake, original-read libraries, source/record windows, UniProt, NCBI sequence/search/taxonomy, Rfam models, Rhea, ChEBI, and BV-BRC genome/feature/protein-family pages. They retain source facts; transport alone is not a numerical scoring sheet.

The current BLAST function boundary is [blast_graders.py](../../gene_annotation_episode/blast_graders.py) → native readers → pairwise/database sheet builders → replaceable database calculator. It is only called by its CLI/tests/verification helpers in the inspected paths. Ordinary/API result publication retains data but never calls this facade. No other native algorithm has a dedicated sheet/grader binding; W05 remains separate.

Publication runs through [tool_information.py](../../gene_annotation_episode/tool_information.py) (`make_tool_info`, `workflow_execution_catalogs`), [scientific_tool_library.py](../../gene_annotation_episode/scientific_tool_library.py) (run-frozen v2 rows/contracts), and [scientific_process_setup.py](../../gene_annotation_episode/scientific_process_setup.py). There are 3 general manuals and 6 launch manuals. Current manual names have declarations, but reading a manual grants no execution capability. Generic fallback instruction text is not a full algorithm manual.

**Ownership and selection:** the 61 execution rows belong to launch/resource/results/monitor owners. Keeping them out of direct scientific/root catalogs is correct. A pure metadata diagnostic reproduces a narrower inconsistency: runtime literal `process.tools("BLAST")` can return `{name: "api.blast.submit", resources: "api"}` without receiver filtering; scientific-child materialization then rejects it with `scientific_tool_contract_changed:api.blast.submit:api`. Semantic retrieval already filters. The proper integration is selected information → fixed launch/service assignment → resource child execution; it must preserve root restrictions.

No numeric catalog truncation was found in the current tool-map loader or retriever. Search/manual pages expose continuation; result previews (12 rows, or 6 for chemistry) are bounded views of retained data. Historical T01–T13 research bundles are background, not actual tools. Installed extra Infernal/HMMER/BLAST executables and PyHMMER do not acquire bindings merely by being present.

**Resources:** local package versions, binary paths, installed skill-client paths and explicit-config gaps are recorded in JSON. Aurora inventory is the retained [WORKSPACE_DIRECTORY.md](../../verification/aurora_bioinformatics_2026-10-22_001/WORKSPACE_DIRECTORY.md) and execution receipt: Gentner/Biopython returned 17 pairwise comparisons on 2026-10-22. It proves no other HPC algorithm/database or current authentication. Polaris has not been exercised; Spark remains a separate non-HPC host with unknown hostname in retained direction. No concrete deployment inventory for either was located.

**Verification performed:** source/schema/manifest inspection, package/file metadata reads, and the pure resolver diagnostic only. No scientific tool, network/API request, SSH/authentication, native job, model episode or test suite was run. Only `current.*` inventory artifacts were written. Existing source, historical receipts, scoring formulas, prompts and execution behavior were unchanged.
