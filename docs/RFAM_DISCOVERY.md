# Sequence-driven Rfam discovery

`public.rfam.search {"subject_ref": "<registered sequence>"}` discovers reported RNA-family matches through the current public Rfam batch API. A known Rfam accession is not required. `public.rfam.collect {"job_ref": "<existing Rfam job>"}` addresses an already accepted discovery job after an interruption or transport failure. These are ordinary selected tools. They neither classify the target, choose a family for a later investigation, create an annotation, add an Episode nor alter credit or numerical continuation.

## Scientific meanings and limitations

The actual submitted operand can be an original input, a mapped feature/product or a registered external evidence sequence. Original-input work respects its assigned scope; the adapter does not silently crop a whole operand into a child's segments. External evidence remains source-only material and never becomes a new credit target. Declared protein is incompatible with this nucleotide operation. Unspecified caller material uses the explicitly selected RNA/nucleotide processing model without rewriting its original molecule declaration, and DNA T is submitted unchanged. No identity-view or classification action is a prerequisite.

Every native hit remains in the actual result source, including overlapping hits, reverse-strand hits and weak reported matches. Independent malformed rows produce precise partial-projection feedback while preserving the raw source and all independently valid projected rows. No additional hit-score threshold, family preference or biological acceptance rule is introduced. The ordinary result previews twelve projected rows explicitly; all typed observations remain queryable and the complete native hit/alignment data remain readable through `source.read` on the returned `source_ref`.

Projected observations are `profile_match` measurements associated with an actual source-bound family reference. The family label/accession are provider assertions, not target function or an actual physical reference RNA. Family `sequence_ref`, `molecule` and `length` remain null. A discovery family reference is not itself an acquired ASCII covariance model for native `rna.cmsearch`; selected model acquisition remains available separately when useful.

Native one-based inclusive `start`/`end` become the physical submitted-sequence interval `[min(start,end)-1,max(start,end))`, with native endpoints and strand retained separately. The observation's operand identifies the actual searched subject, its real physical unit and nucleotide processing-model unit. Alignment `#CM` positions stay in the native source/display; they never become physical family-reference residues or length. For the saved example, the submitted physical interval is 119 nt while the current model display ends at consensus position 120. These are distinct axes.

The current API response does not expose a database release, model release, Infernal version, complete native command or search thresholds. Those values stay unknown; the adapter records `provider_defaults_not_exposed` instead of borrowing local `cmsearch` defaults or the documentation example's old model. It preserves native `opened`, `started` and `closed` strings exactly. The actual saved calibration has opened/started one hour ahead of closed, so no duration or corrected clock is inferred. Zero reported hits mean no reported match in this submitted operand under the service's unexposed defaults; they do not establish organism-wide absence or absence under every RNA model.

## One durable protocol path

The adapter extends the existing `RemoteSearches` framework and its single protocol-wait loop. HMMER and BLAST use this same owner with their own native identity rules. Provider-specific collect/page entrypoints check job ownership before selecting a parser. Rfam returns a complete result and exposes no result-pagination interface here.

A durable intent commits before the one POST. The documented multipart field is `sequence_file`; its file contains the exact selected sequence under a fixed wrapper name, never an Episode-provided host path or URL. Exact multipart bytes, body hash, request headers, URL, actual response bytes, HTTP metadata and retrieval time are retained. The returned `jobId` and `resultURL` must identify the same actual job on `https://batch.rfam.org/result/`. A caller cannot supply an arbitrary provider URL. Successful result publication checks actual `jobId` and returned `searchSequence` against the committed request, retaining contradictory responses as actionable diagnostics rather than attributing them to the target.

A short caller-configured protocol delay precedes the first result GET, as requested by the official API. HTTP 202 `PEND`/`RUN` responses wait on that same known job. Protocol polls are not scientific actions or yield observations. Network calls run off the Store/event-loop owner thread; durable job transitions and scientific publication occur on the owner thread without a write transaction around network work.

Cancellation after acceptance retains the known handle. An ambiguous interrupted/failed POST is never silently repeated. Explicit collection can recover an accepted job after a later transport/representation failure. A committed tool-operation replay returns its saved result without another request or scientific publication; runtime replay does not invent another completed-action observation. A separately selected successful collection remains one ordinary read of the saved measurement, with no duplicated evidence credit. Historical failed tool attempts remain failed.

Documented Rfam GET HTTP 410 means native job `DEL`: it is retained in complete job history but excluded from `public.search.jobs` active-only results. The exact failure and handle survive. An unambiguous HTTP 503 body `HOLD` records the nonterminal native hold state; unrelated HTTP errors do not imply deletion or rejected submission. `collectable` means that a handle/cache is addressable through the interface, not a promise that an expired/deleted remote result can be recovered. Remote lifecycle termination is operational information; it neither completes the annotation goal nor stops the Episode. Failed/unavailable result retrieval creates no completed-action observation.

For a submission HTTP 400 with the exact recognized native `detail` sentence
reporting a nucleotide length maximum, existing owner feedback adds a typed
`cause.provider_feedback` projection. Its version is
`rfam_native_submission_feedback_v1`; fields identify the native `detail` basis,
`maximum_length`, actual `submitted_length`, `unit: "nt"` and the boolean
`submitted_exceeds_reported_maximum`. The number comes from that response, not a
hardcoded host preflight limit. Unknown, malformed or numerically unrepresentable
details retain the generic error and exact diagnostic bytes. An arbitrary HTTP
400 does not acquire length semantics, and a reported limit does not imply that
the submitted sequence actually exceeds it unless the lengths establish that.

The actual saved 2026-10-20 response reports 7,000 nt for a 32,098-nt query. This
structured reason now reaches the responsible Episode through its failed action,
job listing and reopened job cause. The original HTTP code, exact response and
multipart request, unknown POST outcome and absent accepted handle remain as
recorded. The adapter neither crops nor resubmits, chooses a view, adds a
scientific gate, awards credit nor supplies a failed-action yield observation.
An Episode can explicitly select `sequence.view` if it chooses a smaller operand.
Old saved failures are not retroactively parsed or rewritten; new failed
submissions retain this typed cause using the actual submitted sequence length.

## Reusable provenance and evidence level

The result source forward-links its actual submission source with `parent_source_refs`. The existing exporter therefore retains both native response bodies and their request artifacts, including exact multipart bytes, without scanning request JSON as a semantic-reference graph or adding a second exporter. Native profile observations preserve the actual submitted subject and source family identities. Raw provider labels do not cross the parent form boundary as unconstrained findings; the existing parent-owned typed form and reference admission remain unchanged.

The full current [official Rfam API documentation](https://docs.rfam.org/en/latest/api.html) was read. A local exact HTML capture and HTTP metadata accompany the tests. The endpoint is `POST https://batch.rfam.org/submit-job`, followed by GET of its actual returned result URL. Rfam documents results as temporary; local committed evidence remains available after remote expiry.

`validation/providers/rfam-batch-calibration/` contains one actual prior protocol calibration performed by the root agent using the documentation's 119 nt example, including submission intent, exact multipart body, raw submission/result responses and response metadata. It is a known example, not the prepared unknown RNA case, a new target search or evidence of annotation accuracy. Tests reuse those saved bytes and separately label synthetic pending, malformed, conflicting-identity, deletion/hold and recovery scenarios. One fixture passes through the actual shared runtime to verify that one selected search plus protocol polls gives one completed-action observation and zero annotation credit. No model invocation or unknown-target search was launched for this adapter build.
