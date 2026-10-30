# Source and decision trace for information reply 609

This is a source-inspected proposal, not an execution receipt. Paths and line
numbers below describe the inspected checkout on 2026-10-28. The original user
attachment was read in full; its objective and all ten operating principles
were reread after each substantive inspection unit. `GOAL.md` was not read.

## Actual pending-decision path

| Stage | Actual source | Information and consumer |
| --- | --- | --- |
| Child/source discovery | `composition_information.py:136` `child_options`; `runtime.py:2783` `report_sources`; `execution_episodes.py:2162` `fact_sources` and `:1857` `received_report_sources` | The current child-options table lists source/type/meaning. UniProt is advertised for `results` when the service is bound, and as received facts for `annotation` / `scientific_process`. Discovery alone grants no child role or facts. |
| Permitted choices | `runtime.py:2394` `declared_child_roles`, `:2404` `available_child_roles`; `scientific_process_episodes.py:152` `child_roles` and `:352` `allowed_children` | Existing role edges and caller binding determine which child can be requested. The template must not create a results edge, require a fixed itinerary or pick a resource. |
| Optional information surface | `composition_information.py:23` `contract_metadata_catalog`, `:63` `metadata_catalog`, `:75` `lookup_schema`; `episode_bindings.py:230` `contract_information_profile`; `runtime.py:2230` | Existing grammar is `request_context` → `composition_information` → `episode.return_contract`, with only string arguments `role` and `source`. This is enough to identify the selected information. Its advertisement requires an actual bound profile. |
| Freeze original contracts | `runtime.py:931` `DecisionSource.call`, `:2236` `freeze_contract_information`, `:2246` `validate_contract_information` | Fresh opted-in decisions freeze permitted roles, original fact map, actual operation catalog/action schema associations, exchange schema and full instructions in the original model-call request. Fingerprints and host identities stay internal. |
| Parent request | `runtime.py:1148` `exchange_schema`, `:1155` `exchange_response`, `:1263` `exchange_decision` | The model emits one `request_context` envelope while its logical decision is pending. The lookup is not admitted as an ordinary selected action. |
| Resolve source information | `runtime.py:3408` `Workflow.execute` with `_composition_lookup=True`, `:2302` `pending_contract_information`, `:2309` `contract_information_reply`; `episode_contract_information.py:122` `return_contract_information` | The handler checks the original permitted role/source and reads only the original declared fact contract. It returns an internal outcome with `information_kind`, `role`, `source`, `meaning`, `report_schema`, `schema_sha256`, and `text`. No native acquisition, parser, result reader, source lookup or child commission occurs. |
| Persist the exchange | `decision_exchanges.py:145` `resolve_lookup`; `runtime.py:1375` and nearby `exchange_decision` tail; `composition_information.py:42` `requested_contract_information` | The reply is frozen in the existing physical-exchange journal. Repeated identical contract replies are consolidated for presentation inside the same decision; conflicting replies fail. The action index, completion state and local yield observations do not advance. |
| Model-facing reply | `providers.py:308` `_presentation`; `scientific_process_prompt.py:304` `_lookup`, `:394` `_steering`, `:495` `render_scientific_process_prompt` | The provider reconstructs the published scientific state, obtains current or restored lookup replies, rebuilds the full TASK and STEERING, and `_lookup` emits `result.text`. This is the exact message boundary addressed by TEMPLATE001. The generic fallback serializes JSON for contexts outside existing text-task branches; that is not proof of compliant scientific communication. |
| Same pending decision | `runtime.py:1263` `exchange_decision`, especially `:1314` lookup-result frame and `:1357` select-action branch | The next physical exchange has the same logical decision index and original yield snapshot. Only a later `select_action` exits the exchange loop. The information reply does not select that action. |
| Selected form consumer | `runtime.py:3552` `action_schema`, `:3653` `selected`, `:2331` `expanded_contract_form`; `episode_contract_information.py:149` `_references`, `:187` `expand_fact_form`, `:224` `validate_saved_fact_form` | The parent's existing child action supplies `schema_json`. Expansion admits only the explicit top-level UniProt shorthand, checks the original role/source advertisement, invokes the pure registered builder, saves the original compact declaration, and verifies compact/expanded correspondence. The later typed form and original declaration remain internal and unchanged. |

