# Launch instruction library

The separate launch instruction collection is
`gene_annotation_episode/launch_instruction_library/`. Its first entries are
`launch-aurora` (HPC), `launch-local` and `launch-api`. Entries have independently
retrievable sections and source references. These are information for iterative
execution episodes, not canned episodes, an execution registry or the scientific
annotation-focus/thought-pattern/tool library.

Every Workflow freezes this collection into `<run>/launch-instructions/` using
the existing ToolKnowledge snapshot backend. The initial decision receives only
`launch_instruction_library` metadata. Callers may supply a different source
directory as `tools.launch_instruction_library_directory`; resumption still opens
the existing run snapshot. Source edits affect new runs, not existing selections
or earlier recorded decisions.

## Retrieval and a specific launch

The ordinary tool catalog provides:

- `launch.instructions.search`: literal metadata search and pagination, with an
  optional exact `resource_kind` filter (`hpc`, `local`, `api`). Empty query browses.
- `launch.instructions.entry`: section index, hashes, listed operations and sources.
- `launch.instructions.read`: exact zero-based line windows from a section.
- `launch.instructions.select`: pin one or multiple explicitly chosen sections.

For example, the parent may select Aurora storage and existing software information:

```json
{
  "kind": "tool",
  "tool": "launch.instructions.select",
  "arguments": {
    "sections": [
      {"entry_id": "launch-aurora", "section_id": "storage"},
      {"entry_id": "launch-aurora", "section_id": "software"}
    ]
  }
}
```

The result is a `launch_instruction_selection_v1` containing this run's library
identity and the exact section IDs and SHA256 values. The parent supplies that
result as `assignment.launch_instructions` in its ordinary `episode_child`
selection, alongside the job, scope, constraints and original typed return form.
No second launch call is required. Existing resource launch and practical
assignment schemas accept this optional field; legacy assignments without it
remain valid.

Before commissioning can prepare native work, the shared runtime verifies the
pins against its frozen library. The child's first decision receives
`selected_launch_instructions: {selection, sections}` with the selected sections'
complete original text and digests. Subsequent new decisions can receive the same
immutable material. An interrupted or completed saved model request keeps the
exact context it originally received. Root resource assignments are validated
before resource initialization too.

When a launch episode commissions its resource child, its inherited instruction
pins must be retained. It may explicitly add further sections. Reads remain
available during investigation; no manual, read, selection, setup sequence or
resource order is mandatory. Sections may be combined from several entries.

## What each record establishes

| Record | Meaning and authority |
| --- | --- |
| Launch instructions | How particular software/resources can be investigated, prepared, used and diagnosed; source-grounded guidance. |
| Inventory snapshot | What preparations have been recorded, with hashes and observation/availability information; matching catalogs do not establish present usability. |
| Launch assignment and caller binding | Actual requested job, inputs, workspace, charging account, limits, endpoint and selected instruction versions. Instructions cannot override these. |
| Selected status/log/filesystem observation | Actual conditions at the recorded observation time; an old queue limit or balance is not a current measurement. |
| Execution receipt and completion proof | What the selected execution actually did and whether the original validated endpoint was reached. |

Listed tools are references to real operations, not newly enabled capabilities.
Only the current role's actual callable schemas and caller configuration allow
execution. The API collection now documents bounded `api.hmmer.*` operations in
the wired launch family. `ExecutionServiceFactory` installs the caller's explicit
API/local/HPC resources with recursive monitoring and results; instruction
retrieval itself does not authenticate, submit work or configure a resource.

Library tools return the ordinary outcome envelope with empty scientific record
arrays. They use existing own-action accounting, normally zero credit. Delivering
already selected instructions adds no action, observation, scientific evidence,
timing measurement, model call or credit. Existing controllers, typed child forms
and practical terminal expectations retain their existing meanings.

Unknown sections, foreign library identities, wrong section digests and altered
snapshot bytes fail explicitly. Valid other sections remain available. Selected
instructions never authorize replacement of an unknown or active native job.

Saved runs keep their original instruction snapshot and original catalog at each
saved call.
