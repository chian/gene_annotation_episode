# Bioinformatics tool graders: goal and operating principles

User-requested scope record, 2026-10-24. This is additive: it does not replace
GOAL.md, the episode design, earlier user decisions, or the BLAST verification
record. The source inventory is
`research/tool_grader_inventory_2026-10-24/`. Its per-entry status table is the
work tracker; this document states the outcome and constraints.

## Controlling user direction, verbatim

> This is probably a good paradigm. Each tool needs to have it's own scoring sheet and score calculators. So in that sense, this is a tool-facing version of what you did for the evidence-axes. These are the parts that will make that up.

> The exact bayesian formula I do not care about too much because as long as it's formulated well, we can adjust it easily later. I am more worried about getting all these pieces as data first. The BLAST grader will need it's own internal "score sheet" from which the overall parts are all calculated and as long as we do it that way, we can adjust later on.

> great. based on your experience can you formulate a concrete goal and set of operating principles for carrying out the same work for all tool graders? Keep the tool graders separate from the literature graders for now. We will tackle those separately. You should have many many tools available to you that you can add to the tool library (name + description + instructions) if needed. For example, you should have all BV-BRC tools https://github.com/BV-BRC/BV-BRC-MCP and everything that is an actual bioinformatics algorithm and not a literature search from here: https://github.com/chrisagrams/gentner-ave. Start by making a list of all bioinformatics tools available on all resources and then make a goal that populates all of these tool libraries with graders.

## Goal

Populate the actual tool library with truthful, resource-specific information
and functioning deterministic graders for every included bioinformatics
algorithm and analysis mode in the inventoried sources: this checkout's tools
and installed native programs, BV-BRC analysis services, gentner-ave's actual
computational tools, and additional installed biological API clients where they
supply the required results or measurements. Each tool has its own numerical
scoring sheet and calculators. Real matching formats may share parsers and
mathematics; different scientific meanings retain distinct sheets/calculations.

The completed path is:

1. A selectable tool has its actual name, description, resource-specific
   instructions and invocation binding. The parent can choose it; the assigned
   child receives the corresponding instructions and permitted operation.
2. Retained native results and explicitly supplied inputs/metadata populate that
   tool's numerical sheet through tested readers. Tool, mode, database/model,
   subject, coordinates, units, denominators, provenance and missing information
   remain distinguishable where relevant.
3. Deterministic functions calculate the tool's numerical components and any
   explicitly formulated combinations. A saved sheet can be recalculated with
   changed model parameters without another acquisition or analysis run.
4. The actual results path invokes the correct grader and retains the full
   structured result. Only fields needed for the assigned decision cross an
   episode boundary. Evidence-axis aggregation can later consume the typed
   components; this goal does not change the annotation-credit formula.
5. Every included tool/mode has filled examples and meaningful numerical,
   failure, missing-data and source-format tests. Verification records distinguish
   source inspection, synthetic fixtures, recorded native output, actual
   execution and complete episode-path integration.

Completion is checked per tool/mode/resource row. A descriptor, empty sheet,
generic function, passing catalog validation, or unrelated test is insufficient.
No outstanding included row is silently removed to declare the goal complete.
Unavailable credentials, dependencies or native result formats stay explicit
remaining work for their rows while independent work proceeds.

Literature search, paper interpretation and literature judgment graders are
excluded. Biological database readers are supporting inputs, not literature
graders. File, transfer, status and workspace helpers need accurate operational
returns, not fabricated scientific scores. Pure protocols, presentation helpers,
LLM planners and fabricated experiments are accounted for in the inventory but
are not scientific algorithm graders. An intentional numerical simulation is
included as a model result; it must never be presented as observed biology.

## Scope and availability

The pinned source inventories enumerate registrations and implementations,
including exclusions and defects. Their counts are not a count of unique,
working algorithms: wrappers, resource variants and service recipes overlap.
The master index retains each source identity and records verified equivalence
explicitly. New modes or legitimately discovered operations are added with a
reason and source; existing items keep their identities and completed work.

