The single authorized read-only transaction found **46 original child action records for decisions0–45**. It does not inspect any later decision, scientific commitment body, whole model request/response, private provider log or diagnostic artifact body. The capture window was `2026-10-22T12:13:01.858224+00:00` through `12:13:01.916129+00:00`. The connection used `mode=ro`, `query_only=1`, explicit `BEGIN`, `total_changes=0`, and was explicitly rolled back/closed in `finally`. Active WAL was not opened with immutable semantics. DB/WAL/SHM metadata is retained without claiming concurrent-writer equality.

| Bounded original outcomes | Count | Recorded credit |
| --- | --- | --- |
|completed |24 |all nonnull |
|partial |1 |nonnull |
|failed |19 |all null |
|unavailable |1 |null |
|invalid |1 |null |
|missing/pending action result |0 |not inferred |

This separately measures the21 noncompleted records; it does not infer failures by subtracting earlier aggregate counts. The partial record is original reasoning decision12; no reasoning content or partial scientific meaning was queried.

The19 failed records are decisions27–45, each a selected `public.literature.read` with safe recorded feedback category`provider`, code`provider_http_500`. They have the same opaque selected-action SHA256 `2ebac03fe35efe596510980ac13215ca66c2c449d2736c693b39221bb1633bd9` and argument JSON-text SHA256 `08a2ac70a548b3d11b7b3e05b4904dd2b7ec09c7ef20b5beb81ad124c87413ff`. Their distinct actual operation refs are counted in `RESULTS001.json`. No argument body, publication ID or scientific meaning was exported. The recorded code alone does not diagnose the upstream cause, request appropriateness or service behavior.

Decision0 is unavailable `source.pdf.info`, category`execution`, code`pdfinfo_not_configured`. Decision23 is invalid reasoning; its next raw/model technical feedback category is `record_contract_error`. Its reasoning/commit body and detailed record errors were not queried, so no scientific or schema-repair diagnosis is made.

Every one of the20 failed/unavailable **tool** actions has:

- the original outcome feedback object hash equal to next raw`context.feedback`, next model`model_presentation.context.feedback`, and raw/model`last_local_outcome.feedback` hashes;
- matching original operation_ref in the next raw/model last-local-outcome;
- the same safe category/code fields in those views;
- a present next saved call within the explicit maximum46.

All46 bounded actions have a next saved call, and raw/model top-level feedback hashes agree for all46. No whole request or response was fetched: SQL projected only these technical fields and opaque hashes, plus response-nullness. All46 next responses were nonnull at the snapshot. A nonnull response does not prove a later selected action, scientific return or completion.

Exact evidence pointers: `CAPTURE001.json#/rows/0` covers the unavailable tool; `/rows/23` covers invalid reasoning; `/rows/27` through `/rows/45` cover the19 recorded provider failures. Within each row, `outcome_feedback_{category,code,sha256}`, `next_raw_feedback_*`, `next_model_feedback_*`, `next_raw_last_feedback_*` and `next_model_last_feedback_*` supply the comparisons. `action_text_sha256` is original action TEXT hashed opaquely inside the SQL projection; `arguments_json_text_sha256` hashes SQLite's extracted argument JSON text, without returning it. The captured query and parameters are recorded verbatim under `/provenance/query` and `/provenance/parameters`.

No lost failed-tool feedback was reproduced. The records show separate selected own actions with repeated argument identity; they do not establish a hidden retry loop. Current frozen007 `DecisionSource.execute` stages credit/completion only for completed/partial outcomes, and `FeedbackEpisode._acquire_unit_async` retains the unchanged controller decision after `ActionFailure` while exposing its feedback. Thus failure records do not supply invented local observations or another stopping law. This is the existing accounting boundary, not a new diagnosis that the configured numerical controller is incorrect. No additional cap, cancellation, forced closure, approval, automatic retry or scientific correction is proposed.

The runtime source read for this technical interpretation was frozen007 `gene_annotation_episode/runtime.py`, SHA256 `e2e7e4f328f858f961794a13d556611bae620e6dffc8217c615d4a11611a040e`: complete failure wrapper at513–525, next-decision feedback assembly1030–1105, actual outcome/credit/completion gating and original action recording1220–1290, and complete `local_outcome_preview` at2323–2375. The same source bytes and root's initial locator remained unchanged. The first locator's0commissions/returns observations were not extended here; this capture makes no new return or parent-receipt claim.

No concrete runtime implementation defect is supported by this bounded diagnostic. Diagnosing the recorded HTTP500 cause or judging the episode's repeated selection would require a separately scoped inquiry; neither is silently performed. The active investigation remains untouched.
