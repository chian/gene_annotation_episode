# A101 sequence-homology investigations

A101 uses the ordinary recursive `scientific_process` role with the published
sequence-homology investigation instructions. An A101 owner can commission
narrower scientific work, literature work, and launch, monitoring and results
episodes. Its question can start from an unnamed supplied sequence or an
explicit file record or region. Functions can emerge during the investigation.

`gene_annotation_episode.a101_investigation.A101Subtree` constructs a normal
`episode_child` selection against one run's frozen publication and tool catalog.
It adds no role, private decision loop, prescribed itinerary, fixed tool bundle,
score or stopping condition. Existing `process.revise` prepares alternative
thought/tool selections for a separately commissioned scientific child. The
original episode retains its assignment.

## Assembly and commission

Use `bind_assembled_services` with the caller's actual job/execution resources,
tool catalog, units and retrieval configuration. Select this source publication:

```
research/slotted_process_library/publications/2026-10-24-001
```

The scientific child roles should include `scientific_process`, `literature`,
`launch`, `monitor` and `results`. The assembled setup freezes the publication
and tool information; constructing a commission does not execute work.

For live `ModelConnection` calls, use `decision_exchange_v1`. The public
`run_workflow` entry point selects it for its owned model provider. A caller
constructing `Workflow` directly must pass `decision_protocol` explicitly and
preserve the provider's session/frame interfaces when wrapping it. Legacy full
contexts can exceed the provider's input limit as action history grows.
Use `semantic_fast_v1` with the actual configured FAST model for live tool
retrieval; `literal_test_v1` is a lexical test mode.

Enable exact contract discovery for live scientific parents by supplying
`scientific_contract_information_profile=CONTRACT_INFORMATION_PROFILE` to
`bind_assembled_services`, using the constant from `composition_information`.
The assembled case policy accepts the same optional service setting. This
requires `decision_exchange_v1`; legacy mode remains available. Scientific
parents and the native launch parent can request `episode.return_contract` within a pending decision and
select a field using `episode-fact:<source>`. Common evidence-reference facts
are discoverable alongside provider-specific facts. Contract lookup performs
no acquisition and adds no controller observation.

Native homology also needs a complete caller-owned resource selection when its
launch child selects the local adapter. Preserve the actual resource identity,
CPU, memory/scratch/time allocation and registry binding. `resource.inspect`
reports capability and availability; it does not expose the hidden configured
allocation. Supply the actual selection with the launch request or make its
operands explicit in the parent's context. Resource configuration is operational
input, separate from evidence about the protein.

After that setup, a caller can construct the parent's selection:

```python
from gene_annotation_episode.a101_investigation import A101Subtree

subtree = A101Subtree(run_directory)
selection = subtree.commission(
    store,
    target_ref=selected_subject_ref,
    scope=scope,
    completeness="fragment",  # complete, fragment, or unknown: caller declaration
    child_tool_info=selected_actual_tool_resource_pairs,
    thought_id="P01",
    question="Determine which functions the supplied sequence supports and what remains unresolved.",
    evidence_refs=inherited_evidence_refs,
    constraints=parent_constraints,
)
# An existing provider action uses {"selection": selection, "report_update": ...}.
```

The selected subject must have actual original-input coverage contained in the
assigned scope. A multi-record file requires an explicitly selected subject;
a subregion requires its actual feature/product mapping. `a101_material` in
the assignment context retains measured supplied length, molecule, units and
original intervals alongside the caller's completeness declaration. It never
fills an unknown full-protein length from a snippet. No public name or candidate
annotation is required.

Only actual frozen tool/resource choices can enter `child_tool_info`. Execution
capability and instructions retain their existing resource-specific boundaries.
For a completed `process.revise` result, pass `revision=outcome` together with
its matching thought/tool choices. The builder projects canonical information
to callable selectors and carries the original `revision_origin`. The ordinary
scientific binding authenticates that preparation before starting the new child.

## Evidence ownership and returns