For each entry distinguish: source present; prerequisites present; resource
configured; actual invocation bound; format observed; grader tested; actual run
tested; episode integration tested. A local API client is not local execution of
the remote algorithm. A generic SSH/Parsl/Globus transport does not establish
that an algorithm is installed on Aurora, Polaris or Spark.

BV-BRC service functions and output artifacts are the relevant scientific
capabilities. Its bundled LLM workflow planner/external workflow engine is not
adopted as an owner of our episode decisions. Gentner's agent roster, interpreter
and stopping behavior are likewise outside this build. Use actual primitive
service/native operations under the existing episode ownership.

## Operating principles

### Keep the responsibilities separate

| Responsibility | Input | Output |
| --- | --- | --- |
| Tool information | Verified callable/service, input contract and resource instructions | Name, description, resources and corresponding instructions; separate host binding metadata |
| Result reader | Original artifact(s), declared format/version/mode, original request and supplied metadata | That tool's populated typed numerical sheet, retained native facts and specific missing/invalid fields |
| Score calculators | The populated sheet and explicit parameters | Numerical components/combinations with their inputs, units, denominators and assumptions |
| Requested result projection | Graded result and the parent's declared return fields | Only the requested typed facts; no model-written restatement of recorded results |
| Evidence-axis scorer, later W05 work | Applicable tool/literature components | Annotation-score compilation; not implemented by changing a tool grader |

These are function boundaries and ownership rules, not new episode types or a
generic JSON rule interpreter. Each tool's contract must name its actual fields
and functions before coding; the table is not itself a finished scoring sheet.

### Begin with real outputs and numerical questions

For each tool, inspect its complete implementation path and a real native
output/specification. Identify what numerical questions that result can answer
and which inputs the calculations require. A source description or prose log is
not proof that a measurement exists. After reading outside material, reread this
user-direction record and the tool's current contract before designing cells.
Upstream conventions inform the implementation; they do not override the user's
sheet/calculator separation or episode design.

For every numerical cell state what it measures, exact source inputs, formula,
units, population/denominator, range, uncertainty where available and missing-
input behavior. Preserve meaningful intermediate quantities before combining
them. Use program-reported measurements directly where appropriate. Do not
replace them with an LLM impression or encode vague categories as confidence.
A native ordinal classification may be preserved as such; it is not silently
converted into a probability or a universal reliability score.

A scoring sheet must contain usable numerical components, not only provenance
and annotations. Conversely, do not manufacture a score for an operation whose
only result is a file, job handle, or successful retrieval. Those operations
supply artifacts/facts to the relevant scientific grader.

### Preserve modes, associations and complete data

BLAST pairwise correspondence and database identification illustrate why one
tool name can need multiple grading contracts. Record modes before calculating.
Select parsers by actual format/version and field declaration, not merely the
API/local/HPC label. Two resources can share a format; one resource can emit
several incompatible formats. An upstream filename ending in `.json` does not
establish compatibility with another program's JSON schema.

Retain actual native arrays, alignments, matrices, trees, images/masks, model
outputs and sidecar files needed by the calculations. A bounded stdout preview,
first-hit summary or rounded research log cannot replace them. Preserve their
subject, function, taxon, source, sample/replicate, coordinate and condition
associations as applicable. No joins based on independently sorted arrays, no
arbitrary first record, and no inference of an accession link from shared taxon.

Keep missing, not measured, failed, truncated, incompatible and measured zero
distinct. Preserve valid partial results. Never substitute padding for a failed
alignment, a placeholder tree for a failed phylogeny, or mock observations for
an unreadable experiment. Repair such source branches before treating their
output as scientific data. Explicit model simulations and synthetic test
fixtures retain that identity throughout the path.

### Make calculations explicit and replaceable

Deterministic readers/calculators make no network requests, launch no work,
change no resource selection, and invoke no LLM. Any additional acquisition
needed is a declared input requirement for the responsible episode. Preserve
its returned facts so recalculation is independent of acquisition.

