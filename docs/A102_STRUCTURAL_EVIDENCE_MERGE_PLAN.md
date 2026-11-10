# Plan: absorb A111 into A102 structural evidence

Status: implementation authorized and written, 2026-11-04; validation deferred.
The user subsequently requested making this a goal and implementing it, while
retaining the instruction to defer testing during A102's HPC rewiring. See the
[goal record](A102_STRUCTURAL_EVIDENCE_MERGE_GOAL.md) and
[implementation notes](A102_STRUCTURAL_EVIDENCE.md). The design below remains the
validation contract. It authorizes no tests or remote jobs.

## Intended outcome

For new investigations, A102 becomes **Structural evidence**, with two available
scientific paths:

| Path | Scientific responsibility | Principal outputs |
|---|---|---|
| Comparative structure | Structural correspondence, conserved functional features, interfaces and contrasts against relevant alternatives | Existing native correspondence B, feature-qualified results, local traits, interfaces and contrast sheets |
| Experimental structure | What a structural experiment and its fitted model establish about a declared molecular feature or state | Source-linked geometry, matching local validation, support/opposition, qualifications and unresolved components |

Either path can be useful on its own. Neither is a prerequisite or mandatory
stage of the other. Both can contribute to the same explicit functional
question. A111 ceases to be a separately selected/scored axis in the new
catalog, while its useful readers, assessments and historical results remain.

Direct activity measurements stay with A105; intervention evidence stays with
A106. A102 may consume their qualified findings through existing parent-owned
information exchange. A structural contact does not by itself become an
affinity measurement, catalytic demonstration or causal result.

## Current implementation facts that constrain the merge

- `a102_investigation.py` already includes functional feature geometry,
  reference/local trait attribution, interfaces and synthesis. Its constructor
  checks the exact published name `Structural homology`.
- `a102_credit.py` calculates native or specifically attributed correspondence
  B. Functional sheets are already separate from that controller scalar.
- `scientific_process_episodes.py` currently selects that native scorer for
  A102 scientific children solely from their axis identity.
- The default A102 report/resolver assumes comparative results. An
  experimental-only result needs an explicit supported return path; it must
  not be reported as an empty comparison or a native B measurement.
- The experimental implementation already has `literature.structure.populate`,
  `requested_structure_components` and `literature_structure_cells`, using
  `literature_structure_{inputs,calculations,storage,types,prompt}.py` and
  `literature_task_selection.py`.
- Its implemented calculation is conditional selected-model geometry with
  matching local validation. It retains six components: local fit, supporting
  and opposing geometry fractions, and positive/opposing/signed source
  geometry. The existing local-fit calculation uses residue RSCC. Broader
  research proposals are not evidence that additional experimental methods
  have working readers or agreed scoring definitions.

This therefore needs report, ownership and progress integration, not just an
A111-to-A102 label substitution.

## Parallel work and file ownership

The separation is between **scientific interpretation of received records**
and **execution of selected computational work**. There are shared integration
files; the two implementations are not completely independent until those
interfaces are fixed.

| Workstream | Owns | Boundary |
|---|---|---|
| Experimental structural evidence | New A102 experimental assessment/report adapters; reuse of `literature_structure_*`; experimental task text; dataset/model attribution and dependency handling | Consumes admitted source records. Does not choose an HPC host, construct native commands, launch jobs or parse scheduler state |
| A102 HPC wiring | `a102_tools.py`, `a102_resources.py`, `a102_native_worker.py`, native setup, relevant `native_protein_structure_*`, execution/resource registration and `hpc_*` changes | Produces authenticated scientific results through the existing publication/receipt boundary. Does not define experimental interpretation or a new structural evidence score |
| Shared integration, one owner | `a102_investigation.py`, relevant `scientific_process_episodes.py` dispatch/guidance, service factories, tool catalog composition, parent report/presentation and current axis catalog | Small integration patches after both workstreams agree on their interfaces; no simultaneous competing edits |

Keep new experimental modules separate, for example
`a102_experimental_evidence.py` and `a102_structural_report.py`; these are
proposed module names, not existing implementations. Reuse the current
literature repository rather than copying it or creating a second scoring
engine. Treat existing native publication/scoring modules and shared Source
schemas as stable interfaces for this workstream. Any change to those interfaces
belongs to the shared integration stage.

