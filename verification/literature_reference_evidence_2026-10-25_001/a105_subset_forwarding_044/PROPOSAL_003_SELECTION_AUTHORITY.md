# Revised report selection is recorded before a runtime action exists

Additive correction to002, discovered by actual existing native-rate repair
tests in the bounded003 verification group. The two released production files
and two new test files remain the exact ownership boundary. No runtime edit,
extra action, observation or model call is proposed or needed.

The complete Workflow.selected3152–3184 path calls redeliver directly before
constructing an ActionLeaf or recording runtime_actions. ReportRedelivery
intentionally adds no own-action observation. Consequently002's requirement
that every repair already have a runtime_actions row rejects legitimate
existing repairs. The isolated new fixture initially planted such an action
and did not expose that distinction; the actual native consumer did.

The actual selected decision is already durably stored in runtime_model_calls
at the same run/receiving episode/call index with purpose='decision'. The
authenticator may project **only** SQL `response -> '$.selection'` for that one
decision. This is the same public selected-action projection already used by
runtime's public history consumer. No complete request/response, provider
history, prompt or private reasoning is selected or loaded. This is a code-path
correction, not permission for operator/model-history examination.

If an actual runtime_actions selection exists it remains authority. If both
that action and the narrow recorded decision exist, their exact canonical
selections must agree; a conflict is an error. If only the durable decision
exists, it authenticates the already selected repair without manufacturing an
action row or observation. Missing both is a structured binding mismatch.

All other002 checks remain: the repair kind; exact selected purpose and schema;
current attempt delivery_ref; earliest original delivery at the same receiver;
original child identity and original frozen contract; exact admitted subset;
per-view binding and saved-cell validation. No arbitrary schema inclusion
relationship authorizes new information.

The revised fixture will use the actual decision-only representation and check
wrong purpose/schema, delivery identity, original contract, decision purpose and
conflicting action/decision selections. The affected existing native repair and
optical revised-redelivery tests must pass with unchanged runtime code and
unchanged observation histories before final verification is claimed.