`DecisionSource.exchange_decision` was inspected as a complete function. It
services explicit exchanges and returns the parent's selected action; it does
not invoke a continuation controller, create a completed action, or project
credit for a lookup. This proposal adds no private reasoning loop.

## What each proposed information element changes in the parent's decision

| Information | Parent decision it supports | Source authority |
| --- | --- | --- |
| Role and source availability | Whether this child can promise this return at all | Original frozen role/fact map; `return_contract_information` |
| Compact top-level field with explicit selection | How to express the chosen return without hand-writing the expanded schema | `episode_contract_information.py:149-221`; compact004; compact-selection test source |
| Assigned-page scope | Which already assigned acquisition the return describes; no new search/pagination choice | Contract002 §3; `PublicationSelector` at `uniprot_return_contracts.py:332` |
| `all_native_records`, exact primary accession, original ordinal | How to select records when native positions are unknown, or when exact identity/position is known | `RecordSelector` at `:835`; Contract002 §5 |
| Page metadata fields | Whether the later decision needs query totals, release or an explicitly returned pagination operand | `PageIntegerRequest`, `PageTokenRequest`, `PageTextRequest` at `:303-328` |
| Integers and tokens | Which exact identity/version/length/checksum values the later decision needs | `IntegerRequest`, `TokenRequest` at `:213-234`; Contract002 scalar joins |
| Bounded text and semantic pointer | Which exact textual leaf and characters are needed; whether its address is known | `TextRequest` at `:235`; `_TEXT_POINTERS` at `:1110`; validator at `:1161`; Contract002 §5 |
| EC owner/component | Whether the requested annotation concerns the whole entry or a native component | `ECRequest` at `:257`; `_EC_POINTER` at `:1109`; Contract002 §5 |
| Database membership and explicit property windows | Whether all GO or other exact database members and selected properties answer the later question, without unknown xref ordinals | `XrefRequest` at `:281`, `XrefSelector` at `:872`, `XrefPropertyRequest` at `:904` |
| Feature overlap and location qualifications | Whether entry-region relationships matter, while preserving fuzzy/other-sequence limits | `FeatureRequest` at `:262`, `FeatureSelector` at `:853`; Contract002 §5 |
| Owned evidence and include switch | Whether source associations are requested, at which owners, without manufacturing an evidence grade | `EvidenceRequest` at `:276`, `EvidenceSelector` at `:888`; Contract002 §5 |
| Sequence window | Which exact letters the later decision needs without full-sequence delivery | `SequenceRequest` at `:289`; Contract002 §5 |
| Independent material grants | Whether later work actually needs a whole native source or full stored sequence artifact | `PageSelection` / `RecordSelection` at `:346-361`; Contract002 §4; handoff005 |
| Missing/partial/indeterminate distinctions | Whether a planned return can support absence, or only qualified incomplete information | Contract002 §§5, 6, 10; existing selected-value contract |
| Same-decision/no-yield sentence | Prevents treating information retrieval as scientific work or a controller observation | `exchange_decision`, `DecisionExchanges`, original principle 6 |

Selection alternatives and examples are taken from the existing application
definitions. `uniprot_return_selection_schema()` at `:1100` exports the internal
definition tree. `validate_uniprot_return_selection` at `:1161` rejects duplicate
selectors, mixed publication modes, incompatible token ordinals, bad semantic
pointers and invalid windows. `uniprot_selected_return_schema` at `:1220`
expands the exact data contract; `uniprot_fact_sources` at `:1228` advertises the
empty-selection base. None of that expanded tree belongs in this reply.

## Exact unfinished application integration points

1. **Scientific availability.** `ScientificProcessEpisodes` has no
   `contract_information_configuration` or `contract_information_profile`
   callback. `EpisodeBindingRegistry` discovers those callbacks, while
   `composition_information.metadata_catalog` advertises the two contract
   operations only for the profile. The source search found an implementation
   only in `LiteratureEpisodes` (`literature_episodes.py:509-516`), restricted to
   its roles and a specifically configured root annotation parent. Do not bind
   literature work to make UniProt information available. Root must connect the
   existing information profile prospectively to the intended scientific
   receiver, preserving existing role edges and `decision_exchange_v1`.