The default opt-in parent form distinguishes four conclusions: family, molecular
activity, specificity and physiological role. Each has a bounded interpretive
status plus actual hypothesis and assessment references.
The claim fields declare their permitted hypothesis predicates and require
assessments to reference hypotheses selected in the same claim. The form also carries
unresolved alternatives, typed limitations, actual committed records, changed
assessments, the interpretation basis and observations acquired after that basis.
Initial conclusions are `not_assessed`, with no invented hypotheses or witnesses.
The caller can supply its own closed form and explicit initial interpretation.
Every selected action supplies the complete current interpretation in
`report_update`. Keep the initial unknowns until actual evidence supports a
change; recorded fact fields are filled by the host at return time.

Reference characterization should preserve the actual assayed protein or
construct, its measured endpoint and conditions. Source-backed links identify
its relationship to a searched sequence/profile. Database descriptions remain
source statements. Retained alignment/site observations preserve native scores,
denominators and actual correspondence; a substituted residue, an unmapped site
and an unobserved part of a fragment are different outcomes.

The scientific owner commits these relationships and interpretations with the
ordinary reasoning contract. Assessed target claims remain separate from the
source claims in typed investigation findings. The existing receipts transport
the admitted form and dependencies to the parent. Acquisition, repeated hits,
unchanged monitoring and report formatting do not establish scientific findings.

Child return forms must include the evidence the owner needs. For native
homology results, request actual `committed_record_refs` and the registered
`job_result_progress` facts when the decision depends on acquired rows and
search/parse completeness. Returning only `job_ref`, `job_handoff_state` or a
null failure field does not transfer the native result snapshot or establish a
completed no-hit search for the parent. The default A101 form cannot recover
evidence omitted from an intermediate child's selected return form.

After discovering the permitted results child's contracts, a parent can choose
this closed form:

```json
{
  "type": "object",
  "properties": {
    "records": {"$ref": "episode-fact:committed_record_refs"},
    "coverage": {"$ref": "episode-fact:job_result_progress"}
  },
  "required": ["records", "coverage"],
  "additionalProperties": false
}
```

The host expands only explicitly selected facts to their frozen schemas. It
does not add omitted evidence to a metadata-only form. A native-complete,
error-free finished parse with zero parsed/acquired rows and all rows acquired
is a completed empty search. Its bounded conclusion is no informative match in
the searched space; it does not assign a function or establish that no homologs
exist elsewhere. Partial or unavailable acquisition remains a separate limit.

The receiving parent can call `resolve_report(store, admitted_form, scope=scope)`
on the default form. This validates reference types, target attribution, claim
predicates and assessment-to-hypothesis links, and resolves actual evidence.
Evidence-bearing conclusions require hypotheses and assessments. This is an
audit of the received relationships; the scientific judgments remain those of
the responsible episode. Use the ordinary runtime admission boundary first.

A101 numerical credit is routed by host code, using the frozen A101 axis
selection. `ScientificProcessEpisodes.credit_projector` selects
`A101SequenceCredit`; it does not ask the model to select a sheet or declare a
score. On each ordinary runtime projection, the host reads only actually
received native observations, authenticates their retained grader artifacts,
populates the native correspondence sheet and sends its value to the controller.
`episode.credit` uses the same projector. The default A101 return carries the
host-filled `sequence_credit` fact. Plain assessments and interpretation labels
do not contribute to this scalar.

`a101_scoring.py` implements the convention-015 **native correspondence channel**:
`1-exp(-0.020*max(B,0))` for HMMER domain bits, and
`1-exp(-0.025*max(B,0))` times the declared identity mixture for protein BLAST
HSPs. Both include actual paired-reference coverage. The sheet uses a maximum
at each supplied-target position, averages included algorithm channels and uses
a geometric mean over explicitly required regions. Repeated or overlapping
hits therefore do not add independent votes. Whole-sequence and domain bits
are not added. Included empty analyses remain in their algorithm profile.

The constants are a declared numerical convention, not calibrated probabilities.
This native score measures correspondence on the supplied scope. It does not
assert a particular function or biological completeness. Function-specific,
feature-qualified and full-target indices remain separately unknown when their
grounded inputs are absent; a hit label or conserved-site count does not fill
those missing operands. The entire research R1–R7 functional-transfer compiler
is not claimed implemented. Unsupported profiles, missing retained graders,
missing bits and missing exact maps raise explicit scoring-unavailable errors;
they do not fall back to the finding counter or become invented zero grades.

