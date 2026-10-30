# Gene annotation episode

Python package for scoped annotation investigations with typed scientific state,
retained evidence, native tool execution and the shared `method_loop` runtime.

## Usage

Run CLI help from the repository root:

```bash
.venv/bin/python -m gene_annotation_episode --help
.venv/bin/python -m gene_annotation_episode.case_execution --help
```

The general CLI provides `init`, `add-material`, `status`, `capabilities`, `tool`,
`run`, `artifact` and `export`. The case harness accepts explicit caller resources,
model configuration, scoring policy and parameters. Local tool paths are configured
in [resources/local-tools.toml](resources/local-tools.toml).

## Reference

| Area | Documentation |
| --- | --- |
| State | [Scientific state](docs/STATE_API.md), [queries](docs/STATE_QUERY.md), [reference resolution](docs/REFERENCE_RESOLUTION.md) |
| Runtime | [Runtime bindings](docs/RUNTIME_BINDING.md), [credit inspection](docs/EPISODE_CREDIT.md), [yield reports](docs/EPISODE_YIELD_REPORTS.md), [history restoration](docs/BOUNDED_RESTORATION.md) |
| Execution | [Case execution](docs/CASE_EXECUTION.md), [execution services](docs/EXECUTION_WIRING.md), [local job limits](docs/LOCAL_JOB_LIMITS.md), [execution statistics](docs/NATIVE_EXECUTION_STATISTICS.md) |
| Instructions | [Tool instruction retrieval](docs/TOOL_KNOWLEDGE.md), [launch instruction retrieval](docs/LAUNCH_INSTRUCTIONS.md) |
| Materials | [Material intake](docs/MATERIAL_INTAKE.md), [GenBank](docs/GENBANK_INTAKE.md), [packed reads](docs/PACKED_MATERIALS.md), [read-library targets](docs/READ_LIBRARY_TARGETS.md) |
| Evidence | [Evidence access](docs/EVIDENCE_ACCESS.md), [BLAST sheets](docs/BLAST_TOOL_GRADERS.md), [RNA](docs/RNA_EVIDENCE.md), [images](docs/IMAGE_EVIDENCE.md), [spreadsheets](docs/SPREADSHEET_SOURCES.md) |
| Output | [Interpretation records](docs/INTERPRETATION_BASIS.md), [exports](docs/EXPORT.md) |

## Repository contents

- `gene_annotation_episode/` contains application code and functional instruction libraries.
- `method_loop/` contains the shared iterative runtime.
- `tests/` contains automated checks and fixtures.
- `cases/` contains retained case inputs and execution evidence.
- `verification/` contains retained artifacts, numerical examples, receipts and verification results.
- `research/` contains source research, numerical sheets and machine-readable inventories.
- `reference/` contains external reference checkouts.

JSON exports retain the scientific representation and provenance. GFF3 is a
limited projection and excludes CDS rows without a recorded phase.
