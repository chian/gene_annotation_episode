# A105 transport reference display: synthetic fixture correction

This is an implementation verification record, not a goal amendment, a new
scientific template or evidence that A105/W04 is complete. No paper or retained
paper-specific packet was opened. No live model call was made. All new runtime
sources and controlled RPC payloads are synthetic fixtures.

## Correction to the initial diagnosis

The initial suggestion that the observed failure required a production renderer
repair was incorrect. It was based on a manually assembled synthetic reference
that omitted generation provenance. The actual persisted path preserves that
provenance, and the existing renderer already distinguishes the host-generated
accession from external scientific identifiers. The proposed contextual/legacy
fallback was withdrawn before any production mutation.

The original provider-transport test fails at its no-accession assertion on
immutable `a105_primary_active_site_review_151/pin_001` as well as the current
checkout. The pin151 reproduction produced **1 failed in 2.32 s**. The two
relevant prompt/display modules are byte-identical between pin151 and this
checkout. This establishes that the test failure preceded the concurrent six
storage fixes; it does not establish a production prompt failure.

The preserved original test is
`test_literature_transport_integration.original_001.py`. The only change to its
working counterpart adds `origin: tool` and an explanatory comment to the
synthetic transport-curve reference. The assertion forbidding its generated
accession remains unchanged. This aligns the fixture with the record that
`Store.put` actually creates. It does not teach the renderer to guess provenance
from an arbitrary hash-shaped string.

## Inspected ownership and complete relevant paths

Authority read: root `AGENTS.md`, the full original supplied goal attachment,
`docs/TASK_AND_STEERING.md`, and the W04 evidence-axis amendment. `GOAL.md` was
not read. Production changes, biological scoring, schemas/provenance writes,
W05, controllers and goal amendments are outside this workload.

| Path | Inspected responsibility and finding |
| --- | --- |
| `literature_transport_inputs.py` | Complete selected transport input reader and schema. `_context` computes `transport_curve_<64 hex>` from source-bound context witnesses; this is a custody identity rather than a public accession. |
| `literature_transport_storage.py` | Complete writer, replay, read, projection and return schema. `populate` publishes curve references through `Store.put(..., origin="tool")`; exact curve keys and witnesses stay saved. The typed return carries reference bindings and numerical cells, not curve-key hashes. |
| `state.py` | Complete relevant `put`, `get`, `query_records`, `reasoning_view` paths and origin validation. `put` always saves origin in record JSON. The readers preserve that field; there is no legitimate missing-origin transport record produced here. |
| `materials.py` | Complete `model_record_view`. The ordinary transport assay reference returns unchanged; member-label previews also do not drop origin. |
| `episode_services.py` | Relevant full record/scope, repository and own-outcome methods. `read_record` delegates to `Store.get`; it does not strip provenance. |
| `literature_episodes.py` | Relevant complete selected-operation validation/execute, initial/continuing decision contexts, received-fact hook, transport fact-source/route, fact projection, validation and admission methods. Received in-scope records retain full stored metadata independently of working-state pagination. |
| `literature_rate_storage.py` | Relevant complete inherited saved read, ownership, projected fact validation, received-cell admission and replay paths used by transport. Saved numerical cells retain the original meanings and exact requested membership. |
| `literature_experimental_prompt.py` | Shared `_safe`, scientific record selection, dependency closure, full TASK/STEERING construction, source-result rendering and ordinary typed-return dispatch. The authenticated received map is preferred; the working-state fallback preserves complete records too. |
| `literature_received_fact_render.py` | Complete renderer. `_generated_accession` requires the inspected generation family plus actual record kind/origin (and term namespace where applicable). `render_records` removes a generated accession while retaining source relationships and scientific meaning; an explicit external origin preserves the same hash-shaped string. |
| `literature_reference_parent_prompt.py` | Complete parent TASK and shared STEERING boundary. A child return remains evidence under the parent's own task. |
| `scientific_process_prompt.py` | Complete helper implementations used here: text instruction normalization and schema/band rendering. They do not rewrite these stored scientific records. |
| `decision_context.py` | Complete state/frame copying, hashing and reconstruction. It preserves origin rather than rewriting a scientific record to satisfy a display test. |
| `providers.py` | Complete relevant session `complete`, `_presentation`, bootstrap/update/lookup reconstruction and turn dispatch paths. Actual transport receives rendered text with the original output schema separately. |
| `runtime.py`, `episode_bindings.py`, `communication.py` | Relevant working-state, outcome receipt, binding/context and exact typed-fact composition/validation consumers. No changes were made to these consumers or their accounting. |

The production chain is therefore:

`selected literature operation -> source-bound curve identity -> tool-origin
stored reference -> working-state/received metadata -> selected received
scientific records -> local display labels and source meanings -> provider text`.

No step in that chain requires a production fallback for missing provenance.

## Added verification

Owned files are `tests/test_literature_transport_integration.py`, the new
`tests/test_literature_transport_reference_display_158.py`, and this directory.
Production source files are unchanged by this workload.

The new runtime pair commissions the existing literature child, selects the
actual quantity and transport population operations, and observes both a
same-curve response and a different-preparation/different-curve result. Every
actual runtime decision input also traverses the real provider presentation and
`turn/start` transport using `LiteratureWire`'s controlled RPC implementation.
`ScriptedProvider` supplies the selected actions; no model interprets science.

