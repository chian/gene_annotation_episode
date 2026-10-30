# Connected contract information API (059)

Only `LiteratureEpisodes(..., rate_population=True, contract_information_profile="operation_contract_information_v1")` opts in. `None` omits the descriptor configuration field and retains the legacy action-generation/presentation behavior. The explicit profile requires the existing `decision_exchange_v1` protocol. No protocol is switched automatically. The registry's optional `contract_information_configuration()` hook returns the declared profile (or None) without a context/catalog/fact/source lookup; Workflow construction checks it before an owned provider enters. The separate contextual `contract_information_profile(context)` hook controls applicability to bound literature roles and the explicitly assigned source-evidence annotation parent.

There is no new selected action or ordinary callable operation. Two closed requests are added only to the existing `request_context` / `composition_information` lookup branches:

- `episode.operation_contract`: arguments exactly `{operation: nonempty string}`. Unique original actual own-operation lookup; unavailable names return existing typed invalid feedback.
- `episode.return_contract`: arguments exactly `{role: nonempty string, source: nonempty string}`. Only original permitted child roles and declared typed recorded-fact sources; unavailable roles/sources return typed invalid feedback. A leaf with no children has the same valid small request schema and no permitted return-source results.

Their result declarations are the accepted frozen pure-module outcomes. Full requested meaning and lossless schema text are presented under TASK. Their host payload and fingerprints remain internal. A lookup never commissions work, fills a fact, closes an action, creates an observation, or controls continuation. Direct invocation needs no lookup.

The original logical `runtime_model_calls.request` gains exactly one host-only `contract_information` member with these closed keys:

```
version: operation_contract_information_v1
permitted_child_roles: ordered unique role strings
fact_sources_by_role: complete frozen role -> existing source declaration maps
fact_sources_sha256: digest of that exact frozen map
catalog_sha256: digest of original context.tools
 action_schema_sha256: digest of original host schema
exchange_schema: complete original exchange schema in its persisted canonical object order
instructions: complete original instructions
```

(The leading space in the display before `action_schema_sha256` has no semantic significance.) Actual JSON examples in the measured original logical requests are authoritative. Frozen declarations contain no initial fact values. Existing untyped builtin fact labels stay available in literal forms; requests for unavailable declared typed schemas return invalid feedback.

Each original population action branch retains its complete unchanged standalone argument schema, including isolated local-reference `$id` semantics, and adds host-only `x-argument-transport: json_object_contract_information_v1`. Original context catalog rows carry the corresponding `argument_transport`. Validation checks original catalog/schema agreement. Provider generation substitutes a string argument only on that frozen marked branch and strips the marker. Authoritative decoding parses its outer JSON object once using the existing strict parser, including formerly simple object branches. Nested literal strings, omitted fields and explicit nulls survive. Original host schemas validate the decoded object. Default/unmarked transport is unchanged.

Original physical exchange request/restoration/frame/output schema and selected response are checked against the frozen logical declaration. Completed replies remain immutable public exchange rows. Continuing lookup frames also carry `pending_contract_information`, derived solely from already answered contract replies in this same decision. Provider presentation retains all those requested texts across unrelated history lookups. Bootstrap after provider loss/reconstruction uses the existing answered public exchanges. No scientific revision, old frame, controller input, private provider history or extra model-composer cache is introduced. Saved opted-in decisions bypass current catalog/action-schema construction; saved validation uses original declarations.

Parent `schema_json` remains the exact selected string. Only an entire top-level field node `{"$ref":"episode-fact:<source>"}` expands through the frozen original permitted child source map before the existing closed-form guard/compile checks. Ordinary fields, literal schemas, explicit constraints and bounded interpretations remain untouched. The accepted pure declaration is stored separately in `request.message.report_contract_declaration`; the original complete expanded schema remains in the original report contract and child goal. Both are frozen in the actual original C1 commission request, while the exact compact selection stays in its original selected action. Existing saved child identity is located before expansion on blocking replay. Saved validation never reloads a current fact factory. The actual independent C1 factory forwards only the original host declaration to Workflow.build and checks whole original request equality. C4 and native custody code are unchanged.

No implementation changes were made to communication.KEYWORDS, closed-form guard, base044, source readers, calculators, application execution binding, C1 coordinator, C4 admission, durable backend, shared method_loop, W05, A101, model settings or controller settings. There is no paper router, masked catalog, selected default operation set, mandatory information lookup, scientific gate or new stop rule.
