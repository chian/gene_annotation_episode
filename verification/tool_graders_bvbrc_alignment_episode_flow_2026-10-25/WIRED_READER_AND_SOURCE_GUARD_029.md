# Saved reader and integration source guard verification

These checks use the closed MSA run `runs/msa_dna-_7cous9_` as historical evidence. They do not start a Workflow, model, native scientific process, remote BV-BRC request or HPC job. Original run009 remains unchanged. Its pytest fixture error and the absence of executed test bodies remain recorded in `RUN_TERMINAL_023.json`.

The production owner connected the saved-publication reader in `BVBRCAlignmentReturns._latest`. Diagnostic 027 constructs the real API execution binding against a private copy of the original state, then enables SQLite query-only mode and blocks network connections, subprocess creation, native parsers and scientific calculators. It compares the wired reader with the original retained publication, full sheet and full components. It also compares requested facts with the frozen results and scientific forms and with the original scientific-to-root admission.

| Actual call | Wall seconds | Full publication reads |
| --- | ---: | ---: |
| Wired latest, cold | 5.563 | 1 |
| Wired latest, warm | 2.727 | 1 |
| Original requested results facts | 2.851 | 1 |
| Scientific receiver facts | 5.646 | 2 |
| Root receiver facts | 5.726 | 2 |

The two receiving reads correspond to the original result delivery and its actual unchanged redelivery. Every retained body/sheet/components comparison and requested fact comparison passed. The six measured runtime table counts remain 25 actions, 26 model calls, 25 observations, 5 report attempts, 4 frozen forms and 239 record receipts. Before/after SHA256 manifests of the entire original run are equal. The exact numeric examples remain four members, 28 cells, gap fraction 6/28, selected column entropy 0.9182958340544896 bits and native score 92.

Diagnostic 026 is preserved as a harness failure. Its reader and scientific-receiver comparisons succeeded, but its final root check incorrectly assumed that the root had an outbound typed report contract. The root has no outbound form. Additive diagnostic 027 reads the actual scientific-to-root admission contract and form instead. No production behavior was changed for that correction.

Exact diagnostic command (exit 0):

```sh
.venv/bin/python verification/tool_graders_bvbrc_alignment_episode_flow_2026-10-25/verify_wired_saved_reader_027.py > verification/tool_graders_bvbrc_alignment_episode_flow_2026-10-25/wired-saved-reader-027.log 2>&1
```

Detailed counts, input/source hashes, expected source changes since run009, blocked symbols and returned values are in `wired-saved-reader-027.json`.

The integration test now keeps a broad before/after source inventory but enforces equality on this exact used-source union:

- Workspace-owned Python module files loaded at the start or completion, including later imports; bytecode paths are normalized to source paths. Installed packages in `.venv` are environment inputs, whose interpreter identity is already recorded.
- The shared MSA/MetaCATS facade dependency list and the scientific construction implementation list.
- This test and its seven explicit helper modules.
- Every file in the configured scientific publication, the selected case's retained native source files and receipts, and the packaged application manifest plus the selected application's original and derived definition files.

Every used file must have its original BEFORE hash. Changed or deleted used files fail. Later-loaded files without a BEFORE hash also fail. All changed or added paths outside this union remain in the broad manifests and are logged separately. Both configured facade hashes, the actual scientific binding hash and API configuration are independently checked at Workflow closure and after the four test bodies for that case. The production prompt renderer and wired saved-reader helper are included as loaded modules. This is a verification assertion, not an episode action, continuation rule or runtime gate.

Eight checks of the actual guard passed using disposable real files in `guard-check-028`: unchanged inputs; changed used source rejection; deleted used source rejection; changed unimported source acceptance and logging; added unimported source acceptance and logging; changed later-imported source rejection; later-imported source with no BEFORE hash rejection; and restoration of used files while unrelated changes remain logged. The verification saw 223 used paths and 815 broad baseline paths. It changed no production file and launched no Workflow.

Exact guard command (exit 0):

```sh
.venv/bin/python verification/tool_graders_bvbrc_alignment_episode_flow_2026-10-25/verify_source_guard_028.py > verification/tool_graders_bvbrc_alignment_episode_flow_2026-10-25/source-guard-028.log 2>&1
```

`source-guard-028.json` retains each actual guard result and the test hash. Collection also passed with 12 tests in `collect-028.log`. Collection is not execution. The negative prompt assertion remains unchanged. No new full Workflow started while the production owner was correcting the demonstrated source-envelope exposure in scientific STEERING.