Keep individual numerical contributions and explicit sums/products/models.
Record which components a combination uses and which remain unused. Do not
pretend that storing taxonomic/source-quality measurements means the current
formula uses them. Preserve observed tool values separately from derived
normalization. Parameters and assumptions are supplied explicitly so later
tuning changes calculators, not extracted evidence or historical observations.

Handle repeated representations, overlapping alignments, duplicate sequences,
shared samples and dependent evidence explicitly. Do not infer independence
from different filenames or accessions. Population corrections require real
matching populations/denominators; returned-hit counts do not supply database
prevalence. Conditional assignment weights, prediction scores and calibrated
probabilities have different meanings and must be labeled accordingly.

### Preserve the episode backbone

Scientific parents assign the question, constraints and requested return form.
Launch and its API/local/HPC children retain their existing decisions and
resource-specific preparation/monitoring structures. Tools and graders are
primitive operations within that structure. Add no autonomous planner, grading
episode, private reasoning loop, hidden retry, scheduler or scientific gate.

Tool discovery must connect selections to the appropriate child-owned operation;
fixing a missing binding must not restore execution tools to root or grant a
scientific child arbitrary resource-management operations. Keep all three
construction slots: evidence_axis, thought_pattern and child_tool_info. Tool
grading does not define a complete scientific episode or a fixed tool bundle.

Internal JSON retains full structured results. Model-facing TASK supplies the
detailed assignment/instructions; STEERING selects concise decision-relevant
facts and tables. Do not dump sheets, raw output, hashes or tracking history into
prompts. A grader must not create extra turns, credits, controller observations,
or retrospective changes to yields. Monitoring/time information and scientific
information remain separate.

Use the actual resource instructions and caller limits. Do not run a local
database BLAST on this machine. Aurora workflow files remain under
`/lus/flare/projects/BioReason-Aurora-Test`; new jobs charge `EpiCalib`; only the
small tracking file belongs in Aurora home. Obtain required access instructions
with the user when an actual access step needs them; do not guess credentials
or hosts. Preserve the existing pending BLAST RID instead of resubmitting it.

### Define boundaries, then parallelize

Before assigning a coding workload, record its complete tool/mode list, owned
files, native input formats, sheet fields, calculator signatures, metadata joins,
handoff shape, consumers and verification cases. Share format readers or
mathematics only after establishing matching semantics. Source-module or subject
headings alone are not sufficient module boundaries.

Fresh subagents receive the relevant verbatim requirements and the frozen
contracts, with exclusive file ownership. Once those contracts exist, independent
tool families, format readers, calculators and integration tests can be built
concurrently. Coding does not wait merely because the final outputs will later
be composed. Only a specific missing input/contract blocks dependent work;
integration consumes delivered modules. Never reactivate an unrelated old task.

### Verify and report precisely

Each tool/mode needs a populated example whose numerical answers can be checked,
plus counterexamples appropriate to the algorithm: missing/truncated outputs,
units and coordinate boundaries, wrong reference/version, duplicate/overlapping
records, contradictory metadata, negative results and source-format differences.
Compare shared-format results numerically and verify saved-sheet recalculation
without acquisition. Test actual native outputs where available, and distinguish
those from deliberately synthetic fixtures.

Verify the full selected-tool → correct resource child → native output → reader
→ numerical sheet → calculator → requested typed return path for published
bindings. Unit tests alone do not establish it. Reuse existing passing BLAST
work; do not rewrite it just to match a new universal framework.

Keep a fixed row for every inventoried deliverable, including checked work and
exclusions with reasons. Track six independent completion columns: tool info,
sheet contract, readers, calculators, result-path binding, and verification.
Preserve separate live-resource qualifications. Print concise filled numerical
examples and exact remaining work for the user; do not send the user to files
instead of providing the information needed to steer. Keep permanent decisions
unchanged and record later corrections additively. A waiting service blocks its
own live test, not independent implementation for other tools.