For an A101-only receiving root, construct the ordinary runtime with
`a101_investigation.create_a101_workflow(...)`, supplying the existing service
assembly, resources, controller factory and `initial_known_record_refs`.
This factory installs the numerical root binding and receipts, and rejects an
attempt to replace it with the generic counter. The A101 child chooses this
projector automatically even when a general child fallback is a finding counter.
Other evidence axes retain their separately configured credit policies.
The receiving root calculates from its own admitted records, rather than
adding child scores or reading unreceived shared-state observations.

Saved native results can be rescored without tools, models, or changes to the
original trace:

```bash
PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/runs/a101-rescore/tmp" \
  XDG_CACHE_HOME="$PWD/runs/a101-rescore/cache" \
  python -m gene_annotation_episode.a101_replay \
  --source-run runs/previous-real-run \
  --work-directory runs/a101-rescore/working \
  --output runs/a101-rescore/score.json
```

The rescore report preserves the original recorded credits alongside the new
native projection and explicitly records that it is not a live rerun.

## Verification

Reusable inputs and helpers live in `tests/fixtures/a101/`,
`tests/a101_subtree_fixture.py` and `tests/a101_native_return_fixture.py`.
The functional examples in `characterization.txt` are explicitly invented.
The `real/` fixtures retain actual public UniProt sequences and provenance for
native positive-hit and empty-search return-boundary checks. Additional examples
cover the LacY lactose permease (P02920) and ATP synthase gamma subunit AtpG
(P0ABA6). These targets enter as anonymous amino acid sequences and search the
same three-reference panel, which excludes exact target sequences. Their
nonidentical homologs are LacY P18817 and AtpG Q9KNH4; the panel also contains
TPI Q8ZKP7. Native graders automatically supply correspondence credit to the
owning A101 episode and its receiving parent. Function-specific support remains
unassessed: a sequence match alone does not demonstrate transport activity or
an assembled, functioning ATP synthase. Tests run offline from retained inputs.
The native return fixtures assign one phmmer CPU thread, 1 GiB of memory and
64 MiB of scratch per job. Before each new decision, annotation, A101 and launch
episodes receive host-supplied `resource_context`: the shared local budget,
reserved and available capacity, and actual execution capabilities with their
job limits. The scientific prompt displays this context. Native starts reserve
capacity atomically across registries and runs; the default host budget permits
one active job and one CPU. A busy result preserves the original prepared job
for retry. See [local resource coordination](LOCAL_RESOURCES.md) for configuration
and recovery behavior. Resource selection in these cases remains scripted;
separate real competing-launcher tests exercise admission under contention.
Decisions and continuation horizons are scripted engineering inputs. The
integration executes
actual local phmmer, native acquisition,
source reading/extraction, selected-site calculations, reasoning commitments,
typed forms, findings, receipts and archive/recovery paths.

The cases cover a closest homolog with a misleading specificity residue, an
unseen required site in a fragment, missing original traceback, repeated result
acquisition, unchanged monitoring, partial acquisition and interruption after
native submission. They verify engineering behavior and the explicitly stated
case distinctions, without claiming model-driven biological validation.

Run from the repository root in an environment with the project dependencies and
pytest. Put the environment itself, if newly created, and all temporary/cache
paths beneath the run directory. The native integration uses the retained local
phmmer executable under `resources/software/infernal-1.1.5/hmmer/src/phmmer`.

```bash
mkdir -p runs/a101-check/tmp runs/a101-check/cache
PYTHONDONTWRITEBYTECODE=1 TMPDIR="$PWD/runs/a101-check/tmp" \
  XDG_CACHE_HOME="$PWD/runs/a101-check/cache" \
  python -m pytest tests/test_a101_investigation.py tests/test_a101_subtree.py \
  tests/test_a101_return_contracts.py \
  tests/test_a101_real_sequence_examples.py \
  tests/test_resource_result_receipt_preparation.py \
  --basetemp=runs/a101-check/pytest-tmp -q
```
