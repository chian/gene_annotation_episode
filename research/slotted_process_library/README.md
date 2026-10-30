# Three-slot problem-solving library

**Current contract (2026-10-21):** select one existing annotation-credit focus
(A), one existing thought pattern (P), and a variable-size set of actual tools
retrieved from the complete caller-provided tool map for the requested
investigation. No complete episodes or T01–T13 bundles are selectable construction
entries. [CURRENT_SLOT_SOURCES.md](CURRENT_SLOT_SOURCES.md) preserves all 29 A/P
identities and 135 source relationships, retains the existing F01–F05 lane IDs,
and states which historical T operations lack actual implementations. The
runtime correction is in progress; this documentation does not verify it.

The remainder of this README records the original version-1 research catalog.
Its 42-entry counts, one-T-per-selection descriptions and capability contracts
are historical curation, superseded by the current contract above. The case
corpus and historical manifests remain preserved.

This catalog distills the existing 142 distinct published-case groups into options for three selections:

Version 1 contains **10 annotation distinctions, 19 thought patterns and 13 tool contexts**. Its 208 option-to-source links cite 96 distinct case groups explicitly; the coverage register accounts for all 142. There are 23 worked selections covering every entry and six examples of mismatches or evidence limits.

| Slot | Selection contributes | Entry content |
| --- | --- | --- |
| 1. Annotation distinction | The annotation property the child is working to establish, expressed through the structured credit form | Claim scope, distinctions, illustrative bounded values and unsupported extensions |
| 2. Thought pattern | A way to narrow competing explanations and choose informative contrasts as results arrive | Use conditions, live alternatives, decision guidance, result-contingent revisions and boundaries |
| 3. Tools | A coherent small set of evidence operations appropriate to that investigation | Inputs, outputs, actual use, implementation availability and limitations |

Read the [option tables](OPTIONS.md), [full entries](DETAILS.md), and [worked selections](ASSEMBLIES.md). The machine-readable catalogs are [annotation options](annotation_options.json), [thought options](thought_options.json), and [tool options](tool_options.json).

[index.json](index.json) supplies compact discovery metadata. Each option also has its own `entries/<ID>.json` detail file, so later retrieval can select one entry without loading the whole catalog or the case register.

The parent supplies the scientific job, existing evidence, constraints and requested typed return form. Selecting one entry per slot supplies content for constructing a child's decision problem. The child still chooses its actions and revises its approach. An existing observation supplied by the parent remains context; it does not require another construction slot. A tool selection can expose several closely related primitive operations. The entries prescribe no task order or permanent selection for an entire investigation.

Credit is assigned through declared JSON fields and values. Selecting an annotation option does not award credit. Its illustrative values describe distinctions that a form should preserve; they are not installed fields, adopted numerical axes, weights or a replacement scoring formula. Source identity, experimental conditions, missingness and inspection status remain attached to evidence across all three slots.

The thought-pattern entries contain choices about inference: for example, deliberately seek a relative that breaks a sequence-to-function rule, or retain a system output while reconsidering its contributor. Sequence searches, distance calculations and table extraction belong to the tool slot. A tool can produce evidence relevant to a thought pattern without deciding the biological inference.

## Inspecting the sources

- [Option-to-source table](OPTION_SOURCES.md): each option's particular supporting observations, primary links, known locators and inspection limits. [Structured version](option_sources.json).
- [All-case register](CASE_COVERAGE.md): the relation of every one of the 142 groups to each slot, including contextual and limited-inspection mappings. [Structured version](case_coverage.json).
- [Preserved case records](case_records.json): all 149 included records, with seven duplicate records retained within their existing case groups.
- [Original research groupings](corpus/follow_up_lanes.md): F01–F05 keep their names and order. Their research groupings do not impose episode levels or five numerical scoring dimensions.
- [Corpus manifest](corpus/corpus_manifest.json) and [snapshot manifest](corpus_snapshot_manifest.json): original scope and hashes of the retained research records and traces.

The collection contains 134 groups with relevant primary sections inspected and eight with abstract/summary inspection. The latter remain marked as limited. Published outcomes were already known; the entries are case-grounded reconstructions of useful reasoning choices, not transcripts of every author's deliberation or evidence of blind discovery. Reuse of a paper, a case or one measurement across several entries does not create independent evidence.

Research records and curation traces are preserved under `corpus/`. Original absolute paths remain historical provenance. Raw PDF/XML/XLSX/CIF/PDB/TSV/TXT assets were not copied into this catalog; their original research locations and published source links remain in the records. Consequently, historical links to raw assets may require the original research directory or source retrieval.

## Availability and maintenance

Tool entries distinguish repository catalog definitions, read-only research operations actually performed, and capability specifications needing an implementation or supplied data. Their input/output descriptions are normalized capability contracts, not literal API schemas. Exact invocation uses the actual registry and manual. Published biological experiments supply evidence; their appearance in a case does not make those experiments executable capabilities.

Keep A, P and T identifiers stable. Append options with new identifiers; record any split, merge or semantic revision without silently reusing an old identifier. A table mapping indicates curatorial relevance; the explicit source observations and limits explain the actual support. No complete Cartesian product or exhaustive inventory is claimed.

The [fixed six-item checklist](BUILD_SCOPE.md) retains all completed work items. The [catalog manifest](catalog_manifest.json) records the version, file hashes and remaining implementation limits.

The catalog supplies library content. Runtime retrieval, mother-template construction and episode dispatch have not been changed by this work. The examples are retrospective selections, not executed children. Consistency checks are recorded in [validation.json](validation.json); they establish reference and data integrity, not prospective scientific performance. Run `python3 build_catalog.py` in this directory to regenerate the option/source/coverage tables and repeat those checks.