2. **Selection text instead of expanded-schema text.**
   `return_contract_information` currently always calls
   `render_schema_information(report_schema)`. That function preserves every
   schema field in named-definition tables (`schema_information_text.py:95`),
   including internal witnesses; text formatting does not make that an
   appropriate selection guide. Its source-specific reply should use the
   reviewed TEMPLATE001 for this role/source while retaining the existing
   internal result and validation responsibilities. The source of allowed
   selection vocabulary remains `uniprot_return_contracts.py`, not a runtime read
   of this verification directory or a separately maintained schema.

3. **Original information and replay.**
   `DecisionSource.validate_contract_exchange_history` (`runtime.py:1216-1261`)
   reconstructs `contract_information_reply` and requires exact equality with
   the saved lookup. The original frozen source row currently carries only the
   advertised return schema and meaning, not a prospective selection-guide
   declaration; `_fact` also discards any extra metadata. The empty selection
   annotation itself does not contain the record-selector schema. Root must
   define how fresh decisions freeze the reviewed guide/selection-information
   authority and how old decisions keep their original reply. Changing a global
   formatter or consulting current schemas while replaying old calls is
   insufficient. This proposal does not invent a new persisted key or claim the
   issue is solved.

4. **Actual text-task branch.** The provider already reaches
   `_task(state, instructions)` on a lookup continuation for a published
   scientific context and `_lookup` already consumes `result.text`. Verify this
   exact branch, including bootstrap after conversation loss and accumulated
   `pending_contract_information`. A non-published/generic annotation context can
   still reach the provider's JSON fallback; this proposal does not treat that
   as a repaired message. Keep the complete original task; do not replace it
   with the selection guide or a one-line scientist role.

5. **Compact selection connection.** `Workflow.expanded_contract_form` uses the
   frozen fact map under the information profile. Its profile-absent path does
   not generically install compact references for ordinary scientific work;
   absent an existing saved special declaration, it falls back to the original
   literal compiler. Root must verify that the informed scientific parent
   reaches the already implemented compact branch. No change to selector or
   schema-expansion mechanics is proposed.

6. **Forwarded publication operands remain distinct.** The existing
   `received_publication` selector requires exact `source_id` and
   `publication_sha256`; only `results` may use `assigned_page`. The source
   advertisement for scientific children does not supply an already received
   publication operand or make an unknown future one selectable. Internal
   witnesses must remain outside this message. For forwarding, original
   selectors/cells and explicit grants must have actually been delivered;
   changed or unreceived fields yield `field_not_received`. This initial
   results-selection reply introduces no alias, source read, automatic child,
   projection of new windows, or automatic route through another episode. The
   forwarded-operand presentation path remains unfinished.

7. **Verification still needed after feedback and code.** Root's bounded runner
   should exercise an actual published scientific decision: child/source
   discovery → explicit contract request → reviewed text under full TASK →
   select-action with compact nonempty form → original expanded declaration.
   Compare action/observation/yield state before and after only the lookup;
   verify no source/artifact receipts or acquisition. Exercise unknown native
   positions via all-record/GO/overlap selection; unavailable role/source;
   restart during the same decision; exact historical reply reconstruction;
   original task retention; and absence of expanded schema/witness text. These
   are future integration cases, not checks executed here.

## Evidence and limits

The inspected design records were Contract002 in full (with its explicitly
superseded literal-only entry point), compact004, root handoff003, host
handoff005, AGENTS.md and TASK_AND_STEERING.md. The compact test file was read
as source, not run. Relevant selection definitions and complete lookup,
framing, provider, prompt and compact-expansion functions were inspected;
application state and databases were not read. No changed tool, completed-tool
count, integrated capability, user approval or live-resource verification is
claimed. Task603, task607, source/sequence downstream access, and broader R6
provider work remain separate.
