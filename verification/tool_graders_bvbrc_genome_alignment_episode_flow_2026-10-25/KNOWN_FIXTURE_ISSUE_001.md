# Resource-instruction call selection

While original run001 was active, root reported that its separate isolated
candidate Workflow closed and then failed the second test's resource-instruction
filter. This is a reported candidate result, not the terminal result of run001.
The original process, test source, prospective hashes and pins remain unchanged.

Source inspection on 2026-10-25 at 13:34 UTC confirms the cause. Both provider
dispatches in `runtime.py` (lines 912 and 1064) pass the model role `REASONING`
to `provider.complete`. The scripted fixture stores that argument in
`Choices.calls`. The resource-instruction loop in the new test (line 580)
incorrectly filters it against episode roles `launch`, `launch_api`, `results`,
so its selected call list is empty. The actual `episode_id` is retained in every
captured call and decision artifact.

Root is correcting only its isolated candidate to select by the actual closed
episode IDs from `r.launch`, `r.api_record` and `r.results`. This preserves the
intended recurring-instruction assertion. It does not require a production,
prompt, provider-role or method_loop change.

Root explicitly instructed this worker to keep original run001 active and
unaltered, retain its eventual terminal receipt and source guard, and distinguish
this test-selection error from missing execution instructions. Therefore no
canonical test edit or restart is made while run001 remains active. Its actual
terminal outcome will be recorded separately when available; no candidate pass
is attributed to the original run.
