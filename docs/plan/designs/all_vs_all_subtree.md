# all_vs_all_blast subtree: build addendum (2026-11-20)

Builds the owner-approved part of the A101 tree for all-vs-all (parent plus four children). The design reasons are in
`all_vs_all.md`; this addendum is step zero of the build: what already exists and is CALLED, what is new, and the shape.

## The approved view (owner's)

```
├─ all_vs_all_blast             a set vs itself: relationships, clusters, family context
│   ├─ launch_local             (small sets)
│   ├─ launch_hpc               (large sets, split into chunks)
│   ├─ monitor
│   └─ results                  grading is automatic: similarity graph, clustering step, family-context sheet
```

## What already exists and is called (not rewritten)

| Function needed | Existing module / service |
|---|---|
| job contract, compile, search space | `forms/sequence_homology_evidence/blast_all_vs_all_job` |
| the one kind derivation and declared-vs-derived check | `blast_analysis_kind.checked_analysis_kind` |
| set parse, digest, chunk ranges, chunk text | `grading/.../blast_all_vs_all_sets` |
| report to edges, completeness, chunk merge | `grading/.../blast_all_vs_all_graph` |
| thresholds, undirected edges, clusters, redundancy groups | `grading/.../blast_all_vs_all_clusters` |
| target-context and hit-list features | `grading/.../blast_all_vs_all_features` |
| feature validation | `grading/sequence_homology_evidence/feature_rules.validated` |
| running a command on a local resource (the one inspection point) | `jobs/resource_local.execute_on_local_resource` |
| PBS batch job from a command and allocation | `jobs/pbs_batch_job.pbs_batch_job` |
| job handle (operand paths inside the job's directory) | `episode_runtime.job_access.job_handle`, `JobAccess.describe` |
| status check, fetch, handoff/closure rows | `JobAccess.check/fetch`, `jobs/job_records` |
| wait for the job's end event | `native_events` service (`wait`) |
| keeping a graded sheet through custody | `grading/sequence_homology_evidence/tool_grading_artifacts.retain_tool_grading` |
| monitor | copy of `execution_progress_assessment` (it diverges from the copy) |

## What is new (nothing existing does it)

- `forms/sequence_homology_evidence/blast_all_vs_all_chunk_job.py`: the chunk of a set and the native job of one chunk
  from controlled values (operand paths inside the job's directory). Both launch leaves call it.
- `grading/similarity_search/sequence_homology_evidence/blast_all_vs_all_sheet.py`: the graph grading and the
  family-context grading as sheets, the finding rules, and four owner-decision-D18 measures the existing features do
  not give: nearest member of the top function, nearest member of another function, the share of the cluster the target
  links to directly (core versus outlier), and the nearest identity outside the cluster (separation).

## Shape

- `all_vs_all_blast` (parent, code-decided, asks no model): commissions one launch child per chunk, then (HPC only) one
  monitor visit per chunk, then `results`. Its credit is the launches handed off plus what `results` earned.
- `launch_local` / `launch_hpc` (code-decided): build the chunk job from controlled values, check its kind, launch,
  end at handoff. The HPC leaf takes the scheduler allocation and the executable digest from its own settings (D19) and
  is validated offline only (the owner authenticates before any Aurora run).
- `monitor`: the copy of the generic monitor (model-driven, as it ran for real).
- `results` (code-decided): waits for each chunk's end event, then ONE coupled step fetches every chunk's report, merges
  the graph, records completeness, clusters, reads the family-context features and keeps both sheets through custody.
  A chunk whose report is missing makes the graph incomplete, never "no relatives".

Commission fields, the credit and the return follow `all_vs_all.md` sections 3, 7 and the owner's decisions D8, D17,
D18, D19 and I8. Open: who creates the set record with its function labels (the test world supplies it).