The child selects a real source read after receiving its owned transport result.
The parent receives the ordinary typed form and commits a source-subject record
anchored in the synthetic source. These are completed selected actions, not
empty reasoning or fabricated target assessments. The asserted ordinary counts
are root 2 + child 3 = **5 observations**, **one** transport population and
**one** transport receipt. All local gains and final scientific credit are zero.
Provider rendering and reconstruction leave those counts unchanged.

The tests assert that the actual saved curve record equals its working-state
and authenticated received-map copies in both child and parent contexts,
including `origin: tool`. Its host accession and record ID stay out of the
result STEERING while curve labels, source-response scope, native Km 12 uM,
uncertainty meaning, synthetic origin and same/different-curve qualifications
remain. The child receives the substantive transport TASK, and the parent keeps
its own substantive TASK. The exact runtime output schema remains separate.

The persisted-operation pair tests both the real received-map path and the
working-state fallback. Explicit external records retain `P12345`,
`RHEA:12345`, and custom strings with exactly the generated-looking
`transport_curve_<64 hex>` and `native_rate_subject_<24 hex>` shapes. The source
condition/endpoint text `pH 7.5; 50 mM buffer; endpoint <0.2 U/mg` survives.
These identifier spellings are synthetic test operands, not fetched catalog
entries or claims about real molecules.

The original typed form is validated and preserved. Before descriptor
recomposition, the tests restrict artifact access to the saved transport and Km
sheet/request artifacts, forbid the transport input reader/calculator, and set
SQLite to query-only. Recomposition, operation replay, fact projection,
decision-state reconstruction and provider rendering then reproduce the exact
original outcomes/forms/text. Neither original source bytes nor covariance
bytes are reacquired, and no observation is added. Saved reference records stay
unchanged.

## Development checks

- `run001`: original transport tests passed after the provenance correction;
  the first new runtime fixture used empty reasoning and failed before an
  additional completed action. No successful accounting claim is based on it.
- `run002`: the new child source-read path completed; the root callback's
  unsupported source-read selection exhausted the script. It was replaced with
  the actual anchored source-subject commit used by the final fixture.
- `run003`: **4 passed in 29.37 s** for the four new tests, including the
  source-free guard installed before factory recomposition.
- Final focused regression is recorded in `FOCUSED_001.log` and
  `FOCUSED_001.xml`; its result is appended after completion.

This verifies synthetic custody, presentation, numerical meaning, typed return
and reconstruction behavior. It does not demonstrate model-backed scientific
extraction, new paper evaluation, an adopted scoring formula, general scientific
success or completion of W04.

## Frozen test bytes

The parent froze these test versions in its independent pin004 verification.
The new test uses only the existing helper modules
`test_runtime.py`, `test_literature_experimental_prompt_delivery.py` and
`test_literature_transport_integration.py`; it introduces no production helper.

| File | SHA256 |
| --- | --- |
| Corrected `tests/test_literature_transport_integration.py` | `64b4f1f2a3d231188dd8be938d999ee30b63adb0bba4132d906ebf186e0ca0bf` |
| New `tests/test_literature_transport_reference_display_158.py` | `433734dcecca4b96ac6172addf95a5714de24a02ae8e55647805b29b2d84e445` |
| Preserved original transport integration test | `28bc38935fc65c5b3cc59d9a898032acbb3e01569b020918ba81c9f77edc8bd5` |

Production prompt/display/writer hashes inspected here, unchanged by this work:

| File | SHA256 |
| --- | --- |
| `literature_experimental_prompt.py` | `d0dba96cb10fc75b718adaa186f2f77af62d2a9cdc1407f3eb1fea67240db88e` |
| `literature_received_fact_render.py` | `a09afa073b3407e2105a7c4b3299982d407b12b1b3ac4be4774b6ccb796bcb4b` |
| `literature_transport_storage.py` | `3158ef8337cf90f8f8d23d2fa28bb9a62f41a1ccf6adbe3adcea1f2b31fb02c8` |

## Final focused result and separate existing fixture failure

The final focused command ran the transport integration, new158, transport
storage, received-fact semantic prompt, experimental prompt delivery and
reference-parent prompt files. It completed **86 passed, 1 failed in 168.79 s**.
The exact result is in `FOCUSED_001.log`/`FOCUSED_001.xml`; this record does not
claim an all-passing context group.

The corrected original transport test, all four new158 tests, and the transport
storage, received semantic and reference-parent checks passed. The one failure
was the separate
`test_literature_experimental_prompt_delivery.py::test_only_enabled_literature_binding_supplies_experimental_marker`.
Its `EmptyServices` double lacks `provider`, so the already-existing
`source_meaning_projection` repository check raises `AttributeError` before the
marker assertion. The same isolated test was then run on immutable pin151 and
failed identically: **1 failed in 1.21 s**. Thus this additional failure also
predates this fixture correction and the concurrent six storage fixes.

No change was made to that separate test/helper or its production consumer; it
is outside158's declared ownership. The parent was notified with the exact
failure and the independent pin151 reproduction. The final158 test hashes above
remain unchanged.