At implementation start, record the active file ownership and baseline for
the actual HPC branch. Several HPC and A102 tool files are already modified
in the shared workspace. Do not revert, overwrite or opportunistically refactor
those changes. In a shared checkout, use exclusive file ownership; integrate
the shared-file changes through one owner. This plan assigns no other agent
and sends no messages to another workstream.

## Interface to fix before parallel implementation

Use existing immutable Sources, numerical-cell receipts and explicit
target/model mappings. A path, job ID, availability notice or submitted job is
not a scientific result or permission to read its artifacts.

The experimental adapter needs a versioned semantic view containing:

1. **Question and subject:** target, functional assertion where established,
   biological scope, measured molecule, construct and target correspondence.
2. **Original evidence identity:** experiment/dataset identity when established,
   source record, deposited entry/model revision, artifact identity/checksum,
   method and source acquisition provenance. Unknown identity stays explicit.
3. **Physical selection:** model, chains, residues, insertion codes, atom groups,
   alternate locations, state, partners and declared feature panel.
4. **Validation:** the matching validation record/revision, its granularity,
   native values and missing reasons. Preserve coordinate and assignment
   uncertainty; do not infer population occupancy from deposited occupancy.
5. **Assessment and numerical results:** the saved assessment, selected
   components, native units, formulas, bounds, conditions, supporting/opposing
   observations, conclusion, limitations and revision links.
6. **Dependence and use:** parent source/measurement links, repeated
   representations, shared model/dataset identity, and which claim each use
   supports. A different feature question is not automatically a new
   experiment or an independent observation.

This is an adapter over established records, not a replacement HPC job schema.
Comparative jobs retain their current maps, transforms, native metrics,
software provenance and grading grants. The scientific consumer must work
with the same admitted results regardless of their execution location. An
operation requiring execution uses the configured execution service; the
experimental workstream adds no direct local/remote execution bypass.

If the HPC work changes an output contract, its producer version and the small
consumer adapter are reconciled at integration. A local filesystem path must
not become the assumed interface to remote results.

## Implementation sequence

### 1. Define the broader task and report contract

Prepare versioned A102 instructions and a report capable of carrying either or
both evidence paths. Keep one A102 owner; preserve A102's scientific-descendant
boundary by bringing experimental structural work inside A102, rather than
opening a general route for arbitrary sibling axes beneath it.

Proposed core task text:

> Investigate structural evidence relevant to the supplied molecule and
> biological question. Use structural comparison, experimental structural
> evidence, or both according to the uncertainty being addressed. Establish
> model identity, construct, state and provenance. For comparisons, preserve
> correspondence, extent and function-relevant geometry. For experimental
> evidence, establish what the data and selected model support, including
> local validation, assignments and unresolved features. Keep direct
> observations, model-derived geometry and transferred interpretations
> distinguishable. Return the applicable saved numerical components with
> their sources, dependence, biological scope and limitations.

The model receives the operations actually available in its configuration.
There is no required alignment-first sequence, preferred test source or
answer-bearing example in its task text.

Extend the parent result with separately typed comparative and experimental
sections, applicability/status, contradictions, information needs and source
dependencies. An experimental-only report can be useful without a B value.
Unavailable and inapplicable components remain distinguishable from zero.

### 2. Build the experimental adapter independently

Reuse the existing structure population operation, source readers,
experiment/revision handling and six numerical components. Add only the
missing attribution, typed return and A102 interpretation adapters. Keep
assessment on the assayed molecule separate from target transfer.

Preserve current formula meanings and version identifiers. Support the
implemented experimental cases first; label unsupported methods or missing
validation explicitly. Do not import unadopted research formulas or add an
experimental method as a side effect of this organizational merge.

### 3. Preserve provenance across both paths

Join uses through existing source/dataset/model/measurement identities and
explicit dependence links. Reused coordinates, a validation report, a
literature description of the same experiment and alternative model
representations do not become independent confirmations.

