# Initial construction performance

Attempt003 used the30second pytest faulthandler diagnostic. CPython terminated
with signal11 while printing a stack in urllib.parse; exit139, partial stack
retained in diagnostic-003.log. This attempt supplied no completed integration
result. No local core file was present in the workspace after the failure.

Attempt004 command:

```text
.venv/bin/python verification/tool_graders_bvbrc_alignment_episode_flow_2026-10-25/profile_workflow.py > verification/tool_graders_bvbrc_alignment_episode_flow_2026-10-25/diagnostic-004.log 2>&1
```

The separate diagnostic harness profiled only the first30seconds, then disabled
profiling and allowed the real Workflow to continue. The retained profile has
66,224,588calls in29.617profiled seconds. Draft202012Validator.check_schema was
called781times and consumed24.454seconds. Caller breakdown:

| Caller | Calls | Cumulative seconds |
|---|---:|---:|
| scientific_tool_library._profiles |524|15.801|
| resource_tool_information._contract |89|7.811|
| scientific_tool_library._catalog |162|0.462|
| communication.validate_closed_schema |5|0.043|

The main-thread stack was inside scientific child construction, from
prepare_invocation through _assignment, _information_catalog,
tool_information_contracts and _contract into the JSON schema metavalidator.
The full profile, callers and stack are retained as diagnostic-004.* files.
The parent accepted ownership of a content-keyed bounded validation cache
repair; this test owner changed no production validation or controller code.
The old-code diagnostic test process was terminated with SIGTERM after the
profile was collected, exit143, because a fresh source-pin run is necessary.

Before the next run, the expected native MetaCATS p token was corrected to the
exact retained export value0.00389837142433717. The separately calculated
mathematical p remains0.0038983714243371837. A further negative admission check
adds an unrequested numeric field and expects rejection against the unchanged
original selection.
