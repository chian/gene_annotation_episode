# Problem-solving process library and supporting instructions

## Required design

The library is a collection of problem-solving processes. Its purpose is to
help construct an episode's decision problem: the investigation wants to work
on something, and retrieval supplies relevant ways to work on it. Selected
process information fills a common mother episode template, constructing a
child intelligence with a small relevant set of alternatives on each turn.
The child iterates, uses outcomes to revise its choices and can invoke further
problem-solving processes. The parent need not implement every variant as a
separate handwritten episode.

Process information describes the recurring decision, relevant context and
guidance, and permitted alternatives, including narrower process invocations.
Primitive tools and their software/resource instructions support those
decisions. A tool catalog with manuals does not by itself define the child's
problem-solving process.

The parent supplies its job, scope, constraints and requested typed return form.
Library information helps fill the child's decision problem within those
constraints and actual caller-bound capabilities. The child owns its subsequent
choices. Retrieval and template construction do not select a scientific action,
resource, retry, timer or cancellation. They introduce no autonomous workflow
layer. See [EPISODE_STRUCTURE.md](EPISODE_STRUCTURE.md) for ownership boundaries.

Discovery should expose compact process descriptions and invocation information,
with relevant details separately retrievable and known processes directly
addressable. Filling a child from selected process information must narrow its
actual decision context and available alternatives. Leaving every executable
tool schema enabled and merely appending a manual reference does not establish
that behavior. The filled child must retain the supplied process identity and
information through commissioning and worker reconstruction, alongside the
original parent assignment and return contract.

The earlier whole-process candidate in
[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md), C11-C14, remains interrupted.
It is superseded for scientific construction by the three-slot implementation
below. Literature episode implementation remains a separate work item; a working
scientific library does not establish those processes, and working handwritten
literature episodes do not establish library-driven construction.

## Scientific construction from three slots

The required scientific slots are:

1. An annotation-credit focus, selected from source-grounded A options.
2. A thought pattern, selected from source-grounded P options.
3. A set of actual tools, selected by a retriever from the available tool map for
   the parent's desired investigation. This set can contain multiple tools; it
   is not one library option or a fixed list attached to a thought pattern.

The tool map describes callable operations and their actual input schemas.
Supporting manuals can explain those operations. Research proposals, imagined
scripts and capability descriptions are not available tools. The retriever
fills the tool slot with the selected actual tools; construction must carry that
selection into the child's real catalog and execution permissions.

These parts fill a common scientific mother with the parent's actual job, scope,
evidence, constraints and typed return form. There is no catalogue of complete
predefined bioinformatics episodes. All constructed children use the ordinary
shared loop and their own controller. Case/source links explain A/P options;
they are not evidence about the current target or scientific credit receipts.
Worker reconstruction must retain the original selected information and tool
contracts rather than retrieve a different set.

The existing SL implementation got the tool slot wrong: it selects one of 13
research T bundles through `tool_ref` and caller-written operation mappings.
Some of those bundles describe operations that are not implemented. Removing
that mechanism and wiring a retriever over actual tools is active work; the
historical SL/FP checks do not verify this correction. The research corpus also
contains 10 A and 19 P options, whose source relationships remain useful.

The episode retains its original selected focus, thought pattern and tool set.
`process.revise` prepares an alternative approach and an explicit
`revision_origin` for an ordinary, separately selected `episode_child`
commission. It neither changes the current selection nor launches work.
When requested, scientific_process_results
returns each episode's existing credit/yield and its recorded origin through
the original typed forms. Forwarding preserves separate episodes; it introduces
no referral score, score allocation or extra controller observation. These
contracts are in [FIXED_PROCESS_BOUNDARIES.md](FIXED_PROCESS_BOUNDARIES.md).

The initial SL1–SL5 increment has historical engineering evidence. FP0–FP7
tracks the later fixed-process/provenance correction; connected verification is
recorded [separately](fixed_process_verification.json). The complete-role
[LP migration plan](LIBRARY_PROCESS_MIGRATION.md) was wrong and is withdrawn;
its module outputs are not evidence of scientific slot construction. Literature
implementation, production composition and configured-model demonstration remain open
in the [retained checklist](IMPLEMENTATION_CHECKLIST.md).

### Active correction contract and retained checklist

The replacement selection is exactly
`{version: scientific_process_selection_v2, annotation_ref, thought_ref, tools}`.
`annotation_ref` and `thought_ref` retain their A/P reference records. `tools` is
a unique list of zero or more actual callable names, not a reference to a T
entry. The complete actual catalog supplies their descriptions, input schemas
and existing metadata; a run freezes that map for reconstruction.

`process.tools({investigation: string})` is an ordinary selected operation. Its
test retriever returns `{investigation, tools, catalog}`, where `tools` contains
the selected actual names and `catalog` their actual contracts. The parent can
pass `result.tools` directly into the child's selection. Different requests can
produce different sets; a thought pattern does not carry a fixed tool bundle.
The initial implementation uses literal relevance and does not establish
semantic retrieval quality or completeness.

Construction checks selected names against the frozen actual map. The real
decision catalog and execution enforce the same selected contracts. Restoration
uses the saved selection and map; it does not retrieve again or silently convert
old T bindings. `process.revise({thought_ref, tools})` prepares a separate child
with the same annotation focus and recorded origin. Existing credit projection,
per-episode histories and original parent forms retain their meanings.

