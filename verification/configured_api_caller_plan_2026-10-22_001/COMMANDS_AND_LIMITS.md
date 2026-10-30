# Planning invocations and retained limits

All successful validation here used only filesystem reads, stdlib JSON/TOML/hash derivation and jsonschema representation validation. No application import/constructor, state DB open, pytest/application run, HTTP/model/native call or actual fork/preparation/launch occurred. There is no passing caller implementation/test claim.

Artifact derivation command (cwd this bundle):

```sh
/home/chia/repos/gene_annotation_episode/.venv/bin/python derive_proposed_inputs.py
```

Final offline check command (cwd this bundle):

```sh
/home/chia/repos/gene_annotation_episode/.venv/bin/python verify_plan.py > VALIDATION.json
```

Both exited0. DERIVATION_CHECKS.json and VALIDATION.json retain actual final structured output. Schema checks deliberately show exactly the two null blueprint fields fail runnable-parameter validation; no substitute committed refs/native registry was fabricated. SOURCE_INVENTORY005.json and INPUT_IDENTITIES.json retain actual frozen source/test/static identities. READSET.json distinguishes full source reads, complete affected consumer methods, prior unchanged same-session reads, inventories and current test references. An inventory is not a claim every source file was read.

Earlier exploratory read failures are preserved here as narrative because original raw stdout files were not saved, not reconstructed as pretend logs. One combined read was mistakenly run from main rather than005:

```sh
cat cases/gene_001/case.json
cat cases/gene_001/evidence-refs.json
sed -n '114,180p' gene_annotation_episode/case_execution.py
sed -n '219,257p' gene_annotation_episode/resource_estimation.py
sed -n '72,98p' gene_annotation_episode/public_search_operations.py
```

The final command exited2 because that API module is absent from old main. Correct actual005 estimator/client-binding paths were then read. A separate rg invocation with the nonexistent wildcard `reference/episode_tools/episode_tools/*.py` exited2; actual LocalJobPolicy lives in gene_annotation_episode/local_jobs.py and was read there. No application/test work followed either failed read. Combined large cat outputs sometimes exceeded tool output budgets; relevant test references and complete needed caller factories were reread individually before this final proposal. The final READSET states actual coverage without treating truncated output as a full-file read.

A pre-final static derivation initially compared the old policy remainder to its own copy, which would not establish old-vs-proposed preservation. The script was corrected before freeze to derive the second remainder independently from actual PARAMETER_BLUEPRINT.template.policy; their canonical bytes and SHA now match. No production code/state or tests were affected. Future code verification must preserve actual first failing test output rather than repeating this narrative-only limitation.

Future006 baseline and test invocation identities must be captured afresh after exact root adoption and before mutation/test launch. Current005 pin2c9dc895... and static319 verify the proposed input baseline only. Code006 does not exist and has no source hash yet. The particular-profile API client binding is a stdlib source-derived descriptor, not an actual network-service availability test. A real new caller needs separate successful C output and NEW preparation before final parameters/input hashes can exist.

A later source-only cross-check also named nonexistent working_state.py/knowledge.py while locating context consumers; rg printed missing-file diagnostics (the surrounding head pipeline exited0, so no clean rg-success claim). `rg --files gene_annotation_episode -g '*working*' -g '*knowledge*'` identified actual tool_knowledge.py; working_state/annotation_context are runtime.Workflow methods and their complete methods were then read directly. No new consumer or source expansion was proposed. This exploratory lookup is not an application/test failure.
