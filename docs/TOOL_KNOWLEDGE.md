# Tool instruction library

## Retrieval

The supporting tool/manual library supplies instructions used by episodes.

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

## Snapshots and configuration

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