Allow distinct comparisons and distinct questions to retain their own results;
do not erase useful observations merely because they share a structure. Prevent
duplicate contribution in any receiving aggregation. Missing dataset identity
must not be converted into assumed independence.

### 4. Integrate progress and scientific outputs explicitly

Preserve existing comparative B, feature and contrast calculations. Preserve
the experimental source-geometry components as separately named quantities.
Do not sum B with source geometry or multiply them merely because both are
bounded numbers. A workflow/controller progress score is not a final scientific
evidence score.

The current axis-only native scorer is insufficient for experimental-only
work. Proposed progress binding for the new merged workflow:

- Comparative tasks retain their existing native comparison progress binding.
- Experimental tasks use the existing retained-scientific-finding progress
  mechanism, with source-bound findings and revision/dependence handling.
- The shared scientific parent accounts for received findings from either
  path, rather than adding the two children's unlike scalar credits.

Make this binding explicit and versioned at the shared integration seam; do
not silently change the units or cost policy of existing saved workflows.
Do not require a placeholder alignment just to make an experimental task
eligible for progress or return.

The new scientific A102 result is initially a structured component report.
Its parent must consume both sections and their qualifications. If an active
annotation aggregator requires a single scalar for the broadened axis, the
combination rule must be explicitly settled before that new projection is
activated. The legacy B value remains a comparative quantity; relabeling it
as the complete merged score would not complete this work.

### 5. Perform the shared integration once

After the HPC result interface is stable, one integration owner wires the new
task selection, literature structure family, report/resolver, progress binding,
service factory and tool catalog. Keep executable availability owned by the
HPC/tool registry. Experimental adapters can be completed without activating
unfinished catalog entries or changing the running workflow's snapshot.

Locate the actual caller's published instruction source before updating it.
Run-owned snapshots and test fixtures are not the authoritative catalog.
Update the A102 name check and the current catalog together. New catalogs
offer A102 Structural evidence and retire standalone A111; A109 remains
removed. This leaves nine current axes, with no renumbering of the others.

### 6. Preserve historical compatibility

Keep old A111 sources, sheets, formula versions, operation signatures, provider
identities, experiment revisions and frozen instruction snapshots readable
under their original meanings. Preserve old comparative-only A102 workflows
and their bindings. Use explicit versioned routing/adaptation for a new A102
consumer of a legacy experimental sheet; do not rewrite archived scientific
records or treat a renamed reference as newly acquired evidence.

New parent aggregation must not count a legacy A111 sheet once as A111 and
again as its A102 experimental view. Retiring an axis from new selection does
not delete its archived evidence or broaden access to unread sources.

## Deferred validation and completion conditions

No tests, replay jobs, native executions, HPC submissions or live A102
workflows are part of this planning step. Testing stays deferred until the
user resumes it and the HPC integration is ready. Future validation uses full
autonomous workflows, one at a time in this window, under the applicable
resource policy. No targeted checks are substituted for those workflows.

Record expected outcomes separately before those future runs. The cases must
collectively demonstrate:

| Case | Required observed behavior |
|---|---|
| Comparative only | Existing alignment, feature/contrast semantics and numerical custody remain intact across the HPC handoff |
| Experimental only | Relevant experimental structural evidence can produce an applicable result without first producing an alignment or native B |
| Both paths use one structure | Useful results from both paths reach the parent, with shared dataset/model dependence retained and no duplicate independent credit |
| Missing or conflicting experimental evidence | Missing atoms/validation/identity remain unknown; genuine incompatible geometry is distinguished from absence of evidence |
| Legacy evidence | An original A111 sheet remains interpretable under its original formula and provenance when explicitly consumed by a new A102 task |

Validation must establish the actual sequence from source acquisition and
assessment through numerical publication, typed child return and parent
interpretation. Installed tools, populated sheets or accepted report metadata
alone are insufficient. Prompts contain only legitimate task inputs and
available operations; discoveries and assessment choices remain autonomous.

The merge is complete only when both paths are available under the broader
A102 task, the parent demonstrably consumes their applicable results, current
A111 selection/independent contribution is retired, old evidence remains
interpretable, the HPC interface remains intact, and any required final scalar
projection has an explicit agreed definition. Until testing resumes, report
implementation or integration status separately from validated completion.
