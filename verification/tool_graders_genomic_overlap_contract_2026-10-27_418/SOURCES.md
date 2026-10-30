# Source and inspection record

Planning-only evidence for `B-L123-analyze_genomic_region_overlap`, 2026-10-27.
The companion [contract](CONTRACT.md) is a proposed boundary for root review.
No row status or alias was edited.

## Controlling instructions read

- Full immutable user goal attachment at
  `/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt`;
  SHA-256 `11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
- `AGENTS.md`, `docs/EPISODE_STRUCTURE.md`,
  `docs/TIME_AWARE_ESTIMATION.md`, `docs/TASK_AND_STEERING.md`,
  `docs/TOOL_KNOWLEDGE.md`, `docs/PRACTICAL_EXECUTION.md`,
  `docs/PRACTICAL_EXECUTION_CONTRACT_2026-10-22_001.md`, and
  `docs/TOOL_GRADER_GOAL_AND_PRINCIPLES_2026-10-24_001.md`.
- Current relevant rows in both
  `research/tool_grader_inventory_2026-10-24/WORK_STATUS.json` and
  `research/tool_grader_goal_2026-10-24/WORK_STATUS.json`;
  fixed mapping in `research/tool_grader_goal_2026-10-24/SOURCE_ALIASES.json`.

The objective and all sixteen principles were reread verbatim after the
substantial primary-source examination and immediately before the contract was
written. This authoring discipline is not a runtime gate or an episode action.

## Native and format authorities

1. [bedtools intersect documentation](https://bedtools.readthedocs.io/en/latest/content/tools/intersect.html).
   The primary manual specifies A+B+overlap-width output for `-wo`, original A
   occurrence reporting for `-u`, fraction/strand options, and sorted-input
   requirements. Its documented default fraction is 1e-9.
2. [bedtools general usage and BED format](https://bedtools.readthedocs.io/en/latest/content/general-usage.html).
   The primary manual defines tab-delimited BED fields and start/end semantics;
   BED12 block handling requires an explicit relevant mode/option.
3. [bedtools Jaccard documentation](https://bedtools.readthedocs.io/en/latest/content/tools/jaccard.html).
   Inspected for the interval intersection/union meaning. This contract defines
   its denominator algebra explicitly and does not parse or depend on native
   `jaccard` output.
4. [bedtools v2.31.1 ContextIntersect.cpp](https://github.com/arq5x/bedtools2/blob/v2.31.1/src/utils/Contexts/ContextIntersect.cpp).
   `isValidState` requires explicit fractions in (0,1]; fraction options and
   incompatible output flags have native validation.
5. [bedtools v2.31.1 Record.cpp](https://github.com/arq5x/bedtools2/blob/v2.31.1/src/utils/FileRecordTools/Records/Record.cpp).
   `sameChromIntersects` compares positive overlap fractions; zero-length records
   have a separate coordinate expansion path. These explain the proposed tiny
   positive native fraction operands and rejection of silently expanded empty
   spans. This is source reasoning, not an observed local executable test.
6. [bedtools v2.31.1 BedtoolsTypes.h](https://github.com/arq5x/bedtools2/blob/v2.31.1/src/utils/general/BedtoolsTypes.h).
   The native coordinate type is signed 64-bit `CHRPOS`.

The deployed implementation must retain its actual version evidence and test
the proposed options. Website/source version identifiers do not establish that
version is installed in this workspace.

## Local source and dependency observations

Full original function:
`reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/genomics.py::analyze_genomic_region_overlap`,
beginning at line 1965 and ending immediately before
`generate_embeddings_with_state`. The whole source file's inspected SHA-256 was
`74714f05594d4655e946107628114339452cab8eecbb4005feccea49be2906c5`.

Read-only filesystem/PATH checks found:

| Item | Actual observation | Limit |
| --- | --- | --- |
| Biomni | Source function and `biomni-0.0.8.dist-info/METADATA` present | Does not prove successful import or executable dependencies. |
| pandas | `pandas-2.3.3.dist-info/METADATA` present | No import or numerical execution attempted. |
| pybedtools | No package directory/metadata in the inspected reference environment | No claim about another environment. |
| bedtools/intersectBed | No command found in the inspected shell PATH; no corresponding executable in reference `.venv/bin` | No system-wide or remote installation claim. |

No installation, algorithm execution, API experiment, remote login or scheduler
submission occurred. The contract replaces a lossy wrapper with a proposed
direct native binding; its live prerequisites remain unfinished.

## Integration paths actually examined

These are inspected source consumers, not verified deployed paths:

- Complete `ResourceEpisodes` class through its credit projection; this older
  abstraction is not substituted for the newer explicit execution family.
- `ExecutionEpisodes`: constructor and configuration, request schemas and
  validation, launch/resource selection and prepare/init paths, scientific tool
  publication, role instructions/context, concrete native selector/catalog/
  execute dispatch, the full generic native-window acquisition and source
  validation functions, fact-source declarations and facts, admission and
  forwarding entry points, practical completion and credit consumers. Existing
  family-specific implementations were inspected only where relevant; this
  task does not claim a full audit of all 2,000+ lines or all unrelated services.
- Complete `ExecutionServiceFactory` and `PracticalServiceFactory` modules;
  complete `PracticalResourceEpisodes` class; complete `LocalPracticalOperations`
  local execution, observation and read paths; practical assignment schema and
  complete `validate_assignment` consumer.
- Complete `local_jobs.py` and `native_lifecycle.py`; lifecycle enforces memory,
  zero swap, caller wall setting and scratch policy independently of episode
  lifetime. No limits were exercised in this planning task.
- `ExecutionTargetReader._native`, `read_target`, `_qualified`,
  `_native_identity`, `usable_handoff`, `returnable_handoff`, `observe_target`,
  `read_file`, and constructor; native source/request/attempt relationships are
  the reuse boundary.
- Complete `native_rna_structure_local.py` as an existing reserve/read-plan
  example; complete `native_hmmer_acquisition.py` as an existing sealed-manifest
  and streamed capture example. They remain scientific-family-specific; their
  tool semantics are not imported into overlap mathematics.
- Complete `materials.artifact_file` / `artifact_path` and `Store.artifact` /
  `get_artifact` were read. Streaming file capture already exists and should be
  reused instead of invented again.
- `ScientificToolLibrary` profile/information construction and
  `resolve_tool_info` / `resolve_invocations` consumers;
  `ScientificProcessEpisodes._tool_resolution_for`, `_tool_resolution` and
  catalog direct-versus-commission selection. Existing three-slot construction
  and commission-only resource ownership are preserved.

BLAST separation reference: `blast_grading_inputs.parse_blast_json` was read as
a retained-native-data parser; `blast_pairwise_grader` supplies explicit geometry,
union and missing-data examples; `blast_database_grader.calculate_database_probabilities`
was read in full as a saved-sheet, explicit-parameter calculator. The overlap
contract imports none of its database/function kernels, priors or scores.
No BLAST file was modified. Some initial large read responses were truncated;
relevant complete functions or sections were reread in bounded chunks rather
than treating the truncated output as a complete review.

## Evidence classification

| Evidence class | This task |
| --- | --- |
| Source inspection | Yes, bounded to the paths listed above. |
| Primary format/source inspection | Yes, linked above. |
| Hand-worked numerical examples | Yes, synthetic and explicitly labeled in CONTRACT.md. |
| Implemented parser or calculator | No. |
| Automated tests executed | No. |
| Retained live native overlap output | No. |
| Live local scientific execution | No. |
| Live HPC/API execution | No. |
| Actual episode-path communication verification | No. |

Outstanding implementation and verification are listed in the contract; none
was recategorized as completion by this planning record.

## Additive concrete-record and native-evidence follow-up

Root requested exact records after reviewing the first contract. Added
`DATA_CONTRACT.json`, `WORKED_EXAMPLE.json` and `HANDOFF.md`, all planning-only.
The shared packet419 contract was read in full and its exact NativeFileIdentity,
NativeFileDeclaration and NativeFileCapture records copied as interface
definitions. Media type is not part of file identity. No generic operation
registry or second copier is adopted. G1 pure records and G3 projection
ownership are now explicit, including required nullability and fixed per-tool
selected measurement fields. There is no production evidence_class field.

Document-only checks use Python JSON/JSON Schema validation and SHA-256 of the
synthetic strings/canonical saved-sheet JSON. They do not execute a scientific
algorithm, production parser/calculator, native capture or episode, and are not
reported as tool verification. Their final result is retained in
`DOCUMENT_VALIDATION.json`. A first environment lookup found `python` absent;
`python3` was used for these small metadata checks. No package was installed by
this planning agent.

Root subsequently supplied actual native evidence. These complete files were
read rather than treating the message as native proof:

- `software/bedtools/ubuntu-2.31.1+dfsg-2/SOFTWARE.json`: Ubuntu package hash
  `2be06af20009e942be1b332b54220cee397ecfe51c24578bb586b584a3a30b5e`, executable
  hash `b6c6e44b79180f0c9f64f916010c71bcd44baf81e5abe71b63f19aa9d4bc9fb6`,
  observed `bedtools v2.31.1`.
- `software/bedtools/ubuntu-2.31.1+dfsg-2/long_interval_default_fraction.CHECK.json`:
  the native output contains the 1-bp row although the initial expected output
  was empty. This disproves this packet's original default-fraction claim.
- `verification/tool_graders_genomic_overlap_native_2026-10-27_421/run002/work/NATIVE_CHECKS.json`:
  seven plain `intersect -wo -sorted` cases with exact native output matches and
  returncode 0, including overlapping sets, duplicate occurrences, touching
  endpoints, distinct chromosomes, long interval one bp and signed-64-bit
  endpoint one bp. Input/source pins are recorded unchanged. Root reports the
  enforced local_jobs 20 GiB RAM / 4 GiB scratch / zero swap / no wall policy.

CONTRACT section 12 corrects the earlier claim additively and adopts plain
`-wo -sorted` without `-f/-F` for this pinned build. Its scientific numerical
meanings do not change. Native execution belongs to root's packet421; this
planning agent ran no native job. The earlier table records the initial state;
retained native evidence has now been inspected, while parser/calculator and
episode-path verification remain unperformed by this task. The immutable
objective and all sixteen principles were reread verbatim after this native
evidence review and before the final data-contract freeze.
