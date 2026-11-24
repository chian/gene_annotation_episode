# The real entry: `run` and `resume` on the application command line

Status: built (2026-11-20): `gene_annotation_episode/run_command.py`, with its subcommands in `gene_annotation_episode/cli.py`.

## The pieces

- `python -m gene_annotation_episode` (`gene_annotation_episode/cli.py`) registers caller material in a workspace (the run's `Store`) with `init` and
  `add-material`, reads it back with `status`, `artifact` and `export`, and starts and reads runs with `run`, `resume`, `report`, and registers the
  run's other inputs with `propose-annotation` and `freeze-libraries` (below).
- `episode_runtime` is a library. A run starts with `link(registry, entry_path, entry_input, run_id=..., journal=..., collaborators=...)` and is
  replayed with `resume(registry, run_id=..., journal=..., collaborators=...)`. The four collaborators are `store`, `model_provider`, `continuation`
  (settings by binding path) and `services` (name -> factory). The runner records everything (commissions, units, model calls, receipts, returns, resume).
- A script written for one test (a world file in a `tests/` folder) is not a real run by the owner's definition, and no such file is kept in the repository.

## What `run` and `resume` are

Two subcommands of the application CLI, in one new module (`gene_annotation_episode/run_command.py`) that `cli.py`
calls. They contain no episode code and no recording or replay code: the system records everything.

`run` takes:

| Argument | Meaning |
|---|---|
| `--workspace` | the `Store` that `init` and `add-material` created (the registered caller material, the held records) |
| `--entry` | the entry binding path, for example `sequence_homology_evidence` |
| `--commission` | JSON `{assignment, message, selection}`: exactly what a parent would send (controlled values and record references) |
| `--continuation` | JSON mapping binding path -> yield-controller settings |
| `--services` | JSON: the `job_services` configuration (local resource workspace and policy, event ledger, estimate table, instruction directories) |
| `--run-id` | the run id |
| `--journal` | the journal file, under `runs/` |
| `--model-calls` | the directory where the model provider keeps its calls, under `runs/` |

It builds the registry from the entry: the entry's folder is found under `episodic_workflow/root/*/` from its
binding path, its binding is imported, and each binding named in `child_slots` is imported the same way, recursively.
Nothing else is imported (so the reference-only `old_*` folders are never loaded). It links the run with the real
`ModelProvider` (the owner's Codex sign-in) and the real job services, runs to the end, and prints a JSON summary:
the result record, why the entry ended, the unit count, the journal path and the model-call directory.

Every command is started through the single-workflow launcher. The local resource of the `--services` file must have
its job folder (`workspace`) inside the launcher's run directory of that command: the local job route refuses a job
whose output would lie outside the workflow's run (`native_output_outside_workflow_run`). The Store, the journal and
the frozen libraries may live anywhere under `runs/`.

`report` reads a run back from its journal (episodes, units, model answers, controller steps, receipts).
`propose-annotation` registers the caller's proposed annotation (one hypothesis record of caller origin), and
`freeze-libraries` is the general run rule that keeps runs tidy: a run reads frozen copies of its libraries, so a later
edit of a published library cannot change a run that has started. It takes the run's own continuation file
(`--continuation`, the file `run` takes) and the published library (`--source`), and for every head that file
names it freezes the head's libraries into the directories that head's settings name, then prints the selection a
parent commissions each head with. `--head experimental_activity_evidence` is optional and narrows it to one head,
named by its binding path (the command takes no axis: the owner, 2026-11-24); `--tool` names the tools to
offer. The command knows no axis: each axis's library module
(`episode_support/configuration/<head>/process_options.py`) supplies `freeze_selection` with its own pieces (A101 and
A105 do today). An axis without one is reported as not frozen and does not stop the others: the rule is a help, not a
gate. These two are the registrations a run's caller makes before `run`; no command reached them before.

`resume` takes the same arguments except the commission (it is in the journal). It replays the recorded run; a unit
already recorded is not run again and no recorded model call is asked again.

A wrong commission fails with its own error and the command prints it (the CLI's existing `operational_failure`
output, exit code 1). There is no fallback, no autofix and no check added for it.

## Why here

The runner is generic and must stay so; the application CLI is where a caller already registers material, so the
caller's next step (run) belongs there. Episode folders stay free of run harness code, and nothing is written into
a `tests/` folder.

## Real-run recipe (the head and its `pairwise_blast` tool)

`pairwise_blast` is a tool of the head (`a101_tree.md`), not an episode.

1. `init` a workspace with the 76-residue ubiquitin target and `add-material` the 78-residue reference.
2. Write the head's commission (its assignment form) and the continuation and services files for the run.
3. `run --entry sequence_homology_evidence` with the real model, through the launcher.
4. `resume` the same run id into a fresh model-call directory: the model is asked nothing and the result is the same.
5. Refusals from the same command: a tool call naming a record the head does not hold; `blastn` on a protein; a repeat of the same comparison.
