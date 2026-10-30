# Factual integration scope002: evidenced replay repair and test formats

Additive to unchanged scope001 SHA639a5bc3833be3a74b457afc92e5214788e0c91a8f6360b05da51fbb9a9cc256.
No earlier record is replaced. Source007's first coherent137-file pin was
d39a6756507bacd8e9ba90f75912cc01822a316f766cc72764154b7205ba81e3.
The final69 validation,44 runtime and4 detached reconstruction passes retain
their actual pins and evidence. They did not establish all compatibility paths.

Root's separate215-case unchanged-consumer invocation finished209pass/6fail,
0errors/0skips in506.948s. Exact retained command, XML, all raw fixtures, source
before/after and original-file guards are in
/tmp/factual-frame007-root-checks-20261022-o2gix27z. Required source and original
inputs did not change during that invocation. The separately owned NEW Q test
changed outside that invocation's inputs, explicitly recorded in RESULTS.json.

## Real defect and narrow repair

test_direct_observe_without_unit_identity_keeps_legacy_path constructs the
existing ExecutionContextController without a commission capture callback and
replays an already saved valid v6 record. The old-context branch incorrectly
requires that callback even though no capture is performed. A callback is not
part of the saved fact's identity. This violates scope001's pure saved replay.

Runtime owner changes ONLY the old-v6 condition from requiring both original
selected_frame and capture_current_commission_frame to requiring the original
selected_frame. Keep actual request/frame identities and pair validation. Keep
the callback requirement for NEW, unsaved after-action capture. Add meaningful
NEW runtime tests exercising saved v6 with callback=None through both observe
and observe_unit, with captures/provider/backend work forbidden. No other
production file, format, credit, estimator, invocation or observation changes.

The pre-repair runtime.py SHA is
fecd5fa7e766bd3a13ed46b6bb935f586f9013e2997ba7ea667700e80567a909.
Retain exact earlier source/test bytes before editing; earlier sealed evidence
remains historical. No scientific run uses007; active006 remains untouched.

## Five old format assertions

The other failures are explicit prior-format assertions: two fresh durable
completion consumers expect v5, two fresh durable cases without the optional
current-completion marker expect v4, and one fresh detached presented request
expects outer v2. Scope001 explicitly made these FRESH durable requests v3 and
their factual completed contexts v6 independently of the optional current-CE
marker. Absence of that marker still omits current_completion_evidence; the
factual frames must not fabricate or backfill it. Saved genuine v1–v5 and old
request formats still replay unchanged, separately exercised by the new runtime
compatibility cases. Do not alter production behavior to satisfy these stale
fresh-format expectations.

Root owns narrowly updated assertions/comments ONLY in these two older tests:

| Original path | Exact original SHA256 |
| --- | --- |
| tests/test_completion_evidence_runtime.py | aea8b930bab5badfda03b8da55d15d62f693c945c361b04e5ca1920bce369b99 |
| tests/test_model_context_reconstruction.py | 3780f6f7e06ca59d1601e3214c5cdcc9d4bf3dd18cad9a2db29ec6ea42868d87 |

Copy and hash both originals before edits, comparing frozen006 and original
baseline007. In the first test, advance the fresh durable helper's expected tag
to v6 and assert the paired factual fields. Advance the fresh markerless-current-
completion case to v6 with paired fields, explicitly retaining its no-current-CE
assertions and every saved-replay/raw-observation check. Explain that this is a
fresh durable factual record without CE, rather than relabeling saved v4 data.
In the second test, expect closed outer v3 plus local_commission_frame, verify
its run/pending relationship, and retain every exact original model text/hash,
raw-history/presentation and original handoff assertion. No assertion is removed
to hide changed numerical meaning; no fixture quantity or continuation changes.

Record a NEW GENERATION_TEST_AMENDMENT_007_001.json with this scope's hash, both
original and amended hashes and preserved-original paths. Do not change
GENERATION_BASELINE_007.json. Publication/comparison tools may allow only these
two explicit test changes in addition to scope001's three original source
changes and new frame module. All other old tests/inputs remain byte-identical.

## Parallel work and retest handoff

Runtime owner repairs runtime.py and its own NEW runtime test. Root updates the
two older test expectations, with disjoint file ownership. Q's reconstruction
test/operator stays unchanged. Publication preparation stays nonpublishing
until exact new source pin and final results are available. No old215-case
output or earlier B/R/Q evidence is overwritten.

After both code owners freeze, use the new137-file source pin for the full
affected runtime test, the two amended older modules, and Q's unchanged four
actual detached/replay cases. Preserve first failures, exact tests/source, XML
and raw fixtures. The broader209 prior passes retain their original pin; do not
rename them as new-pin results or add repeated checks into a grand total.
The pure validation producer files did not change; their prior component results
retain their original qualified meanings. Any further concrete failure requires
its own diagnosis before scope expansion. No numerical model, support slot or
scientific completion is adopted by this repair.