These bounded items remain visible throughout this correction:

- [x] TR0: fix selection, retrieval and reconstruction interfaces before coding;
  allocate exclusive owners.
- [ ] TR1: implement the actual tool map and test retriever, remove active
  `tool_ref`/T-operation mappings, and wire selection through construction,
  execution, revision provenance and worker restoration. One agent owns this
  entire production path and migration of existing tests.
- [ ] TR2: deliver the current A/P/source table and distinguish original study
  methods, research proposals and implemented tools. A second agent owns only
  the new source table and the research documentation's current-status notices;
  the pinned corpus and A/P identities remain intact.
- [ ] TR3: independently verify multiple-tool selection and execution, changed
  selections for changed requests, exclusion, original forms, fixed selection,
  revision origin and restoration. A third agent owns only two new test files.
- [ ] TR4: review the assembled path, run the appropriate connected checks and
  record exact results and limits. The coordinator owns this integration review
  and current architecture/status documentation. This does not complete the
  full production profile or configured-model scientific demonstration.

The three coding/source/check workloads consume the explicit records above and
can proceed together. Only assembled execution checks require the actual joined
implementation. No dependency on literature implementation is introduced.

## Implemented supporting manual library

The implementation described below is the separate supporting tool/manual
library. It supplies instructions used by episodes; scientific child construction
uses the distinct three-slot library above.

Scientific, launch, monitoring and results episodes use the same three ordinary
retrieval tools. Their generic decision instructions describe retrieval; manuals
are not concatenated into those prompts. A selected read arrives through the
existing recorded outcome and next-decision context. No retrieval agent or
autonomous executor sits outside the shared episode runtime.

- `knowledge.search(query, offset, limit)` searches the small metadata index.
  Empty query pages all entries. All whitespace-separated terms must occur in
  metadata, case-insensitively. This is literal discovery, not biological
  relevance assessment. It does not read manual bodies.
- `knowledge.entry(entry_id)` supplies one entry's section index, associated
  tool names, implementation provenance and section digests.
- `knowledge.read(entry_id, section_id, offset, limit)` reads selected lines of
  one section. Offsets count zero-based manual lines; `next_query` preserves the
  selection for a subsequent page. These coordinates are not scientific source
  anchors. Output contains the exact library identity and section digest.

Available tools with matching entries have `knowledge_entry_ids` in their
existing catalog descriptions. This supplies direct access without requiring
search. Discovery can also find an entry for a capability not enabled for this
episode; reading it grants no execution capability and changes no assignment.

The initial entries describe the existing detached phmmer adapter, Europe PMC /
PMC access, and retained XML/PDF/image/archive/spreadsheet reading. Their claims
describe current implementations. They do not claim that arbitrary programs,
remote queues, OCR, PyMuPDF or dedicated XML-table tools are executable here.

## Ownership and durable instructions

The default library is `gene_annotation_episode/knowledge/index.json` plus its
section files. An entry has an identity, short title/summary/tags, exact tool
names, provenance and separately addressable sections. A caller can supply a
replacement library with the same format using `knowledge_library_directory`
in tool configuration. `ToolRegistry` exposes that caller-owned path; episode
content cannot replace it. Caller-selected executable paths, input databases,
CPU allocations and resource limits retain their existing configuration owners.

At run construction the runtime copies the library into `<run>/tool-knowledge/`
and records a content-derived identity and per-section hashes/line counts in
its manifest. Copies and hashing stream through disk; manual bodies are not
retained in active library state. Resumption opens that existing snapshot.
Editing the source library affects subsequent runs, not that run's retrieved
instructions. Reads detect changes to snapshot bytes and return a specific
failure. Exact supplied pages remain in the existing action journal and can be
revisited with `episode.history`; no parallel manual-read history is added.

Reading instructions returns no scientific records, native measurements,
launch/handoff receipts or acquired-result witnesses. It creates no corresponding
scientific, monitoring or operational contribution under the existing production
projectors. It is one ordinary completed own action with the actual projected
credit, normally unchanged. It neither submits a job nor changes timing history.
Existing parent-defined report forms and numerical continuation remain intact.
Failures identify the selected operation; they do not remove other entries or
reject scientific evidence. There is no mandatory manual-reading step.

## Current decision context and remaining construction work

The supporting manual library keeps manual bodies out of the initial decision
context and does not activate tool schemas. The scientific mother's old T
mapping path is being replaced by selection of actual tools as described above.
The retrieved tool set must narrow the final callable schemas. Other existing
bindings retain their own catalogs. Specialized nested literature episodes were
not implemented by the manual-library change; they have a separate implementation
and retain their own permitted child relationships.

The target is library-assisted construction of bounded decision problems, as
specified above. Categories can assist discovery without becoming compulsory
episode levels. An ordinary capability/manual lookup remains a tool call; its
information can help construct a child, rather than being confined to manuals
consulted after a fixed handwritten child has already been defined.
Literature can motivate bioinformatics work and bioinformatics can motivate
literature work. The episode integrating the relevant returned findings chooses
the next uncertainty; neither is installed as a mandatory stage above the other.

The current integration tests use scripted providers and synthetic controllers.
They verify page delivery, all-role access, unchanged credit for instruction
reads, constrained parent forms and interrupted recovery against original
instructions. They do not establish configured-model use or scientific benefit.
The already running investigation_009 retains its pinned code and settings.
